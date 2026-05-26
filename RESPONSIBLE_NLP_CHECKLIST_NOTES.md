# Notes on the Responsible NLP Research Checklist

> For paper reviewers: per-item rationale, cross-referenced to the
> submitted paper and to this anonymous repository.

---

## A. General

| Item | Answer | Where to verify |
|---|---|---|
| A1 — Limitations section | Yes | Paper § Limitations |
| A2 — Potential risks discussed | Yes | Paper § Ethical Considerations and § Limitations — discusses the risk of using unaudited automated FEM generation without licensed-engineer review. |

## B. Scientific Artifacts

| Item | Answer | Notes |
|---|---|---|
| B — Use or create artifacts | Yes | We use an off-the-shelf VLM and off-the-shelf OCR; we create a 20-building evaluation set (~300 scanned sheets) with ground-truth annotations and the evaluation harness. |
| B1 — Cite creators | Yes | Paper § 5 (VLM, OCR, baseline systems) and References. |
| B2 — License discussion | Yes | Paper § 5.1 + `DATASHEET.md` + `LICENSE`. Code under CC BY-NC 4.0; data under CC BY-NC-ND 4.0. |
| B3 — Consistent intended use | Yes | Paper § 5.1 — research-only; derivatives must remain in research context. |
| B4 — PII / offensive content | N/A | Structural engineering drawings contain no personal identifying information. |
| B5 — Documentation | Yes | `DATASHEET.md` (§ 1–7) plus paper § 5.1. |
| B6 — Data statistics | Yes | Paper § 5.1 and Table 1 — 20 buildings, approximately 300 scanned structural blueprint sheets (primarily beam and column plans). Per-building floor / beam / column counts in Table 1, and as inventory aggregates inside every metrics JSON in `data/metrics/`. We do not report train/dev/test splits because the dataset is used only for end-to-end evaluation, not for model training. |

**Why is the dataset only partially released — and why even the per-entity ground truth is sample-only?**
See `DATASHEET.md` § 6 ("Distribution") and the paper § 5.1. Briefly:

- The ~300-sheet corpus is drawn from mixed sources with mixed
  redistribution rights and overall high sensitivity. We release **one**
  fully visualized sample project (~10 redacted sheets).
- For internal consistency, the **per-entity ground truth** of the other
  19 buildings is also withheld — because that ground truth (axis grid,
  column positions, beam topology, section labels) encodes the structural
  skeleton of buildings whose source drawings we cannot redistribute.
  Releasing the per-entity GT but withholding the drawing would expose
  almost the same architectural information.
- For the 19 withheld buildings we still release per-instance metrics
  JSON, which include **inventory aggregates** for both prediction and
  ground truth (floor count, axis-grid size, column count, beam count) —
  this is sufficient for cross-building distribution inspection without
  per-entity leak.

Reviewers can verify the reported numbers via (a) end-to-end re-derivation
on the released sample project, (b) inventory consistency across all 20
buildings' metrics JSON, and (c) macro-average reproduction via
`code/eval/aggregate.py`. Comparable partial-release practice has been
accepted at recent ACL venues (e.g., Storks et al., ACL 2023 long, which
releases analysis code and a sample data template while withholding
IRB-protected subject data).

## C. Computational Experiments

| Item | Answer | Notes |
|---|---|---|
| C — Computational experiments | Yes | Tables 3 & 4. |
| C1 — Model size & budget | Yes | Paper § 5 and Appendix — VLM model identifier, parameter count, average API cost per building, total GPU/API budget. |
| C2 — Hyperparameters | Yes | Paper § 5.2 — agent-loop hyperparameters, VLM temperature, max iterations. |
| C3 — Descriptive statistics | Yes / partial | Per-instance numbers reported in `data/metrics/`. We report a single deterministic run per cell (VLM temperature = 0); std-dev is not reported because re-running the closed-loop agent on the same input is deterministic up to API-side variance. |
| C4 — Package parameters | Yes | Paper § 5 + Appendix — names and versions of the evaluation library functions (IoU, F1, span-count consistency). |

## D. Human Subjects / Annotators

| Item | Answer | Notes |
|---|---|---|
| D — Human annotators used | Yes | Ground-truth annotations were produced by the authors. |
| D1 — Instructions to annotators | Yes | `data/gt/README.md` summarizes the annotation procedure (silver-standard: starting from a verified system output, then manually cross-checking against the source drawing). |
| D2 — Demographics, compensation | N/A | Authors only. |
| D3 — IRB / consent | N/A | No human subjects. Annotators are the authors. |
| D4 — Annotation cost | Reported | 2–6 hours per building, on the order of ~80 author-hours across the 20-building set. |

## E. AI Assistants

| Item | Answer | Notes |
|---|---|---|
| E — AI assistants used | Yes | Used Claude and/or GPT for writing assistance and code drafting. |
| E1 — Information about use | Yes | Paper § Ethical Considerations — discloses LLM use for writing assistance and code drafting; all technical claims verified by the authors. |

---

*This file is committed in the anonymous repository so reviewers can
cross-reference any checklist item against the actual artifacts.*
