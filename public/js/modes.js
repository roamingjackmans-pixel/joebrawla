// Game modes: Versus Bot, Couch, Training, Arcade Ladder, Survival, Boss Rush (Online lives in ui/online.js).
import { app, playMatch, afterMatch, HOME } from './app.js';
import { Bot, LEVELS } from '../shared/bot.js';
import { FIGHTERS, ORDER } from '../shared/fighters/index.js';
import { STAGES } from './render/stages.js';
import { profile, save, recordArcade, isUnlocked } from './profile.js';
import { show, esc, toast, modal } from './ui/ui.js';
import { characterSelect, difficultySelect, stageSelect } from './ui/select.js';
import { MainMenu, SettingsScreen } from './ui/menus.js';
import { modsScreen } from './ui/mods.js';
import { readDevice, activeDevices } from './input.js';
import { IN } from '../shared/core.js';
import { audio } from './audio.js';

const toMain = () => { audio.music('menu'); show(MainMenu, {}, { root: true }); };
const seed = () => String(Date.now() % 1e9) + Math.random().toString(36).slice(2, 6);

export function go(id) {
  if (id === 'bot') return versusBot();
  if (id === 'couch') return couch();
  if (id === 'training') return training();
  if (id === 'arcade') return arcade();
  if (id === 'survival') return survival();
  if (id === 'bossrush') return bossRush();
  if (id === 'settings') return show(SettingsScreen, { tab: 0 });
  if (id === 'howto') return import('./ui/menus.js').then((m) => m.howToPlay());
  if (id === 'online') return import('./ui/online.js').then((m) => m.onlineHub());
  if (id === 'main') return toMain();
}

// ---------------------------------------------------------------- versus bot
async function versusBot(prev) {
  characterSelect({
    title: 'VERSUS BOT', pickBoth: true, labels: ['YOU', 'BOT'], allowLocked: false,
    onBack: toMain,
    onDone: ({ fighters, colors, schemes }) => {
      difficultySelect({
        def: profile().lastBotLevel ?? 1, onBack: () => versusBot(),
        onDone: (lv) => {
          profile().lastBotLevel = lv; save();
          stageSelect({
            extra: 'Press the Rules button to change modifiers.',
            onBack: () => versusBot(),
            onDone: async (stage) => {
              const mods = await modsScreen({ title: 'RULES', key: 'bot' });
              if (!mods) return versusBot();
              let again = true;
              while (again) {
                const r = await playMatch({
                  setup: { fighters, colors, seed: seed(), mods },
                  players: [{ kind: 'local', device: 'any' }, { kind: 'bot', bot: new Bot(lv, Date.now() & 0xffff) }],
                  stage, tags: ['YOU', `BOT · ${LEVELS[lv].name.toUpperCase()}`], names: [profile().name, FIGHTERS[fighters[1]].name],
                });
                if (r && r.restart) continue;
                if (!r) return toMain();
                const v = await afterMatch(r, { mode: 'bot', colors, names: [profile().name, `${LEVELS[lv].name} bot`], buttons: [{ label: 'Rematch', value: 'again' }, { label: 'Change fighters', value: 'select' }, { label: 'Main menu', value: 'main' }] });
                again = v === 'again';
                if (v === 'select') return versusBot();
                if (v === 'main') return toMain();
              }
            },
          });
        },
      });
    },
  });
}

// ---------------------------------------------------------------- couch
function couch() {
  // claim devices: each player presses an attack on their keyboard half or controller
  const claimed = [null, null];
  const screen = {
    id: 'stage',
    render: () => `<div class="shade-all" style="position:absolute;inset:0"></div><div style="position:relative;text-align:center;margin-top:18vh">
      <h1 class="title-h">COUCH VERSUS</h1><div class="sub" style="margin:10px 0 30px">Each player presses <b>Light</b> on their controller, or <span class="kbd">J</span> (keyboard WASD side) / <span class="kbd">Num1</span> (arrows side).</div>
      <div style="display:flex;gap:4vw;justify-content:center">${[0, 1].map((i) => `<div class="lcard panel" id="cl${i}" style="width:280px"><div class="sub">PLAYER ${i + 1}</div><div class="nm">…</div></div>`).join('')}</div>
      <div class="sub" style="margin-top:24px">Esc to go back</div></div>`,
    tick() {
      for (const dev of activeDevices()) {
        if (claimed.includes(dev)) continue;
        const bits = readDevice(dev);
        if (!(bits & IN.L)) continue;
        const k = claimed[0] ? 1 : 0;
        claimed[k] = dev; audio.ui('big');
        document.querySelector(`#cl${k} .nm`).textContent = { kb: 'Keyboard (WASD)', kb2: 'Keyboard (arrows)', kbm: 'Keyboard + mouse' }[dev] || `Controller ${+dev.slice(3) + 1}`;
        if (k === 1) setTimeout(() => couchSelect(claimed.slice()), 500);
      }
    },
    back: () => { toMain(); return true; },
  };
  show(screen, {}, { root: true });
}

function couchSelect(devices) {
  characterSelect({
    title: 'COUCH VERSUS', players: 2, devices, labels: ['P1', 'P2'],
    onBack: toMain,
    onDone: ({ fighters, colors, schemes }) => stageSelect({
      onBack: () => couchSelect(devices),
      onDone: async (stage) => {
        const mods = await modsScreen({ title: 'RULES', key: 'couch' });
        if (!mods) return couchSelect(devices);
        let wins = [0, 0];
        for (;;) {
          const r = await playMatch({
            setup: { fighters, colors, seed: seed(), mods, simple: schemes.map((x) => x === 'simple') },
            players: [{ kind: 'local', device: devices[0] }, { kind: 'local', device: devices[1] }],
            stage, tags: ['P1', 'P2'], names: ['Player 1', 'Player 2'],
          });
          if (r && r.restart) continue;
          if (!r) return toMain();
          if (r.winner >= 0) wins[r.winner]++;
          const v = await afterMatch(r, { mode: 'couch', record: false, colors, names: ['Player 1', 'Player 2'], title: `SET ${wins[0]} – ${wins[1]}`, buttons: [{ label: 'Rematch', value: 'again' }, { label: 'Change fighters', value: 'select' }, { label: 'Main menu', value: 'main' }] });
          if (v === 'select') return couchSelect(devices);
          if (v === 'main') return toMain();
        }
      },
    }),
  });
}

// ---------------------------------------------------------------- training
function training() {
  characterSelect({
    title: 'TRAINING', pickBoth: true, labels: ['YOU', 'DUMMY'], allowLocked: true,
    onBack: toMain,
    onDone: async ({ fighters, colors }) => {
      const { startTraining } = await import('./training.js');
      for (;;) {
        const r = await startTraining({ fighters, colors });
        if (!r || !r.restart) break;
      }
      toMain();
    },
  });
}

// ---------------------------------------------------------------- arcade ladder
const RIVAL = { joe: 'instructor', gary: 'joe', instructor: 'joe', hollow_knight: 'caretaker', brannigan: 'ignatius', caretaker: 'hollow_knight', mother_spore: 'vexthorn', bloatking: 'aurelia', vexthorn: 'mother_spore', ignatius: 'brannigan', aurelia: 'bloatking', tock: 'gary', landlord: 'joe' };
const FLOOR_TEXT = {
  crypt: 'B1 · The Mossy Crypt. Morning sun on a graveyard that shouldn’t be down here. Eviction notices nailed to every tree.',
  hollows: 'B2 · The Fungal Hollows. A cave open to a leased sky. Everything glows. Everything grows back.',
  drowned: 'B3 · The Drowned Quarter. The court is in session. The court is underwater.',
  forest: 'B4 · The Hollow Forest. NOTICE TO QUIT: this forest is 312 years behind on rent.',
  forge: 'B5 · The Ashen Forge. Locks, keys and chains for Management. Shift’s not over.',
  reliquary: 'B6 · The Frozen Reliquary. Still waiting for the heating repairman.',
  citadel: 'B7 · The Clockwork Citadel. Every lease and late fee is filed here. You are late.',
  abyss: 'B8 · The Abyss. A desk on a rock in the void. Behind it, a grey panel marked MAIN.',
  landing: 'The Landing. Tenants who stopped going down made a home here. Somebody wants a word.',
  basement: 'Building Nine Basement, 11:52 p.m. The breaker box is right there. So is somebody else.',
  training: 'The Training Hall. Management’s orientation. Nobody passes.',
};
const ENDING = {
  joe: 'Joe flips the main breaker, pulls the cord on the backup generator, and climbs forty flights. In 3C the microwave blinks 12:00. An envelope slides under the door: your lease has been automatically renewed.',
  gary: 'Gary sells the Landlord’s desk back to the Landlord at a reasonable markup. He moves into the Abyss. It’s a suite.',
  instructor: 'The Instructor grades the Landlord. F. He finally has someone to train who might pass.',
  hollow_knight: 'The Hollow Knight finds the door he was guarding. It opens onto the stairs. He goes up, for the first time in years.',
  brannigan: 'Brannigan fixes the boiler. The whole building is warm for a week. Rent goes up.',
  caretaker: 'The Caretaker plants the Landlord’s lease in the garden. By spring it has grown into a very good suit.',
  mother_spore: 'Mother Spore takes back the sky. The Hollows bloom so bright the lights in Building Nine stay on all night.',
  bloatking: 'The Bloatking floods the Abyss and calls it a moat. The court is very much in session.',
  vexthorn: 'Vexthorn sets his lantern-heart in the empty office. The forest has a light again.',
  ignatius: 'Ignatius melts every key the Landlord ever ordered. Shift’s over. For once.',
  aurelia: 'Saint Aurelia finds the thermostat. She turns it up two degrees. She weeps.',
  tock: 'Tock files the Landlord under L for Late. Everyone is always late. Even him.',
  landlord: 'The Landlord renews his own lease. Nothing changes. That’s the point.',
};

function arcade() {
  characterSelect({
    title: 'ARCADE LADDER', labels: ['YOU'], onBack: toMain,
    onDone: ({ fighters, colors }) => difficultySelect({
      title: 'LADDER DIFFICULTY', def: profile().lastBotLevel ?? 1, onBack: arcade,
      onDone: async (lv) => {
        const me = fighters[0];
        const pool = ORDER.filter((x) => x !== me && x !== 'landlord' && x !== RIVAL[me]);
        for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]]; }
        const ladder = [...pool.slice(0, 6), RIVAL[me] === 'landlord' ? pool[6] : RIVAL[me], 'landlord'];
        for (let k = 0; k < ladder.length; k++) {
          const opp = ladder[k];
          const boss = k === ladder.length - 1;
          const stage = boss ? 'abyss' : HOME[opp] || 'crypt';
          await storyCard(ladder, k, FLOOR_TEXT[stage] || '', boss ? 'THE LANDLORD' : k === 6 ? 'RIVAL' : `FLOOR ${k + 1}`);
          const level = boss ? lv : Math.max(0, Math.min(3, lv - 1 + Math.floor(k / 3)));
          let cleared = false;
          for (;;) {
            const r = await playMatch({
              setup: { fighters: [me, opp], colors: [colors[0], 0], seed: seed(), mods: { rounds: boss ? 2 : 2 }, boss: [false, boss] },
              players: [{ kind: 'local', device: 'any' }, { kind: 'bot', bot: new Bot(level, k * 31 + 7) }],
              stage, tags: ['YOU', boss ? 'FINAL BOSS' : `FLOOR ${k + 1}`], names: [profile().name, FIGHTERS[opp].name],
            });
            if (r && r.restart) continue;
            if (!r) return toMain();
            if (r.winner === 0) { cleared = true; await afterMatch(r, { mode: 'arcade', colors: [colors[0], 0], names: [profile().name, FIGHTERS[opp].name], buttons: [{ label: k === ladder.length - 1 ? 'Finish' : 'Next floor', value: 'next' }] }); break; }
            const v = await afterMatch(r, { mode: 'arcade', colors: [colors[0], 0], names: [profile().name, FIGHTERS[opp].name], buttons: [{ label: 'Continue', value: 'retry' }, { label: 'Give up', value: 'quit' }] });
            if (v === 'quit') return toMain();
          }
          if (!cleared) return toMain();
        }
        const rec = recordArcade(me, lv);
        await modal(`<h2>THE MAIN BREAKER</h2><p>${esc(ENDING[me] || ENDING.joe)}</p>${rec.unlocks.map((u) => `<p class="gold"><b>NEW FIGHTER: ${esc(FIGHTERS[u.id].name)}</b> · ${esc(u.reason)}</p>`).join('')}`, [{ label: 'The End', value: true }]);
        toMain();
      },
    }),
  });
}

function storyCard(ladder, k, text, label) {
  return new Promise((resolve) => {
    app.showcase.setMode('vs');
    app.showcase.setFighter(1, ladder[k], 0, 'intro');
    const screen = {
      id: 'stage',
      render: () => `<div class="shade-l" style="position:absolute;inset:0"></div><div style="position:relative">
        <h1 class="title-h">${esc(label)}<small>${esc(FIGHTERS[ladder[k]].name)}</small></h1>
        <div class="ladder">${ladder.map((id, i) => `<div class="rung ${i < k ? 'done' : ''} ${i === k ? 'now' : ''} ${i === ladder.length - 1 ? 'boss' : ''}"><b>${i === ladder.length - 1 ? 'B8' : i + 1}</b>${esc(FIGHTERS[id].name.replace('The ', ''))}</div>`).join('')}</div>
        <div class="story">${esc(text)}</div>
        <div style="margin-top:24px"><button class="btn big" data-f data-autofocus data-go>Fight</button></div></div>`,
      mount: (el) => el.querySelector('[data-go]').addEventListener('click', resolve),
      back: () => true,
    };
    show(screen, {}, { root: true });
  });
}

// ---------------------------------------------------------------- survival
function survival() {
  characterSelect({
    title: 'SURVIVAL', labels: ['YOU'], onBack: toMain,
    onDone: async ({ fighters, colors }) => {
      const me = fighters[0];
      let wins = 0, hp = null;
      const p = profile();
      for (;;) {
        const pool = ORDER.filter((x) => x !== me && x !== 'landlord');
        const opp = pool[Math.floor(Math.random() * pool.length)];
        const level = Math.min(3, Math.floor(wins / 3));
        const r = await playMatch({
          setup: { fighters: [me, opp], colors: [colors[0], 0], seed: seed(), mods: { rounds: 1 }, hpStart: [hp, null] },
          players: [{ kind: 'local', device: 'any' }, { kind: 'bot', bot: new Bot(level, wins * 13 + 1) }],
          stage: HOME[opp] || 'crypt', tags: [`STREAK ${wins}`, LEVELS[level].name.toUpperCase()], names: [p.name, FIGHTERS[opp].name], vs: wins === 0, canRestart: false,
        });
        if (!r || r.winner !== 0) {
          const best = wins > p.records.survival;
          if (best) { p.records.survival = wins; p.records.survivalFighter = me; save(); }
          if (r) await afterMatch(r, { mode: 'survival', colors: [colors[0], 0], title: `SURVIVAL · ${wins} WIN${wins === 1 ? '' : 'S'}`, extraRewards: best ? [{ text: `NEW BEST: ${wins}`, cls: 'unlock' }] : [{ text: `Best: ${p.records.survival}` }], buttons: [{ label: 'Main menu', value: 'main' }] });
          return toMain();
        }
        wins++;
        const st = r.stats[0];
        hp = Math.min(st.maxHp, st.hp + Math.round(st.maxHp * 0.15));
        toast(`${wins} down. Health restored a little.`);
      }
    },
  });
}

// ---------------------------------------------------------------- boss rush
const BOSSES = ['caretaker', 'mother_spore', 'bloatking', 'vexthorn', 'ignatius', 'aurelia', 'tock', 'landlord'];
function bossRush() {
  characterSelect({
    title: 'BOSS RUSH', labels: ['YOU'], onBack: toMain,
    onDone: ({ fighters, colors }) => difficultySelect({
      title: 'BOSS RUSH DIFFICULTY', def: 2, onBack: bossRush,
      onDone: async (lv) => {
        const me = fighters[0]; const p = profile();
        let frames = 0;
        for (let k = 0; k < BOSSES.length; k++) {
          const opp = BOSSES[k];
          const r = await playMatch({
            setup: { fighters: [me, opp === me ? 'joe' : opp], colors: [colors[0], 0], seed: seed(), mods: { rounds: 1 }, boss: [false, true] },
            players: [{ kind: 'local', device: 'any' }, { kind: 'bot', bot: new Bot(lv, k * 17 + 3) }],
            stage: HOME[opp], tags: ['YOU', `BOSS ${k + 1} OF 8`], names: [p.name, FIGHTERS[opp].name], canRestart: false,
          });
          if (!r || r.winner !== 0) {
            if (r) await afterMatch(r, { mode: 'bossrush', colors: [colors[0], 0], title: `BOSS RUSH · ${k} OF 8`, buttons: [{ label: 'Main menu', value: 'main' }] });
            return toMain();
          }
          frames += r.frames || 0;
        }
        const secs = Math.round(frames / 60);
        const best = !p.records.bossRush || secs < p.records.bossRush;
        if (best) { p.records.bossRush = secs; p.records.bossRushFighter = me; save(); }
        if (lv >= 2 && !p.unlocked.includes('landlord')) { p.unlocked.push('landlord'); save(); }
        await modal(`<h2>BOSS RUSH CLEARED</h2><p>All eight rulers, in ${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}.${best ? ' <b class="gold">New best!</b>' : ''}</p>`);
        toMain();
      },
    }),
  });
}
