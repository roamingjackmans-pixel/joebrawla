// Moves every fighter has (throws, Breaker, Breaker Reversal, taunt) with per-fighter overrides.

export function universal(o = {}) {
  return {
    throw: {
      name: 'Throw', type: 'throw', startup: 5, active: 3, recovery: 23,
      grab: { range: o.throwRange ?? 72, len: 44, dmgAt: 30, toss: [3.2, 5], hold: 62, ...(o.throw || {}) },
      hits: [{ dmg: o.throwDmg ?? 120, frames: [30, 30], spark: 'H', sfx: 'throw', hitstop: 10, meter: 60 }],
      anim: o.throwAnim,
    },
    bthrow: {
      name: 'Back Throw', type: 'throw', startup: 5, active: 3, recovery: 23,
      grab: { range: o.throwRange ?? 72, len: 48, dmgAt: 34, toss: [3.2, 5], hold: 62, switchSide: true, ...(o.bthrow || {}) },
      hits: [{ dmg: o.bthrowDmg ?? 130, frames: [34, 34], spark: 'H', sfx: 'throw', hitstop: 10, meter: 60 }],
      anim: o.bthrowAnim,
    },
    breaker: {
      name: 'Breaker', type: 'breaker', startup: 20, active: 4, recovery: 30, cost: 1000,
      armor: { frames: [1, 23], hits: 1 },
      vel: [[6, 3.2], [20, 1], [24, 0]],
      hits: [{ dmg: o.breakerDmg ?? 90, box: o.breakerBox ?? [15, 70, 90, 70], stun: 30, bstun: 18, push: 70, effect: 'crumple', wallSplat: true, hitstop: 16, spark: 'X', sfx: 'breaker', juggle: 1 }],
      anim: o.breakerAnim,
    },
    breakerRev: {
      name: 'Breaker Reversal', type: 'breaker', startup: 10, active: 3, recovery: 26, cost: 1000,
      invuln: { full: [1, 18] },
      hits: [{ dmg: 40, box: [10, 40, 85, 110], effect: 'kd', launch: [5, 5], push: 90, hitstop: 12, spark: 'X', sfx: 'breaker' }],
      anim: o.breakerRevAnim,
    },
    taunt: {
      name: 'Taunt', type: 'taunt', startup: 1, active: 1, recovery: 70,
      fx: { at: 40, kind: 'meter', n: 60 },
      anim: o.tauntAnim,
    },
  };
}

/** hurtbox extension helper: limb out from frame a to b */
export const reach = (a, b, box) => ({ frames: [a, b], box });
