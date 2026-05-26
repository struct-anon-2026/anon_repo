# StructAgent — Anonymous Supplementary Repository

> Anonymous supplementary materials for our ARR May 2026 cycle submission
> (preferred venue: EMNLP 2026 Main Conference).
>
> This repository accompanies the paper. The full evaluation set consists of
> **20 buildings (~300 scanned structural blueprint sheets)** — primarily
> beam and column structural plans, with associated section and foundation
> sheets.
>
> The released artifacts are structured around a **single sample project
> (project 378 — the hardest building in the set: 5 floors, 103 beam
> entities, 208 columns, 6 source sheets)** for end-to-end inspection,
> plus per-instance metrics for the remaining buildings:
>
> - **For the sample project:** the redacted source sheets, the
>   ground-truth annotation JSON, the per-instance metrics for every
>   reported experiment cell, and the evaluation code.
> - **For the other 19 buildings:** per-instance metrics JSON only (with
>   predicted/ground-truth inventory aggregates). Source drawings and
>   per-entity ground truth are withheld to be consistent with the
>   sample-only release of source drawings.

## Contents

```
.
├── README.md                              ← you are here
├── DATASHEET.md                           ← dataset documentation (Gebru et al. 2021 template)
├── RESPONSIBLE_NLP_CHECKLIST_NOTES.md     ← per-item rationale for the checklist
├── LICENSE                                ← CC BY-NC 4.0 (code) / CC BY-NC-ND 4.0 (data)
├── code/
│   ├── eval/
│   │   ├── evaluate.py                    ← end-to-end metric computation
│   │   ├── _evaluate_ablation.py          ← ablation cells A3–A6 + B1
│   │   ├── _evaluate_vlm_baseline.py      ← B2 VLM-only baseline
│   │   ├── _prepare_vlm_inputs.py         ← reproduce B2 inputs from the sample project
│   │   ├── aggregate.py                   ← roll per-instance JSON into paper tables
│   │   ├── requirements.txt
│   │   └── README.md
│   └── agent/
│       ├── agent_interface.py             ← H/E/C/Q interface signatures + state-machine pseudo-code
│       └── README.md                      ← scope of released agent code
├── data/
│   ├── metrics/                           ← per-instance metrics JSON (sanitized)
│   │   ├── README.md
│   │   └── *.json
│   ├── gt/                                ← ONE ground-truth JSON (for sample project 378 only)
│   │   ├── README.md
│   │   └── 378.gt.json
│   └── samples/                           ← project 378 — 6 redacted sheets, research-only
│       ├── README.md
│       ├── MANIFEST.json
│       └── sheet_NN_*.png
└── scripts/
    ├── sanitize.py                        ← removes absolute paths / usernames from JSON
    ├── audit_anonymity.py                 ← greps for identifying strings
    └── README.md
```

## Quick start — reproduce Tables 3 and 4

```bash
# 1. install minimal deps
pip install -r code/eval/requirements.txt

# 2. inspect any per-instance metric
python -c "import json; print(json.dumps(json.load(open('data/metrics/378__ablation_A3__metrics.json')), indent=2))"

# 3. (optional) re-derive an aggregate from the per-instance JSON
python code/eval/aggregate.py --in data/metrics --out /tmp/table3.csv
```

The numbers in `data/metrics/` are the exact per-instance metrics reported in
the paper (Tables 3 and 4). The evaluation harness in `code/eval/` is the
script that produced them, given each system's `project_semantic.json` output
and the ground truth in `data/gt/`. We do not release the system outputs
(`project_semantic.json`) themselves; the metrics JSON is the verifiable
artifact.

Scope of released artifacts (per the paper § 5.1):

- **One sample building**: complete release — redacted source sheets
  (`data/samples/`), per-entity ground truth (`data/gt/<sample_id>.gt.json`),
  per-instance metrics for every cell (`data/metrics/<sample_id>__*.json`).
  Sufficient to re-derive a metric end-to-end and to evaluate your own
  system on a known input.
- **Other 19 buildings**: per-instance metrics JSON only. Each metrics
  file includes inventory aggregates for both prediction and ground truth
  (floor count, axis-grid size, column count, beam count), so cross-
  building distribution can be inspected without releasing the per-entity
  ground truth.
- **Per-building summary** (floors, beam entities, columns, difficulty)
  is reported in Table 1 of the paper, and can also be derived from the
  inventory aggregates in `data/metrics/`.

## What is **not** included and why

The released artifacts are sufficient to verify the reported metric values,
but intentionally do not allow full pipeline re-execution. The full system,
the full drawing corpus, and intermediate outputs are withheld because:

1. **Drawing copyright is mixed and overall sensitivity is high.** Some
   inputs come from teaching materials or open engineering references we
   can redistribute under research-only terms; others come from sources we
   do not have unrestricted redistribution rights to. Releasing the full
   ~300-sheet corpus is therefore not possible. We release one carefully
   redacted sample project drawn from the releasable subset, together
   with its per-entity ground truth — and for consistency we **also
   withhold the per-entity ground truth of the other 19 buildings**,
   because that ground truth encodes the structural skeleton (axis grid,
   column positions, beam topology, section labels) of buildings whose
   source drawings we cannot redistribute. Inventory aggregates for those
   buildings are still released through the per-instance metrics JSON.
2. **The agent pipeline includes engineering-oriented components** (CV
   preprocessing, OCR caching, FEM export) whose full release exceeds the
   scope and length of the paper. The paper specifies the externally
   observable behavior; the agent interface stub in `code/agent/` documents
   the I/O contract sufficient for reimplementation.
3. **Intermediate per-sandbox outputs** total several hundred GB and contain
   raw VLM call traces that may carry incidental identifying information
   from the underlying drawings; we do not redistribute them.

See `DATASHEET.md` § "Distribution" and the paper § 5.1 ("Dataset") for the
full discussion.

## Requesting further access

After the review period, qualified researchers may request access to
additional buildings from the 20-building set — either drawings or
per-entity ground truth — on a case-by-case basis, subject to the
redistribution constraints of each source. Requests should briefly
describe the intended research use. The full corpus will not be released
publicly. This anonymous repository will provide contact details after
acceptance.

## License

- Code: CC BY-NC 4.0 (research-only)
- Data: CC BY-NC-ND 4.0 (research-only, no derivatives)

See `LICENSE` for full terms.

---

*Last updated: 2026-05*
