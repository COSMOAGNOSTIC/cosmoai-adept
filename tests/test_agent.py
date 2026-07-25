from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from agent_core.spec import AgentSpec


@tool
def boom(x: str) -> str:
    """A tool that always fails, to exercise error recovery."""
    raise RuntimeError("kaboom")


@tool
def risky(x: str) -> str:
    """A tool that requires human approval before it runs."""
    return f"did risky thing: {x}"


class FakeModel:
    """Stand-in for ChatAnthropic: first call invokes a tool, second call answers."""

    TOOL_NAME = "boom"

    def __init__(self, *args, **kwargs):
        self._calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self._calls += 1
        if self._calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{"name": self.TOOL_NAME, "args": {"x": "hi"}, "id": "call_1"}],
            )
        return AIMessage(content="recovered and done")


class FakeApprovalModel(FakeModel):
    TOOL_NAME = "risky"


def test_agent_recovers_from_tool_error(tmp_path):
    with patch("agent_core.agent.ChatAnthropic", FakeModel):
        from agent_core.agent import build_agent
        spec = AgentSpec(name="test", system_prompt="you are a test agent", tools=[boom], sandbox=str(tmp_path))
        graph = build_agent(spec)
        result = graph.invoke({"messages": [HumanMessage(content="do it")]}, config={"configurable": {"thread_id": "t1"}})
        texts = [str(getattr(m, "content", "")) for m in result["messages"]]
        assert any("kaboom" in t for t in texts)
        assert any("recovered and done" in t for t in texts)


def test_approved_tool_call_executes(tmp_path):
    with patch("agent_core.agent.ChatAnthropic", FakeApprovalModel):
        from agent_core.agent import build_agent
        spec = AgentSpec(
            name="test",
            system_prompt="you are a test agent",
            tools=[risky],
            sandbox=str(tmp_path),
            approval_required={"risky"},
            approval_hook=lambda name, args: True,
        )
        graph = build_agent(spec)
        result = graph.invoke({"messages": [HumanMessage(content="go")]}, config={"configurable": {"thread_id": "t2"}})
        texts = [str(getattr(m, "content", "")) for m in result["messages"]]
        assert any("did risky thing" in t for t in texts)


def test_denied_tool_call_is_blocked(tmp_path):
    with patch("agent_core.agent.ChatAnthropic", FakeApprovalModel):
        from agent_core.agent import build_agent
        spec = AgentSpec(
            name="test",
            system_prompt="you are a test agent",
            tools=[risky],
            sandbox=str(tmp_path),
            approval_required={"risky"},
            approval_hook=lambda name, args: False,
        )
        graph = build_agent(spec)
        result = graph.invoke({"messages": [HumanMessage(content="go")]}, config={"configurable": {"thread_id": "t3"}})
        texts = [str(getattr(m, "content", "")) for m in result["messages"]]
        assert any("denied by human approver" in t for t in texts)
        assert not any("did risky thing" in t for t in texts)


def test_tools_outside_approval_set_are_not_gated(tmp_path):
    # boom isn't in approval_required, so it should run (and fail) exactly
    # as it did before approvals existed - approval_hook is never called.
    hook = MagicMock(return_value=False)
    with patch("agent_core.agent.ChatAnthropic", FakeModel):
        from agent_core.agent import build_agent
        spec = AgentSpec(
            name="test",
            system_prompt="you are a test agent",
            tools=[boom],
            sandbox=str(tmp_path),
            approval_required={"risky"},
            approval_hook=hook,
        )
        graph = build_agent(spec)
        result = graph.invoke({"messages": [HumanMessage(content="go")]}, config={"configurable": {"thread_id": "t4"}})
        texts = [str(getattr(m, "content", "")) for m in result["messages"]]
        assert any("kaboom" in t for t in texts)
        hook.assert_not_called()


def test_default_backend_uses_chat_anthropic(tmp_path):
    from agent_core.agent import _build_model
    with patch("agent_core.agent.ChatAnthropic") as mock_cls:
        mock_cls.return_value.bind_tools.return_value = "bound-anthropic"
        spec = AgentSpec(name="test", system_prompt="p", tools=[], sandbox=str(tmp_path))
        result = _build_model(spec)
        mock_cls.assert_called_once()
        assert result == "bound-anthropic"


def test_local_backend_uses_chat_openai_with_base_url(tmp_path):
    from agent_core.agent import _build_model
    fake_instance = MagicMock()
    fake_instance.bind_tools.return_value = "bound-local"
    with patch("langchain_openai.ChatOpenAI", return_value=fake_instance) as mock_cls:
        spec = AgentSpec(
            name="test",
            system_prompt="p",
            tools=[],
            sandbox=str(tmp_path),
            backend="local",
            local_base_url="http://localhost:1234/v1",
        )
        result = _build_model(spec)
        _, kwargs = mock_cls.call_args
        assert kwargs["base_url"] == "http://localhost:1234/v1"
        assert result == "bound-local"


def test_local_backend_falls_back_to_config_base_url(tmp_path):
    from agent_core.agent import _build_model
    fake_instance = MagicMock()
    fake_instance.bind_tools.return_value = "bound-local"
    with patch("langchain_openai.ChatOpenAI", return_value=fake_instance) as mock_cls, \
         patch("agent_core.agent.LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"):
        spec = AgentSpec(
            name="test", system_prompt="p", tools=[], sandbox=str(tmp_path), backend="local"
        )
        _build_model(spec)
        _, kwargs = mock_cls.call_args
        assert kwargs["base_url"] == "http://localhost:1234/v1"
