# app/llm/client.py
"""
LLM client wrapper supporting OpenAI and Ollama.
Provides unified interface for both providers.
"""
from typing import Optional, Dict, Any
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client supporting OpenAI and Ollama."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        ollama_url: Optional[str] = None,
        timeout_seconds: int = 30,
    ):
        """Initialize LLM client.

        Args:
            openai_api_key: OpenAI API key. If provided, uses OpenAI.
            ollama_url: Ollama service URL. If provided and no OpenAI key, uses Ollama.
            timeout_seconds: Request timeout in seconds.
        """
        self.openai_api_key = openai_api_key
        self.ollama_url = ollama_url
        self.timeout_seconds = timeout_seconds
        self.provider = self._determine_provider()

        if self.provider == "openai":
            try:
                import openai

                openai.api_key = openai_api_key
                self.openai_client = openai.OpenAI(api_key=openai_api_key, timeout=timeout_seconds)
            except ImportError:
                logger.warning("OpenAI library not installed, LLM calls will fail")
                self.openai_client = None
        elif self.provider == "ollama":
            import requests

            self.session = requests.Session()
        else:
            logger.warning("No LLM provider configured")

    def _determine_provider(self) -> str:
        """Determine which LLM provider to use.

        Priority: OpenAI > Ollama > None

        Returns:
            Provider name: "openai", "ollama", or "none".
        """
        if self.openai_api_key:
            return "openai"
        elif self.ollama_url:
            return "ollama"
        return "none"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.0,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate text using configured LLM provider.

        Args:
            prompt: Input prompt.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            model: Model name (uses defaults if not specified).

        Returns:
            Dict with keys: text, usage (dict with prompt_tokens, completion_tokens, total_tokens).
                On error, returns: text (error message), usage (empty).
        """
        if self.provider == "none":
            return {
                "text": "Error: No LLM provider configured. Set OPENAI_API_KEY or OLLAMA_URL.",
                "usage": {},
            }

        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature, model)
            elif self.provider == "ollama":
                return self._generate_ollama(prompt, max_tokens, temperature, model)
        except Exception as e:
            logger.error(f"Error generating text with {self.provider}: {e}")
            return {
                "text": f"Error: Failed to generate text ({str(e)[:100]})",
                "usage": {},
            }

    def _generate_openai(
        self, prompt: str, max_tokens: int, temperature: float, model: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using OpenAI API.

        Args:
            prompt: Input prompt.
            max_tokens: Maximum tokens.
            temperature: Temperature.
            model: Model name (defaults to gpt-3.5-turbo).

        Returns:
            Generation result dict.
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")

        model = model or "gpt-3.5-turbo"

        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return {
            "text": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }

    def _generate_ollama(
        self, prompt: str, max_tokens: int, temperature: float, model: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using Ollama API.

        Args:
            prompt: Input prompt.
            max_tokens: Maximum tokens.
            temperature: Temperature.
            model: Model name (defaults to mistral:latest).

        Returns:
            Generation result dict.
        """
        model = model or "mistral:latest"

        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = self.session.post(url, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()

        data = response.json()
        return {
            "text": data.get("response", "").strip(),
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
        }

    async def generate_async(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.0,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Asynchronous version of generate.

        Args:
            prompt: Input prompt.
            max_tokens: Maximum tokens.
            temperature: Temperature.
            model: Model name.

        Returns:
            Generation result dict.
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.generate(prompt, max_tokens, temperature, model)
        )
