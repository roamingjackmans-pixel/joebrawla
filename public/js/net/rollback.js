// Rollback netcode (GGPO style) for a 1v1 match. Both browsers run the same deterministic simulation; each frame
// we send our input (with the last few for redundancy), predict the opponent's input (= their last known one),
// and when their real input for an earlier frame arrives and differs, we restore that frame's snapshot and
// re-simulate up to now. docs/DESIGN.md §10.
import { step } from '../../shared/sim.js';
import { checksum } from '../../shared/core.js';

const STEP = 1000 / 60;
const MAX_ROLLBACK = 10;     // never predict further ahead than this
const REDUNDANCY = 10;       // inputs per packet
const KEEP = 120;            // frames of history kept

export class RollbackDriver {
  /**
   * opts: { send(msg), local: 0|1 (our player index), delay (frames), readLocal(): bits, onDesync(), onStall(frames) }
   */
  constructor(match, opts) {
    this.m = match; this.o = opts;
    this.li = opts.local; this.ri = 1 - opts.local;
    this.delay = opts.delay ?? 2;
    this.local = new Map(); this.remote = new Map(); this.used = new Map(); this.snaps = new Map();
    this.lastRemote = -1;      // highest frame we have the opponent's real input for (contiguous)
    this.remoteMax = -1;
    this.rollbackTo = Infinity;
    this.acc = 0; this.maxFrame = 0;
    this.remoteFrame = 0; this.remoteAdv = 0; this.rtt = 100; this.lastPing = 0; this.lastHeard = performance.now();
    this.stats = { rollbacks: 0, maxDepth: 0, stalls: 0 };
    this.checks = new Map(); this.remoteChecks = new Map(); this.desynced = false;
    for (let f = 0; f < this.delay; f++) this.local.set(f, 0);
  }

  get frame() { return this.m.state.frame; }

  /** a message from the other side */
  receive(msg) {
    this.lastHeard = performance.now();
    if (msg.t === 'in') {
      // msg.f = frame of the last input in msg.b; msg.b = inputs for frames f-len+1 .. f
      const first = msg.f - msg.b.length + 1;
      for (let k = 0; k < msg.b.length; k++) {
        const fr = first + k;
        if (fr < 0 || this.remote.has(fr)) continue;
        this.remote.set(fr, msg.b[k]);
        if (fr < this.frame && this.used.has(fr) && this.used.get(fr) !== msg.b[k]) this.rollbackTo = Math.min(this.rollbackTo, fr);
        if (fr > this.remoteMax) this.remoteMax = fr;
      }
      while (this.remote.has(this.lastRemote + 1)) this.lastRemote++;
      this.remoteFrame = msg.cur ?? this.remoteFrame;
      if (msg.ack != null) this.acked = msg.ack;
    } else if (msg.t === 'ping') {
      this.o.send({ t: 'pong', ts: msg.ts });
    } else if (msg.t === 'pong') {
      this.rtt = this.rtt * 0.8 + (performance.now() - msg.ts) * 0.2;
    } else if (msg.t === 'ck') {
      this.remoteChecks.set(msg.f, msg.c);
      this.compareChecks();
    }
  }

  compareChecks() {
    for (const [f, c] of this.remoteChecks) {
      if (!this.checks.has(f)) continue;
      if (this.checks.get(f) !== c && !this.desynced) { this.desynced = true; console.warn('[rollback] desync at frame', f); this.o.onDesync?.(f); }
      this.remoteChecks.delete(f);
    }
  }

  inputsFor(fr) {
    const loc = this.local.get(fr) ?? 0;
    let rem = this.remote.get(fr);
    if (rem === undefined) {
      // predict: the opponent keeps doing what they last did
      rem = this.remote.get(this.lastRemote) ?? 0;
      rem &= 0x0f; // directions only: never predict button presses
    }
    this.used.set(fr, rem);
    return this.li === 0 ? [loc, rem] : [rem, loc];
  }

  /** advance; returns { stepped, alpha } for the renderer */
  tick(dtMs, session) {
    const now = performance.now();
    if (now - this.lastPing > 500) { this.lastPing = now; this.o.send({ t: 'ping', ts: now }); }
    // time sync: if we're ahead of the opponent, slow down a touch so rollbacks stay short
    const rttF = this.rtt / STEP;
    const adv = this.frame - (this.remoteFrame + rttF / 2);
    this.remoteAdv = adv;
    let speed = 1;
    if (adv > 2) speed = 0.92; else if (adv > 1) speed = 0.97;
    this.acc += dtMs * speed;
    let stepped = false;
    // 1) roll back if a misprediction was found
    if (this.rollbackTo < this.frame) {
      const from = this.rollbackTo;
      const snap = this.snaps.get(from);
      if (snap) {
        const target = this.frame;
        this.m.state = structuredClone(snap);
        this.stats.rollbacks++; this.stats.maxDepth = Math.max(this.stats.maxDepth, target - from);
        while (this.frame < target) this.simulate(session, true);
      }
      this.rollbackTo = Infinity;
    }
    // 2) new frames
    let n = 0;
    while (this.acc >= STEP && n < 4) {
      if (this.frame - this.lastRemote > MAX_ROLLBACK) { this.stats.stalls++; this.o.onStall?.(this.frame - this.lastRemote); this.acc = Math.min(this.acc, STEP); break; }
      // our input for frame + delay
      const target = this.frame + this.delay;
      if (!this.local.has(target)) this.local.set(target, this.o.readLocal());
      this.sendInputs(target);
      this.simulate(session, false);
      this.acc -= STEP; n++; stepped = true;
    }
    if (n === 4) this.acc = 0;
    // 3) forget old history
    const old = this.frame - KEEP;
    for (const map of [this.local, this.remote, this.used, this.snaps]) for (const k of map.keys()) if (k < old) map.delete(k);
    for (const k of this.checks.keys()) if (k < old - 300) this.checks.delete(k);
    return { stepped, alpha: Math.min(1, this.acc / STEP) };
  }

  sendInputs(upTo) {
    const b = [];
    for (let fr = Math.max(0, upTo - REDUNDANCY + 1); fr <= upTo; fr++) b.push(this.local.get(fr) ?? 0);
    this.o.send({ t: 'in', f: upTo, b, cur: this.frame, ack: this.lastRemote });
  }

  simulate(session, resim) {
    const fr = this.frame;
    this.snaps.set(fr, structuredClone(this.m.state));
    const prev = resim ? null : this.snaps.get(fr);
    const evs = step(this.m, this.inputsFor(fr));
    // checksums on frames both sides have confirmed
    const conf = fr - 1;
    if (conf % 60 === 0 && conf <= this.lastRemote && this.snaps.has(conf + 1) && !this.checks.has(conf)) {
      const c = checksum(this.snaps.get(conf + 1));
      this.checks.set(conf, c);
      this.o.send({ t: 'ck', f: conf, c });
      this.compareChecks();
    }
    if (!resim || this.frame > this.maxFrame) {
      if (this.frame > this.maxFrame) { this.maxFrame = this.frame; session.stepped(prev || structuredClone(this.m.state), evs); }
    }
  }

  /** milliseconds since we last heard from the other side */
  silence() { return performance.now() - this.lastHeard; }
}
