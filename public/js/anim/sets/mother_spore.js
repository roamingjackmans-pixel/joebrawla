// Mother Spore's animation set. A tall, unhurried fungal matriarch: upright posture, the mushroom-stalk staff in
// her right fist (its glowing crown leads every strike), the left hand doing the conjuring (cloud, roots,
// sporelings). Staff angles come from weapon-pack clips (the grip is clip-driven, like UAL Sword_Idle); IK places
// the left hand, the feet and the spine. Keys: 's' first active frame, 'a' last active, 'e' end.
const KNEE = [1, 0.1, 0];
const ARM_L = [-0.3, -1, 0.6];
// body measures (her model: hips 0.95 m, legs 0.93 m) so planted feet stay on the floor when the pelvis drops
const HIP = 0.95, HIP_C = 0.85, LEG = 0.93;
/** feet on the floor for a pelvis drop dy (m), back foot b and front foot f (m from the hips) */
const plant = (dy, b = -0.12, f = 0.16, hip = HIP) => {
  const t = (0.045 - (hip + dy)) / LEG;
  return { fr: [b / LEG, t, -0.12, 1], fl: [f / LEG, t, 0.10, 1], kr: KNEE, kl: KNEE };
};
const plantC = (dy, b, f) => plant(dy, b, f, HIP_C); // on the crouch clip (its pelvis sits lower)

const poses = {
  // ---------------------------------------------------------------- stance and movement
  ms_stance: { // the staff leaning forward at her side, the left hand resting at her waist
    clip: 'spear_carry_Loop', cf: 0.3,
    pel: [0, -0.03, 0], yaw: 10, sp: [3, -6, 0], hd: [6, -8, 0],
    hl: [0.36, -0.74, -0.22, 1], pl: ARM_L, ...plant(-0.03),
  },
  ms_hush: { extends: 'ms_stance', hd: [12, -16, 4], sp: [5, -10, 0], hl: [0.30, 0.42, -0.40, 1], pl: [-0.4, -1, 0.2] },
  ms_walkArms: { hl: [0.34, -0.72, -0.20, 0.9], pl: ARM_L, sp: [2, -4, 0], hd: [4, -6, 0], yaw: 6 },
  ms_guard: { // the staff braced across her body
    clip: 'Sword_Block', cf: 0.4,
    pel: [-0.04, -0.08, 0], yaw: 8, sp: [10, -4, 0], hd: [8, -6, 0],
    hl: [0.62, 0.05, -0.30, 1], pl: [0.1, -1, 0.4], ...plant(-0.08, -0.26, 0.22),
  },
  ms_crouch: { // sinks into her skirts, staff low and level
    clip: 'Crouch_Idle_Loop', cf: 0.1, pel: [0, -0.34, 0], yaw: 12, sp: [24, -6, 0], hd: [-22, -8, 0],
    hl: [0.50, -0.45, -0.20, 1], pl: ARM_L, ...plantC(-0.34, -0.30, 0.30),
  },
  ms_cguard: { extends: 'ms_crouch', sp: [32, -2, 0], hd: [-14, -4, 0], hl: [0.60, 0.15, -0.30, 1], pl: [0.1, -1, 0.4] },
  ms_prejump: { extends: 'ms_stance', pel: [0, -0.14, 0], sp: [14, -6, 0], hl: [0.30, -0.80, -0.10, 1], ...plant(-0.14) },
  ms_jump: { // skirts gathered, the staff held high like a parasol
    clip: 'club_skill_club_bonk', cf: 0.1, sp: [-4, 0, 0], hd: [6, 0, 0],
    hl: [0.20, 0.05, 0.80, 1], pl: [-0.2, -1, 0.2],
    fr: [0.05, -0.80, -0.08, 1], fl: [0.18, -0.72, 0.08, 1], kr: KNEE, kl: KNEE,
  },
  ms_jumpTuck: { extends: 'ms_jump', fr: [0.20, -0.55, -0.08, 1], fl: [0.30, -0.50, 0.08, 1], sp: [8, 0, 0] },
  ms_land: { extends: 'ms_stance', pel: [0, -0.16, 0], sp: [14, -6, 0], ...plant(-0.16) },
  ms_dash: { extends: 'ms_stance', pel: [0.06, -0.08, 0], sp: [16, -6, 0], hd: [-6, -8, 0], hl: [0.05, -0.60, 0.30, 1], ...plant(-0.08, -0.34, 0.28) },
  ms_bdash: { extends: 'ms_stance', pel: [-0.05, -0.04, 0], sp: [-10, -6, 0], hd: [12, -8, 0], hl: [0.10, 0.10, 0.75, 1], fr: [-0.10, -0.95, -0.12, 1], fl: [0.36, -0.84, 0.10, 1] },

  // ---------------------------------------------------------------- normals
  ms_flickWind: { extends: 'ms_stance', yaw: 2, sp: [-6, 4, 0], hd: [12, -6, 0], hl: [0.40, -0.55, -0.15, 1], ...plant(-0.02, -0.18, 0.14) },
  ms_flickOut: { extends: 'ms_stance', yaw: 16, sp: [36, -12, 0], pel: [0.06, -0.06, 0], hd: [-22, -10, 0], hl: [0.30, -0.70, 0.10, 1], ...plant(-0.06, -0.14, 0.26) },
  ms_prodWind: { extends: 'ms_stance', clip: 'spear_light2', cf: 0.0, yaw: -14, sp: [0, 16, 0], pel: [-0.04, -0.05, 0], hl: [0.50, -0.10, -0.05, 1], ...plant(-0.05, -0.30, 0.12) },
  ms_prodOut: { // a long lunge behind the staff
    extends: 'ms_stance', clip: 'spear_light1', cf: 0.12, yaw: 18, sp: [12, -18, 0], pel: [0.14, -0.10, 0], hd: [0, -12, 0],
    hl: [0.10, -0.70, 0.30, 1], ...plant(-0.10, -0.42, 0.40),
  },
  ms_sweepWind: { extends: 'ms_stance', clip: 'spear_skill_spear_sweep', cf: 0.4, yaw: -30, sp: [12, 30, 0], hd: [-6, 16, 0], pel: [-0.02, -0.08, 0], hl: [0.40, 0.10, -0.10, 1], ...plant(-0.03, -0.26, 0.12) },
  ms_sweepOut: { // the cap-crowned staff swept round at head height
    extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.3, yaw: 26, sp: [10, -28, 0], pel: [0.10, -0.08, 0], hd: [0, -16, 0],
    hl: [0.05, -0.50, 0.55, 1], ...plant(-0.08, -0.40, 0.38),
  },
  ms_sweepThru: { extends: 'ms_sweepOut', clip: 'club_skill_club_bonk', cf: 0.31, sp: [4, -36, 0], yaw: 36, hd: [-6, -18, 0] },
  ms_rootWind: { extends: 'ms_crouch', yaw: -4, sp: [20, 10, 0], hl: [0.25, -0.10, -0.25, 1], pl: [-0.6, -0.4, 0.6] },
  ms_rootTap: { extends: 'ms_crouch', yaw: 6, sp: [34, -4, 0], pel: [0.12, -0.36, 0], hd: [-30, -4, 0], hl: [0.98, -0.45, -0.20, 1], pl: [-0.3, 0.4, 1], ...plantC(-0.36, -0.40, 0.34) },
  ms_creepWind: { // drops to one knee, staff cocked over her shoulder
    extends: 'ms_crouch', clip: 'club_skill_club_bonk', cf: 0.25, pel: [0, -0.25, 0], sp: [6, 18, 0], hd: [-6, 8, 0],
    hl: [0.40, -0.40, -0.15, 1], ...plant(-0.31, -0.30, 0.30),
  },
  ms_creepOut: { // the staff skims the floor like a root
    extends: 'ms_crouch', clip: 'club_skill_club_bonk', cf: 0.6, pel: [0.12, -0.25, 0], yaw: 20, sp: [0, -16, 0], hd: [-10, -10, 0],
    hl: [0.70, -0.55, -0.05, 1], pl: [-0.3, 0.2, 1], ...plant(-0.31, -0.42, 0.40),
  },
  ms_uprootWind: { extends: 'ms_crouch', clip: 'spear_light4', cf: 0.25, pel: [0, -0.30, 0], yaw: -10, sp: [20, 14, 0], hl: [0.50, -0.70, -0.10, 1], ...plant(-0.30, -0.26, 0.30) },
  ms_uprootOut: { // springs up behind a vertical thrust of the staff
    extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.28, pel: [0.06, 0.02, 0], yaw: 16, sp: [-14, -12, 0], hd: [-18, -8, 0],
    hl: [0.45, 0.45, -0.20, 1], pl: [-0.2, -1, 0.4], ...plant(0.0, -0.20, 0.30),
  },
  ms_airKnee: { extends: 'ms_jump', fr: [0.55, -0.25, -0.04, 1], kr: [1, 0.3, 0], fl: [0.10, -0.75, 0.10, 1], sp: [12, -6, 0] },
  ms_airDipWind: { extends: 'ms_jump', clip: 'club_skill_club_bonk', cf: 0.2, sp: [-6, 10, 0] },
  ms_airDip: { extends: 'ms_jumpTuck', clip: 'club_skill_club_bonk', cf: 0.42, sp: [26, -10, 0], hd: [-10, 0, 0] },
  ms_capWind: { extends: 'ms_jumpTuck', sp: [-18, 0, 0], hd: [16, 0, 0] },
  ms_capCrash: { // the cap leads: she pitches forward over her own brim
    extends: 'ms_jumpTuck', sp: [46, 0, 0], hd: [-26, 0, 0], pel: [0.06, 0, 0],
    hl: [0.80, -0.30, -0.10, 1], fr: [-0.20, -0.70, -0.08, 1], fl: [-0.05, -0.65, 0.08, 1],
  },
  ms_bonkWind: { extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.2, yaw: -10, sp: [-10, 12, 0], hd: [10, 4, 0], pel: [0, 0.02, 0], hl: [0.40, 0.30, -0.10, 1], ...plant(0.02, -0.16, 0.20) },
  ms_bonkMid: { extends: 'ms_bonkWind', clip: 'club_skill_club_bonk', cf: 0.3, sp: [4, 0, 0], yaw: 2 },
  ms_bonkThru: { extends: 'ms_bonkOut', cf: 0.33, sp: [14, -6, 0], pel: [0.10, -0.10, 0], ...plant(-0.10, -0.38, 0.38) },
  ms_bonkOut: { // a toadstool's worth of staff on the head
    extends: 'ms_stance', clip: 'club_skill_club_bonk', cf: 0.32, yaw: 12, sp: [8, -6, 0], pel: [0.08, -0.06, 0], hd: [-14, -6, 0],
    hl: [0.20, -0.70, 0.30, 1], ...plant(-0.06, -0.38, 0.36),
  },

  // ---------------------------------------------------------------- specials
  ms_castWind: { extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.32, yaw: 14, sp: [-6, -16, 0], hd: [8, -14, 0], hl: [0.20, 0.0, -0.50, 1], pl: [-0.4, -0.6, 0.6] },
  ms_castOut: { // the staff raised, the left palm thrown open toward them: the cloud blooms from it
    extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.4, yaw: -26, sp: [8, 18, 0], pel: [0.05, -0.05, 0], hd: [-4, 16, 0],
    hl: [0.98, 0.10, -0.25, 1], pl: [-0.2, -1, 0.4], ...plant(-0.05, -0.14, 0.26),
  },
  ms_whipWind: { // the staff planted, the left hand drawn back over her shoulder
    extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.36, yaw: 18, sp: [-10, -20, 0], hd: [10, -16, 0], pel: [0, 0.02, 0],
    hl: [-0.20, 0.70, -0.20, 1], pl: [-0.3, 0.6, 1], ...plant(0.02, -0.16, 0.18),
  },
  ms_whipOut: { // she rips the left hand low across the floor and the roots follow it
    extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.4, yaw: -30, sp: [26, 22, 0], pel: [0.08, -0.16, 0], hd: [-18, 18, 0],
    hl: [0.95, -0.70, -0.35, 1], pl: [-0.3, 0.3, 1], ...plant(-0.16, -0.40, 0.36),
  },
  ms_plantWind: { extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.3, yaw: 0, sp: [-4, 0, 0], hd: [6, 0, 0], hl: [0.40, -0.30, -0.10, 1] },
  ms_plant: { // a curtsey: the staff's root-foot tapped into the soil, a sporeling springs up
    extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.4, pel: [0.02, -0.22, 0], yaw: 4, sp: [20, -4, 0], hd: [-14, -4, 0],
    hl: [0.70, -0.65, -0.05, 1], pl: [-0.3, 0.3, 1], ...plant(-0.22, -0.30, 0.24),
  },
  ms_stalkWind: { extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.32, pel: [0, -0.10, 0], yaw: -6, sp: [12, 8, 0], hd: [0, 4, 0], hl: [0.45, -0.70, -0.10, 1], ...plant(-0.10) },
  ms_stalkOut: { // up on her toes, the left palm flung skyward as the stalk bursts out of the floor
    extends: 'ms_stance', clip: 'spear_skill_spear_impale', cf: 0.4, pel: [0.04, 0.05, 0], yaw: 10, sp: [-12, -6, 0], hd: [-20, -6, 0],
    hl: [0.60, 0.80, -0.15, 1], pl: [-0.2, -1, 0.5], fr: [-0.20, -0.97, -0.12, 1], fl: [0.22, -0.97, 0.10, 1],
  },
  ms_glide: { // the staff overhead, skirts flared, legs trailing
    extends: 'ms_jump', clip: 'club_skill_club_bonk', cf: 0.1, sp: [-8, 0, 0], hd: [14, 0, 0],
    hl: [0.10, 0.20, 0.90, 1], pl: [-0.2, -1, 0.2], fr: [-0.04, -0.97, -0.06, 1], fl: [0.06, -0.96, 0.06, 1],
  },
  ms_glideSway: { extends: 'ms_glide', roll: 6, sp: [-6, 0, -6], hl: [0.15, 0.10, 0.90, 1] },

  // ---------------------------------------------------------------- supers
  ms_burstWind: { extends: 'ms_stance', clip: 'spear_light4', cf: 0.3, pel: [0, -0.16, 0], yaw: -12, sp: [18, 12, 0], hd: [-4, 8, 0], hl: [0.45, -0.70, -0.10, 1], ...plant(-0.16, -0.24, 0.26) },
  ms_burst: { extends: 'ms_uprootOut', hl: [0.85, 0.55, -0.10, 1], sp: [-16, -10, 0] },
  ms_conduct: { extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.4, sp: [-12, -6, 0], hd: [-22, -6, 0], hl: [0.55, 0.75, -0.15, 1], pl: [-0.2, -1, 0.5] },
  ms_conduct2: { extends: 'ms_conduct', clip: 'spear_carry_Loop', cf: 0.3, sp: [-8, 10, 4], hd: [-18, 8, 0], hl: [0.90, 0.40, -0.20, 1], yaw: -6 },
  ms_reach: { extends: 'ms_stance', yaw: 20, sp: [14, -16, 0], pel: [0.08, -0.06, 0], hd: [-4, -12, 0], hl: [1.0, 0.0, -0.10, 1], pl: [-0.2, -1, 0.4], ...plant(-0.06, -0.10, 0.32) },
  ms_squeeze: { extends: 'ms_reach', hl: [0.60, 0.05, -0.30, 1], sp: [4, 6, 0], yaw: 4, hd: [4, 0, 0] },
  ms_armsWide: { extends: 'ms_stance', clip: 'spear_charge_release', cf: 0.4, sp: [-16, 0, 0], hd: [-24, 0, 0], hl: [0.20, 0.60, 0.80, 1], pl: [-0.2, -1, 0.3], pel: [0, 0.03, 0], ...plant(0.03, -0.12, 0.16) },
  ms_grab: { extends: 'ms_reach', hl: [0.90, 0.10, -0.15, 1] },
  ms_toss: { extends: 'ms_sweepOut', hl: [0.70, 0.30, -0.10, 1] },
  ms_win: { extends: 'ms_armsWide', hd: [-14, -10, 0], hl: [0.30, 0.50, 0.80, 1] },
  ms_lose: { extends: 'ms_stance', sp: [24, -4, 0], hd: [-30, -6, 0], pel: [0, -0.10, 0], hl: [0.40, -0.80, -0.10, 1], ...plant(-0.10) },
  ms_recoil: { extends: 'ms_stance', pel: [-0.08, -0.06, 0], yaw: -4, sp: [-16, -14, 8], hd: [-22, -14, 6], hl: [0.30, 0.10, 0.30, 1], pl: [-0.6, -1, 0.4], ...plant(-0.06, -0.30, 0.10) },
  ms_recoilBig: { extends: 'ms_recoil', pel: [-0.14, -0.10, 0], sp: [-26, -20, 12], hd: [-32, -14, 10], hl: [0.10, 0.40, 0.60, 1], ...plant(-0.10, -0.34, 0.06) },
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
    cblock: { keys: [[0, { extends: 'ms_cguard', sp: [40, -2, 0] }], [6, 'ms_cguard']], blend: 1 },
    hit: { keys: [[0, 'ms_recoil', 'out'], [4, 'ms_recoilBig', 'out'], [12, 'ms_recoil'], [20, 'ms_stance']], blend: 1 },
    intro: { keys: [[0, 'ms_stance'], [30, 'ms_hush'], [120, 'ms_hush'], [150, 'ms_stance']] },
    win: { keys: [[0, 'ms_stance'], [24, 'ms_conduct2'], [60, 'ms_win'], [140, 'ms_win']], blend: 6 },
    lose: { keys: [[0, 'ms_lose']], blend: 8 },
    taunt: { keys: [[0, 'ms_stance'], [12, 'ms_hush'], [56, 'ms_hush'], [70, 'ms_stance']] },
  },
  moves: {
    st_L: { keys: [[0, 'ms_stance'], [2, 'ms_flickWind'], ['s', 'ms_flickOut', 'in'], ['a+2', 'ms_flickOut'], ['e', 'ms_stance', 'out']] },
    st_M: { keys: [[0, 'ms_stance'], [4, 'ms_prodWind', 'out'], ['s', 'ms_prodOut', 'in'], ['a+3', 'ms_prodOut'], ['e', 'ms_stance', 'io']] },
    st_H: { keys: [[0, 'ms_stance'], [7, 'ms_sweepWind', 'out'], ['s', 'ms_sweepOut', 'in'], ['a', 'ms_sweepThru'], ['a+5', 'ms_sweepThru'], ['e', 'ms_stance', 'io']] },
    cr_L: { keys: [[0, 'ms_crouch'], [2, 'ms_rootWind'], ['s', 'ms_rootTap', 'in'], ['a+2', 'ms_rootTap'], ['e', 'ms_crouch']], trail: 'hand_l' },
    cr_M: { keys: [[0, 'ms_crouch'], [5, 'ms_creepWind', 'out'], ['s', 'ms_creepOut', 'in'], ['a+3', 'ms_creepOut'], ['e', 'ms_crouch', 'io']] },
    cr_H: { keys: [[0, 'ms_crouch'], [6, 'ms_uprootWind', 'out'], ['s', 'ms_uprootOut', 'in'], ['a+4', 'ms_uprootOut'], ['e', 'ms_crouch', 'io']] },
    j_L: { keys: [[0, 'ms_jump'], ['s', 'ms_airKnee', 'out'], ['a', 'ms_airKnee'], ['e', 'ms_jump']], trail: 'foot_r' },
    j_M: { keys: [[0, 'ms_jump'], [4, 'ms_airDipWind'], ['s', 'ms_airDip', 'in'], ['a', 'ms_airDip'], ['e', 'ms_jump']] },
    j_H: { keys: [[0, 'ms_jump'], [6, 'ms_capWind', 'out'], ['s', 'ms_capCrash', 'in'], ['a', 'ms_capCrash'], ['e', 'ms_jumpTuck']], trail: 'Head' },
    bonk: { keys: [[0, 'ms_stance'], [12, 'ms_bonkWind', 'out'], ['s-2', 'ms_bonkMid', 'in'], ['s', 'ms_bonkOut', 'in'], ['a+2', 'ms_bonkThru', 'out'], ['a+8', 'ms_bonkThru'], ['e', 'ms_stance', 'io']] },
    bloom: { keys: [[0, 'ms_stance'], [8, 'ms_castWind', 'out'], ['s', 'ms_castOut', 'in'], ['s+10', 'ms_castOut'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    whip: { keys: [[0, 'ms_stance'], [8, 'ms_whipWind', 'out'], ['s', 'ms_whipOut', 'in'], ['a+6', 'ms_whipOut'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    sporeling: { keys: [[0, 'ms_stance'], [6, 'ms_plantWind', 'out'], [13, 'ms_plant', 'in'], [24, 'ms_plant'], ['e', 'ms_stance', 'io']] },
    stalk: { keys: [[0, 'ms_stance'], [3, 'ms_stalkWind', 'out'], ['s', 'ms_stalkOut', 'in'], ['a+6', 'ms_stalkOut'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    glide: { keys: [[0, 'ms_jumpTuck'], [4, 'ms_glide', 'out'], [20, 'ms_glideSway'], [36, 'ms_glide'], [52, 'ms_glideSway'], ['e', 'ms_jump']] },
    caps: { keys: [[0, 'ms_stance'], [5, 'ms_burstWind', 'out'], ['s', 'ms_burst', 'in'], ['a+4', 'ms_burst'], [24, 'ms_conduct'], [36, 'ms_conduct2'], [48, 'ms_conduct'], ['e', 'ms_stance']] },
    soil: { keys: [[0, 'ms_stance'], [6, 'ms_castWind', 'out'], ['s', 'ms_reach', 'in'], ['a+6', 'ms_reach'], ['e', 'ms_stance', 'io']], trail: 'hand_l' },
    overbloom: { keys: [[0, 'ms_stance'], [6, 'ms_stalkWind', 'out'], ['s', 'ms_plant', 'in'], ['a+8', 'ms_plant'], ['e', 'ms_stance', 'io']] },
    throw: { keys: [[0, 'ms_stance'], ['s', 'ms_grab', 'out'], [12, 'ms_squeeze'], [24, 'ms_sweepWind'], [32, 'ms_toss', 'in'], [44, 'ms_stance']] },
    bthrow: { keys: [[0, 'ms_stance'], ['s', 'ms_grab', 'out'], [14, { extends: 'ms_squeeze', yaw: 90 }], [30, { extends: 'ms_toss', yaw: 180 }], [48, 'ms_stance']] },
    breaker: { keys: [[0, 'ms_stance'], [10, 'ms_prodWind', 'out'], ['s', 'ms_prodOut', 'in'], ['a+8', 'ms_prodOut'], ['e', 'ms_stance']] },
    breakerRev: { keys: [[0, 'ms_guard'], ['s', 'ms_armsWide', 'in'], ['e', 'ms_stance']] },
    taunt: { keys: [[0, 'ms_stance'], [12, 'ms_hush'], [56, 'ms_hush'], [70, 'ms_stance']] },
  },
  cine: {
    // Rain of Caps: she conducts the sky; caps fall in time with each sweep of the staff, the last one huge
    caps: [[0, 'ms_burst'], [8, 'ms_conduct'], [14, 'ms_conduct2'], [20, 'ms_conduct'], [26, 'ms_conduct2'], [32, 'ms_conduct'], [38, 'ms_conduct2'],
      [44, 'ms_conduct'], [52, 'ms_armsWide'], [66, 'ms_bonkWind'], [76, 'ms_bonkMid'], [80, 'ms_bonkOut'], [90, 'ms_bonkOut'], [96, 'ms_stance']],
    // Everything Becomes Soil: mycelium wraps them (squeeze), the staff drives it in, they bloom
    soil: [[0, 'ms_reach'], [16, 'ms_squeeze'], [30, { extends: 'ms_squeeze', sp: [10, 10, 0], hl: [0.45, 0.0, -0.35, 1] }], [50, 'ms_stalkWind'],
      [72, 'ms_bonkWind'], [84, 'ms_bonkMid'], [90, 'ms_bonkOut'], [104, 'ms_bonkOut'], [120, 'ms_hush'], [140, 'ms_armsWide'], [150, 'ms_win'], [175, 'ms_stance']],
    // Overtime Bloom: the floor erupts in glowing fungus around her twirl
    overbloom: [[0, 'ms_plant'], [18, 'ms_armsWide'], [34, { extends: 'ms_armsWide', spin: 120 }], [48, { extends: 'ms_glide', spin: 240 }], [62, { extends: 'ms_armsWide', spin: 360 }],
      [80, { extends: 'ms_conduct', spin: 360 }], [100, { extends: 'ms_stalkWind', spin: 360 }], [124, { extends: 'ms_stalkOut', spin: 360 }], [140, { extends: 'ms_stalkOut', spin: 360 }], [150, { extends: 'ms_stance', spin: 360 }]],
  },
};
