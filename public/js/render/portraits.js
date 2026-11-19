// Character-select portraits, rendered from each fighter's own 3D model (head and shoulders, studio light),
// cached for the session. getPortrait(id) -> Promise<dataURL>.
import * as THREE from '../../vendor/three.bundle.js';
import { FighterView } from './fighterView.js';
import { FIGHTERS } from '../../shared/fighters/index.js';

const cache = new Map();
let rig = null;
let queue = Promise.resolve();

function setup(renderer) {
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xdde6ff, 0x302418, 1.1));
  const key = new THREE.DirectionalLight(0xffe2c0, 3.2); key.position.set(1.5, 2.5, 3); scene.add(key);
  const rim = new THREE.DirectionalLight(0x6fb4ff, 3.5); rim.position.set(-2.5, 2, -2.5); scene.add(rim);
  const rim2 = new THREE.DirectionalLight(0xff8a40, 2.2); rim2.position.set(2.5, 1.5, -2.5); scene.add(rim2);
  const cam = new THREE.PerspectiveCamera(24, 0.8, 0.05, 50);
  const target = new THREE.WebGLRenderTarget(240, 300, { samples: 4 });
  target.texture.colorSpace = THREE.SRGBColorSpace;
  rig = { renderer, scene, cam, target };
}

export function getPortrait(id, renderer) {
  if (cache.has(id)) return cache.get(id);
  const p = (queue = queue.then(() => make(id, renderer)).catch(() => null));
  cache.set(id, p);
  return p;
}

async function make(id, renderer) {
  if (!rig) setup(renderer);
  const v = await FighterView.create(id, FIGHTERS[id], 0);
  rig.scene.add(v.holder);
  const st = { i: 0, act: 'idle', t: 30, x: 0, y: 0, vx: 0, vy: 0, face: 1, move: null, mf: 0, overtime: false, guard: false, jumpDir: 0, hp: 1 };
  v.update(st, st, 1, 1, { phase: 'menu', dt60: 1 });
  v.holder.rotation.y = Math.PI / 2 - 0.55; // three-quarter view
  v.holder.updateMatrixWorld(true);
  const head = v.rig.worldPos('Head');
  const look = head.clone(); look.y -= 0.08;
  rig.cam.position.set(head.x + 0.95, head.y + 0.08, head.z + 1.35);
  rig.cam.lookAt(look);
  const r = rig.renderer;
  const prevT = r.getRenderTarget(), prevTone = r.toneMapping;
  r.setRenderTarget(rig.target);
  r.setClearColor(0x000000, 0);
  r.clear();
  r.render(rig.scene, rig.cam);
  const W = 240, H = 300, px = new Uint8Array(W * H * 4);
  r.readRenderTargetPixels(rig.target, 0, 0, W, H, px);
  r.setRenderTarget(prevT); r.toneMapping = prevTone;
  rig.scene.remove(v.holder);
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d');
  const img = g.createImageData(W, H);
  for (let y = 0; y < H; y++) img.data.set(px.subarray((H - 1 - y) * W * 4, (H - y) * W * 4), y * W * 4);
  // background: a warm gradient so cut-outs pop
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#3a2a1c'); bg.addColorStop(1, '#0c0d12');
  g.fillStyle = bg; g.fillRect(0, 0, W, H);
  const tmp = document.createElement('canvas'); tmp.width = W; tmp.height = H; tmp.getContext('2d').putImageData(img, 0, 0);
  g.drawImage(tmp, 0, 0);
  return c.toDataURL('image/jpeg', 0.85);
}
