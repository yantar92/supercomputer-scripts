#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Intel-MPI/MKL VASP 6.5.1 installer for PLGrid Helios
#
# Put this file in the same directory as:
#   vasp.6.5.1.tgz
#   vdw_kernel.bindat.gz
#   vdw_kernel.bindat.big_endian.gz
#
# Run:
#   chmod +x install_vasp651_intelmpi.sh
#   ./install_vasp651_intelmpi.sh
#
# It self-submits to Slurm by default and installs into:
#   ./vasp651_intelmpi/install
#
# Primary target stack:
#   intel-compilers/2023.2.1 + impi/2021.10.0 + imkl/2023.2.0
#
# Fallbacks:
#   iimpi/2023b + imkl/2023.2.0
#   intel/2023b
#   iimpi/2025b + imkl/2025.2.0
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
ROOT="${WORKDIR}/vasp651_intelmpi"
BUILD_ROOT="${ROOT}/build"
INSTALL_DIR="${ROOT}/install"
BIN_DIR="${INSTALL_DIR}/bin"
VDW_DIR="${INSTALL_DIR}/share/vasp/vdw"
LOG_ROOT="${ROOT}/logs"
SLURM_LOG_DIR="${ROOT}/slurm_logs"
EXAMPLE_DIR="${INSTALL_DIR}/examples"

for f in "${TARBALL}" "vdw_kernel.bindat.gz" "vdw_kernel.bindat.big_endian.gz"; do
    if [[ ! -f "${INPUT_DIR}/${f}" ]]; then
        echo "ERROR: missing file: ${INPUT_DIR}/${f}"
        echo "Run this installer from the directory containing vasp.6.5.1.tgz and vdW kernels."
        exit 1
    fi
done

mkdir -p "${SLURM_LOG_DIR}"

if [[ -z "${SLURM_JOB_ID:-}" && "${VASP651_NO_SBATCH:-0}" != "1" ]]; then
    if ! command -v sbatch >/dev/null 2>&1; then
        echo "ERROR: sbatch not found. Run this on a Helios login node."
        exit 1
    fi

    q_workdir="$(printf '%q' "${WORKDIR}")"
    q_script="$(printf '%q' "${SCRIPT_PATH}")"

    echo "Submitting Intel-MPI VASP build to Slurm."
    echo "Work directory: ${WORKDIR}"
    echo "Install target:  ${INSTALL_DIR}"
    echo "Account:         ${ACCOUNT}"
    echo "Partition:       ${PARTITION}"
    echo "CPUs:            ${CPUS}"
    echo "Time:            ${TIME_LIMIT}"
    echo

    sbatch \
        --job-name=build-vasp651-impi \
        --partition="${PARTITION}" \
        --account="${ACCOUNT}" \
        --nodes=1 \
        --ntasks=1 \
        --cpus-per-task="${CPUS}" \
        --time="${TIME_LIMIT}" \
        --chdir="${WORKDIR}" \
        --output="${SLURM_LOG_DIR}/build-intelmpi-%j.out" \
        --error="${SLURM_LOG_DIR}/build-intelmpi-%j.err" \
        --wrap="cd ${q_workdir} && export VASP651_NO_SBATCH=1 VASP651_WORKDIR=${q_workdir} JOBS=${JOBS} CPUS=${CPUS} ACCOUNT=${ACCOUNT} PARTITION=${PARTITION}; bash ${q_script}"

    echo "Submitted. Check with:"
    echo "  squeue -u \$USER"
    echo "  tail -f ${SLURM_LOG_DIR}/build-intelmpi-*.out"
    exit 0
fi

cd "${WORKDIR}"

echo "======================================================================"
echo " Intel-MPI/MKL VASP ${VASP_VERSION} build"
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

first_command() {
    for c in "$@"; do
        if command -v "${c}" >/dev/null 2>&1; then
            command -v "${c}"
            return 0
        fi
    done
    return 1
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
        echo "ERROR: source directory not found after unpacking: ${profile_build_root}/${tar_root}"
        return 1
    fi

    echo "${profile_build_root}/${tar_root}"
}

find_mkl_libdir() {
    local mklroot="$1"
    local mkl_libdir="${mklroot}/lib/intel64"

    if [[ -d "${mkl_libdir}" ]]; then
        echo "${mkl_libdir}"
        return 0
    fi

    local found
    found="$(find "${mklroot}" -type f -name 'libmkl_core.*' -print -quit 2>/dev/null || true)"
    if [[ -n "${found}" ]]; then
        dirname "${found}"
        return 0
    fi

    return 1
}

check_makefile_sanity() {
    local build_dir="$1"
    local log_dir="$2"
    local cpp_exe="$3"

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
        "${cpp_exe}" -E -P -C -w \
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

write_makefile_intelmpi() {
    local build_dir="$1"
    local fc_cmd="$2"
    local cc_cmd="$3"
    local cxx_cmd="$4"
    local cpp_exe="$5"
    local mklroot="$6"
    local blacs_lib="$7"

    local mkl_libdir
    mkl_libdir="$(find_mkl_libdir "${mklroot}")" || {
        echo "ERROR: could not find MKL libdir under ${mklroot}"
        return 1
    }

    if ! find "${mkl_libdir}" -name "lib${blacs_lib}.*" -print -quit | grep -q .; then
        echo "ERROR: ${blacs_lib} not found in ${mkl_libdir}"
        echo "Available BLACS libs:"
        find "${mkl_libdir}" -name 'libmkl_blacs*' -maxdepth 1 -type f 2>/dev/null || true
        return 1
    fi

    cd "${build_dir}"

    cat > makefile.include <<'MAKE_EOF'
# ======================================================================
# VASP 6.5.1 Intel-MPI/MKL makefile.include
# Generated by install_vasp651_intelmpi.sh
# ======================================================================

CPP_OPTIONS = -DHOST=\"LinuxIntelMPI\" \
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

# Pure MPI build. No OpenMP flags.
MAKE_EOF

    python3 - <<PY
from pathlib import Path
p = Path("makefile.include")
s = p.read_text()
repl = {
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
            echo "Last 180 lines:"
            tail -n 180 "${log_dir}/make.${target}.log" || true
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

write_load_script() {
    local profile="$1"
    local module_line="$2"

    cat > "${INSTALL_DIR}/load_vasp.sh" <<LOAD_EOF
# Source before using this VASP build:
#   source ${INSTALL_DIR}/load_vasp.sh
#
# Build profile:
#   ${profile}

if ! type module >/dev/null 2>&1; then
    if [ -f /etc/profile.d/modules.sh ]; then
        source /etc/profile.d/modules.sh
    elif [ -f /usr/share/lmod/lmod/init/bash ]; then
        source /usr/share/lmod/lmod/init/bash
    fi
fi

module purge
${module_line}

export VASP_PATH="${INSTALL_DIR}"
export VASP_HOME="${INSTALL_DIR}"
export VASP_VDW_DIR="${VDW_DIR}"
export ASE_VASP_VDW="${VDW_DIR}"
export PATH="${BIN_DIR}:\$PATH"

# Intel MPI / Slurm defaults.
export I_MPI_HYDRA_BOOTSTRAP="\${I_MPI_HYDRA_BOOTSTRAP:-slurm}"
export I_MPI_FABRICS="\${I_MPI_FABRICS:-shm:ofi}"

# ASE POTCAR path. Set manually if your potentials are elsewhere.
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

write_examples() {
    cat > "${EXAMPLE_DIR}/job_vasp_std.slurm" <<SLURM_EOF
#!/bin/bash -l
#SBATCH --job-name=vasp651-impi
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

mpiexec "\${VASP_PATH}/bin/vasp_std"
SLURM_EOF

    cat > "${EXAMPLE_DIR}/job_vasp_ncl.slurm" <<SLURM_EOF
#!/bin/bash -l
#SBATCH --job-name=vasp651-impi-ncl
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

mpiexec "\${VASP_PATH}/bin/vasp_ncl"
SLURM_EOF

    chmod 700 "${EXAMPLE_DIR}"/*.slurm
}

install_successful_build() {
    local build_dir="$1"
    local profile="$2"
    local module_line="$3"

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

    write_load_script "${profile}" "${module_line}"
    write_examples

    ln -sfn "${INSTALL_DIR}" "${ROOT}/current"
    return 0
}

try_profile() {
    local profile="$1"
    local blacs_lib="$2"
    shift 2
    local modules=("$@")
    local profile_log="${LOG_ROOT}/${profile}"

    mkdir -p "${profile_log}"

    echo
    echo "======================================================================"
    echo " Trying Intel-MPI/MKL profile: ${profile}"
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
    fc_cmd="$(first_command mpiifort mpiifx mpif90 mpifort || true)"
    cc_cmd="$(first_command icx icc gcc || true)"
    cxx_cmd="$(first_command icpx icpc g++ || true)"
    cpp_exe="$(first_command gcc cpp icx icc || true)"
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
    "${fc_cmd}" -show 2>/dev/null | tee "${profile_log}/mpi_fortran_show.txt" || true

    local tar_root build_dir
    tar_root="$(detect_tar_root)"
    build_dir="$(prepare_source "${profile}" "${tar_root}")"

    write_makefile_intelmpi "${build_dir}" "${fc_cmd}" "${cc_cmd}" "${cxx_cmd}" "${cpp_exe}" "${mklroot}" "${blacs_lib}"
    cat "${build_dir}/makefile.include" | tee "${profile_log}/makefile.include.final.txt"

    check_makefile_sanity "${build_dir}" "${profile_log}" "${cpp_exe}" || return 1
    build_targets "${build_dir}" "${profile}" || return 1

    local module_line
    module_line="module load ${modules[*]}"
    install_successful_build "${build_dir}" "${profile}" "${module_line}"
    return 0
}

SUCCESS_PROFILE=""

# 1. User-requested explicit Intel compiler + Intel MPI + MKL stack.
if try_profile "intel_compilers_2023_2_1__impi_2021_10_0__imkl_2023_2_0" \
    "mkl_blacs_intelmpi_lp64" \
    intel-compilers/2023.2.1 impi/2021.10.0 imkl/2023.2.0; then
    SUCCESS_PROFILE="intel_compilers_2023_2_1__impi_2021_10_0__imkl_2023_2_0"

# 2. EasyBuild Intel MPI toolchain + MKL.
elif try_profile "iimpi_2023b__imkl_2023_2_0" \
    "mkl_blacs_intelmpi_lp64" \
    iimpi/2023b imkl/2023.2.0; then
    SUCCESS_PROFILE="iimpi_2023b__imkl_2023_2_0"

# 3. Full Intel 2023 toolchain if present.
elif try_profile "intel_2023b" \
    "mkl_blacs_intelmpi_lp64" \
    intel/2023b; then
    SUCCESS_PROFILE="intel_2023b"

# 4. Newer Intel MPI + MKL fallback.
elif try_profile "iimpi_2025b__imkl_2025_2_0" \
    "mkl_blacs_intelmpi_lp64" \
    iimpi/2025b imkl/2025.2.0; then
    SUCCESS_PROFILE="iimpi_2025b__imkl_2025_2_0"

else
    echo
    echo "======================================================================"
    echo "ERROR: all Intel-MPI/MKL build profiles failed."
    echo "Logs are in:"
    echo "  ${LOG_ROOT}"
    echo
    echo "Useful commands:"
    echo "  find ${LOG_ROOT} -type f | sort"
    echo "  tail -n 180 ${LOG_ROOT}/*/make.std.log"
    echo "======================================================================"
    exit 1
fi

source "${INSTALL_DIR}/load_vasp.sh"

echo
echo "======================================================================"
echo " VASP ${VASP_VERSION} Intel-MPI/MKL installation finished successfully."
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
echo "Build logs:"
echo "  ${LOG_ROOT}"
echo "======================================================================"
