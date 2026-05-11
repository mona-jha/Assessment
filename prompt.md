# Digital Pathology — Nucleus Detection & Quantification (Syngene/BBRC Task)

## 1. Context & Goal
You are continuing a Syngene/BBRC Digital Pathology assessment. The task is to
**detect and quantify every nucleus** in 50 Hematoxylin & Eosin (H&E) stained
histopathology images, then produce results, data analysis, and a clear write-up
suitable for a team presentation.

Source instruction file: `doc/instruction.txt`
Source images: `doc/Assessment/`

## 2. Dataset
Located at `/Users/vn59a0h/Desktop/task/doc/Assessment/` — 5 sub-folders, one per
cancer type, each containing 10 PNG images (`Image1.png` … `Image10.png`).

| Folder      | Cancer Type                                              | # Images |
|-------------|----------------------------------------------------------|----------|
| `BRC/`      | Breast Carcinoma                                         | 10       |
| `CRC/`      | Colorectal Carcinoma                                     | 10       |
| `HCC/`      | Hepato-Cellular Carcinoma                                | 10       |
| `NSCLC_AD/` | Non-Small Cell Lung Carcinoma — Adenocarcinoma           | 10       |
| `NSCLC_SCC/`| Non-Small Cell Lung Carcinoma — Squamous Cell Carcinoma  | 10       |

Images are RGB H&E micrographs (~560 × 480 px range, varying). Nuclei appear as
dark blue/purple ellipsoidal blobs on a pink/eosin background. **No ground-truth
annotations are provided.**

## 3. Deliverables (produce all of these)
Create everything inside `/Users/vn59a0h/Desktop/task/output/` unless told
otherwise. Required artefacts:

1. **`src/` — runnable Python pipeline**
   - `nucleus_pipeline.py` (or notebook): end-to-end script that loads every
     image, segments nuclei, counts them, saves overlays + per-image stats.
   - `requirements.txt` listing dependencies.
   - Reproducible: a single command (e.g. `python src/nucleus_pipeline.py`)
     should regenerate every output.

2. **`overlays/<COHORT>/ImageN_overlay.png`** — each input image with detected
   nuclei outlined (and/or centroid-marked) plus the count printed on the image.

3. **`masks/<COHORT>/ImageN_mask.png`** — binary / instance segmentation mask.

4. **`results/per_image_stats.csv`** with at least these columns:
   `cohort, image, nucleus_count, mean_area_px, median_area_px,
    std_area_px, mean_eccentricity, mean_solidity, density_per_megapixel`.

5. **`results/per_cohort_summary.csv`** — aggregated mean ± std per cohort
   (count, area, density, etc.).

6. **`results/figures/`** — at minimum:
   - Box/violin plot of nucleus count per cohort.
   - Box plot of nucleus area distribution per cohort.
   - Bar chart of mean density (nuclei per megapixel) per cohort.
   - 1 qualitative grid: original | H-channel | mask | overlay for one
     representative image from each cohort (so 5 rows × 4 cols).

7. **`report/report.md` (or `.pdf`)** — concise technical write-up covering:
   - Problem statement and dataset description.
   - Approach rationale (why the chosen method).
   - Step-by-step methodology with parameters.
   - Quantitative results (tables + figures).
   - Cross-cohort comparison and biological/visual interpretation.
   - Limitations and possible improvements (e.g. StarDist, HoVer-Net,
     Cellpose for production use).

8. **`presentation/slides.md`** (Marp / reveal.js / plain markdown is fine)
   — 8–12 slides covering: objective, data, pipeline diagram, sample
   qualitative results, quantitative results, cohort comparison, limitations,
   future work.

## 4. Recommended Approach (default — implement this unless I say otherwise)

Use a **classical image-processing pipeline first** (fast, transparent, no
training data needed). Optionally add a deep-learning baseline if time permits.

### 4.1 Classical pipeline (primary)
1. **Load** image as RGB (`skimage.io.imread`); record shape.
2. **Stain deconvolution** with `skimage.color.rgb2hed` → take the
   **Hematoxylin (H) channel** (nuclei-specific). Normalise to [0, 1].
3. **Pre-processing**: small Gaussian blur (`sigma≈1`) to reduce noise.
4. **Thresholding**: Otsu on the H channel (or `threshold_local` for
   uneven illumination). Invert if needed so nuclei = foreground.
5. **Morphology**: binary opening (disk r=2) to remove specks, fill small
   holes (`ndi.binary_fill_holes`). Remove objects smaller than ~30 px².
6. **Touching-nuclei separation**: distance transform + `peak_local_max`
   → markers → **watershed** (`skimage.segmentation.watershed`) on the
   negated distance map. Tune `min_distance` (e.g. 6–10 px).
7. **Labelling & filtering**: `skimage.measure.label` + `regionprops`.
   Reject regions outside plausible nucleus bounds (e.g. area 30–2000 px²,
   solidity > 0.7) — tune empirically.
8. **Quantify** per image: count, area stats, eccentricity, solidity,
   density per megapixel (`count / (H*W/1e6)`).
9. **Visualise**: draw boundaries with `skimage.segmentation.find_boundaries`
   or `mark_boundaries`; annotate the count in the top-left corner.

### 4.2 Optional deep-learning baseline (do only if specifically asked)
Use a pre-trained **StarDist** (`stardist.models.StarDist2D.from_pretrained
("2D_versatile_he")`) or **Cellpose** (`model_type="nuclei"`) — both work
out-of-the-box on H&E. Compare counts and qualitative masks against the
classical pipeline.

## 5. Engineering Requirements
- Python 3.10+. Libraries: `numpy`, `scipy`, `scikit-image`, `opencv-python`,
  `matplotlib`, `pandas`, `tqdm`. (Add `stardist`/`cellpose` only if the DL
  baseline is requested.)
- Pipeline must be **deterministic** (set seeds where applicable).
- Vectorise / loop cleanly over the 50 images using `pathlib.Path.rglob`.
- Tune ONE shared parameter set across all cohorts; if cohort-specific tuning
  is needed, document why and how.
- Keep functions small: `load_image`, `segment_nuclei`, `extract_features`,
  `make_overlay`, `process_one`, `main`.
- Save outputs under the directory tree described in §3 — create folders
  with `pathlib`, do NOT hard-code absolute paths beyond the project root.

## 6. Reporting Requirements
- Report nucleus counts and morphometric stats with mean ± std per cohort.
- Discuss qualitative differences between cohorts (e.g. lymphocyte-rich CRC
  margins, hepatocyte size in HCC, glandular patterns in BRC, etc.).
- Be honest about limitations: no GT → counts are estimates; over/under-
  segmentation in dense regions; staining variability.
- Suggest validation paths: manual point-annotations on a few crops, or
  comparison with StarDist/HoVer-Net.

## 7. Execution Plan (follow in order)
1. Confirm input folder structure and sample one image from each cohort to
   sanity-check appearance.
2. Set up `output/` directory tree and `requirements.txt`.
3. Implement the classical pipeline in `src/nucleus_pipeline.py`.
4. Run on a single image; visually verify the overlay before batch-processing.
5. Tune parameters (size limits, watershed `min_distance`) using 1–2 images
   per cohort.
6. Run on all 50 images; write CSVs and overlays.
7. Generate aggregate figures.
8. Write `report.md` and `slides.md`.
9. Final pass: print a short summary table to stdout showing per-cohort
   nucleus-count mean ± std and total nuclei detected.

## 8. Acceptance Criteria
- All 50 overlays + masks exist and look visually reasonable (nuclei
  outlined, no obvious wholesale failures).
- `per_image_stats.csv` has exactly 50 rows.
- `per_cohort_summary.csv` has exactly 5 rows.
- Report and slides are coherent, reference the figures, and discuss results.
- Pipeline re-runs end-to-end with one command.

## 9. What NOT to do
- Do not invent ground-truth annotations or fabricate accuracy/F1 numbers
  (no GT exists). Only report intrinsic statistics and qualitative checks.
- Do not skip cohorts or images.
- Do not commit huge binary outputs into source control assumptions —
  just write them to `output/`.
- Do not over-engineer: a clean classical pipeline that works is better
  than a half-finished deep-learning attempt.

## 10. When You Start
Begin by reading this prompt fully, then:
- list `doc/Assessment/` to confirm 5 × 10 images,
- create the `output/` skeleton,
- implement and run the pipeline,
- and produce the deliverables in §3.

Ask me before deviating from the recommended approach in §4.
