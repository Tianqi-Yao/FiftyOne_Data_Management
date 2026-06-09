# FiftyOne_Data_Management

Long-term **data management** for SWD (Spotted Wing Drosophila) images, built on
**FiftyOne**. Goal: organize, search, browse, filter, manage annotations and run
quality checks over hundreds of thousands of images. This is a research project, not
a software product — see `CLAUDE.md` for the rules. 中文版见 `README_zh.md`.
**Just want to run things? See `quickstart.md` (copy-paste cheat-sheet).**

## Layout

```
FiftyOne_Data_Management/
├── CLAUDE.md                    # constraints for future work
├── README.md / README_zh.md     # this file
├── filename_patterns.yaml       # filename → date/time/focal regex rules (single source)
├── data/                        # symlinks only (gitignored)
│   ├── hot  -> /mnt/D/SWD/01_Data               # SSD, active data
│   └── cold -> /media/tianqi/16tb/SWD/01_Data   # 16TB HDD, cold data
├── scripts/                     # import_dataset.py, make_sources.py, enrich_names.py, coverage.py,
│                                 #   app_defaults.py, predict.py, export_labelme.py, viewspec.py
├── datasets/                    # one *.yaml manifest per dataset (source of truth)
├── notebooks/                   # exploratory browsing / ad-hoc queries
└── exports/                     # reports & exports (gitignored)
```

**Key idea:** images live on SSD/HDD and are referenced **in place** (never copied
into git). FiftyOne stores only filepaths + fields. Organize with fields / views /
tags, not by moving folders.

## Environment

Use the conda env **`fif`** (fiftyone 1.13.4). The env named `fiftyone` is older
(1.10.0) and incompatible with the shared DB.

```bash
conda run -n fif fiftyone app launch        # browse
conda run -n fif python scripts/<...>.py    # run a script
```

## Storage split

| | SSD (hot) `/mnt/D/SWD/01_Data` | 16TB HDD (cold) `/media/tianqi/16tb/SWD/01_Data` |
|---|---|---|
| holds | data being annotated/processed/trained | raw, history, finished, cold |

Raw folders are structurally inconsistent across the years (historical code
iterations). The importer therefore identifies images by **actual pixel resolution**,
not by folder name.

## Import workflow

1. **Generate a draft mapping** from a raw tree (groups dirs by site/focus, lists
   every dir for hand-editing):
   ```bash
   conda run -n fif python scripts/make_sources.py \
       /media/tianqi/16tb/SWD/01_Data/2024_SWD_data_RAW/eachFarm 4656x3496 \
       datasets/swd_2024_eachfarm_16mp.yaml
   ```
2. **Edit the manifest** (`datasets/*.yaml`): set real `location`, move any
   mis-grouped path, drop groups you don't want. It is fully reproducible.
3. **Import** (one-shot: fields + metadata + drop corrupt + parse filenames + index fields):
   ```bash
   conda run -n fif python scripts/import_dataset.py datasets/swd_2024_eachfarm_16mp.yaml
   ```
4. **Re-parse filenames only** (fast, no image reads) when needed:
   ```bash
   conda run -n fif python scripts/enrich_names.py swd_2024_eachfarm_16mp
   ```

### Coverage / gaps

See which days/hours have data (and which are missing) — Day×Hour heatmap. Outputs to
`exports/`: terminal ASCII + PNG + **interactive HTML** (Plotly; hover shows
date/hour/count). Lists fully-empty days.

```bash
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north                 # whole dataset
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1        # filter
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 focus=fixed
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north view=my_saved_view
```

Runs on any **filtered view**: `field=value` tokens (bare token = `site=`; numbers cast
to int), `view=<saved_view>` to start from a saved view, `label=<x>` to name outputs. For
complex filters (ranges, etc.) call the importable function from a notebook:

```python
from coverage import coverage          # scripts/ on sys.path
coverage(dataset.match(F("focal_length") >= 500), label="focal500plus")
coverage(session.view or session.dataset.view(), label="appview")  # the live App view
```

A standalone CLI run can't see the App's live unsaved view; to use it from the CLI,
**Save view** in the App first, then `coverage.py <ds> view=<name>`.

**Click-through is opt-in** (off by default → no saved views created, hover-only). Add
the `links` token + a base URL (arg or `FIFTYONE_URL` env) to make HTML cells **clickable
→ the App, filtered to that day**. It then creates per-day saved views `cov_<label>_<date>`
(FiftyOne OSS deep-links only via saved views; pick the hour in-App with the `time`
slider). Clean them up anytime with `clearviews`.

```bash
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north site=air1 links https://fiftyone.tianqiyao.men
conda run -n fif python scripts/coverage.py swd_2025_eachfarm_16mp_north clearviews   # delete all cov_* views
```

### Predict with a trained model + export to X-AnyLabeling

Run a trained YOLO `.pt` (detection or instance-seg — auto-detected, **no ONNX needed**)
on a view; predictions are stored as a FiftyOne label field (overlaid on images in the
App, editable). Then export to LabelMe JSON for X-AnyLabeling / reuse.

```bash
# 1) sliced inference (recommended for high-res: cv2-slice into tiles, batched YOLO predict,
#    NMS-merge back to full-image coords; finds small objects & no OOM). Self-written, no SAHI.
conda run -n fif python scripts/predict.py /path/to/best.pt swd_2024_eachfarm_16mp site=air1 limit=50 slice=640 overlap=0.2
#    (drop slice= for plain whole-image inference; conf/iou/label_field/device/batch optional)
#    review overlaid predictions:  conda run -n fif fiftyone app launch
# 2) export predictions as LabelMe JSON (X-AnyLabeling opens these)
conda run -n fif python scripts/export_labelme.py swd_2024_eachfarm_16mp site=air1 limit=50 outdir=exports/labelme_air1
```

- Annotations live in the FiftyOne dataset (label field, default `predictions`); the `.json`
  files are an export for external tools. Seg → `shape_type:polygon`, box → `rectangle`.
- **`slice=<N>`** turns on **self-written tiling** (cv2 slice + `tile_positions` snap-back +
  batched `model.predict` + per-class **box-IoU greedy NMS**; seg masks rasterized to bbox).
  No SAHI dependency — works with any model `YOLO()` loads (`.pt/.onnx/.engine`). High-res
  16MP/64MP → always use `slice=` (better recall on small bugs, no mask-upscale OOM).
- Tuning knobs: `conf=` (recall), `iou=` (NMS dedup), `overlap=`, `slice=` (≈ model imgsz;
  64MP can go 1280/2560), `batch=`. Validate counts against your own GT.
- No `outdir` ⇒ writes `<img>.json` **beside each image** (X-AnyLabeling auto-loads it).
- Whole-image mode (no `slice=`) on high-res + instance-seg can OOM (mask upscaled to full
  size); use `slice=`, a detection model, or `device=cpu`. (FiftyOne skips failed images.)

### Manifest shape (mapping mode)

```yaml
name: swd_2024_eachfarm_16mp
defaults: { year: 2024, device: 16MP, status: cold }   # shared fields
compute_metadata: true
parse_filename: true            # -> date / time / focal_length
sources:
  - set: { site: air1, location: Airport, focus: fixed }
    require_resolution: "4656x3496"     # keep only this resolution (by pixels)
    paths:
      - "/media/.../air1/.../4656x3496_fixedfocus"   # one or more dirs/globs
```

## Fields (App UI)

| field | type | App | meaning |
|---|---|---|---|
| `site` / `location` / `focus` / `device` / `status` | String | dropdown | categorical |
| `year` / `focal_length` | Int | slider | numeric |
| `date` | Date | date picker | capture date |
| `time` | DateTime | draggable HH:MM | time-of-day (date 2000-01-01 is a placeholder) |
| `tags` | — | tag filter | workflow / QC, e.g. `qc:name_unparsed` |

Set which fields the App shows by default (persisted in `dataset.app_config`; re-run
after a re-import, which resets it):

```bash
conda run -n fif python scripts/app_defaults.py swd_2025_eachfarm_16mp_north site focus date time focal_length
```

`focus` ∈ {fixed, auto, sweep, unknown}. **Filename parsing rules live in
`filename_patterns.yaml`** (single source, not in code): a list of regexes with named
groups `year/mon/day/hh/mm/focal`; first match wins; extra parts (seconds) ignored;
missing `year` falls back to the manifest's `year`. A name matching none → kept,
tagged `qc:name_unparsed`, listed in `exports/<name>_unparsed_names.txt`. New format →
add one regex line to that file, no code change.

## Naming

- **Dataset**: `swd_<year>_<scope>_<device>` (lowercase), e.g. `swd_2024_eachfarm_16mp`.
- Keep original image filenames; extract date/time/focal into fields instead of renaming.

## Quality / exceptions

- Corrupt images are removed during import; their paths go to
  `exports/<name>_corrupt.txt`.
- Filenames the parser can't read are **kept**, tagged `qc:name_unparsed`, and listed
  in `exports/<name>_unparsed_names.txt` for remediation.

## Current state

`swd_2024_eachfarm_16mp`: 134,280 images (2024 eachFarm, 4656×3496/16MP, corrupt
dropped). focal_length 96–960; dates 2024-05-07 … 2024-10-11.
