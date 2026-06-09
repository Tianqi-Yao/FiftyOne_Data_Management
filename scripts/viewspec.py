#!/usr/bin/env python
"""把命令行 token 解析成一个 FiftyOne view（predict / export / coverage 共用）。

token（按顺序 AND）：
    site=air1            字段等值（裸 token 如 `air1` 等价于 site=air1）
    focus=fixed          字段等值（纯数字转 int，如 year=2025 / focal_length=525）
    view=<saved_view名>  从一个已存的 saved view 出发
    label=<名>           范围标签（给输出文件/视图命名用，默认从过滤推断）
    limit=20             只取前 N 张（试跑用）

各脚本应先取走自己的参数（如 conf=、weights=），把剩下的 token 传进来。
"""
from fiftyone import ViewField as F


def build_view(dataset, tokens):
    """返回 (view, label)。"""
    view = dataset.view()
    label = None
    for tok in tokens:
        if tok.startswith("view="):
            view = dataset.load_saved_view(tok[5:])
            label = label or tok[5:]
        elif tok.startswith("label="):
            label = tok[6:]
        elif tok.startswith("limit="):
            view = view.limit(int(tok[6:]))
        else:
            k, v = tok.split("=", 1) if "=" in tok else ("site", tok)
            vv = int(v) if v.lstrip("-").isdigit() else v
            view = view.match(F(k) == vv)
            label = label or (v if k == "site" else f"{k}-{v}")
    return view, (label or "all")
