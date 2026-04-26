#!/Users/adelmann/git/opalx/.venv-h6/bin/python
"""Run an OPALX SBEND time-step convergence study against the analytic arc."""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INSTALL_DIR = ROOT / 'install'
EXAMPLE_DIR = INSTALL_DIR / 'examples' / 'bend_compare'
STUDY_DIR = EXAMPLE_DIR / 'studies' / 'sbend_dt_convergence'
DATA_DIR = STUDY_DIR / "data"
FIG_DIR = STUDY_DIR / "figures"
WORK_DIR = STUDY_DIR / "work"

ANGLE = math.pi / 4.0
ARC_LENGTH = 1.0
RADIUS = ARC_LENGTH / ANGLE
BASE_INPUT = EXAMPLE_DIR / "sbend_proton_590MeV_45deg_opalx.in"
DIST_FILE = EXAMPLE_DIR / 'opalx_proton_distribution.txt'
PREPARE_WORKSPACE = ROOT / 'bin' / 'prepare_workspace.py'
DT_VALUES = [2.0e-10, 1.0e-10, 5.0e-11, 2.0e-11, 1.0e-11, 5.0e-12, 2.0e-12, 1.0e-12, 5.0e-13]


@dataclass(frozen=True)
class RunResult:
    dt: float
    path_file: Path
    curve_csv: Path
    discrepancy_csv: Path
    final_position_error: float
    max_position_error: float
    rms_position_error: float
    l2_position_error: float
    final_tangent_error_rad: float
    final_tangent_error_deg: float
    final_x: float
    final_z: float
    final_tx: float
    final_tz: float


def ensure_workspace() -> None:
    subprocess.run([str(PREPARE_WORKSPACE)], check=True)


def resolve_opalx_bin() -> Path:
    env = os.environ.get('OPALX_EXE_PATH')
    if not env:
        raise RuntimeError('Set OPALX_EXE_PATH to the OPALX executable or its containing directory.')
    candidate = Path(env).expanduser()
    opalx_bin = candidate / 'opalx' if candidate.is_dir() else candidate
    if not opalx_bin.exists():
        raise RuntimeError(f'Missing OPALX executable: {opalx_bin}')
    return opalx_bin


def prepare_dirs() -> None:
    for directory in [DATA_DIR, FIG_DIR, WORK_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def build_input_text(dt: float) -> str:
    text = BASE_INPUT.read_text()
    text = re.sub(r'Title, string = ".*";', f'Title, string = "OPALX proton SBEND DT study ({dt:.3e})";', text)
    text = re.sub(r'DT = [^,]+,', f'DT = {dt:.16e},', text)
    text = re.sub(r'MAXSTEPS = [^,]+,', 'MAXSTEPS = 50000,', text)
    return text


def read_opalx_design_path(path: Path) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    pattern = re.compile(r'\s+')
    with path.open() as handle:
        for line in handle:
            if not line.strip() or line.startswith('#'):
                continue
            parts = pattern.split(line.strip())
            if len(parts) < 15:
                continue
            rows.append({
                's': float(parts[0]),
                'x': float(parts[1]),
                'y': float(parts[2]),
                'z': float(parts[3]),
                'px': float(parts[4]),
                'py': float(parts[5]),
                'pz': float(parts[6]),
                'label': parts[15].rstrip(',') if len(parts) > 15 else '',
            })
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f'No design path rows found in {path}')
    return df.reset_index(drop=True)


def extract_sbend_body_path(df: pd.DataFrame) -> pd.DataFrame:
    """Extract the SBEND body trajectory on the physical interval s in [0, L].

    The raw design path keeps logging after the active-set handoff at the bend exit.
    For comparison against the analytic sector arc we therefore truncate to the
    physical body interval and linearly interpolate the exact exit point at
    s = L when the last in-bend sample and first out-of-bend sample straddle
    the boundary.
    """
    s_begin = 0.0
    s_end = ARC_LENGTH
    inside = df[df['s'] <= s_end].copy()
    if inside.empty:
        raise RuntimeError('No SBEND rows on the physical body interval.')

    if inside.iloc[-1]['s'] < s_end:
        after = df[df['s'] > s_end]
        if after.empty:
            raise RuntimeError('Design path does not extend beyond SBEND exit for interpolation.')
        left = inside.iloc[-1]
        right = after.iloc[0]
        alpha = (s_end - float(left['s'])) / (float(right['s']) - float(left['s']))
        interp = {'s': s_end}
        for key in ['x', 'y', 'z', 'px', 'py', 'pz']:
            interp[key] = float(left[key]) + alpha * (float(right[key]) - float(left[key]))
        interp['label'] = 'B1'
        inside = pd.concat([inside, pd.DataFrame([interp])], ignore_index=True)

    inside = inside[inside['s'] >= s_begin].copy()
    if abs(float(inside.iloc[0]['s']) - s_begin) > 1.0e-14:
        raise RuntimeError('SBEND study expects the first design-path sample at s = 0.')

    return inside.reset_index(drop=True)


def analytic_point(u: pd.Series) -> tuple[pd.Series, pd.Series]:
    phi = ANGLE * u
    z = RADIUS * phi.map(math.sin)
    x = -RADIUS * phi.map(lambda value: 1.0 - math.cos(value))
    return x, z


def compute_curve_and_errors(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    points = df[['x', 'y', 'z']].copy()
    dx = points['x'].diff().fillna(0.0)
    dy = points['y'].diff().fillna(0.0)
    dz = points['z'].diff().fillna(0.0)
    ds = (dx * dx + dy * dy + dz * dz).map(math.sqrt)
    s_num = ds.cumsum()
    total = float(s_num.iloc[-1]) if len(s_num) > 0 else 0.0
    if total <= 0.0:
        raise RuntimeError('Degenerate design path with zero total length.')
    u = s_num / total
    x_analytic, z_analytic = analytic_point(u)
    radial_error = ((points['x'] - x_analytic) ** 2 + (points['z'] - z_analytic) ** 2).map(math.sqrt)
    squared_error = radial_error ** 2
    l2_position_error = math.sqrt(float((0.5 * (squared_error.iloc[1:].to_numpy() + squared_error.iloc[:-1].to_numpy()) * u.diff().iloc[1:].to_numpy()).sum()))

    p_last = points.iloc[-1].to_numpy(dtype=float)
    p_prev = points.iloc[-2].to_numpy(dtype=float)
    tangent = p_last - p_prev
    tangent /= math.sqrt(float((tangent ** 2).sum()))
    analytic_tx = -math.sin(ANGLE)
    analytic_tz = math.cos(ANGLE)
    cosine = max(-1.0, min(1.0, tangent[0] * analytic_tx + tangent[2] * analytic_tz))
    tangent_error = math.acos(cosine)

    curve = pd.DataFrame({
        'u': u,
        's_num': s_num,
        'x_opalx': points['x'],
        'z_opalx': points['z'],
        'x_analytic': x_analytic,
        'z_analytic': z_analytic,
        'radial_error': radial_error,
    })

    metrics = {
        'final_position_error': float(radial_error.iloc[-1]),
        'max_position_error': float(radial_error.max()),
        'rms_position_error': float(math.sqrt(float((radial_error ** 2).mean()))),
        'l2_position_error': float(l2_position_error),
        'final_tangent_error_rad': float(tangent_error),
        'final_tangent_error_deg': float(tangent_error * 180.0 / math.pi),
        'final_x': float(points.iloc[-1]['x']),
        'final_z': float(points.iloc[-1]['z']),
        'final_tx': float(tangent[0]),
        'final_tz': float(tangent[2]),
    }
    return curve, metrics


def run_case(opalx_bin: Path, dt: float) -> RunResult:
    stem = f'sbend_dt_{dt:.1e}'.replace('+', '').replace('-', 'm')
    input_file = WORK_DIR / f'{stem}.in'
    input_file.write_text(build_input_text(dt))
    shutil.copy2(DIST_FILE, WORK_DIR / DIST_FILE.name)
    subprocess.run([str(opalx_bin), input_file.name, '--info', '1'], cwd=WORK_DIR, check=True, stdout=subprocess.DEVNULL)

    path_file = WORK_DIR / 'data' / f'{input_file.stem}_DesignPath.dat'
    if not path_file.exists():
        raise RuntimeError(f'Missing design path file: {path_file}')
    df = extract_sbend_body_path(read_opalx_design_path(path_file))
    curve, metrics = compute_curve_and_errors(df)

    curve_csv = DATA_DIR / f'{input_file.stem}_curve.csv'
    discrepancy_csv = DATA_DIR / f'{input_file.stem}_discrepancy.csv'
    curve.to_csv(curve_csv, index=False)
    curve[['u', 'radial_error']].to_csv(discrepancy_csv, index=False)
    shutil.copy2(path_file, DATA_DIR / path_file.name)

    return RunResult(
        dt=dt,
        path_file=DATA_DIR / path_file.name,
        curve_csv=curve_csv,
        discrepancy_csv=discrepancy_csv,
        **metrics,
    )


def write_summary(results: list[RunResult]) -> pd.DataFrame:
    summary = pd.DataFrame([
        {
            'dt': r.dt,
            'final_position_error': r.final_position_error,
            'max_position_error': r.max_position_error,
            'rms_position_error': r.rms_position_error,
            'l2_position_error': r.l2_position_error,
            'final_tangent_error_rad': r.final_tangent_error_rad,
            'final_tangent_error_deg': r.final_tangent_error_deg,
            'final_x': r.final_x,
            'final_z': r.final_z,
            'final_tx': r.final_tx,
            'final_tz': r.final_tz,
            'curve_csv': r.curve_csv.name,
            'discrepancy_csv': r.discrepancy_csv.name,
        }
        for r in results
    ]).sort_values('dt', ascending=False)
    anchor_dt = float(summary.iloc[0]['dt'])
    anchor_l2 = float(summary.iloc[0]['l2_position_error'])
    summary['l2_second_order_reference'] = anchor_l2 * (summary['dt'] / anchor_dt) ** 2
    summary.to_csv(FIG_DIR / 'sbend_dt_convergence_summary.csv', index=False)
    return summary


def write_tikz(results: list[RunResult]) -> None:
    summary_tex = FIG_DIR / 'sbend_dt_convergence.tex'
    discrepancy_tex = FIG_DIR / 'sbend_dt_discrepancy.tex'
    l2_tex = FIG_DIR / 'sbend_dt_l2_error.tex'

    summary_lines = [
        r'\documentclass[tikz,border=4pt]{standalone}',
        r'\usepackage{pgfplots}',
        r'\usepgfplotslibrary{groupplots}',
        r'\pgfplotsset{compat=1.18}',
        r'\begin{document}',
        r'\begin{tikzpicture}',
        r'\begin{groupplot}[group style={group size=2 by 1, horizontal sep=2.2cm},',
        r'width=0.48\textwidth, height=0.40\textwidth,',
        r'grid=both, minor grid style={gray!15}, major grid style={gray!30},',
        r'tick label style={font=\small}, label style={font=\small}, title style={font=\small},',
        r'legend style={draw=none, fill=none, font=\scriptsize, at={(0.04,0.96)}, anchor=north west}]',
        r'\nextgroupplot[xmode=log, ymode=log, xlabel={$\Delta t$ [s]}, ylabel={position error [m]}, title={SBEND endpoint/path convergence}]',
        r'\addplot[very thick, blue, mark=*] table[col sep=comma, x=dt, y=final_position_error] {sbend_dt_convergence_summary.csv};',
        r'\addlegendentry{final position}',
        r'\addplot[very thick, green!60!black, mark=square*] table[col sep=comma, x=dt, y=l2_position_error] {sbend_dt_convergence_summary.csv};',
        r'\addlegendentry{$L^2$ along path}',
        r'\addplot[very thick, red, mark=*] table[col sep=comma, x=dt, y=max_position_error] {sbend_dt_convergence_summary.csv};',
        r'\addlegendentry{max along path}',
        r'\nextgroupplot[xmode=log, ymode=log, xlabel={$\Delta t$ [s]}, ylabel={angle error [deg]}, title={SBEND final tangent convergence}]',
        r'\addplot[very thick, black, mark=triangle*] table[col sep=comma, x=dt, y=final_tangent_error_deg] {sbend_dt_convergence_summary.csv};',
        r'\addlegendentry{final tangent}',
        r'\end{groupplot}',
        r'\end{tikzpicture}',
        r'\end{document}',
    ]
    summary_tex.write_text('\n'.join(summary_lines))

    l2_lines = [
        r'\documentclass[tikz,border=4pt]{standalone}',
        r'\usepackage{pgfplots}',
        r'\pgfplotsset{compat=1.18}',
        r'\begin{document}',
        r'\begin{tikzpicture}',
        r'\begin{axis}[width=0.72\textwidth, height=0.44\textwidth,',
        r'xmode=log, ymode=log,',
        r'xlabel={$\Delta t$ [s]}, ylabel={$L^2$ position error [m]},',
        r'grid=both, minor grid style={gray!15}, major grid style={gray!30},',
        r'tick label style={font=\small}, label style={font=\small}, title style={font=\small},',
        r'title={SBEND analytic-vs-OPALX path error},',
        r'legend style={draw=none, fill=none, font=\scriptsize, at={(0.04,0.96)}, anchor=north west}]',
        r'\addplot[very thick, green!60!black, mark=square*] table[col sep=comma, x=dt, y=l2_position_error] {sbend_dt_convergence_summary.csv};',
        r'\addlegendentry{$L^2$ error}',
        r'\addplot[very thick, black, dashed] table[col sep=comma, x=dt, y=l2_second_order_reference] {sbend_dt_convergence_summary.csv};',
        r'\addlegendentry{second-order reference $\propto \Delta t^2$}',
        r'\end{axis}',
        r'\end{tikzpicture}',
        r'\end{document}',
    ]
    l2_tex.write_text('\n'.join(l2_lines))

    palette = ['blue', 'red', 'black', 'teal', 'orange', 'violet', 'brown', 'magenta', 'gray']
    discrepancy_lines = [
        r'\documentclass[tikz,border=4pt]{standalone}',
        r'\usepackage{pgfplots}',
        r'\pgfplotsset{compat=1.18}',
        r'\begin{document}',
        r'\begin{tikzpicture}',
        r'\begin{axis}[width=0.78\textwidth, height=0.46\textwidth,',
        r'xlabel={normalized path coordinate $u$}, ylabel={radial discrepancy [m]},',
        r'ymode=log, grid=both, minor grid style={gray!15}, major grid style={gray!30},',
        r'tick label style={font=\small}, label style={font=\small}, title style={font=\small},',
        r'title={SBEND discrepancy against analytic arc},',
        r'legend style={draw=none, fill=none, font=\scriptsize, at={(0.97,0.03)}, anchor=south east}]',
    ]
    for i, result in enumerate(sorted(results, key=lambda r: r.dt, reverse=True)):
        color = palette[i % len(palette)]
        csv_rel = '../data/' + result.discrepancy_csv.name
        discrepancy_lines.append(
            rf'\addplot[very thick, {color}] table[col sep=comma, x=u, y=radial_error] {{{csv_rel}}};'
        )
        discrepancy_lines.append(rf'\addlegendentry{{$\Delta t={result.dt:.1e}\,\mathrm{{s}}$}}')
    discrepancy_lines.extend([r'\end{axis}', r'\end{tikzpicture}', r'\end{document}'])
    discrepancy_tex.write_text('\n'.join(discrepancy_lines))


def main() -> None:
    ensure_workspace()
    opalx_bin = resolve_opalx_bin()
    prepare_dirs()
    (WORK_DIR / 'data').mkdir(parents=True, exist_ok=True)
    results = [run_case(opalx_bin, dt) for dt in DT_VALUES]
    write_summary(results)
    write_tikz(results)


if __name__ == '__main__':
    main()
