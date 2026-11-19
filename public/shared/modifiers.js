// Game modifiers: the host's toggles in a lobby (and in bot / couch / training setups). docs/DESIGN.md §11.
// MODS lists every modifier for the UI; resolveModifiers(choice) turns a choice into the sim's cfg numbers.

export const MODS = [
  // match
  { id: 'rounds', group: 'Match', name: 'Rounds to win', opts: [1, 2, 3, 5], def: 2, fmt: (v) => `${v}` },
  { id: 'timer', group: 'Match', name: 'Round timer', opts: [30, 60, 99, 0], def: 99, fmt: (v) => (v ? `${v} s` : '∞') },
  { id: 'hp', group: 'Match', name: 'Starting health', opts: [50, 100, 150, 200], def: 100, fmt: (v) => `${v} %` },
  { id: 'damage', group: 'Match', name: 'Damage', opts: [50, 100, 150, 200, 300], def: 100, fmt: (v) => `×${v / 100}` },
  { id: 'meter', group: 'Match', name: 'Power meter', opts: ['normal', 'full', 'infinite', 'none'], def: 'normal', fmt: (v) => ({ normal: 'Normal', full: 'Start full', infinite: 'Infinite', none: 'None' })[v] },
  { id: 'speed', group: 'Match', name: 'Game speed', opts: [80, 100, 120, 140], def: 100, fmt: (v) => (v === 100 ? 'Normal' : v > 100 ? `Turbo ${v} %` : `Slow ${v} %`) },
  // physics
  { id: 'gravity', group: 'Physics', name: 'Gravity', opts: [60, 100, 140], def: 100, fmt: (v) => ({ 60: 'Low', 100: 'Normal', 140: 'Heavy' })[v] },
  { id: 'bouncyWalls', group: 'Physics', name: 'Bouncy walls', opts: [false, true], def: false, desc: 'Walls bounce fighters back and always splat.' },
  { id: 'infiniteJuggle', group: 'Physics', name: 'Infinite juggles', opts: [false, true], def: false, desc: 'No juggle limit, bounce again and again.' },
  { id: 'noKnockdown', group: 'Physics', name: 'No knockdowns', opts: [false, true], def: false, desc: 'Knockdowns become ordinary hits.' },
  // chaos
  { id: 'bigHeads', group: 'Chaos', name: 'Big heads', opts: [false, true], def: false, render: true },
  { id: 'size', group: 'Chaos', name: 'Fighter size', opts: ['normal', 'tiny', 'giant'], def: 'normal', render: true, fmt: (v) => ({ normal: 'Normal', tiny: 'Tiny', giant: 'Giant' })[v] },
  { id: 'vampire', group: 'Chaos', name: 'Vampire', opts: [false, true], def: false, desc: 'Heal 30 % of the damage you deal.' },
  { id: 'oneHitKO', group: 'Chaos', name: 'One-hit KO', opts: [false, true], def: false, desc: 'Any clean hit wins the round.' },
  { id: 'glassCannons', group: 'Chaos', name: 'Glass cannons', opts: [false, true], def: false, desc: 'Half health, triple damage.' },
  { id: 'projectileParty', group: 'Chaos', name: 'Projectile party', opts: [false, true], def: false, desc: 'Throw as many projectiles as you like.' },
  { id: 'overtimeAlways', group: 'Chaos', name: 'Overtime always on', opts: [false, true], def: false, desc: 'Everyone starts in Overtime: +10 % damage and the Overtime Art.' },
  { id: 'suddenDeath', group: 'Chaos', name: 'Sudden death', opts: [false, true], def: false, desc: 'A draw on time puts both at 1 HP for 30 more seconds.' },
  { id: 'randomEachRound', group: 'Chaos', name: 'Random fighter each round', opts: [false, true], def: false },
  { id: 'itemDrops', group: 'Chaos', name: "Gary's item drops", opts: [false, true], def: false, desc: 'Thermoses heal, coins give meter, bombs explode.' },
  { id: 'hazards', group: 'Chaos', name: 'Stage hazards', opts: [false, true], def: false, desc: "Each realm's own trouble." },
  { id: 'blackouts', group: 'Chaos', name: 'Blackouts', opts: [false, true], def: false, render: true, desc: 'The lights go out now and then. Fighters glow.' },
  // rules
  { id: 'chipKO', group: 'Rules', name: 'Chip KO', opts: [true, false], def: true },
  { id: 'throws', group: 'Rules', name: 'Throws', opts: [true, false], def: true },
  { id: 'breaker', group: 'Rules', name: 'Breakers', opts: [true, false], def: true },
  { id: 'justBlock', group: 'Rules', name: 'Just Block window', opts: [4, 8], def: 4, fmt: (v) => `${v} frames` },
  { id: 'simplePenalty', group: 'Rules', name: 'Simple-input damage −15 %', opts: [true, false], def: true },
  { id: 'noBlocking', group: 'Rules', name: 'No blocking', opts: [false, true], def: false },
];

export const PRESETS = {
  Standard: {},
  Tournament: { rounds: 3, timer: 99 },
  'Party Chaos': { itemDrops: true, hazards: true, bigHeads: true, bouncyWalls: true, meter: 'full', blackouts: true },
  'Glass Cannons': { glassCannons: true, rounds: 3 },
  'Juggle Fest': { gravity: 60, infiniteJuggle: true, meter: 'full' },
  'Speed Demons': { speed: 140, meter: 'full' },
  Hardcore: { oneHitKO: true, breaker: false, rounds: 3 },
};

export function defaults() { return Object.fromEntries(MODS.map((m) => [m.id, m.def])); }

/** a choice ({id: value}) -> the simulation's numbers */
export function resolveModifiers(choice = {}) {
  const c = { ...defaults(), ...choice };
  const cfg = {
    mods: c,
    rounds: c.rounds, timer: c.timer, hpPct: c.hp, dmgPct: c.damage, meterMode: c.meter, speedPct: c.speed,
    gravityPct: c.gravity, bouncyWalls: c.bouncyWalls, infiniteJuggle: c.infiniteJuggle, noKnockdown: c.noKnockdown,
    vampire: c.vampire, oneHitKO: c.oneHitKO, projectileParty: c.projectileParty, overtimeAlways: c.overtimeAlways,
    suddenDeath: c.suddenDeath, randomEachRound: c.randomEachRound, itemDrops: c.itemDrops, hazards: c.hazards,
    chipKO: c.chipKO, throws: c.throws, breaker: c.breaker, justBlock: c.justBlock, simplePenalty: c.simplePenalty,
    noBlocking: c.noBlocking,
    meterStart: c.meter === 'full' || c.meter === 'infinite' ? 3000 : 0,
  };
  if (c.glassCannons) { cfg.hpPct = Math.trunc(cfg.hpPct / 2); cfg.dmgPct = cfg.dmgPct * 3; }
  return cfg;
}

/** short labels of the non-default modifiers (VS screen, lobby summary) */
export function activeLabels(choice = {}) {
  const out = [];
  for (const m of MODS) {
    const v = choice[m.id];
    if (v === undefined || v === m.def) continue;
    out.push(typeof v === 'boolean' ? m.name : `${m.name}: ${m.fmt ? m.fmt(v) : v}`);
  }
  return out;
}
