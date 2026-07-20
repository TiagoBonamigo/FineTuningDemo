# Feature Specification: Drive-Cached Dependency Install

**Feature Branch**: `003-pip-cache-drive`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Is it possible to have the requirements installed by pip to be installed on a Google Drive share so that if we are restarting the environment we can skip reinstallation?"

## Clarifications

### Session 2026-07-20

- Q: How should the cache decide when to refresh — reuse Feature 002's prompt pattern, or refresh
  silently? → A: Reuse the Feature 002 pattern — an interactive skip/rebuild prompt plus the
  `UNATTENDED_DEFAULT` unattended constant, with an explicit user-settable flag to force a cache
  rebuild.
- Q: What should be cached to Drive (installable packages vs. the fully-installed environment)? →
  A: Deferred by the user; resolved to the **wheel/package cache** approach (cache the downloaded
  installable packages and run a fast local install each session) as the reproducibility-aligned
  default. Caching the fully-installed environment for direct import is out of scope for this
  version and may be revisited at planning time.
- Q: Which environment characteristics determine cache compatibility (the Runtime Fingerprint)? →
  A: The Python major.minor version plus the CUDA/accelerator tag — the factors that determine
  compiled-wheel compatibility. GPU model and Colab base-image identity are deliberately excluded so
  that runtimes sharing the same Python and CUDA generation reuse the cache instead of rebuilding.
- Q: One cache slot or separate caches per Runtime Fingerprint? → A: A single cache slot. When the
  fingerprint changes the single cache is rebuilt (overwritten); alternating between two runtime
  types therefore rebuilds on each switch — an accepted trade-off for simplicity (§I). Per-fingerprint
  caches are out of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast startup from a warm cache (Priority: P1)

A notebook user who ran the pipeline in a previous session opens a fresh Colab runtime and runs
Stage 0 (Install & Config). Because the project dependencies were cached to Google Drive on the
earlier run, Stage 0 restores them from Drive instead of downloading and building every package
from the internet, so the environment is ready in a fraction of the usual time and the user can
proceed to model loading almost immediately.

**Why this priority**: Dependency installation is the single most repeated wait in the workflow —
every runtime restart (disconnect, timeout, new session) pays the full install cost again.
Eliminating that repeated wait is the entire point of the feature and delivers value on its own.

**Independent Test**: Run Stage 0 once to populate the Drive cache, restart the runtime, and run
Stage 0 again. The second run completes markedly faster than the first and every subsequent stage
imports its libraries successfully.

**Acceptance Scenarios**:

1. **Given** no dependency cache exists on Drive, **When** Stage 0 runs, **Then** dependencies are
   installed normally from their original source and the resulting install is saved to Drive for reuse.
2. **Given** a compatible dependency cache exists on Drive (matching manifest and runtime
   fingerprint), **When** Stage 0 runs on a fresh runtime, **Then** the cache is restored from Drive
   and no packages are downloaded or built from source.
3. **Given** the cache has been restored, **When** any later stage imports a project library,
   **Then** the import succeeds and the library behaves identically to a freshly installed copy.
4. **Given** a warm cache, **When** Stage 0 completes, **Then** the time spent on dependency setup is
   substantially lower than the cold-install baseline.

---

### User Story 2 - Automatic refresh when dependencies change (Priority: P2)

A user edits the pinned dependency list (adds a package or bumps a version) and re-runs the
notebook. The notebook recognizes that the cached dependencies no longer match what the notebook
now requires and rebuilds the cache from scratch, so the user never runs against a stale set of
libraries.

**Why this priority**: A cache that silently serves outdated dependencies would undermine
reproducibility and cause confusing errors. Correct invalidation is what makes the P1 speed-up safe
to rely on, but it is only exercised when the dependency set changes, so it ranks below the core
speed-up.

**Independent Test**: Populate the cache, change the declared dependency list, and re-run Stage 0.
The notebook rebuilds the cache and the newly declared package is present afterward.

**Acceptance Scenarios**:

1. **Given** a cache built from a previous dependency list, **When** the declared dependency list
   changes and Stage 0 runs, **Then** the notebook rebuilds the cache to match the new list.
2. **Given** the declared dependency list is unchanged, **When** Stage 0 runs, **Then** the existing
   cache is reused without rebuilding.
3. **Given** the cache was rebuilt, **When** Stage 0 completes, **Then** the refreshed cache is saved
   to Drive and used by the next session.

---

### User Story 3 - Safe fallback on an incompatible runtime (Priority: P3)

A user starts a runtime whose environment differs from the one that produced the cache (for
example, a different GPU tier or a changed Colab base image, so cached compiled packages would not
load). The notebook detects the mismatch and falls back to a normal clean install rather than
restoring a cache that would fail at import time.

**Why this priority**: Compiled/native packages are tied to the exact runtime that built them.
Without a safety fallback, a mismatched cache would produce broken imports that are hard to
diagnose. This protects the reproducibility guarantee, but it is an exception path that most
sessions never hit, so it is the lowest priority.

**Independent Test**: Populate the cache on one runtime type, then start a runtime whose relevant
environment characteristics differ, and run Stage 0. The notebook performs a clean install instead
of restoring the incompatible cache, and all imports succeed.

**Acceptance Scenarios**:

1. **Given** a cache built under different runtime characteristics, **When** Stage 0 runs, **Then**
   the notebook detects the incompatibility and performs a clean install.
2. **Given** an incompatible cache triggered a clean install, **When** Stage 0 completes, **Then** the
   cache is refreshed to match the current runtime.
3. **Given** the cache matches the current runtime characteristics, **When** Stage 0 runs, **Then**
   the cache is restored without a clean install.

---

### Edge Cases

- What happens when Drive is not mounted when Stage 0 runs? Dependency setup falls back to a normal
  install with no cache read or write, so the notebook still succeeds (just without the speed-up).
- What happens when the cache on Drive is partially written or corrupted (e.g., an earlier session
  was interrupted mid-save)? The notebook treats an unusable cache as "no usable cache" and performs
  a clean install rather than importing a broken environment.
- What happens when the Drive share is full or the cache cannot be written? Dependencies still
  install normally for the current session; the caching step reports that it could not persist and
  the session proceeds without a warm cache for next time.
- What happens when restoring the wheelhouse from Drive is slower than a fresh install? Because the
  warm path installs offline from prebuilt wheels it is not structurally slower; Stage 0's reported
  timing (FR-011) surfaces any regression so the user can disable the cache (see SC-005).
- What happens on the very first run of a brand-new project (no cache yet)? Identical to a normal
  install, plus a one-time save to Drive.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: At Stage 0 startup, the notebook MUST check whether a reusable dependency cache for
  this project exists on Google Drive before installing anything from the internet.
- **FR-002**: When a usable, compatible cache exists, the notebook MUST make all project
  dependencies available from that cache without downloading or building them again.
- **FR-003**: When no usable cache exists, the notebook MUST install the dependencies normally and
  then persist them to Drive so a later session can reuse them.
- **FR-004**: The notebook MUST detect when the declared set of dependencies (names and pinned
  versions) differs from what the cache was built with, and MUST rebuild the cache in that case.
- **FR-005**: The notebook MUST detect when the current runtime is incompatible with the cached
  dependencies — where compatibility is determined by the Python major.minor version and the
  CUDA/accelerator tag — and MUST rebuild the cache for the current runtime (installing fresh and
  refreshing the Drive cache per FR-006) rather than restoring the unusable cache. GPU model and
  Colab base-image identity MUST NOT be part of the compatibility check.
- **FR-006**: After any clean install or rebuild, the notebook MUST refresh the Drive cache to
  reflect the dependencies and runtime just used.
- **FR-007**: When Drive is unavailable, unwritable, or the cache is corrupted, the notebook MUST
  still complete dependency setup for the current session without failing.
- **FR-008**: The caching mechanism MUST NOT change which dependency versions the pipeline runs
  with; a warm-cache run and a cold-install run MUST yield the same effective library versions
  (preserving reproducibility and fair-comparison guarantees).
- **FR-009**: The dependency-caching behavior MUST be consistent with Feature 002's artifact
  resumability: when a cache exists, Stage 0 MUST present the same interactive skip (reuse) /
  rebuild choice, and the existing `UNATTENDED_DEFAULT` constant MUST pre-answer it for unattended
  "Run all" execution. In addition, the notebook MUST provide an explicit user-settable flag that
  forces the cache to be rebuilt on the next run regardless of whether it appears current.
- **FR-010**: The cache MUST store the project's downloaded installable dependency packages
  (not a fully-installed, directly-imported environment). A warm-cache run MUST install from those
  cached packages locally without contacting the internet. Caching a fully-installed environment for
  direct import is explicitly out of scope for this version.
- **FR-011**: The notebook MUST report, at the end of Stage 0, whether dependencies were served
  from cache or freshly installed, and how long dependency setup took, so the user can confirm the
  speed-up.

### Key Entities *(include if feature involves data)*

- **Dependency Cache**: The reusable copy of the project's installed dependencies persisted to
  Google Drive, validated against the declared dependency set and the Runtime Fingerprint. There is
  exactly one cache slot; a fingerprint change rebuilds (overwrites) it rather than creating a second
  cache.
- **Dependency Manifest**: The declared list of required packages and pinned versions that the
  cache is validated against to decide reuse vs. rebuild.
- **Runtime Fingerprint**: The environment characteristics that determine whether a cache built
  earlier can be safely restored now — specifically the Python major.minor version and the
  CUDA/accelerator tag. GPU model and Colab base-image identity are excluded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fresh runtime with a warm, compatible cache, dependency setup (Stage 0) is at
  least 3× faster than the cold-install baseline (target: under 90 seconds), since packages install
  from the local cache rather than being downloaded and built from source.
- **SC-002**: A warm-cache run downloads zero packages from the internet for dependencies already in
  the cache.
- **SC-003**: After a warm-cache restore, 100% of the pipeline's library imports succeed and every
  subsequent stage runs without dependency-related errors.
- **SC-004**: When the declared dependency list changes, the next run uses the updated dependencies
  100% of the time (no stale-cache runs).
- **SC-005**: The warm-cache path installs offline from the local wheelhouse and is therefore never
  structurally slower than the cold-install baseline. Stage 0 reports its elapsed time (FR-011) so any
  regression is visible; if a warm run is observed to be slower, the user can disable the cache (delete
  it or set the force-rebuild flag) rather than the notebook auto-aborting mid-install.
- **SC-006**: When Drive is unavailable or the cache is corrupted, dependency setup still succeeds in
  100% of runs (falling back to a normal install).

## Assumptions

- Google Drive is mounted early enough (as it is in the current notebook) for Stage 0 to read and
  write the cache; if it is not, the feature degrades gracefully to a normal install.
- The pinned dependency list in the notebook is the source of truth for what the cache must contain
  (consistent with the constitution's requirement that dependency versions be pinned).
- The primary target is Google Colab restarts within the same broad runtime type; caching is a
  convenience/speed optimization and never a correctness dependency.
- Reproducibility is paramount: the feature must never cause a session to run against different
  library versions than a clean install would produce (constitution §III Reproducibility, §IV Fair
  Comparison).
- The Drive share has enough free space to hold one project dependency cache; housekeeping of old or
  multiple caches is out of scope for this feature.
- This feature only affects dependency setup (Stage 0); it does not change models, training,
  retrieval, generation, or the artifact-resumability behavior added in Feature 002.
- The cache stores downloaded installable packages and a fast local install runs each session (the
  reproducibility- and simplicity-aligned choice). Caching a fully-installed environment for direct
  import — near-instant but fragile to Python/accelerator changes — was considered and deferred; it
  may be revisited at `/speckit-plan`.
- Compiled packages in the cache remain specific to the Python and accelerator/CUDA combination that
  produced them, so the runtime-mismatch fallback (US3) still applies even with a package cache.
- A user-settable force-rebuild flag exists so a user can deliberately discard and rebuild the cache
  without hand-editing Drive.
