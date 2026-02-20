"""Base recognizer interface and common utilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.database import IntentCategory, IntentRule
from app.models.schema import MatchedRule

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result from intent recognition."""

    intent: str
    confidence: float
    matched_rules: List[MatchedRule] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    recognizer_type: str = ""
    recognition_chain: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0

    def merge(self, other: "IntentResult", weight: float = 1.0) -> None:
        """Merge another result into this one."""
        if other.confidence * weight > self.confidence:
            self.intent = other.intent
            self.confidence = other.confidence * weight
            self.entities.update(other.entities)

        # Merge matched rules
        self.matched_rules.extend(other.matched_rules)
        # Merge recognition chain
        self.recognition_chain.extend(other.recognition_chain)
        # Update processing time
        self.processing_time_ms += other.processing_time_ms


class IntentRecognizer(ABC):
    """Abstract base class for intent recognizers."""

    recognizer_type: str = "base"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize recognizer with optional configuration."""
        self.config = config or {}
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Check if recognizer is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable recognizer."""
        self._enabled = value

    @abstractmethod
    async def recognize(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntentResult]:
        """
        Recognize intent from text.

        Args:
            text: Input text to analyze
            categories: List of available intent categories
            rules: List of intent rules
            context: Additional context information

        Returns:
            IntentResult if intent matched, None otherwise
        """
        pass

    async def initialize(self) -> None:
        """Initialize recognizer (load models, etc.). Override if needed."""
        pass

    async def shutdown(self) -> None:
        """Cleanup resources. Override if needed."""
        pass

    def _create_match_rule(self, rule: IntentRule) -> MatchedRule:
        """Create MatchedRule from IntentRule."""
        return MatchedRule(
            id=rule.id,
            rule_type=rule.rule_type,
            content=rule.content,
            weight=rule.weight,
        )

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
            matched_rules=[self._create_match_rule(r) for r in rules],
            recognizer_type=self.recognizer_type,
        )


class RecognizerChain:
    """
    Chain of responsibility for intent recognition.

    Executes recognizers in order and returns first confident result,
    or combines results from all recognizers.
    """

    def __init__(self, recognizers: List[IntentRecognizer]):
        """Initialize recognizer chain."""
        self.recognizers = recognizers
        self.last_chain = []

    async def recognize(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]] = None,
        combine_results: bool = False,
    ) -> Optional[IntentResult]:
        """
        Recognize intent using the chain.

        Args:
            text: Input text
            categories: Available intent categories
            rules: Intent rules
            context: Additional context
            combine_results: If True, combine all results; otherwise return first match

        Returns:
            IntentResult or None
        """
        if combine_results:
            return await self._recognize_combined(text, categories, rules, context)

        return await self._recognize_first(text, categories, rules, context)

    async def _recognize_first(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]],
    ) -> Optional[IntentResult]:
        """Return first confident result."""
        import time
        recognition_chain = []
        total_time = 0.0
        
        for recognizer in self.recognizers:
            if not recognizer.enabled:
                recognition_chain.append({
                    "recognizer": recognizer.recognizer_type,
                    "status": "skipped",
                    "reason": "disabled",
                    "time_ms": 0.0
                })
                continue

            try:
                start_time = time.time()
                result = await recognizer.recognize(text, categories, rules, context)
                end_time = time.time()
                elapsed_time = (end_time - start_time) * 1000
                # Ensure minimum time value to avoid 0.00ms display
                elapsed_time = max(elapsed_time, 0.01)
                total_time += elapsed_time
                
                if result and result.confidence > 0.5:
                    logger.debug(
                        f"Intent matched by {recognizer.recognizer_type}: "
                        f"{result.intent} (confidence: {result.confidence}, time: {elapsed_time:.2f}ms)"
                    )
                    # Add current recognizer to chain
                    recognition_chain.append({
                        "recognizer": recognizer.recognizer_type,
                        "status": "success",
                        "intent": result.intent,
                        "confidence": result.confidence,
                        "time_ms": elapsed_time
                    })
                    # Update result with chain information
                    result.recognition_chain = recognition_chain
                    result.processing_time_ms = total_time
                    self.last_chain = recognition_chain
                    return result
                else:
                    # Add current recognizer to chain (no match)
                    recognition_chain.append({
                        "recognizer": recognizer.recognizer_type,
                        "status": "no_match",
                        "time_ms": elapsed_time
                    })
            except Exception as e:
                logger.error(f"Error in {recognizer.recognizer_type}: {e}")
                recognition_chain.append({
                    "recognizer": recognizer.recognizer_type,
                    "status": "error",
                    "error": str(e),
                    "time_ms": 0.0
                })

        self.last_chain = recognition_chain
        return None

    async def _recognize_combined(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]],
    ) -> Optional[IntentResult]:
        """Combine results from all recognizers."""
        import time
        results = []
        recognition_chain = []
        total_time = 0.0

        for recognizer in self.recognizers:
            if not recognizer.enabled:
                recognition_chain.append({
                    "recognizer": recognizer.recognizer_type,
                    "status": "skipped",
                    "reason": "disabled",
                    "time_ms": 0.0
                })
                continue

            try:
                start_time = time.time()
                result = await recognizer.recognize(text, categories, rules, context)
                end_time = time.time()
                elapsed_time = (end_time - start_time) * 1000
                # Ensure minimum time value to avoid 0.00ms display
                elapsed_time = max(elapsed_time, 0.01)
                total_time += elapsed_time
                
                if result:
                    results.append(result)
                    recognition_chain.append({
                        "recognizer": recognizer.recognizer_type,
                        "status": "success",
                        "intent": result.intent,
                        "confidence": result.confidence,
                        "time_ms": elapsed_time
                    })
                else:
                    recognition_chain.append({
                        "recognizer": recognizer.recognizer_type,
                        "status": "no_match",
                        "time_ms": elapsed_time
                    })
            except Exception as e:
                logger.error(f"Error in {recognizer.recognizer_type}: {e}")
                recognition_chain.append({
                    "recognizer": recognizer.recognizer_type,
                    "status": "error",
                    "error": str(e),
                    "time_ms": 0.0
                })

        if not results:
            return None

        # Return result with highest confidence
        best_result = max(results, key=lambda r: r.confidence)
        # Update best result with chain information
        best_result.recognition_chain = recognition_chain
        best_result.processing_time_ms = total_time
        return best_result

    async def initialize_all(self) -> None:
        """Initialize all recognizers in the chain."""
        for recognizer in self.recognizers:
            await recognizer.initialize()

    async def shutdown_all(self) -> None:
        """Shutdown all recognizers in the chain."""
        for recognizer in self.recognizers:
            await recognizer.shutdown()
