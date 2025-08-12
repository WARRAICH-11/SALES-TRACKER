from app.ai.rag import SalesRAG
from app.ai.llm import LocalLLM

class DummyLLM:
    def infer(self, prompt: str) -> str:
        return "ok"

def test_rag_answer_monkeypatch(monkeypatch, tmp_path):
    # Monkeypatch LLM
    monkeypatch.setattr('app.ai.rag.LocalLLM', lambda: DummyLLM())
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