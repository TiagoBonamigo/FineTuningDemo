# Research: Domain-Specialized AI Assistant — POC

**Feature**: `specs/001-domain-ai-poc`
**Date**: 2026-07-20
**Phase**: 0 — Research & Technology Decisions

---

## Decision 1: Base Model

**Primary (A100 target)**: `unsloth/Qwen3.5-9B`
**T4 fallback**: `Qwen/Qwen3-4B-Instruct-2507`

### Primary — Qwen3.5-9B

**Rationale**:
- Released March 2026; Apache 2.0 license — fully compliant with §II (Cost Mandate).
- 9B parameters in NF4 occupies ~5 GB VRAM; LoRA fine-tuning in bf16 uses ~22 GB — leaves
  ~18 GB free on an A100 40 GB for activations and batch overhead. Comfortable headroom.
- Benchmark performance is exceptional for a 9B model: beats Qwen3-80B on GPQA Diamond
  (81.7 vs 77.2) and IFEval (91.5 vs 88.9); outperforms GPT-OSS-120B on MMLU-Pro (82.5 vs
  80.8). Strong instruction following benefits domain Q&A fine-tuning directly.
- Unsloth has a dedicated fine-tuning guide and Colab templates for Qwen3.5 (confirmed via
  `unsloth.ai/docs/models/qwen3.5/fine-tune`); `unsloth/Qwen3.5-9B` is the pre-configured
  HuggingFace variant.
- Hybrid architecture (Gated DeltaNet + Gated Attention) gives better long-context retention
  than standard transformer — useful when RAG context is prepended to prompts.
- 262K native context window (overkill for POC but future-proof for production follow-on).
- **Thinking mode**: Qwen3.5 supports both thinking (chain-of-thought) and non-thinking modes.
  For domain Q&A demos, thinking mode MUST be disabled to keep responses concise and comparable:
  pass `enable_thinking=False` in `model.generate()`. This is a one-parameter change, not an
  architectural constraint.
- Approved by constitution §2.2 amendment v1.1.0 (cap raised to 10B for A100).

### T4 fallback — Qwen3-4B-Instruct-2507

**Rationale**:
- July 2025 refresh of Qwen3-4B with improved instruction following and logical reasoning.
  Meaningfully better than Llama 3.2 3B Instruct (the prior default) and the original Qwen3-4B.
- Apache 2.0 ✅; 4B in NF4 ≈ 2.3 GB VRAM — ample headroom on a T4 16 GB.
- Same Qwen family as the primary model: same chat template, same `enable_thinking=False` flag,
  same generation parameter names. Switching between primary and fallback is a one-line
  `MODEL_ID` change.
- Unsloth pre-quantized variant available: `unsloth/Qwen3-4B-bnb-4bit`.

**Alternatives considered**:
- *Qwen3-8B*: Strong option (Apache 2.0, Apr 2025), but Qwen3.5-9B outperforms it on most
  benchmarks and both fit on A100 with similar VRAM budgets. No reason to prefer 8B over 9B.
- *Llama 3.2 3B Instruct*: Prior default. Superseded by Qwen3-4B-Instruct-2507 as T4 fallback
  — newer architecture, better instruction following. Remains an acceptable emergency fallback.
- *Gemma 3 4B*: Stronger per-parameter but Gemma license adds compliance uncertainty. Excluded.
- *Phi-4 mini (3.8B)*: MIT license, strong reasoning; acceptable alternative to the T4 fallback
  if Qwen3 Unsloth support is unavailable for any reason.

---

## Decision 2: Fine-Tuning Configuration

**A100 primary config**: Unsloth QLoRA, `r=32`, `lora_alpha=32`,
target modules `q_proj`, `k_proj`, `v_proj`, `o_proj`,
3 epochs, `max_seq_length=2048`, `batch_size=4`, `grad_accum=2` (effective batch 8).

**Rationale**:
- `r=32` on A100: with ~18 GB headroom above the base model's LoRA VRAM (~22 GB), rank 32
  fits easily and gives better domain knowledge retention than rank 16. Higher ranks offer
  diminishing returns at POC dataset sizes (200–1,000 pairs).
- `lora_alpha=32` equals `r` — scaling factor 1.0, clean learning rate reasoning.
- Adding `k_proj` and `o_proj` to targets (vs. just `q_proj`+`v_proj` previously): on A100
  the VRAM is available, and covering the full attention pathway improves factual recall from
  domain training data, which is the core POC objective.
- `max_seq_length=2048`: A100 handles this comfortably; allows richer training examples and
  longer RAG context windows at inference time (prior 512 limit was T4-driven).
- 3 epochs over 200–1,000 pairs: ~20–40 minutes on A100. Well within the 90-minute mandate.
- Batch size 4 + gradient accumulation 2: stable and efficient on A100 40 GB.

**T4 fallback config** (Qwen3-4B-Instruct-2507; auto-selected when GPU VRAM < 24 GB):
`r=8`, `lora_alpha=8`, targets=`q_proj`+`v_proj`, `max_seq_length=512`,
`batch_size=1`, `grad_accum=8`, `num_epochs=2`. Fits in ~8 GB LoRA VRAM on T4.

**Alternatives considered**:
- Full fine-tuning: prohibited by §2.3 and §I.
- `r=64`: Risks overfitting on small datasets; not justified at POC scale.
- `max_seq_length=4096`: Possible on A100 but doubles memory per sequence; 2048 is sufficient
  for domain Q&A pairs and typical RAG context.

---

## Decision 3: Vector Store

**Decision**: ChromaDB (`chromadb.PersistentClient`)

**Rationale**:
- In-process, no server — fully compliant with §2.4.
- `PersistentClient(path=<drive_path>)` writes the index directly to Google Drive, satisfying
  §III (Reproducibility / Drive persistence) without any extra serialization step.
- Simpler Python API than FAISS (no manual `index.add()` / `faiss.write_index()` calls).
- The retrieval pipeline stays well under 50 lines (§2.4).

**Alternatives considered**:
- *FAISS*: Faster at scale, but requires manual `faiss.write_index` / `faiss.read_index` for
  Drive persistence, adding complexity. Acceptable substitute if ChromaDB causes Colab install
  issues (it occasionally conflicts with older `protobuf` versions — pin `chromadb>=0.5,<1.0`).

---

## Decision 4: Embedding Model

**Decision**: `sentence-transformers/all-MiniLM-L6-v2`

**Rationale**:
- Mandated as the English-language default in §2.4.
- 22 M parameters, runs on CPU without any VRAM impact — important since the GPU is occupied
  by the LLM during inference.
- 384-dimensional embeddings; 512-token input limit aligns with the chunking window.
- Apache 2.0 license.

**Alternatives considered**:
- `BAAI/bge-m3`: Preferred for multilingual domains (§2.4 approved option). Drop-in substitute
  if the target domain uses non-English terminology; note it's heavier (570 M params) and may
  be slower on CPU for large document sets.

---

## Decision 5: Chunking Strategy

**Decision**: Fixed-size character splitter, chunk_size=500 tokens (~2,000 characters with
Llama tokenizer), overlap=50 tokens (~200 characters).

**Rationale**:
- Mandated by §2.4: "simple fixed-size splitter, ~500 tokens with ~50-token overlap."
- Keeps retrieved chunks within the LLM's effective context window even after prepending the
  system prompt and question.
- The overlap prevents splitting mid-sentence at chunk boundaries.
- Implementation: `langchain_text_splitters.RecursiveCharacterTextSplitter` (text-splitting only,
  no LangChain retrieval or chain machinery — compliant with §2.4 "heavy frameworks permitted
  only for text splitting utilities").

---

## Decision 6: Notebook Architecture

**Decision**: Single `notebook.ipynb` with 8 sequential stages (cells grouped by stage).

**Rationale**: §I Simplicity First. One file to upload, one file to share. Zero module imports
from local files.

**Stage map**:

| Stage | Cell group | Description |
|---|---|---|
| 0 | Install & Config | `!pip install` with pinned versions; constants block (model ID, seed, paths) |
| 1 | Drive Mount | Mount Google Drive; create artifact directory structure |
| 2 | Base Model Load | Load Llama 3.2 3B in NF4 via Unsloth; verify with smoke test |
| 3 | Walking Skeleton UI | Minimal Gradio with base model on both panels (first shippable demo) |
| 4 | RAG Pipeline | Load documents → chunk → embed → ChromaDB index; retrieval function |
| 5 | Fine-Tuning | Load training JSONL; SFTTrainer; save LoRA adapter to Drive |
| 6 | Full Pipeline | Load adapter + index; wire specialized inference function |
| 7 | Demo UI | Full Gradio with 2 (or 3) panels, loading indicators, error handling; `share=True` |

Stages 0–3 constitute the "walking skeleton" deliverable (build order step 1+2, §3.3).
Stage 4 completes build order step 3 (RAG).
Stage 5–6 complete build order step 4 (fine-tuning + adapter).
Stage 7 + demo_questions.md complete build order step 5 (demo script + artifacts).

---

## Decision 7: Generation Parameters (Shared Config)

**Decision**:
```python
gen_config = dict(
    max_new_tokens=512,
    temperature=0.1,
    top_p=0.9,
    do_sample=True,
    repetition_penalty=1.1,
    enable_thinking=False,   # Qwen3.5-specific: disables chain-of-thought mode
)
```

**Rationale**:
- Low temperature (0.1) for factual domain Q&A: reduces hallucination, increases consistency
  across runs, makes the comparison fair (§IV).
- `max_new_tokens=512`: sufficient for detailed domain answers; does not need to match
  `max_seq_length` (which governs training context, not generation length).
- `repetition_penalty=1.1`: mild, prevents repetition loops without distorting output.
- `enable_thinking=False` (Qwen3.5-specific): Qwen3.5 defaults to thinking mode (verbose
  chain-of-thought reasoning prefixed with `<think>…</think>`). For side-by-side domain Q&A,
  thinking output would be confusing for non-technical stakeholders and make answers much longer.
  Disabling it produces clean, direct answers. Applied to both variants (§IV Fair Comparison).
- Identical dict passed to both panel inference calls.

---

## Decision 8: Gradio UI Architecture

**Decision**: `gr.Blocks` with one `gr.Textbox` input, two (optionally three) `gr.Textbox`
output panels, one `gr.Button`. Batch generation (no streaming). Gradio's native spinner appears
automatically on output components while the handler runs. Error messages returned as strings
from the handler.

**Rationale**:
- `gr.Blocks` gives layout control (side-by-side columns) that `gr.Interface` does not.
- Gradio 4.x shows an automatic loading indicator on output components while the event handler
  is executing — satisfies FR-002 loading indicator requirement at zero extra code.
- On inference failure: handler wraps model calls in `try/except`; returns error string
  `"⚠️ Generation failed — please retry."` to the panel — satisfies FR-002 error requirement.
- `share=True` on `demo.launch()` generates the public temporary URL.

---

## Resolved Clarifications Incorporated

| Clarification | Impact on research |
|---|---|
| Training pairs manually authored (Q1) | Stage 5 loads JSONL from upload path; no data-gen cell needed |
| Response latency aspirational (Q2) | No streaming; batch `generate()` call; no `TextIteratorStreamer` |
| Per-panel loading indicator (Q3) | Gradio native spinner; no extra implementation needed |
| Error message on failure (Q4) | `try/except` in inference handler; string return to panel |
