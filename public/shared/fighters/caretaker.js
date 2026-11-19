// The Caretaker — Ruler of the Mossy Crypt. Big body: a giant shovel for reach, a lantern, armour and graves.
// docs/ROSTER.md. Slow walk, long pokes (st.M / 2M / st.H reach 1.5–1.7 m), a 41236 command grab, an armoured
// overhead slam that ground-bounces, grave hands at three ranges, and a lantern thrown from the air.
import { defineFighter, pick } from '../movekit.js';
import { universal, reach } from './common.js';

const EX = (v) => (v === 'EX' ? 'ex' : 'special');

export default defineFighter({
  id: 'caretaker', name: 'The Caretaker', title: 'Ruler of the Mossy Crypt', hp: 1150, archetype: 'Big body, shovel reach',
  walkF: 3.2, walkB: 2.7, dashF: { frames: 24, dist: 112 }, dashB: { frames: 26, dist: 95, invuln: 6 },
  jump: { pre: 5, vy: 14.4, vx: 4.0 }, width: 66, height: 200, crouchHeight: 126,
  normals: {
    stand: { L: 'st_L', M: 'st_M', H: 'st_H' },
    crouch: { L: 'cr_L', M: 'cr_M', H: 'cr_H' },
    air: { L: 'j_L', M: 'j_M', H: 'j_H' },
    command: [{ dir: 6, btn: 'M', id: 'bonk' }, { dir: 6, btn: 'H', id: 'sixfeet' }, { dir: 3, btn: 'H', id: 'uproot' }],
  },
  // 41236 is listed before 236 so a half-circle never comes out as Dirt Sweep
  specials: [
    { id: 'plant', motion: '41236', simple: 6 },
    { id: 'dirt', motion: '236', simple: 5 },
    { id: 'slam', motion: '214', simple: 4 },
    { id: 'grave', motion: '22', simple: 2 },
    { id: 'lantern', motion: '236', simple: 5, air: true },
    { id: 'lantern', simple: 6, air: true }, { id: 'lantern', simple: 4, air: true }, { id: 'lantern', simple: 2, air: true },
  ],
  supers: { art: 'lastrites', final: 'garden', overtime: 'fury' },
  autoCombo: ['st_L', 'st_M', 'st_H', 'slam'],
  moves: {
    // ------------------------------------------------------------ standing
    st_L: {
      name: 'Lantern Jab', startup: 5, active: 3, recovery: 8,
      hits: [{ dmg: 30, box: [22, 108, 66, 32], stun: 14, bstun: 11, push: 24, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(4, 10, [12, 104, 66, 36])],
      cancel: { into: ['st_L', 'cr_L', 'st_M', 'cr_M'], special: true, super: true },
    },
    st_M: {
      name: 'Shovel Poke', startup: 9, active: 3, recovery: 15,
      hits: [{ dmg: 55, box: [44, 92, 112, 30], stun: 21, bstun: 16, push: 34, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(7, 20, [20, 88, 112, 36])], vel: [[2, 1.0], [8, 0]],
      cancel: { into: ['st_H', 'cr_H', 'uproot'], special: true, super: true },
    },
    st_H: {
      name: 'Backhand Swing', startup: 13, active: 4, recovery: 22,
      hits: [{ dmg: 90, box: [30, 66, 138, 54], stun: 26, bstun: 21, push: 46, hitstop: 13, spark: 'H', sfx: 'H' }],
      hurt: [reach(10, 26, [16, 60, 132, 62])], vel: [[3, 1.4], [12, 0]],
      cancel: { special: true, super: true },
    },
    // ------------------------------------------------------------ crouching
    cr_L: {
      name: 'Hobnail Boot', startup: 5, active: 2, recovery: 9, crouching: true,
      hits: [{ dmg: 25, box: [22, 2, 62, 26], level: 'low', stun: 13, bstun: 10, push: 22, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(4, 9, [12, 0, 68, 30])],
      cancel: { into: ['cr_L', 'st_L', 'cr_M', 'st_M'], special: true, super: true },
    },
    cr_M: {
      name: 'Edge Poke', startup: 10, active: 3, recovery: 16, crouching: true,
      hits: [{ dmg: 50, box: [42, 0, 104, 28], level: 'low', stun: 20, bstun: 15, push: 32, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(8, 22, [20, 0, 110, 32])],
      cancel: { into: ['st_H', 'cr_H', 'uproot'], special: true, super: true },
    },
    cr_H: {
      name: 'Trim the Edges', startup: 12, active: 4, recovery: 26, crouching: true,
      hits: [{ dmg: 85, box: [34, 0, 140, 26], level: 'low', effect: 'kd', launch: [1.6, 4], bstun: 18, push: 34, hitstop: 13, spark: 'H', sfx: 'H' }],
      hurt: [reach(10, 30, [20, 0, 146, 32])],
      cancel: { special: true, super: true },
    },
    // ------------------------------------------------------------ air
    j_L: {
      name: 'Lantern Swing', air: true, startup: 6, active: 6, recovery: 5, landRecovery: 3,
      hits: [{ dmg: 35, box: [14, 30, 62, 56], level: 'ovh', stun: 14, bstun: 10, push: 20, hitstop: 8, spark: 'fire', sfx: 'L' }],
    },
    j_M: {
      name: 'Spade Jab', air: true, startup: 8, active: 5, recovery: 7, landRecovery: 4,
      hits: [{ dmg: 55, box: [24, -16, 92, 56], level: 'ovh', stun: 18, bstun: 13, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
      cancel: { special: true },
    },
    j_H: {
      name: 'Tamp Down', air: true, startup: 11, active: 6, recovery: 8, landRecovery: 6,
      hits: [{ dmg: 88, box: [12, -36, 96, 76], level: 'ovh', stun: 23, bstun: 17, push: 34, hitstop: 13, spark: 'H', sfx: 'H' }],
    },
    // ------------------------------------------------------------ command normals
    bonk: {
      name: 'Lantern Bonk', startup: 19, active: 3, recovery: 16,
      hits: [{ dmg: 60, box: [26, 96, 72, 76], level: 'ovh', stun: 20, bstun: 14, push: 30, hitstop: 12, spark: 'fire', sfx: 'H' }],
      vel: [[4, 1.2], [16, 0]],
      cancel: { super: true },
    },
    sixfeet: {
      name: 'Six Feet Under', startup: 20, active: 4, recovery: 24,
      armor: { frames: [5, 20], hits: 1 },
      hits: [{ dmg: 105, box: [46, 0, 110, 190], stun: 26, bstun: 20, push: 44, effect: 'kd', launch: [2, 4], hitstop: 15, spark: 'H', sfx: 'H' }],
      hurt: [reach(18, 32, [30, 0, 120, 90])], vel: [[3, 1.5], [16, 0]],
      cancel: { super: true },
    },
    uproot: {
      name: 'Uproot', startup: 11, active: 5, recovery: 26,
      hits: [{ dmg: 75, box: [24, 30, 96, 186], effect: 'launch', launch: [1.2, 13.5], juggle: 2, bstun: 18, push: 10, hitstop: 13, spark: 'H', sfx: 'H' }],
      hurt: [reach(10, 22, [16, 60, 90, 170])],
      cancel: { special: true, super: true },
    },
    // ------------------------------------------------------------ specials
    // 41236: Another One for the Garden — command grab, plants the opponent head-first (hard knockdown)
    plant: (v) => ({
      name: 'Another One for the Garden', type: EX(v), startup: pick(v, [6, 7, 8, 6]), active: 3, recovery: 42,
      invuln: v === 'EX' ? { strike: [1, 9], proj: [1, 9] } : undefined,
      grab: { range: pick(v, [78, 84, 90, 92]), len: 66, hold: 82, toss: [1.2, 2.5], hkd: true, techable: false },
      hits: [
        { dmg: pick(v, [40, 45, 50, 55]), frames: [22, 22], spark: 'M', sfx: 'throw', hitstop: 6, meter: 30 },
        { dmg: pick(v, [100, 110, 120, 130]), frames: [50, 50], spark: 'H', sfx: 'H', hitstop: 14, meter: 60 },
      ],
    }),
    // 236: Dirt Sweep — a low arcing clod of dirt (L short, H long; EX two clods, knockdown)
    dirt: (v) => ({
      name: 'Dirt Sweep', type: EX(v), startup: pick(v, [15, 16, 17, 14]), active: 2, recovery: 26,
      oneProj: true,
      proj: (v === 'EX' ? [4.4, 6.6] : [pick(v, [4.0, 5.2, 6.5])]).map((vx) => ({
        at: pick(v, [15, 16, 17, 14]), kind: 'dirt', x: 82, y: 64, vx, vy: 4.6, gravity: 0.22, life: 52,
        box: [-24, -24, 48, 48], power: v === 'EX' ? 2 : 1,
        hit: { dmg: pick(v, [60, 65, 70, 50]), stun: 20, bstun: 15, push: 36, hitstop: 10, spark: 'M', sfx: 'M', effect: v === 'EX' ? 'kd' : 'normal', launch: [2.2, 5] },
      })),
    }),
    // 214: Overhead Slam — armoured (M/H 1 hit, EX 2) shovel slam; overhead. The victim bounces off the floor
    // (a short launch: the engine's 'bounce' is too low to follow from this far away), -7 on block.
    slam: (v) => ({
      name: 'Overhead Slam', type: EX(v), startup: pick(v, [18, 21, 24, 18]), active: 4, recovery: 13,
      armor: v === 'L' ? undefined : { frames: v === 'EX' ? [1, 18] : [4, pick(v, [0, 20, 23])], hits: v === 'EX' ? 2 : 1 },
      vel: [[3, pick(v, [1.2, 1.8, 2.6, 2.2])], [pick(v, [16, 19, 22, 16]), 0]],
      hits: [{
        dmg: pick(v, [100, 110, 120, 115]), box: [40, 0, pick(v, [112, 124, 138, 130]), 170], level: 'ovh',
        effect: 'launch', launch: [0.5, pick(v, [13, 13, 13, 14])], juggle: 1,
        stun: 28, bstun: 10, push: 40, hitstop: 16, spark: 'H', sfx: 'H',
      }],
      hurt: [reach(pick(v, [18, 21, 24, 18]), 34, [30, 0, 130, 80])],
      cancel: { super: true },
    }),
    // 22: Grave Call — hands burst from the ground near / mid / far (EX: all three)
    grave: (v) => ({
      name: 'Grave Call', type: EX(v), startup: 18, active: 2, recovery: 24,
      oneProj: true,
      proj: (v === 'EX' ? [115, 200, 285] : [pick(v, [115, 200, 285])]).map((dist) => ({
        at: 18, kind: 'hands', place: 'dist', dist, x: 1, y: 1, vx: 0, vy: 0, life: 34, delay: v === 'EX' ? 9 : 12,
        box: [-34, 0, 68, 112], power: 2,
        hit: { dmg: v === 'EX' ? 55 : pick(v, [70, 75, 80]), stun: 24, bstun: 16, push: 10, hitstop: 12, spark: 'M', sfx: 'H', effect: 'launch', launch: [0.6, 10.5], juggle: 2 },
      })),
    }),
    // j.236: Lantern Toss — the lantern flies diagonally down and burns where it lands
    lantern: (v) => ({
      name: 'Lantern Toss', type: EX(v), air: true, startup: 10, active: 2, recovery: 16, landRecovery: 6,
      oneProj: true,
      proj: {
        at: 10, kind: 'fire', x: 40, y: 140, vx: pick(v, [3.0, 4.2, 5.4, 4.6]), vy: -6, life: pick(v, [70, 70, 70, 96]),
        hop: { delay: 0, vx: 0, vy: 0 }, box: [-28, -18, 56, 46], hits: v === 'EX' ? 3 : 1, every: 12,
        hit: { dmg: v === 'EX' ? 34 : pick(v, [55, 60, 65]), stun: 22, bstun: 15, push: 26, hitstop: 10, spark: 'fire', sfx: 'flare', effect: v === 'EX' ? 'kd' : 'normal', launch: [2, 6] },
      },
    }),
    // ------------------------------------------------------------ supers
    lastrites: {
      name: 'Last Rites', type: 'super', cost: 1000, freeze: 36, startup: 9, active: 6, recovery: 34,
      invuln: { strike: [1, 12], throw: [1, 12] },
      vel: [[1, 7], [14, 0]],
      hits: [{ dmg: 30, box: [24, 20, 136, 150], stun: 40, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 126, hold: 112, hits: [[10, 36], [24, 36], [40, 40], [62, 44], [98, 110]] },
    },
    garden: {
      name: 'The Garden', type: 'final', cost: 3000, freeze: 44, startup: 12, active: 8, recovery: 44,
      invuln: { full: [1, 18] },
      hits: [{ dmg: 30, box: [36, 0, 230, 130], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 186, hold: 125, hits: [[30, 70], [62, 70], [98, 90], [156, 190]] },
    },
    fury: {
      name: 'Fury', type: 'overtime', freeze: 44, startup: 12, active: 8, recovery: 40,
      invuln: { full: [1, 20] },
      vel: [[1, 4.5], [18, 0]],
      hits: [{ dmg: 30, box: [10, 20, 140, 170], stun: 60, hitstop: 4, spark: 'fire', sfx: 'H', meter: 0 }],
      cine: { len: 156, hold: 118, hits: [[16, 50], [34, 50], [52, 55], [72, 60], [116, 140]] },
    },
    ...universal({ throwRange: 80, throwDmg: 130, bthrowDmg: 140, breakerBox: [20, 60, 110, 90], breakerDmg: 95 }),
  },
  // presentation
  colors: ['#4f6b2e', '#8a3b1e', '#2e5a6b', '#6b5a2e', '#5a2e6b', '#9a9a6a', '#2b2b2b', '#b8462e'],
  lines: {
    intro: 'Another one for the garden.',
    win: ['Plenty of room.', 'Wipe your feet.', "Don't fret. I'll water you."],
  },
});
