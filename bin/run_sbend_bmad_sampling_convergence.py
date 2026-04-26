#!/Users/adelmann/git/opalx/.venv-h6/bin/python
"""Study the Bmad SBEND geometry-export sampling error against the analytic arc."""

from __future__ import annotations

import math
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INSTALL_DIR = ROOT / 'install'
EXAMPLE_DIR = INSTALL_DIR / 'examples' / 'bend_compare'
STUDY_DIR = EXAMPLE_DIR / 'studies' / 'sbend_bmad_sampling'
DATA_DIR = STUDY_DIR / 'data'
FIG_DIR = STUDY_DIR / 'figures'
ANGLE = math.pi / 4.0
ARC_LENGTH = 1.0
RADIUS = ARC_LENGTH / ANGLE
N_STEPS_VALUES = [5, 10, 20, 40, 80, 160, 320, 640]
CURVE_STEPS = [5, 10, 20, 40, 80]
FINE_SAMPLES = 4001


def prepare_dirs() -> None:
    for directory in [DATA_DIR, FIG_DIR]:
        if directory.exists():
            import shutil
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def analytic_curve(u: pd.Series) -> pd.DataFrame:
    phi = ANGLE * u
    return pd.DataFrame({
        'u': u,
        'z': RADIUS * phi.map(math.sin),
        'x': -RADIUS * phi.map(lambda value: 1.0 - math.cos(value)),
    })


def sampled_curve(n_steps: int) -> pd.DataFrame:
    u = pd.Series([i / (n_steps - 1) for i in range(n_steps)], dtype=float)
    return analytic_curve(u)


def polyline_error_curve(n_steps: int, fine_samples: int = FINE_SAMPLES) -> pd.DataFrame:
    nodes = sampled_curve(n_steps)
    u_fine = pd.Series([i / (fine_samples - 1) for i in range(fine_samples)], dtype=float)
    exact = analytic_curve(u_fine)

    seg_count = n_steps - 1
    seg_pos = u_fine * seg_count
    seg_ix = seg_pos.map(lambda v: min(seg_count - 1, max(0, int(math.floor(v)))) )
    alpha = seg_pos - seg_ix

    z0 = nodes['z'].iloc[seg_ix.to_numpy()].reset_index(drop=True)
    x0 = nodes['x'].iloc[seg_ix.to_numpy()].reset_index(drop=True)
    z1 = nodes['z'].iloc[(seg_ix + 1).to_numpy()].reset_index(drop=True)
    x1 = nodes['x'].iloc[(seg_ix + 1).to_numpy()].reset_index(drop=True)

    z_lin = z0 + alpha.reset_index(drop=True) * (z1 - z0)
    x_lin = x0 + alpha.reset_index(drop=True) * (x1 - x0)
    error = ((z_lin - exact['z']) ** 2 + (x_lin - exact['x']) ** 2).map(math.sqrt)

    return pd.DataFrame({
        'u': u_fine,
        'z_exact': exact['z'],
        'x_exact': exact['x'],
        'z_poly': z_lin,
        'x_poly': x_lin,
        'radial_error': error,
    })


def write_outputs() -> pd.DataFrame:
    rows = []
    for n_steps in N_STEPS_VALUES:
        curve = polyline_error_curve(n_steps)
        csv = DATA_DIR / f'sbend_bmad_sampling_n{n_steps}.csv'
        curve.to_csv(csv, index=False)
        rows.append({
            'n_steps': n_steps,
            'max_position_error': float(curve['radial_error'].max()),
            'rms_position_error': float(math.sqrt(float((curve['radial_error'] ** 2).mean()))),
            'curve_csv': csv.name,
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(FIG_DIR / 'sbend_bmad_sampling_summary.csv', index=False)
    return summary


def write_tikz() -> None:
    summary_tex = FIG_DIR / 'sbend_bmad_sampling_convergence.tex'
    discrepancy_tex = FIG_DIR / 'sbend_bmad_sampling_discrepancy.tex'

    summary_tex.write_text('\n'.join([
        r'\documentclass[tikz,border=4pt]{standalone}',
        r'\usepackage{pgfplots}',
        r'\pgfplotsset{compat=1.18}',
        r'\begin{document}',
        r'\begin{tikzpicture}',
        r'\begin{axis}[width=0.62\textwidth, height=0.44\textwidth,',
        r'xlabel={geometry samples $n_\mathrm{steps}$}, ylabel={polyline error [m]},',
        r'xmode=log, ymode=log, grid=both, minor grid style={gray!15}, major grid style={gray!30},',
        r'tick label style={font=\small}, label style={font=\small}, title style={font=\small},',
        r'title={Bmad SBEND geometry-export sampling convergence},',
        r'legend style={draw=none, fill=none, font=\scriptsize, at={(0.04,0.96)}, anchor=north west}]',
        r'\addplot[very thick, blue, mark=*] table[col sep=comma, x=n_steps, y=max_position_error] {sbend_bmad_sampling_summary.csv};',
        r'\addlegendentry{max error}',
        r'\addplot[very thick, red, mark=square*] table[col sep=comma, x=n_steps, y=rms_position_error] {sbend_bmad_sampling_summary.csv};',
        r'\addlegendentry{RMS error}',
        r'\end{axis}',
        r'\end{tikzpicture}',
        r'\end{document}',
    ]))

    palette = ['blue', 'red', 'black', 'teal', 'orange']
    lines = [
        r'\documentclass[tikz,border=4pt]{standalone}',
        r'\usepackage{pgfplots}',
        r'\pgfplotsset{compat=1.18}',
        r'\begin{document}',
        r'\begin{tikzpicture}',
        r'\begin{axis}[width=0.78\textwidth, height=0.46\textwidth,',
        r'xlabel={normalized path coordinate $u$}, ylabel={polyline discrepancy [m]},',
        r'ymode=log, grid=both, minor grid style={gray!15}, major grid style={gray!30},',
        r'tick label style={font=\small}, label style={font=\small}, title style={font=\small},',
        r'title={Bmad SBEND geometry-export discrepancy against analytic arc},',
        r'legend style={draw=none, fill=none, font=\scriptsize, at={(0.97,0.03)}, anchor=south east}]',
    ]
    for color, n_steps in zip(palette, CURVE_STEPS):
        lines.append(rf'\addplot[very thick, {color}] table[col sep=comma, x=u, y=radial_error] {{{"../data/sbend_bmad_sampling_n" + str(n_steps) + ".csv"}}};')
        lines.append(rf'\addlegendentry{{$n_\mathrm{{steps}}={n_steps}$}}')
    lines.extend([r'\end{axis}', r'\end{tikzpicture}', r'\end{document}'])
    discrepancy_tex.write_text('\n'.join(lines))


def main() -> None:
    prepare_dirs()
    write_outputs()
    write_tikz()


if __name__ == '__main__':
    main()
