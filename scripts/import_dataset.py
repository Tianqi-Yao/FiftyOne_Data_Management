#!/usr/bin/env python
"""按 datasets/<name>.yaml 清单创建/更新一个 FiftyOne 数据集。

用法:
    python scripts/import_dataset.py datasets/swd_2024_eachfarm_16mp.yaml

清单是真相源 —— FiftyOne 数据库可删可重建，重跑本脚本即可。结果完全由
清单决定（可复现）。图片原地引用（不复制），FiftyOne 只存 filepath + 字段。

结构化属性存成**字段**（StringField/IntField...），这样在 App 侧边栏会自动
变成下拉多选 / 数值滑块 / 时间选择器。tags 留给工作流标记。

推荐写法：mapping 模式（可手动编辑、分组批量赋值）
---------------------------------------------------------
    defaults: { year: 2024, device: 16MP, status: cold }   # 所有组共享的字段
    sources:                                               # 映射表，逐条手改
      - set: { site: air1, location: Airport, focus: fixed }
        require_resolution: "4656x3496"   # 可选：按实际像素过滤
        tags: [ ]                          # 可选：这组要打的 tag
        paths:                             # 目录或 glob，可递归
          - "/.../air1/.../4656x3496_fixedfocus"
      - set: { site: air1, location: Airport, focus: auto }
        paths: [ "/.../air1/.../4656x3496_autofocus" ]

每条 source 的 set 字段 = defaults + 本组覆盖，赋给本组所有图。
跨 source 命中同一文件时，靠后的 source 覆盖（并会提示数量）。

简易模式（结构规整时）
---------------------------------------------------------
    root: /.../eachFarm          # 递归遍历（或 path/paths 用 glob）
    require_resolution: "4656x3496"
    exclude_dirs: [sensor]
    tags: [year:2024, device:16mp]
    year/device/...              # 直接当字段

通用选项（两种模式都支持）
---------------------------------------------------------
    compute_metadata: true   # 逐张读图算宽高/大小（HDD 上图多会慢）
    drop_corrupt: true       # 默认 true：算 metadata 时打不开的图，先记到
                             #   exports/<name>_corrupt.txt，再从数据集剔除
    parse_filename: true     # 从文件名解析 date(DateField)/time/focal_length(IntField)
                             #   解析不出的仍导入，但标 tag qc:name_unparsed，
                             #   路径写到 exports/<name>_unparsed_names.txt 待补救
                             #   解析规则在仓库根 filename_patterns.yaml（不写死在代码）
    index: true              # 默认 true：给所有结构化字段建索引（加速 App 筛选/排序）
"""
import os
import re
import sys
import glob
import yaml
from datetime import date as _date, datetime as _datetime
import fiftyone as fo
from fiftyone import ViewField as F
from PIL import Image

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
RES_RE = re.compile(r"(\d{3,4})x(\d{3,4})")
# 仓库根（脚本在 scripts/ 下），报告统一写到这里的 exports/，与运行目录无关
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect_from_roots(roots, exclude_dirs):
    files = []
    for root in roots:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in exclude_dirs]
            for f in fns:
                if f.lower().endswith(IMG_EXTS):
                    files.append(os.path.join(dp, f))
    return files


def collect_from_globs(patterns):
    out = []
    for pat in patterns:
        dirs = glob.glob(pat) if any(c in pat for c in "*?[") else [pat]
        for d in dirs:
            if os.path.isdir(d):
                for ext in IMG_EXTS:
                    out += glob.glob(f"{d}/**/*{ext}", recursive=True)
                    out += glob.glob(f"{d}/**/*{ext.upper()}", recursive=True)
            elif d.lower().endswith(IMG_EXTS):
                out.append(d)
    return out


def resolution(path):
    """优先从路径解析 WxH；解析不到才读像素头。"""
    m = RES_RE.search(path)
    if m:
        return f"{m.group(1)}x{m.group(2)}"
    try:
        w, h = Image.open(path).size
        return f"{w}x{h}"
    except Exception:
        return None


# 文件名解析规则放在仓库根的 filename_patterns.yaml（唯一来源，不写死在代码里）。
PATTERNS_FILE = os.path.join(REPO, "filename_patterns.yaml")


def load_patterns():
    """读 filename_patterns.yaml 里的正则列表（命名组 year/mon/day/hh/mm/focal）。"""
    with open(PATTERNS_FILE) as f:
        return yaml.safe_load(f)["patterns"]


def parse_name(path, year, patterns):
    """从文件名解析 date(DateField) / time(DateTimeField 可拖) / focal_length（解析不到的不加）。

    patterns: 来自 load_patterns() 的正则列表。从上到下，第一条匹配出 hh/mm 的胜出。
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    out = {}
    for pat in patterns:
        mo = re.search(pat, stem)
        if not mo:
            continue
        g = mo.groupdict()
        if not (g.get("hh") and g.get("mm")):
            continue
        y = g.get("year") or year
        if y and g.get("mon") and g.get("day"):
            try:
                out["date"] = _date(int(y), int(g["mon"]), int(g["day"]))
            except ValueError:
                pass
        # time 存成 DateTimeField（固定假日期 2000-01-01 + 真实时分）：
        # App 里就是带 HH:MM 的可拖时段滑块
        out["time"] = _datetime(2000, 1, 1, int(g["hh"]), int(g["mm"]))
        if g.get("focal"):
            out["focal_length"] = int(g["focal"])
        break
    return out


def build_plan(m):
    """返回 {filepath: 字段dict}。靠后的 source 覆盖靠前的。"""
    defaults = m.get("defaults", {})
    plan = {}
    overlaps = 0

    if m.get("sources"):
        for src in m["sources"]:
            attrs = {**defaults, **src.get("set", {})}
            req = src.get("require_resolution")
            files = collect_from_globs(src["paths"] if "paths" in src
                                       else [src["path"]])
            for p in files:
                if req and resolution(p) != req:
                    continue
                if p in plan:
                    overlaps += 1
                plan[p] = {**attrs, "_tags": list(src.get("tags", []))}
    else:
        # 简易模式
        if m.get("root"):
            roots = m["root"] if isinstance(m["root"], list) else [m["root"]]
            files = collect_from_roots(roots, set(m.get("exclude_dirs", [])))
        else:
            files = collect_from_globs(m.get("paths") or [m["path"]])
        req = m.get("require_resolution")
        attrs = {k: m[k] for k in ("year", "location", "device", "site", "focus")
                 if k in m}
        for p in files:
            if req and resolution(p) != req:
                continue
            plan[p] = {**defaults, **attrs, "_tags": list(m.get("tags", []))}

    if overlaps:
        print(f"[warn] {overlaps} 张图被多个 source 命中，按靠后的 source 取值")

    # 从文件名解析 date / time / focal_length；解析不出的打 qc:name_unparsed
    if m.get("parse_filename"):
        patterns = load_patterns()        # 规则来自 filename_patterns.yaml
        for p, attrs in plan.items():
            info = parse_name(p, attrs.get("year"), patterns)
            attrs.update(info)
            if "time" not in info:        # 没拿到日期时间 = 命名异常
                attrs["_tags"].append("qc:name_unparsed")

    return plan


def write_report(name, suffix, paths, msg):
    """把一批异常路径写到 <repo>/exports/<name>_<suffix>.txt 并打印摘要。"""
    exports = os.path.join(REPO, "exports")
    os.makedirs(exports, exist_ok=True)
    log = os.path.join(exports, f"{name}_{suffix}.txt")
    with open(log, "w") as fh:
        fh.write("\n".join(paths) + "\n")
    print(f"[warn] {msg} {len(paths)} 张（清单 {log}）：")
    for p in paths[:10]:
        print(f"    {p}")
    if len(paths) > 10:
        print(f"    ... 共 {len(paths)} 张")
    return log


def ensure_indexes(dataset, fields):
    """给字段建索引（已存在的跳过），返回新建的字段名。加速 App 筛选/排序。"""
    existing = set(dataset.list_indexes())
    created = []
    for f in fields:
        if f not in existing:
            dataset.create_index(f)
            created.append(f)
    return created


def main(manifest_path):
    with open(manifest_path) as f:
        m = yaml.safe_load(f)
    name = m["name"]

    plan = build_plan(m)
    if not plan:
        sys.exit(f"[err] 没匹配到任何图片，检查清单：{manifest_path}")

    # 文件名解析失败的，已标 qc:name_unparsed —— 报告出来，留给补救代码
    unparsed = [p for p in sorted(plan) if "qc:name_unparsed" in plan[p]["_tags"]]
    if unparsed:
        write_report(name, "unparsed_names", unparsed,
                     "文件名无法解析 date/time，已标 qc:name_unparsed")

    if name in fo.list_datasets():
        fo.delete_dataset(name)
    dataset = fo.Dataset(name)

    samples = []
    for p in sorted(plan):
        attrs = dict(plan[p])
        tags = attrs.pop("_tags", [])
        samples.append(fo.Sample(filepath=p, tags=tags, **attrs))  # attrs -> 字段
    dataset.add_samples(samples)
    dataset.persistent = True

    if m.get("compute_metadata", True):
        dataset.compute_metadata()       # 损坏图会失败 -> metadata.width 为空

        if m.get("drop_corrupt", True):
            bad = dataset.match(F("metadata.width") == None)  # noqa: E711
            paths = bad.values("filepath")
            if paths:
                write_report(name, "corrupt", paths, "损坏/无法读取，已剔除")
                dataset.delete_samples(bad.values("id"))

    print(f"[ok] {name}: {len(dataset)} 张图")
    schema = [k for k in dataset.get_field_schema()
              if k not in ("id", "filepath", "tags", "metadata", "created_at",
                           "last_modified_at")]
    print(f"     字段: {schema}")

    if m.get("index", True):                 # 给结构化字段建索引（加速 App 筛选）
        created = ensure_indexes(dataset, schema)
        print(f"     索引: 新建 {created or '无（已存在）'}")
    for fld in schema:
        try:
            print(f"     {fld}: {dataset.count_values(fld)}")
        except Exception:
            pass
    print(f"     浏览: fiftyone app launch")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
