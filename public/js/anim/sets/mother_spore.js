// Mother Spore's animation set. A tall, unhurried fungal matriarch: upright posture, the mushroom-stalk staff in
// her right hand (its head leads every strike), the left hand doing the conjuring (cloud, roots, sporelings).
// Staff angles come from weapon-pack clips (the hand's grip is clip-driven); IK places the left hand, feet, spine.
// Keys: 's' first active frame, 'a' last active, 'e' end.
const KNEE = [1, 0.1, 0];
const ARM_R = [-0.3, -1, -0.6], ARM_L = [-0.3, -1, 0.6];
const FEET = { fr: [-0.12, -0.95, -0.12, 1], fl: [0.16, -0.95, 0.10, 1], kr: KNEE, kl: KNEE };

const poses = {
  // ---------------------------------------------------------------- stance and movement
  ms_stance: { // staff tilted forward at her side, the left hand open in front of her: "hush now"
    clip: 'spear_carry_Loop', ct: 0.6,
    pel: [0, -0.03, 0], yaw: 10, sp: [3, -6, 0], hd: [6, -8, 0],
    hl: [0.42, -0.18, 0.30, 1], pl: ARM_L, ...FEET,
  },
  ms_hush: { extends: 'ms_stance', hd: [10, -14, 4], hl: [0.25, 0.72, 0.62, 1], pl: [-0.2, -1, 0.3] },
  ms_walkArms: { hl: [0.40, -0.20, 0.30, 0.9], pl: ARM_L, sp: [2, -4, 0], hd: [4, -6, 0], yaw: 6 },
  ms_guard: { // the staff held across in front, braced
    clip: 'Sword_Block', cf: 0.4,
    pel: [-0.04, -0.08, 0], yaw: 8, sp: [10, -4, 0], hd: [8, -6, 0],
    hl: [0.48, 0.36, 0.02, 1], pl: [0.1, -1, 0.4], fr: [-0.24, -0.90, -0.14, 1], fl: [0.24, -0.90, 0.12, 1], kr: KNEE, kl: KNEE,
  },
  ms_crouch: { // sinks into her skirts, staff low and level
    clip: 'Crouch_Idle_Loop', ct: 0.3, yaw: 12, sp: [10, -6, 0], hd: [-4, -8, 0],
    hl: [0.46, -0.30, 0.20, 1], pl: ARM_L,
  },
  ms_cguard: { extends: 'ms_crouch', sp: [22, -2, 0], hd: [6, -4, 0], hl: [0.45, 0.30, 0.05, 1], pl: [0.1, -1, 0.4] },
  ms_prejump: { extends: 'ms_stance', pel: [0, -0.14, 0], sp: [14, -6, 0], hl: [0.30, -0.45, 0.35, 1] },
  ms_jump: { // skirts gathered, staff held high like a parasol
    clip: 'club_skill_club_bonk', cf: 0.1, sp: [-4, 0, 0], hd: [6, 0, 0],
    hl: [0.10, 0.10, 0.85, 1], pl: [-0.2, -1, 0.2],
    fr: [0.05, -0.80, -0.08, 1], fl: [0.18, -0.72, 0.08, 1], kr: KNEE, kl: KNEE,
  },
  ms_jumpTuck: { extends: 'ms_jump', fr: [0.20, -0.55, -0.08, 1], fl: [0.30, -0.50, 0.08, 1], sp: [8, 0, 0] },
  ms_land: { extends: 'ms_stance', pel: [0, -0.16, 0], sp: [14, -6, 0] },
  ms_dash: { extends: 'ms_stance', pel: [0.06, -0.08, 0], sp: [16, -6, 0], hd: [-4, -8, 0], hl: [0.10, -0.40, 0.55, 1], fr: [-0.40, -0.85, -0.12, 1], fl: [0.30, -0.88, 0.10, 1] },
  ms_bdash: { extends: 'ms_stance', pel: [-0.05, -0.04, 0], sp: [-10, -6, 0], hd: [12, -8, 0], hl: [0.10, 0.10, 0.75, 1], fr: [-0.10, -0.95, -0.12, 1], fl: [0.36, -0.82, 0.10, 1] },

  // ---------------------------------------------------------------- normals
  ms_flickWind: { extends: 'ms_stance', clip: 'spear_light1', cf: 0.0, yaw: -6, sp: [2, 8, 0], hl: [0.25, -0.05, 0.40, 1] },
  ms_flickOut: { extends: 'ms_stance', clip: 'spear_light1', cf: 0.18, yaw: 14, sp: [8, -14, 0], pel: [0.05, -0.05, 0], hl: [0.20, -0.30, 0.45, 1], fl: [0.26, -0.92, 0.10, 1] },
  ms_prodWind: { extends: 'ms_stance', clip: 'spear_light2', cf: 0.0, yaw: -14, sp: [0, 16, 0], pel: [-0.04, -0.05, 0], hl: [0.20, 0.05, 0.42, 1], fr: [-0.20, -0.92, -0.12, 1] },
  ms_prodOut: {
    extends: 'ms_stance', clip: 'spear_light1', cf: 0.12, yaw: 18, sp: [12, -18, 0], pel: [0.14, -0.10, 0], hd: [0, -12, 0],
    hl: [0.05, -0.35, 0.50, 1], fr: [-0.42, -0.84, -0.12, 1], fl: [0.42, -0.84, 0.10, 1],
  },
  ms_sweepWind: { extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.2, yaw: -24, sp: [-8, 26, 0], hd: [10, 12, 0], hl: [0.30, 0.20, 0.30, 1], fr: [-0.24, -0.92, -0.12, 1] },
  ms_sweepOut: {
    extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.3, yaw: 26, sp: [10, -28, 0], pel: [0.10, -0.08, 0], hd: [0, -16, 0],
    hl: [0.05, -0.20, 0.60, 1], fr: [-0.40, -0.86, -0.12, 1], fl: [0.40, -0.86, 0.10, 1],
  },
  ms_sweepThru: { extends: 'ms_sweepOut', clip: 'club_skill_club_bonk', cf: 0.36, sp: [20, -34, 0], yaw: 34 },
  ms_rootWind: { extends: 'ms_crouch', yaw: -4, sp: [8, 10, 0], hl: [0.30, -0.10, 0.30, 1] },
  ms_rootTap: { extends: 'ms_crouch', clip: 'Crouch_Idle_Loop', ct: 0.3, yaw: 18, sp: [18, -12, 0], pel: [0.10, -0.04, 0], hl: [0.25, -0.40, 0.40, 1] },
  ms_creepWind: { extends: 'ms_crouch', clip: 'club_skill_club_bonk', cf: 0.25, pel: [0, -0.34, 0], sp: [6, 18, 0], hl: [0.30, -0.20, 0.30, 1], fr: [-0.20, -0.62, -0.14, 1], fl: [0.30, -0.60, 0.12, 1], kr: KNEE, kl: KNEE },
  ms_creepOut: {
    extends: 'ms_crouch', clip: 'club_skill_club_bonk', cf: 0.6, pel: [0.12, -0.36, 0], yaw: 20, sp: [24, -16, 0], hd: [-10, -10, 0],
    hl: [0.60, -0.70, 0.10, 1], pl: [-0.3, 0.2, 1], fr: [-0.40, -0.55, -0.14, 1], fl: [0.38, -0.62, 0.12, 1], kr: KNEE, kl: KNEE,
  },
  ms_uprootWind: { extends: 'ms_crouch', clip: 'spear_light4', cf: 0.25, pel: [0, -0.36, 0], yaw: -10, sp: [20, 14, 0], hl: [0.40, -0.55, 0.20, 1], fr: [-0.22, -0.60, -0.14, 1], fl: [0.30, -0.60, 0.12, 1], kr: KNEE, kl: KNEE },
  ms_uprootOut: {
    extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.28, pel: [0.06, 0.02, 0], yaw: 16, sp: [-14, -12, 0], hd: [-18, -8, 0],
    hl: [0.30, 0.60, 0.35, 1], pl: [-0.2, -1, 0.4], fr: [-0.26, -0.94, -0.12, 1], fl: [0.22, -0.96, 0.10, 1],
  },
  ms_airKnee: { extends: 'ms_jump', fr: [0.55, -0.25, -0.04, 1], kr: [1, 0.3, 0], fl: [0.10, -0.75, 0.10, 1], sp: [12, -6, 0] },
  ms_airDipWind: { extends: 'ms_jump', clip: 'club_skill_club_bonk', cf: 0.2, sp: [-6, 10, 0] },
  ms_airDip: { extends: 'ms_jumpTuck', clip: 'club_skill_club_bonk', cf: 0.42, sp: [26, -10, 0], hd: [-10, 0, 0] },
  ms_capWind: { extends: 'ms_jumpTuck', sp: [-18, 0, 0], hd: [16, 0, 0] },
  ms_capCrash: { // the cap leads: she pitches forward over her own brim
    extends: 'ms_jumpTuck', sp: [46, 0, 0], hd: [-26, 0, 0], pel: [0.06, 0, 0],
    hl: [0.70, -0.40, 0.20, 1], fr: [-0.20, -0.70, -0.08, 1], fl: [-0.05, -0.65, 0.08, 1],
  },
  ms_bonkWind: { extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.2, yaw: -10, sp: [-10, 12, 0], hd: [10, 4, 0], pel: [0, 0.02, 0], hl: [0.25, 0.45, 0.25, 1], fl: [0.20, -0.95, 0.10, 1] },
  ms_bonkOut: {
    extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.42, yaw: 12, sp: [26, -6, 0], pel: [0.08, -0.12, 0], hd: [-14, -6, 0],
    hl: [0.15, -0.40, 0.45, 1], fr: [-0.40, -0.85, -0.12, 1], fl: [0.38, -0.86, 0.10, 1],
  },

  // ---------------------------------------------------------------- specials
  ms_castWind: { extends: 'ms_stance', yaw: -18, sp: [-4, 20, 0], hd: [6, 10, 0], hl: [0.10, 0.25, 0.30, 1], pl: [-0.4, -0.6, 0.6] },
  ms_castOut: { extends: 'ms_stance', yaw: 16, sp: [10, -14, 0], pel: [0.05, -0.05, 0], hd: [0, -12, 0], hl: [1.0, 0.18, -0.05, 1], pl: [-0.2, -1, 0.4], fl: [0.26, -0.93, 0.10, 1] },
  ms_castFar: { extends: 'ms_castOut', hl: [1.0, 0.42, -0.05, 1], sp: [4, -14, 0], hd: [-8, -12, 0] },
  ms_whipWind: { extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.2, yaw: -14, sp: [-12, 14, 0], hd: [12, 0, 0], pel: [0, 0.03, 0], hl: [0.20, 0.95, 0.20, 1], pl: [-0.3, 0.2, 1] },
  ms_whipOut: {
    extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.5, yaw: 18, sp: [30, -12, 0], pel: [0.10, -0.16, 0], hd: [-16, -8, 0],
    hl: [0.90, -0.65, 0.05, 1], pl: [-0.3, 0.3, 1], fr: [-0.44, -0.82, -0.12, 1], fl: [0.40, -0.84, 0.10, 1],
  },
  ms_plantWind: { extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.3, yaw: 0, sp: [-4, 0, 0], hd: [6, 0, 0], hl: [0.35, 0.10, 0.25, 1] },
  ms_plant: { // a curtsey: the staff's foot tapped into the soil, a sporeling springs up
    extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.4, pel: [0.02, -0.22, 0], yaw: 4, sp: [20, -4, 0], hd: [-14, -4, 0],
    hl: [0.55, -0.60, 0.20, 1], pl: [-0.3, 0.3, 1], fr: [-0.30, -0.72, -0.14, 1], fl: [0.24, -0.76, 0.10, 1],
  },
  ms_stalkWind: { extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.32, pel: [0, -0.10, 0], yaw: -6, sp: [12, 8, 0], hd: [0, 4, 0], hl: [0.35, -0.50, 0.25, 1] },
  ms_stalkOut: { // up on her toes, the left palm flung skyward as the stalk bursts out of the floor
    extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.4, pel: [0.04, 0.05, 0], yaw: 10, sp: [-12, -6, 0], hd: [-20, -6, 0],
    hl: [0.55, 0.85, 0.15, 1], pl: [-0.2, -1, 0.5], fr: [-0.20, -0.97, -0.12, 1], fl: [0.22, -0.97, 0.10, 1],
  },
  ms_glide: { // the staff overhead, skirts flared, legs trailing
    extends: 'ms_jump', clip: 'club_skill_club_bonk', cf: 0.1, sp: [-8, 0, 0], hd: [14, 0, 0],
    hl: [0.05, 0.25, 0.92, 1], pl: [-0.2, -1, 0.2], fr: [-0.04, -0.97, -0.06, 1], fl: [0.06, -0.96, 0.06, 1],
  },
  ms_glideSway: { extends: 'ms_glide', roll: 6, sp: [-6, 0, -6], hl: [0.10, 0.15, 0.92, 1] },

  // ---------------------------------------------------------------- supers
  ms_burstWind: { extends: 'ms_stance', clip: 'spear_light4', cf: 0.3, pel: [0, -0.16, 0], yaw: -12, sp: [18, 12, 0], hd: [-4, 8, 0], hl: [0.25, -0.50, 0.30, 1], fr: [-0.24, -0.84, -0.12, 1], fl: [0.28, -0.84, 0.10, 1] },
  ms_burst: { extends: 'ms_uprootOut', hl: [0.80, 0.70, 0.10, 1], sp: [-16, -10, 0] },
  ms_conduct: { extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.4, sp: [-12, -6, 0], hd: [-22, -6, 0], hl: [0.50, 0.95, 0.30, 1], pl: [-0.2, -1, 0.5] },
  ms_conduct2: { extends: 'ms_conduct', clip: 'spear_carry_Loop', ct: 0.6, sp: [-8, 10, 4], hd: [-18, 8, 0], hl: [0.85, 0.55, -0.10, 1], yaw: -6 },
  ms_reach: { extends: 'ms_stance', yaw: 20, sp: [14, -16, 0], pel: [0.08, -0.06, 0], hd: [-4, -12, 0], hl: [1.0, 0.10, -0.05, 1], pl: [-0.2, -1, 0.4], fl: [0.32, -0.90, 0.10, 1] },
  ms_squeeze: { extends: 'ms_reach', hl: [0.55, 0.20, 0.10, 1], sp: [4, 6, 0], yaw: 4, hd: [4, 0, 0] },
  ms_armsWide: { extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.4, sp: [-16, 0, 0], hd: [-24, 0, 0], hl: [0.20, 0.70, 0.95, 1], pl: [-0.2, -1, 0.3], pel: [0, 0.03, 0] },
  ms_grab: { extends: 'ms_reach', hl: [0.85, 0.15, 0.0, 1] },
  ms_toss: { extends: 'ms_sweepOut', hl: [0.60, 0.40, 0.20, 1] },
  ms_win: { extends: 'ms_armsWide', hd: [-14, -10, 0], hl: [0.30, 0.55, 0.85, 1] },
  ms_lose: { extends: 'ms_stance', clip: 'spear_carry_Loop', ct: 0.6, sp: [24, -4, 0], hd: [-30, -6, 0], pel: [0, -0.10, 0], hl: [0.30, -0.45, 0.30, 1] },
};

export default {
  style: {},
  packs: ['weapons'],
  poses,
  states: {
    idle: { keys: [[0, 'ms_stance']], loop: true, clip: 'spear_carry_Loop', speed: 0.8 },
    guard: { keys: [[0, 'ms_guard']], blend: 4 },
    walkF: { clip: 'guard_walk_fwd', loop: true, speed: 0.85, over: 'ms_walkArms', keys: [[0, { clip: 'guard_walk_fwd' }]] },
    walkB: { clip: 'guard_walk_back', loop: true, speed: 0.8, over: 'ms_walkArms', keys: [[0, { clip: 'guard_walk_back' }]] },
    crouch: { keys: [[0, 'ms_crouch']], blend: 4 },
    prejump: { keys: [[0, 'ms_stance'], [4, 'ms_prejump', 'out']], blend: 2 },
    jumpU: { keys: [[0, 'ms_jump'], [14, 'ms_jumpTuck'], [30, 'ms_jump']], blend: 3 },
    jumpF: { keys: [[0, 'ms_jump'], [14, { extends: 'ms_jumpTuck', pitch: -8 }], [30, 'ms_jump']], blend: 3 },
    jumpB: { keys: [[0, 'ms_jump'], [14, { extends: 'ms_jumpTuck', pitch: 8 }], [30, 'ms_jump']], blend: 3 },
    land: { keys: [[0, 'ms_land'], [4, 'ms_stance']], blend: 2 },
    dash: { keys: [[0, 'ms_dash'], [16, 'ms_stance']], blend: 3 },
    bdash: { keys: [[0, 'ms_bdash'], [18, 'ms_stance']], blend: 3 },
    dashEnd: { keys: [[0, 'ms_stance']] },
    block: { keys: [[0, { extends: 'ms_guard', pel: [-0.10, -0.10, 0], sp: [18, -4, 0] }], [6, 'ms_guard']], blend: 1 },
    cblock: { keys: [[0, { extends: 'ms_cguard', sp: [30, -2, 0] }], [6, 'ms_cguard']], blend: 1 },
    intro: { keys: [[0, 'ms_stance'], [30, 'ms_hush'], [120, 'ms_hush'], [150, 'ms_stance']] },
    win: { keys: [[0, 'ms_stance'], [24, 'ms_conduct2'], [60, 'ms_win'], [140, 'ms_win']], blend: 6 },
    lose: { keys: [[0, 'ms_lose']], blend: 8 },
    taunt: { keys: [[0, 'ms_stance'], [12, 'ms_hush'], [56, 'ms_hush'], [70, 'ms_stance']] },
  },
  moves: {
    st_L: { keys: [[0, 'ms_stance'], [2, 'ms_flickWind'], ['s', 'ms_flickOut', 'in'], ['a+2', 'ms_flickOut'], ['e', 'ms_stance', 'out']] },
    st_M: { keys: [[0, 'ms_stance'], [4, 'ms_prodWind', 'out'], ['s', 'ms_prodOut', 'in'], ['a+3', 'ms_prodOut'], ['e', 'ms_stance', 'io']] },
    st_H: { keys: [[0, 'ms_stance'], [7, 'ms_sweepWind', 'out'], ['s', 'ms_sweepOut', 'in'], ['a', 'ms_sweepThru'], ['a+5', 'ms_sweepThru'], ['e', 'ms_stance', 'io']] },
    cr_L: { keys: [[0, 'ms_crouch'], [2, 'ms_rootWind'], ['s', 'ms_rootTap', 'in'], ['a+2', 'ms_rootTap'], ['e', 'ms_crouch']] },
    cr_M: { keys: [[0, 'ms_crouch'], [5, 'ms_creepWind', 'out'], ['s', 'ms_creepOut', 'in'], ['a+3', 'ms_creepOut'], ['e', 'ms_crouch', 'io']] },
    cr_H: { keys: [[0, 'ms_crouch'], [6, 'ms_uprootWind', 'out'], ['s', 'ms_uprootOut', 'in'], ['a+4', 'ms_uprootOut'], ['e', 'ms_crouch', 'io']] },
    j_L: { keys: [[0, 'ms_jump'], ['s', 'ms_airKnee', 'out'], ['a', 'ms_airKnee'], ['e', 'ms_jump']], trail: 'foot_r' },
    j_M: { keys: [[0, 'ms_jump'], [4, 'ms_airDipWind'], ['s', 'ms_airDip', 'in'], ['a', 'ms_airDip'], ['e', 'ms_jump']] },
    j_H: { keys: [[0, 'ms_jump'], [6, 'ms_capWind', 'out'], ['s', 'ms_capCrash', 'in'], ['a', 'ms_capCrash'], ['e', 'ms_jumpTuck']], trail: 'Head' },
    bonk: { keys: [[0, 'ms_stance'], [12, 'ms_bonkWind', 'out'], ['s-2', { extends: 'ms_bonkWind', clip: 'club_skill_club_bonk', cf: 0.28 }, 'in'], ['s', 'ms_bonkOut', 'in'], ['a+6', 'ms_bonkOut'], ['e', 'ms_stance', 'io']] },
    bloom: { keys: [[0, 'ms_stance'], [8, 'ms_castWind', 'out'], ['s', 'ms_castOut', 'in'], ['s+10', 'ms_castOut'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    whip: { keys: [[0, 'ms_stance'], [8, 'ms_whipWind', 'out'], ['s', 'ms_whipOut', 'in'], ['a+6', 'ms_whipOut'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    sporeling: { keys: [[0, 'ms_stance'], [6, 'ms_plantWind', 'out'], [13, 'ms_plant', 'in'], [24, 'ms_plant'], ['e', 'ms_stance', 'io']] },
    stalk: { keys: [[0, 'ms_stance'], [3, 'ms_stalkWind', 'out'], ['s', 'ms_stalkOut', 'in'], ['a+6', 'ms_stalkOut'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    glide: { keys: [[0, 'ms_jumpTuck'], [4, 'ms_glide', 'out'], [20, 'ms_glideSway'], [36, 'ms_glide'], [52, 'ms_glideSway'], ['e', 'ms_jump']] },
    caps: { keys: [[0, 'ms_stance'], [5, 'ms_burstWind', 'out'], ['s', 'ms_burst', 'in'], ['a+4', 'ms_burst'], [24, 'ms_conduct'], [36, 'ms_conduct2'], [48, 'ms_conduct'], ['e', 'ms_stance']] },
    soil: { keys: [[0, 'ms_stance'], [6, 'ms_castWind', 'out'], ['s', 'ms_reach', 'in'], ['a+6', 'ms_reach'], ['e', 'ms_stance', 'io']] },
    overbloom: { keys: [[0, 'ms_stance'], [6, 'ms_stalkWind', 'out'], ['s', 'ms_plant', 'in'], ['a+8', 'ms_plant'], ['e', 'ms_stance', 'io']] },
    throw: { keys: [[0, 'ms_stance'], ['s', 'ms_grab', 'out'], [12, 'ms_squeeze'], [24, 'ms_sweepWind'], [32, 'ms_toss', 'in'], [44, 'ms_stance']] },
    bthrow: { keys: [[0, 'ms_stance'], ['s', 'ms_grab', 'out'], [12, 'ms_squeeze'], [24, { extends: 'ms_sweepWind', spin: 90 }], [36, { extends: 'ms_toss', spin: 180 }], [48, 'ms_stance']] },
    breaker: { keys: [[0, 'ms_stance'], [10, 'ms_prodWind', 'out'], ['s', 'ms_prodOut', 'in'], ['a+8', 'ms_prodOut'], ['e', 'ms_stance']] },
    breakerRev: { keys: [[0, 'ms_guard'], ['s', 'ms_armsWide', 'in'], ['e', 'ms_stance']] },
    taunt: { keys: [[0, 'ms_stance'], [12, 'ms_hush'], [56, 'ms_hush'], [70, 'ms_stance']] },
  },
  cine: {
    // Rain of Caps: she conducts the sky; caps fall in time with each sweep of the staff, the last one huge
    caps: [[0, 'ms_burst'], [8, 'ms_conduct'], [14, 'ms_conduct2'], [20, 'ms_conduct'], [26, 'ms_conduct2'], [32, 'ms_conduct'], [38, 'ms_conduct2'],
      [44, 'ms_conduct'], [52, 'ms_armsWide'], [66, 'ms_bonkWind'], [80, 'ms_bonkOut'], [88, 'ms_bonkOut'], [96, 'ms_stance']],
    // Everything Becomes Soil: mycelium wraps them (squeeze), the staff drives it in, they bloom
    soil: [[0, 'ms_reach'], [16, 'ms_squeeze'], [30, { extends: 'ms_squeeze', sp: [10, 10, 0], hl: [0.40, 0.10, 0.30, 1] }], [50, 'ms_stalkWind'],
      [72, 'ms_bonkWind'], [90, 'ms_bonkOut'], [104, 'ms_bonkOut'], [120, 'ms_hush'], [140, 'ms_armsWide'], [150, 'ms_win'], [175, 'ms_stance']],
    // Overtime Bloom: the floor erupts in glowing fungus around her twirl
    overbloom: [[0, 'ms_plant'], [18, 'ms_armsWide'], [34, { extends: 'ms_armsWide', spin: 120 }], [48, { extends: 'ms_glide', spin: 240 }], [62, { extends: 'ms_armsWide', spin: 360 }],
      [80, 'ms_conduct'], [100, 'ms_stalkWind'], [124, 'ms_stalkOut'], [140, 'ms_stalkOut'], [150, 'ms_stance']],
  },
};
