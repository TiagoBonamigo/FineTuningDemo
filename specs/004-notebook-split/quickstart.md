# Quickstart: Validating the Notebook Split

Manual validation (Colab, per §Evaluation Standard). Each scenario maps to spec user stories / success
criteria. Run notebooks from a fresh runtime unless stated. See contracts/ for the exact I/O and pins.

## Prerequisites

- Google Colab Pro+ (A100 preferred; a T4 exercises the fallback path).
- The repo reachable for `git clone` in cell 1 (public, or a token cell / raw-download fallback — D2).
- `domain_docs/` and `training_dataset.jsonl` available to upload for the build phases.
- A clean `DRIVE_BASE` (or a known state) so skip/rebuild and drift behavior are observable.

## Scenario A — Build index in isolation (US1-AS1, SC-001)

1. Fresh runtime. Open `01_build_index.ipynb`, upload `domain_docs/`, Run all.
2. Expect: `chroma_index/` + `chroma_index/meta.json` on Drive; chunk count printed.
3. **Verify the isolation**: `pip list` shows **no** `unsloth`/`transformers`/`trl`/`gradio` installed.

## Scenario B — Fine-tune in isolation (US1-AS2, SC-001/SC-006)

1. Fresh runtime. Open `02_finetune.ipynb`, upload `training_dataset.jsonl`, Run all.
2. Expect: `lora_adapter/` + `lora_adapter/meta.json`; training loss printed.
3. **Verify the isolation**: `pip list` shows **no** `chromadb`/`sentence-transformers`/`gradio`; the
   install completes with no pip dependency-conflict error (SC-006).

## Scenario C — Serve by reusing both artifacts (US2, SC-002)

1. Fresh runtime, with `chroma_index/` and `lora_adapter/` already on Drive. Open
   `03_compare_serve.ipynb`, Run all.
2. Expect: no training or index build runs; a Gradio share link with three panels (Standard /
   Standard+Docs / Specialized) answering the same question side by side.
3. **Verify §IV**: the three panels use identical generation params (all sourced from `config`);
   `vllm` is not installed.

## Scenario D — Full reproduction in order (US3, SC-003/SC-004)

1. From empty artifacts: run A → B → C in sequence (fresh runtime each).
2. Expect: the three-panel demo matches `notebook.ipynb`'s output on the demo question set (parity
   check against the retained monolith) — no functional regression (FR-008).

## Scenario E — Missing upstream artifact fails fast (US1-AS3, FR-007)

1. Fresh Drive (no `lora_adapter/`). Run `03_compare_serve.ipynb`.
2. Expect: a clear halt — "run 02_finetune first" — not a cryptic load error or empty output.

## Scenario F — Config/artifact drift fails fast (FR-013, SC-007)

1. With a valid `lora_adapter/` built for the current base, change the base model in `config.py`
   (e.g. force the T4 fallback profile or edit `MODEL_ID`), then run `03_compare_serve.ipynb`.
2. Expect: `verify_meta` raises, naming `base_model_id` drift and telling you to re-run `02_finetune`
   — the mismatched adapter is never served.

## Scenario G — Single source of truth (FR-011, SC-005)

1. Change one shared constant in `config.py` (e.g. `TEMPERATURE`).
2. Re-run `03_compare_serve.ipynb`. Expect: all three panels reflect the new value; the value exists
   in exactly one place (grep the notebooks — no re-declared `TEMPERATURE`).

## Scenario H — Per-phase wheelhouse, no collision (FR-009, D6)

1. Run A then B on a warm Drive. Expect: each installs from its **own**
   `deps_cache/{fingerprint}/{manifest8}/` slot; running B does not invalidate A's slot; a second run
   of A installs offline (`--no-index`).

## Scenario I — Optional GGUF export (Q2 in-scope, FR-001)

1. With `lora_adapter/` present, run `04_export_gguf.ipynb`.
2. Expect: `gguf_export/` produced; adapter sidecar verified against `config.MODEL_ID` first.

## Regression checks

- Feature 002 skip/rebuild prompts still work per notebook (`UNATTENDED_DEFAULT`).
- Feature 003 warm/cold/fallback behavior still works per manifest slot.
- T4 fallback: on a T4 runtime, fine-tune + serve resolve the fallback profile and fit 16 GB (§III).

## Pass criteria

- Scenarios A–I behave as described; the two build notebooks install with no conflict (SC-006);
  serve/full-run output matches the monolith (SC-004); drift and missing-artifact cases fail fast;
  every shared constant lives in exactly one place. Only then remove `notebook.ipynb` (Decision 8).
