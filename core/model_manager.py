"""
ModelManager — handles LLM communication supporting both:
  1. Local Ollama instances with VRAM-safe arbitration and real-time streaming.
  2. Custom / Remote OpenAI-compatible endpoints (vLLM, LMStudio, OpenRouter, DeepSeek, Together, Groq, etc.).
"""

import asyncio
import json
import time
from typing import Optional, Type, Union, Dict, Any, Callable

import httpx
from pydantic import BaseModel

from aether.config.settings import settings
from aether.core.logger import logger
from aether.core.events import event_bus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _NullLock:
    """No-op async context manager — replaces heavy lock for lightweight or cloud models."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        pass


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ModelManager:
    """
    Unified LLM Controller with VRAM protection, stream broadcasting,
    and hybrid provider support (Ollama & OpenAI-Compatible Custom APIs).
    """

    def __init__(self):
        self._heavy_model_lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None
        self._current_base_url: Optional[str] = None
        self.current_telemetry: Dict[str, Any] = {
            "active_model": None,
            "role": "Ready",
            "provider": getattr(settings, "LLM_PROVIDER", "ollama"),
            "vram_locked": False,
            "status": "ready",
            "last_latency": 0.0,
        }

    def _get_client(self) -> httpx.AsyncClient:
        provider = getattr(settings, "LLM_PROVIDER", "ollama").lower()
        if provider == "openai_compatible":
            base_url = settings.CUSTOM_API_BASE_URL.rstrip("/")
            headers = {"Content-Type": "application/json"}
            if settings.CUSTOM_API_KEY:
                headers["Authorization"] = f"Bearer {settings.CUSTOM_API_KEY}"
        else:
            base_url = settings.OLLAMA_BASE_URL.rstrip("/")
            headers = {}

        if self._client is None or self._client.is_closed or self._current_base_url != base_url:
            self._current_base_url = base_url
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers=headers,
                timeout=httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=10.0),
            )
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call_model(
        self,
        prompt: str,
        model: Optional[str] = None,
        response_format: Optional[Type[BaseModel]] = None,
        temperature: float = 0.7,
        is_heavy: bool = False,
        task_label: str = "Reasoning",
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Union[str, BaseModel]:
        """
        Dispatches request to LLM (Ollama or OpenAI-Compatible Custom API)
        with VRAM locking and real-time streaming.
        """
        provider = getattr(settings, "LLM_PROVIDER", "ollama").lower()
        target_model = model or settings.MODEL_FAST

        # Local VRAM locking only applies to local Ollama on heavy models
        heavy_models = {
            settings.MODEL_DEEP,
            settings.MODEL_DEEP_31B,
            settings.MODEL_CRITIC,
            settings.MODEL_DEEP_FALLBACK,
        }
        use_lock = (provider == "ollama") and (is_heavy or target_model in heavy_models)

        # Role mapping for HUD
        if target_model == settings.MODEL_DEEP:
            role_name = "Deep Abductive Reasoning"
        elif target_model == settings.MODEL_DEEP_31B:
            role_name = "Heavy Reasoning Fallback"
        elif target_model == settings.MODEL_CRITIC:
            role_name = "Adversarial Refutation Critic"
        elif target_model == settings.MODEL_FAST:
            role_name = "Fast Heuristic Planner"
        elif target_model == settings.MODEL_AGGRESSIVE_FAST:
            role_name = "Aggressive Tool Extractor"
        elif target_model == settings.MODEL_VLM:
            role_name = "Vision / OCR Engine"
        else:
            role_name = "Neural Engine"

        short_name = target_model.split("/")[-1].split(":")[0]

        start_time = time.time()
        self.current_telemetry = {
            "active_model": short_name,
            "full_model": target_model,
            "provider": provider,
            "role": role_name,
            "task_label": task_label,
            "vram_locked": use_lock,
            "status": "inferencing",
            "prompt_preview": prompt[:160] + "..." if len(prompt) > 160 else prompt,
        }
        await event_bus.emit_global({
            "type": "model_telemetry",
            "data": self.current_telemetry,
        })

        lock = self._heavy_model_lock if use_lock else _NullLock()

        async with lock:
            if use_lock:
                self.current_telemetry["vram_locked"] = True
                await event_bus.emit_global({
                    "type": "model_telemetry",
                    "data": self.current_telemetry,
                })

            if provider == "openai_compatible":
                result = await self._call_openai_compatible(
                    target_model, prompt, response_format, temperature, on_token
                )
            else:
                result = await self._call_ollama(
                    target_model, prompt, response_format, temperature, on_token
                )

        latency = round(time.time() - start_time, 2)
        self.current_telemetry["status"] = "idle"
        self.current_telemetry["vram_locked"] = False
        self.current_telemetry["last_latency"] = latency

        await event_bus.emit_global({
            "type": "model_telemetry",
            "data": self.current_telemetry,
        })

        return result

    # ------------------------------------------------------------------
    # Ollama Streaming
    # ------------------------------------------------------------------

    async def _call_ollama(
        self,
        target_model: str,
        prompt: str,
        response_format: Optional[Type[BaseModel]],
        temperature: float,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Union[str, BaseModel]:
        client = self._get_client()
        payload: dict = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "15m",
            "options": {"temperature": temperature},
        }

        if response_format is not None:
            payload["format"] = "json"

        short_model = target_model.split("/")[-1].split(":")[0]
        collected_tokens = []

        try:
            async with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            collected_tokens.append(token)
                            if on_token:
                                on_token(token)
                            if len(collected_tokens) % 3 == 0 or chunk.get("done", False):
                                current_text = "".join(collected_tokens)
                                await event_bus.emit_global({
                                    "type": "ai_thought_stream",
                                    "data": {
                                        "model": short_model,
                                        "thought": current_text[-400:],
                                        "full_preview": current_text[:400],
                                    },
                                })
                    except Exception:
                        continue

            raw_text = "".join(collected_tokens)

            await event_bus.emit_global({
                "type": "ai_thought_stream",
                "data": {
                    "model": short_model,
                    "thought": raw_text[:500],
                },
            })

            if response_format is not None:
                return self._parse_json(raw_text, response_format)
            return raw_text

        except Exception as exc:
            logger.error(f"Ollama Model {target_model} failed: {exc}")
            if target_model == settings.MODEL_DEEP:
                logger.warning(f"Falling back to {settings.MODEL_DEEP_FALLBACK}")
                return await self._call_ollama(
                    settings.MODEL_DEEP_FALLBACK, prompt, response_format, temperature, on_token
                )
            raise

    # ------------------------------------------------------------------
    # Custom / OpenAI-Compatible API Streaming
    # ------------------------------------------------------------------

    async def _call_openai_compatible(
        self,
        target_model: str,
        prompt: str,
        response_format: Optional[Type[BaseModel]],
        temperature: float,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> Union[str, BaseModel]:
        client = self._get_client()
        payload: dict = {
            "model": target_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "stream": True,
        }

        if response_format is not None:
            payload["response_format"] = {"type": "json_object"}

        short_model = target_model.split("/")[-1].split(":")[0]
        collected_tokens = []

        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    collected_tokens.append(token)
                                    if on_token:
                                        on_token(token)
                                    if len(collected_tokens) % 3 == 0:
                                        current_text = "".join(collected_tokens)
                                        await event_bus.emit_global({
                                            "type": "ai_thought_stream",
                                            "data": {
                                                "model": short_model,
                                                "thought": current_text[-400:],
                                                "full_preview": current_text[:400],
                                            },
                                        })
                        except Exception:
                            continue

            raw_text = "".join(collected_tokens)

            await event_bus.emit_global({
                "type": "ai_thought_stream",
                "data": {
                    "model": short_model,
                    "thought": raw_text[:500],
                },
            })

            if response_format is not None:
                return self._parse_json(raw_text, response_format)
            return raw_text

        except Exception as exc:
            logger.error(f"Custom OpenAI API model {target_model} failed: {exc}")
            raise

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str, schema: Type[BaseModel]) -> BaseModel:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(cleaned[start : end + 1])
            else:
                raise ValueError(f"No JSON object found in model response: {text[:200]}")

        return schema.model_validate(data)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global Singleton
model_manager = ModelManager()
