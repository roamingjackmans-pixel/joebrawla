// The 3D view of a match: renderer, post-processing, the fight camera (with shakes and cinematic cuts),
// the stage, the two fighters and the effects. game.js feeds it sim state and events every frame.
import * as THREE from '../../vendor/three.bundle.js';
import { FX } from './fx.js';
import { U2M } from './fighterView.js';

const { EffectComposer, RenderPass, UnrealBloomPass, OutputPass, ShaderPass, FXAAPass } = THREE;

export const QUALITY = {
  low: { pixelRatio: 0.75, shadows: false, bloom: false, aa: false, shadowSize: 512 },
  medium: { pixelRatio: 1, shadows: true, bloom: true, aa: true, shadowSize: 1024 },
  high: { pixelRatio: Math.min(devicePixelRatio || 1, 1.5), shadows: true, bloom: true, aa: true, shadowSize: 2048 },
  ultra: { pixelRatio: Math.min(devicePixelRatio || 1, 2), shadows: true, bloom: true, aa: true, shadowSize: 4096 },
};

const GradeShader = {
  uniforms: {
    tDiffuse: { value: null }, vignette: { value: 0.32 }, aberr: { value: 0 }, flash: { value: 0 }, flashCol: { value: new THREE.Color(1, 1, 1) },
    sat: { value: 1.08 }, contrast: { value: 1.06 }, dark: { value: 0 }, tint: { value: new THREE.Color(1, 1, 1) }, time: { value: 0 }, radial: { value: 0 }, center: { value: new THREE.Vector2(0.5, 0.5) },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float vignette, aberr, flash, sat, contrast, dark, time, radial; uniform vec3 flashCol, tint; uniform vec2 center; varying vec2 vUv;
    void main(){
      vec2 uv = vUv;
      vec2 d = uv - center;
      vec3 c;
      if (radial > 0.001) {
        vec3 acc = vec3(0.0);
        for (int i = 0; i < 10; i++) { float k = float(i) / 9.0; acc += texture2D(tDiffuse, center + d * (1.0 - radial * 0.12 * k)).rgb; }
        c = acc / 10.0;
      } else if (aberr > 0.0) {
        c.r = texture2D(tDiffuse, uv + d * aberr * 0.02).r; c.g = texture2D(tDiffuse, uv).g; c.b = texture2D(tDiffuse, uv - d * aberr * 0.02).b;
      } else c = texture2D(tDiffuse, uv).rgb;
      float l = dot(c, vec3(0.299, 0.587, 0.114));
      c = mix(vec3(l), c, sat);
      c = (c - 0.5) * contrast + 0.5;
      c *= tint;
      c *= 1.0 - dark;
      float v = smoothstep(0.85, 0.2, length(d * vec2(1.25, 1.0)));
      c *= mix(1.0 - vignette, 1.0, v);
      c = mix(c, flashCol, flash);
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export class FightScene {
  constructor(canvas, quality = 'high') {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(30, 16 / 9, 0.1, 400);
    this.camera.position.set(0, 1.4, 9);
    this.fx = new FX(this.scene, this.camera);
    this.fighters = [null, null];
    this.cam = { x: 0, y: 1.3, z: 9, lx: 0, ly: 1.05, shake: 0, shakeT: 0, kick: new THREE.Vector3(), fov: 30, override: null };
    this.post = { flash: 0, flashCol: new THREE.Color(1, 1, 1), aberr: 0, dark: 0, radial: 0 };
    this.stage = null;
    this.setQuality(quality);
    this.resize();
    addEventListener('resize', () => this.resize());
  }

  setQuality(q) {
    this.q = QUALITY[q] || QUALITY.high;
    this.renderer.setPixelRatio(this.q.pixelRatio);
    this.renderer.shadowMap.enabled = this.q.shadows;
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    if (this.q.bloom) { this.bloom = new UnrealBloomPass(new THREE.Vector2(1280, 720), 0.42, 0.55, 0.82); this.composer.addPass(this.bloom); } else this.bloom = null;
    this.composer.addPass(new OutputPass());
    this.grade = new ShaderPass(GradeShader);
    this.composer.addPass(this.grade);
    if (this.q.aa) { this.fxaa = new FXAAPass(); this.composer.addPass(this.fxaa); }
    if (this.stage && this.stage.sun) this.stage.sun.shadow.mapSize.set(this.q.shadowSize, this.q.shadowSize);
    this.resize();
  }

  resize() {
    const w = this.canvas.clientWidth || innerWidth, h = this.canvas.clientHeight || innerHeight;
    this.renderer.setSize(w, h, false);
    this.composer.setSize(w, h);
    if (this.fxaa) this.fxaa.setSize?.(w * this.renderer.getPixelRatio(), h * this.renderer.getPixelRatio());
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }

  setStage(stage) {
    if (this.stage) this.stage.group.removeFromParent();
    this.stage = stage;
    this.scene.add(stage.group);
    this.scene.background = stage.background || null;
    this.scene.environment = stage.env || null;
    this.scene.environmentIntensity = stage.envIntensity ?? 0.8;
    this.scene.fog = stage.fog || null;
    if (stage.sun) stage.sun.shadow.mapSize.set(this.q.shadowSize, this.q.shadowSize);
    if (stage.grade) Object.assign(this.grade.uniforms.sat, { value: stage.grade.sat ?? 1.08 });
    if (stage.grade?.tint) this.grade.uniforms.tint.value.set(stage.grade.tint);
    if (this.bloom && stage.bloom) { this.bloom.strength = stage.bloom[0]; this.bloom.threshold = stage.bloom[1]; }
  }

  setFighter(i, view) {
    if (this.fighters[i]) this.fighters[i].dispose();
    this.fighters[i] = view;
    this.scene.add(view.holder);
  }

  shake(amount, frames = 12) { amount *= this.shakeScale ?? 1; this.cam.shake = Math.max(this.cam.shake, amount); this.cam.shakeT = Math.max(this.cam.shakeT, frames); }
  flash(color = 0xffffff, k = 0.6) { this.post.flash = Math.max(this.post.flash, k); this.post.flashCol.set(color); }

  /** fight camera target from the two fighters (metres) */
  followCamera(a, b, dt60) {
    const c = this.cam;
    const mid = (a.x + b.x) / 2;
    const gap = Math.abs(a.x - b.x);
    const top = Math.max(a.y, b.y);
    const z = Math.min(11.5, Math.max(7.4, 5.6 + gap * 0.85 + top * 0.6));
    const halfW = Math.tan((this.camera.fov / 2) * Math.PI / 180) * z * this.camera.aspect;
    const lim = Math.max(0, 7.5 - halfW + 0.35);
    const x = Math.max(-lim, Math.min(lim, mid));
    const y = 1.25 + top * 0.45;
    const k = 1 - Math.pow(0.86, dt60);
    c.x += (x - c.x) * k; c.z += (z - c.z) * k * 0.7; c.y += (y - c.y) * k * 0.6;
    c.lx += (x - c.lx) * k; c.ly += (1.0 + top * 0.5 - c.ly) * k * 0.6;
  }

  render(state, prev, alpha, now, dt60, ctx = {}) {
    const fv = this.fighters;
    if (fv[0] && fv[1] && state) {
      for (let i = 0; i < 2; i++) fv[i].update(state.f[i], prev.f[i], alpha, now, { phase: state.phase, dt60, cine: state.cine });
      const ax = (prev.f[0].x + (state.f[0].x - prev.f[0].x) * alpha) * U2M, bx = (prev.f[1].x + (state.f[1].x - prev.f[1].x) * alpha) * U2M;
      const ay = state.f[0].y * U2M, by = state.f[1].y * U2M;
      this.followCamera({ x: ax, y: ay }, { x: bx, y: by }, dt60);
      this.fx.syncProjectiles(state.proj, U2M, now);
    }
    // camera: follow, or a cinematic override (function of time) from game.js
    const c = this.cam;
    let pos = new THREE.Vector3(c.x, c.y, c.z), look = new THREE.Vector3(c.lx, c.ly, 0), fov = 30;
    if (c.override) {
      const o = c.override(now, pos, look);
      if (o) { pos = o.pos; look = o.look; fov = o.fov || 30; }
    }
    if (c.shakeT > 0) {
      c.shakeT -= dt60;
      const s = c.shake * Math.max(0, c.shakeT / 12);
      pos.x += (Math.random() - 0.5) * s; pos.y += (Math.random() - 0.5) * s; look.x += (Math.random() - 0.5) * s * 0.5;
    }
    this.camera.fov += (fov - this.camera.fov) * 0.25; this.camera.updateProjectionMatrix();
    this.camera.position.copy(pos);
    this.camera.lookAt(look);
    if (this.stage && this.stage.update) this.stage.update(now, dt60, this);
    this.fx.update(dt60);
    // post
    const g = this.grade.uniforms, p = this.post;
    p.flash = Math.max(0, p.flash - 0.08 * dt60);
    p.aberr = Math.max(0, p.aberr - 0.08 * dt60);
    p.radial = Math.max(0, p.radial - 0.04 * dt60);
    g.flash.value = p.flash; g.flashCol.value.copy(p.flashCol); g.aberr.value = p.aberr; g.dark.value = p.dark; g.radial.value = p.radial; g.time.value = now;
    this.composer.render();
  }
}
