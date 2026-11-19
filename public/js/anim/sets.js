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

import { SETS } from './sets/index.js';

/** merge BASE with a fighter's set */
export function setFor(id, clips) {
  const own = SETS[id] || {};
  return {
    style: { ...BASE.style, ...(own.style || {}) },
    states: { ...BASE.states, ...(own.states || {}) },
    moves: { ...BASE.moves, ...(own.moves || {}) },
    cine: own.cine || {},
    clips,
    yScale: 1,
  };
}
