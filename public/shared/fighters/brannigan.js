// Brannigan — the old boilerman, now the Landing's smith. Relentless steam boxer. docs/ROSTER.md
// Plays forward: a fast walk and dash, a jab that is +3 on block, a crouching body blow that is plus, an armoured
// body shot, the Boiler Rush to close distance (L is safe), and Pressure Valve to bank free EX specials
// (up to two) so the pressure never lets up.
import { defineFighter, pick } from '../movekit.js';
import { universal, reach } from './common.js';

export default defineFighter({
  id: 'brannigan', name: 'Brannigan', title: 'Steel Goes Up', hp: 1050, archetype: 'Rushdown boxer',
  walkF: 4.5, walkB: 3.3, dashF: { frames: 16, dist: 128 }, dashB: { frames: 22, dist: 96, invuln: 7 },
  jump: { pre: 4, vy: 14.8, vx: 4.5 }, width: 54, height: 178, crouchHeight: 104,
  normals: {
    stand: { L: 'st_L', M: 'st_M', H: 'st_H' },
    crouch: { L: 'cr_L', M: 'cr_M', H: 'cr_H' },
    air: { L: 'j_L', M: 'j_M', H: 'j_H' },
    command: [{ dir: 6, btn: 'M', id: 'overhand' }, { dir: 3, btn: 'H', id: 'steamcut' }, { dir: 4, btn: 'H', id: 'ironlung' }],
  },
  specials: [
    { id: 'rush', motion: '236', simple: 5 },
    { id: 'hike', motion: '623', simple: 6 },
    { id: 'wrench', motion: '214', simple: 4 },
    { id: 'valve', motion: '22', simple: 2 },
  ],
  supers: { art: 'rent', final: 'pressure', overtime: 'redline' },
  autoCombo: ['st_L', 'st_M', 'st_H', 'rush'],
  moves: {
    // ------------------------------------------------------------ normals: fast and plus
    st_L: {
      name: 'Jab', startup: 4, active: 2, recovery: 7,
      hits: [{ dmg: 26, box: [20, 124, 52, 20], stun: 13, bstun: 11, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 120, 58, 26])],
      cancel: { into: ['st_L', 'cr_L', 'st_M', 'cr_M'], special: true, super: true },
    },
    st_M: {
      name: 'Hook', startup: 6, active: 3, recovery: 13,
      hits: [{ dmg: 50, box: [20, 112, 60, 28], stun: 19, bstun: 15, push: 28, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(5, 14, [10, 108, 64, 32])], vel: [[2, 1.2], [8, 0]],
      cancel: { into: ['st_H', 'cr_H', 'steamcut', 'ironlung'], special: true, super: true },
    },
    st_H: {
      name: 'Straight Right', startup: 9, active: 3, recovery: 18,
      hits: [{ dmg: 82, box: [22, 108, 78, 30], stun: 22, bstun: 17, push: 40, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 22, [10, 104, 82, 34])], vel: [[3, 2.6], [11, 0]],
      cancel: { special: true, super: true },
    },
    cr_L: {
      name: 'Boot Toe', startup: 4, active: 2, recovery: 8, crouching: true,
      hits: [{ dmg: 24, box: [16, 4, 56, 24], level: 'low', stun: 12, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 2, 60, 28])],
      cancel: { into: ['cr_L', 'st_L', 'cr_M', 'st_M'], special: true, super: true },
    },
    cr_M: {
      name: 'Gut Punch', startup: 6, active: 3, recovery: 12, crouching: true,
      hits: [{ dmg: 46, box: [20, 58, 66, 34], stun: 18, bstun: 15, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(5, 14, [10, 56, 68, 38])],
      cancel: { into: ['st_H', 'cr_H', 'steamcut', 'ironlung'], special: true, super: true },
    },
    cr_H: {
      name: 'Stoker Sweep', startup: 9, active: 3, recovery: 24, crouching: true,
      hits: [{ dmg: 76, box: [24, 0, 92, 22], level: 'low', effect: 'kd', launch: [1.5, 4], bstun: 14, push: 30, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 26, [10, 0, 96, 26])],
      cancel: { special: true, super: true },
    },
    j_L: {
      name: 'Knee', air: true, startup: 5, active: 6, recovery: 5, landRecovery: 2,
      hits: [{ dmg: 32, box: [10, 10, 50, 45], level: 'ovh', stun: 14, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
    },
    j_M: {
      name: 'Hammer Fist', air: true, startup: 7, active: 5, recovery: 6, landRecovery: 3,
      hits: [{ dmg: 54, box: [15, 25, 62, 50], level: 'ovh', stun: 18, bstun: 13, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
    },
    j_H: {
      name: 'Double Axe', air: true, startup: 9, active: 5, recovery: 7, landRecovery: 4,
      hits: [{ dmg: 82, box: [12, -10, 70, 60], level: 'ovh', stun: 22, bstun: 16, push: 34, hitstop: 13, spark: 'H', sfx: 'H' }],
    },
    overhand: {
      name: 'Overhand', startup: 16, active: 2, recovery: 16,
      hits: [{ dmg: 56, box: [22, 100, 62, 64], level: 'ovh', stun: 19, bstun: 13, push: 28, hitstop: 12, spark: 'M', sfx: 'H' }],
      vel: [[3, 1.6], [16, 0]],
      cancel: { super: true },
    },
    steamcut: {
      name: 'Steam Uppercut', startup: 9, active: 4, recovery: 21,
      hits: [{ dmg: 68, box: [16, 60, 56, 86], effect: 'launch', launch: [1.2, 13.5], juggle: 2, bstun: 15, push: 10, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 20, [10, 60, 60, 96])],
      cancel: { special: true, super: true },
    },
    ironlung: {
      // armoured body shot: walks through one hit
      name: 'Iron Lung', startup: 13, active: 3, recovery: 18, armor: { frames: [1, 13], hits: 1 },
      hits: [{ dmg: 80, box: [22, 66, 74, 42], stun: 24, bstun: 16, push: 36, hitstop: 13, spark: 'H', sfx: 'H' }],
      hurt: [reach(12, 24, [10, 64, 78, 46])], vel: [[2, 1.8], [12, 0]],
      cancel: { special: true, super: true },
    },

    // ------------------------------------------------------------ specials
    rush: (v) => {
      const ex = v === 'EX';
      const su = pick(v, [11, 13, 16, 10]);
      const act = pick(v, [6, 8, 12, 12]);
      return {
        name: 'Boiler Rush', type: ex ? 'ex' : 'special', startup: su, active: act, recovery: pick(v, [14, 18, 22, 18]),
        vel: [[3, pick(v, [7, 9.5, 14, 13])], [su + act - pick(v, [3, 2, 1, 2]), 0]],
        armor: ex ? { frames: [1, su + 6], hits: 1 } : undefined,
        hits: ex ? [
          { dmg: 45, frames: [su, su + 4], box: [18, 98, 72, 40], stun: 20, bstun: 14, push: 6, hitstop: 8, spark: 'M', sfx: 'M', juggle: 0 },
          { dmg: 75, frames: [su + 6, su + act - 1], box: [18, 98, 76, 40], effect: 'crumple', wallSplat: true, bstun: 18, push: 46, hitstop: 15, spark: 'H', sfx: 'H' },
        ] : [
          { dmg: pick(v, [75, 85, 95, 0]), box: [18, 98, 72, 40], effect: v === 'H' ? 'kd' : 'normal', launch: [3.5, 5], stun: 22, bstun: 18, push: 50, hitstop: 13, spark: 'H', sfx: 'H' },
        ],
        hurt: [reach(su - 2, su + act + 6, [10, 94, 80, 46])],
      };
    },
    hike: (v) => {
      // a grounded uppercut that launches high ("it only ever goes up")
      const ex = v === 'EX';
      const su = pick(v, [4, 5, 6, 4]);
      return {
        name: 'Price Hike', type: ex ? 'ex' : 'special', startup: su, active: pick(v, [4, 5, 6, 9]), recovery: pick(v, [20, 22, 25, 24]),
        invuln: v === 'H' ? { strike: [1, 6], throw: [1, 6] } : ex ? { full: [1, 9] } : { throw: [1, 4] },
        vel: [[1, 1.4], [su + 2, 0]],
        hits: ex ? [
          { dmg: 55, frames: [su, su + 2], box: [14, 66, 58, 110], effect: 'launch', launch: [0.8, 10], juggle: 0, push: 6, hitstop: 10, spark: 'H', sfx: 'H' },
          { dmg: 65, frames: [su + 5, su + 8], box: [6, 90, 70, 130], effect: 'launch', launch: [1.2, 15.5], juggle: 1, push: 10, hitstop: 15, spark: 'X', sfx: 'H' },
        ] : [
          { dmg: pick(v, [80, 90, 105, 0]), box: [14, 66, 58, 110], effect: 'launch', launch: [1.2, pick(v, [13, 14, 15, 0])], juggle: 1, bstun: 14, push: 10, hitstop: 13, spark: 'H', sfx: 'H', meter: 30 },
        ],
        hurt: [reach(su, su + 14, [0, 70, 60, 120])],
      };
    },
    wrench: (v) => {
      // double-fisted overhead "wrench" swing: overhead, ground bounce
      const ex = v === 'EX';
      const su = pick(v, [20, 22, 24, 18]);
      return {
        name: 'Wrench Swing', type: ex ? 'ex' : 'special', startup: su, active: 3, recovery: pick(v, [18, 20, 22, 18]),
        vel: [[4, pick(v, [2.2, 3.2, 4.2, 3.6])], [su, 0]],
        armor: ex ? { frames: [1, su - 1], hits: 1 } : undefined,
        hits: [{ dmg: pick(v, [80, 88, 96, 110]), box: [20, 60, 70, 110], level: 'ovh', effect: 'bounce', stun: 22, bstun: 16, push: 30, hitstop: 15, spark: 'H', sfx: 'H' }],
        hurt: [reach(su - 4, su + 10, [10, 60, 76, 110])],
      };
    },
    valve: (v) => {
      // vents steam: banks a free EX for the next special (holds two)
      const ex = v === 'EX';
      return {
        name: 'Pressure Valve', type: ex ? 'ex' : 'special', startup: 10, active: pick(v, [14, 16, 18, 16]), recovery: pick(v, [10, 12, 12, 10]),
        armor: ex ? { frames: [1, 26], hits: 1 } : undefined,
        fx: { at: 12, kind: 'addvar', name: 'freeEX', value: ex ? 2 : 1, max: 2 },
        hits: v === 'H' || ex ? [{ dmg: 35, frames: [12, 15], box: [-10, 20, 90, 150], effect: 'kd', launch: [4, 4], bstun: 12, push: 60, hitstop: 8, spark: 'M', sfx: 'M' }] : [],
      };
    },

    // ------------------------------------------------------------ supers
    rent: {
      name: 'Rent Goes Up', type: 'super', cost: 1000, freeze: 34, startup: 6, active: 6, recovery: 34,
      invuln: { strike: [1, 9], throw: [1, 9] },
      vel: [[1, 7], [12, 0]],
      hits: [{ dmg: 30, box: [15, 60, 85, 90], stun: 40, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 98, hold: 80, hits: [[10, 35], [20, 35], [32, 45], [48, 50], [70, 125]] },
    },
    pressure: {
      // command-grab Final Notice: the bear hug into an exploding boiler
      name: 'Full Pressure', type: 'final', cost: 3000, freeze: 44, startup: 6, active: 4, recovery: 46,
      invuln: { full: [1, 12] },
      grab: { range: 100, len: 1, techable: false },
      cine: { len: 186, hold: 62, hits: [[40, 90], [84, 90], [150, 280]] },
    },
    redline: {
      name: 'Red Line', type: 'overtime', freeze: 44, startup: 8, active: 8, recovery: 40,
      invuln: { full: [1, 16] },
      hits: [{ dmg: 30, box: [-20, 0, 150, 190], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 140, hold: 90, hits: [[50, 130], [104, 230]] },
    },
    ...universal({ throwDmg: 125, bthrowDmg: 130 }),
  },
  // presentation
  colors: ['#6a4a32', '#33475b', '#5b2626', '#3e5130', '#2a2a2a', '#7a6a50', '#4a3a5e', '#8c8c8c'],
  lines: {
    intro: "Steel's like rent.",
    win: ['It only ever goes up.', 'Mind the pipes.', "Steel's like rent."],
  },
});
