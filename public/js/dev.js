// Developer helpers (loaded with ?dev): freeze a fighter on any move frame and render contact sheets.
import * as THREE from '../vendor/three.bundle.js';

export function installDev(session) {
  const s = session;
  window.posePeek = (id, fr, who = 0) => {
    const st = s.match.state;
    const f = st.f[who];
    if (id.startsWith('s:')) { f.act = id.slice(2); f.move = null; f.t = fr; } else { f.act = 'move'; f.move = id; f.mf = fr; f.t = fr; }
    const v = s.views[who];
    v.anim.key = id.startsWith('s:') ? id : 'm:' + id; v.anim.fade = 0;
    s.prev = structuredClone(st);
    for (let k = 0; k < 3; k++) s.scene.render(st, s.prev, 1, performance.now() / 1000, 1);
  };
  window.closeCam = (x = -1.5, side = false) => {
    s.scene.cam.override = () => side
      ? { pos: new THREE.Vector3(x + 0.2, 1.1, 3.6), look: new THREE.Vector3(x + 0.2, 0.95, 0), fov: 36 }
      : { pos: new THREE.Vector3(x + 2.6, 1.25, 2.6), look: new THREE.Vector3(x + 0.2, 0.95, 0), fov: 38 };
  };
  window.sheet = (list, cols = 4, opts = {}) => {
    s.paused = true;
    const sc = s.scene, cv = sc.renderer.domElement;
    const W = 400, H = 300, rows = Math.ceil(list.length / cols);
    let g = document.getElementById('sheet');
    if (!g) { g = document.createElement('canvas'); g.id = 'sheet'; g.style.cssText = 'position:fixed;inset:0;z-index:99;background:#111;width:100%;height:100%;object-fit:contain'; document.body.appendChild(g); }
    g.width = W * cols; g.height = H * rows;
    const ctx = g.getContext('2d');
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, g.width, g.height);
    list.forEach(([id, fr], i) => {
      window.posePeek(id, fr);
      sc.render(s.match.state, s.prev, 1, performance.now() / 1000, 1);
      const sw = cv.width, sh = cv.height, crop = Math.min(sw, sh * 4 / 3);
      ctx.drawImage(cv, (sw - crop) / 2, 0, crop, sh, (i % cols) * W, Math.floor(i / cols) * H, W, H);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 18px sans-serif'; ctx.fillText(`${id} f${fr}`, (i % cols) * W + 8, Math.floor(i / cols) * H + 22);
    });
    document.getElementById('hud').style.display = 'none';
    return 'ok';
  };
  window.unsheet = () => { document.getElementById('sheet')?.remove(); document.getElementById('hud').style.display = ''; s.paused = false; s.scene.cam.override = null; };
}
