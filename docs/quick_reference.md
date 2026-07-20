# Domain LLM POC — Quick Reference (one page)

> The whole project on one screen. Deep dives: [`how_it_works.md`](how_it_works.md) ·
> [`approach_comparison.md`](approach_comparison.md)

**In a sentence**: run the *same question* through three variants of one small, free open-weight
model — side by side in a browser — so anyone can see whether adapting it to a domain actually
improves the answers.

![Comparison architecture](architecture.svg)

---

### The two levers × the three panels

| Panel | Base model | Fine-tune (LoRA) | RAG (retrieval) | Shows |
|---|:---:|:---:|:---:|---|
| **Standard Model** | ✓ | ✗ | ✗ | raw baseline |
| **Standard + Docs** | ✓ | ✗ | ✓ | RAG's contribution |
| **Specialized Model** | ✓ | ✓ | ✓ | the full combination |

**How to read it:** Standard → Standard+Docs = *what RAG added*. Standard+Docs → Specialized =
*what the adapter added*. Standard → Specialized = *the combined gain*.

---

### The pipeline (one Colab notebook, top to bottom)

`0 Install & Config` → `1 Drive Mount` → `2 Base Model Load` → `3 Skeleton UI` →
`4 RAG Index` → `5 Fine-Tune` → `6 Assemble` → `7 Demo UI` → *(opt.) GGUF export*

---

### What you provide (the real bottleneck)

| Input | Where | Rule |
|---|---|---|
| Domain documents (`.txt/.md/.pdf`) | `/content/domain_docs/` | non-confidential |
| Training dataset (`training_dataset.jsonl`) | `/content/training_dataset.jsonl` | ≥ 200 `user`→`assistant` pairs |

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

- Pinned deps + Drive-cached wheelhouse · fixed seed (`42`) · all artifacts saved to Drive
- Skip/rebuild prompts on the expensive stages (index, adapter) · auto T4 fallback on small GPUs

---

### Done when…

One shared link · same question answered in all panels · Specialized visibly beats Standard on ≥ 4/5
domain questions · general sanity checks stay good in both · one-page findings + invest/iterate/stop call.

---

### Free & simple by mandate

Open-weight models + free OSS only · single notebook · in-process ChromaDB (no server) · Gradio only ·
$0 beyond the existing Colab Pro+ subscription.
