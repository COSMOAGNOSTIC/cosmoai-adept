# cosmoai-adept — Migration Plan

> **Goal:** From a single-purpose weather-bot script to a reusable `agent_core` library with a live observability layer, in phases, each one ending with the library in a working, tested state.
> **Companion doc:** ARCHITECTURE.md describes the destination; this file is the road.
> **Rule of the road:** one phase per sitting, each ends with `pytest -v` green. Never start a phase with the previous one's Definition of Done unmet.
> **Last updated:** 2026-07-25

---

## Phase 0 — Extract the core

- [x] `config.py` — all paths and keys from environment variables
- [x] `security.py` — `safe_path()` sandbox wall, with tests
- [x] `spec.py` — `AgentSpec` dataclass
- [x] `agent.py` — `build_agent()` ReAct graph factory
- [x] `memory.py` — `SqliteSaver` checkpointer factory
- [x] `text.py` — content normalizer, Discord chunker

**Definition of done:** ✅ Complete — core importable, `pip install -e .` clean.

---

## Phase 1 — Tool library

- [x] `tools/files.py`, `tools/log.py` — sandboxed I/O and activity tracking
- [x] `tools/search.py` — Tavily web search, dynamic year in query
- [x] `tools/weather.py` — OpenWeather, `timeout=10`, status checked before parse
- [x] `tools/tts.py` — single ElevenLabs implementation
- [x] Full pytest suite, one file per module

**Definition of done:** ✅ Complete — every tool has a matching test file.

---

## Phase 2 — CI and public release hygiene

- [x] GitHub Actions workflow, Python 3.11 and 3.12
- [x] MIT LICENSE
- [x] README with architecture diagram and Quick Start

**Definition of done:** ✅ Complete — badge green on `main`.

---

## Phase 3 — Observability and a second real feature

- [x] `events.py` — lazy WebSocket broadcaster, no-op with no listener
- [x] `agent.py` wired to emit `model_start` / `model_end` / `tool_start` / `tool_end`
- [x] `tools/digest.py` — scheduled digest pattern (sandbox state + live search into one report)
- [x] `examples/cli_demo.py` — real thin entrypoint, not just a README snippet
- [x] Tests for `events.py` and `tools/digest.py`

**Definition of done:** ✅ Complete — `pytest -v` green (32 tests), entrypoint runs end to end.

---

## Phase 4 — Live spatial visualizer

- [x] `visualizer/` — Godot 4 project, procedural scene (no external asset dependency)
- [x] `Main.gd` — `WebSocketPeer` client, reconnect-on-drop, tool → station mapping
- [x] `visualizer/demo_broadcaster.py` — scripted event replay, no API key required
- [x] Recorded demo GIF, embedded in README
- [x] `visualizer/README.md` — how it works, how to run it, how to swap in real sprites

**Definition of done:** ✅ Complete — demo GIF shows the agent walking between stations live.

---

## Phase 5 — Lock it in

- [ ] Event schema versioning (`schema_version` field) before a second consumer is built against it
- [ ] Swap procedural visualizer graphics for a CC0 tileset (see `visualizer/README.md`)
- [ ] Eval harness: scripted scenarios scoring agent output quality
- [ ] History windowing for long-running threads

**Definition of done:** Event schema versioned, visualizer has real art, eval harness scores at least one scenario end to end.

---

## Phase status

| Phase | Status | Date done |
|---|---|---|
| 0 — Extract the core | ✅ | 2025 |
| 1 — Tool library | ✅ | 2025 |
| 2 — CI and release hygiene | ✅ | 2025 |
| 3 — Observability + digest | ✅ | 2026-07-25 |
| 4 — Live spatial visualizer | ✅ | 2026-07-25 |
| 5 — Lock it in | ⬜ | |
