# Quickstart — 怎么快速跑

久没碰也能照这页直接跑，不用读源码。详细见 `README.md`，约束见 `CLAUDE.md`。

## 环境（重要）
所有命令都用 conda 环境 **`fif`**（不是旧的 `fiftyone`，那个版本不兼容数据库）：
```bash
conda run -n fif python scripts/<脚本>.py ...
conda run -n fif fiftyone app launch          # 打开浏览器 App
```

## 过滤 token 速记（predict / export / coverage 通用，来自 viewspec.py）
```
site=air1        某字段等值（裸 token 如 air1 = site=air1；纯数字自动转 int）
focus=fixed      year=2025  focal_length=525  device=16MP  status=cold
view=<已存视图>   从 App 里保存的 saved view 出发
limit=50         只取前 50 张（试跑）
label=<名>       给输出文件/视图命名（默认从过滤推断）
```

## 数据流水线（按顺序）
```bash
# 1. 扫描原始目录 → 生成可编辑的映射草稿 yaml（按 site/focus 分组）
conda run -n fif python scripts/make_sources.py \
    /media/tianqi/16tb/SWD/01_Data/2025_SWD_data_RAW/02_South 9248x6944 \
    datasets/swd_2025_eachfarm_64mp.yaml
#    → 人工审阅 yaml：改 name、补 defaults(year/device/status)、改 location 真实地名、删不要的组

# 2. 按 yaml 导入到 FiftyOne（原地引用，不复制；含 metadata、剔损坏、解析文件名）
conda run -n fif python scripts/import_dataset.py datasets/swd_2025_eachfarm_64mp.yaml

# 3.（可选）只重算文件名派生字段 date/time/focal（不读图、秒级、幂等）
conda run -n fif python scripts/enrich_names.py swd_2025_eachfarm_64mp

# 4.（一般不用）import 末尾已自动设 App 默认显示字段（site/location/focus/time/date/filepath）。
#    只有想换成别的字段时才跑：
conda run -n fif python scripts/app_defaults.py swd_2025_eachfarm_64mp site location focus time date filepath focal_length_64mp
```
文件名解析规则在根目录 `filename_patterns.yaml`（加新格式只改这里，不改代码）。

## 模型预测 → 导出标注
```bash
# 跑模型（高分辨率必加 slice=：切片+合并，不 OOM）。先 limit 试小批
conda run -n fif python scripts/predict.py /path/to/best.pt swd_2024_eachfarm_16mp \
    site=air1 limit=50 slice=640 overlap=0.2 conf=0.25
#   也可在 App 里筛/选好图 → Save view → 用 view= 直接跑那批：
conda run -n fif python scripts/predict.py /path/to/best.pt swd_2024_eachfarm_16mp view=good slice=640
#   旋钮：conf=(召回) iou=(去重) slice= overlap= batch= device=cpu label_field=  过滤：site=/focus=/view=/limit=

conda run -n fif fiftyone app launch          # 复核：图上叠加的框/多边形，可改

# 导出 LabelMe JSON 给 X-AnyLabeling（分割→polygon，框→rectangle）
conda run -n fif python scripts/export_labelme.py swd_2024_eachfarm_16mp \
    site=air1 limit=50 outdir=exports/labelme_air1
#   不给 outdir = 写在图片旁 <img>.json，X-AnyLabeling 打开图片目录自动加载

# 按某阈值把"每图框数"写进字段（可在网格显示/排序；换阈值就重跑）
conda run -n fif python scripts/count_preds.py swd_2024_eachfarm_16mp conf=0.5 field=n_pred
conda run -n fif python scripts/app_defaults.py swd_2024_eachfarm_16mp site focus n_pred   # 让网格显示它
#   注：App 拖 confidence 滑块只实时改"显示的框"；单张图的实时计数在 App 打开该图后侧栏看。
```

## 工具
```bash
# 采集覆盖热力图（看哪天没数据/不连续）：终端 ASCII + exports/ PNG + 交互 HTML
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1
#   要 HTML 可点击跳 App：加 links + 基址；用完清理：clearviews
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north clearviews
```

## 成批命令（runs/）
重复性的一串命令放 `runs/*.sh`，整跑或单行复制都行，也是"我跑过啥"的记录：
```bash
bash runs/coverage_all_sites.sh          # 给每个 site 出覆盖图
```
新需求就在 `runs/` 加个 `.sh`（改数据集/site 行即可）。

## 脚本一览
| 脚本 | 干啥 | 类型 |
|---|---|---|
| `make_sources.py` | 扫描目录生成映射草稿 yaml | 流水线 1 |
| `import_dataset.py` | 按 yaml 导入 FiftyOne | 流水线 2 |
| `enrich_names.py` | 重算文件名派生字段 | 流水线 3 |
| `app_defaults.py` | 设 App 默认显示字段 | 流水线 4 |
| `predict.py` | YOLO `.pt` 切片推理打标注 | 模型 |
| `export_labelme.py` | 预测导出 LabelMe(X-AnyLabeling) | 模型 |
| `count_preds.py` | 按阈值把每图框数写进字段 | 模型 |
| `coverage.py` | 采集覆盖热力图 | 工具 |
| `remap_field.py` | 批量改字段的值（改文件内超参数后跑，非 argv）| 工具 |
| `viewspec.py` | `build_view` 过滤解析（被上面 import，**别直接跑**）| 库 |

> 新增脚本时：在本表加一行。scripts/ 保持扁平，别用数字前缀或子目录（会破坏互相 import）。
