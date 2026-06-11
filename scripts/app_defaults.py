#!/usr/bin/env python
"""设置数据集在 FiftyOne App 里【默认激活/显示】哪些字段（持久化到 app_config）。

用法:
    python scripts/app_defaults.py <dataset>                       # 用默认字段
    python scripts/app_defaults.py <dataset> site location focus time date filepath  # 指定字段

效果：打开 App 时这些字段默认被选中（侧栏对应分组自动展开），每张图悬停/查看即可
看到它们的值。注意：重新 import 数据集会重置 app_config —— import_dataset.py 末尾已自动
重设（见其 active_fields 选项），手动重设也可重跑本脚本。
"""
import sys
import fiftyone as fo
from fiftyone.core.odm.dataset import ActiveFields

# 列出所有想默认显示的字段；set_active_fields 只设【该数据集存在的】，不存在的自动跳过
# （所以 16MP 数据集只激活 focal_length、64MP 只激活 focal_length_64mp，不会报错）
DEFAULT = ["site", "location", "focus", "focal_length", "focal_length_64mp",
           "time", "date", "filepath"]


def set_active_fields(dataset, fields):
    """把 fields 里【存在的】设为 App 默认激活字段并展开其分组。返回实际设置的字段。"""
    schema = dataset.get_field_schema()
    fields = [f for f in fields if f in schema]
    if not fields:
        return []
    dataset.app_config.active_fields = ActiveFields(exclude=False, paths=fields)
    for g in dataset.app_config.sidebar_groups or []:    # 含这些字段的分组默认展开
        if any(p in fields for p in g.paths):
            g.expanded = True
    dataset.save()
    return fields


def main(name, fields):
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")
    d = fo.load_dataset(name)
    requested = fields or DEFAULT
    done = set_active_fields(d, requested)
    miss = [f for f in requested if f not in done]
    if miss:
        print(f"[warn] 跳过不存在的字段：{miss}")
    if not done:
        sys.exit("[err] 没有有效字段")
    print(f"[ok] {name} 默认激活字段：{done}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
