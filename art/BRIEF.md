# Fighter model brief (for the Blender helper agents)

You are building **game-ready 3D fighter models** for JoeBrawla, a browser fighting game (three.js, side view
like Street Fighter 6) set in the Dungeon Joe world. Read first:

1. `C:\dev\JoeBrawla\docs\ROSTER.md` — your fighter's **Look** paragraph is the brief. Their moves tell you
   which props must exist and move with the hands.
2. `C:\dev\JoeBrawla\docs\DESIGN.md` §14 — the art specification (repeated below).
3. The Dungeon Joe 3D remake you are building on: `C:\dev\AverageJoe\DungeonJoe3D\` — `CLAUDE.md`,
   `docs/ART_CASTING.md` (conventions), and its Blender scripts in `tools/blender/` (`characters/djlib.py`,
   `djmats.py`, `djmats2.py`, `preview.py`, `glb_check.py`, `measure_body.py`; `hub/residents.py` built Gary,
   Brannigan, Marta…; `bosses/caretaker/` built The Caretaker). **Reuse these helpers** (copy what you need into
   your own folder; never edit files under `C:\dev\AverageJoe`).
4. Quality bar: `C:\dev\AverageJoe\DungeonJoe3D\assets\custom\_previews\bosses\caretaker\front.png` and
   `…\bosses\mother_spore\hero.jpg`. Match or beat them. This is a fighting game: the model is seen big, in
   close-ups and super cinematics.

## Sources you may use (all CC0 unless noted)

- `C:\dev\AverageJoe\_downloads\CATALOG.md` lists everything. Most useful:
  - Quaternius **Universal Base Characters** (UBC: Superhero_Male / Superhero_Female bodies with PBR skin
    textures; hair and eyebrows "Rigged to Head Bone").
  - Quaternius **Modular Character Outfits – Fantasy** (peasant/ranger parts on the same 65-bone rig).
  - Quaternius **UAL1 / UAL2** animation libraries (for testing poses): `_downloads/quaternius-ual1/…/UAL1_Standard.glb`,
    `_downloads/quaternius-ual2/…/UAL2_Standard.glb`.
  - Dungeon Joe 3D custom work: `C:\dev\AverageJoe\DungeonJoe3D\assets\custom\` (hair, faces, armour pieces,
    weapons, props). These belong to the owner and may be reused.
  - KayKit, Kenney, Quaternius prop packs in `_downloads`.
- **Never use** the Quaternius **Bestiary** pack (not CC0).
- Blender: `C:\dev\AverageJoe\tools\blender\blender-5.2.3-windows-x64\blender.exe` (run headless:
  `blender.exe -b --factory-startup --python <script.py> -- <args>`). Git Bash and Node 24 are available.

## Specification

- **Rig:** the UAL 65-joint skeleton with the exact Quaternius UAL1 bone names (root, pelvis, spine_01..03,
  neck_01, Head, clavicle/upperarm/lowerarm/hand + fingers, thigh/calf/foot/ball …). Extra bones are fine
  (e.g. `socket_weapon`, a `cape_01..` chain) as long as the 65 are there with UAL names. Bind to the UBC body
  rest pose (A-pose) so UAL clips play correctly. Glue rigid props (weapons, staff, briefcase, hammer, lantern)
  to the hand bone with 100 % weight on `hand_r` / `hand_l`; cloth gets proper weights from the body.
- **Orientation/scale:** glTF Y-up, facing +Z, feet on the origin. Metres. Heights as the Look says.
- **Budget:** 20–45 k triangles total, ≤ 6 materials. PBR (base colour, normal, ORM; emissive where it glows).
  Author textures at 2048; the game ships them at 1024 WebP, so detail must read at 1024.
- **Alternate colours:** name the main cloth material `tint1_<name>` and the accent `tint2_<name>`. The game
  multiplies their base colour for palette swaps, so keep those textures fairly light/neutral in hue
  (value detail, mild colour) and set the material's base colour factor to the default colour.
- **Fighting-game readability:** a strong, distinctive silhouette from the side; hands and heads ~8 % larger
  than realistic; emissive accents (eyes, runes, lantern, molten metal) that bloom; worn, stylized PBR like the
  DJ3D models, not plastic. No floating parts that pierce the body in big poses (test Punch_Cross,
  Sword_Regular_Combo, Jump_Loop, Crouch_Idle_Loop, Hit_Knockback, Spell_Simple_Shoot).
- **Faces:** expressive; eyes that read from 5 m away.

## Deliverables (per fighter `<id>`)

- `C:\dev\JoeBrawla\art\fighters\<id>\` — your Blender Python scripts (re-runnable end to end), notes.
- Work files (`.blend`, the uncompressed source GLB, temporary renders) go in `C:\dev\JoeBrawla\art\_work\<id>\`
  (git-ignored).
- Export the source GLB to `art\_work\<id>\<id>_src.glb`, then compress it for the game:
  `cd C:\dev\JoeBrawla; node tools/assets.mjs fighter art/_work/<id>/<id>_src.glb <id>`
  → `public/assets/fighters/<id>.glb` (aim for ≤ 3.5 MB).
- Preview renders (JPG, 1024 px, EEVEE, a neutral grey studio with a warm key + cool rim light) in
  `art\fighters\<id>\previews\`: `front.jpg`, `side.jpg`, `threeq.jpg`, `face.jpg`, and three posed frames
  driven by UAL clips (`pose_punch.jpg` = Punch_Cross mid-strike, `pose_combo.jpg` = Sword_Regular_Combo,
  `pose_crouch.jpg` = Crouch_Idle_Loop). Look at your renders critically and iterate until they meet the bar.
- A short `art\fighters\<id>\NOTES.md`: sources used, triangle count, materials, bones added, known issues.

## Rules

- Touch only `art\fighters\<your ids>\`, `art\_work\<your ids>\` and `public\assets\fighters\<your ids>.glb`.
  Read anything. Do **not** run git commands that change state, edit other files, or install global software.
- Do not stop to ask questions; choose the closest option to the brief and note it in NOTES.md.
- When done, reply with: file paths, GLB sizes (source and compressed), triangle counts, and an honest
  assessment of quality vs the Caretaker.
