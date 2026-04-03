"""
Configuration settings for InsightWeaver AI Engine
"""

import os
from typing import List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", env="AI_ENGINE_HOST")
    PORT: int = Field(default=8000, env="AI_ENGINE_PORT")

    # API Keys
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    GOOGLE_SEARCH_API_KEY: str = Field(..., env="GOOGLE_SEARCH_API_KEY")
    GOOGLE_SEARCH_CX: str = Field(..., env="GOOGLE_SEARCH_CX")

    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: str = Field(default="", env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")

    # ChromaDB Configuration
    CHROMA_HOST: str = Field(default="localhost", env="CHROMA_HOST")
    CHROMA_PORT: int = Field(default=8000, env="CHROMA_PORT")
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")

    # Model Configuration
    DEFAULT_LLM_PROVIDER: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    DEFAULT_MODEL: str = Field(default="gpt-4", env="DEFAULT_MODEL")
    TEMPERATURE: float = Field(default=0.7, env="TEMPERATURE")
    MAX_TOKENS: int = Field(default=4000, env="MAX_TOKENS")

    # Agent Configuration
    MAX_ITERATIONS: int = Field(default=10, env="MAX_ITERATIONS")
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    AGENT_TIMEOUT: int = Field(default=300, env="AGENT_TIMEOUT")  # seconds

    # Task Configuration
    MAX_CONCURRENT_TASKS: int = Field(default=5, env="MAX_CONCURRENT_TASKS")
    TASK_TIMEOUT_MINUTES: int = Field(default=30, env="TASK_TIMEOUT_MINUTES")

    # Memory Configuration
    SHORT_TERM_MEMORY_TTL: int = Field(default=3600, env="SHORT_TERM_MEMORY_TTL")  # seconds
    LONG_TERM_MEMORY_COLLECTION: str = Field(default="research_memories", env="LONG_TERM_MEMORY_COLLECTION")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # seconds

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="ai_engine.log", env="LOG_FILE")

    # External APIs
    ARXIV_API_BASE: str = Field(
        default="https://export.arxiv.org/api/query",
        env="ARXIV_API_BASE"
    )

    # Performance Configuration
    CHUNK_SIZE: int = Field(default=1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=200, env="CHUNK_OVERLAP")
    EMBEDDING_MODEL: str = Field(default="text-embedding-ada-002", env="EMBEDDING_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()