# Moveset brief (for the helper agents writing fighters)

You are writing complete, tournament-feeling movesets **and** their 3D animations for JoeBrawla, a browser
fighting game (Street Fighter rules, Tekken-style juggles, three.js). Each fighter you own is two files:

- `public/shared/fighters/<id>.js` — frame data (the deterministic simulation reads this)
- `public/js/anim/sets/<id>.js` — how every move looks (render only)

Both currently hold a **placeholder copy of Joe**; replace them entirely.

## Read first

1. `docs/DESIGN.md` §4–§5 (controls, fighting system) and §13 (presentation).
2. `docs/ROSTER.md` — your fighters' **Look**, **Moves** and **Lines**. Implement every move listed there
   (names, inputs, behaviour). You may add normals/command normals; keep the listed specials and supers.
3. The reference fighter: `public/shared/fighters/joe.js` and `public/js/anim/sets/joe.js`. Match its
   structure, completeness and polish.
4. Schema and engine: `public/shared/movekit.js` (authoring format, cm and frames), `public/shared/sim.js`
   (what every field does), `public/shared/fighters/common.js` (throws, Breaker, taunt via `universal()`).
5. Animation: `public/js/anim/poses.js` (pose parameters and the shared pose library), `public/js/anim/animator.js`
   (keys: `[time, pose, ease]`; time is a frame number or `'s'` first active frame, `'a'` last active frame,
   `'e'` end, with offsets like `'s+2'`, `'a-1'`, `'e-4'`; eases `io`, `in`, `out`, `lin`, `snap`),
   `public/js/anim/sets.js` (BASE states every fighter inherits: idle, walk, crouch, jump, hit, knockdown…).
6. Clips you can use: `docs/CLIPS.md` (base pack is always loaded; add `packs: ['weapons']` to your set to use
   the weapon pack; a model's own clips, e.g. `Caretaker_ShovelSwing`, are available for that fighter).

## Engine features you can use (all in sim.js)

Hits: `dmg, chip, stun, bstun, push, level (mid|low|ovh|unbl), effect (normal|kd|hkd|launch|crumple|splat|bounce),
launch [vx, vy] cm/f, juggle, hitstop, spark (L|M|H|X|S|flare|fire|ice|spore|void|water), sfx, wallSplat`.
Moves: `startup/active/recovery, hits[] (frames, box [x,y,w,h] cm from the feet, x forward), hurt[] (extended
hurtboxes), vel [[frame, vx, vy]] cm/f, air (jump attacks), landCancel/landRecovery (rising moves), invuln
{strike, throw, proj, full: [a,b]}, armor {frames, hits}, cancel {into: [ids], special, super}, crouching,
float [a,b] (slow fall), cost (meter), freeze (super flash frames)`.
Projectiles (`proj`): `at, kind, x, y, vx, vy, gravity, life, box, hits, every, power, hit {…}, place ('opp' |
'dist' with dist), random [kinds] + variants {kind: overrides}, trap {arm, range, delay, vx}, hop {delay, vx, vy},
harmless (a wall that only eats projectiles), follow (cm in front of the owner: beams/auras), ground`.
`oneProj: true` on a special = one at a time. Specials: `{ id, motion ('236'|'214'|'623'|'41236'|'22'),
simple (5|6|4|2 = the S-button direction), air: true for air specials, needs(f, state) }`.
Effects (`fx: [{ at, kind }]`): `heal {pct}`, `meter {n}`, `teleport {to: behind|front|rewind|forward, dist}`,
`setvar/addvar {name, value}` (per-round fighter vars; `vars.freeEX > 0` makes the next special EX for free),
`timestop {frames}`, `stealMeter {n}`. Grabs: `grab {range, len, dmgAt, toss [vx,vy], hold, switchSide,
techable: false, steal}` with `hits[]` for the damage. Counter stances: `counter {frames, into: moveId}` (the
`into` move needs `grab`). Reflect: `reflect: [a, b]`. Cinematic supers: `cine {len, hold, hits: [[frame, dmg]]}`
(the first hit connects, then a scripted sequence; animate it in the set's `cine` map).
If you truly need an engine feature that does not exist, do not edit sim.js: write it up in your report.

## Numbers that keep the game fair

HP 900–1250 (ROSTER). Light ~25–35 dmg, startup 3–5; Medium 45–60, 6–9; Heavy 70–95, 9–14. Specials 60–140.
Super Art (1 bar) ~260–320 total; Final Notice (3 bars) ~420–480; Overtime Art ~360–400. Most normals –2 to +3
on block; heavy specials unsafe unless they're the character's thing. Every fighter needs: a fast poke, a
low, an overhead, an anti-air, a combo that works from a light hit (chains in `cancel.into`), a launcher or a
juggle route, something with invulnerability **or** armour, and a reason to use meter. Big bodies are slower
(walk 3.0–3.8 cm/f, dash 22–26 f) with longer reach and armour; small/fast ones walk 4.6–5.2. Set
`width/height/crouchHeight` to the body (Caretaker/Bloatking ~60–72 wide). `autoCombo` = the Simple-scheme L-mash
route. Give `colors` (8 hex strings; [0] is the default look) and `lines` (`intro`, `win: [3 lines]`).

## Animation quality bar

Every move must read clearly from the side camera: anticipation (wind-up), a sharp strike on frame `'s'`, a held
contact pose, a readable recovery. Use clips where they fit (weapon swings, casts, bosses' own moves, retimed
with clip times `ct`/fractions `cf` on the keys) and procedural poses (IK targets) for everything else (kicks,
specific strikes). Weapon fighters need their own stance (`states.idle`, `walkF`, `walkB`, `crouch`, `block`,
`cblock`, `jumpU/F/B` as needed) holding the weapon properly. Big supers (`cine`) should be spectacular: several
distinct beats, big wind-ups, a finisher pose. Put fighter-specific poses in the set's `poses` map, names prefixed
with the fighter id (they're merged into the library). Optional `look: { trail: …, tint1: [...], tint2: [...] }`.

## Check your work

- `npm test` (headless): every fighter compiles, has its supers, and bots finish matches. It must pass.
- Visual: the preview server runs at http://localhost:8095 (start it with the Browser pane's launch config
  `joebrawla` if it isn't). **Open your own browser tab** (never navigate other tabs) at
  `http://localhost:8095/?quick&skip&dev&p1=<id>&p2=joe` and in the page run `closeCam(-1.5, true)` then
  `sheet([[moveId, frame], ['s:idle', 10], …], 4)` to see a contact sheet of poses; `unsheet()` to resume.
  `&bot1=3&bot2=3` watches two bots fight. New models may still be in progress: if a fighter's own model isn't
  in `public/assets/fighters/` yet, it shows a stand-in; pose with IK so it will fit the real body.
- Only edit your fighters' two files each. Do not edit other files, do not run git commands that change
  state. Do not stop to ask questions; choose and note it.

When done, reply with: per fighter, a short summary of the kit (specials, supers, notable frame data), what you
verified (tests, contact sheets), and anything you couldn't do.
