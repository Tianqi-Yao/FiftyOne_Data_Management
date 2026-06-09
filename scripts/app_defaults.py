#!/usr/bin/env python
"""设置数据集在 FiftyOne App 里【默认激活/显示】哪些字段（持久化到 app_config）。

用法:
    python scripts/app_defaults.py <dataset>                       # 用默认字段
    python scripts/app_defaults.py <dataset> site location focal_length focus time date filepath  # 指定字段

效果：打开 App 时这些字段默认被选中（侧栏对应分组自动展开），每张图悬停/查看即可
看到它们的值。注意：重新 import 数据集会重置 app_config —— 重跑本脚本即可恢复。
"""
import sys
import fiftyone as fo
from fiftyone.core.odm.dataset import ActiveFields

DEFAULT = ["site", "location", "focus", "date", "time", "focal_length"]


def main(name, fields):
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")
    d = fo.load_dataset(name)
    schema = d.get_field_schema()

    fields = fields or DEFAULT
    miss = [f for f in fields if f not in schema]
    if miss:
        print(f"[warn] 跳过不存在的字段：{miss}")
    fields = [f for f in fields if f in schema]
    if not fields:
        sys.exit("[err] 没有有效字段")

    d.app_config.active_fields = ActiveFields(exclude=False, paths=fields)
    for g in d.app_config.sidebar_groups or []:    # 含这些字段的分组默认展开
        if any(p in fields for p in g.paths):
            g.expanded = True
    d.save()
    print(f"[ok] {name} 默认激活字段：{fields}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
