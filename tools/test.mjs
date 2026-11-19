// JoeBrawla headless tests: rules, determinism, rollback, and bot-vs-bot matches for every fighter.
//   node tools/test.mjs            (CI runs this; exits 1 on any failure)
//   node tools/test.mjs quick      (skips the long bot matches)
import { createMatch, step } from '../public/shared/sim.js';
import { IN, checksum, CM } from '../public/shared/core.js';
import { FIGHTERS, ORDER } from '../public/shared/fighters/index.js';
import { Bot } from '../public/shared/bot.js';

let fails = 0, passes = 0;
const ok = (cond, msg) => { if (cond) passes++; else { fails++; console.log('FAIL', msg); } };
const quick = process.argv.includes('quick');

function run(match, frames, inputs = () => [0, 0]) {
  const evs = [];
  for (let i = 0; i < frames; i++) { const e = step(match, inputs(i, match.state)); evs.push(...e); }
  return evs;
}
const fresh = (a = 'joe', b = 'joe', mods = {}) => createMatch({ fighters: [a, b], seed: 'test', mods, skipIntro: true });
const toFight = (m) => { run(m, 200); return m; };

// --- every fighter compiles and has the basics
for (const id of ORDER) {
  const d = FIGHTERS[id];
  ok(d.moves.st_L && d.moves.throw && d.moves.breaker, `${id}: basics`);
  for (const s of ['art', 'final', 'overtime']) ok(d.moves[d.supers[s]], `${id}: super ${s}`);
}

// --- a jab at point blank hits
{
  const m = toFight(fresh());
  ok(m.state.phase === 'fight', 'phase reaches fight: ' + m.state.phase);
  m.state.f[0].x = -40 * CM; m.state.f[1].x = 40 * CM;
  const evs = run(m, 20, (i) => [i === 1 ? IN.L : 0, 0]);
  ok(evs.some((e) => e.t === 'hit' && e.who === 1), 'jab hits');
  ok(m.state.f[1].hp === m.state.f[1].maxHp - 30, 'jab does 30: ' + (m.state.f[1].maxHp - m.state.f[1].hp));
}
// --- blocking (P2 holds back = RIGHT, since P1 is on the left)
{
  const m = toFight(fresh());
  m.state.f[0].x = -40 * CM; m.state.f[1].x = 40 * CM;
  const evs = run(m, 30, (i) => [i === 2 ? IN.M : 0, IN.RIGHT]);
  ok(evs.some((e) => e.t === 'block' && e.who === 1), 'st.M blocked');
  ok(m.state.f[1].hp === m.state.f[1].maxHp, 'no chip from a normal');
}
// --- lows must be blocked low
{
  const m = toFight(fresh());
  m.state.f[0].x = -40 * CM; m.state.f[1].x = 40 * CM;
  const evs = run(m, 30, (i) => [i === 2 ? IN.DOWN | IN.L : IN.DOWN, IN.RIGHT]);
  ok(evs.some((e) => e.t === 'hit' && e.who === 1), 'cr.L hits a standing blocker');
}
// --- chain combo L > M > H and a special cancel
{
  const m = toFight(fresh());
  m.state.f[0].x = -40 * CM; m.state.f[1].x = 40 * CM;
  const seq = { 1: IN.L, 9: IN.M, 21: IN.H };
  const evs = run(m, 70, (i) => [seq[i] || 0, 0]);
  const hits = evs.filter((e) => e.t === 'hit' && e.who === 1);
  ok(hits.length === 3, 'L>M>H chain is 3 hits: ' + hits.length);
  ok(hits[2] && hits[2].combo === 3, 'combo counter 3');
}
// --- motion input: 236 + L throws a flare
{
  const m = toFight(fresh());
  const seq = { 1: IN.DOWN, 2: IN.DOWN | IN.RIGHT, 3: IN.RIGHT, 4: IN.RIGHT | IN.L };
  const evs = run(m, 30, (i) => [seq[i] || 0, 0]);
  ok(evs.some((e) => e.t === 'proj' && e.who === 0), 'QCF+L makes a projectile');
}
// --- simple input: S makes a flare too
{
  const m = toFight(fresh());
  const evs = run(m, 30, (i) => [i === 1 ? IN.S : 0, 0]);
  ok(evs.some((e) => e.t === 'proj' && e.who === 0), 'S makes a projectile');
}
// --- throw
{
  const m = toFight(fresh());
  m.state.f[0].x = -35 * CM; m.state.f[1].x = 35 * CM;
  const evs = run(m, 80, (i) => [i === 1 ? IN.THROW : 0, 0]);
  ok(evs.some((e) => e.t === 'grab'), 'throw grabs');
  ok(m.state.f[1].hp < m.state.f[1].maxHp, 'throw damages');
}
// --- super with meter
{
  const m = toFight(fresh('joe', 'joe', { meter: 'full' }));
  m.state.f[0].x = -50 * CM; m.state.f[1].x = 50 * CM;
  const evs = run(m, 200, (i) => [i === 1 ? IN.SUPER : 0, 0]);
  ok(evs.some((e) => e.t === 'super'), 'super flash');
  ok(evs.some((e) => e.t === 'cine'), 'super connects into its cinematic');
  ok(m.state.f[1].maxHp - m.state.f[1].hp > 200, 'super does big damage: ' + (m.state.f[1].maxHp - m.state.f[1].hp));
}
// --- KO ends the round and starts round 2
{
  const m = toFight(fresh());
  m.state.f[1].hp = 10;
  m.state.f[0].x = -40 * CM; m.state.f[1].x = 40 * CM;
  run(m, 600, (i) => [i === 1 ? IN.M : 0, 0]);
  ok(m.state.wins[0] === 1, 'P1 won round 1: ' + m.state.wins);
  ok(m.state.round === 2, 'round 2 started: ' + m.state.round + ' ' + m.state.phase);
}
// --- determinism and rollback
{
  const script = (i) => [[0, IN.RIGHT, IN.L, IN.DOWN | IN.M, IN.UP | IN.RIGHT, IN.H, IN.S][(i * 7 + (i >> 3)) % 7], [IN.LEFT, 0, IN.M, IN.DOWN, IN.LEFT | IN.H, IN.S, 0][(i * 5 + (i >> 4)) % 7]];
  const a = fresh(), b = fresh();
  run(a, 1500, script); run(b, 1500, script);
  ok(checksum(a.state) === checksum(b.state), 'two identical runs agree');
  const c = fresh();
  run(c, 700, script);
  const snap = structuredClone(c.state);
  run(c, 300, (i) => script(i + 700));
  const after = checksum(c.state);
  c.state = snap;
  run(c, 300, (i) => script(i + 700));
  ok(checksum(c.state) === after, 'restore + resimulate agrees (rollback safe)');
}

// --- bots finish matches: every fighter vs every fighter at two levels
if (!quick) {
  let matches = 0, frames = 0, totalHits = 0;
  for (const a of ORDER) for (const b of ORDER) for (const lv of [1, 3]) {
    const m = createMatch({ fighters: [a, b], seed: a + b + lv, skipIntro: true, mods: { rounds: 2 } });
    const bots = [new Bot(lv, 3), new Bot(lv, 9)];
    let n = 0;
    while (m.state.phase !== 'matchEnd' && n < 60 * 60 * 6) { step(m, [bots[0].think(m, 0), bots[1].think(m, 1)]); n++; }
    matches++; frames += n; totalHits += m.state.f[0].stats.hits + m.state.f[1].stats.hits;
    ok(m.state.phase === 'matchEnd', `bots finish ${a} vs ${b} L${lv} (${(n / 3600).toFixed(1)} min, phase ${m.state.phase}, hp ${m.state.f.map((f) => f.hp)})`);
  }
  console.log(`bot matches: ${matches}, avg ${(frames / matches / 3600).toFixed(2)} min, avg hits ${(totalHits / matches).toFixed(0)}`);
}

console.log(`${passes} passed, ${fails} failed`);
if (fails) process.exit(1);
