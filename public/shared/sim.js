// JoeBrawla simulation: one match, stepped 60 times a second. Deterministic and integer-only (see core.js).
// createMatch(setup) -> { cfg, state }; step(match, inputs[2]) advances state by one frame.
// The renderer reads state (and state.events, rebuilt every frame) but never writes to it.
import {
  IN, CM, WALL, MAX_GAP, START_X, GRAVITY, WALL_SPLAT_RANGE, clamp, sign, pct, rand, seedFrom,
} from './core.js';
import { newInputState, feed, refreshDir, motionAge, pressedWithin, pressAge, consume, simpleDir, BUFFER } from './commands.js';
import { FIGHTERS } from './fighters/index.js';
import { resolveModifiers } from './modifiers.js';

export const SCALE = [100, 100, 80, 70, 60, 50, 40, 30, 20, 10];
const JUST_BLOCK_METER = 80;
const INTRO_FRAMES = 170, READY_FRAMES = 96, KO_FRAMES = 150, ROUND_END_FRAMES = 170;

// ---------------------------------------------------------------- setup

/**
 * setup: { fighters: ['joe','gary'], colors: [0,1], seed: 'any string', mods: {...}, simple: [false,false],
 *          boss: [false,false] (boss versions: +HP, armour), stage, skipIntro }
 */
export function createMatch(setup) {
  const cfg = resolveModifiers(setup.mods || {});
  cfg.fighters = setup.fighters.slice();
  cfg.simple = (setup.simple || [false, false]).slice();
  cfg.boss = (setup.boss || [false, false]).slice();
  cfg.hpStart = (setup.hpStart || [null, null]).slice();
  cfg.skipIntro = !!setup.skipIntro;
  cfg.training = !!setup.training;
  const state = {
    frame: 0, rng: seedFrom(String(setup.seed ?? 'joebrawla')), phase: 'intro', pt: 0,
    round: 1, wins: [0, 0], timer: cfg.timer > 0 ? cfg.timer * 60 : -1, slow: 0, freeze: 0, freezeBy: -1,
    f: [null, null], proj: [], nextId: 1, events: [], cine: null, winner: -1, roundWinner: -1, timeStop: 0, timeStopBy: -1,
    lastRound: null, drops: 0,
  };
  for (let i = 0; i < 2; i++) state.f[i] = newFighter(cfg, i);
  resetRound(cfg, state, true);
  if (cfg.skipIntro) { state.phase = 'ready'; state.pt = 0; }
  return { cfg, state };
}

function fighterData(cfg, i) {
  const id = cfg.fighters[i];
  const d = FIGHTERS[id];
  if (!d) throw new Error('unknown fighter ' + id);
  return d;
}

function newFighter(cfg, i) {
  const d = fighterData(cfg, i);
  let maxHp = pct(d.hp, cfg.hpPct);
  if (cfg.boss[i]) maxHp = pct(maxHp, 140);
  return {
    i, ch: d.id, x: 0, y: 0, vx: 0, vy: 0, slide: 0, face: i === 0 ? 1 : -1,
    hp: maxHp, maxHp, meter: cfg.meterStart, act: 'intro', t: 0, move: null, mf: 0, stun: 0, hs: 0,
    contact: 0, hitMask: 0, landed: 0, airUsed: 0, crouch: false, jumpDir: 0,
    combo: 0, comboDmg: 0, juggle: 0, bounced: false, splatted: false, armor: 0, down: 0, knock: '',
    overtime: false, otUsed: false, tapF: 99, tapB: 99, lastDir: 5, inp: newInputState(),
    viaS: false, auto: -1, vars: {}, grab: null, jb: 0, flash: 0, invulnT: 0, hitByProj: false,
    stats: { hits: 0, best: 0, dmg: 0, blocks: 0, jbs: 0 }, rew: [], score: 0,
  };
}

function resetRound(cfg, state, first) {
  for (let i = 0; i < 2; i++) {
    const f = state.f[i];
    const d = fighterData(cfg, i);
    if (cfg.randomEachRound && !first) {
      const ids = Object.keys(FIGHTERS).filter((k) => !FIGHTERS[k].hidden);
      cfg.fighters[i] = ids[rand(state, ids.length)];
      f.ch = cfg.fighters[i];
    }
    const start = cfg.hpStart[i];
    Object.assign(f, {
      x: i === 0 ? -START_X : START_X, y: 0, vx: 0, vy: 0, slide: 0, face: i === 0 ? 1 : -1,
      hp: start != null && first ? start : f.maxHp, act: first ? 'intro' : 'idle', t: 0, move: null, mf: 0, stun: 0, hs: 0,
      contact: 0, hitMask: 0, crouch: false, combo: 0, comboDmg: 0, juggle: 0, bounced: false, splatted: false,
      armor: 0, down: 0, knock: '', overtime: false, grab: null, jb: 0, flash: 0, vars: initVars(d), rew: [],
    });
    if (cfg.meterMode === 'full' || cfg.meterMode === 'infinite') f.meter = 3000;
    if (cfg.meterMode === 'none') f.meter = 0;
    if (cfg.overtimeAlways) f.overtime = true;
  }
  state.proj = [];
  state.timer = cfg.timer > 0 ? cfg.timer * 60 : -1;
  state.cine = null; state.slow = 0; state.freeze = 0; state.timeStop = 0; state.roundWinner = -1;
}

function initVars(d) { return d.initVars ? { ...d.initVars } : {}; }

// ---------------------------------------------------------------- helpers

export const dataOf = (cfg, f) => FIGHTERS[cfg.fighters[f.i]];
const moveOf = (cfg, f) => (f.move ? dataOf(cfg, f).moves[f.move] : null);
const other = (state, f) => state.f[1 - f.i];
const ev = (state, e) => { e.fr = state.frame; state.events.push(e); };
const onGround = (f) => f.y <= 0;
const inWindow = (w, n) => w && n >= w[0] && n <= w[1];

function canAct(f) {
  return f.act === 'idle' || f.act === 'walk' || f.act === 'crouch' || (f.act === 'land' && f.t >= f.stun) || f.act === 'dashEnd';
}

function setAct(f, act) { f.act = act; f.t = 0; }

function startMove(cfg, state, f, id, opts = {}) {
  const d = dataOf(cfg, f);
  const mv = d.moves[id];
  if (!mv) return false;
  const cost = mv.cost || 0;
  if (cost && cfg.meterMode !== 'infinite') {
    if (f.meter < cost) return false;
    f.meter -= cost;
  } else if (cost && f.meter < cost && cfg.meterMode !== 'infinite') return false;
  f.act = 'move'; f.t = 0; f.move = id; f.mf = 0; f.contact = 0; f.hitMask = 0; f.landed = 0;
  f.armor = mv.armor ? mv.armor.hits : 0;
  f.viaS = !!opts.viaS;
  f.crouch = !!mv.crouching;
  if (mv.type === 'super' || mv.type === 'final' || mv.type === 'overtime') {
    state.freeze = mv.freeze ?? 36; state.freezeBy = f.i;
    ev(state, { t: 'super', who: f.i, move: id, kind: mv.type });
    if (mv.type === 'overtime') f.otUsed = true;
  }
  if (mv.type === 'breaker') { ev(state, { t: 'breaker', who: f.i }); }
  if (mv.type === 'ex') ev(state, { t: 'ex', who: f.i, move: id });
  if (!onGround(f) && !mv.air) f.vx = 0;
  if (mv.air) f.airUsed++;
  return true;
}

function spend(cfg, f, n) {
  if (cfg.meterMode === 'infinite') return true;
  if (f.meter < n) return false;
  f.meter -= n; return true;
}

function gainMeter(cfg, f, n) {
  if (cfg.meterMode === 'none') return;
  f.meter = clamp(f.meter + n, 0, 3000);
}

// ---------------------------------------------------------------- input -> intent

/** returns true if a move was started */
function tryCommands(cfg, state, f, opp) {
  const d = dataOf(cfg, f);
  const inp = f.inp;
  const mv = moveOf(cfg, f);
  const ground = onGround(f) && f.act !== 'jump' && f.act !== 'prejump';
  const free = canAct(f);
  const cancelOK = mv && f.act === 'move' && f.contact && f.mf <= mv.startup + mv.active - 1 + (mv.cancel?.slack ?? 6) && mv.cancel;
  const lateDur = f.act === 'move' && mv && f.mf <= 2; // upgrade window (EX / throw / breaker)
  const W = cancelOK || f.act === 'move' ? 10 : BUFFER; // longer buffer while waiting out hitstop / recovery
  const any = (n) => pressedWithin(inp, n, W);
  const atkPressed = ['L', 'M', 'H'].filter((b) => pressAge(inp, b) <= W);
  const did = (inp, motion) => motionAge(inp, motion) <= W;
  const supers = d.supers || {};

  if (!free && !cancelOK && !(f.act === 'jump' || f.act === 'move')) return false;
  if (state.phase !== 'fight' && !cfg.training) return false;

  // --- Overtime Art: Super + S together
  if ((free || (cancelOK && mv.cancel.super)) && f.overtime && !f.otUsed && supers.overtime && ground &&
      pressAge(inp, 'SUPER') <= 4 && pressAge(inp, 'S') <= 4) {
    consume(inp, 'SUPER'); consume(inp, 'S');
    return startMove(cfg, state, f, supers.overtime);
  }
  // --- Final Notice (3 bars): 214214+atk, or down + Super
  if ((free || (cancelOK && mv.cancel.super)) && ground && supers.final) {
    const viaBtn = any('SUPER') && (inp.dir === 1 || inp.dir === 2 || inp.dir === 3);
    const viaMotion = atkPressed.length && did(inp, '214214', f.face);
    if ((viaBtn || viaMotion) && (f.meter >= 3000 || cfg.meterMode === 'infinite')) {
      consume(inp, 'SUPER'); atkPressed.forEach((b) => consume(inp, b));
      return startMove(cfg, state, f, supers.final);
    }
  }
  // --- Super Art (1 bar): 236236+atk, or Super
  if ((free || (cancelOK && mv.cancel.super)) && ground && supers.art) {
    const viaMotion = atkPressed.length && did(inp, '236236', f.face);
    if ((any('SUPER') || viaMotion) && (f.meter >= 1000 || cfg.meterMode === 'infinite')) {
      consume(inp, 'SUPER'); atkPressed.forEach((b) => consume(inp, b));
      return startMove(cfg, state, f, supers.art);
    }
  }
  // --- Breaker (1 bar): Breaker button or M+H
  if (cfg.breaker && ground && (free || (cancelOK && mv.cancel.special)) && d.moves.breaker) {
    const mh = pressAge(inp, 'M') <= 2 && pressAge(inp, 'H') <= 2;
    if ((any('BREAKER') || mh) && (f.meter >= 1000 || cfg.meterMode === 'infinite')) {
      consume(inp, 'BREAKER'); consume(inp, 'M'); consume(inp, 'H');
      return startMove(cfg, state, f, 'breaker');
    }
  }
  // --- Throw: Throw button or L+M (ground, neutral only)
  if (cfg.throws && ground && free) {
    const lm = pressAge(inp, 'L') <= 2 && pressAge(inp, 'M') <= 2;
    if (any('THROW') || lm) {
      consume(inp, 'THROW'); consume(inp, 'L'); consume(inp, 'M');
      const back = inp.dir === 4 || inp.dir === 1 || inp.dir === 7;
      return startMove(cfg, state, f, back && d.moves.bthrow ? 'bthrow' : 'throw');
    }
  }
  // --- Specials
  const specialOK = free || (cancelOK && mv.cancel.special) || (f.act === 'jump');
  if (specialOK) {
    const r = trySpecial(cfg, state, f, d, ground, W);
    if (r) return true;
  }
  // --- Taunt
  if (free && ground && any('TAUNT') && d.moves.taunt) { consume(inp, 'TAUNT'); return startMove(cfg, state, f, 'taunt'); }

  // --- Normals (and chains)
  const btn = ['H', 'M', 'L'].find((b) => pressAge(inp, b) <= W);
  if (!btn) return false;
  let id = null;
  const n = d.normals;
  if (f.act === 'jump' || (!ground && f.act !== 'move')) {
    if (f.airUsed < 1 && f.act === 'jump' && f.t > 2) id = n.air[btn];
  } else {
    const crouching = inp.dir === 1 || inp.dir === 2 || inp.dir === 3;
    const cmd = (n.command || []).find((c) => c.btn === btn && c.dir === inp.dir);
    id = cmd ? cmd.id : crouching ? n.crouch[btn] : n.stand[btn];
    // Simple-scheme auto-combo: L repeatedly walks the chain
    if (cfg.simple[f.i] && btn === 'L' && d.autoCombo && mv && f.act === 'move' && f.contact) {
      const k = d.autoCombo.indexOf(f.move.replace(/_(L|M|H|EX)$/, ''));
      if (k >= 0 && k + 1 < d.autoCombo.length) {
        const next = d.autoCombo[k + 1];
        id = d.moves[next] ? next : next + '_M';
      }
    }
  }
  if (!id) return false;
  if (free || f.act === 'jump') { consume(inp, btn); return startMove(cfg, state, f, id); }
  if (cancelOK) {
    const into = mv.cancel.into || [];
    const special = /_(L|M|H|EX)$/.test(id) && mv.cancel.special;
    if (into.includes(id) || special) { consume(inp, btn); return startMove(cfg, state, f, id); }
  }
  return false;
}

function trySpecial(cfg, state, f, d, ground, W) {
  const inp = f.inp;
  const atk = ['L', 'M', 'H'].filter((b) => pressAge(inp, b) <= W);
  const air = !ground;
  for (const s of d.specials || []) {
    if (!!s.air !== air) continue;
    if (s.needs && !s.needs(f, state)) continue;
    let v = null, viaS = false;
    // classic: motion + attack (two attacks = EX)
    if (atk.length && s.motion && motionAge(inp, s.motion) <= W) {
      // two attack buttons pressed close together = EX
      const close = atk.filter((b) => Math.abs(pressAge(inp, b) - pressAge(inp, atk[0])) <= 2);
      v = close.length >= 2 ? 'EX' : atk.slice().sort((x, y) => pressAge(inp, x) - pressAge(inp, y))[0];
    }
    // simple: S + direction class (S + H = EX)
    if (!v && pressAge(inp, 'S') <= W && s.simple !== undefined && simpleDir(inp) === s.simple) {
      v = Math.abs(pressAge(inp, 'H') - pressAge(inp, 'S')) <= 2 ? 'EX' : 'M';
      viaS = true;
    }
    if (!v) continue;
    if (v === 'EX' && !(f.meter >= 500 || cfg.meterMode === 'infinite')) v = viaS ? 'M' : atk.includes('H') ? 'H' : atk[0];
    const id = `${s.id}_${v}`;
    const mv = d.moves[id];
    if (!mv) continue;
    if (mv.oneProj && state.proj.some((p) => p.owner === f.i && p.main) && !cfg.projectileParty) continue;
    if (v === 'EX' && !spend(cfg, f, 500)) continue;
    ['L', 'M', 'H', 'S'].forEach((b) => consume(inp, b));
    if (f.act === 'jump') { f.vx = f.vx; }
    return startMove(cfg, state, f, id, { viaS });
  }
  return false;
}

/** within the first two frames of a special or normal, a second button upgrades it (EX, throw, breaker) */
function tryUpgrade(cfg, state, f) {
  const d = dataOf(cfg, f);
  const mv = moveOf(cfg, f);
  if (!mv || f.mf > 2) return;
  const inp = f.inp;
  const atk = ['L', 'M', 'H'].filter((b) => pressAge(inp, b) <= 2);
  if (mv.strength && mv.strength !== 'EX' && atk.length >= 2 && !f.viaS) {
    const ex = d.moves[`${mv.base}_EX`];
    if (ex && spend(cfg, f, 500)) { f.move = ex.id; ev(state, { t: 'ex', who: f.i, move: ex.id }); atk.forEach((b) => consume(inp, b)); return; }
  }
  if (mv.type === 'normal' && onGround(f) && f.mf <= 2) {
    if (cfg.throws && pressAge(inp, 'L') <= 2 && pressAge(inp, 'M') <= 2) {
      const back = inp.dir === 4 || inp.dir === 1;
      f.move = back && d.moves.bthrow ? 'bthrow' : 'throw'; f.mf = 0; consume(inp, 'L'); consume(inp, 'M'); return;
    }
    if (cfg.breaker && pressAge(inp, 'M') <= 2 && pressAge(inp, 'H') <= 2 && d.moves.breaker && (f.meter >= 1000 || cfg.meterMode === 'infinite')) {
      startMove(cfg, state, f, 'breaker'); consume(inp, 'M'); consume(inp, 'H');
    }
  }
}

/** an attack is coming: the opponent is in the startup or active frames of a move nearby, or a projectile approaches */
function threatened(cfg, state, f, opp) {
  const mv = moveOf(cfg, opp);
  if (opp.act === 'move' && mv && opp.mf < mv.startup + mv.active && Math.abs(opp.x - f.x) < 300 * CM) return true;
  return state.proj.some((p) => p.owner === opp.i && !p.item && Math.abs(p.x - f.x) < 320 * CM && sign(f.x - p.x) === sign(p.vx || 1));
}

function movement(cfg, state, f, d, opp) {
  const inp = f.inp;
  const dir = inp.dir;
  // dash detection (66 / 44)
  const fwd = dir === 6, back = dir === 4;
  const wasFwd = f.lastDir === 6 || f.lastDir === 3 || f.lastDir === 9;
  const wasBack = f.lastDir === 4 || f.lastDir === 1 || f.lastDir === 7;
  if (fwd && !wasFwd) { if (f.tapF <= 12) { f.tapF = 99; setAct(f, 'dash'); f.vx = 0; return; } f.tapF = 0; }
  if (back && !wasBack) { if (f.tapB <= 12) { f.tapB = 99; setAct(f, 'bdash'); f.vx = 0; return; } f.tapB = 0; }
  if (dir >= 7) {
    setAct(f, 'prejump'); f.jumpDir = dir === 9 ? 1 : dir === 7 ? -1 : 0; f.vx = 0; return;
  }
  f.guard = (dir === 4 || dir === 1) && threatened(cfg, state, f, opp);
  if (dir <= 3) { if (f.act !== 'crouch') setAct(f, 'crouch'); f.crouch = true; f.vx = 0; return; }
  f.crouch = false;
  if (f.guard) { if (f.act !== 'idle') setAct(f, 'idle'); f.vx = 0; return; } // proximity guard: hold your ground
  if (dir === 6) { if (f.act !== 'walk') setAct(f, 'walk'); f.vx = d.walkF * f.face; return; }
  if (dir === 4) { if (f.act !== 'walk') setAct(f, 'walk'); f.vx = -d.walkB * f.face; return; }
  if (f.act !== 'idle') setAct(f, 'idle');
  f.vx = 0;
}

// ---------------------------------------------------------------- per-frame fighter update

function updateFighter(cfg, state, f) {
  const d = dataOf(cfg, f);
  const opp = other(state, f);
  f.t++;
  if (f.throwProt > 0) f.throwProt--;
  if (f.flash > 0) f.flash--;
  if (f.jb > 0) f.jb--;
  f.tapF = Math.min(f.tapF + 1, 99); f.tapB = Math.min(f.tapB + 1, 99);

  switch (f.act) {
    case 'intro': case 'win': case 'lose': case 'ko': case 'timeout': break;
    case 'idle': case 'walk': case 'crouch': case 'dashEnd':
      if (f.act === 'dashEnd') setAct(f, 'idle');
      if (!tryCommands(cfg, state, f, opp)) movement(cfg, state, f, d, opp);
      break;
    case 'land':
      if (f.t >= f.stun) { setAct(f, 'idle'); if (!tryCommands(cfg, state, f, opp)) movement(cfg, state, f, d, opp); }
      break;
    case 'prejump':
      if (f.t >= d.jump.pre) {
        setAct(f, 'jump');
        f.vy = pct(d.jump.vyU, cfg.gravityPct === 100 ? 100 : 100);
        f.vx = f.jumpDir * d.jump.vxU * f.face;
        f.airUsed = 0;
        ev(state, { t: 'jump', who: f.i });
      }
      break;
    case 'jump':
      tryCommands(cfg, state, f, opp);
      break;
    case 'dash': {
      const n = d.dashF.frames;
      f.vx = Math.trunc((d.dashF.distU * 2 * (n - f.t + 1)) / (n * (n + 1))) * f.face;
      if (f.t === 1) ev(state, { t: 'dash', who: f.i });
      if (f.t >= n) { setAct(f, 'dashEnd'); f.vx = 0; }
      break;
    }
    case 'bdash': {
      const n = d.dashB.frames;
      f.vx = -Math.trunc((d.dashB.distU * 2 * (n - f.t + 1)) / (n * (n + 1))) * f.face;
      if (f.t === 1) ev(state, { t: 'dash', who: f.i, back: true });
      if (f.t >= n) { setAct(f, 'dashEnd'); f.vx = 0; }
      break;
    }
    case 'move': advanceMove(cfg, state, f, d, opp); break;
    case 'block': case 'cblock':
      if (f.stun > 0) f.stun--;
      if (f.stun <= 0) { f.throwProt = 3; setAct(f, f.act === 'cblock' ? 'crouch' : 'idle'); }
      else if (cfg.breaker && d.moves.breakerRev && (pressAge(f.inp, 'BREAKER') <= 2 || (pressAge(f.inp, 'M') <= 2 && pressAge(f.inp, 'H') <= 2)) && (f.meter >= 1000 || cfg.meterMode === 'infinite')) {
        consume(f.inp, 'BREAKER'); consume(f.inp, 'M'); consume(f.inp, 'H');
        f.stun = 0; startMove(cfg, state, f, 'breakerRev'); ev(state, { t: 'breaker', who: f.i, reversal: true });
      }
      break;
    case 'hit': case 'chit':
      if (f.stun > 0) f.stun--;
      if (f.stun <= 0) { f.throwProt = 3; f.combo = 0; f.comboDmg = 0; f.bounced = false; f.splatted = false; setAct(f, f.act === 'chit' ? 'crouch' : 'idle'); }
      break;
    case 'crumple':
      if (f.t >= 50) { setAct(f, 'down'); f.down = 40; f.knock = 'crumple'; }
      break;
    case 'splat':
      if (f.t >= 38) { setAct(f, 'air'); f.vy = 0; f.vx = -f.face * cm4(); f.knock = 'kd'; }
      break;
    case 'air': break; // physics handles landing
    case 'down':
      if (f.t >= f.down) { setAct(f, 'wake'); }
      break;
    case 'wake':
      if (f.t >= 18) { f.combo = 0; f.comboDmg = 0; f.juggle = 0; f.bounced = false; f.splatted = false; setAct(f, 'idle'); f.invulnT = 0; }
      break;
    case 'thrown': case 'throwing': case 'cine': case 'cined': break; // driven by the grab/cine logic
    case 'tech':
      if (f.t >= 18) setAct(f, 'idle');
      break;
  }
  if (onGround(f) && (f.act === 'idle' || f.act === 'walk' || f.act === 'crouch' || f.act === 'land' || f.act === 'dashEnd')) faceOpponent(f, opp);
  f.lastDir = f.inp.dir;
}
const cm4 = () => 4 * CM;

function faceOpponent(f, opp) {
  const want = opp.x >= f.x ? 1 : -1;
  if (opp.x !== f.x && want !== f.face) { f.face = want; refreshDir(f.inp, f.face); }
}

function advanceMove(cfg, state, f, d, opp) {
  tryUpgrade(cfg, state, f);
  const mv = moveOf(cfg, f);
  f.mf++;
  // cancels (chains, specials, supers) are checked before the frame runs out
  if (f.mf > 1 && f.contact && mv.cancel && tryCommands(cfg, state, f, opp)) { return; }
  // velocities
  for (const [fr, vx, vy] of mv.vel) {
    if (fr === f.mf) {
      if (vx != null) f.vx = vx * f.face;
      if (vy != null) { f.vy = vy; }
    }
  }
  if (onGround(f) && !mv.vel.some(([fr]) => fr <= f.mf) && !mv.air) f.vx = 0;
  // projectiles
  for (const p of mv.proj) if (p.at === f.mf) spawnProj(cfg, state, f, p, mv);
  if (mv.fx) for (const fx of [].concat(mv.fx)) if (fx.at === f.mf) runFx(cfg, state, f, opp, fx, mv);
  if (f.mf >= mv.total) endMove(cfg, state, f, mv);
}

function endMove(cfg, state, f, mv) {
  f.move = null; f.mf = 0; f.armor = 0; f.viaS = false;
  if (!onGround(f)) { setAct(f, mv.air ? 'jump' : 'air'); if (!mv.air) { f.knock = 'land'; } return; }
  f.crouch = mv.crouching || false;
  setAct(f, f.crouch ? 'crouch' : 'idle');
}

// ---------------------------------------------------------------- special effects of moves

function runFx(cfg, state, f, opp, fx, mv) {
  switch (fx.kind) {
    case 'heal': f.hp = Math.min(f.maxHp, f.hp + pct(f.maxHp, fx.pct)); ev(state, { t: 'heal', who: f.i }); break;
    case 'meter': gainMeter(cfg, f, fx.n); break;
    case 'teleport': {
      let x = f.x;
      if (fx.to === 'behind') x = opp.x + opp.face * Math.round((fx.dist || 80) * CM);
      else if (fx.to === 'front') x = opp.x - opp.face * Math.round((fx.dist || 90) * CM);
      else if (fx.to === 'rewind') { const r = f.rew; x = r.length ? r[0] : f.x; }
      else if (fx.to === 'forward') x = f.x + f.face * Math.round((fx.dist || 200) * CM);
      f.x = clamp(x, -WALL + dataOf(cfg, f).width / 2, WALL - dataOf(cfg, f).width / 2);
      f.y = 0; f.vy = 0;
      ev(state, { t: 'teleport', who: f.i });
      if (fx.face !== false) { const w = opp.x >= f.x ? 1 : -1; if (w !== f.face) { f.face = w; refreshDir(f.inp, f.face); } }
      break;
    }
    case 'setvar': f.vars[fx.name] = fx.value; break;
    case 'addvar': f.vars[fx.name] = clamp((f.vars[fx.name] || 0) + fx.value, fx.min ?? -99, fx.max ?? 99); break;
    case 'timestop': state.timeStop = fx.frames; state.timeStopBy = f.i; ev(state, { t: 'timestop', who: f.i }); break;
    case 'stealMeter': { const n = Math.min(opp.meter, fx.n); opp.meter -= n; gainMeter(cfg, f, n); break; }
  }
}

// ---------------------------------------------------------------- projectiles

function spawnProj(cfg, state, f, p, mv) {
  const opp = other(state, f);
  let x = f.x + f.face * p.x;
  if (p.place === 'opp') x = opp.x + (p.offset ? f.face * Math.round(p.offset * CM) : 0);
  if (p.place === 'dist') x = f.x + f.face * Math.round(p.dist * CM);
  let kind = p.kind;
  if (p.random) { const r = p.random[rand(state, p.random.length)]; kind = r; }
  const variant = p.variants && kind ? p.variants[kind] : null;
  const spec = variant ? { ...p, ...variant, hit: { ...p.hit, ...(variant.hit || {}) } } : p;
  state.proj.push({
    id: state.nextId++, owner: f.i, kind: kind || spec.kind || 'bolt', x, y: spec.y, vx: spec.vx * f.face, vy: spec.vy,
    face: f.face, box: spec.box, life: spec.life, hits: spec.hits, every: spec.every, cool: spec.delay || 0, t: 0,
    hit: spec.hit, power: spec.power, gravity: spec.gravity || 0, main: !!mv.oneProj, simple: f.viaS,
    trap: spec.trap || null, wall: spec.wall || 0, hop: spec.hop || null, from: mv.id, armed: !spec.trap,
    ground: !!spec.ground, reflect: false,
  });
  ev(state, { t: 'proj', who: f.i, kind: kind || spec.kind });
}

function updateProjectiles(cfg, state) {
  const keep = [];
  for (const p of state.proj) {
    p.t++;
    if (state.timeStop > 0 && p.owner !== state.timeStopBy) { keep.push(p); continue; }
    if (p.cool > 0) p.cool--;
    if (p.trap) {
      const opp = state.f[1 - p.owner];
      if (!p.armed && p.t >= p.trap.arm) p.armed = true;
      if (p.armed && !p.triggered && Math.abs(opp.x - p.x) <= p.trap.range * CM && opp.y < 120 * CM) {
        p.triggered = true; p.cool = p.trap.delay || 0; p.vx = p.trap.vx ? sign(opp.x - p.x) * Math.round(p.trap.vx * CM) : 0;
        ev(state, { t: 'trap', who: p.owner, kind: p.kind });
      }
    }
    if (p.hop && p.t > (p.hop.delay || 0)) {
      if (p.y <= 0 && p.vy <= 0) { p.vy = Math.round(p.hop.vy * CM); p.vx = Math.round(p.hop.vx * CM) * sign(state.f[1 - p.owner].x - p.x || 1); }
    }
    if (!p.trap || p.triggered) {
      p.x += p.vx; p.y += p.vy;
      if (p.gravity) p.vy -= p.gravity;
      if ((p.ground || p.hop) && p.y < 0) { p.y = 0; p.vy = 0; if (p.hop) p.vx = 0; }
    }
    p.life--;
    if (p.life > 0 && p.hits > 0 && Math.abs(p.x) < WALL + 200 * CM && p.y > -50 * CM) keep.push(p);
    else ev(state, { t: 'projEnd', id: p.id, kind: p.kind, x: p.x, y: p.y });
  }
  state.proj = keep;
  // projectile vs projectile
  for (let a = 0; a < state.proj.length; a++) for (let b = a + 1; b < state.proj.length; b++) {
    const p = state.proj[a], q = state.proj[b];
    if (p.owner === q.owner || p.hits <= 0 || q.hits <= 0 || p.trap || q.trap) continue;
    if (overlap(projBox(p), projBox(q))) {
      const pp = p.power, qp = q.power;
      p.power -= qp; q.power -= pp;
      if (p.power <= 0) p.hits = 0; if (q.power <= 0) q.hits = 0;
      ev(state, { t: 'clash', x: (p.x + q.x) >> 1, y: (p.y + q.y) >> 1 });
    }
  }
  state.proj = state.proj.filter((p) => p.hits > 0);
}

function projBox(p) { return worldBox(p.x, p.y, p.face, p.box); }

// ---------------------------------------------------------------- boxes

function worldBox(x, y, face, b) {
  const x0 = face > 0 ? x + b[0] : x - b[0] - b[2];
  return [x0, y + b[1], x0 + b[2], y + b[1] + b[3]];
}
function overlap(a, b) { return a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3]; }

export function hurtboxes(cfg, f) {
  const d = dataOf(cfg, f);
  const w = d.width, h = d.height;
  if (f.act === 'down' || f.act === 'wake' && f.t < 14 || f.act === 'ko' || f.act === 'thrown' || f.act === 'cined' || f.act === 'intro' || f.act === 'win' || f.act === 'lose') return [];
  const boxes = [];
  const crouching = f.crouch || f.act === 'crouch' || f.act === 'cblock' || f.act === 'chit';
  if (f.act === 'air' || f.act === 'jump' || (f.act === 'move' && !onGround(f))) {
    boxes.push(worldBox(f.x, f.y, f.face, [-w / 2 - 400, 15 * CM, w + 800, h - 45 * CM]));
  } else if (crouching) {
    boxes.push(worldBox(f.x, f.y, f.face, [-w / 2 - 300, 0, w + 600, d.crouchHeight]));
  } else {
    boxes.push(worldBox(f.x, f.y, f.face, [-w / 2, 0, w, h]));
  }
  const mv = moveOf(cfg, f);
  if (mv) for (const hb of mv.hurt) if (inWindow(hb.frames, f.mf)) boxes.push(worldBox(f.x, f.y, f.face, hb.box));
  return boxes;
}

function invulnTo(cfg, f, kind) {
  if (f.act === 'bdash' && f.t <= dataOf(cfg, f).dashB.invuln && kind !== 'throw') return true;
  const mv = moveOf(cfg, f);
  if (!mv || !mv.invuln) return false;
  const w = mv.invuln[kind] || mv.invuln.full;
  return inWindow(w, f.mf) || inWindow(mv.invuln.full, f.mf);
}

// ---------------------------------------------------------------- hits

function canBlock(f) {
  return onGround(f) && (f.act === 'idle' || f.act === 'walk' || f.act === 'crouch' || f.act === 'block' || f.act === 'cblock' || f.act === 'dashEnd' || (f.act === 'land' && f.t >= f.stun));
}

function holdingAway(def, atkX) {
  const h = def.inp.held;
  return atkX >= def.x ? (h & IN.LEFT) && !(h & IN.RIGHT) : (h & IN.RIGHT) && !(h & IN.LEFT);
}

/**
 * Apply hit `h` from attacker `a` (fighter or null for an ownerless hazard) to defender `def`.
 * src: { proj, x, y } — hit point for effects. Returns 'hit' | 'block' | 'armor' | 'counter' | 'none'.
 */
function applyHit(cfg, state, a, def, h, mv, src) {
  const dd = dataOf(cfg, def);
  const atkX = src.proj ? src.px : a.x;
  // counter stances
  const dmv = moveOf(cfg, def);
  if (dmv && dmv.counter && inWindow(dmv.counter.frames, def.mf) && !src.proj && a) {
    ev(state, { t: 'counterStance', who: def.i, x: src.x, y: src.y });
    a.hs = 14; def.hs = 14;
    startGrab(cfg, state, def, a, dataOf(cfg, def).moves[dmv.counter.into], true);
    return 'counter';
  }
  if (dmv && dmv.reflect && src.proj && inWindow(dmv.reflect, def.mf)) {
    const p = src.proj; p.owner = def.i; p.vx = -p.vx; p.face = -p.face; p.reflect = true; p.life = 120;
    ev(state, { t: 'reflect', who: def.i, x: p.x, y: p.y });
    return 'none';
  }
  // blocking
  const away = holdingAway(def, atkX);
  const down = def.inp.dir === 1 || def.inp.dir === 2 || def.inp.dir === 3 || (def.inp.held & IN.DOWN);
  let blocked = false;
  if (h.level !== 'unbl' && canBlock(def) && away && !cfg.noBlocking) {
    if (h.level === 'low') blocked = !!down;
    else if (h.level === 'ovh') blocked = !down;
    else blocked = true;
  } else if (h.level !== 'unbl' && (def.act === 'block' || def.act === 'cblock') && away && !cfg.noBlocking) {
    blocked = h.level === 'low' ? !!down : h.level === 'ovh' ? !down : true;
  }
  const dirAway = atkX >= def.x ? -1 : 1; // direction the defender gets pushed
  if (blocked) {
    const just = def.inp.backAge <= cfg.justBlock;
    const chip = cfg.chipKO || def.hp - h.chip > 0 ? (just ? 0 : pct(h.chip, cfg.dmgPct)) : 0;
    def.hp = Math.max(cfg.chipKO ? 0 : 1, def.hp - chip);
    if (def.hp <= 0) return koHit(cfg, state, a, def, h, src, chip);
    def.stun = Math.max(1, h.bstun - (just ? 4 : 0));
    setAct(def, down ? 'cblock' : 'block'); def.crouch = !!down;
    pushBack(cfg, state, a, def, h.push, dirAway, src);
    def.hs = h.hitstop; if (a && !src.proj) a.hs = h.hitstop;
    if (a) gainMeter(cfg, a, Math.trunc(h.meter / 2));
    gainMeter(cfg, def, Math.trunc(h.meter / 4) + (just ? JUST_BLOCK_METER : 0));
    def.stats.blocks++;
    if (just) { def.jb = 20; def.stats.jbs++; }
    ev(state, { t: 'block', who: def.i, by: a ? a.i : -1, x: src.x, y: src.y, str: h.spark, just, chip });
    return 'block';
  }
  // armour
  if (def.armor > 0 && dmv && dmv.armor && inWindow(dmv.armor.frames, def.mf) && h.level !== 'unbl') {
    def.armor--;
    const dmg = pct(pct(h.dmg, 50), cfg.dmgPct);
    def.hp = Math.max(1, def.hp - dmg);
    def.hs = h.hitstop; if (a && !src.proj) a.hs = h.hitstop;
    ev(state, { t: 'armor', who: def.i, x: src.x, y: src.y, str: h.spark });
    return 'armor';
  }
  // a clean hit
  const fresh = !(def.act === 'hit' || def.act === 'chit' || def.act === 'air' || def.act === 'crumple' || def.act === 'splat');
  if (fresh) { def.combo = 0; def.comboDmg = 0; def.juggle = 6; def.bounced = false; def.splatted = false; }
  if (def.act === 'air' && def.juggle <= 0 && !cfg.infiniteJuggle) return 'none';
  let counter = 0;
  if (dmv && def.act === 'move') {
    if (def.mf < dmv.startup) counter = 1;
    else if (def.mf >= dmv.startup + dmv.active) counter = 2;
  }
  const isSuper = mv && (mv.type === 'super' || mv.type === 'final' || mv.type === 'overtime');
  let scale = SCALE[Math.min(def.combo, SCALE.length - 1)];
  if (isSuper) scale = Math.max(scale, 50);
  let dmg = pct(h.dmg, scale);
  if (counter) dmg = pct(dmg, 125);
  if (a && a.overtime) dmg = pct(dmg, 110);
  if (a && src.simple && cfg.simplePenalty) dmg = pct(dmg, 85);
  dmg = Math.max(1, pct(dmg, cfg.dmgPct));
  if (cfg.oneHitKO) dmg = def.hp;
  def.hp -= dmg;
  def.combo++; def.comboDmg += dmg;
  if (a) {
    a.stats.hits++; a.stats.dmg += dmg; if (def.combo > a.stats.best) a.stats.best = def.combo;
    gainMeter(cfg, a, h.meter);
    if (cfg.vampire) a.hp = Math.min(a.maxHp, a.hp + pct(dmg, 30));
  }
  gainMeter(cfg, def, Math.trunc(h.meter / 2));
  if (!def.overtime && def.hp > 0 && def.hp * 4 <= def.maxHp) { def.overtime = true; ev(state, { t: 'overtime', who: def.i }); }
  if (def.act === 'move') { def.move = null; def.mf = 0; }
  ev(state, { t: 'hit', who: def.i, by: a ? a.i : -1, x: src.x, y: src.y, str: h.spark, sfx: h.sfx, dmg, counter, combo: def.combo, eff: h.effect, super: isSuper });
  if (def.hp <= 0) { def.hp = 0; return koHit(cfg, state, a, def, h, src, dmg); }

  def.hs = h.hitstop + (counter ? 2 : 0); if (a && !src.proj) a.hs = h.hitstop + (counter ? 2 : 0);
  const decay = Math.min(def.combo - 1, 8);
  const airborne = !onGround(def) || def.act === 'air';
  let eff = h.effect;
  if (cfg.noKnockdown && (eff === 'kd' || eff === 'hkd')) eff = 'normal';
  if (eff === 'crumple' && h.wallSplat) {
    const nearWall = dirAway > 0 ? WALL - def.x < WALL_SPLAT_RANGE : def.x + WALL < WALL_SPLAT_RANGE;
    if (nearWall && !def.splatted) eff = 'splat';
  }
  if (eff === 'splat') {
    const nearWall = dirAway > 0 ? WALL - def.x < WALL_SPLAT_RANGE : def.x + WALL < WALL_SPLAT_RANGE;
    eff = nearWall && (!def.splatted || cfg.bouncyWalls) ? 'splat' : 'kd';
  }
  if (eff === 'bounce' && def.bounced && !cfg.infiniteJuggle) eff = 'kd';
  if (airborne && eff === 'normal') eff = 'juggle';
  if (airborne && eff !== 'splat' && eff !== 'bounce') def.juggle -= h.juggle;

  switch (eff) {
    case 'normal': {
      const crouching = def.crouch || def.act === 'crouch' || def.act === 'cblock' || def.act === 'chit';
      setAct(def, crouching ? 'chit' : 'hit');
      def.stun = Math.max(6, h.stun - decay + (counter === 1 ? 3 : counter === 2 ? 6 : 0));
      pushBack(cfg, state, a, def, h.push, dirAway, src);
      break;
    }
    case 'crumple':
      setAct(def, 'crumple'); def.vx = 0; def.slide = 0; def.juggle = 4; break;
    case 'splat':
      setAct(def, 'splat'); def.splatted = true; def.vx = 0; def.vy = 0; def.slide = 0;
      def.x = dirAway > 0 ? WALL - dd.width / 2 : -WALL + dd.width / 2; def.y = Math.max(def.y, 80 * CM);
      def.face = -dirAway; def.juggle = Math.max(def.juggle, 3);
      ev(state, { t: 'splat', who: def.i, x: def.x, y: def.y });
      break;
    case 'bounce':
      setAct(def, 'air'); def.bounced = true; def.vy = 9 * CM; def.vx = dirAway * 1 * CM; def.knock = 'kd'; def.juggle = Math.max(def.juggle, 3);
      ev(state, { t: 'bounce', who: def.i, x: def.x });
      break;
    case 'launch': {
      const [lx, ly] = h.launch || [2 * CM, 12 * CM];
      setAct(def, 'air'); def.vx = dirAway * lx; def.vy = ly; def.knock = 'kd';
      if (fresh) def.juggle = 6 - h.juggle;
      break;
    }
    case 'juggle': {
      const [lx, ly] = h.launch || [1.6 * CM | 0, 7 * CM];
      setAct(def, 'air'); def.vx = dirAway * lx; def.vy = Math.max(ly, 4 * CM); def.knock = 'kd';
      break;
    }
    case 'kd': case 'hkd': default: {
      const [lx, ly] = h.launch || [3 * CM, 6 * CM];
      setAct(def, 'air'); def.vx = dirAway * lx; def.vy = ly; def.knock = eff === 'hkd' ? 'hkd' : 'kd';
      break;
    }
  }
  if (counter) ev(state, { t: counter === 1 ? 'counterHit' : 'punish', who: def.i, by: a ? a.i : -1 });
  return 'hit';
}

function koHit(cfg, state, a, def, h, src, dmg) {
  def.hp = 0;
  const dirAway = (src.proj ? src.px : a ? a.x : 0) >= def.x ? -1 : 1;
  setAct(def, 'ko'); def.vx = dirAway * 3 * CM; def.vy = 8 * CM; def.knock = 'ko';
  def.hs = 20; if (a && !src.proj) a.hs = 20;
  ev(state, { t: 'ko', who: def.i, by: a ? a.i : -1, x: src.x, y: src.y });
  return 'hit';
}

function pushBack(cfg, state, a, def, push, dirAway, src) {
  const dd = dataOf(cfg, def);
  const atWall = dirAway > 0 ? def.x >= WALL - dd.width / 2 - 20 * CM : def.x <= -WALL + dd.width / 2 + 20 * CM;
  if (atWall && a && !src.proj) a.slide = -dirAway * Math.trunc(push / 5);
  else def.slide = dirAway * Math.trunc(push / 5);
}

// ---------------------------------------------------------------- grabs and cinematics

function startGrab(cfg, state, a, def, mv, untechable) {
  if (!mv) return;
  a.act = 'throwing'; a.t = 0; a.move = mv.id; a.mf = 0;
  def.act = 'thrown'; def.t = 0; def.move = null; def.vx = 0; def.vy = 0; def.y = 0; def.slide = 0;
  a.grab = { move: mv.id, techable: !untechable && mv.grab && mv.grab.techable !== false, by: a.i };
  def.grab = { by: a.i, move: mv.id };
  ev(state, { t: 'grab', who: a.i, def: def.i, move: mv.id });
}

function updateGrab(cfg, state, a, def) {
  const mv = dataOf(cfg, a).moves[a.grab.move];
  const g = mv.grab || {};
  a.mf++;
  const len = g.len || 40;
  // throw tech window
  if (a.grab.techable && a.mf <= 8 && cfg.throws &&
      ((pressAge(def.inp, 'L') <= 3 && pressAge(def.inp, 'M') <= 3) || pressAge(def.inp, 'THROW') <= 3)) {
    consume(def.inp, 'THROW'); consume(def.inp, 'L'); consume(def.inp, 'M');
    setAct(a, 'tech'); setAct(def, 'tech'); a.move = null; a.grab = null; def.grab = null;
    a.slide = -a.face * 2 * CM; def.slide = a.face * 2 * CM;
    ev(state, { t: 'tech', x: (a.x + def.x) >> 1 });
    return;
  }
  // hold the victim in place
  const hold = g.hold ? Math.round(g.hold * CM) : 70 * CM;
  def.x = a.x + a.face * hold; def.face = -a.face;
  if (mv.hits) for (let k = 0; k < mv.hits.length; k++) {
    const h = mv.hits[k];
    const at = h.frames ? h.frames[0] : g.dmgAt || len - 8;
    if (a.mf === at) {
      const dmg = Math.max(1, pct(pct(h.dmg, SCALE[Math.min(def.combo, 9)]), cfg.dmgPct));
      def.hp -= dmg; def.combo++; def.comboDmg += dmg; a.stats.dmg += dmg; a.stats.hits++;
      gainMeter(cfg, a, h.meter); gainMeter(cfg, def, Math.trunc(h.meter / 2));
      if (g.steal) { const n = Math.min(def.meter, g.steal); def.meter -= n; gainMeter(cfg, a, n); }
      a.hs = h.hitstop; def.hs = h.hitstop;
      ev(state, { t: 'hit', who: def.i, by: a.i, x: def.x, y: 110 * CM, str: h.spark, sfx: h.sfx, dmg, counter: 0, combo: def.combo, eff: 'throw' });
      if (def.hp <= 0) { def.hp = 0; }
    }
  }
  if (a.mf >= len) {
    a.grab = null; def.grab = null; a.move = null;
    if (g.switchSide) { const t = a.x; a.x = def.x; def.x = t; a.face = -a.face; refreshDir(a.inp, a.face); }
    setAct(a, 'idle');
    const dirAway = def.x >= a.x ? 1 : -1;
    if (def.hp <= 0) { setAct(def, 'ko'); def.vx = dirAway * 3 * CM; def.vy = 6 * CM; ev(state, { t: 'ko', who: def.i, by: a.i, x: def.x, y: 100 * CM }); }
    else { setAct(def, 'air'); def.vx = dirAway * Math.round((g.toss || [3, 5])[0] * CM); def.vy = Math.round((g.toss || [3, 5])[1] * CM); def.knock = g.hkd ? 'hkd' : 'kd'; }
  }
}

function startCine(cfg, state, a, def, mv) {
  state.cine = { by: a.i, move: mv.id, t: 0, len: mv.cine.len };
  a.act = 'cine'; a.t = 0; def.act = 'cined'; def.t = 0; def.vx = 0; def.vy = 0; def.slide = 0; a.vx = 0; a.vy = 0;
  def.face = -a.face;
  ev(state, { t: 'cine', who: a.i, move: mv.id });
}

function updateCine(cfg, state) {
  const c = state.cine;
  const a = state.f[c.by], def = state.f[1 - c.by];
  const mv = dataOf(cfg, a).moves[c.move];
  c.t++;
  a.y = 0; def.y = 0;
  const hold = Math.round((mv.cine.hold || 90) * CM);
  def.x = clamp(a.x + a.face * hold, -WALL + 30 * CM, WALL - 30 * CM);
  for (const [fr, dmg] of mv.cine.hits) {
    if (fr === c.t) {
      let d = pct(pct(dmg, Math.max(50, SCALE[Math.min(def.combo, 9)])), cfg.dmgPct);
      if (a.overtime) d = pct(d, 110);
      if (cfg.oneHitKO) d = def.hp;
      def.hp = Math.max(0, def.hp - d); def.combo++; def.comboDmg += d; a.stats.dmg += d; a.stats.hits++;
      ev(state, { t: 'hit', who: def.i, by: a.i, x: def.x, y: 110 * CM, str: 'S', sfx: 'H', dmg: d, counter: 0, combo: def.combo, eff: 'cine', super: true });
    }
  }
  if (c.t >= c.len) {
    state.cine = null;
    setAct(a, 'idle'); a.move = null;
    const dirAway = def.x >= a.x ? 1 : -1;
    if (def.hp <= 0) { setAct(def, 'ko'); def.vx = dirAway * 4 * CM; def.vy = 9 * CM; def.knock = 'ko'; ev(state, { t: 'ko', who: def.i, by: a.i, x: def.x, y: 100 * CM }); }
    else { setAct(def, 'air'); def.vx = dirAway * 4 * CM; def.vy = 9 * CM; def.knock = 'hkd'; }
  }
}

// ---------------------------------------------------------------- collision of attacks

function checkHits(cfg, state) {
  const results = [];
  for (const a of state.f) {
    if (a.act !== 'move' || a.hs > 0) continue;
    const mv = moveOf(cfg, a);
    const def = other(state, a);
    // grabs (throws and command grabs)
    if (mv.grab && f_inActive(a, mv) && !a.grabTried) {
      const range = mv.grab.range;
      const gap = Math.abs(def.x - a.x);
      const throwable = onGround(def) && !['hit', 'chit', 'block', 'cblock', 'down', 'wake', 'air', 'thrown', 'throwing', 'ko', 'cine', 'cined', 'splat', 'crumple', 'tech', 'prejump'].includes(def.act) && !invulnTo(cfg, def, 'throw') && !(mv.grab.air === false && !onGround(def));
      const recentStun = def.throwProt > 0;
      if (gap <= range + dataOf(cfg, def).width / 2 && throwable && !recentStun) {
        results.push({ grab: true, a, def, mv });
        continue;
      }
    }
    for (let k = 0; k < mv.hits.length; k++) {
      const h = mv.hits[k];
      if (!inWindow(h.frames, a.mf) || !h.box) continue;
      if (a.hitMask & (1 << k)) continue;
      if (invulnTo(cfg, def, 'strike')) continue;
      if (h.otg === false && def.act === 'down') continue;
      const hb = worldBox(a.x, a.y, a.face, h.box);
      const hurts = hurtboxes(cfg, def);
      if (!hurts.some((b) => overlap(hb, b))) continue;
      const cx = (Math.max(hb[0], hurts[0][0]) + Math.min(hb[2], hurts[0][2])) >> 1;
      const cy = clamp((hb[1] + hb[3]) >> 1, def.y + 10 * CM, def.y + 175 * CM);
      results.push({ a, def, h, k, mv, x: cx, y: cy });
      break;
    }
  }
  // apply simultaneously (trades)
  for (const r of results) {
    if (r.grab) {
      if (results.some((o) => o.grab && o.a === r.def)) { // throw vs throw: tech
        setAct(r.a, 'tech'); setAct(r.def, 'tech'); r.a.move = null; r.def.move = null;
        ev(state, { t: 'tech', x: (r.a.x + r.def.x) >> 1 });
        continue;
      }
      if (r.mv.cine) { r.a.contact = 1; startCine(cfg, state, r.a, r.def, r.mv); continue; }
      startGrab(cfg, state, r.a, r.def, r.mv, r.mv.grab.techable === false);
      continue;
    }
    r.a.hitMask |= 1 << r.k;
    const res = applyHit(cfg, state, r.a, r.def, r.h, r.mv, { x: r.x, y: r.y, simple: r.a.viaS });
    if (res === 'hit' || res === 'armor') r.a.contact = r.a.contact || 1;
    if (res === 'block') r.a.contact = 2;
    if (res === 'hit' && r.mv.cine && r.def.hp > 0) startCine(cfg, state, r.a, r.def, r.mv);
  }
  // projectiles
  for (const p of state.proj) {
    if (p.item || p.cool > 0 || p.hits <= 0 || (p.trap && !p.triggered)) continue;
    const def = state.f[1 - p.owner];
    if (invulnTo(cfg, def, 'proj') || invulnTo(cfg, def, 'strike')) continue;
    const hurts = hurtboxes(cfg, def);
    const pb = projBox(p);
    if (!hurts.some((b) => overlap(pb, b))) continue;
    const owner = state.f[p.owner];
    const res = applyHit(cfg, state, owner, def, p.hit, null, { proj: p, px: p.x, x: p.x, y: clamp(p.y, def.y + 20 * CM, def.y + 170 * CM), simple: p.simple });
    if (res === 'none' && p.reflect) continue;
    p.hits--; p.cool = p.every;
    if (p.hits <= 0) ev(state, { t: 'projEnd', id: p.id, kind: p.kind, x: p.x, y: p.y, hit: true });
  }
  state.proj = state.proj.filter((p) => p.hits > 0);
}
const f_inActive = (a, mv) => a.mf >= mv.startup && a.mf < mv.startup + mv.active;

// ---------------------------------------------------------------- physics

function physics(cfg, state, f) {
  const d = dataOf(cfg, f);
  const g = Math.trunc((GRAVITY * cfg.gravityPct) / 100);
  const mv = moveOf(cfg, f);
  if (f.act === 'thrown' || f.act === 'cined' || f.act === 'splat' || f.act === 'cine') return;
  const airborneState = f.y > 0 || f.vy > 0;
  if (airborneState) {
    let grav = g;
    if (f.act === 'air') grav = g + Math.min(f.combo, 10) * 3; // juggles get heavier
    if (mv && mv.float && inWindow(mv.float, f.mf)) grav = Math.trunc(grav / 5);
    f.vy -= grav;
    f.y += f.vy;
    f.x += f.vx;
    if (f.y <= 0) land(cfg, state, f, d, mv);
  } else {
    f.y = 0;
    f.x += f.vx + f.slide;
    if (f.slide !== 0) { f.slide = Math.trunc((f.slide * 80) / 100); if (Math.abs(f.slide) < 20) f.slide = 0; }
  }
  // rewind history (Tock): positions over the last second
  if (state.frame % 6 === 0) { f.rew.push(f.x); if (f.rew.length > 10) f.rew.shift(); }
}

function land(cfg, state, f, d, mv) {
  f.y = 0; f.vy = 0;
  if (f.act === 'jump') { setAct(f, 'land'); f.stun = 3; f.vx = 0; ev(state, { t: 'land', who: f.i }); return; }
  if (f.act === 'move' && mv && (mv.air || mv.landCancel)) {
    f.move = null; setAct(f, 'land'); f.stun = mv.landRecovery ?? 4; f.vx = 0; ev(state, { t: 'land', who: f.i });
    if (mv.landHit) { /* handled as normal hits */ }
    return;
  }
  if (f.act === 'move') { return; } // a grounded move that hopped (DP): keep going, it ends on its own
  if (f.act === 'air') {
    f.vx = 0;
    if (f.knock === 'land') { setAct(f, 'land'); f.stun = 6; return; }
    setAct(f, 'down'); f.down = f.knock === 'hkd' ? 54 : 30; f.combo = 0;
    ev(state, { t: 'down', who: f.i, x: f.x, hard: f.knock === 'hkd' });
    return;
  }
  if (f.act === 'ko') { f.vx = 0; ev(state, { t: 'down', who: f.i, x: f.x, ko: true }); return; }
  if (f.act === 'splat') return;
  setAct(f, 'land'); f.stun = 3; f.vx = 0;
}

function separate(cfg, state) {
  const [a, b] = state.f;
  const da = dataOf(cfg, a), db = dataOf(cfg, b);
  const ha = onGround(a) ? da.height : 120 * CM, hb = onGround(b) ? db.height : 120 * CM;
  const ya0 = a.y + (onGround(a) ? 0 : 30 * CM), yb0 = b.y + (onGround(b) ? 0 : 30 * CM);
  const yOverlap = ya0 < yb0 + hb && yb0 < ya0 + ha;
  const minGap = (da.width + db.width) >> 1;
  const skip = a.act === 'thrown' || b.act === 'thrown' || a.act === 'cined' || b.act === 'cined' || a.act === 'down' || b.act === 'down';
  if (yOverlap && !skip) {
    const dx = b.x - a.x;
    if (Math.abs(dx) < minGap) {
      const dirAB = dx !== 0 ? sign(dx) : a.face;
      const need = minGap - Math.abs(dx);
      // walking into someone pushes them at half speed
      let pa = need >> 1, pb = need - pa;
      a.x -= dirAB * pa; b.x += dirAB * pb;
    }
  }
  // walls
  for (const f of state.f) {
    const w = dataOf(cfg, f).width >> 1;
    if (f.x < -WALL + w) { f.x = -WALL + w; if (cfg.bouncyWalls && f.act === 'air') { f.vx = Math.abs(f.vx); ev(state, { t: 'wallBounce', who: f.i }); } }
    if (f.x > WALL - w) { f.x = WALL - w; if (cfg.bouncyWalls && f.act === 'air') { f.vx = -Math.abs(f.vx); ev(state, { t: 'wallBounce', who: f.i }); } }
  }
  // max distance (camera)
  const gap = Math.abs(a.x - b.x);
  if (gap > MAX_GAP) {
    const over = gap - MAX_GAP;
    const left = a.x < b.x ? a : b, right = a.x < b.x ? b : a;
    // whoever is moving away gets stopped
    if (left.vx < 0 || left.slide < 0) left.x += over; else if (right.vx > 0 || right.slide > 0) right.x -= over; else { left.x += over >> 1; right.x -= over - (over >> 1); }
  }
}

// ---------------------------------------------------------------- round flow

function roundOver(cfg, state, winner, how) {
  state.phase = 'ko'; state.pt = 0; state.roundWinner = winner; state.slow = how === 'ko' ? 80 : 0;
  if (winner >= 0) state.wins[winner]++;
  ev(state, { t: 'roundOver', winner, how, perfect: winner >= 0 && state.f[winner].hp === state.f[winner].maxHp });
}

function phaseLogic(cfg, state, inputs) {
  state.pt++;
  const [a, b] = state.f;
  if (state.phase === 'intro') {
    const skip = state.pt > 40 && (inputs[0] & 0xff0) && (inputs[1] & 0xff0);
    if (state.pt >= INTRO_FRAMES || skip || cfg.skipIntro) { state.phase = 'ready'; state.pt = 0; for (const f of state.f) setAct(f, 'idle'); ev(state, { t: 'round', n: state.round }); }
    return false;
  }
  if (state.phase === 'ready') {
    if (state.pt === 1 && state.round === 1 && !cfg.skipIntro) { /* already announced */ }
    if (state.pt >= READY_FRAMES) { state.phase = 'fight'; state.pt = 0; for (const f of state.f) if (f.act === 'intro') setAct(f, 'idle'); ev(state, { t: 'fight' }); }
    return false;
  }
  if (state.phase === 'fight') {
    if (cfg.training) { // training: refill and never end
      for (const f of state.f) if (f.hp <= 0) { f.hp = f.maxHp; }
      return true;
    }
    const koA = a.hp <= 0, koB = b.hp <= 0;
    if (koA || koB) { roundOver(cfg, state, koA && koB ? -1 : koA ? 1 : 0, 'ko'); return true; }
    if (state.timer > 0 && !state.cine && state.freeze === 0) {
      state.timer--;
      if (state.timer === 0) {
        if (cfg.suddenDeath && a.hp * b.maxHp === b.hp * a.maxHp) { a.hp = 1; b.hp = 1; state.timer = 30 * 60; ev(state, { t: 'suddenDeath' }); return true; }
        const ra = a.hp * b.maxHp, rb = b.hp * a.maxHp;
        roundOver(cfg, state, ra === rb ? -1 : ra > rb ? 0 : 1, 'time');
        for (const f of state.f) if (f.act !== 'ko') { setAct(f, 'timeout'); f.move = null; f.vx = 0; }
      }
    }
    return true;
  }
  if (state.phase === 'ko') {
    // let the loser fall, then pose
    const settled = state.f.every((f) => f.act !== 'ko' || f.y <= 0) && state.pt > 70;
    if (settled && state.pt >= KO_FRAMES) {
      state.phase = 'roundEnd'; state.pt = 0;
      const w = state.roundWinner;
      for (const f of state.f) {
        f.move = null; f.vx = 0;
        if (f.i === w) setAct(f, 'win'); else if (f.hp > 0) setAct(f, 'lose');
      }
      const need = cfg.rounds;
      if (state.wins[0] >= need || state.wins[1] >= need) {
        state.winner = state.wins[0] >= need && state.wins[1] >= need ? -1 : state.wins[0] >= need ? 0 : 1;
      }
    }
    return true; // fighters keep moving (falling, sliding) during the KO
  }
  if (state.phase === 'roundEnd') {
    if (state.pt >= ROUND_END_FRAMES) {
      if (state.winner !== -1 || (state.wins[0] >= cfg.rounds || state.wins[1] >= cfg.rounds)) {
        state.phase = 'matchEnd'; state.pt = 0; ev(state, { t: 'matchEnd', winner: state.winner });
      } else {
        state.round++; resetRound(cfg, state, false); state.phase = 'ready'; state.pt = 0; ev(state, { t: 'round', n: state.round });
      }
    }
    return false;
  }
  return false;
}

// ---------------------------------------------------------------- the step

/** Advance one frame. inputs: [bitsP1, bitsP2]. Returns state.events (presentation events of this frame). */
export function step(match, inputs) {
  const { cfg, state } = match;
  state.frame++;
  state.events = [];
  // inputs are always recorded (buffers keep working through freezes and hitstop)
  // (button buffers don't age while a fighter is frozen in hitstop or a super flash, like Street Fighter)
  for (let i = 0; i < 2; i++) feed(state.f[i].inp, inputs[i] | 0, state.f[i].face, state.f[i].hs > 0 || state.freeze > 0);
  const live = phaseLogic(cfg, state, inputs);
  if (state.phase === 'roundEnd' || state.phase === 'matchEnd' || state.phase === 'intro' || state.phase === 'ready') {
    for (const f of state.f) { f.t++; }
    return state.events;
  }
  if (state.freeze > 0) { state.freeze--; return state.events; }
  if (state.slow > 0) { state.slow--; if (state.slow % 3 !== 0) return state.events; }
  if (state.cine) { updateCine(cfg, state); for (const f of state.f) f.t++; return state.events; }
  // speed modifier: skip or double frames deterministically
  const reps = speedReps(cfg, state);
  for (let r = 0; r < reps; r++) simFrame(cfg, state, live);
  return state.events;
}

function speedReps(cfg, state) {
  const s = cfg.speedPct;
  if (s === 100) return 1;
  // accumulate: e.g. 120 % runs 6 frames for every 5
  state.speedAcc = (state.speedAcc || 0) + s;
  let n = 0;
  while (state.speedAcc >= 100) { state.speedAcc -= 100; n++; }
  return n;
}

function simFrame(cfg, state, live) {
  const [a, b] = state.f;
  if (state.timeStop > 0) state.timeStop--;
  for (const f of state.f) {
    if (state.timeStop > 0 && f.i !== state.timeStopBy) continue;
    if (f.hs > 0) { f.hs--; continue; }
    if (f.act === 'throwing' && f.grab) { updateGrab(cfg, state, f, other(state, f)); continue; }
    if (f.act === 'thrown') { f.t++; continue; }
    updateFighter(cfg, state, f);
  }
  for (const f of state.f) {
    if (state.timeStop > 0 && f.i !== state.timeStopBy) continue;
    if (f.hs > 0 && f.act !== 'ko') continue;
    physics(cfg, state, f);
  }
  separate(cfg, state);
  if (live || state.phase === 'ko') {
    if (state.phase === 'fight') checkHits(cfg, state);
    updateProjectiles(cfg, state);
  }
  // facing after landing
  for (const f of state.f) if (onGround(f) && (f.act === 'idle' || f.act === 'crouch' || f.act === 'land')) faceOpponent(f, other(state, f));
  // item drops / hazards
  if (cfg.itemDrops && state.phase === 'fight') { itemDrops(cfg, state); pickupItems(cfg, state); }
}

function itemDrops(cfg, state) {
  if (state.frame % 300 !== 150) return;
  const kinds = ['thermos', 'bomb', 'coin'];
  const kind = kinds[rand(state, 3)];
  const x = (rand(state, 1200) - 600) * CM;
  state.proj.push({
    id: state.nextId++, owner: -1, kind: 'item_' + kind, x, y: 600 * CM, vx: 0, vy: 0, face: 1, box: [-30 * CM, 0, 60 * CM, 60 * CM],
    life: 600, hits: 1, every: 1, cool: 0, t: 0, hit: null, power: 0, gravity: 30, main: false, simple: false,
    trap: null, wall: 0, hop: null, from: 'item', armed: true, ground: true, item: kind,
  });
}

/** items are picked up by touching them (handled here so it stays deterministic) */
export function pickupItems(cfg, state) {
  for (const p of state.proj) {
    if (!p.item || p.y > 40 * CM) continue;
    for (const f of state.f) {
      if (Math.abs(f.x - p.x) < 60 * CM && f.y < 60 * CM && p.hits > 0) {
        p.hits = 0;
        if (p.item === 'thermos') f.hp = Math.min(f.maxHp, f.hp + pct(f.maxHp, 10));
        if (p.item === 'coin') gainMeter(cfg, f, 500);
        if (p.item === 'bomb') { f.hp = Math.max(1, f.hp - pct(f.maxHp, 8)); setAct(f, 'air'); f.vy = 10 * CM; f.knock = 'kd'; }
        ev(state, { t: 'item', who: f.i, item: p.item, x: p.x });
      }
    }
  }
}

export { onGround, worldBox, moveOf };
