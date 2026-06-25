#!/usr/bin/env python3
"""
Analyze fill-time scaling versus temperature and radius for 0 V MC pore filling,
but fit the activation temperature factor using only the largest pore size.

Theory at 0 V:
    t_fill = C * R^3 * T * exp(A / T)

Procedure:
    1. Extract t_fill(T, R) for all requested radii.
    2. Identify the largest real radius unless --fit-radius is specified.
    3. Fit A and C only from that largest-radius subset:
           log(t_fill / (T R^3)) = log(C) + A/T
    4. Use that same fitted A and C to predict all smaller radii using R^3.
    5. Plot whether all radii collapse under the largest-pore fitted scaling.

This is useful when the largest pore is expected to be closest to the continuum
diffusion/curvature theory, while smaller pores may show finite-size deviations.

Outputs:
    <prefix>-raw-fill-times.csv
    <prefix>-summary-fill-times.csv
    <prefix>-largest-pore-fit-parameters.csv
    <prefix>-tfill-vs-temperature-largestfit.png/.svg
    <prefix>-arrhenius-collapse-R3-largestfit.png/.svg
    <prefix>-radius-scaling-largestfit.png/.svg
    <prefix>-residuals-largestfit.png/.svg

Example:
    python fit-fill-time-radius-temperature-largestfit.py --radii 7 8 12 15 17 20 25 30 100 --temperatures 1200 1600 1800 2000 2200 --defect-density 0.01
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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
    "lines.linewidth": 1.5,
    "lines.markersize": 4.2,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "mathtext.default": "regular",
})

KB_EV_PER_K = 8.617333262145e-5


@dataclass
class FitResult:
    logC: float
    A_K: float
    fit_radius_nominal_A: float
    fit_radius_real_A: float
    rmse_log_fit_radius: float
    n_fit_points: int


def try_true_radius_angstrom(radius_angstrom: float) -> float:
    try:
        sys.path.insert(0, "../mc-pore")
        from mcpore import HardCarbonPoreModel  # type: ignore
        return float(HardCarbonPoreModel(pore_radius_angstrom=radius_angstrom).real_radius_angstrom)
    except Exception:
        return float(radius_angstrom)


def extract_replica_label(path: Path) -> str:
    m = re.search(r"_r([^/_]+)\.csv(?:\.gz)?$", path.name)
    if m:
        return m.group(1)
    return path.stem


def first_crossing_time(df: pd.DataFrame, threshold_percent: float) -> float | None:
    if df.empty:
        return None

    d = df[["Time", "Filling"]].dropna().sort_values("Time")
    if d.empty:
        return None

    t = d["Time"].to_numpy(dtype=float)
    f = d["Filling"].to_numpy(dtype=float)

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
                matched.extend(Path(d).glob(f"{args.defect_density}_{int(R_nom)}A_{int(T)}K_r*.csv.gz"))
                matched.extend(Path(d).glob(f"{args.defect_density}_{int(R_nom)}A_{int(T)}K_r*.csv"))

            matched = sorted(set(matched))
            R_true = try_true_radius_angstrom(float(R_nom))

            for fpath in matched:
                try:
                    df = pd.read_csv(fpath, names=names, skiprows=1)
                    print(fpath)
                except Exception as exc:
                    print(f"WARNING: could not read {fpath}: {exc}")
                    continue

                tf = first_crossing_time(df, args.threshold)
                if tf is None:
                    if args.keep_unfilled:
                        rows.append({
                            "temperature_K": float(T),
                            "radius_nominal_A": float(R_nom),
                            "radius_real_A": R_true,
                            "replica": extract_replica_label(fpath),
                            "file": str(fpath),
                            "fill_time": np.nan,
                            "reached_threshold": False,
                        })
                    continue

                rows.append({
                    "temperature_K": float(T),
                    "radius_nominal_A": float(R_nom),
                    "radius_real_A": R_true,
                    "replica": extract_replica_label(fpath),
                    "file": str(fpath),
                    "fill_time": float(tf),
                    "reached_threshold": True,
                })

            if args.verbose:
                print(f"T={T:g} K, R={R_nom:g} A: {len(matched)} files")

    raw = pd.DataFrame(rows)
    if raw.empty:
        raise SystemExit("No fill times found. Check --dirs, --defect-density, --temperatures, --radii, and --threshold.")

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


def choose_fit_radius(summary: pd.DataFrame, fit_radius: float | None) -> tuple[float, float]:
    if fit_radius is not None:
        dd = summary[np.isclose(summary["radius_nominal_A"], fit_radius)]
        if dd.empty:
            raise SystemExit(f"--fit-radius {fit_radius:g} A is not present in extracted data.")
        return float(dd["radius_nominal_A"].iloc[0]), float(dd["radius_real_A"].iloc[0])

    idx = summary["radius_real_A"].idxmax()
    return float(summary.loc[idx, "radius_nominal_A"]), float(summary.loc[idx, "radius_real_A"])


def fit_largest_radius(summary: pd.DataFrame, fit_radius_nominal: float, fit_radius_real: float) -> FitResult:
    dd = summary[np.isclose(summary["radius_nominal_A"], fit_radius_nominal)].copy()
    dd = dd[(dd["median"] > 0) & (dd["temperature_K"] > 0)]

    if len(dd) < 2:
        raise SystemExit("Need at least two temperatures for the fit radius.")

    T = dd["temperature_K"].to_numpy()
    R = dd["radius_real_A"].to_numpy()
    y = np.log(dd["median"].to_numpy() / (T * R ** 3))
    X = np.column_stack([np.ones(len(dd)), 1.0 / T])

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    logC, A_K = beta
    yhat = X @ beta
    rmse = float(np.sqrt(np.mean((y - yhat) ** 2)))

    return FitResult(
        logC=float(logC),
        A_K=float(A_K),
        fit_radius_nominal_A=fit_radius_nominal,
        fit_radius_real_A=fit_radius_real,
        rmse_log_fit_radius=rmse,
        n_fit_points=len(dd),
    )


def add_predictions(summary: pd.DataFrame, fit: FitResult) -> pd.DataFrame:
    out = summary.copy()
    T = out["temperature_K"].to_numpy()
    R = out["radius_real_A"].to_numpy()
    pred = np.exp(fit.logC) * R ** 3 * T * np.exp(fit.A_K / T)
    out["pred_largest_radius_fit_R3"] = pred
    out["log_residual_largest_radius_fit_R3"] = np.log(out["median"].to_numpy()) - np.log(pred)
    out["scaled_time_R3_T"] = out["median"] / (out["temperature_K"] * out["radius_real_A"] ** 3)
    out["scaled_time_remove_T"] = out["median"] / (out["temperature_K"] * np.exp(fit.A_K / out["temperature_K"]))
    return out


def save_fit_parameters(fit: FitResult, prefix: str) -> pd.DataFrame:
    df = pd.DataFrame([{
        "model": "largest_radius_fit_fixed_R3",
        "fit_radius_nominal_A": fit.fit_radius_nominal_A,
        "fit_radius_real_A": fit.fit_radius_real_A,
        "C": math.exp(fit.logC),
        "logC": fit.logC,
        "A_K": fit.A_K,
        "activation_energy_eV": fit.A_K * KB_EV_PER_K,
        "radius_power_p_fixed": 3.0,
        "rmse_log_fit_radius": fit.rmse_log_fit_radius,
        "n_fit_points": fit.n_fit_points,
    }])
    df.to_csv(f"{prefix}-largest-pore-fit-parameters.csv", index=False)
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
        label = f"{R_nom:g} A"
        if np.isclose(R_nom, fit.fit_radius_nominal_A):
            label += " fit"

        ax.errorbar(
            dd["temperature_K"], dd["median"],
            yerr=[yerr_low, yerr_high],
            fmt="o", capsize=2, color=color, label=label,
        )

        R_real = float(dd["radius_real_A"].iloc[0])
        pred = np.exp(fit.logC) * R_real ** 3 * Ts_grid * np.exp(fit.A_K / Ts_grid)
        ax.plot(Ts_grid, pred, "-", color=color, alpha=0.9)

    ax.set_xlabel("Temperature (K)")
    ax.set_ylabel("Fill time to threshold (MC steps)")
    ax.set_yscale("log")
    ax.set_title(f"Largest-pore fit: R = {fit.fit_radius_nominal_A:g} A, A = {fit.A_K:.0f} K")
    ax.legend(title="Nominal radius", ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-tfill-vs-temperature-largestfit.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-tfill-vs-temperature-largestfit.svg", bbox_inches="tight")
    plt.close(fig)


def plot_arrhenius_collapse(summary_fit: pd.DataFrame, fit: FitResult, prefix: str) -> None:
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
        label = f"{R_nom:g} A"
        if np.isclose(R_nom, fit.fit_radius_nominal_A):
            label += " fit"
        ax.plot(x, y, "o", color=color, label=label)

    ax.plot(invT_grid, fit.logC + fit.A_K * invT_grid, "-", color="black",
            label="fit from largest pore only")

    ax.set_xlabel("1/T (1/K)")
    ax.set_ylabel(r"log($t_{fill}/(T R^3)$)")
    ax.set_title("R^3 collapse tested using largest-pore temperature fit")
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-arrhenius-collapse-R3-largestfit.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-arrhenius-collapse-R3-largestfit.svg", bbox_inches="tight")
    plt.close(fig)


def plot_radius_scaling(summary_fit: pd.DataFrame, fit: FitResult, prefix: str) -> None:
    fig, ax = plt.subplots()
    cmap = mpl.colormaps["tab20"]
    temps = sorted(summary_fit["temperature_K"].unique())
    R_grid = np.linspace(summary_fit["radius_real_A"].min(), summary_fit["radius_real_A"].max(), 300)

    for i, T in enumerate(temps):
        dd = summary_fit[summary_fit["temperature_K"] == T].sort_values("radius_real_A")
        color = cmap(i % 20)
        y = dd["median"] / (T * np.exp(fit.A_K / T))
        ax.plot(dd["radius_real_A"], y, "o", color=color, label=f"{T:g} K")

    ax.plot(R_grid, np.exp(fit.logC) * R_grid ** 3, "-", color="black",
            label="R^3 prediction from largest pore")

    ax.set_xlabel("Real pore radius (A)")
    ax.set_ylabel(r"$t_{fill}/[T \exp(A/T)]$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Radius scaling after removing largest-pore temperature factor")
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-radius-scaling-largestfit.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-radius-scaling-largestfit.svg", bbox_inches="tight")
    plt.close(fig)


def plot_residuals(summary_fit: pd.DataFrame, fit: FitResult, prefix: str) -> None:
    fig, ax = plt.subplots()
    cmap = mpl.colormaps["tab20"]
    radii = sorted(summary_fit["radius_nominal_A"].unique())

    ax.axhline(0, color="black", linewidth=0.8)
    for i, R_nom in enumerate(radii):
        dd = summary_fit[summary_fit["radius_nominal_A"] == R_nom].sort_values("temperature_K")
        label = f"{R_nom:g} A"
        if np.isclose(R_nom, fit.fit_radius_nominal_A):
            label += " fit"
        ax.plot(dd["temperature_K"], dd["log_residual_largest_radius_fit_R3"],
                "o-", color=cmap(i % 20), label=label)

    ax.set_xlabel("Temperature (K)")
    ax.set_ylabel("log(data / largest-pore R^3 fit)")
    ax.set_title("Residuals relative to largest-pore fit")
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(f"{prefix}-residuals-largestfit.png", bbox_inches="tight")
    fig.savefig(f"{prefix}-residuals-largestfit.svg", bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dirs", nargs="+", default=["fix_samples_0V", "large_pore"],
                   help="Directories containing MC csv/csv.gz files.")
    p.add_argument("--defect-density", default="0.00",
                   help="Defect density prefix in filenames, e.g. 0.01 for 0.01_9A_2200K_r86.csv.gz.")
    p.add_argument("--temperatures", nargs="+", type=float,
                   default=[1600, 1700, 2000, 2200],
                   help="Temperatures in K.")
    p.add_argument("--radii", nargs="+", type=float,
                   default=[7, 8, 12, 15, 17, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100],
                   help="Nominal radii in A, matching filename convention.")
    p.add_argument("--fit-radius", type=float, default=None,
                   help="Nominal radius to use for fitting. Default: largest real radius.")
    p.add_argument("--threshold", type=float, default=99.0,
                   help="Filling percentage used to define fill time.")
    p.add_argument("--prefix", default=None,
                   help="Output prefix. Default is tfill-largestfit-dd<defect-density>-th<threshold>.")
    p.add_argument("--keep-unfilled", action="store_true",
                   help="Keep rows for trajectories that did not reach the threshold in the raw CSV.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.prefix is None:
        th = ("%g" % args.threshold).replace(".", "p")
        args.prefix = f"tfill-largestfit-dd{args.defect_density}-th{th}"

    raw = read_fill_times(args)
    summary = summarize(raw)

    if summary.empty:
        raise SystemExit("No trajectories reached the fill threshold.")

    fit_radius_nom, fit_radius_real = choose_fit_radius(summary, args.fit_radius)
    fit = fit_largest_radius(summary, fit_radius_nom, fit_radius_real)
    summary_fit = add_predictions(summary, fit)

    raw.to_csv(f"{args.prefix}-raw-fill-times.csv", index=False)
    summary_fit.to_csv(f"{args.prefix}-summary-fill-times.csv", index=False)
    fit_table = save_fit_parameters(fit, args.prefix)

    plot_tfill_vs_temperature(summary_fit, fit, args.prefix)
    plot_arrhenius_collapse(summary_fit, fit, args.prefix)
    plot_radius_scaling(summary_fit, fit, args.prefix)
    plot_residuals(summary_fit, fit, args.prefix)

    print("\nFit from largest pore only")
    print(fit_table.to_string(index=False))
    print("\nWrote:")
    for suffix in [
        "raw-fill-times.csv",
        "summary-fill-times.csv",
        "largest-pore-fit-parameters.csv",
        "tfill-vs-temperature-largestfit.png",
        "tfill-vs-temperature-largestfit.svg",
        "arrhenius-collapse-R3-largestfit.png",
        "arrhenius-collapse-R3-largestfit.svg",
        "radius-scaling-largestfit.png",
        "radius-scaling-largestfit.svg",
        "residuals-largestfit.png",
        "residuals-largestfit.svg",
    ]:
        print(f"  {args.prefix}-{suffix}")


if __name__ == "__main__":
    main()
