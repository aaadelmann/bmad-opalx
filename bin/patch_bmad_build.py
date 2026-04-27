#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def patch_file(path: Path, transform, label: str) -> None:
    print(f"[build_bmad] patching {label}: {path}", flush=True)
    text = path.read_text()
    new_text = transform(text)
    path.write_text(new_text)
    print(f"[build_bmad] patched {label}", flush=True)


def patch_dist_prefs(text: str) -> str:
    text = text.replace('export ACC_PLOT_PACKAGE="plplot"', 'export ACC_PLOT_PACKAGE="none"')
    text = text.replace('export ACC_ENABLE_SHARED_ONLY="Y"', 'export ACC_ENABLE_SHARED_ONLY="N"')
    return text


def patch_build_flags_config(text: str) -> str:
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
    return text


def patch_master_cmake(text: str) -> str:
    needle = '# If we use system HDF5 libraries, search for include directories\nfind_package(HDF5 COMPONENTS Fortran HL)\n'
    replacement = '# If we use system HDF5 libraries, search for include directories.\n# Some HDF5 package configs reference ZLIB::ZLIB without importing it first.\nfind_package(ZLIB)\nfind_package(HDF5 COMPONENTS Fortran HL)\n'
    if 'find_package(ZLIB)' not in text and needle in text:
        text = text.replace(needle, replacement)
    return text


def patch_lapack_acc_build(text: str) -> str:
    text = text.replace('LAPACKLIB    = lib/liblapack.a', 'LAPACKLIB    = ../lib/liblapack.a')
    text = text.replace('TMGLIB       = lib/libtmglib.a', 'TMGLIB       = ../lib/libtmglib.a')
    text = text.replace('LAPACKELIB   = lib/liblapacke.a ', 'LAPACKELIB   = ../lib/liblapacke.a ')
    return text


def patch_noplot_interface(text: str) -> str:
    if 'subroutine qp_wait_to_flush_basic' in text:
        return text
    marker = '\nsubroutine qp_end_basic ()\n\nend subroutine qp_end_basic\n\n#endif\n\nend module\n'
    addition = '''
subroutine qp_wait_to_flush_basic(wait)
implicit none
logical, intent(in) :: wait
end subroutine qp_wait_to_flush_basic

subroutine qp_end_basic ()

end subroutine qp_end_basic

#endif

end module
'''
    if marker not in text:
        raise SystemExit('could not locate qp_end_basic marker in noplot_interface.f90')
    return text.replace(marker, '\n' + addition)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: patch_bmad_build.py <build-dir>')

    root = Path(sys.argv[1]).resolve()
    print(f"[build_bmad] patch root: {root}", flush=True)
    patch_file(root / 'util' / 'dist_prefs', patch_dist_prefs, 'dist_prefs')
    patch_file(root / 'util' / 'build_flags_config', patch_build_flags_config, 'build_flags_config')
    patch_file(root / 'util' / 'Master.cmake', patch_master_cmake, 'Master.cmake')
    patch_file(root / 'lapack' / 'acc_build_lapack', patch_lapack_acc_build, 'lapack/acc_build_lapack')
    patch_file(root / 'sim_utils' / 'plot' / 'noplot_interface.f90', patch_noplot_interface, 'sim_utils/plot/noplot_interface.f90')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
