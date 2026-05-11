import socket
import threading
from shared import Request, Response, send_msg, recv_msg

HOST = "0.0.0.0" # Bind to all for Docker compatibility
PORT = 3333

class ClusterManager:
    def __init__(self):
        self.workers = []
        self.rr_index = 0
        self.lock = threading.Lock()

    def add_worker(self, ip, port):
        with self.lock:
            if (ip, port) not in self.workers:
                self.workers.append((ip, port))
                print(f"[REG] New worker: {ip}:{port}")

    def remove_worker(self, ip, port):
        with self.lock:
            if (ip, port) in self.workers:
                self.workers.remove((ip, port))
                self.rr_index = 0
                print(f"[UNREG] Worker removed: {ip}:{port}")

    def get_next_worker(self):
        with self.lock:
            if not self.workers: return None
            worker = self.workers[self.rr_index]
            self.rr_index = (self.rr_index + 1) % len(self.workers)
            return worker

manager = ClusterManager()

def dispatch_to_worker(worker_addr, task_req):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(worker_addr)
            send_msg(s, task_req)
            return recv_msg(s)
    except Exception as e:
        print(f"[ERR] Worker {worker_addr} failed: {e}")
        return None

def handle_connection(conn, addr):
    try:
        while True:
            req = recv_msg(conn)
            if not req: break
            
            if req.command == 'REGISTER':
                manager.add_worker(addr[0], req.worker_port)
                send_msg(conn, Response('OK'))
            
            elif req.command == 'UNREGISTER':
                manager.remove_worker(addr[0], req.worker_port)
                send_msg(conn, Response('OK'))
            
            elif req.command == 'SUBMIT_TASK':
                target = manager.get_next_worker()
                if not target:
                    send_msg(conn, Response('ERROR', message="No workers available"))
                    continue
                
                result = dispatch_to_worker(target, req)
                if result is None:
                    manager.remove_worker(target[0], target[1])
                    send_msg(conn, Response('ERROR', message="Worker crashed during task"))
                else:
                    send_msg(conn, result)
    finally:
        conn.close()

if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[*] Dispatcher Server active on port {PORT}")
    while True:
        c, a = server.accept()
        threading.Thread(target=handle_connection, args=(c, a)).start()