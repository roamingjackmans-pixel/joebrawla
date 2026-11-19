// Gary — "Everything's for sale. Except Gary." Trickster. docs/ROSTER.md
// Plays random and tricky: the ware he throws changes every toss (a fixed, seeded order a HUD can show), a
// counter that pockets the opponent's meter, a mimic chest left on the floor, a crate dropped from the air,
// a cross-up backpack drop and a pack that swings overhead as his anti-air.
import { defineFighter, pick } from '../movekit.js';
import { universal, reach } from './common.js';
import { CM } from '../core.js';

// Merchandise Toss: wares come out of the pack in a fixed shuffled order (three "bags" of pot/scroll/chain),
// shifted by the round number, advancing on every toss. nextWare(f, state) tells a HUD what comes next.
const WARES = ['pot', 'scroll', 'chain'];
const BAG = [0, 1, 2, 1, 0, 2, 2, 0, 1];
const wareOf = (f, state) => BAG[((f.vars.toss || 0) + ((state.round || 1) - 1) * 4) % BAG.length];
const mine = (f, state, kind) => state.proj.some((p) => p.owner === f.i && p.kind === kind);

const TOSS_STARTUP = [14, 13, 12, 11];
function toss(ware) {
  return (v) => {
    const ex = v === 'EX';
    const su = pick(v, TOSS_STARTUP);
    const common = {
      name: 'Merchandise Toss', type: ex ? 'ex' : 'special', startup: su, active: 2, oneProj: true, ware,
      fx: { at: 1, kind: 'addvar', name: 'toss', value: 1, max: 9999 },
    };
    if (ware === 'pot') {
      // a lobbed pot: arcs over and shatters where it lands (hits crouchers; H/EX knock down)
      return {
        ...common, recovery: pick(v, [28, 28, 29, 26]),
        proj: {
          at: su, kind: 'pot', x: 40, y: 165, vx: pick(v, [3.4, 4.8, 6.4, 5.4]), vy: 8, gravity: 0.55, life: 50,
          box: [-24, -24, 48, 48], hits: ex ? 2 : 1, every: 5, power: ex ? 2 : 1,
          hit: { dmg: pick(v, [70, 75, 80, 50]), stun: 22, bstun: 16, push: 30, hitstop: 11, spark: 'H', sfx: 'H', effect: v === 'H' || ex ? 'kd' : 'normal', launch: [2, 5] },
        },
      };
    }
    if (ware === 'scroll') {
      // a scroll flung flat and fast at head height: crouching ducks it
      return {
        ...common, recovery: pick(v, [25, 25, 26, 24]),
        proj: {
          at: su, kind: 'scroll', x: 55, y: 126, vx: pick(v, [8, 10, 12.5, 12]), life: 80,
          box: [-34, -13, 68, 26], hits: ex ? 2 : 1, every: 4, power: 1,
          hit: { dmg: pick(v, [50, 55, 60, 40]), stun: 20, bstun: 15, push: 36, hitstop: 9, spark: 'M', sfx: 'M', effect: ex ? 'kd' : 'normal', launch: [2.5, 5] },
        },
      };
    }
    // chain: slow, heavy, several hits; Gary walks in behind it
    return {
      ...common, recovery: pick(v, [30, 31, 32, 28]),
      proj: {
        at: su, kind: 'chain', x: 50, y: 92, vx: pick(v, [2.8, 3.4, 4.0, 3.8]), life: 120,
        box: [-38, -32, 76, 64], hits: ex ? 5 : 3, every: 8, power: 2,
        hit: { dmg: pick(v, [28, 30, 32, 26]), stun: 18, bstun: 14, push: 8, hitstop: 7, spark: 'L', sfx: 'M', effect: 'normal' },
      },
    };
  };
}

export default defineFighter({
  id: 'gary', name: 'Gary', title: "Everything's for sale", hp: 950, archetype: 'Trickster',
  walkF: 4.2, walkB: 3.5, dashF: { frames: 20, dist: 118 }, dashB: { frames: 23, dist: 100, invuln: 7 },
  jump: { pre: 5, vy: 14.9, vx: 4.4 }, width: 52, height: 180, crouchHeight: 108,
  initVars: { toss: 0 },
  nextWare: (f, state) => WARES[wareOf(f, state)],
  normals: {
    stand: { L: 'st_L', M: 'st_M', H: 'st_H' },
    crouch: { L: 'cr_L', M: 'cr_M', H: 'cr_H' },
    air: { L: 'j_L', M: 'j_M', H: 'j_H' },
    command: [{ dir: 6, btn: 'M', id: 'hatswat' }, { dir: 3, btn: 'H', id: 'upsell' }],
  },
  specials: [
    { id: 'swing', motion: '623', simple: 6 },
    { id: 'toss_pot', motion: '236', simple: 5, needs: (f, s) => wareOf(f, s) === 0 },
    { id: 'toss_scroll', motion: '236', simple: 5, needs: (f, s) => wareOf(f, s) === 1 },
    { id: 'toss_chain', motion: '236', simple: 5, needs: (f, s) => wareOf(f, s) === 2 },
    { id: 'haggle', motion: '214', simple: 4 },
    { id: 'chest', motion: '22', simple: 2, needs: (f, s) => !mine(f, s, 'mimic') },
    { id: 'crate', motion: '214', simple: 4, air: true, needs: (f, s) => f.y > 40 * CM && !mine(f, s, 'crate') },
  ],
  supers: { art: 'clearance', final: 'mustgo', overtime: 'offer' },
  autoCombo: ['st_L', 'st_M', 'st_H', 'swing'],
  moves: {
    // ------------------------------------------------------------ normals
    st_L: {
      name: 'Receipt Slap', startup: 4, active: 2, recovery: 8,
      hits: [{ dmg: 28, box: [18, 118, 54, 24], stun: 13, bstun: 10, push: 22, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 114, 58, 28])],
      cancel: { into: ['st_L', 'cr_L', 'st_M', 'cr_M'], special: true, super: true },
    },
    st_M: {
      name: 'Free Sample', startup: 7, active: 3, recovery: 14,
      hits: [{ dmg: 52, box: [22, 104, 68, 30], stun: 19, bstun: 15, push: 32, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(6, 16, [10, 100, 72, 34])], vel: [[3, 1.2], [9, 0]],
      cancel: { into: ['st_H', 'cr_H', 'upsell'], special: true, super: true },
    },
    st_H: {
      name: 'Backpack Bump', startup: 12, active: 4, recovery: 19,
      hits: [{ dmg: 85, box: [8, 70, 92, 92], stun: 23, bstun: 18, push: 46, hitstop: 13, spark: 'H', sfx: 'H' }],
      hurt: [reach(10, 26, [0, 66, 96, 98])], vel: [[4, 1.6], [14, 0]],
      cancel: { special: true, super: true },
    },
    cr_L: {
      name: 'Toe Tap', startup: 4, active: 2, recovery: 8, crouching: true,
      hits: [{ dmg: 24, box: [16, 4, 58, 24], level: 'low', stun: 12, bstun: 9, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
      hurt: [reach(3, 8, [10, 2, 62, 28])],
      cancel: { into: ['cr_L', 'st_L', 'cr_M', 'st_M'], special: true, super: true },
    },
    cr_M: {
      name: 'Pouch Swat', startup: 8, active: 3, recovery: 15, crouching: true,
      hits: [{ dmg: 48, box: [22, 6, 86, 26], level: 'low', stun: 18, bstun: 13, push: 30, hitstop: 10, spark: 'M', sfx: 'M' }],
      hurt: [reach(7, 18, [10, 4, 90, 30])],
      cancel: { into: ['st_H', 'cr_H', 'upsell'], special: true, super: true },
    },
    cr_H: {
      name: 'Rug Pull', startup: 10, active: 3, recovery: 25, crouching: true,
      hits: [{ dmg: 78, box: [26, 0, 100, 22], level: 'low', effect: 'kd', launch: [1.5, 4], bstun: 14, push: 30, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(9, 28, [10, 0, 104, 26])],
      cancel: { special: true, super: true },
    },
    j_L: {
      name: 'Hat Brim', air: true, startup: 5, active: 7, recovery: 4, landRecovery: 2,
      hits: [{ dmg: 32, box: [10, 10, 52, 45], level: 'ovh', stun: 14, bstun: 10, push: 20, hitstop: 8, spark: 'L', sfx: 'L' }],
    },
    j_M: {
      name: 'Ledger Swat', air: true, startup: 7, active: 5, recovery: 6, landRecovery: 3,
      hits: [{ dmg: 52, box: [15, 30, 64, 46], level: 'ovh', stun: 18, bstun: 13, push: 26, hitstop: 10, spark: 'M', sfx: 'M' }],
    },
    j_H: {
      // the pack swung down under and behind him: hits on the far side too (cross-ups)
      name: 'Pack Drop', air: true, startup: 10, active: 6, recovery: 6, landRecovery: 4,
      hits: [{ dmg: 78, box: [-36, -26, 98, 72], level: 'ovh', stun: 22, bstun: 16, push: 32, hitstop: 12, spark: 'H', sfx: 'H' }],
    },
    hatswat: {
      name: 'Overcharge', startup: 19, active: 2, recovery: 15,
      hits: [{ dmg: 58, box: [24, 96, 62, 66], level: 'ovh', stun: 19, bstun: 13, push: 30, hitstop: 12, spark: 'M', sfx: 'H' }],
      vel: [[4, 1.3], [19, 0]],
      cancel: { super: true },
    },
    upsell: {
      name: 'Upsell', startup: 9, active: 4, recovery: 22,
      hits: [{ dmg: 70, box: [18, 60, 58, 86], effect: 'launch', launch: [1.2, 13.5], juggle: 2, bstun: 15, push: 10, hitstop: 12, spark: 'H', sfx: 'H' }],
      hurt: [reach(8, 20, [10, 60, 62, 96])],
      cancel: { special: true, super: true },
    },

    // ------------------------------------------------------------ specials
    toss_pot: toss('pot'),
    toss_scroll: toss('scroll'),
    toss_chain: toss('chain'),
    haggle: (v) => {
      const ex = v === 'EX';
      const end = pick(v, [16, 20, 24, 28]);
      return {
        name: 'Haggle', type: ex ? 'ex' : 'special', startup: 3, active: end - 2, recovery: pick(v, [16, 18, 20, 15]),
        counter: { frames: [3, end], into: ex ? 'haggle_dealEX' : 'haggle_deal' },
        reflect: ex ? [3, end] : undefined, // EX also sends a projectile back ("no returns" — except these)
      };
    },
    haggle_deal: {
      name: 'Haggle', type: 'throw', startup: 1, active: 1, recovery: 1,
      grab: { len: 36, dmgAt: 22, toss: [6.5, 4], hold: 72, steal: 500 },
      hits: [{ dmg: 60, frames: [22, 22], spark: 'H', sfx: 'H', hitstop: 9, meter: 40 }],
    },
    haggle_dealEX: {
      name: 'Haggle', type: 'throw', startup: 1, active: 1, recovery: 1,
      grab: { len: 40, dmgAt: 24, toss: [7, 5], hold: 72, steal: 1000, hkd: true },
      hits: [{ dmg: 80, frames: [24, 24], spark: 'H', sfx: 'H', hitstop: 11, meter: 40 }],
    },
    chest: (v) => {
      const ex = v === 'EX';
      return {
        name: 'Mimic Chest', type: ex ? 'ex' : 'special', startup: 15, active: 2, recovery: pick(v, [18, 20, 22, 16]),
        proj: {
          at: 15, kind: 'mimic', place: 'dist', dist: pick(v, [70, 130, 195, 130]), y: 0.1, life: 420,
          box: [-34, 0, 68, 66], hits: 1, power: 9,
          trap: { arm: ex ? 6 : 34, range: ex ? 72 : 56, delay: 5 },
          hit: { dmg: ex ? 85 : 65, level: 'low', effect: 'launch', launch: [1, 9.5], juggle: 1, stun: 24, bstun: 18, push: 30, hitstop: 12, spark: 'H', sfx: 'H' },
        },
      };
    },
    swing: (v) => {
      const ex = v === 'EX';
      const su = pick(v, [6, 7, 8, 5]);
      const n = pick(v, [1, 2, 2, 3]);
      const dmg = pick(v, [[80], [40, 55], [45, 62], [35, 35, 62]]);
      return {
        name: 'Backpack Swing', type: ex ? 'ex' : 'special', startup: su, active: n * 7 - 3, recovery: pick(v, [20, 24, 27, 25]),
        invuln: v === 'H' ? { strike: [1, 8], throw: [1, 4] } : ex ? { full: [1, 10] } : { throw: [1, 4] },
        hits: dmg.map((d, k) => {
          const last = k === n - 1;
          return {
            dmg: d, frames: [su + k * 7, su + k * 7 + 3], box: [-42, 72, 152, 118], effect: 'launch',
            launch: last ? [1.5, 12] : [0.4, 7.5], juggle: last ? 1 : 0, stun: 20, bstun: 14, push: last ? 24 : 4,
            hitstop: last ? 13 : 8, spark: last ? 'H' : 'M', sfx: 'H', meter: last ? 30 : 15,
          };
        }),
        hurt: [reach(su, su + n * 7, [-46, 68, 160, 126])],
      };
    },
    crate: (v) => {
      const ex = v === 'EX';
      return {
        name: 'Price Drop', type: ex ? 'ex' : 'special', air: true, startup: 10, active: 2, recovery: 16, landRecovery: 6,
        float: [1, 14], vel: [[1, null, 2.4]],
        proj: {
          at: 10, kind: 'crate', x: 38, y: 170, vx: pick(v, [2.4, 4, 5.6, 4.4]), vy: -6, gravity: 0.25, life: 60,
          box: [-28, -28, 56, 56], hits: ex ? 2 : 1, every: 5, power: 2,
          hit: { dmg: pick(v, [65, 70, 75, 50]), level: 'ovh', effect: ex ? 'bounce' : 'kd', launch: [2, 5], stun: 22, bstun: 16, push: 30, hitstop: 12, spark: 'H', sfx: 'H' },
        },
      };
    },

    // ------------------------------------------------------------ supers
    clearance: {
      // flings the pack open (point-blank hit), then the stock rains down on wherever the opponent stands
      name: 'Clearance Sale', type: 'super', cost: 1000, freeze: 34, startup: 7, active: 4, recovery: 52,
      invuln: { strike: [1, 12], throw: [1, 12], proj: [1, 12] },
      hits: [{ dmg: 45, box: [10, 40, 112, 130], stun: 64, bstun: 30, push: 10, hitstop: 8, spark: 'S', sfx: 'H', meter: 0 }],
      proj: [12, 19, 26, 33, 41].map((at, k) => ({
        at, kind: WARES[k % 3], place: 'opp', offset: [-18, 14, -6, 18, 0][k], y: 330, vy: -17, life: 30,
        box: [-32, -32, 64, 64], hits: 1, power: 3,
        hit: { dmg: k === 4 ? 75 : 50, stun: 26, bstun: 14, push: 6, hitstop: 7, spark: 'H', sfx: 'H', effect: k === 4 ? 'kd' : 'normal', launch: [2, 7], meter: 0 },
      })),
    },
    mustgo: {
      name: 'Everything Must Go', type: 'final', cost: 3000, freeze: 44, startup: 9, active: 6, recovery: 44,
      invuln: { full: [1, 15] },
      vel: [[1, 5], [12, 0]],
      hits: [{ dmg: 30, box: [10, 20, 130, 150], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 175, hold: 100, hits: [[30, 110], [62, 40], [80, 40], [98, 40], [150, 200]] },
    },
    offer: {
      name: 'Final Offer', type: 'overtime', freeze: 44, startup: 12, active: 6, recovery: 40,
      invuln: { full: [1, 18] },
      hits: [{ dmg: 30, box: [0, 0, 210, 200], stun: 60, hitstop: 4, spark: 'S', sfx: 'H', meter: 0 }],
      cine: { len: 150, hold: 120, hits: [[48, 120], [118, 230]] },
    },
    ...universal({ throwDmg: 115, bthrowDmg: 125 }),
  },
  // presentation
  colors: ['#d9a62a', '#3f6fa8', '#8a2f2f', '#3d6b3a', '#5b3f7a', '#2b2b2b', '#d8d0c0', '#b5651d'],
  lines: {
    intro: "Everything's for sale.",
    win: ['Except Gary.', 'No refunds. No receipts. No Gary.', "I'll put it on your tab."],
  },
});
