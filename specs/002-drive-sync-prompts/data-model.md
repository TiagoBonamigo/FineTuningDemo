# Phase 1 Data Model: Interactive Drive Artifact Prompts

This feature is a notebook UX change with no persisted database. The "entities" below are runtime
constructs (constants, function inputs/outputs, and detection targets). They map directly to the
Key Entities in the spec.

## Entity: Unattended Default

The top-level constant that pre-answers all artifact prompts.

| Field | Type | Values | Notes |
|---|---|---|---|
| `UNATTENDED_DEFAULT` | `str \| None` | `None`, `"skip"`, `"rebuild"` | Defined in Cell 3 (Constants). Replaces `FORCE_RETRAIN`. |

**State meaning**:

- `None` → interactive mode: prompt at every stage where an artifact is found (FR-003).
- `"skip"` → reuse any found artifact without prompting (US3 AS-1).
- `"rebuild"` → always rebuild without prompting; mirrors former `FORCE_RETRAIN = True` (US3 AS-2, SC-004).

**Validation**: Any value other than the three above SHOULD raise a clear error at first use so a
typo (e.g. `"Skip"` vs `"skip"`) fails loudly rather than silently falling through to a build.

## Entity: Drive Artifact

A stage output persisted to Drive, detected by a sentinel file (presence-based, FR-010).

| Artifact | Drive path | Sentinel file | Detected in |
|---|---|---|---|
| RAG index (ChromaDB) | `{DRIVE_BASE}/chroma_index` | `chroma.sqlite3` | Stage 4 (Cell 17) |
| LoRA adapter | `{DRIVE_BASE}/lora_adapter` | `adapter_model.safetensors` | Stage 5 (Cell 20) |

**Detection rule**: `os.path.exists(f"{drive_path}/{sentinel}")`. Corrupt-but-present files count
as "found" (spec Edge Cases). Absent Drive mount → path missing → "not found".

## Entity: Artifact Prompt Outcome

The value returned by the gate and consumed by each stage's branch.

| Field | Type | Values | Notes |
|---|---|---|---|
| outcome | `str` | `"skip"`, `"rebuild"` | The only two outcomes; drives the stage `if/else`. |

**Outcome → stage behavior**:

| Outcome | Stage 4 behavior | Stage 5 behavior |
|---|---|---|
| `"skip"` | Load existing collection; embed nothing; leave Drive copy untouched (FR-005). | Leave adapter on Drive; bypass training entirely (FR-005). |
| `"rebuild"` | Re-embed all docs; overwrite Drive index (FR-006). | Run full training; overwrite adapter files (FR-006). |

## State Transitions: `artifact_gate(name, drive_path, sentinel)` → outcome

```text
        ┌─ sentinel absent ──────────────────────────────────► return "rebuild"  (FR-007; no prompt)
        │
found? ─┤                    ┌─ UNATTENDED_DEFAULT == "skip" ──► return "skip"    (no prompt)
        │                    │
        └─ sentinel present ─┼─ UNATTENDED_DEFAULT == "rebuild" ► return "rebuild"(no prompt)
                             │
                             └─ UNATTENDED_DEFAULT is None ─────► PROMPT
                                                                    │
   ┌────────────────────────────────────────────────────────────────┘
   ▼
prompt #1 ─┬─ "" (empty) ──────────────► "skip"      (FR-011)
           ├─ "s"/"skip" ──────────────► "skip"
           ├─ "r"/"rebuild" ───────────► "rebuild"
           └─ unrecognized ─► prompt #2 ─┬─ "r"/"rebuild" ─► "rebuild"
                                         └─ anything else ─► "skip"  (FR-011: default skip)
```

**Input normalization**: trim whitespace, lowercase before matching.
`{"", "s", "skip"} → skip`; `{"r", "rebuild"} → rebuild`; everything else on prompt #1 →
re-prompt; everything except an explicit rebuild token on prompt #2 → skip.
