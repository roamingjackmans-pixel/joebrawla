// A match on screen: owns the simulation, steps it at a fixed 60 Hz (or lets a netcode driver do it), renders
// with interpolation, and turns simulation events into effects, sounds, callouts and camera work.
import * as THREE from '../vendor/three.bundle.js';
import { createMatch, step } from '../shared/sim.js';
import { FIGHTERS } from '../shared/fighters/index.js';
import { FighterView, U2M } from './render/fighterView.js';
import { buildStage } from './render/stages.js';
import { readDevice } from './input.js';
import { audio } from './audio.js';

const STEP = 1000 / 60;
const STR_SHAKE = { L: 0.03, M: 0.06, H: 0.12, X: 0.2, S: 0.14, flare: 0.07, counter: 0.16 };

export class Session {
  /**
   * opts: { scene (FightScene), hud (HUD), setup (createMatch setup), players: [{kind:'local'|'bot'|'net'|'dummy', device, bot}],
   *         stage, colors, onEnd(result), onPause(), driver (optional netcode driver), names }
   */
  constructor(opts) {
    this.o = opts;
    this.scene = opts.scene; this.hud = opts.hud;
    this.match = createMatch(opts.setup);
    this.prev = structuredClone(this.match.state);
    this.acc = 0; this.last = 0; this.running = false; this.paused = false;
    this.lastEventFrame = 0;
    this.cutin = null;
    this.ended = false;
    this.inputHook = null;
    this.recorder = null;
  }

  get state() { return this.match.state; }
  get cfg() { return this.match.cfg; }

  async load(progress) {
    const s = this.o.setup;
    const [v0, v1, stage] = await Promise.all([
      FighterView.create(s.fighters[0], FIGHTERS[s.fighters[0]], (s.colors || [0, 0])[0], this.viewOpts(0)),
      FighterView.create(s.fighters[1], FIGHTERS[s.fighters[1]], (s.colors || [0, 1])[1] ?? 1, this.viewOpts(1)),
      buildStage(this.o.stage || 'crypt', this.scene.renderer),
    ]);
    progress?.(1);
    this.scene.setStage(stage);
    this.scene.setFighter(0, v0); this.scene.setFighter(1, v1);
    this.views = [v0, v1];
    const d = s.fighters.map((id) => FIGHTERS[id]);
    this.hud.setNames(this.o.names || d.map((x) => x.name), d.map((x) => x.title), this.cfg.rounds);
    this.hud.show(true);
  }

  viewOpts(i) {
    const m = this.cfg.mods;
    return { bigHead: m.bigHeads, scale: m.size === 'tiny' ? 0.7 : m.size === 'giant' ? 1.35 : 1 };
  }

  start() {
    this.running = true;
    this.last = performance.now();
    const loop = (t) => {
      if (!this.running) return;
      this.raf = requestAnimationFrame(loop);
      this.frame(t);
    };
    this.raf = requestAnimationFrame(loop);
    audio.music(this.o.stage || 'crypt');
  }

  stop() {
    this.running = false; cancelAnimationFrame(this.raf);
    this.scene.cam.override = null;
    this.scene.fx.clear();
    audio.stopMusic();
  }

  /** inputs for this frame from local devices / bots (a net driver supplies its own) */
  localInputs() {
    const inputs = [0, 0];
    for (let i = 0; i < 2; i++) {
      const p = this.o.players[i];
      if (p.kind === 'local') inputs[i] = readDevice(p.device || 'any');
      else if (p.kind === 'bot' && p.bot) inputs[i] = p.bot.think(this.match, i);
      else if (p.kind === 'dummy' && p.dummy) inputs[i] = p.dummy(this.match, i);
    }
    if (this.inputHook) this.inputHook(inputs);
    return inputs;
  }

  frame(t) {
    const dtMs = Math.min(100, t - this.last); this.last = t;
    const dt60 = dtMs / STEP;
    if (!this.paused) {
      if (this.o.driver) {
        // a netcode driver advances the sim itself and tells us which frames are new
        const r = this.o.driver.tick(dtMs, this);
        if (r && r.stepped) { this.alpha = r.alpha ?? 1; }
      } else {
        this.acc += dtMs;
        let n = 0;
        while (this.acc >= STEP && n < 4) {
          this.prev = structuredClone(this.match.state);
          const evs = step(this.match, this.localInputs());
          this.handleEvents(evs);
          this.o.onStep?.(this.match);
          this.acc -= STEP; n++;
        }
        if (n === 4) this.acc = 0;
      }
    }
    const alpha = this.o.driver ? (this.alpha ?? 1) : this.acc / STEP;
    const now = t / 1000;
    this.updateTrails();
    this.scene.render(this.match.state, this.prev, Math.min(1, alpha), now, dt60);
    this.hud.update(this.match.state, this.cfg, dt60);
    this.updatePost(dt60);
    if (this.match.state.phase === 'matchEnd' && !this.ended) {
      this.ended = true;
      setTimeout(() => this.o.onEnd?.(this.result()), 600);
    }
  }

  /** called by a net driver after it steps (prev/next for interpolation) */
  stepped(prev, evs) { this.prev = prev; this.handleEvents(evs); this.o.onStep?.(this.match); }

  result() {
    const st = this.match.state;
    return { winner: st.winner, wins: st.wins.slice(), frames: st.frame, stats: st.f.map((f) => ({ ...f.stats, hp: f.hp, maxHp: f.maxHp })), fighters: this.o.setup.fighters.slice() };
  }

  updatePost(dt60) {
    const st = this.match.state;
    const p = this.scene.post;
    const target = st.freeze > 0 ? 0.55 : st.timeStop > 0 ? 0.3 : st.cine ? 0.15 : 0;
    p.dark += (target - p.dark) * Math.min(1, 0.25 * dt60);
    const tint = this.scene.grade.uniforms.tint.value;
    if (st.timeStop > 0) tint.setRGB(0.75, 0.85, 1.15); else tint.setRGB(1, 1, 1);
  }

  updateTrails() {
    const st = this.match.state;
    for (let i = 0; i < 2; i++) {
      const f = st.f[i], v = this.views?.[i];
      if (!v) continue;
      const mv = f.move ? FIGHTERS[this.cfg.fighters[i]].moves[f.move] : null;
      const on = f.act === 'move' && mv && mv.hits.length && f.mf >= mv.startup - 1 && f.mf <= mv.startup + mv.active + 1;
      const spec = mv ? (v.anim.set.moves[f.move] || v.anim.set.moves[f.move.replace(/_(L|M|H|EX)$/, '')]) : null;
      const bone = spec?.trail || (mv && /cr_|j_H|latefee|launcher|kick/.test(f.move) ? 'foot_r' : mv && f.move === 'st_L' ? 'hand_l' : 'hand_r');
      const col = mv?.type === 'super' || mv?.type === 'final' ? 0x80d0ff : mv?.type === 'ex' ? 0xffe080 : mv?.type === 'breaker' ? 0xb080ff : 0xffc070;
      this.scene.fx.trail('f' + i, v.bonePos(bone, new THREE.Vector3()), !!on, col, mv?.type === 'normal' ? 0.07 : 0.12);
    }
  }

  // ---------------------------------------------------------------- events -> presentation
  handleEvents(evs) {
    const st = this.match.state;
    if (st.frame <= this.lastEventFrame) return; // re-simulated frames (rollback) don't replay effects
    this.lastEventFrame = st.frame;
    const sc = this.scene, fx = sc.fx, hud = this.hud;
    for (const e of evs) {
      switch (e.t) {
        case 'hit': {
          const x = e.x * U2M, y = e.y * U2M;
          const att = e.by >= 0 ? st.f[e.by] : null;
          const dir = att ? att.face : 1;
          const kind = e.counter ? 'counter' : e.str || 'M';
          fx.hit(x, y, dir, kind, { scale: e.super ? 1.4 : 1 });
          sc.shake(STR_SHAKE[kind] ?? 0.06, kind === 'H' || kind === 'counter' ? 16 : 10);
          if (kind === 'H' || kind === 'counter' || e.super) sc.post.aberr = Math.max(sc.post.aberr, e.super ? 1 : 0.6);
          this.views[e.who].hitFlash(0xffffff, e.str === 'L' ? 0.6 : 1);
          this.views[e.who].anim.onHit(y > 1.25, { L: 0, M: 1, H: 2 }[e.str] ?? 2);
          hud.onDamage(e.who);
          audio.hit(e.str, e.counter, e.super);
          if (e.counter === 1) hud.small(e.by, 'COUNTER', 'red');
          if (e.counter === 2) hud.small(e.by, 'PUNISH!', 'gold');
          break;
        }
        case 'block': {
          const x = e.x * U2M, y = e.y * U2M;
          fx.block(x, y, st.f[e.who].face, e.just);
          if (e.just) { hud.small(e.who, 'JUST BLOCK', 'white'); sc.flash(0xffffff, 0.25); this.views[e.who].hitFlash(0xbfe8ff, 1); audio.justBlock(); }
          else audio.block(e.str);
          sc.shake(0.02, 6);
          break;
        }
        case 'armor': fx.block(e.x * U2M, e.y * U2M, 1, false); this.views[e.who].hitFlash(0xff9040, 1); audio.armor(); break;
        case 'super': this.superCutin(e); break;
        case 'cine': this.cinematic(e); break;
        case 'ex': { const f = st.f[e.who]; fx.burst(f.x * U2M, 1.1, 0xffd060, 30, 4, 0.12); this.views[e.who].hitFlash(0xffd060, 0.8); audio.ex(); break; }
        case 'breaker': {
          const f = st.f[e.who];
          fx.burst(f.x * U2M, 1.0, 0xa060ff, 60, 6, 0.18); fx.ring(f.x * U2M, 1.0, 0.3, 3, 0xa060ff, 20);
          sc.flash(0x9a5cff, 0.35); this.views[e.who].hitFlash(0xa070ff, 1.2);
          hud.small(e.who, e.reversal ? 'BREAKER REVERSAL' : 'BREAKER!', 'violet'); audio.breaker();
          break;
        }
        case 'overtime': hud.small(e.who, 'OVERTIME', 'red'); audio.overtime(); break;
        case 'splat': fx.dust(e.x * U2M, e.y * U2M, 24, true, 0xbbbbbb); sc.shake(0.25, 18); hud.small(1 - e.who, 'WALL SPLAT', 'gold'); audio.splat(); break;
        case 'bounce': fx.dust(e.x * U2M, 0, 20, true); sc.shake(0.15, 12); audio.thud(); break;
        case 'wallBounce': sc.shake(0.12, 10); audio.thud(); break;
        case 'down': fx.dust(e.x * U2M, 0, e.hard || e.ko ? 26 : 16, !!(e.hard || e.ko)); sc.shake(e.ko ? 0.12 : 0.05, 10); audio.thud(e.ko); break;
        case 'land': fx.dust(st.f[e.who].x * U2M, 0, 6); audio.step(); break;
        case 'jump': audio.jump(); break;
        case 'dash': fx.dust(st.f[e.who].x * U2M, 0, 8); audio.dash(); break;
        case 'grab': audio.grab(); break;
        case 'tech': fx.block(e.x * U2M, 1.2, 1, true); hud.small(0, 'TECH', 'blue'); hud.small(1, 'TECH', 'blue'); audio.block('M'); break;
        case 'proj': audio.proj(e.kind); break;
        case 'projEnd': if (e.hit !== undefined || e.kind) fx.burst(e.x * U2M, e.y * U2M, 0xffe090, 16, 3, 0.1); break;
        case 'clash': fx.hit(e.x * U2M, e.y * U2M, 1, 'flare'); audio.hit('M'); break;
        case 'reflect': fx.block(e.x * U2M, e.y * U2M, 1, true); audio.justBlock(); break;
        case 'counterStance': fx.block(e.x * U2M, e.y * U2M, 1, true); sc.flash(0xffffff, 0.3); hud.small(e.who, 'COUNTERED', 'white'); audio.justBlock(); break;
        case 'teleport': fx.burst(st.f[e.who].x * U2M, 1, 0xb080ff, 30, 3, 0.12); audio.whoosh(); break;
        case 'heal': fx.burst(st.f[e.who].x * U2M, 1.2, 0x80ff90, 30, 2, 0.12); audio.heal(); break;
        case 'timestop': sc.flash(0xc0e0ff, 0.5); audio.timestop(); break;
        case 'item': fx.burst(e.x * U2M, 0.4, e.item === 'bomb' ? 0xff6020 : e.item === 'coin' ? 0xffd040 : 0x80ff90, 40, 4, 0.14); if (e.item === 'bomb') { sc.shake(0.2, 14); audio.splat(); } else audio.heal(); break;
        case 'trap': audio.whoosh(); break;
        case 'ko': {
          hud.call('<b>K.O.</b>', 'ko', 2200);
          sc.flash(0xffffff, 0.8); sc.shake(0.3, 24); sc.post.radial = 1;
          fx.hit(e.x * U2M, e.y * U2M, st.f[e.by] ? st.f[e.by].face : 1, 'H', { scale: 2 });
          audio.ko();
          this.koCamera(e.who);
          break;
        }
        case 'round': hud.call(`<b>ROUND ${e.n}</b>`, 'blue', 1300); audio.announce(`Round ${e.n}`); this.scene.cam.override = null; break;
        case 'fight': hud.call('<b>BRAWL!</b>', '', 1000); audio.announce('Brawl!'); audio.gong(); break;
        case 'roundOver':
          if (e.how === 'time') { hud.call('<b>TIME</b>', 'blue', 1600); audio.announce('Time!'); }
          if (e.perfect) setTimeout(() => { hud.call('<b>FLAWLESS LEASE</b>', '', 1800); audio.announce('Flawless lease'); }, 1300);
          if (e.how === 'ko' && e.winner < 0) setTimeout(() => hud.call('<b>DOUBLE K.O.</b>', 'ko', 1600), 900);
          break;
        case 'suddenDeath': hud.call('<b>SUDDEN DEATH</b>', 'ko', 1600); break;
        case 'matchEnd': break;
      }
    }
    // the intro: sweep the camera past each fighter
    if (st.phase === 'intro' && st.pt === 1) this.introCamera();
  }

  superCutin(e) {
    const st = this.match.state;
    const d = FIGHTERS[this.cfg.fighters[e.who]];
    const mv = d.moves[e.move];
    const el = document.createElement('div');
    el.className = `cutin s${e.who} ${e.kind === 'final' ? 'final' : e.kind === 'overtime' ? 'ot' : ''}`;
    el.innerHTML = `<div class="band"></div><div class="name"><small>${e.kind === 'final' ? 'FINAL NOTICE' : e.kind === 'overtime' ? 'OVERTIME ART' : 'SUPER ART'}</small><b>${mv.name}</b></div>`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1150);
    const f = st.f[e.who];
    const fx = this.scene.fx;
    fx.burst(f.x * U2M, 1.2, e.kind === 'overtime' ? 0xff5020 : 0x60c8ff, 80, 5, 0.16);
    fx.ring(f.x * U2M, 1.1, 0.3, 4, e.kind === 'overtime' ? 0xff5020 : 0x60c8ff, 26);
    this.views[e.who].hitFlash(e.kind === 'overtime' ? 0xff6030 : 0x80d8ff, 1.5);
    audio.superFlash(e.kind);
    if (e.kind !== 'super') audio.announce(e.kind === 'final' ? 'Final notice!' : 'Overtime!');
    // camera: a quick push-in on the user during the freeze
    const x = f.x * U2M, face = f.face, t0 = performance.now() / 1000, len = (mv.freeze || 36) / 60;
    this.scene.cam.override = (now) => {
      const k = (now - t0) / len;
      if (k > 1) { this.scene.cam.override = null; return null; }
      const e2 = Math.sin(Math.min(1, k * 1.6) * Math.PI / 2);
      return { pos: new THREE.Vector3(x + face * 1.6 * e2, 1.45, 3.6 + (1 - e2) * 4), look: new THREE.Vector3(x, 1.3, 0), fov: 34 - e2 * 6 };
    };
  }

  cinematic(e) {
    const st = this.match.state;
    const a = st.f[e.who];
    const len = st.cine.len / 60;
    const t0 = performance.now() / 1000;
    const face = a.face;
    const kind = FIGHTERS[this.cfg.fighters[e.who]].moves[e.move].type;
    this.scene.flash(0xffffff, 0.6);
    this.scene.cam.override = (now) => {
      const k = (now - t0) / len;
      if (k > 1 || !this.match.state.cine) { this.scene.cam.override = null; return null; }
      const x = this.match.state.f[e.who].x * U2M + face * 0.45;
      // three shots: low side, orbit, wide finish
      let ang, dist, h, fov;
      if (kind === 'super') { ang = -0.5 + k * 1.4; dist = 3.4 - k * 0.4; h = 1.0 + k * 0.4; fov = 36; }
      else if (k < 0.35) { ang = -0.9 + k * 1.2; dist = 3.0; h = 0.7; fov = 40; }
      else if (k < 0.7) { ang = 0.6 + (k - 0.35) * 2.5; dist = 3.8; h = 1.6; fov = 34; }
      else { ang = 0.15; dist = 6.5 - (k - 0.7) * 3; h = 1.3; fov = 30; }
      const pos = new THREE.Vector3(x + Math.sin(ang) * dist * face, h, Math.cos(ang) * dist);
      return { pos, look: new THREE.Vector3(x, 1.15, 0), fov };
    };
  }

  koCamera(loser) {
    const t0 = performance.now() / 1000;
    this.scene.cam.override = (now) => {
      const k = (now - t0) / 1.8;
      if (k > 1 || this.match.state.phase === 'roundEnd' || this.match.state.phase === 'ready') { this.scene.cam.override = null; return null; }
      const f = this.match.state.f[loser];
      const x = f.x * U2M, y = Math.max(0.6, f.y * U2M + 0.8);
      const ang = -0.6 + k * 0.9;
      return { pos: new THREE.Vector3(x + Math.sin(ang) * 4.2, 1.2 + k * 0.6, Math.cos(ang) * 4.2), look: new THREE.Vector3(x, y, 0), fov: 32 };
    };
  }

  introCamera() {
    const t0 = performance.now() / 1000;
    const st = this.match.state;
    const d = st.f.map((f) => FIGHTERS[this.cfg.fighters[f.i]]);
    this.hud.call(`<small>${d[0].name} vs ${d[1].name}</small>`, '', 1600);
    setTimeout(() => d[0].lines?.intro && this.hud.small(0, '“' + d[0].lines.intro + '”', 'white'), 300);
    setTimeout(() => d[1].lines?.intro && this.hud.small(1, '“' + d[1].lines.intro + '”', 'white'), 1500);
    this.scene.cam.override = (now) => {
      const k = (now - t0) / 2.8;
      if (k > 1 || this.match.state.phase !== 'intro') { this.scene.cam.override = null; return null; }
      const who = k < 0.5 ? 0 : 1;
      const f = this.match.state.f[who];
      const kk = (k % 0.5) * 2;
      const x = f.x * U2M;
      const side = f.face; // in front of the fighter, so we see their face
      return { pos: new THREE.Vector3(x + side * (2.1 - kk * 0.7), 1.15 + kk * 0.35, 3.0 - kk * 0.4), look: new THREE.Vector3(x + side * 0.2, 1.35, 0), fov: 32 };
    };
  }
}
