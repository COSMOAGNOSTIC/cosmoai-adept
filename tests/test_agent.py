from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from agent_core.spec import AgentSpec


@tool
def boom(x: str) -> str:
    """A tool that always fails, to exercise error recovery."""
    raise RuntimeError("kaboom")


class _LegacySandboxInput(BaseModel):
    sandbox: str = Field(description="a tool that (incorrectly) takes sandbox as a model argument")
    filename: str = Field(default="x")


@tool(args_schema=_LegacySandboxInput)
def _legacy_sandbox_tool(sandbox: str, filename: str = "x") -> str:
    """Stand-in for a tool that reintroduces the model-controlled sandbox escape."""
    return "should never build"


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


def test_build_agent_rejects_a_tool_with_a_model_controlled_sandbox(tmp_path):
    """
    A tool that takes `sandbox` as a model-supplied argument lets the model
    choose its own sandbox root and escape the intended one entirely -
    build_agent() must refuse to build an agent around such a tool rather
    than silently accepting it. Regression test for that fix.
    """
    from agent_core.agent import build_agent

    spec = AgentSpec(
        name="test",
        system_prompt="you are a test agent",
        tools=[_legacy_sandbox_tool],
        sandbox=str(tmp_path),
    )
    with pytest.raises(ValueError, match="model-controlled"):
        build_agent(spec)


def test_build_agent_accepts_tools_with_no_sandbox_argument(tmp_path):
    from agent_core.agent import build_agent

    with patch("agent_core.agent.ChatAnthropic"):
        spec = AgentSpec(
            name="test",
            system_prompt="you are a test agent",
            tools=[boom],
            sandbox=str(tmp_path),
        )
        build_agent(spec)  # should not raise


class _AltNamedSandboxInput(BaseModel):
    """
    Same escape as _LegacySandboxInput, but under a different parameter
    name -- the original guard only matched the literal string "sandbox"
    and silently passed anything else. Regression fixture for that gap.
    """

    root: str = Field(description="same trust-boundary bug, different field name")
    filename: str = Field(default="x")


@tool(args_schema=_AltNamedSandboxInput)
def _alt_named_sandbox_tool(root: str, filename: str = "x") -> str:
    """Stand-in for a tool that reintroduces the escape under a non-'sandbox' name."""
    return "should never build"


def test_build_agent_rejects_an_alternately_named_sandbox_argument(tmp_path):
    """
    An independent code review found the original guard only matched the
    literal field name "sandbox" -- a tool naming the same parameter
    "root" or "base_dir" slipped through uninspected. Regression test for
    the broadened name check.
    """
    from agent_core.agent import build_agent

    spec = AgentSpec(
        name="test",
        system_prompt="you are a test agent",
        tools=[_alt_named_sandbox_tool],
        sandbox=str(tmp_path),
    )
    with pytest.raises(ValueError, match="model-controlled"):
        build_agent(spec)


class _UninspectableSchema:
    """Stands in for an args_schema shape the guard has no way to introspect -- neither
    Pydantic v2's `model_fields` nor v1's `__fields__`."""


def test_build_agent_fails_closed_on_an_uninspectable_schema(tmp_path):
    """
    An independent code review found the original guard used
    `getattr(schema, "model_fields", {})`, which silently returns an empty
    set -- and therefore silently PASSES -- for any schema shape it can't
    introspect (e.g. a Pydantic v1 model, which uses `__fields__` instead).
    A security assertion must fail closed on "I can't tell," not pass by
    default. Regression test: a tool with a genuinely uninspectable schema
    must raise, not build successfully.
    """
    from agent_core.agent import build_agent

    fake_tool = MagicMock()
    fake_tool.name = "uninspectable_tool"
    fake_tool.args_schema = _UninspectableSchema

    spec = AgentSpec(
        name="test",
        system_prompt="you are a test agent",
        tools=[fake_tool],
        sandbox=str(tmp_path),
    )
    with pytest.raises(ValueError, match="cannot inspect"):
        build_agent(spec)


def test_build_agent_binds_memory_outside_the_sandbox(tmp_path, monkeypatch):
    """
    An independent code review found the SQLite checkpointer used to live
    inside the agent's own sandbox directory -- the same directory its
    file tools are bound to -- so the model could read or corrupt its own
    conversation memory through ordinary sandboxed file tools. Regression
    test: build_agent() must put the checkpoint DB somewhere the model's
    own tools cannot reach, never inside spec.sandbox.
    """
    from agent_core.agent import build_agent

    memory_root = tmp_path / "memory-root"
    monkeypatch.setattr("agent_core.agent.memory_path", lambda name: str(memory_root))

    sandbox_dir = tmp_path / "sandbox"
    with patch("agent_core.agent.ChatAnthropic"):
        spec = AgentSpec(
            name="test",
            system_prompt="you are a test agent",
            tools=[boom],
            sandbox=str(sandbox_dir),
        )
        build_agent(spec)

    assert (memory_root / "test_memory.db").exists()
    # The bug this regresses: the DB must not end up inside the sandbox
    # the model's own file tools are rooted at.
    assert not (sandbox_dir / "test_memory.db").exists()
