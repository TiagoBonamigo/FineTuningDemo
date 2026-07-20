# Contract: Gradio Demo UI

**Feature**: `specs/001-domain-ai-poc`
**Interface type**: Web UI (Gradio Blocks, public share link)
**Date**: 2026-07-20

---

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Domain AI Assistant — POC Demo                             │
│                                                             │
│  Question                                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ [text input — multiline, placeholder: "Ask a question"] │ │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [ Submit ]                                                 │
│                                                             │
│  Standard Model     │  Standard + Docs (optional)  │  Specialized Model  │
│  ┌──────────────┐   │  ┌──────────────────────┐    │  ┌──────────────┐   │
│  │              │   │  │                      │    │  │              │   │
│  │  (answer or  │   │  │  (answer or          │    │  │  (answer or  │   │
│  │   loading or │   │  │   loading or         │    │  │   loading or │   │
│  │   error)     │   │  │   error)             │    │  │   error)     │   │
│  └──────────────┘   │  └──────────────────────┘    │  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

The middle panel ("Standard + Docs") is optional and may be omitted. Its presence or absence
is a configuration choice at notebook launch time.

---

## Components

### Input

| Component | Type | Behavior |
|---|---|---|
| Question box | `gr.Textbox(lines=3, label="Question", placeholder="Ask a question…")` | Accepts free-text; multiline |
| Submit button | `gr.Button("Submit")` | Triggers inference on both (or all three) panels simultaneously |

### Output panels

| Panel | Label | Model variant |
|---|---|---|
| Left | `"Standard Model"` | Base model, no adapter, no RAG context |
| Middle (optional) | `"Standard Model + Document Access"` | Base model, no adapter, with RAG context |
| Right | `"Specialized Model"` | Base model + LoRA adapter + RAG context |

Each panel is a `gr.Textbox(label=<label>, interactive=False)`.

---

## Behavior Specification

### Normal flow

1. User types a question and clicks Submit.
2. Each panel shows a loading indicator (Gradio's native spinner overlay on the output
   component) while its inference handler runs.
3. When generation completes, the panel displays the generated text.
4. Both panels populate with answers before the UI accepts a new submission (batch mode).

### Error flow

If inference raises any exception (GPU OOM, model load failure, etc.):
- The affected panel displays the string: `"⚠️ Generation failed — please retry."`
- The other panel(s) are unaffected (each panel's handler is wrapped independently).
- No traceback or technical detail is surfaced to the user.

### Empty / initial state

- All output panels are empty (`""`) on page load.
- Submit button is enabled immediately.

---

## Inference handler contract

Each panel maps to one Python function with this signature:

```python
def infer_standard(question: str) -> str:
    """
    Returns: generated answer string, or error message string on failure.
    Side effects: none (read-only model access).
    """

def infer_specialized(question: str) -> str:
    """
    Returns: generated answer string, or error message string on failure.
    Internally: retrieves top-k context from ChromaDB, prepends to prompt, generates.
    """
```

Both functions MUST use the shared `gen_config` dict for all generation parameters (§IV).

---

## Launch parameters

```python
demo.launch(share=True, server_name="0.0.0.0")
```

- `share=True`: generates temporary public URL (valid for 72 hours from Gradio's free sharing
  service; valid while the Colab session is active).
- `server_name="0.0.0.0"`: required for the Colab sandbox port to be accessible.

---

## Constraints

- No user authentication (§2.5 / §Scope).
- No persistence of submitted questions or generated answers (§2.5).
- No analytics or usage tracking (§2.5).
- The share link is ephemeral and tied to the active Colab session lifetime.
