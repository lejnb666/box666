"""
Agent API routes for InsightWeaver AI Engine
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel

from src.agents.base_agent import AgentFactory
from src.services.redis_service import RedisService
from src.services.chroma_service import ChromaService

router = APIRouter()

class AgentExecuteRequest(BaseModel):
    agent_type: str
    task_id: str
    input_data: Dict[str, Any]
    user_id: Optional[str] = None

class AgentExecuteResponse(BaseModel):
    success: bool
    result: Dict[str, Any]
    agent_type: str
    execution_time: float

@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    request: AgentExecuteRequest,
    redis_service: RedisService = Depends(lambda: RedisService())
):
    """
    Execute a specific agent directly.
    """
    try:
        # Create agent instance
        agent = AgentFactory.create_agent(
            agent_type=request.agent_type,
            llm=None,  # This would need proper LLM initialization
            redis_service=redis_service
        )
        
        # Execute agent
        from src.agents.base_agent import AgentContext
        context = AgentContext(
            task_id=request.task_id,
            user_id=request.user_id or "anonymous",
            research_topic=request.input_data.get("topic", ""),
            intermediate_results=request.input_data
        )
        
        result = await agent.execute(context)
        
        return AgentExecuteResponse(
            success=result.success,
            result=result.data,
            agent_type=request.agent_type,
            execution_time=result.metadata.get("execution_time", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

@router.get("/status/{agent_type}")
async def get_agent_status(
    agent_type: str,
    redis_service: RedisService = Depends(lambda: RedisService())
):
    """
    Get status of a specific agent type.
    """
    try:
        # Get agent status from Redis
        status_key = f"agent:status:{agent_type}"
        status_data = await redis_service.get_hash(status_key)
        
        if not status_data:
            return {
                "agent_type": agent_type,
                "status": "idle",
                "active_tasks": 0,
                "total_tasks_completed": 0,
                "average_execution_time": 0.0
            }
        
        return {
            "agent_type": agent_type,
            "status": status_data.get("status", "unknown"),
            "active_tasks": int(status_data.get("active_tasks", 0)),
            "total_tasks_completed": int(status_data.get("total_tasks_completed", 0)),
            "average_execution_time": float(status_data.get("average_execution_time", 0.0)),
            "last_activity": status_data.get("last_activity")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")

@router.get("/list")
async def list_available_agents():
    """
    List all available agent types.
    """
    return {
        "agents": [
            {
                "type": "planning",
                "name": "Planning Agent",
                "description": "Breaks down complex research tasks into manageable sub-tasks",
                "capabilities": ["task_decomposition", "workflow_planning", "resource_allocation"]
            },
            {
                "type": "research",
                "name": "Research Agent",
                "description": "Performs autonomous information gathering from various sources",
                "capabilities": ["web_search", "academic_search", "data_validation", "source_verification"]
            },
            {
                "type": "analysis",
                "name": "Analysis Agent",
                "description": "Processes and validates collected information",
                "capabilities": ["data_processing", "cross_validation", "pattern_recognition", "insight_extraction"]
            },
            {
                "type": "writing",
                "name": "Writing Agent",
                "description": "Generates structured reports and documentation",
                "capabilities": ["report_generation", "content_synthesis", "formatting", "citation_management"]
            }
        ]
    }
