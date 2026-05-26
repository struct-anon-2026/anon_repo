#!/usr/bin/env python3
"""BlueprintAgent project evaluator (self-audit mode).

This is a no-ground-truth evaluation harness that compares CVN v4E pipeline
products against the project's own internal gates and produces a single
``metrics.json`` per project. The output is cross-project comparable and
ready to plug into the paper's Section 5 baseline + ablation tables.

Self-audit mode reads:
  outputs/final/project_semantic.json
  qa/semantic_gate.json
  outputs/web3d/c3d_validation.json
  outputs/fem/fem_export.json
  outputs/fem/analysis_log.json     (optional, OpenSees solver run)

When ``--gt`` is later passed, this script will additionally compute
axis IoU, beam/column F1, etc. That GT mode is left for future work and
is documented in ``paper/eval/README.md``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _safe(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return None


def _floor_summary(floor: dict[str, Any]) -> dict[str, Any]:
    ps = floor.get('primary_structure') or {}
    beams = ps.get('main_beams') or []
    cols = ps.get('columns') or []
    span_sum = sum((b.get('span_count') or 0) for b in beams)
    ns_with_seq = sum(1 for b in beams if b.get('node_sequence'))
    return {
        'floor_id': floor.get('floor_id'),
        'elevation_m': floor.get('elevation_m'),
        'beam_entities': len(beams),
        'beam_fem_segments': span_sum,
        'beams_with_node_sequence': ns_with_seq,
        'columns': len(cols),
    }


def _axis_audit_summary(grid: dict[str, Any]) -> dict[str, Any]:
    apa = grid.get('axis_precision_adjudication') or {}
    decisions = apa.get('decisions') or apa.get('items') or []
    accepted = sum(1 for d in decisions if str(d.get('decision') or d.get('status') or '').lower() in {'accept', 'accepted'})
    rejected = sum(1 for d in decisions if str(d.get('decision') or d.get('status') or '').lower() in {'reject', 'rejected', 'rejected_then_retried'})
    deltas: list[int] = []
    for d in decisions:
        delta = d.get('cv_vs_final_dpx')
        if isinstance(delta, (int, float)):
            deltas.append(abs(int(delta)))
    return {
        'present': bool(apa),
        'provenance': apa.get('provenance'),
        'decision_count': len(decisions),
        'accepted': accepted,
        'rejected': rejected,
        'cv_vs_llm_max_dpx': max(deltas) if deltas else None,
        'cv_vs_llm_mean_dpx': round(sum(deltas) / len(deltas), 3) if deltas else None,
    }


def _span_audit_summary(grid: dict[str, Any]) -> dict[str, Any]:
    sa = grid.get('span_adjudication') or {}
    return {
        'present': bool(sa),
        'status': sa.get('status'),
        'source': sa.get('source'),
        'x_evidence_count': len(sa.get('x_span_evidence_refs') or []),
        'y_evidence_count': len(sa.get('y_span_evidence_refs') or []),
    }


def evaluate(version_root: Path) -> dict[str, Any]:
    sem_path = version_root / 'outputs/final/project_semantic.json'
    if not sem_path.exists():
        raise SystemExit(f'no project_semantic.json under {version_root}')
    sem = read_json(sem_path)
    gate = _safe(version_root / 'qa/semantic_gate.json')
    c3d = _safe(version_root / 'outputs/web3d/c3d_validation.json')
    fem = _safe(version_root / 'outputs/fem/fem_export.json')
    solver = _safe(version_root / 'outputs/fem/analysis_log.json')

    project = sem.get('project') or {}
    floors = sem.get('floors') or []
    blueprints = sem.get('blueprints') or []

    per_floor = [_floor_summary(f) for f in floors]
    total_beams = sum(f['beam_entities'] for f in per_floor)
    total_segments = sum(f['beam_fem_segments'] for f in per_floor)
    total_columns = sum(f['columns'] for f in per_floor)

    axis_audits = []
    span_audits = []
    for f in floors:
        ps = f.get('primary_structure') or {}
        grid = ps.get('grid') or {}
        axis_audits.append({'floor_id': f.get('floor_id'), **_axis_audit_summary(grid)})
        span_audits.append({'floor_id': f.get('floor_id'), **_span_audit_summary(grid)})

    cv_dpx_all = [a['cv_vs_llm_max_dpx'] for a in axis_audits if a.get('cv_vs_llm_max_dpx') is not None]
    project_cv_max = max(cv_dpx_all) if cv_dpx_all else None

    qg = (gate or {}).get('quality_gates') or {}

    metrics: dict[str, Any] = {
        'schema_version': 'cvn.eval.self_audit.v4E.1.0',
        'mode': 'self_audit',
        'version_root': str(version_root),
        'project': {
            'project_key': project.get('project_key'),
            'name': project.get('name'),
            'status': project.get('status'),
        },
        'inventory': {
            'building_count': 1,
            'floor_count': len(floors),
            'blueprint_count': len(blueprints),
            'total_beam_entities': total_beams,
            'total_beam_fem_segments': total_segments,
            'total_columns': total_columns,
            'per_floor': per_floor,
        },
        'gate': {
            'ok': (gate or {}).get('ok'),
            'status': (gate or {}).get('status'),
            'error_count': len((gate or {}).get('errors') or []),
            'warning_count': len((gate or {}).get('warnings') or []),
            'quality_gates': {
                'schema_valid': qg.get('schema_valid'),
                'geometry_valid': qg.get('geometry_valid'),
                'evidence_valid': qg.get('evidence_valid'),
                'axis_cv_adoption_valid': qg.get('axis_cv_adoption_valid'),
                'axis_span_reading_valid': qg.get('axis_span_reading_valid'),
                'axis_px_span_ratio_valid': qg.get('axis_px_span_ratio_valid'),
            },
        },
        'axis_double_audit': {
            'per_floor': axis_audits,
            'project_cv_vs_llm_max_dpx': project_cv_max,
        },
        'span_adjudication': {
            'per_floor': span_audits,
        },
        'c3d': {
            'present': c3d is not None,
            'ok': (c3d or {}).get('ok'),
            'error_count': len((c3d or {}).get('errors') or []),
            'detail': {
                k: ((c3d or {}).get('details') or {}).get(k, {}).get('ok')
                for k in ('column_vertical_continuity', 'beam_endpoint_support', 'floor_height_monotonic', 'component_completeness')
            },
        },
        'fem': {
            'present': fem is not None,
            'ok': (fem or {}).get('ok'),
            'nodes_count': (fem or {}).get('nodes_count'),
            'elements_count': (fem or {}).get('elements_count'),
            'concrete_grade': (fem or {}).get('concrete_grade'),
        },
        'opensees_solver': {
            'present': solver is not None,
            'analyze_return_code': (solver or {}).get('analyze_return_code'),
            'ok': (solver or {}).get('ok'),
            'max_displacement_m': (solver or {}).get('max_displacement_m'),
            'max_displacement_at_node': (solver or {}).get('max_displacement_at_node'),
        },
    }
    return metrics


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='BlueprintAgent self-audit evaluator')
    p.add_argument('--version-root', required=True, help='projects/<id>/<building>/<run_ts>/<version>')
    p.add_argument('--out', required=True, help='output metrics.json path')
    p.add_argument('--print', action='store_true', help='also print to stdout')
    args = p.parse_args(argv)

    version_root = Path(args.version_root).resolve()
    metrics = evaluate(version_root)
    write_json(Path(args.out), metrics)
    if args.print:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
