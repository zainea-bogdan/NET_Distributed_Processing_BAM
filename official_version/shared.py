import pickle

# Constants for common network settings
BUFFER_SIZE = 4096

class Request:
    """Standardized request format for all network operations."""
    def __init__(self, command, payload=None, args=None, worker_port=None, filename=None):
        self.command = command      # 'REGISTER', 'UNREGISTER', 'SUBMIT_TASK'
        self.payload = payload      # Binary content
        self.args = args or []      # List of arguments
        self.worker_port = worker_port
        self.filename = filename    # Original filename, used to determine execution method

class Response:
    """Standardized response format for server/worker feedback."""
    def __init__(self, status, exit_code=None, message=None):
        self.status = status        # 'OK', 'ERROR'
        self.exit_code = exit_code  # Exit code from subprocess
        self.message = message      # Debug/Info message

def send_msg(sock, obj):
    """Helper to send pickled objects with a 4-byte length prefix."""
    data = pickle.dumps(obj)
    sock.sendall(len(data).to_bytes(4, 'big') + data)

def recv_msg(sock):
    """Helper to receive pickled objects using the length prefix."""
    raw_len = sock.recv(4)
    if not raw_len: return None
    msg_len = int.from_bytes(raw_len, 'big')
    
    data = b""
    while len(data) < msg_len:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk: break
        data += chunk
    return pickle.loads(data) if data else None