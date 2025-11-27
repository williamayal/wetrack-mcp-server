"""HTTP/SSE Server for We-Track MCP Server (Remote Access)."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Security, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mcp.types import Tool, TextContent
from src.config.settings import settings
from src.services.mongo_service import mongo_service
from src.auth import verify_authentication
from src.oauth import handle_authorize, handle_token
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

# HTTP Bearer security
bearer_scheme = HTTPBearer(auto_error=False)


async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        GENERATE_PIPELINE_TOOL,
        EXECUTE_PIPELINE_TOOL
    ]


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting HTTP MCP server...")
    try:
        await mongo_service.connect()
        logger.info("MongoDB connected successfully")
        logger.info(f"Server starting on {settings.server_host}:{settings.server_port}")
        logger.info(f"Authentication: Bearer={settings.bearer_token_enabled}, OAuth={settings.oauth_enabled}")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down HTTP MCP server...")
    await mongo_service.disconnect()
    logger.info("MongoDB disconnected")


# Create FastAPI app
app = FastAPI(
    title="We-Track MCP Server",
    description="MCP Server for MongoDB Pipeline Generation - Remote Access via HTTP/SSE",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "We-Track MCP Server",
        "version": "1.0.0",
        "mcp_endpoint": "/sse",
        "health": "/health",
        "authentication": {
            "bearer_enabled": settings.bearer_token_enabled,
            "oauth_enabled": settings.oauth_enabled
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "wetrack-mcp-server",
        "mongodb_connected": mongo_service.client is not None
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server(request: Request):
    """
    OAuth2 Authorization Server Metadata (RFC 8414).
    Claude AI uses this for OAuth discovery.
    """
    # Get base URL from request
    scheme = request.url.scheme
    host = request.headers.get("host", request.url.hostname)
    base_url = f"{scheme}://{host}"
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": ["mcp", "claudeai"]
    }


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource(request: Request):
    """
    OAuth2 Protected Resource Metadata.
    """
    # Get base URL from request
    scheme = request.url.scheme
    host = request.headers.get("host", request.url.hostname)
    base_url = f"{scheme}://{host}"
    
    return {
        "resource": f"{base_url}/mcp",
        "authorization_servers": [base_url],
        "scopes_supported": ["mcp", "claudeai"]
    }


@app.get("/oauth/authorize")
async def oauth_authorize(request: Request):
    """
    OAuth2 authorization endpoint.
    Claude AI will redirect here to initiate OAuth2 flow.
    """
    return await handle_authorize(request)


@app.get("/authorize")
async def authorize(request: Request):
    """
    OAuth2 authorization endpoint (alternative path for Claude AI).
    Claude AI uses /authorize instead of /oauth/authorize.
    """
    return await handle_authorize(request)


@app.post("/oauth/token")
async def oauth_token(request: Request):
    """
    OAuth2 token endpoint.
    Claude AI will exchange authorization code for access token here.
    """
    return await handle_token(request)


@app.post("/token")
async def token(request: Request):
    """
    OAuth2 token endpoint (alternative path for Claude AI).
    Claude AI uses /token instead of /oauth/token.
    """
    return await handle_token(request)


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    """
    MCP protocol endpoint for Claude AI.
    Handles MCP protocol messages via HTTP POST.
    """
    # Authentication disabled for now
    # await verify_authentication(credentials)
    
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        logger.info(f"MCP request: method={method}, id={request_id}")
        
        if method == "initialize":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "wetrack-mcp-server",
                        "version": "1.0.0"
                    }
                }
            })
        
        elif method == "tools/list":
            tools = await list_tools()
            tools_dict = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                tools_dict.append(tool_dict)
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools_dict
                }
            })
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: tool name is required"
                    }
                }, status_code=400)
            
            result = await call_tool(tool_name, arguments)
            
            # Convert TextContent to dict
            content_list = []
            for content in result:
                if isinstance(content, TextContent):
                    content_list.append({
                        "type": content.type,
                        "text": content.text
                    })
                else:
                    content_list.append(str(content))
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": content_list
                }
            })
        
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }, status_code=404)
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}", exc_info=True)
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id if 'request_id' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }, status_code=500)


def main():
    """Main entry point for the HTTP MCP server."""
    import uvicorn
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level="info"
    )


if __name__ == "__main__":
    main()

