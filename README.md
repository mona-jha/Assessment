# Nucleus Detection & Quantification on H&E Histopathology Images

> **Syngene/BBRC Digital Pathology Assessment** — Detect and quantify
> *every* nucleus in 50 H&E images across 5 cancer cohorts, using three
> independent segmentation methods so the results can be cross-validated
> in the absence of ground-truth annotations.
>
> **Author:** Mona Kumari · **Date:** May 2026

---

## TL;DR

| Method     | Total nuclei | Mean per image | Notes                                |
|------------|--------------|-----------------|--------------------------------------|
| Classical  | **24,250**   | 485             | HED stain deconvolution + watershed  |
| Cellpose   | **24,097**   | 482             | Pretrained DL (v4 `cpsam`) on MPS    |
| StarDist   | **20,783**   | 416             | H&E-specific DL (`2D_versatile_he`)  |

- **Classical vs Cellpose**: 0.6% gap in total count.
- **Mean foreground-mask IoU between methods**: 0.51 – 0.67 across cohorts.
- **End-to-end runtime** on a MacBook Pro (Apple Silicon, no NVIDIA GPU): **~6 min**.

Reproduce everything with one command:

```bash
./run.sh                # full pipeline: setup -> weights -> 3 methods -> figures -> ppt
```

---

## Why this approach?

The dataset has **no manual annotations**, so we cannot compute classical
accuracy metrics (precision / recall / F1 / panoptic quality). The most
defensible substitute is to run **methods of different families** and use
their **agreement** as evidence of correctness:

1. **Classical** — pure image processing. Every step is auditable.
   No training data dependency.
2. **Cellpose v4 (`cpsam`)** — generalist deep-learning segmenter.
   Predicts per-pixel flow fields toward cell centres.
3. **StarDist (`2D_versatile_he`)** — H&E-specific deep-learning model.
   Represents each nucleus as a star-convex polygon.

Three orthogonal failure modes. If all three agree, the count is almost
certainly right. Disagreement is itself diagnostic — we can look at the
image.

---

## Repository layout

```
task/
├── README.md                          ← you are here
├── run.sh                             ← single reproducer (./run.sh all)
├── requirements.txt                   ← classical pipeline deps
├── requirements_deeplearning.txt      ← extra deps for StarDist / Cellpose
├── .gitignore
│
├── doc/
│   └── instruction.txt                ← original task description
│   NOTE: Dataset images (doc/Assessment/) are NOT included in this
│         repository. Place the 50 H&E images in doc/Assessment/<COHORT>/
│         to reproduce from scratch.
│
├── code/                              ← all Python pipeline code
│   ├── config.py                      ← paths, cohort list, classical params
│   ├── image_io.py                    ← load images, save masks/overlays
│   ├── features.py                    ← per-image morphometric stats
│   ├── visualisation.py               ← overlay + qualitative-grid drawing
│   ├── method_classical.py            ← HED + watershed (no DL)
│   ├── method_cellpose.py             ← Cellpose v4 'cpsam' wrapper
│   ├── method_stardist.py             ← StarDist 2D_versatile_he wrapper
│   ├── 01_run_segmentation.py         ← runs ONE method on all 50 images
│   ├── 02_compare_methods.py          ← cross-method IoU + scatter
│   ├── 03_make_report_figures.py     ← per-cohort figures + summary CSV
│   ├── 04_make_fpfn_figures.py        ← FP/FN consensus analysis
│   ├── stain_norm.py                  ← Macenko normalisation (evaluated & rejected)
│
├── results/                           ← every artefact lands here
│   ├── classical/
│   │   ├── overlays/<COHORT>_<image>_overlay.png   (50 PNGs)
│   │   ├── masks/<COHORT>_<image>_mask.png         (50 uint16 instance maps)
│   │   └── per_image_stats.csv
│   ├── cellpose/                      ← same layout
│   ├── stardist/                      ← same layout
│   ├── per_cohort_summary.csv         ← 3 methods × 5 cohorts
│   ├── per_image_all_methods.csv      ← long-form, every method × image
│   ├── method_agreement.csv           ← pairwise foreground-IoU per image
│   └── figures/                       ← 11 figures used in the report

```

---

## Quick start (TL;DR commands)

### Option A — one-shot reproducer
```bash
./run.sh                # everything: env + weights + 3 methods + analysis + ppt
```

### Option B — step-by-step
```bash
./run.sh setup          # create .venv and install requirements
./run.sh weights        # download Cellpose (~1.1GB) and StarDist (~5MB)
./run.sh classical      # ~18 s
./run.sh stardist       # ~30 s
./run.sh cellpose       # ~5 min on MPS, ~2h on CPU
./run.sh analysis       # comparison + figures + slides.pptx
```

### Option C — manual (no run.sh)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_deeplearning.txt        # for DL methods

python code/01_run_segmentation.py --method classical
python code/01_run_segmentation.py --method stardist
python code/01_run_segmentation.py --method cellpose
python code/02_compare_methods.py

```

### Useful flags
```bash
# Run a single cohort:
python code/01_run_segmentation.py --method classical --cohort BRC

# Smoke-test (first image only):
python code/01_run_segmentation.py --method cellpose --cohort BRC --limit 1
```

---

## Method 1 — Classical pipeline (no DL)

```
RGB image
 └─ rgb2hed              ← stain deconvolution, keep H channel
     └─ percentile clip [1%, 99%] + Gaussian (σ = 1.0)
         └─ Otsu threshold
             └─ opening (disk r=2) + hole-fill + drop < 30 px²
                 └─ distance transform + watershed (min_distance = 6 px)
                     └─ regionprops + area [30, 4000] + solidity ≥ 0.70
                         └─ count + morphometrics
```

The only knob worth tuning per dataset is `peak_local_max(min_distance=...)`,
which controls how aggressively touching nuclei are split. We use a single
global parameter set across all five cohorts to keep the cohort comparison
fair.

**Runtime**: ~18 s for all 50 images on CPU.
**Code**: [code/method_classical.py](code/method_classical.py)

---

## Method 2 — Cellpose v4 (`cpsam`)

A SAM-based transformer that, for every pixel, predicts a 2D flow vector
pointing toward the nucleus centre, plus a cell-probability. Pixels that
converge to the same point under gradient ascent belong to the same
nucleus. No watershed needed.

| Device                | Time per image | Total (50 images) |
|-----------------------|----------------|--------------------|
| Apple Metal (MPS)     | ~6 s           | **~5 min**         |
| Apple M-series CPU    | ~150 s         | ~2 h               |

We use `diameter=None` (auto-scale) and the default flow / cell-prob
thresholds.

**Code**: [code/method_cellpose.py](code/method_cellpose.py)

---

## Method 3 — StarDist (`2D_versatile_he`)

For every pixel, predicts (a) "is this inside a nucleus?" probability
and (b) 32 ray distances to the nearest boundary — describing a
**star-convex polygon**. NMS picks the best non-overlapping polygons.

We lower `prob_thresh` from the pretrained default of **0.69 → 0.40**.
On dense lymphocyte clusters in BRC and CRC the default missed roughly
half the nuclei; 0.40 brings counts to within 5–10% of the other methods
without introducing visible over-segmentation.

We load StarDist from `~/.stardist/models/2D_versatile_he/` directly
(bypassing keras' SSL-checking downloader for reliability).

**Code**: [code/method_stardist.py](code/method_stardist.py)

---

## Validation without ground truth

We use two cross-method agreement metrics:

1. **Total count per image**
   Plotted as a per-image scatter
   ([results/figures/05_method_count_scatter.png](results/figures/05_method_count_scatter.png)).
   Tight clustering around `y = x` ⇒ strong agreement.

2. **Foreground-mask IoU**
   $$\text{IoU}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
   Each instance map is collapsed to a binary "any nucleus pixel" mask,
   then compared pairwise. Reported as **mean IoU per cohort** in
   [results/method_agreement.csv](results/method_agreement.csv).

3. **FP / FN consensus analysis**
   A pixel is "true nucleus" if ≥2 of 3 methods agree. Detections unique
   to one method are FP-like; consensus nuclei missed by a method are FN-like.
   Figures: [07_fpfn_grid](results/figures/07_fpfn_grid.png),
   [08_fpfn_counts_bar](results/figures/08_fpfn_counts_bar.png),
   [09_fpfn_cohort_bar](results/figures/09_fpfn_cohort_bar.png).

Mean IoU sits between **0.51 and 0.67** across all 15 (cohort, pair)
combinations — strong agreement among three independently-engineered
systems on un-annotated data.

---

## Per-cohort headline results (classical, mean per image)

| Cohort     | Count | Density / Mpx | Mean area (px²) | Eccentricity | Solidity |
|------------|-------|----------------|-----------------|--------------|----------|
| BRC        | 570   | 2,048          | 117             | 0.66         | 0.93     |
| CRC        | 539   | 1,935          | 130             | 0.70         | 0.93     |
| HCC        | 356   | **1,279**      | 118             | 0.72         | 0.93     |
| NSCLC_AD   | 460   | 1,652          |  96             | 0.71         | 0.92     |
| NSCLC_SCC  | 499   | 1,792          | **80**          | 0.67         | 0.94     |

- **HCC** has the lowest density — large hepatocytes with abundant cytoplasm.
- **NSCLC_SCC** has the smallest, most uniform nuclei — dense monomorphic
  squamous cell nests.
- **BRC / CRC** have highest density and largest variance — heterogeneous
  tissue (glands + stroma + lymphocytes).

All three methods agree on the rank ordering of cohorts.

---

## What lives where

| Output                                  | Path                                                 |
|-----------------------------------------|------------------------------------------------------|
| 50 overlays per method                  | `results/<method>/overlays/*.png`                    |
| 50 instance masks per method            | `results/<method>/masks/*.png`                       |
| Per-image morphometrics                 | `results/<method>/per_image_stats.csv`               |
| Per-cohort summary (3 × 5)              | `results/per_cohort_summary.csv`                     |
| Pairwise method agreement (IoU)         | `results/method_agreement.csv`                       |
| Long-form per-image table               | `results/per_image_all_methods.csv`                  |
| 11 figures (qualitative, stats, FP/FN, norm) | `results/figures/0[1-9]_*.png`, `1[0-1]_*.png` |

---

## Stain normalisation — evaluated & rejected

We implemented Macenko normalisation (pure numpy/scipy SVD, see
`code/stain_norm.py`) using BRC/Image1 as the reference. Impact:

| Method    | Without norm | With norm | Δ     |
|-----------|--------------|-----------|-------|
| Classical | 24,250       | 15,497    | −36%  |
| Cellpose  | 24,097       | 24,194    | +0.4% |
| StarDist  | 20,783       | 14,732    | −29%  |

The reference image had stain characteristics too different from other
cohorts — normalisation washed out tissue or over-darkened it, destroying
real nuclei (worst case: BRC/Image3 classical 1,084 → 59, −95%).
IoU dropped from 0.51–0.67 → 0.13–0.44.

**Decision:** All primary results use un-normalised input. See figures
[10_norm_comparison](results/figures/10_norm_comparison.png) and
[11_norm_scatter](results/figures/11_norm_scatter.png).

---

## Limitations

- No ground truth → cross-method agreement is the only validation.
- Watershed in the classical pipeline can over-segment large nuclei.
- StarDist polygon prior misses non-convex / overlapping nuclei.
- Macenko normalisation degraded results on this dataset (reference sensitivity).
- Single global parameter set — not per-cohort tuned.

## Possible improvements

- Manually annotate ~5 crops per cohort → real F1 / panoptic-quality.
- Try Reinhard normalisation or a better Macenko reference image.
- Try **HoVer-Net** for joint nucleus segmentation + cell-type classification.
- Hungarian-matched per-instance IoU between methods (instead of foreground only).
- Method ensemble (consensus mask via union + NMS).

## Contact

Mona Kumari
