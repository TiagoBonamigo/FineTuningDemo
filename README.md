# Domain-Specialized AI Assistant — Proof of Concept

A single Google Colab notebook that takes one small, **free open-weight** language model and shows —
live, side by side in a browser — whether adapting it to your domain actually improves its answers.
The same question is answered by three variants of the same base model at once, so anyone (no ML
background needed) can judge the difference with their own eyes.

> **Status**: POC · **Cost**: $0 beyond an existing Google Colab Pro+ subscription · **Runs as four
> phase notebooks** sharing one `config.py`, persisting to Google Drive.

![Comparison architecture — inputs build a retrieval index and a fine-tuned adapter; one base model powers three panels shown side by side in a Gradio UI.](docs/architecture.svg)

---

## What it does

General models answer domain questions poorly: they don't know your internal facts and don't speak
your terminology. This POC pulls **two independent levers** on top of one base model and compares the
results:

| Panel | Base model | Fine-tune (LoRA) | RAG (retrieval) | Shows |
|---|:---:|:---:|:---:|---|
| **Standard Model** | ✓ | ✗ | ✗ | the raw baseline |
| **Standard + Docs** | ✓ | ✗ | ✓ | what document retrieval adds |
| **Specialized Model** | ✓ | ✓ | ✓ | the full combination |

Reading the panels left-to-right makes the improvement **attributable**: Standard → Standard+Docs is
RAG's contribution; Standard+Docs → Specialized is the fine-tuned adapter's added value.

---

## Quick start (Google Colab)

The pipeline is four **phase notebooks** that hand off through Google Drive and share one `config.py`.
Set `REPO_URL` in each notebook's first (bootstrap) cell to this repo, then run them **in order** on an
**A100** runtime (they auto-fall back to a smaller model on L4/T4). Authorize the Drive mount when
prompted; each notebook installs only its own phase's dependencies.

1. **`01_build_index.ipynb`** — upload your domain documents → `/content/domain_docs/`, **Run all** →
   builds `chroma_index/` on Drive.
2. **`02_finetune.ipynb`** — upload your `training_dataset.jsonl` → `/content/`, **Run all** → trains
   `lora_adapter/` on Drive.
3. **`03_compare_serve.ipynb`** — **Run all** → reloads both artifacts and prints a **public Gradio
   share link**; type a domain question and compare the three panels.
4. *(optional)* **`04_export_gguf.ipynb`** — **Run all** → exports a merged GGUF for local inference.

Full walkthrough with validation checkpoints:
[`specs/004-notebook-split/quickstart.md`](specs/004-notebook-split/quickstart.md) (the original
single-notebook guide is [`specs/001-domain-ai-poc/quickstart.md`](specs/001-domain-ai-poc/quickstart.md)).

**Total run time**: ~25–75 min on A100 (dominated by fine-tuning). No streaming — panels fill in at
once when generation completes.

---

## Inputs you provide

The notebook is the easy part; these two human-authored inputs are the real bottleneck and determine
how impressive the demo is.

| Input | Where it goes | Rule |
|---|---|---|
| **Domain documents** (`.txt` / `.md` / `.pdf`) | `/content/domain_docs/` | non-confidential (shared via a public link) |
| **Training dataset** (`training_dataset.jsonl`) | `/content/training_dataset.jsonl` | ≥ 200 `user`→`assistant` pairs; target 500–1,000 |

See [`data/training_format_example.jsonl`](data/training_format_example.jsonl) for the exact JSONL
format and [`data/demo_questions.md`](data/demo_questions.md) for the demo question template.

---

## How it works (in brief)

The pipeline is four phase notebooks (sharing one `config.py`), each a shippable checkpoint, run in order:

`01 Build Index` → `02 Fine-Tune` → `03 Compare & Serve` → *(optional)* `04 GGUF Export`

Each notebook re-loads what it needs from Drive artifacts (`chroma_index/`, `lora_adapter/`) — nothing
is passed in memory between them, so any phase can be re-run on its own.

- **Fine-tuning** trains a small **LoRA adapter** (QLoRA on a 4-bit base) that teaches the domain's
  tone and terminology — a ~100 MB file, not a retrained model.
- **RAG** chunks and embeds your documents into an in-process **ChromaDB** index, then retrieves the
  top-3 relevant chunks and prepends them to each question.
- **Fair comparison** is enforced: every panel uses the same base model, quantization, system prompt,
  and generation settings — the *only* differences are the adapter and the retrieved context.

Full narrative: [`docs/how_it_works.md`](docs/how_it_works.md).

---

## Configuration defaults

| Base model | Quantization | LoRA | Chunking | Retrieval | Generation |
|---|---|---|---|---|---|
| Qwen3.5-9B (A100) / Qwen3-4B (T4 fallback) | 4-bit NF4 | r=32, α=32, targets q/k/v/o | 2000 chars / 200 overlap | top-3, cosine | temp 0.1, top-p 0.9, 512 tokens, thinking off |

All values live in the shared **`config.py`** (the single source of truth) and are documented in
[`specs/001-domain-ai-poc/data-model.md`](specs/001-domain-ai-poc/data-model.md). Each model-loading
notebook **auto-detects the GPU** via `config.select_profile()` and switches to the T4 fallback config
when VRAM < 24 GB.

---

## Repository layout

```text
config.py                      # single shared module: all constants + setup helpers (the only cross-notebook import)
01_build_index.ipynb           # phase 1 — build the RAG index → chroma_index/
02_finetune.ipynb              # phase 2 — QLoRA fine-tune → lora_adapter/
03_compare_serve.ipynb         # phase 3 — reload artifacts + serve the three-panel Gradio demo
04_export_gguf.ipynb           # phase 4 (optional) — merge + export → gguf_export/
notebook.ipynb                 # original single-notebook pipeline (retained until the split is parity-validated)
README.md                      # this file

data/
├── demo_questions.md          # curated 5–10 question demo set (template)
└── training_format_example.jsonl  # JSONL training-data format reference

docs/
├── quick_reference.md         # one-page cheat sheet (front of the presentation)
├── how_it_works.md            # how this project works, stage by stage
├── approach_comparison.md     # pros/cons of tuning × RAG + deterministic-calculation tie-in
├── architecture.svg           # the diagram at the top of this README
└── findings_template.md       # one-page post-demo findings summary

specs/                         # speckit specifications, plans, and contracts
└── 001-domain-ai-poc/         #   spec.md · plan.md · research.md · data-model.md · quickstart.md
.specify/memory/constitution.md  # the project's non-negotiable principles and constraints
```

---

## Reproducibility & resilience

- **Per-notebook pinned dependencies** plus a **Drive-cached wheelhouse** (keyed per phase) →
  identical, fast, conflict-free installs across runs.
- **Fixed random seed** (`42`) across Python, NumPy, and PyTorch.
- **All artifacts persist to Drive** (`MyDrive/domain-llm-poc/`) — a Colab disconnect never loses the
  adapter or index.
- **Skip / rebuild prompts** on the expensive stages (index, adapter) let a re-run reuse existing work
  by default; set `UNATTENDED_DEFAULT` to answer automatically for hands-off runs.

---

## Constraints (by design)

This project is governed by a ratified [constitution](.specify/memory/constitution.md). In short:

- **Open-weight models and free OSS only** — no paid APIs, no licensing fees.
- **Simplicity first** — a bounded set of four phase notebooks sharing one `config.py`, in-process
  ChromaDB (no server), Gradio only, no orchestration frameworks; readable end-to-end in under an hour.
- **Reproducible on a fresh Colab session** with only the two uploaded inputs, degrading gracefully to
  a T4 GPU.
- **$0** beyond the existing Colab Pro+ subscription.

---

## Documentation map

| I want to… | Read |
|---|---|
| Grasp the whole thing in one screen | [`docs/quick_reference.md`](docs/quick_reference.md) |
| Understand how the notebook works | [`docs/how_it_works.md`](docs/how_it_works.md) |
| Weigh fine-tuning vs. RAG (and add exact calculations) | [`docs/approach_comparison.md`](docs/approach_comparison.md) |
| Reproduce or validate the POC step by step | [`specs/001-domain-ai-poc/quickstart.md`](specs/001-domain-ai-poc/quickstart.md) |
| Run the live demo | [`data/demo_questions.md`](data/demo_questions.md) |
| Record results after the demo | [`docs/findings_template.md`](docs/findings_template.md) |
| Know the rules the project must follow | [`.specify/memory/constitution.md`](.specify/memory/constitution.md) |
