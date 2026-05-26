"""Audit anon_repo/ for identifying-information leaks.

Greps every text file in anon_repo/ for known identifying strings.
Returns non-zero exit code on any hit so it can be wired into a
pre-submission CI gate.

Before submission: fill in AUDIT_TERMS with your real identifying
strings (name, affiliation, city, email, GitHub handle, burner handle,
internal codenames). Do this in a local copy that you never commit;
the committed version of this script intentionally ships with empty
defaults so the file itself doesn't leak identity.

Usage:
    python scripts/audit_anonymity.py [--root .]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# FILL THESE IN LOCALLY BEFORE RUNNING.
# Each entry is either a literal string or a regex (when prefixed with `re:`).
# The committed version is intentionally empty to avoid logging identity here.
# ---------------------------------------------------------------------------

AUDIT_TERMS: list[str] = [
    # --- Real-identity terms (FILL IN before running, in a LOCAL copy never committed) ---
    # NOTE: The committed version of this file ships with NO real-identity strings,
    # not even as comments — comments would leak the very identity we want to hide.
    # Maintain a local copy of this script (e.g. ../audit_local.py outside the repo
    # tree) with the real terms filled in, and run that copy instead of this one.
    # The expected per-line format is:    "<some real string>",
    # See scripts/README.md for the workflow.

    # --- Internal sandbox paths (safe to ship; they're machine paths, not identity) ---
    "E:\\lab",
    "C:\\Users",
]

# Extensions we audit. Add as needed; binary files are skipped.
TEXT_EXTS = {".md", ".py", ".json", ".txt", ".yaml", ".yml", ".toml",
             ".cfg", ".ini", ".sh", ".bat", ".rst"}

# Files to skip entirely.
SKIP_PATHS = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}


def compile_term(term: str) -> re.Pattern:
    if term.startswith("re:"):
        return re.compile(term[3:])
    return re.compile(re.escape(term), re.IGNORECASE)


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PATHS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        yield path


def audit(root: Path, terms: list[str]) -> int:
    if not terms:
        print("[warn] AUDIT_TERMS is empty — fill it in before relying on this gate.",
              file=sys.stderr)
        # We still scan to catch the always-on sandbox-path terms; if they're
        # also empty, we exit with code 1 to make this obvious.
        return 1

    patterns = [(t, compile_term(t)) for t in terms]
    hits: list[tuple[Path, int, str, str]] = []

    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"[skip] {path}: {e}", file=sys.stderr)
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for term, pat in patterns:
                if pat.search(line):
                    hits.append((path, lineno, term, line.strip()[:120]))

    if not hits:
        print(f"[ok] 0 hits across {sum(1 for _ in iter_text_files(root))} files.")
        return 0

    print(f"[fail] {len(hits)} identity-leak hit(s):")
    for path, lineno, term, snippet in hits:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        print(f"  {rel}:{lineno}  [{term}]  {snippet}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."),
                    help="anon_repo root to audit (default: cwd)")
    args = ap.parse_args()
    return audit(args.root.resolve(), AUDIT_TERMS)


if __name__ == "__main__":
    raise SystemExit(main())
