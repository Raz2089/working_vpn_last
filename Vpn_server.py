import socket
import threading
import struct
import os
import pydivert
from collections import deque
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from concurrent.futures import ThreadPoolExecutor
import Vpn_server_gui

SHARED_KEY = b'ThisIsASecretKeyOf32BytesLength!'

connection_map = Vpn_server_gui.connection_map
map_lock = Vpn_server_gui.map_lock
packets_to_send_to_web = deque()
packets_to_web_lock = threading.Lock()

def encrypt(data):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(SHARED_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    return iv + encryptor.update(padded_data) + encryptor.finalize()

def decrypt(encrypted):
    iv = encrypted[:16]
    cipher = Cipher(algorithms.AES(SHARED_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(encrypted[16:]) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        part = sock.recv(n - len(data))
        if not part:
            break
        data += part
    return data

def find_available_port():
    port_sock = socket.socket()
    port_sock.bind(('0.0.0.0', 0))
    return port_sock.getsockname()[1], port_sock

def add_to_connection_map(packet, client_sock, client_ip, client_port, interface):
    key = (packet.dst_addr, packet.dst_port, packet.src_port)
    with map_lock:
        if key not in connection_map:
            connection_map[key] = (client_sock, client_ip, int(client_port), interface)



def handle_client(client_sock, available_port, port_sock, addr):
    try:
        while True:
            metadata_len = struct.unpack("!I", recv_all(client_sock, 4))[0]
            encrypted_meta_data = recv_all(client_sock, metadata_len)
            meta_data = decrypt(encrypted_meta_data).decode()

            client_ip, client_port, interface_id = meta_data.strip().split(":")
            interface = tuple(map(int, interface_id.strip("()").split(",")))

            raw_packet_len = struct.unpack("!I", recv_all(client_sock, 4))[0]
            packet_raw = recv_all(client_sock, raw_packet_len)
            decrypted_packet_raw = decrypt(packet_raw)

            packet = pydivert.Packet(raw=decrypted_packet_raw, direction=pydivert.Direction.OUTBOUND, interface=(1,0))
            packet.src_port = available_port
            add_to_connection_map(packet, client_sock, client_ip, client_port, interface)

            with packets_to_web_lock:
                if packet.tcp and packet.tcp.syn:
                    packets_to_send_to_web.appendleft(packet)
                else:
                    packets_to_send_to_web.append(packet)
    except:
        pass
    finally:
        Vpn_server_gui.disconnect_client(addr)
        client_sock.close()
        port_sock.close()

def send_packets_to_web():
    with pydivert.WinDivert("false") as w:
        while True:
            with packets_to_web_lock:
                if packets_to_send_to_web:
                    packet = packets_to_send_to_web.popleft()
                    w.send(packet)

def handle_packet_from_web(packet_from_web):
    key = (packet_from_web.src_addr, packet_from_web.src_port, packet_from_web.dst_port)
    with map_lock:
        entry = connection_map.get(key)
        if entry:
            try:
                client_sock, client_ip, client_port, interface_id = entry
                client_sock.fileno()
                packet_from_web.interface = interface_id
                packet_from_web.dst_addr = client_ip
                packet_from_web.dst_port = client_port
                packet_from_web.recalculate_checksums()

                encrypted_packet = encrypt(bytes(packet_from_web.raw))
                interface_id_bytes = encrypt(str(interface_id).encode())
                client_sock.sendall(
                    struct.pack("!I", len(encrypted_packet)) + encrypted_packet +
                    struct.pack("!I", len(interface_id_bytes)) + interface_id_bytes
                )
            except:
                pass

def sniff_responses_from_web():
    filter_str = f"inbound and ip and (tcp or udp) and (tcp.DstPort != 3030 or udp.DstPort != 3030)"
    executor = ThreadPoolExecutor(max_workers=100)
    with pydivert.WinDivert(filter_str) as w:
        while True:
            packet_from_web = w.recv()
            if packet_from_web.tcp and packet_from_web.tcp.syn and packet_from_web.tcp.ack:
                threading.Thread(target=handle_packet_from_web, args=(packet_from_web,), daemon=True).start()
            else:
                executor.submit(handle_packet_from_web, packet_from_web)

def main():
    SERVER_ADDRESS = "10.100.102.8"
    SERVER_PORT = 3030

    Vpn_server_gui.start_gui()
    threading.Thread(target=send_packets_to_web, daemon=True).start()
    threading.Thread(target=sniff_responses_from_web, daemon=True).start()

    with socket.socket() as server_sock:
        server_sock.bind((SERVER_ADDRESS, SERVER_PORT))
        server_sock.listen()
        print("Server listening on", SERVER_ADDRESS, SERVER_PORT)

        while True:
            client_conn, addr = server_sock.accept()
            available_port, port_sock = find_available_port()
            print("Client connected:", addr)

            Vpn_server_gui.create_client_square(addr, client_conn)
            threading.Thread(
                target=handle_client,
                args=(client_conn, available_port, port_sock, addr),
                daemon=True
            ).start()

if __name__ == "__main__":
    main()
