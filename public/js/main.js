// JoeBrawla boot. (Menus come next; ?quick starts a test match.)
import { FightScene } from './render/scene.js';
import { HUD } from './hud.js';
import { Session } from './game.js';
import { initInput } from './input.js';
import { audio } from './audio.js';
import { Bot } from '../shared/bot.js';

initInput();
const canvas = document.getElementById('c');
const scene = new FightScene(canvas, 'high');
const hud = new HUD(document.getElementById('hud'));
window.addEventListener('pointerdown', () => audio.unlock(), { once: true });
window.addEventListener('keydown', () => audio.unlock(), { once: true });

const q = new URLSearchParams(location.search);
async function quick() {
  const s = new Session({
    scene, hud,
    setup: { fighters: [q.get('p1') || 'joe', q.get('p2') || 'joe'], seed: 'quick', skipIntro: q.has('skip'), mods: {} },
    players: [0, 1].map((i) => q.has('bot' + (i + 1)) ? { kind: 'bot', bot: new Bot(+q.get('bot' + (i + 1)), i + 7) } : i === 0 ? { kind: 'local', device: 'any' } : { kind: 'dummy', dummy: () => 0 }),
    stage: q.get('stage') || 'crypt',
    onEnd: (r) => console.log('end', r),
  });
  await s.load();
  document.getElementById('loading').classList.add('gone');
  s.start();
  window.session = s;
  if (q.has('dev')) (await import('./dev.js')).installDev(s);
}
quick();
