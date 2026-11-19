// The fight HUD (DOM over the canvas): health bars with a damage trail, Power meters, round pips, timer,
// names, combo counters and big callouts (ROUND 1, BRAWL!, K.O., COUNTER, PUNISH!, JUST BLOCK…).
const $ = (s, r = document) => r.querySelector(s);

export class HUD {
  constructor(root) {
    this.root = root;
    root.innerHTML = `
      <div class="hud-top">
        ${[0, 1].map((i) => `
        <div class="hud-side s${i}">
          <div class="hud-name"><span class="nm"></span><span class="ttl"></span></div>
          <div class="hp"><div class="hp-trail"></div><div class="hp-fill"></div><div class="hp-shine"></div></div>
          <div class="pips"></div>
          <div class="ot">OVERTIME</div>
        </div>`).join('<div class="hud-timer"><div class="t">99</div><div class="rnd"></div></div>')}
      </div>
      <div class="hud-bottom">
        ${[0, 1].map((i) => `<div class="meter s${i}"><div class="bars"><i></i><i></i><i></i></div><div class="lvl">0</div></div>`).join('')}
      </div>
      <div class="combo s0"><b>0</b><span>HITS</span><em></em></div>
      <div class="combo s1"><b>0</b><span>HITS</span><em></em></div>
      <div class="callout"></div>
      <div class="callsmall s0"></div><div class="callsmall s1"></div>
      <div class="netinfo"></div>
      <div class="inputs s0"></div><div class="inputs s1"></div>`;
    this.el = [0, 1].map((i) => ({
      side: $(`.hud-side.s${i}`, root), nm: $(`.hud-side.s${i} .nm`, root), ttl: $(`.hud-side.s${i} .ttl`, root),
      fill: $(`.hud-side.s${i} .hp-fill`, root), trail: $(`.hud-side.s${i} .hp-trail`, root), pips: $(`.hud-side.s${i} .pips`, root),
      ot: $(`.hud-side.s${i} .ot`, root), meter: $(`.meter.s${i}`, root), bars: [...root.querySelectorAll(`.meter.s${i} .bars i`)], lvl: $(`.meter.s${i} .lvl`, root),
      combo: $(`.combo.s${i}`, root), small: $(`.callsmall.s${i}`, root), inputs: $(`.inputs.s${i}`, root),
    }));
    this.timer = $('.hud-timer .t', root);
    this.rnd = $('.hud-timer .rnd', root);
    this.callout = $('.callout', root);
    this.net = $('.netinfo', root);
    this.trail = [1, 1]; this.trailHold = [0, 0];
    this.comboShow = [0, 0];
  }

  setNames(names, titles, rounds) {
    for (let i = 0; i < 2; i++) {
      this.el[i].nm.textContent = names[i]; this.el[i].ttl.textContent = titles[i] || '';
      this.el[i].pips.innerHTML = Array.from({ length: rounds }, () => '<b></b>').join('');
    }
  }
  show(on) { this.root.style.display = on ? '' : 'none'; }

  update(state, cfg, dt60) {
    for (let i = 0; i < 2; i++) {
      const f = state.f[i], e = this.el[i];
      const hp = Math.max(0, f.hp / f.maxHp);
      e.fill.style.transform = `scaleX(${hp})`;
      e.fill.classList.toggle('low', hp <= 0.25);
      if (hp < this.trail[i]) { if (this.trailHold[i] > 0) this.trailHold[i] -= dt60; else this.trail[i] = Math.max(hp, this.trail[i] - 0.006 * dt60); }
      else { this.trail[i] = hp; }
      e.trail.style.transform = `scaleX(${this.trail[i]})`;
      e.ot.classList.toggle('on', !!f.overtime);
      const m = f.meter;
      e.bars.forEach((b, k) => { const v = Math.max(0, Math.min(1, (m - k * 1000) / 1000)); b.style.setProperty('--v', v); b.classList.toggle('full', v >= 1); });
      e.lvl.textContent = Math.floor(m / 1000);
      e.meter.classList.toggle('maxed', m >= 3000);
      [...e.pips.children].forEach((p, k) => p.classList.toggle('won', state.wins[i] > k));
      // combo counter (shown on the attacker's side)
      const def = state.f[1 - i];
      if (def.combo >= 2) { this.comboShow[i] = 90; e.combo.querySelector('b').textContent = def.combo; e.combo.querySelector('em').textContent = def.comboDmg + ' dmg'; }
      if (this.comboShow[i] > 0) { this.comboShow[i] -= dt60; e.combo.classList.add('on'); } else e.combo.classList.remove('on');
    }
    const secs = state.timer < 0 ? '∞' : String(Math.ceil(state.timer / 60)).padStart(2, '0');
    if (this.timer.textContent !== secs) this.timer.textContent = secs;
    this.timer.classList.toggle('low', state.timer >= 0 && state.timer < 600);
    this.rnd.textContent = `ROUND ${state.round}`;
  }

  onDamage(i) { this.trailHold[i] = 40; }

  call(text, cls = '', ms = 1200) {
    const c = this.callout;
    c.className = 'callout ' + cls; c.innerHTML = text;
    void c.offsetWidth; c.classList.add('go');
    clearTimeout(this._ct); this._ct = setTimeout(() => { c.className = 'callout'; }, ms);
  }
  small(i, text, cls = '') {
    const c = this.el[i].small;
    c.className = `callsmall s${i} ${cls}`; c.textContent = text;
    void c.offsetWidth; c.classList.add('go');
    clearTimeout(c._t); c._t = setTimeout(() => { c.className = `callsmall s${i}`; }, 900);
  }
  netInfo(text) { this.net.textContent = text || ''; }
  inputs(i, list) { this.el[i].inputs.innerHTML = list; }
}
