This guide walks you through setting up your shell so that you can use
the group's shared Python (Conda) environments and helper commands on
each cluster. It assumes you already have an account and can log in.

The full technical details (how the environments are built, VASP
makefiles, etc.) live in [supercomputer-access.org](supercomputer-access.md). This file is the
step-by-step guide.


# How the setup works

All group software lives in a shared group directory, `IMDGroup`.
Inside it, `dist/` holds:

-   **`miniconda3`:** the shared Conda environment with the group's standard
    Python libraries (the `base` environment).
-   **`vasp.<version>-<cluster>`:** VASP binaries compiled for that cluster.
-   **`vasp-potcar`:** VASP pseudopotentials.
-   **`bashrc-<cluster>`:** the group shell configuration for that cluster.

You enable all of this by appending a short snippet to your own
`~/.bashrc`. After that, every new login shell has Python, VASP, the
potentials, and the helper commands ready to use. Nothing is installed
in your home directory.


# Step 1: add the group environment to your bashrc

Log in to the cluster, then append the matching snippet to the end of
your `~/.bashrc`.


## Ares, Athena, Helios (PLGrid)

    # Ares, Athena, Helios
    IMDGroup="$PLG_GROUPS_STORAGE/plggkeytech"
    export CLUSTER_NAME="${CLUSTER_NAME:-$(uname -n)}"
    source ${IMDGroup}/dist/bashrc-${CLUSTER_NAME}

The same snippet is available as `$IMDGroup/dist/bashrc.example` if you
prefer to copy it directly.


## LUMI

    # LUMI
    export IMDGroup="/projappl/project_465002777"
    export CLUSTER_NAME="${CLUSTER_NAME:-lumi}"
    source ${IMDGroup}/dist/bashrc-${CLUSTER_NAME}


# Step 2: reload your shell and verify

Log out and back in (or run `source ~/.bashrc`), then run:

    which python                     # should point inside $IMDGroup/dist/miniconda3
    python -c "import ase, pymatgen; print('ok')"
    which vasp_std                   # should print a path, not "not found"
    q                                # prints your Slurm job queue
    gorun --help                     # job submission helper
    imdg --help                      # Materials Project / VASP input-output helper

If `which python` does not point into `$IMDGroup/dist`, your `.bashrc`
snippet is not being sourced. See [Troubleshooting](#org9a9631d).


# What you get

After the setup, each login shell has:

-   `python` from the group Conda environment, with the standard libraries
    (`ase`, `pymatgen`, `phonopy`, `mace-torch`, `torch-dftd`, `rdkit`,
    `optuna`, &hellip;). See [Pinned Python libraries](#org44351e9) for the full pinned list.
-   VASP binaries (`vasp_std`, `vasp_gam`, `vasp_ncl`) in `PATH`.
-   VASP potentials via `VASP_PSP_DIR` and `PMG_VASP_PSP_DIR`.
-   `SCRATCH` pointing to the correct scratch directory on every cluster
    (including LUMI, where it is not set by default).
-   Helper commands:
    -   **`q`:** print your Slurm job queue.
    -   **`scall`:** `srun` with the group's Slurm account already set.
    -   **`sbash`:** start an interactive shell on a compute node (8 CPUs,
        24 h by default).
    -   **`gorun`:** submit VASP jobs (and GPU jobs on LUMI, see below).
    -   **`imdg`:** work with Materials Project and VASP inputs/outputs.


# Pinned Python libraries

The Conda environment is shared and version-pinned for the whole group.
This is the exact `env.yaml` that defines the `base` environment:

    channels:
      - conda-forge
    dependencies:
      - python==3.12.4
      - pip
      - xtb
      - crest
      - pip:
        - pymatgen==2026.5.4
        - ase==3.23.0
        - phonopy
        - "git+https://github.com/yantar92/IMDgroup-pymatgen.git"
        - "git+https://github.com/yantar92/IMDgroup-gorun.git"
        - airsspy==0.1.3
        - preloaded
        - mp-api==0.46.4
        - mace-torch==0.3.16
        - torch-sim-atomistic==0.6.1
        - torch-dftd==0.5.3
        - torch-geometric==2.8.0.post1
        - mcpy==2.0.0
        - rdkit==2026.3.5
        - xgboost==3.2.0
        - lightgbm==4.7.0
        - catboost==1.2.10
        - optuna==4.9.0
        - shap==0.51.0
        - icet==3.2
        - pandas==3.0.5
        - pyarrow==25.0.0


# GPU and MACE on LUMI

The shared `miniconda3` environment above is CPU-only (no PyTorch/MACE).
For GPU work with PyTorch and MACE on LUMI, a separate environment is
built on top of LUMI's multitorch containers.

The simplest way to run GPU/MACE jobs is `gorun gpu`, which wraps the
container and the MACE environment for you:

1.  Write a `RUNFILE.sh` containing the commands you want to run
    (`python -m mace.cli ...` or anything else that needs a GPU).
2.  Run `gorun gpu --mark` to generate a `sub` file you can review,
    then submit it with `sbatch sub`. Or run `gorun gpu` to submit
    immediately.

To work interactively inside the container instead:

    module purge
    module use /appl/local/laifs/modules
    module load lumi-aif-singularity-bindings
    export SIF="$SCRATCH/lumi-python-gpu.sif"
    singularity shell $SIF

The group's Python packages are already active inside the container, so
no extra `activate` step is needed. If you need your own environment,
activate it with `source`:

    source ~/myenv/bin/activate


# Requesting new libraries

The Conda environment is shared and version-pinned for the whole group.
If you need a library that is not installed, ask Ihor to add it to the
common environment rather than installing it into your own home folder.
This keeps everyone on the same, tested setup.

When you do need your own environment (for example, inside the GPU
container), create it with `--system-site-packages` so it reuses the
existing libraries instead of duplicating them (and inflating the number
of files):

    python -m venv --system-site-packages ~/myenv
    source ~/myenv/bin/activate


# Troubleshooting

-   **`which python` does not point into `$IMDGroup/dist`:** Your `.bashrc` snippet is not being sourced. Check that it is at the
    end of `~/.bashrc` and that `IMDGroup` matches the cluster you are on.
-   **`!!! IMD Group env error` when opening a shell:** `IMDGroup` or `CLUSTER_NAME` is not set. Re-check the snippet for the
    cluster you are on.

