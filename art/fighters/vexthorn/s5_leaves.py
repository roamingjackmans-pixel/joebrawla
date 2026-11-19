"""Stage 5: autumn leaves (tint1_leaves).
  * paints a 1024 RGBA alpha-cutout atlas (4 leaf shapes in a 2x2 grid) + normal + ORM with numpy.  The colour is
    kept light/neutral (cream with mild yellow/red hue shifts, darker veins): the material multiplies it by
    LEAF_FACTOR (burnt orange) so palette swaps can recolour the leaves.
  * scatters bent leaf cards (4 tris each) over the shoulder moss, along the antlers (strung garlands hanging off the
    beams), on the hip belt and in the neck moss.  Each card stores its anchor point + group so s6 can skin it
    rigidly to the right bones.
  -> _work/<id>/tex/leaves_albedo.png, leaves_normal.png, leaves_orm.png, _work/<id>/leaves.blend (object leaves_fol)
blender -b --factory-startup --python s5_leaves.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import fblib as L
L.load_joints()
import parts as PT

F32 = np.float32
S = 1024
CELL = S // 2
rng = np.random.default_rng(23)


# ============================================================================================ texture
def aa(d, w=1.3):
    return np.clip(0.5 - d / w, 0, 1)


def leaf_cell(kind, seed):
    """one 512 cell: returns rgba (h,w,4) linear-ish 0..1 and height (h,w)."""
    h = w = CELL
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    # leaf space: base (stem joint) at (0.5, 0.86), tip at (0.5, 0.06); u across, v along (0 base .. 1 tip)
    u = (X - w * 0.5) / (w * 0.5)
    v = (h * 0.86 - Y) / (h * 0.80)
    r = np.sqrt(u * u + (v - 0.42) ** 2)
    th = np.arctan2(u, v - 0.42)
    nz = L.NOISE
    if kind == 0:      # maple: 5 pointed lobes
        lobes = np.abs(np.cos(th * 2.5))
        R = 0.30 + 0.30 * lobes ** 3 + 0.05 * np.cos(th * 9) ** 2
        R = R * np.where(np.abs(th) > 2.6, 0.55, 1.0)
        inside = r - R
    elif kind == 1:    # oak: elongated with round lobes
        half = 0.30 * np.sin(np.pi * np.clip(v, 0, 1)) ** 0.8 * (0.75 + 0.25 * np.abs(np.sin(v * np.pi * 4.5)))
        inside = np.where((v > 0) & (v < 1), np.abs(u) - half, 1.0)
    elif kind == 2:    # aspen / beech: pointed oval
        half = 0.38 * np.sin(np.pi * np.clip(v, 0, 1) ** 0.85) ** 0.9
        inside = np.where((v > 0) & (v < 1), np.abs(u) - half, 1.0)
    else:              # narrow curled willow-ish leaf
        half = 0.2 * np.sin(np.pi * np.clip(v, 0, 1)) ** 0.7
        inside = np.where((v > 0) & (v < 1), np.abs(u + 0.12 * np.sin(v * 2.5)) - half, 1.0)
    # ragged dry edges
    P3 = np.stack([X / 60.0 + seed, Y / 60.0, np.full_like(X, seed * 3.1)], -1)
    edge_n = nz(P3.reshape(-1, 3)).reshape(h, w)
    inside = inside + 0.018 * edge_n
    cov = aa(inside * w * 0.5)
    # stem
    stem = (np.abs(u) < 0.022) & (v < 0.05) & (v > -0.1)
    cov = np.maximum(cov, stem.astype(F32))
    # veins
    mid = np.exp(-(u / 0.012) ** 2) * (v > -0.05) * (v < 0.95)
    vein = mid.copy()
    if kind == 0:
        for a in (-1.3, -0.65, 0.65, 1.3):
            d = np.abs(np.sin(th - a)) * r
            vein = np.maximum(vein, np.exp(-(d / 0.012) ** 2) * (np.cos(th - a) > 0) * (r < 0.6))
    else:
        for k in range(1, 8):
            vk = k / 8.0
            d = np.abs((v - vk) - 0.55 * np.abs(u))
            vein = np.maximum(vein, np.exp(-(d / 0.01) ** 2) * (np.abs(u) < 0.4) * 0.8)
    # colour (cream base, mild hue per leaf, darker blotches + edges)
    hue = [np.array([1.0, 0.93, 0.72], F32), np.array([1.0, 0.78, 0.62], F32), np.array([1.0, 0.98, 0.82], F32),
           np.array([0.98, 0.72, 0.6], F32)][seed % 4]
    base = np.ones((h, w, 3), F32) * hue
    blot = np.clip(L.NOISE2.fbm(np.stack([X / 90.0, Y / 90.0, np.full_like(X, seed)], -1).reshape(-1, 3), 3).reshape(h, w) * 1.6 + 0.2, 0, 1)
    base = base * (0.82 + 0.25 * blot[..., None])
    rim = smoothstep_np(-0.06, 0.0, inside)
    base = base * (1 - 0.45 * rim[..., None]) * np.array([1.0, 0.92, 0.85], F32) ** rim[..., None]
    spots = np.clip(L.NOISE3(np.stack([X / 14.0, Y / 14.0, np.full_like(X, seed * 2.0)], -1).reshape(-1, 3)).reshape(h, w) * 3 - 2.2, 0, 1)
    base = base * (1 - 0.5 * spots[..., None])
    base = base * (1 - 0.35 * vein[..., None])
    base[stem] = np.array([0.55, 0.42, 0.3], F32)
    height = 0.6 * vein - 0.3 * rim + 0.1 * blot
    rgba = np.concatenate([np.clip(base, 0, 1), cov[..., None]], -1)
    return rgba, height


def smoothstep_np(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


tex = np.zeros((S, S, 4), F32)
hgt = np.zeros((S, S), F32)
for k in range(4):
    rgba, hh = leaf_cell(k, k)
    r0, c0 = (k // 2) * CELL, (k % 2) * CELL
    tex[r0:r0 + CELL, c0:c0 + CELL] = rgba
    hgt[r0:r0 + CELL, c0:c0 + CELL] = hh
# bleed colour into transparent texels (no dark fringes at the cutout edge)
mask = tex[..., 3] > 0.5
DI = L.dilate_index(mask, 24)
rgb = L.dilate_fast(tex[..., :3].copy(), DI, (0.9, 0.8, 0.6))
tex[..., :3] = rgb
# bpy images are bottom-up: flip so cell row 0 is at the top of the png
L.save_np_png(tex[::-1].copy(), os.path.join(L.TEX, "leaves_albedo.png"))
gy, gx = np.gradient(L.blur(hgt, 1))
nrm = np.stack([-gx * 3.0, gy * 3.0, np.ones_like(gx)], -1)
nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
L.save_np_png((nrm * 0.5 + 0.5)[::-1].copy(), os.path.join(L.TEX, "leaves_normal.png"), 'Non-Color')
orm = np.stack([np.ones((S, S), F32), np.full((S, S), 0.72, F32) - 0.1 * hgt, np.zeros((S, S), F32)], -1)
L.save_np_png(orm, os.path.join(L.TEX, "leaves_orm.png"), 'Non-Color')
print("LEAVES texture saved")


# ============================================================================================ cards
def cell_uv(k):
    """uv rect (u0, v0, u1, v1) of cell k (row 0 = top of image = high v)."""
    col, row = k % 2, k // 2
    u0 = col * 0.5
    v1 = 1.0 - row * 0.5
    return u0, v1 - 0.5, u0 + 0.5, v1


V, F, UV, ANCH, GRP = [], [], [], [], []
GROUPS = ["shoulder_l", "shoulder_r", "head", "torso", "moss"]


def card(base, along, normal, size, kind, group, anchor=None, bend=0.25, curl=0.0):
    """leaf card: stem at base, blade along `along`; normal = face normal. 6 verts (3 rows x 2), 4 tris."""
    along = L.norm(along)
    n = np.asarray(normal, F32)
    n = L.norm(n - along * float(n @ along))
    side = L.norm(np.cross(along, n))
    # cell space: stem at v=0.86*(cell) from top..., the leaf spans v in [0.06, 0.92] of the cell height
    ln = size
    wd = size * 1.0
    rows = [(-0.08, 0.0), (0.42, bend * 0.5), (1.0, bend)]
    u0, v0, u1, v1 = cell_uv(kind)
    i0 = len(V)
    for t, b in rows:
        for sgn in (-1, 1):
            p = base + along * (t * ln * 0.9) + side * (sgn * wd * 0.5) + n * (b * ln * 0.3 + curl * ln * abs(sgn) * 0.15)
            V.append(p)
            # cell: v_img = 0.86 - 0.80 * t  (from top);  uv v = v1 - 0.5 * v_img
            UV.append((u0 + 0.5 * (0.5 + 0.5 * sgn), v1 - 0.5 * (0.86 - 0.80 * t)))
            ANCH.append(base if anchor is None else anchor)
            GRP.append(GROUPS.index(group))
    for r in range(2):
        a, b, c, d = i0 + 2 * r, i0 + 2 * r + 1, i0 + 2 * r + 3, i0 + 2 * r + 2
        F.append((a, b, c, d))


# ---- shoulders: on the moss caps
dm = np.load(os.path.join(L.WORK, "high_moss.npz"))
MV = dm["V"]
MN = L.vnormals(MV, dm["Q"])
for side, s in PT.SIDES:
    sel = np.nonzero((s * MV[:, 0] > 0.12) & (MN[:, 2] > 0.25) & (MV[:, 2] > 1.5))[0]
    pick = rng.choice(sel, size=min(34, len(sel)), replace=False)
    for i in pick:
        p, n = MV[i], MN[i]
        tang = L.norm(np.cross(n, rng.normal(size=3).astype(F32)))
        out = L.norm(np.array([s * 1.0, 0.0, -0.4], F32))
        along = L.norm(tang * 0.6 + out * (0.5 if s * p[0] > 0.24 else 0.1) + rng.normal(size=3).astype(F32) * 0.2)
        card(p - n * 0.004, along, n + rng.normal(size=3).astype(F32) * 0.25, rng.uniform(0.055, 0.085),
             int(rng.integers(0, 4)), "shoulder_" + side, bend=rng.uniform(0.1, 0.45), curl=rng.uniform(-0.3, 0.3))

# ---- neck moss
sel = np.nonzero((np.abs(MV[:, 0]) < 0.07) & (MV[:, 1] > 0.06) & (MV[:, 2] > 1.58))[0]
for i in rng.choice(sel, size=min(10, len(sel)), replace=False):
    p, n = MV[i], MN[i]
    along = L.norm(np.array([rng.normal() * 0.4, 0.6, -0.8], F32))
    card(p - n * 0.003, along, n, rng.uniform(0.05, 0.07), int(rng.integers(0, 4)), "moss", bend=0.3)


# ---- antlers: garlands strung under the beams + leaves caught on the tines
def beam_point(s, t):
    p = PT.antler_polys(s)[0][0]
    al = PT.arclen(p)
    return np.array([np.interp(t, al, p[:, k]) for k in range(3)], F32)


LANTERN_HANGS = []
for side, s in PT.SIDES:
    for (ta, tb, sag, nl) in ((0.08, 0.52, 0.07, 9), (0.5, 0.92, 0.05, 7)):
        A, B = beam_point(s, ta) + np.array([0, 0, -0.02], F32), beam_point(s, tb) + np.array([0, 0, -0.012], F32)
        pts = []
        for k in range(nl):
            t = (k + 0.5) / nl
            q = A + (B - A) * t
            q = q + np.array([0, 0, -sag * 4 * t * (1 - t)], F32)
            pts.append(q)
        for k, q in enumerate(pts):
            along = L.norm(np.array([rng.normal() * 0.3, rng.normal() * 0.3, -1.0], F32))
            nrm = L.norm(np.array([rng.normal() * 0.5, -1.0 if k % 2 else 1.0, 0.0], F32))
            card(q, along, nrm, rng.uniform(0.062, 0.088), int(rng.integers(0, 4)), "head", bend=0.3, curl=rng.uniform(-0.4, 0.4))
        if ta < 0.3:
            LANTERN_HANGS.append(pts[nl // 2] + np.array([0, 0, -0.004], F32))
    # leaves caught on tines
    for pts, r0, r1, tag in PT.antler_polys(s)[1:]:
        if rng.random() < 0.7:
            al = PT.arclen(pts)
            t = rng.uniform(0.3, 0.7)
            q = np.array([np.interp(t, al, pts[:, k]) for k in range(3)], F32)
            along = L.norm(np.array([rng.normal() * 0.6, rng.normal() * 0.6, -0.6], F32))
            card(q, along, rng.normal(size=3).astype(F32), rng.uniform(0.06, 0.08), int(rng.integers(0, 4)), "head", bend=0.35)
    # a lantern hanging from the brow tine
    bt = PT.antler_polys(s)[1][0]
    al = PT.arclen(bt)
    q = np.array([np.interp(0.55, al, bt[:, k]) for k in range(3)], F32)
    LANTERN_HANGS.append(q + np.array([0, 0, -0.008], F32))

# ---- hip belt clusters
for side, s in PT.SIDES:
    for k in range(9):
        a = s * rng.uniform(0.9, 2.1)
        p = np.array([0.142 * math.sin(a), 0.022 - 0.112 * math.cos(a), 1.06], F32)
        out = L.norm(np.array([math.sin(a), -math.cos(a) * 0.8, 0], F32))
        along = L.norm(np.array([rng.normal() * 0.3, rng.normal() * 0.3, -1.0], F32) + out * 0.3)
        card(p + out * 0.012, along, out + rng.normal(size=3).astype(F32) * 0.3, rng.uniform(0.055, 0.075),
             int(rng.integers(0, 4)), "torso", bend=0.25)

V = np.array(V, F32)
L.clear_scene()
ob = L.bpy_mesh("leaves_fol", V, np.array(F, np.int32))
me = ob.data
uvl = me.uv_layers.new(name="UVMap")
lv = np.zeros(len(me.loops), np.int32)
me.loops.foreach_get("vertex_index", lv)
UVa = np.array(UV, F32)
uvl.data.foreach_set("uv", UVa[lv].ravel())
L.set_attr(ob, "anchor", np.array(ANCH, F32))
a = me.attributes.new("lgroup", 'INT', 'POINT')
a.data.foreach_set("value", np.array(GRP, np.int32))
me.shade_smooth()
L.save_json(os.path.join(L.WORK, "lantern_hangs.json"), [list(map(float, h)) for h in LANTERN_HANGS])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.WORK, "leaves.blend"))
print("LEAVES cards=%d tris=%d lanterns=%d" % (len(F) // 2, len(F) * 2, len(LANTERN_HANGS)))
