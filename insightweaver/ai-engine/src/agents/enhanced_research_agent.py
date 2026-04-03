"""
Enhanced Research Agent - Advanced information gathering with self-improvement capabilities
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import re

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.tools import DuckDuckGoSearchRun

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus
from src.services.chroma_service import ChromaService
from src.config.settings import settings
from src.tools.advanced_search_tools import (
    AcademicSearchTool, NewsSearchTool, PatentSearchTool,
    SocialMediaSearchTool, GovernmentDataTool
)


class SearchStrategy(Enum):
    """Search strategy enumeration."""
    BROAD = "broad"  # General web search
    ACADEMIC = "academic"  # Scholarly sources
    NEWS = "news"  # News and current events
    PATENT = "patent"  # Patent databases
    SOCIAL = "social"  # Social media and forums
    GOVERNMENT = "government"  # Government and official sources
    COMPREHENSIVE = "comprehensive"  # All available sources


@dataclass
class SearchResult:
    """Enhanced search result with quality metrics."""
    title: str
    url: str
    snippet: str
    source_type: str
    relevance_score: float
    credibility_score: float
    freshness_score: float
    content_quality_score: float
    retrieved_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_overall_score(self) -> float:
        """Calculate overall quality score."""
        weights = {
            'relevance': 0.3,
            'credibility': 0.25,
            'freshness': 0.2,
            'quality': 0.25
        }

        return (
            self.relevance_score * weights['relevance'] +
            self.credibility_score * weights['credibility'] +
            self.freshness_score * weights['freshness'] +
            self.content_quality_score * weights['quality']
        )


@dataclass
class ResearchPlan:
    """Detailed research execution plan."""
    search_strategies: List[SearchStrategy]
    search_queries: List[str]
    source_priorities: Dict[str, float]
    quality_thresholds: Dict[str, float]
    max_sources_per_strategy: int
    cross_validation_required: bool
    expected_insights: List[str]


class EnhancedResearchAgent(BaseAgent):
    """Enhanced Research Agent with advanced capabilities and self-improvement."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service,
        chroma_service: ChromaService,
        max_iterations: int = None,
        max_retries: int = None
    ):
        super().__init__(
            name="EnhancedResearchAgent",
            llm=llm,
            redis_service=redis_service,
            max_iterations=max_iterations,
            max_retries=max_retries
        )

        self.chroma_service = chroma_service

        # Initialize advanced search tools
        self.search_tools = {
            SearchStrategy.BROAD: GoogleSerperAPIWrapper(),
            SearchStrategy.ACADEMIC: AcademicSearchTool(),
            SearchStrategy.NEWS: NewsSearchTool(),
            SearchStrategy.PATENT: PatentSearchTool(),
            SearchStrategy.SOCIAL: SocialMediaSearchTool(),
            SearchStrategy.GOVERNMENT: GovernmentDataTool()
        }

        # Research quality metrics
        self.quality_metrics = {
            'sources_evaluated': 0,
            'sources_accepted': 0,
            'cross_validations': 0,
            'insights_generated': 0
        }

        self.logger = logging.getLogger(__name__)

    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the enhanced research agent's core logic."""
        self._current_action = "planning_advanced_research"

        try:
            # Step 1: Create comprehensive research plan
            plan_result = await self._create_research_plan(context)
            if not plan_result.success:
                return plan_result

            research_plan = plan_result.data

            # Step 2: Execute multi-strategy search
            self._current_action = "executing_multi_strategy_search"
            search_result = await self._execute_multi_strategy_search(context, research_plan)
            if not search_result.success:
                return search_result

            search_results = search_result.data

            # Step 3: Advanced source evaluation
            self._current_action = "evaluating_sources"
            evaluation_result = await self._evaluate_sources_advanced(context, search_results, research_plan)
            if not evaluation_result.success:
                return evaluation_result

            evaluated_sources = evaluation_result.data

            # Step 4: Cross-validation and fact-checking
            self._current_action = "cross_validating_information"
            validation_result = await self._cross_validate_information(context, evaluated_sources)
            if not validation_result.success:
                return validation_result

            validated_sources = validation_result.data

            # Step 5: Generate insights and patterns
            self._current_action = "generating_insights"
            insights_result = await self._generate_insights(context, validated_sources, research_plan)
            if not insights_result.success:
                return insights_result

            insights = insights_result.data

            # Step 6: Store learnings for future improvement
            await self._store_learnings(context, research_plan, insights)

            # Update context with enhanced results
            context.intermediate_results["enhanced_research"] = {
                "sources": validated_sources,
                "insights": insights,
                "research_plan": research_plan,
                "quality_metrics": self.quality_metrics,
                "execution_metadata": {
                    "strategies_used": [s.value for s in research_plan.search_strategies],
                    "total_sources_found": len(search_results),
                    "sources_after_validation": len(validated_sources),
                    "cross_validations_performed": self.quality_metrics['cross_validations']
                }
            }

            return AgentResponse(
                success=True,
                data=context.intermediate_results["enhanced_research"],
                messages=[
                    f"Created comprehensive research plan with {len(research_plan.search_strategies)} strategies",
                    f"Executed multi-strategy search finding {len(search_results)} sources",
                    f"Advanced evaluation selected {len(validated_sources)} high-quality sources",
                    f"Generated {len(insights)} key insights with cross-validation",
                    "Research learnings stored for future improvement"
                ],
                metadata={
                    "total_sources_found": len(search_results),
                    "high_quality_sources": len(validated_sources),
                    "insights_generated": len(insights),
                    "cross_validations": self.quality_metrics['cross_validations'],
                    "research_duration_minutes": (time.time() - context.created_at) / 60,
                    "strategies_used": len(research_plan.search_strategies)
                }
            )

        except Exception as e:
            self.logger.error(f"Enhanced research agent execution failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={},
                error=f"Enhanced research failed: {str(e)}"
            )

    async def _create_research_plan(self, context: AgentContext) -> AgentResponse:
        """Create a comprehensive research execution plan."""

        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research strategist. Create a comprehensive research plan for the given topic.

Your plan should include:
1. Multiple search strategies based on the research topic
2. Specific search queries optimized for each strategy
3. Source quality priorities and thresholds
4. Cross-validation requirements
5. Expected insights and patterns to look for

Consider the research topic complexity, required depth, and source credibility when creating the plan.

Provide your plan in JSON format with the following structure:
{
    "search_strategies": ["broad", "academic", "news", "patent", "social", "government"],
    "search_queries": [
        {
            "query": "string",
            "strategy": "string",
            "purpose": "string",
            "expected_quality": "HIGH|MEDIUM|LOW"
        }
    ],
    "source_priorities": {
        "academic": 0.9,
        "government": 0.8,
        "news": 0.6,
        "broad": 0.5,
        "social": 0.3
    },
    "quality_thresholds": {
        "min_relevance_score": 0.7,
        "min_credibility_score": 0.6,
        "min_freshness_score": 0.4,
        "min_overall_score": 0.65
    },
    "max_sources_per_strategy": 15,
    "cross_validation_required": true,
    "expected_insights": ["string"],
    "risk_factors": ["string"],
    "contingency_strategies": ["string"]
}
"""),
            ("human", "Research Topic: {research_topic}\n\nPlanning Context: {planning_context}\n\nUser Requirements: {user_requirements}")
        ])

        try:
            # Get context from previous planning
            planning_context = context.intermediate_results.get("planning", {})
            user_requirements = context.metadata.get("user_requirements", {})

            # Check for similar research in long-term memory
            similar_research = await self.chroma_service.find_similar_research(
                query=context.research_topic,
                n_results=3
            )

            # Incorporate learnings from similar research
            memory_context = self._extract_memory_insights(similar_research)

            chain = planning_prompt | self.llm | JsonOutputParser()
            plan_data = await chain.ainvoke({
                "research_topic": context.research_topic,
                "planning_context": json.dumps(planning_context, indent=2),
                "user_requirements": json.dumps(user_requirements, indent=2),
                "memory_context": json.dumps(memory_context, indent=2)
            })

            # Convert to ResearchPlan object
            research_plan = ResearchPlan(
                search_strategies=[SearchStrategy(s) for s in plan_data.get("search_strategies", [])],
                search_queries=plan_data.get("search_queries", []),
                source_priorities=plan_data.get("source_priorities", {}),
                quality_thresholds=plan_data.get("quality_thresholds", {}),
                max_sources_per_strategy=plan_data.get("max_sources_per_strategy", 10),
                cross_validation_required=plan_data.get("cross_validation_required", True),
                expected_insights=plan_data.get("expected_insights", [])
            )

            # Validate and enhance the plan
            enhanced_plan = await self._enhance_research_plan(research_plan, context)

            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Enhanced research plan created with {len(enhanced_plan.search_strategies)} strategies and {len(enhanced_plan.search_queries)} queries"
            )

            return AgentResponse(
                success=True,
                data=enhanced_plan,
                messages=[
                    f"Research plan created with {len(enhanced_plan.search_strategies)} search strategies",
                    f"Generated {len(enhanced_plan.search_queries)} optimized search queries",
                    f"Quality thresholds set for source evaluation",
                    "Cross-validation requirements defined"
                ]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to create research plan: {str(e)}"
            )

    def _extract_memory_insights(self, similar_research: List[Dict]) -> Dict[str, Any]:
        """Extract insights from similar past research."""
        insights = {
            "successful_strategies": [],
            "effective_queries": [],
            "quality_sources": [],
            "common_insights": []
        }

        for research in similar_research:
            metadata = research.get("metadata", {})

            # Extract successful strategies
            if "strategies_used" in metadata:
                insights["successful_strategies"].extend(metadata["strategies_used"])

            # Extract quality sources
            if "high_quality_sources" in metadata:
                insights["quality_sources"].extend(metadata["high_quality_sources"])

            # Extract common insights
            if "insights_generated" in metadata:
                insights["common_insights"].extend(metadata["insights_generated"])

        # Deduplicate and rank
        insights["successful_strategies"] = list(set(insights["successful_strategies"]))
        insights["effective_queries"] = list(set(insights["effective_queries"]))

        return insights

    async def _enhance_research_plan(self, plan: ResearchPlan, context: AgentContext) -> ResearchPlan:
        """Enhance the research plan based on topic analysis and past learnings."""

        # Analyze topic complexity
        complexity_analysis = await self._analyze_topic_complexity(context.research_topic)

        # Adjust strategies based on complexity
        if complexity_analysis["technical_depth"] > 0.7:
            if SearchStrategy.ACADEMIC not in plan.search_strategies:
                plan.search_strategies.append(SearchStrategy.ACADEMIC)

        if complexity_analysis["current_events"] > 0.5:
            if SearchStrategy.NEWS not in plan.search_strategies:
                plan.search_strategies.append(SearchStrategy.NEWS)

        if complexity_analysis["policy_relevance"] > 0.6:
            if SearchStrategy.GOVERNMENT not in plan.search_strategies:
                plan.search_strategies.append(SearchStrategy.GOVERNMENT)

        # Optimize quality thresholds based on user requirements
        user_requirements = context.metadata.get("user_requirements", {})
        if user_requirements.get("high_quality_only", False):
            plan.quality_thresholds["min_overall_score"] = 0.8
            plan.quality_thresholds["min_credibility_score"] = 0.75

        # Adjust source limits based on deadline
        deadline_minutes = user_requirements.get("deadline_minutes", 30)
        if deadline_minutes < 15:
            plan.max_sources_per_strategy = 5
        elif deadline_minutes > 60:
            plan.max_sources_per_strategy = 25

        return plan

    async def _analyze_topic_complexity(self, topic: str) -> Dict[str, float]:
        """Analyze the complexity and characteristics of the research topic."""

        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze the research topic for complexity and characteristics.

Provide analysis in JSON format:
{
    "technical_depth": 0.0-1.0,
    "current_events": 0.0-1.0,
    "policy_relevance": 0.0-1.0,
    "academic_relevance": 0.0-1.0,
    "requires_cross_domain": 0.0-1.0,
    "complexity_score": 0.0-1.0
}
"""),
            ("human", "Topic: {topic}")
        ])

        try:
            chain = analysis_prompt | self.llm | JsonOutputParser()
            analysis = await chain.ainvoke({"topic": topic})
            return analysis
        except Exception:
            # Return default analysis if LLM fails
            return {
                "technical_depth": 0.5,
                "current_events": 0.3,
                "policy_relevance": 0.3,
                "academic_relevance": 0.5,
                "requires_cross_domain": 0.4,
                "complexity_score": 0.5
            }

    async def _execute_multi_strategy_search(self, context: AgentContext, plan: ResearchPlan) -> AgentResponse:
        """Execute search across multiple strategies."""

        self.logger.info(f"Executing multi-strategy search with {len(plan.search_strategies)} strategies")

        all_results = []
        strategy_results = {}

        # Execute each search strategy
        for strategy in plan.search_strategies:
            self._current_action = f"searching_{strategy.value}"

            strategy_queries = [
                q for q in plan.search_queries
                if q.get("strategy") == strategy.value
            ]

            if not strategy_queries:
                continue

            strategy_results[strategy.value] = []

            for query_info in strategy_queries:
                try:
                    results = await self._execute_strategy_search(
                        strategy,
                        query_info,
                        plan.max_sources_per_strategy
                    )

                    strategy_results[strategy.value].extend(results)
                    all_results.extend(results)

                    # Update progress
                    await self._update_status(
                        context.task_id,
                        AgentStatus.EXECUTING,
                        {
                            "current_strategy": strategy.value,
                            "queries_completed": len(strategy_results[strategy.value]),
                            "total_results": len(all_results)
                        }
                    )

                except Exception as e:
                    self.logger.error(f"Search failed for strategy {strategy.value}: {str(e)}")
                    continue

        await self._add_to_conversation_history(
            context.task_id,
            "ai",
            f"Multi-strategy search completed: {len(all_results)} total results from {len(strategy_results)} strategies"
        )

        return AgentResponse(
            success=True,
            data=all_results,
            messages=[
                f"Executed {len(plan.search_strategies)} search strategies",
                f"Found {len(all_results)} total results",
                f"Strategy distribution: {', '.join([f'{k}: {len(v)}' for k, v in strategy_results.items()])}"
            ]
        )

    async def _execute_strategy_search(self, strategy: SearchStrategy, query_info: Dict, max_results: int) -> List[SearchResult]:
        """Execute search for a specific strategy."""

        tool = self.search_tools.get(strategy)
        if not tool:
            return []

        query = query_info.get("query", "")
        results = []

        try:
            if strategy == SearchStrategy.BROAD:
                search_results = await tool.arun(query)
            else:
                search_results = await tool.search(query, num_results=max_results)

            # Convert to SearchResult objects
            for result in search_results[:max_results]:
                search_result = SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("snippet", ""),
                    source_type=strategy.value,
                    relevance_score=result.get("relevance_score", 0.5),
                    credibility_score=result.get("credibility_score", 0.5),
                    freshness_score=result.get("freshness_score", 0.5),
                    content_quality_score=result.get("quality_score", 0.5),
                    retrieved_at=time.time(),
                    metadata=result.get("metadata", {})
                )
                results.append(search_result)

        except Exception as e:
            self.logger.error(f"Strategy search failed for {strategy.value}: {str(e)}")

        return results

    async def _evaluate_sources_advanced(self, context: AgentContext, search_results: List[SearchResult], plan: ResearchPlan) -> AgentResponse:
        """Advanced source evaluation with multiple quality metrics."""

        self.logger.info(f"Starting advanced evaluation of {len(search_results)} sources")

        evaluated_sources = []
        evaluation_stats = {
            "total_evaluated": 0,
            "passed_relevance": 0,
            "passed_credibility": 0,
            "passed_freshness": 0,
            "passed_overall": 0,
            "average_scores": {
                "relevance": 0,
                "credibility": 0,
                "freshness": 0,
                "quality": 0,
                "overall": 0
            }
        }

        # Score aggregation
        score_sums = {"relevance": 0, "credibility": 0, "freshness": 0, "quality": 0, "overall": 0}

        for result in search_results:
            evaluation_stats["total_evaluated"] += 1
            self.quality_metrics['sources_evaluated'] += 1

            # Calculate advanced scores
            advanced_scores = await self._calculate_advanced_scores(result, context)

            # Apply quality thresholds
            if self._meets_quality_thresholds(advanced_scores, plan.quality_thresholds):
                result.relevance_score = advanced_scores["relevance"]
                result.credibility_score = advanced_scores["credibility"]
                result.freshness_score = advanced_scores["freshness"]
                result.content_quality_score = advanced_scores["quality"]

                evaluated_sources.append(result)
                evaluation_stats["passed_overall"] += 1
                self.quality_metrics['sources_accepted'] += 1

            # Update statistics
            if advanced_scores["relevance"] >= plan.quality_thresholds.get("min_relevance_score", 0.5):
                evaluation_stats["passed_relevance"] += 1

            if advanced_scores["credibility"] >= plan.quality_thresholds.get("min_credibility_score", 0.5):
                evaluation_stats["passed_credibility"] += 1

            if advanced_scores["freshness"] >= plan.quality_thresholds.get("min_freshness_score", 0.3):
                evaluation_stats["passed_freshness"] += 1

            # Aggregate scores
            score_sums["relevance"] += advanced_scores["relevance"]
            score_sums["credibility"] += advanced_scores["credibility"]
            score_sums["freshness"] += advanced_scores["freshness"]
            score_sums["quality"] += advanced_scores["quality"]
            score_sums["overall"] += result.get_overall_score()

        # Calculate averages
        if evaluation_stats["total_evaluated"] > 0:
            for metric in score_sums:
                evaluation_stats["average_scores"][metric] = score_sums[metric] / evaluation_stats["total_evaluated"]

        # Sort by overall score
        evaluated_sources.sort(key=lambda x: x.get_overall_score(), reverse=True)

        await self._add_to_conversation_history(
            context.task_id,
            "ai",
            f"Advanced evaluation completed: {evaluation_stats['passed_overall']}/{evaluation_stats['total_evaluated']} sources passed quality checks"
        )

        return AgentResponse(
            success=True,
            data=evaluated_sources,
            messages=[
                f"Evaluated {evaluation_stats['total_evaluated']} sources with advanced metrics",
                f"{evaluation_stats['passed_overall']} sources met quality thresholds",
                f"Average quality score: {evaluation_stats['average_scores']['overall']:.2f}",
                f"Quality distribution - Relevance: {evaluation_stats['passed_relevance']}, Credibility: {evaluation_stats['passed_credibility']}, Freshness: {evaluation_stats['passed_freshness']}"
            ],
            metadata=evaluation_stats
        )

    async def _calculate_advanced_scores(self, result: SearchResult, context: AgentContext) -> Dict[str, float]:
        """Calculate advanced quality scores for a search result."""

        scores = {
            "relevance": result.relevance_score,
            "credibility": result.credibility_score,
            "freshness": result.freshness_score,
            "quality": result.content_quality_score
        }

        # Enhance relevance score with semantic analysis
        relevance_prompt = ChatPromptTemplate.from_messages([
            ("system", """Calculate the relevance score of this source to the research topic.