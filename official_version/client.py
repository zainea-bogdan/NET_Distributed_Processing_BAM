import socket
import threading
import subprocess
import os
import sys
from shared import Request, Response, send_msg, recv_msg


# trebuie sa setam server_ip si server_port ca sa stim unde se conecteaza clientul nostru
SERVER_IP = "127.0.0.1"
SERVER_PORT = 3333

def worker_service(port):
    """Listens for incoming tasks from the server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen()
        while True:
            conn, _ = s.accept()
            task = recv_msg(conn)
            if task:
                # Execution Logic (Requirement 2.3)
                ext = os.path.splitext(task.filename or "")[1].lower() if task.filename else ""
                tmp_name = f"task_{os.getpid()}{ext or '.bin'}"
                with open(tmp_name, "wb") as f: f.write(task.payload)

                if os.name != 'nt': os.chmod(tmp_name, 0o755)

                cmd = [sys.executable, tmp_name] + task.args if ext == '.py' else [os.path.abspath(tmp_name)] + task.args
                
                res = subprocess.run(cmd, capture_output=False)
                send_msg(conn, Response('OK', exit_code=res.returncode))
                if os.path.exists(tmp_name): os.remove(tmp_name)

if __name__ == "__main__":
    my_port = int(input("Enter Worker Port: "))
    threading.Thread(target=worker_service, args=(my_port,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        send_msg(s, Request('REGISTER', worker_port=my_port))
        recv_msg(s) # Wait for ACK
        
        print("System Ready. Commands: 'submit <file> <args>' or 'exit'")
        try:
            while True:
                line = input("> ").split()
                if not line: continue
                if line[0] == 'exit':
                    send_msg(s, Request('UNREGISTER', worker_port=my_port))
                    break
                if line[0] == 'submit' and len(line) >= 2:
                    with open(line[1], "rb") as f:
                        send_msg(s, Request('SUBMIT_TASK', payload=f.read(), args=line[2:], filename=line[1]))
                    result = recv_msg(s)
                    print(f"Result: Exit Code {result.exit_code}")
        except KeyboardInterrupt:
            pass