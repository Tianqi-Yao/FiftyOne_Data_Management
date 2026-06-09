# FiftyOne_Data_Management（中文）

基于 **FiftyOne** 的 SWD（Spotted Wing Drosophila）图片**长期数据管理**项目。目标：对
几十万张图片做整理、检索、浏览、筛选、标注管理与数据质量检查。这是研究项目，不是软件
产品——规则见 `CLAUDE_zh.md`。English: `README.md`。

## 目录结构

```
FiftyOne_Data_Management/
├── CLAUDE.md / CLAUDE_zh.md     # 给后续工作的约束
├── README.md / README_zh.md     # 本文件
├── data/                        # 只放软链接（gitignored）
│   ├── hot  -> /mnt/D/SWD/01_Data               # SSD，热数据
│   └── cold -> /media/tianqi/16tb/SWD/01_Data   # 16TB HDD，冷数据
├── scripts/                     # import_dataset.py, make_sources.py, enrich_names.py
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

### 清单写法（mapping 模式）

```yaml
name: swd_2024_eachfarm_16mp
defaults: { year: 2024, device: 16MP, status: cold }   # 所有组共享的字段
compute_metadata: true
parse_filename: true            # -> date / time / capture_tod / focal_length
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
| `capture_tod` | DateTime | 可拖 HH:MM | 一天内时段（日期 2000-01-01 是占位）|
| `time` | String "HH:MM" | 下拉 | 可读时间 |
| `tags` | — | 标签筛选 | 工作流 / 质检，如 `qc:name_unparsed` |

`focus` ∈ {fixed, auto, sweep, unknown}。已支持的文件名格式：`MMDD_HHMM_<焦距>`、
`MMDD_HHMM`、`YYYY-MM-DD HH_MM_SS`、`image_YYYYMMDD_HHMMSS`。

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
