#!/usr/bin/env python
"""数据采集覆盖热力图（Day × Hour）：直观看哪天没数据、哪天采集不连续。

可对【任意过滤后的 view】出图，方便只看某些情况。

命令行用法:
    python scripts/coverage.py <dataset> [过滤...] [FiftyOne基址]
过滤 token（可多个，按顺序 AND）：
    site=air1            字段等值过滤（裸 token 如 `air1` 等价于 site=air1）
    focus=fixed          字段等值（纯数字会转 int，如 year=2025 / focal_length=525）
    view=<saved_view名>  从一个已存的 saved view 出发
    label=<名>           输出文件名/saved view 前缀用的范围标签（默认从过滤推断）
    https://host         FiftyOne 基址（或用 FIFTYONE_URL 环境变量）
    links                **开启**点击深链：按天建 cov_<label>_<日期> saved view（需配基址）。
                         默认不开 —— 不建任何视图，HTML 只 hover，零污染。
    clearviews           删掉该数据集所有 cov_* saved view 后退出（清理用）。
例:
    python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 focus=fixed
    python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 links https://fiftyone.tianqiyao.men
    python scripts/coverage.py swd_2024_eachfarm_16mp_north view=myView links https://fiftyone.tianqiyao.men
    python scripts/coverage.py swd_2025_eachfarm_16mp_north clearviews

notebook 用法（任意复杂过滤都行，含范围；也可直接用当前 App 的 view）:
    from coverage import coverage
    coverage(dataset.match(F("focal_length") >= 500), label="focal500plus")
    coverage(session.view or session.dataset.view(), label="appview")  # 当前 App 里筛的 view

产出到 exports/<dataset>_<label>_coverage.{png,html}；HTML hover 显示 日期/小时/张数。
仅当加 `links`（且给基址）才建 saved view 让格子可点击深链（小时在 App 拖 time 滑块）。
小时取自 time 字段（DateTimeField 的 .hour）；没有 date/time 的样本（qc:name_unparsed）跳过。
"""
import os
import re
import sys
from datetime import timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiftyone as fo
import fiftyone.core.utils as fou
from fiftyone import ViewField as F
from import_dataset import REPO

BLOCKS = " ░▒▓█"   # 0, 低 -> 高


def make_day_views(dataset, view, name, lab, days_with_data, base_url):
    """按天建 saved view（先删同范围旧的），返回 {day: 深链 URL}。"""
    prefix = f"cov_{lab}_"
    for v in dataset.list_saved_views():
        if v.startswith(prefix):
            dataset.delete_saved_view(v)
    links = {}
    for d in days_with_data:
        vname = f"{prefix}{d:%Y%m%d}"
        dataset.save_view(vname, view.match(F("date") == d))
        links[d] = f"{base_url.rstrip('/')}/datasets/{name}?view={fou.to_slug(vname)}"
    print(f"已建 {len(links)} 个 saved view（前缀 {prefix}）")
    print("     提示：App 若已开着，硬刷新一下才看得到新视图、深链才跳得对")
    return links


def build_html(tag, days, cell, links, out):
    import plotly.graph_objects as go
    hours = list(range(24))
    z = [[cell.get((d, h), 0) for h in hours] for d in days]
    y = [d.isoformat() for d in days]
    url2d = [[links.get(d, "") for _ in hours] for d in days]
    fig = go.Figure(go.Heatmap(
        z=z, x=hours, y=y, customdata=url2d, colorscale="Viridis",
        hovertemplate="%{y}  %{x}:00<br>%{z} images<extra></extra>",
        colorbar=dict(title="images"),
    ))
    fig.update_yaxes(autorange="reversed", type="category")
    note = ("(click a cell -> that day in FiftyOne)" if links
            else "(hover for counts; pass a FiftyOne base URL to enable click-through)")
    fig.update_layout(title=f"Collection coverage — {tag} {note}",
                      xaxis_title="hour", yaxis_title="date",
                      height=max(400, len(days) * 16 + 200))
    post = ("var gd=document.getElementById('{plot_id}');"
            "gd.on('plotly_click',function(e){var u=e.points[0].customdata;"
            "if(u){window.open(u,'_blank');}});")
    fig.write_html(out, include_plotlyjs="cdn", post_script=post)
    print(f"HTML: {out}")


def clear_cov_views(dataset):
    """删掉数据集里所有 cov_* saved view（覆盖图深链产生的临时视图）。"""
    vs = [v for v in dataset.list_saved_views() if v.startswith("cov_")]
    for v in vs:
        dataset.delete_saved_view(v)
    return len(vs)


def coverage(view, label="all", base_url=None, make_links=False):
    """对一个（可过滤的）view 出覆盖热力图：终端 ASCII + PNG + 交互 HTML。

    make_links=True 时才建 cov_<label>_<日期> saved view 并让 HTML 格子可点击深链
    （需同时给 base_url）。默认 False —— 不建任何视图，只 hover，零污染。
    """
    dataset = view._dataset
    name = view.dataset_name
    lab = re.sub(r"[^0-9A-Za-z]+", "-", label).strip("-").lower() or "all"

    cell = Counter()       # (date, hour) -> 数量
    for d, t in zip(view.values("date"), view.values("time")):
        if d is None or t is None:
            continue
        cell[(d, t.hour)] += 1
    if not cell:
        sys.exit("[err] view 里没有可用的 date/time（过滤太狠？或先跑 enrich_names.py）")

    all_dates = [d for (d, _) in cell]
    d0, d1 = min(all_dates), max(all_dates)
    days = [d0 + timedelta(n) for n in range((d1 - d0).days + 1)]
    daily = {d: sum(cell.get((d, h), 0) for h in range(24)) for d in days}
    vals = sorted(cell.values())
    mx = vals[-1]
    hi = vals[int(0.95 * (len(vals) - 1))] or mx   # 95 分位裁剪，避免异常峰值压扁浓淡

    def ch(c):
        if c == 0:
            return BLOCKS[0]
        return BLOCKS[1 + min(3, int(3 * (c - 1) / max(1, hi - 1)))]

    # ---- 终端 ASCII ----
    tag = f"{name} [{label}]"
    print(f"\n采集覆盖 {tag}   每格=该小时图片数  浓淡 {BLOCKS[1]}低→{BLOCKS[4]}高（峰值 {mx}）")
    print("            " + "".join(str(h % 10) for h in range(24)) + "   日总计")
    for d in days:
        row = "".join(ch(cell.get((d, h), 0)) for h in range(24))
        wd = "一二三四五六日"[d.weekday()]
        print(f"{d.isoformat()} {wd} |{row}| {daily[d] if daily[d] else '—— 无数据'}")
    empty = sum(1 for d in days if daily[d] == 0)
    print(f"\n区间 {d0} ~ {d1}：共 {len(days)} 天，其中 {empty} 天完全无数据。")

    os.makedirs(os.path.join(REPO, "exports"), exist_ok=True)
    base = os.path.join(REPO, "exports", f"{name}_{lab}_coverage")

    # ---- PNG ----
    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        mat = np.array([[cell.get((d, h), 0) for h in range(24)] for d in days], float)
        fig, ax = plt.subplots(figsize=(10, max(3, len(days) * 0.18)))
        im = ax.imshow(mat, aspect="auto", cmap="viridis", interpolation="nearest")
        ax.set_xlabel("hour"); ax.set_ylabel("date")
        ax.set_xticks(range(0, 24, 2))
        step = max(1, len(days) // 40)
        ax.set_yticks(range(0, len(days), step))
        ax.set_yticklabels([days[i].isoformat() for i in range(0, len(days), step)])
        ax.set_title(f"collection coverage  {tag}")
        fig.colorbar(im, ax=ax, label="images")
        fig.tight_layout()
        fig.savefig(base + ".png", dpi=120)
        print(f"PNG: {base}.png")
    except Exception as e:
        print(f"[warn] PNG 跳过：{e}")

    # ---- 交互 HTML（+ 可选深链）----
    try:
        links = {}
        if make_links and base_url:
            days_data = [d for d in days if daily[d] > 0]
            links = make_day_views(dataset, view, name, lab, days_data, base_url)
        elif make_links:
            print("[warn] 加了 links 但没给 FiftyOne 基址，深链跳过（HTML 仅 hover）")
        build_html(tag, days, cell, links, base + ".html")
    except Exception as e:
        print(f"[warn] HTML 跳过：{e}")


def _cli(args):
    name = args[0]
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")
    dataset = fo.load_dataset(name)
    view = dataset.view()
    base_url = os.environ.get("FIFTYONE_URL")
    label = None
    make_links = False
    for tok in args[1:]:
        if tok in ("clearviews", "--clearviews"):
            print(f"已删除 {clear_cov_views(dataset)} 个 cov_* saved view")
            return
        elif tok in ("links", "--links"):
            make_links = True
        elif tok.startswith("http"):
            base_url = tok
        elif tok.startswith("view="):
            view = dataset.load_saved_view(tok[5:])
            label = label or tok[5:]
        elif tok.startswith("label="):
            label = tok[6:]
        else:
            k, v = tok.split("=", 1) if "=" in tok else ("site", tok)
            vv = int(v) if v.lstrip("-").isdigit() else v
            view = view.match(F(k) == vv)
            label = label or (v if k == "site" else f"{k}-{v}")
    coverage(view, label or "all", base_url, make_links)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    _cli(sys.argv[1:])
