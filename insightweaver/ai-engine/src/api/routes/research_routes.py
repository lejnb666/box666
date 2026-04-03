"""
Research API routes for InsightWeaver AI Engine
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
import uuid
import asyncio
import json

from src.agents.workflow_manager import WorkflowManager
from src.services.redis_service import RedisService
from src.services.chroma_service import ChromaService

router = APIRouter()

class ResearchRequest(BaseModel):
    topic: str
    description: Optional[str] = None
    output_format: str = "markdown"
    deadline_minutes: int = 30
    preferences: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class ResearchResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_completion_time: Optional[int] = None

@router.post("/start", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    workflow_manager: WorkflowManager = Depends(lambda: WorkflowManager())
):
    try:
        task_id = str(uuid.uuid4())
        await workflow_manager.initialize_task(task_id, request.dict())
        background_tasks.add_task(
            workflow_manager.execute_research_workflow,
            task_id,
            request.dict()
        )
        return ResearchResponse(
            task_id=task_id,
            status="PLANNING",
            message="Research task started successfully",
            estimated_completion_time=request.deadline_minutes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start research: {str(e)}")

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    redis_service: RedisService = Depends(lambda: RedisService())
):
    try:
        task_data = await redis_service.get_hash(f"task:{task_id}:metadata")
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        agent_statuses = {}
        for agent_name in ["planning", "research", "analysis", "writing"]:
            status_data = await redis_service.get_hash(f"task:{task_id}:agent_status:{agent_name}")
            if status_data:
                agent_statuses[agent_name] = status_data
        
        completed_agents = sum(1 for status in agent_statuses.values()
                             if status.get("status") == "completed")
        progress = (completed_agents / 4) * 100
        
        current_agent = None
        current_action = None
        for agent_name, status in agent_statuses.items():
            if status.get("status") in ["thinking", "executing"]:
                current_agent = agent_name
                current_action = status.get("current_action")
                break
        
        status = task_data.get("status", "PLANNING")
        if not status or status == "UNKNOWN":
            status = "PLANNING"
        
        return {
            "task_id": task_id,
            "status": status.upper(),
            "progress": progress,
            "current_agent": current_agent,
            "current_action": current_action
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.get("/result/{task_id}")
async def get_research_result(
    task_id: str,
    redis_service: RedisService = Depends(lambda: RedisService())
):
    try:
        task_data = await redis_service.get_hash(f"task:{task_id}:metadata")
        if not task_data or task_data.get("status") != "COMPLETED":
            raise HTTPException(status_code=400, detail="Research task not completed yet")
        
        result_key = f"task:{task_id}:results:writing"
        result = await redis_service.get_hash(result_key)
        
        if not result:
            raise HTTPException(status_code=404, detail="Research result not found")
        
        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "result": result.get("content"),
            "metadata": {
                "created_at": task_data.get("created_at"),
                "completed_at": task_data.get("completed_at"),
                "total_duration_minutes": task_data.get("total_duration"),
                "agents_used": task_data.get("agents_used", [])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get research result: {str(e)}")
