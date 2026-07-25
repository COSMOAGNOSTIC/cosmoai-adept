# Adversarial Operational Systems Engineering (AOSE)

**Status:** Proposed / Living Engineering Practice
**Author:** Donnie Langford

## What this is

AOSE is a repeatable engineering discipline for building AI-enabled systems: build the smallest working version, then deliberately try to break it — as an inexperienced user, an expert user, a malicious actor, a failed component, and a changed environment would — before fixing what's found and converting every real failure into a permanent regression test. It treats AI-generated critique as input to be judged, never as authority to be trusted, and it explicitly expects the loop to repeat every time the system changes.

The full methodology is written up separately; this file exists so the practice is traceable *in this repo*, not just described in the abstract. Everything below is a real instance of the loop, not a hypothetical.

## The loop, as it actually happened here

```
BUILD → TRY TO BREAK IT → ASSUME USER ERROR / CLEVER MISUSE / MALICIOUS USE →
ASSUME COMPONENT FAILURE → ASSUME ENVIRONMENT CHANGES →
HAVE OTHER AI MODELS CRITIQUE IT → FIX HIGHEST-RISK PROBLEMS →
ADD REGRESSION TESTS → REPEAT
```

**Round 1 (2026-07-25, "external review response," ADR-009):** an independent Fable-model code review — no shared context with the sessions that built this repo — was asked to trace the code, not read the docs. It found that every file/log/digest/tts tool took `sandbox` as a *model-supplied* argument: `safe_path()` correctly blocked `..`/absolute-path/symlink escape, but only *within* whatever root it was handed, and the model chose the root. `read_file(sandbox="/etc", filename="hostname")` returned the real host file — reproduced directly before the fix. It also found the README's own Quick Start crashed on a clean checkout. Both were fixed the same session — see MIGRATION.md Phase 6.5.

**Round 2 (2026-07-25, second-pass review response, ADR-010 through ADR-012):** the same day, a Gemini portfolio assessment gave this repo confident, uncritical praise and a recommendation (add a Mermaid diagram to the README) that was already implemented — Gemini later admitted it had never fetched the repository. Rather than trust either the praise or a second layer of manual copy-paste review, a second independent Fable pass was pointed directly at `config.py`, `memory.py`, and `agent.py` with instructions to trace cold. It found the Round 1 sandbox fix hadn't fully closed the trust boundary: the conversation-memory checkpointer still lived inside the same directory the model's own file tools operate in, and the guard written to prevent sandbox-argument regressions had two fail-open gaps of its own (a Pydantic-v2-only attribute check that silently passed anything it couldn't introspect, and a name match on the single literal string `"sandbox"`). See MIGRATION.md Phase 6.75.

## Why round 2 matters more than round 1

Round 1 demonstrates that adversarial AI review catches real bugs. Round 2 demonstrates something the methodology needs to keep repeating: **fixing a finding can leave a related trust boundary unfixed, or introduce a fail-open gap in the fix itself — and only re-attacking the fix (not just the original code) catches it.** The sandbox-argument bug and the memory-directory bug are the *same class* of problem (a model-reachable directory holding something it shouldn't reach); finding and fixing one didn't guarantee the other got checked. A single review pass, however good, is a snapshot — the loop's value is in the "repeat," not the first iteration.

## A caveat this methodology needed, found the same day

Gemini's assessment wasn't just wrong about a recommendation — when asked directly, it admitted it had produced the entire review by pattern-matching on repo names and prior chat context, never having fetched the actual files. The methodology's existing rule — "AI-generated criticism is input, not authority" — already covered this in principle, but this was the concrete case that earned it a second half: **an AI reviewer can also be confidently, ungroundedly wrong in the *complimentary* direction, not just the critical one.** Uncritical praise from a model that never examined the artifact is exactly as unreliable as an ungrounded criticism, and both need the same check before being acted on: did this reviewer actually look at the thing it's describing?

## Where the discipline is still open

- Symlink TOCTOU race in `safe_path()`: resolved at check time, opened afterward — a narrow window exists between the two. Low risk in the current single-process design, not yet closed.
- `config.py`'s module-level env reads are still frozen at import time; the Round 2 stderr warning makes a missing `.env` visible, it doesn't make the values reloadable without re-importing.
- No dependency version pinning / lockfile yet.
- An eval harness (scripted scenarios scoring agent output quality) has been flagged by three independent reviewers as the highest-leverage next investment — Watchstander's sibling repo already has one built as a reference pattern; this repo doesn't yet.

These are listed here, not hidden, because AOSE's Step 10 says a discovered failure becomes one of three things: fixed and tested, an accepted risk, or documented technical debt. All three categories exist in this repo on purpose.

---

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component map and full decision log (ADR-001 through ADR-012), and [MIGRATION.md](MIGRATION.md) / [PASSDOWN.md](PASSDOWN.md) for the phase-by-phase and session-by-session record this file draws from.
