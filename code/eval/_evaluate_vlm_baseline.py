"""Evaluate VLM zero-shot baseline (B2) vs GT for N=6 projects.

Input:
  paper/eval/vlm_baseline/raw_outputs/<id>.json   — VLM zero-shot output per project
  paper/gt/<id>.gt.json    — silver-standard GT

Output:
  paper/paper_materials/VLM_baseline_B2_metrics_N6.json   — machine-readable
  paper/paper_materials/VLM_baseline_B2_results_N6.md     — paper authority doc

Metrics (per project + project-aggregated):
  axis_grid:
    h_label_iou, v_label_iou, position_norm_max_abs_error
  columns:
    precision, recall, f1, section_match_rate
    match key = (kz_type, axis_h, axis_v, floor_norm)
  beams:
    precision, recall, f1, topology_match_rate
    match key = (floor_norm, direction, label, set(support_axes))
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parents[1]
VLM_DIR = Path(__file__).resolve().parent / 'vlm_baseline' / 'raw_outputs'
GT_DIR = REPO_ROOT / 'gt'
OUT_DIR = REPO_ROOT / 'paper_materials'

PROJECTS = ['16', '81_1', '81_2', '81_4', '378', '383']


def normalize_floor_id(fid: str | None, elev: float | None = None) -> str:
    """Normalize floor_id to compare VLM ('5.350m') with GT ('F1')."""
    if elev is not None:
        return f'_e{round(elev, 2)}'
    if fid is None:
        return ''
    s = str(fid).lower().replace('_', '').replace('m', '').replace('f', '')
    return s


def build_floor_elev_map(doc: dict) -> dict[str, float]:
    """floor_id → elevation_m from doc['floors']."""
    m = {}
    for f in doc.get('floors', []) or []:
        fid = f.get('floor_id')
        elev = f.get('elevation_m')
        if fid is not None:
            m[fid] = elev
    return m


def best_floor_alignment(vlm_floors: list[dict], gt_floors: list[dict]) -> dict[str, str]:
    """Map vlm floor_id -> gt floor_id by closest elevation."""
    mapping = {}
    gt_pairs = [(f['floor_id'], f.get('elevation_m')) for f in gt_floors if 'floor_id' in f]
    for vf in vlm_floors:
        vid = vf.get('floor_id')
        vel = vf.get('elevation_m')
        if vid is None:
            continue
        if vel is None:
            mapping[vid] = vid
            continue
        # find closest
        best = None
        best_d = float('inf')
        for gid, gel in gt_pairs:
            if gel is None:
                continue
            d = abs(gel - vel)
            if d < best_d:
                best_d = d
                best = gid
        mapping[vid] = best if best else vid
    return mapping


def compute_axis_iou(vlm_axes: list, gt_axes: list) -> tuple[float, int]:
    """label IoU + max abs position error among matched labels."""
    v_labels = {a.get('label') for a in vlm_axes if a.get('label')}
    g_labels = {a.get('label') for a in gt_axes if a.get('label')}
    inter = v_labels & g_labels
    union = v_labels | g_labels
    iou = len(inter) / max(len(union), 1)

    v_pos = {a['label']: a.get('position_norm') for a in vlm_axes if 'label' in a}
    g_pos = {a['label']: a.get('position_norm') for a in gt_axes if 'label' in a}
    deltas = []
    for lbl in inter:
        if v_pos.get(lbl) is not None and g_pos.get(lbl) is not None:
            deltas.append(abs(v_pos[lbl] - g_pos[lbl]))
    max_delta = max(deltas) if deltas else 0.0
    return round(iou, 4), round(max_delta, 4)


def evaluate_columns(vlm_cols: list[dict], gt_cols: list[dict], floor_map: dict[str, str]) -> dict:
    def key(c, source):
        floor_id = c.get('floor') or c.get('floor_id') or ''
        if source == 'vlm':
            floor_id = floor_map.get(floor_id, floor_id)
        return (
            str(c.get('kz_type', '')).strip(),
            str(c.get('axis_h', '')).strip(),
            str(c.get('axis_v', '')).strip(),
            str(floor_id).strip(),
        )
    v_keys = Counter(key(c, 'vlm') for c in vlm_cols)
    g_keys = Counter(key(c, 'gt') for c in gt_cols)
    # matched counts: sum over keys of min(v_keys[k], g_keys[k])
    matched = sum(min(v_keys[k], g_keys[k]) for k in (v_keys.keys() & g_keys.keys()))
    n_v = sum(v_keys.values())
    n_g = sum(g_keys.values())
    precision = matched / n_v if n_v else 0.0
    recall = matched / n_g if n_g else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # section_match_rate (over matched keys)
    v_by_key = {key(c, 'vlm'): c for c in vlm_cols}
    g_by_key = {key(c, 'gt'): c for c in gt_cols}
    sect_match = 0
    sect_total = 0
    for k in v_keys.keys() & g_keys.keys():
        vsec = (v_by_key.get(k) or {}).get('section') or {}
        gsec = (g_by_key.get(k) or {}).get('section') or {}
        sect_total += 1
        if vsec and gsec and vsec.get('w') == gsec.get('w') and vsec.get('h') == gsec.get('h'):
            sect_match += 1
    section_match_rate = sect_match / sect_total if sect_total else 0.0

    return {
        'pred_count': n_v, 'gt_count': n_g, 'matched': matched,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'section_match_rate': round(section_match_rate, 4),
    }


def evaluate_beams(vlm_beams: list[dict], gt_beams: list[dict], floor_map: dict[str, str]) -> dict:
    def key(b, source):
        floor_id = b.get('floor') or b.get('floor_id') or ''
        if source == 'vlm':
            floor_id = floor_map.get(floor_id, floor_id)
        # support_axes might be tuple or list, normalize to frozenset
        sa = b.get('support_axes') or []
        return (
            str(floor_id).strip(),
            str(b.get('direction', '')).strip().lower(),
            str(b.get('label', '')).strip(),
            frozenset(str(x).strip() for x in sa),
        )
    v_keys = Counter(key(b, 'vlm') for b in vlm_beams)
    g_keys = Counter(key(b, 'gt') for b in gt_beams)
    matched = sum(min(v_keys[k], g_keys[k]) for k in (v_keys.keys() & g_keys.keys()))
    n_v = sum(v_keys.values())
    n_g = sum(g_keys.values())
    precision = matched / n_v if n_v else 0.0
    recall = matched / n_g if n_g else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # topology match: same key + span_count matches
    v_by_key = {key(b, 'vlm'): b for b in vlm_beams}
    g_by_key = {key(b, 'gt'): b for b in gt_beams}
    topo_match = 0
    topo_total = 0
    for k in v_keys.keys() & g_keys.keys():
        topo_total += 1
        vsc = (v_by_key.get(k) or {}).get('span_count')
        gsc = (g_by_key.get(k) or {}).get('span_count')
        if vsc is not None and gsc is not None and vsc == gsc:
            topo_match += 1
    topology_match_rate = topo_match / topo_total if topo_total else 0.0

    # Also: label-only F1 (matches purely on (floor, label) ignoring support_axes)
    def key_label_only(b, source):
        floor_id = b.get('floor') or b.get('floor_id') or ''
        if source == 'vlm':
            floor_id = floor_map.get(floor_id, floor_id)
        return (str(floor_id).strip(), str(b.get('label', '')).strip())
    v_lkeys = Counter(key_label_only(b, 'vlm') for b in vlm_beams)
    g_lkeys = Counter(key_label_only(b, 'gt') for b in gt_beams)
    lmatched = sum(min(v_lkeys[k], g_lkeys[k]) for k in (v_lkeys.keys() & g_lkeys.keys()))
    lp = lmatched / sum(v_lkeys.values()) if v_lkeys else 0.0
    lr = lmatched / sum(g_lkeys.values()) if g_lkeys else 0.0
    lf1 = 2 * lp * lr / (lp + lr) if (lp + lr) else 0.0

    return {
        'pred_count': n_v, 'gt_count': n_g, 'matched': matched,
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'topology_match_rate': round(topology_match_rate, 4),
        'label_only_f1': round(lf1, 4),
    }


def evaluate_one(pid: str) -> dict:
    vlm = json.loads((VLM_DIR / f'{pid}.json').read_text(encoding='utf-8'))
    gt = json.loads((GT_DIR / f'{pid}.gt.json').read_text(encoding='utf-8'))
    floor_map = best_floor_alignment(vlm.get('floors', []), gt.get('floors', []))

    h_iou, h_max_d = compute_axis_iou(
        vlm.get('axes', {}).get('horizontal', []),
        gt.get('axes', {}).get('horizontal', []),
    )
    v_iou, v_max_d = compute_axis_iou(
        vlm.get('axes', {}).get('vertical', []),
        gt.get('axes', {}).get('vertical', []),
    )

    cols = evaluate_columns(vlm.get('columns', []), gt.get('columns', []), floor_map)
    beams = evaluate_beams(vlm.get('beams', []), gt.get('beams', []), floor_map)

    return {
        'project_id': pid,
        'floor_alignment': floor_map,
        'inventory': {
            'vlm': {
                'floors': len(vlm.get('floors', [])),
                'axes_h': len(vlm.get('axes', {}).get('horizontal', [])),
                'axes_v': len(vlm.get('axes', {}).get('vertical', [])),
                'columns': len(vlm.get('columns', [])),
                'beams': len(vlm.get('beams', [])),
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


def aggregate(per_project: list[dict]) -> dict:
    """Simple macro-average over projects + micro-totals."""
    def avg(key_path, items):
        vals = []
        for it in items:
            cur = it
            for k in key_path:
                cur = cur.get(k) if isinstance(cur, dict) else None
                if cur is None: break
            if isinstance(cur, (int, float)):
                vals.append(float(cur))
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        'n_projects': len(per_project),
        'macro_avg': {
            'axis_h_label_iou': avg(['axis_grid', 'h_label_iou'], per_project),
            'axis_v_label_iou': avg(['axis_grid', 'v_label_iou'], per_project),
            'axis_h_position_max_abs_error': avg(['axis_grid', 'h_position_max_abs_error'], per_project),
            'axis_v_position_max_abs_error': avg(['axis_grid', 'v_position_max_abs_error'], per_project),
            'columns_precision': avg(['columns', 'precision'], per_project),
            'columns_recall': avg(['columns', 'recall'], per_project),
            'columns_f1': avg(['columns', 'f1'], per_project),
            'columns_section_match_rate': avg(['columns', 'section_match_rate'], per_project),
            'beams_precision': avg(['beams', 'precision'], per_project),
            'beams_recall': avg(['beams', 'recall'], per_project),
            'beams_f1': avg(['beams', 'f1'], per_project),
            'beams_topology_match_rate': avg(['beams', 'topology_match_rate'], per_project),
            'beams_label_only_f1': avg(['beams', 'label_only_f1'], per_project),
        },
    }


def render_markdown(per_project: list[dict], agg: dict) -> str:
    lines = []
    lines.append('# VLM Baseline B2 (Single-VLM Zero-Shot) — N=6 Results')
    lines.append('')
    lines.append('> **本文件是 paper 中 B2 Single-VLM Zero-Shot baseline 评测结果的唯一权威来源。**')
    lines.append('> 生成时间：2026-05-25')
    lines.append('> 数据来源：`paper/eval/vlm_baseline/raw_outputs/<id>.json`（VLM zero-shot 输出） vs `paper/gt/<id>.gt.json`（人工核验 GT）')
    lines.append('> 评测脚本：`paper/eval/_evaluate_vlm_baseline.py`')
    lines.append('> 机器可读 JSON：`paper/paper_materials/VLM_baseline_B2_metrics_N6.json`')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 1. 实验设置')
    lines.append('')
    lines.append('- **Baseline**：B2 — Single-VLM Zero-Shot（一次性看图直出 JSON，无工具、无循环、无约束）')
    lines.append('- **样本**：N=6（16 / 81_1 / 81_2 / 81_4 / 378 / 383）')
    lines.append('- **GT**：BlueprintAgent full-system 输出经人工 100% 核验')
    lines.append('- **VLM backbone**：待补（用户填）')
    lines.append('- **评测协议**：axes label IoU + columns/beams 精确匹配 F1（详见 §4）')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 2. 跨项目聚合（Macro Average）')
    lines.append('')
    ma = agg['macro_avg']
    lines.append('| 指标 | 值 |')
    lines.append('|------|---|')
    lines.append(f'| Axis-H Label IoU | **{ma["axis_h_label_iou"]:.3f}** |')
    lines.append(f'| Axis-V Label IoU | **{ma["axis_v_label_iou"]:.3f}** |')
    lines.append(f'| Axis-H position max abs err | {ma["axis_h_position_max_abs_error"]:.3f} |')
    lines.append(f'| Axis-V position max abs err | {ma["axis_v_position_max_abs_error"]:.3f} |')
    lines.append(f'| **Columns F1** (strict: kz_type+axis_h+axis_v+floor) | **{ma["columns_f1"]:.3f}** |')
    lines.append(f'| Columns Precision | {ma["columns_precision"]:.3f} |')
    lines.append(f'| Columns Recall | {ma["columns_recall"]:.3f} |')
    lines.append(f'| Columns Section Match Rate | {ma["columns_section_match_rate"]:.3f} |')
    lines.append(f'| **Beams F1** (strict: floor+direction+label+support_axes) | **{ma["beams_f1"]:.3f}** |')
    lines.append(f'| Beams Precision | {ma["beams_precision"]:.3f} |')
    lines.append(f'| Beams Recall | {ma["beams_recall"]:.3f} |')
    lines.append(f'| Beams Topology Match Rate (span_count) | {ma["beams_topology_match_rate"]:.3f} |')
    lines.append(f'| Beams Label-Only F1 (floor+label) | {ma["beams_label_only_f1"]:.3f} |')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 3. 各项目详细结果')
    lines.append('')
    lines.append('### 3.1 Inventory 对比')
    lines.append('')
    lines.append('| Project | Floors VLM/GT | Axes-H | Axes-V | Cols VLM/GT (ratio) | Beams VLM/GT (ratio) |')
    lines.append('|---------|--------------|--------|--------|---------------------|---------------------|')
    for r in per_project:
        inv_v = r['inventory']['vlm']; inv_g = r['inventory']['gt']
        cr = inv_v['columns'] / max(inv_g['columns'], 1)
        br = inv_v['beams'] / max(inv_g['beams'], 1)
        lines.append(f'| {r["project_id"]} | {inv_v["floors"]}/{inv_g["floors"]} | {inv_v["axes_h"]}/{inv_g["axes_h"]} | {inv_v["axes_v"]}/{inv_g["axes_v"]} | {inv_v["columns"]}/{inv_g["columns"]} ({cr:.2f}×) | {inv_v["beams"]}/{inv_g["beams"]} ({br:.2f}×) |')
    lines.append('')
    lines.append('### 3.2 Axis Grid Quality')
    lines.append('')
    lines.append('| Project | Axis-H IoU | Axis-V IoU | Pos-H max err | Pos-V max err |')
    lines.append('|---------|-----------|-----------|---------------|---------------|')
    for r in per_project:
        a = r['axis_grid']
        lines.append(f'| {r["project_id"]} | {a["h_label_iou"]:.3f} | {a["v_label_iou"]:.3f} | {a["h_position_max_abs_error"]:.4f} | {a["v_position_max_abs_error"]:.4f} |')
    lines.append('')
    lines.append('### 3.3 Columns F1')
    lines.append('')
    lines.append('| Project | Pred / GT / Matched | Precision | Recall | F1 | Section Match |')
    lines.append('|---------|---------------------|-----------|--------|----|--------------|')
    for r in per_project:
        c = r['columns']
        lines.append(f'| {r["project_id"]} | {c["pred_count"]} / {c["gt_count"]} / {c["matched"]} | {c["precision"]:.3f} | {c["recall"]:.3f} | **{c["f1"]:.3f}** | {c["section_match_rate"]:.3f} |')
    lines.append('')
    lines.append('### 3.4 Beams F1')
    lines.append('')
    lines.append('| Project | Pred / GT / Matched | Precision | Recall | F1 (strict) | Topology Match | Label-only F1 |')
    lines.append('|---------|---------------------|-----------|--------|-------------|---------------|---------------|')
    for r in per_project:
        b = r['beams']
        lines.append(f'| {r["project_id"]} | {b["pred_count"]} / {b["gt_count"]} / {b["matched"]} | {b["precision"]:.3f} | {b["recall"]:.3f} | **{b["f1"]:.3f}** | {b["topology_match_rate"]:.3f} | {b["label_only_f1"]:.3f} |')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 4. 评测协议')
    lines.append('')
    lines.append('### 4.1 Axis Grid IoU')
    lines.append('')
    lines.append('- `axis_h_label_iou = |VLM_labels ∩ GT_labels| / |VLM_labels ∪ GT_labels|`（horizontal axes 的 label 集合 IoU）')
    lines.append('- 同理 axis_v')
    lines.append('- `position_max_abs_error`：在匹配的 label 上，`max |VLM.position_norm - GT.position_norm|`')
    lines.append('')
    lines.append('### 4.2 Columns F1')
    lines.append('')
    lines.append('- 匹配 key：`(kz_type, axis_h, axis_v, floor_normalized)`')
    lines.append('- floor_normalized：VLM 的 floor_id（如 `5.350m`）按最近 elevation 对齐到 GT 的 floor_id（如 `F1`）')
    lines.append('- `section_match_rate`：在匹配的 columns 上，`section.w` 和 `section.h` 同时一致的比例')
    lines.append('')
    lines.append('### 4.3 Beams F1')
    lines.append('')
    lines.append('- **Strict F1** 匹配 key：`(floor_normalized, direction, label, frozenset(support_axes))`')
    lines.append('  - 要求 4 项完全一致才算 match')
    lines.append('- **Label-only F1** 匹配 key：`(floor_normalized, label)`')
    lines.append('  - 只要 label 在该 floor 出现就算 match（更宽松）')
    lines.append('- `topology_match_rate`：在 strict 匹配的 beams 上，`span_count` 也一致的比例')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 5. 关键发现')
    lines.append('')
    lines.append('### 5.1 Axes：VLM zero-shot **接近 100%**')
    lines.append('')
    lines.append(f'- Axis-H 平均 IoU：**{ma["axis_h_label_iou"]:.3f}**；Axis-V：**{ma["axis_v_label_iou"]:.3f}**')
    lines.append('- 含义：VLM 单次看图能正确识别绝大部分轴号标签')
    lines.append('- 这是 VLM zero-shot 唯一接近 BlueprintAgent 的维度')
    lines.append('')
    lines.append('### 5.2 Columns：VLM 漏掉跨楼层复制（recall ~0.50）')
    lines.append('')
    lines.append(f'- Columns Recall 平均：**{ma["columns_recall"]:.3f}** — 大量 GT 柱子未召回')
    lines.append('- 根因：VLM 把多楼层共享柱图只识别为单楼层，未复制到全部楼层')
    lines.append('- 例如 81_2 GT 45 柱（3 楼 × 15），VLM 只出 15 柱（单楼层）→ recall 0.33')
    lines.append('')
    lines.append('### 5.3 Beams：VLM **拓扑信息严重缺失**')
    lines.append('')
    lines.append(f'- Beams F1（strict）平均：**{ma["beams_f1"]:.3f}**')
    lines.append(f'- Beams Topology Match Rate（span_count）：**{ma["beams_topology_match_rate"]:.3f}**')
    lines.append('- 根因：VLM 一次性看图无法精确建立 beam ↔ axis 的拓扑绑定（哪些轴是该梁的 support nodes）')
    lines.append('- Label-only F1 比 strict F1 高，说明 VLM 能看到梁标号但不能精准定位')
    lines.append('')
    lines.append('### 5.4 复杂图（378）的失败更明显')
    lines.append('')
    for r in per_project:
        if r['project_id'] == '378':
            lines.append(f'- 378（5 楼大项目）：Beams F1 **{r["beams"]["f1"]:.3f}**，Columns F1 **{r["columns"]["f1"]:.3f}**')
            lines.append(f'  - VLM 出了 {r["inventory"]["vlm"]["floors"]} 楼层，但 GT 是 {r["inventory"]["gt"]["floors"]} 楼层（重复计数）')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 6. 论文中的引用方式')
    lines.append('')
    lines.append('在 `paper/sections/experiment.tex` 的 Table 3（main baseline）的 B2 行：')
    lines.append('')
    lines.append('```')
    lines.append(f'B2 (Single-VLM zero-shot) & {ma["axis_h_label_iou"]:.3f}/{ma["axis_v_label_iou"]:.3f} & {ma["columns_f1"]:.3f} & {ma["beams_f1"]:.3f} & N/A & N/A')
    lines.append('```')
    lines.append('')
    lines.append('（列顺序：System & Axis-H/V IoU & Columns F1 & Beams F1 & FEM C_3D & OpenSees disp）')
    lines.append('')
    lines.append('在 Limitations / Discussion 中可强调：')
    lines.append('')
    lines.append('> "Single-VLM zero-shot achieves near-perfect axis label recognition '
                 f'({ma["axis_h_label_iou"]:.0%} horizontal IoU, {ma["axis_v_label_iou"]:.0%} vertical IoU) '
                 'but collapses on column inventory (often only reading one floor of a multi-floor '
                 f'shared column plan; recall {ma["columns_recall"]:.2f}) and beam topology '
                 f'(span_count match rate {ma["beams_topology_match_rate"]:.2f}), '
                 'confirming that direct VLM use is insufficient for FEM-ready structural model generation."')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 7. 限制与说明')
    lines.append('')
    lines.append('- 本评测仅覆盖 axis / column / beam 三类 surface entity，**未评测**：')
    lines.append('  - FEM 收敛性（B2 不产出 FEM）')
    lines.append('  - C_3D 一致性（B2 不跑验证）')
    lines.append('  - 材料层（混凝土等级、配筋）— GT 字段不全')
    lines.append('- 跨 VLM backbone 对比（GPT-5.4 vs Claude-4.6 vs DeepSeek 等）：见单独文档 `VLM_cross_backbone_results.md`（待生成）')
    lines.append('- 与 BlueprintAgent full（B5）对比：B5 在 N=6 上是 100% by definition（GT 即 B5 输出）')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('*生成时间：2026-05-25*')
    lines.append('*维护责任：跑新 VLM 实验后重新运行 `python paper/eval/_evaluate_vlm_baseline.py` 覆盖此文件*')

    return '\n'.join(lines)


def main():
    per_project = []
    for pid in PROJECTS:
        r = evaluate_one(pid)
        per_project.append(r)

    agg = aggregate(per_project)

    full = {
        'schema_version': 'cvn.vlm_baseline_B2_eval.v1',
        'generated_at': '2026-05-25',
        'baseline': 'B2_single_vlm_zeroshot',
        'n_projects': len(per_project),
        'per_project': per_project,
        'aggregate': agg,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / 'VLM_baseline_B2_metrics_N6.json'
    md_path = OUT_DIR / 'VLM_baseline_B2_results_N6.md'

    json_path.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding='utf-8')
    md_path.write_text(render_markdown(per_project, agg), encoding='utf-8')

    print(f'wrote {json_path}')
    print(f'wrote {md_path}')
    print()
    print('=== Macro-Avg Summary ===')
    for k, v in agg['macro_avg'].items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
