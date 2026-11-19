#!/usr/bin/env bash
# The Instructor end to end: build + bake + export (art/_work/instructor/instructor_src.glb), compress, previews.
# Shared kit and the preview renderer live in ../joe (lib/, render_previews.py, tools/).
set -e
BL=/c/dev/AverageJoe/tools/blender/blender-5.2.3-windows-x64/blender.exe
HERE="$(cd "$(dirname "$0")" && pwd)"
W=/c/dev/JoeBrawla/art/_work/instructor
mkdir -p "$W"
cd "$HERE"
"$BL" -b --factory-startup --python build_instructor.py > "$W/build.log" 2>&1
grep -E "Traceback|Error:" "$W/build.log" && exit 1 || true
cd /c/dev/JoeBrawla
node tools/assets.mjs fighter art/_work/instructor/instructor_src.glb instructor
cd "$HERE/../joe"
"$BL" -b --factory-startup --python render_previews.py -- instructor > "$W/previews.log" 2>&1
grep -E "HEIGHT|SHEET" "$W/previews.log"
