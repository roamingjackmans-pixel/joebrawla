// node tools/inspect.mjs file.glb  -> scene tree, skins, materials, textures, clips
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
for (const f of process.argv.slice(2)) {
  const doc = await io.read(f);
  const root = doc.getRoot();
  console.log('==', f);
  const walk = (n, d) => { if (d > 3) return; const t = n.getTranslation().map(v => +v.toFixed(3)); const s = n.getScale().map(v => +v.toFixed(3)); console.log('  '.repeat(d) + n.getName(), n.getMesh() ? '[mesh]' : '', n.getSkin() ? '[skin]' : '', 't', t.join(','), 's', s.join(',')); if (n.getName() === 'root') return; for (const c of n.listChildren()) walk(c, d + 1); };
  for (const sc of root.listScenes()) for (const n of sc.listChildren()) walk(n, 0);
  console.log('materials', root.listMaterials().map(m => m.getName()).join(', '));
  console.log('textures', root.listTextures().map(t => `${t.getName()}:${t.getSize()?.join('x')}:${t.getMimeType()}`).join(', '));
  console.log('clips', root.listAnimations().map(a => a.getName()).join(', '));
}
