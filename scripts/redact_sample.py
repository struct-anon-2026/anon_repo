"""Redact and rename the sample project's source sheets.

Reads originals from data/samples/_raw_pre_redaction/ (gitignored),
applies automatic redaction steps, writes the result to data/samples/.
Manual title-block masking is still required afterwards — this script
only handles what can be done deterministically.

Automatic steps applied:
  1. Downsample to <= ~200 dpi (cap the longer edge at MAX_EDGE_PX).
  2. Strip EXIF metadata.
  3. Convert .jpg -> .png (lossless after downsample; smaller artefacts).
  4. Rename to anonymized scheme: sheet_NN_<role>.png

Manual step required after this script (see TODO printout):
  - Mask design-institute stamps, project codes, engineer signatures,
    and project-name fields in the title block of each output sheet.
  - Use any image editor; just paint over with an opaque rectangle.

Usage:
    python scripts/redact_sample.py --in data/samples/_raw_pre_redaction \\
                                    --out data/samples \\
                                    --manifest data/samples/MANIFEST.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except ImportError:
    print("[error] Pillow is required: pip install Pillow", file=sys.stderr)
    raise SystemExit(2)


MAX_EDGE_PX = 2400   # ~200 dpi for an A1 (594 x 841 mm) sheet


# Map original filename substring -> output filename per the MANIFEST.
# Order matters; first substring match wins.
RENAME_RULES: list[tuple[str, str]] = [
    ("1~4层柱平面", "sheet_01_floors_1_to_4_column_plan.png"),
    ("2层梁平面",   "sheet_02_floor_F2_3_90m_beam_plan.png"),
    ("3层梁平面",   "sheet_03_floor_F3_11_70m_beam_plan.png"),
    ("4~5层梁平面", "sheet_04_floors_F4_to_F5_beam_plan.png"),
    ("5~6层柱平面", "sheet_05_floors_5_to_6_column_plan.png"),
    ("6层梁平面",   "sheet_06_floor_F6_23_10m_beam_plan.png"),
]


def output_name_for(original: Path) -> str | None:
    name = original.name
    for substr, out in RENAME_RULES:
        if substr in name:
            return out
    return None


def redact_one(src: Path, dst: Path) -> dict:
    img = Image.open(src)
    w0, h0 = img.size
    # 1. downsample
    longer = max(w0, h0)
    if longer > MAX_EDGE_PX:
        scale = MAX_EDGE_PX / longer
        img = img.resize((int(w0 * scale), int(h0 * scale)), Image.LANCZOS)
    # 2. drop EXIF by re-saving without info
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, format="PNG", optimize=True)
    return {
        "src": str(src.name),
        "dst": str(dst.name),
        "original_px": [w0, h0],
        "released_px": list(img.size),
        "dst_bytes": dst.stat().st_size,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in",  dest="src_dir",  type=Path, required=True)
    ap.add_argument("--out", dest="dst_dir",  type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=None,
                    help="If given, update audit_status in MANIFEST.json after redaction.")
    args = ap.parse_args()

    if not args.src_dir.is_dir():
        print(f"[error] source dir not found: {args.src_dir}", file=sys.stderr)
        return 2

    log: list[dict] = []
    skipped: list[str] = []
    for src in sorted(args.src_dir.iterdir()):
        if src.is_dir() or src.name.startswith("."):
            continue
        out_name = output_name_for(src)
        if out_name is None:
            skipped.append(src.name)
            continue
        dst = args.dst_dir / out_name
        info = redact_one(src, dst)
        print(f"[redacted] {info['src']}  ->  {info['dst']}  "
              f"({info['original_px']} -> {info['released_px']}, "
              f"{info['dst_bytes']/1024:.0f} KB)")
        log.append(info)

    print()
    print(f"Redacted {len(log)} sheets to {args.dst_dir}/")
    if skipped:
        print(f"Skipped (no rename rule): {skipped}")

    print()
    print("=" * 64)
    print("REMAINING MANUAL STEP — required before submission:")
    print("=" * 64)
    print("Open each output sheet and mask, with an opaque rectangle:")
    print("  - the design-institute stamp (often a red round seal)")
    print("  - any project code, project name, address in the title block")
    print("  - the engineer's / reviewer's signature")
    print("  - any phone numbers, fax numbers, or contact info")
    print("Then re-run audit:  python scripts/audit_anonymity.py --root .")

    if args.manifest and args.manifest.exists():
        m = json.loads(args.manifest.read_text(encoding="utf-8"))
        m["audit_status"] = (
            f"Automatic redaction complete ({len(log)} sheets, max edge {MAX_EDGE_PX} px). "
            "MANUAL title-block masking still required before release."
        )
        args.manifest.write_text(
            json.dumps(m, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nUpdated {args.manifest} audit_status.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
