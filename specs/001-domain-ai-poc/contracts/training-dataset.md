# Contract: Training Dataset Format

**Feature**: `specs/001-domain-ai-poc`
**Interface type**: Data input (JSONL file, manually authored by domain expert)
**Date**: 2026-07-20

---

## Summary

The training dataset is a JSONL file of instruction/response pairs in Llama 3 chat format,
manually authored by a domain expert and uploaded to the Colab session before Stage 5 runs.
The notebook validates the file on load; cells abort with a clear error message if validation fails.

---

## File specification

| Property | Value |
|---|---|
| Format | JSON Lines (`.jsonl`) — one JSON object per line |
| Encoding | UTF-8, no BOM |
| Line endings | LF or CRLF both accepted |
| Minimum size | 200 lines |
| Target size | 500–1,000 lines |
| Upload path | `/content/training_dataset.jsonl` (configurable via `DATASET_PATH`) |

---

## Per-line schema

```json
{
  "messages": [
    {"role": "user",      "content": "<string>"},
    {"role": "assistant", "content": "<string>"}
  ]
}
```

### Field rules

| Field | Type | Rule |
|---|---|---|
| `messages` | array | MUST contain exactly 2 elements |
| `messages[0].role` | string | MUST be `"user"` |
| `messages[0].content` | string | MUST be non-empty |
| `messages[1].role` | string | MUST be `"assistant"` |
| `messages[1].content` | string | MUST be non-empty |
| System turn | — | MUST NOT be present; the notebook injects the system prompt at training time |

### Content guidance (for domain expert authoring)

- Questions should be phrased as a user would naturally ask them (not as keyword lookups).
- Answers should be complete, accurate, and use the domain's standard terminology and phrasing.
- Aim for answer length of 50–300 words — enough to be informative, short enough to fit within
  `MAX_SEQ_LEN=512`.
- Include a variety of question types: definitional ("What is X?"), procedural ("How do I do Y?"),
  comparative ("What is the difference between A and B?"), and edge-case ("What happens when Z?").
- Do NOT include questions whose answers are widely known from general training data — the point
  is to teach knowledge the base model does not have.

---

## Validation checks (performed by notebook cell at Stage 5 load time)

```
1. File exists at DATASET_PATH
2. File is valid UTF-8
3. Every line parses as valid JSON
4. Every object contains "messages" key with array of length 2
5. Element 0 has role="user" and non-empty content
6. Element 1 has role="assistant" and non-empty content
7. Total line count >= 200 (warning if < 500)
```

On any validation failure: cell raises `ValueError` with the line number and error description.

---

## Full example

```jsonl
{"messages": [{"role": "user", "content": "What documents are required for a Type-A permit application?"}, {"role": "assistant", "content": "A Type-A permit application requires: (1) completed Form DA-14, (2) a site plan drawn to 1:500 scale, (3) a structural engineer's certificate if the proposed structure exceeds 3 m in height, and (4) proof of land ownership or a notarised lease agreement. All documents must be submitted in triplicate."}]}
{"messages": [{"role": "user", "content": "How long does the standard review process take?"}, {"role": "assistant", "content": "The standard review process takes 15 working days from the date of receipt of a complete application. If additional information is requested, the clock pauses until the information is received and restarts from day 1."}]}
```

---

## Relationship to other contracts

- See [drive-artifacts.md](drive-artifacts.md) for where a copy of the uploaded file is persisted.
- See [data-model.md](../data-model.md) §2 for the full data model specification.
