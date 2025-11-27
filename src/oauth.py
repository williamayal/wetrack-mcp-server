"""OAuth2 implementation for Claude AI connectors."""
import secrets
import hashlib
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request
from fastapi.responses import RedirectResponse
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# File path for persistent storage
_STORAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "oauth_tokens.json")

# Simple in-memory token store (persisted to file)
_token_store: Dict[str, Dict] = {}
_authorization_codes: Dict[str, Dict] = {}


def _load_storage():
    """Load tokens and codes from file."""
    global _token_store, _authorization_codes
    if os.path.exists(_STORAGE_FILE):
        try:
            with open(_STORAGE_FILE, 'r') as f:
                data = json.load(f)
                _token_store = data.get("tokens", {})
                _authorization_codes = data.get("codes", {})
                # Convert datetime strings back to datetime objects for codes
                for code, code_data in _authorization_codes.items():
                    if "created_at" in code_data and isinstance(code_data["created_at"], str):
                        code_data["created_at"] = datetime.fromisoformat(code_data["created_at"])
                    if "expires_at" in code_data and isinstance(code_data["expires_at"], str):
                        code_data["expires_at"] = datetime.fromisoformat(code_data["expires_at"])
                logger.info(f"Loaded {len(_token_store)} tokens and {len(_authorization_codes)} codes from storage")
        except Exception as e:
            logger.warning(f"Failed to load storage file: {e}, starting with empty store")
            _token_store = {}
            _authorization_codes = {}
    else:
        _token_store = {}
        _authorization_codes = {}


def _save_storage():
    """Save tokens and codes to file."""
    try:
        # Convert datetime objects to strings for JSON serialization
        codes_to_save = {}
        for code, code_data in _authorization_codes.items():
            codes_to_save[code] = {
                **code_data,
                "created_at": code_data["created_at"].isoformat() if isinstance(code_data.get("created_at"), datetime) else code_data.get("created_at"),
                "expires_at": code_data["expires_at"].isoformat() if isinstance(code_data.get("expires_at"), datetime) else code_data.get("expires_at")
            }
        
        data = {
            "tokens": _token_store,
            "codes": codes_to_save
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(_STORAGE_FILE), exist_ok=True)
        
        with open(_STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Saved {len(_token_store)} tokens and {len(_authorization_codes)} codes to storage")
    except Exception as e:
        logger.error(f"Failed to save storage file: {e}")


# Load storage on module import
_load_storage()


def generate_authorization_code() -> str:
    """Generate a random authorization code."""
    return secrets.token_urlsafe(32)


def generate_access_token() -> str:
    """Generate a random access token."""
    return secrets.token_urlsafe(48)


def hash_client_secret(client_secret: str) -> str:
    """Hash client secret for comparison."""
    return hashlib.sha256(client_secret.encode()).hexdigest()


def verify_client_credentials(client_id: str, client_secret: str) -> bool:
    """
    Verify OAuth2 client credentials.
    
    Args:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        
    Returns:
        True if credentials are valid
    """
    if not settings.oauth_enabled:
        return False
    
    # Simple verification - in production, use a database
    if settings.oauth_client_id and settings.oauth_client_secret:
        return (client_id == settings.oauth_client_id and 
                client_secret == settings.oauth_client_secret)
    
    return False


def create_access_token(client_id: str, scope: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an OAuth2 access token.
    
    Args:
        client_id: OAuth2 client ID
        scope: Optional scope string
        
    Returns:
        Dictionary with token information
    """
    access_token = generate_access_token()
    expires_in = 86400  # 24 hours (increased to prevent frequent re-auth)
    
    token_data = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": scope or "mcp",
        "client_id": client_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    }
    
    _token_store[access_token] = token_data
    _save_storage()  # Persist to file
    logger.info(f"Access token created for client_id={client_id} (token prefix: {access_token[:10]}..., expires in {expires_in}s)")
    
    return token_data


def verify_access_token(token: str) -> Optional[Dict]:
    """
    Verify an OAuth2 access token.
    
    Args:
        token: Access token to verify
        
    Returns:
        Token data if valid, None otherwise
    """
    logger.debug(f"Verifying token (prefix: {token[:10]}...), store has {len(_token_store)} tokens")
    
    if token not in _token_store:
        logger.warning(f"Token not found in store. Available tokens: {list(_token_store.keys())[:3] if _token_store else 'none'}")
        return None
    
    token_data = _token_store[token]
    
    # Check expiration
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.utcnow() > expires_at:
        # Token expired, remove it
        logger.info(f"Token expired at {expires_at}, removing from store")
        del _token_store[token]
        _save_storage()  # Persist removal
        return None
    
    logger.debug(f"Token valid, expires at {expires_at}")
    return token_data


async def handle_authorize(request: Request) -> RedirectResponse:
    """
    Handle OAuth2 authorization endpoint.
    
    This endpoint is called by Claude AI to initiate OAuth2 flow.
    Supports PKCE (code_challenge) for enhanced security.
    """
    if not settings.oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth2 is not enabled"
        )
    
    # Get query parameters
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    response_type = request.query_params.get("response_type")
    state = request.query_params.get("state")
    scope = request.query_params.get("scope", "mcp")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method", "plain")
    
    # Validate parameters
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required"
        )
    
    if not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri is required"
        )
    
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="response_type must be 'code'"
        )
    
    # Verify client_id
    if client_id != settings.oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client_id"
        )
    
    # Generate authorization code
    auth_code = generate_authorization_code()
    
    # Store authorization code (expires in 10 minutes)
    # Include PKCE challenge if provided
    auth_code_data = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    }
    
    # Store PKCE challenge if provided
    if code_challenge:
        auth_code_data["code_challenge"] = code_challenge
        auth_code_data["code_challenge_method"] = code_challenge_method
    
    _authorization_codes[auth_code] = auth_code_data
    _save_storage()  # Persist to file
    
    # Redirect to callback with authorization code
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"
    
    logger.info(f"OAuth2 authorization granted for client_id={client_id} (PKCE: {code_challenge_method if code_challenge else 'none'})")
    
    return RedirectResponse(url=redirect_url)


async def handle_token(request: Request) -> Dict:
    """
    Handle OAuth2 token endpoint.
    
    This endpoint exchanges authorization code for access token.
    Supports PKCE (code_verifier) for enhanced security.
    """
    if not settings.oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth2 is not enabled"
        )
    
    # Get form data
    form_data = await request.form()
    
    grant_type = form_data.get("grant_type")
    code = form_data.get("code")
    redirect_uri = form_data.get("redirect_uri")
    client_id = form_data.get("client_id")
    client_secret = form_data.get("client_secret")
    code_verifier = form_data.get("code_verifier")  # PKCE
    
    # Validate grant_type
    if grant_type != "authorization_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="grant_type must be 'authorization_code'"
        )
    
    # Validate required parameters
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="code is required"
        )
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id and client_secret are required"
        )
    
    # Verify client credentials
    if not verify_client_credentials(client_id, client_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials"
        )
    
    # Verify authorization code
    if code not in _authorization_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authorization code"
        )
    
    auth_code_data = _authorization_codes[code]
    
    # Check expiration
    if datetime.utcnow() > auth_code_data["expires_at"]:
        del _authorization_codes[code]
        _save_storage()  # Persist removal
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code expired"
        )
    
    # Verify redirect_uri matches
    if redirect_uri and redirect_uri != auth_code_data["redirect_uri"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri mismatch"
        )
    
    # Verify client_id matches
    if client_id != auth_code_data["client_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id mismatch"
        )
    
    # Verify PKCE if it was used during authorization
    if "code_challenge" in auth_code_data:
        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="code_verifier is required for PKCE"
            )
        
        challenge_method = auth_code_data.get("code_challenge_method", "plain")
        stored_challenge = auth_code_data["code_challenge"]
        
        if challenge_method == "S256":
            # Verify SHA256 hash
            import hashlib
            import base64
            verifier_hash = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            if verifier_hash != stored_challenge:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid code_verifier (PKCE verification failed)"
                )
        elif challenge_method == "plain":
            # Plain comparison
            if code_verifier != stored_challenge:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid code_verifier (PKCE verification failed)"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported code_challenge_method: {challenge_method}"
            )
    
    # Create access token
    token_data = create_access_token(
        client_id=client_id,
        scope=auth_code_data["scope"]
    )
    
    # Remove used authorization code
    del _authorization_codes[code]
    _save_storage()  # Persist removal
    
    logger.info(f"OAuth2 token issued for client_id={client_id} (PKCE: {'yes' if 'code_challenge' in auth_code_data else 'no'})")
    
    return token_data

