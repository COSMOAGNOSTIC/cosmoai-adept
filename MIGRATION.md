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

## Phase 5 — Skin the visualizer, fix bubble timing

- [x] Rejected first-pass mockups (flat colors, clustered layout, fast bubbles) replaced after direct feedback
- [x] "Circuit" skin shipped for this repo — HUD/telemetry look, chosen over an RPG/office alternative
- [x] Universal bubble-timing fix: `clamp(text.length() / 12, 3.0, 7.0)` replacing a flat 1.8s
- [x] `demo_broadcaster.py` pacing slowed to match the new floor

**Definition of done:** ✅ Complete — demo GIF re-recorded and screenshot-verified with the new skin and timing.

---

## Phase 6 — Human-in-the-loop approval and local model backend

- [x] `agent_core/approvals.py` — `default_cli_approval_hook`, blocking CLI y/N prompt
- [x] `AgentSpec.approval_required`, `AgentSpec.approval_hook` — mechanical gate keyed on tool name, not prompt instruction
- [x] `agent.py`'s `execute_tools` pauses on a gated tool call, emits `awaiting_approval` / `approval_decided`, returns a `ToolMessage` on denial instead of raising
- [x] `AgentSpec.backend` (`"anthropic"` | `"local"`), `AgentSpec.local_base_url`, `config.LOCAL_LLM_BASE_URL` — swappable model client via `_build_model()`
- [x] `examples/cli_demo.py` — `--local` flag, `write_file` gated behind approval
- [x] Visualizer: `Main.gd` renders an "APPROVAL" station, handles `awaiting_approval` / `approval_decided`; `demo_broadcaster.py` script extended with an approval sequence; demo GIF re-recorded and screenshot-verified
- [x] `tests/test_approvals.py`, new cases in `tests/test_agent.py` — approved/denied/ungated tool calls, both backends
- [x] README, `visualizer/README.md`, ARCHITECTURE.md updated (sections 7–8, ADR-007/008, Design Principle 6)

**Definition of done:** ✅ Complete — `pytest -v` green (42 tests), visualizer shows the Approval node live, both backends covered by tests.

---

## Phase 6.5 — External review response: sandbox trust boundary + quick-start fix

This phase exists because it should never have been possible to get this far without it — an independent Fable-model code review (run against the public repo, no shared context with prior sessions) found two concrete defects, both confirmed by direct reproduction before fixing:

- [x] **Sandbox trust boundary fix (the important one):** every file/log/digest/tts tool previously took `sandbox` as a model-supplied tool argument. `safe_path()` itself was always correct, but it only guards escape *within* whatever root it's handed — and the model chose the root. Reproduced directly: `read_file.invoke({"sandbox": "/etc", "filename": "hostname"})` returned the host's real `/etc/hostname` before this fix. Fixed by moving `sandbox` out of every tool's input schema and into a closure bound once at construction time (`make_file_tools(sandbox)`, `make_log_tools(sandbox)`, `make_digest_tool(sandbox)`, `make_tts_tool(sandbox)`) — the model can no longer supply a value that doesn't exist as a parameter. `agent.py`'s new `_assert_no_model_controlled_sandbox()` enforces this at `build_agent()` time as defense in depth, so a future tool can't silently reintroduce the escape.
- [x] **Quick-start crash fix:** `make_checkpointer()` opened a SQLite file inside `sandbox` without creating the directory first — the README's own Quick Start and `examples/cli_demo.py` both crashed with `OperationalError` on a clean checkout, before an agent had ever run once. Fixed with `os.makedirs(sandbox, exist_ok=True)`.
- [x] Verified: 8 new tests (sandbox-argument-rejection tests on every tool factory, a cross-sandbox isolation test, a `build_agent()` regression test that a reintroduced `sandbox` argument is rejected, a fresh-sandbox smoke test) — 50/50 passing, up from 42.
- [x] ARCHITECTURE.md §4 rewritten to describe the fix and the reasoning, not just the current state; ADR-009 added; Known Debt gained two honestly-disclosed items found in the same review (symlink TOCTOU race, no dependency pinning) that are *not* fixed yet.

**Definition of done:** ✅ Complete — both defects reproduced, fixed, and covered by a regression test that would have caught them; `pytest -v` green (50 tests); the exploit re-run against the fixed code confirmed blocked (see PASSDOWN.md for the verification transcript).

---

## Phase 6.75 — Second-pass review response: memory trust boundary + guard hardening

This phase exists because closing the sandbox trust boundary in Phase 6.5 didn't fully close the trust boundary — a second, more targeted independent Fable-model review pass (asked to trace `config.py`, `memory.py`, and `agent.py` line by line, not read documentation) found the conversation-memory checkpointer had the same class of bug the file tools just got fixed for, plus two fail-open gaps in the guard that was supposed to prevent regressions.

- [x] **Memory trust boundary fix:** `build_agent()` passed `spec.sandbox` straight to `make_checkpointer()`, so the SQLite checkpoint DB lived inside the exact directory the agent's own file tools are rooted at — a model could read another thread's conversation history or corrupt its own checkpoint DB via its ordinary `write_file` tool. Fixed: new `config.memory_path()` (env-overridable via `MEMORY_<NAME>`, same pattern as `sandbox_path()`) resolves a dedicated per-agent directory that is never a tool sandbox root; `build_agent()` now calls `make_checkpointer(memory_path(spec.name), spec.name)`.
- [x] **Sandbox-guard hardening:** `_assert_no_model_controlled_sandbox()` used `getattr(schema, "model_fields", {})`, silently passing (empty field set) any schema shape it couldn't introspect (e.g. Pydantic v1's `__fields__`), and matched only the literal string `"sandbox"`. Fixed: an uninspectable schema now raises instead of passing, and a small set of sandbox-root-like names (`sandbox`, `sandbox_dir`, `root`, `base_dir`, etc.) is checked instead of one exact string.
- [x] **config.py hardening:** a missing `.env` with no `AGENT_SECRETS_DIR` set now warns on stderr at import time instead of silently leaving every `*_API_KEY` constant `None`; `discord_channel_id()` degrades to `0` on a malformed env value instead of raising and crashing the entrypoint at startup.
- [x] 9 new tests (`tests/test_config.py` new; `tests/test_agent.py` gained 3) covering the alt-named-sandbox rejection, the fail-closed uninspectable-schema case, memory binding outside the sandbox, and all three `config.py` fixes. 59/59 passing, up from 50.
- [x] ARCHITECTURE.md §4/§5/§9/§10 updated — Memory Model section rewritten to explain why the isolation matters, Security Model's sandbox-root row and its explanatory paragraph updated, Known Debt gained the config silent-misconfiguration item, ADR-010/011/012 added.

**Definition of done:** ✅ Complete — both real trust-boundary/fail-open issues fixed and covered by regression tests; `pytest -v` green (59 tests).

---

## Phase 7 — Lock it in

- [ ] Event schema versioning (`schema_version` field) before a second consumer is built against it
- [ ] Swap procedural visualizer graphics for a CC0 tileset (see `visualizer/README.md`) — note: superseded for now by the committed Circuit asset set; revisit if a richer look is wanted later
- [ ] Eval harness: scripted scenarios scoring agent output quality — flagged independently by three reviewers (Fable, and two external recruiter-perspective AI assessments) as the single highest-leverage next investment; Watchstander's sibling repo already has one (see its MIGRATION.md Phase 5.75) as a reference pattern
- [ ] History windowing for long-running threads
- [ ] Approval hook reference implementation beyond CLI (Discord reaction or similar)
- [ ] Symlink TOCTOU race in `safe_path()` (re-validate post-open or use `O_NOFOLLOW`)
- [ ] Dependency version pinning / lockfile
- [ ] `config.py`'s module-level env reads are still frozen at import time — the stderr warning added in Phase 6.75 makes a missing `.env` visible, but doesn't make the underlying values reloadable without re-importing the module

**Definition of done:** Event schema versioned, eval harness scores at least one scenario end to end, at least one non-CLI approval hook shipped as reference, dependencies pinned.

---

## Phase status

| Phase | Status | Date done |
|---|---|---|
| 0 — Extract the core | ✅ | 2025 |
| 1 — Tool library | ✅ | 2025 |
| 2 — CI and release hygiene | ✅ | 2025 |
| 3 — Observability + digest | ✅ | 2026-07-25 |
| 4 — Live spatial visualizer | ✅ | 2026-07-25 |
| 5 — Visualizer skin + bubble timing | ✅ | 2026-07-25 |
| 6 — HITL approval + local backend | ✅ | 2026-07-25 |
| 6.5 — External review response (sandbox fix + quick-start fix) | ✅ | 2026-07-25 |
| 6.75 — Second-pass review response (memory boundary + guard hardening) | ✅ | 2026-07-25 |
| 7 — Lock it in | ⬜ | |
