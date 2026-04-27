#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[build_comparison_pdf] %s\n' "$*"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FIG_DIR="${ROOT_DIR}/install/examples/bend_compare/figures"
PDF_PATH="${FIG_DIR}/bend_code_comparison.pdf"

log "figure directory: ${FIG_DIR}"
log "building bend_code_comparison.tex"
cd "${FIG_DIR}"
latexmk -pdf bend_code_comparison.tex
log "wrote ${PDF_PATH}"
