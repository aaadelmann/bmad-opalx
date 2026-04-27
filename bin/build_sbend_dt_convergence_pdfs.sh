#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[build_sbend_dt_pdfs] %s\n' "$*"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FIG_DIR="${ROOT_DIR}/install/examples/bend_compare/studies/sbend_dt_convergence/figures"

log "figure directory: ${FIG_DIR}"
cd "${FIG_DIR}"

log "building sbend_dt_convergence.pdf"
latexmk -pdf sbend_dt_convergence.tex
log "building sbend_dt_discrepancy.pdf"
latexmk -pdf sbend_dt_discrepancy.tex
log "building sbend_dt_l2_error.pdf"
latexmk -pdf sbend_dt_l2_error.tex
log "wrote PDFs under ${FIG_DIR}"
