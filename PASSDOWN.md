# PASSDOWN

> Read this first when picking the project back up. It answers: what's done, what's next, and what was decided but not yet built — so you never have to re-derive context from commit history.
> Update this at the end of every working session, even a short one. If MIGRATION.md is the map, this is "you are here."

---

## 2026-08-14 (latest) — Watchstander → cosmoai-adept parity reconciliation

**Why this session happened:** a Watchstander session diffed its own live `main` against a fresh clone of this repo's live `main` and found six polish/process items Watchstander had picked up over the prior week that this repo hadn't. That passdown was delivered as the first message in a fresh session here and acted on directly.

**What got built:**
- `docs/architecture-diagram.html` — standalone, GitHub-Pages-hosted version of the README's Mermaid diagram, styled to match Watchstander's page (dark theme, legend, per-node explanation cards). The diagram SVG is pre-rendered and embedded inline (via `mmdc`/Puppeteer against the repo's own pinned Chromium), not client-side-rendered Mermaid — same reliability reasoning as Watchstander's copy.
- README.md's Mermaid diagram color-coded by subsystem (`classDef` per Entrypoints/Core/gate-nodes/Models/Viz), matching Watchstander's functional-color convention. Edge labels were already correctly quoted going in — no `|"label with (parens)"|`-style fix needed here, unlike Watchstander's history.
- `docs/prompts/aose-auditor-prompt.md` committed — the working AOSE-auditor system prompt, written repo-agnostic (not Watchstander-specific) so it can be pointed at any codebase's files cold, with a closing note tying it back to this repo's own ADR-009 through ADR-012 review history.
- This entry, plus the three process notes folded into the Culture note below (sync discipline, lost-patch rule, secret-scan habit) — all three were documented in Watchstander but not yet written down here, despite the same multi-session, multi-machine pattern applying equally to both repos.

**Not done in this session, needs a manual step:** GitHub Pages itself has to be enabled by hand — Settings → Pages → Deploy from branch → `main` → `/docs`. The diagram page and README link are only live once that's flipped. **Do this before treating Gap 1 as closed** — a relative link to an unpublished `.html` file resolves to GitHub's raw blob view, not a rendered page, which is the exact bug this fix exists to avoid repeating.

**Addendum, same day — self-audit after Pages went live, bug found and fixed, debt reprioritized.** Once Donnie confirmed the published Pages link worked, a follow-up self-audit ("any known debt here?") found a real bug the batch push above had shipped: `docs/architecture-diagram.html`'s id-rename script renamed the root `<svg>` id and every `url(#adept-svg…)` reference to it, but not the `<marker>`/`<linearGradient>` elements' own `id` attributes — so every `marker-end="url(#adept-svg_flowchart-v2-pointEnd)"` pointed at nothing and arrowheads silently failed to render, no console error. Fixed (all 12 marker ids + 1 gradient id renamed), verified with a zero-unresolved-references check and a rendered screenshot showing arrowheads present, and pushed straight to `main` — see ARCHITECTURE.md ADR-013.

Donnie then asked for the Known Debt table to be reprioritized by a fixed severity order — **security → the code works → the code is stable → everything works as designed → everything else** — rather than left in accumulation order. ARCHITECTURE.md §9 now groups every open item into those five tiers. One new item was added at Donnie's explicit request: the live Godot visualizer and the new `architecture-diagram.html` page both work but neither is polished yet ("we can afford to add a little polish") — tiered 5 (everything else) since it's a polish gap, not a defect, with no specific design direction scoped yet.

**Second addendum, same day — Tier 1 closed, eval harness explicitly promoted.** Donnie resolved the open question above directly: fix the one Tier 1 (security) item, then bump the eval harness above tier order. `agent_core.security.safe_open()` is new — it closes the `safe_path()` TOCTOU race properly, not just cosmetically: `O_NOFOLLOW` on the `open()` syscall itself refuses a symlinked final path component atomically (no window to race), and a post-open re-check of the opened fd's real path via `/proc/self/fd/<fd>` catches a symlink swapped into an *intermediate* directory component, which `O_NOFOLLOW` alone doesn't cover. `tools/files.py`, `tools/log.py`, `tools/digest.py`, and `tools/tts.py` all switched from `safe_path()` + a plain `open()` to `safe_open()`. 11 new tests (`tests/test_security.py`, `tests/test_files.py`) — the important one isn't the ones that pre-place a symlink before calling `safe_open()` (those would have passed even against the old code, since `safe_path()`'s own `realpath()` check already caught a symlink that existed at check time); it's `test_safe_open_closes_the_actual_toctou_race`, which uses `monkeypatch` to introduce the symlink *after* `safe_path()`'s check has already passed and only then lets the `open()` run — that's the actual race, and it's the one that would have slipped through the old `safe_path()`-then-`open()` pattern. Full suite verified locally in a fresh venv before pushing (70/70), and again by re-cloning `main` after the push and diffing byte-for-byte against the local copy. See ARCHITECTURE.md ADR-014.

With Tier 1 closed, the eval harness was pulled out of Tier 5 into its own "Priority override" section in ARCHITECTURE.md §9, ahead of Tiers 2–4, per Donnie's explicit call that it'll become "instantly useful" once it exists — noted as an override of the mechanical tier order rather than silently re-tiering it to match.

**Third addendum, same day — `safe_open()` broke on Windows, fixed.** Donnie ran the freshly-pushed suite locally on a Windows laptop (via a fresh clone, not the cloud session) and got 22 failures. 20 of them were `NotImplementedError: safe_open() requires /proc/self/fd (POSIX only)` — the ADR-014 fix had been built POSIX-only and hard-failed on any other platform, which broke *ordinary* file reads/writes on Windows, not just the symlink-specific tests. That's a real portability bug the local-only Linux venv testing in this session's earlier addendum couldn't have caught. Fixed with a Windows branch in `safe_open()`: `GetFinalPathNameByHandleW` (via `msvcrt`/`ctypes`) re-validates the opened handle's real path after the fact, the closest Windows equivalent to the POSIX branch's `/proc/self/fd/<fd>` re-check. Windows has no `O_NOFOLLOW`, so this is honestly documented in the docstring as a narrower guarantee than POSIX gets — no atomic final-component block, mitigated in practice by Windows requiring `SeCreateSymbolicLinkPrivilege` (admin or Developer Mode) just to create a symlink at all. The remaining 2 failures (`WinError 1314`) were that exact privilege requirement blocking the test setup itself, not a code bug — `_symlink_or_skip()` now catches that and skips those specific tests rather than false-failing in a non-elevated shell. 70/70 still pass locally on Linux after the change; Donnie will confirm the Windows run separately. See ARCHITECTURE.md ADR-015.

**Open questions for next session:** what does the eval harness's first version actually look like — a fixed set of scripted scenarios with expected-behavior assertions, an LLM-as-judge scoring pass, or both? Not scoped yet. Also watch for the same repo-drift pattern happening in reverse — periodically diff this repo's `main` against Watchstander's, rather than only pushing parity checks one direction.

---

## 2026-07-25 — Second-pass review response: memory trust boundary + guard hardening

**Why this session happened:** Donnie shared a Gemini "recruiter lens" assessment of both repos, which — Gemini itself admitted when asked to actually trace code instead of pattern-match on repo names — was written without ever fetching the GitHub URLs; it hallucinated a description of Watchstander and missed that cosmoai-adept's README already had the Mermaid diagram it recommended adding. Rather than relay files back and forth with Gemini manually, a second independent Fable-model pass was run directly against six specific files Gemini had asked for (three per repo: the hazard/deconfliction/HITL modules in Watchstander, and the secrets loader / memory / core execution loop in cosmoai-adept) — cold, with no prior context, specifically to line-trace logic paths, exception handling, and trust boundaries rather than accept anything at face value.

**What got found and verified before fixing (cosmoai-adept side):**
- **The Phase 6.5 sandbox fix didn't fully close the trust boundary — memory had the same bug.** `build_agent()` called `make_checkpointer(spec.sandbox, spec.name)`, so the SQLite conversation-memory DB lived inside the exact directory the agent's own `safe_path()`-bound file tools operate in. `memory.py`'s docstring said the DB was "never in secrets, never in cloud sync" — true — without mentioning it *was* reachable by the model's own tools — not true, and the actual problem: a model could read another thread's conversation history via its own `read_file` tool, or corrupt its checkpoint DB via `write_file`.
- **The sandbox guard added in Phase 6.5 had two fail-open gaps.** `_assert_no_model_controlled_sandbox()` used `getattr(schema, "model_fields", {})` — a Pydantic-v2-only attribute — so a v1-style schema (`__fields__`) silently returned an empty field set and passed uninspected; it also matched only the exact string `"sandbox"`, so a tool naming the same parameter `root` or `base_dir` would slip through. A security assertion should fail closed on "I can't tell," not pass by default — this did the opposite on both counts.
- Two minor config.py issues in the same pass: a missing `.env` with no `AGENT_SECRETS_DIR` set silently leaves every `*_API_KEY` constant `None` (surfacing only as a confusing downstream auth error); `discord_channel_id()` raised an uncaught `ValueError` on a malformed env value, crashing the entrypoint at startup on a typo.

**What got built:**
- `config.py` gained `memory_path(agent_name)` (env-overridable via `MEMORY_<NAME>`, same pattern as `sandbox_path()`), defaulting to `./agent_memory/<agent>` — never a tool sandbox root for any agent. `build_agent()` now calls `make_checkpointer(memory_path(spec.name), spec.name)` instead of passing `spec.sandbox`.
- `_assert_no_model_controlled_sandbox()` rewritten: raises on an uninspectable schema instead of silently passing; checks a small set of sandbox-root-like names (`sandbox`, `sandbox_dir`, `sandbox_path`, `root`, `root_dir`, `base_dir`) instead of one literal string.
- `config.py`: a missing `.env` now prints a stderr warning at import time; `discord_channel_id()` catches the `ValueError` and returns `0` (same as unset) instead of crashing.
- `.gitignore` gained `agent_memory/` alongside the existing `sandboxes/`.
- 9 new tests: `tests/test_config.py` (new file — `memory_path()` vs `sandbox_path()` distinctness, env override, both `discord_channel_id()` fixes, the stderr-warning fix); `tests/test_agent.py` gained an alt-named-sandbox rejection test, an uninspectable-schema fail-closed test, and a test asserting the checkpoint DB lands outside the sandbox directory. 59/59 passing, up from 50.
- ARCHITECTURE.md §4 (Security Model) and §5 (Memory Model) rewritten to explain why each fix exists; Known Debt gained the config silent-misconfiguration item (now partially mitigated); ADR-010/011/012 added. MIGRATION.md gained Phase 6.75.

**Decided but not built:** did not change `config.py`'s underlying module-level-env-frozen-at-import design — the stderr warning makes a missing `.env` visible, it doesn't make the values reloadable without re-importing. Noted honestly in Known Debt rather than treated as fixed.

**Open questions for next session:** is it worth formalizing "ask an independent reviewer to trace N specific files cold" as a repeatable pattern for this project, given it found real issues twice now (the Phase 6.5 sandbox fix, and this session's memory/guard fixes) that a docs-level read — including from other AI reviewers — both missed? Watchstander got the same treatment this session; see that repo's PASSDOWN.md.

---

## 2026-07-25 (earlier still) — External review response: sandbox trust boundary + quick-start fix

**Where things stood coming in:** the two public repos (this one and `Watchstander`) went through an independent Fable-model code/architecture/security review, plus two external recruiter-perspective assessments (ChatGPT, Grok) that Donnie ran separately and brought back for comparison. Fable found two concrete, reproducible defects in this repo that the recruiter assessments — reading docs and READMEs rather than tracing code — had both praised uncritically: the "mechanical, tool-layer sandbox" claim, and (separately) a broken quick-start.

**What got found and verified before fixing:**
- **Sandbox trust boundary was only half-enforced.** Every file/log/digest/tts tool took `sandbox` as a *model-supplied* tool argument. `safe_path()` was always correct at blocking `..`/absolute-path/symlink escape — but only *within* whatever root it was handed, and the model chose the root. Reproduced directly: `read_file.invoke({"sandbox": "/etc", "filename": "hostname"})` returned the real host `/etc/hostname`, not an error. This directly contradicted the "security lives in the tool layer, not the prompt layer" principle that's been in ARCHITECTURE.md since Phase 0 — the principle was aspirational for this one boundary, not actually true in code.
- **Quick-start crash on a clean checkout.** `make_checkpointer()` opened a SQLite file inside `sandbox` without `os.makedirs()` first. Anyone following the README's own Quick Start, or running `examples/cli_demo.py` fresh, hit `OperationalError` before the agent ever ran once.

**What got built:**
- `tools/files.py`, `tools/log.py`, `tools/digest.py`, `tools/tts.py` rewritten as `make_*_tools(sandbox)` factories — `sandbox` is now a Python closure variable bound once by whoever constructs the tools (the entrypoint, e.g. `examples/cli_demo.py`), and is no longer a field in any tool's input schema at all. The model cannot supply a value for a parameter that doesn't exist.
- `agent.py`'s new `_assert_no_model_controlled_sandbox()` runs at `build_agent()` time and raises if any bound tool's schema still contains a `sandbox` field — this is defense in depth so a future tool can't silently reintroduce the exact same escape and have nothing catch it.
- `memory.py`'s `make_checkpointer()` now creates the sandbox directory before opening the database.
- `examples/cli_demo.py` updated to build its tools via the new factories; the system prompt no longer needs to tell the model to "pass sandbox as an argument" (there's nothing left for it to pass).
- 8 new tests: every tool factory has a test asserting `"sandbox" not in args_schema.model_fields`, a cross-sandbox isolation test (two agents built with different sandboxes can't see each other's files), a `build_agent()` regression test with a deliberately reintroduced "legacy" sandbox-taking tool (asserts it's rejected), and a fresh-sandbox smoke test for the quick-start fix. 50/50 tests passing (up from 42).
- Manually re-ran the exact exploit from the Fable review against the fixed code: the model-supplied `sandbox="/etc"` argument is now silently ignored (extra field, not in the schema) and the tool reads from the real bound sandbox instead — confirmed the host file is never touched.
- ARCHITECTURE.md §4 rewritten to describe *why* this fix exists, not just the current state (a "doc that only shows the destination" would have hidden the same class of bug from the next reviewer); ADR-009 added; two more honestly-disclosed-but-not-yet-fixed items added to Known Debt (symlink TOCTOU race, no dependency pinning) that came out of the same review — they weren't in scope for this pass, but they're real and now tracked instead of quietly omitted.

**Decided but not built:** the TOCTOU race and dependency pinning noted above; the Watchstander-side fixes from the same review round (broken graph import, HITL decision not structurally enforced) are a separate PASSDOWN entry in that repo.

**Open questions for next session:** the eval-harness gap was independently flagged by three separate reviewers now (Fable, ChatGPT, Grok) as the highest-leverage next investment — worth prioritizing over further polish. Also worth deciding: should `_assert_no_model_controlled_sandbox()`'s pattern (a runtime invariant check at `build_agent()` time) become a general convention for other trust-boundary assumptions in this framework, rather than a one-off fix?

---

## 2026-07-25 (earlier same day) — HITL approval gate + local LLM backend

**Where things stood coming in:** an externally-pasted PASSDOWN document (from a different session) proposed a HITL "Approval Switch" and a local-LLM-backend integration as open TODOs. Cross-checking it against the actual repo showed most of that document's other items were already done (LICENSE, events.py, visualizer, Mermaid diagram) — but these two were genuinely new scope, and non-trivial enough (direct-attention features, not background plumbing) to build and document properly rather than skip.

**What got built:**
- `agent_core/approvals.py` — `default_cli_approval_hook`, a blocking terminal y/N prompt, used when a spec supplies no hook of its own.
- `spec.py` — `AgentSpec.approval_required: set[str]` (tool names that must pause) and `AgentSpec.approval_hook` (swappable decision function).
- `agent.py` — `execute_tools` now checks `approval_required` before invoking a gated tool; emits `awaiting_approval` then `approval_decided` over the existing event stream; a denial returns a `ToolMessage` explaining the refusal rather than raising, consistent with the existing tool-error-recovery principle.
- `spec.py` / `config.py` / `agent.py` — `AgentSpec.backend` (`"anthropic"` default, `"local"`), `local_base_url`, `LOCAL_LLM_BASE_URL` env default `http://localhost:1234/v1`; `_build_model()` is the single branch point between `ChatAnthropic` and `ChatOpenAI` (via new `langchain-openai` dependency) — everything else (graph, tools, memory, events) is identical either way.
- `examples/cli_demo.py` — `--local` flag to run against a local server instead of the API, `write_file` gated behind approval as the worked example.
- Visualizer: added an "APPROVAL" station (orange, `Main.gd`'s `STATION_LAYOUT`/`STATION_COLOR`), new `match` branches for `awaiting_approval` (walk to station, show which tool is waiting) and `approval_decided` (show approved/denied). `demo_broadcaster.py`'s script extended with a full approval sequence. Re-recorded the demo GIF and screenshot-verified the orange node renders correctly alongside the other five.
- Tests: `tests/test_approvals.py` (new, 4 cases), `tests/test_agent.py` extended with approved/denied/ungated tool-call cases and backend-selection cases (`FakeApprovalModel`, `test_default_backend_uses_chat_anthropic`, `test_local_backend_uses_chat_openai_with_base_url`, `test_local_backend_falls_back_to_config_base_url`). 42/42 passing.
- Docs: README (hero framing already covered the visualizer; added dedicated "Human-in-the-Loop Approval" and "Local LLM Backend" sections, two new Core Architectural Principles bullets, Mermaid diagram extended with an Approval node and a Models subgraph), `visualizer/README.md` (event table rows for the two new events), ARCHITECTURE.md (Design Principle 6, Components table, new sections 7–8, ADR-007/008, a new Known Debt item for non-CLI approval hooks), MIGRATION.md (Phase 6, Phase 5 backfilled for the skin work, Phase 7 renumbered from the old Phase 5).

**Decided but not built:**
- No non-CLI approval hook reference implementation yet (a Discord reaction confirm, a Slack button) — `default_cli_approval_hook` is explicitly documented as wrong for unattended entrypoints. Tracked as debt in ARCHITECTURE.md and as a Phase 7 item.
- Whether `cosmo-core` (the private production sibling) should also get these two features was raised but not confirmed — this work was scoped to `cosmoai-adept` only this session.

**Open questions for next session:**
- Port HITL approval + local backend to `cosmo-core`? Needs an explicit yes from the project owner before touching the production repo.
- Is a Discord-reaction approval hook worth building next, given the Discord bot is the actual unattended deployment target this gate would matter most for?

---

## 2026-07-25 (later same day) — Visualizer skin: Circuit

**Where things stood coming in:** first visualizer pass used flat `ColorRect` placeholders and a fixed 1.8s speech bubble regardless of text length — too fast to read, especially in a recorded demo.

**What got built:**
- Chose "Circuit" skin after reviewing static mockups against a rejected alternative pair (sci-fi vs. RPG office/cottage look) — went sci-fi/telemetry for this public repo specifically, since it reads as systems observability rather than a game.
- `visualizer/assets/gen_assets.py` — generates `bg_circuit.png` (dark grid + vignette), `node_glow.png` (radial glow, tinted per station via `Sprite2D.modulate`), `scanlines.png` (CRT overlay). Committed output, not generated at runtime.
- `Main.gd` rewritten: glowing station nodes, right-angle circuit-trace lines from agent to whichever station it's headed to, diamond-shaped pulsing agent core, HUD-style bordered speech bubble.
- Speech bubble timing fixed: `clamp(text.length() / 12, 3.0, 7.0)` seconds instead of a flat 1.8s — floor keeps even "done" legible, cap keeps a long response from stalling the scene.
- `demo_broadcaster.py` step interval bumped 1.4s → 3.2s to match the new floor, so the recorded GIF is actually readable.
- Re-recorded demo GIF, re-embedded in README.md.

**Decided but not built:**
- Kenney.nl CC0 tileset swap (originally planned) is superseded by the Circuit direction for this repo — no longer the plan here. `cosmo-core`'s sibling visualizer went the pixel-art office route instead; see that repo's PASSDOWN.md.

**Open questions for next session:**
- None outstanding on the visualizer itself. Phase 5 items (event schema versioning, eval harness) are still open, unrelated to this skin work.

---

## 2026-07-25 — Observability, digest tool, live visualizer

**Where things stood coming in:** `agent_core` had a full tool library (files, log, search, weather, tts) and a full test suite, but no real entrypoint — the README's Quick Start was a snippet, not a runnable script — and no digest tool despite the README describing one.

**What got built:**
- `agent_core/events.py` — lazy WebSocket broadcaster (`ws://localhost:8080`), no-op with no listener, wired into `agent.py`'s `call_model` / `execute_tools` at four emit points.
- `agent_core/tools/digest.py` — the digest pattern the README already promised: sandbox state (pending items, recent activity) plus live search, one report.
- `examples/cli_demo.py` — real thin entrypoint, REPL loop, all tools wired.
- `visualizer/` — Godot 4 project. Procedural scene (no external asset dependency yet), `Main.gd` connects as a WebSocket client, animates the agent walking between five stations (Model, Weather, Digest Desk, Log, Files) with speech bubbles, reconnects automatically if the agent process restarts.
- `visualizer/demo_broadcaster.py` — replays a scripted event sequence so the visualizer can be demoed/recorded without an API key.
- Recorded a demo GIF (Xvfb + Godot + ffmpeg), embedded at the top of README.md.
- 32/32 tests passing (`test_events.py`, `test_digest.py` new).
- README reframed: "real-time spatial visualizer and telemetry dashboard for multi-agent systems," architecture diagram extended to show the events → visualizer path.
- ARCHITECTURE.md and MIGRATION.md written for this repo specifically (previously only existed for the private `cosmo-core` sibling project, never for this public one) — see Decision Log in ARCHITECTURE.md, Phase 3/4 in MIGRATION.md.

**Decided but not built (Phase 5 in MIGRATION.md):**
- Event schema has no version field. Fine with one consumer (the visualizer); needs one before a second consumer is built against it.
- Visualizer graphics are procedural `ColorRect` placeholders. Plan is a CC0 top-down tileset from Kenney.nl — swap point is documented in `visualizer/README.md`, logic doesn't change.
- No eval harness yet — scripted scenarios scoring agent output quality, mentioned as debt in ARCHITECTURE.md.

**Open questions for next session:**
- Does the digest tool need a second `topic` example beyond the default, to show it's genuinely reusable and not just a copy of the news block?
- Worth adding a `schema_version` field to events now, before Phase 5, since it's a one-line change and much cheaper before a second consumer exists?

**Culture note — apply this going forward, on every project:** every repo gets `MIGRATION.md` (phased build history, DoD per phase), `ARCHITECTURE.md` (present-tense living doc, decision log), and `PASSDOWN.md` (this file — session log, updated every sitting). The point is that "done" has a written definition and picking the project back up after months away doesn't require reconstructing context from git log.

**Sync discipline — added 2026-08-14, earned via Watchstander's real doc-drift incidents.** Before touching anything in a fresh session on this repo, reconcile local state against this file first:

```
git fetch origin
git status
git log --oneline -5
git branch -a
```

Compare the result against this PASSDOWN's latest entry before assuming it's accurate — a session that skips this step is working from whatever it remembers, not from what's actually on `main`. This matters more on this project specifically because it's worked from multiple machines/sessions, the same pattern that bit Watchstander three times before the rule got written down.

**Lost-patch rule — added 2026-08-14, same root cause as the sync-discipline note above.** Watchstander lost a real, working patch twice because it was delivered chat-only and never saved to disk. Standing rule: every patch that matters gets saved to disk and delivered as a real file in the same session it's built — no exceptions, no "I'll paste it again if you need it."

**Secret-scan habit — added 2026-08-14.** Watchstander found a real secret (an API key file) sitting untracked in a repo folder before it got committed. Since this repo is also public: check `git status` for anything secret-shaped (`.env`, `*key*`, `*token*`, `*credential*` file names) before every `git add .`, not just before the first commit of a session.
