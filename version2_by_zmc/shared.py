import pickle

BUFFER_SIZE = 4096

def create_request(command, payload=None, args=None, worker_port=None, filename=None):
    """Creează un dicționar simplu în loc de o instanță de clasă."""
    return {
        'command': command,
        'payload': payload,
        'args': args if args else [],
        'worker_port': worker_port,
        'filename': filename
    }

def create_response(status, exit_code=None, message=None):
    """Creează un răspuns sub formă de dicționar."""
    return {
        'status': status,
        'exit_code': exit_code,
        'message': message
    }

def trimite_mesaj(soc, date_dict):
    """Serializare: Transformă dicționarul în octeți și îl trimite."""
    date_binare = pickle.dumps(date_dict)
    soc.sendall(len(date_binare).to_bytes(4, 'big') + date_binare)

def primeste_mesaj(soc):
    """Deserializare: Citește lungimea și reconstruiește dicționarul."""
    raw_len = soc.recv(4)
    if not raw_len: return None
    lungime = int.from_bytes(raw_len, 'big')
    
    date_acumulate = b""
    while len(date_acumulate) < lungime:
        pachet = soc.recv(BUFFER_SIZE)
        if not pachet: break
        date_acumulate += pachet
    return pickle.loads(date_acumulate) if date_acumulate else None