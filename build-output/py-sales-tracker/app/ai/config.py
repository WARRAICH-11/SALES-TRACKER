from __future__ import annotations

from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parents[2]
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# LLM
LLM_MODEL_PATH = MODELS_DIR / "llm" / "model.gguf"  # Place a 4-bit GGUF here (e.g., Llama-3, Mistral 7B Q4)
LLM_CONTEXT_WINDOW = 4096
LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.2

# Embeddings
EMBEDDING_MODEL_DIR = MODELS_DIR / "embeddings" / "all-MiniLM-L6-v2"  # Place sentence-transformers model locally
EMBEDDING_DIM = 384

# FAISS index
INDEX_DIR = BASE_DIR / "data" / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
FAISS_INDEX_PATH = INDEX_DIR / "sales.faiss"
DOCSTORE_PATH = INDEX_DIR / "docstore.json"

# Cache
CACHE_PATH = BASE_DIR / "data" / "ai_cache.json"

# Forecasting
FORECAST_ONNX_PATH = BASE_DIR / "data" / "forecast.onnx"
FORECAST_HORIZON_DAYS = 30
FORECAST_WINDOW_DAYS = 60 