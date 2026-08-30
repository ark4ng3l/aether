import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


SETTINGS_FILE = Path("aether/data/settings.json")


class Settings(BaseSettings):
    """
    Centralized configuration for AETHER.
    Configured with uncensored local Ollama models and cognitive reasoning thresholds.
    """
    model_config = SettingsConfigDict(env_prefix="AETHER_")

    # ── Ollama Endpoint ────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── Uncensored Local Models Hierarchy ──────────────────────────────
    # 1. Ultra-Fast Aggressive Tool Caller (E4B)
    MODEL_AGGRESSIVE_FAST: str = "hf.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive:Q4_K_M"

    # 2. Vision & OCR Model (8B)
    MODEL_VLM: str = "hf.co/HauhauCS/Qwen3VL-8B-Uncensored-HauhauCS-Balanced:Q4_K_M"

    # 3. Fast Tactical Planner & Entity Extractor (E4B Aggressive)
    MODEL_FAST: str = "hf.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive:Q4_K_M"
    MODEL_FAST_12B: str = "hf.co/HauhauCS/Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced:Q4_K_M"

    # 4. Adversarial Red-Team Critic (26B)
    MODEL_CRITIC: str = "hf.co/HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP:Q4_K_M"

    # 5. Heavy Deep Reasoning Fallback (31B)
    MODEL_DEEP_31B: str = "hf.co/HauhauCS/Gemma4-31B-QAT-Uncensored-HauhauCS-Balanced-MTP:Q4_K_M"

    # 6. Primary Deep Abductive Reasoning & Synthesis (35B)
    MODEL_DEEP: str = "hermes-3.6-genesis:35b-a3b-uncensored-v7"
    MODEL_DEEP_FALLBACK: str = "hf.co/HauhauCS/Gemma4-31B-QAT-Uncensored-HauhauCS-Balanced-MTP:Q4_K_M"

    # ── Cognitive Reasoning & Thinking Budgets ─────────────────────────
    HYPOTHESIS_RECURSION_LIMIT: int = 5
    MAX_SEARCH_DEPTH: int = 30
    ENTITY_CONFIDENCE_THRESHOLD: float = 0.75

    # ── Model Temperatures ─────────────────────────────────────────────
    REASONING_TEMPERATURE: float = 0.7
    PLANNER_TEMPERATURE: float = 0.2
    CRITIC_TEMPERATURE: float = 0.3

    # ── VRAM & Concurrency Arbitration ────────────────────────────────
    MAX_CONCURRENT_HEAVY_MODELS: int = 1
    VRAM_ARBITRATION_ENABLED: bool = True

    # ── Storage Paths ──────────────────────────────────────────────────
    VECTOR_DB_PATH: str = "aether/data/qdrant"
    GRAPH_DB_PATH: str = "aether/data/graph.db"
    LOG_LEVEL: str = "INFO"

    def load_from_disk(self):
        """Loads saved settings overrides from JSON."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(self, k):
                            setattr(self, k, v)
            except Exception:
                pass

    def update_and_save(self, updates: Dict[str, Any]):
        """Updates setting attributes and saves them to disk."""
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        for k, v in updates.items():
            if hasattr(self, k) and v is not None:
                # Type conversions
                field_type = type(getattr(self, k))
                try:
                    if field_type == int:
                        setattr(self, k, int(v))
                    elif field_type == float:
                        setattr(self, k, float(v))
                    elif field_type == bool:
                        setattr(self, k, bool(v))
                    else:
                        setattr(self, k, str(v))
                except Exception:
                    pass

        # Save to disk
        data = {
            "OLLAMA_BASE_URL": self.OLLAMA_BASE_URL,
            "MODEL_AGGRESSIVE_FAST": self.MODEL_AGGRESSIVE_FAST,
            "MODEL_VLM": self.MODEL_VLM,
            "MODEL_FAST": self.MODEL_FAST,
            "MODEL_CRITIC": self.MODEL_CRITIC,
            "MODEL_DEEP": self.MODEL_DEEP,
            "MODEL_DEEP_FALLBACK": self.MODEL_DEEP_FALLBACK,
            "MODEL_DEEP_31B": self.MODEL_DEEP_31B,
            "HYPOTHESIS_RECURSION_LIMIT": self.HYPOTHESIS_RECURSION_LIMIT,
            "MAX_SEARCH_DEPTH": self.MAX_SEARCH_DEPTH,
            "ENTITY_CONFIDENCE_THRESHOLD": self.ENTITY_CONFIDENCE_THRESHOLD,
            "REASONING_TEMPERATURE": self.REASONING_TEMPERATURE,
            "PLANNER_TEMPERATURE": self.PLANNER_TEMPERATURE,
            "CRITIC_TEMPERATURE": self.CRITIC_TEMPERATURE,
            "MAX_CONCURRENT_HEAVY_MODELS": self.MAX_CONCURRENT_HEAVY_MODELS,
            "VRAM_ARBITRATION_ENABLED": self.VRAM_ARBITRATION_ENABLED,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


settings = Settings()
settings.load_from_disk()
