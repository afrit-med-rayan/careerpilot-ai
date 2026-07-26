import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T", bound=BaseModel)

class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass


def _get_client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set.")
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


async def generate_structured_json(
    prompt: str,
    schema_model: Type[T],
    system_prompt: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.0,
    model: str = "claude-3-5-sonnet-latest",
) -> T:
    """
    Calls Anthropic API to generate structured JSON matching a Pydantic model.
    Includes 1 automatic retry on JSON parse or validation failure.
    """
    client = _get_client()
    
    # We enforce the JSON structure by passing the schema in the prompt
    schema_json = schema_model.model_json_schema()
    
    system_instruction = system_prompt or "You are a helpful AI assistant."
    system_instruction += (
        "\n\nOnly use facts present in the provided context. "
        "Never invent employers, job titles, dates, or metrics. "
        "If information needed to fully answer is missing, state that explicitly rather than fabricating it."
    )
    
    full_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: You MUST respond ONLY with valid JSON that strictly conforms "
        "to the following JSON schema. Do not include any markdown formatting "
        "like ```json or any conversational text before or after the JSON.\n\n"
        f"{json.dumps(schema_json, indent=2)}"
    )

    if settings.debug_log_llm:
        logger.info("=== LLM Request ===")
        logger.info(f"System: {system_instruction}")
        logger.info(f"Prompt: {full_prompt}")

    async def _call() -> str:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_instruction,
            messages=[{"role": "user", "content": full_prompt}]
        )
        # Type check to satisfy mypy, though we expect a text block
        if hasattr(response.content[0], "text"):
            return response.content[0].text
        raise LLMError("Unexpected response format from Anthropic API")

    # Attempt 1
    raw_response = ""
    try:
        raw_response = await _call()
        if settings.debug_log_llm:
            logger.info("=== LLM Response ===")
            logger.info(raw_response)
            
        parsed_dict = json.loads(raw_response.strip())
        return schema_model.model_validate(parsed_dict)
    
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"LLM Parsing failed on attempt 1: {e}. Retrying once.")
        
        # Attempt 2 (Retry)
        retry_prompt = (
            f"Your previous response failed validation with this error:\n{str(e)}\n\n"
            "Please try again. Remember to output ONLY valid JSON matching the schema."
        )
        
        full_prompt = full_prompt + f"\n\nAssistant: {raw_response}\n\nUser: {retry_prompt}"
        
        try:
            raw_response_retry = await _call()
            parsed_dict_retry = json.loads(raw_response_retry.strip())
            return schema_model.model_validate(parsed_dict_retry)
        except Exception as e_retry:
            logger.error(f"LLM Parsing failed on retry: {e_retry}")
            raise LLMError(f"Failed to generate valid structured data: {e_retry}") from e_retry
