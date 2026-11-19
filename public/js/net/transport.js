// JoeBrawla networking: rooms are peer-to-peer (the host's browser runs the game).
//  - Direct WebRTC via PeerJS (works on any static website, like josephjackman.com/games/).
//  - A backup relay for players whose phone or network can't connect directly: if the direct connection fails or
//    hasn't opened within 6 s, their messages go through public MQTT servers over secure websockets (relay.js).
// (Adapted from Alt Whisker Wars' net.js: 4-number room codes, up to 7 guests, no game server.)
// A room has a host and up to 7 guests, numbered by slot (1-7). Events: 'message'(data, fromSlot), 'peer-join'(slot),
// 'peer-leave'(slot); a guest hears from the host as slot 0. send(data, toSlot?) on the host goes to one guest or all.
import { RelayHost, RelayGuest } from './relay.js';

const MAX_GUESTS = 1; // JoeBrawla lobbies are exactly two people
const RTC_WAIT = 6000;
const FORCE_RELAY = typeof location !== 'undefined' && /[?&]forcerelay\b/.test(location.search);
/** room codes: 4 numbers, never starting with 0 */
export function genCode() {
  const a = new Uint32Array(1);
  crypto.getRandomValues(a);
  return String(1000 + (a[0] % 9000));
}
export function cleanCode(c) { return String(c || '').replace(/\D/g, '').slice(0, 4); }

class Emitter {
  constructor() { this._h = {}; }
  on(ev, fn) { (this._h[ev] ||= []).push(fn); return this; }
  off(ev, fn) { this._h[ev] = (this._h[ev] || []).filter(f => f !== fn); }
  emit(ev, ...a) { for (const f of this._h[ev] || []) { try { f(...a); } catch (e) { console.error(e); } } }
}

const cfg = () => window.JB_CONFIG || {};

export class P2PTransport extends Emitter {
  constructor() { super(); this.kind = 'p2p'; this.peer = null; this.conn = null; this.conns = new Map(); this.code = null; this.isHost = false; }
  _peerOpts() {
    const o = { debug: 1 };
    const ice = cfg().iceServers;
    if (Array.isArray(ice) && ice.length) {
      o.config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }, ...ice] };
    }
    return o;
  }
  _newPeer(id) {
    if (!window.Peer) throw new Error('Peer-to-peer library failed to load');
    return new Promise((resolve, reject) => {
      const peer = id ? new window.Peer(id, this._peerOpts()) : new window.Peer(this._peerOpts());
      const timer = setTimeout(() => reject(new Error('Could not reach the matchmaking service')), 10000);
      peer.on('open', () => { clearTimeout(timer); resolve(peer); });
      peer.on('error', err => { clearTimeout(timer); reject(err); });
    });
  }
  /** guest: the one connection to the host */
  _wire(conn) {
    this.conn = conn;
    conn.on('data', d => this.emit('message', d, 0));
    conn.on('close', () => { if (this.conn === conn) { this.conn = null; this.emit('peer-leave', 0); } });
    conn.on('error', () => {});
  }
  /** host: one connection per guest slot */
  _wireGuest(conn, slot) {
    this.conns.set(slot, conn);
    conn.on('data', d => { if (this.conns.get(slot) === conn) this.emit('message', d, slot); });
    conn.on('close', () => { if (this.conns.get(slot) === conn) { this.conns.delete(slot); this.emit('peer-leave', slot); } });
    conn.on('error', () => {});
  }
  async host() {
    const prefix = cfg().peerPrefix || 'joebrawla-v1-';
    let lastErr;
    for (let attempt = 0; attempt < 4; attempt++) {
      const code = genCode();
      try {
        this.peer = await this._newPeer(prefix + code);
        this.code = code; this.isHost = true;
        this.peer.on('connection', conn => {
          const slot = this._slotFor(conn.metadata && conn.metadata.pid);
          if (!slot) { conn.on('open', () => { conn.send({ type: 'full' }); setTimeout(() => conn.close(), 300); }); return; }
          this.conns.set(slot, conn);
          conn.on('open', () => { this._wireGuest(conn, slot); this.emit('peer-join', slot); });
        });
        this.peer.on('disconnected', () => { try { this.peer && !this.peer.destroyed && this.peer.reconnect(); } catch {} });
        this.peer.on('error', e => console.warn('peer error', e && e.type));
        // players who can't connect directly come in through the relay
        this.hub = new RelayHost(code, conn => this._acceptRelay(conn)).start();
        return code;
      } catch (e) {
        lastErr = e;
        try { this.peer && this.peer.destroy(); } catch {}
        if (!(e && e.type === 'unavailable-id')) break;
      }
    }
    throw lastErr || new Error('Could not create room');
  }
  /** host: the same player reconnecting takes back their slot; otherwise the next free one (up to 7 guests) */
  _slotFor(pid) {
    let slot = 0;
    for (const [s, c] of this.conns) if (pid && c.metadata && c.metadata.pid === pid) { slot = s; this.conns.delete(s); try { c.close(); } catch {} }
    if (!slot) for (let s = 1; s <= MAX_GUESTS && !slot; s++) if (!this.conns.has(s) || !this.conns.get(s).open) slot = s;
    return slot;
  }
  /** host: a player coming in through the relay. Their first message says who they are. */
  _acceptRelay(conn) {
    let placed = false;
    conn.on('data', m => {
      if (placed || !m || m.t !== 'relay-hello') return;
      placed = true;
      conn.metadata = { pid: m.pid };
      const slot = this._slotFor(m.pid);
      conn.send({ t: 'relay-ok' });
      if (!slot) { conn.send({ type: 'full' }); setTimeout(() => conn.close(), 300); return; }
      this._wireGuest(conn, slot);
      this.emit('peer-join', slot);
    });
  }
  /**
   * Join: straight to the host's browser if we can, otherwise through the relay. The relay starts connecting at
   * once, so switching over is quick, and gets used if the direct connection fails or hasn't opened within
   * RTC_WAIT. Without the matchmaking service at all, the relay is the only way in.
   */
  async join(code, pid) {
    const prefix = cfg().peerPrefix || 'joebrawla-v1-';
    this.peer = await this._newPeer(null).catch(() => null);
    const relay = new RelayGuest(code).prepare();
    const notFound = msg => Object.assign(new Error(msg), { code: 'notfound' });
    await new Promise((resolve, reject) => {
      let path = null, done = false, conn = null, slow = 0;
      const finish = err => {
        if (done) return;
        done = true; clearTimeout(timer); clearTimeout(slow);
        if (err) { relay.close(); reject(err); } else resolve();
      };
      const timer = setTimeout(() => finish(notFound('Room not found (or the connection was blocked)')), 20000);
      const blocked = () => finish(new Error(this.peer ? "Couldn't connect to that room. Your network may be blocking it." : 'Could not reach the game servers. Check your internet connection.'));
      const useRelay = why => {
        if (path || done) return;
        console.debug('[net] trying the relay:', why);
        if (relay.dead) return blocked();
        path = 'relay';
        clearTimeout(slow);
        if (conn) { try { conn.close(); } catch {} }
        relay.on('data', m => {
          if (done || !m || m.t !== 'relay-ok') return;
          this.kind = 'relay';
          this._wire(relay);
          console.debug('[net] joined through the relay', relay.via);
          finish();
        });
        relay.on('dead', () => { if (!done) blocked(); });
        relay.hello({ t: 'relay-hello', pid });
      };
      if (!this.peer || FORCE_RELAY) { useRelay(this.peer ? 'forced' : 'no matchmaking service'); return; }
      conn = this.peer.connect(prefix + code, { reliable: true, serialization: 'json', metadata: { pid } });
      slow = setTimeout(() => useRelay('direct connection is slow'), RTC_WAIT);
      this.peer.on('error', e => {
        if (done) return;
        if (e && e.type === 'peer-unavailable') finish(notFound('Room not found'));
        else useRelay('error ' + (e && e.type));
      });
      conn.on('open', () => {
        if (path || done) { try { conn.close(); } catch {} return; }
        path = 'direct';
        relay.close();
        this._wire(conn);
        finish();
      });
      conn.on('close', () => { if (!path && !done) useRelay('direct connection failed'); });
      conn.on('error', () => {});
    });
    this.code = code; this.isHost = false;
  }
  send(d, to) {
    const out = c => { if (c && c.open) { try { c.send(d); } catch (e) { console.warn(e); } } };
    if (!this.isHost) return out(this.conn);
    if (to) out(this.conns.get(to)); else for (const c of this.conns.values()) out(c);
  }
  get connected() { return this.isHost ? [...this.conns.values()].some(c => c.open) : !!this.conn && this.conn.open; }
  /**
   * How long a relayed connection may stay silent before it counts as gone: longer while the other side has
   * stepped away (its app was covered or paused). Host: per guest slot; guest: the link to the host. null = normal.
   */
  setPatience(ms, slot) { const c = this.isHost ? this.conns.get(slot) : this.conn; if (c && c.relay) c.patience = ms || 0; }
  /** guest: back from being paused, don't count our own silence against the host */
  refresh() { if (this.conn && this.conn.refresh) this.conn.refresh(); }
  close() {
    try { this.hub && this.hub.stop(); } catch {}
    this.hub = null;
    try { this.conn && this.conn.close(); } catch {}
    for (const c of this.conns.values()) { try { c.close(); } catch {} }
    try { this.peer && this.peer.destroy(); } catch {}
    this.conn = null; this.conns.clear(); this.peer = null;
  }
}


/** Create a room. Returns { transport, code }. */
export async function hostRoom() {
  const t = new P2PTransport();
  const code = await t.host();
  return { transport: t, code };
}
/** Join a room by its 4-number code. */
export async function joinRoom(code, pid) {
  code = cleanCode(code);
  if (code.length !== 4) throw new Error('Room codes are 4 numbers');
  const t = new P2PTransport();
  try { await t.join(code, pid); return t; }
  catch (e) { t.close(); throw e; }
}
