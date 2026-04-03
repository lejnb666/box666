"""
Writing Agent - Generates structured reports and documentation
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse


class WritingAgent(BaseAgent):
    """Writing Agent responsible for report generation and formatting."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service,
        max_iterations: int = None,
        max_retries: int = None
    ):
        super().__init__(
            name="WritingAgent",
            llm=llm,
            redis_service=redis_service,
            max_iterations=max_iterations,
            max_retries=max_retries
        )
        self.logger = logging.getLogger(__name__)

    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the writing agent's core logic."""
        self._current_action = "synthesizing_information"

        try:
            # Step 1: Retrieve analysis results
            analysis_data = await self._retrieve_analysis_data(context)
            if not analysis_data:
                return AgentResponse(
                    success=False,
                    data={},
                    error="No analysis data found to write from"
                )

            # Step 2: Get user preferences
            writing_preferences = self._get_writing_preferences(context)

            # Step 3: Generate structured report
            self._current_action = "generating_report"
            report_result = await self._generate_structured_report(context, analysis_data, writing_preferences)

            # Update context with writing results
            context.intermediate_results["writing"] = report_result.data
            context.metadata["writing_completed_at"] = datetime.now().isoformat()

            return AgentResponse(
                success=True,
                data=report_result.data,
                messages=[
                    "Analysis data synthesized successfully",
                    "Report generated successfully",
                    "Final report ready for delivery"
                ]
            )

        except Exception as e:
            self.logger.error(f"Writing agent execution failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={},
                error=f"Writing failed: {str(e)}"
            )

    async def _retrieve_analysis_data(self, context: AgentContext) -> Dict[str, Any]:
        """Retrieve analysis data from previous agent."""
        analysis_key = f"task:{context.task_id}:results:analysis"
        analysis_data = await self.redis_service.get_hash(analysis_key)

        if not analysis_data or not analysis_data.get("content"):
            return context.intermediate_results.get("analysis", {})

        try:
            return json.loads(analysis_data["content"])
        except json.JSONDecodeError:
            return analysis_data

    def _get_writing_preferences(self, context: AgentContext) -> Dict[str, Any]:
        """Extract writing preferences from context."""
        preferences = context.metadata.get("preferences", {})
        
        return {
            "output_format": context.metadata.get("output_format", "markdown"),
            "tone": preferences.get("tone", "professional"),
            "include_citations": preferences.get("include_citations", True)
        }

    async def _generate_structured_report(self, context: AgentContext, analysis_data: Dict, preferences: Dict) -> AgentResponse:
        """Generate the main structured report content."""

        report_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert technical writer. Create a comprehensive, well-structured report based on the analysis data.

Requirements:
- Maintain factual accuracy
- Use clear, professional language
- Include all key findings and insights
- Provide actionable conclusions
"""),
            ("human", """Analysis Data: {analysis_data}

Research Topic: {research_topic}

Writing Preferences: {preferences}

Please generate a comprehensive report.")
        ])

        try:
            chain = report_prompt | self.llm
            report_content = await chain.ainvoke({
                "analysis_data": json.dumps(analysis_data, indent=2),
                "research_topic": context.research_topic,
                "preferences": json.dumps(preferences, indent=2)
            })

            # Format the content
            formatted_content = await self._format_content(report_content.content, preferences.get("output_format", "markdown"))

            # Store final result in Redis
            result_key = f"task:{context.task_id}:results:writing"
            await self.redis_service.set_hash(result_key, {
                "content": formatted_content,
                "timestamp": datetime.now().isoformat(),
                "format": preferences.get("output_format", "markdown"),
                "research_topic": context.research_topic
            })

            return AgentResponse(
                success=True,
                data={
                    "content": formatted_content,
                    "format": preferences.get("output_format", "markdown"),
                    "word_count": len(formatted_content.split())
                },
                messages=["Generated structured report content"]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to generate report: {str(e)}"
            )

    async def _format_content(self, content: str, output_format: str) -> str:
        """Format the content according to the specified output format."""
        
        if output_format == "markdown":
            # Ensure proper markdown formatting
            if not content.startswith("# "):
                # Add basic markdown structure
                lines = content.split("\n")
                formatted_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("Executive Summary") or line.startswith("Introduction") or line.startswith("Conclusion"):
                        formatted_lines.append(f"## {line}")
                    elif line and not line.startswith("#"):
                        formatted_lines.append(line)
                        formatted_lines.append("")
                    else:
                        formatted_lines.append(line)
                
                content = "\n".join(formatted_lines)
        
        elif output_format == "html":
            # Convert to basic HTML
            content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Research Report</title>
</head>
<body>
    <h1>Research Report</h1>
    <div>{content.replace('\n', '<br>')}</div>
</body>
</html>"""
        
        return content
