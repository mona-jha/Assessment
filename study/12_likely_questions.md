# 12 — Likely review questions & answers

A self-quiz / Q&A bank. Read this before any meeting where you have to
defend the work.

---

### Q1. *"What's the goal in one sentence?"*
> Detect every nucleus in 50 H&E images across 5 cancer cohorts and
> quantify them, using three independent methods because no ground truth
> is available.

---

### Q2. *"Why three methods? Wasn't one enough?"*
> Without ground truth we have no way to compute precision / recall.
> The strongest available substitute is **agreement** between methods of
> **different families**: classical image processing, generalist DL
> (Cellpose), and H&E-specific DL (StarDist). When all three agree on
> a number, that number is almost certainly correct. When they
> disagree, the disagreement is itself diagnostic.

---

### Q3. *"Which method is best?"*
> Depends on the criterion.
> - **Best total-count agreement with the others**: classical and
>   Cellpose are within 0.6%.
> - **Cleanest boundaries on dense regions**: Cellpose.
> - **Fastest**: classical (~18 s for 50 images on CPU).
> - **Most explainable**: classical (every step is a documented
>   image-processing operator).
>
> For a production pipeline I would use Cellpose with classical as a
> sanity-check fallback.

---

### Q4. *"Walk me through the classical pipeline."*
> RGB → HED stain deconvolution (keep H channel) → percentile clip +
> Gaussian smooth → Otsu threshold → opening + hole-fill + drop tiny
> objects → distance-transform watershed (splits touching nuclei) →
> filter by area [30, 4000] px² and solidity ≥ 0.70.
> The watershed is the key step — it converts a binary mask into per-
> instance labels.
>
> Detail in [02_classical_pipeline.md](02_classical_pipeline.md).

---

### Q5. *"Why HED deconvolution and not just the blue channel?"*
> The blue channel of an RGB image picks up *everything* that scatters
> blue light, including pale eosin areas and clean glass. HED
> deconvolution uses the Beer-Lambert model to invert the known stain
> matrix and isolate **only the hematoxylin contribution** at each
> pixel. The result is a clean nucleus-specific channel.
>
> Detail in [03_stain_deconvolution.md](03_stain_deconvolution.md).

---

### Q6. *"What is the watershed step actually doing?"*
> After thresholding, two touching nuclei share one binary blob. The
> distance transform turns each nucleus into a "mountain" with its peak
> at the centre. We find local peaks (`peak_local_max`, min distance
> 6 px) and use them as markers for `watershed`, which floods outward
> from each peak. Where two flood fronts meet, that's the boundary
> between the two nuclei.
>
> Detail in [05_watershed_instances.md](05_watershed_instances.md).

---

### Q7. *"What does Cellpose do internally?"*
> Cellpose v4 (`cpsam`) is a SAM-based transformer that, for every
> pixel, predicts a 2D flow vector pointing to the centre of its
> nucleus, plus a cell-probability. Instances come from gradient ascent
> on the flow field — pixels that converge to the same point are the
> same nucleus. No explicit watershed needed.
>
> Detail in [06_cellpose.md](06_cellpose.md).

---

### Q8. *"And StarDist?"*
> Predicts a star-convex polygon for every pixel: 32 ray distances to
> the boundary plus a centre-probability. NMS picks the best non-
> overlapping polygons.
>
> The polygon prior is a strong shape constraint — great for typical
> ellipse-shaped nuclei, conservative on overlapping or non-convex ones.
>
> Detail in [07_stardist.md](07_stardist.md).

---

### Q9. *"Why did you tune StarDist's `prob_thresh` from 0.69 to 0.40?"*
> The default missed roughly half the nuclei in dense lymphocyte
> clusters in BRC and CRC (smoke-test on `BRC/Image1.png`: 216 vs
> ~580 from the other methods). Lowering to 0.40 produced 495 — much
> closer to classical (577) and Cellpose (590), with no qualitative
> over-segmentation introduced. 0.40 is a commonly-used value for
> `2D_versatile_he` on dense H&E.

---

### Q10. *"How can you trust your numbers without ground truth?"*
> Three lines of evidence:
> 1. **Cross-method count agreement**: classical 24,250, Cellpose 24,097
>    (0.6% gap), StarDist 20,783 (–14%, expected for the conservative
>    polygon prior).
> 2. **Foreground-mask IoU between methods**: 0.51–0.67 across cohorts.
>    Strong for un-annotated data.
> 3. **Biological plausibility**: density ranking HCC < NSCLC_AD <
>    NSCLC_SCC ≈ CRC < BRC matches the known histology of these tumour
>    types.
>
> Detail in [08_method_comparison.md](08_method_comparison.md) and
> [10_results_interpretation.md](10_results_interpretation.md).

---

### Q11. *"What are the limitations of your work?"*
> 1. No ground truth → no precision/recall.
> 2. Watershed in the classical pipeline can over-segment large nuclei.
> 3. StarDist polygon prior misses overlapping/non-convex nuclei.
> 4. Stain variability remains; Macenko normalisation would help.
> 5. Single global parameter set across cohorts (chosen for fairness,
>    not maximum per-cohort accuracy).

---

### Q12. *"How would you improve this in production?"*
> 1. **Manual annotation** of ~5 crops per cohort for real F1 / PQ.
> 2. **Macenko / Reinhard stain normalisation** before all methods.
> 3. **HoVer-Net** for joint segmentation + nucleus-type classification
>    (epithelial / lymphocyte / stromal counts per cohort).
> 4. **Method ensemble**: union-of-masks with NMS to combine the three
>    methods into a single consensus segmentation.
> 5. **Hungarian-matched instance IoU** for proper per-nucleus
>    correspondence between methods.

---

### Q13. *"Why is HCC the lowest density?"*
> Hepatocellular carcinoma tissue is dominated by hepatocytes —
> large cells with abundant pink (eosin) cytoplasm. The nuclei
> themselves are not unusually small; there are just **fewer cells per
> unit tissue area**. All three of our methods independently rank HCC
> as the lowest-density cohort, so this is not a method artefact.

---

### Q14. *"Why does NSCLC_SCC have the smallest, most uniform nuclei?"*
> Squamous cell carcinoma forms dense monomorphic nests of cells with
> small, tightly-packed, similarly-sized nuclei. The standard deviation
> of nucleus area in NSCLC_SCC (~9 px²) is much smaller than in
> NSCLC_AD (~22 px²) or CRC (~67 px²), confirming this uniformity
> quantitatively.

---

### Q15. *"How fast is the pipeline?"*

| Step                                | Time on MacBook Pro (Apple Silicon) |
|-------------------------------------|-------------------------------------|
| Classical (50 images, CPU)          | ~18 s                               |
| StarDist (50 images, CPU)           | ~30 s                               |
| Cellpose (50 images, **MPS**)       | ~5 min                              |
| Cellpose (50 images, CPU only)      | ~2 h (would not be practical)       |
| Comparison + figures + pptx         | ~10 s total                         |

> Apple's MPS backend gives Cellpose a ~25× speedup over CPU. No NVIDIA
> GPU required.

---

### Q16. *"What if I asked you to do this on 5,000 images instead of 50?"*
> Steps:
> 1. Move Cellpose to a GPU machine (would be ~50× faster again on a
>    single H100).
> 2. Parallelise the classical pipeline with `joblib` or `concurrent.
>    futures` — embarrassingly parallel per image.
> 3. Stream image loading; don't keep them all in memory.
> 4. Persist masks as compressed PNGs (already done) or zarr/HDF5 if
>    going larger.
> 5. Likely move to a tile-based workflow if images become whole-slide
>    (gigapixel) instead of small ROIs.

---

### Q17. *"What's `mean_solidity` and why ~0.93?"*
> Solidity = `region_area / convex_hull_area`. A perfectly convex shape
> has solidity 1. Real nuclei are nearly convex (small bumps and
> indentations), giving solidity ~0.92–0.96. The fact that all five
> cohorts average ~0.93 is a *positive sign* — our segmented instances
> look like real nuclei, not jagged fragments.
>
> Definitions in [09_morphometrics.md](09_morphometrics.md).

---

### Q18. *"Could two methods agree and still both be wrong?"*
> Yes — that's why agreement is *evidence*, not *proof*. If all three
> methods share a systematic blind spot (e.g. all under-detecting
> faintly-stained nuclei) they can agree on a wrong answer. The
> ultimate fix is manual annotation of a held-out subset, which is
> listed as a top improvement in the report.

---

### Q19. *"What would change if I gave you ground truth right now?"*
> I would:
> 1. Run all three methods on the annotated subset.
> 2. Compute precision, recall, F1, and panoptic quality per method.
> 3. Pick the best method overall as the "primary".
> 4. Use the other two as automatic sanity-check baselines that flag
>    images where they disagree with the primary by more than a
>    cohort-specific threshold (those go to a human reviewer).

---

### Q20. *"Where is everything?"*

```
task/
├── code/                ← Python (4 modules + 4 scripts)
├── doc/Assessment/      ← input PNGs (provided)
├── results/
│   ├── classical/       ← 50 overlays, 50 masks, per_image_stats.csv
│   ├── cellpose/        ← (same)
│   ├── stardist/        ← (same)
│   ├── per_cohort_summary.csv
│   ├── method_agreement.csv
│   └── figures/         ← 6 figures used in the report
├── report/report.md
├── presentation/
│   ├── slides.md
│   └── slides.pptx
└── study/               ← this folder
```

---

End of Q&A. If you can answer 15+ of these confidently, you can defend
the project in any interview/review setting.

---

### Q21. *"How would you debug a single image where StarDist disagrees badly with the others?"*
> 1. Open `results/method_agreement.csv`, sort by `iou_classical_stardist`,
>    pick the lowest-IoU row.
> 2. Open the three overlay PNGs side-by-side
>    (`results/<method>/overlays/<COHORT>_<image>_overlay.png`).
> 3. Visually inspect: where are nuclei detected by classical/Cellpose
>    but missed by StarDist? Are they in dense clusters, near the
>    image edge, or unusually shaped?
> 4. Lower `prob_thresh` further for that image (e.g. 0.30) and re-run
>    just that image with `--cohort X --limit 1` to confirm whether
>    they reappear.
> 5. If they do, the problem is StarDist's confidence calibration on
>    that tissue type — reportable as a known limitation.

---

### Q22. *"Why is your classical pipeline a single Python file rather than split into modules?"*
> The classical pipeline IS one logical operation: "H&E image → instance
> mask". Splitting it into one-function-per-step modules would add
> import overhead without any clarity benefit — the file is only ~80
> lines. The operations that ARE split out (image I/O, features,
> visualisation, config) are reused across all three methods.

---

### Q23. *"What's the difference between watershed and the polygon prior in StarDist?"*
> Both are answers to "how do I split touching nuclei".
>
> - **Watershed** is *post hoc*: detect a binary blob first, then split.
>   Splits are based on the geometry of the blob (distance peaks).
> - **Polygon prior** is *built in*: each nucleus is a polygon defined
>   by its centre, so two centres = two polygons.
>
> Watershed is more flexible (any blob shape) but can over-segment.
> Polygon prior is more constrained (must be star-convex) but cannot
> over-segment by construction.

---

### Q24. *"How robust is your pipeline to image resolution / magnification?"*
> - **Classical**: parameters (min_area, opening disk radius, watershed
>   min_distance) are in absolute pixels, so they assume a particular
>   magnification. For different magnification we'd scale them
>   proportionally.
> - **Cellpose**: `diameter=None` auto-estimates per image — robust to
>   moderate magnification changes.
> - **StarDist**: assumes magnification roughly matches its training
>   data; for very different mag we'd resize the image first.
>
> All three of our cohorts use comparable magnification, so this
> wasn't a problem here.

---

### Q25. *"Could you run this on a whole-slide image (gigapixel)?"*
> Not directly — our images fit in memory. For a WSI we would:
> 1. Tile the slide into 1024-px patches with ~64 px overlap.
> 2. Run any of the three methods per tile.
> 3. Stitch instance masks back, resolving boundary nuclei via IoU
>    matching across tile borders.
> 4. Aggregate counts and morphometrics at the slide level.
>
> Cellpose has a built-in tiling helper. The classical pipeline would
> need a custom tiling layer (~50 lines of code).
