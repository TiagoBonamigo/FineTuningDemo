"""Shared configuration + setup helpers for the Domain LLM Comparison POC.

This is the SINGLE cross-notebook import (constitution v1.2.0, §I / §Notebook
Decomposition). Every phase notebook (`01_build_index`, `02_finetune`,
`03_compare_serve`, `04_export_gguf`) fetches this file onto the Colab runtime
and does `import config`. It is the single source of truth for all constants —
notebooks MUST NOT re-declare them (FR-011).

Design rule: importing this module MUST be side-effect-free — no pip install, no
Drive mount, no GPU/torch access at import time — so it can be imported *before*
dependencies are installed. `torch` is imported lazily inside the functions that
need it. Everything at module load is stdlib only.

Feature lineage folded in here (the one permitted shared module; no other helper
scripts per §Notebook Decomposition):
  - Feature 002: `artifact_gate()` skip/rebuild prompts.
  - Feature 003: `install_deps()` Drive wheelhouse, re-keyed per dependency
    manifest so the four notebooks do not clobber each other's cache.
"""

import os
import sys
import json
import random
import hashlib
import subprocess

# ─────────────────────────────────────────────────────────────────────────────
# Constants — single source of truth (ported from the monolith's Stage 0)
# ─────────────────────────────────────────────────────────────────────────────

SEED = 42

# ── Model / sequence (A100 defaults; `select_profile` swaps to the T4 set) ───
MODEL_ID    = "unsloth/Qwen3.5-0.8B"
MAX_SEQ_LEN = 2048

# ── LoRA ─────────────────────────────────────────────────────────────────────
LORA_R       = 32
LORA_ALPHA   = 32
LORA_DROPOUT = 0.05
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj"]

# ── Training ─────────────────────────────────────────────────────────────────
# TRAIN_EPOCHS=14 -> ~602 steps on the current training_dataset.jsonl (343 valid pairs,
# steps/epoch = ceil(ceil(343/TRAIN_BATCH)/GRAD_ACCUM) = 43); closest integer-epoch count to 600.
# Steps/epoch shifts if the dataset size changes -- recompute if you add/remove pairs.
TRAIN_EPOCHS  = 14
TRAIN_BATCH   = 4
GRAD_ACCUM    = 2
LEARNING_RATE = 2e-4

# ── RAG ──────────────────────────────────────────────────────────────────────
EMBED_MODEL   = "all-MiniLM-L6-v2"   # extracted from the monolith's hardcoded value
CHUNK_SIZE    = 2000
CHUNK_OVERLAP = 200
TOP_K         = 3

# ── Generation — IDENTICAL across all three panels (§IV Fair Comparison) ──────
MAX_NEW_TOKENS     = 512
TEMPERATURE        = 0.1
TOP_P              = 0.9
REPETITION_PENALTY = 1.1
ENABLE_THINKING    = False   # MUST stay False for all variants (§IV)

# ── Prompt scaffolding — IDENTICAL across all three panels (§IV) ──────────────
SYSTEM_PROMPT      = "You are a helpful assistant. Answer questions clearly and concisely."
RETRIEVAL_TEMPLATE = "Context:\n{context}\n\nQuestion: {question}"

# ── Paths ────────────────────────────────────────────────────────────────────
DRIVE_BASE     = "/content/drive/MyDrive/domain-llm-poc"
DOCS_PATH      = "/content/domain_docs"
DATASET_PATH   = "/content/training_dataset.jsonl"
DEPS_CACHE_DIR = f"{DRIVE_BASE}/deps_cache"

def chroma_index_path():  return f"{DRIVE_BASE}/chroma_index"
def lora_adapter_path():  return f"{DRIVE_BASE}/lora_adapter"
def gguf_export_path():   return f"{DRIVE_BASE}/gguf_export"

# ── Control constants (shared with the gates below) ──────────────────────────
UNATTENDED_DEFAULT = None   # None → interactive prompt | "skip" | "rebuild"
FORCE_REBUILD_DEPS = False  # True → rebuild this phase's wheelhouse regardless of validity

# Which notebook produces which artifact — used to make drift errors actionable.
_PRODUCED_BY = {
    "chroma_index": "01_build_index.ipynb",
    "lora_adapter": "02_finetune.ipynb",
    "gguf_export":  "04_export_gguf.ipynb",
}

_DRIVE_OK = False   # set by mount_drive()


# ─────────────────────────────────────────────────────────────────────────────
# T4 fallback profile (§III degradability) — ported from the monolith's Stage 0
# ─────────────────────────────────────────────────────────────────────────────

# Profile field set applied by select_profile(). The A100 profile is captured from
# the default constants above (single source of truth); the T4 fallback is explicit.
_PROFILE_KEYS = ("MODEL_ID", "MAX_SEQ_LEN", "LORA_R", "LORA_ALPHA",
                 "LORA_TARGETS", "TRAIN_BATCH", "GRAD_ACCUM", "TRAIN_EPOCHS")
_A100_PROFILE = {k: globals()[k] for k in _PROFILE_KEYS}
_T4_PROFILE = {
    "MODEL_ID": "unsloth/Qwen3-4B-bnb-4bit", "MAX_SEQ_LEN": 512,
    "LORA_R": 8, "LORA_ALPHA": 8, "LORA_TARGETS": ["q_proj", "v_proj"],
    "TRAIN_BATCH": 1, "GRAD_ACCUM": 8, "TRAIN_EPOCHS": 2,
}


def select_profile(vram_gb):
    """Resolve and APPLY the model/LoRA/training profile for the detected GPU.

    Below 24 GB VRAM, apply the T4-safe fallback config; otherwise apply the A100
    config. Each branch sets the FULL profile (so the call is idempotent and a
    prior call can't leave stale fields), mutating the module-level constants in
    place — downstream `config.MODEL_ID` etc. reflect the active profile. Called by
    the model-loading notebooks after `import torch`; build-index never calls it.
    """
    fallback = vram_gb < 24
    profile = _T4_PROFILE if fallback else _A100_PROFILE
    globals().update({k: (list(v) if isinstance(v, list) else v) for k, v in profile.items()})
    label = "T4 fallback config" if fallback else "A100 config"
    print(f"GPU VRAM {vram_gb:.1f} GB → {label}  (MODEL_ID={MODEL_ID}, MAX_SEQ_LEN={MAX_SEQ_LEN})")
    return dict(profile)


def detect_vram_gb():
    """Detected primary-GPU VRAM in GB (torch imported lazily). 0.0 if no CUDA."""
    import torch
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)


def set_seeds():
    """Fix random/np/torch seeds to SEED (torch/numpy imported lazily)."""
    import numpy as np
    import torch
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    print(f"Seeds fixed: SEED={SEED}")


# ─────────────────────────────────────────────────────────────────────────────
# Drive mount (idempotent)
# ─────────────────────────────────────────────────────────────────────────────

def mount_drive():
    """Mount Google Drive (idempotent). Returns True on success, False otherwise
    so callers can degrade (e.g. dependency cache disabled)."""
    global _DRIVE_OK
    if _DRIVE_OK:
        return True
    try:
        from google.colab import drive
        drive.mount("/content/drive")
        _DRIVE_OK = True
    except Exception as e:
        print(f"⚠️  Drive not mounted ({e}); Drive-backed features disabled for this run.")
        _DRIVE_OK = False
    return _DRIVE_OK


# ─────────────────────────────────────────────────────────────────────────────
# Feature 002 — skip/rebuild gate for expensive Drive artifacts
# ─────────────────────────────────────────────────────────────────────────────

def artifact_gate(name, drive_path, sentinel, rebuild_verb="Rebuild"):
    """Return "skip" or "rebuild". Prompts only when the artifact exists AND
    UNATTENDED_DEFAULT is None (interactive mode)."""
    if UNATTENDED_DEFAULT not in (None, "skip", "rebuild"):
        raise ValueError(
            'UNATTENDED_DEFAULT must be None, "skip", or "rebuild" — '
            f"got {UNATTENDED_DEFAULT!r}"
        )
    if not os.path.exists(f"{drive_path}/{sentinel}"):
        return "rebuild"
    if UNATTENDED_DEFAULT is not None:
        return UNATTENDED_DEFAULT
    prompt = (f"{name} found on Drive at {drive_path}.\n"
              f"Skip (s) or {rebuild_verb} (r)?  [default: skip] > ")
    for _ in range(2):
        choice = input(prompt).strip().lower()
        if choice in ("", "s", "skip"):
            return "skip"
        if choice in ("r", "rebuild"):
            return "rebuild"
    return "skip"


# ─────────────────────────────────────────────────────────────────────────────
# Feature 003 — Drive wheelhouse, re-keyed per dependency manifest (research D6)
#   slot: deps_cache/{fingerprint}/{manifest8}/{wheels/, manifest.sha256, fingerprint.txt}
# ─────────────────────────────────────────────────────────────────────────────

def _runtime_fingerprint():
    """py<major>.<minor>-<cuda tag> (or -cpu). Computable before torch exists."""
    import re
    py = f"py{sys.version_info.major}.{sys.version_info.minor}"
    cuda = "cpu"
    try:
        out = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=15).stdout
        m = re.search(r"CUDA Version:\s*([0-9]+)\.([0-9]+)", out)
        if m:
            cuda = f"cu{m.group(1)}{m.group(2)}"
    except Exception:
        cuda = "cpu"
    return f"{py}-{cuda}"


def _manifest_hash(reqs):
    return hashlib.sha256("\n".join(r.strip() for r in reqs).encode()).hexdigest()


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return None


def _pip(*args):
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def install_deps(reqs):
    """Install exactly `reqs` (this notebook's minimal phase subset — FR-004),
    reusing a Drive wheelhouse keyed by (runtime fingerprint, manifest hash) so
    each phase gets its own slot and the four notebooks never clobber each other
    (research D6). Falls back to a normal online install on any Drive problem, so
    setup never hard-fails.
    """
    manifest    = _manifest_hash(reqs)
    fingerprint = _runtime_fingerprint()
    slot        = f"{DEPS_CACHE_DIR}/{fingerprint}/{manifest[:8]}"
    wheels_dir  = f"{slot}/wheels"

    def _online():
        print("→ Installing dependencies online (no Drive cache).")
        _pip("install", "-q", *reqs)

    if not _DRIVE_OK:
        return _online()

    wheels_present = os.path.isdir(wheels_dir) and any(
        fn.endswith(".whl") for fn in os.listdir(wheels_dir))
    cache_valid = (
        wheels_present
        and _read(f"{slot}/manifest.sha256") == manifest        # deps unchanged (FR-004)
        and _read(f"{slot}/fingerprint.txt") == fingerprint     # runtime match  (FR-005)
    )

    def _rebuild():
        print(f"→ Building dependency cache for this phase → {slot}")
        os.makedirs(wheels_dir, exist_ok=True)
        _pip("wheel", "-q", "--wheel-dir", wheels_dir, *reqs)
        _pip("install", "-q", "--no-index", "--find-links", wheels_dir, *reqs)
        try:
            with open(f"{slot}/fingerprint.txt", "w") as f:
                f.write(fingerprint)
            with open(f"{slot}/manifest.sha256", "w") as f:   # written LAST = complete-save marker
                f.write(manifest)
        except Exception as e:
            print(f"⚠️  Dependencies installed but cache sentinels not saved ({e}).")

    def _warm():
        print(f"→ Installing offline from wheelhouse {slot}")
        _pip("install", "-q", "--no-index", "--find-links", wheels_dir, *reqs)

    try:
        if not cache_valid:
            reason = "no usable cache" if not wheels_present else "dependencies or runtime changed"
            print(f"→ ({reason})")
            _rebuild()
        elif FORCE_REBUILD_DEPS:
            print("→ FORCE_REBUILD_DEPS set — rebuilding this phase's wheelhouse.")
            _rebuild()
        else:
            decision = artifact_gate("Dependency cache", slot, "manifest.sha256", "Rebuild")
            _warm() if decision == "skip" else _rebuild()
    except Exception as e:
        print(f"⚠️  Wheelhouse path failed ({e}); installing online instead.")
        _online()


# ─────────────────────────────────────────────────────────────────────────────
# Artifact metadata sidecar — drift + existence gate (FR-007 / FR-013)
# ─────────────────────────────────────────────────────────────────────────────

def write_meta(artifact_dir, meta):
    """Write `artifact_dir/meta.json` atomically (call LAST, after the artifact is
    fully saved, so its presence implies a complete build)."""
    os.makedirs(artifact_dir, exist_ok=True)
    tmp = f"{artifact_dir}/meta.json.tmp"
    with open(tmp, "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    os.replace(tmp, f"{artifact_dir}/meta.json")
    print(f"📝 Wrote sidecar {artifact_dir}/meta.json")


def verify_meta(artifact_dir, expected):
    """Fail fast if `artifact_dir` is missing (FR-007) or its sidecar disagrees with
    `expected` on any field (FR-013). Raises with the offending field and the phase
    to re-run so the caller never loads an incompatible or absent artifact."""
    name = os.path.basename(artifact_dir.rstrip("/"))
    producer = _PRODUCED_BY.get(name, "the producing notebook")
    if not os.path.isdir(artifact_dir):
        raise FileNotFoundError(
            f"Required artifact '{name}' not found at {artifact_dir}. Run {producer} first.")
    meta_path = f"{artifact_dir}/meta.json"
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"Artifact '{name}' has no meta.json sidecar at {meta_path}. "
            f"Rebuild it by re-running {producer} (this version stamps a sidecar).")
    with open(meta_path) as f:
        meta = json.load(f)
    mismatches = [
        f"{k}: artifact has {meta.get(k)!r} but config expects {v!r}"
        for k, v in expected.items() if meta.get(k) != v
    ]
    if mismatches:
        raise ValueError(
            f"Config/artifact drift on '{name}':\n  - " + "\n  - ".join(mismatches) +
            f"\nThe stored artifact was built with a different config. Re-run {producer} "
            f"to rebuild it against the current config.")
    print(f"✅ Verified {name}/meta.json matches current config.")
