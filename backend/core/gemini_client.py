"""Google Gemini API client."""
import os
import google.generativeai as genai
from typing import Optional, AsyncGenerator

from core.settings import settings
from core.logging import get_logger

logger = get_logger("gemini")


def configure_gemini() -> None:
    """Configure Gemini API with API key from settings."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    genai.configure(api_key=settings.gemini_api_key)


async def generate_text(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Generate text using Gemini API.
    
    Args:
        system_prompt: System prompt defining agent behavior
        user_input: User input/message
        model: Gemini model to use
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Generated text response
    """
    configure_gemini()
    
    # Create model with configuration
    generation_config = {
        "temperature": temperature,
    }
    if max_tokens:
        generation_config["max_output_tokens"] = max_tokens
    
    try:
        model_client = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        # Combine system prompt and user input
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        
        # Generate response
        response = model_client.generate_content(full_prompt)
        
        return response.text or ""
        
    except Exception as e:
        logger.error("gemini_error", error=str(e), model=model)
        raise


async def generate_streaming(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """
    Generate text with streaming support.
    
    Yields chunks of text as they're generated.
    """
    configure_gemini()
    
    generation_config = {
        "temperature": temperature,
    }
    
    try:
        model_client = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        
        response = model_client.generate_content(
            full_prompt,
            stream=True,
        )
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        logger.error("gemini_streaming_error", error=str(e), model=model)
        raise


