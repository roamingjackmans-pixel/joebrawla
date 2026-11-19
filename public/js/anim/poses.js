// Named procedural poses. A pose is a bag of parameters the animator lerps between keys:
//   clip/ct (clip time, s) or cf (fraction 0..1): base clip pose; pel: [x,y,z] pelvis offset (m);
//   yaw/pitch/roll: pelvis rotation (deg); sp: [bend, twist, side] spine (deg); hd: [pitch, yaw, roll] head;
//   hr/hl/fr/fl: IK targets [fwd, up, left, weight] in limb lengths from shoulder/hip, character space;
//   pr/pl: elbow poles, kr/kl: knee poles (character-space directions); spin: whole-body yaw (deg, visual);
//   tilt: whole-body pitch (deg, visual, for flips); lift: whole-body height offset (m).
// Character space: x forward, y up, z = the fighter's left. Orthodox stance = left foot forward.

const ARM_POLE_R = [-0.3, -1, -0.6], ARM_POLE_L = [-0.3, -1, 0.6], KNEE = [1, 0.1, 0];

export const POSES = {
  // ---------------------------------------------------------------- stances
  stance: {
    clip: 'Idle_Loop', ct: 0.4,
    pel: [0, -0.07, 0], yaw: -32, sp: [8, 18, 0], hd: [8, 14, 0],
    hr: [0.30, 0.42, 0.30, 1], hl: [0.55, 0.40, 0.02, 1], pr: ARM_POLE_R, pl: ARM_POLE_L,
    fr: [-0.24, -0.90, -0.14, 1], fl: [0.30, -0.89, 0.10, 1], kr: KNEE, kl: KNEE,
  },
  guardHigh: { // blocking standing: forearms up in front of the face
    clip: 'Idle_Loop', ct: 0.4,
    pel: [-0.03, -0.09, 0], yaw: -20, sp: [14, 10, 0], hd: [10, 6, 0],
    hr: [0.38, 0.62, 0.20, 1], hl: [0.45, 0.66, 0.0, 1], pr: [0.1, -1, -0.3], pl: [0.1, -1, 0.3],
    fr: [-0.30, -0.88, -0.14, 1], fl: [0.26, -0.88, 0.10, 1], kr: KNEE, kl: KNEE,
  },
  crouch: {
    clip: 'Crouch_Idle_Loop', ct: 0.3,
    pel: [0, 0, 0], yaw: -25, sp: [16, 12, 0], hd: [-6, 10, 0],
    hr: [0.32, 0.38, 0.28, 1], hl: [0.52, 0.36, 0.04, 1], pr: ARM_POLE_R, pl: ARM_POLE_L,
  },
  crouchGuard: {
    clip: 'Crouch_Idle_Loop', ct: 0.3, yaw: -18, sp: [24, 8, 0], hd: [0, 6, 0],
    hr: [0.42, 0.50, 0.20, 1], hl: [0.50, 0.52, 0.0, 1], pr: [0.1, -1, -0.3], pl: [0.1, -1, 0.3],
  },
  prejump: { extends: 'stance', pel: [0, -0.16, 0], sp: [18, 10, 0] },
  land: { extends: 'stance', pel: [0, -0.18, 0], sp: [20, 10, 0] },
  jumpUp: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [6, 10, 0],
    hr: [0.30, 0.36, 0.30, 0.8], hl: [0.46, 0.36, 0.05, 0.8], pr: ARM_POLE_R, pl: ARM_POLE_L,
  },

  // ---------------------------------------------------------------- kicks (rear = right leg)
  kickChamber: {
    extends: 'stance', yaw: 5, sp: [-4, 8, 6], pel: [0, -0.02, 0],
    fr: [0.40, -0.28, -0.02, 1], kr: [0.4, 1, 0], fl: [0.02, -0.93, 0.08, 1],
    hr: [0.15, 0.35, 0.10, 1], hl: [0.45, 0.42, -0.05, 1],
  },
  kickMid: {
    extends: 'stance', yaw: 48, sp: [-12, 18, 14], pel: [-0.03, 0, 0],
    fr: [0.92, -0.06, 0.02, 1], kr: [0, 1, 0.2], fl: [-0.04, -0.95, 0.10, 1],
    hr: [-0.10, 0.20, -0.20, 1], hl: [0.45, 0.40, -0.05, 1], hd: [-4, -24, 0],
  },
  kickHigh: {
    extends: 'kickMid', yaw: 58, sp: [-20, 18, 20], fr: [0.70, 0.52, 0.02, 1], kr: [0, 1, 0.3],
  },
  kickLowCrouch: {
    extends: 'crouch', yaw: 10, sp: [10, 14, 6],
    fr: [0.78, -0.82, 0.0, 1], kr: [0.3, 1, 0], hr: [0.25, 0.30, 0.25, 1],
  },
  sweep: {
    extends: 'crouch', clip: 'Crouch_Idle_Loop', yaw: 70, pel: [0, -0.10, 0], sp: [24, 10, 18],
    fr: [0.95, -0.85, 0.15, 1], kr: [0.2, 1, 0.3], hr: [-0.15, -0.30, -0.10, 1], hl: [0.10, -0.60, 0.30, 1],
  },
  kneeUp: {
    extends: 'stance', yaw: 12, sp: [-6, 12, 0], pel: [0, 0.02, 0],
    fr: [0.42, 0.10, -0.02, 1], kr: [1, 0.3, 0], fl: [-0.02, -0.96, 0.08, 1],
    hr: [0.10, 0.60, 0.20, 1], hl: [0.25, 0.65, 0.05, 1],
  },
  airKnee: {
    clip: 'NinjaJump_Idle_Loop', ct: 0.5, sp: [8, 10, 0],
    fr: [0.55, -0.05, 0, 1], kr: [1, 0.3, 0], fl: [-0.15, -0.70, 0.1, 1], kl: [1, -0.2, 0],
    hr: [0.25, 0.40, 0.25, 1], hl: [0.40, 0.40, 0, 1], pr: ARM_POLE_R, pl: ARM_POLE_L,
  },
  airKick: {
    extends: 'airKnee', sp: [14, 20, 0], yaw: 30, fr: [0.80, -0.55, 0, 1], kr: [0.2, 1, 0], fl: [0.05, -0.60, 0.15, 1],
  },
  airChop: {
    extends: 'airKnee', sp: [24, 10, 0], hr: [0.85, -0.05, 0.05, 1], pr: [-0.5, 0.2, -1], hl: [0.10, 0.20, 0.2, 1],
  },

  // ---------------------------------------------------------------- punches (clip upper body, stance legs)
  jabWind: { extends: 'stance', hl: [0.42, 0.42, 0.0, 1] },
  jabOut: { extends: 'stance', yaw: -40, sp: [6, 26, 0], hl: [1.0, 0.35, -0.10, 1], pl: [-0.2, -0.4, 1] },
  crossWind: { extends: 'stance', yaw: -40, sp: [10, 24, 0], hr: [0.15, 0.40, 0.25, 1] },
  crossOut: { extends: 'stance', yaw: 10, sp: [10, -12, 0], pel: [0.06, -0.08, 0], hr: [1.0, 0.32, 0.18, 1], pr: [-0.2, -0.4, -1], hl: [0.22, 0.42, 0.10, 1], fr: [-0.38, -0.88, -0.12, 1] },
  hayWind: { extends: 'stance', yaw: -55, sp: [4, 40, -6], hr: [-0.15, 0.55, -0.30, 1], pr: [-1, 0.2, -0.5] },
  hayOut: { extends: 'stance', yaw: 25, sp: [16, -30, 8], pel: [0.10, -0.10, 0], hr: [1.0, 0.18, 0.30, 1], pr: [0, 0.3, -1], hl: [0.15, 0.40, 0.15, 1], fr: [-0.45, -0.85, -0.12, 1], fl: [0.40, -0.86, 0.12, 1] },
  hammerUp: { extends: 'stance', yaw: -10, sp: [-12, 10, 0], hr: [0.15, 1.0, 0.10, 1], hl: [0.20, 0.95, -0.05, 1], pr: [-1, 0.4, -0.3], pl: [-1, 0.4, 0.3] },
  hammerDown: { extends: 'stance', yaw: 0, sp: [30, 0, 0], pel: [0.10, -0.16, 0], hr: [0.85, -0.05, 0.10, 1], hl: [0.80, 0.00, -0.05, 1], pr: [-0.3, 0.5, -1], pl: [-0.3, 0.5, 1], fr: [-0.45, -0.82, -0.12, 1], fl: [0.42, -0.82, 0.12, 1] },
  uppercutLow: { extends: 'stance', pel: [0.02, -0.22, 0], yaw: -30, sp: [26, 20, 0], hr: [0.25, -0.10, 0.15, 1] },
  uppercutHigh: { extends: 'stance', pel: [0.05, 0.02, 0], yaw: 20, sp: [-14, -20, 0], hr: [0.25, 1.0, 0.12, 1], pr: [1, 0, -0.3], hl: [0.10, 0.30, 0.20, 1], fr: [-0.10, -0.80, -0.05, 1], kr: [1, 0.2, 0], fl: [0.20, -0.98, 0.10, 1] },
  castOut: { extends: 'stance', yaw: -5, sp: [6, 0, 0], hr: [1.0, 0.30, 0.08, 1], hl: [0.95, 0.36, -0.06, 1], pr: [-0.2, -1, -0.4], pl: [-0.2, -1, 0.4] },
  castWind: { extends: 'stance', yaw: -45, sp: [4, 34, 0], hr: [-0.05, 0.35, -0.10, 1], hl: [0.05, 0.40, 0.10, 1] },
  drink: { clip: 'Consume', cf: 0.5, pel: [0, -0.04, 0], fr: [-0.15, -0.94, -0.12, 1], fl: [0.18, -0.94, 0.10, 1], kr: KNEE, kl: KNEE },
  grabReach: { extends: 'stance', yaw: 0, sp: [12, 0, 0], hr: [0.95, 0.35, 0.25, 1], hl: [0.95, 0.38, -0.20, 1], pr: [-0.3, -1, -0.6], pl: [-0.3, -1, 0.6] },
  rushPunch: { extends: 'crossOut', sp: [20, -10, 0], pel: [0.12, -0.12, 0] },

  // ---------------------------------------------------------------- reactions
  hitHigh: { clip: 'Hit_Head', cf: 0.35, fr: [-0.30, -0.90, -0.14, 0.8], fl: [0.24, -0.90, 0.10, 0.8], kr: KNEE, kl: KNEE },
  hitMid: { clip: 'Hit_Chest', cf: 0.4, fr: [-0.30, -0.90, -0.14, 0.8], fl: [0.24, -0.90, 0.10, 0.8], kr: KNEE, kl: KNEE },
  hitCrouch: { extends: 'crouch', sp: [-10, 0, 10], hd: [-25, 0, 10] },
  recoil: { extends: 'stance', pel: [-0.08, -0.06, 0], yaw: -10, sp: [-16, -14, 8], hd: [-24, -10, 6], hr: [0.15, 0.2, 0.35, 1], hl: [0.25, 0.1, -0.2, 1], pr: [-0.6, -1, -0.4], pl: [-0.6, -1, 0.4], fr: [-0.36, -0.88, -0.14, 1], fl: [0.18, -0.9, 0.1, 1] },
  recoilBig: { extends: 'recoil', pel: [-0.14, -0.1, 0], sp: [-26, -20, 12], hd: [-34, -14, 10], hr: [-0.05, 0.35, 0.5, 1], hl: [0.1, 0.4, -0.5, 1] },
  gut: { extends: 'stance', pel: [-0.06, -0.12, 0], sp: [34, -6, 4], hd: [24, 0, 0], hr: [0.35, -0.05, 0.25, 1], hl: [0.4, -0.02, 0.0, 1], pr: [-0.6, -1, -0.4], pl: [-0.6, -1, 0.4] },
  kneel: { clip: 'Idle_Loop', ct: 0.4, pel: [0, -0.48, 0], sp: [40, 0, 10], hd: [30, 0, 8], fr: [0.05, -0.55, -0.12, 1], kr: [1, -0.4, 0], fl: [0.3, -0.5, 0.12, 1], kl: [1, 0.2, 0], hr: [0.25, -0.75, 0.2, 1], hl: [0.25, -0.75, -0.1, 1] },
  victory: { extends: 'stance', yaw: -10, pel: [0, 0, 0], sp: [-10, 10, 0], hd: [-14, 10, 0], hr: [0.18, 1.0, 0.12, 1], pr: [0, -0.2, -1], hl: [0.0, -0.2, -0.25, 1], fr: [-0.15, -0.95, -0.14, 1], fl: [0.15, -0.95, 0.1, 1] },
  victoryPump: { extends: 'victory', sp: [-4, 14, 0], hr: [0.25, 0.75, 0.15, 1], hd: [-6, 12, 0] },
  juggle: { clip: 'Hit_Knockback', cf: 0.25 },
  fall: { clip: 'knockdown', cf: 0.35 },
  lying: { clip: 'knockdown', cf: 0.98 },
  splat: { clip: 'Hit_Knockback', cf: 0.2, sp: [-25, 0, 0], hr: [-0.2, 0.6, -0.7, 1], hl: [-0.2, 0.6, 0.7, 1] },
};

/** resolve `extends` chains once */
export function resolvePose(p, seen = 0) {
  if (typeof p === 'string') p = POSES[p];
  if (!p) return {};
  if (!p.extends || seen > 6) return p;
  const base = resolvePose(POSES[p.extends], seen + 1);
  const { extends: _, ...rest } = p;
  return { ...base, ...rest };
}
