#!/usr/bin/env python
"""把一个 FiftyOne 数据集整体并进另一个（按 filepath 去重）。

用法:
    python scripts/merge_datasets.py <source> <target> [skip|overwrite]

工作流：新采集的一批 → 先 import 成独立 staging 数据集 → 在它上面跑 predict/复核/标注
（只处理新图，不重复跑旧数据）→ 处理到位后用本脚本把它并进主数据集。

把 source 的样本及其所有字段（predictions 标注、tags、site/date/... 结构化字段）按
filepath 合并进 target，target 就地变大；source 不动（要删自己手动删）。
  - 新批次 filepath 与 target 不重叠 → 纯新增。
  - 万一重叠：skip（默认）保留 target 已有不动；overwrite 用 source 的值重写（tags 合并）。
想保留原始两个、另存合并体：先在 fif 里 d=fo.load_dataset(main); d.clone("新名") 再并进克隆体。
"""
import sys
import fiftyone as fo


def main(source, target, mode="skip"):
    names = fo.list_datasets()
    for n in (source, target):
        if n not in names:
            sys.exit(f"[err] 数据集不存在：{n}")
    if source == target:
        sys.exit("[err] source 与 target 不能是同一个数据集")

    src = fo.load_dataset(source)
    dst = fo.load_dataset(target)
    before = len(dst)
    new_fields = sorted(set(src.get_field_schema()) - set(dst.get_field_schema()))

    dst.merge_samples(src, key_field="filepath", insert_new=True,
                      skip_existing=(mode == "skip"),
                      overwrite=(mode == "overwrite"))

    added = len(dst) - before
    overlap = len(src) - added
    act = "跳过" if mode == "skip" else "覆盖"
    print(f"[{mode}] {source}({len(src)}) → {target}: 原有 {before} → 现 {len(dst)} "
          f"（新增 {added}，{act}重叠 {overlap}）")
    if new_fields:
        print(f"     并入了 target 原来没有的字段: {new_fields}")
    print(f"     复核: conda run -n fif fiftyone app launch")
    print(f"     staging「{source}」未删，确认无误后自己删：")
    print(f"       conda run -n fif python -c \"import fiftyone as fo; fo.delete_dataset('{source}')\"")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not (2 <= len(args) <= 3):
        sys.exit(__doc__)
    mode = args[2] if len(args) == 3 else "skip"
    if mode not in ("skip", "overwrite"):
        sys.exit(f"[err] 模式只能是 skip/overwrite，收到：{mode}")
    main(args[0], args[1], mode)
