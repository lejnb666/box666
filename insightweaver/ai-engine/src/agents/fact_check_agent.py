"""
Fact Check Agent - Validates information accuracy by cross-referencing with source materials
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus
from src.config.settings import settings


class FactCheckAgent(BaseAgent):
    """Fact Check Agent responsible for validating information accuracy."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service,
        max_iterations: int = None,
        max_retries: int = None
    ):
        super().__init__(
            name="FactCheckAgent",
            llm=llm,
            redis_service=redis_service,
            max_iterations=max_iterations,
            max_retries=max_retries
        )

        self.logger = logging.getLogger(__name__)

    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the fact checking agent's core logic."""
        self._current_action = "analyzing_content_for_fact_checking"

        try:
            # Step 1: Extract claims from analysis/writing results
            extraction_result = await self._extract_claims(context)
            if not extraction_result.success:
                return extraction_result

            claims = extraction_result.data.get("claims", [])
            self.logger.info(f"Extracted {len(claims)} claims for fact checking")

            # Step 2: Cross-reference claims with source materials
            self._current_action = "cross_referencing_claims"
            verification_result = await self._verify_claims(context, claims)
            if not verification_result.success:
                return verification_result

            verification_results = verification_result.data

            # Step 3: Generate fact check report
            self._current_action = "generating_fact_check_report"
            report_result = await self._generate_fact_check_report(context, verification_results)

            # Update context with fact checking results
            context.intermediate_results["fact_check"] = report_result
            context.metadata["fact_check_completed_at"] = time.time()
            context.metadata["claims_verified"] = len(claims)

            return AgentResponse(
                success=True,
                data=report_result,
                messages=[
                    f"Extracted {len(claims)} claims for verification",
                    f"Verified claims against {len(verification_results.get('verified_claims', []))} sources",
                    f"Generated fact check report with {verification_results.get('accuracy_score', 0):.2f} accuracy score"
                ],
                metadata={
                    "total_claims": len(claims),
                    "verified_claims": len(verification_results.get("verified_claims", [])),
                    "accuracy_score": verification_results.get("accuracy_score", 0),
                    "fact_check_duration_minutes": (time.time() - context.created_at) / 60
                }
            )

        except Exception as e:
            self.logger.error(f"Fact checking agent execution failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={},
                error=f"Fact checking failed: {str(e)}"
            )

    async def _extract_claims(self, context: AgentContext) -> AgentResponse:
        """Extract factual claims from analysis and writing results."""

        # Get content to fact check
        analysis_results = context.intermediate_results.get("analysis", {})
        writing_results = context.intermediate_results.get("writing", {})

        content_to_check = {
            "analysis_findings": analysis_results.get("key_findings", []),
            "analysis_insights": analysis_results.get("insights", []),
            "final_report": writing_results.get("final_report", ""),
            "executive_summary": writing_results.get("executive_summary", "")
        }

        claims_extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a fact extraction expert. Extract specific factual claims from the provided content that need verification.

A factual claim is:
- A specific statement that can be verified as true or false
- Contains concrete information (numbers, dates, events, relationships)
- Is not an opinion, interpretation, or general observation

For each claim, provide:
- The exact text of the claim
- The source section it came from
- Confidence level that this is a verifiable fact
- Key entities and relationships mentioned

Provide your extraction in JSON format:
{
    "claims": [
        {
            "claim_text": "string",
            "source_section": "string",
            "confidence": 0.0-1.0,
            "entities": ["entity1", "entity2"],
            "claim_type": "statistical|temporal|causal|comparative|definitive"
        }
    ],
    "total_claims": int,
    "extraction_summary": "string"
}
"""),
            ("human", "Content to analyze for factual claims:\n\n{content}")
        ])

        try:
            # Convert content to string for analysis
            content_str = json.dumps(content_to_check, indent=2, default=str)

            chain = claims_extraction_prompt | self.llm | JsonOutputParser()
            extraction_result = await chain.ainvoke({
                "content": content_str
            })

            # Validate extraction
            if not extraction_result.get("claims"):
                return AgentResponse(
                    success=False,
                    data={},
                    error="No factual claims extracted from content"
                )

            # Store extraction in conversation history
            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Extracted {extraction_result['total_claims']} factual claims for verification"
            )

            return AgentResponse(
                success=True,
                data=extraction_result,
                messages=[
                    f"Successfully extracted {extraction_result['total_claims']} factual claims"
                ]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to extract claims: {str(e)}"
            )

    async def _verify_claims(self, context: AgentContext, claims: List[Dict]) -> Dict[str, Any]:
        """Verify extracted claims against source materials."""

        research_results = context.intermediate_results.get("research", {})
        sources = research_results.get("sources", [])

        if not sources:
            return {
                "verified_claims": [],
                "accuracy_score": 0.0,
                "verification_summary": "No source materials available for verification"
            }

        verification_results = {
            "verified_claims": [],
            "unverified_claims": [],
            "contradicted_claims": [],
            "verification_summary": {},
            "accuracy_score": 0.0
        }

        verified_count = 0
        contradicted_count = 0

        # Process each claim
        for claim_idx, claim in enumerate(claims):
            self._current_action = f"verifying_claim_{claim_idx + 1}"

            verification_result = await self._verify_single_claim(claim, sources)

            if verification_result["status"] == "verified":
                verification_results["verified_claims"].append({
                    "claim": claim,
                    "verification": verification_result
                })
                verified_count += 1
            elif verification_result["status"] == "contradicted":
                verification_results["contradicted_claims"].append({
                    "claim": claim,
                    "verification": verification_result
                })
                contradicted_count += 1
            else:
                verification_results["unverified_claims"].append({
                    "claim": claim,
                    "verification": verification_result
                })

            # Update progress
            await self._update_status(
                context.task_id,
                AgentStatus.EXECUTING,
                {
                    "claims_verified": claim_idx + 1,
                    "total_claims": len(claims),
                    "verified_count": verified_count
                }
            )

        # Calculate accuracy score
        total_claims = len(claims)
        if total_claims > 0:
            accuracy_score = (verified_count + (total_claims - verified_count - contradicted_count) * 0.5) / total_claims
        else:
            accuracy_score = 0.0

        verification_results["accuracy_score"] = accuracy_score
        verification_results["verification_summary"] = {
            "total_claims": total_claims,
            "verified": verified_count,
            "contradicted": contradicted_count,
            "unverified": total_claims - verified_count - contradicted_count,
            "accuracy_percentage": round(accuracy_score * 100, 2)
        }

        return AgentResponse(
            success=True,
            data=verification_results,
            messages=[
                f"Verified {verified_count} claims",
                f"Found {contradicted_count} contradicted claims",
                f"Overall accuracy score: {accuracy_score:.2f}"
            ]
        )

    async def _verify_single_claim(self, claim: Dict, sources: List[Dict]) -> Dict[str, Any]:
        """Verify a single claim against available sources."""

        claim_text = claim.get("claim_text", "")
        entities = claim.get("entities", [])

        verification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a fact verification expert. Verify the given claim against the provided source materials.

Your verification should:
1. Search for evidence supporting or contradicting the claim
2. Assess the reliability of matching sources
3. Determine if the claim is verified, contradicted, or unverified
4. Provide specific evidence citations

Provide your verification in JSON format:
{
    "status": "verified|contradicted|unverified",
    "confidence": 0.0-1.0,
    "supporting_evidence": [
        {
            "source_id": "string",
            "evidence_text": "string",
            "relevance_score": 0.0-1.0
        }
    ],
    "contradicting_evidence": [
        {
            "source_id": "string",
            "evidence_text": "string",
            "relevance_score": 0.0-1.0
        }
    ],
    "verification_reasoning": "string"
}
"""),
            ("human", "Claim to verify: {claim_text}\n\nKey entities: {entities}\n\nSource materials: {sources}")
        ])

        try:
            # Prepare sources for verification (limit to most relevant)
            relevant_sources = self._select_relevant_sources(sources, entities, claim_text)
            sources_str = json.dumps(relevant_sources, indent=2, default=str)

            chain = verification_prompt | self.llm | JsonOutputParser()
            verification = await chain.ainvoke({
                "claim_text": claim_text,
                "entities": json.dumps(entities),
                "sources": sources_str
            })

            return verification

        except Exception as e:
            self.logger.error(f"Failed to verify claim '{claim_text}': {str(e)}")
            return {
                "status": "unverified",
                "confidence": 0.0,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "verification_reasoning": f"Verification failed: {str(e)}"
            }

    def _select_relevant_sources(self, sources: List[Dict], entities: List[str], claim_text: str) -> List[Dict]:
        """Select most relevant sources for claim verification."""

        # Score sources based on entity overlap and claim text similarity
        scored_sources = []

        for source in sources:
            score = 0.0
            title = source.get("title", "").lower()
            snippet = source.get("snippet", "").lower()
            claim_lower = claim_text.lower()

            # Score based on entity mentions
            for entity in entities:
                if entity.lower() in title or entity.lower() in snippet:
                    score += 0.3

            # Score based on claim text overlap
            claim_words = set(claim_lower.split())
            title_words = set(title.split())
            snippet_words = set(snippet.split())

            word_overlap = len(claim_words.intersection(title_words)) + len(claim_words.intersection(snippet_words))
            score += word_overlap * 0.1

            # Add relevance score from research phase
            score += source.get("relevance_score", 0.0) * 0.2

            scored_sources.append((score, source))

        # Sort by score and return top sources
        scored_sources.sort(key=lambda x: x[0], reverse=True)
        return [source for _, source in scored_sources[:10]]  # Top 10 sources

    async def _generate_fact_check_report(self, context: AgentContext, verification_results: Dict) -> Dict[str, Any]:
        """Generate comprehensive fact check report."""

        report_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a fact checking report specialist. Generate a comprehensive fact checking report based on the verification results.

Your report should include:
1. Executive summary of fact checking results
2. Detailed analysis of verified and contradicted claims
3. Recommendations for content improvements
4. Overall accuracy assessment
5. Suggestions for additional verification if needed

Provide your report in JSON format:
{
    "executive_summary": "string",
    "accuracy_assessment": {
        "overall_score": 0.0-1.0,
        "score_breakdown": {
            "verified_percentage": 0.0-1.0,
            "contradicted_percentage": 0.0-1.0,
            "unverified_percentage": 0.0-1.0
        },
        "confidence_level": "high|medium|low"
    },
    "key_findings": [
        {
            "finding": "string",
            "impact": "high|medium|low",
            "recommendation": "string"
        }
    ],
    "content_improvements": [
        {
            "claim": "string",
            "suggested_correction": "string",
            "reason": "string"
        }
    ],
    "additional_verification_needed": ["string"]
}
"""),
            ("human", "Research topic: {research_topic}\n\nVerification results: {verification_results}")
        ])

        try:
            chain = report_prompt | self.llm | JsonOutputParser()
            report = await chain.ainvoke({
                "research_topic": context.research_topic,
                "verification_results": json.dumps(verification_results, indent=2, default=str)
            })

            # Store report in conversation history
            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Fact checking completed with {report['accuracy_assessment']['overall_score']:.2f} accuracy score"
            )

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate fact check report: {str(e)}")
            return {
                "executive_summary": "Fact checking report generation failed",
                "accuracy_assessment": {
                    "overall_score": 0.0,
                    "error": str(e)
                },
                "key_findings": [],
                "content_improvements": [],
                "additional_verification_needed": []
            }