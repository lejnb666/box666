"""
Analysis Agent - Processes and validates collected information
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from src.services.chroma_service import ChromaService


class AnalysisAgent(BaseAgent):
    """Analysis Agent responsible for data processing, validation, and insight extraction."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service,
        chroma_service: ChromaService = None,
        max_iterations: int = None,
        max_retries: int = None
    ):
        super().__init__(
            name="AnalysisAgent",
            llm=llm,
            redis_service=redis_service,
            max_iterations=max_iterations,
            max_retries=max_retries
        )
        self.chroma_service = chroma_service
        self.logger = logging.getLogger(__name__)

    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the analysis agent's core logic."""
        self._current_action = "processing_research_data"

        try:
            # Step 1: Retrieve research data
            research_data = await self._retrieve_research_data(context)
            if not research_data:
                return AgentResponse(
                    success=False,
                    data={},
                    error="No research data found to analyze"
                )

            # Step 2: Cross-validate information
            self._current_action = "cross_validating_information"
            validation_result = await self._cross_validate_information(context, research_data)
            if not validation_result.success:
                return validation_result

            # Step 3: Extract key insights
            self._current_action = "extracting_insights"
            insights_result = await self._extract_insights(context, validation_result.data)

            # Update context with analysis results
            context.intermediate_results["analysis"] = insights_result.data
            context.metadata["analysis_completed_at"] = datetime.now().isoformat()

            return AgentResponse(
                success=True,
                data=insights_result.data,
                messages=[
                    f"Analyzed {len(research_data)} information sources",
                    f"Extracted {len(insights_result.data.get('key_findings', []))} key insights",
                    "Analysis completed successfully"
                ]
            )

        except Exception as e:
            self.logger.error(f"Analysis agent execution failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={},
                error=f"Analysis failed: {str(e)}"
            )

    async def _retrieve_research_data(self, context: AgentContext) -> List[Dict[str, Any]]:
        """Retrieve research data from previous agent."""
        research_key = f"task:{context.task_id}:results:research"
        research_data = await self.redis_service.get_hash(research_key)

        if not research_data:
            return []

        # Extract sources from research data
        sources = []
        for key in ["sources", "web_results", "academic_papers"]:
            if research_data.get(key):
                sources.extend(research_data[key])

        return sources

    async def _cross_validate_information(self, context: AgentContext, research_data: List[Dict]) -> AgentResponse:
        """Cross-validate information across different sources."""

        validation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data validation expert. Cross-validate the provided research information.

Provide your analysis in JSON format with validated sources and quality assessment.
"""),
            ("human", "Research Data to Validate: {research_data}")
        ])

        try:
            chain = validation_prompt | self.llm | JsonOutputParser()
            validation_result = await chain.ainvoke({
                "research_data": json.dumps(research_data, indent=2)
            })

            return AgentResponse(
                success=True,
                data=validation_result,
                messages=[f"Validated {len(research_data)} sources"]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to validate information: {str(e)}"
            )

    async def _extract_insights(self, context: AgentContext, validation_data: Dict) -> AgentResponse:
        """Extract key insights from validated information."""

        insights_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an insight extraction expert. Analyze the information to identify key findings, patterns, and implications.

Provide your insights in JSON format.
"""),
            ("human", "Validated Information: {validation_data}\n\nResearch Topic: {research_topic}")
        ])

        try:
            chain = insights_prompt | self.llm | JsonOutputParser()
            insights_result = await chain.ainvoke({
                "validation_data": json.dumps(validation_data, indent=2),
                "research_topic": context.research_topic
            })

            # Store analysis results in Redis
            analysis_key = f"task:{context.task_id}:results:analysis"
            await self.redis_service.set_hash(analysis_key, {
                "content": json.dumps(insights_result),
                "timestamp": datetime.now().isoformat(),
                "research_topic": context.research_topic
            })

            return AgentResponse(
                success=True,
                data=insights_result,
                messages=[f"Extracted {len(insights_result.get('key_findings', []))} key insights"]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to extract insights: {str(e)}"
            )
