"""LLM client module for handling interactions with different LLM providers."""
import os
import logging
from typing import Dict, Any, Optional, List, Union
import httpx
from openai import AsyncOpenAI

from app.core.config import settings

# 로거 설정
logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with different LLM providers."""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self._client = None
        self._http_client = None
        
    async def initialize(self):
        """Initialize the LLM client based on the configured provider."""
        if self._client is not None:
            return
            
        if self.provider == "openrouter":
            if not settings.OPENROUTER_API_KEY:
                raise ValueError("OpenRouter API key is required when using OpenRouter provider")
                
            # Create custom HTTP client with required headers
            self._http_client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://logy-desk.app",  # Your app's URL
                    "X-Title": "Logy-Desk",  # Your app name
                    "Content-Type": "application/json"
                }
            )
            
            # Initialize OpenAI client with the custom HTTP client
            self._client = AsyncOpenAI(
                base_url=settings.OPENROUTER_BASE_URL,
                api_key=settings.OPENROUTER_API_KEY,
                http_client=self._http_client
            )
            print(f"[DEBUG] Initialized OpenRouter client with model: {settings.OPENROUTER_MODEL}")
        else:  # Default to OpenAI
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is required when using OpenAI provider")
                
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            print(f"[DEBUG] Initialized OpenAI client with model: {settings.OPENAI_MODEL}")
    
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
        if self._client is None:
            await self.initialize()
            
        try:
            # 요청 파라미터 준비
            temperature = min(max(temperature, 0.0), 2.0)  # 0.0 ~ 2.0 범위로 제한
            max_tokens = min(max_tokens, 2000)  # 최대 2000 토큰으로 제한
            
            logger.info(f"Generating chat response with {self.provider} model: {self.get_model_name()}")
            
            # API 호출
            response = await self._client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 응답에서 텍스트 추출
            response_text = response.choices[0].message.content
            logger.debug(f"LLM response: {response_text[:200]}..." if len(response_text) > 200 else f"LLM response: {response_text}")
            
            return response_text
            
        except Exception as e:
            error_msg = f"채팅 응답 생성 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
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
