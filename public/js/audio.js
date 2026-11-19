// Sound: CC0 Kenney impact samples layered with synthesized thumps, cracks and whooshes; a procedural
// soundtrack per stage; and an optional announcer using the browser's speech voice.
const SAMPLES = {
  punchM: [0, 1, 2, 3, 4].map((i) => `impactPunch_medium_00${i}`),
  punchH: [0, 1, 2, 3, 4].map((i) => `impactPunch_heavy_00${i}`),
  softH: [0, 1, 2, 3, 4].map((i) => `impactSoft_heavy_00${i}`),
  softM: [0, 1, 2, 3, 4].map((i) => `impactSoft_medium_00${i}`),
  light: [0, 1, 2, 3, 4].map((i) => `impactGeneric_light_00${i}`),
  metalL: [0, 1, 2, 3, 4].map((i) => `impactMetal_light_00${i}`),
  metalM: [0, 1, 2, 3, 4].map((i) => `impactMetal_medium_00${i}`),
  metalH: [0, 1, 2, 3, 4].map((i) => `impactMetal_heavy_00${i}`),
  plate: [0, 1, 2, 3, 4].map((i) => `impactPlate_heavy_00${i}`),
  bell: ['impactBell_heavy_000', 'impactBell_heavy_001'],
  step: [0, 1, 2, 3, 4].map((i) => `footstep_concrete_00${i}`),
  wood: ['impactWood_heavy_000', 'impactWood_heavy_001', 'impactWood_heavy_002'],
  glass: ['impactGlass_heavy_000', 'impactGlass_heavy_001', 'impactGlass_heavy_002'],
  cloth: ['rpg_cloth1', 'rpg_cloth3'], coins: ['rpg_handleCoins'], chop: ['rpg_chop'], latch: ['rpg_metalLatch'],
  uiMove: ['ui_select_001'], uiOk: ['ui_confirmation_001'], uiBack: ['ui_back_001'], uiTab: ['ui_switch_001'], uiErr: ['ui_error_001'], uiBig: ['ui_confirmation_002'],
};

class Audio {
  constructor() {
    this.ctx = null; this.buf = {}; this.vol = { master: 0.8, sfx: 0.9, music: 0.45 }; this.announcer = true; this.voice = null;
    this.musicNodes = null;
  }

  unlock() {
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC();
    const c = this.ctx;
    this.comp = c.createDynamicsCompressor(); this.comp.threshold.value = -14; this.comp.ratio.value = 4; this.comp.attack.value = 0.003; this.comp.release.value = 0.15;
    this.master = c.createGain(); this.master.gain.value = this.vol.master;
    this.sfx = c.createGain(); this.sfx.gain.value = this.vol.sfx;
    this.mus = c.createGain(); this.mus.gain.value = this.vol.music;
    this.sfx.connect(this.comp); this.mus.connect(this.comp); this.comp.connect(this.master); this.master.connect(c.destination);
    // a short room reverb for weight
    this.verb = c.createConvolver(); this.verb.buffer = this.impulse(1.6, 2.8);
    this.verbGain = c.createGain(); this.verbGain.gain.value = 0.22; this.verb.connect(this.verbGain); this.verbGain.connect(this.comp);
    this.noise = this.makeNoise();
    this.loadAll();
  }

  setVolumes(v) { Object.assign(this.vol, v); if (this.ctx) { this.master.gain.value = this.vol.master; this.sfx.gain.value = this.vol.sfx; this.mus.gain.value = this.vol.music; } }

  impulse(sec, decay) {
    const c = this.ctx, n = Math.floor(c.sampleRate * sec), b = c.createBuffer(2, n, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) { const d = b.getChannelData(ch); for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, decay); }
    return b;
  }
  makeNoise() {
    const c = this.ctx, n = c.sampleRate * 2, b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    return b;
  }

  async loadAll() {
    const names = new Set(Object.values(SAMPLES).flat());
    await Promise.all([...names].map(async (n) => {
      try {
        const r = await fetch(`assets/sfx/${n}.ogg`);
        const ab = await r.arrayBuffer();
        this.buf[n] = await this.ctx.decodeAudioData(ab);
      } catch { /* missing sample: synth only */ }
    }));
  }

  play(group, o = {}) {
    if (!this.ctx) return;
    const list = SAMPLES[group]; if (!list) return;
    const b = this.buf[list[Math.floor(Math.random() * list.length)]]; if (!b) return;
    const c = this.ctx, s = c.createBufferSource(); s.buffer = b;
    s.playbackRate.value = (o.rate || 1) * (1 + (Math.random() - 0.5) * (o.vary ?? 0.12));
    const g = c.createGain(); g.gain.value = o.gain ?? 1;
    s.connect(g); g.connect(this.sfx); if (o.verb) g.connect(this.verb);
    s.start(c.currentTime + (o.delay || 0));
  }

  thump(freq = 80, dur = 0.25, gain = 0.9, verb = false) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(freq * 2.2, t); o.frequency.exponentialRampToValueAtTime(freq * 0.5, t + dur);
    g.gain.setValueAtTime(gain, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(this.sfx); if (verb) g.connect(this.verb);
    o.start(t); o.stop(t + dur + 0.05);
  }

  noiseHit(dur = 0.08, hp = 2000, gain = 0.5, lp = 12000) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime, s = c.createBufferSource(); s.buffer = this.noise;
    const f1 = c.createBiquadFilter(); f1.type = 'highpass'; f1.frequency.value = hp;
    const f2 = c.createBiquadFilter(); f2.type = 'lowpass'; f2.frequency.value = lp;
    const g = c.createGain(); g.gain.setValueAtTime(gain, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    s.connect(f1); f1.connect(f2); f2.connect(g); g.connect(this.sfx);
    s.start(t, Math.random()); s.stop(t + dur + 0.02);
  }

  whoosh(dur = 0.18, from = 600, to = 2400, gain = 0.25) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime, s = c.createBufferSource(); s.buffer = this.noise;
    const f = c.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 1.4;
    f.frequency.setValueAtTime(from, t); f.frequency.exponentialRampToValueAtTime(to, t + dur);
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + dur * 0.4); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    s.connect(f); f.connect(g); g.connect(this.sfx);
    s.start(t, Math.random()); s.stop(t + dur + 0.02);
  }

  tone(freq, dur, type = 'sine', gain = 0.2, slide = 0, delay = 0, dest) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime + delay, o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t); if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, freq * slide), t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + 0.01); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(dest || this.sfx);
    o.start(t); o.stop(t + dur + 0.05);
  }

  // ------------------------------------------------------------ game sounds
  hit(str = 'M', counter = 0, sup = false) {
    const big = str === 'H' || str === 'X' || str === 'S' || sup || counter;
    if (str === 'L') { this.play('punchM', { rate: 1.35, gain: 0.7 }); this.noiseHit(0.05, 3000, 0.25); this.thump(140, 0.1, 0.4); }
    else if (!big) { this.play('punchM', { rate: 1.05, gain: 0.95 }); this.play('softM', { gain: 0.5 }); this.noiseHit(0.07, 2200, 0.32); this.thump(110, 0.16, 0.6); }
    else { this.play('punchH', { gain: 1.1, verb: true }); this.play('softH', { gain: 0.7 }); this.noiseHit(0.12, 1500, 0.45, 9000); this.thump(70, 0.32, 1.0, true); }
    if (counter) this.tone(1800, 0.25, 'triangle', 0.12, 0.6);
    if (sup) this.play('glass', { rate: 1.4, gain: 0.25 });
  }
  block(str = 'M') { this.play(str === 'H' ? 'metalM' : 'metalL', { rate: 1.2, gain: 0.6 }); this.noiseHit(0.04, 4000, 0.18); }
  justBlock() { this.play('metalL', { rate: 1.8, gain: 0.7 }); this.tone(2400, 0.35, 'sine', 0.16, 1.002); this.tone(3600, 0.25, 'sine', 0.08); }
  armor() { this.play('metalH', { rate: 0.9, gain: 0.8 }); this.thump(90, 0.2, 0.6); }
  ex() { this.tone(660, 0.18, 'sawtooth', 0.06, 2); this.whoosh(0.2, 800, 4000, 0.18); }
  breaker() { this.thump(55, 0.5, 1, true); this.tone(110, 0.45, 'square', 0.12, 0.5); this.noiseHit(0.3, 300, 0.4, 3000); this.play('latch', { rate: 0.7, gain: 1 }); }
  overtime() { this.tone(220, 0.6, 'sawtooth', 0.08, 0.5); this.thump(60, 0.4, 0.8); }
  splat() { this.play('plate', { gain: 1, verb: true }); this.thump(50, 0.5, 1, true); }
  thud(big) { this.play(big ? 'softH' : 'softM', { rate: 0.8, gain: big ? 1 : 0.6 }); this.thump(big ? 50 : 70, big ? 0.4 : 0.2, big ? 0.9 : 0.5); }
  step() { this.play('step', { gain: 0.35 }); }
  jump() { this.play('cloth', { gain: 0.35, rate: 1.2 }); }
  dash() { this.whoosh(0.16, 400, 1600, 0.2); this.play('step', { gain: 0.3 }); }
  grab() { this.play('cloth', { gain: 0.7 }); this.thump(120, 0.12, 0.4); }
  proj(kind) { this.whoosh(0.35, 300, 3000, 0.25); this.tone(kind === 'flare' ? 880 : 520, 0.3, 'triangle', 0.06, 1.5); }
  heal() { [0, 0.08, 0.16].forEach((d, i) => this.tone(660 * Math.pow(1.26, i), 0.3, 'sine', 0.1, 1, d)); }
  timestop() { this.tone(1200, 1.2, 'sine', 0.15, 0.25); this.play('bell', { rate: 1.5, gain: 0.5, verb: true }); }
  gong() { this.play('bell', { rate: 0.8, gain: 0.7, verb: true }); }
  ko() { this.thump(40, 1.0, 1.2, true); this.play('punchH', { rate: 0.7, gain: 1.2, verb: true }); this.play('glass', { rate: 0.6, gain: 0.5, verb: true }); this.noiseHit(0.6, 200, 0.35, 4000); }
  superFlash(kind) {
    this.whoosh(0.5, 200, 6000, 0.35);
    const base = kind === 'final' ? 196 : kind === 'overtime' ? 147 : 262;
    [1, 1.26, 1.5, 2].forEach((m, i) => this.tone(base * m, 0.9, 'sawtooth', 0.05, 1, i * 0.04));
    this.thump(60, 0.6, 1, true);
  }
  ui(kind) { this.unlock(); this.play({ move: 'uiMove', ok: 'uiOk', back: 'uiBack', tab: 'uiTab', err: 'uiErr', big: 'uiBig' }[kind] || 'uiMove', { gain: 0.5, vary: 0.02 }); }

  announce(text) {
    if (!this.announcer || !window.speechSynthesis) return;
    try {
      const u = new SpeechSynthesisUtterance(text);
      if (!this.voice) { const vs = speechSynthesis.getVoices(); this.voice = vs.find((v) => /Guy|Mark|David|Daniel|Male/i.test(v.name) && /en/i.test(v.lang)) || vs.find((v) => /en/i.test(v.lang)) || null; }
      if (this.voice) u.voice = this.voice;
      u.rate = 0.92; u.pitch = 0.55; u.volume = this.vol.master;
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    } catch { /* no voice */ }
  }

  // ------------------------------------------------------------ music: a small procedural sequencer
  music(stage = 'crypt') {
    if (!this.ctx) return;
    this.stopMusic();
    const P = MUSIC[stage] || MUSIC.crypt;
    const c = this.ctx;
    const out = c.createGain(); out.gain.value = 0.0001; out.connect(this.mus);
    out.gain.exponentialRampToValueAtTime(1, c.currentTime + 1.5);
    const spb = 60 / P.bpm / 4; // 16th notes
    let step = 0, next = c.currentTime + 0.1;
    const nodes = { out, timer: 0 };
    const freq = (n) => 440 * Math.pow(2, (n - 69) / 12);
    const sched = () => {
      while (next < c.currentTime + 0.2) {
        const s = step % 64, bar = Math.floor(step / 16) % 4;
        const chord = P.chords[bar];
        if (P.kick[s % 16] === 'x') this.drum('kick', next, out);
        if (P.snare[s % 16] === 'x') this.drum('snare', next, out);
        if (P.hat[s % 16] === 'x') this.drum('hat', next, out);
        const bn = P.bass[s % 16];
        if (bn !== '.') this.synth(freq(P.root - 24 + chord[0] + (+bn || 0)), spb * 2, 'sawtooth', 0.09, next, out, 400);
        if (s % 16 === 0) for (const k of chord) this.synth(freq(P.root + k), spb * 16, P.padWave || 'triangle', 0.025, next, out, 1600, 0.4);
        if (P.arp && s % 2 === 0) { const k = chord[(s / 2) % chord.length]; this.synth(freq(P.root + 12 + k), spb * 1.5, 'square', 0.018, next, out, 3000); }
        next += spb; step++;
      }
      nodes.timer = setTimeout(sched, 50);
    };
    sched();
    this.musicNodes = nodes;
  }
  stopMusic() {
    const n = this.musicNodes; if (!n || !this.ctx) return;
    clearTimeout(n.timer);
    n.out.gain.cancelScheduledValues(this.ctx.currentTime);
    n.out.gain.setTargetAtTime(0.0001, this.ctx.currentTime, 0.3);
    setTimeout(() => n.out.disconnect(), 1500);
    this.musicNodes = null;
  }
  synth(f, dur, type, gain, t, dest, cutoff = 2000, attack = 0.01) {
    const c = this.ctx, o = c.createOscillator(), g = c.createGain(), fl = c.createBiquadFilter();
    o.type = type; o.frequency.value = f; fl.type = 'lowpass'; fl.frequency.value = cutoff;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(fl); fl.connect(g); g.connect(dest);
    o.start(t); o.stop(t + dur + 0.05);
  }
  drum(kind, t, dest) {
    const c = this.ctx;
    if (kind === 'kick') {
      const o = c.createOscillator(), g = c.createGain();
      o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.15);
      g.gain.setValueAtTime(0.5, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
      o.connect(g); g.connect(dest); o.start(t); o.stop(t + 0.3);
    } else {
      const s = c.createBufferSource(); s.buffer = this.noise;
      const f = c.createBiquadFilter(); f.type = kind === 'hat' ? 'highpass' : 'bandpass'; f.frequency.value = kind === 'hat' ? 7000 : 1800;
      const g = c.createGain(); const d = kind === 'hat' ? 0.04 : 0.16;
      g.gain.setValueAtTime(kind === 'hat' ? 0.06 : 0.22, t); g.gain.exponentialRampToValueAtTime(0.001, t + d);
      s.connect(f); f.connect(g); g.connect(dest); s.start(t, Math.random()); s.stop(t + d + 0.02);
    }
  }
}

const MUSIC = {
  crypt: { bpm: 132, root: 57, chords: [[0, 3, 7], [-4, 0, 3], [-2, 2, 5], [-5, -1, 2]], kick: 'x...x...x...x..x', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.xx', bass: '0.0.0.07.0.0.0.5', arp: true },
  basement: { bpm: 120, root: 52, chords: [[0, 3, 7], [0, 3, 8], [-2, 3, 7], [-1, 2, 6]], kick: 'x..x..x.x..x....', snare: '....x.......x..x', hat: '..x...x...x...x.', bass: '0..0..0.0..3..5.', arp: false, padWave: 'sawtooth' },
  hollows: { bpm: 112, root: 55, chords: [[0, 3, 7], [1, 5, 8], [-2, 2, 5], [0, 3, 7]], kick: 'x.......x.......', snare: '........x.......', hat: 'x.xxx.x.x.xxx.x.', bass: '0...0...3...5...', arp: true },
  drowned: { bpm: 104, root: 50, chords: [[0, 3, 7], [-4, 0, 3], [-5, -2, 2], [-2, 2, 5]], kick: 'x.....x...x.....', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: '0.....0...0...7.', arp: false, padWave: 'sine' },
  forest: { bpm: 126, root: 59, chords: [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]], kick: 'x...x...x...x...', snare: '....x.......x...', hat: 'xx.xxx.xxx.xxx.x', bass: '0.0.0.0.0.0.0.0.', arp: true },
  forge: { bpm: 144, root: 52, chords: [[0, 3, 7], [1, 4, 8], [0, 3, 7], [-2, 1, 5]], kick: 'x.x.x.x.x.x.x.x.', snare: '....x.......x.x.', hat: 'x.x.x.x.x.x.x.x.', bass: '00.000.000.000.0', arp: false, padWave: 'sawtooth' },
  reliquary: { bpm: 96, root: 62, chords: [[0, 4, 7], [-3, 0, 4], [-5, -1, 2], [-1, 2, 7]], kick: 'x.......x.......', snare: '........x.......', hat: '..x...x...x...x.', bass: '0.......0.......', arp: true, padWave: 'sine' },
  citadel: { bpm: 138, root: 60, chords: [[0, 4, 7], [2, 5, 9], [-1, 2, 7], [0, 4, 7]], kick: 'x...x...x...x...', snare: '....x.......x...', hat: 'xxxxxxxxxxxxxxxx', bass: '0.7.0.7.0.7.0.7.', arp: true },
  abyss: { bpm: 100, root: 48, chords: [[0, 3, 6], [0, 3, 7], [-1, 3, 6], [1, 4, 7]], kick: 'x.......x..x....', snare: '........x.......', hat: '....x.......x...', bass: '0.......0..1....', arp: false, padWave: 'sawtooth' },
  landing: { bpm: 118, root: 60, chords: [[0, 4, 7], [5, 9, 12], [-3, 0, 4], [2, 5, 9]], kick: 'x...x...x...x...', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', bass: '0...0.4.0...0.7.', arp: true },
  menu: { bpm: 110, root: 57, chords: [[0, 3, 7], [-4, 0, 3], [-2, 2, 5], [-5, -1, 2]], kick: 'x.......x.......', snare: '....x.......x...', hat: '..x...x...x...x.', bass: '0.......0...5...', arp: true },
};
MUSIC.training = MUSIC.landing;

export const audio = new Audio();
