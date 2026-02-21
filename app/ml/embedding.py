"""Embedding model management for intent recognition."""

import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Global embedding model instance for sharing across recognizers
_global_embedding_model = None


class EmbeddingModel:
    """
    Embedding model wrapper for intent recognition.

    Supports:
    - BGE-M3 (multi-lingual, multi-functionality)
    - BGE-Large-ZH (Chinese optimized)
    - Custom local model paths
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """Initialize embedding model."""
        self.model_name = model_name or settings.model_type
        self.model_path = model_path or settings.model_path
        self.device = device or settings.model_device

        self._model: Optional[SentenceTransformer] = None
        self._loaded = False
        self._model_initialized = False

    async def load(self) -> None:
        """Load embedding model from local path or HuggingFace."""
        if self._loaded:
            logger.info("Embedding model already loaded, skipping...")
            return

        from pathlib import Path

        logger.info(f"Loading embedding model: {self.model_name}")

        # If model_path is a directory that exists, use local model
        if self.model_path and Path(self.model_path).exists() and Path(self.model_path).is_dir():
            model_to_load = self.model_path
            logger.info(f"Using local model from: {model_to_load}")
        else:
            # Fall back to HuggingFace model name
            model_mapping = {
                "bge-m3": "BAAI/bge-m3",
                "bge-large-zh": "BAAI/bge-large-zh-v1.5",
                "bge-small-zh": "BAAI/bge-small-zh-v1.5",
            }
            model_to_load = model_mapping.get(self.model_name, self.model_name)
            logger.info(f"Loading model from HuggingFace: {model_to_load}")

        try:
            logger.info(f"Initializing SentenceTransformer with device: {self.device}")
            self._model = SentenceTransformer(
                model_to_load,
                device=self.device,
            )
            self._loaded = True
            self._model_initialized = True
            logger.info(f"Embedding model loaded successfully: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._loaded = False
            raise

    async def unload(self) -> None:
        """Unload model and free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False
            logger.info("Embedding model unloaded")

    def encode(
        self,
        text: Union[str, List[str]],
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode text to embedding vector.

        Args:
            text: Single text string or list of texts
            normalize: Whether to normalize vectors to unit length

        Returns:
            Embedding vector or matrix
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        try:
            embedding = self._model.encode(
                text,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            return embedding
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if not self._loaded:
            return 0
        return self._model.get_sentence_embedding_dimension()

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded


class VLLMEmbeddingModel(EmbeddingModel):
    """
    vLLM-based embedding model wrapper (alternative).

    Uses vLLM server for high-throughput inference.
    """

    def __init__(self, vllm_url: Optional[str] = None):
        """Initialize vLLM embedding client."""
        super().__init__(
            model_name="vllm",
            model_path=vllm_url,
        )
        self._http_client = None
        self._model_initialized = False

    async def load(self) -> None:
        """Initialize HTTP client to vLLM server."""
        import httpx

        self._http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("vLLM embedding client initialized")

    async def unload(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()

    async def encode(self, text: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """Encode text using vLLM server."""
        import httpx
        import json

        if not self._http_client:
            raise RuntimeError("HTTP client not initialized. Call load() first.")

        # vLLM embeddings API endpoint
        url = f"{self.model_path}/v1/embeddings"

        # Prepare request
        texts_list = [text] if isinstance(text, str) else text
        request_data = {
            "model": self.model_name,
            "input": texts_list,
        }

        try:
            response = await self._http_client.post(
                url,
                json=request_data,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()

            # Extract embeddings from response
            # vLLM OpenAI-compatible API format
            if "data" in data:
                embeddings = [item["embedding"] for item in data["data"]]
            else:
                raise ValueError(f"Unexpected response format: {data}")

            # Normalize if requested
            if normalize:
                import numpy as np
                embeddings = [emb / np.linalg.norm(emb) for emb in embeddings]

            # Return single embedding or matrix
            if isinstance(text, str):
                return np.array(embeddings[0], dtype=np.float32)
            return np.vstack(embeddings).astype(np.float32)

        except httpx.HTTPError as e:
            logger.error(f"vLLM API error: {e}")
            raise RuntimeError(f"vLLM embedding request failed: {e}")
        except Exception as e:
            logger.error(f"Error encoding with vLLM: {e}")
            raise


class SimpleEmbeddingModel:
    """
    Simple embedding model using TF-IDF or similar.
    Placeholder for when model loading fails.
    """

    def __init__(self):
        """Initialize simple embedding model."""
        self._model = None
        self._loaded = False
        self._model_initialized = False
        logger.warning("Using SimpleEmbeddingModel - semantic matching disabled")

    async def load(self) -> None:
        """Initialize (placeholder)."""
        self._loaded = True
        logger.info("Simple embedding model initialized (TF-IDF fallback)")

    async def unload(self) -> None:
        """Cleanup (placeholder)."""
        self._model = None
        self._loaded = False

    def encode(self, text: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """Encode text using TF-IDF (fallback)."""
        logger.warning("SimpleEmbeddingModel.encode() called - returning mock embedding")
        # Return mock embedding for compatibility
        text_list = [text] if isinstance(text, str) else text
        # Simple TF-IDF like hash-based embedding (for demonstration)
        import hashlib
        import numpy as np

        embeddings = []
        for t in text_list:
            # Create a hash-based "embedding" vector (simplified)
            hash_val = int(hashlib.md5(t.encode()).hexdigest()[:16], 16)
            # Generate pseudo-random vector from hash value
            np.random.seed(hash_val % (2**32))
            vec = np.random.rand(128).astype(np.float32)
            embeddings.append(vec)

        if len(embeddings) == 1:
            return embeddings[0]
        return np.vstack(embeddings)

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return 128

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded


def get_embedding_model() -> EmbeddingModel:
    """Get or create global embedding model instance."""
    global _global_embedding_model
    if _global_embedding_model is None:
        _global_embedding_model = EmbeddingModel()
    return _global_embedding_model


def get_embedding_model_status() -> dict:
    """
    Get embedding model loading status.
    
    Returns:
        Dict containing model status information
    """
    global _global_embedding_model
    
    if _global_embedding_model is None:
        return {
            "loaded": False,
            "model_name": None,
            "model_path": None,
            "device": None,
            "dimension": 0,
            "initialized": False
        }
    
    return {
        "loaded": _global_embedding_model.is_loaded,
        "model_name": _global_embedding_model.model_name,
        "model_path": _global_embedding_model.model_path,
        "device": _global_embedding_model.device,
        "dimension": _global_embedding_model.dimension,
        "initialized": _global_embedding_model._model_initialized
    }
