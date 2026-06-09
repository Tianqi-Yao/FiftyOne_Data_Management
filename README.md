# FiftyOne_Data_Management

Long-term **data management** for SWD (Spotted Wing Drosophila) images, built on
**FiftyOne**. Goal: organize, search, browse, filter, manage annotations and run
quality checks over hundreds of thousands of images. This is a research project, not
a software product — see `CLAUDE.md` for the rules. 中文版见 `README_zh.md`.

## Layout

```
FiftyOne_Data_Management/
├── CLAUDE.md / CLAUDE_zh.md     # constraints for future work
├── README.md / README_zh.md     # this file
├── data/                        # symlinks only (gitignored)
│   ├── hot  -> /mnt/D/SWD/01_Data               # SSD, active data
│   └── cold -> /media/tianqi/16tb/SWD/01_Data   # 16TB HDD, cold data
├── scripts/                     # import_dataset.py, make_sources.py, enrich_names.py
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
3. **Import** (one-shot: fields + metadata + drop corrupt + parse filenames):
   ```bash
   conda run -n fif python scripts/import_dataset.py datasets/swd_2024_eachfarm_16mp.yaml
   ```
4. **Re-parse filenames only** (fast, no image reads) when needed:
   ```bash
   conda run -n fif python scripts/enrich_names.py swd_2024_eachfarm_16mp
   ```

### Manifest shape (mapping mode)

```yaml
name: swd_2024_eachfarm_16mp
defaults: { year: 2024, device: 16MP, status: cold }   # shared fields
compute_metadata: true
parse_filename: true            # -> date / time / capture_tod / focal_length
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
| `capture_tod` | DateTime | draggable HH:MM | time-of-day (date 2000-01-01 is a placeholder) |
| `time` | String "HH:MM" | dropdown | readable time |
| `tags` | — | tag filter | workflow / QC, e.g. `qc:name_unparsed` |

`focus` ∈ {fixed, auto, sweep, unknown}. Filename formats handled: `MMDD_HHMM_<focal>`,
`MMDD_HHMM`, `YYYY-MM-DD HH_MM_SS`, `image_YYYYMMDD_HHMMSS`.

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
