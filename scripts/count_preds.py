#!/usr/bin/env python
"""按某个置信度阈值，把每张图的预测框数写进一个字段（默认 n_pred）。

用法:
    python scripts/count_preds.py <dataset> [过滤token...] [conf=0.5] [label_field=predictions] [field=n_pred]
例:
    python scripts/count_preds.py swd_2024_eachfarm_16mp conf=0.5
    python scripts/count_preds.py swd_2024_eachfarm_16mp view=good conf=0.3 field=n_pred_03

为什么需要它：App 里拖 confidence 滑块只改"显示的框"和侧栏总数，**网格每张图上不会有随滑块
实时变的数字**；写进 field 的数又是静态的（预测时那个阈值）。本工具把"≥conf 的框数"按你给的
阈值算出来写进字段——可在网格显示/排序/再筛。换阈值就重跑（纯数据库聚合，秒级，不读图）。
想要单张图的实时计数：在 App 里**打开那张图**，侧栏会随滑块实时显示该图的框数。

跑完建议把字段设为 App 默认显示：
    python scripts/app_defaults.py <dataset> <已有字段...> n_pred
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiftyone as fo
from fiftyone import ViewField as F
from viewspec import build_view


def main(args):
    name = args[0]
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")
    conf, label_field, field = 0.5, "predictions", "n_pred"
    view_tokens = []
    for tok in args[1:]:
        if tok.startswith("conf="):
            conf = float(tok[5:])
        elif tok.startswith("label_field="):
            label_field = tok[len("label_field="):]
        elif tok.startswith("field="):
            field = tok[len("field="):]
        else:
            view_tokens.append(tok)

    dataset = fo.load_dataset(name)
    if label_field not in dataset.get_field_schema():
        sys.exit(f"[err] 字段 {label_field} 不存在，先跑 predict.py？")
    view, _ = build_view(dataset, view_tokens)

    # 服务端聚合：每样本 = 置信度≥conf 的框数（无预测的样本记 0）
    dets = F(f"{label_field}.detections")
    expr = (dets != None).if_else(dets.filter(F("confidence") >= conf).length(), 0)
    if field not in dataset.get_field_schema():
        dataset.add_sample_field(field, fo.IntField)
    view.set_field(field, expr).save(field)
    dataset.create_index(field)   # 方便排序/筛选

    print(f"[ok] {name}: 已写字段 {field} = {label_field} 中 conf≥{conf} 的框数")
    print(f"     每图范围 {view.bounds(field)}；这批共 {view.sum(field)} 个框（{len(view)} 张）")
    print(f"     在 App 网格显示它：python scripts/app_defaults.py {name} <字段...> {field}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
