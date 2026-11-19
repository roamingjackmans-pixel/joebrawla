// The modifiers screen: every game modifier as a row, grouped, with presets. Used before bot/couch matches and
// by the host in an online lobby (there the lobby passes onChange to sync each change to the guest).
import { show, esc, optRow, bindOpt, rerender } from './ui.js';
import { MODS, PRESETS, defaults, activeLabels } from '../../shared/modifiers.js';
import { profile, save } from '../profile.js';

/** resolves with the chosen modifiers ({} = standard), or null if the player backed out */
export function modsScreen({ title = 'RULES', key = 'default', readOnly = false, initial, onChange } = {}) {
  return new Promise((resolve) => {
    const p = profile();
    const mods = { ...defaults(), ...(initial || p.lastMods[key] || {}) };
    const groups = [...new Set(MODS.map((m) => m.group))];
    const fmt = (m, v) => (m.fmt ? m.fmt(v) : typeof v === 'boolean' ? (v ? 'On' : 'Off') : String(v));
    const screen = {
      id: 'mods',
      render: () => `<div class="shade-all" style="position:absolute;inset:0"></div><div style="position:relative">
        <h1 class="title-h">${esc(title)}<small>${readOnly ? 'The host sets the rules' : 'Change anything, or pick a preset'}</small></h1>
        <div class="tabs" style="flex-wrap:wrap">${Object.keys(PRESETS).map((n) => `<div class="tab" data-f data-preset="${esc(n)}">${esc(n)}</div>`).join('')}<div class="tab" data-f data-preset="__surprise">🎲 Surprise me</div></div>
        <div class="opts" style="max-width:820px;max-height:56vh">${groups.map((g) => `<div class="group-h">${esc(g)}</div>${MODS.filter((m) => m.group === g).map((m) => optRow(m.id, m.name + (m.desc ? '' : ''), '', m.desc ? `title="${esc(m.desc)}"` : '')).join('')}`).join('')}</div>
        <div style="margin-top:14px;display:flex;gap:10px">${readOnly ? '' : '<button class="btn big" data-f data-ok data-autofocus>Play</button>'}<button class="btn" data-f data-cancel>${readOnly ? 'Close' : 'Back'}</button></div></div>`,
      mount(el) {
        for (const m of MODS) {
          bindOpt(el, m.id, m.opts, () => mods[m.id], (v) => { if (readOnly) return; mods[m.id] = v; onChange?.(mods); }, (v) => fmt(m, v));
          const row = el.querySelector(`[data-id="${m.id}"] .lab`);
          if (row && m.desc) row.innerHTML = `${esc(m.name)}<em>${esc(m.desc)}</em>`;
        }
        el.querySelectorAll('[data-preset]').forEach((t) => t.addEventListener('click', () => {
          if (readOnly) return;
          const n = t.dataset.preset;
          Object.assign(mods, defaults());
          if (n === '__surprise') {
            for (const m of MODS) if (Math.random() < 0.25) mods[m.id] = m.opts[Math.floor(Math.random() * m.opts.length)];
            mods.oneHitKO = false; mods.noBlocking = false;
          } else Object.assign(mods, PRESETS[n]);
          onChange?.(mods);
          rerender();
        }));
        el.querySelector('[data-ok]')?.addEventListener('click', () => done(mods));
        el.querySelector('[data-cancel]')?.addEventListener('click', () => done(readOnly ? mods : null));
      },
      back: () => { done(readOnly ? mods : null); return true; },
    };
    function done(v) {
      if (v && !readOnly) { p.lastMods[key] = { ...v }; save(); }
      resolve(v ? stripDefaults(v) : null);
    }
    show(screen, {}, { root: true });
  });
}

export function stripDefaults(m) {
  const d = defaults(), out = {};
  for (const k of Object.keys(m)) if (m[k] !== d[k]) out[k] = m[k];
  return out;
}
export { activeLabels };
