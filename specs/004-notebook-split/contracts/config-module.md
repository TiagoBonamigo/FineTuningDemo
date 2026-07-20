# Contract: Shared `config.py` module

The single cross-notebook import. Stdlib-only at import time (safe before pip install). All signatures
are the stable surface every notebook depends on; changing them is a contract change.

## Constants contract

`config` MUST expose, as module-level names, every constant currently in the Stage 0 Constants cell
(see data-model.md for the full list), unchanged in meaning and default value. These are the **single
source of truth**; notebooks reference `config.NAME` and MUST NOT re-assign them (FR-011).

`ENABLE_THINKING` MUST remain `False` (§IV). `SYSTEM_PROMPT`, `RETRIEVAL_TEMPLATE`, and all generation
params are read by the serve notebook only from `config`.

## Behavioral functions

```python
select_profile(vram_gb: float) -> dict
# Returns the active profile: {MODEL_ID, MAX_SEQ_LEN, LORA_R, LORA_ALPHA, LORA_TARGETS,
#   TRAIN_BATCH, GRAD_ACCUM, TRAIN_EPOCHS}. vram_gb < 24 → T4 fallback set; else A100 set.
# Called by fine-tune/serve/export after `import torch`. MUST keep the default (A100) set fitting
# an A100 and the fallback set fitting a 16 GB T4 (§III / FR-010).

set_seeds() -> None
# Fix random/np/torch seeds to config.SEED (torch imported lazily inside).

mount_drive() -> bool
# Idempotent Colab Drive mount; returns False (with a warning) if unavailable so callers can degrade.

artifact_gate(name, drive_path, sentinel, rebuild_verb="Rebuild") -> "skip" | "rebuild"
# Feature 002 semantics, unchanged: honors UNATTENDED_DEFAULT; prompts only when the artifact exists
# and UNATTENDED_DEFAULT is None.

install_deps(reqs: list[str]) -> None
# Feature 003 wheelhouse, re-keyed per manifest. Computes manifest8 from `reqs`; uses cache slot
# deps_cache/{fingerprint}/{manifest8}/wheels/. Cold: pip wheel → install --no-index → save sentinels.
# Warm+valid: install --no-index --find-links offline. Any Drive failure → online `pip install`.
# MUST install exactly `reqs` (the caller's phase subset) and nothing else.

write_meta(artifact_dir: str, meta: dict) -> None
# Write artifact_dir/meta.json atomically (last, after the artifact is fully saved).

verify_meta(artifact_dir: str, expected: dict) -> None
# Raise FileNotFoundError-style error if artifact_dir missing (FR-007). Load meta.json; for each key
# in `expected`, RAISE a clear ValueError naming the field + producing phase if it differs (FR-013).
```

## Guarantees

- Importing `config` MUST NOT trigger any pip install, Drive mount, or GPU access (side-effect-free
  import) — those happen only when a notebook calls the functions.
- `install_deps` MUST NOT install a phase's non-members (a build notebook never pulls the full stack).
- `verify_meta` is the single drift/existence gate used by every consuming notebook (no per-notebook
  bespoke checks — FR-012).
