# Contract: Per-notebook inputs / outputs, pins, and sidecars

Defines each phase notebook's observable contract: what it consumes, produces, pins, and stamps. The
uniform cell-1 bootstrap (fetch repo → `import config` → `mount_drive` → define `PINNED_REQS` →
`install_deps` → `set_seeds`) is required in all four (data-model.md).

## `01_build_index.ipynb`

- **Consumes**: `DOCS_PATH` documents (`domain_docs/`).
- **Produces**: `chroma_index/` (Chroma collection `domain_docs`) + `chroma_index/meta.json`.
- **PINNED_REQS**: `sentence-transformers>=5.2`, `chromadb>=1.0`, `langchain-text-splitters>=0.3`,
  `pypdf>=4.0`. (No torch-heavy training stack, no gradio.)
- **Gate**: `artifact_gate("RAG index", chroma_index, "chroma.sqlite3")` — skip reuses the index.
- **Sidecar written**: `{embed_model, chunk_size, chunk_overlap}`.
- **Fail-fast**: none required upstream (first phase); empty `domain_docs/` → clear error.

## `02_finetune.ipynb`

- **Consumes**: `DATASET_PATH` (`training_dataset.jsonl`).
- **Produces**: `lora_adapter/` (adapter + tokenizer) + `lora_adapter/meta.json`.
- **PINNED_REQS**: `unsloth`, `unsloth_zoo`, `transformers>=5.2`, `trl>=0.15`, `peft>=0.14`,
  `bitsandbytes>=0.45`, `datasets>=3.0`. (No chromadb/sentence-transformers/gradio. vLLM excluded.)
- **Profile**: `config.select_profile(vram)` before base-model load (§III T4 swap).
- **Gate**: `artifact_gate("LoRA adapter", lora_adapter, "adapter_model.safetensors", "Retrain")`.
- **Sidecar written**: `{base_model_id, max_seq_len, lora_r, lora_alpha, lora_targets, seed}`.
- **Fail-fast**: missing/invalid `training_dataset.jsonl` → error (keeps existing JSONL validation).

## `03_compare_serve.ipynb` (the only full-stack notebook)

- **Consumes**: `lora_adapter/` (+ verify `meta.json`), `chroma_index/` (+ verify `meta.json`).
- **Produces**: an ephemeral Gradio share link (three panels).
- **PINNED_REQS**: `unsloth`, `unsloth_zoo`, `transformers>=5.2`, `peft>=0.14`, `bitsandbytes>=0.45`,
  `sentence-transformers>=5.2`, `chromadb>=1.0`, `gradio>=5`, `pillow>=10.4,<12`. **No `trl`/`datasets`
  (inference only); vLLM MUST be absent** (uninstall if pulled — it caps `transformers<5`).
- **Profile**: `config.select_profile(vram)` — MUST resolve to the SAME base as the adapter's sidecar.
- **Verify (fail-fast, FR-007/FR-013)**: adapter `meta.base_model_id == config.MODEL_ID` (active
  profile) and `chroma meta.embed_model == config.EMBED_MODEL`; missing artifact → "run phase N first".
- **§IV invariant**: `infer_base`, `infer_rag_only`, `infer_specialized` share base model,
  quantization, `SYSTEM_PROMPT`, and all generation params — every value read from `config`.

## `04_export_gguf.ipynb` (optional)

- **Consumes**: `lora_adapter/` (+ verify `meta.json`).
- **Produces**: `gguf_export/` (`save_pretrained_merged(..., save_method="merged_4bit")`).
- **PINNED_REQS**: `unsloth`, `unsloth_zoo`, `transformers>=5.2`, `peft>=0.14` + llama.cpp tooling.
- **Verify**: adapter sidecar matches active `config.MODEL_ID`.

## Cross-cutting invariants

- Every artifact write is followed by `config.write_meta(...)` (sidecar is written last).
- Every artifact read is preceded by `config.verify_meta(...)`.
- No notebook installs another phase's stack; `install_deps` receives only that phase's `PINNED_REQS`.
- Only `config` is imported across notebooks; no other local import or helper script (FR-012).
