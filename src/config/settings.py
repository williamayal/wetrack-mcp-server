"""Configuration settings for the application."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_uri: str
    mongodb_database: str
    mongodb_view: str
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model_pipeline: str = "gpt-5.1"  # Pipeline uses 5.1 for complex reasoning
    
    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8001
    
    # Authentication Configuration (OAuth2)
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_enabled: bool = False
    
    # Bearer Token Authentication (simpler alternative)
    bearer_token: Optional[str] = None
    bearer_token_enabled: bool = False
    
    # Static token for MCP (simple verification)
    mcp_token: Optional[str] = None
    mcp_client_id: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()

