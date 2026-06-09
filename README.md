# FiftyOne_Data_Management

SWD（Spotted Wing Drosophila）项目的**图片数据管理**目录。目标是长期方便地
整理、检索、浏览、筛选、管理标注、做数据质量检查。主工具是 **FiftyOne**。

这是研究项目，不是软件工程项目 —— 代码服务于数据管理。详细约束见 `CLAUDE.md`。

## 目录结构

```
FiftyOne_Data_Management/
├── CLAUDE.md          # 核心约束（防止结构越改越复杂）
├── README.md          # 本文件
├── data/              # 只放软链接（gitignored）
│   ├── hot  -> /mnt/D/SWD/01_Data              # SSD 热数据
│   └── cold -> /media/tianqi/16tb/SWD/01_Data  # 16TB HDD 冷数据
├── scripts/           # 所有脚本（扁平，动词命名）
├── datasets/          # 每个 FiftyOne dataset 一个 yaml 清单
├── notebooks/         # 探索性浏览 / 临时查询
└── exports/           # 导出的视图、报告（gitignored）
```

**关键原则：** 图片**原地存放**在 SSD/HDD，FiftyOne 用绝对路径引用，**不进 git**。
组织靠 FiftyOne 的 dataset / view / tag，不靠搬文件夹。

## 存储分工

| | SSD（Hot）`/mnt/D/SWD/01_Data` | 16TB HDD（Cold）`/media/tianqi/16tb/SWD/01_Data` |
|---|---|---|
| 放什么 | 正在标注/处理/训练的批次 | 原始图片、历史、已完成项目、冷数据 |

新批次按 `<year>/<location>/<device>/<batch_date>/*.jpg` 组织（冷热同构）。
既有的 `20XX_SWD_data_RAW/...` 目录保持原样，FiftyOne 照样用绝对路径引用。

## 常用流程

```bash
# 导入：先写 datasets/<name>.yaml，再
python scripts/import_dataset.py datasets/swd_2026_elderfarm_64mp.yaml

# 浏览 / 整理（打 tag、存 view）
fiftyone app launch

# 归档：把批次从 Hot 移到 Cold 并改 filepath
python scripts/archive.py swd_2026_elderfarm_64mp
```

## 命名约定

- **Dataset**：`swd_<year>_<location>_<device>`，如 `swd_2026_elderfarm_64mp`。
- **图片**（新生成的才重命名）：`<year>_<location>_<device>_<YYYYMMDD>_<seq>.jpg`。
- 横切维度（年份/地点/设备/划分/质检）一律用 **tag**，不堆进名字。
