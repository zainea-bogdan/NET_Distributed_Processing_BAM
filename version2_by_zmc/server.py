import socket
import threading
from shared import primeste_mesaj, trimite_mesaj, create_response

# Date globale (Starea serverului)
lista_workeri = []  # Listă de tupluri (ip, port)
index_rr = 0        # Indexul pentru Round-Robin
lock = threading.Lock()

def adauga_worker(ip, port):
    global lista_workeri
    with lock:
        if (ip, port) not in lista_workeri:
            lista_workeri.append((ip, port))
            print(f"[+] Worker nou: {ip}:{port}")

def sterge_worker(ip, port):
    global lista_workeri, index_rr
    with lock:
        if (ip, port) in lista_workeri:
            lista_workeri.remove((ip, port))
            index_rr = 0 # Resetăm indexul pentru siguranță
            print(f"[-] Worker eliminat: {ip}:{port}")

def alege_worker_urmator():
    global lista_workeri, index_rr
    with lock:
        if not lista_workeri: return None
        worker = lista_workeri[index_rr]
        index_rr = (index_rr + 1) % len(lista_workeri)
        return worker

def trimite_task_la_worker(adresa_worker, cerere_task):
    """Conexiune temporară către worker pentru a-i da de lucru."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(adresa_worker)
            trimite_mesaj(s, cerere_task)
            return primeste_mesaj(s)
    except:
        return None

def trateaza_client(conexiune, adresa):
    try:
        while True:
            date = primeste_mesaj(conexiune)
            if not date: break

            comanda = date['command']

            if comanda == 'REGISTER':
                adauga_worker(adresa[0], date['worker_port'])
                trimite_mesaj(conexiune, create_response('OK'))

            elif comanda == 'UNREGISTER':
                sterge_worker(adresa[0], date['worker_port'])
                trimite_mesaj(conexiune, create_response('OK'))

            elif comanda == 'SUBMIT_TASK':
                worker_tinta = alege_worker_urmator()
                if not worker_tinta:
                    trimite_mesaj(conexiune, create_response('ERROR', message="Niciun worker activ"))
                    continue

                rezultat = trimite_task_la_worker(worker_tinta, date)
                if rezultat is None:
                    sterge_worker(worker_tinta[0], worker_tinta[1])
                    trimite_mesaj(conexiune, create_response('ERROR', message="Worker-ul a murit"))
                else:
                    trimite_mesaj(conexiune, rezultat)
    finally:
        conexiune.close()

if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 3333))
    server.listen()
    print("[SERVER] Ascult pe portul 3333...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=trateaza_client, args=(conn, addr)).start()