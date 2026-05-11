#!/usr/bin/env bash
# Build study/study_guide.pdf from the markdown files in study/.
# Requires: pandoc + xelatex (both already on this Mac).

set -euo pipefail
cd "$(dirname "$0")/../.."   # project root (tools/study_pdf -> repo root)

OUT=study/study_guide.pdf
HEADER=tools/study_pdf/_pandoc_header.tex

# Reading order from study/00_INDEX.md
ORDER=(
    study/00_overview.md
    study/01_he_staining.md
    study/09_morphometrics.md
    study/02_classical_pipeline.md
    study/03_stain_deconvolution.md
    study/04_thresholding_morphology.md
    study/05_watershed_instances.md
    study/06_cellpose.md
    study/07_stardist.md
    study/08_method_comparison.md
    study/10_results_interpretation.md
    study/11_codebase_walkthrough.md
    study/12_likely_questions.md
)

pandoc \
    --from=markdown+pipe_tables+tex_math_dollars+raw_tex+yaml_metadata_block \
    --to=pdf \
    --pdf-engine=xelatex \
    --toc --toc-depth=2 \
    --number-sections \
    --top-level-division=chapter \
    -V documentclass=report \
    -V geometry:margin=1in \
    -V mainfont="Helvetica Neue" \
    -V monofont="Menlo" \
    -V monofontoptions:Scale=0.85 \
    -V colorlinks=true \
    -V linkcolor=blue \
    -V urlcolor=blue \
    -V toccolor=black \
    -V title="Nucleus Detection \& Quantification" \
    -V author="Mona Kumari" \
    -V date="May 2026" \
    -H "${HEADER}" \
    "${ORDER[@]}" \
    -o "${OUT}"

echo "Wrote ${OUT}  ($(du -h "${OUT}" | cut -f1))"
