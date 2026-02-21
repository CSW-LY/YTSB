"""LLM-based intent classifier (fallback strategy)."""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.models.database import IntentCategory, IntentRule
from app.services.recognizer.base import IntentRecognizer, IntentResult

logger = logging.getLogger(__name__)

settings = get_settings()


class LLMRecognizer(IntentRecognizer):
    """
    LLM-based intent recognizer (fallback strategy).

    Uses an LLM to classify intent when other methods fail.
    Disabled by default; enable via configuration.
    """

    recognizer_type = "llm"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LLM recognizer."""
        super().__init__(config)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._api_key = settings.llm_api_key
        self._base_url = settings.llm_base_url
        self._model = settings.llm_model
        self._is_connected = False
        self._last_health_check: Optional[float] = None

        # Enable by default if config is provided and valid
        self._enabled = settings.enable_llm_fallback
        if self._enabled:
            logger.info("LLM recognizer enabled by configuration")
        else:
            logger.info("LLM recognizer disabled by configuration")

    async def initialize(self) -> None:
        """Initialize HTTP client with connection test."""
        if not self._enabled:
            logger.info("LLM recognizer initialization skipped (disabled)")
            return

        # Check if already initialized
        if self._http_client:
            logger.info("LLM recognizer already initialized, skipping")
            return

        # Validate configuration
        if not all([self._api_key, self._base_url, self._model]):
            logger.warning("LLM recognizer incomplete configuration, disabling")
            logger.warning(f"API key: {bool(self._api_key)}, Base URL: {bool(self._base_url)}, Model: {bool(self._model)}")
            self._enabled = False
            self._is_connected = False
            return

        try:
            # Initialize HTTP client
            self._http_client = httpx.AsyncClient(timeout=30.0)
            logger.info(f"LLM recognizer HTTP client initialized: {self._base_url}")
            
            # Test connection with a simple prompt
            test_prompt = "Test connection"
            logger.info("Testing LLM connection...")
            response = await self._call_llm(test_prompt)
            
            if response:
                logger.info("LLM connection test successful")
                self._is_connected = True
            else:
                logger.warning("LLM connection test returned no response")
                self._is_connected = False
                
        except httpx.HTTPError as e:
            logger.error(f"LLM connection test failed (HTTP error): {e}")
            self._is_connected = False
        except Exception as e:
            logger.error(f"LLM connection test failed (unknown error): {e}")
            self._is_connected = False
        finally:
            logger.info("LLM recognizer initialization completed")

    async def recognize(
        self,
        text: str,
        categories: List[IntentCategory],
        rules: List[IntentRule],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntentResult]:
        """
        Recognize intent using LLM classification.

        Constructs a prompt with available categories and asks
        the LLM to classify the input.
        """
        if not self._enabled or not self._http_client:
            logger.warning("LLM recognizer not enabled or client not initialized")
            return None

        # Filter active categories
        active_categories = [c for c in categories if c.is_active]
        if not active_categories:
            logger.warning("No active categories available for LLM recognition")
            return None

        try:
            # Build classification prompt
            category_descriptions = "\n".join(
                [
                    f"- {c.code}: {c.name} (描述: {c.description})"
                    for c in sorted(active_categories, key=lambda c: c.priority, reverse=True)
                ]
            )

            prompt = f"""Classify the following user input into one of these intent categories.

Available categories:
{category_descriptions}

User input: "{text}"

Examples:
- Input: "查找零件A123" → Output: {{"intent": "part.search", "confidence": 0.95}}
- Input: "找一个螺栓" → Output: {{"intent": "part.search", "confidence": 0.95}}
- Input: "创建新零件" → Output: {{"intent": "part.create", "confidence": 0.95}}
- Input: "查询BOM结构" → Output: {{"intent": "bom.query", "confidence": 0.95}}

Respond ONLY with a JSON object in this exact format:
{{"intent": "category_code", "confidence": 0.95}}

Choose the most appropriate category based on the user's intent.
If none of the categories match, respond with:
{{"intent": "LLM无法匹配", "confidence": 0.0}}"""

            logger.info(f"LLM prompt: {prompt[:500]}...")  # Log truncated prompt

            # Call LLM API
            response = await self._call_llm(prompt)

            if not response:
                logger.warning("LLM returned no response")
                # Return default "LLM无法匹配" when no response
                return IntentResult(
                    intent="LLM无法匹配",
                    confidence=0.0,
                    recognizer_type=self.recognizer_type,
                )

            logger.info(f"LLM response: {response}")

            # Parse response
            intent_code = response.get("intent")
            confidence = response.get("confidence", 0.5)

            if not intent_code:
                logger.warning(f"LLM returned invalid response: {response}")
                # Return default "LLM无法匹配" when invalid response
                return IntentResult(
                    intent="LLM无法匹配",
                    confidence=0.0,
                    recognizer_type=self.recognizer_type,
                )

            # Find category
            category = next((c for c in active_categories if c.code == intent_code), None)
            if not category:
                # If intent_code is already "LLM无法匹配", return it
                if intent_code == "LLM无法匹配":
                    return IntentResult(
                        intent=intent_code,
                        confidence=0.0,
                        recognizer_type=self.recognizer_type,
                    )
                logger.warning(f"LLM returned unknown intent code: {intent_code}")
                # Return default "LLM无法匹配" when unknown intent code
                return IntentResult(
                    intent="LLM无法匹配",
                    confidence=0.0,
                    recognizer_type=self.recognizer_type,
                )

            logger.info(f"LLM matched intent: {intent_code} (confidence: {confidence})")

            return IntentResult(
                intent=intent_code,
                confidence=min(confidence, 0.95),  # Cap LLM confidence
                recognizer_type=self.recognizer_type,
            )

        except Exception as e:
            logger.error(f"Error in LLM recognition: {e}")
            # Return default "LLM无法匹配" when exception occurs
            return IntentResult(
                intent="LLM无法匹配",
                confidence=0.0,
                recognizer_type=self.recognizer_type,
            )

    async def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call LLM API with prompt."""
        try:
            logger.info(f"Calling LLM API with prompt: {prompt[:300]}...")
            
            response = await self._http_client.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an intent classification assistant. Respond only with valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,  # Low temperature for consistent output
                    "max_tokens": 100,
                },
                timeout=10.0,
            )

            logger.info(f"LLM API response status: {response.status_code}")
            logger.info(f"LLM API response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"LLM API response data: {data}")

            # Extract content from response (format varies by provider)
            content = self._extract_content(data)
            logger.info(f"Extracted content from LLM response: {content}")
            
            if not content:
                logger.warning("No content extracted from LLM response")
                return None

            # Parse JSON response
            try:
                json_response = json.loads(content)
                logger.info(f"Parsed JSON response from LLM: {json_response}")
                return json_response
            except json.JSONDecodeError as e:
                logger.warning(f"LLM returned non-JSON: {content}")
                logger.warning(f"JSON decode error: {e}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"LLM API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_content(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract content from LLM response (handles different formats)."""
        # OpenAI format
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            return content

        # Anthropic format
        if "content" in data:
            content = data["content"]
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            return content

        # Generic
        if "message" in data:
            content = data["message"].get("content")
            # Remove markdown code blocks if present
            if content and content.startswith("```json"):
                content = content[7:-3].strip()
            elif content and content.startswith("```"):
                content = content[3:-3].strip()
            return content

        return None

    async def shutdown(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._is_connected = False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform LLM connection health check.

        Returns:
            Dict containing connection status and health details.
        """
        import time
        from typing import Dict, Any

        # Update last health check time
        self._last_health_check = time.time()

        health_status = {
            "connected": False,
            "enabled": self._enabled,
            "has_client": self._http_client is not None,
            "has_api_key": bool(self._api_key),
            "has_base_url": bool(self._base_url),
            "has_model": bool(self._model),
            "last_health_check": self._last_health_check,
            "error": None
        }

        if not self._enabled:
            health_status["error"] = "LLM recognizer is disabled by configuration"
            return health_status

        if not self._http_client:
            health_status["error"] = "HTTP client not initialized"
            return health_status

        if not all([self._api_key, self._base_url, self._model]):
            health_status["error"] = "Incomplete configuration"
            return health_status

        try:
            # Perform a simple health check with a minimal prompt
            test_prompt = "Health check"
            response = await self._call_llm(test_prompt)

            if response:
                self._is_connected = True
                health_status["connected"] = True
                health_status["response_received"] = True
                logger.info("LLM health check passed")
            else:
                self._is_connected = False
                health_status["error"] = "No response from LLM API"
                health_status["response_received"] = False
                logger.warning("LLM health check failed: no response")

        except httpx.HTTPError as e:
            self._is_connected = False
            health_status["error"] = f"HTTP error: {str(e)}"
            logger.error(f"LLM health check failed: {e}")
        except Exception as e:
            self._is_connected = False
            health_status["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"LLM health check failed: {e}")

        return health_status

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current LLM connection status without performing health check.

        Returns:
            Dict containing current connection status.
        """
        import time
        from typing import Dict, Any

        return {
            "connected": self._is_connected,
            "enabled": self._enabled,
            "has_client": self._http_client is not None,
            "has_api_key": bool(self._api_key),
            "has_base_url": bool(self._base_url),
            "has_model": bool(self._model),
            "model_name": self._model,
            "provider": self._base_url.split('://')[1].split('/')[0] if self._base_url else '未知',
            "last_health_check": self._last_health_check
        }
