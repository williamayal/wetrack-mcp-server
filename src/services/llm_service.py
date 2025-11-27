"""Service for LLM interactions."""
from typing import List, Dict, Any, Optional
from openai import OpenAI
from src.config.settings import settings
from src.services.mongo_service import mongo_service
from src.utils.date_utils import get_current_date_info
from src.utils.json_utils import fix_isodate_in_json, fix_pipeline_dates
import logging
import json

logger = logging.getLogger(__name__)


def extract_text_from_response(response) -> str:
    """
    Extract text from Responses API output structure.
    Responses API: concatenate all text segments from response.output.
    """
    chunks = []
    
    # Try different response structures
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if item is None:
                continue
                
            # Check if item has content attribute
            if hasattr(item, 'content') and item.content is not None:
                # content might be a list
                if isinstance(item.content, list):
                    for c in item.content:
                        if c is not None and hasattr(c, 'text') and c.text:
                            chunks.append(c.text)
                # content might be a string directly
                elif isinstance(item.content, str):
                    chunks.append(item.content)
            # Check if item has text attribute directly
            elif hasattr(item, 'text') and item.text:
                chunks.append(item.text)
    
    # Fallback: check if response has text attribute directly
    if not chunks and hasattr(response, 'text') and response.text:
        chunks.append(response.text)
    
    # Fallback: check if response has content attribute
    if not chunks and hasattr(response, 'content') and response.content:
        if isinstance(response.content, str):
            chunks.append(response.content)
        elif isinstance(response.content, list):
            for c in response.content:
                if isinstance(c, str):
                    chunks.append(c)
                elif hasattr(c, 'text') and c.text:
                    chunks.append(c.text)
    
    result = "".join(chunks) if chunks else ""
    
    # Log for debugging if empty
    if not result:
        logger.warning(f"Empty response extracted. Response structure: {type(response)}, has output: {hasattr(response, 'output')}")
        if hasattr(response, 'output'):
            logger.warning(f"Output type: {type(response.output)}, value: {response.output}")
    
    return result


class LLMService:
    """Service for interacting with OpenAI LLM."""
    
    # Schema completo de FinanceEvent para el LLM
    FINANCE_EVENT_SCHEMA = """
Estructura completa del documento FinanceEvent:
{
  "id": "string",
  "plate": "string",                    // Placa del vehículo
  "command": "string",                  // Comando/operación
  "createdAt": "Date/ISODate",         // Fecha de creación
  "driverName": "string",               // Nombre del conductor
  "clientName": "string",               // Nombre del cliente
  "clientId": "string",                 // ID del cliente
  "materialName": "string | null",      // Nombre del material (opcional)
  "value": "number",                    // Valor monetario
  "source": "event" | "trip" | "toll" | "fuel" | "maintenance",  // Fuente del evento
  "type": "INCOME" | "EXPENSE",         // Tipo: INGRESO o GASTO
  "vehicle": {                          // Objeto anidado (opcional)
    "id": "string",
    "plate": "string",
    "type": "string",                   // Tipo de vehículo
    "brand": "string",
    "year": "number",
    "capacity": "number",                // Capacidad del vehículo
    "status": "string",
    "deviceId": "string | null",
    "clientId": "string | null",
    "driver": {                         // Objeto anidado dentro de vehicle (opcional)
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
"""
    
    # Ejemplos de pipelines comunes (del original we-track-agent con llaves escapadas)
    PIPELINE_EXAMPLES = """
EJEMPLOS DE PIPELINES COMUNES:

1. Filtrar INCOME y EXPENSE, sumar valores y comparar:
[
  {{"$match": {{"type": {{"$in": ["INCOME", "EXPENSE"]}}}}}},
  {{"$group": {{
    "_id": "$type",
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"_id": 1}}}}
]

2. Filtrar INCOME, agrupar por placa, sumar valores:
[
  {{"$match": {{"type": "INCOME"}}}},
  {{"$group": {{
    "_id": "$plate",
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"total": -1}}}}
]

3. Filtrar EXPENSE, agrupar por cliente, sumar valores:
[
  {{"$match": {{"type": "EXPENSE"}}}},
  {{"$group": {{
    "_id": {{"clientId": "$clientId", "clientName": "$clientName"}},
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"total": -1}}}}
]

4. Filtrar por source=fuel, agrupar por placa:
[
  {{"$match": {{"source": "fuel"}}}},
  {{"$group": {{
    "_id": "$plate",
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"total": -1}}}}
]

5. Promedio de value en todos los registros:
[
  {{"$group": {{
    "_id": null,
    "average": {{"$avg": "$value"}},
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}}
  }}}}
]

6. Agrupar por conductor, calcular promedio y desviación estándar:
[
  {{"$group": {{
    "_id": "$driverName",
    "average": {{"$avg": "$value"}},
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}},
    "stdDev": {{"$stdDevPop": "$value"}},
    "min": {{"$min": "$value"}},
    "max": {{"$max": "$value"}}
  }}}},
  {{"$sort": {{"total": -1}}}}
]

7. Filtrar por fecha (rango específico) - createdAt es DATETIME:
[
  {{"$match": {{
    "createdAt": {{
      "$gte": "2024-01-01T00:00:00Z",
      "$lte": "2024-01-31T23:59:59Z"
    }}
  }}}},
  {{"$group": {{
    "_id": "$type",
    "total": {{"$sum": "$value"}}
  }}}}
]

7b. Filtrar por "esta semana" (lunes a hoy) - USA LAS FECHAS PROPORCIONADAS:
[
  {{"$match": {{
    "type": "INCOME",
    "createdAt": {{
      "$gte": "FECHA_INICIO_SEMANA_AQUI",
      "$lte": "FECHA_ACTUAL_AQUI"
    }}
  }}}},
  {{"$group": {{
    "_id": "$plate",
    "total": {{"$sum": "$value"}}
  }}}}
]

7c. Filtrar por "hoy" - USA LA FECHA ACTUAL PROPORCIONADA:
[
  {{"$match": {{
    "createdAt": {{
      "$gte": "FECHA_ACTUAL_00:00:00Z",
      "$lte": "FECHA_ACTUAL_AQUI"
    }}
  }}}}
]

8. Agrupar por día de la semana:
[
  {{"$project": {{
    "dayOfWeek": {{"$dayOfWeek": "$createdAt"}},
    "value": 1,
    "type": 1
  }}}},
  {{"$group": {{
    "_id": "$dayOfWeek",
    "count": {{"$sum": 1}},
    "total": {{"$sum": "$value"}}
  }}}},
  {{"$sort": {{"_id": 1}}}}
]

9. Acceder a campos anidados (vehicle.type):
[
  {{"$match": {{"vehicle.type": {{"$exists": true}}}}}},
  {{"$group": {{
    "_id": "$vehicle.type",
    "total": {{"$sum": "$value"}},
    "count": {{"$sum": 1}}
  }}}},
  {{"$sort": {{"total": -1}}}}
]

10. Contar clientes únicos por placa:
[
  {{"$group": {{
    "_id": "$plate",
    "uniqueClients": {{"$addToSet": "$clientId"}},
    "clientCount": {{"$sum": 1}}
  }}}},
  {{"$project": {{
    "plate": "$_id",
    "uniqueClientCount": {{"$size": "$uniqueClients"}},
    "totalEvents": "$clientCount"
  }}}},
  {{"$sort": {{"uniqueClientCount": -1}}}}
]

11. Detectar outliers usando percentiles:
[
  {{"$group": {{
    "_id": "$plate",
    "values": {{"$push": "$value"}},
    "count": {{"$sum": 1}}
  }}}},
  {{"$project": {{
    "plate": "$_id",
    "p25": {{"$arrayElemAt": [{{"$sortArray": {{"input": "$values", "sortOrder": 1}}}}, {{"$floor": {{"$multiply": [{{"$size": "$values"}}, 0.25]}}}}]}},
    "p75": {{"$arrayElemAt": [{{"$sortArray": {{"input": "$values", "sortOrder": 1}}}}, {{"$floor": {{"$multiply": [{{"$size": "$values"}}, 0.75]}}}}]}},
    "median": {{"$arrayElemAt": [{{"$sortArray": {{"input": "$values", "sortOrder": 1}}}}, {{"$floor": {{"$divide": [{{"$size": "$values"}}, 2]}}}}]}}
  }}}}
]
"""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model_pipeline
    
    async def generate_pipeline(
        self, 
        user_query: str, 
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate MongoDB aggregation pipeline from user query.
        
        Args:
            user_query: User's natural language query
            context: Optional conversational context provided by the orchestrator
            
        Returns:
            MongoDB aggregation pipeline as a list of stages
        """
        # Get current date/time for date filters
        current_date_str, current_datetime_str, start_of_week_str = get_current_date_info()
        
        # Get sample data to help LLM understand structure
        sample_data = await mongo_service.get_view_sample(limit=3)
        sample_str = json.dumps(sample_data, indent=2, default=str) if sample_data else "No sample data available"
        
        # Build context string
        context_str = ('Contexto de conversación previa:\n' + context + '\n') if context else ''
        
        # Build comprehensive system prompt
        system_prompt = f"""Eres un experto en MongoDB y agregaciones. Tu tarea es convertir consultas en lenguaje natural sobre eventos financieros a pipelines de agregación de MongoDB.

{self.FINANCE_EVENT_SCHEMA}

REGLAS IMPORTANTES:
1. Debes responder SOLO con un JSON válido que contenga un array llamado "pipeline"
2. El pipeline debe ser un array de objetos, cada uno representando una etapa de agregación
3. Usa operadores estándar de MongoDB: $match, $group, $project, $sort, $limit, $unwind, etc.
4. Para campos anidados usa notación de punto: "vehicle.type", "vehicle.capacity"
5. Para fechas, usa operadores como $dayOfWeek, $dayOfMonth, $month, $year, $dateToString
6. Para filtros de fecha IMPORTANTE:
   - El campo createdAt en la base de datos está almacenado como DATETIME (datetime object)
   - Usa strings en formato ISO "YYYY-MM-DDTHH:mm:ssZ" o "YYYY-MM-DD HH:mm:ss+00:00"
   - El sistema convertirá automáticamente estos strings a datetime objects
   - Ejemplo correcto: {{"$match": {{"createdAt": {{"$gte": "2025-11-01T00:00:00Z", "$lte": "2025-11-30T23:59:59Z"}}}}}}
   - También puedes usar formato "YYYY-MM-DD HH:mm:ss+00:00" y se convertirá automáticamente
   - NO uses "$$NOW" ni operadores de fecha dinámicos - usa las fechas calculadas que se te proporcionan
   - Para "esta semana", usa las fechas proporcionadas en formato ISO (start_of_week_str y current_datetime_str)
   - Para "hoy", usa la fecha actual proporcionada (00:00:00Z para inicio del día)
   - Las fechas se convertirán automáticamente a datetime objects antes de ejecutar el pipeline
   - IMPORTANTE: Usa las fechas EXACTAS que se proporcionan arriba, no calcules fechas tú mismo
7. NO incluyas explicaciones, solo el JSON con el pipeline
8. El JSON debe ser válido y parseable

OPERADORES COMUNES A USAR:
- $match: Filtrar documentos
- $group: Agrupar y agregar (usar $sum, $avg, $min, $max, $count, $stdDevPop, $stdDevSamp)
- $project: Seleccionar/transformar campos
- $sort: Ordenar resultados
- $limit: Limitar cantidad de resultados
- $unwind: Descomponer arrays
- $addToSet: Agregar valores únicos a un array
- $size: Tamaño de un array
- $dateToString: Convertir fecha a string
- $dayOfWeek, $dayOfMonth, $month, $year: Extraer partes de fecha

CAMPOS PRINCIPALES:
- type: "INCOME" o "EXPENSE" (usar $match para filtrar)
- source: "event", "trip", "toll", "fuel", "maintenance"
- value: número (usar en $sum, $avg, $min, $max)
- plate: placa del vehículo
- clientId, clientName: información del cliente
- driverName: nombre del conductor
- materialName: nombre del material (puede ser null)
- createdAt: fecha (usar operadores de fecha)
- vehicle.type: tipo de vehículo (campo anidado)
- vehicle.capacity: capacidad del vehículo (campo anidado)

{self.PIPELINE_EXAMPLES}

Ejemplo de formato de respuesta:
{{
  "pipeline": [
    {{"$match": {{"type": "INCOME"}}}},
    {{"$group": {{"_id": "$plate", "total": {{"$sum": "$value"}}}}}},
    {{"$sort": {{"total": -1}}}},
    {{"$limit": 10}}
  ]
}}"""
        
        # Build user prompt with context
        user_prompt = f"""Consulta del usuario: {user_query}

FECHA ACTUAL (para usar en filtros de fecha):
- Fecha y hora actual (UTC): {current_datetime_str} (formato ISO: YYYY-MM-DDTHH:mm:ssZ)
- Fecha actual: {current_date_str} (formato: YYYY-MM-DD)
- Inicio de esta semana (lunes): {start_of_week_str} (formato ISO: YYYY-MM-DDTHH:mm:ssZ)

IMPORTANTE: Usa estas fechas como strings en formato ISO. El sistema las convertirá automáticamente a datetime objects.
Ejemplo: {{"$match": {{"createdAt": {{"$gte": "{start_of_week_str}", "$lte": "{current_datetime_str}"}}}}}}

ESTRUCTURA IDEAL ESPERADA (FinanceEvent):
{self.FINANCE_EVENT_SCHEMA}

DATOS REALES DE EJEMPLO de la colección (primeros 3 documentos):
{sample_str}

INSTRUCCIONES CRÍTICAS:
1. La estructura ideal (FinanceEvent) muestra los campos disponibles: id, plate, command, createdAt, driverName, clientName, clientId, materialName, value, source, type, vehicle
2. Los datos REALES arriba muestran la estructura ACTUAL en la base de datos
3. IMPORTANTE: Los datos ya están en el formato FinanceEvent correcto (campos en nivel raíz, no anidados en "data")
4. DEBES generar un pipeline que:
   - Use los campos directamente del nivel raíz: type, value, plate, clientId, clientName, driverName, source, createdAt, etc.
   - Para campos anidados en "vehicle" usa notación de punto: "vehicle.type", "vehicle.capacity"
   - NO busques campos en "data.value" o "data.type" - los campos ya están en el nivel raíz
   - Los campos principales están disponibles directamente: type (INCOME/EXPENSE), value (número), source, plate, etc.

ANÁLISIS REQUERIDO:
- Verifica que los datos REALES coinciden con la estructura ideal (deberían coincidir)
- Usa los campos directamente del nivel raíz como se muestran en los ejemplos
- Solo usa notación de punto para campos dentro de "vehicle" (ej: vehicle.type, vehicle.capacity)
- Genera el pipeline usando los nombres de campos que ves en los ejemplos REALES

{context_str}

Genera un pipeline de agregación de MongoDB que:
1. PRIMERO analice y adapte la estructura real de los datos (usando $project si es necesario)
2. LUEGO aplique los filtros, agrupaciones y cálculos según la consulta
3. Si la consulta menciona fechas/periodos, incluye $match con filtros de fecha
4. Si pregunta por "más", "mayor", "top", incluye $sort y posiblemente $limit
5. Si pregunta por promedios, usa $avg
6. Si pregunta por totales, usa $sum
7. Si pregunta por conteos, usa $sum: 1 en $group
8. Si pregunta por variabilidad, usa $stdDevPop o $stdDevSamp
9. Si pregunta por días de la semana/meses, usa operadores de fecha en $project antes de $group

IMPORTANTE: El pipeline debe funcionar con la estructura REAL de los datos mostrados, no con la estructura ideal.

Responde SOLO con el JSON del pipeline, sin explicaciones adicionales."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Use Responses API for GPT-5.1 models (supports reasoning.effort)
            response = self.client.responses.create(
                model=self.model,
                input=messages,
                text={"verbosity": "low"},  # Low verbosity for JSON pipeline output
                reasoning={"effort": "low"}  # Low effort for faster pipeline generation (supported in GPT-5.1)
            )
            
            # Parse response using Responses API extractor
            raw_text = extract_text_from_response(response)
            
            # Fix ISODate() calls in JSON before parsing (ISODate() is not valid JSON)
            raw_text = fix_isodate_in_json(raw_text)
            
            result = json.loads(raw_text)
            
            # Safety defaults
            if "pipeline" not in result:
                logger.warning("LLM response does not contain 'pipeline' key, returning empty pipeline")
                return []
            
            pipeline = result["pipeline"]
            logger.info(f"Generated pipeline with {len(pipeline)} stages: {json.dumps(pipeline, default=str)}")
            
            # Fix date filters in pipeline (replace $dateFromString with ISODate/datetime)
            pipeline = fix_pipeline_dates(pipeline)
            logger.info(f"Pipeline after date correction: {json.dumps(pipeline, default=str)}")
            
            return pipeline
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {raw_text if 'raw_text' in locals() else 'N/A'}")
            return []  # Return empty pipeline on JSON parse error
        except Exception as e:
            logger.error(f"Error generating pipeline: {e}", exc_info=True)
            raise


# Global instance
llm_service = LLMService()

