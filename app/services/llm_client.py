"""LLM client module for handling interactions with different LLM providers."""

import asyncio
import json
import logging
from typing import Dict, List

import httpx
from openai import AsyncOpenAI
from app.core.config import settings

DEFAULT_MODEL = "google/gemma-3-27b-it:free"

# Configure root logger if not already configured
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
    )

# Get logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure debug level is set for this logger


class LLMClient:
    """Client for interacting with different LLM providers."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self._client = None
        self._http_client = None
        self._current_model = settings.OPENROUTER_MODEL
        # Multiple fallback models in order of preference
        self._fallback_models = [
            "google/gemma-3-27b-it:free",
            "google/gemini-2.5-flash",
            "anthropic/claude-3.5-haiku",
            "openai/gpt-4.1-mini",
            "openai/gpt-4o-mini",
        ]
        self._max_retries = 3
        self._retry_delay = 1.0  # seconds

    async def initialize(self):
        """Initialize the LLM client based on the configured provider."""
        logger.debug("Initializing LLM client...")

        if self._client is not None:
            logger.debug("LLM client already initialized, skipping initialization")
            return

        try:
            if self.provider == "openrouter":
                logger.info(
                    "Initializing OpenRouter client with model: " f"{settings.OPENROUTER_MODEL}"
                )

                if not settings.OPENROUTER_API_KEY:
                    error_msg = "OpenRouter API key is required when using OpenRouter provider"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug("Creating custom HTTP client for OpenRouter")
                # Create custom HTTP client with required headers
                self._http_client = httpx.AsyncClient(
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://logy-desk.app",  # Your app's URL
                        "X-Title": "Logy-Desk",  # Your app name
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,  # Add timeout to prevent hanging
                )

                # Initialize OpenAI client with the custom HTTP client
                logger.debug("Initializing AsyncOpenAI client for OpenRouter")
                self._client = AsyncOpenAI(
                    base_url=settings.OPENROUTER_BASE_URL,
                    api_key=settings.OPENROUTER_API_KEY,
                    http_client=self._http_client,
                )
                logger.info(
                    "Successfully initialized OpenRouter client with model: "
                    f"{settings.OPENROUTER_MODEL}"
                )

            else:  # Default to OpenAI
                logger.info(f"Initializing OpenAI client with model: {settings.OPENAI_MODEL}")

                if not settings.OPENAI_API_KEY:
                    error_msg = "OpenAI API key is required when using OpenAI provider"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug("Initializing standard OpenAI client")
                self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info(
                    "Successfully initialized OpenAI client with model: " f"{settings.OPENAI_MODEL}"
                )

        except Exception as e:
            logger.error(f"Error initializing LLM client: {str(e)}", exc_info=True)
            raise

    def get_model_name(self) -> str:
        """Get the configured model name for the current provider."""
        if self.provider == "openrouter":
            return settings.OPENROUTER_MODEL
        return settings.OPENAI_MODEL

    async def _call_llm_api(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Internal method to call the LLM API with a specific model."""
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response content from LLM API")

            return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"API call to {model} failed: {str(e)}")
            raise

    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        retry_count: int = 0,
    ) -> str:
        """
        단순 채팅 응답을 생성합니다.

        Args:
            messages: 메시지 리스트 (role과 content 키를 가진 딕셔너리)
            temperature: 샘플링 온도 (0.0 ~ 2.0)
            max_tokens: 생성할 최대 토큰 수
            retry_count: 현재 재시도 횟수 (내부용)

        Returns:
            생성된 응답 텍스트

        Raises:
            ValueError: 채팅 응답 생성에 실패한 경우
        """
        if not self._client:
            await self.initialize()

        # Validate input
        if not messages or not isinstance(messages, list):
            raise ValueError("Messages must be a non-empty list")

        # Ensure parameters are within valid ranges
        temperature = max(0.0, min(2.0, temperature))
        max_tokens = min(max_tokens, 2000)

        current_model = self.get_model_name()

        # Log the request
        logger.info(f"Generating chat response with {self.provider} model: {current_model}")
        try:
            messages_preview = [
                {
                    k: (v[:100] + "..." if k == "content" and len(str(v)) > 100 else v)
                    for k, v in msg.items()
                }
                for msg in messages
            ]
            logger.debug(
                "Sending messages to LLM: "
                f"{json.dumps(messages_preview, ensure_ascii=False, indent=2)}"
            )
        except Exception as e:
            logger.warning(f"Could not log message preview: {str(e)}")

        # Try the current model first
        last_error = None

        # Keep track of models we've already tried to prevent infinite loops
        if not hasattr(self, "_tried_models"):
            self._tried_models = set()

        # Get the current model and fallback models
        models_to_try = [current_model]
        if hasattr(self, "_fallback_models"):
            models_to_try.extend([m for m in self._fallback_models if m not in self._tried_models])

        for model in models_to_try:
            if model in self._tried_models:
                continue

            self._tried_models.add(model)
            self._current_model = model
            logger.info(f"Trying model: {model}")

            # Retry logic for each model
            for attempt in range(self._max_retries):
                try:
                    response_text = await self._call_llm_api(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    # Log success
                    response_preview = response_text[:200] + (
                        "..." if len(response_text) > 200 else ""
                    )
                    logger.debug(f"Received LLM response: {response_preview}")
                    logger.info(f"Successfully generated chat response from {model}")

                    return response_text

                except Exception as e:
                    last_error = e
                    if attempt < self._max_retries - 1:
                        retry_delay = self._retry_delay * (2**attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed for model {model}: "
                            f"{str(e)}. Retrying in {retry_delay:.1f}s..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"All {self._max_retries} attempts failed for model {model}")

        # If we get here, all models and retries failed
        error_msg = (
            f"Failed to generate chat response after trying {len(self._tried_models)} "
            f"models and {self._max_retries} retries each"
        )
        if last_error:
            error_msg += f": {str(last_error)}"

        logger.error(error_msg)
        return "죄송합니다. AI 응답을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    async def close(self):
        """Close the client connection."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

        if self._client is not None:
            if hasattr(self._client, "close"):
                await self._client.close()
            self._client = None


# Singleton instance
llm_client = LLMClient()


# Helper function for backward compatibility
async def get_llm_client() -> LLMClient:
    """Get the LLM client instance."""
    await llm_client.initialize()
    return llm_client
