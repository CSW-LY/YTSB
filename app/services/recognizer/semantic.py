"""Semantic-based intent recognizer using embeddings."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ml.embedding import EmbeddingModel
from app.models.database import IntentCategory, IntentRule
from app.services.recognizer.base import IntentRecognizer, IntentResult

logger = logging.getLogger(__name__)

settings = get_settings()


class SemanticRecognizer(IntentRecognizer):
    """
    Semantic similarity-based intent recognizer.

    Uses embedding models to vectorize input and compare with
    intent examples using cosine similarity.
    """

    recognizer_type = "semantic"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize semantic recognizer."""
        super().__init__(config)
        self._embedding_model: Optional[EmbeddingModel] = None
        self._intent_embeddings: Dict[int, List[Tuple[np.ndarray, float]]] = {}
        self._threshold = config.get("threshold", 0.75) if config else 0.75

        # Use global embedding model instance to avoid duplicate loading
        from app.ml.embedding import get_embedding_model
        self._embedding_model = get_embedding_model()

    async def initialize(self) -> None:
        """Initialize embedding model."""
        try:
            await self._embedding_model.load()
            logger.info("Semantic recognizer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fall back to simple model
            await self._use_simple_model()
            self._enabled = False  # Disable full semantic matching

    async def _use_simple_model(self) -> None:
        """Switch to simple embedding model as fallback."""
        from app.ml.embedding import SimpleEmbeddingModel

        logger.warning("Falling back to SimpleEmbeddingModel for semantic matching")
        self._embedding_model = SimpleEmbeddingModel()
        try:
            await self._embedding_model.load()
        except Exception as e:
            logger.error(f"Failed to load simple model: {e}")

    async def recognize(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntentResult]:
        """
        Recognize intent using semantic similarity.

        Returns highest confidence match above threshold.
        """
        if not self._embedding_model:
            return None

        # Build embeddings if needed
        if not self._intent_embeddings:
            await self._build_intent_embeddings(categories, rules)

        if not self._intent_embeddings:
            return None

        try:
            # Encode input text
            text_embedding = self._embedding_model.encode(text)

            # Ensure 2D array for cosine_similarity
            if text_embedding.ndim == 1:
                text_embedding = text_embedding.reshape(1, -1)

            # Calculate similarities for each intent
            results = []

            for category_id, embeddings in self._intent_embeddings.items():
                # Calculate max similarity for this category
                similarities = [
                    cosine_similarity(
                        text_embedding,
                        emb.reshape(1, -1) if emb.ndim == 1 else emb
                    )[0][0] * weight
                    for emb, weight in embeddings
                ]

                if similarities:
                    max_similarity = max(similarities)
                    results.append(
                        {
                            "category_id": category_id,
                            "confidence": max_similarity,
                        }
                    )

            if not results:
                return None

            # Get best result
            best_result = max(results, key=lambda r: r["confidence"])
            if best_result["confidence"] < self._threshold:
                logger.debug(f"Best confidence {best_result['confidence']:.3f} below threshold {self._threshold}")
                return None

            # Find category
            category = next(
                (c for c in categories if c.id == best_result["category_id"]),
                None
            )

            if not category:
                return None

            # Find matched rule
            matched_rule = next(
                (r for r in rules if r.category_id == category.id and r.rule_type == "semantic"),
                None,
            )

            return self._create_result(
                category,
                best_result["confidence"],
                [matched_rule] if matched_rule else []
            )

        except Exception as e:
            logger.error(f"Error in semantic recognition: {e}")
            return None

    async def _build_intent_embeddings(
        self,
        categories: List[IntentCategory],
        rules: List[IntentRule],
    ) -> None:
        """Build embeddings for all semantic rules using batch encoding."""
        category_map = {c.id: c for c in categories}
        
        # Collect all semantic rules
        semantic_rules = []
        for rule in rules:
            if rule.rule_type != "semantic" or not rule.is_active:
                continue

            category = category_map.get(rule.category_id)
            if not category or not category.is_active:
                continue

            semantic_rules.append((rule, category))

        if not semantic_rules:
            return

        try:
            # Batch encode all semantic rules at once
            logger.info(f"Batch encoding {len(semantic_rules)} semantic rules")
            semantic_texts = [rule.content for rule, category in semantic_rules]
            embeddings = self._embedding_model.encode(semantic_texts)

            # Group embeddings by category
            for i, (rule, category) in enumerate(semantic_rules):
                if category.id not in self._intent_embeddings:
                    self._intent_embeddings[category.id] = []

                self._intent_embeddings[category.id].append(
                    (embeddings[i], rule.weight)
                )
            
            logger.info(f"Successfully encoded {len(semantic_rules)} semantic rules")
        except Exception as e:
            logger.error(f"Failed to batch encode semantic rules: {e}")

    def _create_result(
        self,
        category: IntentCategory,
        confidence: float,
        rules: List[IntentRule],
    ) -> IntentResult:
        """Create IntentResult from category and rules."""
        return IntentResult(
            intent=category.code,
            confidence=confidence,
            matched_rules=[
                self._create_match_rule(r) for r in rules
            ],
            recognizer_type=self.recognizer_type,
        )

    def _create_match_rule(self, rule: IntentRule) -> "MatchedRule":
        """Create MatchedRule from IntentRule."""
        from app.models.schema import MatchedRule

        return MatchedRule(
            id=rule.id,
            rule_type=rule.rule_type,
            content=rule.content,
            weight=rule.weight,
        )

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._embedding_model:
            await self._embedding_model.unload()