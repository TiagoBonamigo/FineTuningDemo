# Phase 1 Data Model: Notebook Split (Phase Notebooks)

Entities are the structural units of the split and the artifacts/records that cross phase boundaries.
No relational database — "entities" here are files, modules, and Drive artifacts.

## Entity: Shared config module (`config.py`)

The single version-controlled Python module; the only permitted cross-notebook import (FR-003/FR-011).

- **Constants** (from the current Stage 0 Constants cell): `MODEL_ID`, `SEED`, `MAX_SEQ_LEN`;
  LoRA (`LORA_R`, `LORA_ALPHA`, `LORA_DROPOUT`, `LORA_TARGETS`); training (`TRAIN_EPOCHS`,
  `TRAIN_BATCH`, `GRAD_ACCUM`, `LEARNING_RATE`); RAG (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`,
  `EMBED_MODEL`); generation (`MAX_NEW_TOKENS`, `TEMPERATURE`, `TOP_P`, `REPETITION_PENALTY`,
  `ENABLE_THINKING=False`); prompts (`SYSTEM_PROMPT`, `RETRIEVAL_TEMPLATE`); paths (`DRIVE_BASE`,
  `DOCS_PATH`, `DATASET_PATH`, and derived artifact paths).
- **T4-fallback values**: the smaller-config counterparts (`MODEL_ID`, `MAX_SEQ_LEN`, LoRA, batch,
  epochs) selected below 24 GB VRAM.
- **Functions** (behavioral, see contracts/config-module.md): `select_profile(vram_gb)`,
  `set_seeds()`, `mount_drive()`, `artifact_gate(...)`, `install_deps(reqs)`, `write_meta(path, d)`,
  `verify_meta(path, expected)`.
- **Rules**: stdlib-only at import (safe to import before pip install); no shared constant may be
  re-declared in a notebook (FR-011); it is the single source of truth for §IV parameters.

## Entity: Phase notebook

A self-contained Colab notebook for one pipeline phase (FR-001/FR-006).

- **Attributes**: `name` (`01_build_index` … `04_export_gguf`); `PINNED_REQS` (phase-specific list,
  cell 1); `consumes` (Drive inputs); `produces` (Drive outputs); `needs_gpu_profile` (bool).
- **Cell-1 bootstrap (uniform)**: fetch repo → `import config` → `config.mount_drive()` → define
  `PINNED_REQS` → `config.install_deps(PINNED_REQS)` → `config.set_seeds()`.
- **Rules**: communicates only via Drive artifacts (FR-002); imports only `config` across notebooks
  (FR-012); carries a `## Deviations` note (§Governance).

| Notebook | consumes | produces | needs_gpu_profile |
|---|---|---|---|
| 01_build_index | `domain_docs/` | `chroma_index/` (+ `meta.json`) | no |
| 02_finetune | `training_dataset.jsonl` | `lora_adapter/` (+ `meta.json`) | yes |
| 03_compare_serve | `chroma_index/`, `lora_adapter/` | Gradio link | yes |
| 04_export_gguf | `lora_adapter/` | `gguf_export/` | yes |

## Entity: Drive artifact

A persisted handoff object between phases (unchanged locations under `DRIVE_BASE`).

- `chroma_index/` — persistent ChromaDB collection `domain_docs` (produced by 01, consumed by 03).
- `lora_adapter/` — LoRA adapter weights + tokenizer (produced by 02, consumed by 03 and 04).
- `training_dataset.jsonl` — validated training pairs (input to 02; backed up to Drive).
- `gguf_export/` — merged GGUF (produced by 04).
- `deps_cache/{fingerprint}/{manifest8}/wheels/` — per-phase wheelhouse slot (Feature 003, re-keyed).

## Entity: Artifact metadata sidecar (`meta.json`)

A small JSON written inside a built artifact directory, used for drift detection (FR-013/SC-007).

- **`lora_adapter/meta.json`**: `base_model_id`, `max_seq_len`, `lora_r`, `lora_alpha`,
  `lora_targets`, `seed`.
- **`chroma_index/meta.json`**: `embed_model`, `chunk_size`, `chunk_overlap`.
- **Rules**: written by the producing notebook immediately after the artifact; verified by every
  consumer via `config.verify_meta`; mismatch or absence → fail fast with the offending field + the
  phase to re-run.

## Entity: Dependency manifest (per notebook)

The phase's `PINNED_REQS` list plus its derived `manifest8` cache key.

- **Attributes**: `reqs` (list), `manifest_sha256` (hash of the list), `manifest8` (first 8 chars).
- **Rules**: distinct per notebook (FR-004); drives the wheelhouse slot (Decision 6); a change
  auto-invalidates that phase's slot only (Feature 003 semantics, scoped per phase).

## State Transitions: consuming a phase (drift + skip/rebuild)

```text
Notebook start
  → import config, mount Drive, install_deps(PINNED_REQS)        # Feature 003 (per-manifest slot)
  → For each required input artifact:
        exists?  ── no ──▶ RAISE "run <producing phase> first"   # FR-007
           │ yes
        verify_meta(artifact, expected_from_config)
           ├─ mismatch ──▶ RAISE "<field> drift; re-run <phase>" # FR-013 / SC-007
           └─ ok
  → For each producible artifact (build notebooks):
        artifact_gate(...) ── skip ──▶ reuse Drive artifact       # Feature 002
                            └ rebuild ▶ build, then write_meta()  # FR-013
  → Serve notebook: load base+adapter+RAG, launch 3-panel Gradio  # §IV, all params from config
```
