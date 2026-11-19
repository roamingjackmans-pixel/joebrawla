// Character select (one or two cursors), bot difficulty, stage select, the VS splash and the results screen.
import { show, esc, focus, modal, toast } from './ui.js';
import { FIGHTERS, ORDER } from '../../shared/fighters/index.js';
import { LEVELS } from '../../shared/bot.js';
import { STAGES } from '../render/stages.js';
import { profile, save, isUnlocked, unlockHint, colorsFor } from '../profile.js';
import { getPortrait } from '../render/portraits.js';
import { readDevice } from '../input.js';
import { IN } from '../../shared/core.js';
import { audio } from '../audio.js';
import { app } from '../app.js';
import { showMoveList } from './menus.js';

const BLURB = {
  joe: 'Apartment 3C went down to find the breaker box and came back up knowing how to fight. Fireballs, uppercuts, a Thermos.',
  gary: 'Everything’s for sale. Random wares, mimic traps, haggling counters. Except Gary.',
  instructor: 'Management’s orientation officer. Counters, corrections, a whistle. Nobody passes.',
  hollow_knight: 'Still guarding a door nobody uses. Sword, shield, patience.',
  brannigan: 'The old boilerman. A steam-powered boxer who never stops coming.',
  caretaker: 'Ruler of the Mossy Crypt. Huge reach, grave hands, burials.',
  mother_spore: 'Ruler of the Fungal Hollows. Spores, traps, children that hop.',
  bloatking: 'Ruler of the Drowned Quarter. Grabs you from far away. The court is underwater.',
  vexthorn: 'The Hollow Stag. Fast, silent, teleports in a swirl of leaves.',
  ignatius: 'Foreman of the Ashen Forge. Armoured swings, molten metal, overtime.',
  aurelia: 'The Unthawed saint. Ice lances, mirrors, hovering keep-away.',
  tock: 'Keeper of every lease. Rewinds, gear traps, stops time.',
  landlord: 'He doesn’t conquer. He leases.',
};
export const ARCH = {
  joe: 'All-rounder', gary: 'Trickster', instructor: 'Counters', hollow_knight: 'Footsies', brannigan: 'Rushdown',
  caretaker: 'Big body', mother_spore: 'Zoner / traps', bloatking: 'Grappler', vexthorn: 'Rushdown / mix-ups',
  ignatius: 'Armoured heavy', aurelia: 'Keep-away', tock: 'Setups', landlord: 'Final boss',
};

const ROWS = [ORDER.slice(0, 7), [...ORDER.slice(7), 'random']];

/**
 * Character select. opts: { title, players: 1|2, devices: [dev, dev] (2P), labels: ['P1','CPU'],
 *   fixed: [id|null, id|null] (pre-set picks), allowLocked: false, lockedFor: [bool, bool], onDone({fighters, colors, schemes}), onBack }
 * In 1-player mode with `pickBoth`, P1 picks their own then the opponent's fighter.
 */
export function characterSelect(opts) {
  const p = profile();
  const st = {
    cur: [Math.max(0, ORDER.indexOf(p.lastFighter)), 1], picked: [null, null], color: [p.lastColor[p.lastFighter] || 0, 1],
    scheme: [p.settings.scheme[0], p.settings.scheme[1]], stage: opts.pickBoth ? 0 : 0, active: 0,
  };
  const two = opts.players === 2;
  const ids = (i) => { const flat = ROWS.flat(); return flat[st.cur[i]]; };
  const screen = {
    id: 'select',
    render: () => `<div class="shade-b" style="position:absolute;inset:0"></div>
      <div class="sel-top"><h1 class="title-h" style="font-size:clamp(28px,3.4vw,48px)">${esc(opts.title || 'CHOOSE YOUR FIGHTER')}</h1><div class="sub" id="selsub"></div></div>
      ${[0, 1].map((i) => `<div class="sel-side p${i}" id="side${i}"></div>`).join('')}
      <div class="grid-wrap">${ROWS.map((r, ri) => `<div class="grid-row">${r.map((id, ci) => {
        const idx = ri * 7 + ci;
        const lock = id !== 'random' && !isUnlocked(id) && !opts.allowLocked;
        return `<div class="tile ${id === 'random' ? 'rand' : ''} ${lock ? 'lock' : ''}" data-idx="${idx}" data-id="${id}"><div class="ini">${id === 'random' ? '?' : esc(FIGHTERS[id].name.replace('The ', '')[0])}</div><img alt="" style="display:none"><div class="tn">${id === 'random' ? 'Random' : esc(FIGHTERS[id].name.replace('The ', ''))}</div></div>`;
      }).join('')}</div>`).join('')}</div>
      <div class="hint-bar"><span><span class="kbd">←→↑↓</span> move</span><span><span class="kbd">J</span>/<span class="kbd">A</span> pick</span><span><span class="kbd">U</span>/<span class="kbd">I</span> or <span class="kbd">LB</span>/<span class="kbd">RB</span> colour</span><span><span class="kbd">O</span>/<span class="kbd">Y</span> moves</span><span><span class="kbd">P</span>/<span class="kbd">X</span> Classic/Simple</span><span><span class="kbd">Esc</span> back</span></div>`,
    mount(el) {
      this.el = el;
      // portraits load in the background
      for (const t of el.querySelectorAll('.tile[data-id]')) {
        const id = t.dataset.id; if (id === 'random') continue;
        getPortrait(id, app.scene.renderer).then((url) => { if (url) { const img = t.querySelector('img'); img.src = url; img.style.display = ''; t.querySelector('.ini').style.display = 'none'; } });
      }
      el.querySelectorAll('.tile').forEach((t) => t.addEventListener('click', () => { st.cur[st.active] = +t.dataset.idx; this.paint(); this.pick(st.active); }));
      el.querySelectorAll('.tile').forEach((t) => t.addEventListener('mouseenter', () => { if (st.picked[st.active] == null) { st.cur[st.active] = +t.dataset.idx; this.paint(); } }));
      app.showcase.setMode('select');
      if (opts.fixed) opts.fixed.forEach((f, i) => { if (f) { st.picked[i] = f; } });
      if (opts.pickBoth || !two) st.active = st.picked[0] ? 1 : 0;
      this.prevBits = [0, 0];
      this.paint();
    },
    paint() {
      const el = this.el;
      el.querySelectorAll('.tile').forEach((t) => {
        const i = +t.dataset.idx;
        t.classList.toggle('c0', st.cur[0] === i && (two || st.active === 0 || st.picked[0]));
        t.classList.toggle('c1', st.cur[1] === i && (two || st.active === 1));
      });
      for (let i = 0; i < 2; i++) {
        const side = el.querySelector('#side' + i);
        const show2 = two || opts.pickBoth || i === 0 || opts.fixed?.[1];
        if (!show2) { side.innerHTML = ''; app.showcase.setFighter(i, null); continue; }
        const id = st.picked[i] || ids(i);
        if (id === 'random') { side.innerHTML = `<div class="who">${esc(opts.labels?.[i] || `P${i + 1}`)}</div><div class="nm">RANDOM</div>`; app.showcase.setFighter(i, null); continue; }
        const d = FIGHTERS[id];
        const locked = !isUnlocked(id) && !opts.allowLocked;
        const nCol = colorsFor(id);
        side.innerHTML = `<div class="who">${esc(opts.labels?.[i] || `P${i + 1}`)}</div><div class="nm">${esc(locked ? '???' : d.name)}</div><div class="ttl">${esc(locked ? 'Locked' : d.title || '')}</div>
          <div class="arch">${esc(ARCH[id] || '')} · HP ${d.hp}</div>
          <div class="blurb">${esc(locked ? unlockHint(id) : BLURB[id] || '')}</div>
          ${locked ? '' : `<div class="swatches">${(d.colors || []).map((c, k) => `<i style="background:${c}" class="${k === st.color[i] ? 'on' : ''} ${k >= nCol ? 'lock' : ''}"></i>`).join('')}</div>
          <div class="scheme">Controls: <b>${st.scheme[i] === 'simple' ? 'Simple' : 'Classic'}</b></div>`}
          ${st.picked[i] ? '<div class="ready">READY</div>' : ''}`;
        if (!locked) app.showcase.setFighter(i, id, st.color[i], st.picked[i] ? 'win' : 'idle'); else app.showcase.setFighter(i, null);
      }
      const sub = el.querySelector('#selsub');
      if (sub) sub.textContent = opts.pickBoth ? (st.active === 0 ? 'Pick your fighter' : 'Pick your opponent') : two ? 'Both players pick' : '';
    },
    move(i, dx, dy) {
      if (st.picked[i]) return;
      const flat = ROWS.flat();
      let r = st.cur[i] < 7 ? 0 : 1, c = r ? st.cur[i] - 7 : st.cur[i];
      if (dy) { r = (r + dy + 2) % 2; c = Math.min(c, ROWS[r].length - 1); }
      if (dx) c = (c + dx + ROWS[r].length) % ROWS[r].length;
      st.cur[i] = r * 7 + c;
      audio.ui('move');
      void flat;
      this.paint();
    },
    pick(i) {
      let id = ids(i);
      if (id === 'random') { const pool = ORDER.filter((x) => isUnlocked(x) || opts.allowLocked); id = pool[Math.floor(Math.random() * pool.length)]; }
      if (!isUnlocked(id) && !opts.allowLocked) { audio.ui('err'); toast(esc(unlockHint(id))); return; }
      if (st.color[i] >= colorsFor(id)) st.color[i] = 0;
      if (st.picked[1 - i] === id && st.color[1 - i] === st.color[i]) st.color[i] = (st.color[i] + 1) % Math.max(2, colorsFor(id));
      st.picked[i] = id;
      audio.ui('big');
      if (!two && opts.pickBoth && i === 0) { st.active = 1; st.cur[1] = st.cur[0]; }
      this.paint();
      const need = two || opts.pickBoth ? [0, 1] : [0];
      if (need.every((k) => st.picked[k])) {
        const pr = profile(); pr.lastFighter = st.picked[0]; pr.lastColor[st.picked[0]] = st.color[0]; pr.settings.scheme = st.scheme.slice(); save();
        setTimeout(() => opts.onDone({ fighters: st.picked.slice(), colors: st.color.slice(), schemes: st.scheme.slice() }), 450);
      }
    },
    unpick(i) {
      if (st.picked[i]) { st.picked[i] = null; this.paint(); audio.ui('back'); return true; }
      if (opts.pickBoth && i === 1) { st.active = 0; st.picked[0] = null; this.paint(); audio.ui('back'); return true; }
      return false;
    },
    color(i, d) {
      const id = st.picked[i] || ids(i); if (id === 'random') return;
      const n = colorsFor(id);
      st.color[i] = (st.color[i] + d + n) % n; audio.ui('tab'); this.paint();
    },
    // one cursor (menu navigation) or two (each player's own device)
    nav(edge, NAV) {
      if (two) return true; // handled in tick by device
      const i = st.active;
      if (edge & NAV.left) this.move(i, -1, 0);
      if (edge & NAV.right) this.move(i, 1, 0);
      if (edge & NAV.up) this.move(i, 0, -1);
      if (edge & NAV.down) this.move(i, 0, 1);
      if (edge & NAV.ok) this.pick(i);
      if (edge & NAV.tabL) this.color(i, -1);
      if (edge & NAV.tabR) this.color(i, 1);
      if (edge & NAV.back) { if (!this.unpick(i)) opts.onBack?.(); }
      return true;
    },
    keys(code) {
      const i = two ? null : st.active;
      if (i == null) return false;
      if (code === 'KeyU') this.color(i, -1);
      if (code === 'KeyI') this.color(i, 1);
      if (code === 'KeyO' || code === 'KeyM') { const id = st.picked[i] || ids(i); if (id !== 'random') showMoveList(id, st.scheme[i]); }
      if (code === 'KeyP') { st.scheme[i] = st.scheme[i] === 'simple' ? 'classic' : 'simple'; this.paint(); }
      return false;
    },
    tick() {
      // gamepad extras (Y = move list, X = scheme) and couch cursors
      const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
      if (!two) {
        for (const p of pads) {
          const y = p.buttons[3]?.pressed, x = p.buttons[2]?.pressed;
          if (y && !this.py) { const id = st.picked[st.active] || ids(st.active); if (id !== 'random') showMoveList(id, st.scheme[st.active]); }
          if (x && !this.px) { st.scheme[st.active] = st.scheme[st.active] === 'simple' ? 'classic' : 'simple'; this.paint(); }
          this.py = y; this.px = x;
        }
        return;
      }
      for (let i = 0; i < 2; i++) {
        const b = readDevice(opts.devices[i]);
        const e = b & ~this.prevBits[i];
        this.prevBits[i] = b;
        if (e & IN.LEFT) this.move(i, -1, 0);
        if (e & IN.RIGHT) this.move(i, 1, 0);
        if (e & IN.UP) this.move(i, 0, -1);
        if (e & IN.DOWN) this.move(i, 0, 1);
        if (e & IN.L) this.pick(i);
        if (e & IN.M) { if (!this.unpick(i) && i === 0) opts.onBack?.(); }
        if (e & IN.THROW) this.color(i, -1);
        if (e & IN.S) this.color(i, 1);
        if (e & IN.TAUNT) { st.scheme[i] = st.scheme[i] === 'simple' ? 'classic' : 'simple'; this.paint(); }
      }
    },
    back: () => true,
  };
  show(screen, {}, { root: true });
}

// ---------------------------------------------------------------- bot difficulty
export function difficultySelect({ title = 'DIFFICULTY', onDone, onBack, def = 1 }) {
  const screen = {
    id: 'stage',
    render: () => `<div class="shade-b" style="position:absolute;inset:0"></div><div style="position:relative">
      <h1 class="title-h">${esc(title)}</h1><div class="stage-row" style="margin-top:20px">${LEVELS.map((l, i) => `<div class="stage-card" data-f data-i="${i}" ${i === def ? 'data-autofocus' : ''}><b>${esc(l.name)}</b><span>${['Learning the stairs.', 'Knows a combo or two.', 'Blocks, punishes, anti-airs.', 'Reads you. Owns the building.'][i]}</span></div>`).join('')}</div></div>`,
    mount: (el) => el.querySelectorAll('[data-i]').forEach((c) => c.addEventListener('click', () => onDone(+c.dataset.i))),
    back: () => { onBack?.(); return true; },
  };
  show(screen, {}, { root: true });
}

// ---------------------------------------------------------------- stage select
export function stageSelect({ onDone, onBack, extra = '', title = 'CHOOSE A STAGE' }) {
  const list = STAGES.filter((s) => !s.hidden);
  const p = profile();
  const screen = {
    id: 'stage',
    render: () => `<div class="shade-b" style="position:absolute;inset:0"></div><div style="position:relative">
      <h1 class="title-h">${esc(title)}</h1><div class="sub" style="margin:6px 0 14px">${extra}</div>
      <div class="stage-row">${[...list, { id: 'random', name: 'Random', realm: '?', blurb: 'Any realm.' }].map((s) => `<div class="stage-card" data-f data-id="${s.id}" ${s.id === p.lastStage ? 'data-autofocus' : ''}><b>${esc(s.name)}</b><span>${esc(s.realm)} · ${esc(s.blurb)}</span></div>`).join('')}</div></div>`,
    mount(el) {
      el.addEventListener('focuschange', (e) => { const id = e.detail.dataset.id; if (id && id !== 'random') app.showcase.setStage(id); });
      el.querySelectorAll('[data-id]').forEach((c) => c.addEventListener('click', () => {
        let id = c.dataset.id;
        if (id === 'random') id = list[Math.floor(Math.random() * list.length)].id;
        p.lastStage = id; save();
        onDone(id);
      }));
      app.showcase.setMode('title');
      app.showcase.setFighter(0, null); app.showcase.setFighter(1, null);
    },
    back: () => { onBack?.(); return true; },
  };
  show(screen, {}, { root: true });
}

// ---------------------------------------------------------------- VS splash
export function vsScreen({ fighters, colors, names, tags = ['', ''], info = '', mods = [], stage, ms = 2600 }) {
  return new Promise((resolve) => {
    app.showcase.setMode('vs');
    if (stage) app.showcase.setStage(stage);
    app.showcase.setFighter(0, fighters[0], colors[0], 'intro');
    app.showcase.setFighter(1, fighters[1], colors[1], 'intro');
    const d = fighters.map((f) => FIGHTERS[f]);
    const screen = {
      id: 'vs',
      render: () => `<div class="vs-names"><div><div class="tag">${esc(tags[0])}</div><div class="nm">${esc(names?.[0] || d[0].name)}</div><div class="ttl">${esc(d[0].title || '')}</div><div class="line">“${esc(d[0].lines?.intro || '')}”</div></div>
        <div class="r"><div class="tag">${esc(tags[1])}</div><div class="nm">${esc(names?.[1] || d[1].name)}</div><div class="ttl">${esc(d[1].title || '')}</div><div class="line">“${esc(d[1].lines?.intro || '')}”</div></div></div>
        <div class="vs-mark">VS</div><div class="vs-info">${info}${mods.length ? `<div class="mods">${mods.map(esc).join(' · ')}</div>` : ''}</div>`,
      nav: () => true,
    };
    show(screen, {}, { root: true });
    audio.ui('big'); audio.gong();
    setTimeout(resolve, ms);
  });
}

// ---------------------------------------------------------------- results
/**
 * opts: { winnerIdx, fighters, colors, names, stats, rewards: [{text, cls}], buttons: [{label, value}], title }
 */
export function resultsScreen(opts) {
  return new Promise((resolve) => {
    const w = opts.winnerIdx;
    const wid = w >= 0 ? opts.fighters[w] : opts.fighters[0];
    const d = FIGHTERS[wid];
    app.showcase.setMode('results');
    app.showcase.setFighter(0, wid, opts.colors[Math.max(0, w)], 'win');
    app.showcase.setFighter(1, null);
    const quote = (d.lines?.win || [''])[Math.floor(Math.random() * (d.lines?.win?.length || 1))];
    const s = opts.stats;
    const screen = {
      id: 'results',
      render: () => `<div class="shade-l" style="position:absolute;inset:0"></div><div style="position:relative">
        <div class="res-head"><div class="sub">${esc(opts.title || (w < 0 ? 'DRAW' : `${opts.names?.[w] || (w === 0 ? 'Player 1' : 'Player 2')} WINS`))}</div>
        <div class="nm">${esc(w < 0 ? 'DRAW' : d.name)}</div><div class="quote">“${esc(quote)}”</div></div>
        ${s ? `<div class="res-stats">${[['Damage dealt', s[0].dmg, s[1].dmg], ['Hits', s[0].hits, s[1].hits], ['Best combo', s[0].best, s[1].best], ['Just Blocks', s[0].jbs, s[1].jbs]].map(([k, a, b]) => `<div><span>${k}</span><b>${a} · ${b}</b></div>`).join('')}</div>` : ''}
        <div class="res-rewards">${(opts.rewards || []).map((r, i) => `<div class="rw ${r.cls || ''}" style="animation-delay:${0.3 + i * 0.25}s">${r.text}</div>`).join('')}</div></div>
        <div class="res-btns" style="position:relative">${opts.buttons.map((b, i) => `<button class="btn ${i === 0 ? 'big' : ''}" data-f data-i="${i}" ${i === 0 ? 'data-autofocus' : ''}>${esc(b.label)}</button>`).join('')}</div>`,
      mount: (el) => el.querySelectorAll('[data-i]').forEach((b) => b.addEventListener('click', () => resolve(opts.buttons[+b.dataset.i].value))),
      back: () => true,
    };
    show(screen, {}, { root: true });
    if (opts.rewards?.some((r) => r.cls === 'unlock')) setTimeout(() => audio.ui('big'), 900);
  });
}
