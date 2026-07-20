# Implementation Plan: Drive-Cached Dependency Install

**Branch**: `003-pip-cache-drive` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-pip-cache-drive/spec.md`

## Summary

Make Stage 0 (Install & Config) reuse a **wheelhouse cached on Google Drive** so a restarted Colab
runtime installs the pinned dependencies from local wheels instead of re-downloading and re-building
them. On a cold run the notebook builds the wheelhouse (`pip wheel`), installs from it, and saves it
to Drive; on a warm run it installs offline from the Drive wheelhouse (`pip install --no-index
--find-links`). The cache is validated against a **manifest hash** (the exact pinned dependency list)
and a **runtime fingerprint** (Python major.minor + CUDA tag); a mismatch auto-rebuilds, and a valid
cache triggers the same skip/rebuild prompt as Feature 002 (`UNATTENDED_DEFAULT` + a
`FORCE_REBUILD_DEPS` flag). Any Drive problem falls back to a normal online install so the notebook
never fails to set up.

## Technical Context

**Language/Version**: Python 3.10+ (Google Colab default)

**Primary Dependencies**: **No new runtime libraries.** Uses `pip` itself (`pip wheel`, `pip install
--no-index --find-links`), `google.colab.drive` (pre-installed in Colab), and the standard library
(`os`, `sys`, `subprocess`, `hashlib`, `json`, `shutil`, `time`). The set of *cached* packages is the
notebook's existing pinned install list — unchanged.

**Storage**: Google Drive wheelhouse at `{DRIVE_BASE}/deps_cache/` — a `wheels/` directory plus two
small sentinel files recording the manifest hash and the runtime fingerprint. Single cache slot
(clarified): a fingerprint or manifest change overwrites it.

**Testing**: Manual cell-by-cell verification in Colab per `quickstart.md`; no automated framework
(constitution §Evaluation Standard — qualitative only).

**Target Platform**: Google Colab Pro+ (T4/L4/A100). The mechanism must degrade gracefully to a
normal install when Drive is absent or the cache is unusable.

**Performance Goals**: Warm-cache Stage 0 ≥3× faster than the cold baseline, target <90 s (SC-001);
zero internet downloads on a warm hit (SC-002); never slower than the cold baseline (SC-005).

**Constraints**: MUST preserve exact pinned versions between warm and cold runs (FR-008, §III/§IV);
detection is manifest-hash + fingerprint based; single cache slot; graceful fallback on any Drive
failure (FR-007). Compiled wheels remain Python+CUDA specific — the fingerprint guards restore.

**Scale/Scope**: One Stage-0 wheelhouse for one project. Multi-GB wheelhouses (torch/CUDA) are
expected; housekeeping of old/alternate caches is out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle / Constraint | Gate criterion | Status |
|---|---|---|
| §I Simplicity First | Standard pip-wheelhouse pattern in one Stage-0 block (~60 lines); no new deps, stdlib only; reuses Feature 002's `artifact_gate` | ⚠️ Pass (most complex part of notebook — see Complexity Tracking) |
| §II Cost Mandate | No new libraries, no paid service; uses pip + Drive only | ✅ Pass |
| §III Reproducibility | Wheelhouse built from the SAME pinned list; fingerprint blocks cross-env restore; fallback keeps top-to-bottom run working; pinned deps stay authoritative | ✅ Pass (strengthens resumability) |
| §IV Fair Comparison | Dependency versions identical on warm vs cold runs (FR-008); no model/generation change | ✅ Pass (untouched) |
| Compute | CPU-side pip + Drive I/O; no extra GPU cost | ✅ Pass |
| Model / Fine-tuning / RAG stack | Untouched — feature is confined to dependency setup | ✅ Pass |
| Interface | No Gradio change | ✅ Pass |
| Prohibited list | No paid APIs, Docker, K8s, hosted DB, or React/Vue | ✅ Pass |
| §Governance (Build Order / Deviations) | Stage 0 stays first, but Drive mount + shared-helper definitions move earlier → MUST be recorded in the notebook Deviations section | ⚠️ Requires Deviations note |

**Gates pass with two flags**: the Stage-0 logic is the notebook's most complex block (justified in
Complexity Tracking), and relocating the Drive mount / shared helpers earlier is a Build-Order
deviation that MUST be recorded in the notebook per §Governance.

## Project Structure

### Documentation (this feature)

```text
specs/003-pip-cache-drive/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── deps-cache.md
├── checklists/
│   └── requirements.md  # From /speckit-specify + /speckit-clarify
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
notebook.ipynb
  ├── Cell 1  (Stage 0 install)  # Add a bootstrap prologue + wheelhouse cache logic (main change)
  └── Cell 3  (Constants)        # Remove the relocated definitions (UNATTENDED_DEFAULT, artifact_gate,
                                 #   DRIVE_BASE) now defined earlier in the Stage 0 bootstrap
```

**Structure Decision**: Single-notebook approach per §I. The core change is a **Stage 0 bootstrap
prologue** placed at the very top of the install cell (Cell 1), because the cache must be consulted
*before* the pip install runs. The bootstrap does the minimum that must exist pre-install:
`import os, sys`; mount Drive (`google.colab.drive`, pre-installed, idempotent); define `DRIVE_BASE`,
the deps-cache constants, `FORCE_REBUILD_DEPS`, and — relocated up from Cell 3 — `UNATTENDED_DEFAULT`
and the `artifact_gate` helper. Relocating these upward lets the new Stage-0 cache gate and the
existing Stage 4/5 gates share one definition (Feature 002 stages run later, so they are unaffected).
Cell 3 keeps everything else and no longer redefines the relocated names, avoiding drift.

## Complexity Tracking

> One Constitution Check flag (§I) is justified here.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Stage 0 becomes the most logic-heavy cell (~60 lines: mount, fingerprint, manifest hash, validity, gate, wheelhouse build/install, save, fallback, report) | The feature's entire value is a correct cache that never compromises reproducibility (FR-008) or a working install (FR-007); those guarantees require the validity + fallback logic | A naive "always restore a Drive folder" is far simpler but violates FR-004/FR-005/FR-008 (stale or cross-env restores) and FR-007 (hard fail when Drive is down). The chosen design is the minimum that satisfies the mandatory requirements, and it reuses `artifact_gate` rather than adding a second prompt path. |

---

## Post-Phase 1 Constitution Re-check

After Phase 1 design:

| Area | Design decision | Compliance |
|---|---|---|
| Wheelhouse mechanism | `pip wheel` (cold) + `pip install --no-index --find-links` (warm); stdlib + pip only | §I/§II ✅ |
| Reproducibility | Same pinned list drives both build and install; manifest hash detects drift | §III ✅, FR-008 ✅ |
| Fingerprint | `py{maj.min}` + CUDA tag only (GPU model/base-image excluded) per clarification | §III ✅, FR-005 ✅ |
| Prompt reuse | Valid cache → `artifact_gate("Dependency cache", …)`; `UNATTENDED_DEFAULT` + `FORCE_REBUILD_DEPS` | §I ✅, FR-009 ✅ |
| Fallback | Any Drive/cache failure → normal online `pip install` | §III ✅, FR-007 ✅ |
| Ordering deviation | Drive mount + shared helpers relocated to Stage 0 bootstrap; Stage 1 mount stays (idempotent) | §Governance ⚠️ → recorded in notebook Deviations |
| Untouched surfaces | No change to models, training, RAG, generation, Gradio, or Feature 002 gate behavior | §IV ✅ |

All decisions comply; the single Build-Order deviation is recorded in the notebook's Deviations
section per §Governance. No unjustified violations.
