#!/usr/bin/env bash
# Vexthorn build pipeline (re-runnable end to end).
#   ./run.sh [stage ...]   stages: rig high low bake paint leaves rig2 export previews   (no args = all)
#   Env: FB_SETS="bark bone" limits low/bake/paint to some atlas sets.  Logs: art/_work/<id>/logs/<stage>.log
set -e
cd "$(dirname "$0")"
ID=$(basename "$(pwd)")
B=/c/dev/AverageJoe/tools/blender/blender-5.2.3-windows-x64/blender.exe
LOG=../../_work/$ID/logs
mkdir -p "$LOG"
run() {
  local tag=$1; shift
  echo "== $tag"
  if ! "$B" -b --factory-startup --python-exit-code 1 --python "$@" > "$LOG/$tag.log" 2>&1; then
    grep -E "Error|Traceback|line [0-9]" "$LOG/$tag.log" | tail -15
    echo "!! stage $tag FAILED (see $LOG/$tag.log)"; exit 1
  fi
  grep -E "^(RIG|PART|LOW|UV util|SHRUNK|AO|BAKED|SAVED|PAINT|EMISSION|LEAVES|FINAL|EXPORT|CHECK|RENDER|TRIS)" "$LOG/$tag.log" || true
}
stages="${@:-rig high low bake paint leaves rig2 export previews}"
for s in $stages; do
  case $s in
    rig) run rig s0_rig.py ;;
    high) run high s1_high.py ;;
    low) for S in ${FB_SETS:-bark bone}; do run low_$S s2_low.py -- $S; done ;;
    bake) for S in ${FB_SETS:-bark bone}; do run bake_$S s3_bake.py -- $S; done ;;
    paint) for S in ${FB_SETS:-bark bone}; do run paint_$S s4_paint.py -- $S; done ;;
    leaves) run leaves s5_leaves.py ;;
    rig2) run rig2 s6_assemble.py ;;
    export) run export s7_export.py
            (cd /c/dev/JoeBrawla && node tools/assets.mjs fighter art/_work/$ID/${ID}_src.glb $ID) ;;
    previews) run previews s8_previews.py ;;
  esac
done
