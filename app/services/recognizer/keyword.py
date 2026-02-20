"""Keyword-based intent recognizer."""

import logging
from typing import Any, Dict, List, Optional

from app.models.database import IntentCategory, IntentRule
from app.services.recognizer.base import IntentRecognizer, IntentResult

logger = logging.getLogger(__name__)


class KeywordRecognizer(IntentRecognizer):
    """
    Fast keyword-based intent recognizer.

    Uses Aho-Corasick algorithm for efficient multi-pattern matching.
    Priority: O(1) lookup for exact matches, O(n) for pattern matching.
    """

    recognizer_type = "keyword"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize keyword recognizer."""
        super().__init__(config)
        self._keyword_index: Dict[str, List[tuple]] = {}
        self._exact_match_index: Dict[str, IntentCategory] = {}

    async def initialize(self) -> None:
        """Build keyword index from rules."""
        logger.info("Initializing keyword recognizer")

    def _build_indices(
        self,
        categories: List[IntentCategory],
        rules: List[IntentRule],
    ) -> None:
        """
        Build keyword indices from rules.

        Creates:
        - Exact match index for direct keyword lookup
        - Pattern index for substring matching
        """
        self._keyword_index = {}
        self._exact_match_index = {}

        category_map = {c.id: c for c in categories}

        for rule in rules:
            if rule.rule_type != "keyword" or not rule.is_active:
                continue

            category = category_map.get(rule.category_id)
            if not category or not category.is_active:
                continue

            # Normalize keyword
            content = rule.content.strip().lower()

            # Check for exact match marker (starts with ^)
            if content.startswith("^"):
                exact_keyword = content[1:].strip()
                self._exact_match_index[exact_keyword] = category
            else:
                # 处理逗号分隔的多个关键词
                keywords = [k.strip() for k in content.split(",")]
                for keyword in keywords:
                    if not keyword:
                        continue
                    # Add to pattern index
                    if keyword not in self._keyword_index:
                        self._keyword_index[keyword] = []

                    self._keyword_index[keyword].append((category, rule))

    async def recognize(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntentResult]:
        """
        Recognize intent using keyword matching.

        Strategy:
        1. Check exact match first (fastest)
        2. Then check partial matches with scoring
        """
        # Build indices on first call or if empty
        if not self._keyword_index:
            self._build_indices(categories, rules)

        if not self._keyword_index:
            return None

        text_normalized = text.strip().lower()
        matches = []

        # Check exact match first
        if text_normalized in self._exact_match_index:
            category = self._exact_match_index[text_normalized]
            return IntentResult(
                intent=category.code,
                confidence=1.0,
                recognizer_type=self.recognizer_type,
            )

        # Check partial matches
        for keyword, entries in self._keyword_index.items():
            if keyword in text_normalized:
                for category, rule in entries:
                    # Calculate confidence based on match position
                    match_score = self._calculate_confidence(text_normalized, keyword)
                    matches.append(
                        {
                            "category": category,
                            "rule": rule,
                            "confidence": match_score * rule.weight,
                        }
                    )

        if not matches:
            return None

        # Return best match
        best_match = max(matches, key=lambda m: m["confidence"])
        category = best_match["category"]

        return self._create_result(
            category,
            min(best_match["confidence"], 1.0),
            [best_match["rule"]],
        )

    def _calculate_confidence(self, text: str, keyword: str) -> float:
        """
        Calculate confidence score based on match characteristics.

        Factors:
        - Exact match at start: 1.0
        - Match at word boundary: 0.9
        - Substring match: 0.6
        - Length ratio bonus
        """
        # Exact match
        if text == keyword:
            return 1.0

        # Match at start
        if text.startswith(keyword):
            bonus = 0.9
        # Match at end
        elif text.endswith(keyword):
            bonus = 0.85
        # Check for word boundary
        elif f" {keyword} " in f" {text} " or f" {keyword}" in text:
            bonus = 0.8
        else:
            bonus = 0.6

        # Length ratio bonus (prefer longer keywords)
        length_ratio = len(keyword) / len(text)
        length_bonus = min(length_ratio * 0.2, 0.2)

        return min(bonus + length_bonus, 1.0)
