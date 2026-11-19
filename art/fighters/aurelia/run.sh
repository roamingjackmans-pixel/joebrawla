#!/usr/bin/env bash
# Saint Aurelia -- rebuild everything end to end (Git Bash):  ./run.sh [build] [previews] [compress] [check]
#   build     au_build.py   -> art/_work/aurelia/aurelia_src.glb (+ .blend, tex/, build_report.json)
#   previews  fb_previews.py -> art/fighters/aurelia/previews/*.jpg (+ _work clip-check sheet)
#   compress  tools/assets.mjs -> public/assets/fighters/aurelia.glb
#   check     fb_check.py on both GLBs
set -e
cd "$(dirname "$0")"
B=/c/dev/AverageJoe/tools/blender/blender-5.2.3-windows-x64/blender.exe
ID=aurelia
W=../../_work/$ID
mkdir -p "$W" previews
stages="${@:-build previews compress check}"
for s in $stages; do
  echo "== $s"
  case $s in
    build) "$B" -b --factory-startup --python-exit-code 1 --python au_build.py > "$W/build.log" 2>&1 || { tail -20 "$W/build.log"; exit 1; }
           grep -E "TRIS|EXPORTED" "$W/build.log" ;;
    previews) "$B" -b --factory-startup --python-exit-code 1 --python fb_previews.py -- "$W/${ID}_src.glb" previews \
                --staff-up socket_staff --sheet "$W" > "$W/previews.log" 2>&1 || { tail -20 "$W/previews.log"; exit 1; }
              py fb_sheet.py "$W/clipcheck" "$W/clipcheck_sheet.jpg" 250 ;;
    compress) (cd ../../.. && node tools/assets.mjs fighter art/_work/$ID/${ID}_src.glb $ID | tail -1) ;;
    check) py fb_check.py "$W/${ID}_src.glb"; py fb_check.py ../../../public/assets/fighters/$ID.glb | tail -3 ;;
  esac
done
