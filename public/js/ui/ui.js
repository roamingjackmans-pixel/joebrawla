// Menu framework: screens in #menu, spatial focus navigation with keyboard / gamepad / mouse, option rows that
// change with left/right, toasts and modal dialogs.
import { readNav, onRaw } from '../input.js';
import { audio } from '../audio.js';

const root = () => document.getElementById('menu');
let current = null;
const stack = [];
let navLock = 0;
let repeatT = 0, lastHeld = 0;

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/**
 * show a screen. screen: { id, render(params) -> html, mount(el, params), back() -> true to stay, tick(dt), keys(code) }
 * opts.replace: don't push the current screen on the back stack
 */
export function show(screen, params = {}, opts = {}) {
  if (current && current.unmount) current.unmount();
  if (current && !opts.replace && !opts.root) stack.push({ screen: current.screen, params: current.params });
  if (opts.root) stack.length = 0;
  const el = root();
  el.classList.add('on');
  el.innerHTML = `<div class="screen screen-${screen.id || 'x'}">${screen.render ? screen.render(params) : ''}</div>`;
  current = { screen, params, el: el.firstElementChild };
  if (screen.mount) screen.mount(current.el, params);
  bindMouse(current.el);
  focusFirst();
  navLock = performance.now() + 120;
}

export function back() {
  if (current?.screen.back && current.screen.back(current.params) === true) return;
  const prev = stack.pop();
  if (!prev) return;
  audio.ui('back');
  if (current && current.unmount) current.unmount();
  current = null;
  show(prev.screen, prev.params, { replace: true });
}

export function hideMenu() {
  if (current && current.unmount) current.unmount();
  current = null; stack.length = 0;
  root().classList.remove('on'); root().innerHTML = '';
}
export const currentScreen = () => current;
export function rerender() { if (current) { const { screen, params } = current; current = null; show(screen, params, { replace: true }); } }

// ---------------------------------------------------------------- focus and navigation
const focusables = (scope = current?.el) => scope ? [...scope.querySelectorAll('[data-f]:not([disabled]):not(.hidden)')].filter((e) => e.offsetParent !== null) : [];
export function focused() { return current?.el.querySelector('[data-f].focus'); }
export function focus(el, silent) {
  if (!el) return;
  for (const e of current.el.querySelectorAll('.focus')) e.classList.remove('focus');
  el.classList.add('focus');
  el.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
  if (!silent) audio.ui('move');
  current.el.dispatchEvent(new CustomEvent('focuschange', { detail: el }));
}
function focusFirst() {
  const list = focusables();
  const pre = current.el.querySelector('[data-autofocus]') || list[0];
  if (pre) focus(pre, true);
}

function move(dx, dy) {
  const list = focusables(); if (!list.length) return;
  const cur = focused();
  if (!cur) { focus(list[0]); return; }
  if (cur.dataset.opt !== undefined && dx) { cycleOpt(cur, dx); return; }
  const a = cur.getBoundingClientRect();
  const ax = a.left + a.width / 2, ay = a.top + a.height / 2;
  let best = null, bestD = Infinity;
  for (const e of list) {
    if (e === cur) continue;
    const b = e.getBoundingClientRect();
    const bx = b.left + b.width / 2, by = b.top + b.height / 2;
    const vx = bx - ax, vy = by - ay;
    if (dx && Math.sign(vx) !== dx) continue;
    if (dy && Math.sign(vy) !== dy) continue;
    if (dx && Math.abs(vx) < 4) continue;
    if (dy && Math.abs(vy) < 4) continue;
    const d = dx ? Math.abs(vx) + Math.abs(vy) * 2.5 : Math.abs(vy) + Math.abs(vx) * 2.5;
    if (d < bestD) { bestD = d; best = e; }
  }
  if (best) focus(best);
  else if (cur.dataset.wrap !== undefined) { /* stay */ }
}

function cycleOpt(el, d) {
  el.dispatchEvent(new CustomEvent('opt', { detail: d }));
  audio.ui('tab');
}

function activate(el) {
  if (!el) return;
  if (el.dataset.opt !== undefined) { cycleOpt(el, 1); return; }
  audio.ui(el.dataset.sound || 'ok');
  el.click();
}

function bindMouse(scope) {
  scope.addEventListener('mousemove', (e) => {
    const t = e.target.closest('[data-f]');
    if (t && !t.classList.contains('focus')) focus(t, true);
  });
  scope.addEventListener('click', (e) => {
    const t = e.target.closest('[data-opt]');
    if (t && e.isTrusted) { const r = t.getBoundingClientRect(); cycleOpt(t, e.clientX < r.left + r.width * 0.35 ? -1 : 1); }
  });
}

/** call every frame */
export function tickUI(dt) {
  if (!current) return;
  const nav = readNav();
  const { edge, held, NAV } = nav;
  if (performance.now() < navLock) return;
  // key repeat on held directions
  const dirs = held & (NAV.up | NAV.down | NAV.left | NAV.right);
  let rep = 0;
  if (dirs && dirs === lastHeld) { repeatT += dt; if (repeatT > 0.38) { repeatT = 0.3; rep = dirs; } } else { repeatT = 0; }
  lastHeld = dirs;
  const e = edge | rep;
  if (current.screen.nav && current.screen.nav(e, NAV, held) === true) return;
  if (e & NAV.up) move(0, -1);
  else if (e & NAV.down) move(0, 1);
  else if (e & NAV.left) move(-1, 0);
  else if (e & NAV.right) move(1, 0);
  if (edge & NAV.ok) activate(focused());
  if (edge & NAV.back) back();
  if (edge & NAV.tabL) current.el.dispatchEvent(new CustomEvent('tab', { detail: -1 }));
  if (edge & NAV.tabR) current.el.dispatchEvent(new CustomEvent('tab', { detail: 1 }));
  if (current.screen.tick) current.screen.tick(dt);
}

// keyboard extras (typing into inputs shouldn't navigate)
onRaw((ev) => {
  if (ev.type !== 'key' || !current) return;
  if (current.screen.keys && current.screen.keys(ev.code, ev.e) === true) ev.e.preventDefault();
});

// ---------------------------------------------------------------- option rows
/**
 * An option row: label + current value, left/right (or click) cycles. returns html; wire with bindOpt.
 */
export function optRow(id, label, valueText, extra = '') {
  return `<div class="opt" data-f data-opt data-id="${id}" ${extra}><span class="lab">${esc(label)}</span><span class="val"><i class="arr">‹</i><b>${esc(valueText)}</b><i class="arr">›</i></span></div>`;
}
export function bindOpt(el, id, values, get, set, fmt = (v) => v) {
  const row = el.querySelector(`[data-opt][data-id="${id}"]`);
  if (!row) return;
  const paint = () => { row.querySelector('b').textContent = fmt(get()); };
  row.addEventListener('opt', (e) => {
    const i = values.indexOf(get());
    const n = values[(i + e.detail + values.length) % values.length];
    set(n); paint();
  });
  paint();
}

// ---------------------------------------------------------------- toasts and modals
export function toast(msg, ms = 3200) {
  const t = document.createElement('div'); t.innerHTML = msg;
  document.getElementById('toast').appendChild(t);
  setTimeout(() => t.remove(), ms);
}

/** a modal over everything; buttons: [{label, value, cls}] -> Promise(value) */
export function modal(html, buttons = [{ label: 'OK', value: true }], opts = {}) {
  return new Promise((resolve) => {
    const prev = current;
    const screen = {
      id: 'modal',
      render: () => `<div class="modal-back"><div class="modal ${opts.cls || ''}"><div class="modal-body">${html}</div><div class="modal-btns">${buttons.map((b, i) => `<button class="btn ${b.cls || ''}" data-f data-i="${i}" ${i === (opts.focus ?? 0) ? 'data-autofocus' : ''}>${esc(b.label)}</button>`).join('')}</div></div></div>`,
      mount: (el) => {
        el.querySelectorAll('[data-i]').forEach((b) => b.addEventListener('click', () => done(buttons[+b.dataset.i].value)));
        opts.mount?.(el);
      },
      back: () => { done(opts.cancel ?? null); return true; },
    };
    // modals render on top of the current screen
    const holder = document.createElement('div');
    holder.className = 'modal-layer';
    document.getElementById('overlay').appendChild(holder);
    const saved = current;
    holder.innerHTML = `<div class="screen screen-modal">${screen.render()}</div>`;
    current = { screen, params: {}, el: holder.firstElementChild };
    screen.mount(current.el);
    bindMouse(current.el);
    focusFirst();
    function done(v) {
      holder.remove();
      current = saved || prev;
      resolve(v);
    }
  });
}
