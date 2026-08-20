"""Shared fixtures for the test suite.

The key seam for testing agents.py without hitting the real Anthropic API is
`agents.get_llm()` — every node calls it fresh, so patching it to return a
FakeLLM lets us run the whole LangGraph pipeline deterministically and for
free.
"""
from types import SimpleNamespace

import pytest


class FakeLLM:
    """Stand-in for ChatAnthropic. Picks a canned response by matching a marker
    string against the SystemMessage content, so different nodes (which each
    use a distinct SYSTEM prompt) can be scripted independently in one fixture.
    """

    def __init__(self, responses_by_marker: dict[str, str], default: str = "Generic analysis. ESCALATE: NO"):
        self.responses_by_marker = responses_by_marker
        self.default = default
        self.calls: list[list] = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        system_content = messages[0].content if messages else ""
        for marker, text in self.responses_by_marker.items():
            if marker in system_content:
                return SimpleNamespace(content=text)
        return SimpleNamespace(content=self.default)


@pytest.fixture
def fake_llm_factory(monkeypatch):
    """Patches agents.get_llm to always return the given FakeLLM instance.

    Usage:
        llm = FakeLLM({"Revenue Analyst": "...", "Cost Analyst": "..."})
        fake_llm_factory(llm)
    """
    import agents

    def _install(fake_llm: FakeLLM):
        monkeypatch.setattr(agents, "get_llm", lambda temperature=0.7: fake_llm)
        return fake_llm

    return _install
