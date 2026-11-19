// Turns a fighter's authored data (centimetres, readable fields) into the simulation's compiled form (units).
// See docs/DESIGN.md §5 for the rules these numbers feed. Every fighter file calls defineFighter().
import { cm } from './core.js';

export const STR = ['L', 'M', 'H', 'EX'];
/** pick a value by strength: pick(v, [L, M, H, EX]) */
export const pick = (v, arr) => arr[Math.max(0, STR.indexOf(v))];

const DEFAULT_HIT = {
  dmg: 50, chip: 0, stun: 15, bstun: 11, push: 30, level: 'mid', effect: 'normal', juggle: 1, hitstop: 9,
  spark: 'M', sfx: 'M', meter: null, airPush: 2.5,
};

function box(b) { return b ? [cm(b[0]), cm(b[1]), cm(b[2]), cm(b[3])] : null; }

function compileHit(h, mv) {
  const out = { ...DEFAULT_HIT, ...h };
  if (mv.type !== 'normal' && h.chip === undefined) out.chip = Math.trunc(out.dmg / 5);
  out.box = box(h.box);
  out.push = cm(out.push);
  out.launch = h.launch ? [cm(h.launch[0]), cm(h.launch[1])] : null;
  out.airPush = cm(out.airPush);
  if (!h.frames) out.frames = [mv.startup, mv.startup + mv.active - 1];
  if (out.meter === null) out.meter = Math.max(8, Math.trunc(out.dmg * 0.9));
  return out;
}

function compileProj(p) {
  return {
    ...p,
    x: cm(p.x || 50), y: cm(p.y || 110), vx: cm(p.vx || 0), vy: cm(p.vy || 0), gravity: Math.round((p.gravity || 0) * 100),
    box: box(p.box || [-20, -20, 40, 40]), life: p.life || 120, hits: p.hits || 1, every: p.every || 8,
    hit: compileHit(p.hit || {}, { type: 'special', startup: 1, active: 1 }),
    power: p.power ?? 1,
  };
}

export function compileMove(id, mv) {
  const out = { id, type: 'normal', startup: 5, active: 3, recovery: 10, ...mv };
  out.total = out.startup + out.active + out.recovery;
  out.hits = (mv.hits || []).map((h) => compileHit(h, out));
  out.vel = (mv.vel || []).map(([f, vx, vy]) => [f, vx == null ? null : cm(vx), vy == null ? null : cm(vy)]);
  out.hurt = (mv.hurt || []).map((h) => ({ frames: h.frames, box: box(h.box) }));
  out.proj = mv.proj ? (Array.isArray(mv.proj) ? mv.proj : [mv.proj]).map(compileProj) : [];
  if (mv.grab) out.grab = { ...mv.grab, range: cm(mv.grab.range || 90) };
  if (mv.cancel) out.cancel = { slack: 6, ...mv.cancel };
  if (mv.counter) out.counter = { ...mv.counter };
  return out;
}

/**
 * def: { id, name, hp, walkF, walkB (cm/f), dashF:{frames,dist}, dashB:{frames,dist,invuln}, jump:{pre,vy,vx},
 *        width, height, crouchHeight, moves:{id: move}, specials:[{motion, simple, id:'base' (variants _L.._EX)}],
 *        normals:{stand:{L,M,H}, crouch:{L,M,H}, air:{L,M,H}, command:[{dir, btn, id}]},
 *        supers:{art, final, overtime}, autoCombo:[ids], ... render data (stance, colours, lines) passed through }
 */
export function defineFighter(def) {
  const moves = {};
  for (const [id, mv] of Object.entries(def.moves)) {
    if (typeof mv === 'function') {
      for (const v of STR) {
        const m = mv(v);
        if (m) moves[`${id}_${v}`] = compileMove(`${id}_${v}`, { ...m, strength: v, base: id });
      }
    } else moves[id] = compileMove(id, mv);
  }
  const f = {
    ...def,
    walkF: cm(def.walkF || 4.5), walkB: cm(def.walkB || 3.6),
    dashF: { frames: 18, dist: 120, ...def.dashF }, dashB: { frames: 22, dist: 100, invuln: 7, ...def.dashB },
    jump: { pre: 4, vy: 15.2, vx: 4.6, ...def.jump },
    width: cm(def.width || 48), height: cm(def.height || 172), crouchHeight: cm(def.crouchHeight || 108),
    moves,
  };
  f.dashF.distU = cm(f.dashF.dist); f.dashB.distU = cm(f.dashB.dist);
  f.jump.vyU = cm(f.jump.vy); f.jump.vxU = cm(f.jump.vx);
  for (const s of def.specials || []) {
    for (const v of STR) if (!moves[`${s.id}_${v}`]) throw new Error(`${def.id}: special ${s.id}_${v} missing`);
  }
  return f;
}
