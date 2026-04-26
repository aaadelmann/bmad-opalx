#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/install"
EXAMPLE_DIR="${INSTALL_DIR}/examples/bend_compare"
BMAD_ROOT="${BMAD_ROOT:-${INSTALL_DIR}/bmad-ecosystem}"
BIN_DIR="${BMAD_ROOT}/production/bin"

"${SCRIPT_DIR}/prepare_workspace.py" >/dev/null

if [[ ! -x "${BIN_DIR}/lattice_geometry_example" ]]; then
  echo "Missing executable: ${BIN_DIR}/lattice_geometry_example" >&2
  exit 1
fi
if [[ ! -x "${BIN_DIR}/particle_track_example" ]]; then
  echo "Missing executable: ${BIN_DIR}/particle_track_example" >&2
  exit 1
fi

mkdir -p "${EXAMPLE_DIR}/output"
cd "${EXAMPLE_DIR}"

run_case() {
  local stem="$1"
  "${BIN_DIR}/lattice_geometry_example" "${stem}_geometry.in"
  mv reference_frame.dat "output/${stem}_reference_frame.dat"
  mv element_frame.dat "output/${stem}_element_frame.dat"
  cp "${stem}_track.init" particle_track.init
  "${BIN_DIR}/particle_track_example"
  rm -f particle_track.init
}

run_case sbend_proton_590MeV_45deg
run_case rbend_electron_1GeV_45deg

echo "Wrote Bmad bend comparison outputs under ${EXAMPLE_DIR}/output"
