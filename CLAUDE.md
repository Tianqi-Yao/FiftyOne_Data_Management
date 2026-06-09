# CLAUDE.md — SWD 图片数据管理（中文）

科研**数据管理**项目（用 FiftyOne 管理 SWD 图片）。**不是**企业软件项目。
代码服务于数据管理，不为架构而架构。English: `CLAUDE.md`。

## 核心约束（不可违反）

1. 目录保持**简单**、研究风格。仓库内目录深度 **≤ 3 层**。
2. **优先新增/扩展 `scripts/` 里的脚本**，不要引入框架。
3. **复用已有目录**：`scripts/ datasets/ notebooks/ exports/ data/`。先问"能不能放进
   现有目录"再新建。
4. 不要 `src/core/manager/service/factory` 这类分层。**不要过度抽象。**
5. 不要堆 `docs/` 目录树——说明写进 `README*.md` 或脚本顶部 docstring。
6. **FiftyOne 是主要数据管理工具。** 组织/筛选/检索用 dataset / view / field / tag，
   不要另造一套管理系统。
7. **图片不进 git。** 原地引用，FiftyOne 只存绝对路径。`data/hot`、`data/cold` 是软
   链接（gitignored）。

## 运行环境

- 一律用 **`conda run -n fif`**（fiftyone 1.13.4）。名叫 `fiftyone` 的环境是 1.10.0，
  与共享数据库 `~/.fiftyone` **不兼容**。
- FiftyOne 数据库：默认 `~/.fiftyone`。

## 存储

- **SSD = 热数据**（在用）：`/mnt/D/SWD/01_Data`
- **16TB HDD = 冷数据**（原始/历史/已完成）：`/media/tianqi/16tb/SWD/01_Data`
- 原始目录**结构不统一**（历史代码迭代）。**按图片实际像素尺寸判定，不靠文件夹名。**
  不要相信固定深度的 glob 能取全。

## 数据模型

- 结构化属性存成**字段**（App 自动出好用的 UI）：`site`、`location`、`focus`、`year`、
  `device`、`status`、`date`(DateField)、`time`(DateTimeField，一天内时段=可拖 HH:MM，
  占位日期 2000-01-01)、`focal_length`(IntField)。
- **`tags` 只用于工作流 / 质检**（如 `qc:name_unparsed`，以后 reviewed/good/discard）。
- `datasets/*.yaml` 是**真相源**（可复现、可手改）。数据库可删可重建，重跑导入即可。
- **文件名解析规则放在仓库根 `filename_patterns.yaml`（唯一来源，不写死在代码）。**
  一组带命名组 year/mon/day/hh/mm/focal 的正则。新格式 → 往该文件加一行正则，不改代码。
  解析不出的图标 `qc:name_unparsed`，不静默丢弃。
- 数据集命名：`swd_<year>_<scope>_<device>`，如 `swd_2024_eachfarm_16mp`。

## 脚本（保持这套；扩展，不要增殖）

- `import_dataset.py <清单>` —— 一次跑完的全量导入（收集 → 字段 → `compute_metadata`
  → 剔损坏 → 解析文件名）。
- `make_sources.py <根> <WxH> <out.yaml>` —— 扫描目录，生成可编辑的 `sources:` 映射
  草稿（按 site/focus 分组，逐目录列出供手改）。
- `enrich_names.py <数据集|清单>` —— 可重复跑、**不读图片**：(重新)解析文件名 →
  `date/time/focal_length`。导入过后只想重算文件名派生字段时用。与
  `import_dataset.py` 共用 `parse_name`（单一来源）。
- `app_defaults.py <数据集> [字段...]` —— 设 App 默认激活/显示的字段（写 `app_config.active_fields`，
  持久化；重新 import 会重置 app_config，重跑即可恢复）。
- `coverage.py <数据集> [field=value...|view=名|label=名] [links] [基址]` —— 采集覆盖热力图
  （Day×Hour，终端 ASCII + PNG + 交互 HTML），可对**任意过滤 view** 出图，列出无数据的天。
  核心 `coverage(view, label, base_url, make_links)` 可在 notebook 直接传 view。**深链默认
  关闭**；仅加 `links`（+基址）才按天建 `cov_<label>_<日期>` saved view（OSS 只能靠 saved
  view 深链）。`clearviews` 一键删所有 `cov_*` 视图。**不要默认建一堆 saved view 污染列表。**

## 异常：浮出来，绝不静默丢弃

- 损坏图（读不出 metadata）→ **剔除** + 记录到 `exports/<name>_corrupt.txt`。
- 文件名解析不出 → **保留** + 打 tag `qc:name_unparsed` + 记录到
  `exports/<name>_unparsed_names.txt`。以后补救（扩展 `parse_name` 或单独处理）。

## 动手加东西前先问自己

- 这能不能只加一个 `scripts/*.py`？→ 那就这么做。
- 是不是在重造 FiftyOne 已有的能力？→ 停，用 FiftyOne。
- 会不会让目录变深或更抽象？→ 换简单做法。
