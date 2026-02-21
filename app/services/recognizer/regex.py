"""Regex-based intent recognizer for structured inputs."""

import logging
import re
from typing import Any, Dict, List, Optional

from app.models.database import IntentCategory, IntentRule
from app.services.recognizer.base import IntentRecognizer, IntentResult

logger = logging.getLogger(__name__)


class RegexRecognizer(IntentRecognizer):
    """
    Regex-based intent recognizer.

    Best for structured inputs like:
    - Part numbers: P-12345-001
    - Serial numbers: SN/ABC/12345
    - Date formats, etc.
    """

    recognizer_type = "regex"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize regex recognizer."""
        super().__init__(config)
        self._compiled_patterns: List[tuple] = []

    def _build_pattern_index(
        self,
        categories: List[IntentCategory],
        rules: List[IntentRule],
    ) -> None:
        """Build compiled regex pattern index."""
        self._compiled_patterns = []
        category_map = {c.id: c for c in categories}

        for rule in rules:
            if rule.rule_type != "regex" or not rule.is_active or not rule.enabled:
                continue

            category = category_map.get(rule.category_id)
            if not category or not category.is_active:
                continue

            try:
                pattern = re.compile(rule.content, re.IGNORECASE | re.UNICODE)
                self._compiled_patterns.append((category, rule, pattern))
            except re.error as e:
                logger.warning(f"Invalid regex pattern for rule {rule.id}: {e}")

    async def recognize(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntentResult]:
        """
        Recognize intent using regex patterns.

        Extracts entities using named groups in patterns.
        """
        # Build index on first call or if empty
        if not self._compiled_patterns:
            self._build_pattern_index(categories, rules)

        if not self._compiled_patterns:
            return None

        matches = []

        for category, rule, pattern in self._compiled_patterns:
            match = pattern.search(text)
            if match:
                # Extract named groups as entities
                entities = {}
                if hasattr(match, "groupdict"):
                    entities = {k: v for k, v in match.groupdict().items() if v is not None}

                # Calculate confidence based on match coverage
                matched_text = match.group(0)
                coverage = len(matched_text) / len(text) if text else 0
                confidence = min(0.7 + (coverage * 0.3), 1.0) * rule.weight

                matches.append(
                    {
                        "category": category,
                        "rule": rule,
                        "confidence": confidence,
                        "entities": entities,
                    }
                )

        if not matches:
            return None

        # Return best match
        best_match = max(matches, key=lambda m: m["confidence"])

        result = self._create_result(
            best_match["category"],
            min(best_match["confidence"], 1.0),
            [best_match["rule"]],
        )
        result.entities = best_match["entities"]

        return result
