# Ground-Truth Annotations — Sample Project Only

This directory holds the hand-verified ground truth for **one** building —
the same building released visually under `../samples/`. It is used by the
evaluation harness in `../../code/eval/` to compute the per-instance
metrics for this project in `../metrics/`.

## Why only one?

The 20-building corpus has mixed source rights and is overall sensitive
(see `../../DATASHEET.md` § 3 and § 6). Per-entity ground truth (axis
grid, column positions, beam topology, section labels) encodes the
structural skeleton of a building in a form sufficient to draw a
structural plan resembling the original. Releasing the GT for buildings
whose source drawings we cannot redistribute would expose almost the
same architectural information. We therefore release per-entity GT for
the **sample project only**, matching the sample-only release of source
drawings.

For the other 19 buildings, **inventory aggregates** (floors, axes,
columns, beams — for both prediction and ground truth) are still
released through the per-instance metrics JSON in `../metrics/`. This
lets reviewers inspect cross-building distribution without per-entity
leak.

## Files

```
*.gt.json     ← per-entity ground truth for the released sample building
README.md     ← you are here
```

This GT file shares its project_id prefix with the matching per-instance
metrics in `../metrics/<id>__*.json` and with the released source
sheets in `../samples/`. The full sheet-to-floor mapping is in
`../samples/MANIFEST.json`.

The released sample is the one building in the evaluation set for which
we have unambiguous redistribution rights under research-only terms. We
do not describe its specific project id, scale, or difficulty position
within the evaluation set — those characterizations could either be
read as cherry-picking or could inadvertently narrow-identify the
building. The released GT (this file) and per-instance metrics
(`../metrics/`) are sufficient for any quantitative analysis a reader
needs.

Schema version: `cvn.gt.skeleton.v1`.

## Schema

```jsonc
{
  "schema_version": "cvn.gt.skeleton.v1",
  "project_id": "<string>",
  "difficulty": "easy" | "medium" | "hard",
  "floors": [
    {
      "floor_id": "<string>",
      "floor_name": "<string, e.g. 'beam plan at +5.350m elevation' — may be null if not specified>",
      "elevation_m": <float>,
      "height_m": <float | null>,
      "source_blueprint_id": "<string, internal sheet ID>"
    }
  ],
  "axes": {
    "horizontal": [{"label": "<string>", "position_norm": <float in 0..1>, "source_floor": "<floor_id>"}],
    "vertical":   [{"label": "<string>", "position_norm": <float in 0..1>, "source_floor": "<floor_id>"}]
  },
  "columns": [
    {
      "column_id": "<string>",
      "floor_id": "<floor_id>",
      "axis_h": "<string>", "axis_v": "<string>",   // grid coords (e.g. "A", "3")
      "section_label": "<string, e.g. 'KZ1' for frame column #1>"
    }
  ],
  "beams": [
    {
      "beam_id": "<string>",
      "floor_id": "<floor_id>",
      "label": "<string, e.g. 'KL5(3)' = frame beam #5 with 3 spans>",
      "spans": [
        {"start_axis": ["<h>", "<v>"], "end_axis": ["<h>", "<v>"]}
      ]
    }
  ]
}
```

## Annotation procedure (silver standard)

Applied internally to all 20 buildings (only the sample's result is
released here):

1. Run the full StructAgent pipeline on the building.
2. Author manually cross-checks the output `project_semantic.json` against
   the source drawings, page by page.
3. Corrections are applied directly in the JSON (axis labels, column
   coordinates, beam span topology, section labels).
4. The corrected JSON, stripped of pipeline-internal fields, is committed
   as `<id>.gt.json`.

Per-building annotation effort: 2–6 hours, on the order of ~80 author-hours
across the full 20-building set.

## Domain glossary (for non-civil-engineering readers)

| Term | Meaning |
|---|---|
| 平法 / "plan-based representation" | A Chinese national standard (GB 11G101 series) for representing structural elements directly on plan drawings with coded labels rather than detailed sections. |
| KL | "frame beam" (`框架梁`) — main beam between columns. |
| WKL | "roof frame beam" (`屋面框架梁`) — frame beam at roof level. |
| KZ | "frame column" (`框架柱`) — primary load-bearing column. |
| Secondary axis (e.g. `1/3`) | An axis inserted between two main axes; `1/3` means the first secondary axis between axes 3 and 4. |
| `position_norm` | Normalized position along the drawing's width or height, in [0, 1]. |
