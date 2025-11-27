"""Tool for executing MongoDB aggregation pipelines."""
from typing import Any
from mcp.types import Tool, TextContent
from src.services.mongo_service import mongo_service
from src.utils.json_utils import fix_pipeline_dates
import logging
import json

logger = logging.getLogger(__name__)


EXECUTE_PIPELINE_TOOL = Tool(
    name="execute_mongodb_pipeline",
    description="Ejecuta un pipeline de agregación MongoDB en la colección configurada. Retorna los documentos resultantes de la ejecución.",
    inputSchema={
        "type": "object",
        "properties": {
            "pipeline": {
                "type": "array",
                "description": "Pipeline de MongoDB a ejecutar (array de etapas de agregación)",
                "items": {
                    "type": "object"
                }
            }
        },
        "required": ["pipeline"]
    }
)


async def handle_execute_pipeline(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle execute_mongodb_pipeline tool call.
    
    Args:
        arguments: Tool arguments containing 'pipeline'
        
    Returns:
        List of TextContent with the execution results
    """
    pipeline = arguments.get("pipeline", [])
    
    if not pipeline:
        return [TextContent(
            type="text",
            text='{"error": "pipeline parameter is required and must be a non-empty array"}'
        )]
    
    if not isinstance(pipeline, list):
        return [TextContent(
            type="text",
            text='{"error": "pipeline must be an array"}'
        )]
    
    try:
        logger.info(f"Executing pipeline with {len(pipeline)} stages")
        
        # CRITICAL: Convert date strings to datetime objects before execution
        # This is necessary because when pipeline is serialized through MCP JSON,
        # datetime objects become strings. We need to convert them back.
        logger.info("Converting date strings to datetime objects...")
        pipeline = fix_pipeline_dates(pipeline)
        logger.info("Date conversion completed")
        
        results = await mongo_service.execute_pipeline(pipeline)
        
        result = {
            "results": results,
            "count": len(results)
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    except Exception as e:
        logger.error(f"Error executing pipeline: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f'{{"error": "Failed to execute pipeline: {str(e)}"}}'
        )]

