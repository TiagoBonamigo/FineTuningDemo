---
description: "Task list for Notebook Split (Phase Notebooks)"
---

# Tasks: Notebook Split (Phase Notebooks)

**Input**: Design documents from `specs/004-notebook-split/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: No automated tests — validation is manual per `quickstart.md` (constitution §Evaluation
Standard: qualitative side-by-side only). Story phases end with a manual validation checkpoint.

**Organization**: Tasks grouped by user story. Paths are relative to the repo root
(`/d/Projects/fine-tuning-demo`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1 / US2 / US3 for user-story phases; Setup/Foundational/Polish carry no story label

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the shared module scaffold and the reusable bootstrap pattern.

- [X] T001 Create `config.py` at repo root — module docstring + empty sections (Constants, Profile,
      Seeds/Drive, Feature-002 gate, Feature-003 wheelhouse, Sidecar) so later tasks fill one file.
- [X] T002 [P] Finalize the reusable cell-1 bootstrap snippet (repo clone/pull → `sys.path` → `import
      config` → `config.mount_drive()` → define `PINNED_REQS` → `config.install_deps(PINNED_REQS)` →
      `config.set_seeds()`), incl. the private-repo token / raw-download fallback (research.md D2), as
      a copy-ready block noted in `specs/004-notebook-split/contracts/notebook-io.md`.
- [X] T003 [P] Confirm `config.py` is git-tracked (NOT in `.gitignore`) and that `chroma_index/`,
      `lora_adapter/`, `training_dataset.jsonl`, `gguf_export/`, `deps_cache/` remain gitignored.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement `config.py` — the single cross-notebook import every notebook depends on.

**⚠️ CRITICAL**: No user story can be built until `config.py` exists. All tasks below edit the same
file (`config.py`), so they run sequentially (no `[P]`). Contract: `contracts/config-module.md`.

- [X] T004 Port every constant from the current Stage 0 Constants cell into `config.py` as the single
      source of truth (model/LoRA/training/RAG/generation/prompts/paths); extract the hardcoded
      embedder into `EMBED_MODEL = "all-MiniLM-L6-v2"`. Keep `ENABLE_THINKING = False` (§IV).
- [X] T005 Implement `select_profile(vram_gb)` in `config.py` from the current Cell 5 logic (A100
      default + T4 fallback below 24 GB); default set MUST fit A100, fallback MUST fit 16 GB T4 (§III).
- [X] T006 Implement `set_seeds()` and idempotent `mount_drive()` in `config.py` (torch imported
      lazily; import of `config` stays side-effect-free per contract).
- [X] T007 Port Feature 002 `artifact_gate(name, drive_path, sentinel, rebuild_verb)` into `config.py`
      unchanged in semantics (honors `UNATTENDED_DEFAULT`).
- [X] T008 Port Feature 003 wheelhouse into `config.py` as `install_deps(reqs)`, re-keyed to
      `deps_cache/{fingerprint}/{manifest8}/wheels/` (manifest8 = hash of `reqs`); preserve cold-build /
      warm-offline / online-fallback paths (research.md D6).
- [X] T009 Implement `write_meta(dir, meta)` (atomic, written last) and `verify_meta(dir, expected)`
      (missing dir → fail-fast per FR-007; field mismatch → ValueError naming field + phase per FR-013)
      in `config.py`.

**Checkpoint**: `import config` succeeds with no pip/Drive/GPU side effects; all functions importable.

---

## Phase 3: User Story 1 — Run one phase in isolation with only its deps (P1) 🎯 MVP

**Goal**: The two build phases each run standalone in a minimal, conflict-free environment.

**Independent Test**: On fresh runtimes, `01_build_index.ipynb` produces `chroma_index/` with no
fine-tune/UI deps installed, and `02_finetune.ipynb` produces `lora_adapter/` with no RAG/UI deps and
no pip conflict (quickstart Scenarios A & B; SC-001, SC-006).

- [X] T010 [P] [US1] Create `01_build_index.ipynb` — cell-1 bootstrap with
      `PINNED_REQS = [sentence-transformers>=5.2, chromadb>=1.0, langchain-text-splitters>=0.3,
      pypdf>=4.0]`; port Stage 4 (load docs, chunk, embed, build Chroma collection `domain_docs`);
      gate via `config.artifact_gate("RAG index", chroma_index, "chroma.sqlite3")`; on build call
      `config.write_meta(chroma_index, {embed_model, chunk_size, chunk_overlap})`; add `## Deviations`
      note (feature 004 / constitution v1.2.0).
- [X] T011 [P] [US1] Create `02_finetune.ipynb` — cell-1 bootstrap with
      `PINNED_REQS = [unsloth, unsloth_zoo, transformers>=5.2, trl>=0.15, peft>=0.14, bitsandbytes>=0.45,
      datasets>=3.0]`; `config.select_profile(vram)` before base load; port Stage 2 (base load) + Stage 5
      (JSONL validation, LoRA, train, save adapter); gate via `config.artifact_gate("LoRA adapter",
      lora_adapter, "adapter_model.safetensors", "Retrain")`; on train call `config.write_meta(
      lora_adapter, {base_model_id, max_seq_len, lora_r, lora_alpha, lora_targets, seed})`; add
      `## Deviations` note.
- [ ] T012 [US1] Validate isolation per quickstart Scenarios A & B: each notebook installs only its
      own stack (`pip list` excludes the other), no dependency-conflict error on install, artifacts +
      `meta.json` land on Drive.

**Checkpoint**: Both build notebooks run green in isolation — MVP delivered (index + adapter reusable).

---

## Phase 4: User Story 2 — Reuse existing artifacts to launch the demo (P2)

**Goal**: The serve notebook rebuilds the four-panel demo from Drive artifacts alone.

**Independent Test**: With `chroma_index/` + `lora_adapter/` present, `03_compare_serve.ipynb` serves
a 4-panel Gradio link with no retrain/reindex; missing or drifted artifacts fail fast (quickstart
Scenarios C, E, F; SC-002, SC-007).

- [X] T013 [US2] Create `03_compare_serve.ipynb` — cell-1 bootstrap with the full-stack corrected pins
      `[unsloth, unsloth_zoo, transformers>=5.2, peft>=0.14, bitsandbytes>=0.45, sentence-transformers>=5.2,
      chromadb>=1.0, gradio>=5, pillow>=10.4,<12]` + a vLLM-exclusion guard (uninstall if pulled);
      `config.select_profile(vram)`; `config.verify_meta(lora_adapter, {base_model_id: config.MODEL_ID})`
      and `config.verify_meta(chroma_index, {embed_model: config.EMBED_MODEL})` before load; port Stage 6
      (reload base + attach adapter + reconnect Chroma/embedder) + Stage 7 (4-panel Gradio: Standard /
      Standard+Docs / Specialized (No RAG) / Specialized (RAG), plus per-panel timings); every
      generation param and prompt read from `config` (§IV / FR-005); add `## Deviations` note.
- [ ] T014 [US2] Validate per quickstart Scenarios C (reuse, no rebuild), E (missing `lora_adapter/`
      halts with "run 02_finetune first"), F (base-model drift halts via `verify_meta`); confirm
      `vllm` absent and all four panels share identical generation params.

**Checkpoint**: Demo launches from artifacts only; fail-fast paths verified.

---

## Phase 5: User Story 3 — Reproduce the full experiment in order (P3)

**Goal**: Running the phases in sequence reproduces the monolith with no regression.

**Independent Test**: From empty artifacts, run 01 → 02 → 03; the 4-panel output matches
`notebook.ipynb` on the demo question set (quickstart Scenario D; FR-008, SC-004).

- [ ] T015 [US3] Run `01_build_index.ipynb` → `02_finetune.ipynb` → `03_compare_serve.ipynb` in order
      on a fresh Drive (per quickstart Scenario D); capture the four-panel output for the
      `data/demo_questions.md` set.
- [ ] T016 [US3] Qualitative parity check on `data/demo_questions.md`: establish the baseline by
      running the retained `notebook.ipynb` on a config it can execute (the T4-fallback model if the
      primary pins don't resolve; else use the first validated split run as reference), then confirm
      the split preserves the cross-panel quality ordering (Specialized (RAG) ≥ Standard+Docs ≥
      Standard, and Specialized (RAG) ≥ Specialized (No RAG) ≥ Standard) and factual grounding
      (FR-008/SC-004). Token-identical output is not expected; record and resolve any *qualitative*
      regression before proceeding.

**Checkpoint**: End-to-end reproduction confirmed equivalent to the monolith.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Optional export, doc sync, monolith retirement, and regression coverage.

- [X] T017 [P] Create optional `04_export_gguf.ipynb` — cell-1 bootstrap with
      `PINNED_REQS = [unsloth, unsloth_zoo, transformers>=5.2, peft>=0.14]` (+ llama.cpp tooling);
      `config.verify_meta(lora_adapter, {base_model_id: config.MODEL_ID})`; port the GGUF cell
      (`save_pretrained_merged(..., save_method="merged_4bit")` → `gguf_export/`); add `## Deviations`
      note (feature 004 / constitution v1.2.0); Scenario I.
- [X] T018 [P] Update `README.md` and `docs/how_it_works.md` to describe the four-notebook + `config.py`
      layout and the per-phase run order (the deferred constitution-v1.2.0 doc sync).
- [ ] T019 Remove `notebook.ipynb` after T016 parity passes (research.md Decision 8); confirm no doc
      references the monolith as the sole entry point.
- [ ] T020 [P] Validate regressions per quickstart Scenario H + "Regression checks": Feature 002
      skip/rebuild prompts per notebook; Feature 003 warm/cold/offline + Drive-absent fallback per
      manifest slot (Scenario H, no cross-phase collision); and the T4 fallback profile on a T4
      runtime (§III).
- [ ] T021 [P] Validate single source of truth per quickstart Scenario G (FR-011/SC-005): changing one
      shared constant in `config.py` (e.g. `TEMPERATURE`) is reflected across all notebooks on next
      run, and `grep` confirms no shared constant is re-declared and no cross-notebook import other
      than `config` exists in any `*.ipynb` (also covers FR-012).

---

## Dependencies & Execution Order

- **Setup (T001–T003)** → **Foundational (T004–T009, sequential, same file)** blocks everything.
- **US1 (T010–T012)** depends only on `config.py`. **T010 ∥ T011** (different notebooks); T012 needs both.
- **US2 (T013–T014)** depends on `config.py`; its *test* (T014) needs US1 artifacts (index + adapter).
- **US3 (T015–T016)** depends on US1 + US2 notebooks existing.
- **Polish**: T017 depends on `config.py` + a built `lora_adapter/`; T018/T020 [P]; **T019 depends on
  T016** (never remove the monolith before parity passes).

## Parallel Opportunities

- Setup: **T002 ∥ T003** (after T001 creates the file).
- US1: **T010 ∥ T011** — the two build notebooks are independent files, the biggest parallel win.
- Polish: **T017 ∥ T018 ∥ T020 ∥ T021** (distinct files; T019 gated on T016).

## Implementation Strategy

- **MVP = Phase 1 + 2 + US1** (T001–T012): `config.py` plus the two build notebooks proves the whole
  premise — modularity/reuse and dependency-conflict isolation — before any serving work.
- **Increment 2 = US2** (T013–T014): the reusable four-panel demo.
- **Increment 3 = US3** (T015–T016): end-to-end parity, unlocking monolith removal.
- **Finish = Polish** (T017–T021): optional export, doc sync, retire `notebook.ipynb`, regression sweep.
- Retire the monolith (T019) **only** after parity (T016); keep it as the reference until then.
