# Foreman Ignatius (`ignatius`) — model notes

Shipped: `public/assets/fighters/ignatius.glb` (1.79 MB, 1024 WebP + meshopt). Source: `art/_work/ignatius/ignatius_src.glb`
(34 MB, 2048 PNG). Rebuild everything with `art/fighters/ignatius/run.sh` (Git Bash; stages
`pose high low bake paint rig export check previews compress`, logs in `art/_work/ignatius/logs/`).

## Build method
Same pipeline as the Dungeon Joe 3D Caretaker (its `ct_lib` copied as `jb_lib.py`): every part is an SDF sculpt
(numpy) → surface nets high-poly → decimated low-poly with packed UVs → Cycles bakes (object normal, position, AO,
curvature) → texture-space painting in numpy (`f_paint.py`) → skinning in an A-ish modeling pose, then un-posed onto
the rest skeleton (`s6_rig.py`).

| file | what |
|---|---|
| `f_rig.py` | skeleton edits, modeling pose, measured UAL fist grip |
| `f_parts.py` | body, mail, apron bib, mask, hardhat, leather neck flap, braided beard, right arm, gauntlet, chains, belt, straps, apron skirt, mail skirt, legs/boots |
| `f_props.py` | forge hammer (own frame: origin = grip, +Z to the head) |
| `f_sets.py` | atlases + materials (tint factors come from the paint stage) |
| `f_paint.py` | painters + detail normals |
| `s0…s9`, `render_previews.py` | stages; `clay.py` quick clay renders; `three_check.mjs` engine check |

## Sources
- Quaternius **UAL1** skeleton (`_downloads/quaternius-ual1/…/UAL1_Standard.glb`, CC0) — the rig. UAL1/UAL2 clips for
  previews and checks. No meshes or textures from any pack: all geometry and textures are procedural/original.
- Dungeon Joe 3D Caretaker pipeline code (owner's) — adapted.

## Rig
- 65 UAL1 joints, exact names, hierarchy and **exact UAL1 joint orientations** (check: max 0.05° vs UAL1). No extra bones.
- Translation-only proportion edits (bones whose translation the game strips from clips): shoulders +5 cm wider,
  head joint 3 cm lower/1.2 cm forward (bull neck), hips +2 cm, hand + finger joints ×1.12 (big hands; the fist
  closes round a thicker haft). Leg chain and pelvis untouched, so UAL pelvis tracks keep the boots on the floor.
- Height: the armature object is scaled **×1.115** (glTF `Armature` node scale), so the hardhat top is at 2.150 m and
  clip translations (root/pelvis) scale with the body. Verified in three.js with `public/assets/anim/test.glb`
  (`node art/fighters/ignatius/three_check.mjs ignatius`): rest 2.150 m, Idle feet at −1 cm, Crouch −3 cm.
- **Deviation from the brief:** the brief says "bind to the UBC body rest pose (A-pose)". The UBC male rest is actually
  a T-pose, its joint orientations differ from UAL1 by up to 17° (spine_03/neck) and its legs are 3 cm longer than
  UAL's (feet sink under UAL pelvis tracks). Binding to UAL1's own rest (as the Caretaker does) makes the stock clips
  reproduce exactly; the body is built to scaled-up superhero proportions around it. The mesh is sculpted in a relaxed
  A-pose and un-posed (round-trip error 0.00000 m).
- Hammer: separate mesh `Ignatius_Hammer`, **100 % `hand_r`**, haft along the measured UAL fist axis (the same closed
  fist is used by every UAL clip), striking face toward the fist's punching side.
- Weights: distance-to-bone per part, smoothed, max 4. Apron skirt pelvis → 62 % thighs at the hem, mail skirt
  → 85 % thighs (split front and back), beard/flap blend head → chest, tongs at the left hip partly on `thigh_l`.

## Budget
- **39,524 triangles** (body 35,973 + hammer 3,551). **5 materials**:
  `ignatius_body` (skin, mail, mask, beard, gauntlet, chains, belt; emissive eye slits + ember beard tips),
  `tint2_trim` (hardhat enamel + apron neck strap), `tint1_apron` (scorched leather apron, bib + skirt),
  `ignatius_gear` (mail skirt, trousers, knee guards, boots), `ignatius_hammer` (emissive hot head).
- 3 atlases authored at 2048: body (+tint2), gear (+tint1), hammer. Normal + ORM everywhere, emissive on body and hammer.
- Tint materials: their UV islands hold light, near-neutral value detail (mean 0.75); the base colour factor is the
  default colour (tint1 apron linear (0.106, 0.044, 0.020) = sRGB #5a3a26-ish leather, tint2 trim (0.547, 0.302, 0.032)
  = foundry yellow). Changing the factor recolours cleanly.

## Previews (`previews/`, EEVEE 1024)
front/side/threeq/face = `Idle_Loop` f10 with a preview-only wrist turn so the hammer head rests on the floor
(the raw clip points the haft forward); `pose_punch` = Punch_Cross f11, `pose_combo` = Sword_Regular_Combo f37
(overhead), `pose_crouch` = Crouch_Idle_Loop f10.

## Known issues
- The hammer is a sword-length prop on UAL sword clips: in a few combo frames the haft passes close to the body,
  and in unarmed clips (Idle) it points straight forward from the fist; real moves should use custom key poses.
- The beard bush reads a bit "fur pelt" up close; braids, rings and ember tips read well.
- Chainmail is a painted/normal-mapped ring lattice (no geometry); at 1024 it reads as fine scale mail.
- Leg chain is UAL's (short-legged, stocky silhouette by design of the brief's "big body" on UAL legs).
- UV utilisation of the body atlas is ~43 % (many organic charts); texel density is still ≈ the Caretaker's.
