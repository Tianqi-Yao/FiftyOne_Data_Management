# FiftyOne_Data_Management（中文）

基于 **FiftyOne** 的 SWD（Spotted Wing Drosophila）图片**长期数据管理**项目。目标：对
几十万张图片做整理、检索、浏览、筛选、标注管理与数据质量检查。这是研究项目，不是软件
产品——规则见 `CLAUDE_zh.md`。English: `README.md`。

## 目录结构

```
FiftyOne_Data_Management/
├── CLAUDE.md                    # 给后续工作的约束
├── README.md / README_zh.md     # 本文件
├── filename_patterns.yaml       # 文件名 → date/time/focal 的正则规则（唯一来源）
├── data/                        # 只放软链接（gitignored）
│   ├── hot  -> /mnt/D/SWD/01_Data               # SSD，热数据
│   └── cold -> /media/tianqi/16tb/SWD/01_Data   # 16TB HDD，冷数据
├── scripts/                     # import_dataset.py, make_sources.py, enrich_names.py, coverage.py, app_defaults.py
├── datasets/                    # 每个数据集一个 *.yaml 清单（真相源）
├── notebooks/                   # 探索性浏览 / 临时查询
└── exports/                     # 报告与导出（gitignored）
```

**核心思想**：图片留在 SSD/HDD，**原地引用**（不拷进 git）。FiftyOne 只存 filepath +
字段。组织靠 字段 / view / tag，不靠搬文件夹。

## 运行环境

用 conda 环境 **`fif`**（fiftyone 1.13.4）。名叫 `fiftyone` 的环境是旧版（1.10.0），
与共享数据库不兼容。

```bash
conda run -n fif fiftyone app launch        # 浏览
conda run -n fif python scripts/<...>.py    # 跑脚本
```

## 存储分工

| | SSD（热）`/mnt/D/SWD/01_Data` | 16TB HDD（冷）`/media/tianqi/16tb/SWD/01_Data` |
|---|---|---|
| 放什么 | 正在标注/处理/训练的 | 原始、历史、已完成、冷数据 |

原始目录跨年份结构不统一（历史代码迭代），所以导入按**图片实际像素尺寸**判定，不靠文件
夹名。

## 导入流程

1. **生成草稿映射表**（按 site/focus 把目录分好组，逐目录列出供手改）：
   ```bash
   conda run -n fif python scripts/make_sources.py \
       /media/tianqi/16tb/SWD/01_Data/2024_SWD_data_RAW/eachFarm 4656x3496 \
       datasets/swd_2024_eachfarm_16mp.yaml
   ```
2. **人工编辑清单**（`datasets/*.yaml`）：填真实 `location`、把放错的目录挪组、删掉不
   要的组。完全可复现。
3. **导入**（一次跑完：字段 + metadata + 剔损坏 + 解析文件名）：
   ```bash
   conda run -n fif python scripts/import_dataset.py datasets/swd_2024_eachfarm_16mp.yaml
   ```
4. **只重算文件名字段**（快，不读图片）：
   ```bash
   conda run -n fif python scripts/enrich_names.py swd_2024_eachfarm_16mp
   ```

### 采集覆盖 / 缺口

看哪天哪个小时有数据、哪天缺——Day×Hour 热力图。产出到 `exports/`：终端 ASCII +
PNG + **交互 HTML**（Plotly，hover 显示 日期/小时/张数），并统计完全无数据的天。

```bash
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north                  # 整个数据集
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1         # 过滤
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 focus=fixed
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north view=my_saved_view
```

可对**任意过滤后的 view** 出图：`field=value` token（裸 token = `site=`；纯数字转 int）、
`view=<saved view 名>` 从已存视图出发、`label=<x>` 命名输出。复杂过滤（如范围）在 notebook
里调用可导入的函数：

```python
from coverage import coverage          # scripts/ 已在 sys.path
coverage(dataset.match(F("focal_length") >= 500), label="focal500plus")
coverage(session.view or session.dataset.view(), label="appview")  # 当前 App 里筛的 view
```

CLI 独立进程看不到 App 里临时未保存的 view；要在 CLI 用它，先在 App 里 **Save view**，
再 `coverage.py <ds> view=<名>`。

**点击深链默认关闭**（不建任何 saved view，只 hover）。要让格子可点击 → 跳到 App 当天
视图，加 `links` token + 基址（参数或 `FIFTYONE_URL`）；它才按天建 `cov_<label>_<日期>`
saved view（FiftyOne OSS 只能靠 saved view 深链；小时在 App 拖 `time` 滑块）。随时用
`clearviews` 清理。

```bash
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north clearviews   # 删所有 cov_* 视图
```

```bash
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north air1 https://fiftyone.tianqiyao.men
```

### 清单写法（mapping 模式）

```yaml
name: swd_2024_eachfarm_16mp
defaults: { year: 2024, device: 16MP, status: cold }   # 所有组共享的字段
compute_metadata: true
parse_filename: true            # -> date / time / focal_length
sources:
  - set: { site: air1, location: Airport, focus: fixed }
    require_resolution: "4656x3496"     # 只留这个分辨率（按像素）
    paths:
      - "/media/.../air1/.../4656x3496_fixedfocus"   # 一个或多个目录/glob
```

## 字段（App 里的 UI）

| 字段 | 类型 | App | 含义 |
|---|---|---|---|
| `site` / `location` / `focus` / `device` / `status` | String | 下拉 | 分类 |
| `year` / `focal_length` | Int | 滑块 | 数值 |
| `date` | Date | 日期选择 | 采集日期 |
| `time` | DateTime | 可拖 HH:MM | 一天内时段（日期 2000-01-01 是占位）|
| `tags` | — | 标签筛选 | 工作流 / 质检，如 `qc:name_unparsed` |

设置 App 里默认显示哪些字段（持久化到 `dataset.app_config`；重新 import 会重置，重跑即可）：

```bash
conda run -n fif python scripts/app_defaults.py swd_2025_eachfarm_16mp_north site focus date time focal_length
```

`focus` ∈ {fixed, auto, sweep, unknown}。**文件名解析规则放在 `filename_patterns.yaml`**
（唯一来源，不写死在代码）：一组带命名组 `year/mon/day/hh/mm/focal` 的正则；从上到下第
一条匹配胜出；多余部分（如秒）忽略；缺 `year` 时用清单的 `year`。任何一条都不匹配的图 →
保留、标 `qc:name_unparsed`、列进 `exports/<name>_unparsed_names.txt`。新格式只需往该文件
**加一行正则**，不改代码。

## 命名

- **数据集**：`swd_<year>_<scope>_<device>`（小写），如 `swd_2024_eachfarm_16mp`。
- 原图文件名保持不动；把日期/时间/焦距解析成字段，而不是重命名。

## 质量 / 异常

- 损坏图在导入时剔除，路径写到 `exports/<name>_corrupt.txt`。
- 解析不了的文件名**保留**、打 tag `qc:name_unparsed`，并列进
  `exports/<name>_unparsed_names.txt` 待补救。

## 当前状态

`swd_2024_eachfarm_16mp`：134,280 张（2024 eachFarm，4656×3496/16MP，已剔损坏）。
focal_length 96–960；日期 2024-05-07 … 2024-10-11。
