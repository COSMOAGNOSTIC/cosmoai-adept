import operator
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from agent_core.config import ANTHROPIC_API_KEY, LOCAL_LLM_BASE_URL
from agent_core.memory import make_checkpointer
from agent_core.spec import AgentSpec
from agent_core import events
from agent_core.text import extract_text
from agent_core.approvals import default_cli_approval_hook


def _build_model(spec: AgentSpec):
    """
    Anthropic by default. spec.backend == "local" points the same
    tool-calling ReAct loop at any OpenAI-compatible local server (LM
    Studio, etc.) instead - same AgentSpec, same tools, same graph, just
    a different model client. Requires langchain-openai (see setup.py).
    """
    if spec.backend == "local":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=spec.model,
            base_url=spec.local_base_url or LOCAL_LLM_BASE_URL,
            api_key=spec.local_api_key,
        ).bind_tools(spec.tools)

    return ChatAnthropic(
        model=spec.model,
        api_key=ANTHROPIC_API_KEY,
    ).bind_tools(spec.tools)


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


def _assert_no_model_controlled_sandbox(spec: AgentSpec) -> None:
    """
    Defense in depth for the sandbox trust boundary: no tool bound to this
    agent may expose `sandbox` as a model-supplied argument. The sandbox
    root must be bound at tool-construction time (see tools/files.py's
    make_file_tools() and its siblings), never chosen by the model - a
    model that picks its own sandbox root can point `safe_path()` anywhere
    it likes, since safe_path only guards escape *within* whatever root
    it's handed.

    This used to be true only by convention (the tool modules simply
    didn't take a `sandbox` argument) - it's enforced here as well so a
    future tool can't silently reintroduce the escape and have nothing
    catch it before it reaches a model.
    """
    for t in spec.tools:
        schema = getattr(t, "args_schema", None)
        field_names = set(getattr(schema, "model_fields", {}).keys()) if schema else set()
        if "sandbox" in field_names:
            raise ValueError(
                f"Tool '{t.name}' exposes 'sandbox' as a model-controlled argument. "
                "Bind the sandbox path at tool-construction time instead - see "
                "agent_core/tools/files.py's make_file_tools() for the pattern."
            )


def build_agent(spec: AgentSpec):
    """
    Build and compile a ReAct LangGraph agent from an AgentSpec.
    - Tools bound via bind_tools - never listed in prose prompts
    - Tool errors returned as ToolMessages so the model can recover
    - Checkpointer scoped to agent sandbox - one DB per agent
    - No bound tool may accept `sandbox` as a model-supplied argument
    """
    _assert_no_model_controlled_sandbox(spec)

    model = _build_model(spec)

    checkpointer = make_checkpointer(spec.sandbox, spec.name)

    def call_model(state: AgentState) -> dict:
        events.emit("model_start", agent=spec.name)
        messages = [SystemMessage(content=spec.system_prompt)] + state["messages"]
        response = model.invoke(messages)
        tool_names = [tc["name"] for tc in getattr(response, "tool_calls", [])]
        events.emit(
            "model_end",
            agent=spec.name,
            tool_calls=tool_names,
            text=extract_text(response.content)[:280],
        )
        return {"messages": [response]}

    def execute_tools(state: AgentState) -> dict:
        last = state["messages"][-1]
        results = []
        for tool_call in last.tool_calls:
            tool_name = tool_call["name"]
            tool_map = {t.name: t for t in spec.tools}
            tool = tool_map.get(tool_name)

            if tool_name in spec.approval_required:
                events.emit("awaiting_approval", agent=spec.name, tool=tool_name)
                hook = spec.approval_hook or default_cli_approval_hook
                approved = hook(tool_name, tool_call["args"])
                events.emit(
                    "approval_decided", agent=spec.name, tool=tool_name, approved=approved
                )
                if not approved:
                    results.append(
                        ToolMessage(
                            content=f"Tool call denied by human approver: {tool_name}",
                            tool_call_id=tool_call["id"],
                        )
                    )
                    continue

            events.emit("tool_start", agent=spec.name, tool=tool_name)
            if tool is None:
                result = f"Unknown tool: {tool_name}"
                ok = False
            else:
                try:
                    result = tool.invoke(tool_call["args"])
                    ok = True
                except Exception as e:
                    result = f"Tool error ({tool_name}): {e}"
                    ok = False
            events.emit("tool_end", agent=spec.name, tool=tool_name, ok=ok)
            results.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": results}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", execute_tools)
    graph.set_entry_point("model")
    graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")

    return graph.compile(checkpointer=checkpointer)
