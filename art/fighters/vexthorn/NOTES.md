# Vexthorn, the Hollow Stag (`vexthorn`)

Game file: `public/assets/fighters/vexthorn.glb` (1.98 MB, textures 1024 WebP, meshopt).
Source: `art/_work/vexthorn/vexthorn_src.glb` (30 MB, 2048 PNG textures), work files in `art/_work/vexthorn/`.

## Rebuild
`bash art/fighters/vexthorn/run.sh` runs every stage (about 5 min on the RTX 5090). Stages:
`s0_rig` (skeleton) -> `s1_high` (SDF sculpt) -> `s2_low` (decimate + UV) -> `s3_bake` (pos/normal/AO/curvature)
-> `s4_paint` (numpy texture painting) -> `s5_leaves` (leaf atlas + cards) -> `s6_assemble` (weights, un-pose, join,
materials) -> `s7_export` (+ `tools/assets.mjs`) -> `s8_previews` (`-- sheet` renders clip contact sheets).
`clay.py` renders the high-poly parts for shape checks. Shapes live in `parts.py`, colours in `paint.py`,
proportions and modeling pose in `cfg.py`, shared helpers in `fblib.py`.

## Sources
- Rig: Quaternius UBC `Superhero_Male_FullBody` skeleton (CC0) — bones re-lengthened only (every bone keeps its UBC
  orientation and roll; check printed by s0: 0.000000 rad). The UBC body mesh is not used.
- Toolkit: adapted from the owner's Dungeon Joe 3D Caretaker pipeline (`tools/blender/bosses/caretaker/ct_lib.py`,
  s2/s3/s4 stages, painting style). Everything else (geometry, textures, leaves) is procedural, made here.
- Clips for previews: Quaternius UAL1/UAL2 (CC0). Bestiary pack not used.

## Spec
- Height 2.09 m to the antler tips (feet at 0); body to skull top ~1.84 m. Lean, long-limbed: thigh x1.03, calf
  x1.08, spine x1.04, neck x1.32, forearm x1.15, hand x1.10, fingers x1.25, hips 10 % narrower than UBC.
- Rig: the 65 UAL bones with UAL names, no extra bones. Bind pose = UBC rest. NOTE: the UBC rest is a **T-pose**
  (arms horizontal), not an A-pose as the brief says; I bound to it as instructed ("the UBC body's rest pose").
  The mesh was sculpted in a relaxed A-pose and un-posed onto the rest skeleton (round-trip error 0.00000 m).
- **Pelvis height 0.998 m** (UAL1 clips were authored for 0.917 m). The game must scale root/pelvis translation by
  **k = 1.089** for this fighter (the previews do exactly that); without it the hooves sink ~8 cm in clips.
- Triangles: 43,479 (Body 26,354 / Bone 16,574 / Leaves 568 = 142 cards).
- Materials (3):
  - `tint2_bark` — bark body, arms, hands, claws, legs, hooves. Texture painted light/neutral (value detail, mild
    hue); baseColorFactor = default dark bark `#614b3b`. Emissive map (strength 3): amber light from the heart on
    the inside of the ribcage + ember cracks round it.
  - `vex_bone` — skull, antlers, shoulder/neck moss, lantern-heart, 4 tiny antler lanterns. Final colours.
    Emissive (strength 5): eyes, heart core, lantern glass.
  - `tint1_leaves` — 142 alpha-cutout (MASK 0.5, double-sided) leaf cards: shoulders, antler garlands, tines, hip
    belt, neck. Texture cream/neutral; baseColorFactor = burnt orange `#d2561c`.
  All PBR: base colour, normal (tangent, OpenGL), ORM (AO baked), emissive where it glows. Authored at 2048.
- Skinning: max 4 influences. Skull, antlers, lanterns: 100 % `Head`. Lantern-heart: 100 % `spine_03`. Ribcage
  moves as one block (spine_03 above the heart, spine_02 below). Pauldrons + moss ride `upperarm` with some
  `clavicle`. Hip slabs blend pelvis -> thighs. Hooves: `foot` with 45 % `ball` at the toe.
- Digitigrade legs are faked on the normal UAL leg: false hock + spur a third down the shin, thin cannon, fetlock
  dewclaws, cloven hoof-boots.

## Previews (`art/fighters/vexthorn/previews/`)
front / side / threeq (UAL `Idle_Loop` f0), face, pose_punch (`Punch_Cross` max reach), pose_combo
(`Sword_Regular_Combo` lunge, f20), pose_crouch (`Crouch_Idle_Loop` mid). Contact sheets of Punch_Cross,
Sword_Regular_Combo, Jump_Loop, Crouch_Idle_Loop, Hit_Knockback, Spell_Simple_Shoot: `art/_work/vexthorn/sheet_*.jpg`.

## Known issues
- In fist poses the long claws poke out of/through the curled fingers (claws are long by design).
- Lying flat (end of `Hit_Knockback`) the rigid antlers go through the floor — the game may want to lift the head.
- Tiny lanterns and leaf garlands are rigid on `Head` (no swing bones).
- UV utilisation is modest (~0.45 per atlas), so texel density at the shipped 1024 is soft on the big bark areas;
  detail reads through the normal map and value painting.
- At extreme arm raises the pauldrons rotate halfway with the arm and can touch the neck moss.
