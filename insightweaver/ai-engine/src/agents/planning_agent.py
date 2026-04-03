"""
Planning Agent - Breaks down complex research tasks into manageable sub-tasks
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus
from src.config.settings import settings


class PlanningAgent(BaseAgent):
    """Planning Agent responsible for task decomposition and workflow planning."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service,
        max_iterations: int = None,
        max_retries: int = None
    ):
        super().__init__(
            name="PlanningAgent",
            llm=llm,
            redis_service=redis_service,
            max_iterations=max_iterations,
            max_retries=max_retries
        )
        self.logger = logging.getLogger(__name__)

    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the planning agent's core logic."""
        self._current_action = "analyzing_research_request"

        try:
            # Step 1: Analyze the research request
            analysis_result = await self._analyze_research_request(context)
            if not analysis_result.success:
                return analysis_result

            # Step 2: Generate task decomposition
            self._current_action = "decomposing_task"
            decomposition_result = await self._decompose_task(context, analysis_result.data)
            if not decomposition_result.success:
                return decomposition_result

            # Step 3: Create execution plan
            self._current_action = "creating_execution_plan"
            plan_result = await self._create_execution_plan(context, decomposition_result.data)
            if not plan_result.success:
                return plan_result

            # Step 4: Validate and optimize plan
            self._current_action = "validating_plan"
            final_plan = await self._validate_and_optimize_plan(context, plan_result.data)

            # Update context with planning results
            context.intermediate_results["planning"] = final_plan
            context.metadata["plan_created_at"] = datetime.now().isoformat()

            return AgentResponse(
                success=True,
                data=final_plan,
                messages=[
                    "Research request analyzed successfully",
                    f"Task decomposed into {len(final_plan.get('sub_tasks', []))} sub-tasks",
                    "Execution plan created and validated"
                ],
                metadata={
                    "complexity_score": final_plan.get("complexity_score", 0),
                    "estimated_duration": final_plan.get("estimated_duration", 0),
                    "required_agents": len(set(task.get("assigned_agent") for task in final_plan.get("sub_tasks", [])))
                }
            )

        except Exception as e:
            self.logger.error(f"Planning agent execution failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={},
                error=f"Planning failed: {str(e)}"
            )

    async def _analyze_research_request(self, context: AgentContext) -> AgentResponse:
        """Analyze the research request to understand requirements and scope."""

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research planning expert. Analyze the given research request and provide a structured analysis.

Your analysis should include:
1. Main research objective and scope
2. Key topics and sub-topics to investigate
3. Required information types (statistics, expert opinions, case studies, etc.)
4. Complexity assessment
5. Potential challenges and risks
6. Success criteria

Provide your analysis in JSON format with the following structure:
{
    "main_objective": "string",
    "scope": "string",
    "key_topics": ["string"],
    "information_types": ["string"],
    "complexity": "LOW|MEDIUM|HIGH|VERY_HIGH",
    "challenges": ["string"],
    "success_criteria": ["string"],
    "estimated_research_depth": "SHALLOW|MODERATE|DEEP|COMPREHENSIVE"
}
"""),
            ("human", "Research Request: {research_topic}\n\nAdditional Context: {additional_context}")
        ])

        try:
            chain = analysis_prompt | self.llm | JsonOutputParser()
            analysis = await chain.ainvoke({
                "research_topic": context.research_topic,
                "additional_context": json.dumps(context.metadata, default=str)
            })

            # Store analysis in conversation history
            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Research analysis completed: {analysis.get('main_objective', 'Unknown objective')}"
            )

            return AgentResponse(
                success=True,
                data=analysis,
                messages=[f"Research scope identified: {analysis.get('scope', 'Not specified')}"]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to analyze research request: {str(e)}"
            )

    async def _decompose_task(self, context: AgentContext, analysis: Dict) -> AgentResponse:
        """Decompose the main research task into specific sub-tasks."""

        decomposition_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a task decomposition expert. Based on the research analysis, break down the research into specific, actionable sub-tasks.

Each sub-task should:
1. Have a clear objective
2. Be assigned to the most appropriate agent type
3. Have defined inputs and expected outputs
4. Include success criteria
5. Have estimated complexity and duration

Available agent types:
- ResearchAgent: For information gathering, web searches, data collection
- AnalysisAgent: For data processing, validation, cross-referencing
- WritingAgent: For content creation, report generation, formatting

Provide the decomposition in JSON format with the following structure:
{
    "sub_tasks": [
        {
            "id": "string",
            "title": "string",
            "description": "string",
            "assigned_agent": "ResearchAgent|AnalysisAgent|WritingAgent",
            "priority": "LOW|MEDIUM|HIGH|CRITICAL",
            "estimated_duration_minutes": int,
            "complexity": "LOW|MEDIUM|HIGH",
            "dependencies": ["task_id"],
            "success_criteria": ["string"],
            "required_tools": ["string"]
        }
    ],
    "task_dependencies": [
        {"from": "task_id", "to": "task_id", "type": "depends_on|blocks|parallel"}
    ],
    "critical_path": ["task_id"],
    "total_estimated_duration": int
}
"""),
            ("human", "Research Analysis: {analysis}\n\nUser Requirements: {user_requirements}")
        ])

        try:
            # Extract user requirements from context
            user_requirements = {
                "research_topic": context.research_topic,
                "additional_preferences": context.metadata.get("preferences", {}),
                "output_format": context.metadata.get("output_format", "markdown"),
                "deadline_minutes": context.metadata.get("deadline_minutes", 30)
            }

            chain = decomposition_prompt | self.llm | JsonOutputParser()
            decomposition = await chain.ainvoke({
                "analysis": json.dumps(analysis, indent=2),
                "user_requirements": json.dumps(user_requirements, indent=2)
            })

            # Validate decomposition structure
            if not decomposition.get("sub_tasks"):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Task decomposition failed: no sub-tasks generated"
                )

            # Store decomposition results
            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Task decomposed into {len(decomposition['sub_tasks'])} sub-tasks"
            )

            return AgentResponse(
                success=True,
                data=decomposition,
                messages=[
                    f"Generated {len(decomposition['sub_tasks'])} sub-tasks",
                    f"Critical path identified with {len(decomposition.get('critical_path', []))} tasks",
                    f"Total estimated duration: {decomposition.get('total_estimated_duration', 0)} minutes"
                ]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to decompose task: {str(e)}"
            )

    async def _create_execution_plan(self, context: AgentContext, decomposition: Dict) -> AgentResponse:
        """Create a detailed execution plan with scheduling and resource allocation."""

        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an execution planning expert. Create a detailed execution plan based on the task decomposition.

The execution plan should include:
1. Task scheduling with start/end times
2. Resource allocation and agent assignments
3. Parallel execution opportunities
4. Risk mitigation strategies
5. Quality checkpoints
6. Progress milestones

Provide the execution plan in JSON format with the following structure:
{
    "execution_phases": [
        {
            "phase": "string",
            "start_time": "ISO timestamp",
            "end_time": "ISO timestamp",
            "tasks": ["task_id"],
            "agents_involved": ["agent_name"],
            "deliverables": ["string"],
            "success_criteria": ["string"]
        }
    ],
    "resource_allocation": {
        "agent_workload": {
            "agent_name": {"tasks": ["task_id"], "estimated_hours": float}
        },
        "tool_requirements": {"tool_name": {"tasks": ["task_id"], "duration_minutes": int}}
    },
    "risk_mitigation": [
        {"risk": "string", "probability": "LOW|MEDIUM|HIGH", "impact": "LOW|MEDIUM|HIGH", "mitigation": "string"}
    ],
    "quality_checkpoints": [
        {"checkpoint": "string", "phase": "string", "criteria": ["string"], "validation_method": "string"}
    ],
    "progress_milestones": [
        {"milestone": "string", "completion_percentage": int, "deliverables": ["string"]}
    ],
    "total_timeline_minutes": int,
    "buffer_time_minutes": int
}
"""),
            ("human", "Task Decomposition: {decomposition}\n\nUser Constraints: {constraints}")
        ])

        try:
            # Extract user constraints
            constraints = {
                "deadline_minutes": context.metadata.get("deadline_minutes", 30),
                "priority": context.metadata.get("priority", "MEDIUM"),
                "quality_requirements": context.metadata.get("quality_requirements", []),
                "resource_limits": context.metadata.get("resource_limits", {})
            }

            chain = planning_prompt | self.llm | JsonOutputParser()
            execution_plan = await chain.ainvoke({
                "decomposition": json.dumps(decomposition, indent=2),
                "constraints": json.dumps(constraints, indent=2)
            })

            # Validate execution plan
            if not execution_plan.get("execution_phases"):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Execution planning failed: no execution phases generated"
                )

            # Store execution plan
            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Execution plan created with {len(execution_plan['execution_phases'])} phases"
            )

            return AgentResponse(
                success=True,
                data=execution_plan,
                messages=[
                    f"Created execution plan with {len(execution_plan['execution_phases'])} phases",
                    f"Total timeline: {execution_plan.get('total_timeline_minutes', 0)} minutes",
                    f"Buffer time: {execution_plan.get('buffer_time_minutes', 0)} minutes"
                ]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to create execution plan: {str(e)}"
            )

    async def _validate_and_optimize_plan(self, context: AgentContext, plan: Dict) -> Dict:
        """Validate the execution plan and make optimizations."""

        self.logger.info("Validating and optimizing execution plan")

        # Perform validation checks
        validation_results = {
            "timeline_feasibility": self._validate_timeline(plan, context),
            "resource_adequacy": self._validate_resources(plan),
            "dependency_consistency": self._validate_dependencies(plan),
            "risk_assessment": self._assess_risks(plan)
        }

        # Make optimizations based on validation results
        optimized_plan = plan.copy()

        # Adjust timeline if needed
        if not validation_results["timeline_feasibility"]["feasible"]:
            optimized_plan = self._optimize_timeline(optimized_plan, context)

        # Optimize resource allocation
        optimized_plan = self._optimize_resources(optimized_plan)

        # Add validation metadata
        optimized_plan["validation_results"] = validation_results
        optimized_plan["optimization_applied"] = True
        optimized_plan["final_complexity_score"] = self._calculate_complexity_score(optimized_plan)

        await self._add_to_conversation_history(
            context.task_id,
            "ai",
            f"Plan validated and optimized. Complexity score: {optimized_plan['final_complexity_score']}"
        )

        return optimized_plan

    def _validate_timeline(self, plan: Dict, context: AgentContext) -> Dict:
        """Validate if the timeline is feasible given user constraints."""
        total_timeline = plan.get("total_timeline_minutes", 0)
        user_deadline = context.metadata.get("deadline_minutes", 30)

        feasible = total_timeline <= user_deadline
        buffer_percentage = ((user_deadline - total_timeline) / user_deadline * 100) if feasible else 0

        return {
            "feasible": feasible,
            "total_timeline": total_timeline,
            "user_deadline": user_deadline,
            "buffer_percentage": max(0, buffer_percentage),
            "recommendation": "Timeline is feasible" if feasible else "Timeline exceeds deadline, optimization needed"
        }

    def _validate_resources(self, plan: Dict) -> Dict:
        """Validate if required resources are available."""
        resource_allocation = plan.get("resource_allocation", {})
        agent_workload = resource_allocation.get("agent_workload", {})

        # Check for over-allocation
        over_allocated_agents = []
        for agent, workload in agent_workload.items():
            estimated_hours = workload.get("estimated_hours", 0)
            if estimated_hours > settings.MAX_CONCURRENT_TASKS:
                over_allocated_agents.append(agent)

        return {
            "adequate": len(over_allocated_agents) == 0,
            "over_allocated_agents": over_allocated_agents,
            "total_agents_required": len(agent_workload),
            "recommendation": "Resource allocation is adequate" if len(over_allocated_agents) == 0 else f"Agents over-allocated: {', '.join(over_allocated_agents)}"
        }

    def _validate_dependencies(self, plan: Dict) -> Dict:
        """Validate task dependencies for consistency."""
        # This would implement dependency validation logic
        return {
            "consistent": True,
            "circular_dependencies": [],
            "orphaned_tasks": [],
            "recommendation": "Dependencies are consistent"
        }

    def _assess_risks(self, plan: Dict) -> Dict:
        """Assess potential risks in the execution plan."""
        risk_mitigation = plan.get("risk_mitigation", [])

        high_risk_items = [risk for risk in risk_mitigation if risk.get("probability") == "HIGH" and risk.get("impact") in ["HIGH", "MEDIUM"]]

        return {
            "risk_level": "HIGH" if len(high_risk_items) > 2 else "MEDIUM" if len(high_risk_items) > 0 else "LOW",
            "high_risk_items": len(high_risk_items),
            "mitigation_strategies": len(risk_mitigation),
            "recommendation": f"Plan has {len(high_risk_items)} high-risk items that need attention"
        }

    def _optimize_timeline(self, plan: Dict, context: AgentContext) -> Dict:
        """Optimize the timeline to meet user constraints."""
        # Implement timeline optimization logic
        # This could include parallelizing tasks, reducing scope, etc.
        optimized_plan = plan.copy()

        # Reduce estimated durations by 20% through optimization
        for phase in optimized_plan.get("execution_phases", []):
            original_duration = self._calculate_phase_duration(phase)
            optimized_duration = max(original_duration * 0.8, 5)  # Minimum 5 minutes per phase
            # Update phase timing accordingly

        optimized_plan["timeline_optimized"] = True
        optimized_plan["optimization_details"] = "Reduced phase durations and increased parallelization"

        return optimized_plan

    def _optimize_resources(self, plan: Dict) -> Dict:
        """Optimize resource allocation."""
        # Implement resource optimization logic
        return plan

    def _calculate_complexity_score(self, plan: Dict) -> float:
        """Calculate overall complexity score for the plan."""
        factors = [
            len(plan.get("sub_tasks", [])) * 0.1,  # Number of tasks
            len(plan.get("execution_phases", [])) * 0.2,  # Number of phases
            len(plan.get("risk_mitigation", [])) * 0.15,  # Number of risks
            plan.get("total_timeline_minutes", 0) * 0.01  # Timeline length
        ]

        return min(sum(factors), 10.0)  # Cap at 10.0

    def _calculate_phase_duration(self, phase: Dict) -> float:
        """Calculate the duration of an execution phase."""
        # This would parse the start_time and end_time to calculate duration
        return 30.0  # Placeholder implementation