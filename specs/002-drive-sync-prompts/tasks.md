---
description: "Task list for Interactive Drive Artifact Prompts"
---

# Tasks: Interactive Drive Artifact Prompts

**Input**: Design documents from `specs/002-drive-sync-prompts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/artifact-prompt.md, quickstart.md

**Tests**: No automated test tasks. Per the constitution (§Evaluation Standard — qualitative
side-by-side only) and the spec (no TDD requested), validation is manual via `quickstart.md`.

**Organization**: Tasks are grouped by user story. All changes are in the single file
`notebook.ipynb`; the affected cells are noted per task.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies). ⚠️ This feature touches a single
  file (`notebook.ipynb`), so cross-task `[P]` is rare — most tasks edit the same file and are
  sequential to avoid clobbering. `[P]` is used only where a task edits a genuinely separate cell
  with no shared state and no ordering constraint.
- **[Story]**: Which user story the task belongs to (US1, US2, US3).
- Exact cell locations are given in each description.

## Cell Map (from plan.md)

- **Cell 3** — Constants: holds `FORCE_RETRAIN` (to remove), the new `UNATTENDED_DEFAULT`, and the new `artifact_gate()` helper.
- **Cell 17** — Stage 4 (RAG index) guard.
- **Cell 20** — Stage 5 (LoRA adapter) guard.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the editing surface before changing behavior.

- [X] T001 Open `notebook.ipynb` and confirm the three target cells: the Constants cell containing `FORCE_RETRAIN` (Cell 3), the Stage 4 guard `if _index_exists and not FORCE_RETRAIN:` (Cell 17), and the Stage 5 guard `if _adapter_exists and not FORCE_RETRAIN:` (Cell 20). Record their current index positions in case the notebook has been re-ordered.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared constant and helper that all three user stories depend on. Per
research.md Decision 3 and the contract, this lives in the Constants cell so it is defined before
any stage runs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — Stage 4 and Stage 5
both call `artifact_gate()`.

- [X] T002 In `notebook.ipynb` Cell 3 (Constants), replace the `FORCE_RETRAIN = False` line with `UNATTENDED_DEFAULT = None  # None → interactive prompt | "skip" | "rebuild"` (data-model.md: Unattended Default entity; FR-008, FR-009).
- [X] T003 In `notebook.ipynb` Cell 3, implement the `artifact_gate(name, drive_path, sentinel, rebuild_verb="Rebuild")` helper per contracts/artifact-prompt.md — presence-based detection via `os.path.exists(f"{drive_path}/{sentinel}")`, `UNATTENDED_DEFAULT` short-circuit, `input()` prompt with the contract's prompt text, empty→skip, unrecognized→re-prompt once→skip, returning exactly `"skip"` or `"rebuild"` (satisfies guarantees C1–C10; FR-003–FR-007, FR-010, FR-011).
- [X] T004 In `notebook.ipynb` Cell 3, add validation at the top of `artifact_gate` (or immediately after the constant) that raises a clear `ValueError` if `UNATTENDED_DEFAULT` is not in `{None, "skip", "rebuild"}` (contract guarantee C11; data-model.md validation rule).

**Checkpoint**: `UNATTENDED_DEFAULT` and `artifact_gate()` are defined; running Cell 3 executes without error and both stages can now call the gate.

---

## Phase 3: User Story 1 - Skip or Rebuild RAG Index (Priority: P1) 🎯 MVP

**Goal**: Stage 4 pauses when a ChromaDB index exists on Drive and lets the user skip (load) or rebuild (re-embed + overwrite).

**Independent Test**: Run Stage 4 twice in one session — the second run shows a prompt; `s` loads the existing index with no re-embedding, `r` rebuilds and overwrites the Drive copy (spec US1 Independent Test).

- [X] T005 [US1] In `notebook.ipynb` Cell 17 (Stage 4), replace the `_index_exists = os.path.exists(...)` + `if _index_exists and not FORCE_RETRAIN:` guard with a single call: `_gate = artifact_gate("RAG index", f"{DRIVE_BASE}/chroma_index", "chroma.sqlite3", rebuild_verb="Rebuild")` followed by `if _gate == "skip":` (contract "Call-site contract"; FR-001, FR-003, FR-004).
- [X] T006 [US1] In `notebook.ipynb` Cell 17, keep the existing skip branch body (load collection, print loaded-chunk count) under the `if _gate == "skip":` arm and the existing build body (load docs → chunk → embed → recreate collection → write to Drive) under the `else:` arm unchanged, so skip leaves the Drive index untouched (FR-005) and rebuild overwrites it (FR-006). Remove the now-dead `FORCE_RETRAIN` reference and the "set FORCE_RETRAIN=True to rebuild" hint from the skip message.
- [ ] T007 [US1] Validate Stage 4 per quickstart.md Scenarios A, B, C and spec US1 acceptance scenarios 1–6: prompt appears within 2 s (SC-001), skip loads without embedding, rebuild overwrites, empty→skip, unrecognized→re-prompt-once→skip, and no-artifact→no-prompt (FR-007).

**Checkpoint**: Stage 4 is fully interactive and independently testable; the RAG-index resumability guard no longer references `FORCE_RETRAIN`.

---

## Phase 4: User Story 2 - Skip or Retrain LoRA Adapter (Priority: P2)

**Goal**: Stage 5 pauses when a LoRA adapter exists on Drive and lets the user skip (reuse) or retrain (train + overwrite).

**Independent Test**: With an adapter on Drive, run Stage 5 and choose skip → Stage 6 proceeds immediately with the existing adapter; rerun and choose retrain → training completes and the Drive adapter is overwritten (spec US2 Independent Test).

- [X] T008 [US2] In `notebook.ipynb` Cell 20 (Stage 5), replace the `_adapter_exists = os.path.exists(...)` + `if _adapter_exists and not FORCE_RETRAIN:` guard with a single call: `_gate = artifact_gate("LoRA adapter", f"{DRIVE_BASE}/lora_adapter", "adapter_model.safetensors", rebuild_verb="Retrain")` followed by `if _gate == "skip":` (contract "Call-site contract"; FR-002, FR-003, FR-004).
- [X] T009 [US2] In `notebook.ipynb` Cell 20, keep the existing skip branch (print "skipping", leave adapter in place) under `if _gate == "skip":` and the existing train branch (JSONL validation → dataset backup → LoRA → train → save adapter) under `else:` unchanged, so skip bypasses training (FR-005) and retrain overwrites the adapter (FR-006). Remove the now-dead `FORCE_RETRAIN` reference and the "set FORCE_RETRAIN=True to retrain" hint from the skip message.
- [ ] T010 [US2] Validate Stage 5 per quickstart.md Scenarios D, E, K and spec US2 acceptance scenarios 1–6: skip completes in under 5 s (SC-002), retrain overwrites the Drive adapter and the new version loads in a later session (SC-003, Scenario K), empty→skip, unrecognized→re-prompt-once→skip, and no-adapter→no-prompt (FR-007).

**Checkpoint**: Stage 5 is fully interactive and independently testable; both Stage 4 and Stage 5 now share the identical gate behavior.

---

## Phase 5: User Story 3 - Unattended Run Mode (Priority: P3)

**Goal**: A single top-level constant pre-answers every artifact prompt so "Run all" executes without pausing.

**Independent Test**: Set `UNATTENDED_DEFAULT = "skip"` and Run all → no pauses, artifacts reused; set `UNATTENDED_DEFAULT = "rebuild"` and Run all → no pauses, all artifacts rebuilt (spec US3 Independent Test).

> The unattended short-circuit is implemented inside `artifact_gate` (T003). This phase verifies the
> three modes end to end and closes out the `FORCE_RETRAIN` removal across the whole notebook.

- [X] T011 [US3] Scan the entire `notebook.ipynb` (all cells, markdown and code) for any remaining `FORCE_RETRAIN` reference — including comments, print strings, and Stage 6/7 cells — and remove or rewrite each so zero references remain (FR-009, SC-005).
- [ ] T012 [US3] Validate unattended mode per quickstart.md Scenarios G, H and spec US3 acceptance scenarios 1–3: with `UNATTENDED_DEFAULT="skip"` Run all reuses artifacts with no pause; with `"rebuild"` Run all rebuilds all artifacts with no pause (matching former `FORCE_RETRAIN=True`, SC-004); with `None` each stage prompts when an artifact is found.

**Checkpoint**: All three run modes (interactive, unattended-skip, unattended-rebuild) work; no `FORCE_RETRAIN` remains anywhere.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all stories.

- [X] T013 Run `grep -c "FORCE_RETRAIN" notebook.ipynb` and confirm the result is `0` (quickstart.md Scenario I; SC-005).
- [ ] T014 Execute the full quickstart.md suite (Scenarios A–K) top to bottom on a fresh Colab session with pre-existing Drive artifacts, confirming every scenario's expected outcome and that no manual `FORCE_RETRAIN` editing is needed.
- [ ] T015 Verify §III reproducibility: on a Colab session with **no** artifacts on Drive (clean `DRIVE_BASE`), run the notebook top to bottom (Runtime ▸ Run all) with `UNATTENDED_DEFAULT = None` and confirm no prompt pauses occur and all stages build normally (quickstart.md Scenario J; FR-007, constitution §III).
- [X] T016 If any deviation from the constitution's Build Order or guard behavior was introduced, record a one-line note in the notebook's Deviations section (constitution §Governance); otherwise confirm none is needed.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **BLOCKS all user stories** (T005, T008 call `artifact_gate`; the unattended path in US3 is implemented here).
- **User Stories (Phase 3–5)**: All depend on Phase 2. US3's verification (T012) additionally depends on US1 and US2 being wired so a full Run-all exercises both prompts.
- **Polish (Phase 6)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational (T003). Independently testable via Stage 4 alone.
- **US2 (P2)**: Depends only on Foundational (T003). Independently testable via Stage 5 alone. Independent of US1.
- **US3 (P3)**: Short-circuit logic delivered by Foundational (T003). Full Run-all verification (T012) exercises US1 + US2 prompts, so run it after both are wired.

### Within Each User Story

- Guard-swap task (T005 / T008) before its body-preservation task (T006 / T009) before its validation task (T007 / T010).

### Parallel Opportunities

- ⚠️ **Single-file constraint**: every implementation task edits `notebook.ipynb`. To avoid clobbering the notebook JSON, implementation tasks should be applied **sequentially**, not concurrently, even where cells are logically independent.
- The logically-independent work is US1 (Cell 17) vs US2 (Cell 20): once Foundational is done, these two edits can be assigned to different people **if** they coordinate notebook merges, but they are not marked `[P]` because they share one file.
- Validation tasks (T007, T010, T012) can be observed together in a single Run-all pass once all edits are in.

---

## Parallel Example

```text
# Single-file feature — no safe cross-task file parallelism.
# Recommended order once Phase 2 is complete:
T005 → T006 → T007   (US1, Cell 17)
T008 → T009 → T010   (US2, Cell 20)
T011 → T012          (US3, whole-notebook sweep + Run-all verify)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001).
2. Complete Phase 2: Foundational (T002–T004) — **critical, blocks everything**.
3. Complete Phase 3: User Story 1 (T005–T007).
4. **STOP and VALIDATE**: Stage 4 prompts and skips/rebuilds correctly.
5. Demo the interactive RAG-index guard.

### Incremental Delivery

1. Setup + Foundational → constant and helper defined.
2. US1 → Stage 4 interactive → validate → demo (MVP!).
3. US2 → Stage 5 interactive → validate → demo.
4. US3 → unattended modes verified + `FORCE_RETRAIN` fully removed → validate → demo.
5. Polish → grep-clean confirmation + full quickstart pass.

---

## Notes

- All edits are in `notebook.ipynb`; keep the skip/rebuild **branch bodies** identical to the current code — only the guard condition changes (contract: no behavioral change to embedding/training/save).
- `UNATTENDED_DEFAULT` replaces `FORCE_RETRAIN`; verify zero residual references (T013).
- Each user story is independently testable via its own stage; stop at any checkpoint to validate.
- Commit after each phase (or logical task group).
