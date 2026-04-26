#!/Users/adelmann/git/opalx/.venv-h6/bin/python
"""Generate OPALX vs Bmad bend comparison data and a PGFPlots/TikZ figure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INSTALL_DIR = ROOT / 'install'
EXAMPLE_DIR = INSTALL_DIR / 'examples' / 'bend_compare'
BMAD_OUT = EXAMPLE_DIR / 'output'
OPALX_OUT = EXAMPLE_DIR / 'data'
FIG_DIR = EXAMPLE_DIR / 'figures'
PREPARE_WORKSPACE = ROOT / 'bin' / 'prepare_workspace.py'


def ensure_workspace() -> None:
    subprocess.run([str(PREPARE_WORKSPACE)], check=True)


@dataclass(frozen=True)
class CaseConfig:
    stem: str
    title: str
    bmad_ref: Path
    opalx_path: Path
    table_stem: str
    bend_kind: str
    opalx_length: float
    opalx_angle: float
    analytic_arc_length: float | None = None
    analytic_angle: float | None = None


CASES = [
    CaseConfig(
        stem="sbend_proton_590MeV_45deg",
        title=r"SBEND, proton, $E_{\mathrm{kin}}=590\,\mathrm{MeV}$",
        bmad_ref=BMAD_OUT / "sbend_proton_590MeV_45deg_reference_frame.dat",
        opalx_path=OPALX_OUT / "sbend_proton_590MeV_45deg_opalx_DesignPath.dat",
        table_stem="sbend_proton_590MeV_45deg",
        bend_kind="sbend",
        opalx_length=1.0,
        opalx_angle=math.pi / 4.0,
        analytic_arc_length=1.0,
        analytic_angle=math.pi / 4.0,
    ),
    CaseConfig(
        stem="rbend_electron_1GeV_45deg",
        title=r"RBEND, electron, $E_{\mathrm{kin}}=1\,\mathrm{GeV}$",
        bmad_ref=BMAD_OUT / "rbend_electron_1GeV_45deg_reference_frame.dat",
        opalx_path=OPALX_OUT / "rbend_electron_1GeV_45deg_opalx_DesignPath.dat",
        table_stem="rbend_electron_1GeV_45deg",
        bend_kind="rbend",
        opalx_length=1.082392200292394,
        opalx_angle=math.pi / 4.0,
    ),
]


def read_bmad_reference(path: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    cols = ["x", "y", "z", "r11", "r12", "r13", "r21", "r22", "r23", "tx", "ty", "tz"]
    df = pd.read_csv(path, sep=r"\s+", names=cols, engine="python")
    summary = {
        "final_z": float(df.iloc[-1]["z"]),
        "final_x": float(df.iloc[-1]["x"]),
        "final_tx": float(df.iloc[-1]["tx"]),
        "final_ty": float(df.iloc[-1]["ty"]),
        "final_tz": float(df.iloc[-1]["tz"]),
    }
    return df[["z", "x"]].copy(), summary


def read_raw_opalx_design_path(path: Path) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    pattern = re.compile(r"\s+")
    with path.open() as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = pattern.split(line.strip())
            if len(parts) < 15:
                continue
            rows.append({
                "s": float(parts[0]),
                "x": float(parts[1]),
                "y": float(parts[2]),
                "z": float(parts[3]),
                "px": float(parts[4]),
                "py": float(parts[5]),
                "pz": float(parts[6]),
                "label": parts[15].rstrip(",") if len(parts) > 15 else "",
            })
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"No design-path rows found in {path}")
    return df.reset_index(drop=True)


def extract_sbend_curve(df: pd.DataFrame, arc_length: float) -> pd.DataFrame:
    inside = df[df["s"] <= arc_length].copy()
    if inside.empty:
        raise RuntimeError("No SBEND rows on the physical body interval.")
    if float(inside.iloc[-1]["s"]) < arc_length:
        after = df[df["s"] > arc_length]
        if after.empty:
            raise RuntimeError("SBEND design path does not extend beyond exit for interpolation.")
        left = inside.iloc[-1]
        right = after.iloc[0]
        alpha = (arc_length - float(left["s"])) / (float(right["s"]) - float(left["s"]))
        interp = {"s": arc_length, "label": "B1"}
        for key in ["x", "y", "z", "px", "py", "pz"]:
            interp[key] = float(left[key]) + alpha * (float(right[key]) - float(left[key]))
        inside = pd.concat([inside, pd.DataFrame([interp])], ignore_index=True)
    return inside.reset_index(drop=True)


def extract_rbend_curve(df: pd.DataFrame, length: float, angle: float) -> pd.DataFrame:
    half_angle = 0.5 * angle
    exit_x = -length * math.sin(half_angle)
    exit_z = length * math.cos(half_angle)
    normal_x = -math.sin(half_angle)
    normal_z = math.cos(half_angle)

    signed_distance = (df["x"] - exit_x) * normal_x + (df["z"] - exit_z) * normal_z
    crossing = signed_distance.ge(0.0)
    if not crossing.any():
        raise RuntimeError("RBEND design path never reaches the exit plane.")
    idx = int(crossing.idxmax())
    if idx == 0:
        raise RuntimeError("RBEND exit-plane crossing occurs before any interior sample.")

    inside = df.iloc[:idx].copy()
    left = df.iloc[idx - 1]
    right = df.iloc[idx]
    d_left = float(signed_distance.iloc[idx - 1])
    d_right = float(signed_distance.iloc[idx])
    alpha = -d_left / (d_right - d_left)
    interp = {"s": float(left["s"]) + alpha * (float(right["s"]) - float(left["s"])), "label": "B1"}
    for key in ["x", "y", "z", "px", "py", "pz"]:
        interp[key] = float(left[key]) + alpha * (float(right[key]) - float(left[key]))
    inside = pd.concat([inside, pd.DataFrame([interp])], ignore_index=True)
    return inside.reset_index(drop=True)


def read_opalx_design_path(case: CaseConfig) -> tuple[pd.DataFrame, dict[str, float]]:
    df = read_raw_opalx_design_path(case.opalx_path)
    if case.bend_kind == "sbend":
        df = extract_sbend_curve(df, case.opalx_length)
    elif case.bend_kind == "rbend":
        df = extract_rbend_curve(df, case.opalx_length, case.opalx_angle)
    else:
        raise RuntimeError(f"Unsupported bend kind: {case.bend_kind}")

    p_last = df.iloc[-1][["x", "y", "z"]].to_numpy(dtype=float)
    p_prev = df.iloc[-2][["x", "y", "z"]].to_numpy(dtype=float)
    tangent = p_last - p_prev
    tangent /= float(math.sqrt((tangent ** 2).sum()))
    summary = {
        "final_z": float(p_last[2]),
        "final_x": float(p_last[0]),
        "final_tx": float(tangent[0]),
        "final_ty": float(tangent[1]),
        "final_tz": float(tangent[2]),
    }
    return df[["z", "x"]].copy(), summary


def build_analytic_sbend_curve(arc_length: float, bend_angle: float, num_points: int = 400) -> tuple[pd.DataFrame, dict[str, float]]:
    if abs(bend_angle) < 1.0e-15:
        raise ValueError("bend_angle must be nonzero for analytic SBEND curve")
    radius = arc_length / bend_angle
    phi = pd.Series([bend_angle * i / (num_points - 1) for i in range(num_points)], dtype=float)
    z = radius * phi.map(math.sin)
    x = -radius * phi.map(lambda value: 1.0 - math.cos(value))
    curve = pd.DataFrame({"z": z, "x": x})
    summary = {
        "final_z": float(radius * math.sin(bend_angle)),
        "final_x": float(-radius * (1.0 - math.cos(bend_angle))),
        "final_tx": float(-math.sin(bend_angle)),
        "final_ty": 0.0,
        "final_tz": float(math.cos(bend_angle)),
    }
    return curve, summary


def build_delta_curve(bmad_curve: pd.DataFrame, opalx_curve: pd.DataFrame) -> pd.DataFrame:
    z_min = max(float(bmad_curve["z"].min()), float(opalx_curve["z"].min()))
    z_max = min(float(bmad_curve["z"].max()), float(opalx_curve["z"].max()))
    opalx_overlap = opalx_curve[(opalx_curve["z"] >= z_min) & (opalx_curve["z"] <= z_max)].copy()
    if len(opalx_overlap) < 2:
        raise RuntimeError("Not enough overlapping points to compute OPALX-BMAD delta curve.")
    z_eval = opalx_overlap["z"].to_numpy(dtype=float)
    bmad_interp = np.interp(
        z_eval,
        bmad_curve["z"].to_numpy(dtype=float),
        bmad_curve["x"].to_numpy(dtype=float),
    )
    delta_x = opalx_overlap["x"].to_numpy(dtype=float) - bmad_interp
    return pd.DataFrame({"z": z_eval, "delta_x": delta_x})


def write_case_tables(
    case: CaseConfig,
    bmad_curve: pd.DataFrame,
    opalx_curve: pd.DataFrame,
    delta_curve: pd.DataFrame,
    analytic_curve: pd.DataFrame | None = None,
) -> None:
    bmad_curve.to_csv(FIG_DIR / f"{case.table_stem}_bmad.csv", index=False)
    opalx_curve.to_csv(FIG_DIR / f"{case.table_stem}_opalx.csv", index=False)
    delta_curve.to_csv(FIG_DIR / f"{case.table_stem}_delta.csv", index=False)
    if analytic_curve is not None:
        analytic_curve.to_csv(FIG_DIR / f"{case.table_stem}_analytic.csv", index=False)


def build_summary() -> pd.DataFrame:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, float | str]] = []
    for case in CASES:
        bmad_curve, bmad_summary = read_bmad_reference(case.bmad_ref)
        opalx_curve, opalx_summary = read_opalx_design_path(case)
        delta_curve = build_delta_curve(bmad_curve, opalx_curve)
        analytic_curve = None
        analytic_summary = None
        if case.analytic_arc_length is not None and case.analytic_angle is not None:
            analytic_curve, analytic_summary = build_analytic_sbend_curve(case.analytic_arc_length, case.analytic_angle)
        write_case_tables(case, bmad_curve, opalx_curve, delta_curve, analytic_curve)
        records.append({"case": case.stem, "code": "BMAD", **bmad_summary})
        records.append({"case": case.stem, "code": "OPALX", **opalx_summary})
        if analytic_summary is not None:
            records.append({"case": case.stem, "code": "ANALYTIC", **analytic_summary})
    summary = pd.DataFrame.from_records(records)
    summary.to_csv(FIG_DIR / "bend_code_comparison_summary.csv", index=False)
    return summary


def write_tikz() -> None:
    tex = FIG_DIR / "bend_code_comparison.tex"
    panel_width = r"0.56\textwidth"
    panel_height = r"0.34\textwidth"
    horizontal_shift = r"0.68\textwidth"

    lines = [
        r"\documentclass[tikz,border=4pt]{standalone}",
        r"\usepackage{pgfplots}",
        r"\pgfplotsset{compat=1.18}",
        r"\begin{document}",
        r"\begin{tikzpicture}",
    ]

    for idx, case in enumerate(CASES, start=1):
        bmad_path = FIG_DIR / f"{case.table_stem}_bmad.csv"
        z_table = pd.read_csv(bmad_path)
        xmin = float(z_table['z'].min())
        xmax = float(z_table['z'].max())
        base_at = "{(0,0)}" if idx == 1 else f"{{({horizontal_shift},0)}}"
        axis_name = f"main{idx}"
        lines.extend([
            rf"\begin{{axis}}[name={axis_name}, at={base_at}, anchor=south west,",
            rf"width={panel_width}, height={panel_height},",
            r"xlabel={$z$ [m]}, ylabel={$x$ [m]},",
            rf"xmin={xmin}, xmax={xmax},",
            rf"title={{{case.title}}},",
            r"grid=both, minor grid style={gray!15}, major grid style={gray!30},",
            r"legend style={draw=none, fill=white, fill opacity=0.75, text opacity=1, font=\scriptsize, at={(0.04,0.04)}, anchor=south west, legend columns=1},",
            r"tick label style={font=\small}, label style={font=\small}, title style={font=\small}]",
            rf"\addplot[very thick, blue] table[col sep=comma, x=z, y=x] {{{case.table_stem}_bmad.csv}};",
            r"\addlegendentry{Bmad}",
            rf"\addplot[very thick, red, dashed] table[col sep=comma, x=z, y=x] {{{case.table_stem}_opalx.csv}};",
            r"\addlegendentry{OPALX}",
        ])
        if case.analytic_arc_length is not None and case.analytic_angle is not None:
            lines.extend([
                rf"\addplot[very thick, black, dash dot] table[col sep=comma, x=z, y=x] {{{case.table_stem}_analytic.csv}};",
                r"\addlegendentry{Analytic}",
            ])
        lines.extend([
            r"\end{axis}",
            rf"\begin{{axis}}[at={{({axis_name}.south west)}}, anchor=south west,",
            rf"width={panel_width}, height={panel_height},",
            r"axis x line=none, axis y line*=right,",
            r"ylabel={$\Delta x$ [m]},",
            r"ylabel style={color=green!50!black},",
            r"y tick label style={color=green!50!black, font=\scriptsize},",
            r"tick label style={font=\small}, label style={font=\small},",
            rf"xmin={xmin}, xmax={xmax}, grid=none]",
            rf"\addplot[very thick, green!60!black] table[col sep=comma, x=z, y=delta_x] {{{case.table_stem}_delta.csv}};",
            r"\end{axis}",
        ])

    lines.extend([r"\end{tikzpicture}", r"\end{document}"])
    tex.write_text("\n".join(lines))

def main() -> None:
    ensure_workspace()
    build_summary()
    write_tikz()


if __name__ == "__main__":
    main()
