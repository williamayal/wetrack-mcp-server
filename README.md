# We-Track MCP Server

Servidor MCP (Model Context Protocol) para generar y ejecutar pipelines de agregación de MongoDB basados en consultas en lenguaje natural sobre eventos financieros.

## Descripción

Este servidor MCP expone dos herramientas principales:

1. **`generate_mongodb_pipeline`**: Genera un pipeline de agregación MongoDB desde una consulta en lenguaje natural
2. **`execute_mongodb_pipeline`**: Ejecuta un pipeline de agregación MongoDB en la colección configurada

El servidor está diseñado para ser usado por un modelo orquestador que maneja la memoria conversacional, sesiones y visualización de datos.

## Características

- 🤖 **LLM-Powered**: Usa GPT-4.1 para generar pipelines de MongoDB
- 📊 **Context-Aware**: Incluye schema y ejemplos reales de la colección
- ⚡ **Async**: Operaciones asíncronas para mejor rendimiento
- 🔧 **Modular**: Código organizado en servicios y herramientas separados

## Requisitos

- Python 3.10+
- MongoDB Atlas o MongoDB accesible
- API Key de OpenAI

## Instalación

1. Clonar o navegar al directorio:
```bash
cd wetrack-mcp-server
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

## Configuración

Editar el archivo `.env` con tus configuraciones:

```env
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/database?retryWrites=true&w=majority
MONGODB_DATABASE=prod
MONGODB_VIEW=finance_events_view

OPENAI_API_KEY=tu_api_key_aqui
OPENAI_MODEL_PIPELINE=gpt-4.1-2025-04-14
```

## Uso

### Ejecutar el servidor MCP (modo stdio - local)

```bash
python -m src.server
```

El servidor se ejecuta sobre stdio y espera conexiones MCP locales.

### Ejecutar el servidor MCP (modo HTTP - remoto para Claude AI)

```bash
python -m src.server_http
```

El servidor se ejecuta sobre HTTP en `http://localhost:8000` (o el puerto configurado) y expone el endpoint `/mcp` para conexiones remotas.

**URL del servidor MCP remoto:**
```
http://tu-servidor:8000/mcp
```

Para producción, usa HTTPS:
```
https://tu-dominio.com/mcp
```

### Herramientas Disponibles

#### 1. `generate_mongodb_pipeline`

Genera un pipeline de agregación MongoDB desde una consulta en lenguaje natural.

**Parámetros:**
- `query` (string, requerido): Consulta en lenguaje natural sobre eventos financieros
- `context` (string, opcional): Contexto conversacional previo

**Ejemplo:**
```json
{
  "query": "¿Cuál es la proporción entre ingresos y gastos?",
  "context": "El usuario preguntó anteriormente sobre los ingresos del mes pasado"
}
```

**Retorna:**
```json
{
  "pipeline": [
    {"$match": {"type": {"$in": ["INCOME", "EXPENSE"]}}},
    {"$group": {
      "_id": "$type",
      "total": {"$sum": "$value"},
      "count": {"$sum": 1}
    }},
    {"$sort": {"_id": 1}}
  ],
  "stages_count": 3
}
```

#### 2. `execute_mongodb_pipeline`

Ejecuta un pipeline de agregación MongoDB en la colección configurada.

**Parámetros:**
- `pipeline` (array, requerido): Pipeline de MongoDB a ejecutar

**Ejemplo:**
```json
{
  "pipeline": [
    {"$match": {"type": "INCOME"}},
    {"$group": {"_id": "$plate", "total": {"$sum": "$value"}}},
    {"$sort": {"total": -1}}
  ]
}
```

**Retorna:**
```json
{
  "results": [
    {"_id": "ABC-123", "total": 15000.50},
    {"_id": "XYZ-789", "total": 12000.00}
  ],
  "count": 2
}
```

## Estructura del Proyecto

```
wetrack-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py                 # Servidor MCP principal
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuración
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── generate_pipeline_tool.py  # Herramienta: generar pipeline
│   │   └── execute_pipeline_tool.py    # Herramienta: ejecutar pipeline
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py       # Servicio LLM
│   │   └── mongo_service.py     # Servicio MongoDB
│   └── utils/
│       ├── __init__.py
│       ├── date_utils.py         # Utilidades de fecha
│       └── json_utils.py          # Utilidades JSON
├── requirements.txt
├── .env.example
└── README.md
```

## Flujo de Uso

1. El modelo orquestador llama a `generate_mongodb_pipeline` con:
   - `query`: "¿Cuál es la proporción entre ingresos y gastos?"
   - `context`: (opcional) Contexto conversacional previo

2. El MCP retorna el pipeline generado.

3. El modelo orquestador llama a `execute_mongodb_pipeline` con el pipeline.

4. El MCP retorna los datos.

5. El modelo orquestador procesa los datos y genera la respuesta final (con sus propias herramientas de visualización si las necesita).

## Schema de FinanceEvent

El servidor está configurado para trabajar con documentos que siguen este schema:

```json
{
  "id": "string",
  "plate": "string",
  "command": "string",
  "createdAt": "Date/ISODate",
  "driverName": "string",
  "clientName": "string",
  "clientId": "string",
  "materialName": "string | null",
  "value": "number",
  "source": "event" | "trip" | "toll" | "fuel" | "maintenance",
  "type": "INCOME" | "EXPENSE",
  "vehicle": {
    "id": "string",
    "plate": "string",
    "type": "string",
    "brand": "string",
    "year": "number",
    "capacity": "number",
    "status": "string",
    "deviceId": "string | null",
    "clientId": "string | null",
    "driver": {
      "id": "string",
      "nationalId": "string",
      "fullName": "string",
      "phone": "string",
      "plate": "string | null",
      "licenseExpirationDate": "Date",
      "hireDate": "Date",
      "iessRegistration": "string | null",
      "employmentStatus": "string | null",
      "telegramId": "string | null",
      "salary": "number"
    }
  }
}
```

## Configuración para Claude AI

Para usar este servidor MCP con Claude AI como conector personalizado:

1. **Iniciar el servidor HTTP:**
   ```bash
   python -m src.server_http
   ```

2. **Configurar autenticación en `.env`:**
   ```env
   BEARER_TOKEN_ENABLED=true
   BEARER_TOKEN=tu_token_secreto_muy_seguro
   ```

3. **En Claude AI Settings > Connectors:**
   - Click en "Add custom connector"
   - **Name:** `oceantrans_mcp` (o el nombre que prefieras)
   - **Remote MCP server URL:** `https://tu-dominio.com/mcp` (o `http://localhost:8000/mcp` para desarrollo)
   - **OAuth Client ID (optional):** Dejar vacío si usas Bearer token
   - **OAuth Client Secret (optional):** Dejar vacío si usas Bearer token

4. **Para usar Bearer Token:**
   - Claude AI enviará el token en el header `Authorization: Bearer tu_token_secreto_muy_seguro`
   - Asegúrate de que `BEARER_TOKEN` en tu `.env` coincida con el token que configures

## Notas

- El servidor no maneja memoria conversacional ni sesiones - eso es responsabilidad del modelo orquestador
- El servidor no genera visualizaciones (PNG/Excel) - el modelo orquestador puede usar sus propias herramientas
- Los pipelines generados incluyen corrección automática de fechas (conversión de strings ISO a objetos datetime)
- El servidor obtiene una muestra de 3 documentos de la colección para ayudar al LLM a entender la estructura real
- Para producción, usa HTTPS y configura CORS apropiadamente
- El endpoint `/mcp` implementa el protocolo MCP vía HTTP POST (JSON-RPC 2.0)

## Troubleshooting

### Error de conexión a MongoDB

1. Verificar que `MONGODB_URI` sea correcta
2. Verificar que la base de datos y view existan
3. Verificar conectividad de red

### Error con OpenAI API

1. Verificar que `OPENAI_API_KEY` esté configurada
2. Verificar que la API key sea válida y tenga créditos
3. Verificar que el modelo especificado esté disponible

### Pipeline vacío generado

1. Verificar que la consulta sea clara y específica
2. Revisar los logs para ver el prompt enviado al LLM
3. Verificar que la muestra de datos de la colección sea válida

