import socket
import threading
import pydivert
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
from cryptography.hazmat.primitives import padding


SHARED_KEY = b'ThisIsASecretKeyOf32BytesLength!'

SERVER_ADDRESS = "10.100.102.8"
SERVER_PORT = 3030
print("Connected to server")


def encrypt(data):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(SHARED_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return iv + ciphertext

def decrypt(encrypted):
    iv = encrypted[:16]
    ciphertext = encrypted[16:]
    cipher = Cipher(algorithms.AES(SHARED_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()
    return data


def recv_all(sock , n):
    data = b''
    while len(data) < n:
        part = sock.recv(n- len(data))
        if not part:
            break
        data += part
    return data


def send_packet(client_sock , meta_data , packet_raw):
    encrypted_packet = encrypt(packet_raw)
    encrypted_metadata = encrypt(meta_data)
    metadata_len = struct.pack('!I', len(encrypted_metadata))
    packet_len = struct.pack('!I', len(encrypted_packet))
    client_sock.sendall(metadata_len + encrypted_metadata + packet_len + encrypted_packet)


def collect_data_from_server(client_sock): #also reinject back to packet buffer
    with pydivert.WinDivert("false") as w:
        while True:
            packet_len = struct.unpack("!I", recv_all(client_sock , 4))[0]
            data_from_server = recv_all(client_sock, packet_len)
            decrypted = decrypt(data_from_server)
            interface_len = struct.unpack("!I", recv_all(client_sock , 4))[0]
            interface_encrypted = recv_all(client_sock, interface_len)
            interface = eval(decrypt(interface_encrypted).decode())
            packet_from_server = pydivert.Packet(raw=decrypted, direction=pydivert.Direction.INBOUND, interface=interface)
            print("recieved back from my server" , packet_from_server)
            w.send(packet_from_server)

def collect_packets_from_user(client_sock):
    f = f"outbound and ip and ((tcp and (ip.DstAddr != {SERVER_ADDRESS} or tcp.DstPort != {SERVER_PORT})) or (udp and (ip.DstAddr != {SERVER_ADDRESS} or udp.DstPort != {SERVER_PORT})))"
    with pydivert.WinDivert(f) as w:
        while True:
            packet = w.recv()
            print("sending packet to server")
            client_ip = packet.src_addr
            client_port = packet.src_port

            packet.src_addr = SERVER_ADDRESS

            packet.recalculate_checksums()
            meta_data = f"{client_ip}:{client_port}:{packet.interface}".encode()
            send_packet(client_sock, meta_data, bytes(packet.raw))
            print("sent this packet" , packet)

def main():
    with socket.socket() as client_sock:
        try:
            client_sock.connect((SERVER_ADDRESS, SERVER_PORT))
        except socket.error as e:
            return
        print("Connected to server")

        threading.Thread(target=collect_packets_from_user, args=(client_sock,)).start()
        threading.Thread(target=collect_data_from_server, args=(client_sock,), daemon=True).start()

        threading.Event().wait()

if __name__ == "__main__":
    main()