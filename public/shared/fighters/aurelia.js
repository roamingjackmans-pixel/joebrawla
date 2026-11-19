// Saint Aurelia — PLACEHOLDER (a copy of Joe's moves until this fighter's own moveset is written). docs/ROSTER.md
import { defineFighter, pick } from '../movekit.js';
import { universal, reach } from './common.js';

export default defineFighter({
  id: 'aurelia', name: 'Saint Aurelia', title: 'The Unthawed', hp: 900, placeholder: true, archetype: 'All-rounder',
  walkF: 4.6, walkB: 3.7, dashF: { frames: 18, dist: 125 }, dashB: { frames: 22, dist: 105, invuln: 7 },
  jump: { pre: 4, vy: 15.2, vx: 4.7 }, width: 48, height: 172, crouchHeight: 106,
  normals: {
    stand: { L: 'st_L', M: 'st_M', H: 'st_H' },
    crouch: { L: 'cr_L', M: 'cr_M', H: 'cr_H' },
    air: { L: 'j_L', M: 'j_M', H: 'j_H' },
    command: [{ dir: 6, btn: 'M', id: 'doorknocker' }, { dir: 3, btn: 'H', id: 'launcher' }],
  },
  specials: [
    { id: 'climber', motion: '623', simple: 6 },
    { id: 'flare', motion: '236', simple: 5 },
    { id: 'latefee', motion: '214', simple: 4 },
    { id: 'thermos', motion: '22', simple: 2 },
  ],
  supers: { art: 'surge', final: 'mainbreaker', overtime: 'generator' },
  autoCombo: ['st_L', 'st_M', 'st_H', 'flare'],
  moves: {
    st_L: {
      name: 'Jab', startup: 4, active: 2, recovery: 7,
      hits: [{ dmg: 30, box: [20, 122, 56, 22], stun: 13, bstun: 10, push: 22, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 118, 60, 26])],
      cancel: { into: ['st_L', 'cr_L', 'st_M', 'cr_M'], special: true, super: true },
    },
    st_M: {
      name: 'Straight', startup: 7, active: 3, recovery: 13,
      hits: [{ dmg: 55, box: [22, 112, 68, 26], stun: 19, bstun: 14, push: 32, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(6, 16, [10, 108, 72, 30])], vel: [[3, 1.2], [9, 0]],
      cancel: { into: ['st_H', 'cr_H', 'launcher'], special: true, super: true },
    },
    st_H: {
      name: 'Haymaker', startup: 10, active: 4, recovery: 20,
      hits: [{ dmg: 85, box: [22, 100, 86, 36], stun: 23, bstun: 17, push: 44, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 24, [10, 96, 92, 40])], vel: [[4, 2], [12, 0]],
      cancel: { special: true, super: true },
    },
    cr_L: {
      name: 'Shin Kick', startup: 4, active: 2, recovery: 8, crouching: true,
      hits: [{ dmg: 25, box: [18, 4, 62, 24], level: 'low', stun: 12, bstun: 9, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 2, 66, 28])],
      cancel: { into: ['cr_L', 'st_L', 'cr_M', 'st_M'], special: true, super: true },
    },
    cr_M: {
      name: 'Low Poke', startup: 7, active: 3, recovery: 14, crouching: true,
      hits: [{ dmg: 50, box: [22, 4, 80, 24], level: 'low', stun: 18, bstun: 13, push: 30, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(6, 16, [10, 2, 84, 28])],
      cancel: { into: ['st_H', 'cr_H'], special: true, super: true },
    },
    cr_H: {
      name: 'Sweep', startup: 9, active: 3, recovery: 24, crouching: true,
      hits: [{ dmg: 80, box: [28, 0, 100, 20], level: 'low', effect: 'kd', launch: [1.5, 4], push: 30, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 26, [10, 0, 104, 24])],
      cancel: { special: true, super: true },
    },
    j_L: {
      name: 'Air Knee', air: true, startup: 5, active: 7, recovery: 4, landRecovery: 2,
      hits: [{ dmg: 35, box: [10, 10, 52, 45], level: 'ovh', stun: 14, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
    },
    j_M: {
      name: 'Air Chop', air: true, startup: 7, active: 5, recovery: 6, landRecovery: 3,
      hits: [{ dmg: 55, box: [15, 30, 64, 46], level: 'ovh', stun: 18, bstun: 13, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
    },
    j_H: {
      name: 'Diving Kick', air: true, startup: 9, active: 6, recovery: 6, landRecovery: 4,
      hits: [{ dmg: 80, box: [10, -15, 70, 55], level: 'ovh', stun: 22, bstun: 16, push: 34, hitstop: 12, spark: 'H', sfx: 'H' }],
    },
    doorknocker: {
      name: 'Doorknocker', startup: 18, active: 2, recovery: 16,
      hits: [{ dmg: 60, box: [22, 100, 62, 60], level: 'ovh', stun: 18, bstun: 12, push: 30, hitstop: 12, spark: 'M', sfx: 'H' }],
      vel: [[4, 1.5], [18, 0]],
      cancel: { super: true },
    },
    launcher: {
      name: 'Stairwell Launcher', startup: 9, active: 4, recovery: 22,
      hits: [{ dmg: 70, box: [18, 60, 56, 80], effect: 'launch', launch: [1.2, 13.5], juggle: 2, push: 10, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 20, [10, 60, 60, 90])],
      cancel: { special: true, super: true },
    },
    flare: (v) => ({
      name: 'Flashlight Flare', type: v === 'EX' ? 'ex' : 'special', startup: pick(v, [13, 12, 11, 11]), active: 2, recovery: pick(v, [31, 31, 31, 28]),
      oneProj: true,
      proj: {
        at: pick(v, [13, 12, 11, 11]), kind: 'flare', x: 62, y: 118, vx: pick(v, [5.2, 7.2, 9.5, 8.5]), life: 150,
        box: [-28, -26, 56, 52], hits: v === 'EX' ? 2 : 1, every: 7, power: v === 'EX' ? 2 : 1,
        hit: { dmg: pick(v, [65, 70, 75, 55]), stun: 20, bstun: 16, push: 40, hitstop: 10, spark: 'flare', sfx: 'flare', effect: v === 'EX' ? 'kd' : 'normal', launch: [2.5, 6] },
      },
    }),
    climber: (v) => ({
      name: 'Stair Climber', type: v === 'EX' ? 'ex' : 'special', startup: pick(v, [3, 4, 5, 3]), active: pick(v, [8, 10, 12, 14]), recovery: 16,
      landCancel: true, landRecovery: pick(v, [10, 12, 15, 16]),
      invuln: v === 'H' || v === 'EX' ? { strike: [1, pick(v, [0, 0, 6, 7])], throw: [1, 8] } : { throw: [1, 4] },
      vel: [[pick(v, [3, 4, 5, 3]), pick(v, [1.4, 1.8, 2.2, 2.0]), pick(v, [10, 12.5, 14.5, 15])]],
      hits: [
        { dmg: pick(v, [75, 90, 105, 70]), frames: [pick(v, [3, 4, 5, 3]), pick(v, [4, 5, 6, 4])], box: [10, 60, 58, 100], effect: 'launch', launch: [1.4, 11], juggle: 1, push: 10, hitstop: 13, spark: 'H', sfx: 'H', meter: 30 },
        ...(v === 'EX' ? [{ dmg: 60, frames: [9, 12], box: [5, 100, 60, 100], effect: 'launch', launch: [1.4, 12], juggle: 0, hitstop: 14, spark: 'flare', sfx: 'H' }] : []),
      ],
      hurt: [reach(3, 20, [-10, 60, 60, 140])],
    }),
    latefee: (v) => ({
      name: 'Late Fee', type: v === 'EX' ? 'ex' : 'special', startup: pick(v, [11, 12, 13, 9]), active: pick(v, [8, 16, 24, 24]), recovery: 16,
      vel: [[1, 0.6], [pick(v, [11, 12, 13, 9]), pick(v, [3.2, 4, 4.8, 5]), 0], [pick(v, [19, 28, 37, 33]), 0]],
      invuln: v === 'EX' ? { proj: [1, 30] } : undefined,
      hits: Array.from({ length: pick(v, [1, 2, 3, 3]) }, (_, k) => {
        const s = pick(v, [11, 12, 13, 9]) + k * 8;
        const last = k === pick(v, [1, 2, 3, 3]) - 1;
        return { dmg: pick(v, [70, 45, 38, 45]), frames: [s, s + 3], box: [10, 95, 80, 40], effect: last ? 'kd' : 'normal', launch: [3, 5], stun: 20, bstun: 12, push: last ? 40 : 6, hitstop: 9, spark: 'M', sfx: 'M', juggle: 1 };
      }),
      hurt: [reach(8, 40, [-30, 90, 120, 50])],
    }),
    thermos: (v) => ({
      name: 'Thermos Break', type: v === 'EX' ? 'ex' : 'special', startup: 10, active: 30, recovery: 18,
      fx: [{ at: 32, kind: 'heal', pct: v === 'EX' ? 6 : 3 }, { at: 34, kind: 'meter', n: v === 'EX' ? 0 : 120 }],
    }),
    surge: {
      name: 'Power Surge', type: 'super', cost: 1000, freeze: 34, startup: 8, active: 10, recovery: 30,
      invuln: { strike: [1, 10], throw: [1, 10] },
      vel: [[1, 9], [18, 0]],
      hits: [{ dmg: 40, box: [15, 50, 80, 100], effect: 'normal', stun: 40, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 78, hold: 85, hits: [[8, 36], [16, 36], [24, 36], [32, 36], [42, 40], [62, 96]] },
    },
    mainbreaker: {
      name: 'MAIN BREAKER', type: 'final', cost: 3000, freeze: 44, startup: 10, active: 6, recovery: 40,
      invuln: { full: [1, 14] },
      vel: [[1, 7], [16, 0]],
      hits: [{ dmg: 30, box: [15, 40, 85, 120], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 170, hold: 95, hits: [[34, 110], [86, 140], [140, 190]] },
    },
    generator: {
      name: 'Backup Generator', type: 'overtime', freeze: 44, startup: 12, active: 6, recovery: 40,
      invuln: { full: [1, 16] },
      hits: [{ dmg: 30, box: [10, 30, 100, 140], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 150, hold: 100, hits: [[50, 120], [104, 260]] },
    },
    ...universal({}),
  },
  // presentation
  colors: ['#4a4f58', '#6b2a2a', '#26445e', '#3d5a2c', '#5a4a7a', '#8a6d2a', '#1d1d1f', '#cfcfcf'],
  lines: {
    intro: 'Has anyone seen the breaker box?',
    win: ['Lights are back on. Probably.', 'I just live here.', 'Forty flights. Every day.'],
  },
});
