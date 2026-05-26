"""Deep-copy a CVN project version_root to a shadow workspace.

Used by per-exp RUN_HERE.md step 1 to create an isolated, writable copy of the
read-only source. The destination is typically under
``paper/eval/shadow_workspaces/<cell>_<idx>/`` and the source under
``projects/<id>/<building>/<ts>/v00X/`` (both inside the spawned exp folder).

Usage:
    python paper/eval/shadow_copy.py \\
        --src projects/16/two_floor_demo/20260523_205602_305068/v001 \\
        --dst paper/eval/shadow_workspaces/A1_1 \\
        [--force]                # overwrite existing dst (default: refuse)
        [--clean-stage S [S ...]] # delete listed stage artifacts after copy
                                  # known stages: stage1 / stage2 / outputs / qa

Guarantees:
  - Source is never written to.
  - Hidden / large / cache dirs (__pycache__, .git, .DS_Store) are skipped.
  - Symlinks are followed (we want concrete copies, not links back to source).
  - Errors during copy are NOT silently swallowed.
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

# Patterns that should never be copied into the shadow
IGNORE_PATTERNS = ('__pycache__', '.git', '.pytest_cache', '.DS_Store', 'Thumbs.db')

# Per-stage artifact globs (relative to dst root); --clean-stage uses these
STAGE_CLEAN_GLOBS = {
    'stage1': [
        'work/stage1_evidence/*/coordinate_audit_v4E.json',
        'work/stage1_evidence/*/axis_grid_llm_v4E.json',
        'work/stage1_evidence/*/thin_axis_strips_v4E.json',
        'work/stage1_evidence/*/inspect_*',
    ],
    'stage2': [
        'work/stage2_primary/*/beam_text_candidates.json',
        'work/stage2_primary/*/checkpoint_beam_adjudication.json',
        'work/stage2_primary/*/llm_beam_adjudication_v4E.json',
        'work/stage2_primary/*/primary_structure.json',
        'work/stage2_primary/*/checkpoint_column_adjudication.json',
        'work/stage2_primary/*/llm_column_adjudication_v4E.json',
    ],
    'outputs': [
        'outputs/final/project_semantic.json',
        'outputs/web3d/*',
        'outputs/fem/*',
    ],
    'qa': [
        'qa/semantic_gate.json',
        'qa/visual_output_audit.json',
    ],
}


def _ignore(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if any(p in n for p in IGNORE_PATTERNS)]


def deep_copy(src: Path, dst: Path, force: bool) -> int:
    if not src.exists() or not src.is_dir():
        print(f'ERROR: --src does not exist or is not a directory: {src}', file=sys.stderr)
        return 2
    if dst.exists():
        if not force:
            print(f'ERROR: --dst already exists: {dst}\n'
                  f'  Pass --force to overwrite, or delete it manually first.', file=sys.stderr)
            return 2
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, symlinks=False, ignore=_ignore)
    return 0


def clean_stages(dst: Path, stages: list[str]) -> int:
    unknown = [s for s in stages if s not in STAGE_CLEAN_GLOBS]
    if unknown:
        print(f'ERROR: unknown --clean-stage values: {unknown}\n'
              f'  Known: {sorted(STAGE_CLEAN_GLOBS.keys())}', file=sys.stderr)
        return 2
    removed = 0
    for stage in stages:
        for pat in STAGE_CLEAN_GLOBS[stage]:
            for path in dst.glob(pat):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed += 1
    print(f'cleaned {removed} artifact(s) across stages: {stages}')
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Deep-copy a CVN version_root to a shadow workspace')
    ap.add_argument('--src', required=True, help='Source version_root (read-only)')
    ap.add_argument('--dst', required=True, help='Destination shadow workspace')
    ap.add_argument('--force', action='store_true', help='Overwrite dst if it exists')
    ap.add_argument('--clean-stage', nargs='*', default=[],
                    help=f'Stages to wipe after copy: {sorted(STAGE_CLEAN_GLOBS.keys())}')
    args = ap.parse_args(argv)

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    rc = deep_copy(src, dst, args.force)
    if rc != 0:
        return rc
    print(f'copied {src} -> {dst}')

    if args.clean_stage:
        rc = clean_stages(dst, args.clean_stage)
        if rc != 0:
            return rc

    return 0


if __name__ == '__main__':
    sys.exit(main())
