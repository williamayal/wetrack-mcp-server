"""Authentication utilities for MCP server."""
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer token security
bearer_scheme = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)) -> bool:
    """
    Verify Bearer token authentication.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        True if token is valid
        
    Raises:
        HTTPException if authentication fails
    """
    if not settings.bearer_token_enabled:
        return True  # Authentication disabled
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != settings.bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


async def verify_oauth_token(token: str) -> bool:
    """
    Verify OAuth2 token authentication.
    
    Args:
        token: OAuth2 access token
        
    Returns:
        True if token is valid
        
    Raises:
        HTTPException if authentication fails
    """
    if not settings.oauth_enabled:
        return True  # Authentication disabled
    
    if not token:
        logger.warning("OAuth token missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing OAuth token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token using oauth module
    from src.oauth import verify_access_token
    token_data = verify_access_token(token)
    
    if not token_data:
        logger.warning(f"Invalid or expired OAuth token (token prefix: {token[:10]}...)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"OAuth token verified for client_id={token_data.get('client_id')}")
    return True


async def verify_authentication(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)) -> bool:
    """
    Verify authentication using the configured method.
    Priority: OAuth > Bearer Token > MCP Token > None
    
    Args:
        credentials: HTTP Bearer credentials (optional if auth disabled)
        
    Returns:
        True if authentication is valid
        
    Raises:
        HTTPException if authentication fails
    """
    # If no authentication is enabled, allow access
    if not settings.bearer_token_enabled and not settings.oauth_enabled and not settings.mcp_token:
        return True
    
    # OAuth2 authentication (highest priority)
    if settings.oauth_enabled:
        # For OAuth, we need to extract token from credentials
        if credentials:
            token = credentials.credentials
            logger.info(f"OAuth authentication attempt with token (prefix: {token[:10]}...)")
            return await verify_oauth_token(token)
        else:
            logger.warning("OAuth enabled but no Authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Bearer token authentication
    if settings.bearer_token_enabled:
        return await verify_bearer_token(credentials)
    
    # Simple MCP token verification (static token from .env) - lowest priority
    if settings.mcp_token:
        if not credentials:
            logger.warning("MCP token required but no Authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        received_token = credentials.credentials
        configured_token = settings.mcp_token
        
        # Log both tokens for comparison
        logger.info(f"=== TOKEN COMPARISON ===")
        logger.info(f"Configured token (full): {configured_token}")
        logger.info(f"Received token (full): {received_token}")
        logger.info(f"Tokens match: {received_token == configured_token}")
        logger.info(f"Token lengths - Config: {len(configured_token)}, Received: {len(received_token)}")
        
        if received_token != configured_token:
            logger.warning(f"❌ TOKEN MISMATCH!")
            logger.warning(f"   Configured: {configured_token}")
            logger.warning(f"   Received:   {received_token}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"✅ MCP token verified for client_id={settings.mcp_client_id}")
        return True
    
    return True

