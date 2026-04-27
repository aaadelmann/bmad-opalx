#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[build_bmad] %s\n' "$*"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/install"
SRC_DIR="${INSTALL_DIR}/bmad-ecosystem-src"
EXTERNAL_SRC_DIR="${INSTALL_DIR}/bmad-external-packages-src"
BUILD_DIR="${INSTALL_DIR}/bmad-ecosystem"
BMAD_GIT_URL="${BMAD_GIT_URL:-https://github.com/bmad-sim/bmad-ecosystem.git}"
BMAD_GIT_REF="${BMAD_GIT_REF:-main}"
BMAD_EXTERNAL_GIT_URL="${BMAD_EXTERNAL_GIT_URL:-https://github.com/bmad-sim/bmad-external-packages.git}"
BMAD_EXTERNAL_GIT_REF="${BMAD_EXTERNAL_GIT_REF:-main}"
BMAD_JOBS="${BMAD_JOBS:-20}"
STAMP_FILE="${BUILD_DIR}/.build_stamp"
EXPECTED_EXES=(
  "${BUILD_DIR}/production/bin/lattice_geometry_example"
  "${BUILD_DIR}/production/bin/particle_track_example"
)

have_expected_exes() {
  local exe
  for exe in "${EXPECTED_EXES[@]}"; do
    [[ -x "${exe}" ]] || return 1
  done
  return 0
}

write_build_stamp() {
  cat > "${STAMP_FILE}" <<EOF
BMAD_SRC_REV=${BMAD_SRC_REV}
BMAD_EXTERNAL_REV=${BMAD_EXTERNAL_REV}
EOF
}

log "root directory: ${ROOT_DIR}"
log "install directory: ${INSTALL_DIR}"
log "source directory: ${SRC_DIR}"
log "external packages source directory: ${EXTERNAL_SRC_DIR}"
log "build directory: ${BUILD_DIR}"
log "Bmad git URL: ${BMAD_GIT_URL}"
log "Bmad git ref: ${BMAD_GIT_REF}"
log "Bmad external packages git URL: ${BMAD_EXTERNAL_GIT_URL}"
log "Bmad external packages git ref: ${BMAD_EXTERNAL_GIT_REF}"
log "Bmad parallel build jobs: ${BMAD_JOBS}"

mkdir -p "${INSTALL_DIR}"

if [[ ! -d "${SRC_DIR}/.git" ]]; then
  log "cloning Bmad source tree"
  git clone --branch "${BMAD_GIT_REF}" --single-branch "${BMAD_GIT_URL}" "${SRC_DIR}"
else
  log "updating existing cloned source tree"
  git -C "${SRC_DIR}" pull --ff-only origin "${BMAD_GIT_REF}"
fi

if [[ ! -d "${EXTERNAL_SRC_DIR}/.git" ]]; then
  log "cloning Bmad external packages source tree"
  git clone --branch "${BMAD_EXTERNAL_GIT_REF}" --single-branch "${BMAD_EXTERNAL_GIT_URL}" "${EXTERNAL_SRC_DIR}"
else
  log "updating existing cloned external packages source tree"
  git -C "${EXTERNAL_SRC_DIR}" pull --ff-only origin "${BMAD_EXTERNAL_GIT_REF}"
fi

BMAD_SRC_REV="$(git -C "${SRC_DIR}" rev-parse HEAD)"
BMAD_EXTERNAL_REV="$(git -C "${EXTERNAL_SRC_DIR}" rev-parse HEAD)"
log "Bmad source revision: ${BMAD_SRC_REV}"
log "Bmad external revision: ${BMAD_EXTERNAL_REV}"

if [[ -f "${STAMP_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${STAMP_FILE}"
else
  BMAD_SRC_REV_OLD=""
  BMAD_EXTERNAL_REV_OLD=""
fi

SOURCE_REVISIONS_MATCH=false
if [[ "${BMAD_SRC_REV}" == "${BMAD_SRC_REV_OLD:-}" && "${BMAD_EXTERNAL_REV}" == "${BMAD_EXTERNAL_REV_OLD:-}" ]]; then
  SOURCE_REVISIONS_MATCH=true
fi

if ${SOURCE_REVISIONS_MATCH} && have_expected_exes; then
  log "existing build matches current source revisions; skipping rebuild"
else
  if ${SOURCE_REVISIONS_MATCH} && [[ -d "${BUILD_DIR}" ]]; then
    log "source revisions unchanged; reusing existing staged tree and resuming build"
  else
    log "refreshing build tree"
    rm -rf "${BUILD_DIR}"
    cp -R "${SRC_DIR}" "${BUILD_DIR}"

    log "staging Bmad external packages into build tree"
    shopt -s dotglob nullglob
    for item in "${EXTERNAL_SRC_DIR}"/*; do
      if [[ "$(basename "${item}")" == "README.md" ]]; then
        continue
      fi
      cp -R "${item}" "${BUILD_DIR}/"
    done
    shopt -u dotglob nullglob
  fi

  log "applying local build/config patches"
  python3 "${SCRIPT_DIR}/patch_bmad_build.py" "${BUILD_DIR}"
  python3 "${SCRIPT_DIR}/fix_lapack_paths.py" "${BUILD_DIR}"
  log "patched dist_prefs, build_flags_config, Master.cmake, and lapack/acc_build_lapack"
  log "starting dist_build_production (this phase can stay quiet for a while)"
  (
    cd "${BUILD_DIR}"
    log "initializing Bmad distribution environment"
    set +eu
    source util/dist_source_me > /dev/null
    set -eu
    export ACC_SET_GMAKE_JOBS="${BMAD_JOBS}"
    log "distribution environment initialized: DIST_BASE_DIR=${DIST_BASE_DIR}"
    log "running dist_build_production with ACC_SET_GMAKE_JOBS=${ACC_SET_GMAKE_JOBS}"
    cd util
    ./dist_build_production
  )

  log "dist_build_production completed"
  write_build_stamp
fi

log "checking expected benchmark executables"
for exe in "${EXPECTED_EXES[@]}"; do
  if [[ ! -x "${exe}" ]]; then
    log "missing expected executable: ${exe}"
    exit 1
  fi
  log "found ${exe}"
done

log "Bmad build completed under ${BUILD_DIR}/production"
