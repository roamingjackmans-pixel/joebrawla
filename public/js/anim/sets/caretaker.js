// The Caretaker's animation set. His own boss clips (Caretaker_*) carry the shovel and lantern, so almost every
// move is a retimed clip segment ('ct' = clip seconds), with leg IK for crouches and jumps and lantern-hand IK
// for the light attacks. Keys: [frame | 's' first active | 'a' last active | 'e' end (+/-n), pose, ease].
const C = (clip, ct, extra = {}) => ({ clip: 'Caretaker_' + clip, ct, ...extra });

// leg IK shapes (limb lengths from the hip, character space: x forward, y up, z left)
const CROUCH_LEGS = { pel: [0, -0.3, 0], fr: [-0.3, -0.6, -0.12, 1], fl: [0.3, -0.62, 0.12, 1], kr: [1, 0.1, -0.2], kl: [1, 0.1, 0.2] };
const TUCK = { fr: [0.05, -0.56, -0.1, 1], fl: [0.3, -0.62, 0.1, 1], kr: [1, 0.3, 0], kl: [1, 0.2, 0] };
const SQUAT = { pel: [0, -0.14, 0], fr: [-0.14, -0.78, -0.1, 1], fl: [0.12, -0.78, 0.08, 1], kr: [1, 0.1, -0.2], kl: [1, 0.1, 0.2] };
const HALF_LEGS = { pel: [0, -0.16, 0], fr: [-0.22, -0.76, -0.12, 1], fl: [0.24, -0.76, 0.12, 1], kr: [1, 0.1, -0.2], kl: [1, 0.1, 0.2] };
const LUNGE = { pel: [0.12, -0.04, 0], fr: [-0.32, -0.86, -0.08, 1], fl: [0.2, -0.88, 0.08, 1], kr: [1, 0.1, -0.2], kl: [1, 0.1, 0.2] };
const crouched = (pose, sp = [18, 0, 0]) => ({ ...pose, ...CROUCH_LEGS, sp, hd: [-14, 0, 0] });
const half = (pose, sp = [10, 0, 0]) => ({ ...pose, ...HALF_LEGS, sp });
const air = (pose, sp = [8, 0, 0]) => ({ ...pose, ...TUCK, sp });

// walking backwards: the walk clip played in reverse (keyed, so it can run backwards), 40 cycles
const WALK_LEN = 1.6, WALK_F = 84;
const walkBack = [];
for (let k = 0; k < 40; k++) { walkBack.push([k * WALK_F, C('Walk', WALK_LEN - 0.01), 'lin'], [(k + 1) * WALK_F - 0.01, C('Walk', 0.0), 'lin']); }

export default {
  look: { tint1: ['Caretaker_Foliage'] },
  poses: {
    caretakerStance: C('Idle', 0.3),
    caretakerCrouch: { ...crouched(C('Idle', 0.3), [20, 0, 0]), hr: [0.08, -0.8, -0.22, 1], pr: [-0.6, -0.3, -1] },
    caretakerGuard: { ...C('GraveCall', 0.36), sp: [-6, 0, 0], hd: [6, 0, 0] },
    caretakerCrouchGuard: crouched(C('GraveCall', 0.36), [10, 0, 0]),
    caretakerJump: air(C('Idle', 0.3)),
    // lantern jab (left hand)
    caretakerJabWind: { ...C('Idle', 0.3), sp: [4, 12, 0], hl: [0.2, -0.35, 0.38, 1], pl: [-0.4, -1, 0.4] },
    caretakerJab: { ...C('Idle', 0.3), sp: [10, -22, 0], hd: [6, 10, 0], hl: [0.98, -0.12, 0.02, 1], pl: [-0.3, -0.6, 1] },
    // lantern bonk (overhead)
    caretakerBonkUp: { ...C('LanternToss', 0.5), sp: [-10, 10, 0], hl: [-0.05, 0.9, 0.2, 1], pl: [-1, 0.3, 0.4] },
    caretakerBonkDown: { ...C('LanternToss', 0.7), sp: [22, -10, 0], hd: [-6, 0, 0], hl: [0.9, 0.08, 0.05, 1], pl: [-0.3, 0.6, 1] },
    caretakerBonkThrough: { ...C('LanternToss', 0.72), sp: [28, -10, 0], hd: [-10, 0, 0], hl: [0.8, -0.35, 0.05, 1], pl: [-0.3, 0.6, 1] },
    caretakerPoke: { ...C('Plunge', 0.28), sp: [6, 0, 0], hr: [0.42, -0.08, 0.06, 1], pr: [-0.3, -1, -0.5] },
    // the boot (2L)
    caretakerBoot: { ...crouched(C('Idle', 0.3), [10, 0, -6]), fr: [0.62, -0.72, -0.04, 1], kr: [0.4, 1, 0] },
  },
  states: {
    idle: { keys: [[0, 'caretakerStance']], loop: true, clip: 'Caretaker_Idle', speed: 1 },
    guard: { keys: [[0, 'caretakerGuard']], blend: 4 },
    walkF: { clip: 'Caretaker_Walk', loop: true, speed: 1.25, keys: [[0, C('Walk', 0)]], blend: 6 },
    walkB: { keys: walkBack, blend: 6 },
    crouch: { keys: [[0, { ...C('Idle', 0.3), ...SQUAT }], [4, 'caretakerCrouch']], blend: 3 },
    prejump: { keys: [[0, 'caretakerStance'], [3, { ...C('Idle', 0.3), ...SQUAT, pel: [0, -0.2, 0], sp: [16, 0, 0] }, 'out']], blend: 2 },
    jumpU: { keys: [[0, air(C('Idle', 0.3), [4, 0, 0])], [14, 'caretakerJump'], [30, air(C('Idle', 0.3), [12, 0, 0])]], blend: 3 },
    jumpF: { keys: [[0, air(C('Idle', 0.3), [4, 0, 0])], [12, { ...air(C('Walk', 0.4), [18, 0, 0]), tilt: -12 }], [30, { ...air(C('Idle', 0.3), [10, 0, 0]), tilt: -4 }]], blend: 3 },
    jumpB: { keys: [[0, air(C('Idle', 0.3), [4, 0, 0])], [12, { ...air(C('Idle', 0.3), [-6, 0, 0]), tilt: 10 }], [30, air(C('Idle', 0.3), [6, 0, 0])]], blend: 3 },
    land: { keys: [[0, { ...C('Idle', 0.3), ...SQUAT, pel: [0, -0.2, 0], sp: [18, 0, 0] }], [5, 'caretakerStance']], blend: 2 },
    dash: { keys: [[0, { ...C('Walk', 0.2), sp: [20, 0, 0], pel: [0.06, -0.06, 0] }], [12, { ...C('Walk', 0.9), sp: [14, 0, 0] }], [24, 'caretakerStance']], blend: 3 },
    bdash: { keys: [[0, { ...C('Stagger', 0.1), sp: [-8, 0, 0] }], [12, { ...C('Stagger', 0.2), ...SQUAT }], [26, 'caretakerStance']], blend: 2 },
    dashEnd: { keys: [[0, 'caretakerStance']] },
    block: { keys: [[0, { ...C('GraveCall', 0.36), sp: [-14, 0, 0], pel: [-0.06, 0, 0], hd: [14, 0, 0] }], [6, 'caretakerGuard']], blend: 1 },
    cblock: { keys: [[0, crouched(C('GraveCall', 0.36), [2, 0, 0])], [6, 'caretakerCrouchGuard']], blend: 1 },
    hit: { keys: [[0, C('Stagger', 0.06)], [4, C('Stagger', 0.18)], [12, C('Stagger', 0.42)], [22, 'caretakerStance']], blend: 1 },
    chit: { keys: [[0, { ...crouched(C('Stagger', 0.18), [-6, 0, 8]), hd: [-26, 0, 8] }], [12, 'caretakerCrouch']], blend: 1 },
    crumple: { keys: [[0, C('Stagger', 0.1)], [20, C('Stagger', 0.4)], [34, C('Death', 0.6)], [50, C('Death', 1.6)]], blend: 3 },
    koDown: { keys: [[0, C('Death', 0.5)], [30, C('Death', 1.5)], [70, C('Death', 2.95)]], blend: 5 },
    intro: { keys: [[0, 'caretakerStance'], [24, C('GraveCall', 0.1)], [44, C('GraveCall', 0.34)], [70, C('GraveCall', 0.7)], [110, C('GraveCall', 1.2)], [150, C('GraveCall', 1.75)]], blend: 6 },
    win: { keys: [[0, 'caretakerStance'], [20, C('GraveCall', 0.16)], [36, C('GraveCall', 0.34)], [70, C('GraveCall', 0.9)], [120, C('GraveCall', 1.6)], [160, C('GraveCall', 1.76)]], blend: 6 },
    lose: { keys: [[0, C('Stagger', 0.3)], [30, { ...C('Death', 0.5), hd: [20, 0, 0] }]], blend: 8 },
    timeout: { keys: [[0, 'caretakerStance']] },
    taunt: { keys: [[0, 'caretakerStance'], [12, C('GraveCall', 0.6)], [40, C('GraveCall', 1.6)], [56, C('GraveCall', 1.76)], [70, 'caretakerStance']] },
  },
  moves: {
    // ------------------------------------------------------------ normals
    st_L: { trail: 'hand_l', keys: [[0, 'caretakerStance'], [3, 'caretakerJabWind', 'out'], ['s', 'caretakerJab', 'in'], ['a+1', 'caretakerJab'], ['e', 'caretakerStance', 'io']] },
    st_M: { keys: [[0, 'caretakerStance'], [5, { ...C('Plunge', 0.1), sp: [-6, 16, 0], hr: [0.1, -0.5, -0.1, 1] }, 'out'], ['s', 'caretakerPoke', 'in'], ['a+2', { ...C('Plunge', 0.29), hr: [0.44, -0.06, 0.06, 1], pr: [-0.3, -1, -0.5] }], ['e-5', C('Plunge', 0.18)], ['e', 'caretakerStance']] },
    st_H: { keys: [[0, 'caretakerStance'], [4, C('ShovelSwing', 1.12), 'out'], [10, C('ShovelSwing', 1.36)], ['s', C('ShovelSwing', 1.6), 'in'], ['a+3', C('ShovelSwing', 1.7)], ['e-8', C('ShovelSwing', 1.84)], ['e', 'caretakerStance']] },
    cr_L: { trail: 'foot_r', keys: [[0, 'caretakerCrouch'], [2, { ...crouched(C('Idle', 0.3)), fr: [0.1, -0.5, -0.06, 1], kr: [0.6, 1, 0] }], ['s', 'caretakerBoot', 'in'], ['a+1', 'caretakerBoot'], ['e', 'caretakerCrouch']] },
    cr_M: { keys: [[0, 'caretakerCrouch'], [4, half(C('DirtSweep', 1.15), [10, 0, 0]), 'out'], ['s', { ...half(C('DirtSweep', 1.84), [6, 0, 0]), hr: [0.38, -0.6, 0.2, 1] }, 'in'], ['a+2', { ...half(C('DirtSweep', 1.88), [6, 0, 0]), hr: [0.36, -0.62, 0.2, 1] }], ['e', 'caretakerCrouch']] },
    cr_H: { keys: [[0, 'caretakerCrouch'], [6, { ...half(C('Fury', 1.95), [8, 0, 0]), spin: 35 }, 'out'], ['s', { ...half(C('Fury', 2.13), [8, 0, 0]), hr: [0.2, -0.5, -0.1, 1], spin: 0 }, 'in'], ['a+2', { ...half(C('Fury', 2.16), [8, 0, 0]), hr: [0.16, -0.52, -0.16, 1], spin: -30 }], ['e-8', { ...half(C('Fury', 2.2), [8, 0, 0]), spin: -24 }], ['e', 'caretakerCrouch']] },
    j_L: { trail: 'hand_l', keys: [[0, 'caretakerJump'], [3, { ...air(C('Idle', 0.3)), hl: [0.0, 0.5, 0.3, 1], pl: [-1, 0, 0.4] }, 'out'], ['s', { ...air(C('Idle', 0.3), [18, -14, 0]), hl: [0.9, -0.3, 0.05, 1], pl: [-0.3, 0.4, 1] }, 'in'], ['a', { ...air(C('Idle', 0.3), [18, -14, 0]), hl: [0.85, -0.45, 0.05, 1], pl: [-0.3, 0.4, 1] }], ['e', 'caretakerJump']] },
    j_M: { keys: [[0, 'caretakerJump'], [4, air(C('DirtSweep', 1.12), [6, 10, 0]), 'out'], ['s', air(C('DirtSweep', 1.5), [22, 0, 0]), 'in'], ['a', air(C('DirtSweep', 1.6), [22, 0, 0])], ['e', 'caretakerJump']] },
    j_H: { keys: [[0, 'caretakerJump'], [5, air(C('OverheadSlam', 0.5), [-8, 0, 0]), 'out'], ['s', air(C('OverheadSlam', 0.7), [26, 0, 0]), 'in'], ['a', air(C('OverheadSlam', 0.8), [26, 0, 0])], ['e', 'caretakerJump']] },
    bonk: { trail: 'hand_l', keys: [[0, 'caretakerStance'], [8, 'caretakerBonkUp', 'out'], ['s-3', { ...C('LanternToss', 0.55), sp: [-14, 12, 0], hl: [0.1, 1.0, 0.18, 1], pl: [-1, 0.3, 0.4] }], ['s', 'caretakerBonkDown', 'in'], ['a+4', 'caretakerBonkThrough'], ['e', 'caretakerStance']] },
    sixfeet: { keys: [[0, 'caretakerStance'], [6, C('ShovelSwing', 0.3), 'out'], [12, C('ShovelSwing', 0.55)], ['s-2', C('ShovelSwing', 0.72)], ['s', C('ShovelSwing', 0.9), 'in'], ['a+6', C('ShovelSwing', 0.97)], ['e-6', C('OverheadSlam', 1.5)], ['e', 'caretakerStance']] },
    uproot: { keys: [[0, 'caretakerStance'], [5, crouched(C('DirtSweep', 1.9), [24, 0, 0]), 'out'], ['s', C('Plunge', 0.42), 'in'], ['a', C('Plunge', 0.5)], ['e-8', C('Plunge', 0.52)], ['e', 'caretakerStance']] },
    // ------------------------------------------------------------ specials
    // the grab shares its keys with the whiff: frame 0 is already the reach (the grab restarts the clock)
    plant: { keys: [[0, { ...C('Plunge', 0.12), sp: [10, 0, 0] }], ['s', C('Plunge', 0.16), 'in'], [14, C('DirtSweep', 2.1)], [22, C('DirtSweep', 2.3), 'out'], [30, C('OverheadSlam', 0.35)], [40, C('OverheadSlam', 0.53), 'out'], [50, C('OverheadSlam', 0.72), 'in'], [60, C('OverheadSlam', 1.0)], [66, C('OverheadSlam', 1.4)]] },
    dirt: { keys: [[0, 'caretakerStance'], [5, C('DirtSweep', 1.15), 'out'], ['s-6', C('DirtSweep', 1.9)], ['s', C('DirtSweep', 2.25), 'in'], ['s+6', C('DirtSweep', 2.36)], ['e-6', C('DirtSweep', 2.45)], ['e', 'caretakerStance']] },
    slam: { keys: [[0, 'caretakerStance'], [6, C('OverheadSlam', 0.3), 'out'], ['s-4', { ...C('OverheadSlam', 0.53), sp: [-10, 0, 0] }], ['s', { ...C('OverheadSlam', 0.7), ...LUNGE }, 'in'], ['a+4', { ...C('OverheadSlam', 0.95), ...LUNGE }], ['e-4', C('OverheadSlam', 1.45)], ['e', 'caretakerStance']] },
    grave: { keys: [[0, 'caretakerStance'], [8, C('GraveCall', 0.16), 'out'], ['s', C('GraveCall', 0.34), 'in'], ['s+8', C('GraveCall', 0.7)], ['e-6', C('GraveCall', 0.9)], ['e', 'caretakerStance']] },
    lantern: { trail: 'hand_l', keys: [[0, 'caretakerJump'], [5, air(C('LanternToss', 0.46), [-6, 0, 0]), 'out'], ['s', air(C('LanternToss', 0.66), [16, 0, 0]), 'in'], ['s+6', air(C('LanternToss', 0.75), [12, 0, 0])], ['e', 'caretakerJump']] },
    // ------------------------------------------------------------ supers (frame 0 is held through the super flash)
    lastrites: { keys: [[0, { ...C('Plunge', 0.5), sp: [-10, 0, 0] }], [4, C('Plunge', 0.2)], ['s', C('Plunge', 0.35), 'in'], ['a+6', C('Plunge', 0.37)], ['e', 'caretakerStance']] },
    garden: { keys: [[0, { ...C('GraveCall', 1.6) }], [6, C('GraveCall', 0.16)], ['s', C('GraveCall', 0.34), 'in'], ['a+10', C('GraveCall', 0.7)], ['e', 'caretakerStance']] },
    fury: { keys: [[0, { ...C('Fury', 0.4) }], [6, C('ShovelSwing', 1.3)], ['s', { ...C('ShovelSwing', 1.6), spin: -180 }, 'in'], ['a', { ...C('ShovelSwing', 1.6), spin: -360 }], ['e', { ...C('Idle', 0.3), spin: -360 }]] },
    // ------------------------------------------------------------ universal
    throw: { keys: [[0, C('Plunge', 0.12)], ['s', C('Plunge', 0.17), 'in'], [14, C('DirtSweep', 2.06)], [26, C('DirtSweep', 2.22)], [32, C('DirtSweep', 2.34), 'in'], [44, 'caretakerStance']] },
    bthrow: { keys: [[0, C('Plunge', 0.12)], ['s', C('Plunge', 0.17), 'in'], [16, { ...C('ShovelSwing', 1.2), yaw: 40 }], [30, { ...C('ShovelSwing', 1.45), yaw: 120 }], [36, { ...C('ShovelSwing', 1.65), yaw: 180 }, 'in'], [48, 'caretakerStance']] },
    breaker: { keys: [[0, 'caretakerStance'], [10, { ...C('ShovelSwing', 1.2), pel: [-0.05, 0, 0] }], ['s', C('Plunge', 0.35), 'in'], ['a+8', C('Plunge', 0.37)], ['e', 'caretakerStance']] },
    breakerRev: { keys: [[0, 'caretakerGuard'], ['s', { ...C('Plunge', 0.33), sp: [6, 0, 0] }, 'in'], ['a+6', C('Plunge', 0.36)], ['e', 'caretakerStance']] },
    taunt: { keys: [[0, 'caretakerStance'], [12, C('GraveCall', 0.6)], [40, C('GraveCall', 1.6)], [56, C('GraveCall', 1.76)], [70, 'caretakerStance']] },
  },
  cine: {
    // Last Rites: thrust, backhand, scoop, slam, and the burial
    lastrites: [
      [0, C('Plunge', 0.36)], [6, C('LastRites', 0.4)], [10, C('LastRites', 0.66), 'in'],
      [16, C('ShovelSwing', 1.24)], [24, C('ShovelSwing', 1.62), 'in'],
      [32, C('DirtSweep', 1.85)], [40, C('DirtSweep', 2.26), 'in'],
      [48, C('LastRites', 0.98)], [56, C('LastRites', 1.4)], [62, C('LastRites', 2.32), 'in'], [72, C('LastRites', 2.6)],
      [82, C('OverheadSlam', 0.35)], [92, { ...C('OverheadSlam', 0.53), sp: [-20, 0, 0], hd: [16, 0, 0] }, 'out'], [98, { ...C('OverheadSlam', 0.72), ...LUNGE, sp: [26, 0, 0] }, 'in'],
      [114, { ...C('OverheadSlam', 1.0), ...LUNGE, sp: [20, 0, 0] }], [126, C('OverheadSlam', 1.4)],
    ],
    // The Garden: plant the shovel, call the hands, raise the lantern, then pat the earth down
    garden: [
      [0, C('GraveCall', 0.34)], [20, C('GraveCall', 0.64)], [30, C('GraveCall', 0.8)], [50, C('GraveCall', 1.1)], [62, C('GraveCall', 1.3)],
      [84, C('GraveCall', 1.62)], [98, C('GraveCall', 1.77)], [112, C('OverheadSlam', 0.2)], [128, C('OverheadSlam', 0.4)],
      [146, { ...C('OverheadSlam', 0.53), sp: [-20, 0, 0], hd: [16, 0, 0] }, 'out'], [156, { ...C('OverheadSlam', 0.72), ...LUNGE, sp: [26, 0, 0] }, 'in'], [172, { ...C('OverheadSlam', 1.0), ...LUNGE, sp: [20, 0, 0] }], [186, C('OverheadSlam', 1.4)],
    ],
    // Fury: a burning spin, then two slams
    fury: [
      [0, { ...C('ShovelSwing', 1.6), spin: -360 }], [16, { ...C('ShovelSwing', 1.6), spin: -720 }, 'lin'], [34, { ...C('ShovelSwing', 1.62), spin: -1080 }, 'lin'],
      [52, { ...C('ShovelSwing', 1.64), spin: -1440 }, 'lin'], [60, { ...C('Fury', 1.33), spin: -1440 }], [72, { ...C('Fury', 1.62), spin: -1440 }, 'in'],
      [86, { ...C('Fury', 1.87), spin: -1440 }], [98, { ...C('Fury', 0.3), spin: -1440 }], [110, { ...C('Fury', 0.53), spin: -1440 }],
      [116, { ...C('Fury', 1.62), spin: -1440 }, 'in'], [140, { ...C('Fury', 1.9), spin: -1440 }], [156, { ...C('Fury', 2.6), spin: -1440 }],
    ],
  },
};
