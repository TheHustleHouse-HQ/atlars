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
                        
                    # 400-level errors (except 429 Too Many Requests) shouldn't be retried
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        logger.error(f"OpenRouter Client Error (status {response.status_code}): {response.text}")
                        raise Exception(f"OpenRouter Client Error {response.status_code}: {response.text}")
                    
                    # 500-level or 429
                    logger.warning(f"OpenRouter Server/RateLimit Error (status {response.status_code}): {response.text}")
                        
                except httpx.RequestError as exc:
                    logger.warning(f"Network error while requesting OpenRouter API: {exc}")
                
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying OpenRouter API in {backoff} seconds (Attempt {attempt + 1}/{MAX_RETRIES})...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    
        raise Exception(f"Failed to generate embedding from OpenRouter after {MAX_RETRIES} attempts.")

    async def create_chat_completion(
        self, messages: List[dict], model: str, response_format: Optional[dict] = None, reasoning: Optional[dict] = None
    ) -> dict:
        """
        Creates a chat completion using the OpenRouter API.
        Implements a simple exponential backoff for retries.
        """
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. Returning empty response for development.")
            return {}

        from typing import Any
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if response_format:
            payload["response_format"] = response_format
        if reasoning:
            payload["reasoning"] = reasoning
        
        backoff = INITIAL_BACKOFF
        
        # Chat completions can take longer, so we use a 60s timeout
        chat_timeout = httpx.Timeout(60.0, connect=5.0)
        async with httpx.AsyncClient(timeout=chat_timeout) as client:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                        
                    # Handle Rate Limits with Retry-After if available
                    if response.status_code == 429:
                        logger.warning(f"OpenRouter Rate Limited (429). Attempt {attempt}/{MAX_RETRIES}")
                    # Fast fail on other 4xx errors
                    elif 400 <= response.status_code < 500:
                        logger.error(f"OpenRouter Client Error (status {response.status_code}): {response.text}")
                        raise ValueError(f"OpenRouter Client Error {response.status_code}: {response.text}")
                    else:
                        logger.warning(f"OpenRouter Server Error (status {response.status_code}): {response.text}")
                        
                except httpx.RequestError as exc:
                    logger.warning(f"Network error while requesting OpenRouter API: {exc}")
                except ValueError as exc:
                    raise exc # Re-raise client errors immediately without retrying
                
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying OpenRouter API in {backoff} seconds (Attempt {attempt + 1}/{MAX_RETRIES})...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    
        raise Exception(f"Failed to generate chat completion from OpenRouter after {MAX_RETRIES} attempts.")

# Create a singleton client to be used across the app
openrouter_client = OpenRouterClient()
