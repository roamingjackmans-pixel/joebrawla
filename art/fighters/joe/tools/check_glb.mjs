// Check a fighter GLB against the brief: 65 UAL joints by name, <= 6 materials, tint1_/tint2_ factors, no vertex
// colours, triangle count, textures.   node check_glb.mjs <file.glb> [ual.glb]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
import fs from 'node:fs';
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const [file, ual = 'C:/dev/AverageJoe/DungeonJoe3D/assets/thirdparty/quaternius/anim/UAL1_Standard.glb'] = process.argv.slice(2);
const doc = await io.read(file);
const root = doc.getRoot();
const ualDoc = await io.read(ual);
const ualJoints = ualDoc.getRoot().listSkins()[0].listJoints().map(j => j.getName());
const skins = root.listSkins();
const joints = new Set(skins.flatMap(s => s.listJoints().map(j => j.getName())));
const missing = ualJoints.filter(j => !joints.has(j));
let tris = 0;
const attrs = new Set();
for (const m of root.listMeshes()) for (const p of m.listPrimitives()) {
  tris += (p.getIndices() ? p.getIndices().getCount() : p.getAttribute('POSITION').getCount()) / 3;
  for (const s of p.listSemantics()) attrs.add(s);
}
const mats = root.listMaterials().map(m => {
  const es = m.getExtension('KHR_materials_emissive_strength');
  return `${m.getName()} factor=${m.getBaseColorFactor().map(v => v.toFixed(3)).join(',')}${m.getEmissiveTexture() ? ' emissive x' + (es ? es.getEmissiveStrength() : 1) : ''}`;
});
const arm = root.listNodes().find(n => n.getName() === 'Armature');
console.log(JSON.stringify({
  file, kb: Math.round(fs.statSync(file).size / 1024), tris, materials: mats.length, mats,
  ualJoints: ualJoints.length, missingJoints: missing, extraJoints: [...joints].filter(j => !ualJoints.includes(j)),
  vertexColours: [...attrs].filter(a => a.startsWith('COLOR')), attributes: [...attrs],
  textures: root.listTextures().map(t => `${t.getName() || '?'} ${t.getSize()?.join('x')} ${t.getMimeType()}`),
  armatureScale: arm ? arm.getScale().map(v => +v.toFixed(4)) : null,
}, null, 1));
