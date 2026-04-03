"""
Base Agent class for all InsightWeaver agents
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio
import time
import logging
from dataclasses import dataclass, field

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.config.settings import settings
from src.services.redis_service import RedisService


class AgentStatus(Enum):
    """Agent execution status enumeration."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class AgentContext:
    """Context object passed between agents."""
    task_id: str
    user_id: str
    research_topic: str
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AgentResponse:
    """Standardized response from agent execution."""
    success: bool
    data: Dict[str, Any]
    messages: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all InsightWeaver agents."""

    def __init__(
        self,
        name: str,
        llm: BaseLanguageModel,
        redis_service: RedisService,
        max_iterations: int = None,
        max_retries: int = None,
        model_routing_enabled: bool = True
    ):
        self.name = name
        self.llm = llm  # Default LLM
        self.redis_service = redis_service
        self.max_iterations = max_iterations or settings.MAX_ITERATIONS
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.current_status = AgentStatus.IDLE
        self.current_context: Optional[AgentContext] = None

        # Model routing configuration
        self.model_routing_enabled = model_routing_enabled
        self.available_models: Dict[str, BaseLanguageModel] = {"default": llm}
        self.current_model = "default"

    async def execute(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the agent's main logic with error handling and retries."""
        self.current_context = context
        self.current_status = AgentStatus.THINKING

        # Apply model routing if enabled
        if self.model_routing_enabled:
            await self._select_optimal_model(context, kwargs)

        # Store agent status in Redis for real-time monitoring
        await self._update_status(context.task_id, AgentStatus.THINKING)

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Agent {self.name} starting execution (attempt {attempt + 1})")

                # Execute the agent's core logic
                self.current_status = AgentStatus.EXECUTING
                await self._update_status(context.task_id, AgentStatus.EXECUTING)

                result = await self._execute_core(context, **kwargs)

                if result.success:
                    self.current_status = AgentStatus.COMPLETED
                    await self._update_status(context.task_id, AgentStatus.COMPLETED)
                    self.logger.info(f"Agent {self.name} completed successfully")
                    return result
                else:
                    self.logger.warning(f"Agent {self.name} execution failed: {result.error}")

                    if attempt < self.max_retries - 1:
                        # Implement exponential backoff
                        wait_time = 2 ** attempt
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        self.current_status = AgentStatus.FAILED
                        await self._update_status(context.task_id, AgentStatus.FAILED)
                        return result

            except Exception as e:
                self.logger.error(f"Agent {self.name} encountered error: {str(e)}")

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    self.current_status = AgentStatus.FAILED
                    await self._update_status(context.task_id, AgentStatus.FAILED)
                    return AgentResponse(
                        success=False,
                        data={},
                        error=f"Agent execution failed after {self.max_retries} attempts: {str(e)}"
                    )

        return AgentResponse(
            success=False,
            data={},
            error="Max retries exceeded"
        )

    @abstractmethod
    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Core execution logic to be implemented by subclasses."""
        pass

    async def _update_status(self, task_id: str, status: AgentStatus, metadata: Dict = None):
        """Update agent status in Redis for real-time monitoring."""
        status_data = {
            "agent": self.name,
            "status": status.value,
            "timestamp": time.time(),
            "task_id": task_id
        }

        if metadata:
            status_data["metadata"] = metadata

        if self.current_context:
            status_data["current_action"] = getattr(self, '_current_action', 'unknown')

        await self.redis_service.set_hash(
            f"task:{task_id}:agent_status:{self.name}",
            status_data,
            ttl=settings.SHORT_TERM_MEMORY_TTL
        )

        # Also publish to a stream for real-time updates
        await self.redis_service.publish("agent_status_updates", {
            "task_id": task_id,
            "agent": self.name,
            "status": status.value,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })

    async def _get_conversation_history(self, task_id: str, limit: int = 10) -> List[BaseMessage]:
        """Retrieve conversation history for the task."""
        history_key = f"task:{task_id}:conversation_history"
        messages = await self.redis_service.get_list(history_key, 0, limit - 1)

        # Convert stored messages back to LangChain message objects
        conversation_history = []
        for msg in reversed(messages):
            if msg.get("type") == "human":
                conversation_history.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("type") == "ai":
                conversation_history.append(AIMessage(content=msg.get("content", "")))

        return conversation_history

    async def _add_to_conversation_history(self, task_id: str, message_type: str, content: str):
        """Add a message to the conversation history."""
        history_key = f"task:{task_id}:conversation_history"
        message = {
            "type": message_type,
            "content": content,
            "timestamp": time.time(),
            "agent": self.name
        }

        await self.redis_service.push_to_list(history_key, message, max_length=50)

    def _create_prompt_template(self, template_name: str) -> ChatPromptTemplate:
        """Create a prompt template for the agent."""
        # This would typically load from files or a template registry
        # For now, returning a basic template structure
        return ChatPromptTemplate.from_messages([
            ("system", "You are {agent_name}, an AI agent in the InsightWeaver system. {instructions}"),
            ("human", "{input}")
        ])

    async def _validate_input(self, context: AgentContext, required_fields: List[str]) -> bool:
        """Validate that the context contains required fields."""
        for field in required_fields:
            if not hasattr(context, field) or getattr(context, field) is None:
                self.logger.error(f"Missing required field: {field}")
                return False
        return True

    async def _select_optimal_model(self, context: AgentContext, kwargs: Dict) -> None:
        """Select optimal LLM model based on task characteristics."""
        try:
            # Define task complexity indicators
            task_indicators = {
                "research_topic_complexity": self._assess_topic_complexity(context.research_topic),
                "has_research_data": bool(context.intermediate_results.get("research")),
                "agent_type": self.name,
                "task_type": kwargs.get("task_type", "general")
            }

            # Model selection logic
            selected_model = self._determine_model_for_task(task_indicators)

            if selected_model != self.current_model and selected_model in self.available_models:
                self.current_model = selected_model
                self.llm = self.available_models[selected_model]
                self.logger.info(f"Model switched to {selected_model} for {self.name}")

                # Update status with model information
                await self._update_status(context.task_id, self.current_status, {
                    "selected_model": selected_model,
                    "model_selection_reason": self._get_model_selection_reason(task_indicators)
                })

        except Exception as e:
            self.logger.warning(f"Model selection failed for {self.name}: {str(e)}")
            # Continue with current model

    def _assess_topic_complexity(self, research_topic: str) -> str:
        """Assess the complexity of the research topic."""
        topic_lower = research_topic.lower()

        # Define complexity indicators
        high_complexity_indicators = [
            "analyze", "evaluate", "assess", "compare", "synthesize",
            "multidisciplinary", "complex", "comprehensive", "in-depth"
        ]

        medium_complexity_indicators = [
            "explore", "investigate", "examine", "understand", "study"
        ]

        high_count = sum(1 for indicator in high_complexity_indicators if indicator in topic_lower)
        medium_count = sum(1 for indicator in medium_complexity_indicators if indicator in topic_lower)

        if high_count > 0 or len(research_topic.split()) > 15:
            return "high"
        elif medium_count > 0 or len(research_topic.split()) > 8:
            return "medium"
        else:
            return "low"

    def _determine_model_for_task(self, indicators: Dict) -> str:
        """Determine which model to use based on task indicators."""
        complexity = indicators.get("topic_complexity", "medium")
        agent_type = indicators.get("agent_type", "")
        has_research_data = indicators.get("has_research_data", False)
        task_type = indicators.get("task_type", "general")

        # Model selection matrix
        if "analysis" in agent_type.lower() or "writing" in agent_type.lower():
            if complexity == "high" or has_research_data:
                return "advanced"  # Use most capable model
            else:
                return "standard"
        elif "research" in agent_type.lower():
            if task_type == "web_search":
                return "fast"  # Use faster model for simple searches
            else:
                return "standard"
        elif complexity == "high":
            return "advanced"
        elif complexity == "medium":
            return "standard"
        else:
            return "fast"

    def _get_model_selection_reason(self, indicators: Dict) -> str:
        """Get human-readable reason for model selection."""
        complexity = indicators.get("topic_complexity", "medium")
        agent_type = indicators.get("agent_type", "")
        task_type = indicators.get("task_type", "general")

        reasons = []

        if complexity == "high":
            reasons.append("high topic complexity")
        elif complexity == "low":
            reasons.append("simple topic")

        if "analysis" in agent_type.lower():
            reasons.append("analysis task requiring deep reasoning")
        elif "research" in agent_type.lower() and task_type == "web_search":
            reasons.append("simple web search task")

        return ", ".join(reasons) if reasons else "default selection"

    def register_model(self, model_name: str, model: BaseLanguageModel) -> None:
        """Register an additional LLM model for routing."""
        self.available_models[model_name] = model
        self.logger.info(f"Registered model {model_name} for {self.name}")

    def _log_execution(self, action: str, details: Dict = None):
        """Log agent execution details."""
        log_data = {
            "agent": self.name,
            "action": action,
            "task_id": self.current_context.task_id if self.current_context else None,
            "timestamp": time.time(),
            "current_model": self.current_model
        }

        if details:
            log_data.update(details)

        self.logger.info(f"Agent execution: {log_data}")

    async def cleanup(self):
        """Cleanup resources when agent is done."""
        self.current_status = AgentStatus.IDLE
        self.current_context = None
        self._current_action = None


class AgentFactory:
    """Factory class for creating agent instances."""

    @staticmethod
    def create_agent(
        agent_type: str,
        llm: BaseLanguageModel,
        redis_service: RedisService,
        **kwargs
    ) -> BaseAgent:
        """Create an agent instance based on type."""
        from src.agents.planning_agent import PlanningAgent
        from src.agents.research_agent import ResearchAgent
        from src.agents.analysis_agent import AnalysisAgent
        from src.agents.writing_agent import WritingAgent

        agents = {
            "planning": PlanningAgent,
            "research": ResearchAgent,
            "analysis": AnalysisAgent,
            "writing": WritingAgent
        }

        if agent_type not in agents:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agents[agent_type](llm=llm, redis_service=redis_service, **kwargs)