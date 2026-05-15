import socket
import threading
from datetime import datetime
from collections import deque
from shared import primeste_mesaj, trimite_mesaj


class ClusterManager:
    def __init__(self):
        self.workers = []
        self.rr_index = 0
        self.lock = threading.Lock()
        self.history = []
        self.log_buffer = deque(maxlen=100)

    def log(self, mesaj):
        linie = f"[{datetime.now().strftime('%H:%M:%S')}] {mesaj}"
        print(linie)
        with self.lock:
            self.log_buffer.append(linie)

    def add_worker(self, ip, port):
        with self.lock:
            if (ip, port) not in self.workers:
                self.workers.append((ip, port))
        self.log(f"[REGISTER] Worker nou: {ip}:{port}")

    def remove_worker(self, ip, port):
        with self.lock:
            if (ip, port) in self.workers:
                self.workers.remove((ip, port))
                self.rr_index = 0
        self.log(f"[UNREGISTER] Worker eliminat: {ip}:{port}")

    def get_next_worker(self):
        with self.lock:
            if not self.workers:
                return None
            worker = self.workers[self.rr_index % len(self.workers)]
            self.rr_index += 1
            return worker

    def add_to_history(self, sender_port, executor, task_name, exit_code):
        with self.lock:
            self.history.append({
                'Ora': datetime.now().strftime('%H:%M:%S'),
                'Sender': f"Worker:{sender_port}" if sender_port else 'Dashboard',
                'Executor': f"{executor[0]}:{executor[1]}",
                'Task': task_name or 'unknown',
                'Exit Code': exit_code
            })
            if len(self.history) > 50:
                self.history.pop(0)

    def dispatch_to_worker(self, worker_addr, request):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect(worker_addr)
                trimite_mesaj(s, request)
                return primeste_mesaj(s)
        except Exception as e:
            self.log(f"[ERR] Worker {worker_addr} indisponibil: {e}")
            return None

    def handle_connection(self, conn, addr):
        try:
            while True:
                date = primeste_mesaj(conn)
                if not date:
                    break

                comanda = date.get('command')

                if comanda == 'REGISTER':
                    self.add_worker(addr[0], date['worker_port'])
                    trimite_mesaj(conn, {'status': 'OK'})

                elif comanda == 'UNREGISTER':
                    self.remove_worker(addr[0], date['worker_port'])
                    trimite_mesaj(conn, {'status': 'OK'})

                elif comanda == 'SUBMIT_TASK':
                    worker_tinta = self.get_next_worker()
                    if not worker_tinta:
                        self.log("[WARN] Niciun worker activ pentru task")
                        trimite_mesaj(conn, {'status': 'ERROR', 'message': 'Niciun worker activ'})
                        continue

                    task_name = date.get('filename', 'unknown')
                    sender_port = date.get('sender_port')
                    self.log(f"[DISPATCH] '{task_name}' de la Worker:{sender_port} → {worker_tinta[0]}:{worker_tinta[1]}")

                    rezultat = self.dispatch_to_worker(worker_tinta, date)
                    if rezultat is None:
                        self.remove_worker(worker_tinta[0], worker_tinta[1])
                        trimite_mesaj(conn, {'status': 'ERROR', 'message': 'Worker offline'})
                    else:
                        rezultat['executor_port'] = worker_tinta[1]
                        self.add_to_history(sender_port, worker_tinta, task_name, rezultat.get('exit_code'))
                        self.log(f"[DONE] '{task_name}' finalizat | exit code: {rezultat.get('exit_code')}")
                        trimite_mesaj(conn, rezultat)

                elif comanda == 'GET_STATUS':
                    with self.lock:
                        workeri_curent = list(self.workers)
                    trimite_mesaj(conn, {'status': 'OK', 'workers': workeri_curent})

                elif comanda == 'GET_LOGS':
                    with self.lock:
                        loguri = list(self.log_buffer)
                    trimite_mesaj(conn, {'status': 'OK', 'logs': loguri})

                elif comanda == 'GET_HISTORY':
                    with self.lock:
                        istoric_curent = list(self.history)
                    trimite_mesaj(conn, {'status': 'OK', 'history': istoric_curent})

        finally:
            conn.close()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 3333))
        server.listen()
        self.log("Server pornit pe portul 3333")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=self.handle_connection, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    manager = ClusterManager()
    manager.start()