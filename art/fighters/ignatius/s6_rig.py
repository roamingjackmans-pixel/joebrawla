"""Stage 6: assemble the rigged fighter on the edited UAL1 skeleton.
  * builds the armature (f_rig.make_armature), deletes nothing else (no meshes / actions come with it)
  * per-part skin weights computed in the modeling pose (distance-to-bone rules, smoothed, max 4)
  * un-poses every vertex with the inverse of its blended skinning matrix -> mesh rests on the UAL rest pose
  * joins the body parts into <Name>_Body (one material slot per material), the hammer into <Name>_Hammer
    skinned 100 % to hand_r
  * scales the armature object so the model is f_rig.HEIGHT tall (glTF node scale on `Armature`)
  -> _work/rig.blend
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Matrix, Vector
import jb_lib as L
import f_rig as R
import f_parts as CP
import f_sets
import f_scene as SC

J = L.load_json(os.path.join(L.WORK, "joints.json"))
CP.setJ(J)
CP.init_head()
TEX = os.path.join(L.WORK, "tex")
F32 = np.float32
NAME = "Ignatius"


def H(b):
    return np.array(J[b]["head"], F32)


def T(b):
    return np.array(J[b]["tail"], F32)


def dseg(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def wdist(P, spec, p=5.0):
    cols = []
    for s in spec:
        b, r = s[0], s[1]
        a = s[2] if len(s) > 2 else H(b)
        e = s[3] if len(s) > 3 else T(b)
        cols.append(dseg(P, a, e) / r)
    D = np.stack(cols, 1)
    W = 1.0 / (D ** p + 1e-4)
    W /= W.sum(1, keepdims=True)
    return {s[0]: W[:, i] for i, s in enumerate(spec)}


def finger_tail(f, side, seg):
    return H("%s_0%d_%s" % (f, seg + 1, side)) if seg < 3 else H("%s_04_leaf_%s" % (f, side))


def hand_spec(s, fr=0.02, thumb_r=0.025):
    spec = [("lowerarm_" + s, 0.07, H("lowerarm_" + s), H("hand_" + s)),
            ("hand_" + s, 0.05, H("hand_" + s), H("middle_01_" + s) * 0.65 + H("hand_" + s) * 0.35)]
    for f in ("index", "middle", "ring", "pinky"):
        for seg in (1, 2, 3):
            b = "%s_0%d_%s" % (f, seg, s)
            spec.append((b, fr, H(b), finger_tail(f, s, seg)))
    for seg in (1, 2, 3):
        b = "thumb_0%d_%s" % (seg, s)
        spec.append((b, thumb_r, H(b), H("thumb_0%d_%s" % (seg + 1, s)) if seg < 3 else H("thumb_04_leaf_" + s)))
    return spec


def torso_weights(P):
    x, z = P[:, 0], P[:, 2]
    spec = [("pelvis", 0.20), ("spine_01", 0.22), ("spine_02", 0.24), ("spine_03", 0.26), ("neck_01", 0.12),
            ("Head", 0.10, H("Head"), H("Head") + np.array([0, 0, 0.05], F32)),
            ("clavicle_l", 0.15), ("clavicle_r", 0.15)]
    for s in ("l", "r"):
        spec += [("upperarm_" + s, 0.12), ("lowerarm_" + s, 0.10)]
    W = wdist(P, spec, 5.0)
    sf = CP.sleeve_factor(P)
    for s, sgn in (("l", 1), ("r", -1)):
        side = (sgn * x > 0.05).astype(F32)
        for b in ("upperarm_", "lowerarm_"):
            W[b + s] = W[b + s] * sf * side
    for b in ("pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "Head"):
        W[b] = W[b] * (1 - 0.97 * sf)
    for s, sgn in (("l", 1), ("r", -1)):
        W["clavicle_" + s] = W["clavicle_" + s] * (sgn * x > -0.02)
    # the bull neck follows the head a little, the head joint sits low
    W["Head"] = W["Head"] * (z > 1.55)
    return W


def skirt_like(P, top_z, bottom_z, front_bias=0.5, max_leg=0.85):
    """pelvis at the top, blending into the thighs going down; left/right by x (centre 50/50)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    leg = max_leg * L.smoothstep(top_z, bottom_z, z)
    sd = L.smoothstep(-0.10, 0.10, x)
    return {"pelvis": 1 - leg, "thigh_l": leg * sd, "thigh_r": leg * (1 - sd)}


def part_weights(name, P):
    n = len(P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if name == "torso":
        return torso_weights(P)
    if name == "bib":
        return wdist(P, [("pelvis", 0.2), ("spine_01", 0.22), ("spine_02", 0.24), ("spine_03", 0.26)], 4.0)
    if name in ("mask", "hardhat"):
        return {"Head": np.ones(n, F32)}
    if name == "flap":
        t = L.smoothstep(CP.CC[2] - 0.05, CP.CC[2] - 0.26, z)
        sd = L.smoothstep(-0.12, 0.12, x)
        return {"Head": 1 - 0.75 * t, "neck_01": 0.35 * t, "spine_03": 0.25 * t,
                "clavicle_l": 0.15 * t * sd, "clavicle_r": 0.15 * t * (1 - sd)}
    if name == "beard":
        t = L.smoothstep(CP.CC[2] - 0.16, 1.15, z)
        return {"Head": 1 - 0.7 * t, "spine_03": 0.5 * t, "spine_02": 0.2 * t}
    if name == "arm_r":
        return wdist(P, hand_spec("r"), 6.0)
    if name == "gauntlet":
        W = wdist(P, hand_spec("l", 0.024, 0.03) + [("upperarm_l", 0.08, H("upperarm_l"), H("lowerarm_l"))], 6.0)
        return W
    if name == "belt":
        hang = L.smoothstep(0.95, 0.70, z)
        sd = (x > 0.1).astype(F32)
        return {"spine_01": 0.35 * (1 - hang), "pelvis": 1 - 0.35 * (1 - hang) - 0.5 * hang * sd,
                "thigh_l": 0.5 * hang * sd}
    if name == "apron":
        return skirt_like(P, 0.98, 0.45, max_leg=0.62)
    if name == "mskirt":
        return skirt_like(P, 0.96, 0.60, max_leg=0.85)
    if name == "legs":
        spec = [("pelvis", 0.18)]
        for s in ("l", "r"):
            spec += [("thigh_" + s, 0.12), ("calf_" + s, 0.10), ("foot_" + s, 0.08), ("ball_" + s, 0.06)]
        W = wdist(P, spec, 6.0)
        for s, sgn in (("l", 1), ("r", -1)):
            for b in ("thigh_", "calf_", "foot_", "ball_"):
                W[b + s] = W[b + s] * (sgn * x > -0.01)
            W["ball_" + s] *= 0.5
        return W
    return None          # -> nearest torso weights (chains, straps)


def to_matrix(W, bones, n):
    M = np.zeros((n, len(bones)), F32)
    for b, w in W.items():
        M[:, bones.index(b)] += w
    return M


def limit_norm(M, k=4):
    if M.shape[1] > k:
        idx = np.argsort(-M, 1)[:, k:]
        np.put_along_axis(M, idx, 0, 1)
    M[M < 0.01] = 0
    s = M.sum(1, keepdims=True)
    return M / np.maximum(s, 1e-9)


def smooth_weights(M, ob, iters=4, keep=0.5):
    me = ob.data
    E = np.zeros(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", E)
    E = E.reshape(-1, 2)
    for _ in range(iters):
        M = keep * M + (1 - keep) * L.laplacian(np.zeros((len(M), 1), F32), E, M)
    return M


def mesh_verts(ob):
    V = np.zeros(len(ob.data.vertices) * 3, F32)
    ob.data.vertices.foreach_get("co", V)
    return V.reshape(-1, 3)


def unpose(V, M, bones):
    S = []
    for b in bones:
        Pm = np.array(J[b]["pose"], np.float64)
        Rm = np.array(J[b]["rest"], np.float64)
        S.append(Pm @ np.linalg.inv(Rm))
    S = np.stack(S)
    Sv = np.einsum('vb,bij->vij', M.astype(np.float64), S)
    Vh = np.concatenate([V, np.ones((len(V), 1))], 1)
    Rr = np.linalg.solve(Sv, Vh[:, :, None])[:, :, 0]
    return Rr[:, :3].astype(F32)


def assign_groups(ob, M, bones):
    ob.vertex_groups.clear()
    for j, b in enumerate(bones):
        idx = np.nonzero(M[:, j] > 0)[0]
        if len(idx) == 0:
            continue
        vg = ob.vertex_groups.new(name=b)
        for i in idx:
            vg.add([int(i)], float(M[i, j]), 'REPLACE')


def append_objects(path, suffix="_low"):
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [n for n in src.objects if n.endswith(suffix)]
    out = []
    for ob in dst.objects:
        bpy.context.scene.collection.objects.link(ob)
        out.append(ob)
    return out


# ============================================================================================
arm = R.make_armature()
BONES = [b.name for b in arm.data.bones]
print("RIG bones", len(BONES))

# ---- materials (tint factors from the paint stage)
tints = {}
for aset in f_sets.SIZE:
    p = os.path.join(L.WORK, "tint_%s.json" % aset)
    if os.path.exists(p):
        tints.update(L.load_json(p))
MATS = {}
for key, (mname, aset, fac, emis) in f_sets.MATERIALS.items():
    em = os.path.join(TEX, aset + "_emission.png") if emis > 0 else None
    m = SC.pbr_material(mname, os.path.join(TEX, aset + "_albedo.png"), os.path.join(TEX, aset + "_normal.png"),
                        os.path.join(TEX, aset + "_orm.png"), em, emis)
    if key in tints:
        f = tints[key]
        SC.set_base_factor(m, f)
        print("RIG tint", mname, [round(v, 3) for v in f])
    MATS[key] = m

parts = {p.name: p for p in f_sets.all_parts()}
body_objs = []
for aset in ("body", "gear"):
    body_objs += append_objects(os.path.join(L.WORK, "low_%s.blend" % aset))
order = sorted(body_objs, key=lambda o: 0 if o.name.startswith("torso") else 1)
cache = {}
for ob in order:
    name = ob.name[:-4]
    V = mesh_verts(ob)
    W = part_weights(name, V)
    if W is None:
        TV, TM = cache["torso"]
        sub = TV[::3]
        d = ((V[:, None, :] - sub[None, :, :]) ** 2).sum(-1)
        M = TM[np.argmin(d, 1) * 3]
        M = smooth_weights(M, ob, 2)
        M = limit_norm(M, 4)
    else:
        M = to_matrix(W, BONES, len(V))
        M = limit_norm(M, 4)
        M = smooth_weights(M, ob, iters=4 if name not in ("arm_r", "gauntlet") else 1)
        M = limit_norm(M, 4)
    cache[name] = (V, M)
    Vr = unpose(V, M, BONES)
    ob.data.vertices.foreach_set("co", Vr.ravel())
    ob.data.update()
    assign_groups(ob, M, BONES)
    ob.data.materials.clear()
    ob.data.materials.append(MATS[parts[name].mat])
    print("RIG %-8s verts=%d mat=%s" % (name, len(V), parts[name].mat))

# round trip check on the torso
torso = [o for o in body_objs if o.name.startswith("torso")][0]
mchk = torso.modifiers.new("chk", 'ARMATURE')
mchk.object = arm
R.apply_pose(arm, R.modeling_pose())
dg = bpy.context.evaluated_depsgraph_get()
ev = torso.evaluated_get(dg)
me = ev.to_mesh()
Ve = np.zeros(len(me.vertices) * 3, F32)
me.vertices.foreach_get("co", Ve)
ev.to_mesh_clear()
print("RIG modeling-pose round trip max error %.5f m" % np.abs(Ve.reshape(-1, 3) - cache["torso"][0]).max())
torso.modifiers.remove(mchk)
R.apply_pose(arm, {})

# join body (materials merge into slots)
bpy.ops.object.select_all(action='DESELECT')
for ob in body_objs:
    ob.select_set(True)
bpy.context.view_layer.objects.active = torso
bpy.ops.object.join()
body = torso
body.name = NAME + "_Body"
body.data.name = NAME + "_Body"
body.parent = arm
body.matrix_parent_inverse = Matrix.Identity(4)
mod = body.modifiers.new("Armature", 'ARMATURE')
mod.object = arm

# ---- hammer: prop-local -> hand_r rest space, weighted 100 % hand_r
hm = append_objects(os.path.join(L.WORK, "low_hammer.blend"))[0]
hm.name = NAME + "_Hammer"
hm.data.name = NAME + "_Hammer"
Vh = mesh_verts(hm)
Mr = R.prop_to_armature(J, "r", pose=False)
Vw = (np.c_[Vh, np.ones(len(Vh))] @ Mr.T)[:, :3].astype(F32)
hm.data.vertices.foreach_set("co", Vw.ravel())
hm.data.update()
hm.vertex_groups.clear()
vg = hm.vertex_groups.new(name="hand_r")
vg.add(list(range(len(Vh))), 1.0, 'REPLACE')
hm.data.materials.clear()
hm.data.materials.append(MATS["hammer"])
hm.parent = arm
hm.matrix_parent_inverse = Matrix.Identity(4)
m2 = hm.modifiers.new("Armature", 'ARMATURE')
m2.object = arm

# ---- height: uniform armature scale
Vb = mesh_verts(body)
top = float(Vb[:, 2].max())
K = R.HEIGHT / top
arm.scale = (K, K, K)
bpy.context.view_layer.update()
print("RIG rest top %.4f m (model units) -> armature scale %.4f -> height %.3f m" % (top, K, top * K))
L.save_json(os.path.join(L.WORK, "rig_info.json"), {"scale": K, "top": top})

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "rig.blend"))
tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
htris = sum(len(p.vertices) - 2 for p in hm.data.polygons)
print("RIG saved: body tris=%d hammer tris=%d total=%d materials=%s" % (tris, htris, tris + htris,
      [m.name for m in body.data.materials] + [m.name for m in hm.data.materials]))
