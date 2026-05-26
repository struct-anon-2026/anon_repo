"""Aggregate per-instance metrics into the paper's Tables 3 and 4.

Reads every `<id>__<cell>__metrics.json` (and `<id>__metrics.json` for
the main-system self-audit) under --in, groups by cell, and emits a CSV
with macro-average over the 20 buildings.

Usage:
    python aggregate.py --in ../../data/metrics --out /tmp/tables.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

METRIC_KEYS = [
    ("axis_grid", "h_label_iou"),
    ("axis_grid", "v_label_iou"),
    ("columns", "precision"),
    ("columns", "recall"),
    ("columns", "f1"),
    ("columns", "section_match_rate"),
    ("beams", "precision"),
    ("beams", "recall"),
    ("beams", "f1"),
    ("beams", "topology_match_rate"),
    ("beams", "label_only_f1"),
]


def cell_of(stem: str) -> str:
    # "<id>__ablation_A3__metrics" -> "ablation_A3"
    # "<id>__baseline_B1__metrics" -> "baseline_B1"
    # "<id>__metrics"              -> "main_self_audit"
    parts = stem.split("__")
    if len(parts) == 2:
        return "main_self_audit"
    return parts[1]


def get_nested(d: dict, path: tuple[str, ...]):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    by_cell: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(args.inp.glob("*__metrics.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[skip] {path}: {e}")
            continue
        by_cell[cell_of(path.stem)].append({"_id": payload.get("project_id"), **payload})

    # Build CSV: rows = cells, cols = METRIC_KEYS (macro avg + per-project list).
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "n"] + [".".join(k) + "_macro" for k in METRIC_KEYS])
        for cell, rows in sorted(by_cell.items()):
            macros: list[str] = []
            for k in METRIC_KEYS:
                vals = [get_nested(r, k) for r in rows]
                vals = [v for v in vals if isinstance(v, (int, float))]
                macros.append(f"{statistics.fmean(vals):.4f}" if vals else "—")
            w.writerow([cell, len(rows)] + macros)

    print(f"[ok] wrote {args.out} with {len(by_cell)} cells")
    for cell, rows in sorted(by_cell.items()):
        print(f"  {cell}: n={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
