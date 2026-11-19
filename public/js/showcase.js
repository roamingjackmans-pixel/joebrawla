// The 3D backdrop behind the menus: a stage and up to two fighters posing, with a slow cinematic camera.
// Used by the title, character select, VS and results screens.
import * as THREE from '../vendor/three.bundle.js';
import { FighterView } from './render/fighterView.js';
import { buildStage } from './render/stages.js';
import { FIGHTERS } from '../shared/fighters/index.js';

const fake = (i, act, x) => ({ i, act, t: 0, x: x * 10000, y: 0, vx: 0, vy: 0, face: x < 0 ? 1 : -1, move: null, mf: 0, overtime: false, guard: false, jumpDir: 0, hp: 1, maxHp: 1 });

export class Showcase {
  constructor(scene) {
    this.scene = scene;
    this.views = [null, null]; this.ids = [null, null]; this.states = [null, null];
    this.mode = 'title'; this.stageId = null; this.running = false; this.t0 = performance.now();
    this.loading = new Map();
  }

  async setStage(id) {
    if (this.stageId === id) return;
    this.stageId = id;
    const st = await buildStage(id, this.scene.renderer);
    if (this.stageId === id) this.scene.setStage(st);
  }

  /** slot 0/1: fighter id (or null to clear), colour, pose ('idle' | 'intro' | 'win' | 'lose') */
  async setFighter(slot, id, color = 0, act = 'idle') {
    const key = `${id}:${color}`;
    this.want = this.want || [];
    this.want[slot] = key;
    if (!id) { if (this.views[slot]) { this.views[slot].holder.visible = false; } this.ids[slot] = null; return; }
    if (this.ids[slot] === key && this.views[slot]) { this.views[slot].holder.visible = true; this.pose(slot, act); return; }
    const v = await FighterView.create(id, FIGHTERS[id], color);
    if (this.want[slot] !== key) return; // superseded while loading
    if (this.views[slot]) this.views[slot].dispose();
    this.views[slot] = v; this.ids[slot] = key;
    this.scene.scene.add(v.holder);
    this.pose(slot, act);
  }

  pose(slot, act) {
    const x = this.layoutX(slot);
    this.states[slot] = fake(slot, act, x);
    if (this.views[slot]) { this.views[slot].anim.key = ''; this.views[slot].yaw = null; }
  }

  layoutX(slot) {
    if (this.mode === 'select') return slot === 0 ? -1.7 : 1.7;
    if (this.mode === 'vs') return slot === 0 ? -1.25 : 1.25;
    if (this.mode === 'results') return slot === 0 ? -0.2 : 9;
    return slot === 0 ? -1.1 : 1.1;
  }

  setMode(mode) {
    this.mode = mode;
    for (let i = 0; i < 2; i++) if (this.states[i]) { const s = this.states[i]; s.x = this.layoutX(i) * 10000; s.face = s.x < 0 ? 1 : -1; }
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.scene.cam.override = (now) => this.camera(now);
    let last = performance.now();
    const loop = (t) => {
      if (!this.running) return;
      this.raf = requestAnimationFrame(loop);
      const dt = Math.min(100, t - last); last = t;
      this.frame(t / 1000, dt / (1000 / 60));
    };
    this.raf = requestAnimationFrame(loop);
  }
  stop() {
    this.running = false; cancelAnimationFrame(this.raf);
    this.scene.cam.override = null;
    for (const v of this.views) if (v) v.holder.visible = false;
  }
  /** hide the showcase fighters (a match is starting with its own) */
  clearFighters() { for (let i = 0; i < 2; i++) { if (this.views[i]) this.views[i].dispose(); this.views[i] = null; this.ids[i] = null; this.states[i] = null; } }

  frame(now, dt60) {
    for (let i = 0; i < 2; i++) {
      const v = this.views[i], s = this.states[i];
      if (!v || !s) continue;
      if (!v.holder.parent) this.scene.scene.add(v.holder);
      v.holder.visible = true;
      s.t += dt60;
      v.update(s, s, 1, now, { phase: 'menu', dt60 });
    }
    this.scene.render(null, null, 1, now, dt60);
  }

  camera(now) {
    const t = now - this.t0 / 1000;
    const m = this.mode;
    if (m === 'select') return { pos: new THREE.Vector3(Math.sin(t * 0.08) * 0.4, 1.45, 6.4), look: new THREE.Vector3(0, 1.15, 0), fov: 34 };
    if (m === 'vs') return { pos: new THREE.Vector3(Math.sin(t * 0.25) * 0.6, 1.3, 4.6 - Math.min(1, t * 0.2) * 0.4), look: new THREE.Vector3(0, 1.25, 0), fov: 36 };
    if (m === 'results') { const x = -0.2; return { pos: new THREE.Vector3(x + 1.6 + Math.sin(t * 0.2) * 0.3, 1.35, 3.3), look: new THREE.Vector3(x, 1.2, 0), fov: 34 }; }
    // title: a slow drifting orbit
    const a = Math.sin(t * 0.05) * 0.5;
    return { pos: new THREE.Vector3(Math.sin(a) * 7.5, 1.6 + Math.sin(t * 0.13) * 0.15, Math.cos(a) * 7.5), look: new THREE.Vector3(0, 1.3, 0), fov: 32 };
  }
}
