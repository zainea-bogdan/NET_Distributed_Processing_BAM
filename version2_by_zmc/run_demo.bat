@echo off
TITLE Sistem Procesare Distribuit v2
COLOR 0A

:: 1. Pornire Server
echo [+] Pornire Server Central pe portul 3333...
start "SERVER_CENTRAL" python server.py
timeout /t 2 > nul

:: 2. Pornire Workeri (Cerința 4.2)
echo [+] Pornire Worker 1 pe portul 5001...
start "WORKER_1" python client.py 5001
timeout /t 1 > nul

echo [+] Pornire Worker 2 pe portul 5002...
start "WORKER_2" python client.py 5002
timeout /t 1 > nul

:: 3. Pornire Client pentru trimitere task-uri
echo [+] Pornire Client de control...
echo.
echo ========================================================
echo INSTRUCTIUNI VIDEO:
echo 1. In fereastra 'CLIENT_CONTROL', scrie: 
echo    submit task_test.py arg1 arg2
echo 2. Observa cum Serverul trimite task-ul catre WORKER_1.
echo 3. Repeta comanda si observa cum merge catre WORKER_2 (Round Robin).
echo 4. Inchide WORKER_1 si trimite iar task-ul.
echo ========================================================
echo.

:: Deschidem al treilea client fara port (doar pentru submit)
python client.py 5003

pause