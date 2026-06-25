#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# ONE-FILE VASP 6.5.1 installer for PLGrid Helios
#
# Put this file in the same directory as:
#   vasp.6.5.1.tgz
#   vdw_kernel.bindat.gz
#   vdw_kernel.bindat.big_endian.gz
#
# Run:
#   chmod +x install_vasp651_auto.sh
#   ./install_vasp651_auto.sh
#
# It builds inside:
#   ./vasp651_auto/
#
# Profiles tried, in order:
#   1. iomkl/2023b          Intel compiler + OpenMPI + MKL
#   2. foss/2025b           GNU/OpenMPI coherent 2025b stack
#   3. foss/2023b           GNU/OpenMPI coherent 2023b stack
#   4. iimpi/2023b + imkl   Intel MPI + MKL
#   5. iimpi/2025b + imkl   Intel MPI + MKL
#
# It does NOT use the old hardcoded:
#   GCC/13.2.0 OpenMPI/5.0.3 OpenBLAS/0.3.24 ...
#
# because that stack caused EL8/EL9 libfabric/GLIBC link problems on Helios.
###############################################################################

VASP_VERSION="6.5.1"
TARBALL="vasp.6.5.1.tgz"

ACCOUNT="${ACCOUNT:-plgkeytech2-cpu}"
PARTITION="${PARTITION:-plgrid}"
CPUS="${CPUS:-16}"
JOBS="${JOBS:-${CPUS}}"
TIME_LIMIT="${TIME_LIMIT:-08:00:00}"

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || realpath "${BASH_SOURCE[0]}")"

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    WORKDIR="${VASP651_WORKDIR:-${SLURM_SUBMIT_DIR:-$(pwd -P)}}"
else
    WORKDIR="$(pwd -P)"
fi

INPUT_DIR="${WORKDIR}"
ROOT="${WORKDIR}/vasp651_auto"
BUILD_ROOT="${ROOT}/build"
INSTALL_DIR="${ROOT}/install"
BIN_DIR="${INSTALL_DIR}/bin"
VDW_DIR="${INSTALL_DIR}/share/vasp/vdw"
LOG_ROOT="${ROOT}/logs"
SLURM_LOG_DIR="${ROOT}/slurm_logs"
EXAMPLE_DIR="${INSTALL_DIR}/examples"

###############################################################################
# Basic file check
###############################################################################

for f in "${TARBALL}" "vdw_kernel.bindat.gz" "vdw_kernel.bindat.big_endian.gz"; do
    if [[ ! -f "${INPUT_DIR}/${f}" ]]; then
        echo "ERROR: missing file: ${INPUT_DIR}/${f}"
        echo
        echo "Run this from the directory containing:"
        echo "  ${TARBALL}"
        echo "  vdw_kernel.bindat.gz"
        echo "  vdw_kernel.bindat.big_endian.gz"
        exit 1
    fi
done

###############################################################################
# Self-submit to Slurm unless already inside Slurm
###############################################################################

mkdir -p "${SLURM_LOG_DIR}"

if [[ -z "${SLURM_JOB_ID:-}" && "${VASP651_NO_SBATCH:-0}" != "1" ]]; then
    if ! command -v sbatch >/dev/null 2>&1; then
        echo "ERROR: sbatch not found. Run this on a Helios login node."
        exit 1
    fi

    q_workdir="$(printf '%q' "${WORKDIR}")"
    q_script="$(printf '%q' "${SCRIPT_PATH}")"

    echo "Submitting VASP build to Slurm."
    echo "Work directory: ${WORKDIR}"
    echo "Account:        ${ACCOUNT}"
    echo "Partition:      ${PARTITION}"
    echo "CPUs:           ${CPUS}"
    echo "Time:           ${TIME_LIMIT}"
    echo

    sbatch \
        --job-name=build-vasp651 \
        --partition="${PARTITION}" \
        --account="${ACCOUNT}" \
        --nodes=1 \
        --ntasks=1 \
        --cpus-per-task="${CPUS}" \
        --time="${TIME_LIMIT}" \
        --chdir="${WORKDIR}" \
        --output="${SLURM_LOG_DIR}/build-%j.out" \
        --error="${SLURM_LOG_DIR}/build-%j.err" \
        --wrap="cd ${q_workdir} && export VASP651_NO_SBATCH=1 VASP651_WORKDIR=${q_workdir} JOBS=${JOBS} CPUS=${CPUS} ACCOUNT=${ACCOUNT} PARTITION=${PARTITION}; bash ${q_script}"

    echo
    echo "Submitted. Check with:"
    echo "  squeue -u \$USER"
    echo "  tail -f ${SLURM_LOG_DIR}/build-*.out"
    exit 0
fi

###############################################################################
# Build starts here
###############################################################################

cd "${WORKDIR}"

echo "======================================================================"
echo " VASP ${VASP_VERSION} automatic Helios build"
echo " Host:       $(hostname)"
echo " Workdir:    ${WORKDIR}"
echo " Root:       ${ROOT}"
echo " Install:    ${INSTALL_DIR}"
echo " Jobs:       ${JOBS}"
echo "======================================================================"

echo "OS / GLIBC:"
cat /etc/os-release 2>/dev/null | head -n 8 || true
ldd --version 2>/dev/null | head -n 1 || true
echo

rm -rf "${BUILD_ROOT}" "${INSTALL_DIR}" "${LOG_ROOT}"
mkdir -p "${BUILD_ROOT}" "${BIN_DIR}" "${VDW_DIR}" "${LOG_ROOT}" "${EXAMPLE_DIR}"
chmod -R go-rwx "${ROOT}" 2>/dev/null || true

###############################################################################
# Avoid Conda pollution
###############################################################################

if [[ -n "${CONDA_PREFIX:-}" ]]; then
    echo "WARNING: Conda appears active: ${CONDA_PREFIX}"
    echo "Removing Conda paths from PATH and LD_LIBRARY_PATH for this build."
    PATH="$(echo "$PATH" | tr ':' '\n' | grep -v "${CONDA_PREFIX}" | paste -sd ':' -)"
    export PATH

    if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
        LD_LIBRARY_PATH="$(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -v "${CONDA_PREFIX}" | paste -sd ':' -)"
        export LD_LIBRARY_PATH
    fi

    unset PYTHONPATH || true
fi

###############################################################################
# Module setup
###############################################################################

if ! type module >/dev/null 2>&1; then
    if [[ -f /etc/profile.d/modules.sh ]]; then
        source /etc/profile.d/modules.sh
    elif [[ -f /usr/share/lmod/lmod/init/bash ]]; then
        source /usr/share/lmod/lmod/init/bash
    fi
fi

if ! type module >/dev/null 2>&1; then
    echo "ERROR: module command is not available."
    exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found."; exit 1; }

###############################################################################
# Helper functions
###############################################################################

find_libdir() {
    local root="$1"
    local libname="$2"

    for d in "${root}/lib" "${root}/lib64" "${root}/lib/intel64"; do
        if [[ -d "${d}" ]] && find "${d}" -maxdepth 1 -name "${libname}" | grep -q .; then
            echo "${d}"
            return 0
        fi
    done

    local found
    found="$(find "${root}" -type f -name "${libname}" -print -quit 2>/dev/null || true)"
    if [[ -n "${found}" ]]; then
        dirname "${found}"
    fi
}

detect_tar_root() {
    tar -tzf "${INPUT_DIR}/${TARBALL}" | sed -n '1s#/.*##p'
}

prepare_source() {
    local profile="$1"
    local tar_root="$2"
    local profile_build_root="${BUILD_ROOT}/${profile}"

    rm -rf "${profile_build_root}"
    mkdir -p "${profile_build_root}"

    tar -xzf "${INPUT_DIR}/${TARBALL}" -C "${profile_build_root}"

    if [[ ! -d "${profile_build_root}/${tar_root}" ]]; then
        echo "ERROR: source directory not found: ${profile_build_root}/${tar_root}"
        return 1
    fi

    echo "${profile_build_root}/${tar_root}"
}

first_command() {
    for c in "$@"; do
        if command -v "${c}" >/dev/null 2>&1; then
            command -v "${c}"
            return 0
        fi
    done
    return 1
}

check_makefile_sanity() {
    local build_dir="$1"
    local log_dir="$2"

    cd "${build_dir}"

    if grep -n "fftmpiw" makefile.include; then
        echo "ERROR: makefile.include contains obsolete fftmpiw."
        return 1
    fi

    if ! grep -n 'DHOST' makefile.include >/dev/null 2>&1; then
        echo "ERROR: makefile.include has no HOST macro."
        return 1
    fi

    local test_pre="${log_dir}/ini.preprocess.test.f90"
    mkdir -p "${log_dir}"

    (
        cd src
        gcc -E -P -C -w \
            -DHOST=\"TESTHOST\" \
            -DMPI -DMPI_BLOCK=8000 -Duse_collective \
            -DscaLAPACK -DCACHE_SIZE=4000 -Davoidalloc -Dvasp6 -Dtbdyn -Dfock_dblbuf \
            ini.F > "${test_pre}"
    )

    if grep -n 'HOST,DATE' "${test_pre}" >/dev/null 2>&1; then
        echo "ERROR: HOST macro did not expand in ini.F."
        return 1
    fi

    return 0
}

build_targets() {
    local build_dir="$1"
    local profile="$2"
    local log_dir="${LOG_ROOT}/${profile}"

    mkdir -p "${log_dir}"
    cd "${build_dir}"

    echo "Running make veryclean for ${profile}"
    make veryclean > "${log_dir}/make.veryclean.log" 2>&1 || true
    rm -rf build bin
    mkdir -p bin

    for target in std gam ncl; do
        echo
        echo "======================================================================"
        echo " Building ${target} using profile ${profile}"
        echo " Log: ${log_dir}/make.${target}.log"
        echo "======================================================================"

        rm -rf "build/${target}"

        set +e
        make DEPS=1 -j "${JOBS}" "${target}" 2>&1 | tee "${log_dir}/make.${target}.log"
        local rc=${PIPESTATUS[0]}
        set -e

        if [[ "${rc}" -ne 0 ]]; then
            echo
            echo "ERROR: target ${target} failed for profile ${profile}"
            echo "Last 160 lines:"
            tail -n 160 "${log_dir}/make.${target}.log" || true
            return "${rc}"
        fi

        if [[ ! -x "bin/vasp_${target}" ]]; then
            echo "ERROR: bin/vasp_${target} was not produced."
            return 1
        fi

        ls -lh "bin/vasp_${target}"
    done

    return 0
}

write_makefile_mkl() {
    local build_dir="$1"
    local fc_cmd="$2"
    local cc_cmd="$3"
    local cxx_cmd="$4"
    local cpp_exe="$5"
    local mklroot="$6"
    local blacs_lib="$7"
    local host_label="$8"

    local mkl_libdir="${mklroot}/lib/intel64"
    if [[ ! -d "${mkl_libdir}" ]]; then
        mkl_libdir="$(find "${mklroot}" -type f -name 'libmkl_core.*' -print -quit 2>/dev/null | xargs -r dirname)"
    fi

    if [[ -z "${mkl_libdir}" || ! -d "${mkl_libdir}" ]]; then
        echo "ERROR: could not find MKL libdir under ${mklroot}"
        return 1
    fi

    if ! find "${mkl_libdir}" -name "lib${blacs_lib}.*" -print -quit | grep -q .; then
        echo "ERROR: ${blacs_lib} not found in ${mkl_libdir}"
        return 1
    fi

    cd "${build_dir}"

    cat > makefile.include <<'MAKE_EOF'
# ======================================================================
# VASP 6.5.1 MKL makefile.include
# Generated by install_vasp651_auto.sh
# ======================================================================

CPP_OPTIONS = -DHOST=\"__HOST_LABEL__\" \
              -DMPI -DMPI_BLOCK=8000 -Duse_collective \
              -DscaLAPACK \
              -DCACHE_SIZE=4000 \
              -Davoidalloc \
              -Dvasp6 \
              -Dtbdyn \
              -Dfock_dblbuf

CPP         = __CPP_EXE__ -E -P -C -w $(CPP_OPTIONS) $*$(FUFFIX) >$*$(SUFFIX)

FC          = __FC_CMD__
FCL         = __FC_CMD__

FREE        = -free
FFLAGS      = -w -assume byterecl

OFLAG       = -O2
OFLAG_IN    = $(OFLAG)
DEBUG       = -O0

CPP_LIB     = $(CPP)
FC_LIB      = $(FC)
CC_LIB      = __CC_CMD__
CFLAGS_LIB  = -O
FFLAGS_LIB  = -O1
FREE_LIB    = $(FREE)

OBJECTS_LIB = linpack_double.o

CXX_PARS    = __CXX_CMD__
LLIBS       = -lstdc++

VASP_TARGET_CPU =
FFLAGS     += $(VASP_TARGET_CPU)

MKLROOT    = __MKLROOT__
MKL_LIBDIR = __MKL_LIBDIR__

SCALAPACK = -L$(MKL_LIBDIR) -lmkl_scalapack_lp64 -l__BLACS_LIB__
BLASPACK  = -L$(MKL_LIBDIR) -lmkl_intel_lp64 -lmkl_sequential -lmkl_core

LLIBS += $(SCALAPACK) $(BLASPACK)
LLIBS += -lpthread -ldl -lm

INCS  += -I$(MKLROOT)/include/fftw
MAKE_EOF

    python3 - <<PY
from pathlib import Path
p = Path("makefile.include")
s = p.read_text()
repl = {
    "__HOST_LABEL__": "${host_label}",
    "__CPP_EXE__": "${cpp_exe}",
    "__FC_CMD__": "${fc_cmd}",
    "__CC_CMD__": "${cc_cmd}",
    "__CXX_CMD__": "${cxx_cmd}",
    "__MKLROOT__": "${mklroot}",
    "__MKL_LIBDIR__": "${mkl_libdir}",
    "__BLACS_LIB__": "${blacs_lib}",
}
for k, v in repl.items():
    s = s.replace(k, v)
p.write_text(s)
PY
}

write_makefile_gnu() {
    local build_dir="$1"
    local openblas_libdir="$2"
    local scalapack_libdir="$3"
    local fftw_root="$4"
    local fftw_libdir="$5"
    local flexiblas_libdir="$6"
    local cpp_exe="$7"

    cd "${build_dir}"

    cat > makefile.include <<'MAKE_EOF'
# ======================================================================
# VASP 6.5.1 GNU/FOSS makefile.include
# Generated by install_vasp651_auto.sh
# ======================================================================

CPP_OPTIONS = -DHOST=\"LinuxGNU\" \
              -DMPI -DMPI_BLOCK=8000 -Duse_collective \
              -DscaLAPACK \
              -DCACHE_SIZE=4000 \
              -Davoidalloc \
              -Dvasp6 \
              -Dtbdyn \
              -Dfock_dblbuf

CPP         = __CPP_EXE__ -E -P -C -w $(CPP_OPTIONS) $*$(FUFFIX) >$*$(SUFFIX)

FC          = mpif90
FCL         = mpif90

FREE        = -ffree-form -ffree-line-length-none
FFLAGS      = -w -ffpe-summary=none -fallow-argument-mismatch -fallow-invalid-boz

OFLAG       = -O2
OFLAG_IN    = $(OFLAG)
DEBUG       = -O0

CPP_LIB     = $(CPP)
FC_LIB      = $(FC)
CC_LIB      = gcc
CFLAGS_LIB  = -O
FFLAGS_LIB  = -O1
FREE_LIB    = $(FREE)

OBJECTS_LIB = linpack_double.o

CXX_PARS    = g++
LLIBS       = -lstdc++

VASP_TARGET_CPU =
FFLAGS     += $(VASP_TARGET_CPU)

OPENBLAS_LIBDIR  = __OPENBLAS_LIBDIR__
SCALAPACK_LIBDIR = __SCALAPACK_LIBDIR__
FFTW_ROOT        = __FFTW_ROOT__
FFTW_LIBDIR      = __FFTW_LIBDIR__
FLEXIBLAS_LIBDIR = __FLEXIBLAS_LIBDIR__

SCALAPACK = -L$(SCALAPACK_LIBDIR) -lscalapack

LLIBS += $(SCALAPACK)
LLIBS += -L$(FFTW_LIBDIR) -lfftw3
LLIBS += -lpthread -ldl -lm
INCS  += -I$(FFTW_ROOT)/include
MAKE_EOF

    python3 - <<PY
from pathlib import Path
p = Path("makefile.include")
s = p.read_text()
repl = {
    "__CPP_EXE__": "${cpp_exe}",
    "__OPENBLAS_LIBDIR__": "${openblas_libdir}",
    "__SCALAPACK_LIBDIR__": "${scalapack_libdir}",
    "__FFTW_ROOT__": "${fftw_root}",
    "__FFTW_LIBDIR__": "${fftw_libdir}",
    "__FLEXIBLAS_LIBDIR__": "${flexiblas_libdir}",
}
for k, v in repl.items():
    s = s.replace(k, v)
p.write_text(s)
PY

    if [[ -n "${flexiblas_libdir}" && -d "${flexiblas_libdir}" ]]; then
        cat >> makefile.include <<'MAKE_EOF'

BLASPACK = -L$(FLEXIBLAS_LIBDIR) -lflexiblas
LLIBS += $(BLASPACK)
MAKE_EOF
    else
        cat >> makefile.include <<'MAKE_EOF'

BLASPACK = -L$(OPENBLAS_LIBDIR) -lopenblas
LLIBS += $(BLASPACK)
MAKE_EOF
    fi
}

install_successful_build() {
    local build_dir="$1"
    local profile="$2"
    local profile_load_text="$3"

    echo
    echo "Installing successful build from profile: ${profile}"

    rm -rf "${INSTALL_DIR}"
    mkdir -p "${BIN_DIR}" "${VDW_DIR}" "${EXAMPLE_DIR}" "${INSTALL_DIR}/build_logs"

    for exe in vasp_std vasp_gam vasp_ncl; do
        if [[ ! -x "${build_dir}/bin/${exe}" ]]; then
            echo "ERROR: missing ${build_dir}/bin/${exe}"
            return 1
        fi
        cp "${build_dir}/bin/${exe}" "${BIN_DIR}/${exe}"
        chmod 700 "${BIN_DIR}/${exe}"
    done

    gunzip -c "${INPUT_DIR}/vdw_kernel.bindat.gz" > "${INSTALL_DIR}/vdw_kernel.bindat"
    gunzip -c "${INPUT_DIR}/vdw_kernel.bindat.big_endian.gz" > "${INSTALL_DIR}/vdw_kernel.bindat.big_endian"

    cp "${INSTALL_DIR}/vdw_kernel.bindat" "${VDW_DIR}/vdw_kernel.bindat"
    cp "${INSTALL_DIR}/vdw_kernel.bindat.big_endian" "${VDW_DIR}/vdw_kernel.bindat.big_endian"

    chmod 600 "${INSTALL_DIR}/vdw_kernel.bindat" "${INSTALL_DIR}/vdw_kernel.bindat.big_endian"
    chmod 600 "${VDW_DIR}/vdw_kernel.bindat" "${VDW_DIR}/vdw_kernel.bindat.big_endian"

    cp "${build_dir}/makefile.include" "${INSTALL_DIR}/build_logs/makefile.include.final.txt" || true
    echo "${profile}" > "${INSTALL_DIR}/BUILD_PROFILE.txt"

    write_load_script "${profile}" "${profile_load_text}"
    write_submit_helper
    write_examples

    cat > "${BIN_DIR}/vasp_copy_vdw_kernel_here" <<COPY_EOF
#!/usr/bin/env bash
set -euo pipefail
cp "${INSTALL_DIR}/vdw_kernel.bindat" ./vdw_kernel.bindat
echo "Copied vdw_kernel.bindat to \$(pwd)"
COPY_EOF
    chmod 700 "${BIN_DIR}/vasp_copy_vdw_kernel_here"

    ln -sfn "${INSTALL_DIR}" "${ROOT}/current"
}

write_load_script() {
    local profile="$1"
    local profile_load_text="$2"

    cat > "${INSTALL_DIR}/load_vasp.sh" <<LOAD_EOF
# Source this file before using this VASP build:
#
#   source ${INSTALL_DIR}/load_vasp.sh
#
# Build profile:
#   ${profile}

${profile_load_text}

export VASP_PATH="${INSTALL_DIR}"
export VASP_HOME="${INSTALL_DIR}"
export VASP_VDW_DIR="${VDW_DIR}"
export ASE_VASP_VDW="${VDW_DIR}"

export PATH="${BIN_DIR}:\$PATH"

# ASE POTCAR path.
# Put potentials in one of these:
#   ${ROOT}/potpaw/potpaw_PBE/
#   ${ROOT}/pseudopotentials/potpaw_PBE/
# or export VASP_PP_PATH manually.
if [[ -z "\${VASP_PP_PATH:-}" ]]; then
    if [[ -d "${ROOT}/potpaw" ]]; then
        export VASP_PP_PATH="${ROOT}/potpaw"
    elif [[ -d "${ROOT}/pseudopotentials" ]]; then
        export VASP_PP_PATH="${ROOT}/pseudopotentials"
    fi
fi

export OMP_NUM_THREADS="\${OMP_NUM_THREADS:-1}"
export OMP_STACKSIZE="\${OMP_STACKSIZE:-512m}"
ulimit -s unlimited 2>/dev/null || true
LOAD_EOF

    chmod 700 "${INSTALL_DIR}/load_vasp.sh"
}

write_submit_helper() {
    cat > "${BIN_DIR}/submit_vasp651.sh" <<SUBMIT_EOF
#!/usr/bin/env bash
set -euo pipefail

# Usage from a VASP calculation directory:
#
#   ${BIN_DIR}/submit_vasp651.sh std 1 24:00:00
#   ${BIN_DIR}/submit_vasp651.sh ncl 1 24:00:00
#   ${BIN_DIR}/submit_vasp651.sh gam 1 24:00:00
#
# Optional:
#   ACCOUNT=plgkeytech2-cpu-bigmem ${BIN_DIR}/submit_vasp651.sh std 1 24:00:00

vasp_bin="\${1:-std}"
nodes="\${2:-1}"
time_limit="\${3:-24:00:00}"
account="\${ACCOUNT:-plgkeytech2-cpu}"
partition="\${PARTITION:-plgrid}"
tasks_per_node="\${TASKS_PER_NODE:-96}"

case "\${vasp_bin}" in
    std|gam|ncl) ;;
    *)
        echo "ERROR: first argument must be std, gam, or ncl"
        exit 1
        ;;
esac

cat > sub <<JOB_EOF
#!/bin/bash -l
#SBATCH --job-name=vasp651-\${vasp_bin}
#SBATCH --nodes=\${nodes}
#SBATCH --time=\${time_limit}
#SBATCH --ntasks-per-node=\${tasks_per_node}
#SBATCH --partition=\${partition}
#SBATCH --account=\${account}
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

source "${INSTALL_DIR}/load_vasp.sh"

export OMP_NUM_THREADS=1
export OMP_STACKSIZE=512m
ulimit -s unlimited

mpiexec "\\\${VASP_PATH}/bin/vasp_\${vasp_bin}" > vasp.out
JOB_EOF

echo "Wrote Slurm script: sub"
sbatch sub
SUBMIT_EOF

    chmod 700 "${BIN_DIR}/submit_vasp651.sh"
}

write_examples() {
    cat > "${EXAMPLE_DIR}/job_vasp_std.slurm" <<SLURM_EOF
#!/bin/bash -l
#SBATCH --job-name=vasp651
#SBATCH --nodes=1
#SBATCH --time=24:00:00
#SBATCH --ntasks-per-node=96
#SBATCH --partition=plgrid
#SBATCH --account=plgkeytech2-cpu
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

source "${INSTALL_DIR}/load_vasp.sh"

export OMP_NUM_THREADS=1
export OMP_STACKSIZE=512m
ulimit -s unlimited

mpiexec "\${VASP_PATH}/bin/vasp_std" > vasp.out
SLURM_EOF

    cat > "${EXAMPLE_DIR}/job_vasp_ncl.slurm" <<SLURM_EOF
#!/bin/bash -l
#SBATCH --job-name=vasp651-ncl
#SBATCH --nodes=1
#SBATCH --time=24:00:00
#SBATCH --ntasks-per-node=96
#SBATCH --partition=plgrid
#SBATCH --account=plgkeytech2-cpu
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

source "${INSTALL_DIR}/load_vasp.sh"

export OMP_NUM_THREADS=1
export OMP_STACKSIZE=512m
ulimit -s unlimited

mpiexec "\${VASP_PATH}/bin/vasp_ncl" > vasp.out
SLURM_EOF

    cat > "${EXAMPLE_DIR}/job_vasp_bigmem.slurm" <<SLURM_EOF
#!/bin/bash -l
#SBATCH --job-name=vasp651-bigmem
#SBATCH --nodes=1
#SBATCH --time=24:00:00
#SBATCH --ntasks-per-node=96
#SBATCH --partition=plgrid
#SBATCH --account=plgkeytech2-cpu-bigmem
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

source "${INSTALL_DIR}/load_vasp.sh"

export OMP_NUM_THREADS=1
export OMP_STACKSIZE=512m
ulimit -s unlimited

mpiexec "\${VASP_PATH}/bin/vasp_std" > vasp.out
SLURM_EOF

    chmod 700 "${EXAMPLE_DIR}"/*.slurm
}

try_mkl_profile() {
    local profile="$1"
    local blacs_lib="$2"
    local host_label="$3"
    shift 3
    local modules=("$@")

    local profile_log="${LOG_ROOT}/${profile}"
    mkdir -p "${profile_log}"

    echo
    echo "======================================================================"
    echo " Trying profile: ${profile}"
    echo " Modules: ${modules[*]}"
    echo "======================================================================"

    set +e
    module purge
    module load "${modules[@]}"
    local rc=$?
    set -e

    if [[ "${rc}" -ne 0 ]]; then
        echo "Profile ${profile}: module load failed."
        return 1
    fi

    module list 2>&1 | tee "${profile_log}/modules.loaded.txt"

    local fc_cmd cc_cmd cxx_cmd cpp_exe mklroot
    fc_cmd="$(first_command mpif90 mpifort mpiifort mpiifx || true)"
    cc_cmd="$(first_command icx icc gcc || true)"
    cxx_cmd="$(first_command icpx icpc g++ || true)"
    cpp_exe="$(first_command gcc cpp || true)"
    mklroot="${MKLROOT:-${EBROOTIMKL:-}}"

    if [[ -z "${fc_cmd}" ]]; then
        echo "No MPI Fortran compiler found for ${profile}."
        return 1
    fi

    if [[ -z "${cc_cmd}" || -z "${cxx_cmd}" || -z "${cpp_exe}" ]]; then
        echo "Missing C/C++/CPP compiler for ${profile}."
        return 1
    fi

    if [[ -z "${mklroot}" || ! -d "${mklroot}" ]]; then
        echo "MKLROOT/EBROOTIMKL invalid for ${profile}: ${mklroot:-unset}"
        return 1
    fi

    echo "FC:      ${fc_cmd}"
    echo "CC:      ${cc_cmd}"
    echo "CXX:     ${cxx_cmd}"
    echo "CPP:     ${cpp_exe}"
    echo "MKLROOT: ${mklroot}"

    local tar_root build_dir
    tar_root="$(detect_tar_root)"
    build_dir="$(prepare_source "${profile}" "${tar_root}")"

    write_makefile_mkl "${build_dir}" "${fc_cmd}" "${cc_cmd}" "${cxx_cmd}" "${cpp_exe}" "${mklroot}" "${blacs_lib}" "${host_label}"
    cat "${build_dir}/makefile.include" | tee "${profile_log}/makefile.include.final.txt"

    check_makefile_sanity "${build_dir}" "${profile_log}" || return 1
    build_targets "${build_dir}" "${profile}" || return 1

    local profile_load_text
    profile_load_text="module purge
module load ${modules[*]}"

    install_successful_build "${build_dir}" "${profile}" "${profile_load_text}"
    return 0
}

try_foss_profile() {
    local profile="$1"
    shift
    local modules=("$@")

    local profile_log="${LOG_ROOT}/${profile}"
    mkdir -p "${profile_log}"

    echo
    echo "======================================================================"
    echo " Trying profile: ${profile}"
    echo " Modules: ${modules[*]}"
    echo "======================================================================"

    set +e
    module purge
    module load "${modules[@]}"
    local rc=$?
    set -e

    if [[ "${rc}" -ne 0 ]]; then
        echo "Profile ${profile}: module load failed."
        return 1
    fi

    module list 2>&1 | tee "${profile_log}/modules.loaded.txt"

    command -v mpif90 >/dev/null 2>&1 || { echo "No mpif90 for ${profile}."; return 1; }
    command -v gcc >/dev/null 2>&1 || { echo "No gcc for ${profile}."; return 1; }
    command -v g++ >/dev/null 2>&1 || { echo "No g++ for ${profile}."; return 1; }

    local openblas_root="${EBROOTOPENBLAS:-}"
    local scalapack_root="${EBROOTSCALAPACK:-}"
    local fftw_root="${EBROOTFFTW:-}"
    local flexiblas_root="${EBROOTFLEXIBLAS:-}"

    if [[ -z "${openblas_root}" && -z "${flexiblas_root}" ]]; then
        echo "No OpenBLAS/FlexiBLAS root for ${profile}."
        return 1
    fi

    [[ -d "${scalapack_root}" ]] || { echo "No ScaLAPACK root for ${profile}."; return 1; }
    [[ -d "${fftw_root}" ]] || { echo "No FFTW root for ${profile}."; return 1; }

    local openblas_libdir=""
    local flexiblas_libdir=""
    local scalapack_libdir=""
    local fftw_libdir=""

    if [[ -n "${openblas_root}" && -d "${openblas_root}" ]]; then
        openblas_libdir="$(find_libdir "${openblas_root}" 'libopenblas.*' || true)"
    fi

    if [[ -n "${flexiblas_root}" && -d "${flexiblas_root}" ]]; then
        flexiblas_libdir="$(find_libdir "${flexiblas_root}" 'libflexiblas.*' || true)"
    fi

    scalapack_libdir="$(find_libdir "${scalapack_root}" 'libscalapack.*' || true)"
    fftw_libdir="$(find_libdir "${fftw_root}" 'libfftw3.*' || true)"

    [[ -n "${scalapack_libdir}" ]] || { echo "No ScaLAPACK libdir."; return 1; }
    [[ -n "${fftw_libdir}" ]] || { echo "No FFTW libdir."; return 1; }

    if [[ -z "${openblas_libdir}" && -z "${flexiblas_libdir}" ]]; then
        echo "No OpenBLAS or FlexiBLAS libdir."
        return 1
    fi

    echo "mpif90: $(which mpif90)"
    echo "gcc:    $(which gcc)"
    echo "g++:    $(which g++)"
    echo "OpenBLAS libdir:  ${openblas_libdir:-none}"
    echo "FlexiBLAS libdir: ${flexiblas_libdir:-none}"
    echo "ScaLAPACK libdir: ${scalapack_libdir}"
    echo "FFTW libdir:      ${fftw_libdir}"

    local tar_root build_dir
    tar_root="$(detect_tar_root)"
    build_dir="$(prepare_source "${profile}" "${tar_root}")"

    write_makefile_gnu "${build_dir}" "${openblas_libdir}" "${scalapack_libdir}" "${fftw_root}" "${fftw_libdir}" "${flexiblas_libdir}" "$(command -v gcc)"
    cat "${build_dir}/makefile.include" | tee "${profile_log}/makefile.include.final.txt"

    check_makefile_sanity "${build_dir}" "${profile_log}" || return 1
    build_targets "${build_dir}" "${profile}" || return 1

    local profile_load_text
    profile_load_text="module purge
module load ${modules[*]}"

    install_successful_build "${build_dir}" "${profile}" "${profile_load_text}"
    return 0
}

###############################################################################
# Try profiles
###############################################################################

SUCCESS_PROFILE=""

# Best first choice on Helios from your available modules:
# Intel compiler + OpenMPI + MKL.
if try_mkl_profile "iomkl_2023b" "mkl_blacs_openmpi_lp64" "LinuxIFC" iomkl/2023b; then
    SUCCESS_PROFILE="iomkl_2023b"

# Coherent FOSS 2025b stack, avoids the old hardcoded GCC13/OpenMPI5 stack.
elif try_foss_profile "foss_2025b" foss/2025b; then
    SUCCESS_PROFILE="foss_2025b"

elif try_foss_profile "foss_2023b" foss/2023b; then
    SUCCESS_PROFILE="foss_2023b"

# Intel MPI + MKL. Important: load iimpi as well as imkl.
elif try_mkl_profile "iimpi_2023b_imkl" "mkl_blacs_intelmpi_lp64" "LinuxIFC" iimpi/2023b imkl/2023.2.0; then
    SUCCESS_PROFILE="iimpi_2023b_imkl"

elif try_mkl_profile "iimpi_2025b_imkl" "mkl_blacs_intelmpi_lp64" "LinuxIFC" iimpi/2025b imkl/2025.2.0; then
    SUCCESS_PROFILE="iimpi_2025b_imkl"

else
    echo
    echo "======================================================================"
    echo "ERROR: all build profiles failed."
    echo
    echo "Logs are in:"
    echo "  ${LOG_ROOT}"
    echo
    echo "Useful commands:"
    echo "  find ${LOG_ROOT} -type f | sort"
    echo "  tail -n 160 ${LOG_ROOT}/*/make.std.log"
    echo "======================================================================"
    exit 1
fi

###############################################################################
# Final checks
###############################################################################

source "${INSTALL_DIR}/load_vasp.sh"

echo
echo "======================================================================"
echo " VASP ${VASP_VERSION} installation finished successfully."
echo " Successful profile: ${SUCCESS_PROFILE}"
echo
echo "Installed here:"
echo "  ${INSTALL_DIR}"
echo
echo "Binaries:"
which vasp_std
which vasp_gam
which vasp_ncl
ls -lh "${BIN_DIR}/vasp_std" "${BIN_DIR}/vasp_gam" "${BIN_DIR}/vasp_ncl"
echo
echo "vdW kernel:"
ls -lh "${INSTALL_DIR}/vdw_kernel.bindat" "${INSTALL_DIR}/vdw_kernel.bindat.big_endian"
echo
echo "Use in current shell:"
echo "  source ${INSTALL_DIR}/load_vasp.sh"
echo
echo "Submit from a calculation directory:"
echo "  ${BIN_DIR}/submit_vasp651.sh std 1 24:00:00"
echo "  ${BIN_DIR}/submit_vasp651.sh ncl 1 24:00:00"
echo
echo "Important:"
echo "  VASP_PATH=${INSTALL_DIR}"
echo "  VASP_VDW_DIR=${VDW_DIR}"
echo
echo "Logs:"
echo "  ${LOG_ROOT}"
echo "======================================================================"
