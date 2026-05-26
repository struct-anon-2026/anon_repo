"""Evaluate ablation runs (A3/A4 cells × N=6 projects) against GT.

Each ablation instance lives at <SANDBOX>/exp_<cell>_<idx>/. Inside, the canonical
deliverable is `outputs/final/project_semantic.json` (sometimes under a nested
`projects/<key>/<building>/<ts>/v001/` sub-workspace).

This script:
  1. Resolves the right project_semantic.json under an exp root.
  2. Adapts it to the flat `{floors, axes, columns, beams}` schema that
     `_evaluate_vlm_baseline.py` uses.
  3. Runs the same IoU / F1 evaluator as B2 (so numbers are directly
     cross-comparable to the B2 baseline table).
  4. Emits paper/eval/results/<pid>__ablation_<cell>__metrics.json.

Usage:
  python paper/eval/_evaluate_ablation.py \
    --exp-root <SANDBOX>/exp_A3_1 --project-id 16 --cell A3 \
    --gt paper/gt/16.gt.json \
    --out paper/eval/results/16__ablation_A3__metrics.json

  python paper/eval/_evaluate_ablation.py --batch   # runs all 12 instances
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Reuse evaluators from the B2 script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evaluate_vlm_baseline import (  # type: ignore[import-not-found]
    best_floor_alignment,
    compute_axis_iou,
    evaluate_columns,
    evaluate_beams,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GT_DIR = REPO_ROOT / 'gt'
RESULTS_DIR = REPO_ROOT / 'eval' / 'results'
LAB_ROOT = Path('E:/lab')

PROJECT_ID_TO_GT = {
    '16': '16',
    '81_1': '81_1',
    '81_2': '81_2',
    '81_4': '81_4',
    '378': '378',
    '383': '383',
}

# exp idx → project_id, per paper/eval/handoff/README.md §1.1
IDX_TO_PROJECT = {1: '16', 2: '81_1', 3: '81_2', 4: '81_4', 5: '378', 6: '383'}


KZ_RE = re.compile(r'(KZ\d+[A-Za-z]?)')


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def find_semantic(exp_root: Path) -> Path | None:
    """Return the most authoritative project_semantic.json under exp_root.

    Preference order:
      1. <exp_root>/paper/eval/shadow_workspaces/*/outputs/final/project_semantic.json
         (new layout — agents post-2026-05-25 run in shadow workspace inside exp)
      2. <exp_root>/outputs/final/project_semantic.json (legacy direct-in-exp)
      3. <exp_root>/projects/*/*/*/v*/outputs/final/project_semantic.json
         (most recently modified wins when there are multiples)
    """
    shadow = sorted(
        exp_root.glob('paper/eval/shadow_workspaces/*/outputs/final/project_semantic.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for c in shadow:
        if c.stat().st_size > 1024:
            return c
    top = exp_root / 'outputs' / 'final' / 'project_semantic.json'
    if top.is_file() and top.stat().st_size > 1024:
        return top
    candidates = sorted(
        exp_root.glob('projects/*/*/*/*/outputs/final/project_semantic.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for c in candidates:
        if c.stat().st_size > 1024:
            return c
    return None


def _grid_to_axes(grid: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Convert {x_axis_labels, x_spans_mm, y_axis_labels, y_spans_mm} →
    {axes.horizontal[{label,position_norm}], axes.vertical[...]}."""
    x_labels = grid.get('x_axis_labels') or []
    y_labels = grid.get('y_axis_labels') or []
    x_spans = grid.get('x_spans_mm') or []
    y_spans = grid.get('y_spans_mm') or []

    def _build(labels: list, spans: list) -> list[dict]:
        if not labels:
            return []
        # cumulative positions from 0, normalized to [0,1]
        positions = [0.0]
        for s in spans:
            try:
                positions.append(positions[-1] + float(s))
            except (TypeError, ValueError):
                positions.append(positions[-1])
        total = positions[-1] if positions[-1] > 0 else 1.0
        # If we have more positions than labels, truncate; if fewer, pad uniformly.
        if len(positions) < len(labels):
            # uniform fallback
            return [
                {'label': lbl, 'position_norm': round(i / max(len(labels) - 1, 1), 4)}
                for i, lbl in enumerate(labels)
            ]
        return [
            {'label': lbl, 'position_norm': round(positions[i] / total, 4)}
            for i, lbl in enumerate(labels)
        ]

    return _build(x_labels, x_spans), _build(y_labels, y_spans)


def _merge_axes(per_floor: list[tuple[list[dict], list[dict]]]) -> tuple[list[dict], list[dict]]:
    """Union axes across floors; keep first observed position per label."""
    h_by_label: dict[str, dict] = {}
    v_by_label: dict[str, dict] = {}
    for h, v in per_floor:
        for a in h:
            h_by_label.setdefault(str(a['label']), a)
        for a in v:
            v_by_label.setdefault(str(a['label']), a)
    h_sorted = sorted(h_by_label.values(), key=lambda a: a.get('position_norm') or 0)
    v_sorted = sorted(v_by_label.values(), key=lambda a: a.get('position_norm') or 0)
    return h_sorted, v_sorted


def _extract_kz_type(col: dict) -> str:
    """Try several semantic locations for kz_type."""
    for k in ('kz_type', 'kz_label', 'label'):
        v = col.get(k)
        if v:
            m = KZ_RE.search(str(v))
            if m:
                return m.group(1)
            return str(v).strip()
    oid = str(col.get('object_id') or '')
    m = KZ_RE.search(oid)
    if m:
        return m.group(1)
    sid = str(col.get('source_candidate_id') or '')
    m = KZ_RE.search(sid)
    if m:
        return m.group(1)
    return ''


def _split_grid_node(node: str) -> tuple[str, str]:
    s = str(node or '')
    if '-' in s:
        h, v = s.split('-', 1)
        return h.strip(), v.strip()
    return s.strip(), ''


def _support_axes_from_nodes(node_sequence: list, direction: str) -> list[str]:
    """For direction=x, the varying part of node IDs is axis_h; for direction=y, axis_v."""
    direction = (direction or '').strip().lower()
    axes: list[str] = []
    for n in node_sequence or []:
        h, v = _split_grid_node(str(n))
        axes.append(h if direction == 'x' else v)
    # dedupe while preserving order
    seen = set()
    out = []
    for a in axes:
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def semantic_to_flat(doc: dict) -> dict:
    """Adapt CVN project_semantic.json → flat {floors, axes, columns, beams}."""
    floors_out: list[dict] = []
    cols_out: list[dict] = []
    beams_out: list[dict] = []
    per_floor_axes: list[tuple[list[dict], list[dict]]] = []

    for f in doc.get('floors', []) or []:
        fid = f.get('floor_id')
        elev = f.get('elevation_m')
        floors_out.append({'floor_id': fid, 'elevation_m': elev})

        ps = f.get('primary_structure') or {}
        grid = ps.get('grid') or {}
        h, v = _grid_to_axes(grid)
        per_floor_axes.append((h, v))

        for c in ps.get('columns') or []:
            h_axis, v_axis = _split_grid_node(c.get('grid_node') or '')
            sec = c.get('section') or {}
            cols_out.append({
                'id': c.get('object_id'),
                'kz_type': _extract_kz_type(c),
                'axis_h': h_axis,
                'axis_v': v_axis,
                'section': {
                    'w': sec.get('width_mm') or sec.get('w'),
                    'h': sec.get('height_mm') or sec.get('h'),
                },
                'floor': fid,
            })

        for b in ps.get('main_beams') or []:
            sec = b.get('section') or {}
            direction = b.get('direction')
            beams_out.append({
                'id': b.get('object_id'),
                'floor': fid,
                'label': b.get('label'),
                'direction': direction,
                'support_axes': _support_axes_from_nodes(b.get('node_sequence') or [], direction or ''),
                'span_count': b.get('span_count'),
                'section': {
                    'w': sec.get('width_mm') or sec.get('w'),
                    'h': sec.get('height_mm') or sec.get('h'),
                },
            })

    h_axes, v_axes = _merge_axes(per_floor_axes)
    return {
        'floors': floors_out,
        'axes': {'horizontal': h_axes, 'vertical': v_axes},
        'columns': cols_out,
        'beams': beams_out,
    }


def evaluate_one(pred_doc: dict, gt: dict) -> dict:
    floor_map = best_floor_alignment(pred_doc.get('floors', []), gt.get('floors', []))
    h_iou, h_max_d = compute_axis_iou(
        pred_doc.get('axes', {}).get('horizontal', []),
        gt.get('axes', {}).get('horizontal', []),
    )
    v_iou, v_max_d = compute_axis_iou(
        pred_doc.get('axes', {}).get('vertical', []),
        gt.get('axes', {}).get('vertical', []),
    )
    cols = evaluate_columns(pred_doc.get('columns', []), gt.get('columns', []), floor_map)
    beams = evaluate_beams(pred_doc.get('beams', []), gt.get('beams', []), floor_map)
    return {
        'floor_alignment': floor_map,
        'inventory': {
            'pred': {
                'floors': len(pred_doc.get('floors', [])),
                'axes_h': len(pred_doc.get('axes', {}).get('horizontal', [])),
                'axes_v': len(pred_doc.get('axes', {}).get('vertical', [])),
                'columns': len(pred_doc.get('columns', [])),
                'beams': len(pred_doc.get('beams', [])),
            },
            'gt': {
                'floors': len(gt.get('floors', [])),
                'axes_h': len(gt.get('axes', {}).get('horizontal', [])),
                'axes_v': len(gt.get('axes', {}).get('vertical', [])),
                'columns': len(gt.get('columns', [])),
                'beams': len(gt.get('beams', [])),
            },
        },
        'axis_grid': {
            'h_label_iou': h_iou,
            'v_label_iou': v_iou,
            'h_position_max_abs_error': h_max_d,
            'v_position_max_abs_error': v_max_d,
        },
        'columns': cols,
        'beams': beams,
    }


def run_one(exp_root: Path, project_id: str, cell: str, gt_path: Path, out_path: Path) -> dict:
    semantic_path = find_semantic(exp_root)
    if semantic_path is None:
        result = {
            'schema_version': 'cvn.ablation_eval.v1',
            'project_id': project_id,
            'cell': cell,
            'exp_root': str(exp_root),
            'semantic_path': None,
            'status': 'NO_SEMANTIC_OUTPUT',
            'error': 'no project_semantic.json found under exp root',
        }
        write_json(out_path, result)
        return result

    pred_raw = read_json(semantic_path)
    pred_flat = semantic_to_flat(pred_raw)
    gt = read_json(gt_path)
    metrics = evaluate_one(pred_flat, gt)

    result = {
        'schema_version': 'cvn.ablation_eval.v1',
        'project_id': project_id,
        'cell': cell,
        'exp_root': str(exp_root),
        'semantic_path': str(semantic_path),
        'gt_path': str(gt_path),
        'status': 'OK',
        **metrics,
    }
    write_json(out_path, result)
    return result


BATCH_INSTANCES = [
    (cell, idx) for cell in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1', 'B3') for idx in range(1, 7)
]


def main() -> int:
    p = argparse.ArgumentParser(description='Ablation evaluator (A3/A4 cells)')
    p.add_argument('--exp-root', help='<SANDBOX>/exp_<cell>_<idx>')
    p.add_argument('--project-id', help='one of 16 / 81_1 / 81_2 / 81_4 / 378 / 383')
    p.add_argument('--cell', help='A3 or A4 etc')
    p.add_argument('--gt', help='paper/gt/<id>.gt.json')
    p.add_argument('--out', help='output metrics path')
    p.add_argument('--batch', action='store_true', help='run all 12 (A3+A4) × 6 instances')
    args = p.parse_args()

    if args.batch:
        all_results = []
        for cell, idx in BATCH_INSTANCES:
            project_id = IDX_TO_PROJECT[idx]
            exp_root = LAB_ROOT / f'exp_{cell}_{idx}'
            gt_path = GT_DIR / f'{project_id}.gt.json'
            kind = 'baseline' if cell.startswith('B') else 'ablation'
            out_path = RESULTS_DIR / f'{project_id}__{kind}_{cell}__metrics.json'
            if not gt_path.is_file():
                print(f'[SKIP] {cell}_{idx} ({project_id}): GT missing at {gt_path}')
                continue
            if not exp_root.is_dir():
                print(f'[SKIP] {cell}_{idx} ({project_id}): exp_root missing')
                continue
            r = run_one(exp_root, project_id, cell, gt_path, out_path)
            status = r['status']
            if status == 'OK':
                cf1 = r['columns']['f1']
                bf1 = r['beams']['f1']
                print(f'[OK]   {cell}_{idx} {project_id}: cols_f1={cf1:.3f} beams_f1={bf1:.3f} → {out_path.name}')
            else:
                print(f'[FAIL] {cell}_{idx} {project_id}: {status}')
            all_results.append(r)
        # write batch summary
        cells_seen = sorted({r['cell'] for r in all_results})
        summary_path = REPO_ROOT / 'paper_materials' / f'ablation_batch_metrics_N6_{"_".join(cells_seen)}.json'
        write_json(summary_path, {
            'schema_version': 'cvn.ablation_batch.v1',
            'cells': cells_seen,
            'projects': list(IDX_TO_PROJECT.values()),
            'per_instance': all_results,
        })
        print(f'\nWrote batch summary → {summary_path}')
        return 0

    if not all([args.exp_root, args.project_id, args.cell, args.gt, args.out]):
        p.error('--exp-root --project-id --cell --gt --out are all required (unless --batch)')
    r = run_one(
        Path(args.exp_root),
        args.project_id,
        args.cell,
        Path(args.gt),
        Path(args.out),
    )
    print(json.dumps({
        'status': r['status'],
        'project_id': r.get('project_id'),
        'cell': r.get('cell'),
        'cols_f1': r.get('columns', {}).get('f1'),
        'beams_f1': r.get('beams', {}).get('f1'),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
