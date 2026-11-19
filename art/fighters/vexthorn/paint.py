"""Texture-space painting for Vexthorn (style after the Caretaker's ct_paint.py): every texel knows its high-poly
surface position P, object normal N, AO and curvature; per-part painters return albedo (sRGB 0..1), roughness,
metalness and emission, plus a small-scale height for detail normals.

Palette rules: the 'bark' atlas is the tint2_bark material -> painted light/neutral (value detail, mild hue) and
multiplied in the material by BARK_FACTOR (the default dark bark colour). Everything in the 'bone' atlas is final
colour (skull, antlers, moss, lantern-heart, lanterns).
"""
import math
import numpy as np
import fblib as L
from fblib import F32, hexc, smoothstep, NOISE, NOISE2, NOISE3
import parts as PT

BARK_FACTOR_SRGB = "#614b3b"          # tint2 default colour (base colour factor)


def C(h):
    return hexc(h)


def mix(a, b, t):
    t = np.asarray(t, F32)
    if t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


def fbm(P, s, o=3, n=NOISE):
    return n.fbm(P * s, o)


def brush(P, s=40.0):
    return 0.6 * NOISE2.fbm(P * np.array([s, s, s * 0.35], F32), 2) + 0.4 * NOISE3(P * s * 0.5)


def common_light(col, N, ao, curv, top=0.10, cav=0.55, edge=0.18, aomin=0.42, P=None):
    """painted lighting: soft top light (warm), AO with cool shadow tint, cavity darkening, edge highlight."""
    nz = N[:, 2]
    col = col * (1.0 + top * 1.6 * nz)[:, None]
    col = col * (1.0 + 0.10 * np.clip(nz, 0, 1)[:, None] * np.array([1.0, 0.7, 0.2], F32))
    if P is not None:
        col = col * (0.82 + 0.20 * smoothstep(0.1, 1.6, P[:, 2]))[:, None]
    a = np.clip(ao, 0, 1)
    col = mix(col, col * np.array([0.78, 0.88, 1.12], F32), (1 - a) * 0.6)
    col = col * (aomin + (1 - aomin) * a)[:, None]
    cv = np.clip(curv, -1, 1)
    col = col * (1.0 - cav * np.clip(-cv * 1.6, 0, 1) * 0.5)[:, None]
    col = col + edge * np.clip(cv * 1.8 - 0.15, 0, 1)[:, None] * (0.55 + 0.45 * col)
    return col


def grain(part, P):
    return PT.flow_field(P, part.flow())


# ------------------------------------------------------------------------------------------ BARK (tinted)
def bark_tex(P, M, ao, curv, scale=1.0):
    """neutral bark: light fibrous ridges, mid plates, dark fissures; returns (col, rough, crack)."""
    h = PT.bark_height(P, M, scale)                                  # same field as the geometry
    fine = NOISE3.ridged(PT.aniso(P, M, 30.0 * scale, 260.0 * scale), 2)
    plates = np.clip(NOISE.fbm(PT.aniso(P, M, 3.0, 12.0), 3) * 1.4 + 0.5, 0, 1)
    crack = smoothstep(-0.3, -0.75, h)
    v = 0.60 + 0.14 * (plates - 0.5) + 0.32 * np.clip(h + 0.1, -0.2, 0.5) + 0.12 * (fine - 0.55)
    v = v * (1.0 - 0.72 * crack)
    col = np.stack([v, v, v], 1).astype(F32)
    # mild hue: warm plates, cooler grey weathered ridges, a little grey-green lichen
    hue = fbm(P, 3.5, 3, NOISE2)
    warm = np.clip(hue * 1.5 + 0.4, 0, 1)
    col = col * (np.array([0.97, 0.98, 1.0], F32) * (1 - warm)[:, None] + np.array([1.05, 0.98, 0.92], F32) * warm[:, None])
    ridge = np.clip(h * 2.0, 0, 1)
    col = mix(col, col * np.array([0.98, 1.0, 1.04], F32) + 0.04, ridge * 0.6)
    lich = np.clip(NOISE.fbm(P * 9.0 + 4.0, 3) * 2.6 - 1.1, 0, 1) * smoothstep(0.2, 0.8, ao) * (1 - crack)
    col = mix(col, col * np.array([0.95, 1.08, 0.92], F32) + 0.07, lich * 0.55)
    rough = 0.8 + 0.15 * crack - 0.1 * ridge
    return col, rough.astype(F32), crack


def bark_light(col, P, N, ao, curv):
    return common_light(col, N, ao, curv, top=0.08, cav=0.6, edge=0.22, aomin=0.38, P=P)


def heart_glow(P, N, m=None, k=1.0):
    """amber light from the lantern-heart on surfaces inside the ribcage (emission, sRGB)."""
    to_h = PT.HEART_C - P
    d = np.linalg.norm(to_h, axis=1)
    facing = np.clip((N * to_h).sum(1) / np.maximum(d, 1e-6), 0, 1)
    c, r = PT.CAVITY
    q = np.linalg.norm((P - c) / np.array(r, F32), axis=1)
    inside = smoothstep(1.55, 1.05, q)
    f = inside * facing ** 0.8 * (1.0 / (1.0 + (d / 0.075) ** 2))
    col = C("#ff8a1e")[None, :] * np.clip(f * 1.6 * k, 0, 1)[:, None]
    return col, f


def paint_torso(P, N, ao, curv, part):
    M = grain(part, P)
    m = part.masks(P, N)
    col, rough, crack = bark_tex(P, M, ao, curv, 1.0)
    dt = m["d_tag"]
    # ribs a touch paler and smoother on top (weathered, like old bone-wood)
    rib = smoothstep(0.006, -0.002, dt["rib"])
    col = mix(col, col * 1.12, rib * 0.6)
    # the vine belt: green-tinted bark, lighter
    belt = dt["belt"] < 0.003
    col[belt] = mix(col[belt], col[belt] * np.array([0.95, 1.1, 0.85], F32) + 0.05, 0.8)
    # hip slabs: big plates, a little lighter with darker rims
    slab = m["slab"]
    col[slab] = col[slab] * 1.06
    # inner surfaces of the cavity: darker, soot
    inner = m["inner"]
    col = col * (1 - 0.45 * inner)[:, None]
    col = bark_light(col, P, N, ao, curv)
    em, f = heart_glow(P, N)
    # embers: thin glowing cracks on the chest near the heart
    near = smoothstep(0.22, 0.08, m["heart_d"])
    ember = crack * near * np.clip(NOISE.fbm(P * 14.0, 2) * 2.0 + 0.4, 0, 1)
    em = em + C("#ff7a14")[None, :] * np.clip(ember * 1.4, 0, 1)[:, None]
    return col, rough, None, np.clip(em, 0, 1)


def paint_shoulder(P, N, ao, curv, part):
    M = grain(part, P)
    m = part.masks(P, N)
    col, rough, crack = bark_tex(P, M, ao, curv, 1.15)
    # upper surfaces under the moss: green stain (mild)
    up = np.clip(N[:, 2], 0, 1) ** 2
    col = mix(col, col * np.array([0.9, 1.05, 0.88], F32), up * 0.5)
    fu = m["fungus"]
    if fu.any():
        n = fbm(P[fu], 60.0, 2)
        fc = mix(C("#efe1c4"), C("#d9b98a"), np.clip(n + 0.5, 0, 1))
        rim = np.clip(-N[fu, 2], 0, 1)
        col[fu] = mix(fc, C("#b98c5c"), rim * 0.6)
        rough[fu] = 0.7
    col = bark_light(col, P, N, ao, curv)
    return col, rough, None, None


def paint_arm(P, N, ao, curv, part):
    M = grain(part, P)
    m = part.masks(P, N)
    col, rough, crack = bark_tex(P, M, ao, curv, 1.15)
    rg = m["rings"]
    col[rg] = col[rg] * np.array([1.08, 1.04, 0.98], F32)
    th = m["thorn"]
    col[th] = mix(col[th], np.full(3, 0.3, F32), 0.6)
    col = bark_light(col, P, N, ao, curv)
    return col, rough, None, None


def paint_hand(P, N, ao, curv, part):
    M = grain(part, P)
    m = part.masks(P, N)
    col, rough, crack = bark_tex(P, M, ao, curv, 1.6)
    cl = m["claw"]
    if cl.any():
        t = np.clip(m["claw_t"][cl], 0, 1)
        base = mix(np.full(3, 0.14, F32), np.full(3, 0.22, F32), np.clip(fbm(P[cl], 80.0) + 0.5, 0, 1))
        tip = np.array([0.95, 0.9, 0.8], F32)
        cc = mix(base, tip, smoothstep(0.45, 1.0, t) * 0.9)
        streak = NOISE.ridged(P[cl] * np.array([400, 400, 400], F32), 2)
        cc = cc * (0.9 + 0.15 * streak)[:, None]
        col[cl] = cc
        rough[cl] = 0.35 + 0.15 * (1 - t)
    col = bark_light(col, P, N, ao, curv)
    return col, rough, None, None


def paint_leg(P, N, ao, curv, part):
    M = grain(part, P)
    m = part.masks(P, N)
    col, rough, crack = bark_tex(P, M, ao, curv, 1.0)
    hf = m["hoof"]
    if hf.any():
        ph = P[hf]
        bands = 0.5 + 0.5 * np.sin(ph[:, 2] * 260.0 + NOISE(ph * 40.0) * 2.0)
        hc = mix(np.full(3, 0.12, F32), np.full(3, 0.2, F32), bands * 0.6)
        hc = mix(hc, np.array([0.33, 0.3, 0.27], F32), smoothstep(0.02, 0.0, ph[:, 2]))    # worn sole edge
        col[hf] = hc
        rough[hf] = 0.45
    dc = m["dewclaw"] & ~hf
    col[dc] = mix(col[dc], np.full(3, 0.16, F32), 0.85)
    rough[dc] = 0.45
    cor = m["coronet"] & ~hf
    if cor.any():
        col[cor] = col[cor] * np.array([0.82, 0.86, 0.8], F32)          # matted fur / moss band (tinted)
    col = bark_light(col, P, N, ao, curv)
    # earth on the hooves / lower shins
    dirt = smoothstep(0.16, 0.02, P[:, 2]) * np.clip(0.5 + fbm(P, 9.0), 0, 1)
    col = mix(col, col * np.array([0.85, 0.8, 0.75], F32), dirt * 0.5)
    return col, rough, None, None


# ------------------------------------------------------------------------------------------ BONE atlas (final colours)
MOSS = [C("#16260e"), C("#283f16"), C("#4d6824"), C("#8b8a48")]


def paint_moss(P, N, ao, curv, part):
    n1 = fbm(P, 18.0, 3, NOISE3)
    n2 = fbm(P + 3.3, 55.0, 2, NOISE2)
    col = mix(MOSS[0], MOSS[1], np.clip(0.5 + 0.9 * n1 + 0.5 * (ao - 0.6), 0, 1))
    col = mix(col, MOSS[2], np.clip(n2 * 1.3 + 0.15 * N[:, 2] - 0.1, 0, 1) * np.clip(ao * 1.2, 0, 1) * 0.8)
    col = mix(col, MOSS[3], np.clip(NOISE(P * 90.0) * 2.2 - 1.3, 0, 1) * 0.55)
    # fallen leaf litter flecks (burnt orange) caught in the moss
    lit = np.clip(NOISE2(P * 70.0) * 3.0 - 1.9, 0, 1)
    col = mix(col, C("#b5521d"), lit * 0.8)
    col = common_light(col, N, ao, curv, top=0.14, cav=0.4, edge=0.1, aomin=0.35)
    return col, np.full(len(P), 0.95, F32), None, None


BONE = C("#bcae8d")


def bone_base(P, N, ao, curv):
    n1 = fbm(P, 9.0)
    st = np.clip(fbm(P + 7.7, 14.0, 3, NOISE2) * 1.9 - 0.05, 0, 1)
    col = mix(BONE, C("#c4b48f"), np.clip(0.5 + n1, 0, 1) * 0.5)
    col = mix(col, C("#86704f"), st * 0.6)                                   # tea stains
    cr = smoothstep(0.86, 0.95, NOISE.ridged(P * 34.0, 3))                   # hairline cracks
    col = mix(col, C("#5a4732"), cr * 0.7)
    col = col * (1 + 0.05 * brush(P, 60))[:, None]
    return col, cr


def paint_skull(P, N, ao, curv, part):
    m = part.masks(P, N)
    col, cr = bone_base(P, N, ao, curv)
    # dirt / moss creeping onto the back and underside
    U = PT.skull_unscale(P)
    back = smoothstep(0.0, 0.07, U[:, 1]) * np.clip(0.5 + fbm(P, 20.0, 3, NOISE3), 0, 1)
    col = mix(col, C("#56622e"), back * 0.55)
    under = smoothstep(-0.2, -0.8, N[:, 2])
    col = mix(col, col * np.array([0.75, 0.7, 0.62], F32), under * 0.5)
    sock = m["socket"]
    col = mix(col, C("#1c130e"), np.clip(sock * 1.5 - 0.15, 0, 1) * 0.92)
    col[m["mouth"]] = col[m["mouth"]] * 0.25
    col[m["teeth"]] = mix(C("#e9dfc4"), C("#b5a27c"), np.clip(fbm(P[m["teeth"]], 90.0) + 0.4, 0, 1) * 0.5)
    nose = m["nose"]
    col[nose] = mix(col[nose], C("#3a2a1c"), 0.55)
    col = common_light(col, N, ao, curv, top=0.10, cav=0.7, edge=0.14, aomin=0.35)
    rough = np.full(len(P), 0.62, F32)
    rough = rough - 0.12 * np.clip(curv, 0, 1)
    em = np.zeros((len(P), 3), F32)
    eye = m["eye"]
    if eye.any():
        U = PT.skull_unscale(P[eye])
        g = np.zeros(len(U), F32)
        for i, s in enumerate((1, -1)):
            c = PT.SKULL_EYE[i] - PT.socket_axis(s) * 0.011
            ax = PT.socket_axis(s)
            dd = np.linalg.norm(U - c, axis=1)
            front = ((U - c) @ ax) / 0.0112
            g = np.maximum(g, (dd < 0.0128) * np.clip(0.5 + 0.5 * front, 0, 1))
        hot = mix(C("#e83a00"), C("#ffb028"), smoothstep(0.6, 1.0, g))
        col[eye] = hot
        em[eye] = hot * (0.32 + 0.18 * g)[:, None]
        rough[eye] = 0.3
    # faint ember glow deep in the sockets around the eyes
    glow = np.clip(sock - 0.35, 0, 1) * (~eye)
    em = em + C("#ff6a0a")[None, :] * (glow * 0.35)[:, None]
    return col, rough, None, em


def paint_antler(P, N, ao, curv, part):
    m = part.masks(P, N)
    t = np.clip(m["tip"], 0, 1)
    n1 = fbm(P, 12.0)
    base = mix(C("#3a2c20"), C("#5a4836"), np.clip(0.5 + n1, 0, 1))
    mid = mix(C("#8f7a5c"), C("#a8936f"), np.clip(0.5 + n1, 0, 1))
    tipc = C("#efe6d0")
    col = mix(base, mid, smoothstep(0.0, 0.45, t))
    col = mix(col, tipc, smoothstep(0.55, 0.95, t))
    M = PT.flow_field(P, part.flow(), 0.01)
    gr = NOISE.ridged(PT.aniso(P, M, 14.0, 120.0), 2)
    col = col * (0.82 + 0.25 * gr)[:, None]
    col = mix(col, C("#3a2c20"), smoothstep(0.35, 0.0, gr) * 0.5 * (1 - smoothstep(0.6, 0.9, t)))
    # moss + lichen on the lower beams
    mo = np.clip(fbm(P + 2.0, 14.0, 3, NOISE2) * 2.4 - 0.5, 0, 1) * smoothstep(0.55, 0.15, t) * np.clip(N[:, 2] + 0.3, 0, 1)
    col = mix(col, mix(MOSS[1], MOSS[2], np.clip(fbm(P, 50.0) + 0.5, 0, 1)), mo * 0.85)
    col = common_light(col, N, ao, curv, top=0.12, cav=0.6, edge=0.18, aomin=0.38)
    rough = (0.7 - 0.3 * smoothstep(0.5, 1.0, t) + 0.25 * mo).astype(F32)
    return col, rough, None, None


def paint_heart(P, N, ao, curv, part):
    m = part.masks(P, N)
    core = m["core"]
    U = PT.HEART_C + (P - PT.HEART_C) / PT.HS
    # frame: aged dark bronze; roots: wood
    n = fbm(P, 60.0)
    col = mix(C("#3d2f1f"), C("#6b5333"), np.clip(n + 0.5, 0, 1))
    col = mix(col, C("#c99a52"), np.clip(curv * 1.5 - 0.1, 0, 1) * 0.6)      # rubbed brass highlights
    verd = np.clip(fbm(P, 40.0, 2, NOISE3) * 2.0 - 0.6, 0, 1) * (1 - np.clip(curv, 0, 1))
    col = mix(col, C("#4f7a64"), verd * 0.35)
    metal = np.full(len(P), 0.85, F32)
    rough = np.full(len(P), 0.42, F32)
    root = (U[:, 2] > PT.HEART_C[2] + 0.088) | (U[:, 2] < PT.HEART_C[2] - 0.066)
    col[root] = mix(C("#3a2a1c"), C("#5d4630"), np.clip(fbm(P[root], 40.0) + 0.5, 0, 1))
    metal[root] = 0.0
    rough[root] = 0.85
    col = common_light(col, N, ao, curv, top=0.05, cav=0.5, edge=0.1, aomin=0.45)
    # the inner light falls on the bars from inside
    to_c = PT.HEART_C - P
    dc = np.linalg.norm(to_c, axis=1)
    inward = np.clip((N * to_c).sum(1) / np.maximum(dc, 1e-6), 0, 1)
    em = C("#ff7a10")[None, :] * (inward * (1 - root) * 0.45)[:, None]
    if core.any():
        q = (U[core] - PT.HEART_C)
        r = np.linalg.norm(q / np.array([0.04, 0.03, 0.05], F32), axis=1)
        facet = 0.5 + 0.5 * NOISE.ridged(P[core] * 160.0, 2)
        hot = mix(C("#fff3b8"), C("#ffb02a"), smoothstep(0.2, 0.9, r))
        hot = mix(hot, C("#ff5a08"), smoothstep(0.8, 1.15, r) * 0.8)
        hot = hot * (0.85 + 0.2 * facet)[:, None]
        col[core] = hot
        em[core] = hot
        metal[core] = 0.0
        rough[core] = 0.15
    return col, rough, metal, em


def paint_lantern(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = fbm(P, 200.0)
    col = mix(C("#2a2420"), C("#4a3f33"), np.clip(n + 0.5, 0, 1))
    col = mix(col, C("#a57d45"), np.clip(curv * 1.5, 0, 1) * 0.5)
    metal = np.full(len(P), 0.8, F32)
    rough = np.full(len(P), 0.5, F32)
    cord = m["cord"]
    col[cord] = mix(C("#5a4127"), C("#7d6040"), np.clip(fbm(P[cord], 500.0) + 0.5, 0, 1))
    metal[cord] = 0.0
    rough[cord] = 0.9
    col = common_light(col, N, ao, curv, top=0.05, cav=0.4, edge=0.1, aomin=0.5)
    em = np.zeros((len(P), 3), F32)
    gl = m["glass"]
    if gl.any():
        q = P[gl] - part.off - np.array([0, 0, -0.061], F32)
        r = np.linalg.norm(q / np.array([0.011, 0.011, 0.0125], F32), axis=1)
        hot = mix(C("#ffe9a0"), C("#ff9a20"), smoothstep(0.3, 1.1, r))
        col[gl] = hot
        em[gl] = hot
        metal[gl] = 0.0
        rough[gl] = 0.2
    return col, rough, metal, em


PAINTERS = {"torso": paint_torso, "shoulder_l": paint_shoulder, "shoulder_r": paint_shoulder, "arm_l": paint_arm,
            "arm_r": paint_arm, "hand_l": paint_hand, "hand_r": paint_hand, "leg_l": paint_leg, "leg_r": paint_leg,
            "moss": paint_moss, "skull": paint_skull, "antler_l": paint_antler, "antler_r": paint_antler,
            "heart": paint_heart, "lantern": paint_lantern}


# ------------------------------------------------------------------------------------------ detail normals
def height_detail(part, P, M=None):
    n = part.name
    if part.atlas == "bark" and M is not None:
        sc = {"hand_l": 1.6, "hand_r": 1.6, "arm_l": 1.15, "arm_r": 1.15}.get(n, 1.0)
        return 0.00055 * NOISE3.ridged(PT.aniso(P, M, 30.0 * sc, 260.0 * sc), 2) + 0.0004 * PT.bark_height(P, M, sc * 2.2)
    if n == "moss":
        return 0.0006 * NOISE.fbm(P * 220.0, 2)
    if n in ("skull",):
        return 0.00018 * NOISE.ridged(P * 260.0, 2) + 0.00012 * NOISE2(P * 600.0)
    if n.startswith("antler"):
        return 0.0003 * NOISE2.fbm(P * 300.0, 2)
    return 0.0


def detail_normals(part, P, N, strength=1.0):
    M = PT.flow_field(P, part.flow()) if part.atlas == "bark" else None
    e = 0.0005
    h0 = height_detail(part, P, M)
    if np.isscalar(h0):
        return N
    g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3, F32); d[k] = e
        g[:, k] = (height_detail(part, P + d, M) - height_detail(part, P - d, M)) / (2 * e)
    gt = g - (g * N).sum(1, keepdims=True) * N
    Nn = N - strength * gt
    return Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-6)
