# Mother Spore (`mother_spore`) — fighter model notes

**Files:** `public/assets/fighters/mother_spore.glb` (game, 1.98 MB, meshopt + WebP 1024) ·
`art/_work/mother_spore/mother_spore_src.glb` (source, 45.3 MB, PNG 2048) · `art/_work/mother_spore/mother_spore.blend` ·
previews in `previews/` · rebuild with `./run.sh` (Git Bash; build ≈ 1 min, previews ≈ 1 min).

## What she is
A 2.0 m fungal matriarch (body 1.87 m + the cap): UBC Superhero_Female body scaled ×1.06, head ×1.08, hands ×1.08
with fingers ×1.28 (long fingers; the finger bones were moved with the mesh). Pale mauve skin with fine gill ridges,
three gill slits on each side of the neck, ink-dipped plum fingertips and pulsing teal spots (cheeks, temples, outer
arms, shins); glowing violet slit-pupil eyes. A 0.86 m rust-red fly-agaric cap with raised cream warts, cream gills
glowing teal near the stem and a cream annulus band, worn tilted back like a hat over a mycelium hood. Plum mycelium
dress: corset-like bodice with a pale mycelium web, a drooping cream annulus ruff at the neckline, bracket-fungus
epaulettes, a twisted cord belt with a cluster of little mushrooms on the left hip, four turkey-tail frill tiers and a
thread skirt that darkens into ~26 root tendrils (teal tips) at a mid-calf hem (0.32 m). Mycelium wraps on both
wrists. A 1.92 m gnarled mushroom-stalk staff (scaly stalk, mycelium grip wrap, root foot, three little caps and a
glowing spore bulb at the crown) in the right fist.

## Spec
| | |
|---|---|
| Triangles | **41,278** — Body 10,161 · Cap 3,552 · Dress 9,616 · Misc 17,949 |
| Materials (4) | `ms_skin` (body, own UBC UVs) · `tint1_cap` (cap top; factor rust `#9b3420` → [0.389, 0.041, 0.017]) · `tint2_dress` (bodice, hood, skirt, tiers, epaulettes; factor plum `#64405f` → [0.186, 0.075, 0.167]) · `ms_misc` (gills, band, warts, ruff, roots, belt, hip caps, cuffs, staff, eyes, brows; double-sided) |
| Textures | per material 2048²: base colour, ORM (R = baked AO, G = roughness, B = 0), normal, emission (not on the cap). Tint textures are light and nearly neutral (mean ≈ 0.84 cap, 0.68 dress); the default colour lives in `baseColorFactor`. Emissive strength 5 (skin, dress) / 6 (misc) via KHR_materials_emissive_strength. |
| Rig | the 65 UAL bones (UBC rest = T-pose, bound to the UBC body) + `socket_staff` (child of `hand_r`, at the staff crown) and `socket_cap` (child of `Head`, top of the cap); both weightless. Max 4 influences, normalised. |
| Size | feet on the origin, glTF Y-up facing +Z, cap top 2.00 m (bbox 2.04 m incl. the staff in rest). Pelvis rest height 0.988 m (UAL mannequin 0.917 m): scale clip pelvis translation by ×1.077 if feet float/sink. |

## Weights
Cap, warts, gills, band: 100 % `Head`. Staff: 100 % `hand_r` (placed in the closed fist of UAL1 `Sword_Idle`; the rest
pose has an open hand, so the game must curl the right hand as UAL weapon clips do). Hood: `Head` → `neck_01` →
`spine_03` by height. Bodice: the body's own weights (it is the body's torso, welded, inflated 1 cm). Skirt: split
left/right by x (thighs, blending to calves toward the hem, pelvis near the hips, body transfer at the waist), with a
**front slit from 0.81 m to the hem** so each leg can kick; tiers, roots and belt transfer from the skirt; ruff,
epaulettes, cuffs transfer from the body. Hidden body faces under the clothes are deleted (2,651 faces).

## Sources
- Quaternius Universal Base Characters (CC0): `Superhero_Female_FullBody.gltf` body, eyes, brows/lashes; its base
  colour and normal textures (re-toned and re-painted, baked into the body's own UVs).
- Quaternius UAL1/UAL2 (CC0): `Sword_Idle` (grip measurement), `Punch_Cross`, `Sword_Regular_Combo`,
  `Crouch_Idle_Loop`, `Jump_Loop`, `Hit_Knockback`, `Spell_Simple_Shoot` for previews and the clip check.
- Dungeon Joe 3D (owner's): `tools/blender/characters/djlib.py` (MB geometry builder, NB node DSL, weight transfer —
  adapted into `fblib.py`), `armor/build_faces.py` approach (landmark-placed face paint baked into the body UVs), and
  the Mother Spore boss's colour language (teal-glowing gills, cream warts, mauve skin, mycelium, root tendrils).
  The boss's baked texture atlases were not reused directly (they are laid out for the boss's own UVs). The boss cap is
  violet; this cap follows ROSTER.md (rust red with cream spots).
- Everything else is procedural (`ms_geo.py`, `ms_mats.py`), baked with Cycles into the texture sets above.

## Scripts
`ms_build.py` (body reshape → outfit → weights → bake → GLB; `--look` = fast procedural EEVEE look renders) ·
`ms_geo.py` (cap, hood, bodice, skirt, tiers, roots, ruff, epaulettes, belt, cuffs, staff) · `ms_mats.py`
(procedural materials) · `fblib.py` (shared library) · `fbview.py` (EEVEE studio, bloom) · `fb_previews.py` (renders
from the exported GLB with three.js clip semantics: local rotations only, pelvis translation scaled) · `fb_check.py`
(GLB check) · `fb_sheet.py` (clip-check contact sheet → `art/_work/mother_spore/clipcheck_sheet.jpg`) · `run.sh`.

## Previews
`front/side/threeq.jpg`: `Sword_Idle` f12 with the right wrist turned so the staff stands upright (presentation only).
`face.jpg`: rest pose. `pose_punch.jpg` (Punch_Cross f9), `pose_combo.jpg` (Sword_Regular_Combo f36),
`pose_crouch.jpg` (Crouch_Idle_Loop f12): clip poses exactly as the game would play them.

## Known issues
- The staff is long and rigid in the fist: in generic UAL clips it passes through the cap brim (Punch_Cross guard),
  the legs (Crouch_Idle_Loop) and the floor. Her own move animations should hold it upright or planted.
- The cap is wide (0.86 m) and rigid on `Head`: in head-down stances it shades the face (the eyes still read from
  eye height and below); it digs into the floor in the lying frames of Hit_Knockback.
- The hood's back edge shears a little in strong head twists (top on `Head`, bottom on the spine).
- Skirt back seam stretches between the legs in wide stances (standard for a weighted skirt; front is slit).
- Process note: an early preview run wrote stray renders to `C:\previews\` (7 JPGs) and
  `C:\_work\mother_spore\clipcheck\` (36 JPGs) because Blender resolves relative render paths from the drive root;
  fixed (absolute paths). The stray files can be deleted.
