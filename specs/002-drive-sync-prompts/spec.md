# Feature Specification: Interactive Drive Artifact Prompts

**Feature Branch**: `002-drive-sync-prompts`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "I want to add Google Drive sync capabilities to the notebook, so it can ask if any step generating artifacts should be skipped in case there is a file already in there or if it should re-generate the artifacts."

## Clarifications

### Session 2026-07-20

- Q: When a user provides invalid or empty input at the artifact prompt, what should happen? → A: On empty input → skip; on unrecognized text → ask once more, then skip (Option B).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Skip or Rebuild RAG Index (Priority: P1)

A notebook user opens their Colab session and runs Stage 4 (RAG index build). Because the ChromaDB index from a previous session is already on Drive, the notebook pauses and asks: "RAG index found on Drive. Skip (s) or Rebuild (r)?" If their domain documents have not changed, they type `s` to skip — Stage 4 completes in seconds instead of minutes. If they have added new documents, they type `r` to rebuild.

**Why this priority**: The RAG index is the first artifact that the notebook checks for and the most likely to be safely reused across sessions. Removing the need to edit `FORCE_RETRAIN` reduces user friction and prevents accidental rebuilds.

**Independent Test**: Run Stage 4 twice in the same session. On the second run, a prompt appears; choosing skip produces a loaded index without re-embedding any documents; choosing rebuild produces a freshly populated index and overwrites the Drive copy.

**Acceptance Scenarios**:

1. **Given** a ChromaDB index already exists on Drive, **When** Stage 4 runs, **Then** a prompt is displayed listing the artifact location and offering a skip or rebuild choice before any embedding begins.
2. **Given** the user answers "skip" at the prompt, **When** Stage 4 continues, **Then** the existing index is loaded from Drive and no documents are re-embedded.
3. **Given** the user answers "rebuild" at the prompt, **When** Stage 4 continues, **Then** all domain documents are re-embedded, a fresh index is written to Drive, and the old index is overwritten.
4. **Given** no ChromaDB index exists on Drive, **When** Stage 4 runs, **Then** no prompt is shown and the index is built without interruption.
5. **Given** the user enters empty input at the Stage 4 prompt, **When** Stage 4 continues, **Then** the behavior is identical to choosing skip.
6. **Given** the user enters unrecognized text at the Stage 4 prompt, **When** Stage 4 prompts again once, **Then** any input (including empty) on the second prompt defaults to skip.

---

### User Story 2 - Skip or Retrain LoRA Adapter (Priority: P2)

A notebook user runs Stage 5 (fine-tuning). An existing LoRA adapter from a previous session is present on Drive. The notebook asks: "LoRA adapter found on Drive. Skip (s) or Retrain (r)?" If the training data is unchanged, the user skips — saving 20–40 minutes of GPU time. If they have updated their JSONL data, they retrain.

**Why this priority**: Fine-tuning is the most time-consuming stage. Accidentally re-running it wastes significant A100/T4 compute-unit quota. An explicit user confirmation makes the choice deliberate.

**Independent Test**: Run Stage 5 with an adapter already on Drive; choose skip — Stage 6 proceeds immediately with the existing adapter. Then rerun Stage 5 and choose retrain — training runs to completion and the adapter on Drive is overwritten.

**Acceptance Scenarios**:

1. **Given** a LoRA adapter already exists on Drive, **When** Stage 5 runs, **Then** a prompt is displayed listing the artifact location and offering a skip or retrain choice before training begins.
2. **Given** the user answers "skip" at the prompt, **When** Stage 5 continues, **Then** the existing adapter is left in place on Drive and training is bypassed entirely.
3. **Given** the user answers "retrain" at the prompt, **When** Stage 5 continues, **Then** training runs to completion, the new adapter is saved to Drive, and the old adapter files are overwritten.
4. **Given** no LoRA adapter exists on Drive, **When** Stage 5 runs, **Then** no prompt is shown and training proceeds without interruption.
5. **Given** the user enters empty input at the Stage 5 prompt, **When** Stage 5 continues, **Then** the behavior is identical to choosing skip.
6. **Given** the user enters unrecognized text at the Stage 5 prompt, **When** Stage 5 prompts again once, **Then** any input (including empty) on the second prompt defaults to skip.

---

### User Story 3 - Unattended Run Mode (Priority: P3)

A user who wants to run the entire notebook unattended (e.g., via Colab's "Run all" without supervision) sets a top-level constant before executing. That constant declares the default answer for all artifact prompts — either "always skip if found" or "always rebuild" — so no interactive input is required during the run.

**Why this priority**: Useful for automated or overnight runs, but the interactive prompts (US1, US2) cover the primary use case. The unattended fallback restores the behavior of the old `FORCE_RETRAIN` flag without requiring users to edit per-stage logic.

**Independent Test**: Set the unattended constant to "skip" and click "Run all" — no prompt pauses occur and any existing artifacts are reused. Set it to "rebuild" and click "Run all" — no prompt pauses occur and all artifacts are rebuilt.

**Acceptance Scenarios**:

1. **Given** the unattended default is set to "skip", **When** any artifact-generating stage runs, **Then** if an artifact exists on Drive the stage skips without prompting; if it does not exist the stage builds normally.
2. **Given** the unattended default is set to "rebuild", **When** any artifact-generating stage runs, **Then** artifacts are always rebuilt without prompting, mirroring the old `FORCE_RETRAIN = True` behavior.
3. **Given** the unattended default is not set (interactive mode), **When** any artifact-generating stage runs, **Then** the user is prompted at each stage where an existing artifact is found.

---

### Edge Cases

- What happens when a Drive artifact exists but is incomplete or corrupted (e.g., `chroma.sqlite3` present but index is empty)? The notebook should treat a corrupted artifact identically to a valid one at the prompt stage — detection is presence-based, not validity-based.
- What if the user does not respond to the prompt (e.g., they walk away)? The notebook waits indefinitely; the unattended default constant is the mechanism for avoiding this.
- What if the user enters invalid input (not a recognized choice)? The prompt repeats exactly once with the same message. If the second response is also unrecognized or empty, the notebook defaults to skip and continues.
- What if Drive is not mounted when Stage 4 or Stage 5 runs? Stage 1 already mounts Drive; if the mount is absent the artifact check produces "not found" and no prompt appears — the stage builds normally.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: At Stage 4 startup, the notebook MUST check whether a complete RAG index already exists on Drive before embedding any documents.
- **FR-002**: At Stage 5 startup, the notebook MUST check whether a LoRA adapter already exists on Drive before initiating training.
- **FR-003**: When an artifact is found on Drive, the notebook MUST present the user with a named choice: skip the stage or rebuild the artifact.
- **FR-004**: The prompt MUST identify which artifact was found and its Drive location so the user can make an informed decision.
- **FR-005**: When the user chooses skip, the notebook MUST proceed to the next stage without modifying the Drive artifact.
- **FR-006**: When the user chooses rebuild, the notebook MUST execute the full stage and overwrite the existing Drive artifact on completion.
- **FR-007**: When no artifact is found on Drive, the notebook MUST proceed to build the artifact without presenting any prompt.
- **FR-008**: A top-level constant MUST allow the user to pre-configure the default choice (skip or rebuild) so the notebook can run without interactive input. When the constant is left unset (its default), the notebook operates in interactive mode and prompts at each stage where an artifact is found.
- **FR-009**: The existing `FORCE_RETRAIN` boolean constant MUST be replaced by the new per-stage prompting system; no residual silent-skip logic tied to `FORCE_RETRAIN` should remain.
- **FR-010**: The artifact detection logic MUST remain consistent with the existing checks (presence of specific sentinel files: `chroma.sqlite3` for the RAG index, `adapter_model.safetensors` for the LoRA adapter).
- **FR-011**: When the user provides empty input at the interactive prompt, the notebook MUST treat it as "skip". When the user provides unrecognized input, the notebook MUST display the prompt a second time; if the second response is also unrecognized or empty, the notebook MUST default to skip and continue.

### Key Entities

- **Drive Artifact**: A file or directory persisted to Google Drive that represents a completed pipeline stage output. For this feature: the ChromaDB index (checked via `chroma.sqlite3`) and the LoRA adapter (checked via `adapter_model.safetensors`).
- **Artifact Prompt**: The interactive choice presented to the user when a Drive artifact is detected. Outcome is either "skip" (load existing) or "rebuild" (run stage and overwrite).
- **Unattended Default**: A top-level notebook constant that pre-answers all artifact prompts, enabling non-interactive "Run all" execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a Drive artifact exists, the user sees the prompt within 2 seconds of the stage cell beginning execution — no silent delay before the question appears.
- **SC-002**: A user who skips Stage 5 avoids waiting for training — the stage completes in under 5 seconds instead of 20–40 minutes.
- **SC-003**: A user who rebuilds any artifact sees the Drive copy overwritten; loading the artifact in a subsequent session uses the newly built version.
- **SC-004**: When the unattended default is configured, the notebook completes all 8 stages without any interactive pause, matching the throughput of the former `FORCE_RETRAIN`-guarded notebook.
- **SC-005**: No `FORCE_RETRAIN` references remain in `notebook.ipynb` after the feature is implemented.

## Assumptions

- Drive is mounted at Stage 1 before any artifact check in Stage 4 or Stage 5 occurs; this ordering is already established in `notebook.ipynb` and is not changed by this feature.
- The sentinel files (`chroma.sqlite3`, `adapter_model.safetensors`) reliably indicate a complete artifact; partial or invalid files that happen to share these names are out of scope.
- The feature is scoped to Stage 4 and Stage 5 only. The Stage 7 notebook snapshot copy-to-Drive is not an artifact prompt candidate because it is a non-destructive copy with no rebuild cost.
- Interactive input is the primary UX; the unattended default is a secondary convenience option, not the primary design target.
- This feature does not change any hyperparameter, model, or generation constant; it is a pure UX improvement to the resumability guard logic.
