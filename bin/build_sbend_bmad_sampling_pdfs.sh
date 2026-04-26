#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FIG_DIR="${ROOT_DIR}/install/examples/bend_compare/studies/sbend_bmad_sampling/figures"
cd "${FIG_DIR}"
latexmk -pdf sbend_bmad_sampling_convergence.tex
latexmk -pdf sbend_bmad_sampling_discrepancy.tex
