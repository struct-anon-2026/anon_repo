"""Sanitize metrics, GT, and eval scripts for anonymous release.

Copies files from the source repo into the anon_repo layout and rewrites
absolute paths so that no identifying information leaks via path strings.

Usage:
    python scripts/sanitize.py --src ../../ --dst . --sample-id 378 --strict

Run from anon_repo/ root. The --src flag points to the project root
(the directory that contains `experiments/eval/` and `experiments/gt/`;
older layouts used `paper/eval/` and `paper/gt/`, both are supported).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path replacement rules applied to every string value in JSON, and to
# every string *literal* found in Python source files. Order matters.
# ---------------------------------------------------------------------------

REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    # Sandbox roots first (longest match wins).
    (re.compile(r"E:[\\/]+lab[\\/]+exp_(?P<cell>[A-Za-z0-9_]+)[\\/]+[^\"']*?project_semantic\.json",
                re.IGNORECASE),
     "<SANDBOX>/exp_\\g<cell>/.../project_semantic.json"),
    (re.compile(r"E:[\\/]+lab[\\/]+exp_(?P<cell>[A-Za-z0-9_]+)[\\/]+", re.IGNORECASE),
     "<SANDBOX>/exp_\\g<cell>/"),
    (re.compile(r"E:[\\/]+lab[\\/]+", re.IGNORECASE),
     "<SANDBOX>/"),
    # Project-root paths — new layout (experiments/) takes precedence.
    (re.compile(r"E:[\\/]+Claude_cli_lab[\\/]+experiments[\\/]+gt[\\/]+", re.IGNORECASE),
     "data/gt/"),
    (re.compile(r"E:[\\/]+Claude_cli_lab[\\/]+experiments[\\/]+eval[\\/]+", re.IGNORECASE),
     "code/eval/"),
    # Older layout (paper/) — kept for backward compatibility with pre-reorganization metrics.
    (re.compile(r"E:[\\/]+Claude_cli_lab[\\/]+paper[\\/]+gt[\\/]+", re.IGNORECASE),
     "data/gt/"),
    (re.compile(r"E:[\\/]+Claude_cli_lab[\\/]+paper[\\/]+eval[\\/]+", re.IGNORECASE),
     "code/eval/"),
    (re.compile(r"E:[\\/]+Claude_cli_lab[\\/]+", re.IGNORECASE),
     "<REPO_ROOT>/"),
    # Windows user homes (catches any leaked user name).
    (re.compile(r"C:[\\/]+Users[\\/]+[^\\/\"'\s]+[\\/]+", re.IGNORECASE),
     "<HOME>/"),
    # POSIX home (less likely in this project but cheap to add).
    (re.compile(r"/home/[^/\"'\s]+/", re.IGNORECASE),
     "<HOME>/"),
    (re.compile(r"/Users/[^/\"'\s]+/", re.IGNORECASE),
     "<HOME>/"),
]


def sanitize_string(value: str) -> str:
    for pat, repl in REPLACEMENTS:
        value = pat.sub(repl, value)
    return value


def sanitize_obj(obj):
    if isinstance(obj, str):
        return sanitize_string(obj)
    if isinstance(obj, list):
        return [sanitize_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: sanitize_obj(v) for k, v in obj.items()}
    return obj


def copy_json(src: Path, dst: Path) -> int:
    """Copy a JSON file, sanitizing all string values. Returns # of replacements."""
    raw = src.read_text(encoding="utf-8")
    obj = json.loads(raw)
    cleaned = sanitize_obj(obj)
    cleaned_text = json.dumps(cleaned, indent=2, ensure_ascii=False)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(cleaned_text + "\n", encoding="utf-8")
    # naive count: how many bytes changed
    return abs(len(raw) - len(cleaned_text))


def copy_pyfile(src: Path, dst: Path) -> int:
    """Copy a Python file, sanitizing string literals. Returns # of replacements."""
    raw = src.read_text(encoding="utf-8")
    cleaned = sanitize_string(raw)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(cleaned, encoding="utf-8")
    return abs(len(raw) - len(cleaned))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, required=True,
                    help="Source project root (contains paper/eval/ and paper/gt/)")
    ap.add_argument("--dst", type=Path, required=True,
                    help="Destination anon_repo/ root")
    ap.add_argument("--sample-id", type=str, default=None,
                    help="Project id whose GT JSON is released alongside the sample drawings (e.g. '378'). "
                         "Only this one GT is copied to data/gt/. The other 19 buildings are represented "
                         "by metrics JSON only; their per-entity ground-truth is withheld for consistency "
                         "with the drawing-release policy (one sample project total).")
    ap.add_argument("--strict", action="store_true",
                    help="Fail if no metrics files are copied (catches misconfigured paths) or if "
                         "--sample-id is missing.")
    args = ap.parse_args()

    if args.strict and not args.sample_id:
        print("[error] --strict requires --sample-id <project_id>", file=sys.stderr)
        print("        (which building is released as the visual sample? its GT is released too;", file=sys.stderr)
        print("         all other buildings' GT is withheld.)", file=sys.stderr)
        return 4

    # Resolve source layout — prefer new (experiments/) over old (paper/).
    candidates_eval = [args.src / "experiments" / "eval", args.src / "paper" / "eval"]
    candidates_gt = [args.src / "experiments" / "gt", args.src / "paper" / "gt"]
    src_eval = next((p for p in candidates_eval if p.is_dir()), candidates_eval[0])
    src_gt = next((p for p in candidates_gt if p.is_dir()), candidates_gt[0])
    src_results = src_eval / "results"

    dst_metrics = args.dst / "data" / "metrics"
    dst_gt = args.dst / "data" / "gt"
    dst_code = args.dst / "code" / "eval"

    if not src_results.is_dir():
        print(f"[error] results dir not found: {src_results}", file=sys.stderr)
        print("        tried: experiments/eval/results/ and paper/eval/results/", file=sys.stderr)
        return 2
    if not src_gt.is_dir():
        print(f"[error] gt dir not found: {src_gt}", file=sys.stderr)
        print("        tried: experiments/gt/ and paper/gt/", file=sys.stderr)
        return 2
    print(f"[src] eval = {src_eval.relative_to(args.src) if src_eval.is_relative_to(args.src) else src_eval}")
    print(f"[src] gt   = {src_gt.relative_to(args.src) if src_gt.is_relative_to(args.src) else src_gt}")

    # 1. metrics JSON
    n_metrics = 0
    for f in sorted(src_results.glob("*__metrics.json")):
        # skip dropped projects (e.g. 81_3, 340)
        stem_parts = f.stem.split("__")
        proj = stem_parts[0]
        if proj in {"81_3", "340"}:
            continue
        delta = copy_json(f, dst_metrics / f.name)
        print(f"[metrics] {f.name}   (replaced ~{delta} chars)")
        n_metrics += 1

    if args.strict and n_metrics == 0:
        print("[error] --strict and no metrics copied", file=sys.stderr)
        return 3

    # 2. ground truth — release ONLY the sample project's GT (consistency:
    #    one drawing project released visually = one GT released).
    #    Other projects' per-entity GT is withheld because it encodes the
    #    structural skeleton of buildings whose source drawings we cannot
    #    redistribute.
    n_gt = 0
    if args.sample_id:
        expected = src_gt / f"{args.sample_id}.gt.json"
        if not expected.exists():
            print(f"[error] sample GT not found: {expected}", file=sys.stderr)
            print(f"        expected file: {src_gt.name}/{args.sample_id}.gt.json", file=sys.stderr)
            return 5
        delta = copy_json(expected, dst_gt / expected.name)
        print(f"[gt]      {expected.name}   (sample-only release, replaced ~{delta} chars)")
        n_gt = 1
    else:
        print("[gt]      skipped (no --sample-id given; only the sample project's GT is releasable)")

    # 3. eval scripts
    n_py = 0
    for f in sorted(src_eval.glob("*.py")):
        # skip private helper scripts that orchestrate sandboxes
        if f.stem.startswith("_") and f.stem not in {
            "_evaluate_ablation", "_evaluate_vlm_baseline", "_prepare_vlm_inputs"
        }:
            continue
        delta = copy_pyfile(f, dst_code / f.name)
        print(f"[script]  {f.name}   (replaced ~{delta} chars)")
        n_py += 1

    print()
    print(f"Sanitized: {n_metrics} metrics, {n_gt} GT (sample only), {n_py} scripts.")
    print("Next: python scripts/audit_anonymity.py --root .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
