"""Tool for generating MongoDB aggregation pipelines."""
from typing import Any
from mcp.types import Tool, TextContent
from src.services.llm_service import llm_service
import logging

logger = logging.getLogger(__name__)


GENERATE_PIPELINE_TOOL = Tool(
    name="generate_mongodb_pipeline",
    description="Genera un pipeline de agregación MongoDB desde una consulta en lenguaje natural sobre eventos financieros. Incluye contexto del schema y ejemplos de la colección. Retorna un pipeline listo para ejecutar.",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Consulta en lenguaje natural sobre eventos financieros (ej: '¿Cuál es la proporción entre ingresos y gastos?')"
            },
            "context": {
                "type": "string",
                "description": "Contexto conversacional previo proporcionado por el orquestador (opcional)"
            }
        },
        "required": ["query"]
    }
)


async def handle_generate_pipeline(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle generate_mongodb_pipeline tool call.
    
    Args:
        arguments: Tool arguments containing 'query' and optionally 'context'
        
    Returns:
        List of TextContent with the generated pipeline
    """
    query = arguments.get("query", "")
    context = arguments.get("context")
    
    if not query:
        return [TextContent(
            type="text",
            text='{"error": "query parameter is required"}'
        )]
    
    try:
        logger.info(f"Generating pipeline for query: {query}")
        pipeline = await llm_service.generate_pipeline(user_query=query, context=context)
        
        import json
        result = {
            "pipeline": pipeline,
            "stages_count": len(pipeline)
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    except Exception as e:
        logger.error(f"Error generating pipeline: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f'{{"error": "Failed to generate pipeline: {str(e)}"}}'
        )]

