# Contract: Google Drive Artifact Layout

**Feature**: `specs/001-domain-ai-poc`
**Interface type**: Persistent storage (Google Drive)
**Date**: 2026-07-20

---

## Summary

All artifacts produced by the notebook are saved to a single Google Drive folder. This allows
the Colab session to disconnect without losing work and allows a future session to load artifacts
directly rather than re-running the full pipeline.

---

## Root path

```
/content/drive/MyDrive/domain-llm-poc/
```

Configured via `DRIVE_BASE` constant in Stage 0. The notebook creates this directory if it
does not exist.

---

## Directory layout

```text
domain-llm-poc/
│
├── lora_adapter/                        # LoRA adapter weights
│   ├── adapter_config.json              # PEFT adapter configuration
│   └── adapter_model.safetensors        # Adapter weights (~100 MB typical)
│
├── chroma_index/                        # ChromaDB persistent index
│   └── <chromadb internal structure>    # Managed by chromadb.PersistentClient
│
├── training_dataset.jsonl               # Copy of the uploaded training file
│
└── notebook.ipynb                       # Snapshot of the notebook at Stage 7 completion
```

---

## Artifact specifications

### `lora_adapter/`

| Property | Value |
|---|---|
| Written by | Stage 5 (fine-tuning), `model.save_pretrained(DRIVE_BASE/lora_adapter)` |
| Size | ~100 MB (r=16, q_proj+v_proj on a 3B model) |
| Loaded by | Stage 6 (full pipeline load), `PeftModel.from_pretrained(base_model, DRIVE_BASE/lora_adapter)` |
| Overwritten on re-run | Yes — last training run wins |
| PEFT compatible | Yes — standard PEFT `adapter_config.json` + safetensors format |

### `chroma_index/`

| Property | Value |
|---|---|
| Written by | Stage 4 (RAG build), ChromaDB `PersistentClient(path=DRIVE_BASE/chroma_index)` |
| Loaded by | Stage 6 — same `PersistentClient` call reconnects to the persisted collection |
| Overwritten on re-run | Yes — Stage 4 drops and recreates the `"domain_docs"` collection |
| Manual inspection | Files are ChromaDB-internal; do not edit directly |

### `training_dataset.jsonl`

| Property | Value |
|---|---|
| Written by | Stage 5 (copied from `DATASET_PATH` before training starts) |
| Purpose | Reproducibility — ensures the exact dataset used is preserved alongside the adapter |
| Overwritten on re-run | Yes |

### `notebook.ipynb`

| Property | Value |
|---|---|
| Written by | Stage 7 (optional cell: `shutil.copy("/content/notebook.ipynb", DRIVE_BASE)`) |
| Purpose | Snapshot for reproducibility; avoids relying on a separately stored notebook version |
| Overwritten on re-run | Yes |

---

## Resumability contract

A notebook session that disconnected mid-run can be resumed as follows:

| Scenario | Resume action |
|---|---|
| Disconnected before Stage 4 | Re-run from Stage 0 (no Drive artifacts to restore) |
| Disconnected after Stage 4 (index built) | Skip Stage 4 (index already on Drive); continue from Stage 5 |
| Disconnected after Stage 5 (adapter saved) | Skip Stages 4–5; load adapter from Drive in Stage 6 |
| Disconnected after Stage 7 (full demo built) | Stage 6 fast-loads adapter + index from Drive; re-launch Gradio |

Each stage cell MUST include a guard check: if the artifact already exists on Drive, skip
re-generation and load instead (configurable via `FORCE_RETRAIN=False` flag in Stage 0).

---

## Download contract

Any individual artifact can be downloaded from Colab's file browser or via:

```python
from google.colab import files
files.download(f"{DRIVE_BASE}/lora_adapter/adapter_model.safetensors")
```

The LoRA adapter is independently portable: it can be loaded by any PEFT-compatible inference
stack on any machine with the same base model.
