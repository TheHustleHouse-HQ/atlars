import asyncio
import httpx
import logging
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0


class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",  # Required by OpenRouter for ranking
            "X-Title": "Atlars Backend",             # Optional OpenRouter param
            "Content-Type": "application/json"
        }
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def create_embedding(self, text: str, model: str) -> List[float]:
        """
        Creates an embedding for a given text using the OpenRouter API.
        Implements a simple exponential backoff for retries.
        """
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. Returning empty embedding for development.")
            return []

        payload = {
            "model": model,
            "input": text
        }
        
        backoff = INITIAL_BACKOFF
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        f"{OPENROUTER_BASE_URL}/embeddings",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data["data"][0]["embedding"]
                    
                    # Log error details if it's not a 200
                    logger.error(f"OpenRouter API error (status {response.status_code}): {response.text}")
                    
                    # Don't retry on 4xx client errors, only 5xx server errors or rate limits (429)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        raise Exception(f"OpenRouter client error {response.status_code}: {response.text}")
                        
                except httpx.RequestError as exc:
                    logger.error(f"An error occurred while requesting OpenRouter API: {exc}")
                
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying OpenRouter API in {backoff} seconds (Attempt {attempt + 1}/{MAX_RETRIES})...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    
        raise Exception(f"Failed to generate embedding from OpenRouter after {MAX_RETRIES} attempts.")

# Create a singleton client to be used across the app
openrouter_client = OpenRouterClient()
