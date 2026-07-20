# Phase 0 Research: Interactive Drive Artifact Prompts

All Technical Context items are known — no `NEEDS CLARIFICATION` markers remain (the spec's
2026-07-20 clarification session resolved the empty/invalid-input behavior). This document records
the technical decisions that shape the implementation.

## Decision 1: Interactive prompt mechanism

- **Decision**: Use the Python built-in `input()` inside the stage cells.
- **Rationale**: `input()` renders a text box in the Colab cell output and blocks execution until
  the user responds — exactly the "pause the stage and ask" behavior FR-003 requires, with zero
  new dependencies (§II) and minimal code (§I). It satisfies the edge case "waits indefinitely if
  the user walks away" (spec Edge Cases) without extra timeout machinery.
- **Alternatives considered**:
  - `ipywidgets` buttons — richer UI but adds an async callback model that does not block a
    top-to-bottom "Run all", breaking US3 and adding complexity (§I violation).
  - Colab `google.colab.output` JS dialogs — Colab-specific, harder to reason about, no benefit
    over `input()` for a two-choice prompt.

## Decision 2: Unattended default constant

- **Decision**: Replace `FORCE_RETRAIN = False` with `UNATTENDED_DEFAULT = None` in Cell 3, where
  valid values are `None` (interactive), `"skip"`, or `"rebuild"`.
- **Rationale**: A single tri-state constant expresses all three US3 modes: `None` prompts
  interactively (FR-003), `"skip"` reuses artifacts silently, `"rebuild"` mirrors the old
  `FORCE_RETRAIN = True` behavior (FR-008, SC-004). Naming it `UNATTENDED_DEFAULT` rather than
  reusing `FORCE_RETRAIN` makes FR-009/SC-005 ("no FORCE_RETRAIN references remain") auditable via
  a simple grep.
- **Alternatives considered**:
  - Keeping `FORCE_RETRAIN` as a boolean plus a second `INTERACTIVE` flag — two constants for one
    concept; violates §I and leaves a `FORCE_RETRAIN` reference (FR-009 violation).
  - Per-stage constants (`STAGE4_MODE`, `STAGE5_MODE`) — more flexible than the spec asks for; the
    spec specifies one top-level default (FR-008).

## Decision 3: Shared helper function

- **Decision**: Define one helper — `artifact_gate(name, drive_path, sentinel)` returning
  `"skip"` or `"rebuild"` — in the Constants cell (Cell 3), and call it from both Stage 4 and
  Stage 5.
- **Rationale**: Both stages share identical prompt/skip/rebuild/re-prompt semantics (FR-003–FR-011).
  A single function guarantees they stay behaviorally identical and keeps the reviewer's reading
  cost low (§I). Defining it in Cell 3 (which always runs first) ensures it exists no matter which
  later cells the user executes.
- **Alternatives considered**:
  - Inlining the prompt logic in each stage — duplicates ~25 lines twice, risks the two stages
    drifting apart, and makes FR-011 (re-prompt-once) harder to keep consistent.

## Decision 4: Detection semantics

- **Decision**: Keep presence-based detection on the existing sentinel files —
  `chroma.sqlite3` for the RAG index and `adapter_model.safetensors` for the LoRA adapter — via
  `os.path.exists`.
- **Rationale**: FR-010 mandates consistency with the existing checks, which already use these two
  sentinels. Presence-based detection matches the spec's explicit edge-case ruling that a corrupt
  artifact is treated identically to a valid one (detection is presence, not validity). A single
  `stat` call keeps SC-001 (<2 s to prompt) trivially satisfied.
- **Alternatives considered**:
  - Validity checks (open the sqlite DB / load the adapter) — explicitly out of scope per the spec
    Assumptions and would slow the prompt.

## Decision 5: Invalid / empty input handling

- **Decision**: Empty input → `"skip"`. Unrecognized input → show the same prompt exactly once
  more; any second response (including empty or still-unrecognized) → `"skip"`.
- **Rationale**: Directly encodes the clarification answer (Option B) and FR-011. Defaulting to
  skip on ambiguity is the safe choice — it never destroys an existing artifact or spends GPU time
  without an explicit "rebuild".
- **Accepted tokens**: skip = `{s, skip, ""}`; rebuild = `{r, rebuild}` (case-insensitive,
  whitespace-trimmed). The rebuild verb is surfaced per-stage ("Rebuild" for Stage 4, "Retrain"
  for Stage 5) in the prompt text for clarity, but both map to the `"rebuild"` outcome.

## Decision 6: Drive-not-mounted / artifact-absent path

- **Decision**: When the sentinel file is absent (including when Drive is unmounted so the path
  does not resolve), `artifact_gate` returns `"rebuild"` without prompting.
- **Rationale**: FR-007 requires no prompt when nothing is found; the spec edge case states an
  absent mount yields "not found" and the stage builds normally. Returning `"rebuild"` (build) is
  the correct default — there is nothing to skip to.
