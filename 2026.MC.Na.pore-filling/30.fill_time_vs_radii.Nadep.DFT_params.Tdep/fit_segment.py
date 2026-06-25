#!/usr/bin/env python3
"""
Fit Gusak-Yarmolenko pore-filling theory to segments of the
filling-ratio-vs-time curve.

Theory (spherical diffusion-controlled shrinking core, V=0):
    tau(f) = 1 - (1-f)^(3/2) * [1 + 3*ln(1/sqrt(1-f))]
    t      = K * R_eff^3 * tau(f)

Two modes:
  1. Single-segment fit:
       python fit_segment.py DATA.csv --fmin 20 --fmax 85
  2. Systematic scan:
       python fit_segment.py DATA.csv --scan
       python fit_segment.py DATA.csv --scan --scan-fmin 5,10,15,20,25,30 --scan-fmax 80,85,90

The scan ranks all combinations by R-squared, computes effective radius
against a reference full-range fit, and optionally shows an R-squared
plateau analysis to identify where diffusion control onsets.
"""

import numpy as np
from scipy.optimize import curve_fit
import pandas as pd
import sys
import os


# ═══════════════════════════════════════════════════════════
#  Theory
# ═══════════════════════════════════════════════════════════

def theory_tau(filling):
    """Dimensionless time tau(f) for 0 < filling < 1."""
    f = np.asarray(filling, dtype=float)
    eps = 1e-12
    f = np.clip(f, eps, 1 - eps)
    val = (1 - f) ** 1.5 * (1 + 3 * np.log(1 / np.sqrt(1 - f)))
    return 1 - val


# ═══════════════════════════════════════════════════════════
#  Data
# ═══════════════════════════════════════════════════════════

def load_data(csv_paths):
    """Read one or more MC pore-filling CSV files.

    If multiple files are given, interpolates all runs to the MCS grid
    of the first file and returns the pointwise median (time, filling_pct).
    """
    dfs = [pd.read_csv(p) for p in csv_paths]

    if len(dfs) == 1:
        return (dfs[0]['mcs'].values.astype(float),
                dfs[0]['filling_pct'].values.astype(float))

    mcs_ref = dfs[0]['mcs'].values.astype(float)
    fills = np.zeros((len(mcs_ref), len(dfs)))
    fills[:, 0] = dfs[0]['filling_pct'].values.astype(float)

    for i, df in enumerate(dfs[1:], 1):
        mcs_i = df['mcs'].values.astype(float)
        fill_i = df['filling_pct'].values.astype(float)
        fills[:, i] = np.interp(mcs_ref, mcs_i, fill_i)

    median_fill = np.median(fills, axis=1)
    return mcs_ref, median_fill


# ═══════════════════════════════════════════════════════════
#  Single-segment fit
# ═══════════════════════════════════════════════════════════

def fit_segment(time, filling_pct, f_min, f_max, fit_t0=False):
    """Fit  t = t_ref + A * (tau(f/100) - tau(f_min/100))  on [f_min, f_max].

    Returns dict with keys A, A_std, t_ref, t_ref_std, R2, AICc, etc.,
    or None if the fit fails.
    """
    fratio = filling_pct / 100.0
    mask = (filling_pct >= f_min) & (filling_pct <= f_max)
    n = mask.sum()
    if n < 20:
        return None

    t_seg = time[mask]
    fs = fratio[mask]
    fs_full = fratio[(filling_pct >= f_min)]
    t_ref_interp = np.interp(f_min / 100.0, fratio, time)
    f_min_r = f_min / 100.0
    tau_min = theory_tau(f_min_r)

    # Initial A guess from midpoint
    mid = n // 2
    tau_d = theory_tau(fs[mid]) - tau_min
    A0 = (t_seg[mid] - t_ref_interp) / tau_d if abs(tau_d) > 1e-15 else 1e5

    if fit_t0:
        def model(fr, t0, A):
            return t0 + A * (theory_tau(fr) - tau_min)
        p0 = [t_ref_interp, A0]
    else:
        t_ref = t_ref_interp
        def model(fr, A):
            return t_ref + A * (theory_tau(fr) - tau_min)
        p0 = [A0]

    try:
        popt, pcov = curve_fit(model, fs, t_seg, p0=p0, maxfev=20000)
    except RuntimeError:
        return None

    if fit_t0:
        t_ref_fit, A = popt
        t_ref_std = np.sqrt(max(pcov[0, 0], 0))
        A_std = np.sqrt(max(pcov[1, 1], 0))
    else:
        t_ref_fit = t_ref_interp
        t_ref_std = 0.0
        A = popt[0]
        A_std = np.sqrt(max(pcov[0, 0], 0))

    t_pred = t_ref_fit + A * (theory_tau(fs) - tau_min)
    # predict all the way up to 100%
    t_pred_full = t_ref_fit + A * (theory_tau(fs_full) - tau_min)
    ss_res = np.sum((t_seg - t_pred) ** 2)
    ss_tot = np.sum((t_seg - np.mean(t_seg)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0

    k = 2 if fit_t0 else 1
    aicc = (n * np.log(max(ss_res / n, 1e-15))
            + 2 * k
            + (2 * k * (k + 1)) / max(n - k - 1, 1))

    return {
        'f_min': f_min, 'f_max': f_max, 'n': n,
        't_ref': t_ref_fit, 't_ref_std': t_ref_std,
        'A': A, 'A_std': A_std, 'R2': r2, 'AICc': aicc,
        't_seg': t_seg, 'f_seg': filling_pct[mask], 't_pred': t_pred,
        'fs_full': fs_full * 100.0, 't_pred_full': t_pred_full,
    }


# ═══════════════════════════════════════════════════════════
#  Scan
# ═══════════════════════════════════════════════════════════

def scan(time, filling_pct, f_mins, f_maxs, fit_t0=False,
         A_ref=None, pore_radius=100.0, r2_threshold=0.99):
    """Fit all (f_min, f_max) combinations, rank by a combined score.

    Ranking: segments with R² >= r2_threshold come first, sorted by
    number of points (n) descending -- a slightly worse fit that covers
    many more points is preferred.  Segments below the threshold come
    after, sorted by R² descending as usual.

    If A_ref is None, it is computed from a 5-99% full-range fit.
    """
    if A_ref is None:
        ref = fit_segment(time, filling_pct, 5, 99, fit_t0=fit_t0)
        A_ref = ref['A'] if ref else None
        if A_ref:
            print(f"# Reference A (5-99% fit) = {A_ref:.1f} MCS\n")
        else:
            print("# Reference fit failed\n")

    results = []
    for fmn in f_mins:
        for fmx in f_maxs:
            if fmn >= fmx:
                continue
            r = fit_segment(time, filling_pct, fmn, fmx, fit_t0=fit_t0)
            if r is None:
                continue
            r['A_per_R3'] = r['A'] / (pore_radius ** 3)
            r['R_eff'] = (pore_radius * (r['A'] / A_ref) ** (1 / 3)
                          if A_ref else None)
            results.append(r)

    if not results:
        print("# No valid fits -- check f_min/f_max ranges.")
        return results

    # Two-tier sort: above threshold by n desc, below by R2 desc
    above = [r for r in results if r['R2'] >= r2_threshold]
    below = [r for r in results if r['R2'] < r2_threshold]
    above.sort(key=lambda x: x['n'], reverse=True)
    below.sort(key=lambda x: x['R2'], reverse=True)
    results = above + below
    return results


def print_scan_table(results, top_n=None, r2_threshold=None):
    """Print ranked table of scan results.

    If r2_threshold is given, a blank line separates the above-threshold
    tier (ranked by n_pts) from the below-threshold tier.
    """
    if top_n is None:
        top_n = len(results)
    header = (f"{'Rank':>4s}  {'f_min%':>6s} {'f_max%':>6s} {'n_pts':>7s}  "
              f"{'A':>10s}  {'A_std':>8s}  {'R²':>10s}  "
              f"{'R_eff':>7s}  {'AICc':>10s}")
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    prev_above = None
    shown = 0
    for i, r in enumerate(results, 1):
        if shown >= top_n:
            break
        is_above = r2_threshold is not None and r['R2'] >= r2_threshold
        if prev_above is True and not is_above:
            print()  # blank separator between tiers
        prev_above = is_above
        reff = f"{r['R_eff']:7.1f}" if r.get('R_eff') is not None else "     --"
        print(f"{i:4d}  {r['f_min']:6.1f} {r['f_max']:6.1f} {r['n']:7d}  "
              f"{r['A']:10.1f}  {r['A_std']:8.1f}  {r['R2']:10.6f}  "
              f"{reff}  {r['AICc']:10.1f}")
        shown += 1
    print(sep)
    print(f"{len(results)} combinations tested.")


def print_plateau_analysis(results, f_max, sort_by='f_min'):
    """For a fixed f_max, show R-squared vs f_min to find the plateau.

    The point where dR2 flattens indicates where diffusion control begins.
    """
    subset = [r for r in results if r['f_max'] == f_max]
    subset.sort(key=lambda x: x[sort_by])
    if not subset:
        print(f"# No results for f_max={f_max}")
        return

    print(f"\n{'=' * 80}")
    print(f"  R² plateau analysis at f_max = {f_max}%")
    print(f"{'=' * 80}")
    hdr = (f"{'f_min':>6s} {'n':>7s}  "
           f"{'A':>10s}  {'R²':>10s}  {'ΔR²':>10s}  "
           f"{'R_eff':>7s}  {'AICc':>10s}")
    sep = "-" * len(hdr)
    print(hdr)
    print(sep)

    prev_r2 = None
    for r in subset:
        dr2 = r['R2'] - prev_r2 if prev_r2 is not None else float('nan')
        dr2_str = f"{dr2:10.6f}" if not np.isnan(dr2) else "        --"
        reff = f"{r['R_eff']:7.1f}" if r.get('R_eff') is not None else "     --"
        print(f"{r['f_min']:6.1f} {r['n']:7d}  "
              f"{r['A']:10.1f}  {r['R2']:10.6f}  {dr2_str}  "
              f"{reff}  {r['AICc']:10.1f}")
        prev_r2 = r['R2']
    print(sep)


# ═══════════════════════════════════════════════════════════
#  Plots
# ═══════════════════════════════════════════════════════════


def _compute_xlim(time, filling_pct, threshold=99.0, margin=0.10):
    """Return right x-limit: first time where filling hits threshold, +margin%.

    If the threshold is never reached, returns None (no limit applied).
    """
    idx = np.argmax(filling_pct >= threshold)
    if idx == 0 and filling_pct[0] < threshold:
        return None
    t_hit = time[idx]
    return t_hit * (1 + margin)


def make_single_plot(result, time_full, filling_full, output_path,
                     fill_threshold=99.0):
    """Two-panel diagnostic plot for a single fit."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # Full curve + segment
    ax1.plot(time_full, filling_full, 'b-', lw=0.2, alpha=0.5)
    ax1.axvspan(result['t_seg'][0], result['t_seg'][-1],
                alpha=0.15, color='orange')
    ax1.axvline(result['t_ref'], color='red', ls='--', lw=1,
                label=f"t_ref={result['t_ref']:.1f}")
    ax1.set_xlabel('Time (MCS)')
    ax1.set_ylabel('Filling (%)')
    ax1.set_title('Full trajectory')
    ax1.legend(fontsize=8)

    # Segment zoom
    ax2.plot(result['t_seg'], result['f_seg'], 'bo', ms=2, alpha=0.6)
    ax2.plot(result['t_pred_full'], result['fs_full'], 'r-', lw=2,
             label=f"A={result['A']:.1f}, R²={result['R2']:.5f}")
    ax2.set_xlabel('Time (MCS)')
    ax2.set_ylabel('Filling (%)')
    ax2.set_title(f"Segment [{result['f_min']}%, {result['f_max']}%]")
    ax2.legend(fontsize=8)

    # Limit x-axis to threshold point + 10%
    xlim = _compute_xlim(time_full, filling_full, threshold=fill_threshold)
    if xlim is not None:
        ax1.set_xlim(0, right=xlim)
        ax2.set_xlim(0, right=xlim)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close()
    print(f"  Plot saved to {output_path}")


def make_scan_plot(results, time_full, filling_full, output_path,
                   fill_threshold=99.0):
    """Summary plot for scan mode: R² heatmap + best-fit overlay."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    # --- (0,0): R² heatmap ---
    ax = axes[0, 0]
    f_mins = sorted(set(r['f_min'] for r in results))
    f_maxs = sorted(set(r['f_max'] for r in results), reverse=True)
    r2_grid = np.full((len(f_maxs), len(f_mins)), np.nan)
    for r in results:
        i = f_maxs.index(r['f_max'])
        j = f_mins.index(r['f_min'])
        r2_grid[i, j] = r['R2']
    im = ax.imshow(r2_grid, aspect='auto', origin='upper',
                   cmap='RdYlGn', vmin=0.8, vmax=1.0)
    ax.set_xticks(range(len(f_mins)))
    ax.set_xticklabels([str(int(f)) for f in f_mins])
    ax.set_yticks(range(len(f_maxs)))
    ax.set_yticklabels([str(int(f)) for f in f_maxs])
    ax.set_xlabel('f_min (%)')
    ax.set_ylabel('f_max (%)')
    ax.set_title('R² (green = better)')
    plt.colorbar(im, ax=ax, shrink=0.8)

    # --- (0,1): A vs f_min for each f_max ---
    ax = axes[0, 1]
    for fmx in sorted(set(r['f_max'] for r in results)):
        pts = [(r['f_min'], r['A']) for r in results if r['f_max'] == fmx]
        pts.sort()
        if pts:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, 'o-', ms=4, label=f"f_max={fmx:.0f}")
    ax.set_xlabel('f_min (%)')
    ax.set_ylabel('A (MCS)')
    ax.set_title('Fitted A vs f_min')
    ax.legend(fontsize=7)

    # --- (1,0): R² vs f_min for each f_max ---
    ax = axes[1, 0]
    for fmx in sorted(set(r['f_max'] for r in results)):
        pts = [(r['f_min'], r['R2']) for r in results if r['f_max'] == fmx]
        pts.sort()
        if pts:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, 'o-', ms=4, label=f"f_max={fmx:.0f}")
    ax.set_xlabel('f_min (%)')
    ax.set_ylabel('R²')
    ax.set_title('R² vs f_min')
    ax.legend(fontsize=7)

    # --- (1,1): Top-N fits overlaid on data ---
    topN = 5
    ax = axes[1, 1]
    ax.plot(time_full, filling_full, 'b-', lw=0.2, alpha=0.5)
    best = results[:topN]
    colors = ['red', 'orange', 'magenta', 'cyan', 'purple']
    for r, c in zip(best, colors):
        ax.axvspan(r['t_seg'][0], r['t_seg'][-1], alpha=0.08, color=c)
        ax.plot(r['t_pred_full'], r['fs_full'], color=c, lw=1.5,
                label=f"f_min={r['f_min']:.0f}, f_max={r['f_max']:.0f} "
                      f"(R²={r['R2']:.4f})")
    ax.set_xlabel('Time (MCS)')
    ax.set_ylabel('Filling (%)')
    ax.set_title(f'Top-{topN} fits overlaid')
    ax.legend(fontsize=7)

    # Limit x-axis to threshold point + 10%
    xlim = _compute_xlim(time_full, filling_full, threshold=fill_threshold)
    if xlim is not None:
        ax.set_xlim(0, right=xlim)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close()
    print(f"  Plot saved to {output_path}")


# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

def main():
    import argparse

    p = argparse.ArgumentParser(
        description='Fit pore-filling theory to MC trajectory segments.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single segment
  %(prog)s data.csv --fmin 20 --fmax 85
  %(prog)s data.csv --fmin 20 --fmax 85 --fit-t0
  %(prog)s data.csv --fmin 20 --fmax 85 --plot-dir ./plots

  # Multiple runs → pointwise median
  %(prog)s run1.csv run2.csv run3.csv --fmin 20 --fmax 85

  # Systematic scan
  %(prog)s data.csv --scan --plot-dir ./plots

  # Scan with custom ranges
  %(prog)s data.csv --scan --scan-fmin 5,15,25,35,45 --scan-fmax 80,85,90

  # Scan + plateau analysis at a specific f_max
  %(prog)s data.csv --scan --plateau-fmax 85

  # Scan with two-tier ranking (default threshold 0.99)
  %(prog)s data.csv --scan --scan-r2-threshold 0.995

  # Disable two-tier ranking (pure R² sort)
  %(prog)s data.csv --scan --scan-r2-threshold 0
        """)

    p.add_argument('csv', nargs='+',
                   help='Path(s) to CSV (columns: mcs, filling_pct). '
                        'Multiple files are combined via pointwise median.')

    # Single-fit args
    p.add_argument('--fmin', type=float, default=None,
                   help='Minimum filling %% for segment (0-100)')
    p.add_argument('--fmax', type=float, default=None,
                   help='Maximum filling %% for segment (0-100)')
    p.add_argument('--fit-t0', action='store_true',
                   help='Fit t_ref as free parameter')

    # Scan args
    p.add_argument('--scan', action='store_true',
                   help='Run systematic scan over f_min/f_max combinations')
    p.add_argument('--scan-fmin', type=str, default=None,
                   help='Comma-separated f_min values '
                        '(default: 1,2,5,10,15,20,25,30,35,40,45,50)')
    p.add_argument('--scan-fmax', type=str, default=None,
                   help='Comma-separated f_max values '
                        '(default: 80,85,90,95,99)')
    p.add_argument('--top', type=int, default=20,
                   help='Show top N combinations in scan (default: 20)')
    p.add_argument('--scan-r2-threshold', type=float, default=0.99,
                   help='R² threshold for two-tier ranking: segments '
                        'above this are ranked by n_pts descending; '
                        'below are ranked by R² (default: 0.99)')
    p.add_argument('--plateau-fmax', type=float, default=None,
                   help='Show R² plateau analysis at this f_max')

    # Common args
    p.add_argument('--radius', type=float, default=100.0,
                   help='Nominal pore radius in Angstrom (default: 100)')
    p.add_argument('--A-ref', type=float, default=None,
                   help='Reference A for R_eff calculation '
                        '(default: from 5-99%% fit)')
    p.add_argument('--plot-dir', type=str, default=None,
                   help='Directory to save diagnostic plot(s)')

    args = p.parse_args()

    # ── Load ──
    time, filling_pct = load_data(args.csv if isinstance(args.csv, list) else [args.csv])

    # ── Mode dispatch ──
    if args.scan:
        if args.scan_fmin:
            f_mins = [float(x) for x in args.scan_fmin.split(',')]
        else:
            f_mins = [1, 2, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        if args.scan_fmax:
            f_maxs = [float(x) for x in args.scan_fmax.split(',')]
        else:
            f_maxs = [80, 85, 90, 95, 99]

        results = scan(time, filling_pct, f_mins, f_maxs,
                       fit_t0=args.fit_t0, A_ref=args.A_ref,
                       pore_radius=args.radius,
                       r2_threshold=args.scan_r2_threshold)

        if not results:
            sys.exit(1)

        print(f"# R² threshold for tier ranking: {args.scan_r2_threshold}\n")
        print_scan_table(results, top_n=args.top,
                         r2_threshold=args.scan_r2_threshold)

        if args.plateau_fmax is not None:
            print_plateau_analysis(results, args.plateau_fmax)

        if args.plot_dir:
            os.makedirs(args.plot_dir, exist_ok=True)
            make_scan_plot(results, time, filling_pct,
                           os.path.join(args.plot_dir, 'scan_summary.png'))

    elif args.fmin is not None and args.fmax is not None:
        if not (0 <= args.fmin < args.fmax <= 100):
            p.error("Require 0 <= fmin < fmax <= 100")

        result = fit_segment(time, filling_pct, args.fmin, args.fmax,
                             fit_t0=args.fit_t0)
        if result is None:
            print(f"Fit failed for f_min={args.fmin}, f_max={args.fmax}")
            sys.exit(1)

        # Reference A for R_eff
        if args.A_ref is not None:
            A_ref = args.A_ref
        else:
            ref = fit_segment(time, filling_pct, 5, 99)
            A_ref = ref['A'] if ref else None
        R_eff = (args.radius * (result['A'] / A_ref) ** (1 / 3)
                 if A_ref else None)

        print(f"\n  f_min          = {result['f_min']} %")
        print(f"  f_max          = {result['f_max']} %")
        print(f"  n_points       = {result['n']}")
        print(f"  t_ref          = {result['t_ref']:.2f} MCS")
        if result['t_ref_std'] > 0:
            print(f"  t_ref std      = {result['t_ref_std']:.2f} MCS")
        print(f"  A              = {result['A']:.2f} "
              f"+/- {result['A_std']:.2f} MCS")
        print(f"  A / R_nom^3    = "
              f"{result['A'] / args.radius**3:.6f} MCS/A^3")
        print(f"  R-squared      = {result['R2']:.6f}")
        print(f"  AICc           = {result['AICc']:.1f}")
        if R_eff is not None:
            print(f"  A_ref          = {A_ref:.2f} MCS")
            print(f"  R_eff          = {R_eff:.2f} A")
            print(f"  R_eff / R_nom  = {R_eff / args.radius:.4f}")

        if args.plot_dir:
            os.makedirs(args.plot_dir, exist_ok=True)
            fstem = f"fit_fmin{result['f_min']:.0f}_fmax{result['f_max']:.0f}"
            make_single_plot(result, time, filling_pct,
                             os.path.join(args.plot_dir, fstem + '.png'))

    else:
        p.error("Either use --scan or provide both --fmin and --fmax.")


if __name__ == '__main__':
    main()
