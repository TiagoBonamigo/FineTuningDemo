# Feature Specification: Notebook Split (Phase Notebooks)

**Feature Branch**: `004-notebook-split`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Decompose the single `notebook.ipynb` into the bounded set of phase
notebooks now permitted by constitution v1.2.0 (§I, §Notebook Decomposition), to enable
modularity/reuse of the RAG index and adapter and to isolate dependency conflicts by giving each
build phase a minimal environment. Phases hand off only through Google Drive artifacts and share
exactly one config module."

## Clarifications

### Session 2026-07-20

- Q: How is the single shared config module delivered to each notebook and imported in Colab?
  → A: A version-controlled `config.py` in the repository; each notebook's first cell fetches the
  repo onto the runtime (git clone or raw download) and imports it as a module. It is not hosted
  only on Drive (avoids stale, unversioned copies).
- Q: Is the optional GGUF export in scope for this feature (004)?
  → A: Yes — included now as the optional fourth notebook, extracted from the existing export cell,
  so the capability is not orphaned while the monolith is dismantled.
- Q: How rigorously must the serve notebook surface a config/artifact mismatch?
  → A: Each build phase stamps a small metadata sidecar (base model id + key config) beside its
  artifact; the consuming notebook verifies it against the current config and fails fast on mismatch.
- Q: How is "no regression vs. the monolith" (FR-008/SC-004) verified given sampled decoding and the
  transformers 4.x→5.2 change? → A: Parity is qualitative (cross-panel quality ordering + factual
  grounding on the demo set), not token equality; the baseline is the monolith on a config it can
  actually run (T4-fallback model), or the first validated split run if none is runnable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run one phase in isolation with only its dependencies (Priority: P1)

A team member wants to (re)build just one part of the pipeline — the RAG index, or the fine-tuned
adapter — without loading, installing, or running the other parts. They open the notebook for that
phase in a fresh Colab session, and it installs only the dependencies that phase needs and produces
that phase's Drive artifact.

**Why this priority**: This is the core value of the split. It is what makes each build environment
small enough to avoid the cross-stack version conflicts (e.g. transformers v5 for fine-tuning vs. the
RAG embedding/vector stack) and what lets the index or adapter be rebuilt independently. Without it,
the split delivers nothing the single notebook didn't.

**Independent Test**: On a fresh runtime with only `domain_docs/` present on Drive, run the
build-RAG-index notebook top-to-bottom. Verify `chroma_index/` is written to Drive and that none of
the fine-tuning or UI dependencies were installed. Repeat analogously for the fine-tune notebook with
only `training_dataset.jsonl` present.

**Acceptance Scenarios**:

1. **Given** a fresh Colab session with only `domain_docs/` on Drive, **When** the build-RAG-index
   notebook is run top-to-bottom, **Then** `chroma_index/` is produced on Drive and the installed
   environment contains no fine-tuning or Gradio packages.
2. **Given** a fresh Colab session with only `training_dataset.jsonl` on Drive, **When** the
   fine-tune notebook is run top-to-bottom, **Then** `lora_adapter/` is produced on Drive and the
   installed environment contains no vector-store or Gradio packages.
3. **Given** a phase notebook whose required input artifact is absent, **When** it is run, **Then**
   it stops with a clear message naming the prior phase to run first, rather than producing an
   empty or incorrect artifact.

---

### User Story 2 - Reuse existing artifacts to launch the demo without rebuilding (Priority: P2)

A team member who already has a trained adapter and a built index wants the four-panel comparison
demo. They open only the compare/serve notebook, which reloads both artifacts from Drive and serves
the Gradio UI — no retraining, no reindexing.

**Why this priority**: Reuse is the second half of the modularity goal and the most common day-to-day
action (demoing). It depends on P1's artifacts existing but is independently valuable and testable.

**Independent Test**: With `lora_adapter/` and `chroma_index/` already on Drive, run only the
compare/serve notebook. Verify all four panels (Standard / Standard+Docs / Specialized (No RAG) /
Specialized (RAG)) load and answer a demo question, with no training or embedding-build step executed.

**Acceptance Scenarios**:

1. **Given** `lora_adapter/` and `chroma_index/` present on Drive, **When** the compare/serve
   notebook is run, **Then** a single Gradio link serves all four panels answering the same
   question side by side, and no training or index-build runs.
2. **Given** the compare/serve notebook, **When** a shared parameter (e.g. temperature) is inspected
   across all panels, **Then** all four use the identical value sourced from the shared config
   module.

---

### User Story 3 - Reproduce the full experiment by running the phases in order (Priority: P3)

A newcomer with only the raw inputs reproduces the entire POC by running the phase notebooks in
sequence (build-index → fine-tune → compare/serve), and obtains a demo equivalent to the original
single-notebook result.

**Why this priority**: End-to-end reproducibility is a constitution requirement (§III, Definition of
Done). It is the integration of P1 and P2; valuable but exercised less often than either alone.

**Independent Test**: Starting from an empty Drive artifact folder (only raw `domain_docs/` and
`training_dataset.jsonl` supplied), run the three notebooks in order and confirm the final four-panel
demo behaves equivalently to the pre-split single notebook on the demo question set.

**Acceptance Scenarios**:

1. **Given** only the raw inputs on Drive, **When** the three notebooks are run in order, each
   top-to-bottom, **Then** the full experiment completes with no manual step beyond supplying the
   inputs, and the demo output matches the pre-split baseline behavior.

---

### Edge Cases

- **Missing upstream artifact**: A phase is run before its input exists (serve before the adapter or
  index; fine-tune before the dataset). The notebook MUST fail fast with an actionable message, never
  silently continue on empty/absent data.
- **Config drift across artifacts**: A shared constant that affects an artifact (e.g. `MODEL_ID`) is
  changed after that artifact was built, so a stored adapter no longer matches the configured base
  model. The build phase stamps a metadata sidecar beside the artifact; the consuming notebook
  compares it to the current config and halts with a clear message on mismatch (see FR-013), rather
  than loading an incompatible pairing.
- **Independent dependency caches**: Each notebook keys its own dependency wheelhouse on Drive; the
  caches for different phases MUST NOT collide or invalidate each other.
- **Shared-config edit visibility**: Editing the shared config module MUST take effect in every
  notebook on its next run, with no per-notebook duplicate to update.
- **Partial adoption**: Anything beyond the bounded ≤4-notebook layout (extra helper scripts, ad-hoc
  cross-notebook imports) is out of scope and disallowed by §I.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The codebase MUST be organized as at most four phase notebooks — build-RAG-index,
  fine-tune, compare/serve, and an optional GGUF export — each independently runnable in its own
  Colab session.
- **FR-002**: Phase notebooks MUST exchange state ONLY through Google Drive artifacts
  (`chroma_index/`, `lora_adapter/`, `training_dataset.jsonl`, `gguf_export/`). No notebook may
  depend on another notebook's in-memory state.
- **FR-003**: Exactly one shared configuration module MUST hold every shared constant (base model id,
  seed, sequence length, generation parameters, system prompt, prompt scaffolding, Drive paths) and
  MUST be the only cross-notebook import; each phase notebook imports it rather than redeclaring
  constants. The module MUST be a single version-controlled `config.py` in the repository; each
  notebook's first cell MUST fetch it onto the Colab runtime (e.g. git clone or raw download) and
  import it. It MUST NOT be hosted only on Drive, so the config always travels with the code in
  version control.
- **FR-004**: Each notebook MUST pin, in its first cell, only the minimal dependency subset its phase
  requires (build-index: embeddings + vector store + splitter; fine-tune: training stack;
  compare/serve: full stack; export: export tooling).
- **FR-005**: The compare/serve notebook MUST contain all four inference panels (Standard /
  Standard+Docs / Specialized (No RAG) / Specialized (RAG)) and MUST source every fair-comparison
  parameter (base model, quantization, generation params, system prompt) from the shared config
  module (§IV).
- **FR-006**: Each notebook MUST run top-to-bottom on a fresh Colab session with no manual
  intervention beyond supplying the raw inputs its own phase consumes.
- **FR-007**: When a required input artifact is missing, a notebook MUST halt with a clear, actionable
  message identifying which prior phase to run, and MUST NOT proceed on empty or incorrect data.
- **FR-008**: Running the notebooks in order (build-index → fine-tune → compare/serve) MUST preserve
  the **qualitative** panel behavior of the baseline pipeline on the demo question set — the
  cross-panel quality ordering (Specialized (RAG) ≥ Standard+Docs ≥ Standard, and Specialized (RAG) ≥
  Specialized (No RAG) ≥ Standard; Standard+Docs and Specialized (No RAG) are not ordered against each
  other, since each isolates a different lever) and the factual grounding of the RAG/specialized
  answers in the domain docs. Token-level output equality is NOT required and NOT
  expected, because decoding is sampled and the split intentionally moves to transformers v5. The
  **baseline** is the pre-split notebook run on a configuration it can actually execute (the
  T4-fallback model if the primary model's monolith pins do not resolve); if no runnable monolith
  baseline exists, the first validated split run is recorded as the reference.
- **FR-009**: The existing skip/rebuild gates (`artifact_gate`, feature 002) and the dependency
  wheelhouse cache (feature 003) MUST continue to work on a per-notebook basis.
- **FR-010**: The default configuration MUST still fit a 16 GB T4, and each notebook MUST honor the
  T4 fallback config swap (§III degradability).
- **FR-011**: No shared constant may be re-declared inside an individual notebook; the shared config
  module MUST be the single source of truth, so editing one value updates every notebook (drift
  prevention).
- **FR-012**: The split MUST NOT introduce any new helper scripts, additional cross-notebook imports
  beyond the shared config module, or other new moving parts (§I bound).
- **FR-013**: When a phase produces an artifact (`lora_adapter/`, `chroma_index/`), it MUST also
  write a small metadata sidecar recording the base model id and the config values that artifact
  depends on. A consuming notebook MUST verify the sidecar against the current shared config and
  fail fast with an actionable message on mismatch (e.g. an adapter trained on a different base
  model than is now configured), rather than loading an incompatible pairing.

### Key Entities

- **Phase notebook**: A self-contained Colab notebook responsible for exactly one pipeline phase,
  runnable top-to-bottom in isolation, consuming and producing Drive artifacts.
- **Shared config module**: A single version-controlled `config.py` in the repository holding all
  shared constants; the only permitted cross-notebook import, fetched onto each runtime and imported.
- **Drive artifact**: A persisted handoff object between phases — `chroma_index/` (RAG index),
  `lora_adapter/` (trained adapter), `training_dataset.jsonl` (training data), `gguf_export/`
  (optional local-inference export), plus the `deps_cache/` wheelhouse.
- **Artifact metadata sidecar**: A small record written beside a built artifact capturing the base
  model id and config values it depends on, used by consuming notebooks to detect config drift.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The RAG index can be produced by running only the build-index notebook, whose
  environment installs none of the fine-tuning or UI dependencies.
- **SC-002**: A person holding an existing adapter and index can launch the full four-panel demo by
  running only the compare/serve notebook, with zero retraining or reindexing steps executed.
- **SC-003**: Full reproduction requires running exactly three notebooks in order (four with the
  optional export), each top-to-bottom, with no manual step beyond supplying the raw inputs.
- **SC-004**: For the 5–10 question demo set, the split pipeline preserves the cross-panel quality
  ordering (Specialized (RAG) ≥ Standard+Docs ≥ Standard, and Specialized (RAG) ≥ Specialized (No
  RAG) ≥ Standard) and factual grounding shown by the baseline, judged qualitatively side by side.
  Token-identical output is not required (sampled decoding + transformers v5).
- **SC-005**: Changing any shared constant requires editing exactly one location and takes effect in
  every notebook on its next run.
- **SC-006**: The build-index and fine-tune notebooks each resolve their pinned dependencies with no
  version-conflict errors during install (the isolation goal), whereas co-locating the full stack in
  one environment previously surfaced such conflicts.
- **SC-007**: Changing the base model in the shared config and then running the compare/serve
  notebook against an adapter built for the previous base model produces a clear fail-fast error
  identifying the mismatch, not a silent or cryptic failure.

## Assumptions

- The split targets exactly the constitution v1.2.0 layout (≤4 phase notebooks + one shared config
  module). Adoption is all-or-nothing to that layout; no partial/ad-hoc splitting.
- Google Drive remains the artifact-exchange medium (already the project standard; `DRIVE_BASE`).
- The compare/serve notebook still needs the full stack to coexist in one environment. Resolving that
  environment's dependency conflicts (the transformers-v5 / RAG / Gradio pin set, and excluding vLLM)
  is tracked separately and is a prerequisite for SC-004, not part of this structural feature.
- The existing skip/rebuild gates (feature 002) and the dependency wheelhouse (feature 003) are
  reused unchanged, applied per notebook.
- Model choices (Qwen3.5-9B primary, Qwen3-4B T4 fallback) are unchanged by this feature.
- The optional GGUF export is IN scope for this feature as the optional fourth notebook, extracted
  from the existing export cell; it is not required for the core three-notebook reproduction, but is
  delivered so the capability is not orphaned when the monolith is dismantled.
- The former Stage 3 "walking skeleton" UI is superseded by the compare/serve notebook and need not
  survive as a separate step.
