# Contract: Artifact Gate Helper & Prompt UX

The interface this feature exposes is the notebook-internal `artifact_gate` helper and the text of
the interactive prompt shown to the user. This contract fixes the behavior that Stage 4 and Stage 5
depend on, so both stages remain identical (§IV) and the acceptance scenarios are testable.

## Constant contract

```python
# Cell 3 (Constants) — replaces `FORCE_RETRAIN`
UNATTENDED_DEFAULT = None   # None → interactive prompt | "skip" | "rebuild"
```

- The identifier `FORCE_RETRAIN` MUST NOT appear anywhere in `notebook.ipynb` after this change
  (FR-009, SC-005).

## Function contract

```python
def artifact_gate(name: str, drive_path: str, sentinel: str, rebuild_verb: str = "Rebuild") -> str:
    """Decide whether to skip or rebuild a Drive artifact.

    Returns "skip" or "rebuild". Prompts the user only when the artifact exists
    AND UNATTENDED_DEFAULT is None.
    """
```

| Parameter | Meaning | Example |
|---|---|---|
| `name` | Human-readable artifact name for the prompt | `"RAG index"`, `"LoRA adapter"` |
| `drive_path` | Directory on Drive holding the artifact | `f"{DRIVE_BASE}/chroma_index"` |
| `sentinel` | File whose presence means "artifact exists" | `"chroma.sqlite3"` |
| `rebuild_verb` | Stage-specific verb for the rebuild choice | `"Rebuild"` (Stage 4), `"Retrain"` (Stage 5) |

**Return value**: exactly `"skip"` or `"rebuild"` (never `None`, never raises on user input).

### Behavioral guarantees

| # | Given | Then | Spec ref |
|---|---|---|---|
| C1 | sentinel file absent | returns `"rebuild"`, no prompt printed | FR-007 |
| C2 | sentinel present, `UNATTENDED_DEFAULT == "skip"` | returns `"skip"`, no prompt | US3 AS-1 |
| C3 | sentinel present, `UNATTENDED_DEFAULT == "rebuild"` | returns `"rebuild"`, no prompt | US3 AS-2 |
| C4 | sentinel present, `UNATTENDED_DEFAULT is None` | prints prompt naming `name` + `drive_path`, reads input | FR-003, FR-004 |
| C5 | prompt input `""` | returns `"skip"` | FR-011 |
| C6 | prompt input `s`/`skip` (any case, trimmed) | returns `"skip"` | FR-003 |
| C7 | prompt input `r`/`rebuild` (any case, trimmed) | returns `"rebuild"` | FR-003 |
| C8 | prompt input unrecognized | re-prompts exactly once | FR-011 |
| C9 | second prompt input `r`/`rebuild` | returns `"rebuild"` | FR-011 |
| C10 | second prompt input anything else (incl. empty/unrecognized) | returns `"skip"` | FR-011 |
| C11 | `UNATTENDED_DEFAULT` not in `{None,"skip","rebuild"}` | raises a clear `ValueError` | data-model validation |

## Prompt text contract

The interactive prompt (C4) MUST identify the artifact and its Drive location (FR-004). Format:

```text
{name} found on Drive at {drive_path}.
Skip (s) or {rebuild_verb} (r)?  [default: skip] >
```

- Stage 4 renders `{name}="RAG index"`, `{rebuild_verb}="Rebuild"`.
- Stage 5 renders `{name}="LoRA adapter"`, `{rebuild_verb}="Retrain"`.
- The re-prompt (C8) reuses the identical message text.

## Call-site contract (stage integration)

Stage 4 (Cell 17) and Stage 5 (Cell 20) MUST replace their
`if _<artifact>_exists and not FORCE_RETRAIN:` guard with:

```python
# Stage 4
_gate = artifact_gate("RAG index", f"{DRIVE_BASE}/chroma_index",
                      "chroma.sqlite3", rebuild_verb="Rebuild")
if _gate == "skip":
    ...  # existing "load collection" branch
else:
    ...  # existing "build + overwrite" branch

# Stage 5
_gate = artifact_gate("LoRA adapter", f"{DRIVE_BASE}/lora_adapter",
                      "adapter_model.safetensors", rebuild_verb="Retrain")
if _gate == "skip":
    ...  # existing "skip training" branch
else:
    ...  # existing "train + save" branch
```

The bodies of the skip and rebuild branches are the **existing** Stage 4/5 code — this feature only
changes the guard condition, not the build/train/save logic (§IV: no behavioral change to training,
embedding, or artifact format).
