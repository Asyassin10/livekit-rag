"""
RAG module for vector retrieval using Qdrant and OpenRouter embeddings
"""
import logging
from typing import List, Dict, Optional
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config import settings

logger = logging.getLogger(__name__)


class RAGRetriever:
    """RAG retriever using Qdrant and OpenRouter embeddings"""

    def __init__(self):
        """Initialize Qdrant client and embedding service"""
        logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")

        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION

        # Verify collection exists
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            if self.collection_name not in collection_names:
                logger.warning(
                    f"Collection '{self.collection_name}' not found. "
                    f"Available collections: {collection_names}"
                )
            else:
                logger.info(f"Connected to collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to verify Qdrant collection: {e}")

        # OpenRouter API settings
        self.openrouter_url = "https://openrouter.ai/api/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.info("RAG retriever initialized")

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding vector for text using OpenRouter API

        Args:
            text: Input text to embed

        Returns:
            Embedding vector or None if request fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.openrouter_url,
                    headers=self.headers,
                    json={
                        "model": settings.EMBEDDING_MODEL,
                        "input": text,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None

    async def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Retrieve relevant documents from Qdrant

        Args:
            query: Search query text
            top_k: Number of results to return (default from settings)

        Returns:
            List of retrieved documents with metadata
        """
        if top_k is None:
            top_k = settings.RAG_TOP_K

        try:
            # Get query embedding
            query_embedding = await self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to get query embedding")
                return []

            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=settings.RAG_SCORE_THRESHOLD,
            )

            # Format results
            documents = []
            for result in search_results:
                documents.append({
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "metadata": result.payload.get("metadata", {}),
                })

            logger.info(f"Retrieved {len(documents)} documents for query: {query}")
            return documents

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []

    def format_context(self, documents: List[Dict]) -> str:
        """
        Format retrieved documents into context string for LLM

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted context string
        """
        if not documents:
            return ""

        context_parts = []
        for i, doc in enumerate(documents, 1):
            text = doc.get("text", "").strip()
            if text:
                context_parts.append(f"[Document {i}]: {text}")

        return "\n\n".join(context_parts)


# Global RAG instance
_rag_instance: Optional[RAGRetriever] = None


def get_rag() -> RAGRetriever:
    """Get or create the global RAG instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGRetriever()
    return _rag_instance
