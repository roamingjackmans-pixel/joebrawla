# CLAUDE.md — JoeBrawla

A 3D side-view fighting game (SF6/Tekken presentation, SF rules + Tekken juggles) in the Dungeon Joe world.
Browser, static files, three.js. Online 1v1 with 4-digit friend/room codes (rollback netcode over PeerJS,
MQTT relay fallback), 4 bot difficulties, couch, training, arcade ladder, Survival, Boss Rush.
Hosted at `https://josephjackman.com/games/joebrawla/` from the `ready` branch of
`roamingjackmans-pixel/joebrawla` via the `games` repo (`C:\dev\DungeonJoe\deploy\library.json`).

## How we work
- Owner (2026-11-19): **build everything without stopping**; decide, log it in `docs/DECISIONS.md`, keep going.
- Windows 11 + PowerShell 5.1 for anything given to the owner (chain with `;`). Git Bash available to us.
- Commit and push at milestones on `main` (conventional messages).

## Read first
1. `docs/DESIGN.md` — systems, controls, modes, modifiers, netcode, presentation, art spec
2. `docs/ROSTER.md` — the 13 fighters: look, moves, lines
3. `docs/DECISIONS.md` — why things are the way they are
4. `docs/PROGRESS.md` — what is built and what is next

## Rules that are easy to break
- `public/shared/` is the deterministic simulation: integers only, no `Math.random`, no trig, no DOM, no
  `Date`. It must give identical results in every browser (rollback depends on it). Randomness only from the
  state's RNG.
- Presentation (sound, sparks, camera) never changes the simulation; it is derived from state and must cope
  with rollbacks (events are de-duplicated by frame).
- Moves are data in `public/shared/fighters/<id>.js`; animation timing is keyed to move frames.
- Art: every fighter is on the UAL 65-bone rig (`art/BRIEF.md`). Source art lives outside git (`art/_work/`).
- Never use the Quaternius Bestiary pack (not CC0) — the repo is public.

## Commands
```powershell
npm start            # http://localhost:8095/  (preview in the desktop app's browser pane: launch config "joebrawla")
npm test             # headless rule tests + bot-vs-bot matches (what CI runs)
npm install; node tools/vendor.mjs                     # rebuild public/vendor/three.bundle.js
node tools/assets.mjs fighter <src.glb> <id>           # compress a fighter for the game
node tools/assets.mjs anims <name> <src.glb>:<clips>   # build an animation pack
```
