"""
ChromaDB service for long-term memory and vector storage
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

import chromadb
from chromadb.config import Settings
from chromadb.api.types import Documents, Embeddings, IDs, Where, WhereDocument
import re
from typing import Set

from src.config.settings import settings


class ChromaService:
    """Service for interacting with ChromaDB for long-term memory and vector similarity search."""

    def __init__(self):
        self.client = None
        self.collections: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        try:
            # Initialize ChromaDB client
            if settings.CHROMA_HOST and settings.CHROMA_PORT:
                # Use HTTP client for remote ChromaDB
                self.client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            else:
                # Use persistent client for local storage
                self.client = chromadb.PersistentClient(
                    path=settings.CHROMA_PERSIST_DIRECTORY,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )

            # Initialize default collections
            await self._initialize_collections()

            self._initialized = True
            self.logger.info("ChromaDB service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise

    async def _initialize_collections(self) -> None:
        """Initialize default collections for different types of memories."""
        try:
            # Research memories collection
            research_collection = self.client.get_or_create_collection(
                name="research_memories",
                metadata={"description": "Long-term storage for research results and insights"}
            )
            self.collections["research_memories"] = research_collection

            # Conversation memories collection
            conversation_collection = self.client.get_or_create_collection(
                name="conversation_memories",
                metadata={"description": "Long-term storage for conversation history and context"}
            )
            self.collections["conversation_memories"] = conversation_collection

            # Agent memories collection
            agent_collection = self.client.get_or_create_collection(
                name="agent_memories",
                metadata={"description": "Long-term storage for agent experiences and learnings"}
            )
            self.collections["agent_memories"] = agent_collection

            # User preferences collection
            preferences_collection = self.client.get_or_create_collection(
                name="user_preferences",
                metadata={"description": "Long-term storage for user preferences and patterns"}
            )
            self.collections["user_preferences"] = preferences_collection

            self.logger.info(f"Initialized {len(self.collections)} ChromaDB collections")

        except Exception as e:
            self.logger.error(f"Failed to initialize collections: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check ChromaDB connection health."""
        try:
            if not self._initialized or not self.client:
                return {"status": "uninitialized", "error": "Service not initialized"}

            # Test basic operations
            test_collection = self.client.get_or_create_collection("health_test")
            test_collection.add(
                documents=["health test document"],
                ids=["health_test_1"]
            )
            results = test_collection.query(
                query_texts=["health test"],
                n_results=1
            )
            test_collection.delete(ids=["health_test_1"])

            # Get collection stats
            collection_stats = {}
            for name, collection in self.collections.items():
                try:
                    count = collection.count()
                    collection_stats[name] = {"document_count": count}
                except Exception as e:
                    collection_stats[name] = {"error": str(e)}

            return {
                "status": "healthy",
                "initialized": True,
                "collections": collection_stats,
                "total_documents": sum(stats.get("document_count", 0) for stats in collection_stats.values())
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def get_collection(self, collection_name: str) -> Any:
        """Get a ChromaDB collection by name."""
        try:
            if collection_name in self.collections:
                return self.collections[collection_name]

            # Try to get or create the collection
            collection = self.client.get_or_create_collection(collection_name)
            self.collections[collection_name] = collection
            return collection

        except Exception as e:
            self.logger.error(f"Failed to get collection {collection_name}: {str(e)}")
            raise

    async def add_document(
        self,
        collection_name: str,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> bool:
        """Add a document to a collection."""
        try:
            collection = await self.get_collection(collection_name)

            # Prepare metadata
            if metadata is None:
                metadata = {}

            metadata["added_at"] = asyncio.get_event_loop().time()
            metadata["content_length"] = len(content)

            # Add document
            collection.add(
                ids=[document_id],
                documents=[content],
                metadatas=[metadata],
                embeddings=[embedding] if embedding else None
            )

            self.logger.debug(f"Added document {document_id} to collection {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add document {document_id} to {collection_name}: {str(e)}")
            return False

    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """Add multiple documents to a collection."""
        try:
            collection = await self.get_collection(collection_name)

            # Prepare metadatas if not provided
            if metadatas is None:
                metadatas = []
                for i, doc in enumerate(documents):
                    metadatas.append({
                        "added_at": asyncio.get_event_loop().time(),
                        "content_length": len(doc),
                        "index": i
                    })

            # Add documents
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )

            self.logger.debug(f"Added {len(documents)} documents to collection {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add documents to {collection_name}: {str(e)}")
            return False

    async def query_similar(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Where] = None,
        where_document: Optional[WhereDocument] = None,
        include_embeddings: bool = False,
        include_metadatas: bool = True,
        use_hybrid_search: bool = True
    ) -> Dict[str, Any]:
        """Query for similar documents using hybrid search (semantic + keyword) with reranking."""
        try:
            collection = await self.get_collection(collection_name)

            if use_hybrid_search:
                # Perform hybrid search
                hybrid_results = await self._perform_hybrid_search(
                    collection, query_text, n_results * 2, where, where_document, include_embeddings, include_metadatas
                )

                # Apply cross-encoder reranking
                reranked_results = await self._rerank_results(query_text, hybrid_results, n_results)

                return reranked_results
            else:
                # Use original semantic search
                return await self._semantic_search_only(
                    collection, query_text, n_results, where, where_document, include_embeddings, include_metadatas
                )

        except Exception as e:
            self.logger.error(f"Failed to query collection {collection_name}: {str(e)}")
            return {"query": query_text, "results": [], "total_results": 0, "error": str(e)}

    async def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        try:
            collection = await self.get_collection(collection_name)

            results = collection.get(
                ids=[document_id],
                include=["documents", "metadatas", "embeddings"]
            )

            if results["ids"] and len(results["ids"]) > 0:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0] if results["documents"] else None,
                    "metadata": results["metadatas"][0] if results["metadatas"] else None,
                    "embedding": results["embeddings"][0] if results["embeddings"] else None
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to get document {document_id} from {collection_name}: {str(e)}")
            return None

    async def update_document(
        self,
        collection_name: str,
        document_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> bool:
        """Update an existing document."""
        try:
            collection = await self.get_collection(collection_name)

            # Get current document
            current_doc = await self.get_document(collection_name, document_id)
            if not current_doc:
                self.logger.error(f"Document {document_id} not found in {collection_name}")
                return False

            # Prepare updated data
            updated_content = content if content is not None else current_doc["document"]
            updated_metadata = metadata if metadata is not None else current_doc["metadata"]

            if updated_metadata is None:
                updated_metadata = {}

            updated_metadata["updated_at"] = asyncio.get_event_loop().time()
            updated_metadata["content_length"] = len(updated_content) if updated_content else 0

            # Update document (ChromaDB requires delete + add for updates)
            collection.delete(ids=[document_id])
            collection.add(
                ids=[document_id],
                documents=[updated_content] if updated_content else None,
                metadatas=[updated_metadata] if updated_metadata else None,
                embeddings=[embedding] if embedding else None
            )

            self.logger.debug(f"Updated document {document_id} in collection {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update document {document_id} in {collection_name}: {str(e)}")
            return False

    async def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Delete a document from a collection."""
        try:
            collection = await self.get_collection(collection_name)
            collection.delete(ids=[document_id])

            self.logger.debug(f"Deleted document {document_id} from collection {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id} from {collection_name}: {str(e)}")
            return False

    async def delete_documents(self, collection_name: str, where: Where) -> int:
        """Delete documents matching criteria."""
        try:
            collection = await self.get_collection(collection_name)
            result = collection.delete(where=where)

            deleted_count = len(result) if result else 0
            self.logger.debug(f"Deleted {deleted_count} documents from collection {collection_name}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete documents from {collection_name}: {str(e)}")
            return 0

    async def search_by_metadata(
        self,
        collection_name: str,
        metadata_filter: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search documents by metadata criteria."""
        try:
            collection = await self.get_collection(collection_name)

            results = collection.get(
                where=metadata_filter,
                limit=limit,
                include=["documents", "metadatas"]
            )

            formatted_results = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    formatted_results.append({
                        "id": results["ids"][i],
                        "document": results["documents"][i] if results["documents"] else None,
                        "metadata": results["metadatas"][i] if results["metadatas"] else None
                    })

            return formatted_results

        except Exception as e:
            self.logger.error(f"Failed to search by metadata in {collection_name}: {str(e)}")
            return []

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection."""
        try:
            collection = await self.get_collection(collection_name)

            count = collection.count()
            collection_info = collection.name
            collection_metadata = collection.metadata

            return {
                "name": collection_info,
                "document_count": count,
                "metadata": collection_metadata,
                "status": "healthy"
            }

        except Exception as e:
            return {
                "name": collection_name,
                "document_count": 0,
                "error": str(e),
                "status": "error"
            }

    async def create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a new collection."""
        try:
            collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata or {}
            )
            self.collections[collection_name] = collection

            self.logger.info(f"Created new collection: {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]

            self.logger.info(f"Deleted collection: {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            return False

    async def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections with basic info."""
        try:
            collections = self.client.list_collections()
            collection_info = []

            for collection in collections:
                try:
                    count = collection.count()
                    collection_info.append({
                        "name": collection.name,
                        "document_count": count,
                        "metadata": collection.metadata
                    })
                except Exception as e:
                    collection_info.append({
                        "name": collection.name,
                        "error": str(e)
                    })

            return collection_info

        except Exception as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            return []

    async def reset_database(self) -> bool:
        """Reset the entire database. Use with extreme caution!"""
        try:
            self.client.reset()
            self.collections.clear()
            await self._initialize_collections()

            self.logger.warning("ChromaDB database reset")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset database: {str(e)}")
            return False

    async def _perform_hybrid_search(
        self,
        collection: Any,
        query_text: str,
        n_results: int,
        where: Optional[Where] = None,
        where_document: Optional[WhereDocument] = None,
        include_embeddings: bool = False,
        include_metadatas: bool = True
    ) -> Dict[str, Any]:
        """Perform hybrid search combining semantic and keyword search."""
        try:
            # Perform semantic search
            semantic_results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"] + (["embeddings"] if include_embeddings else [])
            )

            # Perform keyword search
            keyword_results = await self._keyword_search(
                collection, query_text, n_results, where, include_metadatas
            )

            # Combine and deduplicate results
            combined_results = self._merge_search_results(semantic_results, keyword_results)

            return combined_results

        except Exception as e:
            self.logger.error(f"Hybrid search failed: {str(e)}")
            return {"query": query_text, "results": [], "total_results": 0, "error": str(e)}

    async def _keyword_search(
        self,
        collection: Any,
        query_text: str,
        n_results: int,
        where: Optional[Where] = None,
        include_metadatas: bool = True
    ) -> Dict[str, Any]:
        """Perform keyword-based search using text analysis."""
        try:
            # Extract keywords from query
            keywords = self._extract_keywords(query_text)

            # Get all documents (limited for performance)
            all_docs = collection.get(
                where=where,
                include=["documents", "metadatas"]
            )

            if not all_docs["ids"]:
                return {"query": query_text, "results": [], "total_results": 0}

            # Score documents based on keyword overlap
            scored_docs = []
            for i, doc_id in enumerate(all_docs["ids"]):
                document = all_docs["documents"][i] if all_docs["documents"] else ""
                metadata = all_docs["metadatas"][i] if all_docs["metadatas"] and include_metadatas else None

                # Calculate keyword overlap score
                score = self._calculate_keyword_score(document, keywords)

                if score > 0:  # Only include documents with some keyword match
                    scored_docs.append({
                        "id": doc_id,
                        "document": document,
                        "metadata": metadata,
                        "keyword_score": score
                    })

            # Sort by keyword score and return top results
            scored_docs.sort(key=lambda x: x["keyword_score"], reverse=True)
            top_docs = scored_docs[:n_results]

            # Format results
            formatted_results = {
                "query": query_text,
                "results": [],
                "total_results": len(top_docs)
            }

            for doc in top_docs:
                result_item = {
                    "id": doc["id"],
                    "document": doc["document"],
                    "metadata": doc["metadata"],
                    "keyword_score": doc["keyword_score"],
                    "search_type": "keyword"
                }
                formatted_results["results"].append(result_item)

            return formatted_results

        except Exception as e:
            self.logger.error(f"Keyword search failed: {str(e)}")
            return {"query": query_text, "results": [], "total_results": 0, "error": str(e)}

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might", "must", "can", "this", "that",
            "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"
        }

        # Clean and tokenize text
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = set(word for word in words if word not in stop_words)

        return keywords

    def _calculate_keyword_score(self, document: str, keywords: Set[str]) -> float:
        """Calculate keyword overlap score between document and query keywords."""
        if not keywords or not document:
            return 0.0

        doc_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', document.lower()))

        # Calculate Jaccard similarity
        intersection = keywords.intersection(doc_words)
        union = keywords.union(doc_words)

        if not union:
            return 0.0

        jaccard_score = len(intersection) / len(union)

        # Boost score based on keyword frequency in document
        keyword_frequency = sum(1 for word in keywords if word in document.lower())
        frequency_bonus = min(0.3, keyword_frequency * 0.1)

        return jaccard_score + frequency_bonus

    def _merge_search_results(self, semantic_results: Dict, keyword_results: Dict) -> Dict[str, Any]:
        """Merge semantic and keyword search results."""
        merged_results = {
            "query": semantic_results.get("query", ""),
            "results": [],
            "total_results": 0
        }

        # Create a map of document IDs to avoid duplicates
        seen_ids = {}

        # Add semantic results with higher initial weight
        if semantic_results.get("results"):
            for result in semantic_results["results"]:
                doc_id = result.get("id")
                if doc_id not in seen_ids:
                    result["search_type"] = "semantic"
                    result["combined_score"] = (result.get("similarity_score", 0.0) or 0.0) * 0.7
                    merged_results["results"].append(result)
                    seen_ids[doc_id] = len(merged_results["results"]) - 1

        # Add keyword results, updating scores for existing documents
        if keyword_results.get("results"):
            for result in keyword_results["results"]:
                doc_id = result.get("id")
                keyword_score = result.get("keyword_score", 0.0) * 0.3  # Lower weight for keyword

                if doc_id in seen_ids:
                    # Update existing result with keyword score
                    existing_idx = seen_ids[doc_id]
                    merged_results["results"][existing_idx]["combined_score"] += keyword_score
                    merged_results["results"][existing_idx]["search_type"] = "hybrid"
                else:
                    # Add new result
                    result["combined_score"] = keyword_score
                    merged_results["results"].append(result)

        # Sort by combined score
        merged_results["results"].sort(key=lambda x: x.get("combined_score", 0.0), reverse=True)
        merged_results["total_results"] = len(merged_results["results"])

        return merged_results

    async def _rerank_results(
        self,
        query_text: str,
        search_results: Dict,
        n_results: int
    ) -> Dict[str, Any]:
        """Apply cross-encoder reranking to search results."""
        try:
            # Simple reranking based on relevance heuristics
            # In production, this would use a cross-encoder model
            results = search_results.get("results", [])

            for result in results:
                # Calculate additional relevance factors
                relevance_factors = self._calculate_relevance_factors(query_text, result)
                result["rerank_score"] = result.get("combined_score", 0.0) + relevance_factors

            # Sort by rerank score
            results.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

            # Return top N results
            reranked_results = search_results.copy()
            reranked_results["results"] = results[:n_results]
            reranked_results["total_results"] = len(reranked_results["results"])

            return reranked_results

        except Exception as e:
            self.logger.error(f"Reranking failed: {str(e)}")
            return search_results

    def _calculate_relevance_factors(self, query_text: str, result: Dict) -> float:
        """Calculate additional relevance factors for reranking."""
        factors = 0.0
        document = result.get("document", "")
        metadata = result.get("metadata", {})

        # Factor 1: Query term proximity
        if query_text.lower() in document.lower():
            factors += 0.1

        # Factor 2: Document length appropriateness
        doc_length = len(document.split())
        if 100 <= doc_length <= 1000:  # Optimal length range
            factors += 0.05

        # Factor 3: Metadata quality indicators
        if metadata:
            if metadata.get("relevance_score"):
                factors += metadata["relevance_score"] * 0.1
            if metadata.get("source_type") in ["academic", "official"]:
                factors += 0.05

        # Factor 4: Freshness (if timestamp available)
        if metadata and metadata.get("timestamp"):
            # Boost newer documents slightly
            factors += 0.02

        return factors

    async def _semantic_search_only(
        self,
        collection: Any,
        query_text: str,
        n_results: int,
        where: Optional[Where] = None,
        where_document: Optional[WhereDocument] = None,
        include_embeddings: bool = False,
        include_metadatas: bool = True
    ) -> Dict[str, Any]:
        """Perform semantic search only (original implementation)."""
        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"] + (["embeddings"] if include_embeddings else [])
            )

            # Format results
            formatted_results = {
                "query": query_text,
                "results": [],
                "total_results": len(results["ids"][0]) if results["ids"] else 0
            }

            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    result_item = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i] if results["documents"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] and include_metadatas else None,
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "similarity_score": 1.0 - (results["distances"][0][i] if results["distances"] else 0.0)
                    }

                    if include_embeddings and results["embeddings"]:
                        result_item["embedding"] = results["embeddings"][0][i]

                    formatted_results["results"].append(result_item)

            return formatted_results

        except Exception as e:
            self.logger.error(f"Semantic search failed: {str(e)}")
            return {"query": query_text, "results": [], "total_results": 0, "error": str(e)}

    # Memory-specific operations
    async def store_research_memory(
        self,
        task_id: str,
        category: str,
        content: Union[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store research-related memory."""
        try:
            if isinstance(content, dict):
                content = json.dumps(content, default=str)

            document_id = f"{task_id}_{category}_{int(asyncio.get_event_loop().time())}"

            if metadata is None:
                metadata = {}

            metadata.update({
                "task_id": task_id,
                "category": category,
                "memory_type": "research",
                "stored_at": asyncio.get_event_loop().time()
            })

            success = await self.add_document(
                collection_name="research_memories",
                document_id=document_id,
                content=content,
                metadata=metadata
            )

            if success:
                return document_id
            else:
                raise Exception("Failed to store research memory")

        except Exception as e:
            self.logger.error(f"Failed to store research memory for task {task_id}: {str(e)}")
            raise

    async def find_similar_research(
        self,
        query: str,
        task_id: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar research memories."""
        try:
            where = None
            if task_id:
                where = {"task_id": task_id}

            results = await self.query_similar(
                collection_name="research_memories",
                query_text=query,
                n_results=n_results,
                where=where
            )

            return results.get("results", [])

        except Exception as e:
            self.logger.error(f"Failed to find similar research: {str(e)}")
            return []

    async def store_conversation_memory(
        self,
        conversation_id: str,
        user_id: str,
        conversation_data: Dict[str, Any]
    ) -> str:
        """Store conversation memory."""
        try:
            content = json.dumps(conversation_data, default=str)
            document_id = f"conv_{conversation_id}_{int(asyncio.get_event_loop().time())}"

            metadata = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "memory_type": "conversation",
                "stored_at": asyncio.get_event_loop().time()
            }

            success = await self.add_document(
                collection_name="conversation_memories",
                document_id=document_id,
                content=content,
                metadata=metadata
            )

            if success:
                return document_id
            else:
                raise Exception("Failed to store conversation memory")

        except Exception as e:
            self.logger.error(f"Failed to store conversation memory: {str(e)}")
            raise