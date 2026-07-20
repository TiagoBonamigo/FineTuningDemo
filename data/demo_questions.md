# Domain LLM POC — Demo Question Set

> **How to use**: Submit each question below in the Gradio UI. Compare the Standard Model and Specialized Model panels against the **Expected** notes. At least 4 of 5 domain-specific questions should show a clear quality improvement in the Specialized Model panel (SC-001).

---

## Domain-Specific Questions

Questions answerable only from the organization's domain documents. The Specialized Model should clearly outperform the Standard Model here.

1. [REPLACE: domain-specific question requiring specialized knowledge]
   **Expected**: [REPLACE: description of what a correct answer contains — specific facts, terms, or procedures only a domain expert would know]

2. [REPLACE: domain-specific question about a process or procedure]
   **Expected**: [REPLACE: the key steps or conditions the correct answer should mention]

3. [REPLACE: domain-specific question about a product, regulation, or policy]
   **Expected**: [REPLACE: the specific details or requirements the correct answer must include]

4. [REPLACE: domain-specific question using proprietary terminology]
   **Expected**: [REPLACE: the correct use of domain terminology and what context it should appear in]

5. [REPLACE: domain-specific question about an edge case or exception]
   **Expected**: [REPLACE: the exception condition and how the correct answer should handle it]

---

## Terminology Questions

Questions using domain-specific terms the base model is unlikely to know. The Specialized Model should use correct terminology; the Standard Model may give generic or incorrect definitions.

1. [REPLACE: "What does [TERM] mean in the context of [DOMAIN]?"]
   **Expected**: [REPLACE: the precise domain definition, not a dictionary definition]

2. [REPLACE: "How is [TERM A] different from [TERM B] in [DOMAIN]?"]
   **Expected**: [REPLACE: the key distinction as understood by domain practitioners]

---

## General Sanity-Check Questions

Not domain-specific. Both models should answer reasonably. Used to verify fine-tuning did not degrade general capability (SC-006).

1. What is the capital of France?
   **Expected**: Both panels answer "Paris" or equivalent — verifies no catastrophic forgetting.

2. Explain what a neural network is in simple terms.
   **Expected**: Both panels give a reasonable, jargon-free explanation — tests general language capability.

---

*Fill in [REPLACE] placeholders with your domain expert before the demo. The question count and structure satisfy FR-008 and spec.md §SC-001, §SC-006.*
