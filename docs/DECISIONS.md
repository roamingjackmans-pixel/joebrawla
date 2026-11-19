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
- **D9** Motions are judged at the moment a button is pressed and remembered with that press, and button buffers
  don't age during hitstop or super freezes, so specials pressed during hitstop come out (Street Fighter feel).
- **D10** Proximity guard: holding back while an attack is coming makes you stand your ground instead of walking
  away (otherwise blocking felt like retreating out of range).
- **D11** Rollback: 2-frame input delay default (1–4 in settings), 10 frames max rollback, inputs sent with 10
  frames of redundancy over a reliable PeerJS channel, opponent's buttons never predicted (directions only),
  checksums every 60 confirmed frames.
- **D12** Online matches keep simulating in hidden or throttled tabs (worker timer); offline matches pause.
- **D13** Stage hazards and blackouts are deterministic (sim RNG / frame count) so they work online.
- **D14** The Landlord boss version (arcade fight 8, Boss Rush): +40 % HP; from round 2 one hit of armour on
  every special and super ("The Eviction"); from round 3 +20 % damage ("The Deep Lease").
- **D15** Character portraits are rendered from each fighter's model at runtime (no image files to keep in sync).
- **D16** Menu key presses are queued as events (a tap is never lost on a slow frame); game inputs latch taps
  for 45 ms.
