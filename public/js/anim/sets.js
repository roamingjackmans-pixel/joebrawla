// Animation sets: how each action and move looks. BASE covers what every fighter shares; each fighter adds
// its moves (keyed to frame data: 's' = first active frame, 'a' = last active, 'e' = end) and a style.
// A fighter's set may override any state.
import { POSES } from './poses.js';

export const BASE = {
  style: {},
  states: {
    idle: { keys: [[0, 'stance']], loop: true, clip: 'Idle_Loop', speed: 0.9 },
    guard: { keys: [[0, 'guardHigh']], blend: 4 },
    walkF: { clip: 'guard_walk_fwd', loop: true, speed: 1.15, over: 'guardArmsWalk', keys: [[0, { clip: 'guard_walk_fwd' }]] },
    walkB: { clip: 'guard_walk_back', loop: true, speed: 1.0, over: 'guardArmsWalk', keys: [[0, { clip: 'guard_walk_back' }]] },
    crouch: { keys: [[0, 'crouch']], blend: 4 },
    prejump: { keys: [[0, 'stance'], [3, 'prejump', 'out']], blend: 2 },
    jumpU: { keys: [[0, 'jumpUp']], blend: 3 },
    jumpF: { keys: [[0, 'jumpUp'], [10, { extends: 'jumpUp', tilt: -180 }], [24, { extends: 'jumpUp', tilt: -360 }]], blend: 3 },
    jumpB: { keys: [[0, 'jumpUp'], [10, { extends: 'jumpUp', tilt: 180 }], [24, { extends: 'jumpUp', tilt: 360 }]], blend: 3 },
    land: { keys: [[0, 'land'], [3, 'stance']], blend: 2 },
    dash: { keys: [[0, { extends: 'stance', sp: [24, 10, 0], pel: [0.05, -0.12, 0], fr: [-0.45, -0.80, -0.1, 1], fl: [0.45, -0.85, 0.1, 1] }], [12, 'stance']], blend: 2 },
    bdash: { keys: [[0, { clip: 'backstep', cf: 0.1 }], [10, { clip: 'backstep', cf: 0.6 }], [20, 'stance']], blend: 2 },
    dashEnd: { keys: [[0, 'stance']] },
    block: { keys: [[0, { extends: 'guardHigh', pel: [-0.08, -0.12, 0], sp: [20, 6, 0] }], [6, 'guardHigh']], blend: 1 },
    cblock: { keys: [[0, { extends: 'crouchGuard', sp: [30, 6, 0] }], [6, 'crouchGuard']], blend: 1 },
    hit: { keys: [[0, 'hitMid'], [4, { clip: 'Hit_Chest', cf: 0.6, fr: [-0.3, -0.9, -0.14, 0.8], fl: [0.24, -0.9, 0.1, 0.8] }], [16, 'stance']], blend: 1 },
    chit: { keys: [[0, 'hitCrouch'], [12, 'crouch']], blend: 1 },
    air: { keys: [[0, { clip: 'Hit_Knockback', cf: 0.1 }], [10, { clip: 'Hit_Knockback', cf: 0.35 }], [40, { clip: 'Hit_Knockback', cf: 0.5 }]], blend: 2 },
    crumple: { keys: [[0, { clip: 'stagger', cf: 0.05 }], [26, { clip: 'stagger', cf: 0.6 }], [50, { clip: 'knockdown', cf: 0.5 }]], blend: 3 },
    splat: { keys: [[0, 'splat']], blend: 1 },
    down: { keys: [[0, { clip: 'knockdown', cf: 0.55 }], [10, 'lying']], blend: 3 },
    wake: { keys: [[0, { clip: 'getup', cf: 0.35 }], [16, { clip: 'getup', cf: 0.95 }], [18, 'stance']], blend: 3 },
    ko: { keys: [[0, { clip: 'Hit_Knockback', cf: 0.15 }], [30, { clip: 'Hit_Knockback', cf: 0.5 }]], blend: 2 },
    koDown: { keys: [[0, { clip: 'knockdown', cf: 0.6 }], [14, 'lying']], blend: 4 },
    thrown: { keys: [[0, { clip: 'grabbed', cf: 0.1 }], [40, { clip: 'grabbed', cf: 0.9 }]], blend: 2 },
    tech: { keys: [[0, { clip: 'backstep', cf: 0.2 }], [18, 'stance']], blend: 2 },
    cine: { keys: [[0, 'stance']] },
    cined: { keys: [[0, 'hitHigh'], [8, 'hitMid'], [16, 'hitHigh'], [24, 'hitMid']], blend: 2 },
    intro: { keys: [[0, { clip: 'Idle_FoldArms_Loop', cf: 0.2 }]], loop: true, clip: 'Idle_FoldArms_Loop' },
    win: { keys: [[0, { clip: 'level_up', cf: 0 }], [90, { clip: 'level_up', cf: 0.98 }]], blend: 6 },
    lose: { keys: [[0, { clip: 'Idle_No_Loop', cf: 0 }]], loop: true, clip: 'Idle_No_Loop', blend: 6 },
    timeout: { keys: [[0, 'stance']] },
    taunt: { keys: [[0, { clip: 'Yes', cf: 0 }], [70, { clip: 'Yes', cf: 1 }]] },
  },
  moves: {
    throw: { keys: [[0, 'stance'], ['s', 'grabReach', 'out'], [12, { clip: 'Melee_Hook', cf: 0.3 }], [26, { clip: 'OverhandThrow', cf: 0.35 }], [34, { clip: 'OverhandThrow', cf: 0.6 }], [44, 'stance']] },
    bthrow: { keys: [[0, 'stance'], ['s', 'grabReach', 'out'], [14, { extends: 'grabReach', yaw: 90 }], [30, { clip: 'OverhandThrow', cf: 0.5, yaw: 180 }], [48, 'stance']] },
    breaker: { keys: [[0, 'stance'], [10, { extends: 'hayWind', pel: [-0.05, -0.12, 0] }], ['s', 'hayOut', 'in'], ['a+8', 'hayOut'], ['e', 'stance']] },
    breakerRev: { keys: [[0, 'guardHigh'], ['s', 'castOut', 'in'], ['e', 'stance']] },
    taunt: { keys: [[0, { clip: 'Yes', cf: 0 }], [70, { clip: 'Yes', cf: 1 }]] },
  },
};

// helper poses used by sets (registered into POSES at load)
export const EXTRA_POSES = {
  guardArmsWalk: { hr: [0.30, 0.42, 0.30, 0.9], hl: [0.52, 0.42, 0.04, 0.9], pr: [-0.3, -1, -0.6], pl: [-0.3, -1, 0.6], sp: [8, 14, 0], yaw: -20 },
};

Object.assign(POSES, EXTRA_POSES);

export const SETS = {
  joe: {
    style: {},
    moves: {
      st_L: { keys: [[0, 'stance'], [2, 'jabWind'], ['s', 'jabOut', 'in'], ['a+1', 'jabOut'], ['e', 'stance', 'out']] },
      st_M: { keys: [[0, 'stance'], [4, 'crossWind'], ['s', 'crossOut', 'in'], ['a+2', 'crossOut'], ['e', 'stance', 'out']] },
      st_H: { keys: [[0, 'stance'], [6, 'hayWind', 'out'], ['s', 'hayOut', 'in'], ['a+4', 'hayOut'], ['e', 'stance', 'io']] },
      cr_L: { keys: [[0, 'crouch'], [2, { extends: 'crouch', fr: [0.4, -0.7, 0, 1] }], ['s', 'kickLowCrouch', 'in'], ['a+1', 'kickLowCrouch'], ['e', 'crouch']] },
      cr_M: { keys: [[0, 'crouch'], [4, { extends: 'crouch', fr: [0.35, -0.6, 0, 1] }], ['s', { extends: 'kickLowCrouch', fr: [0.95, -0.84, 0.02, 1], yaw: 25 }, 'in'], ['a+2', { extends: 'kickLowCrouch', fr: [0.95, -0.84, 0.02, 1], yaw: 25 }], ['e', 'crouch']] },
      cr_H: { keys: [[0, 'crouch'], [5, { extends: 'sweep', yaw: 10, fr: [0.5, -0.8, 0.3, 1] }], ['s', 'sweep', 'in'], ['a+6', { extends: 'sweep', yaw: 110 }], ['e', 'crouch']] },
      j_L: { keys: [[0, 'jumpUp'], ['s', 'airKnee', 'out'], ['a', 'airKnee'], ['e', 'jumpUp']] },
      j_M: { keys: [[0, 'jumpUp'], [4, { extends: 'airChop', hr: [0.1, 0.8, 0.1, 1] }], ['s', 'airChop', 'in'], ['a', 'airChop'], ['e', 'jumpUp']] },
      j_H: { keys: [[0, 'jumpUp'], [5, { extends: 'airKnee', fr: [0.3, 0.1, 0, 1] }], ['s', 'airKick', 'in'], ['a', 'airKick'], ['e', 'jumpUp']] },
      doorknocker: { keys: [[0, 'stance'], [10, 'hammerUp', 'out'], ['s', 'hammerDown', 'in'], ['a+5', 'hammerDown'], ['e', 'stance']] },
      launcher: { keys: [[0, 'stance'], [4, { extends: 'stance', pel: [0, -0.15, 0] }], ['s', 'kneeUp', 'in'], ['a+3', 'kneeUp'], ['e', 'stance']] },
      flare: { keys: [[0, 'stance'], [6, 'castWind', 'out'], ['s', 'castOut', 'in'], ['s+8', 'castOut'], ['e', 'stance']] },
      climber: { keys: [[0, 'stance'], [2, 'uppercutLow', 'out'], ['s', 'uppercutHigh', 'in'], ['a', { extends: 'uppercutHigh', fr: [0.1, -0.7, 0, 1] }], ['e', 'stance']] },
      latefee: { keys: [[0, 'stance'], [6, 'kickChamber'], ['s', { extends: 'kickHigh', spin: 0 }, 'in'], ['a', { extends: 'kickHigh', spin: -360 * 1 }], ['e', 'stance']], spinPerHit: true },
      thermos: { keys: [[0, 'stance'], [8, { clip: 'Consume', cf: 0.15 }], [34, { clip: 'Consume', cf: 0.7 }], ['e', 'stance']] },
      surge: { keys: [[0, 'stance'], [4, 'rushPunch'], ['s', 'crossOut'], ['e', 'stance']] },
      mainbreaker: { keys: [[0, 'stance'], [6, 'grabReach'], ['e', 'stance']] },
      generator: { keys: [[0, 'stance'], [8, 'castWind'], ['e', 'stance']] },
    },
    cine: {
      surge: [[0, 'jabOut'], [4, 'crossOut'], [8, 'jabOut'], [12, 'crossOut'], [16, 'jabOut'], [20, 'crossOut'], [24, 'jabOut'], [28, 'crossOut'], [34, 'hayWind'], [42, 'hayOut'], [52, 'uppercutLow'], [62, 'uppercutHigh'], [78, 'stance']],
      mainbreaker: [[0, 'grabReach'], [20, 'hayWind'], [34, 'hayOut'], [60, 'hammerUp'], [86, 'hammerDown'], [120, 'castWind'], [140, 'castOut'], [170, 'stance']],
      generator: [[0, 'castWind'], [30, 'hammerUp'], [50, 'hammerDown'], [90, 'castWind'], [104, 'castOut'], [150, 'stance']],
    },
  },
};

/** merge BASE with a fighter's set */
export function setFor(id, clips) {
  const own = SETS[id] || SETS.joe;
  return {
    style: { ...BASE.style, ...(own.style || {}) },
    states: { ...BASE.states, ...(own.states || {}) },
    moves: { ...BASE.moves, ...(own.moves || {}) },
    cine: own.cine || {},
    clips,
    yScale: 1,
  };
}
