# Joe — "Apartment 3C" (`joe`)

Game file: `public/assets/fighters/joe.glb` · source GLB: `art/_work/joe/joe_src.glb` (git-ignored).

## Build (re-runnable end to end)

```bash
art/fighters/joe/run.sh        # Git Bash: build + bake + export -> compress -> previews (~3 min on the RTX 5090)
```

1. `build_joe.py` (Blender 5.2.3 headless) builds every garment / prop procedurally on the UBC body, bakes the
   atlases (Cycles GPU), trims the hidden body, exports `art/_work/joe/joe_src.glb` and sets the palette factors
   (`tools/post.mjs`). `-- --geo` renders a quick unbaked EEVEE look instead (`art/_work/joe/_geo_*.jpg`).
2. `node tools/assets.mjs fighter art/_work/joe/joe_src.glb joe` (the game's pipeline: 1024 WebP, meshopt).
3. `render_previews.py -- joe` copies UAL clips onto the fighter's joints exactly as the game's anim packs do
   (`tools/posed.mjs`: rotations everywhere, translation only on root/pelvis), imports that GLB and renders the
   EEVEE previews in `previews/` plus a clip-check contact sheet `art/_work/joe/joe_clipcheck.png`
   (Punch_Cross, Sword_Regular_Combo, Jump, Crouch_Idle, Hit_Knockback, Spell_Simple_Shoot; 4 frames each).
4. `tools/check_glb.mjs <glb>` checks joints (65 UAL names), materials, factors, vertex colours, textures.

Shared kit (also used by The Instructor): `lib/` — `fkit.py` (fighter build, atlas bake, skin, trim, export),
`garments.py` (collar, rolled cuffs, work/riding boots, hair, tape, hardware, lettering), `fpreview.py` (studio,
cameras), and copies of the Dungeon Joe 3D helpers (`djlib`, `djarmor`, `agcore`, `aggeo`, `agmats`,
`build_faces`, `build_hair`, `en_anim`; outputs redirected to `art/_work/<id>`, nothing under `C:\dev\AverageJoe`
is written). `probe_body.py` measures the UBC body and checks that a Blender round trip keeps the rest pose
(worst joint rotation difference 0.04°).

## Sources (all CC0 / owner's)

- Quaternius Universal Base Characters: `Superhero_Male_FullBody` (body, eyes, eyebrows + lashes, skin normal and
  roughness maps), `Hair_SimpleParted` (Joe's Dungeon Joe 3D hairstyle) with its strand texture.
- Quaternius UAL1 / UAL2: preview / clip-check poses only (not in the GLB).
- Dungeon Joe 3D tooling (owner's): the armour pipeline's body-layer garments, wraps, skirts, belts, procedural
  materials (fabric, leather, plate, rope, metal trim), the class face painter (stubble, eye bags, scar...).
- Everything else is procedural in these scripts. No Bestiary content.

## Result

| | |
|---|---|
| Height | skull top 1.83 m (UBC 1.81 m + the 8 % head), 1.84 m to the top of the hair; armature node scale 1.0 |
| Triangles | TRIS |
| Materials (5) | MATS |
| Textures | authored at 2048 (skin base colour re-baked, cloth atlas, gear atlas; eyes 512), shipped 1024 WebP |
| GLB | source SRCMB MB, game GLB GAMEKB KB |
| Rig | the 65 UAL joints with UAL1 names, UBC rest (T-pose), no extra bones |

- **Proportions:** head and hands +8 %: mesh verts scaled about the Head / wrist joints by skin weight, and the
  finger bones (heads/tails) and Head tail scaled with them, so finger curls still bend at the knuckles. Rest
  rotations are untouched (UAL clips play as on any UBC fighter).
- **Palette:** `tint1_joe_shirt` = shirt, collar, pockets, rolled cuffs (default factor `#4c5058` charcoal);
  `tint2_joe_trousers` = trousers, hems, knee patches (`#4f4532` dark olive-brown). Both share one neutral
  light-grey cloth atlas (value detail only), so any colour multiplies cleanly.
- **Emissive:** the flashlight lens (warm white, strength 8) blooms.
- **Weights:** clothes take the body's weights (nearest surface, smoothed); shirt tails use skirt weights (pelvis at
  the top, thighs below, both thighs at the centre seams); flashlight + ring holster `pelvis 0.6 / thigh_r 0.4`,
  pouch + tools `pelvis 0.65 / thigh_l 0.35`, key + lanyard `pelvis 0.6 / thigh_l 0.4`; hair, brows `Head`.
- **Hidden body removed:** body faces fully covered by clothes (5-ray test) and the feet / lower shins inside the
  boots are deleted, so nothing pokes through in big poses and the triangle count stays low.

## Choices (closest to the brief)

- The Thermos and a hand-held flashlight were explicitly not wanted; the flashlight lives on the right hip only.
- The tool belt is worn over the open shirt (it reads from every side); the brass key hangs from it on an orange
  lanyard; the pouch carries a red screwdriver and yellow-handled pliers.
- Trousers fall over the boots (straight legs, a break over the instep); boots are a designed loft (round toe box,
  toe cap and heel counter overlays, welt, lug sole, laces with brass eyelets), not the body's foot.
- Duct-tape wraps: a tape shell over palm, back of hand, wrist and knuckles plus overlapping strips (edges read);
  fingers and thumb tip stay bare.
- "3C" patch on the upper left sleeve, lettering readable with the arm down.
- Face: stubble, eye bags, a small cheek scar, lash-line darkening, bold angled brows (determined look).

## Known issues

- The open shirt panels and tails are single-layer cloth (double-sided material); in extreme crouches the tails
  fold with the thighs rather than draping.
- Rigid hip gear (holster, pouch) follows a pelvis/thigh blend; in the very highest knee raises the pouch can graze
  the thigh. Nothing pierced the body in the six clips checked.
- The hair is the stock UBC quiff tousled with noise rather than a custom groom.
- Checked in Blender (EEVEE) with the game's clip semantics; not yet looked at inside the three.js game scene.
