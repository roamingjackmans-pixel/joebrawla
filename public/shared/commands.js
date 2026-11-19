// Reading what a player meant from their raw inputs: input history, motion inputs, button buffers.
// Deterministic; lives in the fighter's state so it rolls back with everything else.
// History is stored in absolute directions (as if facing right) and read relative to the fighter's facing
// when the button is pressed, so motions done during a cross-up come out the way Street Fighter's do.
import { IN, numpad } from './core.js';

export const HIST = 32;          // frames of direction history kept
export const BUFFER = 6;         // a button press stays usable this many frames
const BTN = [IN.L, IN.M, IN.H, IN.S, IN.SUPER, IN.THROW, IN.BREAKER, IN.TAUNT];
export const BTN_INDEX = { L: 0, M: 1, H: 2, S: 3, SUPER: 4, THROW: 5, BREAKER: 6, TAUNT: 7 };
const FLIP = [5, 3, 2, 1, 6, 5, 4, 9, 8, 7];

export function newInputState() {
  return { dirs: new Array(HIST).fill(5), head: 0, held: 0, prev: 0, age: [99, 99, 99, 99, 99, 99, 99, 99], backAge: 99, dir: 5, mot: {} };
}

/** record this frame's raw bits; facing is the fighter's facing this frame */
export function feed(inp, bits, facing, frozen = false) {
  inp.prev = inp.held;
  inp.held = bits;
  inp.head = (inp.head + 1) % HIST;
  inp.dirs[inp.head] = numpad(bits, 1);
  const d = numpad(bits, facing);
  const wasBack = inp.dir === 1 || inp.dir === 4 || inp.dir === 7;
  const isBackNow = d === 1 || d === 4 || d === 7;
  inp.dir = d;
  inp.backAge = isBackNow ? (wasBack ? Math.min(inp.backAge + 1, 99) : 0) : 99;
  const pressed = bits & ~inp.prev;
  for (let i = 0; i < BTN.length; i++) {
    if (pressed & BTN[i]) inp.age[i] = 0;
    else if (inp.age[i] < 99 && !frozen) inp.age[i]++;
  }
  // motions are judged when a button is pressed and remembered with that press (so a special pressed during
  // hitstop or recovery still comes out when the fighter is free)
  if (!frozen) for (const k in inp.mot) { inp.mot[k]++; if (inp.mot[k] > 20) delete inp.mot[k]; }
  if (pressed & (IN.L | IN.M | IN.H | IN.S | IN.SUPER)) {
    for (const name of MOTION_NAMES) if (did(inp, name, facing)) inp.mot[name] = 0;
  }
}

/** frames since a button press that came with this motion (99 if none) */
export const motionAge = (inp, name) => (inp.mot[name] ?? 99);

/** facing changed: the current relative direction flips too */
export function refreshDir(inp, facing) { inp.dir = numpad(inp.held, facing); }

export const pressedWithin = (inp, name, frames = BUFFER) => inp.age[BTN_INDEX[name]] <= frames;
export const pressAge = (inp, name) => inp.age[BTN_INDEX[name]];
export const consume = (inp, name) => { inp.age[BTN_INDEX[name]] = 99; };
export const heldBtn = (inp, bit) => (inp.held & bit) !== 0;

// motion patterns: each is a list of steps, each step a set of numpad directions.
const P = (...steps) => steps.map((s) => new Set(String(s).split('').map(Number)));
const MOTIONS = {
  '236236': { win: 32, pats: [P(2, 3, 6, 2, 3, 6), P(2, 6, 2, 6), P(2, 3, 2, 3, 6)] },
  '214214': { win: 32, pats: [P(2, 1, 4, 2, 1, 4), P(2, 4, 2, 4), P(2, 1, 2, 1, 4)] },
  '41236': { win: 24, pats: [P(4, 1, 2, 3, 6), P(4, 2, 6), P(4, 1, 3, 6), P(4, 2, 3, 6)] },
  '623': { win: 16, pats: [P(6, 2, 3), P(6, 1, 3), P(6, 3, 2, 3)] },
  '236': { win: 15, pats: [P(2, 3, 6), P(2, 6), P(1, 3, 6)] },
  '214': { win: 15, pats: [P(2, 1, 4), P(2, 4), P(3, 1, 4)] },
  '22': { win: 14, pats: [P(123, 456789, 123)] },
};

const MOTION_NAMES = ['236236', '214214', '41236', '623', '236', '214', '22'];

/** did the player do this motion recently (read relative to `facing`)? */
export function did(inp, motion, facing) {
  const m = MOTIONS[motion];
  if (!m) return false;
  for (const pat of m.pats) {
    let step = 0;
    for (let k = m.win - 1; k >= 0; k--) {
      let d = inp.dirs[(inp.head - k + HIST * 2) % HIST];
      if (facing < 0) d = FLIP[d];
      if (pat[step].has(d)) { step++; if (step === pat.length) return true; }
    }
  }
  return false;
}

/** simple-scheme direction class for S moves: 5 (none), 6, 4, 2 */
export function simpleDir(inp) {
  const d = inp.dir;
  if (d === 2 || d === 1 || d === 3) return 2;
  if (d === 6 || d === 9) return 6;
  if (d === 4 || d === 7) return 4;
  return 5;
}
