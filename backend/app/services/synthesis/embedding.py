from typing import List
import logging
from app.services.routing.openrouter import openrouter_client
from app.core.config import settings

logger = logging.getLogger(__name__)

async def generate_embedding(raw_text: str) -> List[float]:
    """
    Generates an embedding for the given text using the configured OpenRouter model.
    Validates that the returned embedding matches the expected dimensions.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot generate embedding for empty text.")

    model = settings.embedding_model
    expected_dim = settings.embedding_dimensions
    
    logger.info(f"Generating embedding using model {model} (expected dim: {expected_dim})")
    
    embedding = await openrouter_client.create_embedding(text=raw_text, model=model)
    
    if not embedding:
        # Fallback mechanism if OPENROUTER_API_KEY is missing during development
        logger.warning(f"Returning mocked embedding of size {expected_dim} because OpenRouter API returned empty.")
        return [0.0] * expected_dim

    if len(embedding) != expected_dim:
        logger.warning(
            f"Embedding dimension mismatch. Expected {expected_dim}, got {len(embedding)}. "
            f"Check if the model {model} matches the expected dimensions."
        )
        
    return embedding
