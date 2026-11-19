# JoeBrawla — Design

A 3D side-view fighting game (Street Fighter 6 / Tekken presentation, Street Fighter rules with Tekken-style
juggles and wall splats) set in the world of **Dungeon Joe**. Plays in the browser at
`https://josephjackman.com/games/joebrawla/`. Online 1v1 between friends with 4-digit friend and room codes,
4 bot difficulties, couch versus, training, an arcade ladder with lore, Survival and Boss Rush.

Owner's answers (2026-11-19) that fix the scope: 3D side view built on the Dungeon Joe 3D models; 2D plane
SF-style movement; Classic and Simple control schemes, player's choice; 12 fighters + The Landlord; modes =
online 1v1 + bots ×4 + couch + training + arcade ladder + Survival/Boss Rush; lobbies are exactly 2 people;
strangers can only find you by code (no public matchmaking); fighters unlock by playing (6 at the start, quick
unlocks); epic look with Dungeon Joe's deadpan humour; build everything without stopping; public repo
`roamingjackmans-pixel/joebrawla`, published at `/games/joebrawla/`.

## 1. Pillars

1. **Hits feel enormous.** Hitstop, screen shake, sparks, slow-motion KOs, cinematic supers, a camera that
   breathes with the fight. Every hit has a sound and a flash.
2. **Easy to pick up, deep to master.** Simple controls give every special on one button; Classic gives full
   damage and motion inputs. Chains (L→M→H) make combos reachable on day one; juggles, wall splats, Just
   Blocks, Breakers and meter routes reward practice.
3. **Fair online.** Deterministic simulation with rollback netcode so a match between friends feels local.
4. **Dungeon Joe's voice.** Grim, beautiful realms; deadpan jokes about rent, leases and Management.

## 2. Tech

- Static site in `public/` (no build step, plain ES modules), like the owner's other games. `three.js r187`
  + addons bundled once into `public/vendor/three.bundle.js` (`tools/vendor.mjs`). PeerJS for WebRTC.
- `public/shared/` — the **simulation**: pure, deterministic, integer-only, runs in browser and Node (tests,
  bots). No DOM, no `Math.random`, no floating-point trig.
- `public/js/` — everything else: rendering, animation, VFX, audio, input, UI, networking, profile.
- Assets: `public/assets/fighters/<id>.glb` (UAL 65-bone rig, WebP textures ≤1024, meshopt),
  `public/assets/anim/*.glb` (clip packs, skeleton only), `public/assets/stages/…`, `public/assets/sfx/…`.
  Produced by `tools/assets.mjs` from the Dungeon Joe 3D sources and our Blender work in `art/`.
- Deploy: push `main` → `.github/workflows/ready.yml` runs `npm test` (headless bot matches + rule tests) and
  moves `ready`; the `games` repo (`deploy/library.json`) publishes `public/` at `/games/joebrawla/` with
  `tools/stamp-build.mjs`.

## 3. Simulation

- 60 frames per second, fixed. One `step(state, inputP1, inputP2)` per frame. State is a plain JSON-able object
  (cloned for rollback).
- **Units:** 1 unit = 0.1 mm. 1 m = 10 000 units. Stage is 16 m wide (walls at ±80 000). Max distance between
  fighters 6.4 m (camera limit). Moves are authored in centimetres (×100 at load).
- Integer math only (`Math.trunc`, `Math.floor`, `+ - * /` then truncate); a seeded xorshift RNG in state.
- **Fighter state:** position, velocity, facing, hp, meter (0–3000, 1000 per bar), action (move id + frame),
  hitstun/blockstun timers, juggle points, combo count/damage/scaling, knockdown/wake-up, invulnerability,
  armour, charge timers, input history (for motion inputs), Overtime flag, per-character variables.
- **Boxes:** each fighter has hurtboxes (stand/crouch/air, moves can extend them), a pushbox, and moves have
  hitboxes per active window. Projectiles are entities with their own boxes, hit counts and durability.
- **Order each frame:** read inputs → interpret commands → advance actions → physics → pushbox separation →
  hit detection (both sides at once, trades allowed) → apply hits → projectiles → timers → round logic.
- **Hitstop** freezes both fighters (attacker 1 frame less on block). **Slow-motion** KO and super-flash
  freezes are simulation timers too, so they replay identically under rollback.

## 4. Controls

Four attack buttons and one Super button: **L**ight, **M**edium, **H**eavy, **S**pecial, **Super**.

| Action | Classic | Simple |
|---|---|---|
| Normals | L, M, H (stand, crouch, jump; some 6/3/4 + button command normals) | same |
| Chains | L→L→L, L→M→H (on hit or block), cancel into specials | same, plus **auto-combo**: L, L, L ends in a special |
| Specials | motion + L/M/H (strength) e.g. 236L | **S** + direction (S, 6S, 4S, 2S, j.S), fixed medium strength, 85 % damage |
| EX special (½ bar) | motion + any two of L/M/H | S + H together (+ direction) |
| Super Art (1 bar) | 236236 + any attack, or Super | Super |
| Final Notice (3 bars, cinematic) | 214214 + any attack, or 2 + Super | 2 + Super |
| Overtime Art (HP ≤ 25 %, once per match) | Super + S | Super + S |
| Throw | L+M near (4 = back throw) | same |
| Breaker (1 bar) | M+H: armoured rush; while blocking: Breaker Reversal | same |
| Dash / back dash | 66 / 44 | same |
| Taunt | Select / Backspace | same |

Default bindings (all rebindable, per player):

| | Keyboard (WASD) | Keyboard + mouse | Arrows (P2 couch) | Gamepad |
|---|---|---|---|---|
| Move | WASD | WASD | Arrows | D-pad / left stick |
| L / M / H | J / K / L | Left click / Middle click or E / Right click | Num1 / Num2 / Num3 | X / Y / RB |
| S | I | Space | Num4 | A |
| Super | O | Shift | Num5 | RT |
| Throw (L+M) | U | Q | Num6 | B |
| Breaker (M+H) | P | F | Num8 | LT |
| Taunt / Pause | Backspace / Esc | same | Num0 / Enter | View / Start |

**Motion inputs** read a 30-frame history with leniency (236 accepts 2→3→6 within 12 frames, 623 accepts 6→2→3
or 6→3→2→3, 214, 41236, 22, 236236, 214214, charge [4]6 = hold back 40 frames). Button press buffer 6 frames;
a special input pressed during the last 6 frames of a cancellable move or blockstun comes out on the first
possible frame. Directions are relative to facing.

## 5. The fighting system

**Movement.** Walk (forward/back speeds per fighter), 4-frame pre-jump, jumps up/forward/back with fixed arcs,
dashes (fixed distance, back dash invulnerable frames 1–7), crouch. Fighters always face each other on the
ground; side switches on cross-ups.

**Blocking.** Hold back: high/mid blocked standing; lows must be blocked crouching; overheads (some 6M, jump
attacks) must be blocked standing. Specials and supers do **chip** (no chip KO unless the modifier says).
**Just Block:** pressing back within 4 frames before a hit lands: no chip, blockstun −4, +80 meter, a white flash
and a ping. Throws beat blocking; throw tech (L+M within 7 frames of being grabbed) breaks it.

**Hits.** Damage, hitstun, blockstun, pushback, hit level (high/mid/low/overhead/unblockable), and an effect:
normal, knockdown, hard knockdown (no quick rise), **launch** (airborne juggle), **crumple** (slow stagger to
the floor), **wall splat** (only within 1.6 m of a wall, once per combo), **ground bounce** (once per combo).
**Counter Hit** (hit during startup): +25 % damage, +3 hitstun, "COUNTER". **Punish Counter** (hit during
recovery): +25 % damage, +6 hitstun, "PUNISH!".

**Combos.** Each hit in a combo scales damage: 100, 100, 80, 70, 60, 50, 40, 30 … (min 10 %), supers min 50 %.
Hitstun decays slightly over long combos. **Juggles:** a launched fighter has 6 juggle points; each hit costs
its move's juggle cost; at 0 they fall out. Gravity rises during a juggle so it always ends.

**Meter ("Power").** 3 bars. Gained by attacking (a little on whiff, more on hit or block), by getting hit
and by Just Blocks. EX specials cost ½ bar, Super Art 1, Breaker 1, Final Notice 3.

**Breaker** (M+H, 1 bar; the Dungeon Joe breakers). Neutral: a 20-frame armoured rush (absorbs one hit) that
crumples on hit and wall splats near a wall; it can be thrown. During blockstun: **Breaker Reversal**, an
invincible push-away hit (no damage KO). The world flashes violet like a tripped breaker.

**Overtime** (comeback). At ≤ 25 % HP a fighter enters Overtime: red heat aura, +10 % damage, and the
**Overtime Art** unlocks once per match (Super + S) — a meterless cinematic super ("Shift's not over till I
say it's over").

**Rounds.** Default best of 3 rounds, 99-second timer (see modifiers). Round intro → "ROUND 1" → "BRAWL!" →
KO (slow-motion, camera swing) or TIME. Double KO and draws handled. Win pose + quote. A perfect round says
"FLAWLESS LEASE" (no damage taken).

## 6. Roster

Thirteen fighters; their moves, stats and lines are in `docs/ROSTER.md` (the data files in
`public/shared/fighters/` are the truth). The 6 open at the start: **Joe, Gary, The Instructor, The Hollow
Knight, Brannigan, The Caretaker**. Then, in order, one per arcade-ladder clear or every 2 player levels:
Mother Spore, The Bloatking, Vexthorn, Foreman Ignatius, Saint Aurelia, Archmagister Tock. **The Landlord**:
clear the arcade ladder on The Landlord difficulty (or Boss Rush on Management+).

| Fighter | Archetype | HP | Model |
|---|---|---|---|
| Joe (Apt 3C) | Shoto all-rounder | 1000 | new (UBC body kitbash) |
| Gary | Trickster, random items | 950 | DJ3D `gary` |
| The Instructor | Counters, technical | 1000 | new |
| The Hollow Knight | Sword and shield footsies | 1050 | DJ3D `hollow_knight` |
| Brannigan | Steam boxer rushdown | 1050 | DJ3D resident `brannigan` |
| The Caretaker | Big body, shovel reach, graves | 1150 | DJ3D boss `caretaker` |
| Mother Spore | Zoner, traps | 950 | new humanoid (DJ3D boss is not humanoid) |
| The Bloatking | Grappler | 1250 | DJ3D boss `bloatking` without throne |
| Vexthorn, the Hollow Stag | Rushdown, teleport | 950 | new |
| Foreman Ignatius | Armoured heavy, fire | 1150 | new |
| Saint Aurelia the Unthawed | Ice keep-away, hover | 900 | new |
| Archmagister Tock | Time tricks, setups | 900 | new |
| The Landlord | Final boss / secret | 1100 | new |

## 7. Stages

Ten 3D stages, each a lit set with foreground floor, midground props, an animated background and particles.
Optional stage hazard per stage (a modifier toggle).

1. **The Mossy Crypt** — graveyard valley, morning sun (hazard: grave hands).
2. **The Fungal Hollows** — glowing sinkhole cave open to the sky (falling caps).
3. **The Drowned Quarter** — flooded old city in rain (rising water slows).
4. **The Hollow Forest** — autumn, golden hour (falling branches).
5. **The Ashen Forge** — volcanic foundry at dusk (lava eruptions).
6. **The Frozen Reliquary** — mountain cathedral at noon, snow (icy floor).
7. **The Clockwork Citadel** — brass sky-city above the clouds (giant pendulum).
8. **The Abyss** — the Landlord's desk on a rock in a starry void (static rifts).
9. **The Landing** — the residents' sunny stone courtyard with the hearth.
10. **Building Nine Basement** — the breaker box, flickering bulbs (blackouts).
Plus the **Training Hall** (Management's orientation room) for training mode.

## 8. Modes

- **Online Versus** (friends and codes only): make a lobby (4-digit room code + invite link `?room=1234`) or
  join a friend's from the friends list. Exactly 2 people. Host sets modifiers (guest sees them live), each picks
  a fighter and colour in the lobby, host picks the stage (or Random / Guest's choice). Ready → match → results
  → Rematch (same picks) or Lobby. Running set score. Quick chat lines and taunts. Ping and input delay shown.
- **Versus Bot**: pick fighter, bot fighter, difficulty (Tenant, Superintendent, Management, The Landlord),
  stage, modifiers.
- **Couch Versus**: two players on one PC; "press any button" to claim a device (keyboard WASD, keyboard arrows,
  each gamepad).
- **Arcade Ladder**: 8 fights through the realms, each opponent on their home stage, story cards between,
  a rival fight 7, The Landlord (boss version, three phases: The Interview, The Eviction, The Deep Lease) at 8.
  Choose the difficulty at the start. An ending card per fighter.
- **Survival**: one health bar, 15 % heal between fights, opponents get harder; best streak saved and shown to
  friends.
- **Boss Rush**: the eight realm rulers (Caretaker, Mother Spore, Bloatking, Vexthorn, Ignatius, Aurelia, Tock,
  The Landlord) as boss versions (+40 % HP, light armour on heavies) back to back; best time saved.
- **Training**: dummy (stand, crouch, jump, block none/all/after first hit/random, CPU at any difficulty,
  record and play back 10 s), hitbox view, frame data (startup / on-hit / on-block), input display, damage and
  combo readout, infinite meter/HP toggles, reset to centre or either corner, move list.

## 9. Bots

One AI (`shared/bot.js`) driven by a difficulty profile; it sees the state **N frames late** (reaction time)
and makes decisions with seeded randomness:

| | Tenant | Superintendent | Management | The Landlord |
|---|---|---|---|---|
| Reaction | 28 f | 18 f | 12 f | 8 f |
| Blocks a seen attack | 30 % | 55 % | 80 % | 93 % (right height) |
| Combos | single hits | 2–3 hit chains | hit-confirmed chains → special | optimal routes, meter, juggles |
| Anti-air | rare | sometimes | usually | almost always |
| Throws / tech | rarely / never | some / 20 % | yes / 50 % | mixes / 75 % |
| Punish / whiff punish | no | big whiffs | most | nearly all |
| Uses meter | no | Super when full | EX, Supers, Breaker | everything, Overtime Art |

## 10. Online

- **Identity:** a permanent 4-digit **friend code** per player (claimed on the relay so no two players share it),
  a name, saved in the browser. Adding a friend sends a request to their mailbox (works offline). Friends list
  shows online / in a lobby / in a match / last seen, with **Join** and **Invite**. Rivalry record per friend.
  Recent opponents can be added. Adapted from Don't Wake Gerald's `friends.js` / `relay.js` (topics under
  `jjgames/joebrawla-v1/`, PeerJS ids `joebrawla-v1-…`).
- **Room codes:** 4 digits (1000–9999), invite link `?room=1234`. A third person is told the lobby is full.
- **Transport:** WebRTC data channel via PeerJS; if it fails within 6 s, the public MQTT relay (higher latency).
- **Rollback netcode** (`js/net/rollback.js`): both sides run the same sim; inputs are exchanged every frame with
  redundancy (each packet carries the last 8 frames of inputs). Remote input is predicted (repeat last);
  on a misprediction, restore the snapshot and resimulate. Input delay 2 frames by default (auto 1–4 by ping),
  max rollback 8 frames; time sync slows the side that is ahead. Checksums every 30 frames detect desyncs (logged,
  then the host's state wins). Presentation (sounds, sparks, shakes) is derived from state changes and
  de-duplicated across rollbacks.

## 11. Modifiers

Host toggles in every lobby (and in bot / couch / training). Saved per mode.

- **Match:** rounds to win 1/2/3/5; timer 30/60/99/∞; starting HP 50/100/150/200 %; damage ×0.5/×1/×1.5/×2/×3;
  meter normal / start full / infinite / none; game speed 0.8/1/1.2/1.4 (Turbo).
- **Physics:** gravity low / normal / heavy; bouncy walls (wall hits bounce, always splat); infinite juggles;
  no knockdowns (instant recover).
- **Chaos:** Big Heads; Tiny / Giant fighters; Vampire (heal 30 % of damage dealt); One-Hit KO; Glass Cannons
  (×3 damage both ways, HP 50 %); Projectile Party (projectile specials have no limit and cost no recovery);
  Overtime Always On; Sudden Death (both at 1 HP after time); Random Fighter each round; Mirror Match;
  Item Drops (Gary's wares fall from the sky: Thermos heals, bombs explode, coins give meter);
  Stage Hazards on/off; Blackouts (the lights go out for 2 s at random; fighters glow).
- **Rules:** chip KO on/off; throws on/off; Breaker on/off; Just Block window 4/8 f; Simple-scheme damage
  penalty on/off.
- **Presets:** Standard, Tournament, Party Chaos, Glass Cannons, Juggle Fest (low gravity + infinite juggles),
  Speed Demons (Turbo + meter start full), Hardcore (One-Hit KO + no Breaker).

## 12. Progression

- XP after every match (win 100, loss 60, +perfect, +first win of the day, +friend match bonus). Levels.
- Fighter unlocks as in §6. A locked fighter shows its silhouette and how to unlock it.
- Per fighter: mastery level (wins), **colours** (8 palettes: default + 7 unlocked by mastery), win quotes.
- Titles (shown on the VS screen and friends list) from achievements. Taunts.
- Stats: wins/losses overall and per fighter, longest combo, Survival best, Boss Rush best time,
  rivalry record per friend.
- Saved in `localStorage` (`joebrawla-v1`), with a "move code" to carry a save to another PC (as Don't Wake
  Gerald does).

## 13. Presentation

- **Rendering:** three.js WebGL2, ACES tone mapping, PBR models, per-stage HDRI or sky shader for image lighting,
  a key light with a tight shadow frustum around the fighters, two coloured rim lights per stage (fighters pop
  against the background), bloom, a final pass (vignette, colour grade, chromatic flash on big hits, radial blur
  in supers), FXAA/SMAA. Quality presets Low/Medium/High/Ultra.
- **Camera:** side view, 32° FOV, follows the midpoint, zooms with distance, leans in on jumps; kicks on
  heavy hits; cinematic cuts for intros, supers, KOs, win poses.
- **Animation** (`js/anim/`): every move is a timeline locked to its frame data. Sources: (a) clip segments
  from the UAL and Dungeon Joe 3D libraries, retimed; (b) **procedural key poses** built with two-bone IK
  (hand/foot targets, spine bend/twist, pelvis drop) for kicks and anything the libraries lack; (c) additive
  layers: hit reactions (springs), breathing, head look-at, landing squash. Crossfades 2–4 frames.
  Rendering interpolates between sim frames.
- **VFX:** hit sparks by strength and type (blood-free: light, dust, sparks, spores, ice, embers), slash trails
  on limbs and weapons, shockwave rings, dust on landings, afterimages on dashes and supers, super flash with a
  portrait cut-in, KO shatter of light, Overtime heat aura, Just Block shine, Breaker violet surge.
- **Audio:** Kenney impact sounds (CC0) layered with synthesized whooshes, thumps and crunches;
  synthesized music per stage; an announcer (big title cards, plus the browser's speech voice if the player
  turns it on).
- **UI:** HUD with health bars (red recoverable damage trail), meter bars, round pips, timer, combo counter,
  "COUNTER/PUNISH/JUST BLOCK" callouts, input display (training). Character select with 3D model preview,
  lore blurb and colour picker; VS splash with titles and friend rivalry; results with stats.

## 14. Art specifications (for `art/` work)

- **Rig:** UAL 65-joint skeleton (bone names exactly as Quaternius UAL1), Y-up, facing +Z (glTF), feet at
  origin, A-pose rest from the UBC bodies. Extra bones allowed (e.g. Bloatking's `belly`, `crown`); weapons and
  props skinned to `hand_r` / `hand_l` or a socket bone.
- **Size:** humans 1.80–1.95 m; big bodies (Caretaker, Bloatking, Ignatius) 2.1–2.3 m; Landlord 2.0 m.
- **Budget:** 20–45 k triangles, ≤ 6 materials, PBR textures authored at 2048 (shipped at 1024 WebP).
- **Colours:** materials named `tint1_*` (main cloth) and `tint2_*` (accent) are recoloured for alternate
  palettes; everything else keeps its texture.
- **Look:** the Dungeon Joe 3D style (stylized PBR, chunky readable silhouettes, worn materials), pushed further
  for a fighting game: bigger hands and heads by ~8 %, strong silhouettes from the side, emissive accents
  (eyes, lanterns, runes) for bloom.
- Each fighter: `art/fighters/<id>/` (Blender scripts, previews) → `public/assets/fighters/<id>.glb`.
