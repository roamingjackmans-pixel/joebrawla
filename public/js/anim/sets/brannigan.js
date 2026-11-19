// Brannigan's animation set. An old bare-knuckle brawler: hunched forward, lead fist out and low, rear fist at
// the chin, always leaning into the next punch. Every special pushes forward; the steam moves brace and vent.
// Keys: 's' first active frame, 'a' last active, 'e' end.
const KNEE = [1, 0.1, 0];
const ARM_R = [-0.3, -1, -0.6], ARM_L = [-0.3, -1, 0.6];

const poses = {
  // ---------------------------------------------------------------- stance and movement
  brn_stance: {
    clip: 'Idle_Loop', ct: 0.4,
    pel: [0, -0.12, 0], yaw: -28, sp: [20, 14, 0], hd: [-14, 12, 0],
    hr: [0.40, 0.24, 0.24, 1], hl: [0.68, 0.20, 0.04, 1], pr: ARM_R, pl: ARM_L,
    fr: [-0.30, -0.86, -0.16, 1], fl: [0.32, -0.86, 0.12, 1], kr: KNEE, kl: KNEE,
  },
  brn_walkArms: { hr: [0.40, 0.24, 0.24, 0.95], hl: [0.66, 0.22, 0.04, 0.95], pr: ARM_R, pl: ARM_L, sp: [18, 12, 0], yaw: -22 },
  brn_guard: { // forearms up, chin tucked, shell
    extends: 'brn_stance', pel: [-0.03, -0.15, 0], yaw: -20, sp: [24, 8, 0], hd: [6, 6, 0],
    hr: [0.36, 0.60, 0.18, 1], hl: [0.42, 0.62, 0.0, 1], pr: [0.1, -1, -0.3], pl: [0.1, -1, 0.3],
  },
  brn_crouch: {
    clip: 'Crouch_Idle_Loop', ct: 0.3, yaw: -22, sp: [20, 12, 0], hd: [-10, 10, 0],
    hr: [0.38, 0.34, 0.24, 1], hl: [0.56, 0.32, 0.04, 1], pr: ARM_R, pl: ARM_L,
  },
  brn_cguard: { extends: 'brn_crouch', sp: [28, 6, 0], hd: [2, 6, 0], hr: [0.40, 0.52, 0.20, 1], hl: [0.48, 0.54, 0.0, 1], pr: [0.1, -1, -0.3], pl: [0.1, -1, 0.3] },
  brn_tuck: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [14, 10, 0], hd: [-8, 8, 0],
    hr: [0.38, 0.30, 0.24, 1], hl: [0.50, 0.30, 0.04, 1], pr: ARM_R, pl: ARM_L,
    fr: [0.12, -0.55, -0.10, 1], fl: [0.28, -0.60, 0.10, 1], kr: KNEE, kl: KNEE,
  },

  // ---------------------------------------------------------------- punches
  brn_jabWind: { extends: 'brn_stance', hl: [0.46, 0.26, 0.02, 1] },
  brn_jab: { extends: 'brn_stance', yaw: -40, sp: [14, 26, 0], pel: [0.04, -0.12, 0], hl: [1.0, 0.34, -0.08, 1], pl: [-0.2, -0.4, 1] },
  brn_hookWind: { extends: 'brn_stance', yaw: -50, sp: [12, 34, 0], hl: [0.36, 0.34, 0.36, 1], pl: [0, -0.2, 1] },
  brn_hook: {
    extends: 'brn_stance', yaw: 6, sp: [16, -20, 0], pel: [0.06, -0.14, 0], hd: [-14, -4, 0],
    hl: [0.80, 0.32, -0.30, 1], pl: [0, 0.4, 1], hr: [0.36, 0.36, 0.24, 1],
  },
  brn_crossWind: { extends: 'brn_stance', yaw: -44, sp: [14, 28, 0], pel: [-0.03, -0.12, 0], hr: [0.10, 0.30, 0.22, 1] },
  brn_cross: {
    extends: 'brn_stance', yaw: 14, sp: [16, -14, 0], pel: [0.11, -0.13, 0], hd: [-16, -4, 0],
    hr: [1.0, 0.30, 0.16, 1], pr: [-0.2, -0.4, -1], hl: [0.30, 0.40, 0.08, 1],
    fr: [-0.48, -0.83, -0.12, 1], fl: [0.46, -0.84, 0.12, 1],
  },
  brn_kickLow: { extends: 'brn_crouch', yaw: 8, sp: [12, 12, 6], fr: [0.80, -0.82, 0.0, 1], kr: [0.3, 1, 0] },
  brn_gutWind: { extends: 'brn_crouch', yaw: -38, sp: [24, 26, 0], hr: [0.15, -0.05, 0.22, 1] },
  brn_gut: { extends: 'brn_crouch', yaw: 12, sp: [28, -14, 0], pel: [0.08, 0, 0], hr: [0.96, -0.10, 0.12, 1], pr: [-0.2, -0.6, -1], hl: [0.40, 0.40, 0.0, 1] },
  brn_sweep: {
    extends: 'brn_crouch', yaw: 72, pel: [0, -0.12, 0], sp: [26, 10, 18],
    fr: [0.96, -0.86, 0.15, 1], kr: [0.2, 1, 0.3], hr: [-0.10, -0.40, -0.10, 1], hl: [0.15, -0.65, 0.30, 1],
  },
  brn_airKnee: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [10, 10, 0],
    fr: [0.55, -0.05, 0, 1], kr: [1, 0.3, 0], fl: [-0.15, -0.70, 0.1, 1], kl: [1, -0.2, 0],
    hr: [0.36, 0.36, 0.24, 1], hl: [0.46, 0.36, 0, 1], pr: ARM_R, pl: ARM_L,
  },
  brn_airUp: { extends: 'brn_airKnee', sp: [-10, 10, 0], hr: [0.10, 0.95, 0.10, 1], pr: [-1, 0.4, -0.3] },
  brn_airHammer: { extends: 'brn_airKnee', sp: [30, 0, 0], hr: [0.84, -0.30, 0.10, 1], pr: [-0.3, 0.5, -1] },
  brn_airAxeUp: { extends: 'brn_airKnee', sp: [-16, 0, 0], hr: [0.0, 0.98, 0.06, 1], hl: [0.0, 0.98, -0.06, 1], pr: [-1, 0.4, -0.3], pl: [-1, 0.4, 0.3] },
  brn_airAxe: { extends: 'brn_airKnee', sp: [40, 0, 0], hr: [0.84, -0.42, 0.06, 1], hl: [0.84, -0.42, -0.04, 1], pr: [-0.3, 0.5, -1], pl: [-0.3, 0.5, 1] },
  brn_overhandWind: { extends: 'brn_stance', yaw: -46, sp: [-10, 30, 0], hr: [-0.04, 0.86, 0.06, 1], pr: [-1, 0.4, -0.3] },
  brn_overhand: {
    extends: 'brn_stance', yaw: 12, sp: [34, -12, 0], pel: [0.11, -0.19, 0], hd: [-26, 0, 0],
    hr: [0.88, 0.06, 0.10, 1], pr: [-0.3, 0.5, -1], fr: [-0.46, -0.82, -0.12, 1], fl: [0.44, -0.82, 0.12, 1],
  },
  brn_cutLow: { extends: 'brn_stance', pel: [0.02, -0.26, 0], yaw: -32, sp: [30, 22, 0], hr: [0.24, -0.18, 0.15, 1], pr: [-1, -0.3, -0.3] },
  brn_cutUp: {
    extends: 'brn_stance', pel: [0.05, 0.0, 0], yaw: 22, sp: [-14, -22, 0], hd: [-20, 0, 0],
    hr: [0.26, 1.0, 0.12, 1], pr: [1, 0, -0.3], hl: [0.20, 0.40, 0.20, 1],
    fr: [-0.10, -0.80, -0.05, 1], kr: [1, 0.2, 0], fl: [0.20, -0.98, 0.10, 1],
  },
  brn_lungWind: { // coiled behind the guard, taking the hit
    extends: 'brn_stance', pel: [-0.04, -0.21, 0], yaw: -46, sp: [32, 30, 0], hd: [0, 14, 0],
    hr: [0.06, 0.06, 0.22, 1], hl: [0.44, 0.56, 0.0, 1], pr: [-1, -0.2, -0.4], pl: [0.1, -1, 0.3],
  },
  brn_lung: {
    extends: 'brn_stance', yaw: 18, sp: [30, -18, 0], pel: [0.13, -0.21, 0], hd: [-22, -6, 0],
    hr: [0.96, -0.06, 0.14, 1], pr: [-0.2, -0.6, -1], hl: [0.40, 0.46, 0.02, 1],
    fr: [-0.52, -0.80, -0.14, 1], fl: [0.46, -0.80, 0.12, 1],
  },

  // ---------------------------------------------------------------- specials
  brn_rushWind: { extends: 'brn_stance', pel: [-0.05, -0.21, 0], yaw: -50, sp: [30, 34, 0], hr: [-0.05, 0.26, 0.10, 1], pr: [-1, 0, -0.4], hl: [0.50, 0.40, 0.04, 1] },
  brn_rush: {
    extends: 'brn_stance', yaw: 16, sp: [28, -12, 0], pel: [0.15, -0.17, 0], hd: [-24, -4, 0],
    hr: [1.0, 0.26, 0.14, 1], pr: [-0.2, -0.4, -1], hl: [0.30, 0.30, 0.10, 1],
    fr: [-0.58, -0.76, -0.14, 1], fl: [0.42, -0.82, 0.12, 1],
  },
  brn_hikeLow: { extends: 'brn_stance', pel: [0.02, -0.30, 0], yaw: -42, sp: [36, 24, 0], hd: [-26, 16, 0], hr: [0.24, -0.34, 0.15, 1], pr: [-1, -0.2, -0.4] },
  brn_hikeUp: {
    extends: 'brn_cutUp', pel: [0.06, 0.04, 0], yaw: 26, sp: [-20, -24, 0], hd: [-30, 0, 0], hr: [0.24, 1.0, 0.08, 1],
    fr: [-0.06, -0.86, -0.05, 1], fl: [0.16, -1.0, 0.10, 1],
  },
  brn_axeWind: { // both fists clasped high behind the head
    extends: 'brn_stance', yaw: -10, sp: [-20, 0, 0], pel: [-0.03, -0.05, 0], hd: [-20, 4, 0],
    hr: [-0.04, 0.98, 0.07, 1], hl: [-0.04, 0.98, -0.05, 1], pr: [-1, 0.4, -0.3], pl: [-1, 0.4, 0.3],
  },
  brn_axe: {
    extends: 'brn_stance', yaw: 0, sp: [42, 0, 0], pel: [0.13, -0.25, 0], hd: [-34, 0, 0],
    hr: [0.82, -0.26, 0.07, 1], hl: [0.82, -0.26, -0.05, 1], pr: [-0.3, 0.5, -1], pl: [-0.3, 0.5, 1],
    fr: [-0.52, -0.78, -0.14, 1], fl: [0.46, -0.80, 0.14, 1],
  },
  brn_brace: { // gathering pressure
    extends: 'brn_stance', pel: [0, -0.22, 0], yaw: -10, sp: [32, 0, 0], hd: [-30, 0, 0],
    hr: [0.30, -0.55, 0.26, 1], hl: [0.30, -0.55, -0.20, 1], pr: [-1, -0.2, -0.5], pl: [-1, -0.2, 0.5],
    fr: [-0.24, -0.80, -0.20, 1], fl: [0.24, -0.80, 0.18, 1],
  },
  brn_vent: { // chest out, arms back, head thrown back: the steam goes up
    extends: 'brn_stance', pel: [0, -0.06, 0], yaw: -6, sp: [-24, 0, 0], hd: [-36, 0, 0],
    hr: [-0.30, -0.70, 0.46, 1], hl: [-0.30, -0.70, -0.40, 1], pr: [0.3, -0.2, -1], pl: [0.3, -0.2, 1],
    fr: [-0.22, -0.92, -0.20, 1], fl: [0.22, -0.92, 0.18, 1],
  },
  brn_blastWind: { extends: 'brn_stance', yaw: -40, sp: [26, 30, 0], pel: [-0.04, -0.20, 0], hr: [0.0, 0.0, 0.25, 1], hl: [0.10, 0.0, 0.10, 1], pr: [-1, -0.2, -0.4], pl: [-1, -0.2, 0.4] },
  brn_blast: { // both fists driven forward, steam everywhere
    extends: 'brn_stance', yaw: 0, sp: [14, 0, 0], pel: [0.12, -0.12, 0], hd: [-14, 0, 0],
    hr: [1.0, 0.36, 0.20, 1], hl: [1.0, 0.36, -0.14, 1], pr: [-0.2, -0.4, -1], pl: [-0.2, -0.4, 1],
    fr: [-0.50, -0.82, -0.14, 1], fl: [0.44, -0.84, 0.12, 1],
  },
  brn_grabReach: { extends: 'brn_stance', yaw: 0, sp: [16, 0, 0], pel: [0.06, -0.14, 0], hr: [0.92, 0.26, 0.40, 1], hl: [0.92, 0.26, -0.36, 1], pr: [-0.3, -1, -0.8], pl: [-0.3, -1, 0.8] },
  brn_hug: { // bear hug: arms wrapped round someone just in front
    extends: 'brn_stance', yaw: 0, sp: [8, 0, 0], pel: [0.04, -0.12, 0], hd: [-6, 0, 0],
    hr: [0.62, 0.10, -0.20, 1], hl: [0.62, 0.10, 0.24, 1], pr: [0, 0.2, -1], pl: [0, 0.2, 1],
    fr: [-0.24, -0.86, -0.18, 1], fl: [0.24, -0.86, 0.16, 1],
  },
  brn_hugLift: { extends: 'brn_hug', sp: [-26, 0, 0], pel: [-0.06, -0.04, 0], hd: [-24, 0, 0], hr: [0.56, 0.24, -0.22, 1], hl: [0.56, 0.24, 0.26, 1] },
  brn_squeeze: { extends: 'brn_hugLift', sp: [-30, 0, 0], hr: [0.48, 0.20, -0.30, 1], hl: [0.48, 0.20, 0.34, 1], hd: [-30, 0, 0] },
  brn_burst: { // the boiler goes: arms flung out, head back
    extends: 'brn_vent', sp: [-30, 0, 0], hd: [-40, 0, 0], pel: [-0.04, -0.04, 0],
    hr: [0.20, 0.50, 0.95, 1], hl: [0.20, 0.50, -0.90, 1], pr: [0, -1, 0], pl: [0, -1, 0],
  },
  brn_headbuttWind: { extends: 'brn_hug', sp: [-16, 0, 0], hd: [-26, 0, 0] },
  brn_headbutt: { extends: 'brn_hug', sp: [34, 0, 0], hd: [20, 0, 0], pel: [0.10, -0.16, 0] },
  brn_pound: { extends: 'brn_stance', yaw: -12, sp: [16, 4, 0], hd: [-20, 4, 0], hr: [0.44, 0.10, 0.06, 1], hl: [0.46, 0.08, -0.02, 1] },
  brn_poundHit: { extends: 'brn_pound', hr: [0.46, 0.06, 0.0, 1], hl: [0.46, 0.08, 0.02, 1] },
};

const shake = (t0, n, step, pose, amt) => Array.from({ length: n }, (_, k) => [t0 + k * step, { extends: pose, sp: [32, 0, k % 2 ? amt : -amt], hd: [-30, k % 2 ? 6 : -6, 0] }]);

export default {
  style: {},
  poses,
  look: { tint1: ['brannigan_top'], tint2: ['brannigan_bottom'], alts: [null, '#3b3b3b', '#4a3626', '#2e3e52', '#5a2a2a', '#555a40', '#2b2b2b', '#6e6e6e'] },
  states: {
    idle: { keys: [[0, 'brn_stance']], loop: true, clip: 'Idle_Loop', speed: 1.1 },
    guard: { keys: [[0, 'brn_guard']], blend: 4 },
    walkF: { clip: 'guard_walk_fwd', loop: true, speed: 1.25, over: 'brn_walkArms', keys: [[0, { clip: 'guard_walk_fwd' }]] },
    walkB: { clip: 'guard_walk_back', loop: true, speed: 0.95, over: 'brn_walkArms', keys: [[0, { clip: 'guard_walk_back' }]] },
    crouch: { keys: [[0, 'brn_crouch']], blend: 4 },
    prejump: { keys: [[0, 'brn_stance'], [3, { extends: 'brn_stance', pel: [0, -0.2, 0], sp: [26, 10, 0] }, 'out']], blend: 2 },
    jumpU: { keys: [[0, 'brn_tuck']], blend: 3 },
    jumpF: { keys: [[0, 'brn_tuck'], [10, { extends: 'brn_tuck', tilt: 18 }], [28, { extends: 'brn_tuck', tilt: 6 }]], blend: 3 },
    jumpB: { keys: [[0, 'brn_tuck'], [10, { extends: 'brn_tuck', tilt: -14 }], [28, { extends: 'brn_tuck', tilt: -4 }]], blend: 3 },
    land: { keys: [[0, { extends: 'brn_stance', pel: [0, -0.22, 0], sp: [28, 10, 0] }], [4, 'brn_stance']], blend: 2 },
    dash: { keys: [[0, { extends: 'brn_stance', sp: [30, 10, 0], pel: [0.06, -0.16, 0], fr: [-0.48, -0.80, -0.1, 1], fl: [0.48, -0.84, 0.1, 1] }], [11, 'brn_stance']], blend: 2 },
    dashEnd: { keys: [[0, 'brn_stance']] },
    block: { keys: [[0, { extends: 'brn_guard', pel: [-0.09, -0.17, 0], sp: [30, 6, 0] }], [6, 'brn_guard']], blend: 1 },
    cblock: { keys: [[0, { extends: 'brn_cguard', sp: [34, 6, 0] }], [6, 'brn_cguard']], blend: 1 },
    chit: { keys: [[0, { extends: 'brn_crouch', sp: [-6, 0, 10], hd: [-25, 0, 10] }], [12, 'brn_crouch']], blend: 1 },
    timeout: { keys: [[0, 'brn_stance']] },
    win: { keys: [[0, 'brn_stance'], [16, 'brn_hikeUp', 'out'], [60, { extends: 'brn_hikeUp', hr: [0.20, 1.0, 0.10, 1] }], [90, 'brn_vent']], blend: 6 },
    taunt: { keys: [[0, 'brn_stance'], [8, 'brn_pound'], [12, 'brn_poundHit', 'in'], [20, 'brn_pound'], [24, 'brn_poundHit', 'in'], [32, 'brn_pound'], [36, 'brn_poundHit', 'in'], [48, 'brn_vent', 'out'], [64, 'brn_vent'], [71, 'brn_stance']] },
  },
  moves: {
    st_L: { trail: 'hand_l', keys: [[0, 'brn_stance'], [2, 'brn_jabWind'], ['s', 'brn_jab', 'in'], ['a+1', 'brn_jab'], ['e', 'brn_stance', 'out']] },
    st_M: { trail: 'hand_l', keys: [[0, 'brn_stance'], [3, 'brn_hookWind'], ['s', 'brn_hook', 'in'], ['a+2', 'brn_hook'], ['e', 'brn_stance', 'out']] },
    st_H: { trail: 'hand_r', keys: [[0, 'brn_stance'], [5, 'brn_crossWind', 'out'], ['s', 'brn_cross', 'in'], ['a+4', 'brn_cross'], ['e', 'brn_stance', 'io']] },
    cr_L: { trail: 'foot_r', keys: [[0, 'brn_crouch'], [2, { extends: 'brn_crouch', fr: [0.4, -0.7, 0, 1] }], ['s', 'brn_kickLow', 'in'], ['a+1', 'brn_kickLow'], ['e', 'brn_crouch']] },
    cr_M: { trail: 'hand_r', keys: [[0, 'brn_crouch'], [3, 'brn_gutWind'], ['s', 'brn_gut', 'in'], ['a+2', 'brn_gut'], ['e', 'brn_crouch']] },
    cr_H: { trail: 'foot_r', keys: [[0, 'brn_crouch'], [5, { extends: 'brn_sweep', yaw: 10, fr: [0.5, -0.8, 0.3, 1] }], ['s', 'brn_sweep', 'in'], ['a+6', { extends: 'brn_sweep', yaw: 115 }], ['e', 'brn_crouch']] },
    j_L: { trail: 'foot_r', keys: [[0, 'brn_tuck'], ['s', 'brn_airKnee', 'out'], ['a', 'brn_airKnee'], ['e', 'brn_tuck']] },
    j_M: { trail: 'hand_r', keys: [[0, 'brn_tuck'], [4, 'brn_airUp'], ['s', 'brn_airHammer', 'in'], ['a', 'brn_airHammer'], ['e', 'brn_tuck']] },
    j_H: { trail: 'hand_r', keys: [[0, 'brn_tuck'], [5, 'brn_airAxeUp', 'out'], ['s', 'brn_airAxe', 'in'], ['a', 'brn_airAxe'], ['e', 'brn_tuck']] },
    overhand: { trail: 'hand_r', keys: [[0, 'brn_stance'], [9, 'brn_overhandWind', 'out'], ['s', 'brn_overhand', 'in'], ['a+5', 'brn_overhand'], ['e', 'brn_stance']] },
    steamcut: { trail: 'hand_r', keys: [[0, 'brn_stance'], [4, 'brn_cutLow', 'out'], ['s', 'brn_cutUp', 'in'], ['a+3', 'brn_cutUp'], ['e', 'brn_stance']] },
    ironlung: { trail: 'hand_r', keys: [[0, 'brn_stance'], [4, 'brn_lungWind', 'out'], ['s-2', { extends: 'brn_lungWind', pel: [0, -0.22, 0] }], ['s', 'brn_lung', 'in'], ['a+4', 'brn_lung'], ['e', 'brn_stance']] },
    rush: { trail: 'hand_r', keys: [[0, 'brn_stance'], [3, 'brn_rushWind', 'out'], ['s-2', { extends: 'brn_rush', hr: [0.6, 0.3, 0.14, 1] }], ['s', 'brn_rush', 'in'], ['a', 'brn_rush'], ['e', 'brn_stance']] },
    rush_EX: { trail: 'hand_r', keys: [[0, 'brn_stance'], [3, 'brn_rushWind', 'out'], ['s', 'brn_jab', 'in'], ['s+4', 'brn_crossWind'], ['s+6', 'brn_rush', 'in'], ['a', 'brn_rush'], ['e', 'brn_stance']] },
    hike: { trail: 'hand_r', keys: [[0, 'brn_stance'], [1, 'brn_hikeLow', 'out'], ['s', 'brn_hikeUp', 'in'], ['a+3', 'brn_hikeUp'], ['e', 'brn_stance']] },
    hike_EX: { trail: 'hand_r', keys: [[0, 'brn_stance'], [1, 'brn_hikeLow', 'out'], ['s', 'brn_cutUp', 'in'], ['s+3', { extends: 'brn_hikeLow', pel: [0.04, -0.2, 0] }], ['s+5', 'brn_hikeUp', 'in'], ['a+3', 'brn_hikeUp'], ['e', 'brn_stance']] },
    wrench: { trail: 'hand_r', keys: [[0, 'brn_stance'], [6, 'brn_axeWind', 'out'], ['s-3', { extends: 'brn_axeWind', sp: [-26, 0, 0] }], ['s', 'brn_axe', 'in'], ['a+6', 'brn_axe'], ['e', 'brn_stance']] },
    valve: { keys: [[0, 'brn_stance'], [6, 'brn_brace', 'out'], [10, 'brn_brace'], [13, 'brn_vent', 'in'], ['a', { extends: 'brn_vent', sp: [-20, 0, 6] }], ['e', 'brn_stance']] },
    rent: { trail: 'hand_r', keys: [[0, 'brn_stance'], [3, 'brn_rushWind', 'out'], ['s', 'brn_rush', 'in'], ['a+4', 'brn_rush'], ['e', 'brn_stance']] },
    pressure: { keys: [[0, 'brn_stance'], [3, { extends: 'brn_grabReach', hr: [0.6, 0.3, 0.5, 1], hl: [0.6, 0.3, -0.46, 1] }], ['s', 'brn_grabReach', 'in'], ['a+6', 'brn_grabReach'], ['e', 'brn_stance']] },
    redline: { keys: [[0, 'brn_stance'], [4, 'brn_brace', 'out'], ['s', 'brn_burst', 'in'], ['a+6', 'brn_burst'], ['e', 'brn_stance']] },
    throw: { keys: [[0, 'brn_stance'], ['s', 'brn_grabReach', 'out'], [10, 'brn_hug'], [22, 'brn_headbuttWind'], [30, 'brn_headbutt', 'in'], [38, 'brn_headbutt'], [44, 'brn_stance']] },
    bthrow: { keys: [[0, 'brn_stance'], ['s', 'brn_grabReach', 'out'], [12, 'brn_hug'], [24, { extends: 'brn_hugLift', spin: 120 }], [34, { extends: 'brn_blast', spin: 180 }, 'in'], [42, { extends: 'brn_blast', spin: 180 }], [48, { extends: 'brn_stance', spin: 180 }]] },
    breaker: { trail: 'hand_r', keys: [[0, 'brn_stance'], [8, 'brn_lungWind', 'out'], ['s', 'brn_lung', 'in'], ['a+8', 'brn_lung'], ['e', 'brn_stance']] },
    breakerRev: { keys: [[0, 'brn_guard'], ['s', 'brn_blast', 'in'], ['a+6', 'brn_blast'], ['e', 'brn_stance']] },
    taunt: { keys: [[0, 'brn_stance'], [8, 'brn_pound'], [12, 'brn_poundHit', 'in'], [20, 'brn_pound'], [24, 'brn_poundHit', 'in'], [32, 'brn_pound'], [36, 'brn_poundHit', 'in'], [48, 'brn_vent', 'out'], [64, 'brn_vent'], [71, 'brn_stance']] },
  },
  cine: {
    // Rent Goes Up: jab, cross, hook, a rising uppercut that takes him off the floor, then the steam blast
    rent: [
      [0, 'brn_rush'], [5, 'brn_jabWind'], [10, 'brn_jab', 'in'], [15, 'brn_crossWind'], [20, 'brn_cross', 'in'],
      [26, 'brn_hookWind'], [32, 'brn_hook', 'in'], [40, 'brn_hikeLow'], [48, { extends: 'brn_hikeUp', lift: 0.16 }, 'in'],
      [56, { extends: 'brn_hikeUp', lift: 0.26 }], [63, { extends: 'brn_blastWind', lift: 0.22 }], [70, { extends: 'brn_blast', lift: 0.1 }, 'in'],
      [86, 'brn_blast'], [98, 'brn_stance'],
    ],
    // Full Pressure: the bear hug, two squeezes, lifted off the floor, then the boiler goes
    pressure: [
      [0, 'brn_hug'], [16, 'brn_hugLift'], [32, 'brn_hug'], [40, 'brn_squeeze', 'in'], [56, 'brn_hug'], [74, 'brn_hugLift'],
      [84, { extends: 'brn_squeeze', lift: 0.05 }, 'in'], [100, 'brn_hug'], [122, { extends: 'brn_hugLift', lift: 0.10 }],
      ...shake(126, 6, 4, 'brn_hugLift', 6).map(([t, p]) => [t, { ...p, lift: 0.12, sp: [-24, 0, p.sp[2]] }]),
      [150, { extends: 'brn_burst', lift: 0.06 }, 'in'], [170, 'brn_burst'], [186, 'brn_stance'],
    ],
    // Red Line: the gauge climbs (he shakes), point-blank blast, then the second, bigger one
    redline: [
      [0, 'brn_brace'], ...shake(8, 10, 4, 'brn_brace', 8), [50, 'brn_burst', 'in'], [66, 'brn_burst'],
      [80, 'brn_brace'], ...shake(84, 4, 4, 'brn_brace', 10), [104, { extends: 'brn_burst', lift: 0.08 }, 'in'], [124, 'brn_burst'], [140, 'brn_stance'],
    ],
  },
};
