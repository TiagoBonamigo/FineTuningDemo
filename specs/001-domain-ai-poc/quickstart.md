# Quickstart Validation Guide: Domain-Specialized AI Assistant — POC

**Feature**: `specs/001-domain-ai-poc`
**Date**: 2026-07-20
**Audience**: Anyone reproducing or validating the POC from scratch

---

## Prerequisites

| Requirement | Details |
|---|---|
| Google account | Required to use Colab and Google Drive |
| Google Colab Pro+ | Existing subscription; select A100 runtime (High-RAM) when available |
| Domain documents | Non-confidential source files (`.txt`, `.md`, or `.pdf`) |
| Training dataset | Manually authored `training_dataset.jsonl` (see [training-dataset.md](contracts/training-dataset.md)) |
| Demo question set | `data/demo_questions.md` from this repository |
| Repository access | `notebook.ipynb` downloaded locally or opened via "Open in Colab" link |

---

## Setup Steps

### Step 1 — Open the notebook in Colab

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. File → Open notebook → Upload → select `notebook.ipynb`
3. Runtime → Change runtime type → Select **A100** GPU (or L4/T4 if unavailable) + High-RAM
4. Runtime → Connect

### Step 2 — Upload inputs

In the Colab left sidebar (Files):

1. Upload your domain documents folder as `domain_docs/` (drag-and-drop into `/content/`)
2. Upload `training_dataset.jsonl` to `/content/training_dataset.jsonl`

Verify upload:
```python
# Run this quick check (not in notebook — just mentally verify):
# /content/domain_docs/ contains at least one .txt / .md / .pdf file
# /content/training_dataset.jsonl exists and has >= 200 lines
```

### Step 3 — Mount Google Drive

Run Stage 1 cells. A browser popup asks for Drive permission. Authorize it.

Verify: `/content/drive/MyDrive/domain-llm-poc/` directory created.

### Step 4 — Run all cells top to bottom

Runtime → Run all (or Ctrl+F9)

Expected stage durations on A100:

| Stage | Description | Expected duration |
|---|---|---|
| 0 | Install & Config | 3–5 min |
| 1 | Drive Mount | < 1 min |
| 2 | Base Model Load | 2–4 min |
| 3 | Walking Skeleton UI | < 1 min |
| 4 | RAG Pipeline | 1–3 min (varies with doc count) |
| 5 | Fine-Tuning | 15–60 min (varies with dataset size) |
| 6 | Full Pipeline Load | 1–2 min |
| 7 | Demo UI Launch | < 1 min |

**Total**: ~25–75 min on A100. Under 90 min per constitution §2.3.

On T4: expect 45–90 min for Stage 5 with reduced config (`LORA_R=8`, `TRAIN_EPOCHS=2`).

---

## Validation Checkpoints

### Checkpoint 1 — After Stage 2 (Base Model Load)

Expected output from smoke test cell:
```
Model loaded: meta-llama/Llama-3.2-3B-Instruct-bnb-4bit
Smoke test response: [any coherent sentence]
✅ Base model loaded successfully
```

If you see an OOM error: switch to `LORA_R=8` and `MAX_SEQ_LEN=512`, or use T4 fallback config.

### Checkpoint 2 — After Stage 3 (Walking Skeleton UI)

- A temporary Gradio public URL appears in cell output (e.g., `https://xxxx.gradio.live`)
- Open it in a browser
- Type any question; click Submit
- **Both panels** should populate with answers (the same base model on both at this stage)
- ✅ Walking skeleton demo works

### Checkpoint 3 — After Stage 4 (RAG Pipeline)

Expected output:
```
Loaded N documents from domain_docs/
Created M chunks
Index built: collection 'domain_docs' with M documents
✅ Vector index saved to Drive: /content/drive/MyDrive/domain-llm-poc/chroma_index/
```

Manual test (run in a cell):
```python
print(retrieve("What is [domain-specific term]?"))
```
Should return non-empty context text from your documents.

### Checkpoint 4 — After Stage 5 (Fine-Tuning)

Expected output:
```
Training complete. Steps: N, Loss: X.XX
✅ Adapter saved to Drive: /content/drive/MyDrive/domain-llm-poc/lora_adapter/
```

Verify in Drive: `domain-llm-poc/lora_adapter/adapter_model.safetensors` exists (~80–120 MB).

### Checkpoint 5 — After Stage 7 (Full Demo UI)

- A new Gradio public URL appears
- Open it; type a domain-specific question from `data/demo_questions.md`
- **Left panel** (Standard Model): answers from base knowledge only
- **Right panel** (Specialized Model): answers using fine-tuned adapter + retrieved context
- Observe the quality contrast
- ✅ POC complete

---

## Demo Validation (Using the Curated Question Set)

See `data/demo_questions.md` for the full question set.

Run each question and compare panels against expected-answer notes in that file:

1. At least 4 of 5 domain-specific questions: right panel notably better → **SC-001 ✅**
2. 1–2 general sanity-check questions: both panels reasonable → **SC-006 ✅**
3. Any team member can repeat this without domain expertise → **SC-002 ✅**

---

## Resumability: Restarting After a Disconnect

See [drive-artifacts.md](contracts/drive-artifacts.md) §Resumability contract for the exact
skip-and-load pattern. Summary: set `FORCE_RETRAIN=False` in Stage 0 and re-run all cells —
existing Drive artifacts will be loaded instead of regenerated.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| OOM during training | GPU VRAM too small | Set `LORA_R=8`, `TRAIN_BATCH=1`, `GRAD_ACCUM=8` |
| `chromadb` import error | Version conflict with `protobuf` | Pin `chromadb>=0.5,<1.0` in Stage 0 |
| Gradio URL not generated | `share=True` blocked | Ensure outbound internet access from Colab runtime |
| Training dataset validation fails | JSONL format error | See [training-dataset.md](contracts/training-dataset.md) §Validation checks |
| Both panels give similar answers | Domain too generic, or too few training pairs | Add more varied training pairs; verify domain docs are sufficiently specialized |
| Panel shows "Generation failed" | Inference error (usually OOM after long training) | Restart runtime; reload artifacts from Drive (see Resumability) |
