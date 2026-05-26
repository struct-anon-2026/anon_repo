#!/usr/bin/env python3
"""Prepare per-project VLM input packs for the N=6 paper experiment."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SAMPLES: dict[str, dict[str, str]] = {
    "16": {
        "version_root": "projects/16/two_floor_demo/20260523_205602_305068/v001",
        "gt": "paper/gt/16.gt.json",
        "difficulty": "easy",
    },
    "81_1": {
        "version_root": "projects/81_1/building_unknown/20260524_093150_445010/v002",
        "gt": "paper/gt/81_1.gt.json",
        "difficulty": "medium",
    },
    "81_2": {
        "version_root": "projects/81_2/building_unknown/20260524_115839_069361/v001",
        "gt": "paper/gt/81_2.gt.json",
        "difficulty": "medium",
    },
    "81_4": {
        "version_root": "projects/81_4/building_unknown/20260524_120219_166820/v001",
        "gt": "paper/gt/81_4.gt.json",
        "difficulty": "medium",
    },
    "378": {
        "version_root": "projects/378/building_unknown/20260524_121520_648927/v001",
        "gt": "paper/gt/378.gt.json",
        "difficulty": "hard",
    },
    "383": {
        "version_root": "projects/383/building_unknown/20260524_121733_258903/v001",
        "gt": "paper/gt/383.gt.json",
        "difficulty": "medium",
    },
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.as_posix()


def copy_original_images(version_root: Path, project_dir: Path) -> list[dict[str, str]]:
    src_root = version_root / "blueprints/original"
    copied: list[dict[str, str]] = []
    if not src_root.exists():
        return copied
    for src in sorted(p for p in src_root.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES):
        rel = src.relative_to(src_root)
        dst = project_dir / "images/original" / rel
        copied.append({"source": str(src), "file": copy_file(src, dst)})
    return copied


def sheet_name_from_stage15_path(path: Path) -> str:
    parts = path.parts
    if "stage1_5" not in parts:
        return "unknown_sheet"
    idx = parts.index("stage1_5")
    return parts[idx + 1] if idx + 1 < len(parts) else "unknown_sheet"


def copy_cut_assets(version_root: Path, project_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    stage15 = version_root / "work/stage1_5"
    tiles: list[dict[str, str]] = []
    overlays: list[dict[str, str]] = []
    metadata: list[dict[str, str]] = []
    if not stage15.exists():
        return tiles, overlays, metadata

    for src in sorted(stage15.rglob("*紧凑折叠切片.png")):
        if "调试" in src.name:
            continue
        sheet = sheet_name_from_stage15_path(src)
        dst = project_dir / "images/cut/folded_tiles" / sheet / src.name
        tiles.append({"sheet": sheet, "source": str(src), "file": copy_file(src, dst)})

    for src in sorted(stage15.rglob("核心图块计划叠图_v4E*.png")):
        sheet = sheet_name_from_stage15_path(src)
        dst = project_dir / "images/cut/core_overlays" / sheet / src.name
        overlays.append({"sheet": sheet, "source": str(src), "file": copy_file(src, dst)})

    metadata_names = {
        "axis_context.json",
        "tile_plan_v4E.json",
        "tile_plan_v4E_compact_folded_band.json",
    }
    for src in sorted(stage15.rglob("*.json")):
        if src.name not in metadata_names and not src.name.endswith("_v4E_no_spacer_summary.json"):
            continue
        sheet = sheet_name_from_stage15_path(src)
        dst = project_dir / "cut_metadata" / sheet / src.name
        metadata.append({"sheet": sheet, "source": str(src), "file": copy_file(src, dst)})

    return tiles, overlays, metadata


def blueprint_map(sem: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {bp.get("blueprint_id"): bp for bp in sem.get("blueprints") or [] if bp.get("blueprint_id")}


def source_image_for_floor(floor: dict[str, Any], bps: dict[str, dict[str, Any]]) -> str | None:
    bp_id = floor.get("source_blueprint_id") or (floor.get("primary_structure") or {}).get("blueprint_id")
    bp = bps.get(bp_id) or {}
    source = bp.get("source_path")
    if source and Path(str(source)).suffix.lower() in IMAGE_SUFFIXES:
        return str(source)
    return None


def floor_asset_rows(sem: dict[str, Any], tiles: list[dict[str, str]]) -> list[dict[str, Any]]:
    bps = blueprint_map(sem)
    tiles_by_sheet: dict[str, list[str]] = {}
    for tile in tiles:
        tiles_by_sheet.setdefault(tile["sheet"], []).append(tile["file"])

    rows: list[dict[str, Any]] = []
    for floor in sem.get("floors") or []:
        ps = floor.get("primary_structure") or {}
        bp_id = floor.get("source_blueprint_id") or ps.get("blueprint_id")
        rows.append(
            {
                "floor_id": floor.get("floor_id"),
                "floor_name": floor.get("floor_name") or floor.get("drawing_name"),
                "elevation_m": floor.get("elevation_m"),
                "source_blueprint_id": bp_id,
                "source_image": source_image_for_floor(floor, bps),
                "cut_tile_count": len(tiles_by_sheet.get(str(bp_id), [])),
                "cut_tile_dir": f"images/cut/folded_tiles/{bp_id}" if bp_id in tiles_by_sheet else None,
            }
        )
    return rows


def output_schema(project_id: str) -> dict[str, Any]:
    return {
        "schema_version": "vlm.structural_reading.v1",
        "project_id": project_id,
        "floors": [
            {
                "floor_id": "string",
                "elevation_m": "number|null",
                "height_m": "number|null",
            }
        ],
        "axes": {
            "horizontal": [{"label": "string", "position_norm": "number|null"}],
            "vertical": [{"label": "string", "position_norm": "number|null"}],
        },
        "columns": [
            {
                "id": "string",
                "kz_type": "string|null",
                "axis_h": "string|null",
                "axis_v": "string|null",
                "section": {"w": "number|null", "h": "number|null"},
                "longitudinal_rebar": "string|null",
                "stirrup": "string|null",
                "floor": "string",
            }
        ],
        "beams": [
            {
                "id": "string",
                "floor": "string",
                "label": "string|null",
                "direction": "x|y|null",
                "grid_axis": "string|null",
                "start_node": "string|null",
                "end_node": "string|null",
                "support_axes": ["string"],
                "span_count": "integer|null",
                "section": {"w": "number|null", "h": "number|null"},
                "longitudinal_rebar": "string|null",
                "stirrup": "string|null",
            }
        ],
        "materials": {
            "concrete_grade_beam_slab": ["string"],
            "concrete_grade_wall_column": ["string"],
        },
    }


def prompt_text(
    project_id: str,
    rows: list[dict[str, Any]],
    original_count: int,
    tile_count: int,
    overlay_count: int,
    tile_sheet_counts: dict[str, int],
) -> str:
    floor_lines = "\n".join(
        f"- {row['floor_id']}: source_blueprint_id={row['source_blueprint_id']}, "
        f"source_image={row['source_image']}, cut_tile_dir={row['cut_tile_dir']}"
        for row in rows
    )
    tile_sheet_lines = "\n".join(
        f"- {sheet}: images/cut/folded_tiles/{sheet}/ ({count} 张)"
        for sheet, count in sorted(tile_sheet_counts.items())
    ) or "- 无"
    schema = json.dumps(output_schema(project_id), ensure_ascii=False, indent=2)
    return f"""你是结构施工图阅读专家。请只根据本项目文件夹中的图像读取主结构信息，并输出可和 GT 自动对比的 JSON。

项目 ID: {project_id}
输入图像:
- 原图目录: images/original/  （共 {original_count} 张）
- 切割图目录: images/cut/folded_tiles/  （共 {tile_count} 张紧凑折叠切片）
- 切片覆盖叠图: images/cut/core_overlays/  （共 {overlay_count} 张，可用于理解切片位置）

楼层和图纸映射:
{floor_lines}

切割图纸目录:
{tile_sheet_lines}

读取规则:
1. 只输出 JSON，不要 Markdown 代码围栏，不要解释文字。
2. 识别建筑轴网、框架柱 KZ、主梁 KL/WKL/KZL/JZL 等主梁实体；不要把普通次梁、楼板分布筋、说明文字当成主梁。
3. axis_h 使用数字轴标签，axis_v 使用字母轴标签；如果图纸方向与此不同，仍按图纸中的网格节点拆成 axis_h/axis_v。
4. position_norm 为同一方向轴线从最小像素到最大像素归一化到 [0, 1]；无法确定时填 null。
5. 梁 direction 用 "x" 或 "y"；support_axes 按梁跨越方向列出支承轴线，span_count 等于支承轴线间的跨数。
6. 截面单位为 mm；无法读出的值填 null，不要猜测。
7. id 可以自行稳定命名，但同一输出内必须唯一。
8. 不要读取 gt/ 目录；gt/ 只用于实验后评测。

必须严格输出以下 JSON 结构，字段名不得更改:
{schema}
"""


def write_readme(out_dir: Path, manifest: dict[str, Any]) -> None:
    projects = ", ".join(manifest["projects"].keys())
    text = f"""# VLM Input Pack N=6

Generated at: {manifest['generated_at']}

Projects: {projects}

Each project directory contains:
- `prompt.md`: prompt to send to a VLM with the project images.
- `input_manifest.json`: copied file list and floor-to-image mapping.
- `images/original/`: original blueprint images.
- `images/cut/folded_tiles/`: Stage1.5 no-spacer folded-band tile images.
- `images/cut/core_overlays/`: tile coverage overlay images.
- `cut_metadata/`: tile plans and axis context files.
- `gt/`: GT copy for post-hoc comparison only. Do not include it in the VLM context.

The package deliberately excludes Stage2 inspect-region screenshots because many filenames contain target beam/column labels and would leak StructAgent's later decisions into the VLM baseline.
"""
    write_text(out_dir / "README.md", text)


def prepare_project(project_id: str, sample: dict[str, str], out_dir: Path) -> dict[str, Any]:
    version_root = Path(sample["version_root"])
    sem = read_json(version_root / "outputs/final/project_semantic.json")
    project_dir = out_dir / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True)

    originals = copy_original_images(version_root, project_dir)
    tiles, overlays, cut_metadata = copy_cut_assets(version_root, project_dir)
    gt_src = Path(sample["gt"])
    gt_dst = project_dir / "gt" / f"{project_id}.gt.json"
    copy_file(gt_src, gt_dst)

    rows = floor_asset_rows(sem, tiles)
    tile_sheet_counts = dict(Counter(tile["sheet"] for tile in tiles))
    prompt = prompt_text(project_id, rows, len(originals), len(tiles), len(overlays), tile_sheet_counts)
    write_text(project_dir / "prompt.md", prompt)
    write_json(project_dir / "expected_output_schema.json", output_schema(project_id))

    manifest = {
        "project_id": project_id,
        "difficulty": sample["difficulty"],
        "version_root": str(version_root),
        "semantic_source": str(version_root / "outputs/final/project_semantic.json"),
        "gt_file": str(gt_dst),
        "prompt_file": str(project_dir / "prompt.md"),
        "floors": rows,
        "original_images": originals,
        "folded_tiles": tiles,
        "folded_tile_sheets": tile_sheet_counts,
        "core_overlays": overlays,
        "cut_metadata": cut_metadata,
        "counts": {
            "original_images": len(originals),
            "folded_tiles": len(tiles),
            "core_overlays": len(overlays),
            "cut_metadata": len(cut_metadata),
        },
    }
    write_json(project_dir / "input_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="paper/eval/vlm_inputs_N6_20260525")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    projects: dict[str, Any] = {}
    for project_id, sample in SAMPLES.items():
        projects[project_id] = prepare_project(project_id, sample, out_dir)

    manifest = {
        "schema_version": "structagent.vlm_input_pack.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "out_dir": str(out_dir),
        "projects": projects,
    }
    write_json(out_dir / "manifest.json", manifest)
    write_readme(out_dir, manifest)

    print(f"wrote {out_dir}")
    for project_id, project in projects.items():
        counts = project["counts"]
        print(
            f"  {project_id}: originals={counts['original_images']} "
            f"tiles={counts['folded_tiles']} overlays={counts['core_overlays']} "
            f"metadata={counts['cut_metadata']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
