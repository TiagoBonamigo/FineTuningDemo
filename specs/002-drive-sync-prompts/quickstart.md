# Quickstart: Validating Interactive Drive Artifact Prompts

This guide lists the runnable scenarios that prove the feature works end to end. Run them in a
Colab session on `notebook.ipynb` after the feature is implemented. See
[contracts/artifact-prompt.md](contracts/artifact-prompt.md) for the exact prompt text and return
semantics, and [data-model.md](data-model.md) for the state transitions.

## Prerequisites

- A Colab session with Drive mounted (Stage 1 run) and `DRIVE_BASE` populated from a prior full
  run, so `{DRIVE_BASE}/chroma_index/chroma.sqlite3` and
  `{DRIVE_BASE}/lora_adapter/adapter_model.safetensors` already exist.
- Cell 3 (Constants) executed so `UNATTENDED_DEFAULT` and `artifact_gate` are defined.

## Scenario A — Stage 4 interactive skip (US1, FR-003/FR-005)

1. Set `UNATTENDED_DEFAULT = None` in Cell 3 and run it.
2. Run Stage 4 (Cell 17).
3. **Expect**: within 2 s, a prompt naming the RAG index and its Drive path appears (SC-001).
4. Type `s` and press Enter.
5. **Expect**: "Loaded existing collection: N chunks"; no embedding progress bar; Drive index
   untouched.

## Scenario B — Stage 4 interactive rebuild (US1, FR-006)

1. With `UNATTENDED_DEFAULT = None`, run Stage 4 again.
2. At the prompt, type `r`.
3. **Expect**: documents load, chunks embed (progress bar), a fresh index is written and the Drive
   copy is overwritten.

## Scenario C — Empty and invalid input (FR-011)

1. `UNATTENDED_DEFAULT = None`, artifact present, run Stage 4.
2. Press Enter with no text → **Expect**: treated as skip (Scenario A outcome).
3. Run again, type `maybe` (unrecognized) → **Expect**: the same prompt reappears exactly once.
4. On the second prompt type `xyz` (or press Enter) → **Expect**: defaults to skip and continues.
5. Run again, type `maybe`, then on the re-prompt type `r` → **Expect**: rebuild proceeds.

## Scenario D — Stage 5 skip saves training time (US2, SC-002)

1. `UNATTENDED_DEFAULT = None`, adapter present, run Stage 5 (Cell 20).
2. At "LoRA adapter found … Skip (s) or Retrain (r)?", type `s`.
3. **Expect**: Stage 5 completes in under 5 s (printed `Stage 5 complete in …s`); no training loop;
   Stage 6 loads the existing adapter.

## Scenario E — Stage 5 retrain (US2, FR-006)

1. `UNATTENDED_DEFAULT = None`, run Stage 5, type `r`.
2. **Expect**: JSONL validation, training runs to completion, adapter saved and Drive copy
   overwritten.

## Scenario F — No artifact → no prompt (FR-007)

1. Delete (or point `DRIVE_BASE` away from) the sentinel files.
2. Run Stage 4 and Stage 5.
3. **Expect**: no prompt appears; both stages build normally.

## Scenario G — Unattended "skip" (US3 AS-1, SC-004)

1. Set `UNATTENDED_DEFAULT = "skip"`, artifacts present, choose Runtime ▸ Run all.
2. **Expect**: no pause at Stage 4 or Stage 5; existing artifacts reused; notebook runs all stages
   uninterrupted.

## Scenario H — Unattended "rebuild" (US3 AS-2, SC-004)

1. Set `UNATTENDED_DEFAULT = "rebuild"`, Run all.
2. **Expect**: no pause; index rebuilt and adapter retrained, matching former `FORCE_RETRAIN = True`
   throughput.

## Scenario I — Regression: no FORCE_RETRAIN remains (FR-009, SC-005)

1. Search the notebook source:
   ```bash
   grep -c "FORCE_RETRAIN" notebook.ipynb
   ```
2. **Expect**: `0` matches.

## Scenario J — Clean-slate reproducibility run (§III, FR-007)

1. Point `DRIVE_BASE` at an empty folder (or delete both sentinel files) so no artifacts exist.
2. Set `UNATTENDED_DEFAULT = None` and choose Runtime ▸ Run all.
3. **Expect**: no prompt pauses at any stage; Stage 4 builds the index and Stage 5 trains, both
   without asking — matching the "top to bottom without manual intervention" guarantee (§III).

## Scenario K — Rebuild persists across sessions (SC-003)

1. With an artifact present and `UNATTENDED_DEFAULT = None`, run Stage 4 (or Stage 5) and choose
   rebuild/retrain; note the new artifact is written to Drive.
2. Disconnect and start a fresh Colab session; run Stage 1 (Drive mount), then the same stage and
   choose skip.
3. **Expect**: the artifact loaded is the version rebuilt in step 1 (e.g., updated chunk count or
   adapter timestamp), confirming the overwrite persisted across sessions.

## Pass criteria

All scenarios A–K behave as described, matching the acceptance scenarios in
[spec.md](spec.md) and the behavioral guarantees C1–C11 in the contract.
