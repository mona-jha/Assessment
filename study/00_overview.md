# 00 — Overview (the 3-minute summary)

## The task in one sentence
Detect every nucleus in 50 H&E histopathology images covering 5 cancer
types (10 each), report counts and morphometrics, and present results.
**No ground-truth annotations were provided.**

## The dataset

| Cohort      | Disease                                                       |
|-------------|---------------------------------------------------------------|
| BRC         | Breast carcinoma                                              |
| CRC         | Colorectal carcinoma                                          |
| HCC         | Hepatocellular carcinoma                                      |
| NSCLC_AD    | Non-small-cell lung carcinoma — adenocarcinoma                |
| NSCLC_SCC   | Non-small-cell lung carcinoma — squamous cell carcinoma       |

Each PNG is roughly 480 × 560 px, RGB. Nuclei are blue/purple
(hematoxylin) on a pink background (eosin).

## The headline result

| Method     | Total nuclei | Notes                                       |
|------------|--------------|---------------------------------------------|
| Classical  | 24,250       | HED stain deconvolution + watershed         |
| Cellpose   | 24,097       | Pretrained DL (v4 `cpsam`)                  |
| StarDist   | 20,783       | Pretrained DL on H&E (`2D_versatile_he`)    |

- Classical and Cellpose agree to within **0.6%** in total count.
- Foreground-mask IoU between every pair of methods: **0.51 – 0.67**
  per cohort. That is strong agreement on un-annotated data.

## Why three methods?

Without ground truth we cannot compute precision/recall. The most
defensible substitute is **agreement between methods of different
families**:

- Classical = pure image processing (no learned weights).
- Cellpose = generalist deep learning (flow-based).
- StarDist = H&E-specific deep learning (polygon-based).

If three independent systems agree, the count is almost certainly right.
If they disagree, we look at the image.

## What's in the repository

```
task/
├── doc/Assessment/<COHORT>/Image*.png   ← inputs (provided)
├── code/                                 ← Python code
├── results/                              ← every artefact (50 overlays per
│                                          method, masks, CSVs, figures)
├── report/report.md                      ← long-form write-up
├── presentation/slides.pptx              ← deck for the team
└── study/                                ← this folder
```

## Run everything in 6 minutes

```bash
python code/01_run_segmentation.py --method classical    # 18 s CPU
python code/01_run_segmentation.py --method stardist     # 30 s CPU
python code/01_run_segmentation.py --method cellpose     # 5 min on Apple MPS
python code/02_compare_methods.py                        # cross-method IoU
python code/03_make_report_figures.py                    # final figures
python code/make_pptx.py                                 # slides.pptx
```

## Every artefact, in one paragraph each

- **`results/<method>/overlays/`** — 50 PNGs per method. Same image as
  the input, with yellow contours marking the boundary of every detected
  nucleus and a count caption in the corner. The fastest way to sanity-
  check a method visually.
- **`results/<method>/masks/`** — 50 instance label PNGs. Encoded as
  `uint16`, each pixel value is the integer ID of the nucleus it belongs
  to (0 = background). These are the ground-truth-shaped artefacts you
  would feed into any downstream pipeline.
- **`results/<method>/per_image_stats.csv`** — one row per image with
  count + 7 morphometric columns (see
  [09_morphometrics.md](09_morphometrics.md) for definitions).
- **`results/per_cohort_summary.csv`** — 15 rows = 3 methods × 5 cohorts.
  This is the single table you would put in a paper.
- **`results/method_agreement.csv`** — 50 × 3 rows: pairwise foreground
  IoU per image. The validation backbone.
- **`results/figures/0[1-6]_*.png`** — six figures used in the report
  and the slides; described in detail in
  [08_method_comparison.md](08_method_comparison.md).

## What to read next
- [01_he_staining.md](01_he_staining.md) if you want to understand *what*
  you are looking at in an H&E image.
- [02_classical_pipeline.md](02_classical_pipeline.md) if you want to
  understand *how* we segmented nuclei.
- [12_likely_questions.md](12_likely_questions.md) if you have a meeting
  in 10 minutes and need to be prepared.
