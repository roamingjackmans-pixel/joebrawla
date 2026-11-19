// The computer opponent: one AI with four difficulty profiles (docs/DESIGN.md §9). It reads the match like a
// player (with a reaction delay), and answers with raw input bits, so the simulation can't tell it apart from
// a person. Its randomness is its own seeded stream, never the match's.
import { IN, CM } from './core.js';
import { FIGHTERS } from './fighters/index.js';

export const LEVELS = [
  { name: 'Tenant', react: 28, block: 0.3, lowBlock: 0.2, aa: 0.1, punish: 0.1, confirm: 0.15, combo: 1, tech: 0, meter: 0, throwUse: 0.02, aggression: 0.35, jump: 0.012, mistakes: 0.25 },
  { name: 'Superintendent', react: 18, block: 0.55, lowBlock: 0.45, aa: 0.35, punish: 0.35, confirm: 0.5, combo: 2, tech: 0.2, meter: 0.4, throwUse: 0.05, aggression: 0.5, jump: 0.01, mistakes: 0.12 },
  { name: 'Management', react: 12, block: 0.8, lowBlock: 0.75, aa: 0.7, punish: 0.7, confirm: 0.8, combo: 3, tech: 0.5, meter: 0.8, throwUse: 0.08, aggression: 0.6, jump: 0.008, mistakes: 0.05 },
  { name: 'The Landlord', react: 8, block: 0.93, lowBlock: 0.92, aa: 0.92, punish: 0.92, confirm: 0.95, combo: 4, tech: 0.75, meter: 1, throwUse: 0.1, aggression: 0.68, jump: 0.006, mistakes: 0.01 },
];

const MOTION_STEPS = {
  '236': [2, 3, 6], '214': [2, 1, 4], '623': [6, 2, 3], '41236': [4, 1, 2, 3, 6], '22': [2, 5, 2],
  '236236': [2, 3, 6, 2, 3, 6], '214214': [2, 1, 4, 2, 1, 4],
};

function dirBits(n, face) {
  // numpad direction relative to facing -> raw bits
  const fwd = face > 0 ? IN.RIGHT : IN.LEFT, back = face > 0 ? IN.LEFT : IN.RIGHT;
  return ({ 1: IN.DOWN | back, 2: IN.DOWN, 3: IN.DOWN | fwd, 4: back, 5: 0, 6: fwd, 7: IN.UP | back, 8: IN.UP, 9: IN.UP | fwd })[n];
}

const reachOf = (mv) => (mv && mv.hits.length ? Math.max(...mv.hits.filter((h) => h.box).map((h) => h.box[0] + h.box[2]), 0) : 0);

/** what a fighter can do, read from its data once */
export function kitOf(id) {
  const d = FIGHTERS[id];
  const kit = { d, pokes: [], antiAir: null, reversal: null, proj: null, cmdGrab: null, ender: null, launcher: null, specials: d.specials || [] };
  const n = d.normals;
  for (const id2 of [n.stand.M, n.crouch.M, n.stand.H, n.crouch.L, n.stand.L, n.crouch.H]) {
    const mv = d.moves[id2]; if (mv) kit.pokes.push({ id: id2, reach: reachOf(mv), startup: mv.startup, low: mv.hits.some((h) => h.level === 'low'), crouch: id2.startsWith('cr') });
  }
  for (const s of kit.specials) {
    const mv = d.moves[`${s.id}_H`] || d.moves[`${s.id}_M`];
    if (!mv || s.air) continue;
    if (mv.proj.length && mv.proj[0].vx > 0 && !kit.proj) kit.proj = s;
    else if (mv.grab && !kit.cmdGrab) kit.cmdGrab = s;
    else if (mv.invuln && (mv.invuln.strike || mv.invuln.full) && mv.hits.length && !kit.reversal) kit.reversal = s;
    if (mv.hits.some((h) => h.effect === 'launch') && mv.startup <= 8 && !kit.antiAir) kit.antiAir = s;
    if (!kit.ender && mv.hits.length && !mv.grab && !mv.proj.length && !mv.counter) kit.ender = s;
  }
  if (!kit.antiAir) kit.antiAir = kit.reversal;
  if (!kit.ender) kit.ender = kit.proj || kit.antiAir;
  for (const c of n.command || []) { const mv = d.moves[c.id]; if (mv && mv.hits.some((h) => h.effect === 'launch')) kit.launcher = c; }
  kit.chain = [n.stand.L, n.stand.M, n.stand.H].filter((x) => d.moves[x]);
  kit.lowChain = [n.crouch.L, n.crouch.M].filter((x) => d.moves[x]);
  return kit;
}

export class Bot {
  constructor(level = 1, seed = 1) {
    this.p = LEVELS[Math.max(0, Math.min(3, level))];
    this.level = level;
    this.s = (seed * 2654435761) >>> 0 || 1;
    this.hist = [];        // perceived opponent snapshots (for reaction delay)
    this.plan = [];        // queued input frames
    this.kit = null; this.kitFor = null;
    this.cool = 0; this.mood = 0; this.walkT = 0; this.walkDir = 0;
  }
  r() { this.s ^= this.s << 13; this.s ^= this.s >>> 17; this.s ^= this.s << 5; return ((this.s >>> 0) % 10000) / 10000; }
  chance(p) { return this.r() < p; }

  /** returns the raw input bits for player i this frame */
  think(match, i) {
    const st = match.state, cfg = match.cfg;
    const me = st.f[i], op = st.f[1 - i];
    if (this.kitFor !== cfg.fighters[i]) { this.kit = kitOf(cfg.fighters[i]); this.kitFor = cfg.fighters[i]; this.opKit = kitOf(cfg.fighters[1 - i]); }
    // perceive the opponent late
    this.hist.push({ act: op.act, move: op.move, mf: op.mf, x: op.x, y: op.y, vy: op.vy, t: op.t, contact: op.contact });
    if (this.hist.length > 40) this.hist.shift();
    const seen = this.hist[Math.max(0, this.hist.length - 1 - this.p.react)];
    if (st.phase !== 'fight') { this.plan = []; return this.chance(0.02) ? IN.L : 0; }
    const face = me.face;
    const dist = Math.abs(op.x - me.x);
    // a plan in progress keeps going (combos, motions), unless we got hit
    if (this.plan.length) {
      if (me.act === 'hit' || me.act === 'chit' || me.act === 'air' || me.act === 'down' || me.act === 'thrown') this.plan = [];
      else return this.nextPlan(face);
    }
    // being thrown: tech
    if (me.act === 'thrown' && me.t <= 6 && this.chance(this.p.tech / 4)) return IN.L | IN.M;
    // our attack connected: confirm into more
    if (me.act === 'move' && me.contact === 1 && me.move && !this.confirmed) {
      this.confirmed = true;
      if (this.chance(this.p.confirm)) return this.continueCombo(me, op, cfg, face);
    }
    if (me.act !== 'move') this.confirmed = false;
    if (me.act === 'move' || me.act === 'prejump') return 0;
    // waking up / in stun: block
    const free = me.act === 'idle' || me.act === 'walk' || me.act === 'crouch' || me.act === 'land' || me.act === 'block' || me.act === 'cblock' || me.act === 'dashEnd' || me.act === 'wake';
    if (!free && me.act !== 'jump') return 0;

    const opMoveData = seen.move ? FIGHTERS[cfg.fighters[1 - i]].moves[seen.move] : null;
    const threat = seen.act === 'move' && opMoveData && seen.mf < opMoveData.startup + opMoveData.active && Math.abs(seen.x - me.x) < (reachOf(opMoveData) + 140 * CM);
    const projComing = st.proj.some((p) => p.owner === op.i && Math.abs(p.x - me.x) < 260 * CM && Math.sign(me.x - p.x) === Math.sign(p.vx || 1));
    const opAir = seen.y > 40 * CM && seen.act !== 'air' && seen.act !== 'ko';
    const opRecovering = seen.act === 'move' && opMoveData && seen.mf >= opMoveData.startup + opMoveData.active && !seen.contact;

    // anti-air
    if (opAir && dist < 260 * CM && seen.vy < 0 && this.kit.antiAir && this.chance(this.p.aa / 3)) {
      return this.special(this.kit.antiAir, 'H', face);
    }
    // block what's coming
    if ((threat || projComing) && me.act !== 'jump') {
      const low = opMoveData && opMoveData.hits.some((h) => h.level === 'low');
      const ovh = opMoveData && opMoveData.hits.some((h) => h.level === 'ovh');
      if (this.chance(this.p.block)) {
        const crouch = low ? this.chance(this.p.lowBlock / this.p.block) : ovh ? false : this.chance(0.45);
        // Breaker Reversal when blocking a lot, with meter
        if ((me.act === 'block' || me.act === 'cblock') && me.meter >= 1000 && this.chance(this.p.meter * 0.04)) return IN.BREAKER;
        return dirBits(crouch ? 1 : 4, face);
      }
    }
    if (me.act === 'block' || me.act === 'cblock') return dirBits(me.act === 'cblock' ? 1 : 4, face);
    // punish whiffs and unsafe moves
    if (opRecovering && dist < 170 * CM && this.chance(this.p.punish / 3)) return this.punish(me, op, cfg, face, dist);
    if (me.act === 'jump') {
      // air attack on the way down
      if (me.vy < 0 && dist < 150 * CM && this.chance(0.3)) return this.press(['H', 'M'][Math.floor(this.r() * 2)]);
      return 0;
    }
    if (this.cool > 0) { this.cool--; return this.walkInput(face); }
    return this.neutral(me, op, cfg, face, dist, opAir);
  }

  neutral(me, op, cfg, face, dist, opAir) {
    const p = this.p, k = this.kit;
    const pokeRange = Math.max(...k.pokes.map((x) => x.reach)) || 100 * CM;
    // supers when they would land (point blank, opponent recovering) or randomly at high level
    if (me.meter >= 1000 && dist < 140 * CM && this.chance(p.meter * 0.01)) return IN.SUPER;
    if (me.overtime && !me.otUsed && dist < 150 * CM && this.chance(p.meter * 0.01)) return IN.SUPER | IN.S;
    // throws up close
    if (dist < 90 * CM && this.chance(p.throwUse)) { this.cool = 6; return IN.THROW; }
    if (k.cmdGrab && dist < 110 * CM && this.chance(p.throwUse * 0.8)) return this.special(k.cmdGrab, 'L', face);
    // fireballs at range
    if (k.proj && dist > 280 * CM && this.chance(0.03 + p.aggression * 0.02)) return this.special(k.proj, this.chance(0.5) ? 'L' : 'H', face);
    // pokes in range
    const pokes = k.pokes.filter((x) => x.reach + 20 * CM >= dist - 30 * CM);
    if (pokes.length && dist < pokeRange + 40 * CM && this.chance(0.05 + p.aggression * 0.07)) {
      const poke = pokes[Math.floor(this.r() * pokes.length)];
      this.cool = 10;
      return this.pressMove(poke.id, face);
    }
    // jump in sometimes
    if (dist > 160 * CM && dist < 330 * CM && this.chance(p.jump)) { this.cool = 30; return dirBits(9, face); }
    // dash in when far
    if (dist > 330 * CM && this.chance(0.02 * p.aggression)) { this.plan = [dirBits(6, face), 0, dirBits(6, face), dirBits(6, face)]; return this.nextPlan(face); }
    // Breaker rush now and then
    if (me.meter >= 1000 && dist < 200 * CM && this.chance(p.meter * 0.004)) return IN.BREAKER;
    return this.walkInput(face, dist, pokeRange);
  }

  walkInput(face, dist = 200 * CM, pokeRange = 100 * CM) {
    if (this.walkT <= 0) {
      this.walkT = 10 + Math.floor(this.r() * 30);
      const want = pokeRange + 30 * CM;
      const r = this.r();
      if (dist > want + 60 * CM) this.walkDir = r < 0.25 + this.p.aggression * 0.6 ? 6 : r < 0.8 ? 5 : 4;
      else if (dist < want - 50 * CM) this.walkDir = r < 0.45 ? 4 : r < 0.7 ? 5 : 2;
      else this.walkDir = r < 0.35 ? 5 : r < 0.6 ? 4 : r < 0.8 ? 6 : 2;
    }
    this.walkT--;
    return dirBits(this.walkDir, face);
  }

  punish(me, op, cfg, face, dist) {
    const k = this.kit;
    if (me.meter >= 1000 && this.chance(this.p.meter * 0.5) && dist < 150 * CM) return IN.SUPER;
    const seq = this.comboSeq(dist);
    this.plan = seq;
    return this.nextPlan(face);
  }

  comboSeq(dist) {
    const k = this.kit, n = this.p.combo;
    const steps = [];
    const chain = dist < 70 * CM ? k.chain : k.chain.slice(1);
    for (let j = 0; j < Math.min(n, chain.length); j++) steps.push({ move: chain[j] });
    if (n >= 3 && k.ender) steps.push({ special: k.ender, str: n >= 4 ? 'H' : 'M' });
    const out = [];
    for (const s of steps) {
      if (s.move) { out.push(...this.btnFrames(s.move)); out.push(0, 0, 0, 0, 0, 0, 0, 0); }
      else out.push(...this.motionFrames(s.special.motion, s.str));
    }
    return out;
  }

  continueCombo(me, op, cfg, face) {
    const k = this.kit;
    const cur = me.move.replace(/_(L|M|H|EX)$/, '');
    const idx = k.chain.indexOf(me.move);
    const plan = [];
    if (idx >= 0 && idx + 1 < k.chain.length && idx + 1 < this.p.combo) plan.push(...this.btnFrames(k.chain[idx + 1]));
    else if (k.ender && this.p.combo >= 2 && FIGHTERS[cfg.fighters[me.i]].moves[me.move]?.cancel?.special) {
      if (me.meter >= 1000 && this.chance(this.p.meter * 0.3)) plan.push(IN.SUPER);
      else plan.push(...this.motionFrames(k.ender.motion, this.level >= 2 ? 'H' : 'M'));
    }
    if (!plan.length) return 0;
    void cur;
    this.plan = plan;
    return this.nextPlan(face);
  }

  btnFrames(id) {
    // a normal's id -> direction + button (relative directions resolved in nextPlan)
    const d = this.kit.d;
    const n = d.normals;
    let dir = 5, btn = 'L';
    for (const st of ['stand', 'crouch']) for (const b of ['L', 'M', 'H']) if (n[st][b] === id) { dir = st === 'crouch' ? 2 : 5; btn = b; }
    for (const c of n.command || []) if (c.id === id) { dir = c.dir; btn = c.btn; }
    return [{ dir, btn }];
  }
  pressMove(id, face) { this.plan = this.btnFrames(id); return this.nextPlan(face); }
  press(btn) { return IN[btn]; }

  motionFrames(motion, str = 'M') {
    const steps = MOTION_STEPS[motion] || [5];
    const out = steps.map((d) => ({ dir: d }));
    out[out.length - 1] = { dir: steps[steps.length - 1], btn: str };
    return out;
  }
  special(s, str, face) {
    if (!s) return 0;
    if (s.motion) { this.plan = this.motionFrames(s.motion, str); return this.nextPlan(face); }
    return IN.S;
  }

  nextPlan(face) {
    const x = this.plan.shift();
    if (x === undefined) return 0;
    if (typeof x === 'number') return x;
    return dirBits(x.dir ?? 5, face) | (x.btn ? IN[x.btn] : 0);
  }
}
