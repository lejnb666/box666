"""
Health check API routes for InsightWeaver AI Engine
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from src.services.redis_service import RedisService
from src.services.chroma_service import ChromaService

router = APIRouter()

@router.get("/live")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "insightweaver-ai-engine",
        "timestamp": "2024-04-02T10:00:00Z"
    }

@router.get("/ready")
async def readiness_check(
    redis_service: RedisService = Depends(lambda: RedisService()),
    chroma_service: ChromaService = Depends(lambda: ChromaService())
):
    """
    Readiness check endpoint that verifies all dependencies are available.
    """
    try:
        # Check Redis connectivity
        redis_health = await redis_service.health_check()
        
        # Check ChromaDB connectivity
        chroma_health = await chroma_service.health_check()
        
        # Determine overall status
        all_healthy = redis_health.get("status") == "healthy" and chroma_health.get("status") == "healthy"
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "service": "insightweaver-ai-engine",
            "timestamp": "2024-04-02T10:00:00Z",
            "dependencies": {
                "redis": redis_health,
                "chroma": chroma_health
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "insightweaver-ai-engine",
            "timestamp": "2024-04-02T10:00:00Z",
            "error": str(e)
        }

@router.get("/metrics")
async def get_metrics(
    redis_service: RedisService = Depends(lambda: RedisService())
):
    """
    Get system metrics and performance data.
    """
    try:
        # Get agent performance metrics
        agent_metrics = {}
        for agent_type in ["planning", "research", "analysis", "writing"]:
            metrics_key = f"metrics:agent:{agent_type}"
            metrics = await redis_service.get_hash(metrics_key)
            if metrics:
                agent_metrics[agent_type] = metrics
        
        # Get system-wide metrics
        system_metrics_key = "metrics:system"
        system_metrics = await redis_service.get_hash(system_metrics_key)
        
        return {
            "timestamp": "2024-04-02T10:00:00Z",
            "agents": agent_metrics,
            "system": system_metrics or {},
            "total_active_tasks": len(await redis_service.get_keys("task:*:metadata")),
            "total_completed_tasks": int(system_metrics.get("total_completed_tasks", 0) if system_metrics else 0)
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": "2024-04-02T10:00:00Z"
        }
