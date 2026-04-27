#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fix_lapack_paths.py <build-dir>")

    root = Path(sys.argv[1]).resolve()
    path = root / "lapack" / "acc_build_lapack"
    text = path.read_text()

    marker = 'EOF\n\n    if [[ $ACC_COMPILER_TOOLSET == mingw* ]] ; then\n'
    block = '''EOF

    python3 - <<PY2
from pathlib import Path
work_dir = Path("${WORK_DIR}")
path = Path("make.inc")
text = path.read_text()
replacements = {
    'BLASLIB      = ../../lib/libblas.a': f'BLASLIB      = {work_dir / "lib" / "libblas.a"}',
    'CBLASLIB     = ../../lib/libcblas.a': f'CBLASLIB     = {work_dir / "lib" / "libcblas.a"}',
    'LAPACKLIB    = ../lib/liblapack.a': f'LAPACKLIB    = {work_dir / "lib" / "liblapack.a"}',
    'TMGLIB       = ../lib/libtmglib.a': f'TMGLIB       = {work_dir / "lib" / "libtmglib.a"}',
    'LAPACKELIB   = ../lib/liblapacke.a ': f'LAPACKELIB   = {work_dir / "lib" / "liblapacke.a"} ',
    'LAPACKLIB    = lib/liblapack.a': f'LAPACKLIB    = {work_dir / "lib" / "liblapack.a"}',
    'TMGLIB       = lib/libtmglib.a': f'TMGLIB       = {work_dir / "lib" / "libtmglib.a"}',
    'LAPACKELIB   = lib/liblapacke.a ': f'LAPACKELIB   = {work_dir / "lib" / "liblapacke.a"} ',
}
for old, new in replacements.items():
    text = text.replace(old, new)
path.write_text(text)
PY2

    if [[ $ACC_COMPILER_TOOLSET == mingw* ]] ; then
'''

    if 'work_dir = Path("${WORK_DIR}")' not in text:
        if marker not in text:
            raise SystemExit("could not find make.inc generation marker in acc_build_lapack")
        text = text.replace(marker, block)
        path.write_text(text)
        print(f"[build_bmad] patched lapack absolute path rewrite into {path}", flush=True)
    else:
        print(f"[build_bmad] lapack absolute path rewrite already present in {path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
