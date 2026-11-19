// node cmp_rest.mjs a.gl(t|b) b.gl(t|b)  -> compares rest TRS of same-named nodes (JSON only, no resources)
import fs from 'node:fs';
function nodes(f) {
  const buf = fs.readFileSync(f);
  let json;
  if (f.toLowerCase().endsWith('.gltf')) json = JSON.parse(buf.toString('utf8'));
  else { const len = buf.readUInt32LE(12); json = JSON.parse(buf.subarray(20, 20 + len).toString('utf8')); }
  return Object.fromEntries(json.nodes.map(n => [n.name, n]));
}
const [fa, fb] = process.argv.slice(2);
const ma = nodes(fa), mb = nodes(fb);
let worst = 0, wn = '', tw = 0, twn = '';
for (const [k, na] of Object.entries(ma)) {
  const nb = mb[k]; if (!nb) continue;
  const ra = na.rotation || [0, 0, 0, 1], rb = nb.rotation || [0, 0, 0, 1];
  const dot = Math.abs(ra[0]*rb[0]+ra[1]*rb[1]+ra[2]*rb[2]+ra[3]*rb[3]);
  const ang = 2*Math.acos(Math.min(1,dot))*180/Math.PI;
  const ta = na.translation || [0, 0, 0], tb = nb.translation || [0, 0, 0];
  const dt = Math.hypot(ta[0]-tb[0], ta[1]-tb[1], ta[2]-tb[2]);
  if (process.argv.includes('-v') && (ang > 0.05 || dt > 1e-3)) console.log(k.padEnd(18), 'rot diff', ang.toFixed(3), 'deg  trans diff', dt.toFixed(4));
  if (ang > worst) { worst = ang; wn = k; }
  if (dt > tw) { tw = dt; twn = k; }
}
console.log('worst rot diff', worst.toFixed(4), wn, '| worst trans diff', tw.toFixed(4), twn, '| nodes', Object.keys(ma).length, Object.keys(mb).length);
