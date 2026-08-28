from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration for AETHER.
    Configured with uncensored local Ollama models on RTX 4070.
    """
    model_config = SettingsConfigDict(env_prefix="AETHER_")

    # ── Ollama Endpoint ────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── Uncensored Local Models Hierarchy ──────────────────────────────
    # 1. Ultra-Fast Aggressive Tool Caller (E4B)
    MODEL_AGGRESSIVE_FAST: str = "hf.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive:Q4_K_M"

    # 2. Vision & OCR Model (8B)
    MODEL_VLM: str = "hf.co/HauhauCS/Qwen3VL-8B-Uncensored-HauhauCS-Balanced:Q4_K_M"

    # 3. Fast Heuristic Planner & Entity Extractor (12B)
    MODEL_FAST: str = "hf.co/HauhauCS/Gemma4-12B-QAT-Uncensored-HauhauCS-Balanced:Q4_K_M"

    # 4. Adversarial Red-Team Critic (26B)
    MODEL_CRITIC: str = "hf.co/HauhauCS/Gemma4-26B-A4B-QAT-Uncensored-HauhauCS-Balanced-MTP:Q4_K_M"

    # 5. Heavy Deep Reasoning Fallback (31B)
    MODEL_DEEP_31B: str = "hf.co/HauhauCS/Gemma4-31B-QAT-Uncensored-HauhauCS-Balanced-MTP:Q4_K_M"

    # 6. Primary Deep Abductive Reasoning & Synthesis (35B)
    MODEL_DEEP: str = "hermes-3.6-genesis:35b-a3b-uncensored-v7"
    MODEL_DEEP_FALLBACK: str = "hf.co/HauhauCS/Gemma4-31B-QAT-Uncensored-HauhauCS-Balanced-MTP:Q4_K_M"

    # ── VRAM & Concurrency Arbitration ────────────────────────────────
    MAX_CONCURRENT_HEAVY_MODELS: int = 1
    VRAM_ARBITRATION_ENABLED: bool = True

    # ── OSINT Thresholds ───────────────────────────────────────────────
    ENTITY_CONFIDENCE_THRESHOLD: float = 0.75
    HYPOTHESIS_RECURSION_LIMIT: int = 5
    MAX_SEARCH_DEPTH: int = 10

    # ── Storage Paths ──────────────────────────────────────────────────
    VECTOR_DB_PATH: str = "aether/data/qdrant"
    GRAPH_DB_PATH: str = "aether/data/graph.db"
    LOG_LEVEL: str = "INFO"


settings = Settings()
