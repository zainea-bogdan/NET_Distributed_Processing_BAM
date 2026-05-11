@echo off
TITLE Distributed System Test Runner

:: 1. Start the Server in a new window
echo Starting Server...
start "Server Instance" python server.py

:: Give the server 2 seconds to bind to the port
timeout /t 2 /nobreak > nul

:: 2. Start 4 Clients with different worker ports
echo Starting 4 Clients...

:: Client 1
start "Client - Port 5001" cmd /k "echo Port: 5001 && python client.py"
:: Client 2
start "Client - Port 5002" cmd /k "echo Port: 5002 && python client.py"
:: Client 3
start "Client - Port 5003" cmd /k "echo Port: 5003 && python client.py"
:: Client 4
start "Client - Port 5004" cmd /k "echo Port: 5004 && python client.py"

echo.
echo All instances launched. 
echo Please enter the port number (5001-5004) in each client terminal.
pause