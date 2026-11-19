// JoeBrawla simulation core: units, constants, input bits, RNG. Deterministic: integers only.
// 1 unit = 0.1 mm. CM = 100 units. Moves are authored in centimetres and converted with cm().

export const FPS = 60;
export const CM = 100;
export const M = 10000;
export const cm = (v) => Math.round(v * CM);

// stage and physics
export const WALL = 750 * CM;            // walls at ±7.5 m
export const MAX_GAP = 560 * CM;         // fighters can't walk further apart than this (camera)
export const START_X = 150 * CM;         // ±1.5 m at round start
export const GROUND = 0;
export const GRAVITY = 73;               // units / frame² (0.73 cm/f²)
export const WALL_SPLAT_RANGE = 160 * CM;

// raw input bits (what devices produce and the network sends)
export const IN = {
  UP: 1, DOWN: 2, LEFT: 4, RIGHT: 8,
  L: 16, M: 32, H: 64, S: 128, SUPER: 256, THROW: 512, BREAKER: 1024, TAUNT: 2048,
};
export const BUTTONS = IN.L | IN.M | IN.H | IN.S | IN.SUPER | IN.THROW | IN.BREAKER | IN.TAUNT;
export const ATTACKS = IN.L | IN.M | IN.H;

/** numpad direction (1-9) relative to facing (+1 = facing right) */
export function numpad(bits, facing) {
  const up = bits & IN.UP, down = bits & IN.DOWN;
  let fwd = 0;
  const right = bits & IN.RIGHT ? 1 : 0, left = bits & IN.LEFT ? 1 : 0;
  if (right && !left) fwd = facing > 0 ? 1 : -1;
  else if (left && !right) fwd = facing > 0 ? -1 : 1;
  const v = up && !down ? 1 : down && !up ? -1 : 0;
  return 5 + fwd + v * 3;
}
export const isDown = (n) => n === 1 || n === 2 || n === 3;
export const isUp = (n) => n === 7 || n === 8 || n === 9;
export const isBack = (n) => n === 1 || n === 4 || n === 7;
export const isFwd = (n) => n === 3 || n === 6 || n === 9;

// deterministic RNG (xorshift32) stored in state.rng
export function rand(state, n) {
  let x = state.rng | 0;
  x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
  state.rng = x | 0;
  return ((x >>> 0) % n);
}
export function seedFrom(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return (h | 1) | 0;
}

export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const sign = (v) => (v > 0 ? 1 : v < 0 ? -1 : 0);
/** integer percentage */
export const pct = (v, p) => Math.trunc((v * p) / 100);

/** a stable 32-bit checksum of a JSON-able value (desync detection) */
export function checksum(obj) {
  const s = JSON.stringify(obj);
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}
