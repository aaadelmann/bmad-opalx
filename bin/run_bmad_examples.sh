#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[run_bmad_examples] %s\n' "$*"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/install"
EXAMPLE_DIR="${INSTALL_DIR}/examples/bend_compare"
OUTPUT_DIR="${EXAMPLE_DIR}/output"
BMAD_ROOT="${BMAD_ROOT:-${INSTALL_DIR}/bmad-ecosystem}"
BIN_DIR="${BMAD_ROOT}/production/bin"

log "root directory: ${ROOT_DIR}"
log "example directory: ${EXAMPLE_DIR}"
log "output directory: ${OUTPUT_DIR}"
log "Bmad root: ${BMAD_ROOT}"
log "preparing workspace inputs"
"${SCRIPT_DIR}/prepare_workspace.py" >/dev/null

if [[ ! -x "${BIN_DIR}/lattice_geometry_example" ]]; then
  echo "Missing executable: ${BIN_DIR}/lattice_geometry_example" >&2
  exit 1
fi
if [[ ! -x "${BIN_DIR}/particle_track_example" ]]; then
  echo "Missing executable: ${BIN_DIR}/particle_track_example" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
cd "${EXAMPLE_DIR}"

run_case() {
  local stem="$1"
  log "running geometry export for ${stem}"
  "${BIN_DIR}/lattice_geometry_example" "${stem}_geometry.in"
  mv reference_frame.dat "${OUTPUT_DIR}/${stem}_reference_frame.dat"
  mv element_frame.dat "${OUTPUT_DIR}/${stem}_element_frame.dat"
  log "running tracking export for ${stem}"
  cp "${stem}_track.init" particle_track.init
  "${BIN_DIR}/particle_track_example"
  rm -f particle_track.init
  log "finished ${stem}"
}

run_case sbend_proton_590MeV_45deg
run_case rbend_electron_1GeV_45deg

log "wrote Bmad bend comparison outputs under ${OUTPUT_DIR}"
