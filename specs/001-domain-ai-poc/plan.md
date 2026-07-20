# Implementation Plan: Domain-Specialized AI Assistant — POC

**Branch**: `001-domain-ai-poc` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-domain-ai-poc/spec.md`

## Summary

Build a single Colab notebook that fine-tunes a small open-weight LLM (Llama 3.2 3B Instruct)
with QLoRA on manually authored domain JSONL training data, builds a ChromaDB vector retrieval
index from domain documents, and serves a Gradio UI with two side-by-side panels (standard model
vs. specialized model) for live stakeholder demos. The notebook runs top-to-bottom on a fresh
Colab session; all artifacts persist to Google Drive.

## Technical Context

**Language/Version**: Python 3.10+ (Google Colab default)

**Primary Dependencies**:
- `unsloth` — QLoRA fine-tuning, Colab-optimized (Qwen3.5 support confirmed)
- `bitsandbytes` — 4-bit NF4 quantization
- `peft` — LoRA adapter management
- `transformers` + `datasets` — model loading and dataset utilities
- `sentence-transformers` — embedding model for RAG (`all-MiniLM-L6-v2`)
- `chromadb` — in-process vector store (no server required)
- `gradio` — demo UI with public share link
- `google.colab.drive` — Drive mount for artifact persistence

**Storage**: Google Drive (`MyDrive/domain-llm-poc/`) for adapter, index, and dataset;
in-process ChromaDB for the vector index during the session.

**Testing**: Manual cell-by-cell verification in notebook; inference smoke test cell; Gradio UI
manual walkthrough.

**Target Platform**: Google Colab Pro+ — **A100 40 GB (assumed primary)**; T4 16 GB fallback
config available via `MODEL_ID` swap + reduced hyperparameters.

**Project Type**: Jupyter Notebook — single self-contained file

**Performance Goals**: Inference response aspirational target ~30 s on A100 (batch output, no
streaming); training completes in ~20–40 minutes on A100 with Qwen3.5-9B.

**Constraints**: A100 40 GB primary; 4-bit NF4 for both training and inference; $0 total cost;
batch output only; per-panel loading indicator; plain-language error message on failure; no
paid APIs; `enable_thinking=False` on all Qwen3.5 generation calls.

**Scale/Scope**: Single-session, single-user POC; 200–1,000 training pairs (manually authored);
5–10 demo questions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle / Constraint | Gate criterion | Status |
|---|---|---|
| §I Simplicity First | Single notebook; in-process ChromaDB; Gradio only; no orchestration frameworks | ✅ Pass |
| §II Cost Mandate | Qwen3.5-9B (Apache 2.0, HuggingFace); all free OSS libraries; zero paid APIs | ✅ Pass |
| §III Reproducibility | Pinned deps in cell 1; fixed random seed (`42`); Drive persistence; T4 fallback config available | ✅ Pass |
| §IV Fair Comparison | Same base model, 4-bit NF4, identical gen params + `enable_thinking=False`; simultaneous Gradio inference | ✅ Pass |
| Compute | Colab Pro+ A100 40 GB (primary); T4 fallback via `MODEL_ID` swap | ✅ Pass |
| Model | Qwen3.5-9B — ≤10B A100 cap (§2.2 v1.1.0), open-weight, HuggingFace, Apache 2.0 | ✅ Pass |
| Fine-tuning stack | Unsloth + QLoRA; LoRA adapters only; training <90 min target | ✅ Pass |
| RAG stack | ChromaDB in-process; `all-MiniLM-L6-v2`; plain Python retrieval ~50 lines | ✅ Pass |
| Interface | Gradio with batch output; per-panel "Generating…" indicator; error message on failure | ✅ Pass |
| Prohibited list | No paid APIs, Docker, K8s, hosted DB, or React/Vue | ✅ Pass |

**All gates pass. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/001-domain-ai-poc/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── gradio-ui.md
│   ├── training-dataset.md
│   └── drive-artifacts.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
notebook.ipynb                    # Main Colab notebook — single file, all pipeline stages

data/
├── demo_questions.md             # Curated 5–10 question demo set with expected-answer notes
└── training_format_example.jsonl # JSONL format reference / blank template (not domain data)

docs/
└── findings_template.md          # One-page post-demo findings summary template
```

**Structure Decision**: Single-notebook approach per §I (Simplicity First). All pipeline stages
— dependency install, model load, RAG index build, fine-tuning, Gradio UI — run sequentially in
one `.ipynb` file. Domain documents and actual training data are uploaded by the domain expert
and are not committed to the repository.

## Complexity Tracking

> No Constitution Check violations — no justification table needed.

---

## Post-Phase 1 Constitution Re-check

After Phase 1 design:

| Area | Design decision | Compliance |
|---|---|---|
| Notebook architecture | Single `.ipynb`; no helper modules required | §I ✅ |
| Gradio loading state | Native Gradio spinner (automatic when handler is running) | §I ✅ |
| Error handling | `try/except` in inference handler; error string returned to panel | §I ✅ |
| ChromaDB persistence | `chromadb.PersistentClient(path=drive_path)` — Drive-backed | §III ✅ |
| Generation params | Shared `gen_config` dict with `enable_thinking=False` passed to both model calls | §IV ✅ |
| LoRA rank/alpha | `r=32, lora_alpha=32` on A100; reducible to `r=8` for T4 fallback | §2.3 ✅ |
| Model | Qwen3.5-9B approved under §2.2 v1.1.0 (10B cap); T4 fallback = Qwen3-4B-Instruct-2507 | §2.2 ✅ |

All design decisions comply. No deviations required.
