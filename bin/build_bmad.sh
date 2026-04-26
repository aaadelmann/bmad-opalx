#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${ROOT_DIR}/install"
SRC_DIR="${INSTALL_DIR}/bmad-ecosystem-src"
BUILD_DIR="${INSTALL_DIR}/bmad-ecosystem"
BMAD_GIT_URL="${BMAD_GIT_URL:-https://github.com/bmad-sim/bmad-ecosystem.git}"
BMAD_GIT_REF="${BMAD_GIT_REF:-main}"

mkdir -p "${INSTALL_DIR}"

if [[ ! -d "${SRC_DIR}/.git" ]]; then
  git clone --branch "${BMAD_GIT_REF}" --single-branch "${BMAD_GIT_URL}" "${SRC_DIR}"
fi

rm -rf "${BUILD_DIR}"
cp -R "${SRC_DIR}" "${BUILD_DIR}"

BUILD_DIR_ENV="${BUILD_DIR}" python3 - <<'PY'
import os
from pathlib import Path

root = Path(os.environ['BUILD_DIR_ENV'])

path = root / 'util' / 'dist_prefs'
text = path.read_text()
text = text.replace('export ACC_PLOT_PACKAGE="plplot"', 'export ACC_PLOT_PACKAGE="none"')
text = text.replace('export ACC_ENABLE_SHARED_ONLY="Y"', 'export ACC_ENABLE_SHARED_ONLY="N"')
path.write_text(text)

path = root / 'util' / 'build_flags_config'
text = path.read_text()
old = '''else
    export PLOT_LINK_LIBS="pgplot"
    export PLOT_LINK_FLAGS="-lpgplot"
fi
'''
new = '''elif [ "${ACC_PLOT_PACKAGE}" == "pgplot" ] ; then
    export PLOT_LINK_LIBS="pgplot"
    export PLOT_LINK_FLAGS="-lpgplot"
else
    export PLOT_LINK_LIBS=""
    export PLOT_LINK_FLAGS=""
fi
'''
if 'export PLOT_LINK_LIBS=""' not in text and old in text:
    text = text.replace(old, new)
path.write_text(text)

path = root / 'util' / 'Master.cmake'
text = path.read_text()
needle = '# If we use system HDF5 libraries, search for include directories\nfind_package(HDF5 COMPONENTS Fortran HL)\n'
replacement = '# If we use system HDF5 libraries, search for include directories.\n# Some HDF5 package configs reference ZLIB::ZLIB without importing it first.\nfind_package(ZLIB)\nfind_package(HDF5 COMPONENTS Fortran HL)\n'
if 'find_package(ZLIB)' not in text and needle in text:
    text = text.replace(needle, replacement)
path.write_text(text)
PY

(
  cd "${BUILD_DIR}/util"
  ./dist_build_production
)

echo "Bmad build completed under ${BUILD_DIR}/production"
