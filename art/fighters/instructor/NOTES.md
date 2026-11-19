# The Instructor (`instructor`)

Game file: `public/assets/fighters/instructor.glb` · source GLB: `art/_work/instructor/instructor_src.glb`
(git-ignored).

## Build (re-runnable end to end)

```bash
art/fighters/instructor/run.sh   # Git Bash: build + bake + export -> compress -> previews
```

`build_instructor.py` (Blender 5.2.3 headless; `-- --geo` for a quick unbaked look) uses the shared kit in
`../joe/lib` (fkit, garments, Dungeon Joe 3D helpers) and the previews / clip check of `../joe/render_previews.py`
(see `../joe/NOTES.md` for how clips are applied exactly as the game does). Clip-check sheet:
`art/_work/instructor/instructor_clipcheck.png`.

## Sources (all CC0 / owner's)

- Quaternius Universal Base Characters: `Superhero_Male_FullBody` (body, eyes, eyebrows), `Hair_Buzzed` (grey).
- Quaternius UAL1 / UAL2: previews / clip check only.
- Dungeon Joe 3D tooling (owner's): body-layer garments, skirts, belts, gloves, procedural materials, face painter.
- Everything else (tunic, collar, sash, cap, boots, baton, clipboard, whistle, moustache) is procedural. No Bestiary.

## Result

| | |
|---|---|
| Height | 1.95 m to the top of the skull, 2.05 m with the cap; the armature node is scaled ×1.0674 (bones keep the UBC rest, so pelvis translations in the clips scale with him) |
| Triangles | **33,611** (skin 7,074 · uniform 8,163 · sash 2,056 · eyes 768 · gear 15,550) |
| Materials (5) | `instructor_skin`, `instructor_eyes` (emissive iris), `tint1_instructor_uniform`, `tint2_instructor_sash`, `instructor_gear` |
| Textures | authored at 2048 (skin, cloth atlas, gear atlas; eyes 512 + emissive iris), shipped 1024 WebP |
| GLB | source 34.2 MB (PNG 2048), game GLB 1.59 MB (1,625 KB) |
| Rig | the 65 UAL joints with UAL1 names, UBC rest, no extra bones |

- **Head and hands +8 %** (as Joe: mesh and finger bones scaled about the joints, rest rotations unchanged).
- **Palette:** `tint1_instructor_uniform` = tunic, collar, cuffs, shoulder boards, pockets, breeches, cap crown
  (default `#6e7a8a` slate); `tint2_instructor_sash` = sash, rosette and tails, collar / cuff piping, breeches seam
  stripes, cap band (`#b0242a` crimson). One neutral cloth atlas shared by both.
- **Baton:** black training baton with a ribbed grip and a steel cap, gripped where the UAL "sword" fist closes
  (en_anim grip centre), tip out of the thumb side, **100 % `hand_r`**.
- **Clipboard** (board, paper, steel clip, two black straps) rigid on `spine_03`, leaning with the back; **whistle**
  on a gold cord from the left shoulder board, rigid on `spine_03`; cap, badge, chin cord, hair, brows,
  moustache on `Head`; sash knot and tails `pelvis 0.6 / thigh_l 0.4`.
- **Emissive:** a cold pale-blue glint in the irises (strength 2.5), so the eyes read under the low visor and bloom.
- Hidden body removed (5-ray coverage test; feet and shins inside the riding boots).

## Choices (closest to the brief)

- Dress tunic with a high stand collar, double row of brass buttons, flapped breast pockets, shoulder boards and a
  short flared skirt with a back vent; Sam Browne belt with a brass buckle; sash from the right shoulder to a
  rosette at the left hip.
- Breeches flare at the thigh and tuck into tall polished boots (glossy black, low roughness).
- Peaked cap: crimson band, wide raised crown, black patent visor worn low, brass "M" (Management) badge, gold
  chin cord.
- Stern face: wrinkles, eye bags, a brow scar, grey stubble shadow, bushy grey brows pulled down at the inner ends,
  a thick grey military moustache.

## Known issues

- The tunic skirt is a single cloth layer weighted like a skirt; in deep lunges it stretches between the thighs.
- The clipboard is rigid on `spine_03`; when he bends double its top edge stands off the back.
- Checked in Blender (EEVEE) with the game's clip semantics; not yet looked at inside the three.js game scene.
