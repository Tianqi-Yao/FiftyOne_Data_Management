#!/usr/bin/env python
"""按 datasets/<name>.yaml 清单创建/更新一个 FiftyOne 数据集。

用法:
    python scripts/import_dataset.py datasets/swd_2026_elderfarm_64mp.yaml

清单是真相源 —— FiftyOne 数据库可删可重建，重跑本脚本即可。
图片原地引用（不复制），FiftyOne 只存 filepath + metadata。
"""
import sys
import yaml
import fiftyone as fo


def main(manifest_path):
    with open(manifest_path) as f:
        m = yaml.safe_load(f)

    name = m["name"]
    path = m["path"]
    tags = m.get("tags", [])

    # 已存在则覆盖重建（清单是真相源）
    if name in fo.list_datasets():
        fo.delete_dataset(name)

    # 原地引用：递归收集 path 下的图片，不复制文件
    dataset = fo.Dataset.from_dir(
        dataset_dir=path,
        dataset_type=fo.types.ImageDirectory,
        name=name,
    )
    dataset.persistent = True
    dataset.tags = list(tags)

    # 把 year/location/device 存成样本字段，方便筛选
    for key in ("year", "location", "device"):
        if key in m:
            dataset.set_values(key, [m[key]] * len(dataset))

    dataset.compute_metadata()
    print(f"[ok] {name}: {len(dataset)} samples  tags={tags}")
    print(f"     浏览: fiftyone app launch")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
