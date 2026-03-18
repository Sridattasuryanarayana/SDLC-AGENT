"""
Configuration Management for Multi-Agent System.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv


@dataclass
class Config:
    """System configuration."""
    
    # LLM Settings
    llm_provider: str = "mock"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    local_llm_url: str = "http://localhost:11434"
    local_llm_model: str = "codellama"
    
    # WAIP Settings
    waip_api_key: Optional[str] = None
    waip_api_endpoint: str = "https://api.waip.wiprocms.com"
    waip_model: str = "gpt-4o"
    
    # Project Settings
    output_dir: str = "./output"
    debug_mode: bool = False
    max_iterations: int = 10
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            local_llm_url=os.getenv("LOCAL_LLM_URL", "http://localhost:11434"),
            local_llm_model=os.getenv("LOCAL_LLM_MODEL", "codellama"),
            waip_api_key=os.getenv("WAIP_API_KEY"),
            waip_api_endpoint=os.getenv("WAIP_API_ENDPOINT", "https://api.waip.wiprocms.com"),
            waip_model=os.getenv("WAIP_MODEL", "gpt-4o"),
            output_dir=os.getenv("OUTPUT_DIR", "./output"),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            max_iterations=int(os.getenv("MAX_ITERATIONS", "10")),
        )
    
    def get_api_key(self) -> Optional[str]:
        """Get API key for the configured provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            return self.anthropic_api_key
        elif self.llm_provider == "waip":
            return self.waip_api_key
        return None
    
    def get_model(self) -> str:
        """Get model name for the configured provider."""
        if self.llm_provider == "openai":
            return self.openai_model
        elif self.llm_provider == "anthropic":
            return self.anthropic_model
        elif self.llm_provider == "local":
            return self.local_llm_model
        elif self.llm_provider == "waip":
            return self.waip_model
        return "mock"
    
    def get_base_url(self) -> Optional[str]:
        """Get base URL for the configured provider."""
        if self.llm_provider == "local":
            return self.local_llm_url
        elif self.llm_provider == "waip":
            return self.waip_api_endpoint
        return None
