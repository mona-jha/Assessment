---
marp: true
title: Nucleus Detection & Quantification on H&E Images
paginate: true
---

# Nucleus Detection & Quantification
### H&E Histopathology — Syngene/BBRC Assessment
Mona Kumari · May 2026

---

## Objective
- Detect and quantify **every nucleus** in 50 H&E images.
- 5 cancer cohorts × 10 images:
  **BRC, CRC, HCC, NSCLC_AD, NSCLC_SCC**.
- **No ground truth** → cannot compute precision/recall.
- Strategy: run **three independent methods** and use their agreement
  as evidence of correctness.

---

## Three methods, three families

| Method      | Family            | Why                                               |
|-------------|-------------------|---------------------------------------------------|
| Classical   | Image processing  | Transparent, no training needed                   |
| Cellpose v4 | Generalist DL     | Robust pretrained flow-based segmenter            |
| StarDist    | H&E-specific DL   | Star-convex polygon prior, trained on H&E nuclei  |

Same interface (`segment(rgb) → labels`), same outputs, same driver script.

---

## Classical pipeline (no DL)

```
RGB
 └─ rgb2hed → Hematoxylin channel        ← nucleus-specific signal
     └─ percentile clip + Gaussian (σ=1)
         └─ Otsu threshold
             └─ opening + fill + small-object removal
                 └─ distance transform + watershed   ← splits touching nuclei
                     └─ regionprops + area/solidity filter
                         └─ count + morphometrics
```

End-to-end: **~18 s** for all 50 images on CPU.

---

## DL pipelines

**Cellpose v4 (`cpsam`)**
- Apple Metal (MPS): **~6 s/image** (vs ~150 s on CPU; ~25× speedup)
- `diameter=None` → auto-scales per image
- Total: **5 min** for 50 images

**StarDist (`2D_versatile_he`)**
- Pretrained specifically on H&E nuclei
- Lowered `prob_thresh` from 0.69 → 0.40 to recover dense lymphocyte clusters
- Total: **30 s** for 50 images

---

## Sample qualitative result — classical

![w:1100](../results/figures/01_qualitative_grid_classical.png)

*Original | H channel | Instances | Overlay — one row per cohort.*

---

## Cross-method qualitative comparison

![w:1100](../results/figures/06_method_qualitative_grid.png)

*Per cohort: original + boundaries from each of the three methods.*

---

## Total nuclei detected

| Method     | Total  | BRC   | CRC   | HCC   | NSCLC_AD | NSCLC_SCC |
|------------|--------|-------|-------|-------|----------|-----------|
| Classical  | 24,250 | 5,704 | 5,391 | 3,562 | 4,602    | 4,991     |
| Cellpose   | 24,097 | 5,790 | 5,499 | 3,278 | 4,118    | 5,412     |
| StarDist   | 20,783 | 5,309 | 4,601 | 2,775 | 3,662    | 4,436     |

- Classical ≈ Cellpose (<1% gap) — strong cross-method validation.
- StarDist more conservative (~14% lower) — star-convex prior.

---

## Per-image count agreement

![w:1100](../results/figures/05_method_count_scatter.png)

*Each point = one image. Tight clustering around y = x → high agreement.*

---

## Mask agreement (mean foreground-IoU per cohort)

| Cohort     | classical vs cellpose | classical vs stardist | cellpose vs stardist |
|------------|-----------------------|-----------------------|----------------------|
| BRC        | 0.57                  | 0.63                  | 0.62                 |
| CRC        | 0.55                  | 0.57                  | 0.62                 |
| HCC        | 0.66                  | 0.64                  | 0.67                 |
| NSCLC_AD   | 0.51                  | 0.52                  | 0.66                 |
| NSCLC_SCC  | 0.56                  | 0.57                  | 0.60                 |

High agreement (0.51–0.67) across all cohorts.
HCC highest — large, well-separated hepatocyte nuclei are easy for all methods.

---

## Density comparison (classical)

![w:900](../results/figures/04_density_by_cohort.png)

---

## Count & area distributions (classical)

![w:560](../results/figures/02_count_by_cohort.png) ![w:560](../results/figures/03_area_by_cohort.png)

---

## Biological interpretation
- **HCC**: lowest density (~1,279 / Mpx classical) — large hepatocytes with
  abundant cytoplasm.
- **BRC / CRC**: highest density (~2,000 / Mpx) and variance — heterogeneous
  architecture (glands + stroma + lymphocytic infiltrate).
- **NSCLC_SCC**: smallest nuclei (≈ 80 px²) — dense monomorphic
  squamous nests.
- **NSCLC_AD**: moderate density, mid-sized nuclei — adenocarcinoma glands.
- Classical and Cellpose agree within 1% on totals → high confidence
  in the ~24,000 nucleus count across all 50 images.

---

## Macenko normalisation — evaluated & rejected

| Method    | Without norm. | With norm. | Δ     |
|-----------|---------------|------------|-------|
| Classical | 24,250        | 15,497     | −36%  |
| Cellpose  | 24,097        | 24,194     | +0.4% |
| StarDist  | 20,783        | 14,732     | −29%  |

- Reference image (BRC/Image1) too different from other cohorts.
- Washed out tissue or over-darkened images → lost real nuclei.
- IoU dropped from 0.51–0.67 → 0.13–0.44.
- **Decision: use un-normalised results throughout.**

---

## Limitations
- No ground truth → cross-method agreement is our only validation.
- StarDist polygon prior misses non-convex/overlapping nuclei in dense
  regions.
- Watershed in the classical pipeline occasionally over-segments large
  nuclei.
- Macenko normalisation degraded results on this dataset.

---

## Next steps
- **HoVer-Net** for nucleus-type classification
  (epithelial / lymphocyte / stromal).
- **Manual annotation** of ~5 crops per cohort → real F1 / PQ metrics.
- **Reinhard normalisation** as alternative to Macenko — compare impact.
- **Method ensemble** (consensus mask) for a single best segmentation.

---

## Deliverables
- `code/` — 4 small modules + 3 numbered scripts, single-command pipeline.
- `results/<method>/` — 50 overlays + 50 masks + per_image_stats.csv per method.
- `results/per_cohort_summary.csv` — final aggregated table (3 × 5 cohorts).
- `results/method_agreement.csv` — pairwise IoU per image.
- `results/figures/` — 11 figures referenced in this deck.
- `results_norm/` — normalised results preserved for comparison.
- `report/report.html` — styled HTML report with embedded figures.
- `report/report.md` — plain-text Markdown version.

End-to-end runtime on MacBook Pro (Apple Silicon, no NVIDIA GPU): **~6 min**.

---

# Thank you
Questions?
