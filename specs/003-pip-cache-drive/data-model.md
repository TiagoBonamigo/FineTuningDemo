# Phase 1 Data Model: Drive-Cached Dependency Install

Runtime constructs only — no database. Entities map to the spec's Key Entities and to the on-Drive
cache layout.

## Entity: Dependency Cache (the wheelhouse)

One cache slot on Drive holding built wheels plus validity sentinels.

**On-Drive layout** (`DEPS_CACHE_DIR = f"{DRIVE_BASE}/deps_cache"`):

```text
{DRIVE_BASE}/deps_cache/
├── wheels/            # *.whl built by `pip wheel` (the wheelhouse; multi-GB expected)
├── manifest.sha256    # sentinel: hex sha256 of the pinned dependency manifest
└── fingerprint.txt    # sentinel: e.g. "py3.11-cu121" or "py3.11-cpu"
```

| Field | Type | Notes |
|---|---|---|
| location | path | Single slot. A manifest/fingerprint change overwrites it (no second cache). |
| wheels/ | dir of `.whl` | Presence of at least one wheel + both sentinels = "present". |
| manifest.sha256 | text | Compared to the current manifest hash for dependency validity. |
| fingerprint.txt | text | Compared to the current runtime fingerprint for runtime validity. |

**Validity rule**: `cache_valid = wheels_present AND manifest.sha256 == current_manifest_hash AND
fingerprint.txt == current_fingerprint`.

## Entity: Dependency Manifest

The declared, pinned dependency list — the source of truth (spec Assumptions).

| Field | Type | Notes |
|---|---|---|
| requirements | ordered list[str] | The exact pinned specifiers the notebook installs (as in the current Stage 0 install command). |
| hash | sha256 hex | `sha256` of the normalized (trimmed, newline-joined) requirements; written to `manifest.sha256`. |

**Validation**: any add/remove/version change alters the hash → cache is dependency-invalid → rebuild
(FR-004, SC-004).

## Entity: Runtime Fingerprint

Environment characteristics that gate cross-runtime restore (clarified scope).

| Field | Type | Source | Notes |
|---|---|---|---|
| python_tag | str | `sys.version_info` | `py{major}.{minor}` |
| cuda_tag | str | `nvidia-smi` (parsed) | `cu<major><minor>` or `cpu` if no GPU |
| value | str | derived | `f"{python_tag}-{cuda_tag}"`; written to `fingerprint.txt` |

Excludes GPU model and Colab base-image identity (clarification).

## Entity: Control constants (Cell 1 bootstrap)

| Constant | Type | Values | Notes |
|---|---|---|---|
| `UNATTENDED_DEFAULT` | `str \| None` | `None` / `"skip"` / `"rebuild"` | Relocated from Cell 3; shared with Stage 4/5 (Feature 002). |
| `FORCE_REBUILD_DEPS` | bool | `False` (default) / `True` | New. `True` forces a wheelhouse rebuild on the next run regardless of validity (FR-009 force flag). |

## State Transitions: Stage 0 dependency-setup decision

```text
mount Drive ──fail──────────────────────────────────► ONLINE INSTALL (fallback, FR-007)
     │ ok
     ▼
compute manifest_hash + fingerprint
     │
cache_valid? = present AND manifest match AND fingerprint match
     │
     ├─ not valid ─────────────────────────────────► REBUILD  (no prompt; FR-004/FR-005)
     │
     └─ valid ─┬─ FORCE_REBUILD_DEPS == True ───────► REBUILD  (no prompt)
               │
               └─ else artifact_gate(...) ──"skip"──► WARM INSTALL (offline from wheelhouse)
                                          └─"rebuild"─► REBUILD

REBUILD        = pip wheel → build wheelhouse → pip install --no-index --find-links → save wheelhouse
                 + sentinels to Drive (write failure = non-fatal, FR-007)
WARM INSTALL   = pip install --no-index --find-links=wheels   (zero downloads, SC-002)
                 └─ on failure ─────────────────────► ONLINE INSTALL (fallback, FR-007)
ONLINE INSTALL = pip install <pinned list>   (from internet; attempts cache save afterward)
```

Every terminal path prints whether dependencies came from cache or were freshly installed, plus the
Stage 0 elapsed time (FR-011).
