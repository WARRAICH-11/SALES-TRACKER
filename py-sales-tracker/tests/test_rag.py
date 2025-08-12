import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, patch
from app.ai.rag import SalesRAG
from app.ai.llm import LocalLLM

class DummyLLM:
    def infer(self, prompt: str) -> str:
        return "ok"

@patch('app.ai.rag.Embeddings')
@patch('app.ai.rag.LocalLLM')
def test_rag_answer_monkeypatch(mock_llm, mock_embeddings, tmp_path):
    # Mock the embeddings to avoid model loading
    mock_embeddings_instance = Mock()
    mock_embeddings.return_value = mock_embeddings_instance
    
    # Mock the LLM
    mock_llm_instance = DummyLLM()
    mock_llm.return_value = mock_llm_instance
    
    class DummySession:
        def execute(self, *args, **kwargs):
            class X:
                def scalars(self):
                    return []
                def __iter__(self):
                    return iter([])
            return X()
    
    rag = SalesRAG(DummySession())
    ans = rag.answer("test")
    assert ans == "ok" 