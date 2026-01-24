"""Embedding provider for generating vector embeddings from text."""
import httpx
from typing import List, Optional

from app.config.settings import get_settings


class EmbeddingProvider:
    """
    Ollama embedding provider using the /api/embed endpoint.
    
    Generates vector embeddings from text descriptions for semantic search.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_embedding_model
        self.timeout = timeout or settings.ollama_embedding_timeout
        
        # Async HTTP client
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of float values representing the embedding vector
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "input": text,
        }
        
        response = await client.post("/api/embed", json=payload)
        response.raise_for_status()
        
        data = response.json()
        embeddings = data.get("embeddings", [])
        
        if not embeddings or not embeddings[0]:
            raise ValueError(f"No embedding returned for text: {text[:50]}...")
        
        return embeddings[0]
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is running and responsive.
        
        Uses the /api/tags endpoint to verify connection.
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_embedding_dim(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            The dimension of the embedding vectors
        """
        # Generate a test embedding to determine dimension
        test_embedding = await self.embed("test")
        return len(test_embedding)
