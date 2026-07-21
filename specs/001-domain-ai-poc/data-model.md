# Data Model: Domain-Specialized AI Assistant — POC

**Feature**: `specs/001-domain-ai-poc`
**Date**: 2026-07-20

---

## Overview

This POC has no relational database. "Data model" here describes the schemas of the four
external data objects that flow into or out of the notebook: configuration, training dataset,
vector index, and demo question set.

---

## 1. Notebook Configuration

A constants block at the top of Stage 0 (cell group "Install & Config"). All tunable values
are declared here; downstream cells reference them by name.

| Field | Type | Default | Description |
|---|---|---|---|
| `MODEL_ID` | str | `"unsloth/Qwen3.5-0.8B"` | HuggingFace model ID (T4 fallback: `"Qwen/Qwen3-4B-Instruct-2507"`) |
| `SEED` | int | `42` | Global random seed (NumPy, PyTorch, Transformers) |
| `MAX_SEQ_LEN` | int | `2048` | Training + inference sequence length (T4 fallback: `512`) |
| `LORA_R` | int | `32` | LoRA rank (T4 fallback: `8`) |
| `LORA_ALPHA` | int | `32` | LoRA alpha (= rank for scaling factor 1.0; T4 fallback: `8`) |
| `LORA_DROPOUT` | float | `0.05` | LoRA dropout rate |
| `LORA_TARGETS` | list[str] | `["q_proj","k_proj","v_proj","o_proj"]` | Modules to adapt (T4 fallback: `["q_proj","v_proj"]`) |
| `TRAIN_EPOCHS` | int | `14` | Training epochs (T4 fallback: `2`) |
| `TRAIN_BATCH` | int | `4` | Per-device batch size (T4 fallback: `1`) |
| `GRAD_ACCUM` | int | `2` | Gradient accumulation steps (T4 fallback: `8`) |
| `LEARNING_RATE` | float | `2e-4` | AdamW learning rate |
| `CHUNK_SIZE` | int | `2000` | Character chunk size for text splitting (~500 tokens) |
| `CHUNK_OVERLAP` | int | `200` | Character overlap between chunks |
| `TOP_K` | int | `3` | Number of retrieved document chunks per query |
| `MAX_NEW_TOKENS` | int | `512` | Max tokens to generate per response |
| `TEMPERATURE` | float | `0.1` | Sampling temperature (both variants) |
| `TOP_P` | float | `0.9` | Top-p sampling (both variants) |
| `REPETITION_PENALTY` | float | `1.1` | Repetition penalty (both variants) |
| `ENABLE_THINKING` | bool | `False` | Qwen3.5 thinking mode — MUST be False for both variants (§IV) |
| `DRIVE_BASE` | str | `"/content/drive/MyDrive/domain-llm-poc"` | Root Drive artifact path |
| `DOCS_PATH` | str | `"/content/domain_docs"` | Local path for uploaded domain documents |
| `DATASET_PATH` | str | `"/content/training_dataset.jsonl"` | Local path for uploaded training file |
| `SYSTEM_PROMPT` | str | `"You are a helpful assistant. Answer questions clearly and concisely."` | System prompt injected into every inference call — MUST be identical for all three panel variants (§IV Fair Comparison) |
| `RETRIEVAL_TEMPLATE` | str | `"Context:\n{context}\n\nQuestion: {question}"` | Template for assembling RAG prompt; `{context}` is filled by `retrieve()`, `{question}` by the user input |

**Invariant**: `TEMPERATURE`, `TOP_P`, `MAX_NEW_TOKENS`, `REPETITION_PENALTY` MUST be passed
identically to both the standard model and the specialized model inference calls (§IV Fair
Comparison). `SYSTEM_PROMPT` MUST be identical across all three panel variants; it is injected
at inference time, not present in the training JSONL.

---

## 2. Training Dataset (JSONL)

**File**: uploaded by domain expert to `DATASET_PATH` before running Stage 5.
**Format**: One JSON object per line (JSONL). UTF-8 encoded.

### Schema (per line)

```json
{
  "messages": [
    {"role": "user",      "content": "<question or instruction>"},
    {"role": "assistant", "content": "<expected domain answer>"}
  ]
}
```

### Constraints

| Constraint | Rule |
|---|---|
| Minimum pairs | 200 lines |
| Target pairs | 500–1,000 lines |
| Maximum | No hard upper limit; >2,000 lines will extend training beyond 90-minute target on T4 |
| `role` values | MUST be exactly `"user"` and `"assistant"` (Llama 3 chat template) |
| `content` values | Non-empty strings; no JSON-embedded markup required |
| Line format | Each line is a valid standalone JSON object; no trailing commas |
| Encoding | UTF-8; no BOM |
| Domain specificity | Questions SHOULD be answerable only from domain knowledge; answers SHOULD use domain terminology |
| No system turn | The system prompt is injected by the notebook at training time; do NOT include a system role in the JSONL |

### Example line

```json
{"messages": [{"role": "user", "content": "What is the maximum rated load for a Type-B mounting bracket?"}, {"role": "assistant", "content": "The Type-B mounting bracket is rated for a maximum static load of 250 kg and a dynamic load of 180 kg per the current product specification sheet (rev. 4.2)."}]}
```

---

## 3. Vector Index (ChromaDB Collection)

Built from domain documents in Stage 4. Persisted to Drive at
`DRIVE_BASE/chroma_index/`.

### Collection structure

| Field | Value |
|---|---|
| Collection name | `"domain_docs"` |
| Embedding model | `all-MiniLM-L6-v2` (384-dimensional) |
| Distance metric | Cosine similarity |
| Metadata per chunk | `{"source": "<filename>", "chunk_id": <int>}` |

### Document processing pipeline

```
domain_docs/ (uploaded files)
  → read text content
  → RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
  → List[str] chunks
  → SentenceTransformer.encode()
  → ChromaDB collection.add(documents=chunks, embeddings=embeddings, metadatas=metas)
  → PersistentClient auto-saves to DRIVE_BASE/chroma_index/
```

### Retrieval function signature (conceptual)

```
retrieve(query: str, k: int = TOP_K) -> str
  Returns: concatenated top-k chunk texts, prefixed with "Context:\n"
  Used as: prefix prepended to user question in specialized model prompt
```

### Supported document formats

| Format | Handling |
|---|---|
| `.txt` | Direct read |
| `.md` | Direct read |
| `.pdf` | `pdfplumber` or `pypdf` text extraction (add to pinned deps if used) |

---

## 4. Demo Question Set

**File**: `data/demo_questions.md` (committed to repository)

### Schema

A markdown document with three required sections:

```markdown
# Domain LLM POC — Demo Question Set

## Domain-Specific Questions (answers require domain knowledge)
<!-- Minimum 3, maximum 7 questions -->
1. <question text>
   **Expected**: <brief description of what a good answer contains>

## Terminology Questions (use domain-specific terms)
<!-- Minimum 1, maximum 3 questions -->
1. <question text>
   **Expected**: <brief description>

## General Sanity-Check Questions (not domain-specific)
<!-- Exactly 1–2 questions -->
1. <question text>
   **Expected**: <both models should answer reasonably>
```

### Constraints

| Constraint | Rule |
|---|---|
| Total questions | 5–10 |
| Domain-specific | ≥3; answerable only from domain documents |
| Terminology | ≥1; uses domain-specific terms the base model is unlikely to know |
| General sanity checks | 1–2; verifies fine-tuning did not degrade general capability |
| Expected answer notes | Must be descriptive enough for a non-expert to judge the response quality |

---

## 5. Drive Artifact Hierarchy

**Root**: `DRIVE_BASE` = `/content/drive/MyDrive/domain-llm-poc/`

```text
domain-llm-poc/
├── lora_adapter/          # LoRA adapter weights (~100 MB)
│   ├── adapter_config.json
│   └── adapter_model.safetensors
├── chroma_index/          # ChromaDB persistent index (Drive-backed)
│   └── <chroma internal structure>
├── training_dataset.jsonl # Copy of the uploaded training file (for reproducibility)
└── notebook.ipynb         # Copy of the notebook at training time
```

### Lifecycle

| Artifact | Created | Overwritten on re-run |
|---|---|---|
| `lora_adapter/` | Stage 5 (fine-tuning) | Yes — last run wins |
| `chroma_index/` | Stage 4 (RAG build) | Yes — rebuilt from documents |
| `training_dataset.jsonl` | Stage 5 (copied from upload) | Yes |
| `notebook.ipynb` | Stage 7 (optional save) | Yes |
