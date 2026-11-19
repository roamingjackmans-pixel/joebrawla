// Training mode: a dummy you can configure (stand, crouch, jump, block, CPU, record & playback), hitbox view,
// frame data, input display, meter and health refills, position resets. docs/DESIGN.md §8.
import { app, playMatch } from './app.js';
import { Bot } from '../shared/bot.js';
import { IN, CM, WALL, START_X } from '../shared/core.js';
import { FIGHTERS } from '../shared/fighters/index.js';
import { hurtboxes, worldBox, moveOf, dataOf } from '../shared/sim.js';
import { show, esc, optRow, bindOpt, hideMenu } from './ui/ui.js';
import { readDevice, onRaw } from './input.js';
import * as THREE from '../vendor/three.bundle.js';

const T = {
  action: 'stand', block: 'none', cpu: 1, meter: 'refill', hp: true, boxes: false, frames: true, inputs: true, reset: 'center',
};
const OPTS = [
  ['action', 'Dummy action', ['stand', 'crouch', 'jump', 'cpu', 'playback'], { stand: 'Stand', crouch: 'Crouch', jump: 'Jump', cpu: 'CPU fights back', playback: 'Play back recording' }],
  ['block', 'Dummy blocks', ['none', 'all', 'after', 'random'], { none: 'Never', all: 'Everything', after: 'After the first hit', random: 'Randomly' }],
  ['cpu', 'CPU level', [0, 1, 2, 3], { 0: 'Tenant', 1: 'Superintendent', 2: 'Management', 3: 'The Landlord' }],
  ['meter', 'Power meter', ['refill', 'infinite', 'normal'], { refill: 'Refill after combos', infinite: 'Infinite', normal: 'Normal' }],
  ['hp', 'Refill health', [true, false], { true: 'On', false: 'Off' }],
  ['boxes', 'Show hitboxes', [false, true], { true: 'On', false: 'Off' }],
  ['frames', 'Show frame data', [true, false], { true: 'On', false: 'Off' }],
  ['inputs', 'Show inputs', [true, false], { true: 'On', false: 'Off' }],
  ['reset', 'Reset position (Taunt / Backspace)', ['center', 'left', 'right'], { center: 'Middle', left: 'Left corner', right: 'Right corner' }],
];

export async function startTraining({ fighters, colors }) {
  let session = null;
  const rec = { on: false, frames: [], face: 1, play: 0 };
  let blockTimer = 0, lastDummyHit = 0;
  const bot = new Bot(T.cpu, 99);
  const overlay = makeOverlay();
  const fd = { start: -1, p1Free: -1, p2Free: -1, text: '', move: '' };
  const hist = [];
  let resetPrev = false;

  const dummy = (match, i) => {
    const st = match.state, me = st.f[1], op = st.f[0];
    // record/playback
    if (T.action === 'playback' && rec.frames.length) {
      let b = rec.frames[rec.play % rec.frames.length]; rec.play++;
      if (me.face !== rec.face) { const l = b & IN.LEFT, r = b & IN.RIGHT; b = (b & ~(IN.LEFT | IN.RIGHT)) | (l ? IN.RIGHT : 0) | (r ? IN.LEFT : 0); }
      return b;
    }
    if (T.action === 'cpu') { bot.p = bot.p; return bot.think(match, 1); }
    let bits = 0;
    if (T.action === 'crouch') bits |= IN.DOWN;
    if (T.action === 'jump') bits |= IN.UP;
    // blocking
    const back = op.x < me.x ? IN.RIGHT : IN.LEFT;
    if (me.act === 'hit' || me.act === 'chit' || me.act === 'air') lastDummyHit = st.frame;
    let wantBlock = T.block === 'all' || (T.block === 'after' && st.frame - lastDummyHit < 90) || (T.block === 'random' && ((st.frame >> 5) & 1));
    if (wantBlock) {
      const mv = moveOf(match.cfg, op);
      const low = mv && mv.hits.some((h) => h.level === 'low');
      const ovh = mv && mv.hits.some((h) => h.level === 'ovh');
      bits = back | (low ? IN.DOWN : 0) | (T.action === 'crouch' && !ovh ? IN.DOWN : 0);
      if (ovh) bits &= ~IN.DOWN;
    }
    return bits;
  };

  const onStep = (match) => {
    const st = match.state, cfg = match.cfg;
    const [a, b] = st.f;
    // refills when nothing is happening
    const quiet = a.act !== 'move' && b.act !== 'hit' && b.act !== 'chit' && b.act !== 'air' && b.act !== 'down' && b.combo === 0;
    if (quiet) {
      if (T.hp) { a.hp = a.maxHp; b.hp = b.maxHp; }
      if (T.meter === 'refill') { a.meter = 3000; b.meter = 3000; }
    }
    if (T.meter === 'infinite') { a.meter = 3000; b.meter = 3000; }
    // frame data for P1's last move
    const mv = moveOf(cfg, a);
    if (a.act === 'move' && a.mf === 1) { fd.start = st.frame; fd.move = mv?.name || a.move; fd.data = mv; fd.p1Free = -1; fd.p2Free = -1; }
    const free = (f) => ['idle', 'walk', 'crouch', 'jump', 'dashEnd'].includes(f.act) || (f.act === 'land' && f.t >= f.stun);
    if (fd.start >= 0) {
      if (fd.p1Free < 0 && free(a)) fd.p1Free = st.frame;
      if (fd.p2Free < 0 && free(b)) fd.p2Free = st.frame;
      if (fd.p1Free >= 0 && fd.p2Free >= 0) {
        const adv = fd.p2Free - fd.p1Free;
        const d = fd.data;
        fd.text = `<div>${esc(fd.move)}${d ? ` · startup ${d.startup} · active ${d.active} · recovery ${d.recovery}` : ''}</div><div class="adv ${adv >= 0 ? 'pos' : 'neg'}">${adv >= 0 ? '+' : ''}${adv}</div>`;
        fd.start = -1;
      }
    }
    // inputs history
    const bits = readDevice('any');
    if (bits !== (hist[0]?.b ?? -1)) { hist.unshift({ b: bits, n: 1 }); if (hist.length > 14) hist.pop(); } else hist[0].n++;
    // record
    if (rec.on) { rec.frames.push(bits); if (rec.frames.length >= 600) { rec.on = false; app.hud.call('<b>RECORDED</b>', 'blue', 900); } }
    // reset with taunt
    const resetNow = !!(bits & IN.TAUNT);
    if (resetNow && !resetPrev) resetPositions(match);
    resetPrev = resetNow;
  };

  const keys = onRaw((e) => {
    if (e.type !== 'key' || !session) return;
    if (e.code === 'F9') { rec.on = !rec.on; if (rec.on) { rec.frames = []; rec.face = session.match.state.f[0].face; app.hud.call('<b>RECORDING</b>', 'ko', 900); } }
    if (e.code === 'F10') { T.action = T.action === 'playback' ? 'stand' : 'playback'; rec.play = 0; app.hud.call(`<b>${T.action === 'playback' ? 'PLAYBACK' : 'STAND'}</b>`, 'blue', 700); }
  });

  let rafId = 0;
  const draw = () => {
    rafId = requestAnimationFrame(draw);
    if (!session) return;
    overlay.update(session, T, fd, hist);
  };

  const result = await playMatch({
    setup: { fighters, colors, seed: 'training', mods: { timer: 0, rounds: 5 }, skipIntro: true, training: true },
    players: [{ kind: 'local', device: 'any' }, { kind: 'dummy', dummy }],
    stage: 'training', vs: false, training: true,
    trainingMenu: (resume) => trainingMenu(resume),
    onReady: (s) => { session = s; s.o.onStep = onStep; rafId = requestAnimationFrame(draw); app.hud.call('<b>TRAINING</b><small>Esc: menu · Backspace / View: reset · F9 record · F10 playback</small>', 'blue', 2600); },
  });
  cancelAnimationFrame(rafId); keys(); overlay.remove();
  return result;

  function resetPositions(match) {
    const st = match.state;
    const pos = T.reset === 'left' ? [-WALL + 120 * CM, -WALL + 40 * CM] : T.reset === 'right' ? [WALL - 120 * CM, WALL - 40 * CM] : [-START_X, START_X];
    if (T.reset === 'right') pos.reverse();
    st.f.forEach((f, i) => { Object.assign(f, { x: pos[i], y: 0, vx: 0, vy: 0, slide: 0, act: 'idle', t: 0, move: null, mf: 0, stun: 0, hs: 0, combo: 0, comboDmg: 0, hp: f.maxHp, face: pos[i] < pos[1 - i] ? 1 : -1 }); });
    st.proj = [];
    session.prev = structuredClone(st);
    rec.play = 0;
  }
}

function trainingMenu(resume) {
  const screen = {
    id: 'mods',
    render: () => `<div class="shade-all" style="position:absolute;inset:0"></div><div style="position:relative"><h1 class="title-h">TRAINING<small>F9 records 10 s of your inputs · F10 plays them back on the dummy</small></h1>
      <div class="opts">${OPTS.map(([k, label]) => optRow(k, label, '')).join('')}</div>
      <div style="margin-top:14px"><button class="btn big" data-f data-ok>Back to training</button></div></div>`,
    mount(el) {
      for (const [k, , vals, names] of OPTS) bindOpt(el, k, vals, () => T[k], (v) => { T[k] = v; }, (v) => names[v] ?? String(v));
      el.querySelector('[data-ok]').addEventListener('click', () => { hideMenu(); resume(); });
    },
    back: () => { hideMenu(); resume(); return true; },
  };
  show(screen, {}, { root: true });
}

// ---------------------------------------------------------------- the overlay (boxes, frame data, inputs)
function makeOverlay() {
  const c = document.createElement('canvas'); c.id = 'boxes'; document.body.appendChild(c);
  const fdEl = document.createElement('div'); fdEl.className = 'framedata'; document.body.appendChild(fdEl);
  const inEl = document.createElement('div'); inEl.className = 'inputs s0'; inEl.style.cssText = 'position:fixed;left:1vw;top:30vh;z-index:7'; document.body.appendChild(inEl);
  const g = c.getContext('2d');
  const v = new THREE.Vector3();
  const ARROW = { 1: '↙', 2: '↓', 3: '↘', 4: '←', 5: '·', 6: '→', 7: '↖', 8: '↑', 9: '↗' };
  return {
    remove() { c.remove(); fdEl.remove(); inEl.remove(); },
    update(session, T, fd, hist) {
      const sc = app.scene;
      c.width = innerWidth; c.height = innerHeight;
      g.clearRect(0, 0, c.width, c.height);
      fdEl.style.display = T.frames ? '' : 'none'; fdEl.innerHTML = fd.text || '';
      inEl.style.display = T.inputs ? '' : 'none';
      inEl.innerHTML = hist.map((h) => {
        const d = (h.b & IN.UP ? 8 : h.b & IN.DOWN ? 2 : 5) + (h.b & IN.RIGHT ? 1 : h.b & IN.LEFT ? -1 : 0);
        const btns = ['L', 'M', 'H', 'S', 'SUPER'].filter((k) => h.b & IN[k]).join(' ');
        return `<div>${ARROW[d]} <b style="color:#ffd34a">${btns}</b> <span style="color:#888">${Math.min(99, h.n)}</span></div>`;
      }).join('');
      if (!T.boxes) return;
      const { cfg, state } = session.match;
      const proj = (x, y) => { v.set(x / 10000, y / 10000, 0).project(sc.camera); return [(v.x + 1) / 2 * c.width, (1 - v.y) / 2 * c.height]; };
      const rect = (b, fill, stroke) => {
        const [x0, y0] = proj(b[0], b[3]), [x1, y1] = proj(b[2], b[1]);
        g.fillStyle = fill; g.strokeStyle = stroke; g.lineWidth = 1.5;
        g.fillRect(x0, y0, x1 - x0, y1 - y0); g.strokeRect(x0, y0, x1 - x0, y1 - y0);
      };
      for (const f of state.f) {
        for (const b of hurtboxes(cfg, f)) rect(b, 'rgba(60,160,255,0.18)', 'rgba(90,180,255,0.9)');
        const mv = moveOf(cfg, f);
        if (mv) for (const h of mv.hits) if (h.box && f.mf >= h.frames[0] && f.mf <= h.frames[1]) rect(worldBox(f.x, f.y, f.face, h.box), 'rgba(255,40,40,0.3)', 'rgba(255,80,80,1)');
        const d = dataOf(cfg, f);
        rect([f.x - d.width / 2, f.y, f.x + d.width / 2, f.y + 20 * CM], 'rgba(255,220,0,0.1)', 'rgba(255,220,0,0.6)');
      }
      for (const p of state.proj) if (p.box) rect(worldBox(p.x, p.y, p.face, p.box), 'rgba(255,140,0,0.3)', 'rgba(255,160,0,1)');
    },
  };
}
