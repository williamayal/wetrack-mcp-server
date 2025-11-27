# Cómo Funciona la Autenticación

## 📁 Ubicación de los Archivos

### 1. **Configuración (Credenciales)**
**Archivo:** `.env` (debes crearlo)

Este archivo contiene las credenciales de autenticación:

```env
# OAuth2 Credentials (para Claude AI)
OAUTH_ENABLED=true
OAUTH_CLIENT_ID=oceantrans_client_12345
OAUTH_CLIENT_SECRET=tu_secret_muy_seguro_aqui

# Bearer Token (alternativa simple)
BEARER_TOKEN_ENABLED=false
BEARER_TOKEN=otro_token_secreto
```

**⚠️ IMPORTANTE:** Este archivo contiene secretos. **NUNCA** lo subas a Git.

### 2. **Código de Autenticación**

#### `src/config/settings.py`
- Lee las variables del archivo `.env`
- Expone `settings.oauth_client_id`, `settings.oauth_client_secret`, etc.

#### `src/auth.py`
- **`verify_bearer_token()`** - Verifica tokens Bearer simples
- **`verify_oauth_token()`** - Verifica tokens OAuth2
- **`verify_authentication()`** - Función principal que decide qué método usar

#### `src/oauth.py`
- **`_token_store`** - Diccionario en memoria que guarda los access tokens activos
- **`_authorization_codes`** - Diccionario en memoria que guarda los códigos de autorización temporales
- **`handle_authorize()`** - Maneja `/oauth/authorize` (genera códigos)
- **`handle_token()`** - Maneja `/oauth/token` (intercambia código por token)
- **`verify_access_token()`** - Verifica si un token es válido y no ha expirado

## 🔐 Flujo de Autenticación OAuth2

### Paso 1: Claude AI solicita autorización
```
Claude AI → GET /oauth/authorize?client_id=...&redirect_uri=...
```

### Paso 2: Servidor genera código
- El servidor verifica que `client_id` coincida con `OAUTH_CLIENT_ID` del `.env`
- Genera un código de autorización único
- Guarda el código en `_authorization_codes` (en memoria)
- Redirige a Claude AI con el código

### Paso 3: Claude AI intercambia código por token
```
Claude AI → POST /oauth/token
Body: {
  grant_type: "authorization_code",
  code: "codigo_generado",
  client_id: "...",
  client_secret: "..."
}
```

### Paso 4: Servidor valida y emite token
- Verifica que `client_id` y `client_secret` coincidan con `.env`
- Verifica que el código exista y no haya expirado
- Genera un access token único
- Guarda el token en `_token_store` (en memoria) con expiración de 1 hora
- Retorna el token a Claude AI

### Paso 5: Claude AI usa el token
```
Claude AI → POST /mcp
Headers: {
  Authorization: Bearer <access_token>
}
```

### Paso 6: Servidor verifica el token
- Extrae el token del header `Authorization`
- Llama a `verify_access_token()` que busca en `_token_store`
- Verifica que el token exista y no haya expirado
- Si es válido, permite el acceso

## 💾 Almacenamiento de Tokens

**Actualmente:** Los tokens se guardan **en memoria** (variables globales en `src/oauth.py`)

```python
# En src/oauth.py
_token_store: Dict[str, Dict] = {}  # Guarda access tokens
_authorization_codes: Dict[str, Dict] = {}  # Guarda códigos temporales
```

**⚠️ Limitación:** Si reinicias el servidor, todos los tokens se pierden y Claude AI tendrá que autenticarse de nuevo.

**Para producción:** Deberías usar una base de datos (Redis, MongoDB, etc.) para persistir los tokens.

## 🔑 Credenciales OAuth

Las credenciales OAuth están en **2 lugares**:

1. **En tu servidor (`.env`):**
   ```env
   OAUTH_CLIENT_ID=oceantrans_client_12345
   OAUTH_CLIENT_SECRET=tu_secret_muy_seguro_aqui
   ```

2. **En Claude AI (Settings > Connectors):**
   - OAuth Client ID: `oceantrans_client_12345` (debe coincidir)
   - OAuth Client Secret: `tu_secret_muy_seguro_aqui` (debe coincidir)

**⚠️ IMPORTANTE:** Ambos valores deben ser **exactamente iguales** en ambos lugares.

## 🔍 Verificación de Autenticación

Cada vez que Claude AI hace una request a `/mcp`:

1. El servidor extrae el header `Authorization: Bearer <token>`
2. Llama a `verify_authentication()` en `src/auth.py`
3. Si OAuth está habilitado, llama a `verify_oauth_token()`
4. `verify_oauth_token()` llama a `verify_access_token()` en `src/oauth.py`
5. `verify_access_token()` busca el token en `_token_store`
6. Si encuentra el token y no ha expirado → ✅ Permite acceso
7. Si no encuentra el token o expiró → ❌ Retorna 401 Unauthorized

## 📝 Resumen

| Componente | Ubicación | Propósito |
|------------|-----------|-----------|
| **Credenciales OAuth** | `.env` | `OAUTH_CLIENT_ID` y `OAUTH_CLIENT_SECRET` |
| **Código de verificación** | `src/auth.py` | Verifica tokens en requests |
| **Lógica OAuth2** | `src/oauth.py` | Genera tokens, valida códigos |
| **Tokens activos** | Memoria (`_token_store` en `oauth.py`) | Guarda tokens emitidos |
| **Códigos temporales** | Memoria (`_authorization_codes` en `oauth.py`) | Guarda códigos de autorización |

## 🚀 Para Mejorar (Producción)

1. **Persistir tokens en base de datos** (Redis/MongoDB)
2. **Refresh tokens** para renovar access tokens sin re-autenticación
3. **Rate limiting** por client_id
4. **Logging de autenticaciones** para auditoría
5. **Revocación de tokens** manual

