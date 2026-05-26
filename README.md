# StructAgent — Anonymous Supplementary Repository

> Anonymous supplementary materials for our ARR May 2026 cycle submission
> (preferred venue: EMNLP 2026 Main Conference).
>
> This repository accompanies the paper. The full evaluation set consists of
> **20 real-building projects (~300 scanned structural blueprint sheets)** —
> primarily beam and column structural plans, with associated section and
> foundation sheets.
>
> Because these are drawings of real building projects, **most are subject
> to redistribution restrictions (engineering-design intellectual property,
> client confidentiality, or third-party rights) and cannot be publicly
> released.** The released artifacts are therefore structured around:
>
> - **One sample building** for which we have unambiguous redistribution
>   rights, released for end-to-end inspection: redacted source sheets,
>   per-entity ground-truth annotation, and per-instance metrics for every
>   experiment cell.
> - **Per-instance metrics for the remaining buildings**, sufficient for
>   reproducibility of the reported numbers without releasing the
>   underlying drawings or per-entity ground truth.

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
│   │   ├── _prepare_vlm_inputs.py         ← reproduce B2 inputs from the sample
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
│   ├── gt/                                ← ONE ground-truth JSON (the released sample only)
│   │   ├── README.md
│   │   └── *.gt.json
│   └── samples/                           ← released sample — redacted sheets, research-only
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

# 2. inspect any per-instance metric (replace <project_id> with any released id)
python -c "import json, glob; print(glob.glob('data/metrics/*__metrics.json')[0])"

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

- **The released sample building**: complete bundle — redacted source
  sheets (`data/samples/`), per-entity ground truth (`data/gt/`),
  per-instance metrics for every cell (`data/metrics/`). Sufficient to
  re-derive a metric end-to-end and to evaluate your own system on a
  known input.
- **Other buildings in the evaluation set**: per-instance metrics JSON
  only. Each metrics file includes inventory aggregates for both
  prediction and ground truth (floor count, axis-grid size, column
  count, beam count), so cross-building distribution can be inspected
  without releasing per-entity ground truth.
- **Per-building summary** (floors, beams, columns) is reported in
  Table 1 of the paper, and can also be derived from the inventory
  aggregates in `data/metrics/`.

## What is **not** included and why

The released artifacts are sufficient to verify the reported metric values,
but intentionally do not allow full pipeline re-execution. The full system,
the full drawing corpus, and intermediate outputs are withheld because:

1. **The drawings are of real building projects.** Most are subject to
   redistribution restrictions (engineering-design IP, client
   confidentiality, third-party rights). Releasing the full corpus is
   therefore not possible. We release one building for which we have
   unambiguous redistribution rights, together with its per-entity
   ground truth — and for consistency we **also withhold the per-entity
   ground truth of the other buildings**, because that ground truth
   encodes the structural skeleton (axis grid, column positions, beam
   topology, section labels) of buildings whose source drawings we
   cannot redistribute. Inventory aggregates for those buildings are
   still released through the per-instance metrics JSON.
2. **The agent pipeline includes engineering-oriented components** (CV
   preprocessing, OCR caching, FEM export) whose full release exceeds
   the scope and length of the paper. The paper specifies the externally
   observable behavior; the agent interface stub in `code/agent/`
   documents the I/O contract sufficient for reimplementation.
3. **Intermediate per-sandbox outputs** total several hundred GB and
   contain raw VLM call traces that may carry incidental identifying
   information from the underlying drawings; we do not redistribute them.

See `DATASHEET.md` § "Distribution" and the paper § 5.1 ("Dataset") for the
full discussion.

## Requesting further access

After the review period, qualified researchers may request access to
additional buildings (drawings and/or per-entity ground truth) on a
case-by-case basis, subject to the redistribution constraints of each
source. Requests should briefly describe the intended research use. The
full corpus will not be released publicly. This anonymous repository will
provide contact details after acceptance.

## License

- Code: CC BY-NC 4.0 (research-only)
- Data: CC BY-NC-ND 4.0 (research-only, no derivatives)

See `LICENSE` for full terms.

---

*Last updated: 2026-05*
