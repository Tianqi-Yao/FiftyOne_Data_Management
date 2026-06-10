#!/usr/bin/env bash
# 批量出每个 site 的采集覆盖图（terminal ASCII + exports/ PNG + HTML），覆盖全部 3 个数据集。
# 用法：① 整段跑 `bash runs/coverage_all_sites.sh`  ② 或单行复制到终端。
# 改用途：增删下面的行即可（site 含空格要加引号，如 "0_New Folder"）。
#
# 想让 HTML 格子可点击跳 App：在每行末尾加  links https://fiftyone.tianqiyao.men
#   （注意：会按天给每个 site 建一堆 cov_ saved view，量大；用完 `coverage.py <数据集> clearviews` 清）

cd "$(dirname "$0")/.." || exit 1     # 切到仓库根，保证 scripts/ 路径对

# ===== 2024 eachFarm 16MP =====
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=air1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=air2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=jeff focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=lloyd1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=ms1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=ms2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=southfarm1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=southfarm2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=sw1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2024_eachfarm_16mp site=sw2 focus=fixed links https://fiftyone.tianqiyao.men

# ===== 2025 North 16MP =====
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site="0_New Folder" focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=jeff focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=lloyd1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=lloyd2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=southfarm1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=southfarm2 focus=fixed links https://fiftyone.tianqiyao.men

# ===== 2025 South 64MP =====
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=ElderFarm1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=ElderFarm2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=HSH1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=ms1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=ms2 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=sw1 focus=fixed links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_64mp_south site=sw2 focus=fixed links https://fiftyone.tianqiyao.men

# ---- 想"加新 site / 新数据集不用手改"的循环版（取消注释即可，自动遍历每个数据集的所有 site）----
# for DATASET in swd_2024_eachfarm_16mp swd_2025_eachfarm_16mp_north swd_2025_eachfarm_64mp_south; do
#   while IFS= read -r SITE; do
#     conda run -n fif python scripts/coverage.py "$DATASET" site="$SITE" focus=fixed
#   done < <(conda run -n fif python -c "import fiftyone as fo;print('\n'.join(fo.load_dataset('$DATASET').distinct('site')))")
# done
