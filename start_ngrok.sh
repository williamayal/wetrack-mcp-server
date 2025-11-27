#!/bin/bash
# Script para iniciar el servidor MCP con ngrok

echo "Iniciando servidor MCP HTTP..."
python -m src.server_http &
SERVER_PID=$!

# Esperar a que el servidor inicie
sleep 3

echo "Iniciando ngrok tunnel..."
ngrok http 8000 --log=stdout &
NGROK_PID=$!

echo "Servidor MCP corriendo en http://localhost:8000"
echo "Ngrok tunnel iniciado. Presiona Ctrl+C para detener."

# Esperar por señales
trap "kill $SERVER_PID $NGROK_PID; exit" INT TERM

# Mantener el script corriendo
wait

