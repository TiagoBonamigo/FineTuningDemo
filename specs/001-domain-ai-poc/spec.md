# Feature Specification: Domain-Specialized AI Assistant — Proof of Concept

**Feature Branch**: `001-domain-ai-poc`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Domain-Specialized AI Assistant: Proof of Concept"

## Overview

General-purpose AI models answer domain-specific questions poorly because their training data does
not include the organization's internal knowledge. This POC produces a live, side-by-side
demonstration that lets any observer judge — with their own eyes — whether adapting a freely
available AI model to a specific domain produces a visible quality improvement.

The deliverable is a shared browser link: one question box, two simultaneous answer panels
(standard model vs. specialized model), optionally a third panel (standard model with document
access). No technical background is needed to see the difference.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Live Side-by-Side Comparison (Priority: P1)

A sponsor or skeptical stakeholder opens a shared link in any browser. They type a question — their
own, not a pre-scripted one — press one button, and both the standard model and the specialized
model answer simultaneously. The contrast in answer quality is visible without any explanation.

**Why this priority**: This is the entire purpose of the POC. Without this, nothing else matters.
Every other user story either supports or extends this core moment.

**Independent Test**: Open the shared Gradio link, type a domain-specific question, press submit,
and verify two populated answer panels appear. Target response time is 30 seconds on A100; batch
output (panels appear all at once when generation completes) is acceptable. No other setup required.

**Acceptance Scenarios**:

1. **Given** the shared Gradio link is open, **When** a stakeholder types any question and submits,
   **Then** both panels populate with answers from their respective model variants simultaneously.
2. **Given** the same question is sent to both variants, **When** a domain-specific question is
   asked, **Then** the specialized model's answer is noticeably more relevant, accurate, or
   appropriately scoped to the domain than the standard model's answer.
3. **Given** a general (non-domain) question is asked, **When** it is submitted,
   **Then** both panels produce reasonable answers, confirming specialization did not degrade
   general capability.

---

### User Story 2 — Curated Demonstration Script (Priority: P2)

A product owner or demo facilitator has a prepared set of 5–10 questions with documented
expected-answer characteristics. Any team member can run a live demo using this set without
relying on improvisation or domain expertise in the moment.

**Why this priority**: Repeatability protects the demo from poor question choices that could
accidentally make both models look bad or mask real differences.

**Independent Test**: Load the demo question set, send each question through the Gradio interface
one at a time, and verify that each answer pair reflects the expected quality contrast described
in the question set document.

**Acceptance Scenarios**:

1. **Given** the demo question set exists, **When** any team member opens the Gradio link and
   submits each prepared question, **Then** the answers consistently demonstrate the quality
   contrast without facilitation expertise.
2. **Given** the question set includes domain-only questions, terminology-heavy questions, and
   1–2 general sanity checks, **When** each category is tested, **Then** domain questions show
   clear improvement, and general questions show no degradation.

---

### User Story 3 — Reproducible Specialization Pipeline (Priority: P3)

A technically capable colleague starts with a fresh Colab session, uploads the domain documents
and training dataset, and runs the notebook top to bottom. They arrive at the same specialized
model artifact without manual assistance.

**Why this priority**: A POC that can only be re-run by its original author is a dead end. The
pipeline must be a seed for a real project, not a throwaway.

**Independent Test**: On a fresh Colab session (no cached state), run the notebook from the first
cell to the last using only the documented inputs. Verify the resulting model artifacts match
expected file sizes and pass basic inference smoke tests.

**Acceptance Scenarios**:

1. **Given** a fresh Colab session with the notebook and domain documents, **When** all cells
   are run top to bottom, **Then** the specialization completes without manual intervention
   beyond the initial document upload.
2. **Given** the notebook completes, **When** the resulting model is queried with domain
   questions, **Then** it produces answers consistent with the original demo.
3. **Given** training completes, **When** artifacts are inspected,
   **Then** the LoRA adapter and vector index are saved to Google Drive and downloadable.

---

### Edge Cases

- What happens when a stakeholder asks a question that is completely outside the domain?
  The standard model answers normally; the specialized model answers normally too (fine-tuning
  on a narrow domain should not significantly impair general capability on a small model).
- What if the two model panels produce very similar answers for domain questions?
  This is a valid finding: the domain may not be distinctive enough, or the model size may
  be too small. It should be reported, not hidden.
- What if the temporary Gradio link expires mid-demo?
  The link is ephemeral by design; the Colab session must be restarted to regenerate it.
  This is expected behavior and should be disclosed to demo attendees in advance.
- What if Colab disconnects during training?
  Drive persistence means the training checkpoint is recoverable. The notebook must checkpoint
  frequently enough that loss does not exceed one epoch of work.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The demonstration interface MUST accept a single free-text question and submit it
  to both model variants simultaneously with one user action.
- **FR-002**: The interface MUST display the standard model's answer and the specialized model's
  answer in distinct, clearly labeled panels. Each panel MUST show a visible loading indicator
  (spinner or "Generating…" text) while its inference is running, replacing it with the answer
  when generation completes. If inference fails (e.g., GPU out of memory, model load error),
  the panel MUST display a brief plain-language error message (e.g., "Generation failed — please
  retry") rather than remaining blank.
- **FR-003**: The standard model variant MUST operate with no domain adaptation: no fine-tuning,
  no retrieved context.
- **FR-004**: The specialized model variant MUST apply both domain fine-tuning (LoRA adapter) and
  retrieval-augmented context from the domain document index.
- **FR-005**: Both model variants MUST use identical generation parameters (temperature, max
  tokens, top-p) and identical system prompt scaffolding.
- **FR-006**: The interface MUST be shareable via a temporary public link accessible from any
  browser without installation or login.
- **FR-007**: An optional third panel SHOULD be available to show the standard model with
  document retrieval but without fine-tuning, enabling attribution of improvement.
- **FR-008**: The demonstration question set MUST contain 5–10 curated questions with documented
  expected-answer characteristics, covering: domain-only questions, terminology-heavy questions,
  and 1–2 general sanity-check questions.
- **FR-009**: The specialization notebook MUST run end-to-end on a fresh Colab session without
  manual intervention beyond uploading the domain documents and the manually authored training
  dataset JSONL file.
- **FR-010**: All artifacts (LoRA adapter, vector index, training dataset, notebook) MUST be
  persisted to Google Drive or be individually downloadable upon notebook completion.
- **FR-011**: The entire POC MUST use only open-weight models and free, open-source libraries.
  No paid APIs, licensing fees, or additional cloud subscriptions are permitted.
- **FR-012**: After the first stakeholder demo, a one-page findings summary MUST be produced
  documenting what improved, what did not, and a recommendation (invest / iterate / stop).

### Key Entities

- **Domain Documents**: Non-confidential source files (PDFs, text, markdown) that define the
  target knowledge domain. Chosen and provided by the project owner.
- **Training Dataset**: JSONL file of instruction/response pairs manually authored by a domain
  expert and uploaded to the Colab session; min 200 pairs, target 500–1,000. The file is an
  external input to the notebook, not generated by it.
- **LoRA Adapter**: Fine-tuned model delta weights (~100 MB) representing the domain specialization.
  Applied on top of the base model at inference time.
- **Vector Index**: Embedded document chunk store (ChromaDB or FAISS) enabling retrieval-augmented
  generation. Built from domain documents at notebook runtime.
- **Demo Question Set**: A documented list of 5–10 questions with expected-answer descriptions,
  organized into domain-only, terminology, and general sanity-check categories.
- **Findings Summary**: A one-page document produced after the first live demo, capturing
  observable differences, attribution (fine-tune vs. RAG), and a go/iterate/stop recommendation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Non-expert observers (no ML background required) consistently rate the specialized
  model's answers as more relevant or accurate than the standard model's answers for at least
  4 out of 5 domain-specific questions in the curated demo set.
- **SC-002**: Any team member can facilitate a repeatable demo using the curated question set
  and the shared link, without domain expertise or real-time improvisation.
- **SC-003**: A technically capable colleague can reproduce the full specialization pipeline on
  a fresh Colab session in under 2 working hours, starting from the notebook and domain documents.
- **SC-004**: Total project spend at completion is $0 in licensing fees, API charges, or cloud
  subscriptions outside the existing Colab Pro+ subscription.
- **SC-005**: The findings summary clearly identifies whether improvement is attributable
  primarily to fine-tuning, to document retrieval, or to both — enabling an informed
  build-vs-buy conversation with stakeholders.
- **SC-006**: General-capability sanity-check questions produce answers of comparable quality
  from both variants, confirming specialization did not degrade the model's general usefulness.

## Assumptions

- Domain documents are non-confidential and may be shared via a temporary public Gradio link.
- The project owner (domain expert) will contribute time to: select domain documents, manually
  author the 200–1,000 JSONL training pairs, and review the curated demo question set. This is
  the primary bottleneck for the POC timeline (not the technology).
- The implementing team has access to the existing Google Colab Pro+ subscription.
- One person with Python and Jupyter familiarity can complete the POC in approximately 2 working
  days: ~1 day for the working demo, ~1 day for specialization and demo preparation.
- The demo is a one-time or occasional event; no uptime SLA or persistent infrastructure is needed.
- The target audience for the demo is business stakeholders; no ML knowledge is assumed on their part.
- The specific domain to be demonstrated is deferred to the project owner; the POC methodology
  is domain-agnostic and works by substituting the input documents.
- The temporary Gradio share link being ephemeral (valid only while the Colab session is active)
  is acceptable and will be disclosed to demo attendees in advance.

## Clarifications

### Session 2026-07-20

- Q: How will the 200–1,000 JSONL training pairs be produced? → A: Manually authored by a domain expert and uploaded as a pre-built JSONL file; not generated by the notebook.
- Q: Should the 30-second panel response time be a hard requirement or aspirational guideline? → A: Aspirational guideline only; batch output (panels appear all at once) is acceptable; no streaming required.
- Q: What should Gradio panels show while inference is running? → A: Each panel MUST show a visible loading indicator (spinner or "Generating…" text) until its answer arrives.
- Q: What should a panel display when inference fails? → A: A brief plain-language error message (e.g., "Generation failed — please retry"); panel must not remain blank.
