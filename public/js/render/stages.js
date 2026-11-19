// Stages: each builds a lit 3D set around the fighting line (fighters on z = 0, walls at x = ±7.5 m, camera
// at z ≈ 7–11 m looking toward -z). A stage may load a GLB set from assets/stages/<id>.glb and dress it;
// until those exist, every realm has a procedural set here. docs/DESIGN.md §7.
import * as THREE from '../../vendor/three.bundle.js';
import { loadGLB } from './fighterView.js';

export const STAGES = [
  { id: 'crypt', name: 'The Mossy Crypt', realm: 'B1', blurb: 'A graveyard valley in the morning sun.' },
  { id: 'hollows', name: 'The Fungal Hollows', realm: 'B2', blurb: 'A glowing sinkhole cave open to the sky.' },
  { id: 'drowned', name: 'The Drowned Quarter', realm: 'B3', blurb: 'A flooded old city in the rain.' },
  { id: 'forest', name: 'The Hollow Forest', realm: 'B4', blurb: 'Autumn at golden hour.' },
  { id: 'forge', name: 'The Ashen Forge', realm: 'B5', blurb: 'A volcanic foundry at dusk.' },
  { id: 'reliquary', name: 'The Frozen Reliquary', realm: 'B6', blurb: 'A mountain cathedral at noon.' },
  { id: 'citadel', name: 'The Clockwork Citadel', realm: 'B7', blurb: 'A brass sky-city above the clouds.' },
  { id: 'abyss', name: 'The Abyss', realm: 'B8', blurb: "The Landlord's desk, on a rock in the void." },
  { id: 'landing', name: 'The Landing', realm: 'Hub', blurb: 'The residents’ sunny courtyard.' },
  { id: 'basement', name: 'Building Nine Basement', realm: 'Top', blurb: 'The breaker box. Flickering bulbs.' },
  { id: 'training', name: 'The Training Hall', realm: 'Orientation', blurb: "Management's orientation room.", hidden: true },
];

// ---------------------------------------------------------------- helpers

function skyDome(top, mid, bottom, sunDir, sunCol, opts = {}) {
  const g = new THREE.SphereGeometry(180, 32, 16);
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { top: { value: new THREE.Color(top) }, mid: { value: new THREE.Color(mid) }, bottom: { value: new THREE.Color(bottom) }, sunDir: { value: sunDir.clone().normalize() }, sunCol: { value: new THREE.Color(sunCol) }, stars: { value: opts.stars || 0 }, time: { value: 0 } },
    vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: `uniform vec3 top, mid, bottom, sunCol, sunDir; uniform float stars, time; varying vec3 vD;
      float h(vec3 p){ return fract(sin(dot(p, vec3(12.9898,78.233,45.164))) * 43758.5453); }
      void main(){
        float y = vD.y;
        vec3 c = y > 0.0 ? mix(mid, top, pow(y, 0.6)) : mix(mid, bottom, pow(-y, 0.5));
        float s = max(dot(vD, sunDir), 0.0);
        c += sunCol * (pow(s, 400.0) * 3.0 + pow(s, 12.0) * 0.35);
        if (stars > 0.0) { vec3 q = floor(vD * 300.0); float st = step(0.997, h(q)); c += vec3(st) * stars * (0.6 + 0.4 * sin(time * 2.0 + h(q) * 30.0)); }
        gl_FragColor = vec4(c, 1.0);
      }`,
  });
  const mesh = new THREE.Mesh(g, m); mesh.renderOrder = -10; mesh.frustumCulled = false;
  return mesh;
}

function noiseCanvas(size, fn) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d'); const img = g.createImageData(size, size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) { const [r, gg, b] = fn(x / size, y / size); const i = (y * size + x) * 4; img.data[i] = r; img.data[i + 1] = gg; img.data[i + 2] = b; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0);
  return c;
}
function vnoise(x, y, s) {
  const h = (a, b) => { const n = Math.sin(a * 127.1 + b * 311.7) * 43758.5453; return n - Math.floor(n); };
  x *= s; y *= s; const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = h(xi % s, yi % s), b = h((xi + 1) % s, yi % s), c = h(xi % s, (yi + 1) % s), d = h((xi + 1) % s, (yi + 1) % s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y) { let t = 0, a = 0.5, f = 4; for (let i = 0; i < 5; i++) { t += vnoise(x, y, f) * a; a *= 0.5; f *= 2; } return t; }

function groundTexture(colA, colB, colC, opts = {}) {
  const A = new THREE.Color(colA), B = new THREE.Color(colB), C = new THREE.Color(colC);
  const canvas = noiseCanvas(512, (x, y) => {
    const n = fbm(x, y), m = fbm(x + 3.1, y + 7.7);
    let col = A.clone().lerp(B, n);
    if (m > 0.55) col.lerp(C, Math.min(1, (m - 0.55) * 3));
    if (opts.tiles) { const tx = (x * opts.tiles) % 1, ty = (y * opts.tiles) % 1; const edge = Math.min(tx, ty, 1 - tx, 1 - ty); if (edge < 0.03) col.multiplyScalar(0.55); }
    return [col.r * 255, col.g * 255, col.b * 255];
  });
  const t = new THREE.CanvasTexture(canvas);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}

function ground(tex, rough = 0.92, size = [80, 60], repeat = [10, 7.5]) {
  tex.repeat.set(repeat[0], repeat[1]);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size[0], size[1], 1, 1), new THREE.MeshStandardMaterial({ map: tex, roughness: rough, metalness: 0 }));
  m.rotation.x = -Math.PI / 2; m.position.z = -size[1] / 2 + 12; m.receiveShadow = true;
  return m;
}

function lights(group, o) {
  const hemi = new THREE.HemisphereLight(o.sky ?? 0xbcd0ff, o.groundCol ?? 0x403020, o.hemi ?? 0.55);
  group.add(hemi);
  const sun = new THREE.DirectionalLight(o.sunCol ?? 0xfff0dd, o.sun ?? 2.6);
  sun.position.set(...(o.sunPos || [5, 9, 7]));
  sun.castShadow = true;
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03;
  Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 6, bottom: -2, near: 1, far: 40 });
  group.add(sun); group.add(sun.target);
  const rimA = new THREE.DirectionalLight(o.rimA ?? 0x6fb4ff, o.rimAI ?? 2.0); rimA.position.set(-7, 4, -6); group.add(rimA);
  const rimB = new THREE.DirectionalLight(o.rimB ?? 0xffa060, o.rimBI ?? 1.6); rimB.position.set(7, 3, -6); group.add(rimB);
  const fill = new THREE.DirectionalLight(o.fill ?? 0xffffff, o.fillI ?? 0.35); fill.position.set(0, 2, 10); group.add(fill);
  return { sun, hemi, rimA, rimB };
}

function envFrom(renderer, sky) {
  const pm = new THREE.PMREMGenerator(renderer);
  const s = new THREE.Scene(); s.add(sky.clone());
  const tex = pm.fromScene(s, 0.02).texture;
  pm.dispose();
  return tex;
}

function rand(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

/** low hills as a jagged band far behind */
function ridge(color, z, height, seed, opts = {}) {
  const r = rand(seed);
  const w = opts.width || 220, n = 60;
  const shape = new THREE.Shape();
  shape.moveTo(-w / 2, -2);
  for (let i = 0; i <= n; i++) { const x = -w / 2 + (w * i) / n; shape.lineTo(x, height * (0.45 + 0.55 * Math.abs(Math.sin(i * 0.37 + seed)) * (0.6 + 0.4 * r()))); }
  shape.lineTo(w / 2, -2);
  const m = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({ color, fog: true }));
  m.position.set(0, 0, z);
  return m;
}

function motes(group, color, n = 120, area = [24, 6, 14], size = 0.06, opts = {}) {
  const g = new THREE.BufferGeometry();
  const P = new Float32Array(n * 3), seeds = new Float32Array(n);
  for (let i = 0; i < n; i++) { P[i * 3] = (Math.random() - 0.5) * area[0]; P[i * 3 + 1] = Math.random() * area[1]; P[i * 3 + 2] = -Math.random() * area[2] + 2; seeds[i] = Math.random() * 100; }
  g.setAttribute('position', new THREE.BufferAttribute(P, 3));
  g.setAttribute('seed', new THREE.BufferAttribute(seeds, 1));
  const m = new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 }, col: { value: new THREE.Color(color) }, size: { value: size * 600 }, fall: { value: opts.fall || 0 }, hgt: { value: area[1] } },
    vertexShader: `attribute float seed; uniform float time, size, fall, hgt; varying float vA;
      void main(){ vec3 p = position; p.x += sin(time * 0.4 + seed) * 0.6; p.y = mod(p.y - time * fall + sin(time * 0.7 + seed) * 0.3, hgt); p.z += cos(time * 0.3 + seed) * 0.4;
        vA = 0.5 + 0.5 * sin(time * 2.0 + seed * 3.0); vec4 mv = modelViewMatrix * vec4(p,1.0); gl_PointSize = size / -mv.z; gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 col; varying float vA; void main(){ float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard; gl_FragColor = vec4(col, (1.0 - d * 2.0) * vA); }`,
    transparent: true, depthWrite: false, blending: opts.normal ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
  const pts = new THREE.Points(g, m); pts.frustumCulled = false;
  group.add(pts);
  return m;
}

function std(color, rough = 0.85, metal = 0, extra = {}) { return new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal, ...extra }); }

function scatter(group, n, seed, make, area) {
  const r = rand(seed);
  for (let i = 0; i < n; i++) {
    const x = area.x[0] + r() * (area.x[1] - area.x[0]);
    const z = area.z[0] + r() * (area.z[1] - area.z[0]);
    if (Math.abs(z) < 1.6 && Math.abs(x) < 8.5) continue; // keep the fighting line clear
    const o = make(r, x, z);
    if (o) group.add(o);
  }
}

function tree(r, x, z, trunkCol, leafCols, h = 6) {
  const g = new THREE.Group();
  const th = h * (0.7 + r() * 0.6);
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12 * th / 5, 0.25 * th / 5, th * 0.5, 7), std(trunkCol, 0.95));
  trunk.position.y = th * 0.25; trunk.castShadow = true; g.add(trunk);
  const col = leafCols[Math.floor(r() * leafCols.length)];
  for (let k = 0; k < 3; k++) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(th * (0.32 - k * 0.07), th * 0.42, 8), std(col, 0.9, 0, { flatShading: true }));
    cone.position.y = th * (0.42 + k * 0.17); cone.castShadow = true; g.add(cone);
  }
  g.position.set(x, 0, z); g.rotation.y = r() * 6;
  return g;
}

function gravestone(r, x, z) {
  const g = new THREE.Group();
  const kind = r();
  const mat = std(new THREE.Color().setHSL(0.25, 0.08, 0.32 + r() * 0.15), 0.95);
  let m;
  if (kind < 0.5) { m = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.9, 0.16), mat); m.position.y = 0.45; const top = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.16, 16, 1, false, 0, Math.PI), mat); top.rotation.set(Math.PI / 2, 0, Math.PI / 2); top.position.y = 0.9; g.add(top); }
  else if (kind < 0.8) { m = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.1, 0.14), mat); m.position.y = 0.55; const bar = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.14, 0.14), mat); bar.position.y = 0.8; g.add(bar); }
  else { m = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.6, 0.5), mat); m.position.y = 0.8; const cap = new THREE.Mesh(new THREE.ConeGeometry(0.4, 0.5, 4), mat); cap.position.y = 1.85; cap.rotation.y = Math.PI / 4; g.add(cap); }
  g.add(m);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.position.set(x, 0, z); g.rotation.set((r() - 0.5) * 0.2, (r() - 0.5) * 0.6, (r() - 0.5) * 0.15);
  return g;
}

function rock(r, x, z, col, s = 1) {
  const m = new THREE.Mesh(new THREE.DodecahedronGeometry((0.4 + r() * 1.2) * s, 0), std(col, 0.95, 0, { flatShading: true }));
  m.position.set(x, 0.2 * s, z); m.rotation.set(r() * 3, r() * 3, r() * 3); m.scale.y = 0.6; m.castShadow = true; m.receiveShadow = true;
  return m;
}

// ---------------------------------------------------------------- builders

const BUILD = {
  crypt(renderer) {
    const group = new THREE.Group();
    const sunDir = new THREE.Vector3(0.5, 0.35, -1);
    const sky = skyDome(0x6aa2d8, 0xcfe0e8, 0x8aa090, sunDir, 0xfff2d0);
    group.add(sky);
    const L = lights(group, { sunCol: 0xffecd0, sun: 2.8, sunPos: [6, 8, 6], hemi: 0.6, sky: 0xcfe4ff, groundCol: 0x4a5a30, rimA: 0x9fd0ff, rimB: 0xffc080 });
    group.add(ground(groundTexture(0x4b6a2c, 0x6f8a3a, 0x5a4a32)));
    // a dirt path along the fighting line
    const path = new THREE.Mesh(new THREE.PlaneGeometry(40, 3.2), std(0x6b5638, 1, 0, { map: groundTexture(0x6b5638, 0x857050, 0x4f4030) }));
    path.material.map.repeat.set(8, 1); path.rotation.x = -Math.PI / 2; path.position.set(0, 0.01, 0); path.receiveShadow = true; group.add(path);
    group.add(ridge(0x6f8fa0, -90, 22, 3), ridge(0x597a62, -60, 14, 7), ridge(0x4a6a40, -38, 7, 11));
    scatter(group, 40, 5, (r, x, z) => tree(r, x, z, 0x4a3524, [0x2f5a2a, 0x3d6a30, 0x355e38], 7), { x: [-34, 34], z: [-34, -9] });
    scatter(group, 36, 9, (r, x, z) => gravestone(r, x, z), { x: [-16, 16], z: [-8, -2.2] });
    scatter(group, 16, 17, (r, x, z) => rock(r, x, z, 0x6a7060), { x: [-24, 24], z: [-20, -3] });
    // ruined arch behind the fight
    const arch = new THREE.Group(); const stone = std(0x8a8f86, 0.92);
    for (const sx of [-2.2, 2.2]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.9, 4.6, 0.9), stone); p.position.set(sx, 2.3, 0); p.castShadow = true; arch.add(p); }
    const top = new THREE.Mesh(new THREE.BoxGeometry(5.6, 0.8, 1.0), stone); top.position.y = 4.9; top.rotation.z = 0.04; arch.add(top);
    arch.position.set(-3, 0, -12); arch.rotation.y = 0.15; group.add(arch);
    const motesM = motes(group, 0xfff4c0, 140, [30, 6, 16], 0.05);
    const fog = new THREE.Fog(0xc9dbe0, 18, 95);
    return { group, sky, sun: L.sun, fog, env: envFrom(renderer, sky), envIntensity: 0.7, bloom: [0.35, 0.86], update: (t) => { motesM.uniforms.time.value = t; } };
  },

  basement(renderer) {
    const group = new THREE.Group();
    const sky = skyDome(0x0a0a0c, 0x16140f, 0x0a0908, new THREE.Vector3(0, 1, 0), 0x000000);
    group.add(sky);
    const L = lights(group, { sunCol: 0xffd9a0, sun: 1.6, sunPos: [2, 9, 5], hemi: 0.25, sky: 0x6a5a40, groundCol: 0x101010, rimA: 0x5aa0ff, rimAI: 2.4, rimB: 0xff9040, rimBI: 1.8 });
    group.add(ground(groundTexture(0x4a4844, 0x5c5a55, 0x3a3835, { tiles: 4 }), 0.75));
    const wallMat = std(0x6a5f52, 0.9, 0, { map: groundTexture(0x6a5f52, 0x7a6e5e, 0x55493d, { tiles: 6 }) });
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(60, 14), wallMat); wall.position.set(0, 7, -7); wall.receiveShadow = true; group.add(wall);
    // pipes along the wall
    const pipeMat = std(0x8a6a40, 0.4, 0.8);
    for (let k = 0; k < 4; k++) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.12 + k * 0.03, 0.12 + k * 0.03, 60, 12), pipeMat); p.rotation.z = Math.PI / 2; p.position.set(0, 4.2 + k * 0.45, -6.6 + k * 0.05); p.castShadow = true; group.add(p); }
    // the breaker box
    const box = new THREE.Mesh(new THREE.BoxGeometry(1.4, 2, 0.3), std(0x5a6a70, 0.5, 0.7)); box.position.set(1.5, 2.4, -6.7); group.add(box);
    const lever = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.5, 0.12), std(0xaa2222, 0.4, 0.3)); lever.position.set(1.5, 2.4, -6.45); group.add(lever);
    // hanging bulbs that flicker
    const bulbs = [];
    for (const bx of [-6, -1, 4, 9]) {
      const l = new THREE.PointLight(0xffc070, 18, 12, 2); l.position.set(bx, 4.6, -2.5); group.add(l);
      const glow = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffe0a0 })); glow.position.copy(l.position); group.add(glow);
      const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 3), std(0x111111)); cord.position.set(bx, 6.2, -2.5); group.add(cord);
      bulbs.push({ l, glow, seed: Math.random() * 10 });
    }
    const dust = motes(group, 0xffe8c0, 160, [30, 6, 10], 0.035, { fall: 0.05 });
    const fog = new THREE.Fog(0x15120e, 10, 40);
    return { group, sky, sun: L.sun, fog, env: envFrom(renderer, sky), envIntensity: 0.25, bloom: [0.6, 0.75], grade: { sat: 1.0 },
      update: (t) => { dust.uniforms.time.value = t; for (const b of bulbs) { const f = Math.sin(t * 17 + b.seed) > 0.97 ? 0.2 : 1; b.l.intensity = 18 * f; b.glow.material.color.setScalar(f); } } };
  },
};

/** build a stage by id (procedural set, plus assets/stages/<id>.glb if it exists) */
export async function buildStage(id, renderer) {
  const make = BUILD[id] || BUILD.crypt;
  const st = make(renderer);
  try {
    const g = await loadGLB(`assets/stages/${id}.glb`);
    const set = g.scene.clone();
    set.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; o.castShadow = !o.name.includes('noshadow'); } });
    st.group.add(set);
    st.hasSet = true;
  } catch { /* procedural only */ }
  st.id = id;
  return st;
}
