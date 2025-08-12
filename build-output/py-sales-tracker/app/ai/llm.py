from __future__ import annotations

from typing import Iterable

try:
    from llama_cpp import Llama
except Exception:  # pragma: no cover - optional at runtime
    Llama = None  # type: ignore

from app.ai.config import LLM_MODEL_PATH, LLM_CONTEXT_WINDOW, LLM_MAX_TOKENS, LLM_TEMPERATURE


class LocalLLM:
    def __init__(self) -> None:
        if Llama is None:
            raise RuntimeError("llama-cpp-python not installed. Install to enable local LLM.")
        self.llm = Llama(
            model_path=str(LLM_MODEL_PATH),
            n_ctx=LLM_CONTEXT_WINDOW,
            n_threads=4,
            n_gpu_layers=0,  # CPU-only by default for portability
            embedding=False,
            verbose=False,
        )

    def infer(self, prompt: str) -> str:
        out = self.llm(
            prompt=prompt,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            stop=["</s>", "<|eot_id|>"]
        )
        return out["choices"][0]["text"].strip() 