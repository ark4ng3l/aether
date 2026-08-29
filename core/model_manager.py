"""
ModelManager — handles all Ollama LLM communication with VRAM-safe locking
and real-time token streaming for all 6 uncensored local models on NVIDIA RTX 4070.
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
    """No-op async context manager — replaces heavy lock for lightweight models."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        pass


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ModelManager:
    """
    Handles communication with Ollama across 6 uncensored local models:
      1. Gemma 4 E4B (Ultra-Fast Aggressive)
      2. Qwen3 VL 8B (Vision / OCR)
      3. Gemma 4 12B (Fast Heuristic Planning)
      4. Gemma 4 26B (Adversarial Critic)
      5. Gemma 4 31B (Deep Reasoning Fallback)
      6. Hermes 3.6 Genesis 35B (Deep Abductive Reasoning & Dossier)
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self._heavy_model_lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None
        self.current_telemetry: Dict[str, Any] = {
            "active_model": None,
            "role": "Ready",
            "vram_locked": False,
            "status": "ready",
            "last_latency": 0.0,
        }

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
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
        Dispatches request to uncensored Ollama model with VRAM lock protection
        and real-time token streaming over WebSocket event bus.
        """
        target_model = model or settings.MODEL_FAST
        
        # Heavy models (≥ 26B parameters) require single sequential VRAM lock
        heavy_models = {
            settings.MODEL_DEEP,
            settings.MODEL_DEEP_31B,
            settings.MODEL_CRITIC,
            settings.MODEL_DEEP_FALLBACK,
        }
        use_lock = is_heavy or target_model in heavy_models

        # Role mapping for HUD
        if target_model == settings.MODEL_DEEP:
            role_name = "Hermes 35B [Deep Abductive Reasoning]"
        elif target_model == settings.MODEL_DEEP_31B:
            role_name = "Gemma4 31B [Heavy Reasoning Fallback]"
        elif target_model == settings.MODEL_CRITIC:
            role_name = "Gemma4 26B [Adversarial Refutation Critic]"
        elif target_model == settings.MODEL_FAST:
            role_name = "Gemma4 12B [Fast Heuristic Planner]"
        elif target_model == settings.MODEL_AGGRESSIVE_FAST:
            role_name = "Gemma4 E4B [Aggressive Tool Extractor]"
        elif target_model == settings.MODEL_VLM:
            role_name = "Qwen3 VL 8B [Vision / OCR]"
        else:
            role_name = "Neural Engine"

        short_name = target_model.split("/")[-1].split(":")[0]

        start_time = time.time()
        self.current_telemetry = {
            "active_model": short_name,
            "full_model": target_model,
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

            result = await self._call_streaming(
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
    # Streaming Internals
    # ------------------------------------------------------------------

    async def _call_streaming(
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
                            # Broadcast real-time token stream in chunks
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

            # Final thought emission
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
            logger.error(f"Model {target_model} failed: {exc}")
            # Fallback chain: Hermes 35B -> Gemma 31B -> Gemma 26B
            if target_model == settings.MODEL_DEEP:
                logger.warning(f"Falling back from Hermes 35B to {settings.MODEL_DEEP_FALLBACK}")
                return await self._call_streaming(
                    settings.MODEL_DEEP_FALLBACK, prompt, response_format, temperature, on_token
                )
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
