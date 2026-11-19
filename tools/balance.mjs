// Balance report: every fighter vs every fighter with The Landlord-level bots, both sides, N matches each.
//   node tools/balance.mjs [matchesPerPair=4] [level=3]
// Prints each fighter's win rate, average round length and damage per hit, and the most lopsided matchups.
import { createMatch, step } from '../public/shared/sim.js';
import { ORDER } from '../public/shared/fighters/index.js';
import { Bot } from '../public/shared/bot.js';

const N = +(process.argv[2] || 4), LV = +(process.argv[3] || 3);
const ids = ORDER;
const res = Object.fromEntries(ids.map((id) => [id, { w: 0, l: 0, frames: 0, rounds: 0, dmg: 0, hits: 0 }]));
const pair = {};
for (const a of ids) for (const b of ids) {
  if (a === b) continue;
  for (let k = 0; k < N; k++) {
    const m = createMatch({ fighters: [a, b], seed: `${a}-${b}-${k}`, skipIntro: true, mods: { rounds: 2 } });
    const bots = [new Bot(LV, k * 7 + 1), new Bot(LV, k * 7 + 2)];
    let n = 0;
    while (m.state.phase !== 'matchEnd' && n < 60 * 60 * 8) { step(m, [bots[0].think(m, 0), bots[1].think(m, 1)]); n++; }
    const w = m.state.winner;
    const rounds = m.state.wins[0] + m.state.wins[1];
    for (const [i, id] of [[0, a], [1, b]]) {
      const r = res[id];
      if (w === i) r.w++; else if (w === 1 - i) r.l++;
      r.frames += n; r.rounds += rounds; r.dmg += m.state.f[i].stats.dmg; r.hits += m.state.f[i].stats.hits;
    }
    const key = [a, b].sort().join(' vs ');
    pair[key] ||= { [a]: 0, [b]: 0 };
    if (w >= 0) pair[key][[a, b][w]]++;
  }
}
console.log(`\nWin rates (bots at level ${LV}, ${N} matches per ordered pair)\n`);
console.log('fighter'.padEnd(16), 'win %'.padStart(6), 'sec/round'.padStart(10), 'dmg/hit'.padStart(8));
for (const id of ids.slice().sort((x, y) => res[y].w / (res[y].w + res[y].l || 1) - res[x].w / (res[x].w + res[x].l || 1))) {
  const r = res[id];
  console.log(id.padEnd(16), (100 * r.w / (r.w + r.l || 1)).toFixed(0).padStart(6), (r.frames / 60 / Math.max(1, r.rounds)).toFixed(1).padStart(10), (r.dmg / Math.max(1, r.hits)).toFixed(0).padStart(8));
}
const lop = Object.entries(pair).map(([k, v]) => { const [x, y] = Object.keys(v); const t = v[x] + v[y]; return [k, t ? Math.max(v[x], v[y]) / t : 0.5, v]; }).sort((p, q) => q[1] - p[1]).slice(0, 8);
console.log('\nMost lopsided matchups:');
for (const [k, r, v] of lop) console.log(' ', k.padEnd(30), (r * 100).toFixed(0) + '%', JSON.stringify(v));
