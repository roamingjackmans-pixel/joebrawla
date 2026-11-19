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

// ---------------------------------------------------------------- generic realms (until each stage's GLB arrives)
// palette and dressing per realm; a stage GLB + its stage.json replace the dressing and lighting
const REALM = {
  hollows: { sky: [0x1d3a4a, 0x2f6a6a, 0x0a1614], sun: [0xc8fff0, 1.6, [2, 10, 3]], hemi: [0x60ffd0, 0x201030, 0.5], rim: [0x40ffc0, 0xb060ff], fog: [0x123a3a, 14, 70], ground: [0x2a2a3a, 0x3a3050, 0x204040], parts: ['spores', 0x60ffc0], props: 'mushroom', bloom: [0.7, 0.7] },
  drowned: { sky: [0x22304a, 0x5a6a80, 0x1a2228], sun: [0xffd0a0, 1.8, [-6, 6, 4]], hemi: [0x8090b0, 0x102030, 0.55], rim: [0x60a0ff, 0xffa060], fog: [0x3a4a5a, 12, 60], ground: [0x2a3540, 0x3a4550, 0x1e2a30], parts: ['rain', 0xa0c0e0], props: 'ruins', water: true, bloom: [0.45, 0.8] },
  forest: { sky: [0x6a7aa8, 0xffb070, 0x5a3a20], sun: [0xffb060, 3.0, [-8, 4, 3]], hemi: [0xffd0a0, 0x402010, 0.6], rim: [0xffd080, 0xff6020], fog: [0xd09060, 16, 80], ground: [0x5a3a1a, 0x7a4a20, 0x3a2a10], parts: ['leaves', 0xff8030], props: 'autumn', bloom: [0.45, 0.8] },
  forge: { sky: [0x1a0a08, 0x5a1a08, 0x100604], sun: [0xff9050, 2.4, [4, 7, 5]], hemi: [0xff6020, 0x100808, 0.45], rim: [0xff4010, 0xffa040], fog: [0x2a0e06, 12, 60], ground: [0x2a2420, 0x3a3028, 0x1a1410], parts: ['embers', 0xff7020], props: 'forge', bloom: [0.8, 0.7] },
  reliquary: { sky: [0x6aa0e0, 0xdde8f4, 0xc0d0e0], sun: [0xffffff, 3.2, [3, 10, 6]], hemi: [0xe0f0ff, 0x8090a0, 0.8], rim: [0x80c0ff, 0xffe0a0], fog: [0xd8e4f0, 16, 80], ground: [0xdfe6ee, 0xc8d4e0, 0xffffff], parts: ['snow', 0xffffff], props: 'ice', bloom: [0.35, 0.85] },
  citadel: { sky: [0x3a6ab0, 0xf0d8b0, 0xfff0d0], sun: [0xfff0c0, 3.0, [6, 8, 4]], hemi: [0xfff0d0, 0x806040, 0.7], rim: [0xffd080, 0x80c0ff], fog: [0xf0e0c8, 20, 100], ground: [0x8a6a3a, 0xa8844a, 0x6a5030], parts: ['motes', 0xffe0a0], props: 'gears', bloom: [0.45, 0.8] },
  abyss: { sky: [0x05020c, 0x1a0830, 0x000000], sun: [0xc0a0ff, 1.8, [2, 9, 4]], hemi: [0x6040a0, 0x000000, 0.4], rim: [0x9040ff, 0x40c0ff], fog: [0x0a0418, 14, 90], ground: [0x2a2430, 0x3a3040, 0x1a1420], parts: ['stars', 0xc080ff], props: 'void', stars: 1, bloom: [0.8, 0.65] },
  landing: { sky: [0x7ab0e8, 0xf0ecd8, 0xc0b090], sun: [0xfff0d0, 3.0, [5, 9, 6]], hemi: [0xdde8ff, 0x605040, 0.65], rim: [0xa0d0ff, 0xffb070], fog: [0xe8e0d0, 18, 90], ground: [0x8a8070, 0x9a9080, 0x6a6050], tiles: 5, parts: ['motes', 0xfff4c0], props: 'courtyard', bloom: [0.35, 0.86] },
  training: { sky: [0x202024, 0x3a3a40, 0x18181a], sun: [0xffffff, 2.4, [0, 10, 6]], hemi: [0xffffff, 0x303030, 0.6], rim: [0x6fb4ff, 0xffa060], fog: [0x26262a, 14, 60], ground: [0x5a5a60, 0x66666e, 0x4a4a50], tiles: 8, parts: ['dust', 0xffffff], props: 'hall', bloom: [0.3, 0.88] },
};

function realmProps(group, kind, seed) {
  const rr = rand(seed);
  const add = (m, x, z, y = 0) => { m.position.set(x, y, z); m.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); group.add(m); };
  const ring = (n, fn) => { for (let i = 0; i < n; i++) { const x = (rr() - 0.5) * 60, z = -4 - rr() * 40; if (Math.abs(x) < 9 && z > -6) continue; fn(x, z, rr); } };
  if (kind === 'mushroom') ring(40, (x, z, q) => { const g = new THREE.Group(); const h = 1 + q() * 6; const st = new THREE.Mesh(new THREE.CylinderGeometry(0.15 * h / 3, 0.25 * h / 3, h, 10), std(0xd8c8b0)); st.position.y = h / 2; g.add(st); const teal = q() < 0.5; const cap = new THREE.Mesh(new THREE.SphereGeometry(h * 0.45, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), std(teal ? 0x40ffd0 : 0xa060ff, 0.5, 0, { emissive: teal ? 0x10a080 : 0x6020a0, emissiveIntensity: 1.2 })); cap.position.y = h; g.add(cap); add(g, x, z); });
  if (kind === 'ruins' || kind === 'courtyard' || kind === 'hall') ring(kind === 'hall' ? 10 : 26, (x, z, q) => { const h = 2 + q() * 7; const b = new THREE.Mesh(new THREE.BoxGeometry(1 + q() * 3, h, 1 + q() * 3), std(kind === 'ruins' ? 0x5a6470 : 0x9a9080, 0.9)); add(b, x, z, h / 2 - (kind === 'ruins' ? 0.8 : 0)); });
  if (kind === 'autumn') ring(46, (x, z, q) => add(tree(q, 0, 0, 0x3a2414, [0xd0601a, 0xe08a20, 0xb03a14, 0xf0b030], 8), x, z));
  if (kind === 'forge') ring(22, (x, z, q) => { const h = 4 + q() * 14; add(new THREE.Mesh(new THREE.CylinderGeometry(0.6 + q(), 1 + q(), h, 10), std(0x2a2420, 0.7, 0.4)), x, z, h / 2); if (q() < 0.4) add(new THREE.Mesh(new THREE.SphereGeometry(0.6, 12, 8), new THREE.MeshStandardMaterial({ color: 0xff5010, emissive: 0xff4000, emissiveIntensity: 3 })), x + 1.5, z, 0.3); });
  if (kind === 'ice') ring(30, (x, z, q) => { const h = 2 + q() * 8; add(new THREE.Mesh(new THREE.ConeGeometry(0.4 + q(), h, 6), std(0xcfe8ff, 0.15, 0.1, { transparent: true, opacity: 0.85, emissive: 0x204060, emissiveIntensity: 0.3 })), x, z, h / 2); });
  if (kind === 'gears') ring(18, (x, z, q) => { const R = 1 + q() * 4; const g = new THREE.Mesh(new THREE.TorusGeometry(R, 0.25 * R, 6, 16), std(0xc89a40, 0.35, 0.9)); g.name = 'anim_spin_z_' + Math.round(10 + q() * 30); add(g, x, z, R + 0.5); });
  if (kind === 'void') ring(30, (x, z, q) => { const m = new THREE.Mesh(new THREE.DodecahedronGeometry(0.5 + q() * 2.5, 0), std(0x3a3048, 0.9, 0, { flatShading: true })); m.name = 'anim_bob'; add(m, x, z, 2 + q() * 10); });
}

function particlesFor(group, type, color) {
  const T = {
    motes: [140, [30, 6, 16], 0.05, {}], spores: [220, [30, 7, 16], 0.06, { fall: -0.15 }], rain: [600, [30, 9, 14], 0.03, { fall: 6, normal: true }],
    leaves: [140, [30, 7, 16], 0.08, { fall: 0.5, normal: true }], embers: [220, [30, 8, 16], 0.05, { fall: -0.8 }], snow: [360, [30, 8, 16], 0.06, { fall: 0.6, normal: true }],
    dust: [120, [30, 6, 12], 0.03, { fall: 0.05 }], stars: [200, [40, 12, 20], 0.05, { fall: -0.05 }], ash: [220, [30, 8, 16], 0.05, { fall: 0.4, normal: true }],
  }[type] || [100, [30, 6, 16], 0.05, {}];
  return motes(group, color, T[0], T[1], T[2], T[3]);
}

const hex = (v) => (typeof v === 'string' ? new THREE.Color(v).getHex() : v);

function genericStage(renderer, R, opts = {}) {
  const group = new THREE.Group();
  const sunPos = R.sun[2] || [5, 9, 7];
  const sky = skyDome(hex(R.sky[0]), hex(R.sky[1]), hex(R.sky[2]), new THREE.Vector3(sunPos[0], Math.max(1, sunPos[1] * 0.3), sunPos[2] - 12), hex(R.sun[0]), { stars: R.stars || 0 });
  group.add(sky);
  const L = lights(group, { sunCol: hex(R.sun[0]), sun: R.sun[1], sunPos, sky: hex(R.hemi[0]), groundCol: hex(R.hemi[1]), hemi: R.hemi[2], rimA: hex(R.rim[0]), rimB: hex(R.rim[1]) });
  if (!opts.noGround) group.add(ground(groundTexture(hex(R.ground[0]), hex(R.ground[1]), hex(R.ground[2]), { tiles: R.tiles }), R.water ? 0.25 : 0.9));
  if (R.water && !opts.noGround) { const w = new THREE.Mesh(new THREE.PlaneGeometry(80, 60), new THREE.MeshStandardMaterial({ color: 0x203040, roughness: 0.05, metalness: 0.6, transparent: true, opacity: 0.55 })); w.rotation.x = -Math.PI / 2; w.position.set(0, 0.03, -18); w.receiveShadow = true; group.add(w); }
  if (!opts.noProps) { group.add(ridge(hex(R.fog[0]), -90, 26, 5), ridge(new THREE.Color(hex(R.fog[0])).multiplyScalar(0.8).getHex(), -60, 14, 9)); realmProps(group, R.props, 7); }
  const pm = R.parts ? particlesFor(group, R.parts[0], hex(R.parts[1])) : null;
  const fog = new THREE.Fog(hex(R.fog[0]), R.fog[1], R.fog[2]);
  return { group, sky, sun: L.sun, fog, env: envFrom(renderer, sky), envIntensity: R.env ?? 0.7, bloom: R.bloom, exposure: R.exposure, update: (t) => { if (pm) pm.uniforms.time.value = t; sky.material.uniforms.time.value = t; } };
}

/** stage.json (from the stage art) -> the same shape as REALM entries */
function fromJson(j) {
  return {
    sky: [j.sky?.top, j.sky?.mid, j.sky?.bottom].map((x) => x || '#888888'),
    sun: [j.sun?.color || '#ffffff', j.sun?.intensity ?? 2.6, j.sun?.dir ? j.sun.dir.map((v) => v * 10) : [5, 9, 7]],
    hemi: [j.hemi?.sky || '#bcd0ff', j.hemi?.ground || '#403020', j.hemi?.intensity ?? 0.55],
    rim: j.rim || ['#6fb4ff', '#ffa060'], fog: [j.fog?.color || '#888888', j.fog?.near ?? 18, j.fog?.far ?? 90],
    ground: ['#555555', '#666666', '#444444'], parts: j.particles ? [j.particles.type, j.particles.color] : null,
    bloom: j.bloom, exposure: j.exposure, stars: j.particles?.type === 'stars' ? 1 : 0,
  };
}

/** animate named nodes of a stage set: anim_spin_<axis>_<deg/s>, anim_bob, anim_sway, anim_flicker */
function nodeAnimator(set) {
  const list = [];
  set.traverse((o) => {
    const n = o.name || '';
    if (!n.startsWith('anim_')) return;
    const m = /anim_spin_([xyz])_(\d+)/.exec(n);
    list.push({ o, kind: m ? 'spin' : n.startsWith('anim_bob') ? 'bob' : n.startsWith('anim_sway') ? 'sway' : n.startsWith('anim_flicker') ? 'flicker' : '', axis: m?.[1], speed: m ? +m[2] : 0, y: o.position.y, r: o.rotation.clone(), seed: Math.random() * 10 });
  });
  return (t) => {
    for (const a of list) {
      if (a.kind === 'spin') a.o.rotation[a.axis] = a.r[a.axis] + t * a.speed * Math.PI / 180;
      else if (a.kind === 'bob') a.o.position.y = a.y + Math.sin(t * 0.8 + a.seed) * 0.25;
      else if (a.kind === 'sway') a.o.rotation.z = a.r.z + Math.sin(t * 0.9 + a.seed) * 0.05;
      else if (a.kind === 'flicker') a.o.traverse((m) => { if (m.material && m.material.emissive) m.material.emissiveIntensity = 1 + (Math.sin(t * 13 + a.seed) > 0.9 ? -0.7 : Math.sin(t * 3 + a.seed) * 0.2); });
    }
  };
}

/** build a stage by id: its GLB set + stage.json when they exist, else a procedural realm */
export async function buildStage(id, renderer) {
  let json = null;
  try { const r = await fetch(`assets/stages/${id}.json`); if (r.ok) json = await r.json(); } catch { /* none yet */ }
  let gltf = null;
  if (json) { try { gltf = await loadGLB(`assets/stages/${id}.glb`); } catch { /* none yet */ } }
  let st;
  const withAnim = (stage, root) => { const anim = nodeAnimator(root); const base = stage.update; stage.update = (t, dt, sc) => { base?.(t, dt, sc); anim(t); }; return stage; };
  if (gltf) {
    st = genericStage(renderer, fromJson(json), { noGround: true, noProps: true });
    const set = gltf.scene.clone();
    set.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; o.castShadow = !o.name.includes('noshadow'); } });
    st.group.add(set);
    withAnim(st, set);
    st.hasSet = true;
  } else if (BUILD[id]) st = BUILD[id](renderer);
  else if (REALM[id]) st = withAnim(genericStage(renderer, REALM[id]), new THREE.Group());
  else st = BUILD.crypt(renderer);
  if (REALM[id] && !gltf) { const anim = nodeAnimator(st.group); const base = st.update; st.update = (t, dt, sc) => { base?.(t, dt, sc); anim(t); }; }
  st.id = id;
  return st;
}
