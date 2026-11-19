// The Instructor's animation set. Rigid and exact: side-on fencer's stance, left hand behind his back (he
// teaches one-handed), the baton in the right hand doing the work. Every baton pose sits on one frame of the
// rapier thrust clip so the wrist keeps the baton in line with the forearm; IK then aims the forearm.
// Keys: 's' first active frame, 'a' last active, 'e' end.
const KNEE = [1, 0.1, 0];
const BAT = { clip: 'rapier_charge_release', cf: 0.35 };
const BACK_L = [-0.34, -0.66, -0.22, 1], BACK_PL = [-0.6, -0.2, 1];
const ARM_R = [-0.3, -1, -0.6];

const poses = {
  // ---------------------------------------------------------------- stance and movement
  instr_stance: {
    ...BAT, pel: [0, -0.05, 0], yaw: -55, sp: [0, 8, 0], hd: [2, 42, 0],
    hr: [0.55, -0.18, 0.10, 1], pr: ARM_R, hl: BACK_L, pl: BACK_PL,
    fr: [-0.20, -0.94, -0.10, 1], fl: [0.28, -0.93, 0.06, 1], kr: KNEE, kl: KNEE,
  },
  instr_walkArms: { hr: [0.55, -0.18, 0.10, 1], pr: ARM_R, hl: BACK_L, pl: BACK_PL, sp: [0, 8, 0], yaw: -42, hd: [2, 32, 0] },
  instr_guard: { // baton raised upright in front of the face; the left hand stays behind his back
    extends: 'instr_stance', pel: [-0.03, -0.09, 0], yaw: -50, sp: [8, 8, 0], hd: [8, 38, 0],
    hr: [0.40, 0.34, 0.20, 1], pr: [0.2, -1, -0.4],
  },
  instr_crouch: {
    ...BAT, pel: [0, -0.40, 0], yaw: -45, sp: [16, 8, 0], hd: [-8, 36, 0],
    hr: [0.62, -0.32, 0.10, 1], pr: ARM_R, hl: BACK_L, pl: BACK_PL,
    fr: [-0.24, -0.60, -0.14, 1], fl: [0.36, -0.60, 0.10, 1], kr: [1, 0.25, 0], kl: [1, 0.25, 0],
  },
  instr_cguard: { extends: 'instr_crouch', sp: [24, 8, 0], hd: [0, 34, 0], hr: [0.40, 0.30, 0.20, 1], pr: [0.2, -1, -0.4] },
  instr_tuck: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [4, 10, 0], yaw: -30, hd: [0, 24, 0],
    hr: [0.55, -0.10, 0.10, 1], pr: ARM_R, hl: BACK_L, pl: BACK_PL,
    fr: [0.10, -0.55, -0.08, 1], fl: [0.25, -0.62, 0.08, 1], kr: KNEE, kl: KNEE,
  },
  instr_salute: { // baton upright before the face
    clip: 'rapier_guard_Loop', ct: 0.4, pel: [0, -0.02, 0], yaw: -40, sp: [-2, 6, 0], hd: [-2, 34, 0],
    hr: [0.30, 0.38, 0.22, 1], pr: [0.2, -1, -0.5], hl: BACK_L, pl: BACK_PL,
    fr: [-0.06, -0.97, -0.10, 1], fl: [0.08, -0.97, 0.08, 1], kr: KNEE, kl: KNEE,
  },

  // ---------------------------------------------------------------- normals
  instr_tapWind: { extends: 'instr_stance', yaw: -60, hr: [0.36, 0.04, 0.12, 1] },
  instr_tapOut: { extends: 'instr_stance', yaw: -64, sp: [2, 14, 0], pel: [0.03, -0.05, 0], hr: [1.0, 0.10, 0.04, 1], pr: [-0.2, -1, -0.4] },
  instr_pointWind: { extends: 'instr_stance', yaw: -66, sp: [-2, 16, 0], pel: [-0.04, -0.06, 0], hr: [0.18, -0.10, 0.10, 1], pr: [-1, -0.3, -0.3] },
  instr_pointOut: { // fencer's lunge
    extends: 'instr_stance', yaw: -70, sp: [8, 10, 0], pel: [0.12, -0.15, 0], hd: [-4, 50, 0],
    hr: [1.0, -0.04, 0.04, 1], pr: [-0.2, -1, -0.3],
    fl: [0.54, -0.85, 0.06, 1], fr: [-0.38, -0.86, -0.10, 1],
  },
  instr_chopWind: { extends: 'instr_stance', yaw: -40, sp: [-12, 20, 0], pel: [-0.02, -0.04, 0], hr: [0.04, 0.96, 0.06, 1], pr: [-1, 0.4, -0.3], hd: [-6, 30, 0] },
  instr_chopOut: {
    extends: 'instr_stance', yaw: -26, sp: [26, -6, 0], pel: [0.10, -0.16, 0], hd: [-16, 22, 0],
    hr: [0.88, -0.30, 0.08, 1], pr: [-0.3, 0.4, -1],
    fl: [0.46, -0.84, 0.08, 1], fr: [-0.40, -0.86, -0.12, 1],
  },
  instr_rapWind: { extends: 'instr_stance', yaw: -50, sp: [-8, 12, 0], hr: [0.34, 0.86, 0.08, 1], pr: [-1, 0.3, -0.4] },
  instr_rapOut: { extends: 'instr_stance', yaw: -50, sp: [18, 8, 0], pel: [0.06, -0.10, 0], hr: [0.92, 0.22, 0.06, 1], pr: [-0.3, 0.4, -1] },
  instr_crackWind: { // baton cocked across the body
    extends: 'instr_stance', yaw: -4, sp: [4, 30, 0], pel: [-0.04, -0.08, 0], hd: [0, 22, 0],
    hr: [0.15, 0.36, 0.55, 1], pr: [0, -1, 0.4],
  },
  instr_crackOut: {
    extends: 'instr_stance', yaw: -82, sp: [12, -20, 0], pel: [0.15, -0.17, 0], hd: [-6, 62, 0],
    hr: [0.95, 0.14, -0.36, 1], pr: [-0.2, -1, -0.5],
    fl: [0.56, -0.83, 0.06, 1], fr: [-0.44, -0.84, -0.12, 1],
  },
  instr_kickLow: { extends: 'instr_crouch', yaw: -20, sp: [10, 10, 4], fr: [0.84, -0.56, 0.02, 1], kr: [0.3, 1, 0] },
  instr_lowPoint: { extends: 'instr_crouch', yaw: -58, sp: [32, 8, 0], pel: [0.08, -0.42, 0], hr: [0.96, -0.70, 0.06, 1], pr: [-0.3, -0.2, -1] },
  instr_sweep: { extends: 'instr_crouch', yaw: 38, pel: [0, -0.44, 0], sp: [24, 10, 14], fr: [0.98, -0.58, 0.15, 1], kr: [0.2, 1, 0.3], hr: [0.30, -0.55, 0.10, 1] },
  instr_airKnee: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [8, 10, 0], yaw: -30,
    fr: [0.55, -0.05, 0, 1], kr: [1, 0.3, 0], fl: [-0.15, -0.70, 0.1, 1], kl: [1, -0.2, 0],
    hr: [0.50, 0.0, 0.10, 1], pr: ARM_R, hl: BACK_L, pl: BACK_PL,
  },
  instr_airWind: { extends: 'instr_airKnee', ...BAT, sp: [-8, 16, 0], hr: [0.10, 0.95, 0.05, 1], pr: [-1, 0.4, -0.3] },
  instr_airBaton: { extends: 'instr_airKnee', ...BAT, sp: [26, 4, 0], hr: [0.86, -0.42, 0.06, 1], pr: [-0.3, 0.4, -1] },
  instr_stamp: { // straight-legged heel stamp, back upright
    extends: 'instr_airKnee', ...BAT, sp: [-6, 8, 0], yaw: -40,
    fr: [0.62, -0.80, 0.0, 1], kr: [1, 0.4, 0], fl: [-0.10, -0.45, 0.08, 1], kl: [1, 0, 0],
    hr: [0.45, 0.30, 0.10, 1],
  },

  // ---------------------------------------------------------------- specials
  instr_quizLow: { extends: 'instr_stance', pel: [0.02, -0.26, 0], yaw: -45, sp: [26, 6, 0], hd: [-14, 30, 0], hr: [0.32, -0.72, 0.10, 1], pr: [-1, 0, -0.4] },
  instr_quizUp: {
    extends: 'instr_stance', pel: [0.03, 0.04, 0], yaw: -34, sp: [-14, 0, 0], hd: [-22, 30, 0],
    hr: [0.30, 1.0, 0.08, 1], pr: [1, 0, -0.3],
    fr: [-0.10, -0.80, -0.05, 1], kr: [1, 0.2, 0], fl: [0.20, -0.98, 0.08, 1],
  },
  instr_whistleIn: { // the whistle to his lips, chest up for the breath
    extends: 'instr_stance', yaw: -40, sp: [-12, 10, 0], hd: [-14, 30, 0],
    hl: [0.24, 0.30, -0.32, 1], pl: [-0.3, -1, 0.6],
  },
  instr_whistleOut: {
    extends: 'instr_stance', yaw: -46, sp: [22, 6, 0], pel: [0.05, -0.11, 0], hd: [4, 34, 0],
    hl: [0.22, 0.20, -0.30, 1], pl: [-0.3, -1, 0.6], hr: [0.42, -0.42, 0.20, 1],
    fl: [0.40, -0.88, 0.06, 1],
  },
  instr_demo: { // "Show me." Knees soft, the left hand open and waiting, the baton back by the hip
    extends: 'instr_stance', pel: [-0.02, -0.13, 0], yaw: -40, sp: [6, 10, 0], hd: [4, 32, 0],
    hl: [0.62, 0.04, 0.0, 1], pl: [-0.3, -1, 0.6], hr: [0.12, -0.55, 0.14, 1], pr: [-1, -0.2, -0.4],
  },
  instr_demo2: { extends: 'instr_demo', hl: [0.56, 0.14, 0.02, 1], hd: [6, 26, 6] },
  instr_catch: { extends: 'instr_demo', yaw: -36, pel: [0.02, -0.12, 0], hl: [0.86, 0.10, 0.04, 1], hr: [0.34, 0.55, 0.15, 1], pr: [-1, 0.2, -0.4] },
  instr_armbar: { extends: 'instr_catch', yaw: -12, pel: [-0.06, -0.14, 0], sp: [12, 0, 0], hl: [0.40, -0.08, -0.08, 1] },
  instr_elbowCrack: { extends: 'instr_armbar', sp: [22, -4, 0], hr: [0.72, -0.22, 0.04, 1], pr: [-0.3, 0.4, -1] },
  instr_hipLoad: {
    extends: 'instr_stance', yaw: 30, pel: [0.04, -0.30, 0], sp: [40, 0, 0], hd: [-20, 0, 0],
    hr: [0.20, 0.46, 0.10, 1], hl: [0.20, 0.46, -0.10, 1], pr: [-0.2, -1, -0.6], pl: [-0.2, -1, 0.6],
    fr: [-0.10, -0.75, -0.18, 1], fl: [0.30, -0.75, 0.16, 1],
  },
  instr_slam: {
    extends: 'instr_hipLoad', yaw: -10, sp: [52, -10, 0], pel: [0.08, -0.34, 0], hd: [-34, 10, 0],
    hr: [0.76, -0.86, 0.10, 1], hl: [0.76, -0.86, -0.10, 1], pr: [-0.3, 0.4, -1], pl: [-0.3, 0.4, 1],
  },
  instr_signal: { extends: 'instr_stance', yaw: -46, sp: [-4, 10, 0], hd: [-8, 36, 0], hr: [0.24, 0.98, 0.08, 1], pr: [-1, 0.3, -0.4] },
  instr_pointFloor: { extends: 'instr_stance', yaw: -58, sp: [14, 10, 0], hd: [-16, 40, 0], hr: [0.92, -0.46, 0.06, 1], pr: [-0.3, -0.3, -1] },
  instr_pointFar: { extends: 'instr_stance', yaw: -62, sp: [-2, 12, 0], hd: [-4, 44, 0], hr: [1.0, 0.36, 0.04, 1], pr: [-0.3, -1, -0.4] },
  instr_palm: { extends: 'instr_stance', yaw: -30, sp: [6, 6, 0], hd: [-6, 22, 0], hr: [0.42, -0.12, 0.12, 1], hl: [0.42, -0.32, -0.02, 1], pl: [-0.3, -1, 0.6] },
  instr_palmHit: { extends: 'instr_palm', hr: [0.44, -0.30, 0.04, 1] },
  instr_inspect: { extends: 'instr_stance', yaw: -40, sp: [18, 10, 6], hd: [-6, 30, 12], pel: [0.03, -0.06, 0] },
  instr_write: { // clipboard in the left hand, writing with the baton
    extends: 'instr_stance', yaw: -30, sp: [12, 6, 0], hd: [-24, 20, 0],
    hl: [0.42, -0.08, 0.02, 1], pl: [-0.3, -1, 0.6], hr: [0.40, -0.02, 0.16, 1], pr: [-0.5, -1, -0.5],
  },
  instr_stampUp: { extends: 'instr_stance', yaw: -36, sp: [-14, 14, 0], hd: [-14, 30, 0], hl: [0.10, 1.0, -0.05, 1], pl: [-1, 0.4, 0.4], hr: [0.40, -0.40, 0.20, 1] },
  instr_stampDown: {
    extends: 'instr_stance', yaw: -48, sp: [30, 10, 0], pel: [0.12, -0.18, 0], hd: [-16, 36, 0],
    hl: [0.96, 0.24, -0.04, 1], pl: [-0.3, 0.3, 1], hr: [0.30, -0.45, 0.20, 1],
    fl: [0.50, -0.84, 0.06, 1], fr: [-0.42, -0.85, -0.12, 1],
  },
  instr_reachBoard: { extends: 'instr_stance', yaw: -30, sp: [-4, 24, 0], hd: [-4, 22, 0], hl: [-0.08, 0.86, 0.22, 1], pl: [0.3, 0.3, 1] },
  instr_boardSwing: {
    extends: 'instr_stance', yaw: -80, sp: [10, -14, 0], pel: [0.10, -0.12, 0], hd: [-6, 56, 0],
    hl: [0.98, 0.30, -0.12, 1], pl: [-0.2, -1, 0.6], fl: [0.48, -0.85, 0.06, 1],
  },
  instr_breathe: { extends: 'instr_whistleIn', sp: [-22, 10, 0], pel: [-0.03, -0.02, 0], hd: [-22, 30, 0] },
  instr_blast: { extends: 'instr_whistleOut', sp: [34, 6, 0], pel: [0.10, -0.16, 0], hd: [10, 34, 0], fl: [0.52, -0.84, 0.06, 1], fr: [-0.40, -0.86, -0.12, 1] },
};

const att = (k) => [k, 'instr_stance'];
void att;

export default {
  style: {},
  packs: ['weapons'],
  poses,
  look: { alts: [null, '#1c3f8a', '#c9a227', '#2e6b2e', '#5b2a6b', '#d0d0d0', '#151515', '#b85c1c'] },
  states: {
    // rigid: he doesn't sway; breathing only
    idle: { keys: [[0, 'instr_stance']], blend: 5 },
    guard: { keys: [[0, 'instr_guard']], blend: 4 },
    walkF: { clip: 'guard_walk_fwd', loop: true, speed: 1.0, over: 'instr_walkArms', keys: [[0, { clip: 'guard_walk_fwd' }]] },
    walkB: { clip: 'guard_walk_back', loop: true, speed: 0.95, over: 'instr_walkArms', keys: [[0, { clip: 'guard_walk_back' }]] },
    crouch: { keys: [[0, 'instr_crouch']], blend: 4 },
    prejump: { keys: [[0, 'instr_stance'], [3, { extends: 'instr_stance', pel: [0, -0.16, 0], sp: [14, 8, 0] }, 'out']], blend: 2 },
    jumpU: { keys: [[0, 'instr_tuck']], blend: 3 },
    jumpF: { keys: [[0, 'instr_tuck'], [10, { extends: 'instr_tuck', tilt: 14 }], [28, { extends: 'instr_tuck', tilt: 4 }]], blend: 3 },
    jumpB: { keys: [[0, 'instr_tuck'], [10, { extends: 'instr_tuck', tilt: -12 }], [28, { extends: 'instr_tuck', tilt: -4 }]], blend: 3 },
    land: { keys: [[0, { extends: 'instr_stance', pel: [0, -0.16, 0], sp: [14, 8, 0] }], [4, 'instr_stance']], blend: 2 },
    dash: { keys: [[0, { extends: 'instr_pointOut', hr: [0.6, -0.1, 0.1, 1] }], [8, { extends: 'instr_stance', pel: [0.05, -0.1, 0] }], [14, 'instr_stance']], blend: 2 },
    dashEnd: { keys: [[0, 'instr_stance']] },
    block: { keys: [[0, { extends: 'instr_guard', pel: [-0.09, -0.12, 0], sp: [16, 8, 0] }], [6, 'instr_guard']], blend: 1 },
    cblock: { keys: [[0, { extends: 'instr_cguard', sp: [30, 8, 0] }], [6, 'instr_cguard']], blend: 1 },
    chit: { keys: [[0, { extends: 'instr_crouch', sp: [-6, 0, 10], hd: [-25, 20, 10] }], [12, 'instr_crouch']], blend: 1 },
    timeout: { keys: [[0, 'instr_stance']] },
    intro: { keys: [[0, 'instr_salute']], loop: true, clip: 'rapier_guard_Loop', speed: 0.6 },
    win: { keys: [[0, 'instr_stance'], [20, 'instr_salute', 'io'], [60, 'instr_salute'], [80, { extends: 'instr_palm' }], [86, 'instr_palmHit'], [92, 'instr_palm'], [98, 'instr_palmHit'], [110, 'instr_stance']], blend: 6 },
    taunt: { keys: [[0, 'instr_stance'], [8, 'instr_palm'], [14, 'instr_palmHit', 'in'], [20, 'instr_palm'], [26, 'instr_palmHit', 'in'], [32, 'instr_palm'], [38, 'instr_palmHit', 'in'], [50, 'instr_salute'], [64, 'instr_salute'], [71, 'instr_stance']] },
  },
  moves: {
    st_L: { keys: [[0, 'instr_stance'], [2, 'instr_tapWind'], ['s', 'instr_tapOut', 'in'], ['a+1', 'instr_tapOut'], ['e', 'instr_stance', 'out']] },
    st_M: { keys: [[0, 'instr_stance'], [4, 'instr_pointWind'], ['s', 'instr_pointOut', 'in'], ['a+2', 'instr_pointOut'], ['e', 'instr_stance', 'io']] },
    st_H: { keys: [[0, 'instr_stance'], [7, 'instr_chopWind', 'out'], ['s', 'instr_chopOut', 'in'], ['a+4', 'instr_chopOut'], ['e', 'instr_stance', 'io']] },
    cr_L: { trail: 'foot_r', keys: [[0, 'instr_crouch'], [2, { extends: 'instr_crouch', fr: [0.4, -0.5, 0, 1] }], ['s', 'instr_kickLow', 'in'], ['a+1', 'instr_kickLow'], ['e', 'instr_crouch']] },
    cr_M: { keys: [[0, 'instr_crouch'], [4, { extends: 'instr_crouch', hr: [0.25, -0.40, 0.10, 1], yaw: -60 }], ['s', 'instr_lowPoint', 'in'], ['a+2', 'instr_lowPoint'], ['e', 'instr_crouch']] },
    cr_H: { trail: 'foot_r', keys: [[0, 'instr_crouch'], [6, { extends: 'instr_sweep', yaw: -20, fr: [0.5, -0.55, 0.3, 1] }], ['s', 'instr_sweep', 'in'], ['a+6', { extends: 'instr_sweep', yaw: 100 }], ['e', 'instr_crouch']] },
    j_L: { trail: 'foot_r', keys: [[0, 'instr_tuck'], ['s', 'instr_airKnee', 'out'], ['a', 'instr_airKnee'], ['e', 'instr_tuck']] },
    j_M: { keys: [[0, 'instr_tuck'], [4, 'instr_airWind'], ['s', 'instr_airBaton', 'in'], ['a', 'instr_airBaton'], ['e', 'instr_tuck']] },
    j_H: { trail: 'foot_r', keys: [[0, 'instr_tuck'], [5, { extends: 'instr_stamp', fr: [0.25, -0.30, 0, 1] }, 'out'], ['s', 'instr_stamp', 'in'], ['a', 'instr_stamp'], ['e', 'instr_tuck']] },
    attention: { keys: [[0, 'instr_stance'], [10, 'instr_rapWind', 'out'], ['s', 'instr_rapOut', 'in'], ['a+5', 'instr_rapOut'], ['e', 'instr_stance']] },
    correction: { keys: [[0, 'instr_stance'], [9, 'instr_crackWind', 'out'], ['s', 'instr_crackOut', 'in'], ['a+5', 'instr_crackOut'], ['e', 'instr_stance', 'io']] },
    whistle: { trail: 'hand_l', keys: [[0, 'instr_stance'], [5, 'instr_whistleIn', 'out'], ['s-2', { extends: 'instr_whistleIn', sp: [-16, 10, 0] }], ['s', 'instr_whistleOut', 'in'], ['s+10', 'instr_whistleOut'], ['e', 'instr_stance']] },
    popquiz: { keys: [[0, 'instr_stance'], [2, 'instr_quizLow', 'out'], ['s', 'instr_quizUp', 'in'], ['a', { extends: 'instr_quizUp', hr: [0.15, 1.0, 0.08, 1] }], ['e', 'instr_stance']] },
    demo: { keys: [[0, 'instr_stance'], [4, 'instr_demo', 'out'], ['a-6', 'instr_demo2', 'io'], ['a', 'instr_demo'], ['e', 'instr_stance']] },
    // counter success (grab frames): catch, crack the elbow, hip throw, slam
    demo_take: { trail: 'hand_r', keys: [[0, 'instr_catch'], [10, 'instr_armbar'], [17, { extends: 'instr_armbar', hr: [0.30, 0.70, 0.12, 1] }], [20, 'instr_elbowCrack', 'in'], [27, 'instr_hipLoad'], [35, { extends: 'instr_hipLoad', sp: [10, 0, 0], pel: [0, -0.18, 0] }], [38, 'instr_slam', 'in'], [46, 'instr_slam'], [50, 'instr_stance']] },
    demo_takeEX: { trail: 'hand_r', keys: [[0, 'instr_catch'], [10, 'instr_armbar'], [17, { extends: 'instr_armbar', hr: [0.30, 0.70, 0.12, 1] }], [20, 'instr_elbowCrack', 'in'], [26, { extends: 'instr_armbar', hr: [0.30, 0.70, 0.12, 1] }], [30, 'instr_elbowCrack', 'in'], [36, 'instr_hipLoad'], [41, { extends: 'instr_hipLoad', sp: [10, 0, 0], pel: [0, -0.18, 0] }], [44, 'instr_slam', 'in'], [52, 'instr_slam'], [56, 'instr_stance']] },
    dummy_L: { keys: [[0, 'instr_stance'], [6, 'instr_signal', 'out'], ['s', 'instr_pointFloor', 'in'], ['s+6', 'instr_pointFloor'], ['e', 'instr_stance']] },
    dummy_M: { keys: [[0, 'instr_stance'], [6, 'instr_signal', 'out'], ['s', 'instr_pointFloor', 'in'], ['s+6', 'instr_pointFloor'], ['e', 'instr_stance']] },
    dummy_H: { keys: [[0, 'instr_stance'], [6, 'instr_signal', 'out'], ['s', { extends: 'instr_pointFloor', hr: [0.98, -0.30, 0.06, 1] }, 'in'], ['s+6', { extends: 'instr_pointFloor', hr: [0.98, -0.30, 0.06, 1] }], ['e', 'instr_stance']] },
    dummy_EX: { keys: [[0, 'instr_stance'], [5, 'instr_signal', 'out'], ['s', 'instr_pointFar', 'in'], ['s+8', 'instr_pointFar'], ['e', 'instr_stance']] },
    orientation: { keys: [[0, 'instr_stance'], [4, 'instr_pointWind', 'out'], ['s', 'instr_pointOut', 'in'], ['a+6', 'instr_pointOut'], ['e', 'instr_stance']] },
    exam: { keys: [[0, 'instr_stance'], [5, 'instr_pointWind', 'out'], ['s', 'instr_pointOut', 'in'], ['a+6', 'instr_pointOut'], ['e', 'instr_stance']] },
    nobody: { trail: 'hand_l', keys: [[0, 'instr_stance'], [5, 'instr_reachBoard', 'out'], ['s', 'instr_boardSwing', 'in'], ['a+6', 'instr_boardSwing'], ['e', 'instr_stance']] },
    throw: { keys: [[0, 'instr_stance'], ['s', 'instr_catch', 'out'], [12, 'instr_armbar'], [24, 'instr_hipLoad'], [30, 'instr_slam', 'in'], [38, 'instr_slam'], [44, 'instr_stance']] },
    bthrow: { keys: [[0, 'instr_stance'], ['s', 'instr_catch', 'out'], [14, { extends: 'instr_armbar', spin: 90 }], [26, { extends: 'instr_hipLoad', spin: 180 }], [34, { extends: 'instr_slam', spin: 180 }, 'in'], [42, { extends: 'instr_slam', spin: 180 }], [48, { extends: 'instr_stance', spin: 180 }]] },
    breaker: { keys: [[0, 'instr_stance'], [10, 'instr_crackWind', 'out'], ['s', 'instr_crackOut', 'in'], ['a+8', 'instr_crackOut'], ['e', 'instr_stance']] },
    breakerRev: { keys: [[0, 'instr_guard'], ['s', 'instr_crackOut', 'in'], ['a+6', 'instr_crackOut'], ['e', 'instr_stance']] },
    taunt: { keys: [[0, 'instr_stance'], [8, 'instr_palm'], [14, 'instr_palmHit', 'in'], [20, 'instr_palm'], [26, 'instr_palmHit', 'in'], [32, 'instr_palm'], [38, 'instr_palmHit', 'in'], [50, 'instr_salute'], [64, 'instr_salute'], [71, 'instr_stance']] },
  },
  cine: {
    // "for your own good": a blur of taps high, middle, low, two cracks, then the big overhead
    orientation: [
      [0, 'instr_pointOut'], [4, 'instr_tapWind'], [8, 'instr_tapOut', 'in'], [12, 'instr_rapWind'], [16, 'instr_rapOut', 'in'],
      [20, { extends: 'instr_pointWind', yaw: -60 }], [24, { extends: 'instr_lowPoint', fr: [-0.38, -0.70, -0.12, 1], fl: [0.46, -0.66, 0.08, 1], pel: [0.08, -0.30, 0] }, 'in'],
      [28, 'instr_crackWind'], [32, 'instr_crackOut', 'in'], [38, { extends: 'instr_crackWind', yaw: 10 }], [44, { extends: 'instr_crackOut', yaw: -90 }, 'in'],
      [54, 'instr_chopWind'], [64, { extends: 'instr_chopWind', lift: 0.06, sp: [-18, 20, 0] }], [72, 'instr_chopOut', 'in'], [84, 'instr_chopOut'], [92, 'instr_stance'],
    ],
    // the grading: a crack to the knee, questions, notes on the clipboard, then the F stamped on the forehead
    exam: [
      [0, 'instr_pointOut'], [16, 'instr_chopWind'], [30, { extends: 'instr_lowPoint', pel: [0.08, -0.30, 0], fr: [-0.38, -0.70, -0.12, 1], fl: [0.46, -0.66, 0.08, 1] }, 'in'],
      [44, 'instr_inspect'], [58, 'instr_rapWind'], [70, 'instr_rapOut', 'in'], [80, 'instr_rapOut'],
      [92, 'instr_write'], [98, { extends: 'instr_write', hr: [0.40, 0.05, 0.10, 1] }], [104, 'instr_write'], [112, 'instr_crackOut', 'in'],
      [122, 'instr_crackOut'], [136, 'instr_stampUp', 'io'], [148, { extends: 'instr_stampUp', lift: 0.04 }], [154, 'instr_stampDown', 'in'],
      [168, 'instr_stampDown'], [182, 'instr_salute'],
    ],
    // clipboard to the face, then the whistle at full volume
    nobody: [
      [0, 'instr_boardSwing'], [12, 'instr_reachBoard'], [24, { extends: 'instr_boardSwing', yaw: -100 }, 'in'], [40, 'instr_boardSwing'],
      [56, 'instr_whistleIn'], [80, 'instr_breathe', 'io'], [100, 'instr_blast', 'in'], [130, 'instr_blast'], [144, 'instr_stance'],
    ],
  },
};
