---
description: "Task list for Domain-Specialized AI Assistant — POC"
---

# Tasks: Domain-Specialized AI Assistant — POC

**Input**: Design documents from `specs/001-domain-ai-poc/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: No automated test suite (spec explicitly excludes benchmark/LLM-judge pipelines).
Validation is manual per quickstart.md checkpoints.

**Organization**: Tasks follow the risk-first build order from §3.3 of the constitution:
base inference → Gradio UI → RAG → fine-tuning → demo script + persistence.
US1 delivers the working demo; US2 and US3 add repeatability and reproducibility on top.

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

## Path Conventions

```text
notebook.ipynb                    # Main Colab notebook (all pipeline stages)
data/
├── demo_questions.md             # Curated demo question set (US2)
└── training_format_example.jsonl # JSONL format reference (US3)
docs/
└── findings_template.md          # Post-demo findings summary template (US2)
specs/001-domain-ai-poc/
└── quickstart.md                 # Validation guide (reference, not modified here)
```

---

## Phase 1: Setup

**Purpose**: Repository skeleton and notebook scaffold. No model code yet.

- [X] T001 Create `notebook.ipynb` with 8 empty cell groups labelled Stage 0–7 (markdown headings: `# Stage 0: Install & Config`, `# Stage 1: Drive Mount`, etc.) — `notebook.ipynb`
- [X] T002 [P] Create `data/` directory with `.gitkeep`; create `docs/` directory with `.gitkeep` — `data/.gitkeep`, `docs/.gitkeep`
- [X] T003 [P] Create `data/training_format_example.jsonl` with 3 example lines in Llama/Qwen chat format (`{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`), including an inline comment block explaining all field rules per `specs/001-domain-ai-poc/contracts/training-dataset.md` — `data/training_format_example.jsonl`

---

## Phase 2: Foundational

**Purpose**: Core notebook infrastructure that ALL user stories depend on. Must complete before any story work begins.

**⚠️ CRITICAL**: No user story work can begin until Stage 2 smoke test passes.

- [X] T004 Implement Stage 0 cells in `notebook.ipynb`: (a) `!pip install` cell with pinned versions for `unsloth`, `bitsandbytes`, `peft`, `trl`, `transformers`, `datasets`, `sentence-transformers`, `chromadb>=0.5,<1.0`, `gradio`, `langchain-text-splitters`, `pypdf`; (b) constants cell defining all variables from `specs/001-domain-ai-poc/data-model.md` §1 (`MODEL_ID="unsloth/Qwen3.5-9B"`, `SEED=42`, `MAX_SEQ_LEN=2048`, `LORA_R=32`, `LORA_ALPHA=32`, `LORA_TARGETS`, `TRAIN_EPOCHS=3`, `TRAIN_BATCH=4`, `GRAD_ACCUM=2`, `LEARNING_RATE=2e-4`, `CHUNK_SIZE=2000`, `CHUNK_OVERLAP=200`, `TOP_K=3`, `MAX_NEW_TOKENS=512`, `TEMPERATURE=0.1`, `TOP_P=0.9`, `REPETITION_PENALTY=1.1`, `ENABLE_THINKING=False`, `DRIVE_BASE`, `DOCS_PATH`, `DATASET_PATH`, `SYSTEM_PROMPT="You are a helpful assistant. Answer questions clearly and concisely."`, `RETRIEVAL_TEMPLATE="Context:\n{context}\n\nQuestion: {question}"`); (c) seed-fixing cell (`random.seed`, `np.random.seed`, `torch.manual_seed`) — `notebook.ipynb`
- [X] T005 Implement Stage 1 cells in `notebook.ipynb`: (a) `drive.mount('/content/drive')` cell; (b) `os.makedirs` cell creating `DRIVE_BASE/lora_adapter`, `DRIVE_BASE/chroma_index` if they do not exist — `notebook.ipynb`
- [X] T006 Implement Stage 2 cells in `notebook.ipynb`: (a) load `MODEL_ID` with `FastLanguageModel.from_pretrained(model_name=MODEL_ID, max_seq_length=MAX_SEQ_LEN, load_in_4bit=True)` via Unsloth; (b) smoke test cell that generates 1 response to `"Hello, what is 2+2?"` and prints it with a `✅ Base model loaded` confirmation — `notebook.ipynb`

**Checkpoint**: `✅ Base model loaded` appears in Stage 2 output. Proceed to user stories only after this passes.

---

## Phase 3: User Story 1 — Live Side-by-Side Comparison (Priority: P1) 🎯 MVP

**Goal**: A shareable Gradio link where a stakeholder types any question and both model variants answer simultaneously.

**Independent Test**: Open the Gradio share URL, type a domain-specific question, click Submit, and verify (a) a loading indicator appears on each panel while inference runs, (b) both panels populate with distinct answers, (c) no blank/error state on a clean run.

- [X] T007 [US1] Implement Stage 3 cells in `notebook.ipynb` — Walking Skeleton UI: (a) define `infer_base(question: str) -> str` that formats messages as `[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":question}]`, tokenizes with `tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")`, calls `model.generate()` with `gen_config` dict (`max_new_tokens`, `temperature`, `top_p`, `repetition_penalty`, `enable_thinking=False`), and returns decoded text, wrapping the call in `try/except` to return `"⚠️ Generation failed — please retry."` on any exception; (b) build `gr.Blocks()` layout with one `gr.Textbox` input, two side-by-side `gr.Textbox` output panels labelled `"Standard Model"` and `"Specialized Model"`, and one `gr.Button("Submit")`; (c) wire button `.click()` to `infer_base` on BOTH output panels simultaneously; (d) assign the Blocks instance to `skeleton_demo` and call `skeleton_demo.launch(share=True, server_name="0.0.0.0")`; (e) manually verify share URL opens and both panels respond to a test question — `notebook.ipynb`
- [X] T008 [US1] Implement Stage 4 cells in `notebook.ipynb` — RAG Pipeline: (a) recursive file loader reading all files under `DOCS_PATH` — for `.txt`/`.md` use `Path.read_text(encoding="utf-8")`; for `.pdf` use `pypdf.PdfReader` to extract text page-by-page and concatenate before splitting; (b) `RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)` to produce chunks; (c) `SentenceTransformer("all-MiniLM-L6-v2")` for CPU embedding; (d) `chromadb.PersistentClient(path=f"{DRIVE_BASE}/chroma_index")` collection `"domain_docs"` — drop and recreate on each run; (e) batch `collection.add()` with chunk texts, embeddings, and `{"source": filename, "chunk_id": i}` metadata; (f) `retrieve(query: str, k: int = TOP_K) -> str` function returning the top-k chunk texts joined by `"\n---\n"` (raw context string, no question appended — prompt assembly uses `RETRIEVAL_TEMPLATE`); (g) print `✅ Vector index saved to Drive` with chunk count — `notebook.ipynb`
- [X] T009 [US1] Implement Stage 5 cells in `notebook.ipynb` — Fine-Tuning: (a) JSONL validation cell: load `DATASET_PATH`, check file exists, UTF-8 decode, assert every line has `messages[0].role=="user"` and `messages[1].role=="assistant"` with non-empty content, assert line count >= 200, warn if < 500 — abort with `ValueError` and line number on failure; (b) `shutil.copy(DATASET_PATH, f"{DRIVE_BASE}/training_dataset.jsonl")`; (c) apply LoRA with `FastLanguageModel.get_peft_model(model, r=LORA_R, lora_alpha=LORA_ALPHA, target_modules=LORA_TARGETS, lora_dropout=LORA_DROPOUT, bias="none")`; (d) `SFTTrainer` with `max_seq_length=MAX_SEQ_LEN`, `num_train_epochs=TRAIN_EPOCHS`, `per_device_train_batch_size=TRAIN_BATCH`, `gradient_accumulation_steps=GRAD_ACCUM`, `learning_rate=LEARNING_RATE`, cosine scheduler; (e) `trainer.train()`; (f) `model.save_pretrained(f"{DRIVE_BASE}/lora_adapter")`; (g) print `✅ Adapter saved to Drive` — `notebook.ipynb`
- [X] T010 [US1] Implement Stage 6 cells in `notebook.ipynb` — Full Pipeline Load: (a) reload base model in NF4 (same `FastLanguageModel.from_pretrained` as Stage 2); (b) `PeftModel.from_pretrained(base_model, f"{DRIVE_BASE}/lora_adapter")`; (c) reconnect ChromaDB `PersistentClient(path=f"{DRIVE_BASE}/chroma_index")`; (d) define `infer_specialized(question: str) -> str` that calls `retrieve(question)`, formats prompt as `RETRIEVAL_TEMPLATE.format(context=context, question=question)`, wraps in messages `[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":formatted_prompt}]`, tokenizes with `tokenizer.apply_chat_template`, generates with same `gen_config`, returns decoded text, wraps in `try/except` returning `"⚠️ Generation failed — please retry."` on failure; (e) define `infer_rag_only(question: str) -> str` using the same pattern as `infer_specialized` but running on `base_model` (no LoRA adapter) — this powers the middle "Standard + Docs" attribution panel; (f) print `✅ Specialized model ready` — `notebook.ipynb`
- [X] T011 [US1] Implement Stage 7 cells in `notebook.ipynb` — Full Demo UI: (a) call `gr.close_all()` as the very first line to release the Stage 3 skeleton UI and free the Gradio port; (b) rebuild `gr.Blocks()` with three columns: `"Standard Model"` (calls `infer_base`, no adapter, no RAG), `"Standard + Docs"` (calls `infer_rag_only`, base model + RAG via `RETRIEVAL_TEMPLATE`, no adapter — for attribution analysis), `"Specialized Model"` (calls `infer_specialized`, fine-tuned adapter + RAG); (c) all output `gr.Textbox` components with `interactive=False`; (d) single `gr.Button("Submit")` wiring all three panels simultaneously via `.click()`; (e) Gradio's native spinner handles the loading indicator automatically while the handler runs — no extra code needed; (f) `demo.launch(share=True, server_name="0.0.0.0")`; (g) print the share URL prominently — `notebook.ipynb`
- [ ] T012 [US1] Manual validation of Stage 7 demo UI: open share URL in browser; submit one domain-specific question; verify (a) loading spinner visible on each panel during inference, (b) all panels populate with answers, (c) Specialized Model panel answer is distinguishably different from Standard Model panel, (d) `enable_thinking=False` confirmed — no `<think>...</think>` prefix in any response

**Checkpoint**: All three panels answer simultaneously, loading indicators visible, no `<think>` prefixes. User Story 1 is complete and independently demonstrable.

---

## Phase 4: User Story 2 — Curated Demonstration Script (Priority: P2)

**Goal**: A prepared set of 5–10 questions with documented expected-answer characteristics, plus a post-demo findings template.

**Independent Test**: Any team member opens the Gradio link and submits each question from `data/demo_questions.md` in sequence; the contrast between panels is observable without domain expertise.

- [X] T013 [P] [US2] Create `data/demo_questions.md` with the following structure and placeholder content: (a) `## Domain-Specific Questions` section — 5 placeholder questions of the form `1. [REPLACE: domain question] **Expected**: [REPLACE: description of what a good answer contains]`; (b) `## Terminology Questions` section — 2 placeholder questions; (c) `## General Sanity-Check Questions` section — 2 placeholder questions (e.g., "What is the capital of France?"); include a header note explaining the 3-category structure per `specs/001-domain-ai-poc/contracts/training-dataset.md` and `spec.md` §FR-008 — `data/demo_questions.md`
- [X] T014 [P] [US2] Create `docs/findings_template.md` with a one-page post-demo findings template containing sections: `## Demo Details` (date, attendees, domain, Gradio URL), `## Observations` (table: question | Standard Model quality | Specialized Model quality | Contrast visible?), `## Attribution` (fine-tuning contribution vs. RAG contribution based on optional 3rd panel), `## Recommendation` (radio: Invest / Iterate / Stop — with one-line justification) — `docs/findings_template.md`

**Checkpoint**: `data/demo_questions.md` and `docs/findings_template.md` exist and are filled with the correct structure. Any facilitator can run a demo using the question set.

---

## Phase 5: User Story 3 — Reproducible Specialization Pipeline (Priority: P3)

**Goal**: A technically capable colleague runs `notebook.ipynb` top-to-bottom on a fresh Colab session and arrives at the same specialized model without manual assistance beyond uploading domain documents and `training_dataset.jsonl`.

**Independent Test**: On a fresh Colab session (no cached Drive artifacts), run all cells; verify all 5 quickstart.md checkpoints pass and artifacts appear in Drive.

- [X] T015 [US3] Add T4 fallback auto-detection cell to Stage 0 in `notebook.ipynb`, inserted after the constants block: query `torch.cuda.get_device_properties(0).total_memory`; if < 24 GB (T4/L4), override `MODEL_ID="unsloth/Qwen3-4B-bnb-4bit"`, `MAX_SEQ_LEN=512`, `LORA_R=8`, `LORA_ALPHA=8`, `LORA_TARGETS=["q_proj","v_proj"]`, `TRAIN_BATCH=1`, `GRAD_ACCUM=8`, `TRAIN_EPOCHS=2`; print GPU name + selected config profile (`"A100 config"` or `"T4 fallback config"`) — `notebook.ipynb`
- [X] T016 [US3] Add `FORCE_RETRAIN = False` constant to the Stage 0 constants block; add resumability guard cells at the start of Stage 4 (skip ChromaDB build if `DRIVE_BASE/chroma_index` exists and `not FORCE_RETRAIN`), Stage 5 (skip training if `DRIVE_BASE/lora_adapter/adapter_model.safetensors` exists and `not FORCE_RETRAIN`), and Stage 6 (always load from Drive — no guard needed); print `⏩ Skipping [stage] — artifact found on Drive` when guard triggers — `notebook.ipynb`
- [X] T017 [US3] Add optional Drive snapshot cell to Stage 7 in `notebook.ipynb`: `shutil.copy("/content/notebook.ipynb", f"{DRIVE_BASE}/notebook.ipynb")`; print `✅ Notebook snapshot saved to Drive` — `notebook.ipynb`
- [ ] T018 [US3] End-to-end reproducibility validation: on a fresh Colab session, upload domain docs and `training_dataset.jsonl`, run all cells top-to-bottom; verify all 5 checkpoints from `specs/001-domain-ai-poc/quickstart.md` pass in sequence (base model loaded, walking skeleton UI, RAG index built, adapter saved, full demo UI live); verify Drive contains `lora_adapter/`, `chroma_index/`, `training_dataset.jsonl`, `notebook.ipynb`

**Checkpoint**: Fresh-session run completes without manual intervention beyond uploads. All Drive artifacts present. User Story 3 is complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish line — confirm zero spend, run full quickstart validation, tidy output.

- [X] T019 [P] Add per-stage elapsed time logging: wrap each Stage cell group with `stage_start = time.time()` at top and `print(f"Stage N complete in {time.time()-stage_start:.1f}s")` at bottom — `notebook.ipynb`
- [ ] T020 Run complete quickstart.md walkthrough end-to-end: verify all 5 checkpoints pass (§Checkpoint 1–5 in `specs/001-domain-ai-poc/quickstart.md`); document any deviations in a `## Deviations` section at the top of `notebook.ipynb` per §3.4 of the constitution
- [ ] T021 [P] Confirm $0 total spend: verify all installed packages have Apache 2.0 / MIT / BSD licences; confirm no paid API calls in any cell (grep for `openai`, `anthropic`, `cohere`, `replicate` in notebook source); confirm only Colab Pro+ compute was used
- [X] T022 [P] [Optional] Export merged GGUF for local inference: call `model.save_pretrained_merged(f"{DRIVE_BASE}/gguf_export", tokenizer, save_method="merged_4bit")` via Unsloth's `save_pretrained_merged` helper; verify output file appears in Drive — skip if Drive quota is tight (GGUF is ~5 GB); record in `## Deviations` cell if omitted — `notebook.ipynb`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1; Stage 2 smoke test GATES all user story work
- **US1 (Phase 3)**: Depends on Foundational; tasks T007–T012 are strictly sequential (each stage builds on the previous)
- **US2 (Phase 4)**: Depends on Phase 3 completion (demo questions require knowing what the model can answer); T013 and T014 are parallel with each other
- **US3 (Phase 5)**: T015 and T016 can start after T006 (model load); T017 after T011; T018 after T015–T017 are complete
- **Polish (Phase 6)**: Depends on all user stories complete

### Within User Story 1

Tasks T007–T012 are strictly sequential — each stage's output is the input to the next:
```
T007 (walking skeleton) → T008 (RAG) → T009 (fine-tune) → T010 (full load) → T011 (full UI) → T012 (validate)
```

### Parallel Opportunities

```bash
# Phase 1 — after T001:
T002 (create data/ + docs/)
T003 (training_format_example.jsonl)
# Both can run simultaneously

# Phase 4 — both documents independent:
T013 (demo_questions.md)
T014 (findings_template.md)

# Phase 5 — T015 and T016 can run simultaneously (different cells):
T015 (T4 fallback detection cell)
T016 (FORCE_RETRAIN guard cells)

# Phase 6 — independent checks:
T019 (elapsed time logging)
T021 (spend confirmation)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T006) — CRITICAL, gates everything
3. Complete Phase 3: User Story 1 (T007–T012)
4. **STOP and VALIDATE**: Open Gradio link, run 3 questions, verify contrast
5. Share link with a stakeholder for initial feedback

### Incremental Delivery

1. Setup + Foundational → base model running *(Phase 1–2)*
2. T007 → walking skeleton Gradio with base model on both panels *(first shareable demo)*
3. T008 → RAG pipeline wired to right panel *(improved specialized panel)*
4. T009–T011 → fine-tuning + full demo UI *(complete POC)*
5. T013–T014 → demo script + findings template *(US2 complete)*
6. T015–T018 → reproducibility hardening *(US3 complete)*

### Constitution Build Order Compliance (§3.3)

| Build order step | Tasks |
|---|---|
| 1. Base model inference | T004, T005, T006 |
| 2. Gradio dual-panel UI | T007 |
| 3. RAG pipeline | T008 |
| 4. Fine-tuning + adapter | T009, T010 |
| 5. Demo script + persistence | T011, T012, T013, T014, T017 |

---

## Notes

- `[P]` tasks touch different files or independent notebook cells — no merge conflicts
- US1 tasks T007–T012 are in the same file (`notebook.ipynb`) but strictly sequential — do not parallelize
- US2 tasks (T013, T014) are pure content authoring — domain expert input needed for `[REPLACE]` placeholders
- T018 (reproducibility run) MUST be on a fresh session — do not reuse the development session
- Constitution §3.4: any deviation from the build order MUST be recorded in a `## Deviations` cell at the top of `notebook.ipynb`
- `enable_thinking=False` MUST appear in every `gen_config` usage (T007, T010, T011) — do not omit
