// Gary's animation set. A hunched, shifty merchant: the huge pack is his weapon (Backpack Bump, Pack Drop,
// Backpack Swing), his shield (he turns it toward hits when blocking) and his shop (every toss, chest and
// crate comes out of it). Keys: 's' first active frame, 'a' last active, 'e' end.
const KNEE = [1, 0.1, 0];
const ARM_R = [-0.3, -1, -0.6], ARM_L = [-0.3, -1, 0.6];
const LOW_R = [-0.7, -0.5, -0.6]; // elbow back for a low hand

const poses = {
  // ---------------------------------------------------------------- stance and movement
  gary_stance: {
    clip: 'Idle_Loop', ct: 0.4,
    pel: [0, -0.10, 0], yaw: -22, sp: [16, 12, 0], hd: [-8, 10, 0],
    hr: [0.34, -0.52, 0.14, 1], hl: [0.62, 0.02, 0.02, 1], pr: LOW_R, pl: ARM_L,
    fr: [-0.28, -0.87, -0.16, 1], fl: [0.32, -0.86, 0.12, 1], kr: KNEE, kl: KNEE,
  },
  gary_walkArms: { hr: [0.32, -0.52, 0.14, 0.9], hl: [0.58, 0.0, 0.04, 0.9], pr: LOW_R, pl: ARM_L, sp: [14, 10, 0], yaw: -16 },
  gary_guard: { // turns a shoulder and the pack into the hit, arms over the head
    extends: 'gary_stance', spin: 62, pel: [-0.04, -0.14, 0], sp: [26, 6, 0], hd: [12, -20, 0],
    hr: [0.30, 0.55, 0.30, 1], hl: [0.40, 0.62, 0.05, 1], pr: [0.1, -1, -0.4], pl: [0.1, -1, 0.4],
  },
  gary_crouch: {
    clip: 'Crouch_Idle_Loop', ct: 0.3, yaw: -20, sp: [22, 10, 0], hd: [-14, 8, 0],
    hr: [0.38, -0.30, 0.20, 1], hl: [0.60, -0.05, 0.04, 1], pr: LOW_R, pl: ARM_L,
  },
  gary_cguard: {
    extends: 'gary_crouch', spin: 55, sp: [34, 4, 0], hd: [8, -14, 0],
    hr: [0.30, 0.50, 0.30, 1], hl: [0.36, 0.56, 0.06, 1], pr: [0.1, -1, -0.4], pl: [0.1, -1, 0.4],
  },
  gary_reachPack: { // right hand over the shoulder, into the pack
    extends: 'gary_stance', yaw: -8, sp: [6, 26, -6], hd: [-6, 30, 0],
    hr: [-0.18, 0.85, -0.10, 1], pr: [0.3, 0.2, -1], hl: [0.50, -0.05, 0.05, 1],
  },
  gary_reachPack2: { // both hands over the shoulders
    extends: 'gary_stance', yaw: 0, sp: [4, 0, 0], hd: [-14, 0, 0], pel: [0, -0.06, 0],
    hr: [-0.12, 0.88, -0.18, 1], hl: [-0.12, 0.88, 0.18, 1], pr: [0.4, 0.3, -1], pl: [0.4, 0.3, 1],
  },

  // ---------------------------------------------------------------- normals
  gary_slapWind: { extends: 'gary_stance', yaw: -12, sp: [12, 4, 0], hl: [0.28, 0.24, -0.30, 1], pl: [-0.2, -0.2, 1] },
  gary_slapOut: { extends: 'gary_stance', yaw: -40, sp: [10, 24, 0], pel: [0.03, -0.10, 0], hl: [0.98, 0.30, 0.10, 1], pl: [-0.2, -0.5, 1] },
  gary_sampleWind: { extends: 'gary_stance', yaw: -38, sp: [14, 26, 0], hr: [-0.05, -0.30, -0.05, 1], pr: [-1, -0.2, -0.4] },
  gary_sampleOut: {
    extends: 'gary_stance', yaw: 8, sp: [14, -12, 0], pel: [0.07, -0.11, 0], hd: [-10, -4, 0],
    hr: [1.0, 0.12, 0.16, 1], pr: [-0.2, -0.6, -1], hl: [0.25, -0.20, 0.10, 1],
    fr: [-0.42, -0.84, -0.14, 1], fl: [0.38, -0.84, 0.12, 1],
  },
  gary_bumpWind: { extends: 'gary_stance', spin: -28, pel: [0.02, -0.16, 0], sp: [26, -10, 0], hr: [0.30, -0.30, 0.25, 1], hl: [0.45, -0.25, 0.15, 1] },
  gary_bumpOut: { // back to the opponent, the pack slammed into them
    extends: 'gary_stance', spin: 165, pel: [-0.10, -0.08, 0], sp: [-24, 0, 0], hd: [-20, 30, 0],
    hr: [0.28, -0.05, -0.28, 1], hl: [0.28, -0.05, 0.28, 1], pr: [0.3, -1, -0.6], pl: [0.3, -1, 0.6],
    fr: [-0.10, -0.92, -0.18, 1], fl: [0.36, -0.82, 0.16, 1],
  },
  gary_kickLow: { extends: 'gary_crouch', yaw: 10, sp: [14, 12, 6], fr: [0.80, -0.84, 0.0, 1], kr: [0.3, 1, 0], hr: [0.25, -0.10, 0.25, 1] },
  gary_swatWind: { extends: 'gary_crouch', yaw: -40, sp: [26, 28, 0], hr: [-0.25, -0.55, -0.15, 1], pr: [-1, 0, -0.3] },
  gary_swatOut: {
    extends: 'gary_crouch', yaw: 22, sp: [40, -22, 0], pel: [0.08, -0.04, 0],
    hr: [0.95, -0.80, 0.06, 1], pr: [0, 0.6, -1], hl: [0.35, -0.30, 0.20, 1],
  },
  gary_sweep: {
    extends: 'gary_crouch', yaw: 72, pel: [0, -0.12, 0], sp: [26, 10, 18],
    fr: [0.96, -0.86, 0.15, 1], kr: [0.2, 1, 0.3], hr: [-0.15, -0.55, -0.10, 1], hl: [0.15, -0.75, 0.30, 1],
  },
  gary_chopUp: { // one-hand overhead wind-up, leaning back
    extends: 'gary_stance', yaw: -14, sp: [-14, 14, 0], pel: [-0.03, -0.06, 0], hd: [-14, 8, 0],
    hr: [0.05, 1.0, 0.10, 1], pr: [-1, 0.4, -0.3], hl: [0.45, 0.10, 0.05, 1],
  },
  gary_chopDown: {
    extends: 'gary_stance', yaw: 6, sp: [34, -6, 0], pel: [0.10, -0.18, 0], hd: [-26, 0, 0],
    hr: [0.92, -0.10, 0.12, 1], pr: [-0.3, 0.5, -1], hl: [0.30, -0.40, 0.15, 1],
    fr: [-0.46, -0.80, -0.12, 1], fl: [0.42, -0.82, 0.12, 1],
  },
  gary_heaveLow: { extends: 'gary_stance', pel: [0.02, -0.26, 0], yaw: -10, sp: [34, 6, 0], hr: [0.40, -0.75, 0.15, 1], hl: [0.40, -0.75, -0.05, 1], pr: LOW_R, pl: [-0.7, -0.5, 0.6] },
  gary_heaveUp: {
    extends: 'gary_stance', pel: [0.05, 0.04, 0], yaw: 4, sp: [-16, -4, 0], hd: [-24, 0, 0],
    hr: [0.35, 0.98, 0.16, 1], hl: [0.35, 0.98, -0.06, 1], pr: [1, 0, -0.4], pl: [1, 0, 0.4],
    fr: [-0.12, -0.84, -0.08, 1], kr: [1, 0.2, 0], fl: [0.22, -0.98, 0.10, 1],
  },
  gary_airKnee: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [12, 10, 0],
    fr: [0.55, -0.05, 0, 1], kr: [1, 0.3, 0], fl: [-0.15, -0.70, 0.1, 1], kl: [1, -0.2, 0],
    hr: [0.30, 0.10, 0.25, 1], hl: [0.45, 0.20, 0, 1], pr: ARM_R, pl: ARM_L,
  },
  gary_airSwat: { extends: 'gary_airKnee', sp: [26, 10, 0], hl: [0.90, -0.10, 0.02, 1], pl: [-0.5, 0.2, 1], hr: [0.15, 0.30, 0.25, 1] },
  gary_airSwatWind: { extends: 'gary_airKnee', sp: [-6, 16, 0], hl: [0.10, 0.85, 0.05, 1], pl: [-1, 0.3, 0.4] },
  gary_packSit: { // tipped back in the air, sitting on the pack: it lands on whoever is under or behind him
    extends: 'gary_airKnee', tilt: -70, sp: [-10, 0, 0], hd: [24, 0, 0],
    fr: [0.62, 0.10, -0.10, 1], fl: [0.62, 0.15, 0.12, 1], kr: [1, 0.6, 0], kl: [1, 0.6, 0],
    hr: [0.30, 0.55, -0.35, 1], hl: [0.30, 0.55, 0.35, 1],
  },

  // ---------------------------------------------------------------- specials
  gary_lobWind: { extends: 'gary_stance', pel: [-0.02, -0.17, 0], yaw: -30, sp: [26, 18, 0], hr: [-0.35, -0.62, -0.06, 1], pr: [-0.2, -0.8, -0.6], hd: [-18, 16, 0] },
  gary_lobOut: {
    extends: 'gary_stance', pel: [0.05, -0.04, 0], yaw: -4, sp: [-6, -6, 0], hd: [-18, 0, 0],
    hr: [0.82, 0.55, 0.12, 1], pr: [-0.2, -1, -0.6], hl: [0.30, -0.20, 0.15, 1],
    fr: [-0.36, -0.86, -0.12, 1], fl: [0.36, -0.90, 0.12, 1],
  },
  gary_flingWind: { extends: 'gary_stance', yaw: 18, sp: [18, 34, 0], hr: [0.30, -0.18, 0.55, 1], pr: [0, -1, 0.3], hl: [0.10, -0.40, 0.25, 1] },
  gary_flingOut: {
    extends: 'gary_stance', yaw: -36, sp: [8, -10, 0], pel: [0.04, -0.10, 0],
    hr: [0.96, 0.20, -0.30, 1], pr: [-0.2, -1, -0.4], hl: [-0.05, -0.30, 0.25, 1],
    fr: [-0.40, -0.85, -0.14, 1], fl: [0.36, -0.86, 0.12, 1],
  },
  gary_whirl: { extends: 'gary_chopUp', sp: [-18, 22, 0], hr: [-0.25, 0.92, -0.20, 1], pr: [0, 0.3, -1] },
  gary_hurl: {
    extends: 'gary_stance', yaw: 14, sp: [26, -16, 0], pel: [0.10, -0.14, 0],
    hr: [0.95, 0.24, 0.10, 1], pr: [-0.3, -0.4, -1], hl: [0.10, -0.30, 0.15, 1],
    fr: [-0.48, -0.80, -0.12, 1], fl: [0.40, -0.84, 0.12, 1],
  },
  gary_haggle: { // "wait, wait — let's talk": palm up, leaning back, the other hand on his heart
    extends: 'gary_stance', pel: [-0.05, -0.08, 0], yaw: -30, sp: [-6, 18, -4], hd: [6, 14, 10],
    hl: [0.66, 0.50, -0.04, 1], pl: [-0.3, -1, 0.4], hr: [0.56, 0.42, 0.26, 1], pr: [-0.2, -1, -0.8],
  },
  gary_haggle2: { extends: 'gary_haggle', sp: [-4, 22, -6], hd: [4, 20, 14], hl: [0.70, 0.56, 0.02, 1], hr: [0.60, 0.48, 0.24, 1] },
  gary_shake: { // the handshake
    extends: 'gary_stance', yaw: -8, sp: [14, 2, 0], pel: [0.03, -0.10, 0], hd: [-12, 0, 0],
    hr: [0.82, 0.02, 0.12, 1], pr: [-0.3, -1, -0.6], hl: [0.55, 0.06, 0.18, 1],
  },
  gary_shakeUp: { extends: 'gary_shake', hr: [0.82, 0.22, 0.12, 1], hl: [0.56, 0.22, 0.18, 1] },
  gary_shoveWind: { extends: 'gary_stance', yaw: -6, pel: [-0.06, -0.16, 0], sp: [8, 0, 0], hr: [0.30, 0.25, 0.25, 1], hl: [0.30, 0.25, -0.10, 1], pr: [-1, -0.4, -0.5], pl: [-1, -0.4, 0.5] },
  gary_shove: {
    extends: 'gary_stance', yaw: 0, pel: [0.12, -0.12, 0], sp: [24, 0, 0], hd: [-22, 0, 0],
    hr: [1.0, 0.25, 0.20, 1], hl: [1.0, 0.25, -0.12, 1], pr: [-0.3, -1, -0.8], pl: [-0.3, -1, 0.8],
    fr: [-0.50, -0.80, -0.14, 1], fl: [0.36, -0.86, 0.12, 1],
  },
  gary_setDown: { // crouched, both hands setting something on the floor in front
    clip: 'Crouch_Idle_Loop', ct: 0.3, yaw: -6, sp: [44, 0, 0], hd: [-30, 0, 0], pel: [0.04, -0.04, 0],
    hr: [0.78, -0.92, 0.20, 1], hl: [0.78, -0.92, -0.06, 1], pr: [-0.5, 0.2, -1], pl: [-0.5, 0.2, 1],
  },
  gary_swingWind: {
    extends: 'gary_stance', pel: [0, -0.22, 0], yaw: 0, sp: [30, 0, 0], hd: [-26, 0, 0],
    hr: [0.10, 0.30, -0.30, 1], hl: [0.10, 0.30, 0.30, 1], pr: [0.2, -1, -0.3], pl: [0.2, -1, 0.3],
  },
  gary_swingUp: { // arms up, heaving the pack round over his head
    extends: 'gary_stance', pel: [0, 0.05, 0], yaw: 0, sp: [-26, 0, 0], hd: [-30, 0, 0],
    hr: [0.10, 1.0, -0.25, 1], hl: [0.10, 1.0, 0.25, 1], pr: [0, 0, -1], pl: [0, 0, 1],
    fr: [-0.14, -0.94, -0.14, 1], fl: [0.18, -0.96, 0.14, 1], kr: KNEE, kl: KNEE,
  },
  gary_jumpReach: { extends: 'gary_airKnee', sp: [0, 24, 0], hr: [-0.15, 0.85, -0.10, 1], pr: [0.3, 0.2, -1], hd: [-6, 28, 0] },
  gary_crateThrow: {
    extends: 'gary_airKnee', sp: [34, 0, 0], hd: [-20, 0, 0],
    hr: [0.85, -0.45, 0.20, 1], hl: [0.85, -0.45, -0.10, 1], pr: [-0.3, 0.3, -1], pl: [-0.3, 0.3, 1],
  },

  // ---------------------------------------------------------------- supers
  gary_packOpen: { // flings the pack open overhead: arms up and forward, chest to the sky
    extends: 'gary_stance', pel: [0.02, 0.0, 0], yaw: -6, sp: [-28, 0, 0], hd: [-34, 0, 0], lift: 0.04,
    hr: [0.60, 0.85, -0.35, 1], hl: [0.60, 0.85, 0.40, 1], pr: [-0.3, 0, -1], pl: [-0.3, 0, 1],
    fr: [-0.22, -0.95, -0.16, 1], fl: [0.24, -0.95, 0.16, 1],
  },
  gary_hawk: { // pointing at the customer, the other hand up: "Everything must go!"
    extends: 'gary_stance', yaw: -30, sp: [6, 20, 0], hd: [-12, 12, 0],
    hr: [0.15, 0.95, -0.10, 1], pr: [0, 0, -1], hl: [1.0, 0.30, -0.05, 1], pl: [-0.2, -0.6, 1],
  },
  gary_packFront: { // the pack (mimic) swung round toward the opponent, Gary leaning back behind it
    extends: 'gary_stance', spin: 180, pel: [-0.06, -0.10, 0], sp: [-26, 0, 0], hd: [-10, 0, 0],
    hr: [0.10, 0.55, -0.30, 1], hl: [0.10, 0.55, 0.30, 1], pr: [0.3, -1, -0.6], pl: [0.3, -1, 0.6],
    fr: [-0.06, -0.92, -0.18, 1], fl: [0.34, -0.84, 0.16, 1],
  },
  gary_chomp: { extends: 'gary_packFront', sp: [-46, 0, 0], pel: [-0.16, -0.18, 0], fr: [0.14, -0.86, -0.18, 1], fl: [0.46, -0.76, 0.16, 1] },
  gary_chew: { extends: 'gary_packFront', sp: [-14, 0, 8], pel: [-0.02, -0.06, 0] },
  gary_ledger: { // reading the golden ledger
    extends: 'gary_stance', yaw: -10, sp: [22, 4, 0], hd: [-30, 0, 0],
    hr: [0.48, -0.20, 0.16, 1], hl: [0.48, -0.20, -0.06, 1], pr: [-0.5, -1, -0.5], pl: [-0.5, -1, 0.5],
  },
  gary_lick: { extends: 'gary_ledger', hd: [-14, 0, 0], hr: [0.25, 0.30, 0.20, 1], pr: [0, -1, -1] },
  gary_point: { extends: 'gary_stance', yaw: -26, sp: [4, 16, 0], hd: [-10, 10, 0], hr: [0.40, -0.10, 0.30, 1], hl: [1.0, 0.36, 0.0, 1], pl: [-0.2, -0.6, 1] },
  gary_bookUp: {
    extends: 'gary_stance', yaw: 0, sp: [-18, 0, 0], hd: [-26, 0, 0], pel: [0, -0.04, 0],
    hr: [0.15, 1.0, -0.12, 1], hl: [0.15, 1.0, 0.12, 1], pr: [-1, 0.4, -0.3], pl: [-1, 0.4, 0.3],
  },
  gary_bookSlam: {
    extends: 'gary_stance', yaw: 0, sp: [38, 0, 0], pel: [0.10, -0.22, 0], hd: [-30, 0, 0],
    hr: [0.90, -0.15, 0.16, 1], hl: [0.90, -0.15, -0.06, 1], pr: [-0.3, 0.5, -1], pl: [-0.3, 0.5, 1],
    fr: [-0.50, -0.78, -0.14, 1], fl: [0.44, -0.80, 0.14, 1],
  },
  gary_bow: { extends: 'gary_stance', yaw: -6, sp: [40, 0, 0], hd: [-10, 0, 0], hr: [0.20, -0.40, 0.30, 1], hl: [0.65, -0.35, 0.10, 1] },
};

// Backpack Swing spins once per hit (L 1, M/H 2, EX 3)
function swing(n) {
  return {
    trail: 'spine_03',
    keys: [
      [0, 'gary_stance'], [2, 'gary_swingWind', 'out'],
      ['s', { extends: 'gary_swingUp', spin: -120 }, 'in'],
      ...Array.from({ length: n }, (_, k) => [`s+${k * 7 + 4}`, { extends: 'gary_swingUp', spin: -120 - 360 * (k + 1) + 120 }, 'lin']),
      ['a+4', { extends: 'gary_swingUp', spin: -360 * n - 20, sp: [-10, 0, 0] }, 'out'],
      ['e', { extends: 'gary_stance', spin: -360 * n }],
    ],
  };
}

const tossKeys = (wind, out) => [
  [0, 'gary_stance'], [4, 'gary_reachPack', 'out'], ['s-4', wind, 'io'], ['s', out, 'in'], ['s+7', out], ['e', 'gary_stance'],
];

export default {
  style: {},
  poses,
  look: { trail: 'spine_03' },
  states: {
    idle: { keys: [[0, 'gary_stance']], loop: true, clip: 'Idle_Loop', speed: 0.8 },
    guard: { keys: [[0, 'gary_guard']], blend: 4 },
    walkF: { clip: 'guard_walk_fwd', loop: true, speed: 1.0, over: 'gary_walkArms', keys: [[0, { clip: 'guard_walk_fwd' }]] },
    walkB: { clip: 'guard_walk_back', loop: true, speed: 0.9, over: 'gary_walkArms', keys: [[0, { clip: 'guard_walk_back' }]] },
    crouch: { keys: [[0, 'gary_crouch']], blend: 4 },
    // no flips with that pack: a tucked hop, leaning into the jump (positive tilt pitches forward)
    jumpU: { keys: [[0, 'jumpUp']], blend: 3 },
    jumpF: { keys: [[0, 'jumpUp'], [9, { extends: 'jumpUp', tilt: 22, sp: [20, 10, 0] }], [28, { extends: 'jumpUp', tilt: 6 }]], blend: 3 },
    jumpB: { keys: [[0, 'jumpUp'], [9, { extends: 'jumpUp', tilt: -16, sp: [0, 10, 0] }], [28, { extends: 'jumpUp', tilt: -4 }]], blend: 3 },
    prejump: { keys: [[0, 'gary_stance'], [4, { extends: 'gary_stance', pel: [0, -0.2, 0], sp: [24, 10, 0] }, 'out']], blend: 2 },
    land: { keys: [[0, { extends: 'gary_stance', pel: [0, -0.2, 0], sp: [26, 10, 0] }], [4, 'gary_stance']], blend: 2 },
    dash: { keys: [[0, { extends: 'gary_stance', sp: [28, 8, 0], pel: [0.05, -0.14, 0], fr: [-0.45, -0.80, -0.1, 1], fl: [0.45, -0.85, 0.1, 1] }], [14, 'gary_stance']], blend: 2 },
    dashEnd: { keys: [[0, 'gary_stance']] },
    block: { keys: [[0, { extends: 'gary_guard', spin: 74, pel: [-0.10, -0.16, 0], sp: [32, 6, 0] }], [7, 'gary_guard']], blend: 2 },
    cblock: { keys: [[0, { extends: 'gary_cguard', spin: 66, sp: [40, 4, 0] }], [7, 'gary_cguard']], blend: 2 },
    chit: { keys: [[0, { extends: 'gary_crouch', sp: [-6, 0, 10], hd: [-25, 0, 10] }], [12, 'gary_crouch']], blend: 1 },
    timeout: { keys: [[0, 'gary_stance']] },
    intro: { keys: [[0, { clip: 'Idle_Talking_Loop', cf: 0 }]], loop: true, clip: 'Idle_Talking_Loop' },
    win: { keys: [[0, { clip: 'Dance_Loop', cf: 0 }]], loop: true, clip: 'Dance_Loop', speed: 0.9, blend: 6 },
    taunt: { keys: [[0, 'gary_stance'], [10, { extends: 'gary_point', spin: 120 }], [40, { extends: 'gary_hawk', spin: 150 }], [62, { extends: 'gary_bow', spin: 0 }], [71, 'gary_stance']] },
  },
  moves: {
    st_L: { trail: 'hand_l', keys: [[0, 'gary_stance'], [2, 'gary_slapWind'], ['s', 'gary_slapOut', 'in'], ['a+1', 'gary_slapOut'], ['e', 'gary_stance', 'out']] },
    st_M: { trail: 'hand_r', keys: [[0, 'gary_stance'], [4, 'gary_sampleWind'], ['s', 'gary_sampleOut', 'in'], ['a+2', 'gary_sampleOut'], ['e', 'gary_stance', 'out']] },
    st_H: { trail: 'spine_03', keys: [[0, 'gary_stance'], [7, 'gary_bumpWind', 'out'], ['s', 'gary_bumpOut', 'in'], ['a+3', { extends: 'gary_bumpOut', spin: 185 }], ['e-6', { extends: 'gary_stance', spin: 330 }, 'io'], ['e', { extends: 'gary_stance', spin: 360 }]] },
    cr_L: { trail: 'foot_r', keys: [[0, 'gary_crouch'], [2, { extends: 'gary_crouch', fr: [0.4, -0.7, 0, 1] }], ['s', 'gary_kickLow', 'in'], ['a+1', 'gary_kickLow'], ['e', 'gary_crouch']] },
    cr_M: { trail: 'hand_r', keys: [[0, 'gary_crouch'], [4, 'gary_swatWind'], ['s', 'gary_swatOut', 'in'], ['a+2', 'gary_swatOut'], ['e', 'gary_crouch']] },
    cr_H: { trail: 'foot_r', keys: [[0, 'gary_crouch'], [6, { extends: 'gary_sweep', yaw: 10, fr: [0.5, -0.8, 0.3, 1] }], ['s', 'gary_sweep', 'in'], ['a+6', { extends: 'gary_sweep', yaw: 115 }], ['e', 'gary_crouch']] },
    j_L: { trail: 'foot_r', keys: [[0, 'jumpUp'], ['s', 'gary_airKnee', 'out'], ['a', 'gary_airKnee'], ['e', 'jumpUp']] },
    j_M: { trail: 'hand_l', keys: [[0, 'jumpUp'], [4, 'gary_airSwatWind'], ['s', 'gary_airSwat', 'in'], ['a', 'gary_airSwat'], ['e', 'jumpUp']] },
    j_H: { trail: 'spine_03', keys: [[0, 'jumpUp'], [5, { extends: 'gary_airKnee', tilt: 18, sp: [24, 0, 0] }, 'out'], ['s', 'gary_packSit', 'in'], ['a', { extends: 'gary_packSit', tilt: -82 }], ['e', { extends: 'jumpUp', tilt: 0 }]] },
    hatswat: { trail: 'hand_r', keys: [[0, 'gary_stance'], [11, 'gary_chopUp', 'out'], ['s', 'gary_chopDown', 'in'], ['a+5', 'gary_chopDown'], ['e', 'gary_stance']] },
    upsell: { trail: 'hand_r', keys: [[0, 'gary_stance'], [5, 'gary_heaveLow', 'out'], ['s', 'gary_heaveUp', 'in'], ['a+3', 'gary_heaveUp'], ['e', 'gary_stance']] },
    toss_pot: { trail: 'hand_r', keys: tossKeys('gary_lobWind', 'gary_lobOut') },
    toss_scroll: { trail: 'hand_r', keys: tossKeys('gary_flingWind', 'gary_flingOut') },
    toss_chain: { trail: 'hand_r', keys: tossKeys('gary_whirl', 'gary_hurl') },
    haggle: { keys: [[0, 'gary_stance'], [3, 'gary_haggle', 'out'], ['a-4', 'gary_haggle2', 'io'], ['a', 'gary_haggle'], ['e', 'gary_stance']] },
    // counter success (a grab: frames are grab frames): handshake, three pumps, then the shove
    haggle_deal: { keys: [[0, 'gary_haggle'], [3, 'gary_shake', 'out'], [7, 'gary_shakeUp'], [10, 'gary_shake'], [13, 'gary_shakeUp'], [16, 'gary_shake'], [20, 'gary_shoveWind'], [22, 'gary_shove', 'in'], [30, 'gary_shove'], [36, 'gary_stance']] },
    haggle_dealEX: { keys: [[0, 'gary_haggle'], [3, 'gary_shake', 'out'], [7, 'gary_shakeUp'], [10, 'gary_shake'], [13, 'gary_shakeUp'], [16, 'gary_shake'], [21, 'gary_shoveWind'], [24, 'gary_shove', 'in'], [34, 'gary_shove'], [40, 'gary_stance']] },
    chest: { keys: [[0, 'gary_stance'], [5, 'gary_reachPack2', 'out'], [11, 'gary_setDown', 'io'], ['s+4', 'gary_setDown'], ['e', 'gary_stance']] },
    swing_L: swing(1), swing_M: swing(2), swing_H: swing(2), swing_EX: swing(3),
    crate: { keys: [[0, 'jumpUp'], [4, 'gary_jumpReach', 'out'], ['s', 'gary_crateThrow', 'in'], ['s+6', 'gary_crateThrow'], ['e', 'jumpUp']] },
    clearance: { trail: 'hand_r', keys: [[0, 'gary_stance'], [4, 'gary_reachPack2', 'out'], ['s', 'gary_packOpen', 'in'], ['s+10', { extends: 'gary_packOpen', lift: 0 }], [26, 'gary_hawk', 'io'], [44, { extends: 'gary_hawk', hl: [1.0, 0.40, 0.05, 1] }], ['e', 'gary_stance']] },
    mustgo: { trail: 'spine_03', keys: [[0, 'gary_stance'], [5, { extends: 'gary_reachPack2', pel: [0, -0.16, 0] }, 'out'], ['s', 'gary_packFront', 'in'], ['a+4', 'gary_chomp'], ['e', 'gary_stance']] },
    offer: { keys: [[0, 'gary_stance'], [7, 'gary_ledger', 'out'], ['s', 'gary_point', 'in'], ['a+6', 'gary_point'], ['e', 'gary_stance']] },
    throw: { keys: [[0, 'gary_stance'], ['s', 'gary_shake', 'out'], [10, 'gary_shakeUp'], [16, 'gary_bumpWind'], [26, 'gary_bumpOut', 'in'], [34, { extends: 'gary_bumpOut', spin: 190 }], [44, { extends: 'gary_stance', spin: 360 }]] },
    bthrow: { keys: [[0, 'gary_stance'], ['s', 'gary_shake', 'out'], [14, { extends: 'gary_shake', spin: 90 }], [28, { extends: 'gary_hurl', spin: 180 }, 'in'], [40, { extends: 'gary_hurl', spin: 180 }], [48, { extends: 'gary_stance', spin: 180 }]] },
    breaker: { trail: 'spine_03', keys: [[0, 'gary_stance'], [10, 'gary_bumpWind', 'out'], ['s', 'gary_bumpOut', 'in'], ['a+8', 'gary_bumpOut'], ['e', { extends: 'gary_stance', spin: 360 }]] },
    breakerRev: { keys: [[0, 'gary_guard'], ['s', 'gary_shove', 'in'], ['a+6', 'gary_shove'], ['e', 'gary_stance']] },
    taunt: { keys: [[0, 'gary_stance'], [10, { extends: 'gary_point', spin: 120 }], [40, { extends: 'gary_hawk', spin: 150 }], [62, { extends: 'gary_bow', spin: 0 }], [71, 'gary_stance']] },
  },
  cine: {
    // Clearance Sale has no cinematic (the stock really falls); Everything Must Go: the pack is a mimic
    mustgo: [
      [0, 'gary_packFront'], [14, { extends: 'gary_chomp', sp: [-60, 0, 0], lift: 0.1 }], [26, { extends: 'gary_chomp', lift: 0.12 }],
      [30, { extends: 'gary_packFront', sp: [10, 0, 0], pel: [0.12, -0.2, 0] }, 'in'], [40, 'gary_chew'], [50, 'gary_packFront'],
      [62, { extends: 'gary_chomp', lift: 0.06 }], [72, { extends: 'gary_chew', sp: [12, 0, 10] }, 'in'], [80, 'gary_chew'],
      [90, { extends: 'gary_chomp', lift: 0.06 }], [100, { extends: 'gary_chew', sp: [12, 0, -10] }, 'in'], [106, 'gary_chew'],
      [112, { extends: 'gary_chew', spin: 200 }], [128, { extends: 'gary_chomp', spin: 170, sp: [-60, 0, 0] }],
      [150, { extends: 'gary_shove', spin: 0 }, 'in'], [162, 'gary_hawk'], [175, 'gary_stance'],
    ],
    offer: [
      [0, 'gary_ledger'], [14, 'gary_lick'], [24, 'gary_ledger'], [40, 'gary_point', 'in'], [48, { extends: 'gary_point', hl: [1.0, 0.5, 0.0, 1] }],
      [70, 'gary_bookUp', 'io'], [100, { extends: 'gary_bookUp', lift: 0.08 }], [118, 'gary_bookSlam', 'in'], [136, 'gary_bookSlam'], [150, 'gary_bow'],
    ],
  },
};
