// Visual effects: hit sparks, streaks, flashes, shockwave rings, dust, trails and projectile visuals.
// Everything is pooled and additive where it glows. Driven by sim events (game.js) and projectile state.
import * as THREE from '../../vendor/three.bundle.js';

const MAXP = 2400, MAXS = 700;

function radialTexture(stops) {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  for (const [o, col] of stops) gr.addColorStop(o, col);
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const softTex = () => radialTexture([[0, 'rgba(255,255,255,1)'], [0.25, 'rgba(255,255,255,0.8)'], [0.6, 'rgba(255,255,255,0.15)'], [1, 'rgba(255,255,255,0)']]);
const smokeTex = () => radialTexture([[0, 'rgba(255,255,255,0.7)'], [0.5, 'rgba(255,255,255,0.35)'], [1, 'rgba(255,255,255,0)']]);

function starTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const g = c.getContext('2d');
  g.translate(128, 128);
  const gr = g.createRadialGradient(0, 0, 0, 0, 0, 128);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.15, 'rgba(255,255,255,0.9)'); gr.addColorStop(0.4, 'rgba(255,255,255,0.15)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(-128, -128, 256, 256);
  g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 6; i++) {
    g.rotate(Math.PI / 3 + (i % 2) * 0.2);
    const lg = g.createLinearGradient(0, 0, 128, 0);
    lg.addColorStop(0, 'rgba(255,255,255,0.9)'); lg.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = lg; g.beginPath(); g.moveTo(0, -4 + (i % 2) * 2); g.lineTo(128 - (i % 2) * 40, 0); g.lineTo(0, 4 - (i % 2) * 2); g.fill();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// spark palettes by strength / kind
export const SPARK = {
  L: { core: 0xfff4d0, glow: 0xffb040, n: 10, size: 0.5, speed: 3.5 },
  M: { core: 0xfff0c0, glow: 0xff8a20, n: 18, size: 0.8, speed: 4.5 },
  H: { core: 0xffffff, glow: 0xff5a10, n: 30, size: 1.2, speed: 6 },
  X: { core: 0xf0d8ff, glow: 0x9a40ff, n: 36, size: 1.5, speed: 7 },     // Breaker violet
  S: { core: 0xffffff, glow: 0x40c8ff, n: 40, size: 1.6, speed: 7.5 },   // supers
  flare: { core: 0xffffe8, glow: 0xffe070, n: 22, size: 1.0, speed: 5 },
  block: { core: 0xd8ecff, glow: 0x4aa8ff, n: 12, size: 0.7, speed: 3.5 },
  just: { core: 0xffffff, glow: 0xffffff, n: 20, size: 1.1, speed: 4 },
  counter: { core: 0xffe0e0, glow: 0xff2030, n: 30, size: 1.4, speed: 6.5 },
  fire: { core: 0xfff0c0, glow: 0xff4400, n: 26, size: 1.1, speed: 5 },
  ice: { core: 0xffffff, glow: 0x66ccff, n: 26, size: 1.0, speed: 5 },
  spore: { core: 0xe8fff0, glow: 0x40ffb0, n: 26, size: 1.0, speed: 3.5 },
  void: { core: 0xf0e0ff, glow: 0x8020ff, n: 26, size: 1.1, speed: 5 },
  water: { core: 0xe0f4ff, glow: 0x3090ff, n: 26, size: 1.0, speed: 4.5 },
};

export class FX {
  constructor(scene, camera) {
    this.scene = scene; this.camera = camera;
    this.soft = softTex(); this.smoke = smokeTex(); this.star = starTexture();
    // glowing particles (additive)
    this.p = this.makePoints(MAXP, this.soft, THREE.AdditiveBlending);
    // dust/smoke (normal blending)
    this.d = this.makePoints(900, this.smoke, THREE.NormalBlending);
    // streak sparks
    const sg = new THREE.BufferGeometry();
    sg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAXS * 6), 3));
    sg.setAttribute('color', new THREE.BufferAttribute(new Float32Array(MAXS * 6), 3));
    this.sLines = new THREE.LineSegments(sg, new THREE.LineBasicMaterial({ vertexColors: true, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }));
    this.sLines.frustumCulled = false; this.sLines.renderOrder = 10;
    scene.add(this.sLines);
    this.streaks = [];
    this.sprites = [];   // flashes and rings
    this.trails = new Map();
    this.projViews = new Map();
    this.tmp = new THREE.Vector3();
  }

  makePoints(n, tex, blending) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('size', new THREE.BufferAttribute(new Float32Array(n), 1));
    g.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(n), 1));
    const m = new THREE.ShaderMaterial({
      uniforms: { tex: { value: tex }, scale: { value: 600 } },
      vertexShader: `attribute float size; attribute float alpha; varying vec3 vC; varying float vA;
        uniform float scale;
        void main(){ vC = color; vA = alpha; vec4 mv = modelViewMatrix * vec4(position,1.0); gl_PointSize = size * scale / -mv.z; gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `uniform sampler2D tex; varying vec3 vC; varying float vA;
        void main(){ vec4 t = texture2D(tex, gl_PointCoord); gl_FragColor = vec4(vC * t.rgb, t.a * vA); }`,
      transparent: true, depthWrite: false, blending, vertexColors: true,
    });
    const pts = new THREE.Points(g, m);
    pts.frustumCulled = false; pts.renderOrder = blending === THREE.AdditiveBlending ? 11 : 5;
    this.scene.add(pts);
    return { pts, g, list: [], max: n, blending };
  }

  spawnP(sys, x, y, z, vx, vy, vz, life, size, color, opts = {}) {
    if (sys.list.length >= sys.max) sys.list.shift();
    sys.list.push({ x, y, z, vx, vy, vz, life, max: life, size, c: new THREE.Color(color), grav: opts.grav ?? 4, drag: opts.drag ?? 2.5, grow: opts.grow ?? 0, a: opts.a ?? 1 });
  }

  spawnStreak(x, y, z, vx, vy, vz, life, color) {
    if (this.streaks.length >= MAXS) this.streaks.shift();
    this.streaks.push({ x, y, z, vx, vy, vz, life, max: life, c: new THREE.Color(color) });
  }

  sprite(tex, x, y, z, size, color, life, opts = {}) {
    const m = new THREE.SpriteMaterial({ map: tex, color, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, depthTest: opts.depthTest ?? false, rotation: opts.rot ?? Math.random() * 6.28 });
    const s = new THREE.Sprite(m);
    s.position.set(x, y, z); s.scale.setScalar(size); s.renderOrder = 12;
    this.scene.add(s);
    this.sprites.push({ s, life, max: life, size, grow: opts.grow ?? 1.6, kind: 'sprite' });
  }

  ring(x, y, z, size, color, life, opts = {}) {
    const g = new THREE.RingGeometry(0.85, 1, 48);
    const m = new THREE.MeshBasicMaterial({ color, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, side: THREE.DoubleSide });
    const r = new THREE.Mesh(g, m);
    r.position.set(x, y, z);
    if (opts.flat) r.rotation.x = -Math.PI / 2; else r.lookAt(this.camera.position);
    if (opts.side) r.rotation.y = Math.PI / 2;
    r.scale.setScalar(size * 0.2); r.renderOrder = 12;
    this.scene.add(r);
    this.sprites.push({ s: r, life, max: life, size, grow: 1, kind: 'ring' });
  }

  /** the big one: a hit at (x, y) in metres, toward dir (+1/-1) */
  hit(x, y, dir, kind = 'M', opts = {}) {
    const sp = SPARK[kind] || SPARK.M;
    const z = 0.25;
    const k = opts.scale || 1;
    this.sprite(this.star, x, y, z, sp.size * 1.6 * k, sp.core, 7 + sp.size * 4, { grow: 1.3 });
    this.sprite(this.soft, x, y, z, sp.size * 2.4 * k, sp.glow, 10 + sp.size * 5, { grow: 1.8 });
    if (kind !== 'L') this.ring(x, y, z, sp.size * 1.3 * k, sp.glow, 12 + sp.size * 4);
    for (let i = 0; i < sp.n * k; i++) {
      const a = (Math.random() - 0.5) * Math.PI * 1.3 + (dir > 0 ? 0 : Math.PI);
      const v = sp.speed * (0.4 + Math.random() * 0.9);
      this.spawnStreak(x, y, z, Math.cos(a) * v, Math.sin(a) * v + 1.2, (Math.random() - 0.5) * v * 0.8, 8 + Math.random() * 10, sp.core);
      if (i % 2 === 0) this.spawnP(this.p, x, y, z, Math.cos(a) * v * 0.6, Math.sin(a) * v * 0.6 + 1, (Math.random() - 0.5) * 2, 14 + Math.random() * 14, 0.08 + Math.random() * 0.12 * sp.size, sp.glow);
    }
  }

  block(x, y, dir, just) {
    const sp = just ? SPARK.just : SPARK.block;
    this.sprite(this.soft, x, y, 0.25, just ? 2.6 : 1.4, sp.glow, just ? 16 : 9, { grow: 1.5 });
    this.ring(x, y, 0.25, just ? 1.8 : 0.9, sp.glow, just ? 16 : 10, { side: true });
    for (let i = 0; i < sp.n; i++) {
      const a = (Math.random() - 0.5) * Math.PI * 0.9 + (dir > 0 ? Math.PI : 0);
      const v = sp.speed * (0.3 + Math.random());
      this.spawnStreak(x, y, 0.25, Math.cos(a) * v, Math.sin(a) * v + 1, (Math.random() - 0.5) * v, 6 + Math.random() * 8, sp.core);
    }
  }

  dust(x, y, n = 14, big = false, color = 0x9a8a70) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI;
      const v = (big ? 2.4 : 1.4) * (0.3 + Math.random());
      this.spawnP(this.d, x + (Math.random() - 0.5) * 0.4, y + 0.05, (Math.random() - 0.5) * 0.6, Math.cos(a) * v, Math.sin(a) * v * 0.4 + 0.3, (Math.random() - 0.5), 30 + Math.random() * 30, (big ? 0.7 : 0.45) + Math.random() * 0.4, color, { grav: -0.3, drag: 3, grow: 1.2, a: 0.55 });
    }
  }

  burst(x, y, color, n = 40, speed = 5, size = 0.15) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, b = (Math.random() - 0.5) * Math.PI;
      const v = speed * (0.3 + Math.random());
      this.spawnP(this.p, x, y, 0.2, Math.cos(a) * Math.cos(b) * v, Math.sin(a) * v, Math.sin(b) * v, 20 + Math.random() * 30, size * (0.5 + Math.random()), color, { grav: 1 });
    }
  }

  /** a glowing ribbon following a bone while `on` */
  trail(key, pos, on, color = 0xffd080, width = 0.12) {
    let t = this.trails.get(key);
    if (!t) {
      const N = 14;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 2 * 3), 3));
      g.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(N * 2), 1));
      const idx = [];
      for (let i = 0; i < N - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
      g.setIndex(idx);
      const m = new THREE.ShaderMaterial({
        uniforms: { col: { value: new THREE.Color(color) } },
        vertexShader: 'attribute float alpha; varying float vA; void main(){ vA = alpha; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
        fragmentShader: 'uniform vec3 col; varying float vA; void main(){ gl_FragColor = vec4(col * 1.6, vA); }',
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(g, m); mesh.frustumCulled = false; mesh.renderOrder = 9;
      this.scene.add(mesh);
      t = { mesh, g, pts: [], N, life: 0 };
      this.trails.set(key, t);
    }
    t.mesh.material.uniforms.col.value.set(color);
    if (on) { t.pts.unshift(pos.clone()); t.life = 1; } else if (t.pts.length) t.pts.pop();
    if (t.pts.length > t.N) t.pts.length = t.N;
    const P = t.g.attributes.position.array, A = t.g.attributes.alpha.array;
    for (let i = 0; i < t.N; i++) {
      const p = t.pts[Math.min(i, t.pts.length - 1)];
      const k = 1 - i / t.N;
      const w = width * k;
      if (!p) { A[i * 2] = A[i * 2 + 1] = 0; continue; }
      P[i * 6] = p.x; P[i * 6 + 1] = p.y + w; P[i * 6 + 2] = p.z;
      P[i * 6 + 3] = p.x; P[i * 6 + 4] = p.y - w; P[i * 6 + 5] = p.z;
      A[i * 2] = A[i * 2 + 1] = t.pts.length > 1 ? k * 0.8 : 0;
    }
    t.g.attributes.position.needsUpdate = true; t.g.attributes.alpha.needsUpdate = true;
  }

  update(dt60) {
    const dt = dt60 / 60;
    for (const sys of [this.p, this.d]) {
      const P = sys.g.attributes.position.array, C = sys.g.attributes.color.array, S = sys.g.attributes.size.array, A = sys.g.attributes.alpha.array;
      sys.list = sys.list.filter((q) => (q.life -= dt60) > 0);
      let i = 0;
      for (const q of sys.list) {
        q.vy -= q.grav * dt; const dr = Math.exp(-q.drag * dt);
        q.vx *= dr; q.vy *= dr; q.vz *= dr;
        q.x += q.vx * dt; q.y += q.vy * dt; q.z += q.vz * dt;
        if (q.y < 0.02 && sys === this.p) { q.y = 0.02; q.vy *= -0.4; }
        const k = q.life / q.max;
        P[i * 3] = q.x; P[i * 3 + 1] = q.y; P[i * 3 + 2] = q.z;
        C[i * 3] = q.c.r; C[i * 3 + 1] = q.c.g; C[i * 3 + 2] = q.c.b;
        S[i] = q.size * (1 + q.grow * (1 - k));
        A[i] = Math.min(1, k * 1.5) * q.a;
        i++;
      }
      for (let j = i; j < sys.max; j++) A[j] = 0;
      sys.g.setDrawRange(0, Math.max(i, 1));
      for (const k of ['position', 'color', 'size', 'alpha']) sys.g.attributes[k].needsUpdate = true;
    }
    // streaks
    const SP = this.sLines.geometry.attributes.position.array, SC = this.sLines.geometry.attributes.color.array;
    this.streaks = this.streaks.filter((q) => (q.life -= dt60) > 0);
    let i = 0;
    for (const q of this.streaks) {
      q.vy -= 6 * dt; const dr = Math.exp(-3 * dt); q.vx *= dr; q.vy *= dr; q.vz *= dr;
      q.x += q.vx * dt; q.y += q.vy * dt; q.z += q.vz * dt;
      const k = q.life / q.max, L = 0.035;
      SP[i * 6] = q.x; SP[i * 6 + 1] = q.y; SP[i * 6 + 2] = q.z;
      SP[i * 6 + 3] = q.x - q.vx * L; SP[i * 6 + 4] = q.y - q.vy * L; SP[i * 6 + 5] = q.z - q.vz * L;
      for (let j = 0; j < 2; j++) { SC[i * 6 + j * 3] = q.c.r * k * 2; SC[i * 6 + j * 3 + 1] = q.c.g * k * 2; SC[i * 6 + j * 3 + 2] = q.c.b * k * 2; }
      i++;
    }
    this.sLines.geometry.setDrawRange(0, i * 2);
    this.sLines.geometry.attributes.position.needsUpdate = true; this.sLines.geometry.attributes.color.needsUpdate = true;
    // sprites and rings
    this.sprites = this.sprites.filter((o) => {
      o.life -= dt60;
      if (o.life <= 0) { o.s.removeFromParent(); o.s.material.dispose(); if (o.s.geometry && o.kind === 'ring') o.s.geometry.dispose(); return false; }
      const k = o.life / o.max;
      if (o.kind === 'ring') { o.s.scale.setScalar(o.size * (0.2 + (1 - k) * 1.6)); o.s.material.opacity = k; }
      else { o.s.scale.setScalar(o.size * (1 + (1 - k) * (o.grow - 1))); o.s.material.opacity = Math.min(1, k * 1.4); }
      return true;
    });
  }

  // ---------------------------------------------------------------- projectiles
  syncProjectiles(list, U2M, now) {
    const seen = new Set();
    for (const p of list) {
      seen.add(p.id);
      let v = this.projViews.get(p.id);
      if (!v) { v = this.makeProj(p); this.projViews.set(p.id, v); }
      const x = p.x * U2M, y = p.y * U2M;
      v.group.position.set(x, y, 0.1);
      v.group.scale.x = p.face >= 0 ? 1 : -1;
      if (v.update) v.update(now, p);
      if (Math.random() < 0.7 && v.color != null) this.spawnP(this.p, x - p.face * 0.2, y + (Math.random() - 0.5) * 0.3, 0.1 + (Math.random() - 0.5) * 0.3, -p.face * 0.8, (Math.random() - 0.5), 0, 14, 0.25, v.color, { grav: 0 });
    }
    for (const [id, v] of this.projViews) if (!seen.has(id)) { v.group.removeFromParent(); this.projViews.delete(id); }
  }

  makeProj(p) {
    const group = new THREE.Group();
    const kind = p.kind || 'bolt';
    const color = { flare: 0xfff0a0, fire: 0xff6020, ice: 0x80d8ff, spore: 0x60ffb0, void: 0x9040ff, water: 0x40a0ff }[kind] ?? 0xffd060;
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.soft, color, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }));
    glow.scale.set(1.3, 0.9, 1); group.add(glow);
    const core = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.star, color: 0xffffff, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }));
    core.scale.setScalar(0.7); group.add(core);
    if (kind === 'flare') {
      // a cone of torchlight
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.42, 1.2, 24, 1, true), new THREE.MeshBasicMaterial({ color: 0xfff4c0, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      cone.rotation.z = Math.PI / 2; cone.position.x = -0.35; group.add(cone);
    }
    if (kind.startsWith('item_')) {
      const col = { item_thermos: 0xd0d8e0, item_bomb: 0x222222, item_coin: 0xffcc33 }[kind];
      const m = new THREE.Mesh(kind === 'item_coin' ? new THREE.CylinderGeometry(0.15, 0.15, 0.04, 20) : kind === 'item_bomb' ? new THREE.SphereGeometry(0.18, 16, 12) : new THREE.CylinderGeometry(0.09, 0.09, 0.32, 16), new THREE.MeshStandardMaterial({ color: col, metalness: 0.6, roughness: 0.35 }));
      m.castShadow = true; group.clear(); group.add(m);
      if (kind === 'item_coin') m.rotation.x = Math.PI / 2;
      this.scene.add(group);
      return { group, update: (now) => { m.rotation.y = now * 3; }, color: null };
    }
    this.scene.add(group);
    return { group, color, update: (now) => { core.material.rotation = now * 6; glow.scale.set(1.3 + Math.sin(now * 30) * 0.08, 0.9, 1); } };
  }

  clear() {
    for (const v of this.projViews.values()) v.group.removeFromParent();
    this.projViews.clear();
    for (const o of this.sprites) o.s.removeFromParent();
    this.sprites = []; this.streaks = []; this.p.list = []; this.d.list = [];
  }
}
