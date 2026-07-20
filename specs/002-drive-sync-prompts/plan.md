# Implementation Plan: Interactive Drive Artifact Prompts

**Branch**: `002-drive-sync-prompts` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-drive-sync-prompts/spec.md`

## Summary

Replace the single `FORCE_RETRAIN` boolean in `notebook.ipynb` with an interactive per-stage
resumability guard. When Stage 4 (RAG index) or Stage 5 (LoRA adapter) detects an existing
artifact on Google Drive, the notebook prompts the user to **skip** (load the existing artifact)
or **rebuild** (re-run the stage and overwrite the Drive copy). A single top-level constant
(`UNATTENDED_DEFAULT`) pre-answers all prompts so "Run all" executes without pausing. Detection
stays presence-based on the existing sentinel files (`chroma.sqlite3`, `adapter_model.safetensors`).
This is a pure UX change to the guard logic — no model, hyperparameter, generation, or artifact
format changes.

## Technical Context

**Language/Version**: Python 3.10+ (Google Colab default)

**Primary Dependencies**: No new dependencies. Uses the Python built-in `input()` for interactive
prompts and `os.path.exists` for detection — both already implicit in the notebook. Existing
Stage 4/5 dependencies (`chromadb`, `unsloth`, `trl`, `datasets`, `sentence-transformers`) are
unchanged.

**Storage**: Google Drive (`/content/drive/MyDrive/domain-llm-poc/`) — read for artifact
detection, written only when the user chooses rebuild. No new storage locations.

**Testing**: Manual cell-by-cell verification in Colab per the Independent Test steps in the spec;
`quickstart.md` enumerates the runnable validation scenarios. No automated test framework (§I,
qualitative-only per constitution).

**Target Platform**: Google Colab Pro+ (A100/L4/T4). The `input()` prompt renders in the Colab
cell output area and blocks the cell until the user responds.

**Project Type**: Jupyter Notebook — single self-contained file (`notebook.ipynb`)

**Performance Goals**: Prompt appears within 2 s of the stage cell starting (SC-001) — the
detection is a single `os.path.exists` stat call. A skip on Stage 5 returns in under 5 s (SC-002)
versus 20–40 min of training.

**Constraints**: Detection MUST remain presence-based (not validity-based) on the two existing
sentinel files. `FORCE_RETRAIN` MUST be fully removed (FR-009, SC-005). Empty input → skip;
unrecognized input → re-prompt once, then default to skip (FR-011). No prompt when no artifact
exists (FR-007).

**Scale/Scope**: Two artifact-generating stages (Stage 4, Stage 5). One shared helper function,
one new constant, and edits to the two stage guard blocks. Stage 7 notebook-snapshot copy is
explicitly out of scope (non-destructive, no rebuild cost).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle / Constraint | Gate criterion | Status |
|---|---|---|
| §I Simplicity First | One shared helper (~30 lines) + two guard edits; no new abstraction, no framework | ✅ Pass |
| §II Cost Mandate | Zero new libraries; built-in `input()` only; no paid service | ✅ Pass |
| §III Reproducibility | `UNATTENDED_DEFAULT` restores non-interactive "Run all"; artifacts still Drive-persisted; no seed/pin change | ✅ Pass |
| §IV Fair Comparison | No change to base model, quantization, generation params, or prompt scaffolding | ✅ Pass (untouched) |
| Compute | No compute change; prompt is a CPU-side stdin read | ✅ Pass |
| Model | Unchanged (`unsloth/Qwen3.5-9B`) | ✅ Pass |
| Fine-tuning stack | Stage 5 training logic unchanged; only the guard around it changes | ✅ Pass |
| RAG stack | Stage 4 index build unchanged; only the guard around it changes | ✅ Pass |
| Interface | No Gradio change; prompt is a notebook-cell interaction, not a UI framework | ✅ Pass |
| Prohibited list | No paid APIs, Docker, K8s, hosted DB, or React/Vue introduced | ✅ Pass |

**All gates pass. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/002-drive-sync-prompts/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── artifact-prompt.md
├── checklists/
│   └── requirements.md  # Pre-existing (/speckit-checklist)
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
notebook.ipynb           # Main Colab notebook — the only file changed by this feature
  ├── Cell 3  (Constants)     # Remove FORCE_RETRAIN; add UNATTENDED_DEFAULT; add artifact_gate() helper
  ├── Cell 17 (Stage 4 guard) # Replace `_index_exists and not FORCE_RETRAIN` with artifact_gate(...)
  └── Cell 20 (Stage 5 guard) # Replace `_adapter_exists and not FORCE_RETRAIN` with artifact_gate(...)
```

**Structure Decision**: Single-notebook approach per §I (Simplicity First). The prompt logic is a
single reusable helper defined once in the Constants cell (Cell 3) so both Stage 4 and Stage 5
call the same code path — this keeps the two guards behaviorally identical and satisfies FR-003
through FR-011 in one place. Placing the helper in the Constants cell (which runs before any
stage) guarantees it is defined regardless of which stages the user runs.

## Complexity Tracking

> No Constitution Check violations — no justification table needed.

---

## Post-Phase 1 Constitution Re-check

After Phase 1 design:

| Area | Design decision | Compliance |
|---|---|---|
| Helper placement | Single `artifact_gate()` in Cell 3; both stages call it | §I ✅ |
| Detection | Reuses existing `os.path.exists` sentinel checks — no validity parsing | §I ✅, spec FR-010 ✅ |
| Input handling | Built-in `input()`; empty→skip, unrecognized→re-prompt once→skip | §I ✅ |
| Unattended path | `UNATTENDED_DEFAULT` short-circuits `input()`; preserves Run-all reproducibility | §III ✅ |
| Overwrite semantics | Rebuild path unchanged from existing Stage 4/5 write logic | §III ✅ |
| Untouched surfaces | No edits to model load, generation, Gradio, or dataset format | §IV ✅ |

All design decisions comply. No deviations required.
