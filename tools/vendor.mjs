// Builds public/vendor/three.bundle.js (three.js + the addons in tools/three-entry.js, minified) and copies PeerJS.
//   node tools/vendor.mjs      (needs `npm install` for the dev dependencies)
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
await build({
  entryPoints: [path.join(root, 'tools/three-entry.js')],
  bundle: true, minify: true, format: 'esm', target: 'es2022',
  outfile: path.join(root, 'public/vendor/three.bundle.js'),
  legalComments: 'eof',
});
const peer = path.join(root, '../FriendSlop101/public/vendor/peerjs.min.js');
if (fs.existsSync(peer)) fs.copyFileSync(peer, path.join(root, 'public/vendor/peerjs.min.js'));
console.log('vendor ok', fs.statSync(path.join(root, 'public/vendor/three.bundle.js')).size);
