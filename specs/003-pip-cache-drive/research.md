# Phase 0 Research: Drive-Cached Dependency Install

The spec's two open decisions were resolved in the `/speckit-clarify` session (Runtime Fingerprint =
Python+CUDA; single cache slot). This document records the remaining technical decisions and the
honest feasibility caveats that shape the design.

## Decision 1: Cache format — Drive wheelhouse (not a restored site-packages tree)

- **Decision**: Cache a **wheelhouse** — a directory of `.whl` files on Drive — and install from it
  each session with `pip install --no-index --find-links=<wheelhouse>`. Build/refresh it with
  `pip wheel --wheel-dir=<wheelhouse> <pinned requirements>`.
- **Rationale**: This is the wheel/package-cache approach chosen in the spec (FR-010). `pip` still
  performs its normal resolution and install, so versions match a cold install exactly (FR-008,
  §III/§IV). It is a standard, well-understood pip pattern (§I) needing no new dependencies (§II).
- **Alternatives considered**:
  - Copy the fully-installed `site-packages` to Drive and add it to `sys.path` — near-instant but
    fragile to any Python/CUDA change and slow to read thousands of small files from Drive; out of
    scope per spec FR-010.
  - `pip download` instead of `pip wheel` — `download` can leave sdists that still build at install
    time; `pip wheel` materializes built wheels so the warm install is pure-binary and offline.

## Decision 2: Runtime Fingerprint computation

- **Decision**: `fingerprint = f"py{sys.version_info.major}.{sys.version_info.minor}-{cuda_tag}"`,
  where `cuda_tag` is the CUDA version parsed from `nvidia-smi` output (e.g., `cu121`), or `cpu`
  when no GPU is present. Stored as a small text sentinel in the cache.
- **Rationale**: Python minor version and CUDA generation are what determine compiled-wheel
  compatibility (torch, bitsandbytes, unsloth), matching the clarification. `nvidia-smi` is available
  before any pip install (it ships with the Colab image), so the fingerprint can be computed in the
  Stage 0 bootstrap before torch exists.
- **Alternatives considered**:
  - Read CUDA from `torch.version.cuda` — unavailable on a cold run (torch not yet installed).
  - Include GPU model / Colab base-image hash — rejected in clarification (causes needless rebuilds).

## Decision 3: Manifest hash (dependency-drift detection)

- **Decision**: The manifest is the exact ordered list of pinned requirement strings the notebook
  installs. Store `manifest_hash = sha256(normalized_manifest)` as a sentinel in the cache. A cache
  is dependency-valid only when the stored hash equals the current one (FR-004).
- **Rationale**: Hashing the literal pinned list makes any add/remove/version-bump invalidate the
  cache deterministically (SC-004), with no per-package comparison logic (§I).
- **Alternatives considered**: Comparing installed `pip freeze` output — heavier and includes
  transitive versions that vary; the declared pinned list is the spec's source of truth (Assumptions).

## Decision 4: Reusing Feature 002's prompt for the user choice

- **Decision**: Compute `cache_valid = wheelhouse_present AND manifest_matches AND fingerprint_matches`.
  If not valid → decision is `"rebuild"` with **no prompt** (stale/absent/cross-env auto-rebuild,
  FR-004/FR-005/FR-007). If valid → decision comes from, in order: `FORCE_REBUILD_DEPS` (force flag)
  → else `artifact_gate("Dependency cache", DEPS_CACHE_DIR, <validity sentinel>, rebuild_verb="Rebuild")`,
  which applies the same skip/rebuild prompt and `UNATTENDED_DEFAULT` short-circuit as Stage 4/5.
- **Rationale**: Satisfies FR-009 ("same interactive choice … `UNATTENDED_DEFAULT`") without a second
  prompt implementation. `artifact_gate` is only invoked once presence+validity are established, so
  its presence-based prompt fires exactly when a genuinely reusable cache exists.
- **Consequence**: `UNATTENDED_DEFAULT` and `artifact_gate` must be defined *before* the Stage 0
  install. They currently live in Cell 3 (after install) → relocate them to the Stage 0 bootstrap
  (see Decision 6).

## Decision 5: Graceful fallback (never fail setup)

- **Decision**: Wrap Drive mount, cache read, and cache write in try/except. On any failure (Drive
  unmounted, unwritable, corrupt/partial wheelhouse, or a failed offline install) the notebook falls
  back to a normal online `pip install` of the pinned list and continues; a cold rebuild also attempts
  to (re)write the cache but a write failure is non-fatal (FR-007, SC-006).
- **Rationale**: Reproducibility (§III) requires the notebook to always complete top-to-bottom;
  caching is an optimization, never a correctness dependency (Assumptions).
- **Alternatives considered**: Hard-failing on cache errors — rejected; it would make Drive a single
  point of failure for the whole pipeline.

## Decision 6: Ordering / notebook restructure

- **Decision**: Add a **bootstrap prologue** at the top of the Stage 0 install cell (Cell 1) that
  runs before any pip install: `import os, sys`; mount Drive (idempotent); define `DRIVE_BASE`,
  `DEPS_CACHE_DIR`, `FORCE_REBUILD_DEPS`, and — relocated from Cell 3 — `UNATTENDED_DEFAULT` and
  `artifact_gate`. Cell 3 stops redefining the relocated names.
- **Rationale**: The cache decision and the shared prompt must exist before install. Relocating the
  shared helper upward also benefits Feature 002 (single definition for all gates). The existing
  Stage 1 `drive.mount` stays as-is and is a harmless idempotent no-op after the bootstrap mount.
- **Deviation**: This changes the Build Order (Drive mount + config now partly precede the install).
  Per §Governance it MUST be noted in the notebook's Deviations section.

## Feasibility caveats (must be surfaced, not hidden)

- **Wheelhouse size**: torch + CUDA + unsloth wheels can total several GB. Reading them back from
  Drive is faster than re-downloading over the network in most Colab sessions, but not free. SC-005
  mandates a fallback if the warm path is ever slower than a cold install; the design measures Stage 0
  duration and reports it (FR-011) so regressions are visible.
- **Where the time actually goes**: On Colab the cold cost is dominated by downloading large wheels
  and building a few sdists. The warm path removes the download and (because wheels are prebuilt)
  the builds — the expected saving. Pure dependency *resolution* is not eliminated but is minor.
- **Single-slot thrash**: Alternating T4↔A100 (different CUDA tag) rebuilds each switch (accepted in
  clarification). Users who alternate frequently will see less benefit; documented in quickstart.
- **First run pays extra**: The cold run additionally runs `pip wheel` and copies the wheelhouse to
  Drive, so the *first ever* Stage 0 is slightly slower than today's plain install. All subsequent
  warm runs recoup it. Called out in quickstart Scenario A.
