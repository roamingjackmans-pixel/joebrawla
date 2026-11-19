// The player's save (browser localStorage): name, friend code, settings, XP and level, unlocked fighters and
// colours, stats, records and rivalries. docs/DESIGN.md §12.
import { STARTERS, UNLOCK_ORDER, FIGHTERS } from '../shared/fighters/index.js';

const KEY = 'joebrawla-v1' + (new URLSearchParams(location.search).get('slot') ? '-' + new URLSearchParams(location.search).get('slot') : '');
let data = null;

const NAMES = ['Joe', 'Tenant', 'Apt 3C', 'Downstairs Joe', 'Night Shift', 'The New Guy', 'Late Rent', 'Breaker Box'];

function fresh() {
  return {
    v: 1, name: NAMES[Math.floor(Math.random() * NAMES.length)] + ' ' + (100 + Math.floor(Math.random() * 900)),
    friendCode: '', codeClaimed: false, created: Date.now(),
    settings: { quality: 'high', master: 0.8, sfx: 0.9, music: 0.45, announcer: true, scheme: ['classic', 'classic'], binds: null, inputDelay: 2, showInputs: false, shake: 1 },
    xp: 0, level: 1, unlocked: [...STARTERS], seenUnlocks: [], colors: {}, mastery: {},
    stats: { matches: 0, wins: 0, losses: 0, perFighter: {}, longestCombo: 0, perfects: 0 },
    records: { survival: 0, survivalFighter: '', bossRush: 0, bossRushFighter: '' },
    arcade: {}, // fighter -> highest level cleared (0..3)
    rivals: {}, recent: [], titles: ['Tenant'], title: 'Tenant',
    friends: [], requests: [], ignored: [], mailOut: [], mailGone: [],
    lastMods: {}, lastFighter: 'joe', lastStage: 'crypt', lastColor: {},
  };
}

export function profile() {
  if (data) return data;
  try { data = JSON.parse(localStorage.getItem(KEY)); } catch { data = null; }
  const f = fresh();
  if (!data || data.v !== 1) data = f;
  for (const k of Object.keys(f)) if (data[k] === undefined) data[k] = f[k];
  data.settings = { ...f.settings, ...data.settings };
  data.stats = { ...f.stats, ...data.stats };
  data.records = { ...f.records, ...data.records };
  return data;
}
export function save() { try { localStorage.setItem(KEY, JSON.stringify(profile())); } catch { /* private mode */ } }

// ---------------------------------------------------------------- levels and unlocks
export const xpForLevel = (lv) => 200 + (lv - 1) * 120;

export function isUnlocked(id) { return profile().unlocked.includes(id); }

/** the next fighter to unlock and how */
export function nextUnlock() {
  const p = profile();
  const next = UNLOCK_ORDER.find((id) => !p.unlocked.includes(id));
  return next || (!p.unlocked.includes('landlord') ? 'landlord' : null);
}
export function unlockHint(id) {
  if (id === 'landlord') return 'Clear the Arcade Ladder on The Landlord difficulty.';
  const p = profile();
  const idx = UNLOCK_ORDER.indexOf(id);
  const ahead = UNLOCK_ORDER.slice(0, idx).filter((x) => !p.unlocked.includes(x)).length;
  return ahead === 0 ? 'Next unlock: clear the Arcade Ladder once, or gain 2 levels.' : `Unlocks after ${ahead} more fighter${ahead > 1 ? 's' : ''}.`;
}

function unlockNext(reason) {
  const p = profile();
  const id = UNLOCK_ORDER.find((x) => !p.unlocked.includes(x));
  if (!id) return null;
  p.unlocked.push(id);
  return { id, reason };
}

/**
 * Record a finished match. r: { fighter, opponent, won, perfect, combo, mode, friendCode?, friendName?, level? }
 * Returns { xp, levelUps: [n], unlocks: [{id, reason}], titles: [] }
 */
export function recordMatch(r) {
  const p = profile();
  const out = { xp: 0, levelUps: [], unlocks: [], titles: [] };
  let xp = r.won ? 100 : 60;
  if (r.perfect) xp += 40;
  if (r.mode === 'online') xp += 40;
  const today = new Date().toDateString();
  if (r.won && p.lastWinDay !== today) { xp += 100; p.lastWinDay = today; }
  out.xp = xp;
  p.xp += xp;
  while (p.xp >= xpForLevel(p.level)) {
    p.xp -= xpForLevel(p.level); p.level++; out.levelUps.push(p.level);
    if (p.level % 2 === 1) { const u = unlockNext(`Reached level ${p.level}`); if (u) out.unlocks.push(u); }
  }
  p.stats.matches++;
  if (r.won) p.stats.wins++; else p.stats.losses++;
  if (r.perfect) p.stats.perfects++;
  p.stats.longestCombo = Math.max(p.stats.longestCombo, r.combo || 0);
  const pf = (p.stats.perFighter[r.fighter] ||= { w: 0, l: 0 });
  if (r.won) pf.w++; else pf.l++;
  // mastery unlocks colours: 1 per 3 wins with a fighter
  const m = (p.mastery[r.fighter] = (p.mastery[r.fighter] || 0) + (r.won ? 1 : 0));
  const colorsOpen = Math.min(8, 2 + Math.floor(m / 3));
  p.colors[r.fighter] = colorsOpen;
  if (r.friendCode) {
    const rv = (p.rivals[r.friendCode] ||= { w: 0, l: 0, name: r.friendName || '' });
    if (r.won) rv.w++; else rv.l++;
    if (r.friendName) rv.name = r.friendName;
  }
  // titles
  const T = [
    [p.stats.wins >= 1, 'First Blood'], [p.stats.wins >= 25, 'Regular'], [p.stats.wins >= 100, 'Superintendent'],
    [p.stats.perfects >= 1, 'Flawless Lease'], [p.stats.longestCombo >= 10, 'Combo Tenant'], [p.stats.longestCombo >= 20, 'Late Fee Collector'],
    [p.level >= 10, 'Long-term Lease'], [p.level >= 25, 'Freehold'],
  ];
  for (const [cond, t] of T) if (cond && !p.titles.includes(t)) { p.titles.push(t); out.titles.push(t); }
  save();
  return out;
}

export function recordArcade(fighter, level) {
  const p = profile();
  const out = { unlocks: [] };
  p.arcade[fighter] = Math.max(p.arcade[fighter] ?? -1, level);
  const u = unlockNext('Cleared the Arcade Ladder');
  if (u) out.unlocks.push(u);
  if (level >= 3 && !p.unlocked.includes('landlord')) { p.unlocked.push('landlord'); out.unlocks.push({ id: 'landlord', reason: 'Cleared the ladder on The Landlord difficulty' }); }
  if (!p.titles.includes('Ladder Climber')) p.titles.push('Ladder Climber');
  if (level >= 3 && !p.titles.includes('Evictor')) p.titles.push('Evictor');
  save();
  return out;
}

export function colorsFor(id) { return profile().colors[id] || 2; }
export function allFighterIds() { return Object.keys(FIGHTERS); }

// ---------------------------------------------------------------- move codes (carry a save to another PC)
export function exportSave() { return btoa(unescape(encodeURIComponent(JSON.stringify(profile())))); }
export function importSave(text) {
  const obj = JSON.parse(decodeURIComponent(escape(atob(text.trim()))));
  if (!obj || obj.v !== 1) throw new Error('Not a JoeBrawla save');
  data = obj; save();
}
