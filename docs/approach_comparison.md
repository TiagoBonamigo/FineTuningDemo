# Adapting Open-Source LLMs to a Domain — Approach Comparison & Deterministic Calculation

> **Purpose**: A presentation baseline for the Domain LLM Comparison POC. It compares four ways
> to make a free, open-weight model useful for a specific domain, weighs the pros and cons of
> each, and shows how any of them ties into a **calculation function or MCP tool** to handle the
> tasks LLMs are fundamentally bad at: exact, deterministic computation.
>
> **Audience**: Business stakeholders and technical reviewers evaluating a *build vs. buy* /
> *invest vs. iterate vs. stop* decision (see `docs/findings_template.md`, spec §SC-005).
>
> **This POC's domain**: laytime & voyage-charterparty calculation (NOR validity, SHEX/SHINC/WWD, SOF
> analysis, demurrage/despatch) — see the repo `README.md`. The framework below is domain-agnostic;
> §9 grounds it in the laytime specifics.
>
> **Date**: 2026-07-21 · **Scope**: Qualitative, POC-level. No benchmark claims.

---

## 1. Executive Summary (the one-slide version)

Two independent problems block a general model from being useful in a specialized domain:

1. **The knowledge & behavior gap** — a stock model doesn't know your internal facts and doesn't
   speak in your domain's terminology, format, or tone. → Solved by **fine-tuning** and/or **RAG**.
2. **The precision gap** — LLMs *approximate* arithmetic and multi-step calculations; they cannot
   be trusted with numbers that must be exact. → Solved by **delegating to deterministic code**
   (a calculation function or an MCP tool), *not* by more training or more retrieval.

The four approaches below all address problem (1). None of them fixes problem (2) — that requires
the tool layer described in §6–7. The strongest architecture combines them:

> **Fine-tuning** teaches the model *how to behave*. **RAG** gives it *fresh facts to ground on*.
> A **calculation function / MCP** gives it *a way to be exactly right about numbers*.

| Approach | Knows domain facts | Stays current | Speaks the domain | Exact at math | Build effort |
|---|---|---|---|---|---|
| Pure open-source model | ❌ | ❌ | ❌ | ❌ | Lowest |
| Fine-tuned, no RAG | ⚠️ frozen | ❌ | ✅ | ❌ | Medium |
| Untuned + RAG | ✅ (if retrieved) | ✅ | ❌ | ❌ | Medium |
| Fine-tuned + RAG | ✅ | ✅ | ✅ | ❌ | Highest |
| **+ Calculation function / MCP** | — | — | — | ✅ | +Small |

---

## 2. The Two Problems We're Actually Solving

It is worth being explicit that "make the AI good at our domain" is **two orthogonal axes**, not one.
Conflating them is the most common reason a demo underwhelms.

```
                         PRECISION AXIS
                    (exact / deterministic)
                              ▲
                              │   ← solved ONLY by a calculation
                              │      function or MCP tool
                              │
   KNOWLEDGE & BEHAVIOR AXIS  │
   (facts, terminology,       │
    tone, format)  ───────────┼───────────────►
   ← solved by fine-tuning     │
     and/or RAG                │
```

- **Knowledge & behavior axis** — *Does it know our facts and sound like us?* Fine-tuning and RAG
  are the two levers. This is what the four-way comparison in §3–5 is about.
- **Precision axis** — *When it does math, is it exactly right, every time?* No amount of tuning or
  retrieval makes a probabilistic token predictor a reliable calculator. This axis is handled by the
  deterministic tool layer in §6–7.

Keeping the axes separate is what lets us say honestly: *"the fine-tuned + RAG model is the best
answer engine, and it should hand every calculation to a function that is exactly right."*

---

## 3. The Four Approaches (the 2×2 matrix)

Two levers — **fine-tuning** (adapt the weights) and **RAG** (retrieve context at query time) —
combine into four configurations:

|                      | **No RAG** | **With RAG** |
|----------------------|------------|--------------|
| **Not fine-tuned**   | ① Pure open-source model *(baseline)* | ③ Untuned + RAG |
| **Fine-tuned (LoRA)**| ② Fine-tuned, no RAG | ④ Fine-tuned + RAG *(specialized)* |

**What each lever actually does:**

| Lever | Changes… | Good at teaching | Cannot provide |
|---|---|---|---|
| **Fine-tuning** (LoRA/QLoRA) | the model's *weights* | tone, format, terminology, task behavior, "how to answer" | fresh facts, source citations, exact math |
| **RAG** (retrieval) | the model's *prompt/context* | up-to-date facts, source-grounding, "what to answer with" | behavior/format/tone changes, exact math |

A useful mental model: **fine-tuning is long-term memory and manners; RAG is an open-book exam;
neither is a calculator.**

---

## 4. Pros & Cons — Deep Dive per Approach

### ① Pure Open-Source Model (baseline)

*The stock instruction-tuned model, no adaptation. In this POC this is the "Standard Model" panel.*

**Pros**
- Simplest possible setup — load and run; nothing to build or maintain.
- Zero data-preparation labor (no training set, no document corpus).
- Fully general; no risk of domain over-fitting or capability regression.
- Fastest to a first demo; the honest baseline the other three are measured against.

**Cons**
- No knowledge of your internal facts, products, policies, or edge cases.
- Generic tone; misuses or ignores domain terminology.
- **Confidently hallucinates** when asked domain questions — no grounding, no citations.
- Cannot be pointed at "our documents"; knowledge is frozen at its pre-training cutoff.

**Best for**: establishing the baseline; general-purpose Q&A; the control in the comparison.

---

### ② Fine-Tuned, No RAG

*A LoRA adapter trained on domain Q&A pairs, but no document retrieval at query time. In this POC
this is the "Specialized (No RAG)" panel.*

**Pros**
- Answers in the **domain's voice, format, and terminology** — behavior lives "in the weights."
- No retrieval step → shorter prompts, lower per-query latency, works fully offline.
- Can teach behaviors RAG can't: house answer format, refusal on out-of-scope, reasoning style.
- Consistent style across every answer without prompt engineering.

**Cons**
- **Knowledge is frozen at training time** — updating a fact means re-training, not editing a file.
- Facts learned from examples are **unreliable and un-citeable**; it can't show its sources.
- Still hallucinates specifics confidently (memorized patterns ≠ a fact store).
- Requires a **curated training set** (200–1,000 hand-authored pairs) — the primary bottleneck
  (spec §Assumptions), and a domain-expert time cost.
- Risk of **catastrophic forgetting** — degrading general ability (why the POC keeps sanity-check
  questions, §SC-006).

**Best for**: fixed style/format/terminology requirements; stable knowledge that rarely changes;
latency- or offline-sensitive deployments.

---

### ③ Untuned + RAG

*The stock model, but domain documents are chunked, embedded, and retrieved into the prompt at
query time. In this POC this is the "Standard + Docs" panel.*

**Pros**
- **Current and updatable** — change a document, re-index, done. No re-training.
- Answers are **grounded and citeable** — you can trace a claim back to a source chunk.
- Reduces hallucination by anchoring the model to retrieved text.
- Lower authoring effort than a training set — point it at documents you already have.
- Base model stays fully general; no regression risk.

**Cons**
- **Retrieval quality is the ceiling** — wrong/irrelevant chunks → wrong answers; embeddings and
  chunking must be tuned.
- **Does not change behavior** — tone/format/terminology stay generic; it reads your docs but
  doesn't *sound* like you.
- Adds **latency and token/prompt-length cost** on every query.
- Struggles when the answer must be synthesized across many chunks, or when the corpus is thin.
- Can be *distracted* by retrieved-but-irrelevant context.

**Best for**: large or frequently-changing knowledge bases; when source attribution/auditability
matters; when you can't invest in authoring a training set.

---

### ④ Fine-Tuned + RAG (specialized)

*Both levers: a domain LoRA adapter **and** document retrieval. In this POC this is the
"Specialized (RAG)" panel — the headline configuration.*

**Pros**
- **Best of both** — domain behavior/voice/format from fine-tuning + fresh, grounded, citeable
  facts from RAG.
- Highest answer quality for domain Q&A; the configuration most likely to produce the visible
  "wow" contrast the demo targets (spec §SC-001).
- Facts stay updatable via documents; style stays consistent via the adapter.

**Cons**
- **Most moving parts** — two artifacts to build *and* maintain (training set **and** corpus/index).
- Highest complexity → hardest to reproduce and debug; two bottlenecks stacked.
- The two levers can **conflict**: a fine-tuned prior vs. a retrieved fact — which wins? Needs
  prompt scaffolding to prefer retrieved context for facts.
- Larger prompts + adapter load → highest resource/latency cost of the four.
- **Still not exact at math** — see §6. This is the ceiling all four share.

**Best for**: the production target once the POC proves value; domains needing both a distinct
voice/format *and* current, auditable facts.

---

## 5. Side-by-Side Comparison Table

| Dimension | ① Pure model | ② Fine-tuned | ③ Untuned + RAG | ④ Fine-tuned + RAG |
|---|---|---|---|---|
| Knows internal facts | ❌ None | ⚠️ Frozen, fuzzy | ✅ If retrieved | ✅ If retrieved |
| Knowledge freshness | ❌ Cutoff | ❌ Retrain to update | ✅ Edit docs | ✅ Edit docs |
| Domain tone / format / terms | ❌ Generic | ✅ Strong | ❌ Generic | ✅ Strong |
| Source citations / auditability | ❌ | ❌ | ✅ | ✅ |
| Hallucination risk (facts) | 🔴 High | 🟠 Medium (confident) | 🟢 Lower (grounded) | 🟢 Lowest |
| Exact / deterministic math | ❌ | ❌ | ❌ | ❌ *(needs §6)* |
| Inference latency | 🟢 Lowest | 🟢 Low | 🟠 +retrieval | 🔴 Highest |
| Build effort | 🟢 Lowest | 🟠 Author dataset | 🟠 Curate corpus | 🔴 Both |
| Update effort | — | 🔴 Retrain | 🟢 Re-index | 🟠 Re-index (facts) |
| Reproducibility / debug | 🟢 Easy | 🟠 | 🟠 | 🔴 Hardest |
| Regression risk (general ability) | 🟢 None | 🟠 Forgetting | 🟢 None | 🟠 Forgetting |
| POC panel | Standard Model | Specialized (No RAG) | Standard + Docs | **Specialized (RAG)** |

> **Note on the POC**: all four cells are directly observable in the Gradio demo (Standard, Standard
> + Docs, Specialized (No RAG), Specialized (RAG)) — each with its own generation-time reading, so the
> "Inference latency" row above isn't just theoretical. Comparing Standard vs. Specialized (No RAG)
> isolates how much of the improvement comes from the adapter alone; comparing Specialized (No RAG)
> vs. Specialized (RAG) isolates how much retrieval adds on top of it (spec §SC-005, FR-007).

---

## 6. The Missing Axis: Deterministic Calculation

**All four approaches share one hard ceiling: none of them can be trusted to do exact math.**

### Why LLMs fail at calculation

An LLM predicts the next *token*; it does not *compute*. Arithmetic is approximated from patterns
seen in training, so:

- Error rate grows with digit count and with the number of chained steps.
- The same prompt can yield different numbers on different runs (temperature > 0).
- It fails **silently and confidently** — a wrong total looks exactly as authoritative as a right one.

For anything business-critical — pricing, quotes, tax, discounts, unit conversions, financial
totals, dates/SLAs, dosages, engineering tolerances — probabilistic "close enough" is not acceptable.

### Why neither fine-tuning nor RAG fixes it

- **Fine-tuning ≠ calculator.** You can show the model thousands of solved sums; it memorizes
  patterns and still fails on unseen numbers. Worse: it may nail the common cases and be
  catastrophically, confidently wrong on the edge cases.
- **RAG ≠ calculator.** RAG can retrieve the *formula* or the *rate table*, but the LLM still has to
  *apply* it — and applying it is the unreliable step. Retrieval improves the inputs, not the arithmetic.

> The fix is architectural, not model-level: **let the model decide *what* to compute, and let
> deterministic code *do* the computing.**

### The pattern: function calling / tool use

1. The (specialized) LLM understands intent and **extracts the parameters**.
2. It **calls a deterministic function** (or MCP tool) with those parameters.
3. The function returns an **exact, tested result**.
4. The LLM **presents** the result in natural language (with domain tone and, via RAG, citations).

This layer gives you what the model alone never can:

| Property | Delivered by the tool layer |
|---|---|
| **Correct** | exact, unit-tested code — not an approximation |
| **Reproducible** | same input → same output, independent of temperature |
| **Auditable** | every call and its arguments can be logged and inspected |
| **Maintainable** | fix the function, not the model — no retraining |

### Calculation function vs. MCP — which delegation mechanism?

Both expose deterministic code to the model; they differ in reach and overhead.

| | **In-process calculation function** | **MCP tool (server)** |
|---|---|---|
| What it is | A plain Python function the app calls directly | A tool exposed over the Model Context Protocol |
| Coupling | Lives inside this one app/notebook | Reusable across *any* MCP-compatible app, model, or agent |
| Discovery | Hard-wired by the developer | Standardized, self-describing tool schema |
| Infra | None — just code | A server process (local stdio subprocess, or remote) |
| Setup cost | Minimal | Moderate (define server, schema, transport) |
| Best when | A single app needs a few calculations | Many apps/agents must share the same trusted tools; productionizing |
| POC fit | ✅ Start here (§I Simplicity First) | Graduate to this when the tool must be shared/productionized |

> **Constitution note**: a plain in-process function is trivially compliant (free, simple, local).
> An MCP server is *allowed* — a local **stdio** subprocess needs no Docker or hosted database — but
> it adds a moving part. For the POC, prefer the plain function; reach for MCP only when the
> deterministic tools need to outlive this notebook and serve multiple applications.

---

## 7. Tying It Together — Reference Architecture

The specialized model becomes the **reasoning and routing layer**; the deterministic tool becomes
the **calculation layer**. They are complementary, not competing.

```
        User question
              │
              ▼
 ┌────────────────────────────────────────────────┐
 │  SPECIALIZED LLM   (fine-tuned + RAG)           │
 │  • parses domain intent & terminology (tuning)  │
 │  • retrieves grounding facts / rates (RAG)      │
 │  • decides: answer directly OR call a tool      │
 └───────────────┬────────────────────────────────┘
          needs an exact calculation?
          ┌───────┴─────────┐
         no                yes → extract parameters
          │                       │
          │                       ▼
          │         ┌──────────────────────────────┐
          │         │  DETERMINISTIC LAYER           │
          │         │  calculation function / MCP    │
          │         │  • exact · tested · logged     │
          │         └──────────────┬─────────────────┘
          │                        │ exact result
          ▼                        ▼
   ┌──────────────────────────────────────────────┐
   │  LLM composes the final answer                 │
   │  natural language + exact value + citation     │
   └──────────────────────────────────────────────┘
```

**Division of labor** — play each component to its strength:

| The specialized LLM is good at… | The deterministic tool is good at… |
|---|---|
| understanding messy natural-language questions | exact arithmetic and unit conversion |
| domain terminology, tone, and answer format | applying rate tables, tax, discount, pricing rules |
| retrieving and summarizing the right documents | date/time math and rounding rules |
| choosing *which* tool to call and with *what* arguments | anything that must be reproducible and auditable |
| explaining the result in plain language | anything regulatory, financial, or safety-critical |

**Worked example** — *"What's the total landed cost if I order 240 units at last quarter's contract rate?"*

1. **RAG** retrieves last quarter's contract rate and the landed-cost formula from the domain docs.
2. **Fine-tuning** ensures the model uses the house terms ("landed cost", "contract rate") and format.
3. The LLM extracts `{ quantity: 240, rate: <retrieved>, … }` and calls
   `calculate_landed_cost(...)` (function or MCP tool).
4. The tool returns the **exact** figure.
5. The LLM presents the number with a breakdown **and cites the source document**.

Every component does what it is reliably good at — and nothing it isn't.

---

## 8. Decision Guide — When to Use What

| If you need… | Start with |
|---|---|
| A baseline / control for comparison | ① Pure model |
| A fixed house voice, format, or task behavior over stable knowledge | ② Fine-tuned |
| Current, citeable facts over a changing knowledge base | ③ Untuned + RAG |
| Both a distinct domain voice **and** fresh, auditable facts | ④ Fine-tuned + RAG |
| **Any exact number** (price, tax, quote, conversion, date) | **+ calculation function / MCP** |
| To share those exact tools across many apps/agents later | Promote the function to an **MCP tool** |

Rule of thumb: **add levers only when the previous rung leaves a visible gap.** RAG before
fine-tuning if the pain is *stale/unknown facts*; fine-tuning before RAG if the pain is *wrong
tone/format*; the deterministic tool the moment a real number has to be correct.

---

## 9. How This Maps to This POC

- The demo now compares **all four cells** side-by-side in Gradio — **① Standard**, **② Specialized
  (No RAG)**, **③ Standard + Docs**, and **④ Specialized (RAG)** — with a per-panel timing readout,
  giving a clean, direct read on fine-tuning's contribution, RAG's contribution, and their combination
  without needing to infer any of them (spec §SC-005, `docs/findings_template.md`).
- The domain is **laytime & voyage-charterparty calculation** — NOR validity, SHEX/SHINC/WWD, SOF
  analysis, demurrage/despatch (see `README.md`, `domain_docs/`, `training_dataset.jsonl`). This
  happens to be a sharp illustration of the whole framework above: the terminology and analysis
  *sequence* (e.g. the NOR → turn-time → laytime-commencement chain, or the step-by-step SOF
  walk-through in `domain_docs/04_sof_analysis_guide.md`) is exactly what fine-tuning and RAG are good
  at teaching; the *arithmetic* — demurrage/despatch amounts, elapsed laytime, prorated exceptions —
  is exactly the exact-math ceiling in §6 that neither lever can fix.
- The **deterministic calculation layer (§6–7) is beyond the current POC scope** — the POC is
  scoped to qualitative Q&A comparison, not tool use. It is the most natural **"invest" next step**,
  and this domain gives it a concrete first target: a `calculate_laytime(...)` / `calculate_demurrage(...)`
  function that takes the NOR time, turn time, exception clauses, and SOF intervals the LLM already
  extracts, and returns an exact, auditable figure. It is cheap (start as a plain Python function),
  stays within every constraint (free, local, Colab-friendly, no Docker), and closes the one gap all
  four approaches share.
- Constraints that still apply to any extension: open-weight models only, free/OSS libraries,
  Colab-runnable, and **Simplicity First** — which is why the recommended sequence is
  *function first, MCP later*.

---

## 10. Talking Points / Anticipated Questions

- **"Isn't fine-tuning enough on its own?"** — It fixes *how* the model answers, not *what facts*
  it has or *whether the math is right*. Great voice, stale/uncertain facts, unreliable numbers.
- **"Isn't RAG enough on its own?"** — It fixes the facts, not the voice, and not the math. It
  reads your documents but still sounds generic and still miscalculates.
- **"Why can't we just tell the model to be careful with math?"** — Because it doesn't compute; it
  predicts. 'Careful' still produces a plausible guess. Determinism has to come from code.
- **"Function or MCP?"** — Same idea, different reach. A function is the fastest correct answer for
  one app; MCP is the standard when many apps/agents must share the same trusted tools.
- **"What does this cost?"** — The four approaches trade build/maintenance effort for quality
  (see §5). The calculation layer is comparatively cheap and removes an entire class of risk.
- **"Why show 'Specialized (No RAG)' as its own panel instead of just 'Standard' and 'Specialized'?"**
  — Without it, a visible gain in the fully-specialized panel is ambiguous: is it the adapter, the
  retrieved documents, or both? The extra panel makes fine-tuning's standalone contribution directly
  observable instead of inferred.

---

## Appendix — Glossary

- **Open-weight / open-source model** — a model whose weights are freely downloadable and runnable
  (e.g., Qwen family), no paid API. The foundation for all four approaches.
- **Fine-tuning (LoRA / QLoRA)** — training small adapter weights on domain examples to change the
  model's behavior; cheap enough to run on a single Colab GPU.
- **RAG (Retrieval-Augmented Generation)** — retrieving relevant document chunks at query time and
  prepending them to the prompt so the model answers from grounded, current text.
- **Function calling / tool use** — the model emits a structured call to code, which runs and
  returns a result the model then uses. The mechanism behind the deterministic layer.
- **MCP (Model Context Protocol)** — an open standard for exposing tools, resources, and data to
  LLM applications in a uniform, discoverable way; the productionized form of a shared tool.
- **Deterministic** — same input always yields the same output; the property exact calculations
  require and probabilistic generation cannot guarantee.
```
