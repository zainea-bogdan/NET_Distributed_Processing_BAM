import socket
import threading
import subprocess
import os
import sys
import time
from shared import primeste_mesaj, trimite_mesaj


def asculta_taskuri(port):
    serviciu = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serviciu.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serviciu.bind(('0.0.0.0', port))
    serviciu.listen()
    print(f"[WORKER:{port}] Ascult task-uri...")

    while True:
        conn, _ = serviciu.accept()
        task = primeste_mesaj(conn)
        if task:
            ext = os.path.splitext(task.get('filename') or '')[1].lower()
            fname = f"task_{os.getpid()}{ext or '.bin'}"
            with open(fname, 'wb') as f:
                f.write(task['payload'])

            if os.name != 'nt':
                os.chmod(fname, 0o755)

            comanda = [sys.executable, fname] + task.get('args', []) if ext == '.py' else [os.path.abspath(fname)] + task.get('args', [])

            print(f"[WORKER:{port}] Execut: {fname}")
            proces = subprocess.run(comanda)
            print(f"[WORKER:{port}] Finalizat | exit code: {proces.returncode}")

            trimite_mesaj(conn, {'status': 'OK', 'exit_code': proces.returncode})

            if os.path.exists(fname):
                os.remove(fname)
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python worker.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    threading.Thread(target=asculta_taskuri, args=(port,), daemon=True).start()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 3333))
            trimite_mesaj(s, {'command': 'REGISTER', 'worker_port': port})
            primeste_mesaj(s)
            print(f"[WORKER:{port}] Inregistrat la server cu succes.")
    except Exception as e:
        print(f"[WORKER:{port}] Eroare la inregistrare: {e}")
        sys.exit(1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[WORKER:{port}] Se inchide...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 3333))
                trimite_mesaj(s, {'command': 'UNREGISTER', 'worker_port': port})
                primeste_mesaj(s)
        except:
            pass