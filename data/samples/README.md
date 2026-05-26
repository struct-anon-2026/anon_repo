# Released Sample Building — Redacted Visual Reference (Research-Only)

This directory holds **one sample building** from the evaluation set —
released as a redacted visual reference so that a reader can:

- Inspect the input modality of StructAgent (what a scanned structural
  blueprint sheet looks like in practice, including beam plan and column
  plan sheets).
- Reproduce the B2 (single-VLM zero-shot) baseline on a known input.
- Compare full outputs to the per-entity ground-truth annotation in
  `../gt/` (released alongside this sample).

Of the buildings in the evaluation set, **only this one is released as
a full bundle** (redacted source sheets here, per-entity ground truth
in `../gt/`, per-instance metrics for every cell in `../metrics/`). The
other buildings are represented in this repository by their per-instance
metrics JSON only — both their source drawings and their per-entity
ground truth are withheld. See `../../DATASHEET.md` § 6 ("Distribution")
for the rationale.

## Why this specific building was chosen

The buildings in the evaluation set are drawings of real building
projects. Most are subject to redistribution restrictions (engineering-
design intellectual property, client confidentiality, third-party
rights). For the released sample, we chose the one building for which
we have unambiguous redistribution rights under research-only terms.

We intentionally do not describe its specific project id, scale, or
difficulty position within the evaluation set — those characterizations
could either be read as cherry-picking or could inadvertently
narrow-identify the building. The released ground-truth JSON
(`../gt/`) and per-instance metrics JSON (`../metrics/`) for this
building are sufficient for any quantitative analysis a reader needs.

## Files

```
MANIFEST.json                                  ← machine-readable index (sheet → floors → matching metrics)
sheet_01_floors_1_to_4_column_plan.png         ← column plan, lower floors
sheet_02_floor_F2_3_90m_beam_plan.png          ← beam plan
sheet_03_floor_F3_11_70m_beam_plan.png         ← beam plan
sheet_04_floors_F4_to_F5_beam_plan.png         ← beam plan, grouped floors
sheet_05_floors_5_to_6_column_plan.png         ← column plan, upper floors
sheet_06_floor_F6_23_10m_beam_plan.png         ← beam plan, top floor
_raw_pre_redaction/                            ← (gitignored) un-redacted originals; never released
```

## Redaction applied

1. **Automatic** (via `../../scripts/redact_sample.py`):
   - Downsample to ≤ 2400 px long edge (≈ 200 dpi for A1 sheets)
   - Strip EXIF metadata
   - Convert .jpg → .png, deterministic anonymized filenames (no
     project codes in filenames)
2. **Manual** (in image editor):
   - Any design-institute stamps (typically red round seals)
   - Any project codes, project name, address, or city in the title block
   - Engineer / reviewer signatures
   - Any phone numbers, fax numbers, or contact info

## What you can do with the released sample

- Visually inspect a real input to StructAgent across multiple sheet
  types for one building.
- Run the VLM-only B2 baseline end-to-end on this building using
  `../../code/eval/_prepare_vlm_inputs.py` → your VLM API →
  `../../code/eval/_evaluate_vlm_baseline.py`, then verify the result
  matches the released B2 metric for this building in `../metrics/`.
- Use this building to test your own agent against the released
  ground truth (`../gt/`) and compare to our per-instance metric.

## What the released sample alone does not let you do

- Run the full StructAgent pipeline (the pipeline is withheld; see
  `../../code/agent/README.md`).
- Re-derive ablation cells A3–A6 or baseline B1 on other buildings;
  those are released as per-instance metrics only, and their per-entity
  ground truth is also withheld.
- Profile cross-building per-entity variance — the per-entity GT is
  only released for this one building. Cross-building **aggregate**
  variance can still be inspected via `inventory.pred` / `inventory.gt`
  blocks in every metrics JSON.

## Requesting access to additional buildings

After acceptance, qualified researchers may request additional buildings
(drawings and/or per-entity GT) on a case-by-case basis, subject to the
redistribution constraints of each source. See `../../README.md` §
"Requesting further access" and `../../DATASHEET.md` § 6.
