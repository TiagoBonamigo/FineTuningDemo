<!--
## Sync Impact Report

- Version change: 1.1.0 → 1.2.0
- Bump type: MINOR (expanded guidance — permits optional notebook decomposition; no principle removed).
- Modified principles: I. Simplicity First (rationale softened, decomposition clause added);
  IV. Fair Comparison (added split-safety clause: all panels + shared params in the serve notebook).
- Added sections: Technology Constraints → "Notebook Decomposition (optional)".
- Clarified: III. Reproducibility (per-notebook minimal dependency pinning affirmed);
  Quality & Delivery Standards → Definition of Done (generalized "the notebook" → multi-notebook layout).
- Unchanged: II. Cost Mandate; III. T4-degradability requirement.
- Templates reviewed: plan-template.md ✅ (generic Constitution Check gate, no hard-coded principle text),
  spec-template.md ✅, tasks-template.md ✅, checklist-template.md ✅. No edits required.
- Skills reviewed: .claude/skills/speckit-* ✅ (generic guidance, no stale references).
- ⚠ Pending manual sync (runtime guidance docs, outside this file):
  - `CLAUDE.md` — "Keep it a single notebook" and "no local module imports and no helper scripts"
    must be reconciled with the optional decomposition + single shared config module.
  - `README.md`, `docs/how_it_works.md` — "one notebook" framing to be updated if a split is adopted.
- Deferred TODOs: none.

---

## Amendment Log

### v1.2.0 — 2026-07-20

- **§I Simplicity First**: Softened the rationale's single-Colab-session assumption and added a
  decomposition clause — the codebase MAY be split into at most four phase notebooks
  (build-RAG-index, fine-tune, compare/serve, optional GGUF export) that communicate ONLY through
  Google Drive artifacts, plus exactly one shared configuration module as the single source of
  truth for constants. No other cross-notebook imports or helper scripts are permitted.
- **§Technology Constraints**: Added "Notebook Decomposition (optional)" defining the allowed phase
  notebooks, their Drive-artifact-only handoff, per-notebook minimal dependency pinning, and that
  only the compare/serve notebook co-locates the full stack.
- **§III Reproducibility**: Affirmed that each notebook pins its own minimal dependency subset in
  its first cell (existing plural phrasing made explicit).
- **§IV Fair Comparison**: Added that when split, all three inference panels MUST live in the single
  compare/serve notebook and every shared parameter MUST be imported from the shared config module,
  so the fair-comparison invariant cannot drift across files.
- **§Definition of Done**: Generalized items referring to "the notebook" to hold for the
  multi-notebook layout.
- Rationale: Enables modularity/reuse of the RAG index and adapter, and shrinks each build
  notebook's dependency surface (isolating conflicts such as transformers-v5 vs. the RAG stack)
  while preserving Simplicity, Reproducibility, and Fair Comparison.
- Version bump type: MINOR (expanded/clarified guidance; no principle removed or redefined).

### v1.1.0 — 2026-07-20

- **§2.2 Model Requirements**: Raised A100 upgrade cap from 8B to 10B parameters.
  Added approved candidates: Qwen3.5-9B (primary A100 model), Qwen3-4B-Instruct-2507 (T4 fallback).
  Replaced outdated A100 examples (Llama 3.1 8B, Qwen2.5 7B) with current recommendations.
- **§2.6 Prohibited**: Updated model size cap to match §2.2 (8B → 10B).
- Rationale: Qwen3.5-9B (Apache 2.0, March 2026) delivers substantially better domain Q&A
  performance than Qwen3-8B on A100, fits within 40 GB VRAM at ~22 GB LoRA VRAM, and has
  first-class Unsloth support. The 1B overage from the prior cap is trivial relative to the
  performance gain. Qwen3-4B-Instruct-2507 is the July 2025 refresh of Qwen3-4B with improved
  instruction following — superior T4 fallback.
- Version bump type: MINOR (new model approvals, expanded guidance).
-->

# Domain LLM Comparison POC Constitution

This document defines the non-negotiable technical principles, constraints, and standards that govern
all implementation decisions for this project. Any plan, task, or code change that conflicts with
this constitution MUST be revised or explicitly justified as an amendment (see §Governance).

## Core Principles

### I. Simplicity First

Every component MUST use the simplest viable implementation. If a feature can be delivered in fewer
moving parts, it MUST be. No microservices, no orchestration frameworks, no databases requiring a
server process. A reviewer MUST be able to read the entire codebase in under one hour.

The codebase MAY be a single notebook, or — when it aids modularity/reuse or isolates dependency
conflicts — MAY be decomposed into **at most four** phase notebooks (build-RAG-index, fine-tune,
compare/serve, and an optional GGUF export). Decomposition is permitted ONLY under these limits:

- Phase notebooks MUST communicate exclusively through Google Drive artifacts (e.g.
  `chroma_index/`, `lora_adapter/`, `training_dataset.jsonl`). No notebook may depend on another's
  in-memory state.
- Exactly **one** shared configuration module MAY exist as the single source of truth for constants
  (model id, seed, generation parameters, system prompt, paths). It is the ONLY permitted
  cross-notebook import. No other local module imports and no additional helper scripts are allowed.
- The "readable in under one hour" bar applies to the whole set, not per notebook.

**Rationale**: POC scope does not justify incidental complexity. Every additional abstraction is a
maintenance burden and a reproducibility risk. A bounded, artifact-decoupled split does not add
incidental complexity — it removes it, by letting each phase run in its own Colab session with a
minimal dependency surface — so it is permitted within the strict limits above.

### II. Cost Mandate

The project MUST incur no software licensing cost. The sole approved paid resource is a Google Colab
Pro+ subscription (already available to the team).

- All libraries MUST be free and open source (Apache 2.0, MIT, or comparable licenses).
- All models MUST be open-weight and freely downloadable — no gated commercial APIs.
- All compute MUST run on Google Colab (Pro+) or on the developer's local machine.
- No paid inference APIs, no additional cloud subscriptions, no other paid services of any kind.
- Colab compute-unit consumption on Pro+ MUST be treated as a budget, not an unlimited resource.

**Rationale**: The POC must be reproducible by any team member with only a Google account and the
existing Pro+ subscription, with zero incremental spend.

### III. Reproducibility

Anyone with a Google account MUST be able to reproduce the full experiment by running the
notebook(s) top to bottom without manual intervention beyond dataset upload.

- Random seeds MUST be fixed where the framework allows.
- All dependency versions MUST be pinned in the first cell of each notebook. When the codebase is
  split (see §I), each notebook MUST pin only its OWN minimal dependency subset — not the union —
  so its environment stays as small and conflict-free as its phase allows.
- All artifacts (adapter weights, vector index, dataset) MUST be persisted to Google Drive or be
  downloadable, so a Colab disconnect never destroys work.
- Notebooks MUST gracefully degrade to a T4 GPU (16 GB VRAM), i.e., default configs MUST fit 16 GB.

**Rationale**: A POC that can only be re-run by the original author is not a POC — it is a
one-time demo. Pinned dependencies and Drive persistence guarantee long-term reproducibility.

### IV. Fair Comparison

The comparison between the baseline and enhanced model variants MUST be scientifically honest.

- Both variants MUST share: the same base model, the same quantization level, the same generation
  parameters (temperature, max tokens, top-p), and the same system prompt scaffolding.
- The only permitted differences between variants are (a) the LoRA adapter and (b) the retrieved
  context.
- Identical questions MUST be sent to both variants simultaneously.
- When the codebase is split (see §I), all three inference panels (Standard / Standard+Docs /
  Specialized) MUST live in the single compare/serve notebook, and every shared parameter (base
  model, quantization, generation params, system prompt) MUST be imported from the shared
  configuration module — never re-declared per notebook — so the invariant cannot drift across files.

**Rationale**: Any variable beyond the intended one (adapter / retrieved context) would confound
the comparison and undermine the POC's core purpose: demonstrating the value of fine-tuning + RAG.

## Technology Constraints

### Compute Environment

| Constraint | Requirement |
|---|---|
| Training environment | Google Colab Pro+: NVIDIA A100 (40 GB VRAM) preferred; L4 (24 GB) or T4 (16 GB) acceptable fallbacks |
| Session features | Background execution and ~24 h sessions (Pro+) MAY be used; no single run MUST require more than a few hours |
| Inference environment | Same Colab session as training, or local machine via GGUF export |
| Session resilience | All artifacts MUST be persisted to Google Drive or downloadable (see §III Reproducibility) |

### Notebook Decomposition (optional)

The project MAY ship as one notebook or as the bounded split permitted by §I. If split, the layout
MUST be exactly the following phase notebooks, each runnable top-to-bottom in its own Colab session:

| Notebook | Responsibility | Consumes (Drive) | Produces (Drive) | Dependency surface |
|---|---|---|---|---|
| Build RAG index | Chunk + embed docs, build the vector store | `domain_docs/` | `chroma_index/` | embeddings + vector store + splitter only |
| Fine-tune | QLoRA training of the base model | `training_dataset.jsonl` | `lora_adapter/` | training stack only (Unsloth/PEFT/TRL/transformers) |
| Compare/serve | Load base + adapter + RAG; Gradio side-by-side | `chroma_index/`, `lora_adapter/` | — (ephemeral Gradio link) | the full stack (the ONLY notebook that co-locates everything) |
| GGUF export *(optional)* | Merge + export for local inference | `lora_adapter/` | `gguf_export/` | export tooling only |

- Handoff between notebooks MUST be through the Drive artifacts above only — never shared in-memory
  state (see §I). Each notebook re-loads what it needs from Drive.
- Each notebook pins only its own minimal dependency subset (see §III). Isolating the build phases
  is an explicit benefit: a smaller per-notebook surface removes cross-stack version conflicts.
- The compare/serve notebook is the sole place the full stack must coexist; its pins MUST still
  satisfy §IV Fair Comparison for all three panels.

### Model Requirements

- Default base model size: **1B–4B parameters** (guarantees T4 compatibility and fast iteration).
- With an A100 runtime, models up to **10B parameters** (e.g., Qwen3.5-9B, Qwen3-8B) are
  approved as the primary target — permitted only after the full pipeline works end-to-end with
  the small default (see §Build Order).
- Models MUST be open-weight, instruction-tuned, and available on Hugging Face without payment.
- **Approved T4-safe candidates (1–4B)**: Qwen3-4B-Instruct-2507 *(preferred)*, Llama 3.2 3B
  Instruct, Qwen2.5 3B Instruct, Gemma 3 4B, Phi-3.5-mini. Substitutions allowed only if all
  constraints in this section are satisfied.
- **Approved A100 candidates (up to 10B)**: Qwen3.5-9B *(preferred)*, Qwen3-8B.
- Quantization: 4-bit QLoRA / bitsandbytes NF4 for both training and inference.

### Fine-Tuning Stack

- Framework: **Unsloth** (free, Colab-optimized) with QLoRA.
- Method: LoRA adapters only. Full fine-tuning is **prohibited** (does not fit the compute budget
  and violates §I Simplicity First).
- Dataset format: JSONL instruction/response pairs; minimum 200 pairs, target 500–1,000.
- Training MUST complete in under 90 minutes on the target GPU. On a T4 fallback, epochs, sequence
  length, or dataset size MUST be reduced to stay within this limit.
- The adapter MUST be exportable as a LoRA adapter (~100 MB) and optionally as a merged GGUF.

### RAG Stack

- Embeddings: `sentence-transformers`, model `all-MiniLM-L6-v2` (English) or `bge-m3`
  (multilingual). CPU inference is acceptable.
- Vector store: **ChromaDB** or **FAISS** — in-process only, no server.
- Chunking: simple fixed-size splitter, ~500 tokens with ~50-token overlap. No agentic chunking,
  no proposition indexing.
- Retrieval: top-k similarity search, k = 3–5, prepended to the prompt with a fixed template.
- Heavy frameworks (LangChain, LlamaIndex) are permitted **only** for text splitting utilities.
  The retrieval pipeline itself MUST be plain Python (~50 lines max).

### Interface

- Framework: **Gradio** (runs in Colab; free public share link).
- Layout: one question input; side-by-side output panels (baseline vs. enhanced); single submit
  action fanning out to both variants.
- An optional third panel (base + RAG, no fine-tune) is encouraged for improvement attribution.
- No authentication, no persistence of user queries, no analytics. The share link is ephemeral.

### Prohibited

The following are explicitly **forbidden** in any part of the pipeline:

- Paid APIs (OpenAI, Anthropic, Cohere, etc.), including for dataset generation presented as part
  of the reproducible flow.
- Any paid service other than the approved Colab Pro+ subscription.
- Models above 10B parameters; models above 4B before the small-model pipeline is proven.
- Any component requiring Docker, Kubernetes, or a hosted database.
- Frontend frameworks (React, Vue) — Gradio only.

## Quality & Delivery Standards

### Definition of Done

The POC is complete when ALL of the following hold:

1. A single shared Gradio link (served by the compare/serve notebook, if split) answers the same
   question with all model variants side by side.
2. Every notebook runs end to end on a fresh Colab session without manual intervention beyond
   dataset upload; if split, running them in order (build-index → fine-tune → compare/serve)
   reproduces the full experiment.
3. A demo script of 5–10 domain questions demonstrably shows a quality difference between variants.
4. All artifacts (notebook(s), shared config module, dataset, adapter, index) are stored in one
   Drive folder or repository.

### Evaluation Standard

- Evaluation is **qualitative side-by-side comparison** — no benchmark suites, no LLM-as-judge
  pipelines. Formal evaluation is explicitly out of scope for the POC.
- The demo question set MUST include:
  - (a) Questions answerable only from domain documents.
  - (b) Questions using domain-specific terminology.
  - (c) One or two general questions as a sanity check that fine-tuning did not degrade general ability.

### Build Order (Risk-First)

Work MUST proceed in this order so a working demo exists at every stage:

1. Base model inference in Colab (walking skeleton).
2. Gradio dual-panel UI wired to the base model twice.
3. RAG pipeline attached to one panel.
4. Fine-tuning; adapter attached to the enhanced panel.
5. Demo script and artifact persistence.

Any deviation from this order MUST be recorded in the Deviations section of the affected notebook.

## Governance

- This constitution supersedes all other practices for this project. Any plan, spec, or task that
  conflicts with it MUST be revised before execution.
- **Amendment process**: Any deviation from this constitution MUST be recorded in a "Deviations"
  section at the top of the affected notebook, with a one-line justification. Silent deviations
  are not permitted.
- **Versioning policy**:
  - MAJOR bump: backward-incompatible removal or redefinition of a principle.
  - MINOR bump: new principle, section added, or materially expanded guidance.
  - PATCH bump: clarifications, wording fixes, non-semantic refinements.
- **Compliance review**: All plans and task lists generated by speckit MUST pass the Constitution
  Check gate in the plan-template before Phase 0 research begins.
- **Runtime guidance**: See `.specify/templates/` for plan, spec, and tasks templates that encode
  this constitution's constraints as actionable gates.

**Version**: 1.2.0 | **Ratified**: 2026-07-20 | **Last Amended**: 2026-07-20
