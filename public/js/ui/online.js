// Online Versus: the friends hub (your 4-digit code, friends, requests, invites) and the 2-player lobby
// (picks, host rules, stage, ready, set score, quick chat), then rollback-netcode matches. docs/DESIGN.md §10.
import { show, esc, toast, modal, focus, rerender, hideMenu } from './ui.js';
import { app, playMatch, afterMatch } from '../app.js';
import { profile, save, isUnlocked } from '../profile.js';
import { FIGHTERS } from '../../shared/fighters/index.js';
import { STAGES } from '../render/stages.js';
import { activeLabels } from '../../shared/modifiers.js';
import { hostRoom, joinRoom, cleanCode } from '../net/transport.js';
import {
  myFriendCode, friends, friendRequests, acceptRequest, ignoreRequest, addFriend, removeFriend, isPending,
  recentPlayers, noteRecent, onFriends, setStatusFn, setBusyCheck, presence, beReachable, claimCode, cleanFriendCode,
} from '../net/friends.js';
import { RollbackDriver } from '../net/rollback.js';
import { readDevice } from '../input.js';
import { audio } from '../audio.js';
import { MainMenu } from './menus.js';
import { characterSelect, ARCH } from './select.js';
import { modsScreen } from './mods.js';

const QUICK = ['GG!', 'Rematch?', 'Nice combo.', 'Your deposit will not be returned.', 'Lights are back on.', 'One more.', 'Ouch.', 'Wipe your feet.'];
let lobby = null;   // the current lobby (host or guest)
let wired = false;

function wireOnce() {
  if (wired) return; wired = true;
  setStatusFn(() => ({ room: lobby && !lobby.full() && !lobby.inMatch ? lobby.code : '', what: lobby?.inMatch ? 'in a match' : lobby ? 'in a lobby' : app.inMatch ? 'playing offline' : 'in the menus' }));
  setBusyCheck(() => !!(lobby && (lobby.full() || lobby.inMatch)) || app.inMatch);
  onFriends('invite', (inv) => invitePopup(inv));
  onFriends('request', (r) => toast(`<b>${esc(r.name)}</b> (${esc(r.code)}) sent you a friend request. See Online Versus.`));
  onFriends('accepted', (r) => toast(`<b>${esc(r.name)}</b> accepted your friend request.`));
  onFriends('change', () => { const c = document.querySelector('.screen-online'); if (c && !document.querySelector('.modal-layer')) hubPaint(); });
}

// ---------------------------------------------------------------- the hub
export async function onlineHub() {
  wireOnce();
  beReachable();
  claimCode().catch(() => {});
  show(HubScreen, {}, { root: true });
}

const HubScreen = {
  id: 'online',
  render: () => `<div class="shade-all" style="position:absolute;inset:0"></div><div style="position:relative" id="hub"></div>`,
  mount() { hubPaint(); presence.checkAll?.(); this.t = setInterval(() => presence.checkAll?.(), 20000); },
  unmount() { clearInterval(this.t); },
  back: () => { show(MainMenu, {}, { root: true }); return true; },
};

function statusOf(code) {
  const s = presence.status.get(code);
  if (!s) return { cls: '', text: 'checking…' };
  if (s.state === 'online') return s.room ? { cls: 'lobby', text: `in lobby ${s.room}`, room: s.room } : { cls: s.what === 'in a match' ? 'match' : 'on', text: s.what || 'online' };
  if (s.state === 'checking') return { cls: '', text: 'checking…' };
  return { cls: '', text: 'offline' };
}

function hubPaint() {
  const el = document.getElementById('hub'); if (!el) return;
  const p = profile();
  const fs = friends(), reqs = friendRequests(), recent = recentPlayers();
  const rec = (code) => { const r = p.rivals[code]; return r ? `${r.w}–${r.l}` : ''; };
  const keep = document.querySelector('.screen-online .focus')?.dataset.key;
  el.innerHTML = `<h1 class="title-h">ONLINE VERSUS<small>Friends and codes · 1 v 1 lobbies</small></h1>
    <div class="online-grid">
      <div>
        <div class="sub">YOUR FRIEND CODE</div><div class="code-big">${esc(myFriendCode())}</div>
        <div class="sub" style="margin:6px 0 18px">Give it to a friend so they can add you. Name: <b style="color:#fff">${esc(p.name)}</b></div>
        <div style="display:flex;flex-direction:column;gap:8px;max-width:360px">
          <button class="btn big" data-f data-key="create" data-autofocus>Create a lobby</button>
          <button class="btn" data-f data-key="join">Join with a lobby code</button>
          <button class="btn" data-f data-key="add">Add a friend by code</button>
          <button class="btn" data-f data-key="back">Back</button>
        </div>
      </div>
      <div class="panel" style="padding:14px 16px;max-height:70vh;overflow-y:auto">
        ${reqs.length ? `<div class="group-h">Friend requests</div>${reqs.map((r) => `<div class="friend"><div><b>${esc(r.name)}</b> <span class="meta">${esc(r.code)}</span></div><div class="acts"><button class="btn small" data-f data-key="acc:${r.code}">Accept</button><button class="btn small" data-f data-key="ign:${r.code}">Ignore</button></div></div>`).join('')}` : ''}
        <div class="group-h">Friends (${fs.length})</div>
        ${fs.length ? fs.map((f) => { const s = statusOf(f.code); return `<div class="friend"><div><span class="dot ${s.cls}"></span><b>${esc(f.name)}</b> <span class="meta">${esc(f.code)}${isPending(f.code) ? ' · request sent' : ''}${rec(f.code) ? ' · you ' + rec(f.code) : ''}</span><div class="meta">${esc(s.text)}</div></div><div class="acts">${s.room ? `<button class="btn small" data-f data-key="joinf:${s.room}">Join</button>` : ''}${s.cls === 'on' ? `<button class="btn small" data-f data-key="inv:${f.code}">Invite</button>` : ''}<button class="btn small" data-f data-key="rm:${f.code}">✕</button></div></div>`; }).join('') : '<div class="sub" style="padding:10px">No friends yet. Add one with their 4-digit code.</div>'}
        ${recent.length ? `<div class="group-h">Played recently</div>${recent.map((r) => `<div class="friend"><div><b>${esc(r.name)}</b> <span class="meta">${esc(r.code)}</span></div><div class="acts"><button class="btn small" data-f data-key="addr:${r.code}:${esc(r.name)}">Add friend</button></div></div>`).join('')}` : ''}
      </div>
    </div>`;
  el.querySelectorAll('[data-key]').forEach((b) => b.addEventListener('click', () => hubAction(b.dataset.key)));
  if (keep) { const k = el.querySelector(`[data-key="${keep}"]`); if (k) focus(k, true); }
}

async function hubAction(key) {
  const [k, a, b] = key.split(':');
  if (k === 'back') return show(MainMenu, {}, { root: true });
  if (k === 'create') return createLobby();
  if (k === 'join') { const code = await askCode('JOIN A LOBBY', 'Type the 4-digit lobby code.'); if (code) joinLobby(code); return; }
  if (k === 'add') {
    const code = await askCode('ADD A FRIEND', 'Type their 4-digit friend code.');
    if (!code) return;
    const r = addFriend(code);
    toast(r.ok ? (r.accepted ? 'You are now friends.' : 'Friend request sent. It waits for them if they’re offline.') : esc(r.msg));
    return hubPaint();
  }
  if (k === 'acc') { acceptRequest(a); return hubPaint(); }
  if (k === 'ign') { ignoreRequest(a); return hubPaint(); }
  if (k === 'rm') { const ok = await modal('<h2>REMOVE FRIEND?</h2>', [{ label: 'Remove', value: true }, { label: 'Keep', value: false }], { focus: 1 }); if (ok) removeFriend(a); return hubPaint(); }
  if (k === 'joinf') return joinLobby(a);
  if (k === 'inv') { await createLobby(); lobby?.invite(a); return; }
  if (k === 'addr') { addFriend(a, b); toast('Friend request sent.'); return hubPaint(); }
}

async function askCode(title, text) {
  let v = '';
  const r = await modal(`<h2>${esc(title)}</h2><p>${esc(text)}</p><input id="codein" inputmode="numeric" maxlength="4" autocomplete="off">`, [{ label: 'OK', value: true }, { label: 'Cancel', value: false }], {
    mount: (m) => { const i = m.querySelector('#codein'); setTimeout(() => i.focus(), 60); i.addEventListener('input', () => { i.value = cleanCode(i.value); v = i.value; }); i.addEventListener('keydown', (e) => { if (e.key === 'Enter' && i.value.length === 4) { e.stopPropagation(); m.querySelector('[data-i="0"]').click(); } }); },
  });
  return r && v.length === 4 ? v : null;
}

function invitePopup(inv) {
  audio.ui('big');
  const box = document.createElement('div');
  box.className = 'invite-pop panel';
  box.innerHTML = `<b>${esc(inv.name)}</b> wants to brawl! <div class="sub">Lobby ${esc(inv.room)}</div><div style="display:flex;gap:8px;margin-top:10px"><button class="btn small" data-y>Join</button><button class="btn small" data-n>Not now</button></div>`;
  document.body.appendChild(box);
  const close = () => box.remove();
  box.querySelector('[data-y]').onclick = () => { inv.respond('yes'); close(); if (app.inMatch) { toast('Finish your match first.'); return; } if (lobby) lobby.leave(true); joinLobby(inv.room); };
  box.querySelector('[data-n]').onclick = () => { inv.respond('no'); close(); };
  setTimeout(close, 40000);
}

// ---------------------------------------------------------------- lobby
class Lobby {
  constructor(transport, code, isHost) {
    this.t = transport; this.code = code; this.isHost = isHost; this.inMatch = false;
    const p = profile();
    const me = { name: p.name, code: myFriendCode(), title: p.title, level: p.level, fighter: p.lastFighter && isUnlocked(p.lastFighter) ? p.lastFighter : 'joe', color: 0, scheme: p.settings.scheme[0], ready: false };
    this.s = { code, players: isHost ? [me, null] : [null, me], mods: { ...(p.lastMods.online || {}) }, stage: p.lastStage || 'crypt', stageMode: 'host', set: [0, 0] };
    this.me = isHost ? 0 : 1;
    this.chat = [];
    this.driver = null;
    transport.on('message', (m) => this.onMsg(m));
    transport.on('peer-join', () => { /* the guest says hello */ });
    transport.on('peer-leave', () => this.onLeave());
    if (!isHost) this.send({ t: 'hello', ...me, v: 1 });
  }
  full() { return !!(this.s.players[0] && this.s.players[1]); }
  other() { return this.s.players[1 - this.me]; }
  send(m) { try { this.t.send(m); } catch (e) { console.warn(e); } }
  sync() { if (this.isHost) this.send({ t: 'lobby', s: this.s }); this.paint(); }

  onMsg(m) {
    if (!m || typeof m !== 'object') return;
    if (this.driver && (m.t === 'in' || m.t === 'ping' || m.t === 'pong' || m.t === 'ck')) { this.driver.receive(m); return; }
    switch (m.t) {
      case 'hello': if (this.isHost) { this.s.players[1] = { name: String(m.name || 'Joe').slice(0, 16), code: cleanFriendCode(m.code), title: m.title || '', level: m.level | 0, fighter: FIGHTERS[m.fighter] ? m.fighter : 'joe', color: m.color | 0, scheme: m.scheme === 'simple' ? 'simple' : 'classic', ready: false }; noteRecent(m.code, m.name); audio.ui('big'); this.sync(); } break;
      case 'lobby': if (!this.isHost) { const mine = this.s.players[1]; this.s = m.s; if (mine && this.s.players[1]) Object.assign(this.s.players[1], { fighter: this.s.players[1].fighter }); const o = this.s.players[0]; if (o) noteRecent(o.code, o.name); this.paint(); } break;
      case 'pick': { const pl = this.s.players[1 - this.me]; if (pl) { Object.assign(pl, { fighter: FIGHTERS[m.fighter] ? m.fighter : pl.fighter, color: m.color | 0, scheme: m.scheme }); pl.ready = false; this.sync(); } break; }
      case 'ready': { const pl = this.s.players[1 - this.me]; if (pl) { pl.ready = !!m.on; this.sync(); } break; }
      case 'chat': this.chat.push({ who: this.other()?.name || '?', text: QUICK[m.id] || '' }); audio.ui('tab'); this.paint(); break;
      case 'start': if (!this.isHost) this.runMatch(m); break;
      case 'loaded': this.peerLoaded = true; this.maybeGo(); break;
      case 'go': this.goNow?.(); break;
      case 'bye': this.onLeave(true); break;
      case 'full': toast('That lobby is full.'); this.close(); onlineHub(); break;
    }
  }

  onLeave(said) {
    if (this.closed) return;
    if (this.inMatch) { toast('Your opponent left the match.'); this.forfeit = true; this.endMatch?.(); }
    if (this.isHost) { this.s.players[1] = null; this.s.players[0].ready = false; toast('Your opponent left the lobby.'); this.sync(); }
    else { toast('The host closed the lobby.'); this.close(); if (!this.inMatch) onlineHub(); }
  }

  pick(fighter, color, scheme) {
    const me = this.s.players[this.me];
    Object.assign(me, { fighter, color, scheme, ready: false });
    profile().lastFighter = fighter; save();
    if (this.isHost) this.sync(); else { this.send({ t: 'pick', fighter, color, scheme }); this.paint(); }
  }
  setReady(on) { this.s.players[this.me].ready = on; if (this.isHost) this.sync(); else { this.send({ t: 'ready', on }); this.paint(); } }
  say(id) { this.send({ t: 'chat', id }); this.chat.push({ who: 'You', text: QUICK[id] }); this.paint(); }
  invite(code) { if (!this.isHost) return; presence.invite(code, this.code).then((a) => { if (a === 'busy') toast('They’re busy right now.'); else if (a === 'no') toast('They said not now.'); }).catch(() => toast('They seem to be offline.')); toast('Invite sent.'); }

  leave(quiet) { this.send({ t: 'bye' }); this.close(); if (!quiet) onlineHub(); }
  close() { this.closed = true; try { this.t.close(); } catch { /* gone */ } if (lobby === this) lobby = null; }

  // ---- the match
  startAsHost() {
    if (!this.isHost || !this.full()) return;
    const [a, b] = this.s.players;
    let stage = this.s.stage;
    if (this.s.stageMode === 'random' || stage === 'random') { const list = STAGES.filter((x) => !x.hidden); stage = list[Math.floor(Math.random() * list.length)].id; }
    const m = { t: 'start', seed: String(Date.now()) + Math.random().toString(36).slice(2, 6), stage, mods: this.s.mods, fighters: [a.fighter, b.fighter], colors: [a.color, b.color === a.color && a.fighter === b.fighter ? (a.color + 1) % 8 : b.color], simple: [a.scheme === 'simple', b.scheme === 'simple'], delay: profile().settings.inputDelay };
    this.send(m);
    this.runMatch(m);
  }

  maybeGo() { if (this.isHost && this.peerLoaded && this.selfLoaded) { this.send({ t: 'go' }); this.goNow?.(); } }

  async runMatch(m) {
    this.inMatch = true; this.peerLoaded = this.peerLoaded || false; this.selfLoaded = false; this.forfeit = false;
    const p = profile();
    const names = this.s.players.map((x) => x?.name || '?');
    const opp = this.other();
    let driver = null;
    const result = await playMatch({
      setup: { fighters: m.fighters, colors: m.colors, seed: m.seed, mods: m.mods, simple: m.simple },
      players: [{ kind: 'net' }, { kind: 'net' }], stage: m.stage, names, online: true, localIndex: this.me,
      tags: this.me === 0 ? ['YOU', opp?.code || ''] : [opp?.code || '', 'YOU'],
      info: (() => { const r = p.rivals[opp?.code]; return r ? `<div class="rival">You ${r.w} – ${r.l} ${esc(opp.name)}</div>` : ''; })(),
      driver: (driver = new RollbackDriver(null, { send: (x) => this.send(x), local: this.me, delay: m.delay || p.settings.inputDelay || 2, readLocal: () => readDevice('any'), onDesync: () => toast('Connection hiccup (desync). The match continues.') })),
      onReady: (session) => {
        driver.m = session.match;
        // hold the clock until both sides have loaded
        session.paused = true;
        this.selfLoaded = true;
        this.goNow = () => { session.paused = false; this.goNow = null; };
        this.endMatch = () => { session.ended = true; session.o.onEnd?.(null); };
        if (!this.isHost) this.send({ t: 'loaded' }); else this.maybeGo();
        this.driver = driver;
        this.netHud = setInterval(() => { app.hud.netInfo(`ping ${Math.round(driver.rtt)} ms · delay ${driver.delay} · rollbacks ${driver.stats.rollbacks}`); if (driver.silence() > 15000 && !session.ended) { toast('Lost the connection.'); this.endMatch(); } }, 500);
      },
      canRestart: false,
    });
    clearInterval(this.netHud);
    this.driver = null; this.inMatch = false; this.peerLoaded = false;
    if (this.closed) return onlineHub();
    if (result && result.winner >= 0) this.s.set[result.winner]++;
    this.s.players.forEach((x) => x && (x.ready = false));
    const v = await afterMatch(result || { winner: this.forfeit ? this.me : -1, fighters: m.fighters, stats: null }, {
      mode: 'online', localIndex: this.me, colors: m.colors, names, friendCode: opp?.code, friendName: opp?.name, record: !!result,
      title: `SET ${this.s.set[0]} – ${this.s.set[1]}`, buttons: [{ label: 'Back to lobby', value: 'lobby' }, { label: 'Leave', value: 'leave' }],
    });
    if (v === 'leave') return this.leave();
    show(LobbyScreen, {}, { root: true });
    this.sync();
  }

  paint() { if (document.querySelector('.screen-lobby')) lobbyPaint(); }
}

async function createLobby() {
  if (lobby) { show(LobbyScreen, {}, { root: true }); return; }
  toast('Opening a lobby…');
  try {
    const { transport, code } = await hostRoom();
    lobby = new Lobby(transport, code, true);
    show(LobbyScreen, {}, { root: true });
  } catch (e) { toast('Could not open a lobby: ' + esc(e.message || e)); }
}

async function joinLobby(code) {
  toast(`Finding lobby ${esc(code)}…`);
  try {
    const p = profile();
    if (!p.uid) { p.uid = Math.random().toString(36).slice(2); save(); }
    const transport = await joinRoom(code, p.uid);
    lobby = new Lobby(transport, code, false);
    show(LobbyScreen, {}, { root: true });
  } catch (e) { toast(esc(e.message || 'Could not join that lobby.')); }
}

const LobbyScreen = {
  id: 'lobby',
  render: () => `<div class="shade-all" style="position:absolute;inset:0"></div><div style="position:relative" id="lob"></div>`,
  mount() { lobbyPaint(); app.showcase.setMode('select'); },
  back: () => { lobby?.leave(); return true; },
};

function lobbyPaint() {
  const el = document.getElementById('lob'); if (!el || !lobby) return;
  const L = lobby, s = L.s;
  const keep = document.querySelector('.screen-lobby .focus')?.dataset.key;
  const card = (pl, i) => pl ? `<div class="lcard panel"><div class="sub">${i === 0 ? 'HOST' : 'GUEST'}${i === L.me ? ' · YOU' : ''} · Lv ${pl.level} · ${esc(pl.title || '')}</div><div class="nm">${esc(pl.name)}</div>
      <div><b>${esc(FIGHTERS[pl.fighter]?.name || '?')}</b> <span class="sub">${esc(ARCH[pl.fighter] || '')} · ${pl.scheme === 'simple' ? 'Simple' : 'Classic'}</span></div><div class="${pl.ready ? 'rd' : 'sub'}">${pl.ready ? 'READY' : 'not ready'}</div></div>`
    : `<div class="lcard panel empty">Waiting for someone to join with code ${esc(s.code)}…</div>`;
  const mods = activeLabels(s.mods);
  const me = s.players[L.me];
  const canStart = L.isHost && L.full() && s.players.every((x) => x.ready);
  const st = STAGES.find((x) => x.id === s.stage);
  el.innerHTML = `<h1 class="title-h">LOBBY <span class="gold">${esc(s.code)}</span><small>Set ${s.set[0]} – ${s.set[1]} · invite link: ${esc(location.origin + location.pathname)}?room=${esc(s.code)}</small></h1>
    <div class="lobby-cards" style="margin-top:2vh">${card(s.players[0], 0)}${card(s.players[1], 1)}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2vw;margin-top:2vh">
      <div style="display:flex;flex-direction:column;gap:8px">
        <button class="btn" data-f data-key="fighter" data-autofocus>Change fighter</button>
        <button class="btn ${me?.ready ? 'red' : ''}" data-f data-key="ready">${me?.ready ? 'Not ready' : 'Ready!'}</button>
        ${L.isHost ? `<button class="btn big" data-f data-key="start" ${canStart ? '' : 'disabled'}>Start the match</button>` : '<div class="sub">The host starts when you are both ready.</div>'}
        <button class="btn" data-f data-key="rules">${L.isHost ? 'Rules & modifiers' : 'See the rules'}</button>
        ${L.isHost ? `<button class="btn" data-f data-key="stage">Stage: ${esc(s.stageMode === 'random' ? 'Random' : st?.name || s.stage)}</button>` : `<div class="sub">Stage: ${esc(s.stageMode === 'random' ? 'Random' : st?.name || s.stage)}</div>`}
        ${L.isHost && !L.full() ? '<button class="btn" data-f data-key="invite">Invite a friend</button>' : ''}
        <button class="btn red" data-f data-key="leave">Leave lobby</button>
      </div>
      <div class="panel" style="padding:12px 14px">
        <div class="group-h" style="margin-top:0">Rules</div><div class="sub" style="min-height:20px">${mods.length ? mods.map(esc).join(' · ') : 'Standard: best of 3 rounds, 99 seconds.'}</div>
        <div class="group-h">Chat</div><div class="chatlog">${L.chat.slice(-8).map((c) => `<div><b>${esc(c.who)}:</b> ${esc(c.text)}</div>`).join('')}</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">${QUICK.map((q, i) => `<button class="btn small" data-f data-key="say:${i}">${esc(q)}</button>`).join('')}</div>
      </div>
    </div>`;
  el.querySelectorAll('[data-key]').forEach((b) => b.addEventListener('click', () => lobbyAction(b.dataset.key)));
  if (keep) { const k = el.querySelector(`[data-key="${keep}"]`); if (k) focus(k, true); }
  // show both fighters in 3D behind the lobby
  s.players.forEach((pl, i) => app.showcase.setFighter(i, pl ? pl.fighter : null, pl ? pl.color : 0, pl?.ready ? 'win' : 'idle'));
}

async function lobbyAction(key) {
  const L = lobby; if (!L) return;
  const [k, a] = key.split(':');
  if (k === 'leave') return L.leave();
  if (k === 'ready') return L.setReady(!L.s.players[L.me].ready);
  if (k === 'start') return L.startAsHost();
  if (k === 'say') return L.say(+a);
  if (k === 'fighter') {
    return characterSelect({
      title: 'PICK YOUR FIGHTER', labels: ['YOU'], onBack: () => show(LobbyScreen, {}, { root: true }),
      onDone: ({ fighters, colors, schemes }) => { L.pick(fighters[0], colors[0], schemes[0]); show(LobbyScreen, {}, { root: true }); },
    });
  }
  if (k === 'rules') {
    const v = await modsScreen({ title: 'LOBBY RULES', key: 'online', readOnly: !L.isHost, initial: L.s.mods, onChange: (m) => { if (L.isHost) { L.s.mods = { ...m }; L.send({ t: 'lobby', s: L.s }); } } });
    if (L.isHost && v) { L.s.mods = v; profile().lastMods.online = v; save(); L.s.players.forEach((x) => x && (x.ready = false)); }
    show(LobbyScreen, {}, { root: true }); L.sync(); return;
  }
  if (k === 'stage') {
    const list = [...STAGES.filter((x) => !x.hidden).map((x) => x.id), 'random'];
    const i = list.indexOf(L.s.stageMode === 'random' ? 'random' : L.s.stage);
    const n = list[(i + 1) % list.length];
    if (n === 'random') L.s.stageMode = 'random'; else { L.s.stageMode = 'host'; L.s.stage = n; app.showcase.setStage(n); }
    return L.sync();
  }
  if (k === 'invite') {
    const on = friends().filter((f) => presence.status.get(f.code)?.state === 'online');
    if (!on.length) return toast('None of your friends are online right now. Share the code instead: ' + esc(L.code));
    const pickd = await modal(`<h2>INVITE</h2>${on.map((f, i) => `<button class="btn" data-f data-inv="${f.code}" style="margin:4px">${esc(f.name)}</button>`).join('')}`, [{ label: 'Close', value: null }], { mount: (m) => m.querySelectorAll('[data-inv]').forEach((b) => b.addEventListener('click', () => { L.invite(b.dataset.inv); })) });
    void pickd;
  }
}

/** ?room=1234 in the address joins that lobby straight away */
export function autoJoinFromURL() {
  const code = cleanCode(new URLSearchParams(location.search).get('room'));
  if (code.length === 4) { wireOnce(); beReachable(); joinLobby(code); return true; }
  return false;
}
export function initOnline() { wireOnce(); }
