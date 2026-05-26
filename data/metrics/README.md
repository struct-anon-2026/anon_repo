# Per-Instance Metrics (Released)

This directory holds the per-instance metrics JSON files for every
reported experiment in the paper. They produce Tables 3 and 4 when
aggregated.

## Scope

- 20 buildings (the full evaluation set).
- One metrics JSON per (building × experiment cell).
- Experiment cells reported in the paper:
  - **Ablation:** A3 (no cross-sheet aggregate), A4 (no C_3D gate),
    A5 (no axis-span sanity gate), A6 (no LLM axis adjudication).
  - **Baseline:** B1 (pure-OCR rule), B2 (single-VLM zero-shot).
  - **Self-audit:** the full StructAgent run against its own ground truth
    (B5 row in Table 3).

Approximately 140 JSON files in total when all cells × all 20 buildings
are populated. The exact set present in this directory at any given time
is whatever the sanitization script (`../../scripts/sanitize.py`) most
recently copied from the experiment results.

**This directory is the primary verification artifact for the other 19
buildings whose per-entity ground truth is not released** (see
`../gt/README.md` for the rationale). Each metrics JSON carries
`inventory.pred` and `inventory.gt` blocks with aggregate counts
(floors, axes, columns, beams), which let a reviewer inspect cross-
building distribution and sanity-check the F1 / precision / recall
values without per-entity GT leak.

## File naming

```
<project_id>__ablation_A3__metrics.json
<project_id>__ablation_A4__metrics.json
<project_id>__ablation_A5__metrics.json
<project_id>__ablation_A6__metrics.json
<project_id>__baseline_B1__metrics.json
<project_id>__baseline_B2__metrics.json     (when released as per-instance; otherwise see batched file)
<project_id>__metrics.json                  (self-audit; B5 row)
```

`<project_id>` ranges over the 20-building set. Each metrics file is
self-describing through its embedded `project_id`, `cell`, and
`inventory.{pred,gt}` fields; the prefix is just a label and carries
no encoded information about which building it is.

## Schema

See `../../code/eval/README.md` for the full JSON schema. Each file
includes: `schema_version`, `project_id`, `cell`, `floor_alignment`,
`inventory.{pred,gt}`, `axis_grid`, `columns`, `beams`.

## Sanitization

These files were produced internally with paths like
`E:\\lab\\exp_A3_1\\...\\project_semantic.json` and references to the
internal repository root. All such absolute paths in `semantic_path`,
`gt_path`, and `exp_root` have been stripped and replaced with relative
placeholders (`<SANDBOX>/exp_<cell>/.../project_semantic.json` and
`data/gt/<id>.gt.json`).

The numeric metric values are unchanged.

## Aggregating to paper tables

```bash
python ../../code/eval/aggregate.py --in . --out /tmp/tables.csv
```

This reproduces Tables 3 and 4 (macro-average across the 20 buildings,
rounded to the precision shown in the paper).
