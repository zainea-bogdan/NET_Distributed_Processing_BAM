import pickle

BUFFER_SIZE = 4096

def create_request(command, payload=None, args=None, worker_port=None, filename=None, sender_port=None):
    return {
        'command': command,
        'payload': payload,
        'args': args if args else [],
        'worker_port': worker_port,
        'filename': filename,
        'sender_port': sender_port
    }

def trimite_mesaj(soc, date_dict):
    try:
        date_binare = pickle.dumps(date_dict)
        soc.sendall(len(date_binare).to_bytes(4, 'big') + date_binare)
    except Exception as e:
        print(f"Eroare trimitere: {e}")

def primeste_mesaj(soc):
    try:
        raw_len = soc.recv(4)
        if not raw_len:
            return None
        lungime = int.from_bytes(raw_len, 'big')
        date = b""
        while len(date) < lungime:
            pachet = soc.recv(min(BUFFER_SIZE, lungime - len(date)))
            if not pachet:
                break
            date += pachet
        return pickle.loads(date) if date else None
    except Exception as e:
        print(f"Eroare primire: {e}")
        return None