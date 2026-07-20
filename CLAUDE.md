# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A proof-of-concept that fine-tunes a small open-weight LLM (QLoRA) and adds RAG, then serves a
Gradio UI comparing three variants of the same base model side by side (Standard / Standard+Docs /
Specialized). It runs entirely in Google Colab and persists artifacts to Google Drive. See
`README.md` for the user-facing overview and `docs/how_it_works.md` for the stage-by-stage narrative.

## The whole application is one notebook

`notebook.ipynb` is the entire codebase — a single self-contained file with **8 sequential stages
(0–7)** plus an optional GGUF export. There are no local module imports and no helper scripts. All
tunable values live in one **constants block at the top of Stage 0**; downstream cells reference them
by name. Read the notebook top-to-bottom to understand the system; nothing is hidden in other files.

> **Optional decomposition (constitution v1.2.0, §I).** The single-notebook layout above is still
> the current shape, but the constitution now *permits* splitting into at most four phase notebooks
> (build-RAG-index, fine-tune, compare/serve, optional GGUF export) that hand off **only** through
> Drive artifacts, plus **exactly one** shared config module (the sole permitted cross-notebook
> import). If you split, the Stage 0 constants block becomes that shared module. Do not introduce any
> other helper scripts or cross-notebook imports.

The three inference functions are the heart of it, defined in Stage 6 and wired to Gradio in Stage 7:
`infer_base` (Standard panel), `infer_rag_only` (base + RAG, Standard+Docs panel), and
`infer_specialized` (base + LoRA adapter + RAG, Specialized panel).

## There is no build / test / lint toolchain — and that is intentional

- **No `package.json`, `requirements.txt`, `pytest`, or CI.** Dependencies are pinned *inside the
  notebook* as `PINNED_REQS` in the Stage 0 bootstrap cell — that list is the single source of truth
  for versions. Do not add a separate requirements file; edit `PINNED_REQS`.
- **"Running" means Colab.** The notebook needs a CUDA GPU (A100 preferred). The intended flow is
  *Runtime → Run all* in Colab, not local execution.
- **"Testing" is manual.** Each stage is a checkpoint verified by eye; the authoritative validation
  procedure (expected outputs, smoke tests, troubleshooting) is
  `specs/001-domain-ai-poc/quickstart.md`. There is no automated test to run.
- **Inputs and outputs are gitignored** (`training_dataset.jsonl`, `domain_docs/`, `lora_adapter/`,
  `chroma_index/`, `gguf_export/`). Never commit real training data or model weights. `data/` holds
  only *format templates*, not domain data.

## Invariants you must not break

These cross-cut the whole notebook and come from the project constitution
(`.specify/memory/constitution.md`, currently v1.2.0). Any change that conflicts must be revised or
recorded as an amendment.

- **Fair Comparison (§IV).** All three panels MUST share the same base model, the same 4-bit (NF4)
  quantization, the same `SYSTEM_PROMPT`, and the same generation params (`TEMPERATURE`, `TOP_P`,
  `MAX_NEW_TOKENS`, `REPETITION_PENALTY`, `ENABLE_THINKING=False`). The *only* permitted differences
  between panels are (a) the LoRA adapter and (b) the retrieved context. If you touch any
  inference/generation code, preserve this — it is the entire point of the POC.
- **T4 degradability (§III).** The notebook auto-detects GPU VRAM and, below 24 GB, swaps `MODEL_ID`
  and the LoRA/training hyperparameters to a smaller fallback config. The default config MUST fit a
  16 GB T4. Any config change must keep *both* the A100 path and the T4 fallback path valid.
- **Cost & simplicity (§I, §II).** Free open-weight models and free OSS only — no paid APIs, no
  Docker/K8s, no hosted DB, no orchestration frameworks, no frontend frameworks (Gradio only),
  in-process ChromaDB only. Keep it a single notebook **or** the bounded split §I now permits (≤4
  phase notebooks handing off only via Drive artifacts + one shared config module) — nothing more
  elaborate.
- **Record deviations.** Any departure from the constitution or the risk-first build order must be
  noted in a `## Deviations` section at the top of the notebook with a one-line justification (there
  is already a real example — the Stage 0 Drive-mount hoist). Silent deviations are not allowed.

## Reproducibility & resumability mechanics

- All artifacts persist under `MyDrive/domain-llm-poc/` (`DRIVE_BASE`). A Colab disconnect must never
  destroy work.
- `artifact_gate()` (defined in the Stage 0 bootstrap) drives **skip / rebuild** behavior for the
  expensive stages (RAG index in Stage 4, LoRA adapter in Stage 5) so re-runs reuse existing Drive
  artifacts. `UNATTENDED_DEFAULT` (`None` → interactive prompt, `"skip"`, or `"rebuild"`) controls
  whether it prompts or answers automatically.
- Dependencies are cached to Drive as a wheelhouse (`deps_cache/`), keyed by a runtime fingerprint
  (Python + CUDA version) and a manifest hash of `PINNED_REQS`, so a warm run installs offline.
- A fixed `SEED = 42` is applied across Python, NumPy, and PyTorch.

## How work is done here: spec-driven development (speckit)

This repo is developed with **speckit**. Features are specified before they are implemented, each in
its own `specs/NNN-name/` directory (`spec.md`, `plan.md`, `research.md`, `data-model.md`,
`quickstart.md`, `contracts/`, `checklists/`, `tasks.md`). Three features exist: `001-domain-ai-poc`
(the core POC), `002-drive-sync-prompts` (the skip/rebuild gates), and `003-pip-cache-drive` (the
dependency wheelhouse). The currently active feature is tracked in `.specify/feature.json`.

When adding or changing functionality, prefer the speckit skills (`speckit-specify`, `speckit-clarify`,
`speckit-plan`, `speckit-tasks`, `speckit-implement`, `speckit-analyze`) rather than editing the
notebook ad hoc, and pass the **Constitution Check** gate in `plan.md` before implementing. Amend the
constitution only via `speckit-constitution` (it keeps `.specify/templates/` in sync and bumps the
version). Constraint-encoding templates live in `.specify/templates/`.
