"""OpenAI-compatible LLM client supporting local engines and cloud endpoints."""

import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import openai

logger = logging.getLogger(__name__)

DEFAULT_MODEL: str = "gpt-4o"
DEFAULT_TIMEOUT_SEC: float = 60.0
MAX_RETRIES: int = 3
INITIAL_BACKOFF_SEC: float = 2.0


class OpenAICompatibleClient:
    """Client for generating completions using OpenAI-compatible API endpoints."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        """Initialize client with credentials and endpoint configuration."""
        self.model = model
        self.timeout = timeout
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not resolved_key:
            logger.warning(
                "No API key provided and OPENAI_API_KEY is not set. Local endpoints without auth may work."
            )

        resolved_base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._client = openai.OpenAI(
            api_key=resolved_key or "EMPTY",
            base_url=resolved_base_url,
            timeout=timeout,
        )

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Tuple[str, int, int]:
        """Send chat completion request with automatic retry and exponential backoff.

        Args:
            messages: List of chat message dictionaries with 'role' and 'content'.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in completion response.

        Returns:
            Tuple of (completion_text, prompt_tokens, completion_tokens).

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        backoff = INITIAL_BACKOFF_SEC
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = response.choices[0].message.content or ""
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                return text, prompt_tokens, completion_tokens

            except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError) as e:
                last_error = e
                logger.warning(
                    "LLM request attempt %d failed with transient error: %s. Backing off for %.1fs...",
                    attempt,
                    str(e),
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2.0
            except openai.APIError as e:
                # Fatal or non-transient API error
                logger.error("LLM API error: %s", str(e))
                raise RuntimeError(f"OpenAI API fatal error: {str(e)}") from e
            except Exception as e:
                logger.error("Unexpected error during LLM invocation: %s", str(e))
                raise RuntimeError(f"Failed to query LLM: {str(e)}") from e

        raise RuntimeError(f"LLM request exceeded {MAX_RETRIES} retries. Last error: {last_error}")
