// The app: one 3D scene, the HUD, the menu showcase, and every game mode's flow (docs/DESIGN.md §8).
import { Session } from './game.js';
import { Bot, LEVELS } from '../shared/bot.js';
import { FIGHTERS, ORDER } from '../shared/fighters/index.js';
import { activeLabels } from '../shared/modifiers.js';
import { profile, save, recordMatch, recordArcade } from './profile.js';
import { audio } from './audio.js';
import { readNav, readDevice, activeDevices, onRaw } from './input.js';
import { show, hideMenu, toast, esc, modal } from './ui/ui.js';

export const app = {
  scene: null, hud: null, showcase: null, session: null, inMatch: false,
  go: (id) => import('./modes.js').then((m) => m.go(id)),
  applySettings() {
    const s = profile().settings;
    audio.setVolumes({ master: s.master, sfx: s.sfx, music: s.music });
    audio.announcer = s.announcer;
    if (this.scene && this.scene.qName !== s.quality) { this.scene.setQuality(s.quality); this.scene.qName = s.quality; }
  },
};

export const HOME = {
  joe: 'basement', gary: 'landing', instructor: 'training', hollow_knight: 'crypt', brannigan: 'landing', caretaker: 'crypt',
  mother_spore: 'hollows', bloatking: 'drowned', vexthorn: 'forest', ignatius: 'forge', aurelia: 'reliquary', tock: 'citadel', landlord: 'abyss',
};

/**
 * Play one match. opts: { setup, players, stage, names, tags, info, vs (show VS splash), training, online, driver,
 *   onPause (custom pause), canRestart }
 * Resolves with the session's result, or null if the player quit.
 */
export async function playMatch(opts) {
  const { scene, hud, showcase } = app;
  const s = profile().settings;
  if (opts.vs !== false) {
    await import('./ui/select.js').then((m) => m.vsScreen({
      fighters: opts.setup.fighters, colors: opts.setup.colors || [0, 1], names: opts.names, tags: opts.tags,
      info: opts.info || '', mods: activeLabels(opts.setup.mods || {}), stage: opts.stage,
    }));
  }
  hideMenu();
  showcase.stop(); showcase.clearFighters();
  const loading = document.getElementById('loading');
  loading.classList.remove('gone'); loading.querySelector('.dim').textContent = 'stepping into the ring…';
  const session = new Session({
    scene, hud, setup: { ...opts.setup, simple: opts.setup.simple || s.scheme.map((x) => x === 'simple') },
    players: opts.players, stage: opts.stage, names: opts.names, driver: opts.driver,
    onEnd: (r) => finish(r),
  });
  let finish;
  const done = new Promise((res) => { finish = res; });
  try { await session.load(); } catch (e) { console.error(e); loading.classList.add('gone'); toast('Could not load the match: ' + esc(e.message)); return null; }
  loading.classList.add('gone');
  app.session = session; app.inMatch = true;
  if (opts.onReady) opts.onReady(session);
  session.start();
  scene.shakeScale = s.shake;
  // pause / menu during the match
  let paused = false;
  const pause = () => {
    if (paused || session.ended) return;
    paused = true;
    if (!opts.online) session.paused = true;
    import('./ui/menus.js').then((m) => m.pauseMenu({
      online: !!opts.online, canRestart: opts.canRestart !== false, training: !!opts.training,
      onResume: () => { paused = false; session.paused = false; hideMenu(); },
      onRestart: () => { paused = false; hideMenu(); session.stop(); finish({ restart: true }); },
      onQuit: () => { paused = false; hideMenu(); session.stop(); finish(null); },
      onMoves: () => m.showMoveList(opts.setup.fighters[opts.localIndex ?? 0], s.scheme[0]),
      onTraining: () => opts.trainingMenu?.(() => { paused = false; session.paused = false; hideMenu(); }),
    }));
  };
  // switching away pauses an offline match (online keeps going)
  const onVis = () => { if (document.hidden && !opts.online && !paused && !session.ended) pause(); };
  document.addEventListener('visibilitychange', onVis);
  const offKey = onRaw((e) => { if (e.type === 'key' && (e.code === 'Escape' || e.code === 'Enter') && !paused && app.inMatch) pause(); });
  let startWas = false;
  const padPoll = setInterval(() => {
    const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
    const st = pads.some((p) => p.buttons[9]?.pressed);
    if (st && !startWas && !paused) pause();
    startWas = st;
  }, 50);
  const result = await done;
  clearInterval(padPoll); offKey(); document.removeEventListener('visibilitychange', onVis);
  session.stop();
  app.inMatch = false; app.session = null;
  hud.show(false);
  showcase.start();
  return result;
}

/** after a match: XP, unlocks, the results screen. Returns the button value chosen. */
export async function afterMatch(result, ctx) {
  const { resultsScreen } = await import('./ui/select.js');
  const li = ctx.localIndex ?? 0;
  const rewards = [];
  if (ctx.record !== false && result && !result.restart) {
    const won = result.winner === li;
    const myStats = result.stats[li];
    const rec = recordMatch({ fighter: result.fighters[li], opponent: result.fighters[1 - li], won, perfect: won && myStats.hp === myStats.maxHp, combo: myStats.best, mode: ctx.mode, friendCode: ctx.friendCode, friendName: ctx.friendName });
    rewards.push({ text: `+${rec.xp} XP` });
    for (const l of rec.levelUps) rewards.push({ text: `LEVEL ${l}!` });
    for (const t of rec.titles) rewards.push({ text: `New title: ${esc(t)}` });
    for (const u of rec.unlocks) rewards.push({ text: `NEW FIGHTER: ${esc(FIGHTERS[u.id].name.toUpperCase())} · ${esc(u.reason)}`, cls: 'unlock' });
  }
  for (const r of ctx.extraRewards || []) rewards.push(r);
  return resultsScreen({
    winnerIdx: result ? result.winner : -1, fighters: result ? result.fighters : ctx.fighters, colors: ctx.colors || [0, 1], names: ctx.names,
    stats: result?.stats, rewards, buttons: ctx.buttons, title: ctx.title,
  });
}

// keep the menu running smoothly: UI ticks every frame when no match is running
export function startUILoop(tickUI) {
  let last = performance.now();
  const loop = (t) => {
    requestAnimationFrame(loop);
    const dt = Math.min(0.1, (t - last) / 1000); last = t;
    if (!app.inMatch || document.querySelector('#menu.on') || document.querySelector('.modal-layer')) tickUI(dt);
  };
  requestAnimationFrame(loop);
}

export { LEVELS, ORDER, readNav, readDevice, activeDevices, show, modal };
