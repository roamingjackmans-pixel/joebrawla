# Stage brief (for the Blender helper agents)

You are building **3D fighting-game stages** for JoeBrawla (three.js, side view like Street Fighter 6) set in the
Dungeon Joe realms. Read `C:\dev\JoeBrawla\docs\DESIGN.md` §7 (the stage list) and the realm descriptions in
`C:\dev\AverageJoe\DungeonJoe3D\docs\STORY.md` and `…\docs\ART_CASTING.md`. The current procedural placeholder
for The Mossy Crypt is in `C:\dev\JoeBrawla\public\js\render\stages.js` (look at it in the game at
http://localhost:8095/?quick&skip&stage=crypt — open your **own** browser tab, never navigate other tabs).

## Framing (this is what the player sees)

- glTF Y-up, metres. Fighters stand on the line **z = 0**, x from −7.5 to +7.5 (invisible walls there).
- Camera: z between +7.4 and +11.5, height 1.25–2.5 m, looking at (x, ~1.0, 0), vertical FOV 30°, 16:9. The
  camera slides along x within the walls. So at z = 0 you see about x ±12; at z = −30 about ±25; at z = −100 about ±60.
- **Keep clear:** nothing taller than 0.25 m in z ∈ [−1.5, +6] (between the camera and the fighters); the floor
  is flat at y = 0 for x ∈ [−10, 10], z ∈ [−2, +6] and extends to the camera's bottom edge (to z ≈ +8).
- Composition: a strong, readable **midground** (z −3 to −20: architecture, props, set dressing that tells the
  realm's story), a **background** (z −20 to −150: big silhouettes, terrain, the realm's landmark), and floor
  detail near the line. Leave a calm area behind the fighters' torsos (y 0.8–2 m around z −2 to −6) so they read.
  Think Street Fighter 6 / Tekken 8 stages: lively, deep, but the fight is the focus.
- The landmark: each realm needs one memorable element in the background (see below).

## Lighting and sky

The game supplies the sun, hemisphere light, two rim lights, fog and a gradient sky dome per stage. Do **not**
put lights or a sky sphere in the GLB. Glowing things (lanterns, lava, crystals, windows, runes) use emissive
materials so they bloom. If a painted backdrop helps, make one big curved mesh far away named
`backdrop_noshadow` (unlit look: emissive texture, black base colour). Name any mesh that must not cast shadows
with `noshadow` in its name. Optional animated pieces by node name prefix: `anim_spin_y_<deg per s>`,
`anim_bob`, `anim_sway`, `anim_flicker` (emissive) — the game animates those.

Write `art/stages/<id>/stage.json` with your recommended lighting:
`{ "sun": {"dir": [x,y,z], "color": "#hex", "intensity": n}, "hemi": {"sky": "#hex", "ground": "#hex", "intensity": n},
"rim": ["#hexA", "#hexB"], "fog": {"color": "#hex", "near": n, "far": n}, "sky": {"top": "#hex", "mid": "#hex", "bottom": "#hex"},
"particles": {"type": "motes|snow|embers|rain|spores|leaves|dust|stars|ash", "color": "#hex"}, "bloom": [strength, threshold],
"exposure": n }`. Tune it by checking your previews against a three.js-like look (ACES tone mapping).

## Budget and sources

- ≤ 150 k triangles, ≤ 10 materials if you can (atlas/trim sheets), textures authored ≤ 2048 (shipped 1024 WebP),
  aim for ≤ 6 MB compressed. Instancing is fine (glTF EXT_mesh_gpu_instancing is not needed; plain copies of
  small meshes are OK within budget).
- CC0 packs: `C:\dev\AverageJoe\_downloads\CATALOG.md` (KayKit forest/halloween/dungeon bits, Kenney graveyard,
  Quaternius medieval village and fantasy props megakits, Poly Haven HDRIs for reference only). The owner's
  Dungeon Joe 3D custom props and environment pieces in `C:\dev\AverageJoe\DungeonJoe3D\assets\custom\` (props,
  hub, enemies) may be reused. **Never** use the Quaternius Bestiary pack.
- Blender: `C:\dev\AverageJoe\tools\blender\blender-5.2.3-windows-x64\blender.exe -b --factory-startup --python <script> -- <args>`.
  Reuse helpers from `C:\dev\AverageJoe\DungeonJoe3D\tools\blender\` (copy into your folder; never edit files under
  `C:\dev\AverageJoe`).

## Deliverables (per stage `<id>`)

- `art/stages/<id>/` — re-runnable Blender scripts, `stage.json`, `NOTES.md` (sources, triangle count, size).
- Work files in `art/_work/stages/<id>/` (git-ignored). Export `art/_work/stages/<id>/<id>_src.glb`, then
  `cd C:\dev\JoeBrawla; node tools/assets.mjs prop art/_work/stages/<id>/<id>_src.glb stages/<id>.glb --tex 1024`
  → `public/assets/stages/<id>.glb`.
- Previews (JPG 1280×720, EEVEE) in `art/stages/<id>/previews/`: `game.jpg` from the game camera (camera at
  (0, 1.5, 9.5) looking at (0, 1.0, 0), FOV 30° vertical) with two 1.8 m grey capsules standing at x = ±1.5, z = 0
  for scale, and `wide.jpg` (camera at (0, 2.5, 16) looking at (0, 2, −10)). Look at them critically and iterate.
- Touch only `art/stages/<your ids>/`, `art/_work/stages/<your ids>/`, `public/assets/stages/<your ids>.glb`.
  No git commands that change state. Don't stop to ask; choose and note it.

When done, reply with: per stage, size, triangles, what the landmark is, and an honest quality assessment.

## The stages

| id | Realm | Look | Landmark |
|---|---|---|---|
| `crypt` | The Mossy Crypt (B1) | Graveyard valley in morning sun, mossy headstones, a dirt path, wildflowers, eviction notices nailed to trees | A ruined chapel on the hill and the Caretaker's open grave |
| `hollows` | The Fungal Hollows (B2) | A sinkhole cave open to the sky; giant glowing mushrooms (teal/violet), shelf fungus, spore haze, a shaft of daylight | Mother Spore's colossal mushroom tree in the light shaft |
| `drowned` | The Drowned Quarter (B3) | A flooded old city at dusk in rain; ankle-deep water on the fighting floor (a flat reflective water plane at y = 0.02 is fine), half-sunk buildings, gondolas, lamp posts | The sunken palace with the Bloatking's crown-shaped dome |
| `forest` | The Hollow Forest (B4) | Autumn at golden hour: orange/red trees, fallen leaves, hollow trunks with tiny lanterns, deer skulls, mist | A giant hollow tree with a glowing lantern heart |
| `forge` | The Ashen Forge (B5) | Volcanic foundry at dusk: anvils, chains, crucibles pouring molten metal, conveyor of keys and locks, smoke stacks | The great forge furnace mouth glowing behind the fight |
| `reliquary` | The Frozen Reliquary (B6) | A mountain cathedral at noon: snow, frozen pews, ice pillars, stained glass, a broken radiator ("the heating") | The frozen altar with Saint Aurelia's empty icy throne |
| `citadel` | The Clockwork Citadel (B7) | A brass sky-city above the clouds: gears, pipes, walkways, ledgers and filing cabinets, a sea of clouds below | An enormous clock tower face behind the fight |
| `abyss` | The Abyss (B8) | A rock floating in a starry void; violet static at the edges; floating fragments of the other realms | The Landlord's desk, chair and a grey breaker panel marked MAIN |
| `landing` | The Landing (hub) | A sunny stone courtyard halfway down the stairs; a hearth, the residents' stalls (smithy, market desk, gem bench), plants, laundry lines | The brass breaker panel with eight switches by the hearth |
| `basement` | Building Nine Basement | The building's basement at 11:52 p.m.: concrete, pipes, boiler, storage cages, flickering bulbs, a door with a brass plaque MANAGEMENT | The breaker box on the wall, and the stairs going down |
