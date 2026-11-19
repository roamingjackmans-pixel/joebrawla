// One fighter on screen: the model (cloned from a cached GLB), its rig and animator, colours, hit flashes
// and the per-frame transform from the simulation state.
import * as THREE from '../../vendor/three.bundle.js';
import { Rig } from '../anim/rig.js';
import { Animator } from '../anim/animator.js';
import { setFor } from '../anim/sets.js';
import { RENDER } from './fighterLooks.js';

const { GLTFLoader, MeshoptDecoder, SkeletonUtils } = THREE;
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const cache = new Map();
export const U2M = 1 / 10000; // sim units -> metres

export function loadGLB(url) {
  if (!cache.has(url)) cache.set(url, new Promise((res, rej) => loader.load(url, res, undefined, rej)));
  return cache.get(url);
}

let clipsPromise = null;
/** the shared animation clip library, name -> AnimationClip */
export function loadClips() {
  if (!clipsPromise) {
    clipsPromise = Promise.all(['base'].map((n) => loadGLB(`assets/anim/${n}.glb`))).then((gs) => {
      const out = {};
      for (const g of gs) for (const c of g.animations) out[c.name] = c;
      return out;
    });
  }
  return clipsPromise;
}

async function loadModel(id) {
  const look = RENDER[id] || {};
  const tries = [look.model || id, ...(look.fallback ? [look.fallback] : []), 'gary'];
  for (const m of tries) {
    try { return { gltf: await loadGLB(`assets/fighters/${m}.glb`), model: m }; } catch { /* try the next */ }
  }
  throw new Error('no model for ' + id);
}

export class FighterView {
  static async create(id, fighterData, colorIdx = 0, opts = {}) {
    const [{ gltf, model }, clips] = await Promise.all([loadModel(id), loadClips()]);
    return new FighterView(id, fighterData, gltf, model, clips, colorIdx, opts);
  }

  constructor(id, data, gltf, model, clips, colorIdx, opts) {
    this.id = id; this.data = data; this.model = model;
    this.look = RENDER[id] || {};
    this.holder = new THREE.Group();
    this.obj = SkeletonUtils.clone(gltf.scene);
    this.holder.add(this.obj);
    this.materials = [];
    this.obj.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;
        o.material = Array.isArray(o.material) ? o.material.map((m) => this.own(m)) : this.own(o.material);
      }
    });
    this.setColor(colorIdx);
    this.rig = new Rig(this.obj);
    const set = setFor(id, clips);
    set.yScale = this.look.yScale || 1;
    this.anim = new Animator(this.rig, set, data);
    this.yaw = null;
    this.flash = 0; this.flashColor = new THREE.Color(1, 1, 1);
    this.glow = 0; this.glowColor = new THREE.Color(1, 0.3, 0.1);
    this.scaleMul = opts.scale || 1;
    this.bigHead = !!opts.bigHead;
    this.obj.scale.setScalar(this.look.scale || 1);
  }

  own(m) {
    const c = m.clone();
    c.userData.baseColor = c.color ? c.color.clone() : null;
    c.userData.baseEmissive = c.emissive ? c.emissive.clone() : null;
    c.userData.baseEmissiveIntensity = c.emissiveIntensity ?? 1;
    this.materials.push(c);
    return c;
  }

  setColor(idx) {
    const pal = (this.data.colors || [])[idx];
    const look = this.look;
    const t1 = look.tint1 || [], t2 = look.tint2 || [];
    const alt = (look.alts || [])[idx];
    for (const m of this.materials) {
      if (!m.color || !m.userData.baseColor) continue;
      m.color.copy(m.userData.baseColor);
      if (idx === 0) continue;
      const n = m.name || '';
      const is1 = n.startsWith('tint1') || t1.some((x) => n.startsWith(x));
      const is2 = n.startsWith('tint2') || t2.some((x) => n.startsWith(x));
      if (is1 && pal) m.color.set(pal).multiplyScalar(1.6);
      else if (is2 && alt) m.color.set(alt).multiplyScalar(1.6);
    }
  }

  /**
   * f: fighter state now, p: fighter state one sim frame earlier (for interpolation), alpha 0..1
   */
  update(f, p, alpha, now, ctx) {
    const lerp = (a, b) => a + (b - a) * alpha;
    const x = lerp(p.x, f.x) * U2M, y = lerp(p.y, f.y) * U2M;
    // move frame with sub-frame interpolation (for the animation timeline)
    const frameF = f.act === 'move' && p.act === 'move' && p.move === f.move ? lerp(p.mf, f.mf) : f.mf;
    let ff = f.act === 'move' ? frameF : f.t + alpha;
    if (f.act === 'cine' && ctx.cine) ff = ctx.cine.t + alpha;
    this.anim.update(f, ff, now, { phase: ctx.phase, dt60: ctx.dt60, cine: ctx.cine });
    // facing: turn smoothly
    const want = f.face > 0 ? Math.PI / 2 : -Math.PI / 2;
    if (this.yaw === null) this.yaw = want;
    const dy = want - this.yaw;
    this.yaw += dy * Math.min(1, 0.35 * ctx.dt60);
    if (Math.abs(dy) < 0.01) this.yaw = want;
    const v = this.anim.visual;
    this.holder.position.set(x, y + (v.lift || 0), 0);
    this.holder.rotation.set(0, 0, 0);
    this.holder.rotateY(this.yaw + (v.spin || 0) * Math.PI / 180);
    if (v.tilt) {
      // flips rotate around the body's middle
      const c = (this.rig.pelvisY || 0.95);
      this.holder.position.y += c;
      this.holder.rotateX(v.tilt * Math.PI / 180 * (f.face > 0 ? 1 : 1));
      this.obj.position.y = -c;
    } else this.obj.position.y = 0;
    // juggle tumble
    if (f.act === 'air' || (f.act === 'ko' && f.y > 0)) {
      const c = 0.9;
      this.holder.position.y += c; this.obj.position.y = -c;
      this.holder.rotateX(-Math.min(1.2, (f.t || 0) * 0.04) * (f.vy < 0 ? 1.4 : 1));
    }
    const s = this.scaleMul;
    this.holder.scale.setScalar(s);
    if (this.bigHead && this.rig.bones.Head) this.rig.bones.Head.scale.setScalar(1.9);
    // flashes (hit white, Overtime heat, Just Block shine)
    if (this.flash > 0) this.flash = Math.max(0, this.flash - 0.18 * ctx.dt60);
    const glowTarget = f.overtime ? 0.35 + 0.15 * Math.sin(now * 8) : 0;
    this.glow += (glowTarget - this.glow) * 0.2;
    for (const m of this.materials) {
      if (!m.emissive) continue;
      const base = m.userData.baseEmissive;
      m.emissive.copy(base || m.emissive.set(0, 0, 0));
      m.emissiveIntensity = m.userData.baseEmissiveIntensity;
      if (this.glow > 0.01) { m.emissive.lerp(this.glowColor, this.glow); m.emissiveIntensity = Math.max(m.emissiveIntensity, 1); }
      if (this.flash > 0) { m.emissive.lerp(this.flashColor, Math.min(1, this.flash)); m.emissiveIntensity = Math.max(m.emissiveIntensity, 1.4 * this.flash); }
    }
  }

  hitFlash(color = 0xffffff, k = 1) { this.flash = k; this.flashColor.set(color); }

  bonePos(name, out) { return this.rig.worldPos(name, out); }

  dispose() { this.holder.removeFromParent(); }
}
