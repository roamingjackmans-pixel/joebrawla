// Drives one fighter's skeleton from the simulation state: picks the animation for the current action or
// move, evaluates its keyed poses at the exact (interpolated) move frame, crossfades, and adds life
// (breathing, flinches, look-at). Purely visual: it reads sim state and never writes it.
import { POSES, resolvePose } from './poses.js';

const NUM_KEYS = ['ct', 'cf', 'yaw', 'pitch', 'roll', 'spin', 'tilt', 'lift'];
const VEC_KEYS = ['pel', 'sp', 'hd', 'hr', 'hl', 'fr', 'fl', 'pr', 'pl', 'kr', 'kl'];
const IK_KEYS = ['hr', 'hl', 'fr', 'fl'];
const ease = {
  io: (t) => t * t * (3 - 2 * t),
  in: (t) => t * t * t,
  out: (t) => 1 - (1 - t) * (1 - t) * (1 - t),
  lin: (t) => t,
  snap: (t) => (t < 1 ? 0 : 1),
};

function lerpPose(a, b, t) {
  const out = {};
  out.clip = t < 0.5 ? a.clip : b.clip;
  out.clipA = a.clip; out.clipB = b.clip; out.mix = t;
  out.ctA = a.ct; out.cfA = a.cf; out.ctB = b.ct; out.cfB = b.cf;
  for (const k of NUM_KEYS) if (a[k] !== undefined || b[k] !== undefined) out[k] = (a[k] ?? 0) + ((b[k] ?? 0) - (a[k] ?? 0)) * t;
  for (const k of VEC_KEYS) {
    const va = a[k], vb = b[k];
    if (!va && !vb) continue;
    if (IK_KEYS.includes(k)) {
      // missing IK = weight 0 at the same place as the other side
      const A = va || [...vb.slice(0, 3), 0], B = vb || [...va.slice(0, 3), 0];
      out[k] = [0, 1, 2, 3].map((i) => (A[i] ?? 1) + ((B[i] ?? 1) - (A[i] ?? 1)) * t);
    } else {
      const A = va || [0, 0, 0], B = vb || [0, 0, 0];
      out[k] = [0, 1, 2].map((i) => A[i] + (B[i] - A[i]) * t);
    }
  }
  return out;
}

/** key time: number, or 's' (first active frame), 'a' (last active), 'e' (end), with +/- offsets */
function keyTime(k, mv, dur) {
  if (typeof k === 'number') return k;
  const m = /^([sae])([+-]\d+)?$/.exec(k);
  if (!m || !mv) return dur || 0;
  const base = m[1] === 's' ? mv.startup : m[1] === 'a' ? mv.startup + mv.active - 1 : mv.total;
  return base + (m[2] ? +m[2] : 0);
}

export class Animator {
  constructor(rig, set, fighter) {
    this.rig = rig;
    this.set = set;              // merged animation set for this fighter (base + own)
    this.fighter = fighter;      // compiled fighter data (moves)
    this.key = '';
    this.t0 = 0;                 // render time the current track started
    this.fade = 0; this.fadeLen = 1;
    this.flinch = 0; this.flinchDir = 1; this.flinchHigh = true;
    this.breath = Math.random() * 10;
    this.visual = { spin: 0, tilt: 0, lift: 0 };
    this.clips = set.clips;      // name -> AnimationClip
  }

  /** which animation spec applies now */
  track(f, phase) {
    const S = this.set.states;
    const mvSet = this.set.moves;
    if (f.act === 'move' || f.act === 'throwing') {
      const id = f.move;
      if (id) {
        const spec = mvSet[id] || mvSet[id.replace(/_(L|M|H|EX)$/, '')] || null;
        if (spec) return { key: 'm:' + id, spec, mv: this.fighter.moves[id] };
      }
      return { key: 'm:?', spec: S.idle, mv: null };
    }
    let name = f.act;
    if (name === 'walk') name = f.vx * f.face >= 0 ? 'walkF' : 'walkB';
    if (name === 'idle' && f.guard) name = 'guard';
    if (name === 'jump') name = f.jumpDir > 0 ? 'jumpF' : f.jumpDir < 0 ? 'jumpB' : 'jumpU';
    if (name === 'air') name = f.hp <= 0 ? 'ko' : 'air';
    if (name === 'ko' && f.y <= 0 && f.t > 20) name = 'koDown';
    const spec = S[name] || S.idle;
    return { key: 's:' + name, spec, mv: null };
  }

  /** a hit landed on this fighter: start a flinch */
  onHit(high, strength) { this.flinch = Math.min(1.4, 0.5 + strength * 0.35); this.flinchHigh = high; }

  update(f, frameF, now, opts = {}) {
    const { key, spec, mv } = this.track(f, opts.phase);
    if (key !== this.key) {
      this.rig.takeSnapshot();
      this.fade = 1;
      this.fadeLen = spec.blend ?? (key.startsWith('m:') ? 3 : 5);
      this.key = key; this.t0 = now; this.startF = f.t;
    }
    const rig = this.rig;
    rig.resetToRest();
    rig.charBasis();
    // time within the spec: move frames (with sub-frame interpolation) or seconds for loops
    let pose;
    if (spec.keys) {
      const fr = mv ? frameF : f.t + (frameF % 1);
      pose = this.evalKeys(spec.keys, fr, mv);
    } else {
      pose = resolvePose(spec.pose || 'stance');
    }
    if (spec.loop) {
      const t = (now - this.t0) * (spec.speed || 1);
      pose = { ...pose, clip: spec.clip || pose.clip, ct: undefined, cf: undefined, loopT: t };
    }
    this.apply(pose, spec, f, now);
    // crossfade from the previous pose
    if (this.fade > 0) {
      const k = this.fade;
      rig.blendSnapshot(ease.io(k));
      this.fade = Math.max(0, this.fade - (opts.dt60 || 1) / this.fadeLen);
    }
    this.visual.spin = pose.spin || 0;
    this.visual.tilt = pose.tilt || 0;
    this.visual.lift = pose.lift || 0;
    // flinch decays
    if (this.flinch > 0) this.flinch = Math.max(0, this.flinch - (opts.dt60 || 1) * 0.09);
  }

  evalKeys(keys, fr, mv) {
    // keys: [[time, pose, ease?], ...]
    let k0 = keys[0], k1 = keys[0];
    let t0 = keyTime(k0[0], mv), t1 = t0;
    for (let i = 0; i < keys.length; i++) {
      const ti = keyTime(keys[i][0], mv);
      if (ti <= fr) { k0 = keys[i]; t0 = ti; k1 = keys[i + 1] || keys[i]; t1 = keys[i + 1] ? keyTime(keys[i + 1][0], mv) : ti; }
    }
    if (fr < keyTime(keys[0][0], mv)) return resolvePose(keys[0][1]);
    const a = resolvePose(k0[1]), b = resolvePose(k1[1]);
    if (k0 === k1 || t1 <= t0) return a;
    const e = ease[k1[2] || 'io'] || ease.io;
    return lerpPose(a, b, e(Math.min(1, (fr - t0) / (t1 - t0))));
  }

  sampleBase(name, ct, cf, loopT) {
    const clip = this.clips[name];
    if (!clip) return false;
    let t = ct ?? (cf != null ? cf * clip.duration : 0);
    if (loopT != null) t = loopT % clip.duration;
    this.rig.sample(clip, t, 1, { yScale: this.yScale });
    return true;
  }

  apply(p, spec, f, now) {
    const rig = this.rig;
    this.yScale = this.set.yScale || 1;
    // base clip(s)
    if (p.clipA && p.clipB && p.clipA !== p.clipB) {
      this.sampleBase(p.clipA, p.ctA, p.cfA, p.loopT);
      const clipB = this.clips[p.clipB];
      if (clipB) rig.sample(clipB, p.ctB ?? (p.cfB != null ? p.cfB * clipB.duration : 0), p.mix, { yScale: this.yScale });
    } else if (p.clip) {
      this.sampleBase(p.clip, p.ct, p.cf, p.loopT);
    }
    // overlay pose for loops (e.g. guard arms on a walk clip)
    if (spec.over) p = { ...resolvePose(spec.over), ...stripBase(p), clip: p.clip };
    const st = this.set.style || {};
    // breathing on idle-ish states
    const idleish = this.key === 's:idle' || this.key === 's:guard' || this.key === 's:crouch';
    const breathe = idleish ? Math.sin(now * 2.2 + this.breath) : 0;
    const pel = p.pel ? [...p.pel] : [0, 0, 0];
    pel[1] += breathe * 0.012 + (st.pelY || 0) * (p.pel ? 1 : 0);
    rig.pelvis({ off: pel, yaw: (p.yaw || 0) + (st.yaw || 0) * (p.yaw !== undefined ? 1 : 0), pitch: p.pitch || 0, roll: p.roll || 0 });
    // flinch: snap the spine/head back, decaying
    const fl = this.flinch;
    const sp = p.sp ? [...p.sp] : [0, 0, 0];
    if (fl > 0) { sp[0] -= fl * (this.flinchHigh ? 14 : 22); sp[2] += fl * 6; }
    sp[0] += breathe * 1.2 + (st.lean || 0) * (p.sp ? 1 : 0);
    rig.spine(sp[0], sp[1], sp[2]);
    // legs first, then arms (arms follow the spine)
    if (p.fr && p.fr[3] > 0) { rig.ik('foot_r', p.fr, p.kr || [1, 0, 0]); levelFoot(rig, 'foot_r', 'ball_r'); }
    if (p.fl && p.fl[3] > 0) { rig.ik('foot_l', p.fl, p.kl || [1, 0, 0]); levelFoot(rig, 'foot_l', 'ball_l'); }
    if (p.hr && p.hr[3] > 0) rig.ik('hand_r', p.hr, p.pr || [-0.3, -1, -0.6]);
    if (p.hl && p.hl[3] > 0) rig.ik('hand_l', p.hl, p.pl || [-0.3, -1, 0.6]);
    const hd = p.hd ? [...p.hd] : [0, 0, 0];
    if (fl > 0) hd[0] -= fl * (this.flinchHigh ? 22 : 8);
    rig.head(hd[0], hd[1], hd[2]);
  }
}

function stripBase(p) { const { clip, ct, cf, loopT, clipA, clipB, ...rest } = p; return rest; }

/** keep the sole level after IK so feet don't point at the sky */
function levelFoot(rig, foot, ball) {
  const F = rig.bones[foot], B = rig.bones[ball];
  if (!F || !B) return;
  const fp = rig.worldPos(foot), bp = rig.worldPos(ball);
  const d = bp.clone().sub(fp);
  const len = d.length();
  d.y = 0;
  if (d.lengthSq() < 1e-6) return;
  d.normalize().multiplyScalar(len);
  d.y = -len * 0.25; // toes slightly down, like a planted foot
  rig.aim(F, fp.add(d));
}
