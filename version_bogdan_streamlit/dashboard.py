import streamlit as st
import socket
import subprocess
import os
import sys
import time
import pandas as pd
from shared import primeste_mesaj, trimite_mesaj

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_ADDR = ('127.0.0.1', 3333)

st.set_page_config(page_title="Cluster Monitor", layout="wide", page_icon="📡")


# --- Helpers ---

def server_activ():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(SERVER_ADDR)
            return True
    except:
        return False


def interogheaza_server(comanda):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(SERVER_ADDR)
            trimite_mesaj(s, {'command': comanda})
            return primeste_mesaj(s)
    except:
        return None


def trimite_task(payload, filename, args, sender_port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(30)
            s.connect(SERVER_ADDR)
            trimite_mesaj(s, {
                'command': 'SUBMIT_TASK',
                'payload': payload,
                'filename': filename,
                'args': args,
                'sender_port': sender_port
            })
            return primeste_mesaj(s)
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def porneste_server():
    return subprocess.Popen(
        [sys.executable, 'server.py'],
        cwd=SCRIPT_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )


def porneste_worker(port):
    return subprocess.Popen(
        [sys.executable, 'worker.py', str(port)],
        cwd=SCRIPT_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )


def desregistreaza_worker(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(SERVER_ADDR)
            trimite_mesaj(s, {'command': 'UNREGISTER', 'worker_port': port})
            primeste_mesaj(s)
    except:
        pass


# --- Session state init ---
if 'workeri_porniti' not in st.session_state:
    st.session_state.workeri_porniti = {}  # {port: Popen}
if 'server_proc' not in st.session_state:
    st.session_state.server_proc = None
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

# Clean up dead worker processes so sidebar stays accurate
dead_ports = [p for p, proc in st.session_state.workeri_porniti.items() if proc.poll() is not None]
for p in dead_ports:
    st.session_state.workeri_porniti.pop(p)


# --- Sidebar ---
with st.sidebar:
    st.header("Administrare Cluster")

    st.subheader("Server Central")
    activ = server_activ()
    if activ:
        st.success("Server activ pe portul 3333")
        proc_server = st.session_state.server_proc
        if proc_server and proc_server.poll() is None:
            if st.button("Oprire Server", width="stretch", type="secondary"):
                proc_server.terminate()
                st.session_state.server_proc = None
                time.sleep(0.3)
                st.rerun()
    else:
        st.error("Server oprit")
        if st.button("Pornire Server", width="stretch"):
            proc = porneste_server()
            st.session_state.server_proc = proc
            time.sleep(0.8)
            st.rerun()

    st.divider()

    st.subheader("Workers")
    port_nou = st.number_input("Port", min_value=5001, max_value=6000, value=5001, step=1)
    if st.button("Adauga Worker", width="stretch", disabled=not activ):
        if port_nou not in st.session_state.workeri_porniti:
            proc = porneste_worker(port_nou)
            st.session_state.workeri_porniti[port_nou] = proc
        time.sleep(0.8)
        st.rerun()

    if st.session_state.workeri_porniti:
        st.divider()
        st.caption("Porniti in aceasta sesiune:")
        for p in st.session_state.workeri_porniti:
            st.code(f"Worker :{p}")


# --- Main area ---
st.title("Sistem Distribuit de Procesare")

if not activ:
    st.warning("Porneste serverul din bara laterala pentru a incepe.")
    st.stop()

status = interogheaza_server('GET_STATUS')
workeri = status.get('workers', []) if status else []

# --- Worker cards ---
st.subheader("Noduri Active")

if not workeri:
    st.info("Niciun worker activ. Adauga unul din bara laterala.")
else:
    cols = st.columns(len(workeri))
    for idx, (ip, port) in enumerate(workeri):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"### Worker :{port}")
                st.caption(f"{ip}:{port}")

                fisier = st.file_uploader(
                    "Alege task (.py)",
                    type=['py'],
                    key=f"upload_{port}"
                )
                argumente = st.text_input(
                    "Argumente (optionale)",
                    key=f"args_{port}",
                    placeholder="ex: arg1 arg2"
                )

                if st.button(f"Submit din Worker {port}", key=f"btn_{port}", width="stretch"):
                    if fisier:
                        args_lista = argumente.split() if argumente.strip() else []
                        with st.spinner("Se executa task-ul in cluster..."):
                            rezultat = trimite_task(
                                fisier.getvalue(),
                                fisier.name,
                                args_lista,
                                sender_port=port
                            )
                        st.session_state.last_result = {
                            'status': rezultat.get('status'),
                            'sender': port,
                            'executor': rezultat.get('executor_port'),
                            'task': fisier.name,
                            'exit_code': rezultat.get('exit_code'),
                            'message': rezultat.get('message')
                        }
                        st.rerun()
                    else:
                        st.warning("Alege un fisier .py mai intai.")

                if st.button(f"Stop Worker {port}", key=f"stop_{port}", width="stretch", type="secondary"):
                    desregistreaza_worker(port)
                    proc = st.session_state.workeri_porniti.pop(port, None)
                    if proc:
                        proc.terminate()
                    st.rerun()

# --- Last result banner ---
if st.session_state.last_result:
    r = st.session_state.last_result
    st.divider()
    if r['status'] == 'OK':
        st.success(
            f"Ultimul task: `{r['task']}` | "
            f"Trimis de Worker **:{r['sender']}** → "
            f"Executat de Worker **:{r['executor']}** | "
            f"Exit Code: `{r['exit_code']}`"
        )
    else:
        st.error(f"Eroare: {r.get('message', 'Necunoscuta')}")

st.divider()

# --- History and Logs ---
col_istoric, col_log = st.columns([3, 2])

with col_istoric:
    st.subheader("Istoric Task-uri")
    date_istoric = interogheaza_server('GET_HISTORY')
    if date_istoric and date_istoric.get('history'):
        df = pd.DataFrame(date_istoric['history'])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write("Niciun task executat inca.")

with col_log:
    st.subheader("Logs Server")
    date_log = interogheaza_server('GET_LOGS')
    if date_log and date_log.get('logs'):
        st.text_area(
            "",
            value="\n".join(date_log['logs']),
            height=300,
            disabled=True,
            label_visibility="collapsed"
        )
    else:
        st.write("Niciun log disponibil.")