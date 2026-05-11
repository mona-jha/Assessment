#!/usr/bin/env bash
# =============================================================================
# run.sh -- One-shot reproduction script for the nucleus-detection pipeline
# =============================================================================
#
# Usage:
#   ./run.sh                 # full pipeline (setup + all 3 methods + analysis)
#   ./run.sh setup           # only create venv and install requirements
#   ./run.sh weights         # only download Cellpose & StarDist pretrained weights
#   ./run.sh classical       # only run the classical method
#   ./run.sh stardist        # only run StarDist
#   ./run.sh cellpose        # only run Cellpose
#   ./run.sh analysis        # only run cross-method comparison + figures + ppt
#   ./run.sh clean           # delete generated outputs (results/ presentation/slides.pptx)
#
# Author: Mona Kumari
# =============================================================================

set -euo pipefail

# ---------- Configuration ----------------------------------------------------
PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"
CELLPOSE_DIR="$HOME/.cellpose/models"
STARDIST_DIR="$HOME/.stardist/models/2D_versatile_he"

# Pretty colours (only when stdout is a terminal)
if [ -t 1 ]; then
    BLUE='\033[1;34m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'
    RED='\033[1;31m'; RESET='\033[0m'
else
    BLUE=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

step()    { echo -e "\n${BLUE}>>> $*${RESET}"; }
success() { echo -e "${GREEN}[OK] $*${RESET}"; }
warn()    { echo -e "${YELLOW}[WARN] $*${RESET}"; }
fail()    { echo -e "${RED}[FAIL] $*${RESET}"; exit 1; }

# ---------- Sub-commands -----------------------------------------------------

cmd_setup() {
    step "1. Creating virtual environment in ${VENV_DIR}"
    if [ ! -d "${VENV_DIR}" ]; then
        ${PYTHON} -m venv "${VENV_DIR}"
        success "Created ${VENV_DIR}"
    else
        success "Reusing existing ${VENV_DIR}"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

    step "2. Upgrading pip"
    pip install --quiet --upgrade pip

    step "3. Installing classical dependencies (requirements.txt)"
    pip install --quiet -r requirements.txt
    success "Classical deps installed"

    step "4. Installing deep-learning dependencies (requirements_deeplearning.txt)"
    pip install --quiet -r requirements_deeplearning.txt || \
        warn "DL install failed -- you can still run the classical method."
    success "Setup complete"
}

cmd_weights() {
    step "Downloading pretrained model weights (only if missing)"

    # ---- Cellpose v4 cpsam (~1.1 GB) ----
    if [ ! -f "${CELLPOSE_DIR}/cpsam" ]; then
        warn "Cellpose 'cpsam' not found at ${CELLPOSE_DIR}/cpsam"
        warn "Downloading large weights from Hugging Face (~1.1 GB)."
        mkdir -p "${CELLPOSE_DIR}"
        # Cellpose downloads on first model.eval() call. Trigger it explicitly:
        # shellcheck disable=SC1091
        source "${VENV_DIR}/bin/activate"
        ${PYTHON} -c "from cellpose import models; models.CellposeModel(gpu=False)" || \
            fail "Cellpose weight download failed -- check connectivity."
        success "Cellpose weights ready"
    else
        success "Cellpose weights already present (${CELLPOSE_DIR}/cpsam)"
    fi

    # ---- StarDist 2D_versatile_he (~5 MB) ----
    if [ ! -f "${STARDIST_DIR}/weights_best.h5" ]; then
        warn "StarDist '2D_versatile_he' not found at ${STARDIST_DIR}"
        mkdir -p "${STARDIST_DIR}"
        local base="https://github.com/stardist/stardist-models/releases/download/v0.1"
        for f in config.json thresholds.json weights_best.h5; do
            if [ ! -f "${STARDIST_DIR}/${f}" ]; then
                curl -fLsS "${base}/python_2D_versatile_he/${f}" -o "${STARDIST_DIR}/${f}" || \
                    fail "Failed to fetch ${f} -- check connectivity."
            fi
        done
        success "StarDist weights downloaded"
    else
        success "StarDist weights already present (${STARDIST_DIR})"
    fi
}

_activate_venv() {
    if [ ! -d "${VENV_DIR}" ]; then
        fail "Virtual env not found. Run: ./run.sh setup"
    fi
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
}

cmd_classical() {
    step "Running classical pipeline on all 50 images"
    _activate_venv
    mkdir -p results/classical
    ${PYTHON} code/01_run_segmentation.py --method classical 2>&1 | tee results/classical/run.log
    success "Classical: results/classical/{overlays,masks,per_image_stats.csv}"
}

cmd_stardist() {
    step "Running StarDist on all 50 images"
    _activate_venv
    mkdir -p results/stardist
    ${PYTHON} code/01_run_segmentation.py --method stardist 2>&1 | tee results/stardist/run.log
    success "StarDist: results/stardist/..."
}

cmd_cellpose() {
    step "Running Cellpose v4 (cpsam) on all 50 images (uses MPS if available)"
    _activate_venv
    mkdir -p results/cellpose
    ${PYTHON} code/01_run_segmentation.py --method cellpose 2>&1 | tee results/cellpose/run.log
    success "Cellpose: results/cellpose/..."
}

cmd_analysis() {
    step "Cross-method comparison (foreground IoU, count scatter)"
    _activate_venv
    ${PYTHON} code/02_compare_methods.py
    success "Wrote results/method_agreement.csv, results/per_image_all_methods.csv"

    step "Per-cohort summary CSV + 6 figures"
    ${PYTHON} code/03_make_report_figures.py
    success "Wrote results/figures/*.png and results/per_cohort_summary.csv"

    step "Building presentation (slides.pptx)"
    ${PYTHON} code/make_pptx.py
    success "Wrote presentation/slides.pptx"
}

cmd_clean() {
    step "Removing generated artefacts"
    rm -rf results/classical results/cellpose results/stardist
    rm -f  results/per_cohort_summary.csv results/per_image_all_methods.csv \
           results/method_agreement.csv
    rm -rf results/figures
    rm -f  presentation/slides.pptx
    success "Clean (kept doc/, code/, study/, report/, .venv/)"
}

cmd_all() {
    cmd_setup
    cmd_weights
    cmd_classical
    cmd_stardist
    cmd_cellpose
    cmd_analysis
    echo
    echo -e "${GREEN}=============================================================${RESET}"
    echo -e "${GREEN}Pipeline complete. Open these files to review:${RESET}"
    echo "  - results/per_cohort_summary.csv"
    echo "  - results/method_agreement.csv"
    echo "  - results/figures/*.png"
    echo "  - report/report.md"
    echo "  - presentation/slides.pptx"
    echo "  - study/README.md   (self-study guide)"
    echo -e "${GREEN}=============================================================${RESET}"
}

# ---------- Dispatch ---------------------------------------------------------
case "${1:-all}" in
    all)        cmd_all       ;;
    setup)      cmd_setup     ;;
    weights)    cmd_weights   ;;
    classical)  cmd_classical ;;
    stardist)   cmd_stardist  ;;
    cellpose)   cmd_cellpose  ;;
    analysis)   cmd_analysis  ;;
    clean)      cmd_clean     ;;
    *)
        echo "Usage: $0 {all|setup|weights|classical|stardist|cellpose|analysis|clean}"
        exit 2
        ;;
esac
