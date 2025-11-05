# Gemini Integration

## Overview

The backend uses Google's Gemini API via the `google-generativeai` Python SDK to execute agent prompts.

## Setup

### API Key Configuration

Store your Gemini API key in `backend/.env`:

```bash
GEMINI_API_KEY=your_api_key_here
```

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### Installation

```bash
pip install google-generativeai
```

## Basic Usage

### Client Setup

```python
# backend/core/gemini_client.py
import os
import google.generativeai as genai
from typing import Optional


def configure_gemini() -> None:
    """Configure Gemini API with API key from environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    genai.configure(api_key=api_key)


def generate_text(
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
    
    model_client = genai.GenerativeModel(
        model_name=model,
        generation_config=generation_config,
    )
    
    # Combine system prompt and user input
    full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
    
    # Generate response
    response = model_client.generate_content(full_prompt)
    
    return response.text or ""


def generate_streaming(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
):
    """
    Generate text with streaming support.
    
    Yields chunks of text as they're generated.
    """
    configure_gemini()
    
    generation_config = {
        "temperature": temperature,
    }
    
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
```

## Available Models

- `gemini-2.5-pro`: Best for complex reasoning tasks (recommended for advanced use cases)
- `gemini-2.5-flash`: Faster, cost-effective, good for most tasks (recommended default)

## Error Handling

```python
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse


def safe_generate_text(
    system_prompt: str,
    user_input: str,
    model: str = "gemini-2.5-flash",
) -> tuple[str, Optional[str]]:
    """
    Safely generate text with error handling.
    
    Returns:
        Tuple of (response_text, error_message)
    """
    try:
        configure_gemini()
        model_client = genai.GenerativeModel(model_name=model)
        full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
        response = model_client.generate_content(full_prompt)
        return (response.text or "", None)
    except Exception as e:
        return ("", str(e))
```

## Conversation Context

For multi-turn conversations, maintain chat history:

```python
def generate_with_history(
    system_prompt: str,
    messages: list[dict[str, str]],
    model: str = "gemini-2.5-flash",
) -> str:
    """Generate response with conversation history."""
    configure_gemini()
    
    model_client = genai.GenerativeModel(model_name=model)
    
    # Start chat with system prompt
    chat = model_client.start_chat(
        history=[{"role": "system", "parts": [system_prompt]}]
    )
    
    # Send messages in order
    for msg in messages:
        chat.send_message(msg["content"])
    
    # Get final response
    response = chat.send_message(messages[-1]["content"])
    return response.text or ""
```

## Tool Integration (Future)

When implementing tool calling:

```python
# Define tools
tools = [
    {
        "function_declarations": [
            {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        ]
    }
]

# Use with model
model_client = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    tools=tools,
)
```

## Rate Limiting

Implement rate limiting to avoid hitting API quotas:

```python
from time import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
    
    def can_make_request(self) -> bool:
        now = time()
        # Remove old requests
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True
```

## Cost Considerations

- **Gemini 1.5 Pro**: ~$0.00125 per 1K input tokens, ~$0.005 per 1K output tokens
- **Gemini 1.5 Flash**: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens

Monitor usage and implement cost controls:
- Set max tokens per request
- Implement user quotas
- Log token usage per run

## Best Practices

1. **Always configure API key on startup**: Fail fast if key is missing
2. **Use appropriate models**: Flash for simple tasks, Pro for complex reasoning
3. **Set reasonable temperature**: 0.7 for creativity, 0.3 for consistency
4. **Handle errors gracefully**: Network issues, API errors, rate limits
5. **Log token usage**: Track costs and optimize prompts
6. **Stream when possible**: Better UX for long responses
7. **Validate responses**: Check for empty or malformed outputs

