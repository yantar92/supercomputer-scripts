#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from pymatgen.io.vasp.inputs import Incar, Kpoints, Poscar
from pymatgen.io.vasp.outputs import Xdatcar


@dataclass(frozen=True)
class Settings:
    # Core
    encut: int = 550
    isif: int = 2
    ncore: int = 16
    prec: str = "Accurate"
    lasph: bool = True

    # Spin
    ispin: int = 2  # 2 = spin-polarized, 1 = non-spin

    # Symmetry (keep enabled; do NOT force ISYM=0)
    isym: int = 2

    # KPOINTS (length-based) with forced kc=1
    length_densities: tuple[float, float, float] = (50.0, 50.0, 1.0)

    # Ionic relaxation
    ibrion: int = 2
    nsw: int = 500
    potim: float = 0.5
    ediffg: float = -0.01

    # Electronic convergence (more robust for early frames)
    ediff: float = 1e-6
    nelmin: int = 8
    nelm: int = 100
    algo: str = "Normal"

    # Smearing
    ismear: int = 0
    sigma: float = 0.05

    # Outputs
    lcharg: bool = False
    lwave: bool = False


def find_xdatcars(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.name.lower().startswith("xdatcar")
    )


def _safe_auto_kpoints_by_lengths(structure, length_densities: tuple[float, float, float]) -> tuple[int, int, int]:
    try:
        kp = Kpoints.automatic_density_by_lengths(
            structure,
            length_densities=list(length_densities),
            force_gamma=True,
        )
        ka, kb, kc = kp.kpts[0]
        return max(1, int(ka)), max(1, int(kb)), max(1, int(kc))
    except TypeError:
        try:
            kp = Kpoints.automatic_density_by_lengths(structure, list(length_densities), True)
            ka, kb, kc = kp.kpts[0]
            return max(1, int(ka)), max(1, int(kb)), max(1, int(kc))
        except Exception:
            pass
    except AttributeError:
        pass

    rl = structure.lattice.reciprocal_lattice
    ba, bb, bc = rl.abc  # Å^-1
    da, db, dc = length_densities
    ka = max(1, int(round(da * ba)))
    kb = max(1, int(round(db * bb)))
    kc = max(1, int(round(dc * bc)))
    return ka, kb, kc


def kpoints_gamma_ab_c1(structure, length_densities: tuple[float, float, float]) -> Kpoints:
    ka, kb, _kc = _safe_auto_kpoints_by_lengths(structure, length_densities)
    return Kpoints.gamma_automatic(kpts=(ka, kb, 1))


def write_source_index(out_dir: Path, original_index: int) -> None:
    (out_dir / "SOURCE_FRAME_INDEX.txt").write_text(f"{original_index}\n", encoding="utf-8")


def write_final_note(out_dir: Path, xdatcar_path: Path) -> None:
    # Short, explicit traceability note
    (out_dir / "FINAL_NOTE.txt").write_text(
        "This folder was generated from the TRUE last frame in XDATCAR.\n"
        f"XDATCAR: {xdatcar_path}\n"
        "Source frame index is stored in SOURCE_FRAME_INDEX.txt\n",
        encoding="utf-8",
    )


def write_inputs(structure, out_dir: Path, settings: Settings, overwrite: bool) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)

    outcar_path = out_dir / "OUTCAR"
    if outcar_path.exists() and not overwrite:
        return False

    incar_path = out_dir / "INCAR"
    poscar_path = out_dir / "POSCAR"
    kpoints_path = out_dir / "KPOINTS"

    incar_dict: dict[str, object] = {
        "ENCUT": settings.encut,
        "ISIF": settings.isif,
        "NCORE": settings.ncore,
        "PREC": settings.prec,
        "LASPH": settings.lasph,

        # Electronic stability
        "EDIFF": settings.ediff,
        "NELMIN": settings.nelmin,
        "NELM": settings.nelm,
        "ALGO": settings.algo,
        "ISYM": settings.isym,

        # Ionic relaxation
        "IBRION": settings.ibrion,
        "NSW": settings.nsw,
        "POTIM": settings.potim,
        "EDIFFG": settings.ediffg,

        # Smearing
        "ISMEAR": settings.ismear,
        "SIGMA": settings.sigma,

        # Outputs
        "LCHARG": settings.lcharg,
        "LWAVE": settings.lwave,

        # Spin
        "ISPIN": settings.ispin,
    }

    Incar(incar_dict).write_file(str(incar_path))
    Poscar(structure).write_file(str(poscar_path))
    kpoints_gamma_ab_c1(structure, settings.length_densities).write_file(str(kpoints_path))
    return True


def build_selected_indices(n: int, start: int, stop: int | None, stride: int, from_last: bool) -> list[int]:
    start = max(0, start)
    stride = max(1, stride)

    if stop is None:
        stop = n
    stop = max(0, min(stop, n))

    if from_last:
        order = list(range(n - 1, -1, -1))  # last -> first
        return order[start:stop:stride]

    return list(range(start, stop, stride))


def write_set_for_one_xdatcar(
    xd_path: Path,
    structures,
    relax_dir_name: str,
    final_dir_name: str,
    settings: Settings,
    overwrite: bool,
    from_last: bool,
    start: int,
    stop: int | None,
    stride: int,
) -> tuple[int, int]:
    """
    Creates:
      <XDATCAR parent>/<relax_dir_name>/
         FINAL/                  (always true last frame)
         frame_000000/           (first in selected order; by default also last frame)
         frame_000001/
         ...

    Default (from_last=True):
      frame_000000 is the last XDATCAR frame, then older frames follow.
    """
    base_out = xd_path.parent / relax_dir_name
    base_out.mkdir(parents=True, exist_ok=True)

    n = len(structures)

    # Always write FINAL from the true last frame (n-1)
    final_dir = base_out / final_dir_name
    did_write_final = write_inputs(structures[-1], final_dir, settings, overwrite=overwrite)
    write_source_index(final_dir, n - 1)
    write_final_note(final_dir, xd_path)

    selected = build_selected_indices(n=n, start=start, stop=stop, stride=stride, from_last=from_last)

    written_here = 0
    skipped_here = 0

    for seq, src_i in enumerate(selected):
        frame_dir = base_out / f"frame_{seq:06d}"
        did_write = write_inputs(structures[src_i], frame_dir, settings, overwrite=overwrite)
        write_source_index(frame_dir, src_i)
        if did_write:
            written_here += 1
        else:
            skipped_here += 1

    return written_here, skipped_here


def main() -> None:
    ap = argparse.ArgumentParser()

    ap.add_argument("--root", type=str, default=".")
    ap.add_argument("--relax-dir-name", type=str, default="RELAX_ISIF2")
    ap.add_argument("--final-dir-name", type=str, default="FINAL")

    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--stop", type=int, default=None)

    # Default: final-first
    ap.add_argument("--from-last", action="store_true", default=True)
    ap.add_argument("--forward", action="store_true", default=False)

    ap.add_argument("--overwrite", action="store_true")

    ap.add_argument("--encut", type=int, default=550)
    ap.add_argument("--isif", type=int, default=2)
    ap.add_argument("--ncore", type=int, default=16)

    ap.add_argument("--ld-a", type=float, default=50.0)
    ap.add_argument("--ld-b", type=float, default=50.0)
    ap.add_argument("--ld-c", type=float, default=1.0)

    ap.add_argument("--nsw", type=int, default=500)
    ap.add_argument("--ibrion", type=int, default=2)
    ap.add_argument("--potim", type=float, default=0.5)
    ap.add_argument("--ediffg", type=float, default=-0.01)

    ap.add_argument("--ediff", type=float, default=1e-6)
    ap.add_argument("--nelmin", type=int, default=8)
    ap.add_argument("--nelm", type=int, default=200)
    ap.add_argument("--algo", type=str, default="Normal")

    ap.add_argument("--isym", type=int, default=2, help="Symmetry on by default (2).")

    ap.add_argument("--prec", type=str, default="Accurate")

    lasph_group = ap.add_mutually_exclusive_group()
    lasph_group.add_argument("--lasph", dest="lasph", action="store_true")
    lasph_group.add_argument("--no-lasph", dest="lasph", action="store_false")
    ap.set_defaults(lasph=True)

    ap.add_argument("--ismear", type=int, default=0)
    ap.add_argument("--sigma", type=float, default=0.05)

    ap.add_argument("--lcharg", action="store_true", default=False)
    ap.add_argument("--lwave", action="store_true", default=False)

    args = ap.parse_args()
    from_last = bool(args.from_last) and not bool(args.forward)

    base_settings = Settings(
        encut=args.encut,
        isif=args.isif,
        ncore=args.ncore,
        isym=args.isym,
        length_densities=(args.ld-a, args.ld-b, args.ld-c) if False else (args.ld_a, args.ld_b, args.ld_c),  # keep robust

        ibrion=args.ibrion,
        nsw=args.nsw,
        potim=args.potim,
        ediffg=args.ediffg,

        ediff=args.ediff,
        nelmin=args.nelmin,
        nelm=args.nelm,
        algo=args.algo,

        prec=args.prec,
        lasph=args.lasph,

        ismear=args.ismear,
        sigma=args.sigma,

        lcharg=args.lcharg,
        lwave=args.lwave,
    )

    spin_settings = replace(base_settings, ispin=2)
    nospin_settings = replace(base_settings, ispin=1)

    root = Path(args.root).resolve()
    xdatcars = find_xdatcars(root)
    if not xdatcars:
        print(f"No XDATCAR files found under {root}")
        return

    print(f"Found {len(xdatcars)} XDATCAR file(s) under {root}")

    total_written = 0
    total_skipped = 0

    for xd_path in xdatcars:
        try:
            xd = Xdatcar(str(xd_path))
            structures = xd.structures
        except Exception as exc:
            print(f"[error] Could not parse {xd_path}: {exc}")
            continue

        if not structures:
            print(f"[skip] No frames in {xd_path}")
            continue

        for label, s in (("SPIN", spin_settings), ("NOSPIN", nospin_settings)):
            relax_dir = f"{args.relax_dir_name}_{label}"
            written_here, skipped_here = write_set_for_one_xdatcar(
                xd_path=xd_path,
                structures=structures,
                relax_dir_name=relax_dir,
                final_dir_name=args.final_dir_name,
                settings=s,
                overwrite=args.overwrite,
                from_last=from_last,
                start=args.start,
                stop=args.stop,
                stride=args.stride,
            )
            total_written += written_here
            total_skipped += skipped_here
            mode = "from last (final-first)" if from_last else "forward"
            print(f"[ok] {xd_path} -> {xd_path.parent / relax_dir} [{mode}] (written: {written_here}, skipped: {skipped_here})")

    print(f"Done. Written: {total_written}, skipped: {total_skipped}")


if __name__ == "__main__":
    main()
