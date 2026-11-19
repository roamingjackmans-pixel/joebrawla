// Mother Spore — Ruler of the Fungal Hollows. Zoner and trap-layer: a slow drifting spore cloud (one at a
// time), hopping sporelings and a puffball mine (two at a time), a long low root lash, a mushroom stalk that
// erupts in front of her (anti-air) and a cap she glides on. Slow on foot, long staff reach, floaty in the air.
// Counterplay: every zoning tool has a slow start and a long finish, the cloud can be jumped or shot down,
// sporelings can be jumped and outrun, the stalk loses to cross-ups. docs/ROSTER.md
import { defineFighter, pick } from '../movekit.js';
import { universal, reach } from './common.js';

/** sporelings and puffballs on screen (two at a time) */
const fewSporelings = (f, state) => state.proj.filter((p) => p.owner === f.i && p.from.startsWith('sporeling')).length < 2;

export default defineFighter({
  id: 'mother_spore', name: 'Mother Spore', title: 'Ruler of the Fungal Hollows', hp: 950, archetype: 'Zoner',
  walkF: 3.6, walkB: 3.4, dashF: { frames: 22, dist: 120 }, dashB: { frames: 24, dist: 115, invuln: 7 },
  jump: { pre: 5, vy: 14.6, vx: 4.2 }, width: 54, height: 186, crouchHeight: 112,
  normals: {
    stand: { L: 'st_L', M: 'st_M', H: 'st_H' },
    crouch: { L: 'cr_L', M: 'cr_M', H: 'cr_H' },
    air: { L: 'j_L', M: 'j_M', H: 'j_H' },
    command: [{ dir: 6, btn: 'M', id: 'bonk' }],
  },
  specials: [
    { id: 'stalk', motion: '623', simple: 6 },
    { id: 'bloom', motion: '236', simple: 5 },
    { id: 'whip', motion: '214', simple: 4 },
    { id: 'sporeling', motion: '22', simple: 2, needs: fewSporelings },
    { id: 'glide', motion: '214', simple: 5, air: true, needs: (f) => f.airUsed < 1 },
  ],
  supers: { art: 'caps', final: 'soil', overtime: 'overbloom' },
  autoCombo: ['st_L', 'st_M', 'st_H', 'whip'],
  moves: {
    // ------------------------------------------------------------ normals (staff reach, deliberate timing)
    st_L: {
      name: 'Spore Flick', startup: 5, active: 2, recovery: 8,
      hits: [{ dmg: 28, box: [26, 118, 60, 24], stun: 13, bstun: 11, push: 22, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(4, 9, [12, 114, 66, 28])],
      cancel: { into: ['st_L', 'cr_L', 'st_M', 'cr_M'], special: true, super: true },
    },
    st_M: {
      name: 'Stalk Prod', startup: 8, active: 3, recovery: 14,
      hits: [{ dmg: 52, box: [30, 100, 96, 26], stun: 19, bstun: 14, push: 32, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(7, 18, [20, 98, 100, 30])], vel: [[3, 1.0], [9, 0]],
      cancel: { into: ['st_H', 'cr_H'], special: true, super: true },
    },
    st_H: {
      name: 'Cap Sweep', startup: 12, active: 5, recovery: 19,
      hits: [{ dmg: 85, box: [16, 75, 104, 85], stun: 23, bstun: 18, push: 44, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(10, 26, [16, 80, 100, 70])], vel: [[5, 1.4], [13, 0]],
      cancel: { special: true, super: true },
    },
    cr_L: {
      name: 'Root Tap', startup: 5, active: 2, recovery: 8, crouching: true,
      hits: [{ dmg: 24, box: [24, 2, 60, 22], level: 'low', stun: 12, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(4, 9, [10, 0, 70, 26])],
      cancel: { into: ['cr_L', 'st_L', 'cr_M', 'st_M'], special: true, super: true },
    },
    cr_M: {
      name: 'Creeping Root', startup: 9, active: 3, recovery: 14, crouching: true,
      hits: [{ dmg: 48, box: [32, 0, 100, 22], level: 'low', stun: 18, bstun: 14, push: 30, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(8, 20, [20, 0, 104, 26])],
      cancel: { into: ['st_H', 'cr_H'], special: true, super: true },
    },
    cr_H: {
      name: 'Uproot', startup: 10, active: 4, recovery: 24, crouching: true,
      hits: [{ dmg: 72, box: [12, 60, 70, 120], effect: 'launch', launch: [1.4, 12.5], juggle: 2, bstun: 16, push: 10, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(9, 22, [10, 70, 70, 110])],
      cancel: { special: true, super: true },
    },
    j_L: {
      name: 'Frill Kick', air: true, startup: 5, active: 6, recovery: 5, landRecovery: 2,
      hits: [{ dmg: 30, box: [6, 10, 50, 46], level: 'ovh', stun: 14, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
    },
    j_M: {
      name: 'Staff Dip', air: true, startup: 8, active: 5, recovery: 6, landRecovery: 3,
      hits: [{ dmg: 52, box: [18, -16, 66, 56], level: 'ovh', stun: 18, bstun: 13, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
    },
    j_H: {
      name: 'Cap Crash', air: true, startup: 10, active: 6, recovery: 6, landRecovery: 4,
      hits: [{ dmg: 80, box: [-6, -22, 82, 64], level: 'ovh', stun: 22, bstun: 16, push: 34, hitstop: 12, spark: 'H', sfx: 'H' }],
    },
    bonk: {
      name: 'Toadstool Bonk', startup: 19, active: 2, recovery: 15,
      hits: [{ dmg: 58, box: [30, 60, 76, 90], level: 'ovh', stun: 18, bstun: 12, push: 30, hitstop: 12, spark: 'spore', sfx: 'H' }],
      hurt: [reach(12, 28, [20, 80, 80, 90])], vel: [[5, 1.2], [18, 0]],
      cancel: { super: true },
    },

    // ------------------------------------------------------------ specials
    // a slow spore cloud drifting forward (L close, H far); one on screen; any projectile pops it
    bloom: (v) => ({
      name: 'Spore Bloom', type: v === 'EX' ? 'ex' : 'special', startup: 16, active: 2, recovery: pick(v, [28, 30, 32, 26]),
      oneProj: true,
      proj: {
        at: 16, kind: 'spore', x: 70, y: 95, vx: pick(v, [1.0, 1.6, 2.3, 1.4]), life: pick(v, [140, 150, 160, 200]),
        box: v === 'EX' ? [-50, -50, 100, 100] : [-38, -38, 76, 76], hits: v === 'EX' ? 3 : 2, every: 20, power: v === 'EX' ? 2 : 1,
        hit: { dmg: v === 'EX' ? 34 : 32, stun: 22, bstun: 14, push: 16, hitstop: 8, spark: 'spore', sfx: 'M' },
      },
    }),
    // roots lash along the floor: long low knockdown, unsafe up close; EX lashes twice and launches
    whip: (v) => {
      const s = pick(v, [14, 16, 18, 14]);
      const far = pick(v, [150, 180, 210, 200]);
      return {
        name: 'Tendril Whip', type: v === 'EX' ? 'ex' : 'special', startup: s, active: v === 'EX' ? 11 : 4, recovery: pick(v, [22, 24, 26, 24]),
        hits: v === 'EX' ? [
          { dmg: 50, frames: [s, s + 2], box: [40, 0, far - 40, 28], level: 'low', stun: 26, bstun: 14, push: 6, hitstop: 9, spark: 'spore', sfx: 'M', juggle: 0 },
          { dmg: 70, frames: [s + 8, s + 10], box: [40, 0, far - 40, 130], effect: 'launch', launch: [1.2, 12], juggle: 2, bstun: 14, push: 20, hitstop: 12, spark: 'spore', sfx: 'H' },
        ] : [
          { dmg: pick(v, [70, 75, 80, 80]), box: [40, 0, far - 40, 28], level: 'low', effect: 'kd', launch: [2, 5], bstun: 14, push: 30, hitstop: 11, spark: 'spore', sfx: 'H' },
        ],
        hurt: [reach(s - 2, s + (v === 'EX' ? 14 : 8), [30, 0, far - 50, 30])],
      };
    },
    // L: a puffball mine that bursts when the opponent walks close; M/H/EX: a sporeling that hops after them
    sporeling: (v) => ({
      name: v === 'L' ? 'Sporeling (Puffball)' : 'Sporeling', type: v === 'EX' ? 'ex' : 'special', startup: 14, active: 2, recovery: 22,
      proj: v === 'L' ? {
        at: 14, kind: 'spore', x: 85, y: 1, life: 360, box: [-26, -1, 52, 44], hits: 1, power: 1,
        trap: { arm: 20, range: 55, delay: 5 },
        hit: { dmg: 55, effect: 'launch', launch: [0.6, 9], juggle: 2, stun: 20, bstun: 16, push: 20, hitstop: 10, spark: 'spore', sfx: 'H' },
      } : {
        at: 14, kind: 'spore', x: 60, y: 1, life: pick(v, [0, 300, 260, 260]), gravity: 0.6,
        box: [-20, -1, 40, 40], hits: v === 'EX' ? 2 : 1, every: 12, power: v === 'EX' ? 3 : 1,
        delay: pick(v, [0, 40, 24, 16]), hop: { delay: pick(v, [0, 40, 24, 16]), vx: pick(v, [0, 2.2, 3.0, 3.4]), vy: 6.5 },
        hit: { dmg: v === 'EX' ? 40 : 45, effect: v === 'EX' ? 'kd' : 'normal', launch: [2, 5], stun: 22, bstun: 14, push: 20, hitstop: 9, spark: 'spore', sfx: 'M' },
      },
    }),
    // a giant stalk bursts out of the floor in front of her: L close and fast, H far; EX two stalks, invulnerable
    stalk: (v) => {
      const s = pick(v, [6, 7, 8, 6]);
      return {
        name: 'Stalk Slam', type: v === 'EX' ? 'ex' : 'special', startup: s, active: v === 'EX' ? 7 : 6, recovery: pick(v, [24, 26, 28, 26]),
        invuln: v === 'EX' ? { full: [1, s + 4] } : { throw: [1, 4] },
        hits: v === 'EX' ? [
          { dmg: 70, frames: [s, s + 2], box: [20, 0, 70, 210], effect: 'launch', launch: [1, 13], juggle: 1, bstun: 16, push: 10, hitstop: 13, spark: 'spore', sfx: 'H' },
          { dmg: 70, frames: [s + 4, s + 6], box: [80, 0, 70, 210], effect: 'launch', launch: [1.4, 13.5], juggle: 0, bstun: 16, push: 10, hitstop: 13, spark: 'spore', sfx: 'H' },
        ] : [
          { dmg: pick(v, [80, 90, 100, 0]), box: [pick(v, [28, 55, 85, 0]), 0, 66, 205], effect: 'launch', launch: [1.2, 12.5], juggle: 1, bstun: 16, push: 10, hitstop: 13, spark: 'spore', sfx: 'H', meter: 30 },
        ],
      };
    },
    // j.S: the cap opens like a parasol; L drifts back, M hangs, H sails forward; EX sheds spores below
    glide: (v) => ({
      name: 'Cap Glide', type: v === 'EX' ? 'ex' : 'special', air: true, startup: 4, active: pick(v, [40, 48, 56, 48]), recovery: 4, landRecovery: 7,
      float: [1, 64],
      vel: [[1, pick(v, [-1.8, 0.8, 2.8, 2.0]), 1.5]],
      hits: v === 'EX' ? [10, 22, 34].map((a) => ({ dmg: 30, frames: [a, a + 2], box: [-50, -70, 100, 80], level: 'ovh', stun: 18, bstun: 12, push: 14, hitstop: 7, spark: 'spore', sfx: 'M' })) : [],
    }),

    // ------------------------------------------------------------ supers
    // a staff burst up close starts the cinematic; if it misses, caps rain on the opponent anyway (blockable)
    caps: {
      name: 'Rain of Caps', type: 'super', cost: 1000, freeze: 34, startup: 10, active: 6, recovery: 44,
      invuln: { strike: [1, 14], throw: [1, 14] },
      hits: [{ dmg: 40, box: [10, 30, 120, 150], stun: 40, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 96, hold: 110, hits: [[16, 35], [26, 35], [36, 35], [46, 35], [56, 35], [82, 100]] },
      proj: [-60, 40, -20, 70, 0, -80].map((off, k) => ({
        at: 18 + k * 6, kind: 'spore', place: 'opp', offset: off, y: 330, vy: -9, gravity: 0.5, life: 60,
        box: [-34, -24, 68, 48], hits: 1, power: 2,
        hit: { dmg: 42, stun: 22, bstun: 16, push: 14, hitstop: 8, spark: 'spore', sfx: 'M' },
      })),
    },
    soil: {
      name: 'Everything Becomes Soil', type: 'final', cost: 3000, freeze: 44, startup: 12, active: 6, recovery: 40,
      invuln: { full: [1, 16] },
      hits: [{ dmg: 30, box: [20, 0, 150, 120], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 175, hold: 110, hits: [[30, 100], [90, 130], [150, 220]] },
    },
    overbloom: {
      name: 'Overtime Bloom', type: 'overtime', freeze: 44, startup: 14, active: 6, recovery: 40,
      invuln: { full: [1, 18] },
      hits: [{ dmg: 30, box: [0, 0, 420, 70], level: 'low', stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 150, hold: 120, hits: [[34, 110], [80, 100], [124, 150]] },
    },
    ...universal({ throwRange: 74 }),
  },
  // presentation (tint1 = cap)
  colors: ['#a8402c', '#3b6e8f', '#6a8f3b', '#d8c9a0', '#5e3a7a', '#c9a227', '#2b2b33', '#e8e8e8'],
  lines: {
    intro: 'Hush now.',
    win: ['Everything becomes soil in the end.', 'Wipe that look off. It grows back.', 'Lie still. The roots will find you.'],
  },
});
