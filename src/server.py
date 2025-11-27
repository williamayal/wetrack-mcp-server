"""MCP Server for We-Track MongoDB Pipeline Generation."""
import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from src.config.settings import settings
from src.services.mongo_service import mongo_service
from src.tools.generate_pipeline_tool import (
    GENERATE_PIPELINE_TOOL,
    handle_generate_pipeline
)
from src.tools.execute_pipeline_tool import (
    EXECUTE_PIPELINE_TOOL,
    handle_execute_pipeline
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("wetrack-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        GENERATE_PIPELINE_TOOL,
        EXECUTE_PIPELINE_TOOL
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "generate_mongodb_pipeline":
            return await handle_generate_pipeline(arguments)
        elif name == "execute_mongodb_pipeline":
            return await handle_execute_pipeline(arguments)
        else:
            return [TextContent(
                type="text",
                text=f'{{"error": "Unknown tool: {name}"}}'
            )]
    except Exception as e:
        logger.error(f"Error in tool call {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f'{{"error": "Tool execution failed: {str(e)}"}}'
        )]


async def main():
    """Main entry point for the MCP server."""
    try:
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        await mongo_service.connect()
        logger.info("MongoDB connected successfully")
        
        # Start MCP server
        logger.info("Starting MCP server...")
        async with stdio_server() as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise
    finally:
        # Disconnect from MongoDB
        if mongo_service.client:
            await mongo_service.disconnect()
            logger.info("MongoDB disconnected")


if __name__ == "__main__":
    asyncio.run(main())

