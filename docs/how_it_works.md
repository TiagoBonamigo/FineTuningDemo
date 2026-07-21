# How This Project Works

> **What this document is**: A plain-language walkthrough of *how* the Domain LLM Comparison POC
> actually works — the idea, the moving parts, the pipeline stage by stage, and what happens when
> someone asks a question.
>
> **Packaging note (feature `004-notebook-split`, constitution v1.2.0)**: the pipeline is now four
> **phase notebooks** sharing one `config.py`, handing off through Google Drive. The stage narrative
> below is unchanged in logic — it is simply distributed across the notebooks:
> `01_build_index.ipynb` (Stage 4 · RAG index) · `02_finetune.ipynb` (Stages 2 + 5 · base load +
> fine-tune) · `03_compare_serve.ipynb` (Stages 6 + 7 · reload + four-panel demo) ·
> `04_export_gguf.ipynb` (optional export). The original `notebook.ipynb` is retained until the split
> is parity-validated. All constants referenced below now live in `config.py`.
>
> **Companion doc**: [`approach_comparison.md`](approach_comparison.md) argues *why* you'd combine
> fine-tuning and RAG (pros/cons of each approach). This doc explains *how* this project does it.
>
> **Domain**: this POC's documents and training pairs are laytime & voyage-charterparty calculation
> (NOR validity, SHEX/SHINC/WWD, SOF analysis, demurrage/despatch) — see the repo `README.md` for the
> full input list. The mechanics below are domain-agnostic; swap in different `domain_docs/` and
> `training_dataset.jsonl` to repurpose the pipeline for any other domain.
>
> **Date**: 2026-07-21

---

## 1. The idea in one paragraph

A general-purpose open-weight model doesn't know your organization's internal facts and doesn't
speak in your domain's terminology. This project takes one small, free model and produces a **live,
side-by-side comparison** that lets anyone see — in a browser — whether adapting that model to a
domain actually improves its answers. It does this by running the *same question* through four
variants of the same base model at once and showing the answers next to each other. Everything runs
in a small set of Google Colab notebooks (one per pipeline phase, sharing one `config.py`), uses only
free open-source software, and saves its work to Google Drive so it can be reproduced or resumed.

---

## 2. The mental model: one base model, two levers, four panels

There is **one base model** (Qwen). On top of it we can pull **two independent levers**:

| Lever | What it changes | What it adds |
|---|---|---|
| **Fine-tuning** (a LoRA adapter) | the model's *weights* | domain tone, terminology, answer style |
| **RAG** (retrieval) | the model's *prompt* | fresh, grounded facts pulled from your documents at query time |

Combining "adapter on/off" with "retrieval on/off" gives **all four** possible variants — the demo
shows every one of them side-by-side:

![Comparison architecture — inputs build the index and adapter; one base model powers every panel; a Gradio UI runs all of them at once.](architecture.svg)

| Panel | Base model | LoRA adapter | RAG retrieval | What it isolates |
|---|:---:|:---:|:---:|---|
| **Standard Model** | ✓ | ✗ | ✗ | the raw baseline |
| **Standard + Docs** | ✓ | ✗ | ✓ | *RAG's* contribution alone |
| **Specialized (No RAG)** | ✓ | ✓ | ✗ | *fine-tuning's* contribution alone |
| **Specialized (RAG)** | ✓ | ✓ | ✓ | the full combination |

Reading the panels is what makes the improvement **attributable**:

- **Standard → Standard + Docs** shows how much *document retrieval* helped, on its own.
- **Standard → Specialized (No RAG)** shows how much the *fine-tuned adapter* helped, on its own.
- **Specialized (No RAG) → Specialized (RAG)** shows how much *retrieval adds on top of* the
  fine-tuned adapter.
- **Standard → Specialized (RAG)** shows the *combined* effect.

That attribution feeds directly into the post-demo `findings_template.md` and the
invest / iterate / stop recommendation.

> These four panels correspond one-to-one with all four cells (①②③④) of the 2×2 matrix in
> [`approach_comparison.md`](approach_comparison.md). Earlier, only three of the four cells were
> shown by default and "fine-tuned without RAG" had to be added as an extra panel to get a clean
> read on the adapter's standalone contribution — the demo now surfaces that cell (`Specialized (No
> RAG)`) permanently, so all four configurations are directly comparable without any setup change.

---

## 3. The one rule that keeps it honest: fair comparison

The comparison is only meaningful if the **only** things that differ between panels are the two
levers. So every panel shares, identically:

- the **same base model** and the **same 4-bit (NF4) quantization**,
- the **same system prompt** (`SYSTEM_PROMPT`),
- the **same generation settings** — `temperature=0.1`, `top_p=0.9`, `max_new_tokens=512`,
  `repetition_penalty=1.1`, and `enable_thinking=False` (Qwen's chain-of-thought mode is turned off
  so answers stay short and comparable).

The *only* permitted differences are **(a)** whether the LoRA adapter is attached and **(b)** whether
retrieved context is prepended to the question. Everything else is held constant on purpose. (This is
Principle IV of the project constitution — "Fair Comparison".)

---

## 4. The pipeline: what the notebook does, stage by stage

The notebook runs top-to-bottom in **eight sequential stages**. Each stage is a shippable checkpoint —
the demo already "works" (with less magic) partway through. This is deliberate: the build order is
risk-first, so a working demo exists at every step.

```
 Stage 0  Install & Config ─── pinned deps (cached to Drive), constants,
              │                  auto-detect GPU, fix random seed
 Stage 1  Drive Mount ───────── create the artifact folder on Google Drive
              │
 Stage 2  Base Model Load ───── load Qwen in 4-bit + smoke test
              │
 Stage 3  Walking Skeleton ──── minimal Gradio UI, base model only  ◀── first live demo
              │
 Stage 4  RAG Pipeline ──────── docs → chunk → embed → ChromaDB index
              │
 Stage 5  Fine-Tuning ───────── validate JSONL → LoRA → train → save adapter
              │
 Stage 6  Full Pipeline Load ── reload base + attach adapter + reconnect index
              │                  → define the 4 inference functions
 Stage 7  Demo UI ───────────── 4-panel Gradio with public share link  ◀── final demo
              │
 (opt.)   GGUF Export ───────── merge to a local-inference file
```

### Stage 0 — Install & Config
Each phase notebook opens by cloning this repo (to fetch the shared `config.py`) and installing only
**its own minimal, pinned dependency subset** — `01_build_index` needs embeddings/ChromaDB, `02_finetune`
needs the training stack, `03_compare_serve` needs the full stack (base model, adapter, RAG, Gradio),
`04_export_gguf` needs just the export tooling. Splitting the list this way avoids the dependency
conflicts a single shared install would hit (e.g. `vllm` vs. the `transformers` version Qwen3.5 needs).
To avoid re-downloading every time, each notebook **caches its own built wheels to Drive**
(`deps_cache/`, keyed by Python/CUDA runtime *and* by a hash of that phase's dependency list, so the
four notebooks never clobber each other's cache): a later run on the same runtime installs *offline*
from that wheelhouse. It then:
- defines every tunable value as a named constant (model ID, LoRA settings, chunk sizes, generation
  params, paths),
- **auto-detects the GPU**: if it sees < 24 GB of VRAM it silently swaps to the smaller **T4 fallback
  config** (a 4-bit Qwen3-4B, `LORA_R=8`, shorter sequences, smaller batch) so the same notebook runs
  on a weaker machine,
- fixes the random seed (`42`) across Python, NumPy, and PyTorch for reproducibility.

### Stage 1 — Drive Mount
Mounts Google Drive and creates the artifact folder `MyDrive/domain-llm-poc/`. Everything the notebook
produces — the adapter, the index, a copy of your dataset — lands here, so a Colab disconnect never
destroys work.

### Stage 2 — Base Model Load
Loads the base model in 4-bit NF4 via Unsloth's `FastLanguageModel`, then runs a **smoke test**
("what is 2+2?") to prove the model and tokenizer work before anything else is built on top.

### Stage 3 — Walking Skeleton UI
Launches a minimal Gradio interface with a public share link, wiring the **base model** to the panels.
No RAG, no adapter yet — the point is to confirm the UI plumbing and the share link work *before*
adding complexity. This is the first thing you could actually put in front of someone.

### Stage 4 — RAG Pipeline
Turns your uploaded domain documents into a searchable index:
`load files (.txt/.md/.pdf) → split into ~500-token chunks (2000 chars, 200 overlap) → embed each
chunk with all-MiniLM-L6-v2 → store vectors in a ChromaDB collection` that persists to Drive. It also
defines `retrieve(query)`, which embeds a question, finds the **top-3** most similar chunks, and
returns their text. If an index already exists on Drive, the stage offers to **skip and reuse it**
rather than rebuild. Once built, it stamps a `meta.json` sidecar (embed model, chunk size/overlap) next
to the index so a later stage can detect if the config has drifted since the index was built.

### Stage 5 — Fine-Tuning
Turns your hand-authored Q&A file into a domain adapter:
- **validates** the training JSONL (each line must be a `user` → `assistant` message pair; needs
  ≥ 200 pairs),
- attaches trainable **LoRA** layers to the base model (rank 32 on A100, targeting the attention
  projections),
- formats each example with the model's chat template and trains with TRL's `SFTTrainer` for a few
  epochs,
- **saves the adapter (~100 MB) to Drive** and backs up a copy of your dataset, then stamps its own
  `meta.json` sidecar (base model ID, LoRA settings, seed) alongside it.

Like Stage 4, if an adapter already exists it offers to **skip and reuse** instead of retraining —
so a re-run after a disconnect doesn't repeat the expensive step.

### Stage 6 — Full Pipeline Load
Assembles the finished system. It first checks each artifact's `meta.json` sidecar against the current
config and **fails fast with an actionable message** if either is missing or was built under different
settings — so a stale index or adapter never gets loaded silently. It then reloads the base model
**fresh**, attaches the saved LoRA adapter to produce the *specialized* model, reconnects the ChromaDB
index, and defines the **four inference functions** — one per panel:

| Function | Model used | Retrieval? | Powers panel |
|---|---|:---:|---|
| `infer_base` | base model | ✗ | Standard Model |
| `infer_rag_only` | base model | ✓ | Standard + Docs |
| `infer_specialized_no_rag` | base **+ adapter** | ✗ | Specialized (No RAG) |
| `infer_specialized` | base **+ adapter** | ✓ | Specialized (RAG) |

### Stage 7 — Demo UI
Launches the **full four-panel Gradio app** with a public share link. One question box, one Submit
button; on submit it runs all four functions, fills all four panels, and shows a small **timings**
readout with each panel's own generation wall-clock time (panels run sequentially on one GPU, so these
are individual, not overlapping, times). This is the deliverable stakeholders actually use.

### (Optional) GGUF Export
Merges the adapter into the base weights and exports a single 4-bit **GGUF** file for running the
specialized model locally (outside Colab). Skipped by default to save Drive space.

---

## 5. What happens when someone asks a question

When a user types a question and clicks **Submit**, the same string is sent to all four inference
functions, in sequence (one GPU, one model call at a time). Here's the path for each, using an actual
demo question:

```
       "Under a WIBON clause, when does laytime commence if NOR is tendered at anchorage?"
                                          │
      ┌───────────────┬──────────────────┼──────────────────────┬───────────────────────┐
      ▼               ▼                  ▼                      ▼
 infer_base     infer_rag_only    infer_specialized_no_rag   infer_specialized
      │               │                  │                      │
      │        retrieve(q): embed →      │               retrieve(q): embed →
      │        top-3 chunks from index   │               top-3 chunks from index
      │               │                  │                      │
      │        prepend context to Q      │               prepend context to Q
      │        (RETRIEVAL_TEMPLATE)      │               (RETRIEVAL_TEMPLATE)
      ▼               ▼                  ▼                      ▼
 base model      base model        base model + LoRA      base model + LoRA
      │               │                  │                      │
      └── same system prompt, same generation settings, thinking off ─────────────────┘
      ▼               ▼                  ▼                      ▼
  Standard      Standard + Docs   Specialized (No RAG)   Specialized (RAG)
 panel text        panel text          panel text            panel text
```

The two RAG panels wrap the question in a fixed template before generating:

```
Context:
<top-3 retrieved chunks, joined>

Question: <the user's question>
```

The two non-RAG panels get the bare question. Every panel then generates with the *identical* system
prompt and settings — so any visible difference is caused only by the adapter and/or the retrieved
context. If generation fails (e.g. the GPU runs out of memory), the panel shows
`⚠️ Generation error: <exception type>: <message>` instead of going blank, and the full traceback for
every failed panel is written to a collapsible "Debug log" accordion below the panels — so a failure
is diagnosable without opening the Colab console.

---

## 6. The two levers, a little deeper

### Fine-tuning — QLoRA, done cheaply
Rather than retraining the whole model (impossible on a free GPU), the project trains a small **LoRA
adapter**: a few extra low-rank weight matrices inserted into the attention layers, while the big base
model stays frozen and quantized to 4-bit. That's what "QLoRA" means — LoRA on top of a quantized
model. The result is a ~100 MB file that "teaches" the domain's voice and terminology, trains in
minutes-to-an-hour, and is attached at load time. It changes *how* the model answers, not *what facts*
it can look up.

### RAG — retrieval as an open-book exam
The domain documents are chopped into overlapping chunks and converted to vectors (embeddings). At
question time, the question is embedded the same way and the **most similar chunks** are pulled back
and pasted in front of the question. The model then answers "open book," grounded in text it can
actually see. It changes *what facts* are available, not the model's voice. Retrieval quality is the
ceiling: good chunks → good answers.

*(Neither lever makes the model reliable at exact arithmetic — that's a separate problem the companion
doc covers under "deterministic calculation.")*

---

## 7. What you have to provide (the human inputs)

The notebook is the easy part. Two inputs are supplied by a person and are the real bottleneck:

| Input | What it is | Where it goes |
|---|---|---|
| **Domain documents** | Non-confidential `.txt` / `.md` / `.pdf` files that define the domain | uploaded to `/content/domain_docs/` |
| **Training dataset** | A hand-authored `training_dataset.jsonl` of ≥ 200 `user`→`assistant` Q&A pairs | uploaded to `/content/training_dataset.jsonl` |

A domain expert authors the Q&A pairs and picks the documents. That effort — not the technology — is
what determines whether the demo is impressive. This repo ships both inputs **pre-built** for the
laytime domain (`domain_docs/`, `training_dataset.jsonl`) so the demo runs with no authoring step;
swap in your own domain's files to repurpose the pipeline.

---

## 8. What gets produced, and where

Everything persists under one Drive folder, `MyDrive/domain-llm-poc/`:

```
domain-llm-poc/
├── lora_adapter/             # fine-tuned adapter (~100 MB) + meta.json sidecar   ← Stage 5 (02_finetune.ipynb)
├── chroma_index/             # ChromaDB vector index + meta.json sidecar          ← Stage 4 (01_build_index.ipynb)
├── deps_cache/                # cached dependency wheels, one slot per notebook   ← Stage 0 (every notebook)
├── training_dataset.jsonl     # backup of your training Q&A file                  ← Stage 5 (02_finetune.ipynb)
└── gguf_export/                # optional merged GGUF file                        ← (opt.) 04_export_gguf.ipynb
```

Because these live on Drive, a later run can **load them instead of rebuilding** — which is what makes
the pipeline resumable after a disconnect, and lets any one phase notebook be re-run on its own.

---

## 9. Why it's reproducible and resilient

The project is designed so *anyone* with a Google account can re-run it and get the same result:

- **Per-notebook pinned dependencies** + a **Drive-cached wheelhouse** (one cache slot per notebook,
  keyed by runtime + dependency manifest) → identical, fast installs across runs, with no cross-phase
  dependency conflicts.
- **Fixed random seed** → deterministic training behavior where the framework allows.
- **Everything saved to Drive** → a Colab disconnect never loses the adapter or index.
- **Skip / rebuild prompts** on the expensive stages (RAG index, adapter) → a re-run reuses existing
  artifacts by default, or rebuilds on request. Set `UNATTENDED_DEFAULT` to answer automatically for
  hands-off runs.
- **Artifact metadata sidecars** (`meta.json`) on the index and adapter → the compare/serve and export
  notebooks fail fast with an actionable message if an artifact is missing or was built under a
  different config, instead of silently loading something incompatible.
- **Automatic T4 fallback** → the same notebook runs on a weaker GPU by swapping to a smaller model
  and lighter training config, with no manual edits.

---

## 10. What "working" looks like

The POC is considered successful when:

1. A single shared Gradio link answers the same question in all panels side-by-side.
2. The pipeline runs end-to-end on a fresh Colab session (four notebooks, in order) with no manual
   steps beyond uploading the two inputs — or none at all, using the laytime inputs already in this repo.
3. On the curated demo questions, the Specialized (RAG) panel is visibly better than the Standard panel
   for the domain questions — while the general "sanity-check" questions stay good across all panels
   (proving the fine-tuning didn't damage general ability).
4. All artifacts sit in one Drive folder, and a one-page `findings_template.md` records what improved,
   what didn't, and the invest / iterate / stop call.

---

## 11. The constraints that shaped these choices

Nearly every design decision above traces back to four project principles:

- **Simplicity First** → one notebook, or the bounded four-phase split used today, sharing one
  `config.py` and handing off only through Drive artifacts; in-process ChromaDB (no server), Gradio
  only, no orchestration frameworks. A reviewer can read the whole thing in under an hour.
- **Cost Mandate** → only open-weight models and free OSS libraries; the sole paid resource is the
  existing Colab Pro+ subscription. No paid APIs anywhere.
- **Reproducibility** → pinned deps, fixed seeds, Drive persistence, and a mandatory T4-compatible
  default config.
- **Fair Comparison** → identical everything across panels except the adapter and the retrieved
  context (see §3).

---

## Appendix — key terms

- **Base model** — the stock, open-weight LLM everything is built on (Qwen; a 9B model on A100, a 4B
  model on smaller GPUs).
- **4-bit / NF4 quantization** — storing the model's weights in 4 bits so a large model fits in a
  small GPU's memory.
- **LoRA adapter** — a small set of trainable weights added to a frozen base model; the output of
  fine-tuning (~100 MB).
- **QLoRA** — LoRA training performed on a 4-bit-quantized base model; how fine-tuning fits on a free
  GPU.
- **Embedding** — a numeric vector representing a piece of text, so similar texts sit close together.
- **ChromaDB** — the in-process vector database that stores document embeddings and answers
  similarity searches.
- **RAG (Retrieval-Augmented Generation)** — retrieving relevant document chunks at query time and
  putting them in the prompt so the model answers from grounded text.
- **Gradio** — the Python library that builds the browser UI and generates the temporary public share
  link.
- **GGUF** — a file format for running the merged model locally, outside Colab.
```
