// JoeBrawla boot: load the essentials, put up the title screen over a live 3D stage, wire friends and invites.
// Dev shortcuts: ?quick (straight into a match; &p1=id&p2=id&stage=id&bot1=0-3&bot2=0-3&skip&dev).
import { FightScene } from './render/scene.js';
import { HUD } from './hud.js';
import { Session } from './game.js';
import { initInput, setBinds } from './input.js';
import { audio } from './audio.js';
import { Bot } from '../shared/bot.js';
import { app, startUILoop } from './app.js';
import { Showcase } from './showcase.js';
import { profile, save } from './profile.js';
import { show, tickUI, toast } from './ui/ui.js';
import { TitleScreen } from './ui/menus.js';
import { loadClips } from './render/fighterView.js';
import { initFriends, claimCode, myFriendCode } from './net/friends.js';
import { initOnline, autoJoinFromURL } from './ui/online.js';
import { ORDER } from '../shared/fighters/index.js';

const q = new URLSearchParams(location.search);
const bar = document.querySelector('#loading .bar i');
const setBar = (k) => { if (bar) bar.style.width = `${Math.round(k * 100)}%`; };

initInput();
const p = profile();
setBinds(p.settings.binds);
const canvas = document.getElementById('c');
app.scene = new FightScene(canvas, p.settings.quality);
app.scene.qName = p.settings.quality;
app.hud = new HUD(document.getElementById('hud'));
app.showcase = new Showcase(app.scene);
app.applySettings();
window.addEventListener('pointerdown', () => audio.unlock(), { once: true });
window.addEventListener('keydown', () => audio.unlock(), { once: true });
window.app = app;

async function boot() {
  setBar(0.1);
  if (q.has('quick')) return quick();
  try {
    await loadClips();
    setBar(0.45);
    await app.showcase.setStage('crypt');
    setBar(0.7);
    const pool = ORDER.filter((id) => p.unlocked.includes(id));
    const a = pool[Math.floor(Math.random() * pool.length)];
    let b = pool[Math.floor(Math.random() * pool.length)]; if (b === a) b = pool[(pool.indexOf(a) + 1) % pool.length];
    await Promise.all([app.showcase.setFighter(0, a, 0, 'idle'), app.showcase.setFighter(1, b, 1, 'idle')]);
  } catch (e) { console.error(e); }
  setBar(1);
  app.showcase.start();
  document.getElementById('loading').classList.add('gone');
  startUILoop(tickUI);
  initOnline();
  try { initFriends(); } catch (e) { console.warn(e); }
  myFriendCode(); // every player gets their 4-digit code on the first visit
  if (!p.codeClaimed) claimCode().catch(() => {});
  if (!autoJoinFromURL()) show(TitleScreen, {}, { root: true });
}

async function quick() {
  const s = new Session({
    scene: app.scene, hud: app.hud,
    setup: { fighters: [q.get('p1') || 'joe', q.get('p2') || 'joe'], seed: 'quick', skipIntro: q.has('skip'), mods: Object.fromEntries((q.get('mods') || '').split(',').filter(Boolean).map((kv) => { const [k, v] = kv.split(':'); return [k, v === 'true' ? true : v === 'false' ? false : isNaN(+v) ? v : +v]; })) },
    players: [0, 1].map((i) => q.has('bot' + (i + 1)) ? { kind: 'bot', bot: new Bot(+q.get('bot' + (i + 1)), i + 7) } : i === 0 ? { kind: 'local', device: 'any' } : { kind: 'dummy', dummy: () => 0 }),
    stage: q.get('stage') || 'crypt',
    onEnd: (r) => console.log('end', r),
  });
  await s.load();
  document.getElementById('loading').classList.add('gone');
  s.start();
  app.session = s; app.inMatch = true;
  window.session = s;
  if (q.has('dev')) (await import('./dev.js')).installDev(s);
}

boot();
window.addEventListener('error', (e) => { if (String(e.message || '').includes('ResizeObserver')) return; console.error(e.error || e.message); });
