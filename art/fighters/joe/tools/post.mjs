// Post-process a fighter source GLB in place: base colour factors for the palette materials, then a report
// (triangles, materials, textures, joints, height).
//   node post.mjs <src.glb> '{"tint1_joe_shirt":"#3c3f44", ...}'
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
import fs from 'node:fs';
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const [file, json] = process.argv.slice(2);
const factors = json ? JSON.parse(json) : {};
const doc = await io.read(file);
const root = doc.getRoot();
const lin = (h) => { h = h.replace('#', ''); return [0, 2, 4].map(i => { const c = parseInt(h.slice(i, i + 2), 16) / 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }); };
for (const m of root.listMaterials()) {
  const f = factors[m.getName()];
  if (f) m.setBaseColorFactor([...lin(f), 1]);
}
await io.write(file, doc);
let tris = 0;
const perMat = {};
for (const mesh of root.listMeshes()) for (const p of mesh.listPrimitives()) {
  const n = p.getIndices() ? p.getIndices().getCount() / 3 : p.getAttribute('POSITION').getCount() / 3;
  tris += n;
  const mn = p.getMaterial()?.getName() || '-';
  perMat[mn] = (perMat[mn] || 0) + n;
}
const skin = root.listSkins()[0];
const joints = skin ? skin.listJoints().map(j => j.getName()) : [];
const arm = root.listNodes().find(n => n.getName() === 'Armature');
console.log(JSON.stringify({
  file, bytes: fs.statSync(file).size, tris, perMaterial: perMat,
  materials: root.listMaterials().map(m => ({ name: m.getName(), factor: m.getBaseColorFactor().map(v => +v.toFixed(3)), doubleSided: m.getDoubleSided(), emissive: m.getEmissiveTexture() ? 'tex' : null })),
  textures: root.listTextures().map(t => `${t.getName()} ${t.getSize()?.join('x')} ${t.getMimeType()}`),
  joints: joints.length, armatureScale: arm ? arm.getScale() : null,
  meshes: root.listNodes().filter(n => n.getMesh()).map(n => n.getName()),
}, null, 1));
