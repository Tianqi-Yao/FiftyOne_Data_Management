#!/usr/bin/env python
"""扫描一个目录，生成 import_dataset.py 用的 sources 映射草稿（YAML）。

用法:
    python scripts/make_sources.py <扫描根目录> <目标分辨率> [输出.yaml]
例:
    python scripts/make_sources.py \
        /media/tianqi/16tb/SWD/01_Data/2024_SWD_data_RAW/eachFarm \
        4656x3496 datasets/swd_2024_eachfarm_16mp.yaml

把每个含目标分辨率图片的目录，按 (site, focus) 归好类，paths 列出具体目录、
数量写在注释里。**生成后请人工审阅**：改 location 真实地名、把放错的目录挪到
对的组、删掉不要的组。结果完全由这张表决定（可复现）。
"""
import os
import re
import sys
import collections
from PIL import Image

RES_RE = re.compile(r"(\d{3,4})x(\d{3,4})")
EXCLUDE = {"sensor"}


def resolution(path):
    m = RES_RE.search(path)
    if m:
        return f"{m.group(1)}x{m.group(2)}"
    try:
        return "x".join(map(str, Image.open(path).size))
    except Exception:
        return None


def focus_mode(path):
    p = path.lower()
    if "fixedfocus" in p:
        return "fixed"
    if "autofocus" in p:
        return "auto"
    if re.search(r"focus_\d+", p):
        return "sweep"
    return "unknown"


def site_of(path, root):
    rel = os.path.relpath(path, root)
    return rel.split(os.sep)[0]


def main(root, target, out=None):
    # groups[(site, focus)] = {dir: count}
    groups = collections.defaultdict(lambda: collections.Counter())
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE]
        for f in fns:
            if not f.lower().endswith(".jpg"):
                continue
            full = os.path.join(dp, f)
            if resolution(full) != target:
                continue
            groups[(site_of(full, root), focus_mode(full))][dp] += 1

    name = f"swd_{os.path.basename(root.rstrip('/')).lower()}"
    lines = [
        f"# 自动生成的草稿，请人工审阅：改 name、补 defaults、改 location 真实地名、挪放错的目录。",
        f"# 跑: python scripts/import_dataset.py <本文件>",
        f"name: {name}   # TODO 按约定改名，如 swd_<year>_<场>_<device>",
        f"defaults: {{ }}   # TODO 补共享字段，如 {{ year: 2024, device: 16MP, status: cold }}",
        f"compute_metadata: true",
        f"sources:",
    ]
    for (site, focus) in sorted(groups):
        dirs = groups[(site, focus)]
        total = sum(dirs.values())
        lines.append(f"  # ---- {site} / {focus}: {total} 张 ----")
        lines.append(f"  - set: {{ site: {site}, location: {site}, focus: {focus} }}   # TODO location")
        lines.append(f"    require_resolution: \"{target}\"")
        lines.append(f"    paths:")
        for d in sorted(dirs):
            lines.append(f"      - \"{d}\"   # {dirs[d]} 张")
    text = "\n".join(lines) + "\n"

    if out:
        with open(out, "w") as f:
            f.write(text)
        print(f"[ok] 已写出草稿: {out}")
        print(f"     {len(groups)} 组, 共 {sum(sum(g.values()) for g in groups.values())} 张")
        print(f"     审阅后跑: python scripts/import_dataset.py {out}")
    else:
        print(text)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
