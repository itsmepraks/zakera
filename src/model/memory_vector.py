"""Vector-based memory management with semantic search capabilities.

Provides advanced conversation memory using embeddings for:
- Semantic similarity search
- Context-aware message retrieval
- Intelligent memory consolidation
- Topic clustering and summarization
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning(
        "sentence-transformers not available. "
        "Install with: pip install sentence-transformers"
    )

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning(
        "faiss not available for optimized similarity search. "
        "Install with: pip install faiss-cpu"
    )

logger = logging.getLogger(__name__)


class VectorMemoryConfig(BaseModel):
    """Configuration for vector-based memory."""

    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model name"
    )
    max_messages: int = Field(
        default=100,
        ge=1,
        description="Maximum messages to store"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for retrieval"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        description="Number of similar messages to retrieve"
    )
    cluster_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for clustering"
    )
    enable_caching: bool = Field(
        default=True,
        description="Enable embedding caching"
    )
    cache_size: int = Field(
        default=1000,
        ge=1,
        description="Maximum cached embeddings"
    )


class Message(BaseModel):
    """Message with metadata."""

    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    embedding: Optional[np.ndarray] = Field(
        default=None,
        description="Message embedding vector"
    )

    class Config:
        arbitrary_types_allowed = True


class VectorMemoryStore:
    """Vector-based conversation memory with semantic search.
    
    Features:
    - Semantic similarity-based message retrieval
    - Automatic context pruning based on relevance
    - Topic clustering and summarization
    - Efficient embedding caching
    - FAISS-accelerated search (when available)
    """

    def __init__(self, config: VectorMemoryConfig):
        """Initialize vector memory store.
        
        Args:
            config: Vector memory configuration
        
        Raises:
            RuntimeError: If sentence-transformers is not available
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers is required for VectorMemoryStore. "
                "Install with: pip install sentence-transformers"
            )
        
        self.config = config
        self.messages: List[Message] = []
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
        # Load sentence transformer model
        logger.info(f"Loading embedding model: {config.model_name}")
        self.encoder = SentenceTransformer(config.model_name)
        self.embedding_dim = self.encoder.get_sentence_embedding_dimension()
        
        # Initialize FAISS index if available
        self.faiss_index = None
        if FAISS_AVAILABLE:
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info("FAISS index initialized for accelerated search")
        
        logger.info(
            f"VectorMemoryStore initialized with model: {config.model_name}, "
            f"embedding_dim: {self.embedding_dim}"
        )

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content.
        
        Args:
            content: Message content
        
        Returns:
            Content hash
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text with caching.
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        if self.config.enable_caching:
            content_hash = self._get_content_hash(text)
            
            if content_hash in self.embedding_cache:
                return self.embedding_cache[content_hash]
        
        # Generate embedding
        embedding = self.encoder.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Cache embedding
        if self.config.enable_caching:
            if len(self.embedding_cache) >= self.config.cache_size:
                # Remove oldest entry (simple FIFO)
                self.embedding_cache.pop(next(iter(self.embedding_cache)))
            
            self.embedding_cache[content_hash] = embedding
        
        return embedding

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add message to memory.
        
        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata
        """
        # Generate embedding
        embedding = self._get_embedding(content)
        
        # Create message
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
        )
        
        self.messages.append(message)
        
        # Update FAISS index
        if self.faiss_index is not None:
            self.faiss_index.add(embedding.reshape(1, -1))
        
        # Enforce max messages limit
        if len(self.messages) > self.config.max_messages:
            removed = self.messages.pop(0)
            logger.debug(f"Removed oldest message: {removed.content[:50]}...")
        
        logger.debug(
            f"Added {role} message to memory "
            f"(total: {len(self.messages)})"
        )

    def get_recent_messages(
        self,
        n: int = 10,
        role: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Get recent messages.
        
        Args:
            n: Number of recent messages
            role: Optional role filter
        
        Returns:
            List of message dictionaries
        """
        messages = self.messages
        
        if role:
            messages = [m for m in messages if m.role == role]
        
        recent = messages[-n:]
        
        return [
            {"role": m.role, "content": m.content}
            for m in recent
        ]

    def search_similar(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        role: Optional[str] = None,
    ) -> List[Tuple[Message, float]]:
        """Search for similar messages using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            role: Optional role filter
        
        Returns:
            List of (message, similarity_score) tuples
        """
        if not self.messages:
            return []
        
        top_k = top_k or self.config.top_k
        threshold = threshold or self.config.similarity_threshold
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Filter by role if specified
        candidates = self.messages
        if role:
            candidates = [m for m in candidates if m.role == role]
        
        if not candidates:
            return []
        
        # Use FAISS for fast search if available
        if self.faiss_index is not None and not role:
            # FAISS search
            scores, indices = self.faiss_index.search(
                query_embedding.reshape(1, -1),
                min(top_k, len(self.messages))
            )
            
            results = [
                (self.messages[idx], float(score))
                for idx, score in zip(indices[0], scores[0])
                if score >= threshold
            ]
        else:
            # Manual similarity computation
            embeddings = np.array([m.embedding for m in candidates])
            similarities = np.dot(embeddings, query_embedding)
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = [
                (candidates[idx], float(similarities[idx]))
                for idx in top_indices
                if similarities[idx] >= threshold
            ]
        
        logger.debug(
            f"Found {len(results)} similar messages for query: {query[:50]}..."
        )
        
        return results

    def get_context_messages(
        self,
        query: str,
        max_messages: int = 10,
        include_recent: int = 3,
    ) -> List[Dict[str, str]]:
        """Get context-aware messages for query.
        
        Combines recent messages with semantically similar messages.
        
        Args:
            query: Current query/message
            max_messages: Maximum messages to return
            include_recent: Number of recent messages to always include
        
        Returns:
            List of context messages
        """
        # Get recent messages
        recent = self.get_recent_messages(n=include_recent)
        
        # Get similar messages
        similar = self.search_similar(
            query,
            top_k=max_messages - include_recent,
        )
        
        # Combine and deduplicate
        seen = set()
        context = []
        
        # Add recent messages first
        for msg in recent:
            key = f"{msg['role']}:{msg['content']}"
            if key not in seen:
                context.append(msg)
                seen.add(key)
        
        # Add similar messages
        for message, score in similar:
            key = f"{message.role}:{message.content}"
            if key not in seen and len(context) < max_messages:
                context.append({
                    "role": message.role,
                    "content": message.content,
                })
                seen.add(key)
        
        logger.debug(f"Retrieved {len(context)} context messages")
        
        return context

    def cluster_messages(
        self,
        threshold: Optional[float] = None,
    ) -> List[List[Message]]:
        """Cluster messages by semantic similarity.
        
        Args:
            threshold: Clustering similarity threshold
        
        Returns:
            List of message clusters
        """
        if not self.messages:
            return []
        
        threshold = threshold or self.config.cluster_threshold
        
        # Simple agglomerative clustering
        clusters = []
        used = set()
        
        for i, message in enumerate(self.messages):
            if i in used:
                continue
            
            # Start new cluster
            cluster = [message]
            used.add(i)
            
            # Find similar messages
            for j, other in enumerate(self.messages[i+1:], start=i+1):
                if j in used:
                    continue
                
                similarity = float(
                    np.dot(message.embedding, other.embedding)
                )
                
                if similarity >= threshold:
                    cluster.append(other)
                    used.add(j)
            
            clusters.append(cluster)
        
        logger.info(
            f"Clustered {len(self.messages)} messages into {len(clusters)} groups"
        )
        
        return clusters

    def summarize_cluster(
        self,
        cluster: List[Message],
    ) -> str:
        """Generate summary for message cluster.
        
        Args:
            cluster: List of messages in cluster
        
        Returns:
            Summary text
        """
        # Extract key information
        contents = [m.content for m in cluster]
        roles = [m.role for m in cluster]
        
        # Generate simple summary
        summary = (
            f"Topic cluster with {len(cluster)} messages. "
            f"Roles: {', '.join(set(roles))}. "
            f"Representative content: {contents[0][:100]}..."
        )
        
        return summary

    def consolidate_memory(self) -> Dict[str, Any]:
        """Consolidate memory by clustering and summarizing.
        
        Returns:
            Consolidation statistics
        """
        if not self.messages:
            return {"status": "empty", "clusters": 0}
        
        # Cluster messages
        clusters = self.cluster_messages()
        
        # Generate summaries
        summaries = [
            self.summarize_cluster(cluster)
            for cluster in clusters
        ]
        
        stats = {
            "status": "completed",
            "total_messages": len(self.messages),
            "clusters": len(clusters),
            "summaries": summaries,
        }
        
        logger.info(
            f"Memory consolidation: {stats['total_messages']} messages "
            f"into {stats['clusters']} clusters"
        )
        
        return stats

    def clear(self) -> None:
        """Clear all messages from memory."""
        self.messages.clear()
        self.embedding_cache.clear()
        
        if self.faiss_index is not None:
            self.faiss_index.reset()
        
        logger.info("Memory cleared")

    def export(self) -> Dict[str, Any]:
        """Export memory to dictionary.
        
        Returns:
            Dictionary with memory data
        """
        return {
            "config": self.config.dict(),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self.messages
            ],
            "total_messages": len(self.messages),
            "embedding_dim": self.embedding_dim,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics.
        
        Returns:
            Statistics dictionary
        """
        role_counts = defaultdict(int)
        for msg in self.messages:
            role_counts[msg.role] += 1
        
        return {
            "total_messages": len(self.messages),
            "role_distribution": dict(role_counts),
            "cached_embeddings": len(self.embedding_cache),
            "embedding_dim": self.embedding_dim,
            "faiss_enabled": self.faiss_index is not None,
        }
