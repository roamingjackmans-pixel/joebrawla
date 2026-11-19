// The Instructor — Management's orientation officer. Counters and corrections. docs/ROSTER.md
// Plays patient and exact: long, precise baton pokes that are plus or even, a counter stance that ends in a
// textbook hard-knockdown takedown, a short whistle blast that shoves people back out, a training dummy that eats
// a projectile (and, on the way down, one strike), and a step-in Correction that splats on the wall.
import { defineFighter, pick } from '../movekit.js';
import { universal, reach } from './common.js';

const mine = (f, state, kind) => state.proj.some((p) => p.owner === f.i && p.kind === kind);

export default defineFighter({
  id: 'instructor', name: 'The Instructor', title: 'Orientation Officer', hp: 1000, archetype: 'Counter fighter',
  walkF: 4.0, walkB: 3.7, dashF: { frames: 19, dist: 118 }, dashB: { frames: 22, dist: 108, invuln: 7 },
  jump: { pre: 4, vy: 15.3, vx: 4.4 }, width: 48, height: 190, crouchHeight: 112,
  normals: {
    stand: { L: 'st_L', M: 'st_M', H: 'st_H' },
    crouch: { L: 'cr_L', M: 'cr_M', H: 'cr_H' },
    air: { L: 'j_L', M: 'j_M', H: 'j_H' },
    command: [{ dir: 6, btn: 'M', id: 'attention' }, { dir: 6, btn: 'H', id: 'correction' }],
  },
  specials: [
    { id: 'popquiz', motion: '623', simple: 6 },
    { id: 'whistle', motion: '236', simple: 5 },
    { id: 'demo', motion: '214', simple: 4 },
    { id: 'dummy', motion: '22', simple: 2, needs: (f, s) => !mine(f, s, 'dummy') && !mine(f, s, 'dummyDrop') },
  ],
  supers: { art: 'orientation', final: 'exam', overtime: 'nobody' },
  autoCombo: ['st_L', 'st_M', 'st_H', 'popquiz'],
  moves: {
    // ------------------------------------------------------------ normals: long baton reach, good on block
    st_L: {
      name: 'Baton Tap', startup: 5, active: 2, recovery: 8,
      hits: [{ dmg: 28, box: [26, 120, 66, 20], stun: 14, bstun: 11, push: 22, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(4, 9, [10, 116, 66, 26])],
      cancel: { into: ['st_L', 'cr_L', 'st_M', 'cr_M'], special: true, super: true },
    },
    st_M: {
      name: 'Pointer', startup: 8, active: 3, recovery: 13,
      hits: [{ dmg: 50, box: [28, 104, 86, 22], stun: 19, bstun: 15, push: 30, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(7, 17, [10, 100, 86, 28])], vel: [[3, 1.4], [9, 0]],
      cancel: { into: ['st_H', 'cr_H', 'correction'], special: true, super: true },
    },
    st_H: {
      name: 'Demerit', startup: 12, active: 3, recovery: 19,
      hits: [{ dmg: 85, box: [24, 88, 84, 56], stun: 23, bstun: 18, push: 42, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(10, 24, [10, 86, 88, 60])], vel: [[4, 1.8], [12, 0]],
      cancel: { special: true, super: true },
    },
    cr_L: {
      name: 'Shin Check', startup: 4, active: 2, recovery: 8, crouching: true,
      hits: [{ dmg: 24, box: [18, 4, 60, 24], level: 'low', stun: 12, bstun: 9, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 2, 64, 28])],
      cancel: { into: ['cr_L', 'st_L', 'cr_M', 'st_M'], special: true, super: true },
    },
    cr_M: {
      name: 'Low Pointer', startup: 8, active: 3, recovery: 15, crouching: true,
      hits: [{ dmg: 46, box: [26, 8, 94, 22], level: 'low', stun: 18, bstun: 14, push: 30, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(7, 18, [10, 4, 96, 28])],
      cancel: { into: ['st_H', 'cr_H', 'correction'], special: true, super: true },
    },
    cr_H: {
      name: 'Textbook Sweep', startup: 10, active: 3, recovery: 24, crouching: true,
      hits: [{ dmg: 78, box: [26, 0, 98, 22], level: 'low', effect: 'kd', launch: [1.5, 4], bstun: 14, push: 30, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(9, 27, [10, 0, 100, 26])],
      cancel: { special: true, super: true },
    },
    j_L: {
      name: 'Knee', air: true, startup: 5, active: 6, recovery: 5, landRecovery: 2,
      hits: [{ dmg: 32, box: [10, 10, 50, 45], level: 'ovh', stun: 14, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
    },
    j_M: {
      name: 'Baton Down', air: true, startup: 7, active: 5, recovery: 6, landRecovery: 3,
      hits: [{ dmg: 54, box: [18, 20, 74, 50], level: 'ovh', stun: 18, bstun: 13, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
    },
    j_H: {
      name: 'Heel Stamp', air: true, startup: 9, active: 6, recovery: 6, landRecovery: 4,
      hits: [{ dmg: 80, box: [16, -20, 66, 55], level: 'ovh', stun: 22, bstun: 16, push: 34, hitstop: 12, spark: 'H', sfx: 'H' }],
    },
    attention: {
      name: 'Attention!', startup: 18, active: 2, recovery: 15,
      hits: [{ dmg: 56, box: [26, 100, 66, 64], level: 'ovh', stun: 19, bstun: 13, push: 28, hitstop: 12, spark: 'M', sfx: 'H' }],
      vel: [[4, 1.2], [18, 0]],
      cancel: { super: true },
    },
    correction: {
      // step-in baton crack: wall splat in the corner, knockdown anywhere else
      name: 'Correction', startup: 15, active: 3, recovery: 21,
      hits: [{ dmg: 90, box: [24, 78, 88, 62], effect: 'splat', wallSplat: true, launch: [3.5, 5], stun: 24, bstun: 18, push: 50, hitstop: 14, spark: 'H', sfx: 'H' }],
      hurt: [reach(12, 28, [10, 76, 90, 66])], vel: [[3, 4.2], [13, 0]],
      cancel: { super: true },
    },

    // ------------------------------------------------------------ specials
    whistle: (v) => {
      const ex = v === 'EX';
      return {
        name: 'Whistle Blast', type: ex ? 'ex' : 'special', startup: pick(v, [12, 12, 13, 11]), active: 2, recovery: pick(v, [20, 22, 24, 20]),
        oneProj: true,
        proj: {
          at: pick(v, [12, 12, 13, 11]), kind: 'whistle', x: 45, y: 112, vx: pick(v, [8, 8.5, 9, 9]), life: pick(v, [16, 22, 28, 30]),
          box: [-30, -60, 60, 120], hits: ex ? 2 : 1, every: 6, power: ex ? 3 : 2,
          hit: { dmg: pick(v, [45, 50, 55, 38]), stun: 18, bstun: 16, push: pick(v, [140, 150, 160, 80]), hitstop: 9, spark: 'M', sfx: 'M', effect: ex ? 'kd' : 'normal', launch: [6, 6] },
        },
      };
    },
    popquiz: (v) => {
      const ex = v === 'EX';
      const su = pick(v, [5, 6, 7, 4]);
      return {
        name: 'Pop Quiz', type: ex ? 'ex' : 'special', startup: su, active: pick(v, [6, 8, 10, 12]), recovery: 16,
        landCancel: true, landRecovery: pick(v, [10, 12, 14, 14]),
        invuln: v === 'H' ? { strike: [1, 7], throw: [1, 7] } : ex ? { full: [1, 9] } : { throw: [1, 4] },
        vel: [[su, pick(v, [1.2, 1.5, 1.8, 1.6]), pick(v, [9, 11, 13, 13.5])]],
        hits: [
          { dmg: pick(v, [85, 95, 105, 60]), frames: [su, su + 2], box: [12, 70, 60, 110], effect: 'launch', launch: [1.3, 11], juggle: 1, push: 10, hitstop: 13, spark: 'H', sfx: 'H', meter: 30 },
          ...(ex ? [{ dmg: 60, frames: [su + 6, su + 9], box: [6, 100, 60, 110], effect: 'launch', launch: [1.3, 12], juggle: 0, hitstop: 14, spark: 'H', sfx: 'H' }] : []),
        ],
        hurt: [reach(su, su + 14, [-10, 70, 62, 140])],
      };
    },
    demo: (v) => {
      const ex = v === 'EX';
      const end = pick(v, [15, 20, 25, 28]);
      return {
        name: 'Demonstration', type: ex ? 'ex' : 'special', startup: 4, active: end - 3, recovery: pick(v, [14, 16, 18, 14]),
        counter: { frames: [ex ? 1 : 4, end], into: ex ? 'demo_takeEX' : 'demo_take' },
        invuln: ex ? { throw: [1, 10] } : undefined,
      };
    },
    demo_take: {
      // catch the arm, crack the elbow, hip throw, put them on the floor (hard knockdown at his feet)
      name: 'Demonstration', type: 'throw', startup: 1, active: 1, recovery: 1,
      grab: { len: 50, toss: [1.5, 3], hold: 66, hkd: true },
      hits: [
        { dmg: 45, frames: [20, 20], spark: 'M', sfx: 'M', hitstop: 6, meter: 30 },
        { dmg: 65, frames: [38, 38], spark: 'H', sfx: 'H', hitstop: 12, meter: 40 },
      ],
    },
    demo_takeEX: {
      name: 'Demonstration', type: 'throw', startup: 1, active: 1, recovery: 1,
      grab: { len: 56, toss: [1.5, 3], hold: 66, hkd: true },
      hits: [
        { dmg: 50, frames: [20, 20], spark: 'M', sfx: 'M', hitstop: 6, meter: 20 },
        { dmg: 40, frames: [30, 30], spark: 'M', sfx: 'M', hitstop: 6, meter: 20 },
        { dmg: 70, frames: [44, 44], spark: 'H', sfx: 'H', hitstop: 14, meter: 20 },
      ],
    },
    dummy: (v) => {
      const ex = v === 'EX';
      if (ex) {
        // EX: the dummy drops on the opponent's head (overhead, knocks down)
        return {
          name: 'Dummy Drop', type: 'ex', startup: 12, active: 2, recovery: 18,
          proj: {
            at: 12, kind: 'dummyDrop', place: 'opp', y: 420, vy: -15, life: 34, box: [-30, -40, 60, 80], hits: 1, power: 3,
            hit: { dmg: 85, level: 'ovh', effect: 'kd', launch: [1, 6], stun: 24, bstun: 18, push: 20, hitstop: 14, spark: 'H', sfx: 'H' },
          },
        };
      }
      // the dummy lands in front: it eats one projectile, and while it drops it soaks one strike (armour)
      return {
        name: 'Dummy Drop', type: 'special', startup: 14, active: 2, recovery: pick(v, [14, 15, 16, 14]),
        armor: { frames: [1, 15], hits: 1 },
        proj: {
          at: 14, kind: 'dummy', place: 'dist', dist: pick(v, [80, 130, 180, 130]), y: 0.1, life: 300,
          box: [-24, 0, 48, 176], hits: 1, power: 1, harmless: true,
        },
      };
    },

    // ------------------------------------------------------------ supers
    orientation: {
      name: 'Orientation', type: 'super', cost: 1000, freeze: 34, startup: 8, active: 6, recovery: 32,
      invuln: { strike: [1, 10], throw: [1, 10] },
      vel: [[1, 8], [14, 0]],
      hits: [{ dmg: 30, box: [20, 60, 90, 90], stun: 40, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 92, hold: 90, hits: [[6, 24], [11, 24], [16, 24], [21, 24], [26, 24], [31, 24], [40, 32], [52, 34], [74, 80]] },
    },
    exam: {
      name: 'Final Exam', type: 'final', cost: 3000, freeze: 44, startup: 10, active: 6, recovery: 44,
      invuln: { full: [1, 14] },
      vel: [[1, 7], [16, 0]],
      hits: [{ dmg: 30, box: [15, 50, 90, 110], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 182, hold: 95, hits: [[30, 80], [64, 50], [76, 50], [112, 60], [154, 200]] },
    },
    nobody: {
      name: 'Nobody Passes', type: 'overtime', freeze: 44, startup: 10, active: 6, recovery: 40,
      invuln: { full: [1, 16] },
      hits: [{ dmg: 30, box: [10, 60, 100, 110], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 144, hold: 95, hits: [[24, 110], [100, 250]] },
    },
    ...universal({ throwDmg: 120, bthrowDmg: 130 }),
  },
  // presentation
  colors: ['#5a6270', '#2f3b52', '#4b4038', '#2e4a3a', '#6b6b6b', '#1f1f24', '#8a8f9a', '#5c2a2a'],
  lines: {
    intro: 'Elbows in.',
    win: ['Nobody passes.', 'Again.', 'Elbows in. Again.'],
    vs: { joe: 'You again.' },
  },
});
