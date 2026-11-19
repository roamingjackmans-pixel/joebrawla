// Copy UAL clips onto a fighter GLB (by joint name), exactly as the game's anim packs do (tools/assets.mjs anims):
// rotations on every joint, translation only on root / pelvis, no scale. The result is what three.js plays, so
// Blender previews and clip checks can import it and see the same poses.
//
//   node posed.mjs <fighter.glb> <out.glb> <src.glb>:Clip,Clip ...
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });

const [fighter, out, ...specs] = process.argv.slice(2);
const doc = await io.read(fighter);
const root = doc.getRoot();
for (const a of root.listAnimations()) a.dispose();
const byName = new Map(root.listNodes().map(n => [n.getName(), n]));
const buf = root.listBuffers()[0];
let n = 0;
for (const spec of specs) {
  const m = spec.match(/^(.*\.glb):(.+)$/i);
  if (!m) throw new Error('bad spec ' + spec);
  const src = await io.read(m[1]);
  const want = new Set(m[2].split(','));
  for (const a of src.getRoot().listAnimations()) {
    const nm = a.getName();
    const short = nm.replace(/_Loop$/, '');
    if (!want.has(nm) && !want.has(short)) continue;
    const clip = doc.createAnimation(short);
    for (const ch of a.listChannels()) {
      const bone = ch.getTargetNode()?.getName();
      const p = ch.getTargetPath();
      const target = byName.get(bone);
      if (!target) continue;
      if (p === 'scale' || p === 'weights') continue;
      if (p === 'translation' && bone !== 'root' && bone !== 'pelvis') continue;
      const s = ch.getSampler();
      const input = doc.createAccessor().setType('SCALAR').setArray(s.getInput().getArray().slice()).setBuffer(buf);
      const output = doc.createAccessor().setType(s.getOutput().getType()).setArray(s.getOutput().getArray().slice()).setBuffer(buf);
      const sampler = doc.createAnimationSampler().setInput(input).setOutput(output).setInterpolation(s.getInterpolation());
      clip.addSampler(sampler);
      clip.addChannel(doc.createAnimationChannel().setTargetNode(target).setTargetPath(p).setSampler(sampler));
    }
    n++;
    console.log('clip', short, clip.listChannels().length, 'channels');
  }
}
await io.write(out, doc);
console.log('wrote', out, n, 'clips');
