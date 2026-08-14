# cosmoai-adept — Architecture

> **Status:** Living document. Update when a decision changes, a component is added/removed, or a migration phase completes.
> **Last updated:** 2026-08-14 (later still) — `safe_open()` made cross-platform: it worked on POSIX only and raised `NotImplementedError` on Windows, breaking ordinary file reads/writes there entirely (ADR-015)

## 1. Purpose and Scope

`cosmoai-adept` is a shared library (`agent_core`) for building multiple independent LangGraph agents — Discord bots, CLI tools, scheduled jobs — without duplicating framework code per agent. It ships with a live 2D spatial visualizer so an agent's activity is observable in real time, not just from logs.

Out of scope: any specific deployment's prompts, credentials, or private tool integrations. This repo is the reusable core; a real deployment is a thin `AgentSpec` plus an entrypoint that imports from here.

## 2. Design Principles

1. Security lives in the tool layer, never the prompt layer.
2. One core, thin agents. No forks. Adding an agent means writing a spec and an entrypoint, not touching the framework.
3. Fail loud into the model. Tool errors become `ToolMessage`s the model can see and recover from, never silent exceptions.
4. Observable by default, invasive by nothing. `events.py` broadcasts activity over WebSocket; if nothing's listening, it's a no-op — zero cost, zero coupling.
5. Least privilege. Every tool declares exactly the inputs it needs; nothing reaches outside its sandbox — and the sandbox root itself is bound once, by whoever constructs the `AgentSpec`, never accepted as a model-supplied tool argument (see ADR-009 — an earlier version of this repo got this wrong).
6. High-risk actions are gated mechanically, not by prompt instruction. A tool name in `approval_required` pauses for a human decision at the tool-execution layer — the same place `safe_path()` lives, not something a clever prompt could argue its way around.

## 3. Components

| Module | Responsibility |
|---|---|
| `config.py` | All settings from environment variables, never hardcoded |
| `security.py` | `safe_path()` — sandbox wall, `realpath` before prefix check; `safe_open()` — opens a validated path and re-checks it post-open, closing the TOCTOU gap `safe_path()` alone leaves open. POSIX: `O_NOFOLLOW` + `/proc/self/fd` re-check. Windows: `GetFinalPathNameByHandleW` re-check (no `O_NOFOLLOW` equivalent exists there — see ADR-015 for the narrower guarantee this implies) |
| `agent.py` | `build_agent(spec)` — ReAct graph factory, checkpointer wiring, tool-error recovery, event emission, approval gate, backend selection |
| `events.py` | Lazy-started WebSocket broadcaster for live telemetry |
| `approvals.py` | Human-in-the-loop approval hook, defaults to a blocking CLI y/N prompt |
| `memory.py` | `SqliteSaver` checkpointer factory, one DB per agent |
| `spec.py` | `AgentSpec` dataclass — the only thing that varies per agent |
| `text.py` | `extract_text()` normalizer, `chunk_for_discord()` |
| `tools/files.py` | `make_file_tools(sandbox)` — read/write/list through `safe_path`, sandbox bound at construction |
| `tools/log.py` | `make_log_tools(sandbox)` — write_log, pending-items list (add/read/complete) |
| `tools/search.py` | Tavily web search, dynamic year in query |
| `tools/weather.py` | OpenWeather, `timeout=10`, status checked before parse |
| `tools/tts.py` | `make_tts_tool(sandbox)` — single ElevenLabs implementation |
| `tools/digest.py` | `make_digest_tool(sandbox)` — scheduled digest: sandbox state + live search into one report |
| `examples/cli_demo.py` | Reference thin entrypoint — the pattern every real agent follows |
| `visualizer/` | Godot 4 project rendering live agent activity spatially |

## 4. Security Model

Threat: prompt injection via search results and other tool output landing in model context, and — the one this section exists to be explicit about — a model choosing its own sandbox root instead of the one the deployer intended.

| Surface | Control |
|---|---|
| File writes/reads | `safe_open()` — validates via `safe_path` (rejects `..`, absolute paths, symlink escape, **within** whatever root it's given), opens the file, then re-validates the actual opened path before handing it back, closing the check-to-open TOCTOU gap plain `safe_path()`-then-`open()` left (see ADR-014). On POSIX this re-check is backed by `O_NOFOLLOW` at the syscall level (fully atomic); on Windows there's no `O_NOFOLLOW` equivalent, so the guarantee there is narrower — see ADR-015 |
| Sandbox root selection | Bound once at tool-construction time via each `tools/*.py` module's `make_*_tools(sandbox)` factory (see `agent_core/tools/files.py`), never accepted as a tool argument. `agent.py`'s `_assert_no_model_controlled_sandbox()` enforces this at `build_agent()` time — a tool exposing any of a small set of sandbox-root-like field names (`sandbox`, `sandbox_dir`, `root`, `base_dir`, etc.) raises before the agent is built, and a tool whose schema this guard can't even introspect raises too, rather than silently passing |
| Tool failures | Returned as `ToolMessage`s, never raised into the graph |
| Telemetry | `events.py` broadcasts operational metadata (tool names, timestamps, short text previews) only — never full tool arguments or raw file contents |

**Why the sandbox-root row exists as its own line, not folded into the row above:** an earlier version of every file/log/digest/tts tool took `sandbox` as a model-supplied argument. `safe_path()` itself was always correct — it genuinely blocks `..` traversal and symlink escape — but it was guarding escape *within* whatever root the model handed it, and the model chose the root. A model could call `read_file(sandbox="/etc", filename="hostname")` and read outside the intended sandbox entirely, with `safe_path()` never objecting because nothing about that call looks like an escape from `/etc`. This was caught by an independent Fable-model code review and reproduced directly (see PASSDOWN.md). The fix moves the sandbox root out of the tool's input schema and into a closure bound at construction time — the model literally cannot supply a `sandbox` value anymore, because the parameter doesn't exist in the tool it's calling. `_assert_no_model_controlled_sandbox()` is defense in depth so a future tool can't quietly reintroduce this by adding the parameter back.

**The guard itself had two fail-open gaps, since fixed (ADR-011).** A second, more targeted Fable review pass — asked to trace `agent.py` line by line rather than read this document — found the original guard used `getattr(schema, "model_fields", {})`, a Pydantic-v2-only attribute; a v1-style schema (`__fields__`) or any other uninspectable shape silently returned an empty field set and passed uninspected. It also matched only the exact string `"sandbox"`, so a tool naming the same parameter `root` or `base_dir` slipped through. Both are the wrong failure direction for a security assertion — "I can't tell" should raise, not pass. Fixed: an uninspectable schema now raises, and a small set of known sandbox-root-like names is checked instead of one literal string.

**Formerly a known limitation, closed 2026-08-14 (ADR-014):** `safe_path()` resolves symlinks via `realpath()` at check time, but every tool used to hand the resulting string to a plain `open()` afterward — a TOCTOU race existed if something swapped a symlink into the sandbox between the check and the open. `agent_core.security.safe_open()` now does both the check and the open together: `O_NOFOLLOW` makes the `open()` syscall itself refuse a symlinked final path component (no window to race, since the kernel does it atomically), and a post-open re-check of the opened fd's real path via `/proc/self/fd/<fd>` catches a symlink swapped into an *intermediate* directory component, which `O_NOFOLLOW` alone doesn't cover. Every tool that opens a file (`tools/files.py`, `tools/log.py`, `tools/digest.py`, `tools/tts.py`) now goes through `safe_open()` instead of `safe_path()` + a plain `open()`.

## 5. Memory Model

`SqliteSaver` checkpointer, one database per agent, stored in a dedicated per-agent memory directory (`config.memory_path()`) that is **never** the same directory as that agent's sandbox. `thread_id` scopes conversation memory — a Discord channel ID, a CLI session tag — so each channel's history is isolated with no cross-bleed.

**Why this is called out explicitly:** an earlier version of `build_agent()` passed `spec.sandbox` straight to `make_checkpointer()`, so the checkpoint DB lived inside the exact directory the agent's own `safe_path()`-bound file tools are rooted at. `memory.py`'s docstring correctly said the DB was "never in secrets, never in cloud sync" — true — without mentioning it *was* reachable by the model's own tools — not true, and the actual problem: a model could read another thread's conversation history (a real cross-conversation information leak) or corrupt its own checkpoint DB using nothing more than its ordinary, sandboxed `write_file` tool. This was caught by a second independent Fable-model review pass, specifically requested to trace `config.py`, `memory.py`, and `agent.py` line by line rather than read documentation. Fixed: `build_agent()` now calls `make_checkpointer(memory_path(spec.name), spec.name)`; `memory_path()` defaults to `./agent_memory/<agent>` (env-overridable via `MEMORY_<NAME>`, same pattern as `sandbox_path()`/`SANDBOX_<NAME>`), which is never a tool sandbox root for any agent.

## 6. Observability Model

`agent_core.events.emit(event_type, **payload)` is called at four points in `build_agent()`'s graph: `model_start`, `model_end`, `tool_start`, `tool_end`. The broadcaster starts its WebSocket server on first `emit()` call, on a background thread, and silently no-ops if the port is taken or nothing is listening — importing `agent_core` never opens a socket by itself. The bundled Godot visualizer is one consumer; the event schema is stable enough for others (a web dashboard, a log shipper) to consume the same stream.

## 7. Human-in-the-Loop Approval

`AgentSpec.approval_required: set[str]` names tools that must pause for a human decision before they run. In `agent.py`'s `execute_tools`, a tool call whose name is in that set never reaches `tool.invoke()` until `spec.approval_hook(tool_name, args) -> bool` returns `True`; the gate emits `awaiting_approval` then `approval_decided` over the same event stream `events.py` already broadcasts, so the visualizer renders it as the agent pausing at an Approval station. If no `approval_hook` is supplied, `agent_core.approvals.default_cli_approval_hook` is used — a blocking terminal y/N prompt, correct for `examples/cli_demo.py` and wrong for anything unattended (a Discord bot, a scheduled job), which must supply its own hook (a reaction-based confirm, a Slack button, etc.). A denial returns a `ToolMessage` explaining the tool was denied rather than raising, consistent with the tool-error-recovery principle — the model sees the denial and can respond to the user instead of crashing.

## 8. Model Backend

`AgentSpec.backend` is `"anthropic"` (default) or `"local"`. `agent.py`'s `_build_model()` is the only place this branches: `"anthropic"` builds a `ChatAnthropic` client as before; `"local"` builds a `ChatOpenAI` client pointed at `spec.local_base_url` (falling back to `config.LOCAL_LLM_BASE_URL`, default `http://localhost:1234/v1`) — any OpenAI-compatible server, LM Studio included. Everything downstream — the graph, the tools, the checkpointer, the event stream — is identical regardless of backend; only the model client differs. This exists so the framework can run entirely on local, GPU-offloaded models with zero API cost and zero network egress, which matters both for cheap iteration and for a fully offline demo.

## 9. Known Debt

Reprioritized 2026-08-14 by severity tier, not just accumulation order: **security → the code works → the code is stable → everything works as designed → everything else.** An item's tier is what it would break if left alone, not how old or how annoying it is. The marker-id rendering bug that used to live in this section (broken arrowheads on `docs/architecture-diagram.html`) was found and fixed the same session this reprioritization happened — see ADR-013 — and is no longer open debt.

### Tier 1 — Security

No open items. The only Tier 1 item, the symlink TOCTOU race in `safe_path()`, was closed the same day it was tiered — see ADR-014 and §4 above.

### Priority override — Eval harness

Donnie explicitly pulled this above tier order on 2026-08-14, right after Tier 1 closed, on the basis that it'll become "instantly useful" once it exists. It doesn't strictly belong ahead of Tiers 2–4 by the security → works → stable → designed-as-intended ordering above — it isn't broken, stuck, or misbehaving, so by that ordering alone it would sit in Tier 5 — but a direct, explicit priority call from the project owner overrides the mechanical tier order, and that's noted here rather than silently reordering the tiers to match after the fact.

| Item | Notes |
|---|---|
| Eval harness | Scripted scenarios scoring agent output quality — flagged by three independent reviewers (Fable, and two external recruiter-perspective AI assessments) as the single highest-leverage next investment, and now the explicit next thing to build per Donnie's 2026-08-14 call |

### Tier 2 — The code works

| Item | Notes |
|---|---|
| `config.py` silent-misconfiguration risk (partially mitigated) | If `AGENT_SECRETS_DIR` is unset and cwd isn't the repo root, every `*_API_KEY` constant resolves to `None`. Now emits a stderr warning at import time (see ADR-012) so the cause is visible immediately rather than surfacing only as a confusing auth error deep inside a model call — the underlying fragility (module-level env reads frozen at import time) is unchanged |

### Tier 3 — The code is stable

| Item | Notes |
|---|---|
| No dependency version pinning | `setup.py` has no version bounds and there's no lockfile — a fast-moving LangChain/LangGraph release could silently break the build between test runs |

### Tier 4 — Everything works as designed

| Item | Notes |
|---|---|
| Approval hook UX beyond CLI | `default_cli_approval_hook` only makes sense for interactive entrypoints; no Discord/Slack reference hook shipped yet |

### Tier 5 — Everything else

| Item | Notes |
|---|---|
| Visualizer doesn't fully hit the mark yet | Flagged 2026-08-14: the live Godot visualizer and the newer `docs/architecture-diagram.html` page both work correctly, but neither is polished enough yet — "we can afford to add a little polish." No specific direction scoped yet (motion/easing pass on the Godot side, spacing/typography pass on the diagram page, or both); this is a placeholder to come back to, not a design spec |
| History windowing | Long threads will eventually need summarize-and-truncate |
| Event schema versioning | No `schema_version` field yet — fine at one consumer, needed before a second |

## 10. Decision Log

| ID | Date | Decision | Rationale |
|---|---|---|---|
| ADR-001 | 2026-06 | Shared `agent_core` library, thin agent configs | Per-agent forks were already diverging; every fix was paid N times |
| ADR-002 | 2026-06 | `SqliteSaver` for all agent memory | One platform primitive beats hand-rolled text-file memory |
| ADR-003 | 2026-06 | Tool errors return as messages, never raise | Agent should see and recover from failures, not crash the run |
| ADR-004 | 2026-07 | `events.py` as a lazy, no-op-by-default WebSocket broadcaster | Wanted live observability without coupling `agent_core` to any specific front end, and without cost when nothing's watching |
| ADR-005 | 2026-07 | Godot 4 for the reference visualizer, not a web canvas | Native `WebSocketPeer`, tiny footprint, headless CLI builds for CI/demo recording, and it's the right tool if this grows into a richer spatial dashboard |
| ADR-006 | 2026-07 | "Circuit" (dark HUD/telemetry) skin over an RPG/office look for this public repo | Reads as systems observability to a recruiter/reviewer, not a game — chosen after reviewing static mockups of both directions |
| ADR-007 | 2026-07 | Approval gate keyed on tool *name*, declared on the spec | Mechanical and can't be argued around by clever prompting — same reasoning as `safe_path()` |
| ADR-008 | 2026-07 | `_build_model()` branches on `spec.backend` rather than a separate `build_agent()` per backend | One code path for the graph regardless of model source keeps tools/memory/events identical either way |
| ADR-009 | 2026-07 | Sandbox root moved from a model-supplied tool argument to a closure bound at tool-construction time (`make_file_tools(sandbox)` etc.), enforced by `build_agent()` | An independent code review (Fable model) found the previous design let a model choose its own sandbox root and read/write outside the intended one, since `safe_path()` only guards escape *within* whatever root it's handed. This makes "security lives in the tool layer" true in practice, not just in the argument names |
| ADR-010 | 2026-07-25 | Conversation-memory checkpointer moved from the agent's sandbox to a dedicated `config.memory_path()` directory that is never any agent's tool-accessible root | A second, more targeted Fable review pass (asked to trace `config.py`/`memory.py`/`agent.py` specifically, not read docs) found the checkpointer DB living inside the exact directory the model's own file tools operate in — a real information-leak and integrity risk, not just a naming inconsistency |
| ADR-011 | 2026-07-25 | `_assert_no_model_controlled_sandbox()` hardened to fail closed on an uninspectable `args_schema` and to check a small set of sandbox-root-like field names instead of the single literal string `"sandbox"` | The same review pass found the original guard used a Pydantic-v2-only attribute lookup that silently passed (empty field set) on any schema shape it couldn't introspect, and matched only one exact field name — both are the wrong failure direction for a security assertion |
| ADR-012 | 2026-07-25 | `config.py` warns on stderr when no `.env` is found, and `discord_channel_id()` degrades to `0` on a malformed value instead of raising | Same review pass: a missing `.env` used to fail silently (every API key `None`, surfacing only as a confusing downstream auth error) and a typo'd channel-id env var crashed the entrypoint outright at import time — neither is the behavior a config loader should have on bad input |
| ADR-013 | 2026-08-14 | `docs/architecture-diagram.html`'s SVG `<marker>` and `<linearGradient>` element ids renamed from the `my-svg…` prefix `mmdc` originally generated to match the root `id="adept-svg"` rename | A self-audit run right after publishing the page (prompted by "any known debt here?") found the id-rename script had renamed the root `<svg>` id and every `url(#adept-svg…)` reference to it, but not the marker/gradient elements' own `id` attributes — so every `marker-end="url(#adept-svg_flowchart-v2-pointEnd)"` pointed at nothing and arrowheads silently failed to render, with no console error. Fixed by renaming all 12 marker ids and the 1 gradient id to match; verified by confirming zero unresolved `url(#...)` references and by a rendered screenshot showing arrowheads present |
| ADR-014 | 2026-08-14 (later same day) | New `agent_core.security.safe_open()` closes the `safe_path()` TOCTOU race: `O_NOFOLLOW` on the `open()` syscall itself, plus a post-open re-check of the opened fd's real path via `/proc/self/fd/<fd>`. `tools/files.py`, `tools/log.py`, `tools/digest.py`, and `tools/tts.py` all switched from `safe_path()` + a plain `open()` to `safe_open()` | Direct request from the project owner to close the one open Tier 1 (security) item once Known Debt was tiered by severity. `safe_path()`'s `realpath()` check already caught a symlink that existed *at check time*; the gap was specifically a symlink appearing *between* that check and a later plain `open()` call. `O_NOFOLLOW` closes the final-path-component half of that gap atomically at the syscall level; the fd re-check closes the intermediate-directory-component half, which `O_NOFOLLOW` alone doesn't cover. 11 new tests added (`tests/test_security.py`, `tests/test_files.py`), including one that simulates the actual race via `monkeypatch` (symlink introduced *after* `safe_path()`'s check has already passed) rather than only testing a symlink that's already in place before the call — the pre-placed-symlink tests alone would have passed even against the old, unfixed code, since `safe_path()`'s own `realpath()` resolution already caught those |
| ADR-015 | 2026-08-14 (later still) | `safe_open()` given a Windows code path — `GetFinalPathNameByHandleW` (via `msvcrt.get_osfhandle` + `ctypes`) re-validates the opened handle's real path, the Windows equivalent of the POSIX branch's `/proc/self/fd/<fd>` re-check. Two of the new ADR-014 tests now go through a `_symlink_or_skip()` helper that skips (not fails) when the environment can't create a symlink at all | ADR-014 shipped `safe_open()` POSIX-only, raising `NotImplementedError` on any other platform — caught only when Donnie ran the suite locally on Windows: 20 of 22 failures were ordinary read/write calls hitting that hard stop, not symlink-specific. Windows has no `O_NOFOLLOW`, so the fix cannot give POSIX-equivalent atomicity — that gap is documented directly in the `safe_open()` docstring rather than silently assumed away. The other 2 failures were `WinError 1314` (`SeCreateSymbolicLinkPrivilege` missing) — a Windows privilege requirement for creating symlinks at all, not a code bug — so those specific tests skip gracefully instead of false-failing in a non-elevated shell |

## 11. Maintenance Rules

Update this document when: a migration phase completes, a component is added, a decision changes, or debt is paid. If the doc and the code disagree, the doc is the bug. See [MIGRATION.md](MIGRATION.md) for how we got here, [PASSDOWN.md](PASSDOWN.md) for what's next, and [AOSE.md](AOSE.md) for the adversarial-review discipline behind ADR-009 through ADR-012 specifically.
