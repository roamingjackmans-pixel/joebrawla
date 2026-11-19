// Stamps a deploy with its version and makes every file URL unique to that build.
//   node tools/stamp-build.mjs <public dir> <commit>
// Run by the games site's deploy on a throwaway copy of public/ (never commit the result).
// GitHub Pages lets browsers reuse files for ~10 minutes; with ?v=<commit> on every script, stylesheet and
// import, a new build is all-new URLs, so nobody mixes old and new code (which would break online play).
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const [dir = 'public', commitArg = 'dev'] = process.argv.slice(2);
const commit = String(commitArg).slice(0, 7);
const root = path.resolve(dir);
const pkg = JSON.parse(fs.readFileSync(path.join(root, '..', 'package.json'), 'utf8'));
const built = new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
const build = (() => {
  try { const n = execSync('git rev-list --count HEAD', { cwd: path.join(root, '..'), stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); if (/^\d+$/.test(n) && n !== '1') return n; } catch { /* not a git checkout */ }
  return /^\d+$/.test(process.env.GITHUB_RUN_NUMBER || '') ? process.env.GITHUB_RUN_NUMBER : null;
})();
const [maj = '1', min = '0', patch = '0'] = String(pkg.version).split('.');
const info = { version: `${maj}.${min}.${build ?? patch}`, commit, built };
fs.writeFileSync(path.join(root, 'version.js'), `// Build stamp (written at deploy time).\nwindow.JB_VERSION = ${JSON.stringify(info)};\n`);
fs.writeFileSync(path.join(root, 'version.json'), JSON.stringify(info) + '\n');

const indexPath = path.join(root, 'index.html');
let html = fs.readFileSync(indexPath, 'utf8');
let n = 0;
html = html.replace(/(<(?:script|link)\b[^>]*?\s(?:src|href)=")((?!https?:|data:|\/\/)[^"?#]+\.(?:js|css))(")/g, (m, a, url, b) => { n++; return `${a}${url}?v=${commit}${b}`; });
fs.writeFileSync(indexPath, html);

// every ES module import in js/ and shared/ (recursively), static and dynamic
let m = 0;
const walk = (d) => {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) { walk(p); continue; }
    if (!e.name.endsWith('.js')) continue;
    const src = fs.readFileSync(p, 'utf8');
    const out = src.replace(/((?:\bfrom|\bimport)\s*\(?\s*['"])(\.{1,2}\/[^'"?]+\.js)(['"])/g, (all, a, url, b) => { m++; return `${a}${url}?v=${commit}${b}`; });
    if (out !== src) fs.writeFileSync(p, out);
  }
};
for (const sub of ['js', 'shared']) if (fs.existsSync(path.join(root, sub))) walk(path.join(root, sub));
// the developer-only pages and test model don't ship
for (const f of ['proto.html', 'dev', 'assets/fighters/mannequin.glb']) fs.rmSync(path.join(root, f), { recursive: true, force: true });
console.log(`stamped v${info.version} (${commit}) · ${n} page assets · ${m} imports`);
