# Sample Project — Redacted Visual Reference (Research-Only)

This directory holds the **one sample project** — project `378` (the hardest
building in the evaluation set: 5 floors, 103 beam entities, 208 columns).
It is sufficient for a reader to:

- Inspect the input modality of StructAgent (what a scanned structural
  blueprint sheet looks like in practice, including beam plan and column
  plan sheets).
- Reproduce the B2 (single-VLM zero-shot) baseline on a known input.
- Compare full outputs to the per-entity ground-truth annotation in
  `../gt/378.gt.json` (released alongside this sample).

Of the 20 evaluation buildings, **only project `378` is released as a
full bundle** (redacted source sheets here, per-entity ground truth in
`../gt/378.gt.json`, per-instance metrics for every cell in
`../metrics/378__*.json`). The other 19 buildings are represented in
this repository by their per-instance metrics JSON only — both their
source drawings and their per-entity ground truth are withheld. See
`../../DATASHEET.md` § 6 ("Distribution") for the rationale.

## Why project 378?

| Property | Value |
|---|---|
| Difficulty | `hard` (the only hard project in the 20-building set) |
| Floors | 5 (F2 through F6, ground floor unlabeled) |
| Beam entities | 103 |
| Columns | 208 |
| Source category | Category A — teaching / publicly available engineering reference |
| Sheet count | 6 source sheets (covers 5 floors via grouped sheets like "floors 1–4 column plan") |
| Filename profile | Generic plan-method terminology only; no project code, institution name, or building use in the original filenames |
| Sample size | ~2.8 MB after downsampling to 2400 px long edge |

Project 378 also drives the strongest ablation story: removing the
LLM-driven axis adjudication (cell A6) collapses both column and beam F1
to 0 on this building, and removing the C_3D gate (cell A4) drops column
F1 to ~0.1. The visual sample lets reviewers correlate the metrics with
the actual sheet complexity.

## Files (after the redaction workflow below)

```
MANIFEST.json                                  ← machine-readable index (sheet → floors → matching metrics)
sheet_01_floors_1_to_4_column_plan.png         ← column plan covering F1–F4
sheet_02_floor_F2_3_90m_beam_plan.png          ← beam plan, +3.90 m
sheet_03_floor_F3_11_70m_beam_plan.png         ← beam plan, +11.70 m
sheet_04_floors_F4_to_F5_beam_plan.png         ← beam plan, F4–F5
sheet_05_floors_5_to_6_column_plan.png         ← column plan covering F5–F6
sheet_06_floor_F6_23_10m_beam_plan.png         ← beam plan, +23.10 m
_raw_pre_redaction/                            ← (gitignored) un-redacted originals; never released
```

## Redaction workflow (must be complete before push)

Each output sheet must have its `redaction_pending` array in
`MANIFEST.json` emptied before the repo is published. The current pipeline:

1. **Automatic redaction** (already done by `../../scripts/redact_sample.py`):
   - Downsample to ≤ 2400 px long edge (≈ 200 dpi for A1 sheets)
   - Strip EXIF metadata
   - Convert .jpg → .png, deterministic anonymized filenames
2. **Manual masking** (pending — must be done in any image editor):
   - Mask design-institute stamps (often red round seals)
   - Mask any project code, project name, address, or city in the title block
   - Mask engineer / reviewer signatures
   - Mask any phone numbers, fax numbers, or contact info
3. **Update MANIFEST**: for each sheet, move each completed item from
   `redaction_pending` to `redaction_applied`.
4. **Re-audit**: `python ../../scripts/audit_anonymity.py --root ../..`
   must report 0 hits.
5. **Visual gate**: open every sheet in an incognito browser tab; verify
   nothing identifying remains.

## What you can do with the sample project

- Visually inspect a real input to StructAgent across multiple sheet types
  for one building (the hardest one).
- Run the VLM-only B2 baseline end-to-end on this building using
  `../../code/eval/_prepare_vlm_inputs.py` → your VLM API →
  `../../code/eval/_evaluate_vlm_baseline.py`, then verify the result
  matches the released B2 metric for this project in
  `../metrics/378__baseline_B2__metrics.json`.
- Use this building to test your own agent against the released GT
  (`../gt/378.gt.json`) and compare to our per-instance metric.

## What the released sample alone does not let you do

- Run the full StructAgent pipeline (the pipeline is withheld; see
  `../../code/agent/README.md`).
- Re-derive ablation cells A3–A6 or baseline B1 on other buildings;
  those are released as per-instance metrics only, and their per-entity
  ground truth is also withheld.
- Profile cross-building per-entity variance — the per-entity GT is only
  released for this one building. Cross-building **aggregate** variance
  can still be inspected via `inventory.pred` / `inventory.gt` blocks in
  every metrics JSON.

## Requesting access to additional buildings

After acceptance, qualified researchers may request additional buildings
(drawings and/or per-entity GT) from the 20-building set on a
case-by-case basis, subject to the redistribution constraints of each
source. See `../../README.md` § "Requesting further access" and
`../../DATASHEET.md` § 6.
