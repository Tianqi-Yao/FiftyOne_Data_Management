# CLAUDE.md — SWD 图片数据管理

## 核心约束（不可违反）

1. **保持目录结构简单**，研究项目风格，不是企业软件。
2. **目录深度 ≤ 3 层**（项目仓库内）。新功能不许靠加深目录解决。
3. **优先新增脚本，不要新增框架**。一个任务 = `scripts/` 里一个动词命名的脚本。
4. **优先复用已有目录**：`scripts/ datasets/ notebooks/ exports/ data/`。先问「能不能放进现有目录」，再考虑新建。
5. **不要堆 docs**。说明写进 `README.md` 或脚本顶部注释，不要建文档目录树。
6. **不要过度抽象**：不要 src/core/manager/service/factory 这类分层，不要为复用而提前抽象。
7. 这是**科研数据管理项目**，不是企业软件项目。代码服务于数据管理，不为架构而架构。
8. **FiftyOne 是主要数据管理工具**。组织/筛选/检索用 FiftyOne 的 dataset/view/tag，不要自己造管理系统。
9. **SSD = Hot Data**（正在标注/处理/训练）：`/mnt/D/SWD/01_Data`。
10. **16TB_HDD = Cold Data**（原始/历史/已完成）：`/media/tianqi/16tb/SWD/01_Data`。
11. **图片不进 git 仓库**，原地引用 + `data/` 下软链接；FiftyOne 用绝对路径引用。

## 约定速查

- 存储树（冷热同构）：`<tier>/SWD/01_Data/<year>/<location>/<device>/<batch_date>/*.jpg`
- Dataset 名：`swd_<year>_<location>_<device>`（小写 snake，前缀恒为 `swd_`）
- 横切维度（年份/地点/设备/划分/质检）用 **tag**，不堆进名字。
- `datasets/*.yaml` 是真相源，FiftyOne 数据库可丢弃重建。

## 新增东西前先问自己

- 这能不能只加一个 `scripts/*.py` 解决？→ 能就这么做。
- 这是不是又在 FiftyOne 之外造轮子？→ 是就停下，用 FiftyOne。
- 这会不会让目录变深或变抽象？→ 会就换简单做法。
