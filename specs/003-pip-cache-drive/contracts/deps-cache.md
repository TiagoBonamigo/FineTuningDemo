# Contract: Stage 0 Dependency Cache

The interface this feature exposes is the Stage 0 bootstrap block (constants + behavior) and the
on-Drive cache layout. This contract fixes the behavior so it is testable and consistent with
Feature 002's gate.

## Constant contract (Cell 1 bootstrap)

```python
DRIVE_BASE         = "/content/drive/MyDrive/domain-llm-poc"   # relocated up from Cell 3
DEPS_CACHE_DIR     = f"{DRIVE_BASE}/deps_cache"
UNATTENDED_DEFAULT = None    # None | "skip" | "rebuild"  (relocated up from Cell 3; shared with Stage 4/5)
FORCE_REBUILD_DEPS = False   # True → rebuild the wheelhouse next run regardless of validity
```

- After this feature, `UNATTENDED_DEFAULT` and `artifact_gate` are defined **before** the pip
  install and MUST NOT be redefined in Cell 3.
- `DRIVE_BASE` MUST be defined once (in the bootstrap); Cell 3 references but does not redefine it.

## Fingerprint contract

```python
runtime_fingerprint() -> str   # e.g. "py3.11-cu121" or "py3.11-cpu"
```

| Guarantee | Detail |
|---|---|
| F1 | Value is `f"py{sys.version_info.major}.{sys.version_info.minor}-{cuda_tag}"`. |
| F2 | `cuda_tag` derives from `nvidia-smi`; `cpu` when no GPU/`nvidia-smi` present. |
| F3 | MUST be computable before any pip install (no torch dependency). |
| F4 | GPU model and Colab base-image identity MUST NOT affect the value. |

## Manifest contract

```python
manifest_hash(requirements: list[str]) -> str   # sha256 hex
```

| Guarantee | Detail |
|---|---|
| M1 | Input is the exact pinned requirement list Stage 0 installs. |
| M2 | Hash is deterministic over normalized (trimmed, newline-joined) input. |
| M3 | Any add/remove/version change MUST change the hash. |

## Decision contract (behavioral guarantees)

Let `cache_valid = wheels_present AND stored_manifest == manifest_hash AND stored_fingerprint == runtime_fingerprint`.

| # | Given | Then | Spec ref |
|---|---|---|---|
| D1 | Drive mount fails | online install; no cache read/write; setup succeeds | FR-007, SC-006 |
| D2 | wheelhouse absent (first run) | rebuild: build wheelhouse, install from it, save to Drive; no prompt | FR-003, US1-AS1 |
| D3 | `cache_valid` false — manifest differs | rebuild; no prompt | FR-004, SC-004 |
| D4 | `cache_valid` false — fingerprint differs | rebuild; no prompt | FR-005 |
| D5 | `cache_valid` true, `UNATTENDED_DEFAULT is None`, `FORCE_REBUILD_DEPS` false | prompt via `artifact_gate("Dependency cache", DEPS_CACHE_DIR, <sentinel>, rebuild_verb="Rebuild")` | FR-009 |
| D6 | `cache_valid` true, decision "skip" | offline install from wheelhouse; zero downloads | FR-002, SC-002 |
| D7 | `cache_valid` true, decision "rebuild" (prompt, `FORCE_REBUILD_DEPS`, or `UNATTENDED_DEFAULT="rebuild"`) | rebuild + overwrite wheelhouse | FR-006 |
| D8 | offline install raises (corrupt/partial wheelhouse) | fall back to online install; setup succeeds | FR-007, SC-006 |
| D9 | any rebuild/online-install completes but Drive write fails | setup still succeeds; warn that cache was not persisted | FR-007 |
| D10 | after any rebuild or online install | refresh `wheels/`, `manifest.sha256`, `fingerprint.txt` to current values (best-effort) | FR-006 |
| D11 | end of Stage 0 (every path) | print cache-hit vs fresh-install and elapsed seconds | FR-011 |
| D12 | warm vs cold run | identical effective installed versions | FR-008, SC-003 |

## Wheelhouse operation contract

```python
# Rebuild (cold / stale / forced):
pip wheel   --wheel-dir={DEPS_CACHE_DIR}/wheels  <pinned requirements>
pip install --no-index --find-links={DEPS_CACHE_DIR}/wheels  <pinned requirements>
# then write manifest.sha256 + fingerprint.txt

# Warm (valid + skip):
pip install --no-index --find-links={DEPS_CACHE_DIR}/wheels  <pinned requirements>
```

- The pinned requirement list MUST be the single source used for BOTH `pip wheel` and every
  `pip install` (guarantees D12 / FR-008). It stays exactly the notebook's current Stage 0 list.
- Warm install MUST pass `--no-index` so a missing wheel fails fast into the D8 fallback rather than
  silently reaching the internet.

## Cell 3 call-site contract

Cell 3 (Constants) MUST have `UNATTENDED_DEFAULT` and the `artifact_gate` definition **removed**
(now defined in the Cell 1 bootstrap). All later `artifact_gate(...)` call sites (Stage 4 Cell 17,
Stage 5 Cell 20) are unchanged and continue to work against the relocated definition.
