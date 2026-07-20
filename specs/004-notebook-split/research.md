# Phase 0 Research: Notebook Split (Phase Notebooks)

Resolves the design unknowns for decomposing `notebook.ipynb` into four phase notebooks + one shared
`config.py`. Each decision records what was chosen, why, and the alternatives rejected.

## Decision 1: Notebook boundaries (stage → notebook mapping)

**Decision**: Cut at the Drive-artifact boundaries the monolith already has.

| Notebook | From current stages | Produces |
|---|---|---|
| `01_build_index.ipynb` | Stage 4 (RAG) | `chroma_index/` |
| `02_finetune.ipynb` | Stage 2 (base load) + Stage 5 (train) | `lora_adapter/` |
| `03_compare_serve.ipynb` | Stage 6 (reload) + Stage 7 (UI) | Gradio link |
| `04_export_gguf.ipynb` | optional GGUF cell | `gguf_export/` |

**Rationale**: Stage 6 already calls `FastLanguageModel.from_pretrained(MODEL_ID)`, attaches the
adapter from `lora_adapter/`, and reconnects Chroma from `chroma_index/` — i.e. it rebuilds the whole
serving pipeline from Drive with **no** dependence on Stages 2–5 in-memory objects. The monolith is
therefore already artifact-decoupled at exactly these seams.

**Alternatives considered**: (a) Split base-load (Stage 2) into its own notebook — rejected: the base
model is only an input to training and serving, not a reusable artifact, and reloading it is cheap
relative to a notebook boundary. (b) Keep Stage 3 walking-skeleton as a notebook — rejected: it is a
dev-time smoke test superseded by the serve notebook (see Decision 8).

## Decision 2: `config.py` delivery & import mechanism

**Decision**: `config.py` is committed to the repo. Cell 1 of each notebook fetches the repo onto the
Colab runtime and imports it: `!git clone --depth 1 <repo>` (or `git -C <dir> pull` if present), then
`sys.path.insert(0, <repo dir>)` and `import config`. A `raw`-download of just `config.py` is the
documented fallback.

**Rationale**: Matches the clarify decision (version-controlled, not Drive-hosted) so the config always
travels with the code. Git clone also brings the notebooks themselves, enabling "open from GitHub in
Colab → Run all". Import (not `%run`) gives an explicit `config.X` namespace, making FR-011 (no
re-declared constants) auditable.

**Alternatives considered**: Drive-hosted `config.py` (rejected by clarify — stale/unversioned risk);
`%run config.py` injecting globals (rejected: implicit namespace, harder to prove single-source-of-
truth). **Caveat**: a private repo needs an auth token for `git clone` in Colab; documented in
quickstart as a one-line token cell or the raw-download fallback.

## Decision 3: `config.py` scope — constants **and** shared setup helpers

**Decision**: `config.py` holds (a) all constants, (b) `select_profile(vram_gb)` for the T4 swap,
(c) `set_seeds()`, (d) `mount_drive()`, (e) `artifact_gate()` (Feature 002), (f) `install_deps(reqs)`
(Feature 003 wheelhouse), and (g) sidecar helpers `write_meta()` / `verify_meta()`.

**Rationale**: All four notebooks need the identical mount/gate/wheelhouse/drift mechanism.
Constitution §Notebook Decomposition permits **exactly one** shared module and forbids additional
helper scripts, so the shared mechanism must live in that one module. All helpers are stdlib-only and
define no heavy state at import time, so `import config` is safe to run *before* the pip install.

**Alternatives considered**: Duplicate the bootstrap in each notebook (rejected: ~80 lines × 4, maximal
drift risk, contradicts §I). A second `utils.py` (rejected: forbidden by §Notebook Decomposition).

## Decision 4: T4 fallback inside `config.py`

**Decision**: `config.py` defines both the A100 defaults and the T4-fallback values, and
`select_profile(vram_gb)` returns the active `MODEL_ID` + LoRA/training/seq-len set (below 24 GB →
fallback). The fine-tune, serve, and export notebooks call it after importing `torch`; the build-index
notebook does not (it never touches `MODEL_ID`).

**Rationale**: Preserves §III degradability with the swap centralized in the single source of truth, so
fine-tune and serve can never disagree on which model/profile is active (which would break §IV).

**Alternatives considered**: Per-notebook duplicated detection (rejected: drift risk — serve could load
a different base than was trained). Environment variable (rejected: extra moving part, not reproducible).

## Decision 5: Artifact metadata sidecar (drift detection, FR-013)

**Decision**: When a build phase writes an artifact, it also writes `meta.json` **inside** the artifact
directory recording the config values that artifact depends on:

- `lora_adapter/meta.json`: `{ base_model_id, max_seq_len, lora_r, lora_alpha, lora_targets, seed }`
- `chroma_index/meta.json`: `{ embed_model, chunk_size, chunk_overlap }`

Consuming notebooks call `config.verify_meta(path, expected_subset)`; on mismatch or missing file they
`raise` with an actionable message naming the offending field and the phase to re-run. `verify_meta`
also covers the missing-artifact case (FR-007) — absent directory → same fail-fast path.

**Rationale**: Cheap (one small JSON), testable (SC-007), and reliably satisfies the spec's "MUST
surface the mismatch". Stored inside the artifact dir so it travels with the artifact and is covered by
the existing Drive persistence.

**Alternatives considered**: Best-effort natural load failure (rejected by clarify — cryptic);
documentation only (rejected by clarify — surfaces nothing at runtime). Hashing full config (rejected:
over-broad — unrelated config changes would false-trip; only artifact-affecting fields are recorded).

## Decision 6: Wheelhouse partitioning (Feature 003 extension)

**Decision**: Re-key the wheelhouse from Feature 003's single `deps_cache/wheels/` slot to
`deps_cache/{fingerprint}/{manifest8}/wheels/`, where `manifest8` is the first 8 hex chars of the
manifest hash of that notebook's `PINNED_REQS`. Sentinels (`manifest.sha256`, `fingerprint.txt`) move
into the same slot.

**Rationale**: Four notebooks → four `PINNED_REQS` → four manifests. A shared slot would rebuild on
every switch between notebooks (the "caches must not collide" edge case). Partitioning is a minimal
keying change that preserves every 002/003 guarantee independently per phase, and lets a phase's warm
cache survive across the other phases' runs.

**Alternatives considered**: One superset `PINNED_REQS` shared by all notebooks (rejected: defeats the
conflict-isolation goal — the build notebooks would install the full conflicting stack). Separate
top-level `deps_cache_<phase>/` dirs (rejected: manifest keying already uniquely identifies a slot and
also dedupes identical req sets).

## Decision 7: Per-notebook `PINNED_REQS`

**Decision**: Each notebook pins only its phase's stack (full detail in contracts/notebook-io.md):

- **build-index**: `sentence-transformers>=5.2`, `chromadb>=1.0`, `langchain-text-splitters>=0.3`,
  `pypdf>=4.0`.
- **fine-tune**: `unsloth`, `unsloth_zoo`, `transformers>=5.2`, `trl>=0.15`, `peft>=0.14`,
  `bitsandbytes>=0.45`, `datasets>=3.0`.
- **compare/serve**: fine-tune stack **minus** `trl`/`datasets` (inference only) **plus**
  `sentence-transformers>=5.2`, `chromadb>=1.0`, `gradio>=5`, `pillow>=10.4,<12`; **exclude vLLM**.
- **export**: `unsloth`, `unsloth_zoo`, `transformers>=5.2`, `peft>=0.14` + llama.cpp tooling.

**Rationale**: This is where the earlier dependency-conflict analysis lands — the corrected pins
(transformers v5 anchor, uncapped RAG libs, gradio 5 + pillow<12, no vLLM) apply in the serve notebook
where the full stack must coexist, while the build notebooks get small, conflict-free environments
(SC-006). Chroma≥1.0 and sentence-transformers≥5.2 are required for transformers-v5 tokenizer/numpy
compatibility.

**Alternatives considered**: Uniform pins across notebooks (rejected: reintroduces the conflict in the
build phases). Pinning exact versions (deferred: the Feature 003 wheelhouse already freezes the
resolved set; floors + wheelhouse give reproducibility without brittle pins).

## Decision 8: Drop the walking skeleton; retire `notebook.ipynb` after parity

**Decision**: The Stage 3 skeleton UI is not carried into any notebook. `notebook.ipynb` is kept in the
repo until the four notebooks demonstrably reproduce its demo output (FR-008), then removed in the same
feature.

**Rationale**: The skeleton exists to smoke-test the base model early in one runtime; that role is
filled by the serve notebook. Keeping the monolith around briefly de-risks the cutover (side-by-side
parity check) without violating the ≤4-notebook rule (it is scheduled for removal, not a fifth phase).

**Alternatives considered**: Delete the monolith immediately (rejected: loses the parity reference for
SC-004). Keep it indefinitely (rejected: two sources of truth, contradicts the split's intent).

## Feasibility caveats (surfaced, not hidden)

- **Private-repo clone in Colab** needs a token; documented with a raw-download fallback (D2).
- **Serve-notebook conflict resolution** is assumed solved by the D7 pins but its end-to-end
  validation (all three panels load together) is the SC-004 prerequisite tracked in the spec's
  Assumptions — this feature records the pins; the install must be confirmed on a real A100 runtime.
- **First-run cost**: partitioned wheelhouses mean each phase builds its own slot once (cold), so the
  very first run of all four notebooks builds up to four caches; warm runs are offline thereafter.
