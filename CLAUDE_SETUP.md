# Configuración para Claude AI

Esta guía te ayudará a configurar el servidor MCP como un conector personalizado en Claude AI.

## Paso 1: Iniciar el Servidor HTTP

```bash
cd wetrack-mcp-server
python -m src.server_http
```

El servidor estará disponible en `http://localhost:8000` (o el puerto configurado).

## Paso 2: Configurar Autenticación

Edita el archivo `.env`:

```env
# Habilitar autenticación Bearer Token
BEARER_TOKEN_ENABLED=true
BEARER_TOKEN=tu_token_secreto_muy_seguro_aqui

# O usar OAuth2 (más complejo)
# OAUTH_ENABLED=true
# OAUTH_CLIENT_ID=tu_client_id
# OAUTH_CLIENT_SECRET=tu_client_secret
```

**Importante:** Elige un token seguro y único. Este token será usado por Claude AI para autenticarse.

## Paso 3: Exponer el Servidor con Ngrok

Ngrok ya está configurado con tu authtoken. Para iniciar el servidor con ngrok:

### Opción A: Usar el script automatizado
```bash
./start_ngrok.sh
```

### Opción B: Iniciar manualmente
```bash
# Terminal 1: Iniciar servidor MCP
python -m src.server_http

# Terminal 2: Iniciar ngrok
ngrok http 8000
```

Ngrok te dará una URL pública como: `https://xxxx-xxxx-xxxx.ngrok-free.app`

### Opción B: Desplegar en un servidor (producción)
- Despliega en un servidor con dominio propio
- Configura HTTPS con certificado SSL
- Configura el firewall para permitir conexiones en el puerto 8000

## Paso 4: Configurar OAuth2 en `.env`

Edita el archivo `.env` para habilitar OAuth2:

```env
# Habilitar OAuth2
OAUTH_ENABLED=true
OAUTH_CLIENT_ID=tu_client_id_aqui
OAUTH_CLIENT_SECRET=tu_client_secret_aqui

# Deshabilitar Bearer token si usas OAuth2
BEARER_TOKEN_ENABLED=false
```

**Importante:** 
- El `OAUTH_CLIENT_ID` y `OAUTH_CLIENT_SECRET` deben ser valores seguros y únicos
- Estos valores los usarás en Claude AI para autenticarse

## Paso 5: Configurar en Claude AI

1. Ve a **Settings** > **Connectors** en Claude AI
2. Click en **"Add custom connector"**
3. Completa el formulario:
   - **Name:** `oceantrans_mcp` (o el nombre que prefieras)
   - **Remote MCP server URL:** 
     - Con ngrok: `https://xxxx-xxxx-xxxx.ngrok-free.app/mcp`
     - Producción: `https://tu-dominio.com/mcp`
   - **OAuth Client ID:** El mismo valor que `OAUTH_CLIENT_ID` en tu `.env`
   - **OAuth Client Secret:** El mismo valor que `OAUTH_CLIENT_SECRET` en tu `.env`
4. Click en **"Add"**

Claude AI automáticamente:
- Redirigirá a `/oauth/authorize` para obtener un código de autorización
- Intercambiará el código por un token en `/oauth/token`
- Usará el token para autenticar todas las requests al servidor MCP

## Paso 6: Verificar OAuth2 Flow

Cuando Claude AI se conecte por primera vez:

1. **Autorización:** Claude AI redirigirá a `https://tu-ngrok-url.ngrok-free.app/oauth/authorize?client_id=...&redirect_uri=...&response_type=code&state=...`
2. **Código de autorización:** El servidor generará un código y lo enviará a Claude AI
3. **Intercambio de token:** Claude AI enviará el código a `/oauth/token` para obtener un access token
4. **Uso del token:** Claude AI usará el token en todas las requests al endpoint `/mcp`

**Endpoints OAuth2 disponibles:**
- `GET /oauth/authorize` - Iniciar flujo OAuth2
- `POST /oauth/token` - Intercambiar código por token
- `POST /mcp` - Endpoint MCP (requiere token OAuth2)

## Verificación

1. Verifica que el servidor esté corriendo:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verifica que la autenticación funcione:
   ```bash
   curl -H "Authorization: Bearer tu_token_secreto_muy_seguro" \
        -X POST http://localhost:8000/mcp \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   ```

3. En Claude AI, prueba hacer una consulta que use las herramientas:
   - "Genera un pipeline para obtener los ingresos totales"
   - "Ejecuta este pipeline: [tu pipeline aquí]"

## Troubleshooting

### Error: "Connection refused"
- Verifica que el servidor esté corriendo
- Verifica que el puerto sea correcto
- Verifica que el firewall permita conexiones

### Error: "Unauthorized" o "401"
- Verifica que `BEARER_TOKEN_ENABLED=true` en `.env`
- Verifica que el token en Claude AI coincida con `BEARER_TOKEN`
- Verifica que el header `Authorization: Bearer ...` esté presente

### Error: "Method not found"
- Verifica que el endpoint sea `/mcp` (no `/sse` u otro)
- Verifica que el método JSON-RPC sea correcto

### Las herramientas no aparecen en Claude AI
- Verifica que el servidor responda correctamente a `tools/list`
- Revisa los logs del servidor para ver errores
- Verifica que MongoDB esté conectado

## Seguridad

- **Nunca** compartas tu `BEARER_TOKEN` públicamente
- Usa HTTPS en producción
- Configura CORS apropiadamente para limitar orígenes permitidos
- Considera usar rate limiting para prevenir abuso
- Monitorea los logs para detectar accesos no autorizados

