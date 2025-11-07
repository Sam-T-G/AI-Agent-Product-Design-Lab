"""Google Gemini API client."""
import os
import google.generativeai as genai
from typing import Optional, AsyncGenerator

from core.settings import settings
from core.logging import get_logger

logger = get_logger("gemini")


def configure_gemini(api_key: Optional[str] = None) -> None:
    """Configure Gemini API with API key from settings."""
    key = api_key or settings.gemini_api_key
    if not key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    genai.configure(api_key=key)


async def generate_text(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
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
    configure_gemini(api_key)
    
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


async def generate_text(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> str:
    """
    Generate text without streaming (for internal processing).
    
    Args:
        system_prompt: System prompt defining behavior
        user_input: User input/message
        model: Gemini model to use
        temperature: Sampling temperature (0-1)
        api_key: Optional API key override
        
    Returns:
        Complete generated text
    """
    configure_gemini(api_key)
    
    generation_config = {
        "temperature": temperature,
    }
    
    try:
        model_client = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        response = model_client.generate_content(full_prompt)
        
        if hasattr(response, 'text') and response.text:
            return response.text
        elif hasattr(response, 'parts') and response.parts:
            text_parts = []
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
            return "".join(text_parts)
        else:
            logger.warning("gemini_no_text_generated", model=model)
            return "[No response generated]"
            
    except Exception as e:
        logger.error("gemini_text_error", error=str(e), model=model)
        return f"[Error: {str(e)}]"


async def generate_streaming(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    images: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Generate text with streaming support.
    
    Args:
        system_prompt: System prompt defining agent behavior
        user_input: User input/message
        model: Gemini model to use (must support vision for images)
        temperature: Sampling temperature (0-1)
        api_key: Optional API key override
        images: Optional list of base64-encoded image strings
    
    Yields chunks of text as they're generated.
    """
    logger.info("gemini_generate_start", model=model, has_api_key=bool(api_key), has_images=bool(images), prompt_length=len(user_input))
    configure_gemini(api_key)
    
    generation_config = {
        "temperature": temperature,
    }

    try:
        # Use vision-capable model if images are provided
        # Both gemini-2.5-pro and gemini-2.5-flash support vision
        if images and model not in ["gemini-2.5-pro", "gemini-2.5-flash"]:
            # Switch to a vision-capable model (both 2.5 models support vision)
            if "flash" in model.lower():
                model = "gemini-2.5-flash"
            else:
                model = "gemini-2.5-pro"

        model_client = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        # Prepare content: text + images
        import base64
        import io
        from PIL import Image
        
        content_parts = []
        
        # Add images if provided
        if images:
            for img_base64 in images:
                try:
                    # Remove data URL prefix if present
                    if "," in img_base64:
                        img_base64 = img_base64.split(",")[1]
                    
                    # Decode base64 to image
                    img_data = base64.b64decode(img_base64)
                    img = Image.open(io.BytesIO(img_data))
                    content_parts.append(img)
                except Exception as e:
                    logger.warning("failed_to_process_image", error=str(e))
                    # Continue with other images
        
        # Add text prompt
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        content_parts.append(full_prompt)
        
        # Generate with streaming
        response = model_client.generate_content(
            content_parts,
            stream=True,
        )
        
        # Use asyncio to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Process chunks in a non-blocking way
        has_content = False
        chunk_count = 0
        for chunk in response:
            # Yield control back to the event loop periodically
            await asyncio.sleep(0)
            
            chunk_count += 1
            
            # Check if chunk has text content
            if hasattr(chunk, 'text') and chunk.text:
                has_content = True
                yield chunk.text
            elif hasattr(chunk, 'parts') and chunk.parts:
                # Handle parts directly if text accessor fails
                for part in chunk.parts:
                    if hasattr(part, 'text') and part.text:
                        has_content = True
                        yield part.text
        
        logger.info("gemini_generate_complete", model=model, chunk_count=chunk_count, has_content=has_content)
        
        # If no content was generated, check finish_reason
        if not has_content:
            # Try to get finish_reason from response metadata
            finish_reason = "unknown"
            try:
                if hasattr(response, '_done') and response._done:
                    if hasattr(response, 'candidates') and response.candidates:
                        finish_reason = response.candidates[0].finish_reason if response.candidates[0].finish_reason else "unknown"
            except:
                pass
            
            logger.warning(
                "gemini_no_content_generated",
                model=model,
                finish_reason=finish_reason,
                prompt_length=len(user_input),
            )
            # Yield a helpful error message instead of crashing
            yield f"[System: The AI model did not generate a response. This may be due to content filtering or the prompt being too complex. Please try rephrasing or simplifying your request.]"
                
    except Exception as e:
        logger.error("gemini_streaming_error", error=str(e), model=model)
        # Don't crash - yield error message
        yield f"[System Error: {str(e)}]"


