#!/usr/bin/env python3
"""
Fit the temperature dependence of the filling time for one pore radius at 0 V.

Model used for a fixed radius:
    rate(T)  = K_rate * exp(-A/T) / T
    t_fill(T)= C * T * exp(A/T)

A is reported in Kelvin.  If you want the activation energy in eV,
E_eV = k_B * A with k_B = 8.617333262e-5 eV/K.

The script treats each *_r*.csv.gz file as one independent MC trajectory,
extracts the first time when Filling reaches a chosen threshold, and fits the
fill times as a function of temperature.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KB_EV_PER_K = 8.617333262e-5


@dataclass
class FillTimeRecord:
    temperature: float
    radius: int
    file: str
    t_fill: float
    max_filling: float


def setup_plot_style() -> None:
    a4_width = 4.13 * 2
    width = a4_width / 2
    height = width * 3 / 4
    mpl.rcParams.update({
        "figure.figsize": (width, height),
        "figure.dpi": 300,
        "savefig.dpi": 600,
        "font.size": 13,
        "axes.labelsize": 11,
        "axes.titlesize": 13,
        "legend.fontsize": 10,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.width": 0.6,
        "ytick.minor.width": 0.6,
        "lines.linewidth": 1.5,
        "lines.markersize": 4.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "mathtext.default": "regular",
    })


def read_trajectory(path: Path) -> pd.DataFrame:
    names = ["Time", "Filling", "Formation energy"]
    df = pd.read_csv(path, names=names, skiprows=1)
    df = df[["Time", "Filling"]].dropna()
    df = df.sort_values("Time").drop_duplicates("Time", keep="last")
    return df


def normalize_threshold(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, float, str]:
    """Return a copy with Filling in percent and threshold in percent."""
    out = df.copy()
    max_f = float(out["Filling"].max())

    # Existing plotting code suggests Filling is usually percent.  If it is a
    # fraction, convert it to percent.  A threshold <= 1 is interpreted as a
    # fraction in either case.
    if max_f <= 1.5:
        out["Filling"] = out["Filling"] * 100.0

    threshold_percent = threshold * 100.0 if threshold <= 1.0 else threshold
    return out, threshold_percent, "percent"


def first_crossing_time(df: pd.DataFrame, threshold: float) -> float | None:
    dfp, threshold_percent, _ = normalize_threshold(df, threshold)
    y = dfp["Filling"].to_numpy(dtype=float)
    t = dfp["Time"].to_numpy(dtype=float)

    if len(t) == 0 or np.nanmax(y) < threshold_percent:
        return None

    idx = int(np.argmax(y >= threshold_percent))
    if idx == 0:
        return float(t[0])

    t0, t1 = float(t[idx - 1]), float(t[idx])
    y0, y1 = float(y[idx - 1]), float(y[idx])
    if y1 == y0:
        return t1

    # Linear interpolation between the two MC samples around the threshold.
    return t0 + (threshold_percent - y0) * (t1 - t0) / (y1 - y0)


def discover_files(dirs: list[Path], voltage: str, radius: int, temperatures: list[int] | None) -> dict[int, list[Path]]:
    by_temp: dict[int, list[Path]] = {}
    temp_re = re.compile(rf"{re.escape(voltage)}V_(\d+)K_{radius}A_r.*\.csv\.gz$")

    for d in dirs:
        for path in sorted(d.glob(f"{voltage}V_*K_{radius}A_r*.csv.gz")):
            m = temp_re.search(path.name)
            if not m:
                continue
            temp = int(m.group(1))
            if temperatures is not None and temp not in temperatures:
                continue
            by_temp.setdefault(temp, []).append(path)

    return dict(sorted(by_temp.items()))


def collect_fill_times(
    dirs: list[Path],
    voltage: str,
    radius: int,
    temperatures: list[int] | None,
    threshold: float,
) -> pd.DataFrame:
    by_temp = discover_files(dirs, voltage, radius, temperatures)
    records: list[FillTimeRecord] = []
    skipped = []

    for temp, paths in by_temp.items():
        for path in paths:
            df = read_trajectory(path)
            t_fill = first_crossing_time(df, threshold)
            max_f = float(df["Filling"].max())
            if t_fill is None:
                skipped.append((path, max_f))
                continue
            records.append(FillTimeRecord(temp, radius, str(path), float(t_fill), max_f))

    if skipped:
        print("Skipped trajectories that did not reach the threshold:")
        for path, max_f in skipped[:20]:
            print(f"  {path}  max Filling={max_f:g}")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more")

    if not records:
        raise RuntimeError("No trajectories reached the requested fill threshold.")

    return pd.DataFrame([r.__dict__ for r in records])


def fit_temperature_dependence(df: pd.DataFrame, statistic: str = "median") -> tuple[pd.DataFrame, float, float, float]:
    grouped = df.groupby("temperature")["t_fill"]
    summary = grouped.agg(
        n="count",
        mean="mean",
        median="median",
        q25=lambda x: np.quantile(x, 0.25),
        q75=lambda x: np.quantile(x, 0.75),
        std="std",
    ).reset_index()

    if statistic not in {"mean", "median"}:
        raise ValueError("statistic must be 'mean' or 'median'")

    fit_df = summary.dropna(subset=[statistic]).copy()
    if len(fit_df) < 2:
        raise RuntimeError("Need at least two temperatures with valid fill times for a fit.")

    T = fit_df["temperature"].to_numpy(dtype=float)
    t = fit_df[statistic].to_numpy(dtype=float)

    # log(t/T) = log(C) + A/T
    x = 1.0 / T
    y = np.log(t / T)
    slope, intercept = np.polyfit(x, y, 1)
    A_K = float(slope)
    C = float(np.exp(intercept))
    E_eV = A_K * KB_EV_PER_K

    summary["fit_t_fill"] = C * summary["temperature"] * np.exp(A_K / summary["temperature"])
    summary["fit_statistic"] = statistic
    return summary, C, A_K, E_eV


def plot_t_vs_T(raw: pd.DataFrame, summary: pd.DataFrame, C: float, A_K: float, args: argparse.Namespace) -> None:
    fig, ax = plt.subplots()

    rng = np.random.default_rng(args.jitter_seed)
    temps = raw["temperature"].to_numpy(dtype=float)
    jitter_width = args.jitter * max(1.0, np.ptp(sorted(raw["temperature"].unique())) / max(1, raw["temperature"].nunique()))
    ax.scatter(temps + rng.normal(0.0, jitter_width, size=len(raw)), raw["t_fill"], alpha=0.01, s=14, label="runs")

    yerr_low = summary[args.statistic] - summary["q25"]
    yerr_high = summary["q75"] - summary[args.statistic]
    ax.errorbar(
        summary["temperature"],
        summary[args.statistic],
        yerr=[yerr_low, yerr_high],
        fmt="o",
        capsize=3,
        label=f"{args.statistic} $t_{{fill}}$ (IQR)",
    )

    T_grid = np.linspace(summary["temperature"].min() * 0.98, summary["temperature"].max() * 1.02, 300)
    ax.plot(T_grid, C * T_grid * np.exp(A_K / T_grid), "-", color="black", label=r"fit: $C T e^{A/T}$")

    ax.set_xlabel("Temperature (K)")
    ax.set_ylabel("Fill time (MC steps)")
    ax.set_title(f"Radius {args.radius} A, {args.voltage} V, threshold {args.threshold:g}")
    ax.legend()
    fig.savefig(f"{args.out_prefix}-tfill-vs-temperature.png", bbox_inches="tight")
    fig.savefig(f"{args.out_prefix}-tfill-vs-temperature.svg", bbox_inches="tight")


def plot_arrhenius(raw: pd.DataFrame, summary: pd.DataFrame, C: float, A_K: float, args: argparse.Namespace) -> None:
    fig, ax = plt.subplots()

    x_raw = 1.0 / raw["temperature"].to_numpy(dtype=float)
    y_raw = np.log(raw["t_fill"].to_numpy(dtype=float) / raw["temperature"].to_numpy(dtype=float))
    ax.scatter(x_raw, y_raw, alpha=0.35, s=14, label="runs")

    T = summary["temperature"].to_numpy(dtype=float)
    x = 1.0 / T
    y = np.log(summary[args.statistic].to_numpy(dtype=float) / T)
    ax.plot(x, y, "o", label=args.statistic)

    x_grid = np.linspace(x.min() * 0.98, x.max() * 1.02, 300)
    ax.plot(x_grid, np.log(C) + A_K * x_grid, "-", color="black", label="linear fit")

    ax.set_xlabel(r"$1/T$ (1/K)")
    ax.set_ylabel(r"$\ln(t_{fill}/T)$")
    ax.set_title("Linearized temperature dependence")
    ax.legend()
    fig.savefig(f"{args.out_prefix}-arrhenius.png", bbox_inches="tight")
    fig.savefig(f"{args.out_prefix}-arrhenius.svg", bbox_inches="tight")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius", type=int, required=True, help="Pore radius label in the filename, e.g. 15 for *_15A_r*.csv.gz")
    parser.add_argument("--voltage", default="0.00", help="Voltage label in the filename. Default: 0.00")
    parser.add_argument("--dirs", nargs="+", default=["fix_samples_0V", "large_pore"], help="Directories to search")
    parser.add_argument("--temperatures", type=int, nargs="*", default=None, help="Temperatures to include. Default: auto-discover")
    parser.add_argument("--threshold", type=float, default=99.0, help="Fill threshold. Use 99 for percent or 0.99 for fraction. Default: 99")
    parser.add_argument("--statistic", choices=["median", "mean"], default="median", help="Statistic fitted at each temperature")
    parser.add_argument("--out-prefix", default=None, help="Output prefix. Default: tfill-R{radius}-{voltage}V")
    parser.add_argument("--jitter", type=float, default=0.015, help="Small x-jitter for individual run points")
    parser.add_argument("--jitter-seed", type=int, default=12345)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.out_prefix is None:
        args.out_prefix = f"tfill-R{args.radius}-{args.voltage}V"

    setup_plot_style()
    dirs = [Path(d) for d in args.dirs]

    raw = collect_fill_times(dirs, args.voltage, args.radius, args.temperatures, args.threshold)
    summary, C, A_K, E_eV = fit_temperature_dependence(raw, args.statistic)

    raw_out = f"{args.out_prefix}-raw-fill-times.csv"
    summary_out = f"{args.out_prefix}-summary-fit.csv"
    raw.to_csv(raw_out, index=False)
    summary.to_csv(summary_out, index=False)

    plot_t_vs_T(raw, summary, C, A_K, args)
    plot_arrhenius(raw, summary, C, A_K, args)

    print("\nFit model for fixed radius:")
    print("  t_fill(T) = C * T * exp(A/T)")
    print("  equivalent rate = const * exp(-A/T) / T")
    print(f"\nFitted using {args.statistic} fill time at each temperature")
    print(f"  C   = {C:.8e} MC steps / K")
    print(f"  A   = {A_K:.6g} K")
    print(f"  E   = {E_eV:.6g} eV")
    print(f"\nWrote {raw_out}")
    print(f"Wrote {summary_out}")
    print(f"Wrote {args.out_prefix}-tfill-vs-temperature.png/.svg")
    print(f"Wrote {args.out_prefix}-arrhenius.png/.svg")


if __name__ == "__main__":
    main()
