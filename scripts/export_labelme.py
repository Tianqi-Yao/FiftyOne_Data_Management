#!/usr/bin/env python
"""把 FiftyOne 里的预测（label 字段）导出成 X-AnyLabeling 用的 LabelMe JSON。

用法:
    python scripts/export_labelme.py <dataset> [过滤token...] [label_field=predictions] [outdir=<目录>]
例:
    python scripts/export_labelme.py swd_2024_eachfarm_16mp site=air1 limit=50 outdir=exports/labelme_air1
    python scripts/export_labelme.py swd_2024_eachfarm_16mp view=myView          # 不给 outdir = 写在图片旁

- 每张图一个 LabelMe `.json`：分割→shape_type=polygon，检测框→rectangle，label/points 都填好。
- 不给 outdir：写在**图片旁**（同名 .json，imagePath=文件名）——X-AnyLabeling 打开图片目录直接识别。
  给 outdir：集中写到该目录（imagePath=图片绝对路径），不污染原始数据目录。
- 过滤 token 见 viewspec.py。mask→多边形用 FiftyOne 的 to_polyline()。
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiftyone as fo
from PIL import Image
from viewspec import build_view


def image_size(sample):
    md = sample.metadata
    if md is not None and md.width and md.height:
        return md.width, md.height
    w, h = Image.open(sample.filepath).size
    return w, h


def shapes_for(sample, label_field, W, H):
    dets = sample[label_field]
    if dets is None:
        return []
    polys = dets.to_polylines(tolerance=2)          # 与 detections 对齐
    shapes = []
    for det, poly in zip(dets.detections, polys.polylines):
        desc = {} if det.confidence is None else {"confidence": round(det.confidence, 4)}
        if det.mask is not None:                    # 分割 → 多边形（可能多个环）
            for ring in poly.points:
                if len(ring) < 3:
                    continue
                pts = [[round(x * W, 2), round(y * H, 2)] for x, y in ring]
                shapes.append(dict(label=det.label, points=pts, group_id=None,
                                   shape_type="polygon", flags={}, description=desc))
        else:                                       # 检测 → 矩形（两角点）
            x, y, w, h = det.bounding_box
            pts = [[round(x * W, 2), round(y * H, 2)],
                   [round((x + w) * W, 2), round((y + h) * H, 2)]]
            shapes.append(dict(label=det.label, points=pts, group_id=None,
                               shape_type="rectangle", flags={}, description=desc))
    return shapes


def main(args):
    name = args[0]
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")
    label_field = "predictions"
    outdir = None
    view_tokens = []
    for tok in args[1:]:
        if tok.startswith("label_field="):
            label_field = tok[len("label_field="):]
        elif tok.startswith("outdir="):
            outdir = tok[len("outdir="):]
        else:
            view_tokens.append(tok)

    dataset = fo.load_dataset(name)
    if label_field not in dataset.get_field_schema():
        sys.exit(f"[err] 字段 {label_field} 不存在，先跑 predict.py？")
    view, _ = build_view(dataset, view_tokens)
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    n_img = n_shape = 0
    for sample in view.iter_samples(progress=True):
        W, H = image_size(sample)
        shapes = shapes_for(sample, label_field, W, H)
        if outdir:
            out = os.path.join(outdir, os.path.splitext(os.path.basename(sample.filepath))[0] + ".json")
            image_path = sample.filepath                       # 绝对路径
        else:
            out = os.path.splitext(sample.filepath)[0] + ".json"
            image_path = os.path.basename(sample.filepath)     # 同目录文件名
        with open(out, "w") as f:
            json.dump({"version": "5.5.0", "flags": {}, "shapes": shapes,
                       "imagePath": image_path, "imageData": None,
                       "imageHeight": H, "imageWidth": W}, f, ensure_ascii=False, indent=2)
        n_img += 1
        n_shape += len(shapes)

    where = outdir if outdir else "（写在各图片旁）"
    print(f"[ok] 导出 {n_img} 个 LabelMe json，共 {n_shape} 个标注 → {where}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
