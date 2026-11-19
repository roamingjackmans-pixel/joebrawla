#!/usr/bin/env bash
# Joe end to end: build + bake + export (art/_work/joe/joe_src.glb), compress for the game, previews.
set -e
BL=/c/dev/AverageJoe/tools/blender/blender-5.2.3-windows-x64/blender.exe
HERE="$(cd "$(dirname "$0")" && pwd)"
W=/c/dev/JoeBrawla/art/_work/joe
mkdir -p "$W"
cd "$HERE"
"$BL" -b --factory-startup --python build_joe.py > "$W/build.log" 2>&1
grep -E "Traceback|Error:" "$W/build.log" && exit 1 || true
cd /c/dev/JoeBrawla
node tools/assets.mjs fighter art/_work/joe/joe_src.glb joe
cd "$HERE"
"$BL" -b --factory-startup --python render_previews.py -- joe > "$W/previews.log" 2>&1
grep -E "HEIGHT|SHEET" "$W/previews.log"
