// Keyboard, mouse and gamepad -> the simulation's input bits (shared/core.js IN), per device.
// Devices: 'kb' (WASD + J K L I O U P), 'kb2' (arrows + numpad), 'kbm' (WASD + mouse buttons),
// 'pad0'..'pad3' (gamepads), and 'any' (keyboard + mouse + every pad: the default for one local player).
// Bindings are rebindable (settings) and stored in the profile.
import { IN } from '../shared/core.js';

export const ACTIONS = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'L', 'M', 'H', 'S', 'SUPER', 'THROW', 'BREAKER', 'TAUNT'];
export const ACTION_LABEL = { UP: 'Up / Jump', DOWN: 'Down / Crouch', LEFT: 'Left', RIGHT: 'Right', L: 'Light', M: 'Medium', H: 'Heavy', S: 'Special', SUPER: 'Super', THROW: 'Throw (L+M)', BREAKER: 'Breaker (M+H)', TAUNT: 'Taunt' };

export const DEFAULT_BINDS = {
  kb: { UP: ['KeyW'], DOWN: ['KeyS'], LEFT: ['KeyA'], RIGHT: ['KeyD'], L: ['KeyJ'], M: ['KeyK'], H: ['KeyL'], S: ['KeyI'], SUPER: ['KeyO'], THROW: ['KeyU'], BREAKER: ['KeyP'], TAUNT: ['Backspace'] },
  kb2: { UP: ['ArrowUp'], DOWN: ['ArrowDown'], LEFT: ['ArrowLeft'], RIGHT: ['ArrowRight'], L: ['Numpad1'], M: ['Numpad2'], H: ['Numpad3'], S: ['Numpad4'], SUPER: ['Numpad5'], THROW: ['Numpad6'], BREAKER: ['Numpad8'], TAUNT: ['Numpad0'] },
  kbm: { UP: ['KeyW', 'Space'], DOWN: ['KeyS'], LEFT: ['KeyA'], RIGHT: ['KeyD'], L: ['Mouse0'], M: ['KeyE', 'Mouse1'], H: ['Mouse2'], S: ['ShiftLeft'], SUPER: ['KeyR'], THROW: ['KeyQ'], BREAKER: ['KeyF'], TAUNT: ['KeyT'] },
  pad: { UP: ['b12', 'a1-'], DOWN: ['b13', 'a1+'], LEFT: ['b14', 'a0-'], RIGHT: ['b15', 'a0+'], L: ['b2'], M: ['b3'], H: ['b5'], S: ['b0'], SUPER: ['b7'], THROW: ['b1'], BREAKER: ['b6'], TAUNT: ['b8'] },
};

const keys = new Set();
const mouse = new Set();
// a tap shorter than a frame still counts: keys stay "down" for 45 ms after being pressed
const tapped = new Map();
const TAP_MS = 45;
const down = (c) => keys.has(c) || mouse.has(c) || (tapped.has(c) && performance.now() - tapped.get(c) < TAP_MS);
let binds = structuredClone(DEFAULT_BINDS);
let listeners = [];

export function setBinds(b) { binds = { ...structuredClone(DEFAULT_BINDS), ...(b || {}) }; }
export function getBinds() { return binds; }

export function initInput(target = window) {
  target.addEventListener('keydown', (e) => {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
    keys.add(e.code); if (!e.repeat) { tapped.set(e.code, performance.now()); navQueue |= KEY_NAV[e.code] || 0; }
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Backspace', 'Tab'].includes(e.code)) e.preventDefault();
    for (const l of listeners) l({ type: 'key', code: e.code, e });
  });
  target.addEventListener('keyup', (e) => keys.delete(e.code));
  target.addEventListener('blur', () => { keys.clear(); mouse.clear(); });
  const canvas = document.getElementById('c');
  const mdown = (e) => { mouse.add('Mouse' + e.button); tapped.set('Mouse' + e.button, performance.now()); for (const l of listeners) l({ type: 'mouse', code: 'Mouse' + e.button, e }); };
  (canvas || target).addEventListener('mousedown', mdown);
  target.addEventListener('mouseup', (e) => mouse.delete('Mouse' + e.button));
  (canvas || target).addEventListener('contextmenu', (e) => e.preventDefault());
}

/** raw listener for rebinding and menus: fn({type, code}) ; returns unsubscribe */
export function onRaw(fn) { listeners.push(fn); return () => { listeners = listeners.filter((x) => x !== fn); }; }

function pads() { return navigator.getGamepads ? Array.from(navigator.getGamepads()).filter(Boolean) : []; }

function padActive(pad, code) {
  if (code[0] === 'b') { const b = pad.buttons[+code.slice(1)]; return !!b && (b.pressed || b.value > 0.5); }
  if (code[0] === 'a') {
    const ax = pad.axes[+code[1]] || 0;
    return code.endsWith('-') ? ax < -0.5 : ax > 0.5;
  }
  return false;
}

function bitsFromKeys(map) {
  let bits = 0;
  for (const a of ACTIONS) for (const c of map[a] || []) if (down(c)) { bits |= IN[a]; break; }
  return bits;
}
function bitsFromPad(pad, map) {
  let bits = 0;
  for (const a of ACTIONS) for (const c of map[a] || []) if (padActive(pad, c)) { bits |= IN[a]; break; }
  return bits;
}

/** current bits for a device id */
export function readDevice(dev) {
  let bits = 0;
  if (dev === 'any') {
    bits |= bitsFromKeys(binds.kb) | bitsFromKeys(binds.kbm) | bitsFromKeys(binds.kb2);
    for (const p of pads()) bits |= bitsFromPad(p, binds.pad);
  } else if (dev === 'kb' || dev === 'kb2' || dev === 'kbm') bits = bitsFromKeys(binds[dev]);
  else if (dev.startsWith('pad')) {
    const p = pads().find((x) => x.index === +dev.slice(3));
    if (p) bits = bitsFromPad(p, binds.pad);
  }
  // opposite directions cancel (SOCD: left+right = neutral, up+down = up)
  if ((bits & IN.LEFT) && (bits & IN.RIGHT)) bits &= ~(IN.LEFT | IN.RIGHT);
  if ((bits & IN.UP) && (bits & IN.DOWN)) bits &= ~IN.DOWN;
  return bits;
}

/** which devices have something pressed right now (couch "press a button to join") */
export function activeDevices() {
  const out = [];
  const anyKey = (map) => ACTIONS.slice(4).some((a) => (map[a] || []).some((c) => down(c)));
  if (anyKey(binds.kb)) out.push('kb');
  if (anyKey(binds.kb2)) out.push('kb2');
  if (anyKey(binds.kbm) && !anyKey(binds.kb)) out.push('kbm');
  for (const p of pads()) if (p.buttons.some((b, i) => i < 12 && b.pressed)) out.push('pad' + p.index);
  return out;
}

// ---------------------------------------------------------------- menu navigation (edges)
let prevNav = 0;
// menu presses are queued as events, so a tap is never lost even when frames are slow
let navQueue = 0;
const KEY_NAV = { ArrowUp: 1, KeyW: 1, ArrowDown: 2, KeyS: 2, ArrowLeft: 4, KeyA: 4, ArrowRight: 8, KeyD: 8, Enter: 16, KeyJ: 16, Space: 16, Escape: 32, KeyK: 32 };
const NAV = { up: 1, down: 2, left: 4, right: 8, ok: 16, back: 32, tabL: 64, tabR: 128, start: 256 };
export function readNav() {
  let n = 0;
  if (down('ArrowUp') || down('KeyW')) n |= NAV.up;
  if (down('ArrowDown') || down('KeyS')) n |= NAV.down;
  if (down('ArrowLeft') || down('KeyA')) n |= NAV.left;
  if (down('ArrowRight') || down('KeyD')) n |= NAV.right;
  if (down('Enter') || down('KeyJ') || down('Space')) n |= NAV.ok;
  if (down('Escape') || down('KeyK')) n |= NAV.back;
  for (const p of pads()) {
    if (padActive(p, 'b12') || padActive(p, 'a1-')) n |= NAV.up;
    if (padActive(p, 'b13') || padActive(p, 'a1+')) n |= NAV.down;
    if (padActive(p, 'b14') || padActive(p, 'a0-')) n |= NAV.left;
    if (padActive(p, 'b15') || padActive(p, 'a0+')) n |= NAV.right;
    if (padActive(p, 'b0')) n |= NAV.ok;
    if (padActive(p, 'b1')) n |= NAV.back;
    if (padActive(p, 'b4')) n |= NAV.tabL;
    if (padActive(p, 'b5')) n |= NAV.tabR;
    if (padActive(p, 'b9')) n |= NAV.start;
  }
  const edge = (n & ~prevNav) | navQueue;
  navQueue = 0;
  prevNav = n;
  return { held: n, edge, NAV };
}
export { NAV };

export function keyLabel(code) {
  if (!code) return '—';
  if (code.startsWith('Key')) return code.slice(3);
  if (code.startsWith('Digit')) return code.slice(5);
  if (code.startsWith('Numpad')) return 'Num' + code.slice(6);
  if (code.startsWith('Mouse')) return ['Left click', 'Middle click', 'Right click', 'Mouse 4', 'Mouse 5'][+code.slice(5)] || code;
  if (code.startsWith('Arrow')) return { ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→' }[code];
  if (code[0] === 'b') return ['A', 'B', 'X', 'Y', 'LB', 'RB', 'LT', 'RT', 'View', 'Start', 'L3', 'R3', 'D↑', 'D↓', 'D←', 'D→'][+code.slice(1)] || code;
  if (code[0] === 'a') return 'Stick ' + (code[1] === '0' ? (code.endsWith('-') ? '←' : '→') : code.endsWith('-') ? '↑' : '↓');
  return code.replace('Left', ' L').replace('Right', ' R');
}
