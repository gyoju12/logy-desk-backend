"""LLM client module for handling interactions with different LLM providers."""
import os

DEFAULT_MODEL = "google/gemma-3-27b-it:free"
import logging
from typing import Dict, Any, Optional, List, Union
import httpx
from openai import AsyncOpenAI

from app.core.config import settings

# Configure root logger if not already configured
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
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
        self._fallback_models = [
            "google/gemma-3-27b-it:free", 
            "google/gemma-3-27b-it:free", 
            "google/gemma-3-27b-it:free", 
            "google/gemma-3-27b-it:free", 
            "google/gemma-3-27b-it:free"
        ]
        
    async def initialize(self):
        """Initialize the LLM client based on the configured provider."""
        logger.debug("Initializing LLM client...")
        
        if self._client is not None:
            logger.debug("LLM client already initialized, skipping initialization")
            return
            
        try:
            if self.provider == "openrouter":
                logger.info(f"Initializing OpenRouter client with model: {settings.OPENROUTER_MODEL}")
                
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
                        "Content-Type": "application/json"
                    },
                    timeout=30.0  # Add timeout to prevent hanging
                )
                
                # Initialize OpenAI client with the custom HTTP client
                logger.debug("Initializing AsyncOpenAI client for OpenRouter")
                self._client = AsyncOpenAI(
                    base_url=settings.OPENROUTER_BASE_URL,
                    api_key=settings.OPENROUTER_API_KEY,
                    http_client=self._http_client
                )
                logger.info(f"Successfully initialized OpenRouter client with model: {settings.OPENROUTER_MODEL}")
                
            else:  # Default to OpenAI
                logger.info(f"Initializing OpenAI client with model: {settings.OPENAI_MODEL}")
                
                if not settings.OPENAI_API_KEY:
                    error_msg = "OpenAI API key is required when using OpenAI provider"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.debug("Initializing standard OpenAI client")
                self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info(f"Successfully initialized OpenAI client with model: {settings.OPENAI_MODEL}")
                
        except Exception as e:
            logger.error(f"Error initializing LLM client: {str(e)}", exc_info=True)
            raise
    
    def get_model_name(self) -> str:
        """Get the configured model name for the current provider."""
        if self.provider == "openrouter":
            return settings.OPENROUTER_MODEL
        return settings.OPENAI_MODEL
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        단순 채팅 응답을 생성합니다.
        
        Args:
            messages: 메시지 리스트 (role과 content 키를 가진 딕셔너리)
            temperature: 샘플링 온도 (0.0 ~ 2.0)
            max_tokens: 생성할 최대 토큰 수
            
        Returns:
            생성된 응답 텍스트
        """
        logger.debug("Starting to generate chat response")
        
        # Initialize client if needed
        if self._client is None:
            logger.debug("LLM client not initialized, initializing now...")
            await self.initialize()
        
        try:
            # Validate and prepare request parameters
            temperature = min(max(temperature, 0.0), 2.0)  # 0.0 ~ 2.0 범위로 제한
            max_tokens = min(max_tokens, 2000)  # 최대 2000 토큰으로 제한
            
            logger.info(f"Generating chat response with {self.provider} model: {self.get_model_name()}")
            logger.debug(f"Request parameters - temperature: {temperature}, max_tokens: {max_tokens}")
            logger.debug(f"Messages being sent to LLM: {messages}")
            
            # Make the API call
            logger.debug("Sending request to LLM API...")
            response = await self._client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract and log the response
            if not response.choices or not response.choices[0].message.content:
                error_msg = "Empty or invalid response from LLM API"
                logger.error(f"{error_msg}. Response: {response}")
                raise ValueError(error_msg)
            
            response_text = response.choices[0].message.content
            
            # Log a portion of the response for debugging
            response_preview = (
                response_text[:200] + "..." 
                if len(response_text) > 200 
                else response_text
            )
            logger.debug(f"Received LLM response: {response_preview}")
            logger.info("Successfully generated chat response")
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error generating chat response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(f"Failed to generate chat response: {str(e)}") from e
            return f"죄송합니다. 응답을 생성하는 중 오류가 발생했습니다: {str(e)}"

    async def close(self):
        """Close the client connection."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            
        if self._client is not None:
            if hasattr(self._client, 'close'):
                await self._client.close()
            self._client = None

# Singleton instance
llm_client = LLMClient()

# Helper function for backward compatibility
async def get_llm_client() -> LLMClient:
    """Get the LLM client instance."""
    await llm_client.initialize()
    return llm_client
