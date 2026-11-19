// Load the shipped fighter GLB in three.js (Node, textures stripped), drive it with the game's UAL clip pack and
// report the skinned bounds (height, foot level, reach) per clip -> proves the rig plays correctly in the engine.
//   node art/fighters/<id>/three_check.mjs <id> [clip:time ...]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });

async function bare(file) {
  const doc = await io.read(file);
  for (const t of doc.getRoot().listTextures()) t.dispose();
  for (const e of doc.getRoot().listExtensionsUsed()) if (/meshopt|texture_webp|texture_basisu/i.test(e.extensionName)) e.dispose();
  const bin = await io.writeBinary(doc);
  return bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.byteLength);
}
const parse = (buf) => new Promise((res, rej) => new GLTFLoader().parse(buf, '', res, rej));

const id = process.argv[2] || 'ignatius';
const fighter = await parse(await bare(path.join(root, 'public/assets/fighters', id + '.glb')));
const anims = await parse(await bare(path.join(root, 'public/assets/anim/test.glb')));
const scene = fighter.scene;
const meshes = [];
scene.traverse((o) => { if (o.isSkinnedMesh) meshes.push(o); });
const clips = Object.fromEntries(anims.animations.map((c) => [c.name, c]));
const mixer = new THREE.AnimationMixer(scene);

function bounds() {
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3();
  const v = new THREE.Vector3();
  for (const m of meshes) {
    m.skeleton.update();
    const pos = m.geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 3) {
      m.getVertexPosition(i, v);
      v.applyMatrix4(m.matrixWorld);
      box.expandByPoint(v);
    }
  }
  return box;
}
const fmt = (b) => `y ${b.min.y.toFixed(3)}..${b.max.y.toFixed(3)}  x ${b.min.x.toFixed(2)}..${b.max.x.toFixed(2)}  z ${b.min.z.toFixed(2)}..${b.max.z.toFixed(2)}`;
console.log('rest      ', fmt(bounds()));
const want = process.argv.slice(3).length ? process.argv.slice(3) :
  ['Idle_Loop:0.3', 'Punch_Cross:0.37', 'Sword_Regular_Combo:1.2', 'Crouch_Idle_Loop:0.3', 'Jump_Loop:0.3', 'Hit_Knockback:0.4', 'Spell_Simple_Shoot:0.4'];
for (const w of want) {
  const [name, t] = w.split(':');
  const clip = clips[name];
  if (!clip) { console.log('missing clip', name); continue; }
  mixer.stopAllAction();
  const a = mixer.clipAction(clip);
  a.reset().play();
  mixer.setTime(+t);
  console.log(name.padEnd(22), fmt(bounds()));
}
