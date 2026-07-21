from unittest.mock import patch
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from agent_core.spec import AgentSpec


@tool
def boom(x: str) -> str:
    """A tool that always fails, to exercise error recovery."""
    raise RuntimeError("kaboom")


class FakeModel:
    """Stand-in for ChatAnthropic: first call invokes the tool, second call answers."""

    def __init__(self, *args, **kwargs):
        self._calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self._calls += 1
        if self._calls == 1:
            return AIMessage(content="", tool_calls=[{"name": "boom", "args": {"x": "hi"}, "id": "call_1"}])
        return AIMessage(content="recovered and done")


def test_agent_recovers_from_tool_error(tmp_path):
    with patch("agent_core.agent.ChatAnthropic", FakeModel):
        from agent_core.agent import build_agent
        spec = AgentSpec(name="test", system_prompt="you are a test agent", tools=[boom], sandbox=str(tmp_path))
        graph = build_agent(spec)
        result = graph.invoke({"messages": [HumanMessage(content="do it")]}, config={"configurable": {"thread_id": "t1"}})
        texts = [str(getattr(m, "content", "")) for m in result["messages"]]
        assert any("kaboom" in t for t in texts)
        assert any("recovered and done" in t for t in texts)
