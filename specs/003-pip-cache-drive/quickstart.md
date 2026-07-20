# Quickstart: Validating Drive-Cached Dependency Install

Runnable scenarios that prove the feature works end to end. Run in Colab against `notebook.ipynb`
after implementation. See [contracts/deps-cache.md](contracts/deps-cache.md) for the exact guarantees
(D1–D12) and [data-model.md](data-model.md) for the decision state machine.

## Prerequisites

- A Colab session (any tier). Note the runtime type (T4/L4/A100) — it sets the CUDA fingerprint.
- Drive available to mount. For warm-cache scenarios, one prior full Stage 0 run must have populated
  `{DRIVE_BASE}/deps_cache/`.

## Scenario A — First run builds the cache (US1-AS1, FR-003)

1. Start a fresh runtime with **no** `deps_cache` on Drive.
2. Run Stage 0.
3. **Expect**: Drive mounts; no usable cache found; dependencies install normally; a wheelhouse plus
   `manifest.sha256` and `fingerprint.txt` are written under `{DRIVE_BASE}/deps_cache/`. Stage 0
   prints "fresh install" and its elapsed time (this first run is slightly slower than a plain
   install because it also builds + saves the wheelhouse).

## Scenario B — Warm cache is fast and offline (US1, SC-001/SC-002)

1. Restart the runtime (same tier as Scenario A) so the RAM environment is wiped but Drive persists.
2. Run Stage 0; at the prompt type `s` (skip/reuse) — or pre-set `UNATTENDED_DEFAULT="skip"`.
3. **Expect**: install runs offline from the wheelhouse (`--no-index`), **zero** package downloads,
   Stage 0 at least 3× faster than the Scenario A baseline (target <90 s), and every later stage
   imports its libraries successfully.

## Scenario C — Interactive rebuild on a valid cache (FR-009, D5/D7)

1. Warm cache present, `UNATTENDED_DEFAULT=None`, `FORCE_REBUILD_DEPS=False`.
2. Run Stage 0; at "Dependency cache found … Skip (s) or Rebuild (r)?" type `r`.
3. **Expect**: the wheelhouse is rebuilt and overwritten; Stage 0 prints a fresh install.
4. Repeat, typing empty / `s` → reuse (matches Feature 002 prompt semantics).

## Scenario D — Force-rebuild flag (FR-009 force flag)

1. Warm cache present. Set `FORCE_REBUILD_DEPS=True`. Run Stage 0.
2. **Expect**: rebuild with no prompt, regardless of validity. Reset the flag to `False` afterward.

## Scenario E — Dependency change auto-invalidates (US2, FR-004/SC-004)

1. Warm cache present. Edit the pinned install list (add a package or bump a version).
2. Run Stage 0 (interactive or unattended).
3. **Expect**: manifest hash mismatch → automatic rebuild (no skip prompt); the new/changed package
   is present afterward; `manifest.sha256` updates.

## Scenario F — Runtime mismatch falls back safely (US3, FR-005/D4)

1. Build the cache on one tier (e.g., T4). Start a runtime with a different CUDA tag (e.g., A100).
2. Run Stage 0.
3. **Expect**: fingerprint mismatch → clean rebuild rather than restoring incompatible wheels; all
   imports succeed; `fingerprint.txt` updates to the new runtime.

## Scenario G — Drive unavailable / cache corrupt → still succeeds (FR-007, SC-006)

1. **Drive absent**: do not mount Drive (or point `DRIVE_BASE` at an unwritable path); run Stage 0 →
   **Expect** a normal online install that completes successfully, no hard failure.
2. **Corrupt cache**: delete a wheel or truncate `manifest.sha256`, then run Stage 0 → **Expect** the
   offline install fails fast and falls back to an online install that succeeds.

## Scenario H — Never slower than cold (SC-005)

1. Compare the Stage 0 elapsed time (printed, FR-011) on a warm run vs the Scenario A cold baseline.
2. **Expect**: warm ≤ cold. (If a future change made warm slower, the fallback path must trigger.)

## Scenario I — Reproducibility parity (FR-008, SC-003)

1. After a warm run, capture installed versions of the key libraries; compare to a cold run's.
2. **Expect**: identical effective versions — caching changed speed, not what is installed.

## Regression checks

- Feature 002 still works: Stage 4/5 prompts behave unchanged with `artifact_gate` now defined in the
  Stage 0 bootstrap (`grep` confirms a single `def artifact_gate` and single `UNATTENDED_DEFAULT`).
- The notebook Deviations section records the Build-Order change (Drive mount + shared helpers moved
  into Stage 0).

## Pass criteria

Scenarios A–I behave as described, matching the acceptance scenarios in [spec.md](spec.md) and the
behavioral guarantees D1–D12 in the contract.
