# Agent Interface — Released Scope

This directory contains the **observable interface** of the StructAgent
agent loop, not the full pipeline implementation.

## What is here

- `agent_interface.py` — Python type signatures and a state-machine
  pseudo-code description of the H/E/C/Q loop (Hypothesize → Evidence →
  Check → Question), as introduced in paper § 3 and § 4.

## What is **not** here, and why

The full pipeline (CVN v4E) consists of ~40 modules covering layout
analysis, OCR caching, axis-grid adjudication, cross-sheet aggregation,
3D consistency checking, and FEM export. Releasing the full pipeline is
out of scope for this submission for two reasons:

1. **Paper focus.** The contribution is the agent design (constraint-
   triggered active reading, H/E/C/Q loop, entity-level validation), not
   the implementation of individual CV/OCR/FEM components. These
   components are described at the level needed to understand the agent
   loop (paper § 4); their internal engineering choices are not the
   research contribution.
2. **Engineering IP.** Several modules are part of a longer-running
   production pipeline.

**What the released stub is sufficient for:**
- Understanding the exact input/output contract of the agent loop.
- Reimplementing the agent loop on top of a different set of vision
  tools, by satisfying the interface.
- Comparing your agent loop to ours on the released sample inputs
  (using the evaluation harness in `../eval/`).

**What the released stub is not sufficient for:**
- Re-running the exact pipeline that produced the metrics in
  `../../data/metrics/`. Those metrics are the verifiable artifact;
  the pipeline itself is described in the paper.

A subset of pipeline modules — cleaned and refactored for general use —
will be released separately after acceptance.
