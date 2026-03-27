"""Semantic embeddings service using Hugging Face sentence-transformers.

Provides vector embeddings for chat messages to enable:
- Semantic search over conversation history
- Relevant context retrieval for follow-up queries
- Reduced token usage by selecting only relevant past messages
"""

from typing import Dict, List, Optional, Tuple
from loguru import logger
import numpy as np

# Lazy-loaded model
_model = None

# Default model - lightweight (80MB), fast, 384-dim embeddings
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _get_model(model_name: str = DEFAULT_MODEL):
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {model_name}")
            _model = SentenceTransformer(model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


class EmbeddingService:
    """Manages semantic embeddings for chat messages and context retrieval."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        max_history_embeddings: int = 100,
        enabled: bool = True,
    ) -> None:
        self.model_name = model_name
        self.max_history_embeddings = max_history_embeddings
        self.enabled = enabled
        self._loaded = False
        # In-memory store: list of (text, embedding, metadata) tuples
        self._history: List[Tuple[str, np.ndarray, Dict]] = []

    def _ensure_loaded(self) -> bool:
        """Ensure the model is loaded. Returns False if loading fails."""
        if self._loaded:
            return True
        try:
            _get_model(self.model_name)
            self._loaded = True
            return True
        except Exception:
            self.enabled = False
            return False

    def embed(self, text: str) -> Optional[np.ndarray]:
        """
        Get the embedding vector for a text string.

        Args:
            text: Input text to embed.

        Returns:
            Numpy array of the embedding, or None if unavailable.
        """
        if not self.enabled or not self._ensure_loaded():
            return None

        try:
            model = _get_model(self.model_name)
            return model.encode(text, normalize_embeddings=True)
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return None

    def add_to_history(self, text: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to the embedding history.

        Args:
            text: The message text to store.
            metadata: Optional metadata (e.g., role, timestamp, tool_name).
        """
        if not self.enabled:
            return

        embedding = self.embed(text)
        if embedding is None:
            return

        self._history.append((text, embedding, metadata or {}))

        # Trim oldest entries if over limit
        if len(self._history) > self.max_history_embeddings:
            self._history = self._history[-self.max_history_embeddings :]

    def find_relevant(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.3,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Find the most semantically relevant messages from history.

        Args:
            query: The query text to search against.
            top_k: Maximum number of results to return.
            min_similarity: Minimum cosine similarity threshold.

        Returns:
            List of (text, similarity_score, metadata) tuples, sorted by relevance.
        """
        if not self.enabled or not self._history:
            return []

        query_embedding = self.embed(query)
        if query_embedding is None:
            return []

        # Compute cosine similarities (embeddings are already normalized)
        scored = []
        for text, emb, metadata in self._history:
            similarity = float(np.dot(query_embedding, emb))
            if similarity >= min_similarity:
                scored.append((text, similarity, metadata))

        # Sort by similarity descending, take top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_relevant_context(self, query: str, top_k: int = 3) -> List[str]:
        """
        Get relevant past messages as plain strings for prompt injection.

        This is the primary interface for the orchestrator to retrieve
        relevant conversation context.

        Args:
            query: The current user message.
            top_k: Number of relevant messages to retrieve.

        Returns:
            List of relevant message strings.
        """
        results = self.find_relevant(query, top_k=top_k)
        return [text for text, _, _ in results]

    def clear(self) -> None:
        """Clear all stored embeddings."""
        self._history.clear()
        logger.debug("Embedding history cleared")

    def history_size(self) -> int:
        """Get the number of stored embeddings."""
        return len(self._history)
