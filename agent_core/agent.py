import operator
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from agent_core.config import ANTHROPIC_API_KEY
from agent_core.memory import make_checkpointer
from agent_core.spec import AgentSpec
from agent_core import events
from agent_core.text import extract_text


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


def build_agent(spec: AgentSpec):
    """
    Build and compile a ReAct LangGraph agent from an AgentSpec.
    - Tools bound via bind_tools - never listed in prose prompts
    - Tool errors returned as ToolMessages so the model can recover
    - Checkpointer scoped to agent sandbox - one DB per agent
    """
    model = ChatAnthropic(
        model=spec.model,
        api_key=ANTHROPIC_API_KEY,
    ).bind_tools(spec.tools)

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
            tool_map = {t.name: t for t in spec.tools}
            tool = tool_map.get(tool_call["name"])
            events.emit("tool_start", agent=spec.name, tool=tool_call["name"])
            if tool is None:
                result = f"Unknown tool: {tool_call['name']}"
                ok = False
            else:
                try:
                    result = tool.invoke(tool_call["args"])
                    ok = True
                except Exception as e:
                    result = f"Tool error ({tool_call['name']}): {e}"
                    ok = False
            events.emit("tool_end", agent=spec.name, tool=tool_call["name"], ok=ok)
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
