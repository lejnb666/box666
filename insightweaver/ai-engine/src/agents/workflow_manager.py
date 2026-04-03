"""
Multi-Agent Workflow Manager - Coordinates the collaboration between different agents
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from langgraph import StateGraph, END
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse, AgentFactory
from src.agents.planning_agent import PlanningAgent
from src.agents.research_agent import ResearchAgent
from src.agents.analysis_agent import AnalysisAgent
from src.agents.writing_agent import WritingAgent
from src.agents.fact_check_agent import FactCheckAgent
from src.services.redis_service import RedisService
from src.services.chroma_service import ChromaService
from src.config.settings import settings


class WorkflowStatus(Enum):
    """Workflow execution status enumeration."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class WorkflowState:
    """State object for the multi-agent workflow."""
    task_id: str
    user_id: str
    research_topic: str
    current_agent: str = ""
    agent_statuses: Dict[str, str] = field(default_factory=dict)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: WorkflowStatus = WorkflowStatus.CREATED


class WorkflowManager:
    """Manages the multi-agent workflow execution using LangGraph."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service: RedisService,
        chroma_service: ChromaService
    ):
        self.llm = llm
        self.redis_service = redis_service
        self.chroma_service = chroma_service
        self.logger = logging.getLogger(__name__)

        # Initialize agents
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()

        # Create workflow graph
        self.workflow_graph = self._create_workflow_graph()

        # Active workflows tracking
        self.active_workflows: Dict[str, WorkflowState] = {}

    def _initialize_agents(self):
        """Initialize all available agents."""
        agent_configs = [
            ("planning", PlanningAgent),
            ("research", ResearchAgent),
            ("analysis", AnalysisAgent),
            ("writing", WritingAgent),
            ("fact_check", FactCheckAgent)
        ]

        for agent_name, agent_class in agent_configs:
            try:
                agent = agent_class(
                    llm=self.llm,
                    redis_service=self.redis_service,
                    max_iterations=settings.MAX_ITERATIONS,
                    max_retries=settings.MAX_RETRIES
                )
                self.agents[agent_name] = agent
                self.logger.info(f"Initialized {agent_name} agent")

            except Exception as e:
                self.logger.error(f"Failed to initialize {agent_name} agent: {str(e)}")

    def _create_workflow_graph(self) -> StateGraph:
        """Create the LangGraph workflow for multi-agent collaboration."""

        # Define the workflow graph
        workflow = StateGraph(WorkflowState)

        # Add nodes for each agent
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("research", self._research_node)
        workflow.add_node("analysis", self._analysis_node)
        workflow.add_node("fact_check", self._fact_check_node)
        workflow.add_node("writing", self._writing_node)
        workflow.add_node("coordinator", self._coordinator_node)

        # Define the workflow edges
        workflow.add_edge("planning", "research")
        workflow.add_edge("research", "analysis")
        workflow.add_edge("analysis", "fact_check")
        workflow.add_edge("fact_check", "writing")
        workflow.add_edge("writing", "coordinator")

        # Add conditional edges for error handling and re-planning
        workflow.add_conditional_edges(
            "coordinator",
            self._should_continue,
            {
                "continue": "planning",
                "end": END,
                "research": "research",
                "analysis": "analysis",
                "writing": "writing"
            }
        )

        # Set entry point
        workflow.set_entry_point("planning")

        return workflow.compile()

    async def execute_workflow(
        self,
        task_id: str,
        user_id: str,
        research_topic: str,
        user_requirements: Dict[str, Any]
    ) -> str:
        """Execute the complete multi-agent workflow."""

        self.logger.info(f"Starting workflow execution for task {task_id}")

        # Create initial workflow state
        initial_state = WorkflowState(
            task_id=task_id,
            user_id=user_id,
            research_topic=research_topic,
            agent_statuses={agent: "waiting" for agent in self.agents.keys()},
            intermediate_results={},
            status=WorkflowStatus.RUNNING
        )

        # Store user requirements in state
        initial_state.intermediate_results["user_requirements"] = user_requirements

        # Add to active workflows
        self.active_workflows[task_id] = initial_state

        try:
            # Execute the workflow
            final_state = await self.workflow_graph.ainvoke(initial_state)

            # Update workflow status
            if final_state.final_output:
                final_state.status = WorkflowStatus.COMPLETED
                await self._store_final_result(task_id, final_state.final_output)
            else:
                final_state.status = WorkflowStatus.FAILED
                final_state.error_message = "No final output generated"

            # Update active workflows
            self.active_workflows[task_id] = final_state

            # Store workflow result in Redis
            await self._update_workflow_status(task_id, final_state)

            self.logger.info(f"Workflow completed for task {task_id}")
            return final_state.final_output or ""

        except Exception as e:
            self.logger.error(f"Workflow execution failed for task {task_id}: {str(e)}")

            # Update state with error
            initial_state.status = WorkflowStatus.FAILED
            initial_state.error_message = str(e)
            self.active_workflows[task_id] = initial_state

            # Store error in Redis
            await self._update_workflow_status(task_id, initial_state)

            raise

    async def _planning_node(self, state: WorkflowState) -> WorkflowState:
        """Planning agent node in the workflow."""

        self.logger.info(f"Executing planning node for task {state.task_id}")

        state.current_agent = "planning"
        state.agent_statuses["planning"] = "executing"
        state.updated_at = time.time()

        # Create agent context
        context = AgentContext(
            task_id=state.task_id,
            user_id=state.user_id,
            research_topic=state.research_topic,
            intermediate_results=state.intermediate_results,
            metadata=state.intermediate_results.get("user_requirements", {})
        )

        try:
            # Execute planning agent
            planning_agent = self.agents["planning"]
            result = await planning_agent.execute(context)

            if result.success:
                state.agent_statuses["planning"] = "completed"
                state.intermediate_results.update(result.data)
                state.updated_at = time.time()

                # Store planning results in long-term memory
                await self._store_in_long_term_memory(
                    state.task_id,
                    "planning_results",
                    result.data
                )

            else:
                state.agent_statuses["planning"] = "failed"
                state.error_message = result.error
                state.status = WorkflowStatus.FAILED

        except Exception as e:
            state.agent_statuses["planning"] = "failed"
            state.error_message = f"Planning node failed: {str(e)}"
            state.status = WorkflowStatus.FAILED

        return state

    async def _research_node(self, state: WorkflowState) -> WorkflowState:
        """Research agent node in the workflow."""

        self.logger.info(f"Executing research node for task {state.task_id}")

        state.current_agent = "research"
        state.agent_statuses["research"] = "executing"
        state.updated_at = time.time()

        # Create agent context
        context = AgentContext(
            task_id=state.task_id,
            user_id=state.user_id,
            research_topic=state.research_topic,
            intermediate_results=state.intermediate_results,
            metadata=state.intermediate_results.get("user_requirements", {})
        )

        try:
            # Execute research agent
            research_agent = self.agents["research"]
            result = await research_agent.execute(context)

            if result.success:
                state.agent_statuses["research"] = "completed"
                state.intermediate_results.update(result.data)
                state.updated_at = time.time()

                # Store research results in long-term memory
                await self._store_in_long_term_memory(
                    state.task_id,
                    "research_results",
                    result.data
                )

            else:
                state.agent_statuses["research"] = "failed"
                state.error_message = result.error
                state.status = WorkflowStatus.FAILED

        except Exception as e:
            state.agent_statuses["research"] = "failed"
            state.error_message = f"Research node failed: {str(e)}"
            state.status = WorkflowStatus.FAILED

        return state

    async def _analysis_node(self, state: WorkflowState) -> WorkflowState:
        """Analysis agent node in the workflow."""

        self.logger.info(f"Executing analysis node for task {state.task_id}")

        state.current_agent = "analysis"
        state.agent_statuses["analysis"] = "executing"
        state.updated_at = time.time()

        # Create agent context
        context = AgentContext(
            task_id=state.task_id,
            user_id=state.user_id,
            research_topic=state.research_topic,
            intermediate_results=state.intermediate_results,
            metadata=state.intermediate_results.get("user_requirements", {})
        )

        try:
            # Execute analysis agent
            analysis_agent = self.agents["analysis"]
            result = await analysis_agent.execute(context)

            if result.success:
                state.agent_statuses["analysis"] = "completed"
                state.intermediate_results.update(result.data)
                state.updated_at = time.time()

                # Store analysis results in long-term memory
                await self._store_in_long_term_memory(
                    state.task_id,
                    "analysis_results",
                    result.data
                )

            else:
                state.agent_statuses["analysis"] = "failed"
                state.error_message = result.error
                state.status = WorkflowStatus.FAILED

        except Exception as e:
            state.agent_statuses["analysis"] = "failed"
            state.error_message = f"Analysis node failed: {str(e)}"
            state.status = WorkflowStatus.FAILED

        return state

    async def _fact_check_node(self, state: WorkflowState) -> WorkflowState:
        """Fact Check agent node in the workflow."""

        self.logger.info(f"Executing fact check node for task {state.task_id}")

        state.current_agent = "fact_check"
        state.agent_statuses["fact_check"] = "executing"
        state.updated_at = time.time()

        # Create agent context
        context = AgentContext(
            task_id=state.task_id,
            user_id=state.user_id,
            research_topic=state.research_topic,
            intermediate_results=state.intermediate_results,
            metadata=state.intermediate_results.get("user_requirements", {})
        )

        try:
            # Execute fact check agent
            fact_check_agent = self.agents["fact_check"]
            result = await fact_check_agent.execute(context)

            if result.success:
                state.agent_statuses["fact_check"] = "completed"
                state.intermediate_results.update(result.data)
                state.updated_at = time.time()

                # Store fact check results in long-term memory
                await self._store_in_long_term_memory(
                    state.task_id,
                    "fact_check_results",
                    result.data
                )

            else:
                state.agent_statuses["fact_check"] = "failed"
                state.error_message = result.error
                state.status = WorkflowStatus.FAILED

        except Exception as e:
            state.agent_statuses["fact_check"] = "failed"
            state.error_message = f"Fact check node failed: {str(e)}"
            state.status = WorkflowStatus.FAILED

        return state

    async def _writing_node(self, state: WorkflowState) -> WorkflowState:
        """Writing agent node in the workflow."""

        self.logger.info(f"Executing writing node for task {state.task_id}")

        state.current_agent = "writing"
        state.agent_statuses["writing"] = "executing"
        state.updated_at = time.time()

        # Create agent context
        context = AgentContext(
            task_id=state.task_id,
            user_id=state.user_id,
            research_topic=state.research_topic,
            intermediate_results=state.intermediate_results,
            metadata=state.intermediate_results.get("user_requirements", {})
        )

        try:
            # Execute writing agent
            writing_agent = self.agents["writing"]
            result = await writing_agent.execute(context)

            if result.success:
                state.agent_statuses["writing"] = "completed"
                state.final_output = result.data.get("final_report", "")
                state.updated_at = time.time()

                # Store final report in long-term memory
                await self._store_in_long_term_memory(
                    state.task_id,
                    "final_report",
                    {"report": state.final_output}
                )

            else:
                state.agent_statuses["writing"] = "failed"
                state.error_message = result.error
                state.status = WorkflowStatus.FAILED

        except Exception as e:
            state.agent_statuses["writing"] = "failed"
            state.error_message = f"Writing node failed: {str(e)}"
            state.status = WorkflowStatus.FAILED

        return state

    async def _coordinator_node(self, state: WorkflowState) -> WorkflowState:
        """Coordinator node that manages workflow transitions, quality checks, and dynamic replanning."""

        self.logger.info(f"Executing coordinator node for task {state.task_id}")

        state.current_agent = "coordinator"
        state.updated_at = time.time()

        # Evaluate current progress vs. original goals
        evaluation_result = await self._evaluate_progress(state)

        # Perform quality checks
        quality_check_result = await self._perform_quality_checks(state)

        # Dynamic replanning logic
        if quality_check_result["passed"]:
            # All quality checks passed, workflow can complete
            state.status = WorkflowStatus.COMPLETED
            self.logger.info(f"All quality checks passed for task {state.task_id}")
        else:
            # Determine if we need dynamic replanning or simple rework
            if evaluation_result["gap_analysis"]["significant_gap"]:
                # Significant gap detected, trigger dynamic replanning
                replanning_result = await self._dynamic_replanning(state, evaluation_result)
                if replanning_result["success"]:
                    # Update intermediate_results with new plan
                    state.intermediate_results["planning"] = replanning_result["updated_plan"]
                    state.agent_statuses["planning"] = "waiting"  # Trigger re-planning
                    next_action = "planning"
                    self.logger.info(f"Dynamic replanning triggered for task {state.task_id}")
                else:
                    # Replanning failed, fall back to quality check routing
                    next_action = quality_check_result["next_action"]
                    self.logger.warning(f"Dynamic replanning failed, using quality check routing for task {state.task_id}")
            else:
                # Use quality check results for routing
                next_action = quality_check_result["next_action"]
                self.logger.info(f"Quality check routing used for task {state.task_id}")

            # Reset the agent that needs to rework
            if next_action in state.agent_statuses:
                state.agent_statuses[next_action] = "waiting"

        return state

    async def _evaluate_progress(self, state: WorkflowState) -> Dict[str, Any]:
        """Evaluate current progress against original research goals using LLM."""
        try:
            # Prepare evaluation prompt
            evaluation_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a research evaluation expert. Compare the current intermediate results with the original research objective to identify gaps and assess progress.

Your evaluation should:
1. Identify key gaps between current results and original goals
2. Assess completeness of information gathered
3. Determine if significant replanning is needed
4. Provide specific recommendations for improvement

Provide your evaluation in JSON format:
{
    "goal_alignment_score": 0.0-1.0,
    "information_gaps": ["gap1", "gap2"],
    "missing_requirements": ["req1", "req2"],
    "significant_gap": true/false,
    "recommendations": ["recommendation1", "recommendation2"]
}
"""),
                ("human", "Original Research Objective: {research_topic}\n\nUser Requirements: {user_requirements}\n\nCurrent Intermediate Results: {intermediate_results}")
            ])

            # Get user requirements and current results
            user_requirements = state.intermediate_results.get("user_requirements", {})
            intermediate_results_str = json.dumps(state.intermediate_results, indent=2, default=str)

            # Invoke LLM for evaluation
            chain = evaluation_prompt | self.llm | JsonOutputParser()
            evaluation = await chain.ainvoke({
                "research_topic": state.research_topic,
                "user_requirements": json.dumps(user_requirements, indent=2),
                "intermediate_results": intermediate_results_str
            })

            return {
                "success": True,
                "gap_analysis": evaluation,
                "evaluation_timestamp": time.time()
            }

        except Exception as e:
            self.logger.error(f"Failed to evaluate progress for task {state.task_id}: {str(e)}")
            return {
                "success": False,
                "gap_analysis": {
                    "goal_alignment_score": 0.5,
                    "information_gaps": ["Evaluation failed"],
                    "missing_requirements": [],
                    "significant_gap": False,
                    "recommendations": ["Continue with current workflow"]
                },
                "evaluation_timestamp": time.time()
            }

    async def _dynamic_replanning(self, state: WorkflowState, evaluation_result: Dict) -> Dict[str, Any]:
        """Perform dynamic replanning based on gap analysis."""
        try:
            # Prepare replanning prompt
            replanning_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a research strategist performing dynamic replanning. Based on the gap analysis, create an updated research plan to address identified gaps.

Your updated plan should:
1. Address all identified information gaps
2. Include new search queries targeting missing information
3. Adjust research phases based on current progress
4. Prioritize high-impact activities
5. Consider alternative approaches if current methods are insufficient

Provide your updated plan in JSON format matching the original planning structure:
{
    "search_queries": [
        {
            "query": "string",
            "purpose": "string",
            "source_types": ["web", "academic", "news"],
            "priority": "HIGH|MEDIUM|LOW",
            "expected_results": "string",
            "gap_addressed": "string"
        }
    ],
    "data_requirements": [...],
    "research_phases": [...],
    "replanning_reason": "string",
    "priority_adjustments": ["adjustment1", "adjustment2"]
}
"""),
                ("human", "Original Research Objective: {research_topic}\n\nCurrent Plan: {current_plan}\n\nGap Analysis: {gap_analysis}\n\nIntermediate Results: {intermediate_results}")
            ])

            # Get current plan and gap analysis
            current_plan = state.intermediate_results.get("planning", {})
            gap_analysis = evaluation_result.get("gap_analysis", {})
            intermediate_results_str = json.dumps(state.intermediate_results, indent=2, default=str)

            # Invoke LLM for replanning
            chain = replanning_prompt | self.llm | JsonOutputParser()
            updated_plan = await chain.ainvoke({
                "research_topic": state.research_topic,
                "current_plan": json.dumps(current_plan, indent=2),
                "gap_analysis": json.dumps(gap_analysis, indent=2),
                "intermediate_results": intermediate_results_str
            })

            # Store replanning history
            replanning_history = state.intermediate_results.get("replanning_history", [])
            replanning_history.append({
                "timestamp": time.time(),
                "gap_analysis": gap_analysis,
                "updated_plan": updated_plan
            })
            state.intermediate_results["replanning_history"] = replanning_history

            return {
                "success": True,
                "updated_plan": updated_plan,
                "replanning_timestamp": time.time()
            }

        except Exception as e:
            self.logger.error(f"Failed to perform dynamic replanning for task {state.task_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "updated_plan": state.intermediate_results.get("planning", {}),
                "replanning_timestamp": time.time()
            }

    async def _perform_quality_checks(self, state: WorkflowState) -> Dict[str, Any]:
        """Perform quality checks on the workflow results."""

        quality_checks = {
            "planning_completeness": self._check_planning_completeness(state),
            "research_sufficiency": self._check_research_sufficiency(state),
            "analysis_accuracy": self._check_analysis_accuracy(state),
            "writing_quality": self._check_writing_quality(state)
        }

        # Determine overall quality
        passed_checks = sum(1 for check in quality_checks.values() if check["passed"])
        total_checks = len(quality_checks)

        overall_passed = passed_checks >= total_checks * 0.75  # 75% pass rate required

        # Determine next action if checks failed
        next_action = "end"
        if not overall_passed:
            # Find the first failed check and route back to that agent
            for check_name, check_result in quality_checks.items():
                if not check_result["passed"]:
                    if "planning" in check_name:
                        next_action = "planning"
                    elif "research" in check_name:
                        next_action = "research"
                    elif "analysis" in check_name:
                        next_action = "analysis"
                    elif "writing" in check_name:
                        next_action = "writing"
                    break

        return {
            "passed": overall_passed,
            "checks": quality_checks,
            "passed_count": passed_checks,
            "total_checks": total_checks,
            "next_action": next_action
        }

    def _check_planning_completeness(self, state: WorkflowState) -> Dict[str, Any]:
        """Check if planning phase produced complete results."""
        planning_results = state.intermediate_results.get("planning", {})

        required_elements = ["sub_tasks", "execution_plan", "complexity_score"]
        missing_elements = [elem for elem in required_elements if elem not in planning_results]

        return {
            "passed": len(missing_elements) == 0,
            "missing_elements": missing_elements,
            "score": 1.0 if len(missing_elements) == 0 else 0.0
        }

    def _check_research_sufficiency(self, state: WorkflowState) -> Dict[str, Any]:
        """Check if research phase gathered sufficient information."""
        research_results = state.intermediate_results.get("research", {})
        sources = research_results.get("sources", [])

        min_sources = 5
        min_relevance_score = 0.6

        high_quality_sources = [
            src for src in sources
            if src.get("relevance_score", 0) >= min_relevance_score
        ]

        return {
            "passed": len(high_quality_sources) >= min_sources,
            "source_count": len(sources),
            "high_quality_count": len(high_quality_sources),
            "score": min(1.0, len(high_quality_sources) / min_sources)
        }

    def _check_analysis_accuracy(self, state: WorkflowState) -> Dict[str, Any]:
        """Check if analysis phase produced accurate results."""
        analysis_results = state.intermediate_results.get("analysis", {})

        required_elements = ["key_findings", "data_validation", "insights"]
        has_required_elements = all(elem in analysis_results for elem in required_elements)

        # Check for contradictions or inconsistencies
        contradictions = analysis_results.get("contradictions", [])

        return {
            "passed": has_required_elements and len(contradictions) <= 2,
            "has_required_elements": has_required_elements,
            "contradiction_count": len(contradictions),
            "score": 0.8 if has_required_elements else 0.0
        }

    def _check_writing_quality(self, state: WorkflowState) -> Dict[str, Any]:
        """Check if writing phase produced high-quality output."""
        final_output = state.final_output or ""

        min_length = 500
        has_structure = any(marker in final_output for marker in ["# ", "## ", "1.", "- "])
        has_citations = "[" in final_output and "]" in final_output

        return {
            "passed": len(final_output) >= min_length and has_structure,
            "length": len(final_output),
            "has_structure": has_structure,
            "has_citations": has_citations,
            "score": 0.9 if len(final_output) >= min_length and has_structure else 0.3
        }

    def _should_continue(self, state: WorkflowState) -> str:
        """Determine if the workflow should continue or end."""

        if state.status == WorkflowStatus.FAILED:
            return END

        if state.status == WorkflowStatus.COMPLETED:
            return END

        # Check if we should loop back for improvements
        if state.current_agent == "coordinator":
            # This decision is made in the coordinator node
            return "end"

        # Default progression
        agent_sequence = ["planning", "research", "analysis", "writing", "coordinator"]
        current_index = agent_sequence.index(state.current_agent) if state.current_agent in agent_sequence else -1

        if current_index < len(agent_sequence) - 1:
            return agent_sequence[current_index + 1]
        else:
            return "coordinator"

    async def _store_in_long_term_memory(self, task_id: str, category: str, data: Dict[str, Any]):
        """Store results in long-term memory using ChromaDB."""
        try:
            collection_name = settings.LONG_TERM_MEMORY_COLLECTION
            document_id = f"{task_id}_{category}_{int(time.time())}"

            # Convert data to string for storage
            document_content = json.dumps(data, default=str)

            await self.chroma_service.add_document(
                collection_name=collection_name,
                document_id=document_id,
                content=document_content,
                metadata={
                    "task_id": task_id,
                    "category": category,
                    "timestamp": time.time(),
                    "user_id": data.get("user_id", "unknown")
                }
            )

            self.logger.info(f"Stored {category} in long-term memory for task {task_id}")

        except Exception as e:
            self.logger.error(f"Failed to store in long-term memory: {str(e)}")

    async def _store_final_result(self, task_id: str, final_output: str):
        """Store the final result in Redis for quick access."""
        try:
            result_key = f"task:{task_id}:final_result"
            await self.redis_service.set_value(
                result_key,
                {
                    "final_report": final_output,
                    "completed_at": time.time(),
                    "status": "completed"
                },
                ttl=86400  # 24 hours
            )

        except Exception as e:
            self.logger.error(f"Failed to store final result: {str(e)}")

    async def _update_workflow_status(self, task_id: str, state: WorkflowState):
        """Update workflow status in Redis for real-time monitoring."""
        try:
            status_key = f"task:{task_id}:workflow_status"
            status_data = {
                "status": state.status.value,
                "current_agent": state.current_agent,
                "agent_statuses": state.agent_statuses,
                "updated_at": state.updated_at,
                "error_message": state.error_message
            }

            await self.redis_service.set_value(status_key, status_data, ttl=3600)

            # Publish status update
            await self.redis_service.publish("workflow_status_updates", {
                "task_id": task_id,
                "status": state.status.value,
                "current_agent": state.current_agent,
                "timestamp": time.time()
            })

        except Exception as e:
            self.logger.error(f"Failed to update workflow status: {str(e)}")

    async def get_workflow_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow."""
        if task_id in self.active_workflows:
            state = self.active_workflows[task_id]
            return {
                "task_id": state.task_id,
                "status": state.status.value,
                "current_agent": state.current_agent,
                "agent_statuses": state.agent_statuses,
                "updated_at": state.updated_at,
                "error_message": state.error_message
            }

        return None

    async def cancel_workflow(self, task_id: str) -> bool:
        """Cancel an active workflow."""
        if task_id in self.active_workflows:
            state = self.active_workflows[task_id]
            state.status = WorkflowStatus.CANCELLED
            state.updated_at = time.time()

            await self._update_workflow_status(task_id, state)

            self.logger.info(f"Cancelled workflow for task {task_id}")
            return True

        return False

    async def get_workflow_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get the execution history of a workflow."""
        try:
            history_key = f"task:{task_id}:execution_history"
            history = await self.redis_service.get_list(history_key, 0, -1)
            return history or []

        except Exception as e:
            self.logger.error(f"Failed to get workflow history: {str(e)}")
            return []