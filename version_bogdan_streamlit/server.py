import socket
import threading
from datetime import datetime
from collections import deque
from shared import primeste_mesaj, trimite_mesaj

lista_workeri = []
index_rr = 0
lock = threading.Lock()
istoric = []
log_buffer = deque(maxlen=100)


def log(mesaj):
    linie = f"[{datetime.now().strftime('%H:%M:%S')}] {mesaj}"
    print(linie)
    with lock:
        log_buffer.append(linie)


def adauga_worker(ip, port):
    global lista_workeri
    with lock:
        if (ip, port) not in lista_workeri:
            lista_workeri.append((ip, port))
    log(f"[REGISTER] Worker nou: {ip}:{port}")


def sterge_worker(ip, port):
    global lista_workeri, index_rr
    with lock:
        if (ip, port) in lista_workeri:
            lista_workeri.remove((ip, port))
            index_rr = 0
    log(f"[UNREGISTER] Worker eliminat: {ip}:{port}")


def alege_worker_urmator():
    global lista_workeri, index_rr
    with lock:
        if not lista_workeri:
            return None
        worker = lista_workeri[index_rr % len(lista_workeri)]
        index_rr += 1
        return worker


def adauga_in_istoric(sender_port, executor, task_name, exit_code):
    with lock:
        istoric.append({
            'Ora': datetime.now().strftime('%H:%M:%S'),
            'Sender': f"Worker:{sender_port}" if sender_port else 'Dashboard',
            'Executor': f"{executor[0]}:{executor[1]}",
            'Task': task_name or 'unknown',
            'Exit Code': exit_code
        })
        if len(istoric) > 50:
            istoric.pop(0)


def trimite_task_la_worker(adresa_worker, cerere):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(adresa_worker)
            trimite_mesaj(s, cerere)
            return primeste_mesaj(s)
    except Exception as e:
        log(f"[ERR] Worker {adresa_worker} indisponibil: {e}")
        return None


def trateaza_client(conexiune, adresa):
    try:
        while True:
            date = primeste_mesaj(conexiune)
            if not date:
                break

            comanda = date.get('command')

            if comanda == 'REGISTER':
                adauga_worker(adresa[0], date['worker_port'])
                trimite_mesaj(conexiune, {'status': 'OK'})

            elif comanda == 'UNREGISTER':
                sterge_worker(adresa[0], date['worker_port'])
                trimite_mesaj(conexiune, {'status': 'OK'})

            elif comanda == 'SUBMIT_TASK':
                worker_tinta = alege_worker_urmator()
                if not worker_tinta:
                    log("[WARN] Niciun worker activ pentru task")
                    trimite_mesaj(conexiune, {'status': 'ERROR', 'message': 'Niciun worker activ'})
                    continue

                task_name = date.get('filename', 'unknown')
                sender_port = date.get('sender_port')
                log(f"[DISPATCH] '{task_name}' de la Worker:{sender_port} → {worker_tinta[0]}:{worker_tinta[1]}")

                rezultat = trimite_task_la_worker(worker_tinta, date)
                if rezultat is None:
                    sterge_worker(worker_tinta[0], worker_tinta[1])
                    trimite_mesaj(conexiune, {'status': 'ERROR', 'message': 'Worker offline'})
                else:
                    rezultat['executor_port'] = worker_tinta[1]
                    adauga_in_istoric(sender_port, worker_tinta, task_name, rezultat.get('exit_code'))
                    log(f"[DONE] '{task_name}' finalizat | exit code: {rezultat.get('exit_code')}")
                    trimite_mesaj(conexiune, rezultat)

            elif comanda == 'GET_STATUS':
                with lock:
                    workeri_curent = list(lista_workeri)
                trimite_mesaj(conexiune, {'status': 'OK', 'workers': workeri_curent})

            elif comanda == 'GET_LOGS':
                with lock:
                    loguri = list(log_buffer)
                trimite_mesaj(conexiune, {'status': 'OK', 'logs': loguri})

            elif comanda == 'GET_HISTORY':
                with lock:
                    istoric_curent = list(istoric)
                trimite_mesaj(conexiune, {'status': 'OK', 'history': istoric_curent})

    finally:
        conexiune.close()


if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 3333))
    server.listen()
    log("Server pornit pe portul 3333")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=trateaza_client, args=(conn, addr), daemon=True).start()