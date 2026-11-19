// JoeBrawla asset pipeline (needs `npm install`; never runs in CI).
//
//   node tools/assets.mjs fighter <src.glb> <id> [--tex 1024] [--keep-clips]
//       -> public/assets/fighters/<id>.glb : textures resized + WebP, meshopt-compressed, clips dropped
//          (fighters are animated from the shared clip packs) unless --keep-clips.
//   node tools/assets.mjs anims <out-name> <src.glb>[:Clip,Clip|*] ...
//       -> public/assets/anim/<out-name>.glb : skeleton + the named clips only (no meshes), resampled,
//          translation kept only on root/pelvis, scale tracks dropped, meshopt-compressed.
//          A clip can be renamed with Old=New. Sources must use the UAL bone names.
//   node tools/assets.mjs prop <src.glb> <out path under public/assets> [--tex 1024]
//       -> a static model (stage pieces), same compression as fighters.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { resample, prune, dedup, textureCompress, meshopt, weld } from '@gltf-transform/functions';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
import sharp from 'sharp';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
await MeshoptDecoder.ready;
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder,
});

const args = process.argv.slice(2);
const cmd = args.shift();
const flag = (name, def) => { const i = args.indexOf(name); if (i < 0) return def; const v = args[i + 1]; args.splice(i, 2); return v; };
const bool = (name) => { const i = args.indexOf(name); if (i < 0) return false; args.splice(i, 1); return true; };
const kb = (f) => (fs.statSync(f).size / 1024).toFixed(0) + ' KB';

async function finishModel(doc, out, tex) {
  await doc.transform(
    dedup(), prune(),
    textureCompress({ encoder: sharp, targetFormat: 'webp', resize: [tex, tex], quality: 86 }),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
  );
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await io.write(out, doc);
  console.log('wrote', path.relative(root, out), kb(out));
}

if (cmd === 'fighter' || cmd === 'prop') {
  const tex = +flag('--tex', 1024);
  const keep = bool('--keep-clips');
  const [src, id] = args;
  const doc = await io.read(src);
  if (!keep) for (const a of doc.getRoot().listAnimations()) a.dispose();
  const out = cmd === 'fighter' ? path.join(root, 'public/assets/fighters', id + '.glb') : path.join(root, 'public/assets', id);
  await finishModel(doc, out, tex);
} else if (cmd === 'anims') {
  const [name, ...specs] = args;
  let base = null;
  const byName = new Map();
  const seen = new Set();
  for (const spec of specs) {
    const m = spec.match(/^(.*\.glb)(?::(.+))?$/i);
    if (!m) throw new Error('bad source ' + spec);
    const [, file, list] = m;
    const want = !list || list === '*' ? null : new Map(list.split(',').map(s => { const [a, b] = s.split('='); return [a.trim(), (b || a).trim()]; }));
    const doc = await io.read(file);
    if (!base) {
      base = doc;
      for (const n of base.getRoot().listNodes()) byName.set(n.getName(), n);
      for (const n of base.getRoot().listNodes()) { n.setMesh(null); n.setSkin(null); }
      for (const a of base.getRoot().listAnimations()) {
        const nm = a.getName();
        if (want && !want.has(nm)) { a.dispose(); continue; }
        if (want) a.setName(want.get(nm));
        seen.add(a.getName());
      }
      continue;
    }
    // copy the wanted clips from this source onto the base skeleton, matching bones by name
    for (const a of doc.getRoot().listAnimations()) {
      const nm = a.getName();
      if (want && !want.has(nm)) continue;
      const outName = want ? want.get(nm) : nm;
      if (seen.has(outName)) { console.warn('duplicate clip', outName, 'skipped'); continue; }
      seen.add(outName);
      const clip = base.createAnimation(outName);
      for (const ch of a.listChannels()) {
        const target = byName.get(ch.getTargetNode()?.getName());
        if (!target) continue;
        const s = ch.getSampler();
        const input = base.createAccessor().setType('SCALAR').setArray(s.getInput().getArray().slice());
        const output = base.createAccessor().setType(s.getOutput().getType()).setArray(s.getOutput().getArray().slice());
        const sampler = base.createAnimationSampler().setInput(input).setOutput(output).setInterpolation(s.getInterpolation());
        clip.addSampler(sampler);
        clip.addChannel(base.createAnimationChannel().setTargetNode(target).setTargetPath(ch.getTargetPath()).setSampler(sampler));
      }
    }
  }
  // drop tracks the fighters must not inherit: scale everywhere, translation below the pelvis
  for (const a of base.getRoot().listAnimations()) {
    for (const ch of a.listChannels()) {
      const p = ch.getTargetPath();
      const bone = ch.getTargetNode()?.getName();
      if (p === 'scale' || (p === 'translation' && bone !== 'root' && bone !== 'pelvis') || p === 'weights') {
        const s = ch.getSampler(); ch.dispose(); s.dispose();
      }
    }
  }
  await base.transform(resample({ tolerance: 0.0005 }), dedup(), prune({ keepLeaves: true, keepAttributes: false }),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' }));
  const out = path.join(root, 'public/assets/anim', name + '.glb');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await io.write(out, base);
  console.log('wrote', path.relative(root, out), kb(out), base.getRoot().listAnimations().length, 'clips');
} else {
  console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').filter(l => l.startsWith('//')).join('\n'));
}
