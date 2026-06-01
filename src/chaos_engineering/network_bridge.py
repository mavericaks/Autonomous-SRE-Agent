import socket, threading, sys, time

def handle_client(client_socket, target_host, target_port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.connect((target_host, target_port))
    except Exception as e:
        print(f"[!] Unable to connect to {target_host}:{target_port} - {e}")
        client_socket.close()
        return

    def forward(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if len(data) == 0: break
                dst.sendall(data)
        except: pass
        src.close()
        dst.close()

    threading.Thread(target=forward, args=(client_socket, server_socket), daemon=True).start()
    threading.Thread(target=forward, args=(server_socket, client_socket), daemon=True).start()

def start_proxy(listen_port, target_host, target_port, name):
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy.bind(("0.0.0.0", listen_port))
    proxy.listen(100)
    print(f"[*] {name} Bridge Active: Listening on 0.0.0.0:{listen_port} -> Forwarding to {target_host}:{target_port}")
    
    while True:
        client_socket, addr = proxy.accept()
        threading.Thread(target=handle_client, args=(client_socket, target_host, target_port), daemon=True).start()

if __name__ == "__main__":
    print("=====================================================")
    print("Starting Autonomous SRE Network Bridge for Mobile Devices")
    print("If Windows Firewall prompts you, click 'Allow Access'")
    print("=====================================================")
    
    # Bridge 1: The Kubernetes Application (Video Stream / TPS Endpoint)
    threading.Thread(target=start_proxy, args=(30080, "192.168.137.229", 30080, "K8s App"), daemon=True).start()
    
    # Bridge 2: The Real-Time Visual Dashboard UI
    threading.Thread(target=start_proxy, args=(8080, "127.0.0.1", 8080, "Visual Dashboard"), daemon=True).start()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)
