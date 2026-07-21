# Domain LLM POC — Quick Reference (one page)

> The whole project on one screen. Deep dives: [`how_it_works.md`](how_it_works.md) ·
> [`approach_comparison.md`](approach_comparison.md)

**In a sentence**: run the *same question* through four variants of one small, free open-weight
model — side by side in a browser — so anyone can see whether adapting it to a domain actually
improves the answers. **Domain in this repo**: laytime & voyage-charterparty calculation (NOR, SHEX,
demurrage) — see `README.md`.

![Comparison architecture](architecture.svg)

---

### The two levers × the four panels

| Panel | Base model | Fine-tune (LoRA) | RAG (retrieval) | Shows |
|---|:---:|:---:|:---:|---|
| **Standard Model** | ✓ | ✗ | ✗ | raw baseline |
| **Standard + Docs** | ✓ | ✗ | ✓ | RAG's contribution alone |
| **Specialized (No RAG)** | ✓ | ✓ | ✗ | fine-tuning's contribution alone |
| **Specialized (RAG)** | ✓ | ✓ | ✓ | the full combination |

**How to read it:** Standard → Standard+Docs = *what RAG added alone*. Standard → Specialized
(No RAG) = *what fine-tuning added alone*. Specialized (No RAG) → Specialized (RAG) = *what RAG adds
on top of fine-tuning*. Standard → Specialized (RAG) = *the combined gain*.

---

### The pipeline (four Colab notebooks, sharing one `config.py`)

`01 Build Index` (RAG) → `02 Fine-Tune` (QLoRA) → `03 Compare & Serve` (4-panel demo) →
*(opt.) `04 GGUF Export`*

Each notebook hands off through Drive artifacts only — no in-memory state crosses notebooks.

---

### What you provide (the real bottleneck)

| Input | Where | Rule |
|---|---|---|
| Domain documents (`.txt/.md/.pdf`) | `/content/domain_docs/` | non-confidential |
| Training dataset (`training_dataset.jsonl`) | `/content/training_dataset.jsonl` | ≥ 200 `user`→`assistant` pairs |

This repo ships both, pre-built for the laytime domain — run the demo with no authoring needed.

---

### Defaults at a glance

| Base model | Quantization | LoRA | Chunking | Retrieval | Generation |
|---|---|---|---|---|---|
| Qwen3.5-9B (A100) / Qwen3-4B (T4) | 4-bit NF4 | r=32, α=32, q/k/v/o | 2000 chars / 200 overlap | top-3, cosine | temp 0.1, top-p 0.9, 512 tok, thinking off |

---

### The one rule (fair comparison)

Every panel shares the **same base model, quantization, system prompt, and generation settings**.
The **only** differences allowed are the adapter and the retrieved context.

---

### Reproducible & resilient

- Per-notebook pinned deps + Drive-cached wheelhouse (one slot per notebook) · fixed seed (`42`) ·
  all artifacts saved to Drive
- Skip/rebuild prompts on the expensive stages (index, adapter) · auto T4 fallback on small GPUs
- `meta.json` sidecars on the index/adapter → downstream notebooks fail fast on a missing or
  config-drifted artifact instead of silently loading it

---

### Done when…

One shared link · same question answered in all panels · Specialized (RAG) visibly beats Standard on
≥ 4/5 domain questions · general sanity checks stay good across all panels · one-page findings +
invest/iterate/stop call.

---

### Free & simple by mandate

Open-weight models + free OSS only · four phase notebooks sharing one `config.py` · in-process
ChromaDB (no server) · Gradio only · $0 beyond the existing Colab Pro+ subscription.
