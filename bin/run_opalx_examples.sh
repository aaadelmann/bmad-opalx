#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/install"
EXAMPLE_DIR="${INSTALL_DIR}/examples/bend_compare"

"${SCRIPT_DIR}/prepare_workspace.py" >/dev/null

: "${OPALX_EXE_PATH:?Set OPALX_EXE_PATH to the OPALX executable or its containing directory, e.g. ~/opalx/build/src}"

if [[ -d "${OPALX_EXE_PATH}" ]]; then
  OPALX_BIN="${OPALX_EXE_PATH%/}/opalx"
else
  OPALX_BIN="${OPALX_EXE_PATH}"
fi

if [[ ! -x "${OPALX_BIN}" ]]; then
  echo "Missing executable: ${OPALX_BIN}" >&2
  exit 1
fi

mkdir -p "${EXAMPLE_DIR}/data"
cd "${EXAMPLE_DIR}"

run_case() {
  local input_file="$1"
  local stem="${input_file%.in}"
  rm -f "${stem}.h5" "${stem}.stat"
  "${OPALX_BIN}" "${input_file}" --info 1 >/dev/null
}

run_case sbend_proton_590MeV_45deg_opalx.in
run_case rbend_electron_1GeV_45deg_opalx.in

echo "Wrote OPALX bend comparison outputs under ${EXAMPLE_DIR}/data"
