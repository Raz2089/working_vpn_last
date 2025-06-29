# vpn_gui.py
import tkinter as tk
from datetime import datetime
import threading

connected_clients = {}
connection_map = {}
map_lock = threading.Lock()
root = None

def create_client_square(addr, client_sock):
    if root is None:
        return

    ip, port = addr
    client_frame = tk.Frame(root, bg='#404040', relief='raised', bd=2, width=200, height=150)
    client_frame.pack_propagate(False)
    client_frame.pack(side='left', padx=10, pady=10)

    icon_frame = tk.Frame(client_frame, bg='#606060', width=60, height=60)
    icon_frame.pack_propagate(False)
    icon_frame.pack(pady=10)
    tk.Label(icon_frame, text="👤", font=('Arial', 20), bg='#606060', fg='white').pack(expand=True)

    tk.Label(client_frame, text=f"IP: {ip}", font=('Arial', 10), bg='#404040', fg='white').pack()
    tk.Label(client_frame, text=f"Port: {port}", font=('Arial', 10), bg='#404040', fg='white').pack()

    time_label = tk.Label(client_frame, text="Connected: 0s", font=('Arial', 9), bg='#404040', fg='lightgreen')
    time_label.pack()

    def disconnect_click():
        force_disconnect_client(addr)

    client_frame.bind("<Button-1>", lambda e: disconnect_click())
    for child in client_frame.winfo_children():
        child.bind("<Button-1>", lambda e: disconnect_click())

    connected_clients[addr] = {
        'connect_time': datetime.now(),
        'frame': client_frame,
        'time_label': time_label,
        'socket': client_sock
    }

def force_disconnect_client(addr):
    if addr in connected_clients:
        print(f"Force disconnecting client {addr}")
        try:
            client_sock = connected_clients[addr]['socket']
            client_sock.close()
        except Exception as e:
            print(f"Error closing socket for {addr}: {e}")

def disconnect_client(addr):
    if addr in connected_clients:
        try:
            connected_clients[addr]['frame'].destroy()
        except:
            pass
        del connected_clients[addr]
        print(f"Client {addr} disconnected")

        with map_lock:
            keys_to_remove = []
            for key, value in connection_map.items():
                if value[1] == addr[0] and value[2] == addr[1]:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del connection_map[key]

def update_client_times():
    for addr, client_info in list(connected_clients.items()):
        try:
            elapsed = datetime.now() - client_info['connect_time']
            seconds = int(elapsed.total_seconds())

            if seconds < 60:
                time_text = f"Connected: {seconds}s"
            elif seconds < 3600:
                minutes = seconds // 60
                time_text = f"Connected: {minutes}m"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                time_text = f"Connected: {hours}h {minutes}m"

            client_info['time_label'].config(text=time_text)
        except:
            pass

    if root:
        root.after(1000, update_client_times)

def create_gui():
    global root
    root = tk.Tk()
    root.title("VPN Clients")
    root.configure(bg='#2c2c2c')
    root.geometry("800x600")

    tk.Label(root, text="Connected VPN Clients",
             font=('Arial', 14, 'bold'), bg='#2c2c2c', fg='white').pack(pady=10)

    update_client_times()
    root.mainloop()

def start_gui():
    threading.Thread(target=create_gui, daemon=True).start()
