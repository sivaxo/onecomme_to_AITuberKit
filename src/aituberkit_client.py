"""Client utilities for interacting with AITuberKit REST API."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Tuple

import requests

from .config import Config


class AITuberKitClient:
    """HTTP client for the AITuberKit external adapter."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(__name__)

    async def health_check(self) -> bool:
        """Perform a simple GET request to confirm connectivity."""

        def _get() -> bool:
            try:
                response = requests.get(
                    self._config.aituberkit_base_url,
                    timeout=self._config.aituberkit_timeout,
                )
                return response.ok
            except Exception as exc:
                self._logger.warning("AITuberKit health check failed: %s", exc)
                return False

        return await asyncio.to_thread(_get)

    async def send_prompt(self, prompt: str, *, system_prompt: Optional[str] = None) -> Tuple[str, float]:
        """Send prompt to AITuberKit for generation. Returns response text and elapsed time."""

        def _post() -> Tuple[str, float]:
            params = {
                "clientId": self._config.aituberkit_client_id,
                "type": "ai_generate",
            }
            payload: dict = {
                "useCurrentSystemPrompt": self._config.use_aituberkit_system_prompt,
                "messages": [prompt],
            }
            if system_prompt is not None:
                payload["systemPrompt"] = system_prompt

            start = time.perf_counter()
            response = requests.post(
                self._config.aituberkit_messages_url,
                params=params,
                json=payload,
                timeout=self._config.aituberkit_timeout,
            )
            elapsed = time.perf_counter() - start
            response.raise_for_status()
            try:
                data = response.json()
                if isinstance(data, dict) and "message" in data:
                    return str(data["message"]), elapsed
            except ValueError:
                pass
            return response.text, elapsed

        return await asyncio.to_thread(_post)

    async def classify(self, prompt: str) -> str:
        """Request classification (YES/NO) from AITuberKit."""

        response_text, _ = await self.send_prompt(prompt)
        return response_text.strip()
