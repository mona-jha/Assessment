# 00 — Master Index & Reading Plan

> **How to use this folder.** Read the files in the order listed below.
> Each file is short (5–10 minutes), self-contained, and ends with a
> "what to read next" pointer. After all 13 you will be able to defend
> the project end-to-end in any review setting.

---

## Sequential reading plan (recommended order)

### Part A — Context (~25 min)
| # | File | Time | What you will know after |
|---|------|------|--------------------------|
| 1 | [00_overview.md](00_overview.md) | 5 min | The 60-second elevator summary and where every artefact lives. |
| 2 | [01_he_staining.md](01_he_staining.md) | 8 min | Why H&E images look the way they do; what hematoxylin and eosin actually stain; what variability you can expect across cohorts. |
| 3 | [09_morphometrics.md](09_morphometrics.md) | 10 min | Every column of the per-image CSV, with units and ranges. (Read this before results so the numbers later make sense.) |

### Part B — Method 1: classical pipeline (~30 min)
| # | File | Time | What you will know after |
|---|------|------|--------------------------|
| 4 | [02_classical_pipeline.md](02_classical_pipeline.md) | 10 min | The end-to-end flow of `method_classical.py`. |
| 5 | [03_stain_deconvolution.md](03_stain_deconvolution.md) | 10 min | The Beer-Lambert math behind `rgb2hed` and why it beats grayscale. |
| 6 | [04_thresholding_morphology.md](04_thresholding_morphology.md) | 7 min | Otsu's method and the four morphological operators we use. |
| 7 | [05_watershed_instances.md](05_watershed_instances.md) | 8 min | The trick that splits touching nuclei. |

### Part C — Methods 2 & 3: deep-learning models (~20 min)
| # | File | Time | What you will know after |
|---|------|------|--------------------------|
| 8 | [06_cellpose.md](06_cellpose.md) | 10 min | Cellpose's flow-vector formulation and the v4 SAM backbone. |
| 9 | [07_stardist.md](07_stardist.md) | 10 min | Star-convex polygons and why we lowered `prob_thresh` to 0.40. |

### Part D — Validation & results (~25 min)
| # | File | Time | What you will know after |
|---|------|------|--------------------------|
| 10 | [08_method_comparison.md](08_method_comparison.md) | 10 min | How we validate without ground truth (foreground IoU + count agreement). |
| 11 | [10_results_interpretation.md](10_results_interpretation.md) | 10 min | What the per-cohort numbers mean biologically. |

### Part E — Code & Q&A (~25 min)
| # | File | Time | What you will know after |
|---|------|------|--------------------------|
| 12 | [11_codebase_walkthrough.md](11_codebase_walkthrough.md) | 12 min | A file-by-file tour of `code/` so you can navigate the repo. |
| 13 | [12_likely_questions.md](12_likely_questions.md) | 15 min | 20 anticipated reviewer questions with prepared answers. |

**Total time end-to-end: ~2 hours.**

---

## Quick reference — by topic

If you don't have time for the full tour and just need ONE file:

| If a reviewer asks about… | Open this |
|---------------------------|-----------|
| The high-level idea | [00_overview.md](00_overview.md) |
| H&E biology | [01_he_staining.md](01_he_staining.md) |
| The classical algorithm | [02_classical_pipeline.md](02_classical_pipeline.md) |
| `rgb2hed` math | [03_stain_deconvolution.md](03_stain_deconvolution.md) |
| Otsu / morphology | [04_thresholding_morphology.md](04_thresholding_morphology.md) |
| Watershed / instance separation | [05_watershed_instances.md](05_watershed_instances.md) |
| Cellpose internals | [06_cellpose.md](06_cellpose.md) |
| StarDist internals | [07_stardist.md](07_stardist.md) |
| Validation without GT | [08_method_comparison.md](08_method_comparison.md) |
| What every CSV column means | [09_morphometrics.md](09_morphometrics.md) |
| Per-cohort biology | [10_results_interpretation.md](10_results_interpretation.md) |
| Code structure | [11_codebase_walkthrough.md](11_codebase_walkthrough.md) |
| "What's a good answer to ___?" | [12_likely_questions.md](12_likely_questions.md) |

---

## Mental model — one diagram

```
                ┌────────────────────────────────────────────────┐
                │   50 H&E images  (5 cohorts × 10 images)       │
                │   No ground-truth annotations                  │
                └────────────────┬───────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
 ┌──────────────┐         ┌─────────────┐         ┌─────────────┐
 │  Classical   │         │  Cellpose   │         │  StarDist   │
 │  HED+watersh │         │  v4 cpsam   │         │  versatile  │
 │  (no DL)     │         │  (DL flow)  │         │  (DL poly)  │
 └──────┬───────┘         └──────┬──────┘         └──────┬──────┘
        │                        │                        │
        ▼                        ▼                        ▼
   24,250 nuclei            24,097 nuclei            20,783 nuclei
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ Cross-method agreement metrics│
                  │  • Total count scatter        │
                  │  • Foreground-mask IoU        │
                  │  • Per-cohort morphometrics   │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ Biological interpretation     │
                  │ HCC: lowest density           │
                  │ NSCLC_SCC: smallest, uniform  │
                  │ BRC/CRC: high density, varied │
                  └──────────────────────────────┘
```

That picture is the entire project. Every other study file expands one
arrow.

---

## What this folder is *not*

- **Not the report.** That's [`report/report.md`](../report/report.md).
- **Not the slides.** Those are [`presentation/slides.pptx`](../presentation/slides.pptx).
- **Not the code.** That's [`code/`](../code/).

This folder is a **learning aid** — written for someone who already has
the report and the code in front of them and wants to understand
*why* every decision was made.

---

## Author
Mona Kumari · May 2026
