#!/usr/bin/env python3
"""Watch ATAT output and generate new
structures using emc2 instead of built-in maps enumeration.
"""
import hashlib
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
from IMDgroup.pymatgen.core.structure import IMDStructure as Structure

# =============================================================================
# CONFIG (edit as needed)
# =============================================================================
EMC2 = "emc2"
PARALLEL = "parallel"
PARALLEL_JOBS = int(os.environ.get("MC_WORKERS", "96"))

# Stop and refresh file names
STOP_FILE = "stop"
REFRESH_FILE = "refresh"

# Candidate directory + archival naming
OUT_DIR = Path("mc_candidates")
ARCHIVED_NAME = "emc2_snapshot.out"

# MAPS outputs that trigger
TRIGGER_FILES = ["clusters.out", "eci.out", "gs_str.out"]
REQUIRED_FILES = ["clusters.out", "lat.in", "gs_str.out", "eci.out", "mcsupcel.in"]

# New structure folder numbering
START_INDEX = 1000

# Candidate file prefix
CAND_GLOB_PREFIX = "gs"  # filenames start with gs{tag}_...

# Always move processed candidates
MOVE_PROCESSED = True

# Optional: keep original snapshot filename in the numeric folder too
COPY_ORIGINAL_NAME = True

# Script to run DFT
DFT_SCRIPT = ["run_all.py", "--local"]

# ---- emc2 schedule: inverse temperature stepping with -db ----
T0 = 2000
T1 = 10
DB = 0.005  # smaller => more T points
# DB = 0.05  # smaller => more T points

# Explicit equilibration + sampling (do NOT use -dx)
EQ = 8000
N = 40000

# ---- μ grid: ends + midpoints + boundaries (always on) ----
EPS_BOUNDARY = 0.03

# Seeds per μ (random + anchored)
DO_RANDOM = True
DO_ANCHORED = True

# Polling / stability
POLL_S = 5
STABLE_FOR_S = 10

# Internal dirs
RUNS_DIR = Path("mc_runs")
LOCKFILE = Path(".mc_proposer.lock")


# =============================================================================
# Utility
# =============================================================================
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_is_stable(path: Path, stable_for_s: int) -> bool:
    if not path.exists():
        return False
    size0 = path.stat().st_size
    t0 = time.time()
    while time.time() - t0 < stable_for_s:
        time.sleep(1)
        if not path.exists():
            return False
        if path.stat().st_size != size0:
            size0 = path.stat().st_size
            t0 = time.time()
    return True


def acquire_lock() -> bool:
    if LOCKFILE.exists():
        return False
    LOCKFILE.write_text(str(os.getpid()))
    return True


def release_lock():
    try:
        LOCKFILE.unlink()
    except FileNotFoundError:
        pass


def ensure_required_present(workdir: Path) -> None:
    missing = [f for f in REQUIRED_FILES if not (workdir / f).exists()]
    if missing:
        raise RuntimeError(f"Missing required files for emc2: {missing}. Need {REQUIRED_FILES}.")


def count_ground_states_from_gs_out(gs_out: Path) -> int:
    n = 0
    for line in gs_out.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        n += 1
    return n


def build_mu_list(G: int) -> List[float]:
    """
    Always: ends (-0.5, G-0.5), midpoints (i+0.5), boundaries (i±eps).
    """
    mus = set()
    mus.add(-0.5)
    mus.add(G - 0.5)
    for i in range(G):
        mus.add(i + 0.5)
        mus.add(i - EPS_BOUNDARY)
        mus.add(i + EPS_BOUNDARY)
    return sorted(mus)


def pick_anchored_index(mu: float, G: int) -> int:
    # midpoints i+0.5 -> i; boundaries near i -> i; clamp
    i = int(mu) if mu >= 0 else 0
    return max(0, min(G - 1, i))


def deterministic_seed(tag: str, mu: float, kind: str, idx: int) -> int:
    s = f"{tag}|{mu:.6f}|{kind}|{idx}"
    # 31-bit int
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16) & 0x7FFFFFFF


def snapshot_inputs(workdir: Path, tag: str) -> Path:
    run_root = RUNS_DIR / f"run_{tag}"
    run_root.mkdir(parents=True, exist_ok=True)
    for f in REQUIRED_FILES:
        shutil.copy2(workdir / f, run_root / f)
    return run_root


def stable_trigger_files(workdir: Path) -> bool:
    for f in TRIGGER_FILES:
        p = workdir / f
        if p.exists() and (not file_is_stable(p, STABLE_FOR_S)):
            return False
    return True


# =============================================================================
# GNU parallel job generation
# =============================================================================
def write_jobs_file(jobs_path: Path, run_root: Path, tag: str, mu_list: List[float], G: int):
    """
    One job per (mu, seed-kind). Each job runs in its own subdir, symlinks required files,
    runs emc2 with -db, writes a single -oss snapshot into mc_candidates.
    """
    run_root_abs = run_root.resolve()
    out_abs = OUT_DIR.resolve()

    lines = []

    def add_job(mu: float, idx: int, kind: str):
        # idx = -1 for random, else ground-state index
        seed = deterministic_seed(tag, mu, kind, idx if idx >= 0 else 0)
        if idx == -1:
            suffix = "_rnd"
        else:
            suffix = f"_gs{idx:03d}"
        outname = f"gs{tag}_mu{mu:+.6f}{suffix}.out".replace("+", "p").replace("-", "m")
        wdir = (run_root_abs / f"mu_{mu:+.6f}{suffix}").as_posix()
        cmd = (
            f'bash -lc \'set -euo pipefail; '
            f'wdir="{wdir}"; '
            f'mkdir -p "$wdir"; '
            f'ln -sf "{run_root_abs}/clusters.out" "$wdir/clusters.out"; '
            f'ln -sf "{run_root_abs}/lat.in" "$wdir/lat.in"; '
            f'ln -sf "{run_root_abs}/gs_str.out" "$wdir/gs_str.out"; '
            f'ln -sf "{run_root_abs}/eci.out" "$wdir/eci.out"; '
            f'ln -sf "{run_root_abs}/mcsupcel.in" "$wdir/mcsupcel.in"; '
            f'cd "$wdir"; '
            f'"{EMC2}" -mu0={mu} -gs={idx} -sd={seed} -T0={T0} -T1={T1} -db={DB} -eq={EQ} -n={N} -q -oss="{outname}"; '
            f'mv -f "{outname}" "{out_abs}/{outname}";\''
        )
        lines.append(cmd)

    for mu in mu_list:
        if DO_RANDOM:
            add_job(mu, -1, "random")
        if DO_ANCHORED:
            idx = pick_anchored_index(mu, G)
            add_job(mu, idx, "anchored")

    jobs_path.write_text("\n".join(lines) + "\n")


def run_parallel(jobs_path: Path):
    OUT_DIR.mkdir(exist_ok=True)
    # GNU parallel may require `parallel --will-cite` once on the machine.
    cmd = f'{PARALLEL} --jobs={PARALLEL_JOBS} --lb < "{jobs_path}"'
    subprocess.run(cmd, shell=True, check=True)


# =============================================================================
# Staging / dedupe by hash vs prior generations
# =============================================================================
def numeric_dirs(root: Path, start_at: int) -> List[Path]:
    out = []
    for d in root.iterdir():
        if d.is_dir() and d.name.isdigit() and int(d.name) >= start_at:
            out.append(d)
    out.sort(key=lambda x: int(x.name))
    return out


def next_numeric_dir(root: Path, start_at: int) -> Path:
    ds = numeric_dirs(root, start_at)
    if not ds:
        return root / str(start_at)
    return root / str(int(ds[-1].name) + 1)


def archived_hashes(root: Path, start_at: int) -> Dict[str, Path]:
    """
    hash -> path for all previously archived snapshots (*/emc2_snapshot.out) in numeric dirs >= start_at
    """
    hmap: Dict[str, Path] = {}
    for d in numeric_dirs(root, start_at):
        p = d / ARCHIVED_NAME
        if p.exists():
            try:
                hmap[sha256_file(p)] = p
            except Exception:
                pass
    return hmap


def stage_candidates(root: Path, tag: str) -> int:
    """
    Returns number of newly staged unique structures.
    """
    candidates = sorted(OUT_DIR.glob(f"{CAND_GLOB_PREFIX}{tag}_*.out"))
    if not candidates:
        print("[stage] No candidates found for this generation.")
        return 0

    # Deduplicate within batch
    seen_new = set()
    batch_unique: List[Tuple[Path, str]] = []
    for p in candidates:
        h = sha256_file(p)
        if h in seen_new:
            continue
        seen_new.add(h)
        batch_unique.append((p, h))

    # Deduplicate vs prior archived
    old_hash_map = archived_hashes(root, START_INDEX)
    old_hashes = set(old_hash_map.keys())

    truly_new = [(p, h) for (p, h) in batch_unique if h not in old_hashes]

    # Move processed default: create processed_<tag> regardless of whether new unique found
    processed_dir = None
    if MOVE_PROCESSED:
        processed_dir = OUT_DIR / f"processed_{tag}"
        processed_dir.mkdir(parents=True, exist_ok=True)

    if not truly_new:
        print(f"[stage] {len(candidates)} candidates -> 0 new unique (all duplicates of previous generations).")
        if MOVE_PROCESSED:
            for p in candidates:
                shutil.move(str(p), str(processed_dir / p.name))
        return 0

    print(f"[stage] Found {len(truly_new)} new unique candidates.")

    # Create numeric dirs and archive snapshots
    next_dir = next_numeric_dir(root, START_INDEX)
    created = 0

    for p, h in truly_new:
        d = next_dir
        d.mkdir(parents=True, exist_ok=False)

        dst = d / ARCHIVED_NAME
        shutil.copy2(p, dst)
        if COPY_ORIGINAL_NAME:
            shutil.copy2(p, d / p.name)
        generate_strout(dst, root / "POSCAR")

        created += 1
        next_dir = root / str(int(d.name) + 1)

    print(f"[stage] Staged {created} structures into folders starting at {START_INDEX}.")

    # Move all candidates from this generation into processed_<tag> (default)
    if MOVE_PROCESSED:
        for p in candidates:
            shutil.move(str(p), str(processed_dir / p.name))

    return created


def generate_strout(mc_out: Path, base_poscar: Path):
    """Convert MC_OUT file to str.out in the same dir using BASE_POSCAR.
    """
    mc_structure = Structure.from_file(mc_out)
    base = Structure.from_file(base_poscar)
    new = base.copy()

    distance_threshold = 0.1

    # Get all atoms from s that you want to insert
    atoms_to_insert = []
    for site in mc_structure:
        atoms_to_insert.append({
            'species': site.species,
            'coords': site.frac_coords,
            'properties': site.properties
        })

    # Remove atoms from new that are too close to any atom in s
    indices_to_replace = []
    for i, site in enumerate(new):
        for j, atom in enumerate(atoms_to_insert):
            # Calculate distance between sites
            distance = new.lattice.get_distance_and_image(
                site.frac_coords,
                atom['coords']
            )[0]
            if distance < distance_threshold:
                indices_to_replace.append((i, j))
                break  # No need to check other atoms for this site

    assert len(atoms_to_insert) == len(indices_to_replace)

    for i, j in sorted(indices_to_replace, reverse=True):
        new.replace(
            i, species=atoms_to_insert[j]['species'],
            coords=atoms_to_insert[j]['coords'],
            coords_are_cartesian=False,
            properties=atoms_to_insert[j]['properties'])

    new.to_file(str(mc_out.resolve().parent / "str.out"))
    return


# =============================================================================
# Main watcher
# =============================================================================
def main():
    root = Path(".").resolve()
    RUNS_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)

    print(f"[mc_proposer] watching {root} for changes in {TRIGGER_FILES}")

    prev = {}
    # for f in TRIGGER_FILES:
    #     p = root / f
    #     prev[f] = sha256_file(p) if p.exists() else None

    while True:
        time.sleep(POLL_S)

        changed = []
        for f in TRIGGER_FILES:
            p = root / f
            if not p.exists():
                continue
            h = sha256_file(p)
            if prev.get(f) != h:
                changed.append(f)
                prev[f] = h

        if not changed:
            print(f"[mc_proposer] No changes. Waiting for {POLL_S}s")
            continue

        if not stable_trigger_files(root):
            print(f"[mc_proposer] maps is still writing to files. Waiting for {POLL_S}s")
            continue

        if not acquire_lock():
            print(f"[mc_proposer] {LOCKFILE} exist. Waiting for {POLL_S}s")
            continue

        try:
            ensure_required_present(root)

            tag = time.strftime("%Y%m%d_%H%M%S")
            print(f"[mc_proposer] trigger: {changed} -> generation {tag}")

            G = count_ground_states_from_gs_out(root / "gs.out")
            if G < 2:
                print(f"[mc_proposer] gs.out has {G} GS lines; skipping.")
                continue

            mu_list = build_mu_list(G)
            print(f"[mc_proposer] G={G} -> μ points={len(mu_list)} (ends+midpoints+boundaries)")
            print(f"[mc_proposer] seeds: random={DO_RANDOM} anchored={DO_ANCHORED}; parallel jobs={PARALLEL_JOBS}")

            run_root = snapshot_inputs(root, tag)
            jobs_path = run_root / "jobs.txt"
            write_jobs_file(jobs_path, run_root, tag, mu_list, G)

            print("[mc_proposer] running emc2 jobs via GNU parallel...")
            run_parallel(jobs_path)

            # Stage / dedupe / archive snapshots (no str.out conversion here)
            new_count = stage_candidates(root, tag)
            if new_count == 0:
                (root / STOP_FILE).touch()
                print(f"Touched {STOP_FILE} to stop MAPS.")
                release_lock()
                return

            # Run DFT
            if DFT_SCRIPT:
                print(f"[mc_proposer] running DFT: {' '.join(DFT_SCRIPT)}")
                subprocess.run(DFT_SCRIPT, cwd=root, check=True)
                (root / REFRESH_FILE).touch()

            print(f"[mc_proposer] done {tag} (new staged: {new_count})")

        finally:
            release_lock()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        release_lock()
        raise
