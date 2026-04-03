#!/usr/bin/env python3
"""
InsightWeaver AI Engine - Main Application Entry Point

This module serves as the entry point for the AI Engine microservice,
handling multi-agent collaboration and LLM orchestration.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config.settings import settings
from src.api.routes import research_routes, agent_routes, health_routes
from src.services.redis_service import RedisService
from src.services.chroma_service import ChromaService
from src.agents.workflow_manager import WorkflowManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    print("🚀 Starting InsightWeaver AI Engine...")

    # Initialize services
    redis_service = RedisService()
    chroma_service = ChromaService()
    workflow_manager = WorkflowManager()

    # Store services in app state
    app.state.redis_service = redis_service
    app.state.chroma_service = chroma_service
    app.state.workflow_manager = workflow_manager

    # Initialize connections
    await redis_service.connect()
    await chroma_service.initialize()

    print("✅ AI Engine services initialized successfully")

    yield

    # Shutdown
    print("🛑 Shutting down InsightWeaver AI Engine...")
    await redis_service.disconnect()
    print("👋 AI Engine shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="InsightWeaver AI Engine",
    description="Multi-Agent Automated Research and Report Generation System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research_routes.router, prefix="/api/v1/research", tags=["research"])
app.include_router(agent_routes.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(health_routes.router, prefix="/api/v1/health", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint providing basic API information."""
    return {
        "name": "InsightWeaver AI Engine",
        "version": "1.0.0",
        "status": "operational",
        "description": "Multi-Agent Research and Report Generation System",
        "documentation": "/docs" if settings.DEBUG else "Contact administrator",
        "agents_available": ["planning", "research", "analysis", "writing"]
    }


@app.get("/status")
async def status():
    """Detailed system status endpoint."""
    redis_status = await app.state.redis_service.health_check()
    chroma_status = await app.state.chroma_service.health_check()

    return {
        "system": {
            "status": "healthy",
            "uptime": "running",
            "environment": settings.ENVIRONMENT
        },
        "services": {
            "redis": redis_status,
            "chroma": chroma_status
        },
        "agents": {
            "planning": "ready",
            "research": "ready",
            "analysis": "ready",
            "writing": "ready"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )