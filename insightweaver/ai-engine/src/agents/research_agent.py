"""
Research Agent - Gathers information from various sources using web search, APIs, and databases
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import quote_plus

import aiohttp
import requests
from bs4 import BeautifulSoup
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.agents.base_agent import BaseAgent, AgentContext, AgentResponse, AgentStatus
from src.config.settings import settings
from src.tools.search_tools import GoogleSearchTool, ArXivSearchTool, WebScraperTool


class ResearchAgent(BaseAgent):
    """Research Agent responsible for gathering information from various sources."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        redis_service,
        max_iterations: int = None,
        max_retries: int = None
    ):
        super().__init__(
            name="ResearchAgent",
            llm=llm,
            redis_service=redis_service,
            max_iterations=max_iterations,
            max_retries=max_retries
        )

        # Initialize research tools
        self.google_search = GoogleSearchTool()
        self.arxiv_search = ArXivSearchTool()
        self.web_scraper = WebScraperTool()

        self.logger = logging.getLogger(__name__)
        self.search_results_cache = {}

    async def _execute_core(self, context: AgentContext, **kwargs) -> AgentResponse:
        """Execute the research agent's core logic."""
        self._current_action = "planning_research_strategy"

        try:
            # Step 1: Plan research strategy
            strategy_result = await self._plan_research_strategy(context)
            if not strategy_result.success:
                return strategy_result

            research_plan = strategy_result.data

            # Step 2: Execute information gathering
            self._current_action = "gathering_information"
            gathering_result = await self._gather_information(context, research_plan)
            if not gathering_result.success:
                return gathering_result

            gathered_data = gathering_result.data

            # Step 3: Validate and filter results
            self._current_action = "validating_results"
            validation_result = await self._validate_and_filter_results(context, gathered_data)
            if not validation_result.success:
                return validation_result

            filtered_results = validation_result.data

            # Step 4: Organize and summarize findings
            self._current_action = "organizing_findings"
            final_result = await self._organize_findings(context, filtered_results)

            # Update context with research results
            context.intermediate_results["research"] = final_result
            context.metadata["research_completed_at"] = time.time()
            context.metadata["sources_found"] = len(final_result.get("sources", []))

            return AgentResponse(
                success=True,
                data=final_result,
                messages=[
                    f"Research strategy planned with {len(research_plan.get('search_queries', []))} queries",
                    f"Gathered information from {len(gathered_data.get('sources', []))} sources",
                    f"Validated and filtered to {len(filtered_results.get('sources', []))} high-quality sources",
                    "Research findings organized and summarized"
                ],
                metadata={
                    "total_sources_found": len(gathered_data.get("sources", [])),
                    "high_quality_sources": len(filtered_results.get("sources", [])),
                    "search_queries_executed": len(research_plan.get("search_queries", [])),
                    "research_duration_minutes": (time.time() - context.created_at) / 60
                }
            )

        except Exception as e:
            self.logger.error(f"Research agent execution failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={},
                error=f"Research failed: {str(e)}"
            )

    async def _plan_research_strategy(self, context: AgentContext) -> AgentResponse:
        """Plan the research strategy based on the research objective."""

        strategy_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research strategist. Create a comprehensive research plan to gather information on the given topic.

Your research strategy should include:
1. Key search queries optimized for different search engines
2. Specific data types to look for (statistics, expert opinions, case studies, etc.)
3. Source quality criteria and reliability indicators
4. Information gaps that need to be addressed
5. Potential biases to watch for
6. Timeline for different research phases

Provide your strategy in JSON format with the following structure:
{
    "search_queries": [
        {
            "query": "string",
            "purpose": "string",
            "source_types": ["web", "academic", "news"],
            "priority": "HIGH|MEDIUM|LOW",
            "expected_results": "string"
        }
    ],
    "data_requirements": [
        {
            "type": "statistics|expert_opinion|case_study|trend_analysis|comparison",
            "description": "string",
            "importance": "HIGH|MEDIUM|LOW",
            "target_sources": ["string"]
        }
    ],
    "quality_criteria": {
            "reliability_indicators": ["string"],
            "bias_indicators": ["string"],
            "freshness_requirements": "string"
    },
    "research_phases": [
        {
            "phase": "string",
            "focus": "string",
            "queries": ["query_id"],
            "expected_duration_minutes": int
        }
    ],
    "information_gaps": ["string"],
    "potential_challenges": ["string"]
}
"""),
            ("human", "Research Objective: {research_topic}\n\nPlanning Context: {planning_context}")
        ])

        try:
            # Get planning context from previous agent results
            planning_context = context.intermediate_results.get("planning", {})

            chain = strategy_prompt | self.llm | JsonOutputParser()
            strategy = await chain.ainvoke({
                "research_topic": context.research_topic,
                "planning_context": json.dumps(planning_context, indent=2)
            })

            # Validate strategy structure
            if not strategy.get("search_queries"):
                return AgentResponse(
                    success=False,
                    data={},
                    error="Research strategy planning failed: no search queries generated"
                )

            # Store strategy in conversation history
            await self._add_to_conversation_history(
                context.task_id,
                "ai",
                f"Research strategy created with {len(strategy['search_queries'])} search queries"
            )

            return AgentResponse(
                success=True,
                data=strategy,
                messages=[
                    f"Created research strategy with {len(strategy['search_queries'])} search queries",
                    f"Identified {len(strategy['data_requirements'])} data requirements",
                    f"Planned {len(strategy['research_phases'])} research phases"
                ]
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                error=f"Failed to plan research strategy: {str(e)}"
            )

    async def _gather_information(self, context: AgentContext, strategy: Dict) -> AgentResponse:
        """Execute the information gathering based on the research strategy."""

        self.logger.info(f"Starting information gathering for task {context.task_id}")

        gathered_data = {
            "sources": [],
            "raw_data": {},
            "search_metadata": {},
            "gathering_timestamp": time.time()
        }

        search_queries = strategy.get("search_queries", [])
        research_phases = strategy.get("research_phases", [])

        # Execute searches for each phase
        for phase_idx, phase in enumerate(research_phases):
            self._current_action = f"executing_research_phase_{phase_idx + 1}"
            phase_focus = phase.get("focus", f"Phase {phase_idx + 1}")

            self.logger.info(f"Executing research phase: {phase_focus}")

            phase_queries = phase.get("queries", [])
            phase_results = []

            # Execute queries for this phase
            for query_idx, query_id in enumerate(phase_queries):
                if query_id < len(search_queries):
                    query_info = search_queries[query_id]

                    # Check if we've hit iteration limits
                    if query_idx >= self.max_iterations:
                        self.logger.warning(f"Reached max iterations limit at query {query_idx}")
                        break

                    try:
                        query_result = await self._execute_search_query(context, query_info)

                        if query_result.get("success", False):
                            phase_results.extend(query_result.get("results", []))

                            # Store in gathered data
                            gathered_data["sources"].extend(query_result.get("results", []))
                            gathered_data["raw_data"][query_info["query"]] = query_result

                            # Update progress
                            await self._update_status(
                                context.task_id,
                                AgentStatus.EXECUTING,
                                {
                                    "current_phase": phase_focus,
                                    "queries_completed": query_idx + 1,
                                    "total_queries": len(phase_queries),
                                    "sources_found": len(gathered_data["sources"])
                                }
                            )

                    except Exception as e:
                        self.logger.error(f"Failed to execute query {query_info['query']}: {str(e)}")
                        # Continue with next query rather than failing completely

            # Store phase metadata
            gathered_data["search_metadata"][f"phase_{phase_idx}"] = {
                "focus": phase_focus,
                "queries_executed": len(phase_results),
                "results_count": len(phase_results),
                "timestamp": time.time()
            }

            # Brief pause between phases to avoid rate limiting
            if phase_idx < len(research_phases) - 1:
                await asyncio.sleep(2)

        # Store gathering summary in conversation history
        await self._add_to_conversation_history(
            context.task_id,
            "ai",
            f"Information gathering completed. Found {len(gathered_data['sources'])} sources across {len(research_phases)} phases"
        )

        return AgentResponse(
            success=True,
            data=gathered_data,
            messages=[
                f"Executed {len(search_queries)} search queries across {len(research_phases)} phases",
                f"Gathered {len(gathered_data['sources'])} information sources",
                f"Research completed in {(time.time() - context.created_at) / 60:.1f} minutes"
            ]
        )

    async def _execute_search_query(self, context: AgentContext, query_info: Dict) -> Dict:
        """Execute a single search query using appropriate tools with streaming content processing."""

        query = query_info["query"]
        source_types = query_info.get("source_types", ["web"])
        purpose = query_info.get("purpose", "General research")

        self.logger.info(f"Executing search query: {query}")

        results = []
        search_errors = []

        # Execute different types of searches based on source_types
        for source_type in source_types:
            try:
                if source_type == "web":
                    web_results = await self.google_search.search(query, num_results=10)

                    # Process results with streaming content extraction
                    processed_results = await self._process_web_results_streaming(web_results, query)
                    results.extend(processed_results)

                elif source_type == "academic":
                    academic_results = await self.arxiv_search.search(query, max_results=5)

                    # Process academic results with streaming
                    processed_results = await self._process_academic_results_streaming(academic_results, query)
                    results.extend(processed_results)

                elif source_type == "news":
                    # Could integrate with news APIs here
                    pass

            except Exception as e:
                error_msg = f"Search failed for {source_type}: {str(e)}"
                self.logger.warning(error_msg)
                search_errors.append(error_msg)

        # Implement self-reflection: if no results, try alternative queries
        if not results and len(search_errors) > 0:
            self.logger.info(f"No results found for query '{query}', attempting alternatives")
            alternative_queries = await self._generate_alternative_queries(query)

            for alt_query in alternative_queries[:2]:  # Try up to 2 alternatives
                try:
                    alt_results = await self.google_search.search(alt_query, num_results=5)
                    if alt_results:
                        # Process with streaming as well
                        processed_alt_results = await self._process_web_results_streaming(alt_results, alt_query)
                        results.extend(processed_alt_results)
                        break  # Stop if we found some results
                except Exception as e:
                    self.logger.warning(f"Alternative query '{alt_query}' also failed: {str(e)}")

        return {
            "success": len(results) > 0,
            "query": query,
            "purpose": purpose,
            "results": results,
            "errors": search_errors,
            "timestamp": time.time()
        }

    async def _process_web_results_streaming(self, web_results: List[Dict], query: str) -> List[Dict]:
        """Process web search results with streaming content extraction."""
        processed_results = []

        for idx, result in enumerate(web_results):
            try:
                # Extract basic info
                url = result.get("url", result.get("link", ""))
                title = result.get("title", "No title")
                snippet = result.get("snippet", result.get("description", "No description"))

                # Stream content from URL if available
                full_content = ""
                if url and url.startswith(("http://", "https://")):
                    try:
                        full_content = await self._stream_content_from_url(url)
                    except Exception as e:
                        self.logger.warning(f"Failed to stream content from {url}: {str(e)}")
                        full_content = snippet  # Fallback to snippet

                # Process content in chunks if it's too long
                if len(full_content) > settings.MAX_CONTENT_LENGTH:
                    content_chunks = self._chunk_content(full_content)
                    summarized_content = await self._summarize_chunks_streaming(content_chunks, query)
                else:
                    summarized_content = full_content if full_content else snippet

                # Format result with processed content
                formatted_result = self._format_search_result(
                    result_id=f"web_{idx}_{hash(query) % 10000}",
                    source_type="web",
                    title=title,
                    url=url,
                    snippet=snippet,
                    full_content=summarized_content,
                    query=query,
                    position=idx + 1,
                    original_data=result
                )

                processed_results.append(formatted_result)

            except Exception as e:
                self.logger.error(f"Failed to process web result {idx}: {str(e)}")
                # Add basic result without content processing
                formatted_result = self._format_search_result(
                    result_id=f"web_{idx}_{hash(query) % 10000}",
                    source_type="web",
                    title=result.get("title", "No title"),
                    url=result.get("url", result.get("link", "")),
                    snippet=result.get("snippet", result.get("description", "No description")),
                    full_content="Content processing failed",
                    query=query,
                    position=idx + 1,
                    original_data=result
                )
                processed_results.append(formatted_result)

        return processed_results

    async def _process_academic_results_streaming(self, academic_results: List[Dict], query: str) -> List[Dict]:
        """Process academic search results with streaming content extraction."""
        processed_results = []

        for idx, result in enumerate(academic_results):
            try:
                # Extract academic-specific fields
                title = result.get("title", "No title")
                abstract = result.get("abstract", result.get("summary", "No abstract"))
                authors = result.get("authors", [])
                url = result.get("url", result.get("pdf_url", ""))
                published_date = result.get("published", "")

                # For academic papers, we might want to fetch the full text or additional details
                full_content = abstract  # Start with abstract

                # Try to get additional content if URL is available
                if url and url.startswith(("http://", "https://")):
                    try:
                        additional_content = await self._stream_content_from_url(url)
                        if len(additional_content) > len(abstract):
                            full_content = additional_content
                    except Exception as e:
                        self.logger.debug(f"Could not fetch additional content from {url}: {str(e)}")

                # Process content if needed
                if len(full_content) > settings.MAX_CONTENT_LENGTH:
                    content_chunks = self._chunk_content(full_content)
                    summarized_content = await self._summarize_chunks_streaming(content_chunks, query)
                else:
                    summarized_content = full_content

                # Format academic result
                formatted_result = self._format_search_result(
                    result_id=f"academic_{idx}_{hash(query) % 10000}",
                    source_type="academic",
                    title=title,
                    url=url,
                    snippet=abstract[:500],  # Truncated abstract as snippet
                    full_content=summarized_content,
                    query=query,
                    position=idx + 1,
                    original_data=result,
                    metadata={
                        "authors": authors,
                        "published_date": published_date,
                        "content_type": "academic_paper"
                    }
                )

                processed_results.append(formatted_result)

            except Exception as e:
                self.logger.error(f"Failed to process academic result {idx}: {str(e)}")
                # Add basic result
                formatted_result = self._format_search_result(
                    result_id=f"academic_{idx}_{hash(query) % 10000}",
                    source_type="academic",
                    title=result.get("title", "No title"),
                    url=result.get("url", result.get("pdf_url", "")),
                    snippet=result.get("abstract", result.get("summary", "No abstract"))[:500],
                    full_content="Content processing failed",
                    query=query,
                    position=idx + 1,
                    original_data=result
                )
                processed_results.append(formatted_result)

        return processed_results

    async def _stream_content_from_url(self, url: str, max_length: int = 50000) -> str:
        """Stream content from URL with chunked processing to avoid token overflow."""
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_chunks = []
                        total_length = 0

                        # Stream content in chunks
                        async for chunk in response.content.iter_chunked(8192):  # 8KB chunks
                            chunk_text = chunk.decode('utf-8', errors='ignore')
                            content_chunks.append(chunk_text)
                            total_length += len(chunk_text)

                            # Stop if we've reached max length
                            if total_length >= max_length:
                                break

                        full_content = ''.join(content_chunks)

                        # If content is HTML, extract text
                        if '<html' in full_content.lower() or '<body' in full_content.lower():
                            soup = BeautifulSoup(full_content, 'html.parser')
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.decompose()
                            full_content = soup.get_text()

                        return full_content.strip()
                    else:
                        raise Exception(f"HTTP {response.status}: Failed to fetch content")

        except Exception as e:
            self.logger.warning(f"Failed to stream content from {url}: {str(e)}")
            return f"Content unavailable: {str(e)}"

    def _chunk_content(self, content: str, chunk_size: int = 3000) -> List[str]:
        """Split content into manageable chunks for processing."""
        words = content.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    async def _summarize_chunks_streaming(self, chunks: List[str], query_context: str) -> str:
        """Summarize content chunks using Map-Reduce approach to prevent token overflow."""
        if not chunks:
            return ""

        if len(chunks) == 1:
            return chunks[0]

        try:
            # Map phase: Summarize each chunk
            chunk_summaries = []

            for i, chunk in enumerate(chunks):
                self._current_action = f"summarizing_chunk_{i+1}"

                summary = await self._summarize_single_chunk(chunk, query_context)
                if summary:
                    chunk_summaries.append(summary)

                # Brief pause to avoid overwhelming the LLM
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.1)

            # Reduce phase: Combine summaries
            if len(chunk_summaries) > 1:
                combined_summary = await self._combine_summaries(chunk_summaries, query_context)
                return combined_summary
            elif chunk_summaries:
                return chunk_summaries[0]
            else:
                return "Summary generation failed"

        except Exception as e:
            self.logger.error(f"Failed to summarize chunks: {str(e)}")
            # Fallback: return first chunk truncated
            return chunks[0][:5000] if chunks else ""

    async def _summarize_single_chunk(self, chunk: str, query_context: str) -> str:
        """Summarize a single chunk of content."""
        try:
            summary_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a content summarization expert. Create a concise summary of the provided text chunk that preserves key information relevant to the research query.

Focus on:
- Key facts and findings
- Important statistics or data
- Relevant entities and relationships
- Unique insights

Keep the summary focused and informative, removing redundant information.
"""),
                ("human", "Research Query Context: {query_context}\n\nText Chunk to Summarize:\n{chunk_text}")
            ])

            # Truncate chunk if it's too long for the prompt
            max_chunk_length = 6000  # Leave room for prompt and response
            if len(chunk) > max_chunk_length:
                chunk = chunk[:max_chunk_length] + "..."

            chain = summary_prompt | self.llm
            summary = await chain.ainvoke({
                "query_context": query_context,
                "chunk_text": chunk
            })

            return summary.content if hasattr(summary, 'content') else str(summary)

        except Exception as e:
            self.logger.warning(f"Failed to summarize chunk: {str(e)}")
            # Return truncated chunk as fallback
            return chunk[:2000] + "..." if len(chunk) > 2000 else chunk

    async def _combine_summaries(self, summaries: List[str], query_context: str) -> str:
        """Combine multiple summaries into a coherent final summary."""
        try:
            combine_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a summary synthesis expert. Combine the provided summaries into a single, coherent summary that:

1. Preserves all unique and important information
2. Eliminates redundancy
3. Maintains logical flow
4. Highlights key findings most relevant to the research query
5. Preserves citations and source information when available

The final summary should be comprehensive yet concise.
"""),
                ("human", "Research Query Context: {query_context}\n\nSummaries to Combine:\n{summaries_text}")
            ])

            # Join summaries with clear separators
            summaries_text = "\n\n--- NEXT SUMMARY ---\n\n".join(summaries)

            # Truncate if too long
            max_summaries_length = 8000
            if len(summaries_text) > max_summaries_length:
                summaries_text = summaries_text[:max_summaries_length] + "..."

            chain = combine_prompt | self.llm
            final_summary = await chain.ainvoke({
                "query_context": query_context,
                "summaries_text": summaries_text
            })

            return final_summary.content if hasattr(final_summary, 'content') else str(final_summary)

        except Exception as e:
            self.logger.warning(f"Failed to combine summaries: {str(e)}")
            # Return first few summaries as fallback
            return " ".join(summaries[:3])

    def _format_search_result(self, result_id: str, source_type: str, title: str, url: str,
                            snippet: str, full_content: str, query: str, position: int,
                            original_data: Dict, metadata: Optional[Dict] = None) -> Dict:
        """Format search result with processed content."""
        formatted_result = {
            "id": result_id,
            "source_type": source_type,
            "title": title,
            "url": url,
            "snippet": snippet,
            "full_content": full_content[:10000],  # Limit stored content
            "relevance_score": original_data.get("relevance_score", 0.5),
            "retrieved_at": time.time(),
            "query_used": query,
            "position": position,
            "content_processed": True,
            "metadata": {
                "position": position,
                "source_specific_data": original_data,
                "processing_timestamp": time.time()
            }
        }

        if metadata:
            formatted_result["metadata"].update(metadata)

        return formatted_result

    async def _generate_alternative_queries(self, original_query: str) -> List[str]:
        """Generate alternative search queries when the original fails."""

        alternative_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a search query optimization expert. When a search query returns no results, generate alternative queries that might yield better results.

Consider:
1. Synonyms and related terms
2. Broader or more specific terms
3. Different phrasings
4. Removing potentially problematic terms
5. Adding context or qualifiers

Provide 3-5 alternative queries in JSON format:
{"alternative_queries": ["query1", "query2", "query3"]}
"""),
            ("human", "Original failed query: {original_query}")
        ])

        try:
            chain = alternative_prompt | self.llm | JsonOutputParser()
            alternatives = await chain.ainvoke({"original_query": original_query})
            return alternatives.get("alternative_queries", [])

        except Exception as e:
            self.logger.error(f"Failed to generate alternative queries: {str(e)}")
            # Return basic alternatives as fallback
            return [
                original_query.replace(" ", " OR "),
                f"\"{original_query}\"",
                original_query.split()[0]  # Just the first word
            ]

    def _format_search_results(self, raw_results: List[Dict], source_type: str, query: str) -> List[Dict]:
        """Format search results into a standardized structure."""

        formatted_results = []

        for idx, result in enumerate(raw_results):
            formatted_result = {
                "id": f"{source_type}_{idx}_{hash(query) % 10000}",
                "source_type": source_type,
                "title": result.get("title", "No title"),
                "url": result.get("url", result.get("link", "")),
                "snippet": result.get("snippet", result.get("description", "No description")),
                "relevance_score": result.get("relevance_score", 0.5),
                "retrieved_at": time.time(),
                "query_used": query,
                "metadata": {
                    "position": idx + 1,
                    "source_specific_data": result
                }
            }

            formatted_results.append(formatted_result)

        return formatted_results

    async def _validate_and_filter_results(self, context: AgentContext, gathered_data: Dict) -> AgentResponse:
        """Validate and filter the gathered results for quality and relevance."""

        self.logger.info("Starting result validation and filtering")

        sources = gathered_data.get("sources", [])
        strategy = context.intermediate_results.get("planning", {})
        quality_criteria = strategy.get("quality_criteria", {})

        validated_sources = []
        validation_stats = {
            "total_sources": len(sources),
            "passed_validation": 0,
            "failed_validation": 0,
            "filtered_duplicates": 0,
            "average_relevance_score": 0
        }

        # Remove duplicates based on URL and title similarity
        unique_sources = self._remove_duplicates(sources)
        validation_stats["filtered_duplicates"] = len(sources) - len(unique_sources)

        # Validate each unique source
        relevance_scores = []

        for source in unique_sources:
            validation_result = await self._validate_source(source, quality_criteria, context)

            if validation_result["valid"]:
                # Update source with validation metadata
                source["validation_metadata"] = validation_result
                source["relevance_score"] = validation_result["relevance_score"]
                validated_sources.append(source)
                validation_stats["passed_validation"] += 1
                relevance_scores.append(validation_result["relevance_score"])
            else:
                validation_stats["failed_validation"] += 1

        # Calculate average relevance score
        if relevance_scores:
            validation_stats["average_relevance_score"] = sum(relevance_scores) / len(relevance_scores)

        # Sort by relevance score
        validated_sources.sort(key=lambda x: x["relevance_score"], reverse=True)

        filtered_data = gathered_data.copy()
        filtered_data["sources"] = validated_sources
        filtered_data["validation_stats"] = validation_stats
        filtered_data["filtered_at"] = time.time()

        await self._add_to_conversation_history(
            context.task_id,
            "ai",
            f"Validation completed: {validation_stats['passed_validation']}/{validation_stats['total_sources']} sources passed validation"
        )

        return AgentResponse(
            success=True,
            data=filtered_data,
            messages=[
                f"Validated {validation_stats['total_sources']} sources",
                f"{validation_stats['passed_validation']} sources passed quality checks",
                f"Removed {validation_stats['filtered_duplicates']} duplicate sources",
                f"Average relevance score: {validation_stats['average_relevance_score']:.2f}"
            ]
        )

    def _remove_duplicates(self, sources: List[Dict]) -> List[Dict]:
        """Remove duplicate sources based on URL and title similarity."""

        unique_sources = []
        seen_urls = set()
        seen_titles = set()

        for source in sources:
            url = source.get("url", "").lower().strip()
            title = source.get("title", "").lower().strip()

            # Normalize URL (remove common variations)
            normalized_url = url.replace("https://", "").replace("http://", "").split("?")[0]

            # Simple duplicate detection
            is_duplicate = False

            if normalized_url in seen_urls:
                is_duplicate = True
            elif title in seen_titles:
                is_duplicate = True
            elif len(title) > 10 and any(self._title_similarity(title, seen_title) > 0.8 for seen_title in seen_titles):
                is_duplicate = True

            if not is_duplicate:
                unique_sources.append(source)
                seen_urls.add(normalized_url)
                seen_titles.add(title)

        return unique_sources

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (simple implementation)."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def _validate_source(self, source: Dict, quality_criteria: Dict, context: AgentContext) -> Dict:
        """Validate a single source for quality and relevance."""

        validation_result = {
            "valid": True,
            "relevance_score": source.get("relevance_score", 0.5),
            "quality_score": 0.5,
            "issues": [],
            "strengths": []
        }

        # Check URL validity
        url = source.get("url", "")
        if not url or not url.startswith(("http://", "https://")):
            validation_result["valid"] = False
            validation_result["issues"].append("Invalid or missing URL")
            return validation_result

        # Check content quality indicators
        title = source.get("title", "")
        snippet = source.get("snippet", "")

        if len(title) < 5:
            validation_result["issues"].append("Title too short")
            validation_result["quality_score"] -= 0.1

        if len(snippet) < 20:
            validation_result["issues"].append("Snippet too short")
            validation_result["quality_score"] -= 0.1

        # Check for reliability indicators
        reliability_indicators = quality_criteria.get("reliability_indicators", [])
        for indicator in reliability_indicators:
            if indicator.lower() in url.lower() or indicator.lower() in title.lower():
                validation_result["strengths"].append(f"Contains reliability indicator: {indicator}")
                validation_result["quality_score"] += 0.1

        # Check for bias indicators
        bias_indicators = quality_criteria.get("bias_indicators", [])
        for indicator in bias_indicators:
            if indicator.lower() in title.lower() or indicator.lower() in snippet.lower():
                validation_result["issues"].append(f"Potential bias indicator: {indicator}")
                validation_result["quality_score"] -= 0.1

        # Assess relevance to research topic
        research_topic = context.research_topic.lower()
        title_lower = title.lower()
        snippet_lower = snippet.lower()

        relevance_factors = [
            1.0 if research_topic in title_lower else 0.0,
            0.5 if research_topic in snippet_lower else 0.0,
            len([word for word in research_topic.split() if word in title_lower]) / len(research_topic.split()),
            len([word for word in research_topic.split() if word in snippet_lower]) / len(research_topic.split())
        ]

        validation_result["relevance_score"] = max(relevance_factors)

        # Final validation decision
        if validation_result["quality_score"] < 0.3 or len(validation_result["issues"]) > 3:
            validation_result["valid"] = False

        # Ensure scores are within bounds
        validation_result["relevance_score"] = max(0.0, min(1.0, validation_result["relevance_score"]))
        validation_result["quality_score"] = max(0.0, min(1.0, validation_result["quality_score"]))

        return validation_result

    async def _organize_findings(self, context: AgentContext, filtered_data: Dict) -> Dict:
        """Organize and summarize the research findings."""

        self.logger.info("Organizing research findings")

        sources = filtered_data.get("sources", [])
        validation_stats = filtered_data.get("validation_stats", {})

        # Group sources by type and relevance
        organized_findings = {
            "executive_summary": await self._generate_executive_summary(sources, context),
            "sources_by_type": self._group_sources_by_type(sources),
            "key_information": await self._extract_key_information(sources, context),
            "source_quality_analysis": validation_stats,
            "research_metadata": {
                "total_sources": len(sources),
                "research_topic": context.research_topic,
                "completed_at": time.time(),
                "organization_method": "relevance_and_type_based"
            }
        }

        # Add source categorization
        organized_findings["categorized_sources"] = await self._categorize_sources(sources, context)

        await self._add_to_conversation_history(
            context.task_id,
            "ai",
            f"Research findings organized: {len(sources)} sources categorized and summarized"
        )

        return organized_findings

    async def _generate_executive_summary(self, sources: List[Dict], context: AgentContext) -> str:
        """Generate an executive summary of the research findings."""

        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research summarization expert. Create a concise executive summary of the research findings.

The summary