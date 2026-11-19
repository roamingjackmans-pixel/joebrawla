// A fighter's skeleton: bone lookup, clip sampling, two-bone IK, spine bends and pose snapshots.
// Works on any model with the UAL 65 bone names (docs/DESIGN.md §14). Character space = (forward, up, left)
// of the model (glTF +Z forward, +X left), so poses don't care which way the fighter faces.
import * as THREE from '../../vendor/three.bundle.js';

const _v1 = new THREE.Vector3(), _v2 = new THREE.Vector3(), _v3 = new THREE.Vector3(), _v4 = new THREE.Vector3();
const _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _q3 = new THREE.Quaternion();
const _m = new THREE.Matrix4();
const DEG = Math.PI / 180;

export const LIMBS = {
  hand_r: ['upperarm_r', 'lowerarm_r', 'hand_r', 'clavicle_r'],
  hand_l: ['upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_l'],
  foot_r: ['thigh_r', 'calf_r', 'foot_r'],
  foot_l: ['thigh_l', 'calf_l', 'foot_l'],
};

export class Rig {
  constructor(root) {
    this.root = root;              // the model's scene root (we position/rotate a parent group)
    this.bones = {};
    root.traverse((o) => { if (o.isBone) this.bones[o.name] = o; });
    this.list = Object.values(this.bones);
    this.rest = new Map();
    for (const b of this.list) this.rest.set(b, { q: b.quaternion.clone(), p: b.position.clone(), s: b.scale.clone() });
    this.bindings = new Map();
    this.snap = null;
    this.measure();
  }

  /** limb lengths and rest heights, measured in the model's bind pose */
  measure() {
    this.resetToRest();
    this.root.updateMatrixWorld(true);
    const wp = (n) => this.bones[n] ? this.bones[n].getWorldPosition(new THREE.Vector3()) : new THREE.Vector3();
    const invRoot = new THREE.Matrix4().copy(this.root.matrixWorld).invert();
    const lp = (n) => wp(n).applyMatrix4(invRoot);
    this.len = {};
    for (const [k, [a, b, c]] of Object.entries(LIMBS)) {
      this.len[k] = [lp(a).distanceTo(lp(b)), lp(b).distanceTo(lp(c))];
    }
    this.pelvisY = lp('pelvis').y || 0.95;
    this.headY = lp('Head').y || 1.6;
    // each bone's direction to its first child, in the bone's own space (for aiming)
    this.axis = new Map();
    for (const b of this.list) {
      const child = b.children.find((c) => c.isBone);
      if (child && child.position.lengthSq() > 1e-10) this.axis.set(b, child.position.clone().normalize());
    }
  }

  resetToRest() {
    for (const [b, r] of this.rest) { b.quaternion.copy(r.q); b.position.copy(r.p); b.scale.copy(r.s); }
  }

  // ------------------------------------------------------------ clips

  bind(clip) {
    let bd = this.bindings.get(clip);
    if (bd) return bd;
    const chans = [];
    for (const tr of clip.tracks) {
      const dot = tr.name.lastIndexOf('.');
      const bone = this.bones[tr.name.slice(0, dot)];
      const prop = tr.name.slice(dot + 1);
      if (!bone || (prop !== 'quaternion' && prop !== 'position')) continue;
      if (prop === 'position' && bone.name !== 'pelvis') continue; // only the pelvis may move
      chans.push({ bone, prop, interp: tr.createInterpolant() });
    }
    bd = { clip, chans, dur: clip.duration };
    this.bindings.set(clip, bd);
    return bd;
  }

  /** write clip pose at time t (seconds) with weight w (1 = replace) onto the bones */
  sample(clip, t, w = 1, opts = {}) {
    const bd = this.bind(clip);
    const tt = Math.max(0, Math.min(t, bd.dur - 1e-4));
    for (const c of bd.chans) {
      const r = c.interp.evaluate(tt);
      if (c.prop === 'quaternion') {
        _q1.set(r[0], r[1], r[2], r[3]);
        if (w >= 1) c.bone.quaternion.copy(_q1); else c.bone.quaternion.slerp(_q1, w);
      } else {
        // pelvis: keep the height (scaled to this body) and damp horizontal drift (the sim owns position)
        const rest = this.rest.get(c.bone).p;
        const k = opts.drift ?? 0.3;
        _v1.set(rest.x + (r[0] - rest.x) * k, r[1] * (opts.yScale ?? 1), rest.z + (r[2] - rest.z) * k);
        if (w >= 1) c.bone.position.copy(_v1); else c.bone.position.lerp(_v1, w);
      }
    }
  }

  // ------------------------------------------------------------ snapshots (crossfades)

  takeSnapshot() {
    if (!this.snap) this.snap = this.list.map((b) => ({ b, q: new THREE.Quaternion(), p: new THREE.Vector3() }));
    for (const s of this.snap) { s.q.copy(s.b.quaternion); s.p.copy(s.b.position); }
    this.hasSnap = true;
  }
  /** blend the current pose back toward the snapshot: k = weight of the snapshot (0..1) */
  blendSnapshot(k) {
    if (!this.hasSnap || k <= 0) return;
    for (const s of this.snap) { s.b.quaternion.slerp(s.q, k); s.b.position.lerp(s.p, k); }
  }

  // ------------------------------------------------------------ procedural layers

  charBasis() {
    // the model root's world axes: forward (+Z model), up, left (+X model)
    this.root.updateMatrixWorld(true);
    const e = this.root.matrixWorld.elements;
    this.fwd = (this.fwd || new THREE.Vector3()).set(e[8], e[9], e[10]).normalize();
    this.left = (this.left || new THREE.Vector3()).set(e[0], e[1], e[2]).normalize();
    this.up = (this.up || new THREE.Vector3()).set(e[4], e[5], e[6]).normalize();
    this.scale = Math.hypot(e[0], e[1], e[2]);
  }
  charDir(x, y, z, out) {
    return out.set(0, 0, 0).addScaledVector(this.fwd, x).addScaledVector(this.up, y).addScaledVector(this.left, z);
  }

  /** rotate a bone by a world-space rotation q (pre-multiplied), keeping its children attached */
  rotateWorld(bone, q) {
    bone.updateWorldMatrix(true, false);
    bone.parent.getWorldQuaternion(_q2);
    bone.getWorldQuaternion(_q3);
    _q3.premultiply(q);
    bone.quaternion.copy(_q2.invert().multiply(_q3));
    bone.updateMatrixWorld(true);
  }

  /** rotation about a character-space axis by deg */
  charRot(ax, ay, az, deg, out = _q1) {
    this.charDir(ax, ay, az, _v4).normalize();
    return out.setFromAxisAngle(_v4, deg * DEG);
  }

  /** pelvis offset (m, character space) and rotations (deg): yaw about up, pitch about left, roll about fwd */
  pelvis(p) {
    const b = this.bones.pelvis; if (!b) return;
    if (p.off) {
      this.charDir(p.off[0], p.off[1], p.off[2], _v1).divideScalar(this.scale || 1);
      // convert world offset into the pelvis parent's space
      b.parent.updateWorldMatrix(true, false);
      _q2.copy(b.parent.getWorldQuaternion(_q2)).invert();
      _v1.applyQuaternion(_q2);
      const ps = b.parent.getWorldScale(_v2);
      b.position.add(_v1.multiplyScalar((this.scale || 1) / (ps.x || 1)));
    }
    if (p.yaw) this.rotateWorld(b, this.charRot(0, 1, 0, p.yaw));
    if (p.pitch) this.rotateWorld(b, this.charRot(0, 0, 1, p.pitch));
    if (p.roll) this.rotateWorld(b, this.charRot(1, 0, 0, p.roll));
  }

  /** spread a bend (forward +), twist (toward the fighter's left +) and side lean (to the right +) over the spine */
  spine(bend = 0, twist = 0, side = 0) {
    const parts = ['spine_01', 'spine_02', 'spine_03'];
    for (const n of parts) {
      const b = this.bones[n]; if (!b) continue;
      if (bend) this.rotateWorld(b, this.charRot(0, 0, 1, bend / 3));
      if (twist) this.rotateWorld(b, this.charRot(0, 1, 0, twist / 3));
      if (side) this.rotateWorld(b, this.charRot(1, 0, 0, side / 3));
    }
  }

  head(pitch = 0, yaw = 0, roll = 0) {
    const b = this.bones.Head || this.bones.neck_01; if (!b) return;
    if (pitch) this.rotateWorld(b, this.charRot(0, 0, 1, pitch));
    if (yaw) this.rotateWorld(b, this.charRot(0, 1, 0, yaw));
    if (roll) this.rotateWorld(b, this.charRot(1, 0, 0, roll));
  }

  /** aim `bone` so its child direction points at world position `to` */
  aim(bone, to) {
    const axis = this.axis.get(bone); if (!axis) return;
    bone.updateWorldMatrix(true, false);
    const from = bone.getWorldPosition(_v1);
    bone.getWorldQuaternion(_q3);
    const cur = _v2.copy(axis).applyQuaternion(_q3).normalize();
    const want = _v3.copy(to).sub(from).normalize();
    _q1.setFromUnitVectors(cur, want);
    this.rotateWorld(bone, _q1);
  }

  /**
   * Two-bone IK. limb: 'hand_r' | 'hand_l' | 'foot_r' | 'foot_l'.
   * t: [x, y, z, w] target in limb lengths from the limb's root joint (shoulder / hip), character space.
   * pole: [x, y, z] character-space direction the elbow/knee should point. w blends with the current pose.
   */
  ik(limb, t, pole) {
    const [an, bn, cn] = LIMBS[limb];
    const A = this.bones[an], B = this.bones[bn], C = this.bones[cn];
    if (!A || !B || !C) return;
    const w = t[3] ?? 1;
    if (w <= 0) return;
    const [la, lb] = this.len[limb];
    const L = (la + lb) * (this.scale || 1);
    A.updateWorldMatrix(true, true);
    const a = A.getWorldPosition(new THREE.Vector3());
    const target = this.charDir(t[0], t[1], t[2], new THREE.Vector3()).multiplyScalar(L).add(a);
    if (w < 1) { // blend toward the clip's own end position
      const cur = C.getWorldPosition(new THREE.Vector3());
      target.lerp(cur, 1 - w);
    }
    const sa = la * (this.scale || 1), sb = lb * (this.scale || 1);
    const toT = target.clone().sub(a);
    const d = Math.min(Math.max(toT.length(), Math.abs(sa - sb) + 1e-3), (sa + sb) * 0.9995);
    const dir = toT.normalize();
    const pdir = this.charDir(pole[0], pole[1], pole[2], new THREE.Vector3()).normalize();
    pdir.addScaledVector(dir, -pdir.dot(dir));
    if (pdir.lengthSq() < 1e-6) pdir.copy(this.up).addScaledVector(dir, -this.up.dot(dir));
    pdir.normalize();
    const cosA = (sa * sa + d * d - sb * sb) / (2 * sa * d);
    const sinA = Math.sqrt(Math.max(0, 1 - cosA * cosA));
    const elbow = a.clone().addScaledVector(dir, cosA * sa).addScaledVector(pdir, sinA * sa);
    const end = a.clone().addScaledVector(dir, d);
    this.aim(A, elbow);
    this.aim(B, end);
  }

  /** world position of a bone (for effects: hit sparks at the fist, trails) */
  worldPos(name, out = new THREE.Vector3()) {
    const b = this.bones[name]; if (!b) return out.set(0, 0, 0);
    b.updateWorldMatrix(true, false);
    return b.getWorldPosition(out);
  }
}
