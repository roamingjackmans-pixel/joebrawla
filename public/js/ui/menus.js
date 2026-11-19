// Title, main menu, settings (controls with rebinding, video, audio, online, save), pause, results, move list.
import { show, back, hideMenu, esc, optRow, bindOpt, toast, modal, rerender, focus } from './ui.js';
import { profile, save, xpForLevel, exportSave, importSave } from '../profile.js';
import { ACTIONS, ACTION_LABEL, DEFAULT_BINDS, getBinds, setBinds, keyLabel, onRaw } from '../input.js';
import { audio } from '../audio.js';
import { FIGHTERS } from '../../shared/fighters/index.js';
import { app } from '../app.js';

const LORE = [
  '11:52 p.m., Building Nine. The lights go out for the third time this month.',
  'Every tenant is “Joe” on the lease, whatever their real name. Management prefers it.',
  'Under Building Nine are eight realms stacked like basement floors. A man in a very good suit owns all of them.',
  'Each floor has a breaker. Each ruler keeps theirs switched off, and guarded.',
  'The Instructor has trained every Joe. None has passed.',
  '“Everything’s for sale. Except Gary.”',
  'Joe’s Thermos: still warm. Nobody knows how. Nobody asks.',
];

// ---------------------------------------------------------------- title
export const TitleScreen = {
  id: 'title',
  render: () => `<div class="logo">JOEBRAWLA<small>A DUNGEON JOE FIGHTER</small></div><div class="press">PRESS ANY BUTTON</div>
    <div class="ver">${esc((window.JB_VERSION || {}).version || 'dev')} · keyboard, mouse or controller</div>`,
  mount(el) {
    this._done = false;
    el.addEventListener('click', () => this.go());
    this._off = onRaw(() => this.go());
    app.showcase.setMode('title');
  },
  go() { if (this._done) return; this._done = true; this._off?.(); audio.unlock(); audio.ui('big'); audio.music('menu'); show(MainMenu, {}, { root: true }); },
  nav(edge) { if (edge) this.go(); return true; },
  unmount() { this._off?.(); },
};

// ---------------------------------------------------------------- main menu
const ITEMS = [
  { id: 'online', label: 'Online Versus', sub: 'Brawl a friend · 4-digit codes · friends list' },
  { id: 'bot', label: 'Versus Bot', sub: 'Tenant, Superintendent, Management, The Landlord' },
  { id: 'arcade', label: 'Arcade Ladder', sub: 'Eight floors down to The Landlord' },
  { id: 'couch', label: 'Couch Versus', sub: 'Two players, one screen' },
  { id: 'survival', label: 'Survival', sub: 'One health bar. How far can you go?' },
  { id: 'bossrush', label: 'Boss Rush', sub: 'The eight realm rulers, back to back' },
  { id: 'training', label: 'Training', sub: 'Dummy, hitboxes, frame data, move lists' },
  { id: 'howto', label: 'How to Play', sub: 'Controls and the basics in one page' },
  { id: 'settings', label: 'Settings', sub: 'Controls, video, audio, save' },
];

export const MainMenu = {
  id: 'main',
  render() {
    const p = profile();
    const need = xpForLevel(p.level);
    const reqs = (p.requests || []).length;
    return `<div class="shade-l" style="position:absolute;inset:0"></div>
    <div class="main-grid" style="position:relative">
      <div>
        <h1 class="title-h">JOEBRAWLA<small>A Dungeon Joe fighter</small></h1>
        <div class="menu-list">${ITEMS.map((it, i) => `<div class="menu-item" data-f data-id="${it.id}" ${i === 0 ? 'data-autofocus' : ''}>${it.label}<small>${it.sub}</small>${it.id === 'online' && reqs ? `<span class="badge">${reqs} REQUEST${reqs > 1 ? 'S' : ''}</span>` : ''}</div>`).join('')}</div>
      </div>
      <div class="lore-box panel" style="position:absolute;right:0;bottom:2vh">${esc(LORE[Math.floor(Math.random() * LORE.length)])}</div>
    </div>
    <div class="profile-card panel"><div class="lv">${p.level}</div><div><div><b>${esc(p.name)}</b> · <span class="sub">${esc(p.title)}</span></div>
      <div class="xpbar"><i style="width:${Math.min(100, (p.xp / need) * 100)}%"></i></div>
      <div class="fc">FRIEND CODE <b>${esc(p.friendCode || '····')}</b></div></div></div>
    <div class="hint-bar"><span><span class="kbd">↑↓</span> choose</span><span><span class="kbd">Enter</span>/<span class="kbd">A</span> select</span></div>`;
  },
  mount(el) {
    el.querySelectorAll('.menu-item').forEach((m) => m.addEventListener('click', () => app.go(m.dataset.id)));
    app.showcase.setMode('title');
    const p = profile();
    if (!p.seenHowTo) { p.seenHowTo = true; save(); setTimeout(() => howToPlay(), 500); }
  },
};

// ---------------------------------------------------------------- settings
const TABS = ['Controls', 'Keys', 'Video', 'Audio', 'Profile'];
export const SettingsScreen = {
  id: 'settings',
  render(params) {
    const tab = params.tab || 0;
    const s = profile().settings, p = profile();
    let body = '';
    if (tab === 0) {
      body = `<div class="opts">
        <div class="group-h">Control style</div>
        ${optRow('scheme0', 'Player 1 control style', '')}
        ${optRow('scheme1', 'Player 2 control style (couch)', '')}
        <div class="sub" style="padding:8px 16px;line-height:1.5">Classic: motion inputs (↓↘→ + attack) for full damage, S-button shortcuts at 85 %.<br>Simple: the same, plus an auto-combo when you keep pressing Light. Specials are always on S + a direction.</div>
        <div class="group-h">Feel</div>
        ${optRow('showInputs', 'Show inputs on screen', '')}
        ${optRow('shake', 'Screen shake', '')}
      </div>`;
    } else if (tab === 1) {
      const b = getBinds();
      body = `<div class="opts" style="max-width:1000px"><div class="bind-row"><div class="lab"></div><div>Keyboard</div><div>Keyboard 2 (couch)</div><div>Keyboard + mouse</div><div>Controller</div></div>
        ${ACTIONS.map((a) => `<div class="bind-row"><div class="lab">${ACTION_LABEL[a]}</div>${['kb', 'kb2', 'kbm', 'pad'].map((d) => `<div class="bk" data-f data-dev="${d}" data-act="${a}">${(b[d][a] || []).map(keyLabel).join(' / ') || '—'}</div>`).join('')}</div>`).join('')}
        <div style="margin-top:10px"><button class="btn small" data-f data-reset>Reset all keys</button> <span class="sub">Select a key box and press the new key or button. Esc cancels.</span></div></div>`;
    } else if (tab === 2) {
      body = `<div class="opts">${optRow('quality', 'Graphics quality', '')}<div class="sub" style="padding:8px 16px">Low is for older laptops; Ultra wants a strong graphics card.</div></div>`;
    } else if (tab === 3) {
      body = `<div class="opts">${optRow('master', 'Master volume', '')}${optRow('sfx', 'Effects', '')}${optRow('music', 'Music', '')}${optRow('announcer', 'Announcer voice', '')}<div class="sub" style="padding:8px 16px">The announcer uses your computer's built-in speech voice.</div></div>`;
    } else {
      body = `<div class="opts">
        <div class="opt" data-f data-name><span class="lab">Name<em>Shown to friends and opponents</em></span><span class="val"><b>${esc(p.name)}</b></span></div>
        ${optRow('title', 'Title', '')}
        ${optRow('inputDelay', 'Online input delay', '', 'title="Frames of delay before rollback. 2 is right for most connections."')}
        <div class="opt" data-f data-export><span class="lab">Move my save to another computer<em>Copies a save code</em></span><span class="val"><b>Export</b></span></div>
        <div class="opt" data-f data-import><span class="lab">Load a save code</span><span class="val"><b>Import</b></span></div>
      </div>`;
    }
    return `<div class="shade-all" style="position:absolute;inset:0"></div><div style="position:relative">
      <h1 class="title-h">SETTINGS</h1>
      <div class="tabs">${TABS.map((t, i) => `<div class="tab ${i === tab ? 'on' : ''}" data-f data-tab="${i}">${t}</div>`).join('')}</div>
      ${body}</div>
      <div class="hint-bar"><span><span class="kbd">LB</span>/<span class="kbd">RB</span> or click: tabs</span><span><span class="kbd">←→</span> change</span><span><span class="kbd">Esc</span>/<span class="kbd">B</span> back</span></div>`;
  },
  mount(el, params) {
    const s = profile().settings, p = profile();
    const setS = (k) => (v) => { s[k] = v; save(); app.applySettings(); };
    el.querySelectorAll('[data-tab]').forEach((t) => t.addEventListener('click', () => { params.tab = +t.dataset.tab; rerender(); }));
    el.addEventListener('tab', (e) => { params.tab = ((params.tab || 0) + e.detail + TABS.length) % TABS.length; rerender(); });
    const sch = (i) => (v) => { s.scheme[i] = v; save(); };
    bindOpt(el, 'scheme0', ['classic', 'simple'], () => s.scheme[0], sch(0), (v) => (v === 'classic' ? 'Classic' : 'Simple'));
    bindOpt(el, 'scheme1', ['classic', 'simple'], () => s.scheme[1], sch(1), (v) => (v === 'classic' ? 'Classic' : 'Simple'));
    bindOpt(el, 'showInputs', [false, true], () => s.showInputs, setS('showInputs'), (v) => (v ? 'On' : 'Off'));
    bindOpt(el, 'shake', [0, 0.5, 1, 1.5], () => s.shake, setS('shake'), (v) => ({ 0: 'Off', 0.5: 'Low', 1: 'Normal', 1.5: 'Extra' })[v]);
    bindOpt(el, 'quality', ['low', 'medium', 'high', 'ultra'], () => s.quality, setS('quality'), (v) => v[0].toUpperCase() + v.slice(1));
    const vol = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];
    const pctf = (v) => `${Math.round(v * 100)} %`;
    for (const k of ['master', 'sfx', 'music']) bindOpt(el, k, vol, () => Math.round(s[k] * 10) / 10, setS(k), pctf);
    bindOpt(el, 'announcer', [true, false], () => s.announcer, setS('announcer'), (v) => (v ? 'On' : 'Off'));
    bindOpt(el, 'title', p.titles, () => p.title, (v) => { p.title = v; save(); });
    bindOpt(el, 'inputDelay', [1, 2, 3, 4], () => s.inputDelay, setS('inputDelay'), (v) => `${v} frame${v > 1 ? 's' : ''}`);
    el.querySelector('[data-name]')?.addEventListener('click', async () => {
      const v = await modal(`<h2>YOUR NAME</h2><input id="nm" maxlength="16" value="${esc(p.name)}">`, [{ label: 'Save', value: 'ok' }, { label: 'Cancel', value: null }], { mount: (m) => setTimeout(() => m.querySelector('#nm').focus(), 50) });
      if (v === 'ok') { const n = document.querySelector('#nm')?.value; }
      const inp = document.getElementById('nm');
      if (v === 'ok' && inp) { p.name = inp.value.replace(/[<>]/g, '').trim().slice(0, 16) || p.name; save(); }
      rerender();
    });
    el.querySelector('[data-export]')?.addEventListener('click', async () => {
      const code = exportSave();
      try { await navigator.clipboard.writeText(code); toast('Save code copied. Paste it into Import on the other computer.'); } catch { await modal(`<h2>SAVE CODE</h2><p>Copy this:</p><textarea style="width:100%;height:120px">${esc(code)}</textarea>`); }
    });
    el.querySelector('[data-import]')?.addEventListener('click', async () => {
      let text = '';
      const v = await modal('<h2>LOAD A SAVE</h2><p>Paste the save code. This replaces the save on this computer.</p><textarea id="sv" style="width:100%;height:120px"></textarea>', [{ label: 'Load', value: 'ok' }, { label: 'Cancel', value: null }], { mount: (m) => m.querySelector('#sv').addEventListener('input', (e) => { text = e.target.value; }) });
      if (v === 'ok') { try { importSave(text); toast('Save loaded.'); location.reload(); } catch (e) { toast('That code didn’t work: ' + esc(e.message)); } }
    });
    // rebinding
    el.querySelectorAll('.bk').forEach((bk) => bk.addEventListener('click', () => listenBind(bk)));
    el.querySelector('[data-reset]')?.addEventListener('click', () => { profile().settings.binds = null; save(); setBinds(null); rerender(); });
  },
};

function listenBind(bk) {
  bk.classList.add('listen'); bk.textContent = 'press…';
  const dev = bk.dataset.dev, act = bk.dataset.act;
  let padTimer = 0;
  const finish = (code) => {
    off(); clearInterval(padTimer);
    if (code && code !== 'Escape') {
      const b = structuredClone(getBinds());
      b[dev][act] = [code];
      profile().settings.binds = b; save(); setBinds(b);
    }
    setTimeout(rerender, 30);
  };
  const off = onRaw((e) => { if (dev !== 'pad') { e.e?.preventDefault?.(); finish(e.code); } else if (e.code === 'Escape') finish(null); });
  if (dev === 'pad') {
    const start = performance.now();
    padTimer = setInterval(() => {
      if (performance.now() - start < 250) return;
      for (const p of navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : []) {
        const i = p.buttons.findIndex((b) => b.pressed);
        if (i >= 0) return finish('b' + i);
        const ax = p.axes.findIndex((a) => Math.abs(a) > 0.7);
        if (ax >= 0) return finish(`a${ax}${p.axes[ax] < 0 ? '-' : '+'}`);
      }
    }, 30);
  }
}

// ---------------------------------------------------------------- how to play
export function howToPlay() {
  const row = (a, b, c, d) => `<tr><td>${a}</td><td>${b}</td><td>${c}</td><td>${d}</td></tr>`;
  return modal(`<h2>HOW TO PLAY</h2>
    <table class="howto"><tr><th></th><th>Keyboard</th><th>Keyboard + mouse</th><th>Controller</th></tr>
    ${row('Move · jump · crouch', 'W A S D', 'W A S D (Space jumps)', 'D-pad / left stick')}
    ${row('Light · Medium · Heavy', 'J · K · L', 'Left click · E · Right click', 'X · Y · RB')}
    ${row('Special', 'I', 'Left Shift', 'A')}
    ${row('Super', 'O', 'R', 'RT')}
    ${row('Throw · Breaker', 'U · P', 'Q · F', 'B · LT')}
    ${row('Pause', 'Esc', 'Esc', 'Start')}</table>
    <div class="howto-tips">
    <p><b>Block</b> by holding away from your opponent. Crouch-block lows, stand-block overheads and jump-ins. Tap away right as a hit lands for a <b>Just Block</b>.</p>
    <p><b>Combos</b>: Light → Medium → Heavy chain together, then cancel into a special. Launchers pop people up for juggles; heavy hits near a wall <b>splat</b> them.</p>
    <p><b>Specials</b>: Special + a direction (→, ←, ↓ or none), or the classic motions (↓↘→ + attack and friends) for full damage. Two attacks or Special + Heavy = <b>EX</b> (½ bar).</p>
    <p><b>Power meter</b> (3 bars): <b>Super</b> = Super Art (1 bar), ↓ + Super = <b>Final Notice</b> (3 bars). <b>Breaker</b> (Medium + Heavy, 1 bar) is an armoured rush, or a reversal while you're blocking.</p>
    <p><b>Overtime</b>: under 25 % health you hit 10 % harder and get one <b>Overtime Art</b> (Super + Special).</p>
    <p>Every fighter's moves are in the pause menu and on the character select (O / Y).</p></div>`, [{ label: 'Got it', value: true }], { cls: 'wide' });
}

// ---------------------------------------------------------------- move list
export function moveListHTML(id, scheme = 'classic') {
  const d = FIGHTERS[id];
  const nm = (mid) => d.moves[mid]?.name || d.moves[mid + '_M']?.name || mid;
  const dirName = { 5: 'S', 6: '→ + S', 4: '← + S', 2: '↓ + S' };
  const motion = { 236: '↓↘→', 214: '↓↙←', 623: '→↓↘', 41236: '←↙↓↘→', 22: '↓↓' };
  const rows = [];
  rows.push('<h4>SPECIALS</h4>');
  for (const s of d.specials || []) rows.push(`<div class="mv"><b>${esc(nm(s.id))}${s.air ? ' (air)' : ''}</b><span>${scheme === 'simple' && s.simple !== undefined ? dirName[s.simple] : (motion[s.motion] || '') + ' + L/M/H'}</span></div>`);
  rows.push('<div class="mv"><b>EX version (½ bar)</b><span>two attacks / S + H</span></div>');
  rows.push('<h4>COMMAND NORMALS</h4>');
  for (const c of d.normals.command || []) rows.push(`<div class="mv"><b>${esc(nm(c.id))}</b><span>${{ 6: '→', 3: '↘', 4: '←', 2: '↓', 1: '↙' }[c.dir] || ''} + ${c.btn}</span></div>`);
  rows.push('<h4>SUPERS</h4>');
  rows.push(`<div class="mv"><b>${esc(nm(d.supers.art))} (1 bar)</b><span>${scheme === 'simple' ? 'Super' : '↓↘→↓↘→ + attack · or Super'}</span></div>`);
  rows.push(`<div class="mv"><b>${esc(nm(d.supers.final))} (3 bars)</b><span>${scheme === 'simple' ? '↓ + Super' : '↓↙←↓↙← + attack · or ↓ + Super'}</span></div>`);
  rows.push(`<div class="mv"><b>${esc(nm(d.supers.overtime))} (Overtime, once)</b><span>Super + S</span></div>`);
  rows.push('<h4>SYSTEM</h4>');
  rows.push('<div class="mv"><b>Throw / back throw</b><span>L + M · ← L + M</span></div>');
  rows.push('<div class="mv"><b>Breaker (1 bar, armoured)</b><span>M + H</span></div>');
  rows.push('<div class="mv"><b>Breaker Reversal (while blocking)</b><span>M + H</span></div>');
  rows.push('<div class="mv"><b>Just Block</b><span>tap ← as it hits</span></div>');
  rows.push('<div class="mv"><b>Dash / back dash</b><span>→→ / ←←</span></div>');
  rows.push('<div class="mv"><b>Chains</b><span>L → M → H, then cancel into a special</span></div>');
  return `<div class="movelist">${rows.join('')}</div>`;
}

export function showMoveList(id, scheme) {
  return modal(`<h2>${esc(FIGHTERS[id].name.toUpperCase())}</h2>${moveListHTML(id, scheme)}`, [{ label: 'Close', value: true }], { cls: 'wide' });
}

// ---------------------------------------------------------------- pause
export function pauseMenu({ canRestart = true, online = false, training = false, onResume, onRestart, onQuit, onMoves, onTraining }) {
  const screen = {
    id: 'pause',
    render: () => `<div class="shade-all" style="position:absolute;inset:0"></div><div class="pause-box panel" style="position:relative">
      <h1 class="title-h" style="font-size:44px">${online ? 'MENU' : 'PAUSED'}</h1>
      ${online ? '<div class="sub">The match keeps going while this is open.</div>' : ''}
      <button class="btn" data-f data-a="resume" data-autofocus>Resume</button>
      ${training ? '<button class="btn" data-f data-a="training">Training options</button>' : ''}
      <button class="btn" data-f data-a="moves">Move list</button>
      ${canRestart && !online ? '<button class="btn" data-f data-a="restart">Restart</button>' : ''}
      <button class="btn red" data-f data-a="quit">${online ? 'Leave match' : 'Quit'}</button></div>`,
    mount: (el) => {
      el.querySelectorAll('[data-a]').forEach((b) => b.addEventListener('click', () => {
        const a = b.dataset.a;
        if (a === 'resume') onResume();
        if (a === 'restart') onRestart();
        if (a === 'quit') onQuit();
        if (a === 'moves') onMoves();
        if (a === 'training') onTraining();
      }));
    },
    back: () => { onResume(); return true; },
  };
  show(screen, {}, { root: true });
}

export { back, hideMenu };
