# Evaluation Harness

Scripts that compute the per-instance metrics in `../../data/metrics/`.

## Files

| File | Role |
|---|---|
| `evaluate.py` | Compare one prediction `project_semantic.json` vs one `*.gt.json`; emit `<id>__metrics.json`. Used for the main system. |
| `_evaluate_ablation.py` | Cells A3–A6 + B1 (pure-OCR baseline). Reads from `exp_<cell>_<i>/.../outputs/final/project_semantic.json`. |
| `_evaluate_vlm_baseline.py` | Cell B2 (single-VLM zero-shot). Reads raw VLM JSON from `vlm_baseline/raw_outputs/`. |
| `_prepare_vlm_inputs.py` | Reproduce the B2 prompt and image inputs from the released sample. |

> Filenames prefixed `_` denote internal-experiment scripts (we kept the
> original names for traceability with the metrics JSON `cell` field).

## What the metrics mean

Per `data/metrics/<id>__<cell>__metrics.json`:

```jsonc
{
  "schema_version": "cvn.ablation_eval.v1",
  "project_id": "...",
  "cell": "A3" | "A4" | "A5" | "A6" | "B1" | "B2" | "self",
  "inventory": {"pred": {...}, "gt": {...}},
  "axis_grid": {
    "h_label_iou": <float>,                     // axis-label set IoU (horizontal)
    "v_label_iou": <float>,                     // axis-label set IoU (vertical)
    "h_position_max_abs_error": <float>,        // worst normalized position error (0–1)
    "v_position_max_abs_error": <float>
  },
  "columns": {
    "pred_count": <int>, "gt_count": <int>, "matched": <int>,
    "precision": <float>, "recall": <float>, "f1": <float>,
    "section_match_rate": <float>               // fraction of matched cols with correct section label
  },
  "beams": {
    "pred_count": <int>, "gt_count": <int>, "matched": <int>,
    "precision": <float>, "recall": <float>, "f1": <float>,
    "topology_match_rate": <float>,             // fraction of matched beams with correct span topology
    "label_only_f1": <float>                    // F1 ignoring geometry, label-only match
  }
}
```

Macro-average across the 20 buildings = simple arithmetic mean per metric;
this is how Tables 3 and 4 in the paper are produced.

## Reproducing Tables 3 and 4 from released artifacts

If you only want to *verify* the reported numbers (no system re-run):

```bash
pip install -r requirements.txt
python aggregate.py --in ../../data/metrics --out /tmp/table3_table4.csv
```

If you want to *re-derive* metrics from a system output of your own
(e.g., your own agent's `project_semantic.json` on one of the released
sample buildings):

```bash
python evaluate.py \
  --pred /path/to/your/project_semantic.json \
  --gt   ../../data/gt/16.gt.json \
  --out  /tmp/your_system_on_16.json
```

## What you cannot reproduce from this repo alone

- Per-cell ablation runs (A3–A6) require the full pipeline source and the
  full drawing set; both are withheld. The released metrics JSON are the
  artifacts of those runs.
- B2 (single-VLM zero-shot) can be reproduced *on the one released sample
  project* using `_prepare_vlm_inputs.py` + your own VLM API key, and the
  result can be cross-checked against the per-instance B2 metric for that
  project in `../../data/metrics/`.

## Requirements

See `requirements.txt`. Core dependencies: `numpy`, `shapely`,
`scikit-image` (for IoU); no model weights, no GPU.
