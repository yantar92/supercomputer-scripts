#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# USER SETTINGS (override via env)
# -----------------------------
T0_VERIFY="${T0_VERIFY:-1}"   # "0 K" verification (1 K is safer than 0 K)
T_RT="${T_RT:-300}"

MU0="${MU0:--0.60}"
MU1="${MU1:-0.60}"
DMU="${DMU:-0.01}"

ER="${ER:-20}"
EQ="${EQ:-5000}"
N="${N:-50000}"
TSTAT="${TSTAT:-3}"
GS_INIT="${GS_INIT:--1}"
USE_G2C="${USE_G2C:-1}"

JOBS="${JOBS:-96}"             # number of parallel workers

# -----------------------------
# Per-directory worker
# -----------------------------
run_dir() {
    local d="$1"
    [[ -z "$d" ]] && exit 0
    echo "==> [$d] starting"

    if [[ ! -d "$d" ]]; then
	echo "==> [$d] SKIP: not a directory"
	exit 0
    fi

    pushd "$d" >/dev/null

    for f in lat.in clusters.out eci.out; do
	if [[ ! -f "$f" ]]; then
	    echo "==> [$d] SKIP: missing $f"
	    popd >/dev/null
	    exit 0
	fi
    done

    if [[ ! -f gs_str.out ]]; then
	echo "==> [$d] WARN: gs_str.out missing; emc2 may still run depending on setup"
    fi

    run_one() {
	local T="$1"
	local OUT="$2"
	local cmd=(emc2
		   "-T0=${T}" -keV
		   "-mu0=${MU0}" "-mu1=${MU1}" "-dmu=${DMU}" -abs
		   "-gs=${GS_INIT}"
		   "-er=${ER}"
		   "-eq=${EQ}" "-n=${N}"
		   "-tstat=${TSTAT}"
		   "-o=${OUT}"
		  )
	[[ "${USE_G2C}" == "1" ]] && cmd+=(-g2c)

	[ -f "${OUT%.out}.log" ] && echo "Found "${OUT%.out}.log"; skipping emc2 run" && return 0

	echo "==> [$d] ${cmd[*]}"
	"${cmd[@]}" > "${OUT%.out}.log" 2>&1
    }

    postprocess() {
	local OUT="$1"
	local DAT="${OUT%.out}_F_vs_c.dat"
	local REF="ref_energy.out"
	local E0=0
	local E1=0
	# Apply linear baseline correction using ref_energy.out (E_new = E_old + c*E(c=1) + (1-c)*E(c=0))
	if [[ -f "$REF" ]]; then
	    # read first line, first column
	    E0=$(awk 'NR==1 {print $1}' "$REF")
	    E1=$(awk 'NR==2 {print $1}' "$REF")
	fi
	awk -v e0="$E0" -v e1="$E1" '
      $1!="#" && NF>=5 {
        mu=$2; Emux=$3; x=$4; col5=$5;
        c=(x+1)/2;
        Enew = col5 + c*e1 + (1-c)*e0;
        Emux_new = Emux + c*e1 + (1-c)*e0;
        printf "%.8f\t%.10f\t%.10f\t%.8f\t%.10f\n", c, Enew, mu, x, Emux_new
      }
    ' "$OUT" > "$DAT"
    }

    OUT0="mc_T${T0_VERIFY}K.out"
    OUTT="mc_T${T_RT}K.out"

    run_one "$T0_VERIFY" "$OUT0"
    postprocess "$OUT0"

    run_one "$T_RT" "$OUTT"
    postprocess "$OUTT"

  popd >/dev/null
  echo "==> [$d] done"
}

export -f run_dir
export T0_VERIFY T_RT MU0 MU1 DMU ER EQ N TSTAT GS_INIT USE_G2C

# -----------------------------
# Input directories
# -----------------------------
if [[ $# -lt 1 ]]; then
  cat <<EOF
Usage:
  $0 dir1 dir2 ...
  $0 -f dirs.txt
Env overrides:
  JOBS=8 ER=25 EQ=10000 N=200000 MU0=-0.9 MU1=0.9 DMU=0.005 $0 -f dirs.txt
EOF
  exit 2
fi

dirs=()
if [[ "$1" == "-f" ]]; then
  [[ $# -eq 2 ]] || { echo "Error: -f requires a file"; exit 2; }
  mapfile -t dirs < "$2"
else
  dirs=("$@")
fi

# GNU parallel required
command -v parallel >/dev/null 2>&1 || {
  echo "Error: GNU parallel not found. Install it or use the xargs -P version."
  exit 1
}

printf "%s\n" "${dirs[@]}" | parallel -j "${JOBS}" --no-notice run_dir {}

