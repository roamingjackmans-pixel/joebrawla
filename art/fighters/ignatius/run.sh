#!/usr/bin/env bash
# Fighter build pipeline (re-runnable end to end).
#   ./run.sh [stage ...]   stages: pose high low bake paint rig export check previews compress
#   (no args = everything).  Env: PARTS="torso mask" limits the high-poly rebuild, SETS="body" limits
#   low/bake/paint to some texture atlases.  Logs: art/_work/<id>/logs/<stage>.log.  Stops at the first failure.
set -e
cd "$(dirname "$0")"
ID=$(basename "$(pwd)")
B=/c/dev/AverageJoe/tools/blender/blender-5.2.3-windows-x64/blender.exe
LOG=../../_work/$ID/logs
mkdir -p "$LOG"
ALLSETS=$(grep -o '^SIZE = {.*}' f_sets.py | grep -o '"[a-z]*":' | tr -d '":' | tr '\n' ' ')
run() {
  local tag=$1; shift
  echo "== $tag"
  if ! "$B" -b --factory-startup --python-exit-code 1 --python "$@" > "$LOG/$tag.log" 2>&1; then
    grep -E "Error|Traceback|line [0-9]" "$LOG/$tag.log" | tail -15
    echo "!! stage $tag FAILED (see $LOG/$tag.log)"; exit 1
  fi
  grep -E "^(GRIP|PART|LOW|UV util|SHRUNK|AO|BAKED|SAVED|PAINT|TINT|RENDER|RIG|EXPORT|CHECK)" "$LOG/$tag.log" || true
}
stages="${@:-pose high low bake paint rig export check previews compress}"
for s in $stages; do
  case $s in
    pose) run pose s0_pose.py ;;
    high) run high s1_high.py -- $PARTS ;;
    low) for S in ${SETS:-$ALLSETS}; do run low_$S s2_low.py -- $S; done ;;
    bake) for S in ${SETS:-$ALLSETS}; do run bake_$S s3_bake.py -- $S; done ;;
    paint) for S in ${SETS:-$ALLSETS}; do run paint_$S s4_paint.py -- $S; done ;;
    rig) run rig s6_rig.py ;;
    export) run export s8_export.py ;;
    check) run check s9_check.py ;;
    previews) run previews render_previews.py ;;
    compress) (cd ../../.. && node tools/assets.mjs fighter art/_work/$ID/${ID}_src.glb $ID) ;;
  esac
done
