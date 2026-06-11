#!/usr/bin/env python
"""给【已存在】的数据集，从文件名补 date / time / focal_length 字段。

用法:
    python scripts/enrich_names.py swd_2024_eachfarm_16mp
    python scripts/enrich_names.py datasets/swd_2024_eachfarm_16mp.yaml

只用数据库里已有的 filepath，**不读图片文件**，134k 张几秒钟。
适合：已经 import 过一次（metadata/字段都在），只想补/重算文件名派生字段。
解析不出 date/time 的，打 tag qc:name_unparsed 并写 exports/<name>_unparsed_names.txt。

import_dataset.py 是“一次跑完”的全量脚本；本脚本是可单独重跑的“文件名解析”那一步。
两者共用同一个 parse_name，结果一致。
"""
import os
import sys
import yaml
import fiftyone as fo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_dataset import parse_name, write_report, REPO, load_patterns  # 复用


def resolve_name(arg):
    if arg.endswith((".yaml", ".yml")) and os.path.exists(arg):
        with open(arg) as f:
            return yaml.safe_load(f)["name"]
    return arg


def main(arg):
    name = resolve_name(arg)
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")
    dataset = fo.load_dataset(name)
    patterns = load_patterns()           # 规则来自 filename_patterns.yaml

    ids = dataset.values("id")
    paths = dataset.values("filepath")
    years = dataset.values("year") if "year" in dataset.get_field_schema() \
        else [None] * len(ids)

    infos = [parse_name(p, y, patterns) for p, y in zip(paths, years)]
    unparsed_ids = [ids[i] for i, info in enumerate(infos) if "time" not in info]

    # 字段无关：parse_name 返回啥就写啥（date/time/focal_length/focal_length_64mp…）
    # 某字段全 None 就跳过（如某数据集没焦距）——否则 set_values 无法推断类型报错
    for fname in sorted(set().union(*infos)) if infos else []:
        vals = [info.get(fname) for info in infos]
        if any(v is not None for v in vals):
            dataset.set_values(fname, vals)

    # 先清旧标记，保证可重复跑（已能解析的不该再背着旧 tag）
    stale = dataset.match_tags("qc:name_unparsed")
    if len(stale):
        stale.untag_samples("qc:name_unparsed")

    if unparsed_ids:
        view = dataset.select(unparsed_ids)
        view.tag_samples("qc:name_unparsed")
        write_report(name, "unparsed_names", view.values("filepath"),
                     "文件名无法解析 date/time，已标 qc:name_unparsed")
    else:
        stale = os.path.join(REPO, "exports", f"{name}_unparsed_names.txt")
        if os.path.exists(stale):
            os.remove(stale)   # 没有异常了，清掉旧报告

    ok = sum(1 for info in infos if "time" in info)
    print(f"[ok] {name}: {len(ids)} 张，{ok} 张拿到 date/time")
    schema = dataset.get_field_schema()
    for f in (sorted(set().union(*infos)) if infos else []):   # 报告实际写入的字段
        if f in schema:
            print(f"     {f}: {dataset.bounds(f)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
