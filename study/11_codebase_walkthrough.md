# 11 — Codebase walkthrough

A guided tour of every file in [`code/`](../code/). Each entry says
*what the file is for*, *what to read in it*, and *what depends on it*.

## Directory map

```
code/
├── ../requirements.txt              ← classical pipeline deps (at repo root)
├── ../requirements_deeplearning.txt ← extra deps for Cellpose / StarDist (at repo root)
│
├── config.py                     ← paths, cohort list, classical params
├── image_io.py                   ← load images, save masks/overlays
├── features.py                   ← per-image morphometric stats
├── visualisation.py              ← overlay drawing, qualitative grids
│
├── method_classical.py           ← classical segmenter (no DL)
├── method_cellpose.py            ← Cellpose v4 wrapper
├── method_stardist.py            ← StarDist wrapper (local model load)
│
├── 01_run_segmentation.py        ← driver: run ONE method on all 50 images
├── 02_compare_methods.py         ← cross-method IoU + scatter figure
├── 03_make_report_figures.py     ← per-cohort figures + summary CSV
└── make_pptx.py                  ← build presentation/slides.pptx
```

## The four "library" files
These contain reusable helpers and zero CLI logic.

### `config.py`
Single source of truth for:
- `INPUT_DIR`, `RESULTS_DIR`, `FIGURES_DIR` — path constants.
- `COHORTS` — list of cohort folder names.
- `CLASSICAL` — a frozen `ClassicalParams` dataclass with all the
  classical-pipeline thresholds.

If you want to retune, edit ONE place. Everything else imports from here.

### `image_io.py`
Three small functions:
- `load_rgb(path)` — read PNG to HxWx3 uint8.
- `save_mask(labels, path)` — write uint16 PNG (instances).
- `save_overlay(rgb_overlay, path)` — write the overlay PNG.
- `gather_inputs(input_dir, cohorts)` — return a sorted
  `[(cohort, path), ...]` list for the entire dataset.
- `output_paths(method, cohort, image_stem, results_dir)` — compute
  the canonical overlay/mask file paths.

### `features.py`
One function:
- `extract_features(labels, image_shape)` → dict with all the columns
  documented in [09_morphometrics.md](09_morphometrics.md).

### `visualisation.py`
Two functions:
- `make_overlay(rgb, labels)` — yellow nucleus boundaries + count box.
- `qualitative_grid(rows, out_path)` — generic 5×4 figure builder.

## The three "method" files
Each implements the contract `segment(rgb) -> uint32 instance label image`
and exposes a `NAME` constant.

### `method_classical.py`
Self-contained classical pipeline. Plus `hematoxylin_channel(rgb)` is
exposed because the qualitative grid wants to display the H channel
side-by-side with the original.

→ Walked through line-by-line in
[02_classical_pipeline.md](02_classical_pipeline.md) and
[05_watershed_instances.md](05_watershed_instances.md).

### `method_cellpose.py`
Lazy-loads `models.CellposeModel(gpu=...)`, choosing MPS / CUDA / CPU
in that order. Then calls `model.eval(rgb, diameter=None, ...)`.

→ Explained in [06_cellpose.md](06_cellpose.md).

### `method_stardist.py`
Loads from a local copy under `~/.stardist/models/2D_versatile_he/`
(bypassing keras' SSL-checking downloader). Calls
`predict_instances(img, prob_thresh=0.40, nms_thresh=0.30)`.

→ Explained in [07_stardist.md](07_stardist.md).

## The three driver scripts (numbered)

### `01_run_segmentation.py`
Runs ONE method on all 50 images.

```bash
python code/01_run_segmentation.py --method classical
python code/01_run_segmentation.py --method cellpose
python code/01_run_segmentation.py --method stardist
```

Flags:
- `--cohort BRC` — restrict to one cohort.
- `--limit 1` — process only the first N images (smoke-test).

Implementation:
1. Lazy-import the chosen method module (no TF/Torch cost when only
   classical is requested).
2. Loop with `tqdm`.
3. Per image: `load_rgb` → `method.segment` → save mask + overlay →
   `extract_features`.
4. Write `results/<method>/per_image_stats.csv`.
5. Print a per-cohort summary to stdout.

### `02_compare_methods.py`
After all three methods are run:
- Builds `results/per_image_all_methods.csv` (long-form, one row per
  (image, method)).
- Computes pairwise foreground-mask IoU per image →
  `results/method_agreement.csv`.
- Generates `figures/05_method_count_scatter.png` and
  `figures/06_method_qualitative_grid.png`.

→ Explained in [08_method_comparison.md](08_method_comparison.md).

### `03_make_report_figures.py`
Per-cohort aggregate figures + the classical qualitative grid:
- `figures/01_qualitative_grid_classical.png`
- `figures/02_count_by_cohort.png`
- `figures/03_area_by_cohort.png`
- `figures/04_density_by_cohort.png`
- `results/per_cohort_summary.csv` (3 methods × 5 cohorts = 15 rows)

### `make_pptx.py`
Reads the figures + tables and writes
`presentation/slides.pptx`. Uses `python-pptx`. 17 slides, 16:9.

## Adding a new method
The architecture makes this trivial. Steps:

1. Create `code/method_yournewname.py` with:
   ```python
   NAME = "yournewname"

   def segment(rgb: np.ndarray) -> np.ndarray:
       # ... do whatever, return uint32 instance label image
   ```
2. Register it in `01_run_segmentation.py`'s `AVAILABLE_METHODS` dict.
3. Run `python code/01_run_segmentation.py --method yournewname`.
4. Re-run `02_compare_methods.py` and `03_make_report_figures.py`.

No other file needs to change.

## What lives outside `code/`
- [`results/`](../results/) — every artefact (overlays, masks, CSVs,
  figures).
- [`report/report.md`](../report/report.md) — the long-form write-up.
- [`presentation/slides.md`](../presentation/slides.md) +
  [`slides.pptx`](../presentation/slides.pptx) — the deck.
- [`study/`](README.md) — this folder.

## Conventions worth knowing
- **Filenames carry context**: `BRC_Image1_overlay.png` makes sense even
  if copied out of the tree.
- **Numbered scripts** (`01_…`, `02_…`, `03_…`) advertise the run order.
- **Lazy imports** in `01_run_segmentation.py` mean classical-only runs
  don't import TF/Torch.
- **One global parameter set** in `CLASSICAL`; never per-cohort tuning.

## Reading a script: a worked walk-through of `01_run_segmentation.py`

```python
# 1. Parse CLI args (--method, --cohort, --limit)
args = parser.parse_args()

# 2. Lazy-import the chosen method module
if args.method == "classical":
    from method_classical import segment, NAME
elif args.method == "cellpose":
    from method_cellpose import segment, NAME
elif args.method == "stardist":
    from method_stardist import segment, NAME

# 3. Build the input list
targets = gather_inputs(INPUT_DIR, COHORTS)
if args.cohort:
    targets = [t for t in targets if t[0] == args.cohort]
if args.limit:
    targets = targets[:args.limit]

# 4. Loop with a progress bar
rows = []
for cohort, path in tqdm(targets, desc=NAME):
    rgb     = load_rgb(path)
    labels  = segment(rgb)            # <-- method-specific
    overlay = make_overlay(rgb, labels)

    op, mp  = output_paths(NAME, cohort, path.stem, RESULTS_DIR)
    save_overlay(overlay, op)
    save_mask(labels, mp)

    feats   = extract_features(labels, rgb.shape)
    feats.update(cohort=cohort, image=path.name)
    rows.append(feats)

# 5. Write the per-image CSV
pd.DataFrame(rows).to_csv(
    RESULTS_DIR / NAME / "per_image_stats.csv", index=False)
```

Five steps. Anything in `code/01_run_segmentation.py` that isn't one of
these is just argument parsing or a per-cohort summary print at the end.

## What to do when something breaks

| Symptom                                  | Fix                                                     |
|------------------------------------------|---------------------------------------------------------|
| ImportError on `cellpose` / `stardist`   | Run `pip install -r requirements_deeplearning.txt` |
| `cpsam` weights download fails           | Check connectivity; rerun `./run.sh weights`            |
| StarDist SSL error                       | Manually place weights in `~/.stardist/models/2D_versatile_he/` |
| Cellpose extremely slow on Mac           | Verify MPS: `python -c "import torch; print(torch.backends.mps.is_available())"` should print `True` |
| `KeyError: 'overlay'`                    | Likely an old run with pre-refactor paths — delete `results/` and re-run |

## Adding new morphometrics

If you wanted to add `mean_perimeter` to every CSV:

1. In `code/features.py`, add `"mean_perimeter": float(np.mean([r.perimeter for r in regions]))` to the dict returned by `extract_features`.
2. Re-run all three methods (classical takes ~18s; the DL methods need
   their CSVs regenerated only if you also re-run them).

Everything downstream (`02_compare_methods.py`, `03_make_report_figures.py`,
`make_pptx.py`) reads CSVs by column name and gracefully ignores
unknown columns, so nothing else needs changing.
