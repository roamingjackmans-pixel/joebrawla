# Progress

## Done
- **Simulation** (`public/shared/`): deterministic integer sim at 60 Hz: movement, dashes, jumps, blocking
  (high/low/overhead), proximity guard, Just Block, chains and cancels, specials with Classic motions and Simple
  S-button inputs, EX upgrades, Super Art / Final Notice / Overtime Art with cinematics, throws and techs,
  command grabs, counters, reflects, armour, invulnerability, projectiles (traps, hoppers, walls, beams),
  juggles with points and rising gravity, wall splats, ground bounces, crumples, counter/punish counters, combo
  scaling, meter, Breaker and Breaker Reversal, rounds, timer, KO slow-motion, all 30 modifiers, stage hazards,
  item drops, Landlord boss phases.
- **Bots** (`shared/bot.js`): 4 levels with reaction delay, blocking, anti-airs, punishes, hit-confirmed combos,
  meter use.
- **Rendering**: three.js scene with ACES, shadows, rim lights, bloom, grading, FXAA; fight camera with shakes
  and cinematic cuts (intro, supers, KOs); effects (sparks, streaks, rings, dust, trails, projectiles, hazard
  warnings); HUD; procedural realm stages and a JSON-driven loader for the stage GLBs.
- **Animation**: UAL rig, clip sampling with retiming, two-bone IK pose system, crossfades, flinch springs,
  per-fighter sets; base states for every action.
- **Game**: title, main menu, settings (controls with rebinding for keyboard / keyboard+mouse / pad, video,
  audio, profile, save codes), character select with 3D models and generated portraits, stage select, rules
  (modifiers + presets), VS, results with XP/levels/unlocks/titles, pause, move lists. Modes: Versus Bot, Couch
  (device claiming), Training (dummy, recording, hitboxes, frame data, inputs), Arcade Ladder (story cards,
  rival, Landlord boss, endings), Survival, Boss Rush.
- **Online**: friend codes, friends list, requests, invites, presence (from Don't Wake Gerald), 2-player
  lobbies with host rules, stage, ready, quick chat, set score; rollback netcode (verified in Node with a jittery
  link and between two real browsers); hidden-tab netplay via a worker clock.
- **Models**: joe, instructor (new), mother_spore, vexthorn (new), gary, caretaker, hollow_knight, brannigan,
  bloatking (DJ3D, compressed).
- **Deploy**: repo `roamingjackmans-pixel/joebrawla`, `ready.yml` CI (tests + ready branch), `stamp-build.mjs`.

## Paused when the usage limit was reached (2026-11-19)
Helper agents were stopped; their finished work is in the repo, the rest is still a placeholder.
- Movesets + animation sets DONE: gary, instructor, brannigan, mother_spore (caretaker partly).
  STILL PLACEHOLDER (Joe's moves): hollow_knight, bloatking, ignatius, landlord, vexthorn, aurelia, tock.
- Models: all in except **landlord** (shows Gary); aurelia/tock/ignatius were exported but not reviewed in-game.
- Stages: none finished. crypt and forge have stage.json but no compressed GLB yet; every realm shows its
  procedural look. Blender scripts in art/stages/ can be resumed.
- Balance (tools/balance.mjs 2 3): bloatking/ignatius 71 %, caretaker 31 % — re-run after the movesets land.

## Next
1. Review and integrate each agent's work (contact sheets, bot matches, balance).
2. Copy stage.json files to `public/assets/stages/<id>.json`.
3. Trim the weapons clip pack to the clips the sets use.
4. Add JoeBrawla to the games site (`C:\dev\DungeonJoe\deploy\library.json`).
