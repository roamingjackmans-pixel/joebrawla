# Decisions

Newest last. Each: what, why.

- **D1 (owner, 2026-11-19)** Scope from the owner's answers: 3D side view on the Dungeon Joe 3D models;
  SF-style 2D plane; Classic + Simple controls; 12 fighters + The Landlord; online 1v1 + 4 bot levels + couch +
  training + arcade ladder + Survival/Boss Rush; lobbies of exactly 2; codes and friends only; fighters unlock
  by playing (6 open, quick unlocks); epic look with Dungeon Joe humour; build it all without stopping; public
  repo, `/games/joebrawla/`.
- **D2** Static ES-module site with no build step (like Don't Wake Gerald), so the `games` repo can publish
  `public/` directly; three.js r187 and its addons pre-bundled by esbuild into one vendor file.
- **D3** Story canon is the Dungeon Joe 3D remake's `STORY.md` (Building Nine, The Landlord, breakers,
  residents), the most developed version of the lore; the original game's bosses and classes agree with it.
- **D4** Every fighter is on the UAL 65-bone rig so one animation system drives all of them; the ~370 UAL and
  Dungeon Joe 3D clips are the motion library, retimed to frame data, plus procedural IK key poses for kicks and
  anything the libraries lack (they contain no kicks).
- **D5** Deterministic integer simulation (1 unit = 0.1 mm, 60 Hz) with rollback netcode; the render
  interpolates and never feeds back into the simulation.
- **D6** Four attack buttons (L, M, H, S) + Super, with Throw (L+M) and Breaker (M+H) as macros on their own
  keys too; works on a pad, a keyboard, or keyboard + mouse.
- **D7** Mother Spore's DJ3D model is a non-humanoid boss; she gets a new humanoid fighter model reusing its
  look. The Bloatking ships without his throne.
- **D8** Room codes and friend codes are both 4 digits (room 1000–9999), as the owner asked and as Don't Wake
  Gerald does; friend codes are claimed on the MQTT relay to avoid duplicates.
