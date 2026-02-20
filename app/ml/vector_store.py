"""Simple in-memory vector store for intent examples."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.embedding import EmbeddingModel

logger = logging.getLogger(__name__)


class SimpleVectorStore:
    """
    In-memory vector store for intent examples.

    Stores intent example embeddings for fast similarity search.
    """

    def __init__(self, embedding_model: EmbeddingModel):
        """Initialize vector store."""
        self.embedding_model = embedding_model
        self._vectors: Dict[int, List[Tuple[np.ndarray, float]]] = {}
        self._metadata: Dict[int, Dict[str, Any]] = {}

    async def add_intent_examples(
        self,
        intent_id: int,
        examples: List[str],
        weights: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add examples for an intent.

        Args:
            intent_id: Intent category ID
            examples: List of example texts
            weights: Optional weight for each example
            metadata: Optional metadata to store
        """
        if not examples:
            return

        if weights is None:
            weights = [1.0] * len(examples)

        # Encode all examples
        embeddings = self.embedding_model.encode(examples)

        # Store with weights
        if intent_id not in self._vectors:
            self._vectors[intent_id] = []

        for emb, weight in zip(embeddings, weights):
            self._vectors[intent_id].append((emb, weight))

        # Store metadata
        if metadata:
            self._metadata[intent_id] = metadata

        logger.debug(f"Added {len(examples)} examples for intent {intent_id}")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
    ) -> List[Tuple[int, float, np.ndarray]]:
        """
        Search for similar intents.

        Args:
            query: Query text
            top_k: Return top k results
            min_similarity: Minimum similarity threshold

        Returns:
            List of (intent_id, similarity, vector) tuples
        """
        if not self._vectors:
            return []

        # Encode query
        query_embedding = self.embedding_model.encode(query)

        # Ensure 2D array for cosine_similarity
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        results = []

        for intent_id, vectors in self._vectors.items():
            for vector, weight in vectors:
                # Ensure 2D array for cosine_similarity
                vec = vector.reshape(1, -1) if vector.ndim == 1 else vector
                similarity = cosine_similarity(
                    query_embedding,
                    vec
                )[0][0] * weight

                if similarity >= min_similarity:
                    results.append((intent_id, similarity, vector))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    async def get_best_match(
        self,
        query: str,
        min_similarity: float = 0.5,
    ) -> Optional[Tuple[int, float]]:
        """
        Get best matching intent.

        Returns:
            (intent_id, similarity) or None if no match
        """
        results = await self.search(query, top_k=1, min_similarity=min_similarity)

        if results:
            return results[0][:2]

        return None

    def clear(self) -> None:
        """Clear all stored vectors."""
        self._vectors.clear()
        self._metadata.clear()

    def get_intent_count(self) -> int:
        """Get number of stored intents."""
        return len(self._vectors)

    def get_example_count(self, intent_id: Optional[int] = None) -> int:
        """Get number of examples stored."""
        if intent_id is not None:
            return len(self._vectors.get(intent_id, []))

        return sum(len(vectors) for vectors in self._vectors.values())
