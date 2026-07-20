---
description: "Task list for Drive-Cached Dependency Install"
---

# Tasks: Drive-Cached Dependency Install

**Input**: Design documents from `specs/003-pip-cache-drive/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/deps-cache.md, quickstart.md

**Tests**: No automated test tasks. Per the constitution (§Evaluation Standard — qualitative only)
and the spec (no TDD requested), validation is manual via `quickstart.md`.

**Organization**: Tasks are grouped by user story. All changes are in the single file
`notebook.ipynb` (plus its Deviations markdown); affected cells are noted per task.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies). ⚠️ This feature edits a single
  file (`notebook.ipynb`), almost entirely Cell 1. `[P]` is therefore essentially unused — tasks
  are sequential to avoid clobbering the notebook JSON and the shared Stage-0 block.
- **[Story]**: US1 / US2 / US3.
- Exact cell locations are given in each description.

## Cell Map (from plan.md)

- **Cell 1** — Stage 0 (Install & Config): gains a bootstrap prologue + wheelhouse cache logic (the
  bulk of this feature).
- **Cell 3** — Constants: loses the relocated `DRIVE_BASE`, `UNATTENDED_DEFAULT`, `artifact_gate`.
- **Deviations** — a notebook markdown cell recording the Build-Order change (§Governance).

## Story slicing rationale

The wheelhouse engine is monolithic, so the stories are sliced by *how strict the reuse decision is*:
US1 reuses a present cache (the speed-up), US2 adds manifest-hash invalidation (makes reuse correct
when deps change), US3 adds fingerprint invalidation + failure fallbacks (makes reuse safe across
runtimes and Drive faults). Each slice is independently demoable.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the editing surface and baseline before restructuring.

- [X] T001 In `notebook.ipynb`, confirm Cell 1 (Stage 0 `!pip install`), Cell 3 (Constants defining `DRIVE_BASE`, `UNATTENDED_DEFAULT`, `artifact_gate`), and the Stage 1 `drive.mount` (Cell 9); record the current pinned dependency list verbatim and the cold Stage-0 install time as the SC-001/SC-005 baseline.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Restructure Stage 0 so the cache can be consulted before install, WITHOUT changing
install behavior yet (still installs online). This unblocks all three stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — every story builds on
the relocated helpers and the requirements-as-list refactor.

- [X] T002 In `notebook.ipynb`, relocate `DRIVE_BASE`, `UNATTENDED_DEFAULT`, and the `artifact_gate` definition from Cell 3 into a new bootstrap prologue at the **top of Cell 1**, and delete them from Cell 3 (contracts/deps-cache.md "Cell 3 call-site contract"; plan Structure Decision). Confirm Stage 4/5 (`artifact_gate` call sites) still resolve against the relocated definition.
- [X] T003 In `notebook.ipynb` Cell 1 bootstrap, add `import os, sys`; mount Drive via `google.colab.drive` wrapped in try/except (idempotent, non-fatal); and define `DEPS_CACHE_DIR = f"{DRIVE_BASE}/deps_cache"` and `FORCE_REBUILD_DEPS = False` (contracts constant contract; data-model control constants).
- [X] T004 In `notebook.ipynb` Cell 1, refactor the existing `!pip install` into an explicit Python list of pinned requirement strings (`PINNED_REQS`) used as the single source for both the wheelhouse build and every install path (contracts "Wheelhouse operation contract"; guarantees D12/FR-008).
- [ ] T005 Verify the restructured notebook still performs a normal online install end-to-end (Stage 0 completes; later stages import) and that Feature 002's Stage 4/5 prompts still work — a pure-refactor regression check before caching is added.

**Checkpoint**: Stage 0 mounts Drive, defines cache constants + relocated helpers, and installs online exactly as before. No caching yet.

---

## Phase 3: User Story 1 - Fast startup from a warm cache (Priority: P1) 🎯 MVP

**Goal**: A restarted runtime installs from a Drive wheelhouse instead of the internet, gated by the
same skip/rebuild prompt as Feature 002.

**Independent Test**: Run Stage 0 once (builds + saves the wheelhouse), restart the runtime, run
Stage 0 again → offline install, markedly faster, all imports succeed (quickstart Scenarios A, B).

- [X] T006 [US1] In `notebook.ipynb` Cell 1, implement `runtime_fingerprint()` (→ `py{maj}.{min}-{cuda_tag}` from `sys` + `nvidia-smi`, `cpu` if no GPU) and `manifest_hash(reqs)` (→ sha256 of the normalized `PINNED_REQS`), per contracts F1–F4 / M1–M3. (Defined here as US1 is first to write the sentinels; the *conditions* using them arrive in US2/US3.)
- [X] T007 [US1] In `notebook.ipynb` Cell 1, implement the **rebuild path**: `pip wheel --wheel-dir={DEPS_CACHE_DIR}/wheels PINNED_REQS` → `pip install --no-index --find-links={DEPS_CACHE_DIR}/wheels PINNED_REQS` → write `manifest.sha256` and `fingerprint.txt` to `DEPS_CACHE_DIR` (data-model REBUILD; contracts D2/D7/D10).
- [X] T008 [US1] In `notebook.ipynb` Cell 1, implement the **warm path + decision**: if the wheelhouse is present, decide via `FORCE_REBUILD_DEPS` → else `artifact_gate("Dependency cache", DEPS_CACHE_DIR, "manifest.sha256", rebuild_verb="Rebuild")`; on `"skip"` run offline `pip install --no-index --find-links=…/wheels PINNED_REQS`; on `"rebuild"` run the T007 path (contracts D5/D6/D7; FR-002/FR-009; SC-002). Note: T007 MUST write `manifest.sha256` **last** (after wheels + `fingerprint.txt`) so its presence implies a complete save.
- [X] T009 [US1] In `notebook.ipynb` Cell 1, print at the end of Stage 0 whether dependencies were served from cache or freshly installed, plus elapsed seconds (contracts D11; FR-011).
- [ ] T010 [US1] Validate per quickstart Scenarios A, B, C, D and spec US1 acceptance scenarios: first run builds+saves the wheelhouse; a restarted warm run installs offline with zero downloads (SC-002), ≥3× faster / <90 s target (SC-001); interactive `r` rebuilds and `s`/empty reuses; `FORCE_REBUILD_DEPS=True` forces rebuild.

**Checkpoint**: Warm restarts reuse the Drive wheelhouse via the Feature-002-style prompt. (Reuse is presence-based only until US2/US3 tighten validity.)

---

## Phase 4: User Story 2 - Automatic refresh when dependencies change (Priority: P2)

**Goal**: A changed pinned dependency list auto-rebuilds the cache — no stale-dependency runs.

**Independent Test**: With a warm cache, edit `PINNED_REQS` and re-run Stage 0 → the cache rebuilds
and the new/changed package is present (quickstart Scenario E).

- [X] T011 [US2] In `notebook.ipynb` Cell 1, add the **manifest-hash condition** to the reuse decision: reuse (allow the skip prompt) only when the stored `manifest.sha256` equals `manifest_hash(PINNED_REQS)`; otherwise force a rebuild with no prompt (data-model "not valid → REBUILD"; contracts D3; FR-004/SC-004).
- [ ] T012 [US2] Validate per quickstart Scenario E and spec US2 acceptance scenarios: changing `PINNED_REQS` triggers an automatic rebuild (no skip prompt), the changed package is installed, and `manifest.sha256` updates; an unchanged list still reuses.

**Checkpoint**: The cache can no longer serve dependencies that don't match the declared list.

---

## Phase 5: User Story 3 - Safe fallback on an incompatible runtime (Priority: P3)

**Goal**: A runtime whose Python/CUDA differs from the cache, or an unusable Drive/cache, never
restores broken wheels — it cleanly (re)installs instead.

**Independent Test**: Build the cache on one tier, start a runtime with a different CUDA tag, run
Stage 0 → clean rebuild instead of restoring incompatible wheels; all imports succeed (Scenario F).

- [X] T013 [US3] In `notebook.ipynb` Cell 1, add the **fingerprint condition** to the reuse decision: reuse only when stored `fingerprint.txt` equals `runtime_fingerprint()`; otherwise force a clean rebuild with no prompt (contracts D4; FR-005).
- [X] T014 [US3] In `notebook.ipynb` Cell 1, add robustness fallbacks: treat a missing/partial wheelhouse or unreadable sentinel as "no usable cache"; wrap the offline install so a failure falls back to a normal online install; make Drive-write failures non-fatal with a warning (contracts D1/D8/D9; FR-007/SC-006; edge cases).
- [ ] T015 [US3] Validate per quickstart Scenarios F, G, H, I and spec US3 acceptance scenarios: fingerprint mismatch → clean rebuild; Drive-absent and corrupt-cache → online-install fallback succeeds (SC-006); warm never slower than cold (SC-005); warm vs cold yield identical versions (FR-008/SC-003).

**Checkpoint**: All three run modes (warm reuse, auto-rebuild on change, safe fallback) work; setup never hard-fails.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Governance and full-suite verification.

- [X] T016 Add/append a **Deviations** note in `notebook.ipynb` recording that the Drive mount and shared helpers (`DRIVE_BASE`, `UNATTENDED_DEFAULT`, `artifact_gate`) were moved into the Stage 0 bootstrap ahead of install, with a one-line justification (constitution §Governance; plan §Governance flag).
- [X] T017 Regression checks via `grep`: exactly one `def artifact_gate(` and one `UNATTENDED_DEFAULT` assignment remain (no duplication after relocation), and no `FORCE_RETRAIN` reference reappears (Feature 002 intact).
- [ ] T018 Execute the full quickstart suite (Scenarios A–I) top to bottom on a fresh Colab session, confirming every scenario's expected outcome including the SC-001/SC-005 timing comparison against the T001 baseline.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — start immediately.
- **Foundational (Phase 2)**: depends on Setup. **BLOCKS all stories** (relocation + `PINNED_REQS` refactor underpin every cache path).
- **US1 (Phase 3)**: depends on Foundational. Delivers the MVP.
- **US2 (Phase 4)**: depends on US1 (adds a condition to US1's decision logic).
- **US3 (Phase 5)**: depends on US1 (adds conditions + fallbacks to US1's decision logic); independent of US2.
- **Polish (Phase 6)**: depends on all stories.

### Within Each User Story

- Helpers/rebuild (T006, T007) before warm-path decision (T008) before report (T009) before validation (T010).
- US2/US3 condition tasks (T011, T013) before their validation (T012, T015).

### Parallel Opportunities

- ⚠️ **Single-file, single-cell**: nearly all tasks edit Cell 1 of `notebook.ipynb`. They MUST be applied sequentially; no cross-task `[P]` is safe.
- US2 (T011) and US3 (T013/T014) both amend the same decision block in Cell 1, so despite being independent stories they cannot be edited concurrently — sequence US2 then US3 (or vice versa).
- Validation observations (T010, T012, T015, T018) can be gathered together in a single Colab Run-all pass once edits are in.

---

## Parallel Example

```text
# Single-file feature — sequential only. Recommended order after Phase 2:
T006 → T007 → T008 → T009 → T010     (US1 engine + MVP validation)
T011 → T012                          (US2 manifest invalidation)
T013 → T014 → T015                   (US3 fingerprint + robustness)
T016 → T017 → T018                   (polish: deviations, grep, full suite)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup (T001).
2. Phase 2 Foundational (T002–T005) — **critical, blocks everything**.
3. Phase 3 US1 (T006–T010).
4. **STOP and VALIDATE**: warm restart reuses the wheelhouse and is markedly faster.
5. Demo the speed-up. (US1 alone reuses on presence; land US2/US3 before relying on it across dep or runtime changes.)

### Incremental Delivery

1. Setup + Foundational → Stage 0 restructured, still online-installs.
2. US1 → warm-cache speed-up → validate → demo (MVP!).
3. US2 → auto-rebuild on dependency change → validate → demo.
4. US3 → safe fallback on runtime mismatch / Drive faults → validate → demo.
5. Polish → deviations note, grep regression, full quickstart.

---

## Notes

- All edits are in `notebook.ipynb` (mostly Cell 1); keep the pinned list (`PINNED_REQS`) the single
  source for wheel build and every install so warm/cold versions stay identical (FR-008).
- Reuses Feature 002's `artifact_gate` (now relocated to the Stage 0 bootstrap) — do not add a second
  prompt implementation (FR-009).
- Caching must never make setup fail (FR-007) or slower than cold (SC-005); the T009 timing report
  and the T014 fallbacks are what enforce this.
- Commit after each phase (or logical task group).
