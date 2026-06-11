#!/usr/bin/env python
"""批量改某字段的【内容/值】（App 能改字段名，但改不了值，得用代码）。

不用命令行参数——改下面的超参数后直接 `conda run -n fif python scripts/remap_field.py`。
默认 DRY_RUN=True 先预览会改多少；确认无误再把 DRY_RUN 改 False 真正写入。

SRC_FIELD/DST_FIELD = 指定输入/输出字段：同名=原地改；填不同名=读旧字段、把改后的值写进新字段。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiftyone as fo
from fiftyone import ViewField as F

# ===================== 超参数（每次改这里）=====================
DATASET   = "swd_2025_eachfarm_64mp_south"
SRC_FIELD = "device"             # 读哪个字段
DST_FIELD = "device"             # 写到哪个字段（同名=原地改；不同名=另存为新字段）
MAPPING   = {"16MP": "64MP"}     # 旧值 -> 新值（只改命中的样本，其余不动）
DRY_RUN   = True                 # True 只预览；改 False 才真正写入
# ==============================================================


def main():
    d = fo.load_dataset(DATASET)
    print(f"{DATASET}.{SRC_FIELD} 现状: {d.count_values(SRC_FIELD)}")
    total = 0
    for old, new in MAPPING.items():
        m = d.match(F(SRC_FIELD) == old)
        n = len(m)
        total += n
        print(f"  {old!r} -> {new!r}: {n} 张" + ("（预览）" if DRY_RUN else ""))
        if not DRY_RUN and n:
            m.set_values(DST_FIELD, [new] * n)
    if DRY_RUN:
        print(f"[预览] 共会改 {total} 张。确认后把 DRY_RUN 改成 False 再跑。")
    else:
        d.save()
        print(f"[ok] 已改 {total} 张。{DST_FIELD} 现状: {d.count_values(DST_FIELD)}")


if __name__ == "__main__":
    main()
