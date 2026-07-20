# Implementation Plan: Notebook Split (Phase Notebooks)

**Branch**: `004-notebook-split` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-notebook-split/spec.md`

## Summary

Decompose the monolithic `notebook.ipynb` (Stages 0–7 + optional GGUF export) into the bounded set of
**four phase notebooks** permitted by constitution v1.2.0, plus **one shared `config.py`**:

- `01_build_index.ipynb` — chunk + embed `domain_docs/`, build the vector store → `chroma_index/`.
- `02_finetune.ipynb` — load the base model, QLoRA-train → `lora_adapter/`.
- `03_compare_serve.ipynb` — reload base + adapter + RAG, serve the three-panel Gradio demo.
- `04_export_gguf.ipynb` *(optional)* — merge + export → `gguf_export/`.

Phases hand off **only through Drive artifacts** (no shared in-memory state), and every shared
constant lives in a single version-controlled `config.py` fetched onto each runtime and imported
(FR-003). Each notebook pins **only its phase's minimal dependency subset** in its first cell (FR-004,
§III) — which is what isolates the transformers-v5 fine-tuning stack from the RAG embedding/vector
stack. Build phases **stamp a metadata sidecar** next to each artifact; consuming notebooks verify it
against the current config and **fail fast on drift** (FR-013). The existing skip/rebuild gate
(Feature 002) and the Drive wheelhouse (Feature 003) are preserved by moving their helpers into
`config.py` and **partitioning the wheelhouse per dependency manifest** so the four notebooks don't
clobber each other's cache.

This feature is **structural**: `03_compare_serve.ipynb` still co-locates the full stack, and it
adopts the corrected pin set (transformers≥5.2, sentence-transformers≥5.2, chromadb≥1.0, gradio≥5,
pillow<12, no vLLM) so all three panels load together; validating that resolution is a prerequisite
for SC-004 but the pins themselves are recorded here as each notebook's `PINNED_REQS`.

## Technical Context

**Language/Version**: Python 3.10+ (Google Colab default). Notebooks are Jupyter/Colab `.ipynb`; the
shared module is a plain `config.py`.

**Primary Dependencies**: **No new libraries introduced by the split itself.** The existing stack is
re-partitioned across notebooks (RAG: `sentence-transformers`, `chromadb`, `langchain-text-splitters`,
`pypdf`; fine-tune: `unsloth`, `unsloth_zoo`, `transformers`, `trl`, `peft`, `bitsandbytes`,
`datasets`; serve: fine-tune-minus-`trl`/`datasets` + RAG + `gradio` + `pillow`; export: `unsloth` +
`peft` + llama.cpp tooling). `config.py` uses stdlib only (`os`, `sys`, `subprocess`, `hashlib`,
`json`, `shutil`, `random`) plus `google.colab.drive` and, in the model-loading notebooks, `torch`
(for GPU detection). The serve notebook adopts the corrected pins from the dependency-conflict
analysis.

**Storage**: Google Drive under `DRIVE_BASE` — unchanged artifact locations (`chroma_index/`,
`lora_adapter/`, `training_dataset.jsonl`, `gguf_export/`, `deps_cache/`) plus a small
`meta.json` sidecar written inside `chroma_index/` and `lora_adapter/`. The wheelhouse is
re-keyed to `deps_cache/{fingerprint}/{manifest8}/wheels/` so each phase gets its own slot.

**Testing**: Manual, per `quickstart.md`; no automated framework (§Evaluation Standard — qualitative).
Each notebook is validated by running it top-to-bottom on a fresh Colab runtime.

**Target Platform**: Google Colab Pro+ (A100 preferred; L4/T4 fallback per §III). Each notebook runs
in its own session.

**Performance Goals**: No per-phase regression vs. the monolith; the split reduces install time and
conflict risk for the two build notebooks (SC-006). Warm wheelhouse still installs offline (Feature
003 preserved per-notebook).

**Constraints**: ≤4 notebooks + exactly one shared module (§I); Drive-artifact-only handoff (FR-002);
no shared constant re-declared per notebook (FR-011); no new helper scripts or cross-notebook imports
beyond `config.py` (FR-012); T4 default must still fit 16 GB (FR-010, §III); all three panels + shared
params in the serve notebook (FR-005, §IV).

**Scale/Scope**: One POC pipeline, four notebooks, one shared module. Multi-GB per-phase wheelhouses
are expected; housekeeping of stale cache slots is out of scope (as in Feature 003).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle / Constraint | Gate criterion | Status |
|---|---|---|
| §I Simplicity First | ≤4 phase notebooks + one shared `config.py`; Drive-artifact handoff; whole set still readable in <1 h | ⚠️ Pass (config.py absorbs shared setup helpers — see Complexity Tracking) |
| §I / §Notebook Decomposition | Exactly the four permitted notebooks; the ONLY cross-notebook import is `config.py`; no other helper scripts | ✅ Pass |
| §II Cost Mandate | No new libraries, no paid service; same OSS stack re-partitioned | ✅ Pass |
| §III Reproducibility | Each notebook pins its own minimal subset in cell 1; Features 002/003 preserved per-notebook; `config.py` version-controlled | ⚠️ Pass (wheelhouse re-keyed per manifest — see Complexity Tracking) |
| §III T4 degradability | `config.select_profile()` applies the T4 swap in each model-loading notebook; default fits 16 GB | ✅ Pass |
| §IV Fair Comparison | All three panels live only in `03_compare_serve.ipynb`; every shared param imported from `config.py`, never re-declared (FR-005/FR-011) | ✅ Pass (drift-proofed) |
| Model / Fine-tuning / RAG stack | Same models and stack; only the environment is partitioned per phase | ✅ Pass |
| Interface | Gradio three-panel UI unchanged, moved wholesale to the serve notebook | ✅ Pass |
| Prohibited list | No paid APIs, Docker, K8s, hosted DB, or React/Vue; vLLM explicitly excluded from serve | ✅ Pass |
| §Governance (Build Order / Deviations) | Phase-notebook layout supersedes the single-notebook risk-first stage order → MUST be recorded in a Deviations note in each notebook | ⚠️ Requires Deviations note |

**Gates pass with three flags** (all justified below): `config.py` holds the shared setup helpers
(not just constants); the Feature-003 wheelhouse is re-keyed per manifest to avoid cross-notebook
collision; and the move from stage-order to phase-notebook layout is a Build-Order deviation that MUST
be recorded per §Governance.

## Project Structure

### Documentation (this feature)

```text
specs/004-notebook-split/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── config-module.md #   config.py public API contract
│   └── notebook-io.md    #   per-notebook inputs/outputs + sidecar + PINNED_REQS
├── checklists/
│   └── requirements.md  # From /speckit-specify + /speckit-clarify
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
config.py                     # NEW — single shared module: constants + profile + setup helpers + sidecar
01_build_index.ipynb          # NEW — from Stage 4 (+ bootstrap, seed, sidecar write)
02_finetune.ipynb             # NEW — from Stages 2 + 5 (+ bootstrap, profile, sidecar write)
03_compare_serve.ipynb        # NEW — from Stages 6 + 7 (+ bootstrap, sidecar verify); the ONLY full-stack notebook
04_export_gguf.ipynb          # NEW — from the optional GGUF cell (+ bootstrap, sidecar verify)
notebook.ipynb                # REMOVED once the four notebooks reproduce it (kept until parity confirmed)
```

**Structure Decision**: Four phase notebooks + one `config.py`, per constitution v1.2.0
§Notebook Decomposition. The current `notebook.ipynb` maps cleanly because **Stage 6 already reloads
the entire serving pipeline from Drive artifacts** with zero reliance on in-memory state from earlier
stages — so the artifact boundaries at Stages 4/5/6 become the notebook boundaries. Cell 1 of each
notebook is a thin bootstrap: fetch the repo (so `config.py` is present), `import config`, mount
Drive, define this phase's `PINNED_REQS`, and `config.install_deps(PINNED_REQS)`. The former Stage 3
"walking skeleton" UI is dropped (superseded by the serve notebook). `notebook.ipynb` is retained
until the four notebooks demonstrably reproduce it (FR-008), then removed.

## Complexity Tracking

> Three Constitution Check flags are justified here.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `config.py` holds shared setup helpers (`mount_drive`, `artifact_gate`, `install_deps`, sidecar read/write, `select_profile`), not only constants | Four notebooks each need the identical mount / gate / wheelhouse / drift logic; consolidating it in the one permitted module keeps it DRY and drift-free | Duplicating ~80 lines of bootstrap across four notebooks maximizes moving parts and drift risk — the opposite of §I. A second helper module is forbidden (§Notebook Decomposition allows exactly one). Putting the shared mechanism in the single allowed module is the fewest-moving-parts option. Helpers are stdlib-only and lightweight at import, so `config` imports cleanly before any pip install. |
| Feature 003 wheelhouse re-keyed to `deps_cache/{fingerprint}/{manifest8}/` | Four notebooks now have four different `PINNED_REQS` → four manifests; a single shared slot would thrash (each run rebuilds on a different manifest) | Keeping Feature 003's single slot causes constant cache invalidation across notebooks (the "independent caches must not collide" edge case). Partitioning by manifest hash is a minimal keying change that preserves every 002/003 guarantee per-notebook. |
| Phase-notebook layout replaces the single-notebook risk-first stage order | The split is the entire point of the feature (modularity + conflict isolation), sanctioned by constitution v1.2.0 | Not splitting leaves the transformers-v5 vs. RAG-stack conflict unmitigated in build phases and blocks artifact reuse. Recorded as a Deviations note per §Governance rather than avoided. |

---

## Post-Phase 1 Constitution Re-check

After Phase 1 design (see research.md, data-model.md, contracts/, quickstart.md):

| Area | Design decision | Compliance |
|---|---|---|
| One shared module | `config.py` is the sole cross-notebook import; constants never re-declared per notebook (contract: config-module.md) | §I, FR-003/FR-011 ✅ |
| Handoff | Only `chroma_index/`, `lora_adapter/`, `training_dataset.jsonl`, `gguf_export/` cross phases; no in-memory sharing | FR-002 ✅ |
| Minimal deps | Four distinct `PINNED_REQS` lists (notebook-io.md); build notebooks exclude the other stack | §III, FR-004, SC-006 ✅ |
| Fair comparison | All three panels + all generation params sourced from `config` in the serve notebook only | §IV, FR-005 ✅ |
| Drift safety | `meta.json` sidecar written at build, verified at consume; fail-fast on mismatch/missing | FR-007/FR-013, SC-007 ✅ |
| Reproducibility | 002 gate + 003 wheelhouse preserved via `config` helpers; wheelhouse partitioned per manifest | §III, FR-009 ✅ |
| T4 degradability | `config.select_profile(vram)` applied in fine-tune + serve + export notebooks | §III, FR-010 ✅ |
| Deviations | Each notebook carries a `## Deviations` note citing feature 004 + constitution v1.2.0 | §Governance ✅ |

**Result**: Gates hold post-design. The three flags are documented deviations/justifications, not
violations. Ready for `/speckit-tasks`.
