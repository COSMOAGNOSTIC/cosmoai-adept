# cosmoai-adept — Architecture

> **Status:** Living document. Update when a decision changes, a component is added/removed, or a migration phase completes.
> **Last updated:** 2026-07-25

## 1. Purpose and Scope

`cosmoai-adept` is a shared library (`agent_core`) for building multiple independent LangGraph agents — Discord bots, CLI tools, scheduled jobs — without duplicating framework code per agent. It ships with a live 2D spatial visualizer so an agent's activity is observable in real time, not just from logs.

Out of scope: any specific deployment's prompts, credentials, or private tool integrations. This repo is the reusable core; a real deployment is a thin `AgentSpec` plus an entrypoint that imports from here.

## 2. Design Principles

1. Security lives in the tool layer, never the prompt layer.
2. One core, thin agents. No forks. Adding an agent means writing a spec and an entrypoint, not touching the framework.
3. Fail loud into the model. Tool errors become `ToolMessage`s the model can see and recover from, never silent exceptions.
4. Observable by default, invasive by nothing. `events.py` broadcasts activity over WebSocket; if nothing's listening, it's a no-op — zero cost, zero coupling.
5. Least privilege. Every tool declares exactly the inputs it needs; nothing reaches outside its sandbox.

## 3. Components

| Module | Responsibility |
|---|---|
| `config.py` | All settings from environment variables, never hardcoded |
| `security.py` | `safe_path()` — sandbox wall, `realpath` before prefix check |
| `agent.py` | `build_agent(spec)` — ReAct graph factory, checkpointer wiring, tool-error recovery, event emission |
| `events.py` | Lazy-started WebSocket broadcaster for live telemetry |
| `memory.py` | `SqliteSaver` checkpointer factory, one DB per agent |
| `spec.py` | `AgentSpec` dataclass — the only thing that varies per agent |
| `text.py` | `extract_text()` normalizer, `chunk_for_discord()` |
| `tools/files.py` | Read/write/list through `safe_path` |
| `tools/log.py` | `write_log`, pending-items list (add/read/complete) |
| `tools/search.py` | Tavily web search, dynamic year in query |
| `tools/weather.py` | OpenWeather, `timeout=10`, status checked before parse |
| `tools/tts.py` | Single ElevenLabs implementation |
| `tools/digest.py` | Scheduled digest: sandbox state + live search into one report |
| `examples/cli_demo.py` | Reference thin entrypoint — the pattern every real agent follows |
| `visualizer/` | Godot 4 project rendering live agent activity spatially |

## 4. Security Model

Threat: prompt injection via search results and other tool output landing in model context.

| Surface | Control |
|---|---|
| File writes/reads | `safe_path` sandbox wall — rejects `..`, absolute paths, symlink escape |
| Tool failures | Returned as `ToolMessage`s, never raised into the graph |
| Telemetry | `events.py` broadcasts operational metadata (tool names, timestamps, short text previews) only — never full tool arguments or raw file contents |

## 5. Memory Model

`SqliteSaver` checkpointer, one database per agent, stored in that agent's sandbox. `thread_id` scopes conversation memory — a Discord channel ID, a CLI session tag — so each channel's history is isolated with no cross-bleed.

## 6. Observability Model

`agent_core.events.emit(event_type, **payload)` is called at four points in `build_agent()`'s graph: `model_start`, `model_end`, `tool_start`, `tool_end`. The broadcaster starts its WebSocket server on first `emit()` call, on a background thread, and silently no-ops if the port is taken or nothing is listening — importing `agent_core` never opens a socket by itself. The bundled Godot visualizer is one consumer; the event schema is stable enough for others (a web dashboard, a log shipper) to consume the same stream.

## 7. Known Debt

| Item | Notes |
|---|---|
| History windowing | Long threads will eventually need summarize-and-truncate |
| Event schema versioning | No `schema_version` field yet — fine at one consumer, needed before a second |
| Eval harness | Scripted scenarios scoring agent output quality |

## 8. Decision Log

| ID | Date | Decision | Rationale |
|---|---|---|---|
| ADR-001 | 2026-06 | Shared `agent_core` library, thin agent configs | Per-agent forks were already diverging; every fix was paid N times |
| ADR-002 | 2026-06 | `SqliteSaver` for all agent memory | One platform primitive beats hand-rolled text-file memory |
| ADR-003 | 2026-06 | Tool errors return as messages, never raise | Agent should see and recover from failures, not crash the run |
| ADR-004 | 2026-07 | `events.py` as a lazy, no-op-by-default WebSocket broadcaster | Wanted live observability without coupling `agent_core` to any specific front end, and without cost when nothing's watching |
| ADR-005 | 2026-07 | Godot 4 for the reference visualizer, not a web canvas | Native `WebSocketPeer`, tiny footprint, headless CLI builds for CI/demo recording, and it's the right tool if this grows into a richer spatial dashboard |
| ADR-006 | 2026-07 | "Circuit" (dark HUD/telemetry) skin over an RPG/office look for this public repo | Reads as systems observability to a recruiter/reviewer, not a game — chosen after reviewing static mockups of both directions |

## 9. Maintenance Rules

Update this document when: a migration phase completes, a component is added, a decision changes, or debt is paid. If the doc and the code disagree, the doc is the bug. See [MIGRATION.md](MIGRATION.md) for how we got here and [PASSDOWN.md](PASSDOWN.md) for what's next.
