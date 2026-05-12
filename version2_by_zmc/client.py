import socket
import threading
import subprocess
import os
import sys
from shared import primeste_mesaj, trimite_mesaj, create_request

def asculta_pentru_taskuri(port):
    """Thread care stă la dispoziția serverului."""
    serviciu = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serviciu.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serviciu.bind(('0.0.0.0', port))
    serviciu.listen()

    while True:
        conn, _ = serviciu.accept()
        task = primeste_mesaj(conn)
        if task:
            ext = os.path.splitext(task.get('filename') or "")[1].lower()
            nume_fisier = f"executabil_{os.getpid()}{ext or '.bin'}"
            with open(nume_fisier, "wb") as f:
                f.write(task['payload'])

            if os.name != 'nt': os.chmod(nume_fisier, 0o755)

            comanda = [sys.executable, nume_fisier] + task['args'] if ext == '.py' else [os.path.abspath(nume_fisier)] + task['args']

            print(f"[WORKER] Rulez: {comanda}")
            proces = subprocess.run(comanda)

            trimite_mesaj(conn, {'status': 'OK', 'exit_code': proces.returncode})

            if os.path.exists(nume_fisier): os.remove(nume_fisier)
        conn.close()

if __name__ == "__main__":
    port_local = int(input("Portul tau de worker: "))

    threading.Thread(target=asculta_pentru_taskuri, args=(port_local,), daemon=True).start()

    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.connect(('127.0.0.1', 3333))

    trimite_mesaj(soc, create_request('REGISTER', worker_port=port_local))
    primeste_mesaj(soc)

    print("Gata! Comenzi: 'submit <fisier> <argumente>' sau 'exit'")
    while True:
        cmd = input("> ").split()
        if not cmd: continue

        if cmd[0] == 'exit':
            trimite_mesaj(soc, create_request('UNREGISTER', worker_port=port_local))
            break

        elif cmd[0] == 'submit' and len(cmd) >= 2:
            with open(cmd[1], "rb") as f:
                continut = f.read()

            cerere = create_request('SUBMIT_TASK', payload=continut, args=cmd[2:], filename=cmd[1])
            trimite_mesaj(soc, cerere)

            rezultat = primeste_mesaj(soc)
            print(f"[REUSITA] Cod iesire: {rezultat['exit_code']}")

    soc.close()