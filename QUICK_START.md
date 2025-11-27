# Inicio Rápido - We-Track MCP Server con OAuth2

## Configuración Rápida

### 1. Configurar `.env`

```bash
cd wetrack-mcp-server
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
# MongoDB
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/database
MONGODB_DATABASE=prod
MONGODB_VIEW=finance_events_view

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL_PIPELINE=gpt-4.1-2025-04-14

# OAuth2 (para Claude AI)
OAUTH_ENABLED=true
OAUTH_CLIENT_ID=oceantrans_client_12345
OAUTH_CLIENT_SECRET=tu_secret_muy_seguro_aqui

# Deshabilitar Bearer token si usas OAuth2
BEARER_TOKEN_ENABLED=false
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Iniciar Servidor con Ngrok

```bash
./start_ngrok.sh
```

O manualmente:

```bash
# Terminal 1
python -m src.server_http

# Terminal 2
ngrok http 8000
```

### 4. Obtener URL de Ngrok

Ngrok mostrará una URL como:
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:8000
```

Copia esta URL.

### 5. Configurar en Claude AI

1. Ve a **Settings** > **Connectors** > **Add custom connector**
2. Completa:
   - **Name:** `oceantrans_mcp`
   - **Remote MCP server URL:** `https://xxxx-xxxx-xxxx.ngrok-free.app/mcp`
   - **OAuth Client ID:** `oceantrans_client_12345` (el mismo que en `.env`)
   - **OAuth Client Secret:** `tu_secret_muy_seguro_aqui` (el mismo que en `.env`)
3. Click **Add**

### 6. Probar

En Claude AI, prueba:
- "Genera un pipeline MongoDB para obtener los ingresos totales"
- "Ejecuta este pipeline: [tu pipeline aquí]"

## Verificación

### Verificar que el servidor funciona:

```bash
curl http://localhost:8000/health
```

### Verificar endpoints OAuth2:

```bash
# Autorización (debe redirigir)
curl "http://localhost:8000/oauth/authorize?client_id=oceantrans_client_12345&redirect_uri=http://localhost&response_type=code"
```

## Troubleshooting

### Error: "OAuth2 is not enabled"
- Verifica que `OAUTH_ENABLED=true` en `.env`
- Reinicia el servidor

### Error: "Invalid client_id"
- Verifica que `OAUTH_CLIENT_ID` en `.env` coincida con el de Claude AI

### Error: "Invalid client credentials"
- Verifica que `OAUTH_CLIENT_SECRET` en `.env` coincida con el de Claude AI

### Ngrok no funciona
- Verifica que ngrok esté instalado: `ngrok version`
- Verifica que el authtoken esté configurado: `ngrok config check`

