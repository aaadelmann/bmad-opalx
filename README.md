# bmad-opalx

Script-only workspace for Bmad vs OPALX bend benchmarks.

The repository keeps only the driver scripts. All cloned source trees, builds,
benchmark inputs, and generated outputs live under `install/`, which is ignored.

## Requirements

- `git`
- a working C/Fortran toolchain compatible with Bmad
- `cmake`
- `python3`
- `latexmk` and a TeX installation with `pgfplots`
- OPALX built separately

The scripts assume the OPALX-side Python environment:
- `/Users/adelmann/git/opalx/.venv-h6`

## Repository layout

Repo-owned content:
- `bin/build_bmad.sh`
  - clone upstream Bmad, apply the local build patches, build under `install/`
- `bin/prepare_workspace.py`
  - generate the benchmark decks and working directories under `install/examples/`
- `bin/run_bmad_examples.sh`
  - run the Bmad bend benchmarks
- `bin/run_opalx_examples.sh`
  - run the matching OPALX bend benchmarks
- `bin/generate_bend_code_comparison.py`
  - generate comparison tables and the TikZ figure
- `bin/build_comparison_pdf.sh`
  - compile the main comparison PDF
- `bin/run_sbend_dt_convergence.py`
  - run the SBEND timestep study
- `bin/build_sbend_dt_convergence_pdfs.sh`
  - compile the SBEND timestep-study PDFs
- `bin/run_sbend_bmad_sampling_convergence.py`
  - run the Bmad SBEND sampling study
- `bin/build_sbend_bmad_sampling_pdfs.sh`
  - compile the Bmad sampling-study PDFs

Generated content:
- `install/bmad-ecosystem-src/`
  - cloned upstream Bmad source tree
- `install/bmad-ecosystem/`
  - patched local build tree and Bmad installation
- `install/examples/`
  - generated benchmark inputs, outputs, CSVs, and PDFs

## Local Bmad patching

`bin/build_bmad.sh` applies three local build/configuration patches to the cloned
Bmad tree before building:

1. `util/dist_prefs`
   - set `ACC_PLOT_PACKAGE="none"`
   - set `ACC_ENABLE_SHARED_ONLY="N"`
2. `util/build_flags_config`
   - add an explicit no-plot branch so no plot libraries are linked
3. `util/Master.cmake`
   - add `find_package(ZLIB)` before `find_package(HDF5 ...)`

These are build-system patches only. No Bmad bend-model physics is modified.

## OPALX executable

The OPALX runner expects `OPALX_EXE_PATH` to point either to:
- the OPALX executable itself, or
- the directory containing `opalx`

Example used locally:

```bash
export OPALX_EXE_PATH=~/opalx/build/src
```

If you want the exact path used during local testing on this machine:

```bash
export OPALX_EXE_PATH=/Users/adelmann/git/opalx/build/src
```

## 1. Get and build Bmad

From the repository root:

```bash
cd /Users/adelmann/git/bmad-opalx
./bin/build_bmad.sh
```

This will:
- clone `https://github.com/bmad-sim/bmad-ecosystem.git` into `install/bmad-ecosystem-src/`
- copy it to `install/bmad-ecosystem/`
- patch the local build tree
- build Bmad under `install/bmad-ecosystem/production/`

You can override the upstream and branch/tag with:

```bash
BMAD_GIT_URL=<repo-url> BMAD_GIT_REF=<branch-or-tag> ./bin/build_bmad.sh
```

## 2. Run the main bend comparison

### Run the Bmad benchmarks

```bash
./bin/run_bmad_examples.sh
```

This writes Bmad outputs under:
- `install/examples/bend_compare/output/`

### Run the matching OPALX benchmarks

```bash
OPALX_EXE_PATH=~/opalx/build/src ./bin/run_opalx_examples.sh
```

This writes OPALX outputs under:
- `install/examples/bend_compare/data/`

### Generate the comparison tables and TikZ source

```bash
./bin/generate_bend_code_comparison.py
```

This writes under:
- `install/examples/bend_compare/figures/`

Main outputs:
- `bend_code_comparison_summary.csv`
- `bend_code_comparison.tex`

### Build the comparison PDF

```bash
./bin/build_comparison_pdf.sh
```

Main PDF:
- `install/examples/bend_compare/figures/bend_code_comparison.pdf`

## 3. Run the SBEND timestep study

### Execute the study

```bash
OPALX_EXE_PATH=~/opalx/build/src ./bin/run_sbend_dt_convergence.py
```

This writes under:
- `install/examples/bend_compare/studies/sbend_dt_convergence/data/`
- `install/examples/bend_compare/studies/sbend_dt_convergence/figures/`

Main data products:
- `sbend_dt_convergence_summary.csv`
- per-`dt` trajectory/error CSVs

### Build the timestep-study PDFs

```bash
./bin/build_sbend_dt_convergence_pdfs.sh
```

Generated PDFs:
- `sbend_dt_convergence.pdf`
- `sbend_dt_discrepancy.pdf`
- `sbend_dt_l2_error.pdf`

## 4. Run the Bmad SBEND sampling study

### Execute the study

```bash
./bin/run_sbend_bmad_sampling_convergence.py
```

This writes under:
- `install/examples/bend_compare/studies/sbend_bmad_sampling/data/`
- `install/examples/bend_compare/studies/sbend_bmad_sampling/figures/`

### Build the sampling-study PDFs

```bash
./bin/build_sbend_bmad_sampling_pdfs.sh
```

Generated PDFs:
- `sbend_bmad_sampling_convergence.pdf`
- `sbend_bmad_sampling_discrepancy.pdf`

## 5. Full workflow

If everything is already built on the OPALX side:

```bash
cd /Users/adelmann/git/bmad-opalx
./bin/build_bmad.sh
./bin/run_bmad_examples.sh
OPALX_EXE_PATH=~/opalx/build/src ./bin/run_opalx_examples.sh
./bin/generate_bend_code_comparison.py
./bin/build_comparison_pdf.sh
OPALX_EXE_PATH=~/opalx/build/src ./bin/run_sbend_dt_convergence.py
./bin/build_sbend_dt_convergence_pdfs.sh
./bin/run_sbend_bmad_sampling_convergence.py
./bin/build_sbend_bmad_sampling_pdfs.sh
```

## Output locations

Main comparison:
- `install/examples/bend_compare/output/`
- `install/examples/bend_compare/data/`
- `install/examples/bend_compare/figures/`

SBEND timestep study:
- `install/examples/bend_compare/studies/sbend_dt_convergence/data/`
- `install/examples/bend_compare/studies/sbend_dt_convergence/figures/`

Bmad sampling study:
- `install/examples/bend_compare/studies/sbend_bmad_sampling/data/`
- `install/examples/bend_compare/studies/sbend_bmad_sampling/figures/`
