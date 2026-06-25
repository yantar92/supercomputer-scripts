#!/usr/bin/env python3
"""
Fit fill-time scaling versus temperature and radius for 0 V MC pore filling.

Theory at 0 V:
    t_fill = C * R^3 * T * exp(A / T)

where A = DeltaE/k_B in kelvin.  To test radius scaling at the same time,
this script also fits the more general model

    t_fill = C * R^p * T * exp(A / T)

or, after taking logs,

    log(t_fill / T) = log(C) + p log(R) + A / T.

Outputs:
    <prefix>-raw-fill-times.csv
    <prefix>-summary-fill-times.csv
    <prefix>-fit-parameters.csv
    <prefix>-tfill-vs-temperature.png/.svg
    <prefix>-arrhenius-collapse-R3.png/.svg
    <prefix>-radius-scaling.png/.svg
    <prefix>-residuals.png/.svg

Example:
    python fit-fill-time-radius-temperature.py --radii 7 8 12 15 17 20 25 30 --temperatures 1200 1600 1800 2000 2200
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Keep the same basic style as plot-theory.py
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
    "legend.fontsize": 9,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "ytick.minor.width": 0.6,
    "xtick.minor.width": 0.6,
    "lines.linewidth": 1.5,
    "lines.markersize": 4.2,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "mathtext.default": "regular",
})


KB_EV_PER_K = 8.617333262145e-5


@dataclass
class FitResult:
    name: str
    logC: float
    A_K: float
    p: float
    rmse_log: float
    n: int


def try_true_radius_angstrom(radius_angstrom: float) -> float:
    """
    Use the same real-radius convention as plot-theory.py when ../mc-pore is available.
    If not available, fall back to the nominal radius.
    """
    try:
        sys.path.insert(0, "../mc-pore")
        from mcpore import HardCarbonPoreModel  # type: ignore
        return float(HardCarbonPoreModel(pore_radius_angstrom=radius_angstrom).real_radius_angstrom)
    except Exception:
        return float(radius_angstrom)


def extract_replica_label(path: Path) -> str:
    """
    Extract r* label from filenames such as 0.00V_2200K_15A_r12.csv.gz.
    """
    m = re.search(r"_r([^/_]+)\.csv(?:\.gz)?$", path.name)
    if m:
        return m.group(1)
    return path.stem


def first_crossing_time(df: pd.DataFrame, threshold_percent: float) -> float | None:
    """
    Return first linearly interpolated MC time at which Filling reaches threshold_percent.
    Works whether Filling is stored as 0-100 percent or 0-1 fraction.
    """
    if df.empty:
        return None

    d = df[["Time", "Filling"]].dropna().sort_values("Time")
    if d.empty:
        return None

    t = d["Time"].to_numpy(dtype=float)
    f = d["Filling"].to_numpy(dtype=float)

    # If data are stored as 0-1 fractions, convert to percent.
    finite = np.isfinite(f)
    if finite.any() and np.nanmax(f[finite]) <= 1.5:
        f = 100.0 * f

    ok = np.where(f >= threshold_percent)[0]
    if len(ok) == 0:
        return None

    i = int(ok[0])
    if i == 0:
        return float(t[0])

    t0, t1 = t[i - 1], t[i]
    f0, f1 = f[i - 1], f[i]

    if not np.isfinite([t0, t1, f0, f1]).all() or f1 == f0:
        return float(t1)

    w = (threshold_percent - f0) / (f1 - f0)
    return float(t0 + w * (t1 - t0))


def read_fill_times(args: argparse.Namespace) -> pd.DataFrame:
    names = ["Time", "Filling", "Formation energy"]
    rows = []

    for T in args.temperatures:
        for R_nom in args.radii:
            matched = []
            for d in args.dirs:
                matched.extend(Path(d).glob(f"{args.voltage}V_{int(T)}K_{int(R_nom)}A_r*.csv.gz"))
                matched.extend(Path(d).glob(f"{args.voltage}V_{int(T)}K_{int(R_nom)}A_r*.csv"))

            matched = sorted(set(matched))
            R_true = try_true_radius_angstrom(float(R_nom))

            for path in matched:
                try:
                    df = pd.read_csv(path, names=names, skiprows=1)
                except Exception as exc:
                    print(f"WARNING: could not read {path}: {exc}")
                    continue

                tf = first_crossing_time(df, args.threshold)
                if tf is None:
                    if args.keep_unfilled:
                        rows.append({
                            "temperature_K": float(T),
                            "radius_nominal_A": float(R_nom),
                            "radius_real_A": R_true,
                            "replica": extract_replica_label(path),
                            "file": str(path),
                            "fill_time": np.nan,
                            "reached_threshold": False,
                        })
                    continue

                rows.append({
                    "temperature_K": float(T),
                    "radius_nominal_A": float(R_nom),
                    "radius_real_A": R_true,
                    "replica": extract_replica_label(path),
                    "file": str(path),
                    "fill_time": float(tf),
                    "reached_threshold": True,
                })

            if args.verbose:
                print(f"T={T:g} K, R={R_nom:g} A: {len(matched)} files")

    raw = pd.DataFrame(rows)
    if raw.empty:
        raise SystemExit("No fill times found. Check --dirs, --voltage, --temperatures, --radii, and --threshold.")

    return raw


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw[raw["reached_threshold"] & raw["fill_time"].notna()].copy()
    g = d.groupby(["temperature_K", "radius_nominal_A", "radius_real_A"], as_index=False)
    return g["fill_time"].agg(
        n="count",
        mean="mean",
        median="median",
        std="std",
        q25=lambda x: np.quantile(x, 0.25),
        q75=lambda x: np.quantile(x, 0.75),
        min="min",
        max="max",
    )


def fit_log_model(df: pd.DataFrame, radius_power: float | None = None, use_summary: bool = True) -> FitResult:
    """
    Fit log(t/T) = logC + p log(R) + A/T.
    If radius_power is not None, p is fixed.
    """
    if use_summary:
        d = summarize(df).rename(columns={"median": "fit_time"})
    else:
        d = df[df["reached_threshold"] & df["fill_time"].notna()].copy()
        d["fit_time"] = d["fill_time"]

    d = d[(d["fit_time"] > 0) & (d["temperature_K"] > 0) & (d["radius_real_A"] > 0)].copy()
    if len(d) < 3:
        raise SystemExit("Not enough valid points for a fit.")

    y = np.log(d["fit_time"].to_numpy() / d["temperature_K"].to_numpy())
    invT = 1.0 / d["temperature_K"].to_numpy()
    logR = np.log(d["radius_real_A"].to_numpy())

    if radius_power is None:
        X = np.column_stack([np.ones(len(d)), logR, invT])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        logC, p, A_K = beta
        yhat = X @ beta
        name = "free_p"
    else:
        y2 = y - radius_power * logR
        X = np.column_stack([np.ones(len(d)), invT])
        beta, *_ = np.linalg.lstsq(X, y2, rcond=None)
        logC, A_K = beta
        p = float(radius_power)
        yhat = X @ beta + p * logR
        name = f"fixed_p_{radius_power:g}"

    rmse = float(np.sqrt(np.mean((y - yhat) ** 2)))
    return FitResult(name=name, logC=float(logC), A_K=float(A_K), p=float(p), rmse_log=rmse, n=len(d))


def add_predictions(summary: pd.DataFrame, fits: list[FitResult]) -> pd.DataFrame:
    out = summary.copy()
    T = out["temperature_K"].to_numpy()
    R = out["radius_real_A"].to_numpy()

    for fit in fits:
        pred = np.exp(fit.logC) * (R ** fit.p) * T * np.exp(fit.A_K / T)
        out[f"pred_{fit.name}"] = pred
        out[f"log_residual_{fit.name}"] = np.log(out["median"].to_numpy()) - np.log(pred)

    return out


def save_fit_parameters(fits: list[FitResult], path: Path) -> pd.DataFrame:
    rows = []
    for fit in fits:
        rows.append({
            "model": fit.name,
            "C": math.exp(fit.logC),
            "logC": fit.logC,
            "A_K": fit.A_K,
            "activation_energy_eV": fit.A_K * KB_EV_PER_K,
            "radius_power_p": fit.p,
            "rmse_log": fit.rmse_log,
            "n_fit_points": fit.n,
        })
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def plot_tfill_vs_temperature(summary_fit: pd.DataFrame, fit: FitResult, prefix: str) -> None:
    fig, ax = plt.subplots()
    cmap = mpl.colormaps["tab20"]

    radii = sorted(summary_fit["radius_nominal_A"].unique())
    Ts_grid = np.linspace(summary_fit["temperature_K"].min(), summary_fit["temperature_K"].max(), 300)

    for i, R_nom in enumerate(radii):
        dd = summary_fit[summary_fit["radius_nominal_A"] == R_nom].sort_values("temperature_K")
        color = cmap(i % 20)
        yerr_low = dd["median"] - dd["q25"]
        yerr_high = dd["q75"] - dd["median"]
        ax.errorbar(
            dd["temperature_K"], dd["median"],
            yerr=[yerr_low, yerr_high],
            fmt="o", capsize=2, color=color,
            label=f"{R_nom:g} A"
        )

        R_real = float(dd["radius_real_A"].iloc[0])
        pred = np.exp(fit.logC) * (R_real ** fit.p) * Ts_grid * np.exp(fit.A_K / Ts_grid)
        ax.plot(Ts_grid, pred, "-", color=color, alpha=0.9)

    ax.set_xlabel("Temperature (K)")
    ax.set_ylabel(f"Fill time to threshold (MC steps)")
    ax.set_yscale("log")
    ax.set_title(f"Fit with p = {fit.p:.2f}, A = {fit.A_K:.0f} K")
    ax.legend(title="Nominal radius", ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-tfill-vs-temperature.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-tfill-vs-temperature.svg", bbox_inches="tight")
    plt.close(fig)


def plot_arrhenius_collapse(summary_fit: pd.DataFrame, fit_fixed_p3: FitResult, prefix: str) -> None:
    fig, ax = plt.subplots()
    cmap = mpl.colormaps["tab20"]

    radii = sorted(summary_fit["radius_nominal_A"].unique())
    invT_grid = np.linspace(
        (1.0 / summary_fit["temperature_K"]).min(),
        (1.0 / summary_fit["temperature_K"]).max(),
        300,
    )

    for i, R_nom in enumerate(radii):
        dd = summary_fit[summary_fit["radius_nominal_A"] == R_nom].sort_values("temperature_K")
        color = cmap(i % 20)

        x = 1.0 / dd["temperature_K"]
        y = np.log(dd["median"] / (dd["temperature_K"] * dd["radius_real_A"] ** 3))
        ax.plot(x, y, "o", color=color, label=f"{R_nom:g} A")

    ax.plot(invT_grid, fit_fixed_p3.logC + fit_fixed_p3.A_K * invT_grid,
            "-", color="black", label="global fit, p=3")

    ax.set_xlabel("1/T (1/K)")
    ax.set_ylabel(r"log($t_{fill}/(T R^3)$)")
    ax.set_title(f"R^3 + activated-temperature collapse, A = {fit_fixed_p3.A_K:.0f} K")
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-arrhenius-collapse-R3.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-arrhenius-collapse-R3.svg", bbox_inches="tight")
    plt.close(fig)


def plot_radius_scaling(summary_fit: pd.DataFrame, fit_free: FitResult, prefix: str) -> None:
    fig, ax = plt.subplots()
    cmap = mpl.colormaps["tab20"]

    temps = sorted(summary_fit["temperature_K"].unique())
    R_grid = np.linspace(summary_fit["radius_real_A"].min(), summary_fit["radius_real_A"].max(), 300)

    for i, T in enumerate(temps):
        dd = summary_fit[summary_fit["temperature_K"] == T].sort_values("radius_real_A")
        color = cmap(i % 20)
        x = dd["radius_real_A"]
        y = dd["median"] / (T * np.exp(fit_free.A_K / T))
        ax.plot(x, y, "o", color=color, label=f"{T:g} K")

    # Use arbitrary normalization from the global fit; all temperatures should collapse here.
    y_grid = np.exp(fit_free.logC) * R_grid ** fit_free.p
    ax.plot(R_grid, y_grid, "-", color="black", label=f"global fit, p={fit_free.p:.2f}")

    y_grid_3 = np.exp(fit_free.logC) * R_grid ** 3
    # Rescale the p=3 reference to pass through the middle of the free-p curve.
    mid = len(R_grid) // 2
    y_grid_3 *= y_grid[mid] / y_grid_3[mid]
    ax.plot(R_grid, y_grid_3, "--", color="black", label="R^3 reference")

    ax.set_xlabel("Real pore radius (A)")
    ax.set_ylabel(r"$t_{fill}/[T \exp(A/T)]$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Radius scaling after removing fitted temperature factor")
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-radius-scaling.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-radius-scaling.svg", bbox_inches="tight")
    plt.close(fig)


def plot_residuals(summary_fit: pd.DataFrame, fit: FitResult, prefix: str) -> None:
    fig, ax = plt.subplots()
    cmap = mpl.colormaps["tab20"]

    radii = sorted(summary_fit["radius_nominal_A"].unique())
    for i, R_nom in enumerate(radii):
        dd = summary_fit[summary_fit["radius_nominal_A"] == R_nom].sort_values("temperature_K")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.plot(
            dd["temperature_K"],
            dd[f"log_residual_{fit.name}"],
            "o-",
            color=cmap(i % 20),
            label=f"{R_nom:g} A",
        )

    ax.set_xlabel("Temperature (K)")
    ax.set_ylabel("log(data / fit)")
    ax.set_title(f"Residuals for {fit.name}")
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-residuals.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-residuals.svg", bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dirs", nargs="+", default=["fix_samples_0V", "large_pore"],
                   help="Directories containing MC csv/csv.gz files.")
    p.add_argument("--voltage", default="0.00",
                   help="Voltage prefix in filenames, e.g. 0.00 for 0.00V_2200K_15A_r*.csv.gz.")
    p.add_argument("--temperatures", nargs="+", type=float,
                   default=[1200, 1400, 1600, 1800, 2000, 2200],
                   help="Temperatures in K.")
    p.add_argument("--radii", nargs="+", type=float,
                   default=[7, 8, 12, 15, 17, 20, 25, 30, 100],
                   help="Nominal radii in A, matching filename convention.")
    p.add_argument("--threshold", type=float, default=99.0,
                   help="Filling percentage used to define fill time.")
    p.add_argument("--prefix", default=None,
                   help="Output prefix. Default is tfill-allR-<voltage>V-th<threshold>.")
    p.add_argument("--keep-unfilled", action="store_true",
                   help="Keep rows for trajectories that did not reach the threshold in the raw CSV.")
    p.add_argument("--fit-all-trajectories", action="store_true",
                   help="Fit every trajectory instead of medians per T,R.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.prefix is None:
        th = ("%g" % args.threshold).replace(".", "p")
        args.prefix = f"tfill-allR-{args.voltage}V-th{th}"

    raw = read_fill_times(args)
    summary = summarize(raw)

    if summary.empty:
        raise SystemExit("No trajectories reached the fill threshold.")

    fit_free = fit_log_model(raw, radius_power=None, use_summary=not args.fit_all_trajectories)
    fit_p3 = fit_log_model(raw, radius_power=3.0, use_summary=not args.fit_all_trajectories)
    fits = [fit_free, fit_p3]

    summary_fit = add_predictions(summary, fits)

    raw.to_csv(f"{args.prefix}-raw-fill-times.csv", index=False)
    summary_fit.to_csv(f"{args.prefix}-summary-fill-times.csv", index=False)
    fit_table = save_fit_parameters(fits, Path(f"{args.prefix}-fit-parameters.csv"))

    plot_tfill_vs_temperature(summary_fit, fit_free, args.prefix)
    plot_arrhenius_collapse(summary_fit, fit_p3, args.prefix)
    plot_radius_scaling(summary_fit, fit_free, args.prefix)
    plot_residuals(summary_fit, fit_free, args.prefix)

    print("\nFit summary")
    print(fit_table.to_string(index=False))
    print("\nWrote:")
    for suffix in [
        "raw-fill-times.csv",
        "summary-fill-times.csv",
        "fit-parameters.csv",
        "tfill-vs-temperature.png",
        "tfill-vs-temperature.svg",
        "arrhenius-collapse-R3.png",
        "arrhenius-collapse-R3.svg",
        "radius-scaling.png",
        "radius-scaling.svg",
        "residuals.png",
        "residuals.svg",
    ]:
        print(f"  {args.prefix}-{suffix}")


if __name__ == "__main__":
    main()
