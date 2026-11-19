# 🥊 JoeBrawla

A 3D fighting game in the world of **Dungeon Joe**: Street Fighter rules with Tekken-style juggles and wall
splats, cinematic supers, thirteen fighters from the Dungeon Joe lore, ten realm stages, online 1v1 with your
friends (4-digit codes, rollback netcode), four bot difficulties, couch versus, an arcade ladder down to The
Landlord, Survival, Boss Rush and a full training mode.

**Play:** https://josephjackman.com/games/joebrawla/ (keyboard, keyboard + mouse, or any controller)

## The fighters

Joe (Apt 3C) · Gary · The Instructor · The Hollow Knight · Brannigan · The Caretaker (open from the start) ·
Mother Spore · The Bloatking · Vexthorn · Foreman Ignatius · Saint Aurelia · Archmagister Tock (unlock by
playing: one per arcade-ladder clear or every 2 levels) · **The Landlord** (clear the ladder on The Landlord
difficulty). Moves, looks and lines: `docs/ROSTER.md`.

## Controls (defaults, all rebindable in Settings → Keys)

| | Keyboard | Keyboard + mouse | Controller |
|---|---|---|---|
| Move / jump / crouch | WASD | WASD (Space jumps) | D-pad or left stick |
| Light / Medium / Heavy | J / K / L | Left click / E / Right click | X / Y / RB |
| Special | I | Left Shift | A |
| Super | O | R | RT |
| Throw (L+M) | U | Q | B |
| Breaker (M+H) | P | F | LT |
| Taunt · Pause | Backspace · Esc | T · Esc | View · Start |

- **Classic** controls: motion inputs (↓↘→ + attack and friends) at full damage. **Simple**: Special + a direction
  for every special (85 % damage) and an auto-combo on Light. Both work at once; pick per player in Settings or on
  the character select (P / X).
- Chains: L → M → H, then cancel into a special or super. Launchers juggle, heavy hits wall-splat.
- **Power** meter (3 bars): EX specials (½), Super Art (1), Breaker (1), **Final Notice** (3, cinematic).
- **Overtime** under 25 % health: +10 % damage and a once-per-match **Overtime Art** (Super + S).
- **Just Block**: tap back right as a hit lands. **Breaker** (M+H): armoured rush, or a reversal while blocking.

## Playing with friends

Online Versus → you get a permanent **4-digit friend code**. Add friends by code (requests wait if they're
offline), see who's online, **Join** their lobby or **Invite** them. Lobbies have a **4-digit code** and a link
(`?room=1234`), exactly two players. The host sets the rules (30+ modifiers and presets: Party Chaos, Glass
Cannons, Juggle Fest…) and the stage; each player picks a fighter, colour and control style; ready up and brawl.
The set score and your rivalry record with each friend are kept.

Matches use **rollback netcode**: both browsers run the same deterministic simulation and exchange only inputs,
so it plays like you're on the same couch. Connections are peer-to-peer (PeerJS / WebRTC), with a fallback through
public MQTT servers for networks that block that.

## Run it locally

```powershell
cd C:\dev\JoeBrawla; npm start        # http://localhost:8095/
npm test                              # rules, determinism, rollback netcode, bot matches for every fighter
```

Two players on one PC for online testing: open a second tab with `?slot=2` (a separate save), create a lobby in
one and join from the other. Developer shortcuts: `?quick&p1=joe&p2=gary&stage=crypt&bot1=3&bot2=3&skip&dev`.

## How it's built

- `public/shared/` — the simulation: integer-only, deterministic, 60 Hz (`sim.js`), moves as data
  (`fighters/*.js`), input reading (`commands.js`), bots (`bot.js`), modifiers.
- `public/js/` — three.js rendering (`render/`), the IK + clip animation system (`anim/`), effects, HUD, audio
  (Kenney CC0 impacts + synthesized), menus (`ui/`), online (`net/`: friends, relay, transport, rollback).
- `public/assets/` — fighters and stages (GLB, built from the Dungeon Joe 3D models and Blender work in `art/`),
  animation packs (Quaternius UAL, CC0, plus the Dungeon Joe 3D clips), sounds.
- Design and decisions: `docs/DESIGN.md`, `docs/ROSTER.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`.

## Deploying

`.github/workflows/ready.yml` runs the tests on every push to `main` and moves `ready`. The
[games](https://github.com/roamingjackmans-pixel/games) repo publishes it at `josephjackman.com/games/joebrawla/`
(`deploy/library.json`), stamping the version with `tools/stamp-build.mjs`.

## Credits

Characters and world: Dungeon Joe. Animation library: Quaternius Universal Animation Library (CC0). Base bodies,
outfits: Quaternius (CC0). Props: KayKit, Kenney, Quaternius (CC0). Impact sounds: Kenney (CC0).
