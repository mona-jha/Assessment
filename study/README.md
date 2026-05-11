# Study Folder — Self-Study Companion

> **Start here:** open [`00_INDEX.md`](00_INDEX.md) for the recommended
> sequential reading plan. Each file is short (5–12 minutes) and
> self-contained.

| Sequence | File | Topic |
|----------|------|-------|
| 0 | [00_INDEX.md](00_INDEX.md) | Master index & reading plan |
| 1 | [00_overview.md](00_overview.md) | 60-second project summary |
| 2 | [01_he_staining.md](01_he_staining.md) | What H&E images really show |
| 3 | [09_morphometrics.md](09_morphometrics.md) | Every CSV column explained |
| 4 | [02_classical_pipeline.md](02_classical_pipeline.md) | Classical method (no DL) |
| 5 | [03_stain_deconvolution.md](03_stain_deconvolution.md) | Beer–Lambert math |
| 6 | [04_thresholding_morphology.md](04_thresholding_morphology.md) | Otsu + morphology |
| 7 | [05_watershed_instances.md](05_watershed_instances.md) | Splitting touching nuclei |
| 8 | [06_cellpose.md](06_cellpose.md) | Cellpose v4 deep dive |
| 9 | [07_stardist.md](07_stardist.md) | StarDist deep dive |
| 10 | [08_method_comparison.md](08_method_comparison.md) | Validation without GT |
| 11 | [10_results_interpretation.md](10_results_interpretation.md) | Biology of the cohorts |
| 12 | [11_codebase_walkthrough.md](11_codebase_walkthrough.md) | File-by-file code tour |
| 13 | [12_likely_questions.md](12_likely_questions.md) | 20-question Q&A bank |

**Total time end-to-end: ~2 hours.**

## Single-PDF version

Prefer to read on a tablet or print? The same content is available as a
51-page bookmarked PDF: [`study_guide.pdf`](study_guide.pdf).

To rebuild it after editing any of the markdown files:

```bash
./tools/study_pdf/build.sh       # requires pandoc + xelatex (already on this Mac)
```

Author: Mona Kumari · May 2026
