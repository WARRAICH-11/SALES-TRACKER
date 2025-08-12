import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.ai.rag import SalesRAG
from app.ai.llm import LocalLLM

class DummyLLM:
    def infer(self, prompt: str) -> str:
        return "ok"

def test_rag_answer_monkeypatch():
    """Test RAG functionality with proper mocking."""
    
    class DummySession:
        def execute(self, *args, **kwargs):
            class X:
                def scalars(self):
                    return []
                def __iter__(self):
                    return iter([])
            return X()
    
    # Mock embedding model to return valid array structure
    mock_embeddings = MagicMock()
    mock_embeddings.encode.return_value = np.array([
        [0.1, 0.2, 0.3, 0.4, 0.5],  # Fake embedding for first document
        [0.4, 0.5, 0.6, 0.7, 0.8]   # Fake embedding for second document
    ], dtype=np.float32)
    
    # Mock LLM
    mock_llm = DummyLLM()
    
    with patch('app.ai.rag.Embeddings', return_value=mock_embeddings):
        with patch('app.ai.rag.LocalLLM', return_value=mock_llm):
            with patch('app.ai.rag.faiss') as mock_faiss:
                # Mock FAISS index
                mock_index = MagicMock()
                mock_index.search.return_value = (
                    np.array([[0.9, 0.8]]),  # scores
                    np.array([[0, 1]])       # indices
                )
                mock_faiss.IndexFlatIP.return_value = mock_index
                
                rag = SalesRAG(DummySession())
                rag.doc_texts = ["test doc 1", "test doc 2"]
                rag.index = mock_index
                
                ans = rag.answer("test")
                assert ans == "ok" 