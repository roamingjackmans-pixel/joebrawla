"""Texture-space painting for Archmagister Tock (same pipeline as Vexthorn).  Painters return albedo (sRGB 0..1),
roughness, metalness, emission.  tint1_robe and tint2_trim are painted light/neutral and multiplied in the material
by ROBE_FACTOR / TRIM_FACTOR (their default colours); everything in the body and staff atlases is final colour.
"""
import math
import numpy as np
import fblib as L
from fblib import F32, hexc, smoothstep, NOISE, NOISE2, NOISE3
import parts as PT
from sdfx import aniso, flow_field

ROBE_FACTOR_SRGB = "#203070"         # deep academic blue
TRIM_FACTOR_SRGB = "#d8ab4e"         # brass
GLOW = "#6ff2ff"                     # Tock's time-magic glow (aqua)


def C(h):
    return hexc(h)


def mix(a, b, t):
    t = np.asarray(t, F32)
    if t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


def fbm(P, s, o=3, n=NOISE):
    return n.fbm(P * s, o)


def common_light(col, N, ao, curv, top=0.10, cav=0.55, edge=0.18, aomin=0.42):
    nz = N[:, 2]
    col = col * (1.0 + top * 1.6 * nz)[:, None]
    a = np.clip(ao, 0, 1)
    col = mix(col, col * np.array([0.8, 0.88, 1.1], F32), (1 - a) * 0.5)
    col = col * (aomin + (1 - aomin) * a)[:, None]
    cv = np.clip(curv, -1, 1)
    col = col * (1.0 - cav * np.clip(-cv * 1.6, 0, 1) * 0.5)[:, None]
    col = col + edge * np.clip(cv * 1.8 - 0.15, 0, 1)[:, None] * (0.55 + 0.45 * col)
    return col


# ------------------------------------------------------------------------------------------ materials
def brass(P, N, ao, cv):
    n1 = fbm(P, 9.0)
    col = mix(C("#9c6f22"), C("#d3a447"), np.clip(0.5 + n1, 0, 1))
    tarn = np.clip((1 - ao) * 1.6 + np.clip(-cv, 0, 1) * 0.8 + fbm(P + 3.0, 25.0, 2, NOISE2) * 0.4 - 0.25, 0, 1)
    col = mix(col, C("#3e2c12"), tarn * 0.75)
    verd = np.clip(fbm(P, 30.0, 2, NOISE3) * 2.2 - 0.8, 0, 1) * tarn
    col = mix(col, C("#4c7d68"), verd * 0.55)
    pol = np.clip(cv * 2.0 - 0.1, 0, 1)
    col = mix(col, C("#f7e09a"), pol * 0.55)
    scratch = np.clip(NOISE.ridged(P * np.array([900, 90, 300], F32), 2) - 0.8, 0, 1) * 2.5
    col = col * (1 + 0.12 * scratch)[:, None]
    rough = 0.26 + 0.38 * tarn + 0.06 * fbm(P, 60.0) - 0.08 * pol
    return col, np.clip(rough, 0.15, 0.85).astype(F32), np.clip(1.0 - 0.4 * verd, 0, 1).astype(F32)


def walnut(P, N, ao, cv, M):
    g = NOISE.fbm(aniso(P, M, 6.0, 140.0), 3)
    rings = 0.5 + 0.5 * np.sin(g * 18.0)
    col = mix(C("#2f1b10"), C("#6a3f24"), rings * 0.7 + 0.15)
    col = mix(col, C("#1d0f07"), np.clip(NOISE2.fbm(aniso(P, M, 3.0, 60.0), 2) * 2.0 - 0.6, 0, 1) * 0.6)
    col = mix(col, C("#8a5a32"), np.clip(cv * 1.6 - 0.2, 0, 1) * 0.5)          # worn lacquer edges
    rough = 0.36 + 0.2 * (1 - rings) * 0.5 + 0.1 * np.clip(-cv, 0, 1)
    return col, rough.astype(F32), np.zeros(len(P), F32)


def steel(P, N, ao, cv):
    col = mix(C("#141a28"), C("#36425e"), np.clip(0.5 + fbm(P, 40.0), 0, 1))
    col = mix(col, C("#a5b4cf"), np.clip(cv * 1.8 - 0.2, 0, 1) * 0.5)
    return col, np.full(len(P), 0.3, F32), np.full(len(P), 1.0, F32)


def glow_col(P, centre=None, rad=0.012):
    if centre is None:
        return C(GLOW)[None, :].repeat(len(P), 0)
    r = np.linalg.norm(P - centre, axis=1) / rad
    return mix(C("#f4ffff"), C(GLOW), smoothstep(0.2, 1.0, r))


def paint_tagged(P, N, ao, cv, part, extra=None):
    m = part.masks(P, N)
    col = np.zeros((len(P), 3), F32)
    rough = np.full(len(P), 0.5, F32)
    metal = np.zeros(len(P), F32)
    em = np.zeros((len(P), 3), F32)
    M = flow_field(P, part.flow())
    for tag, sel in m.items():
        if not sel.any():
            continue
        p, n, a, c = P[sel], N[sel], ao[sel], cv[sel]
        if tag == "brass":
            cc, rr, mm = brass(p, n, a, c)
        elif tag == "walnut":
            cc, rr, mm = walnut(p, n, a, c, M[sel])
        elif tag in ("steel",):
            cc, rr, mm = steel(p, n, a, c)
        elif tag in ("glow", "lens", "eye"):
            cc = glow_col(p)
            rr, mm = np.full(len(p), 0.15, F32), np.zeros(len(p), F32)
            em[sel] = cc * {"glow": 1.0, "lens": 0.9, "eye": 0.45}[tag]
            if tag == "lens":
                cc = mix(cc, C("#dffcff"), 0.3)
        elif tag == "dial":
            cc, rr, mm, ee = dial(p, n, part)
            em[sel] = ee
        elif tag == "wire":
            cc, rr, mm = wire(p, n, a, c, part, M[sel])
        else:
            cc, rr, mm = brass(p, n, a, c)
        col[sel], rough[sel], metal[sel] = cc, rr, mm
    lit = common_light(col, N, ao, cv, top=0.06, cav=0.45, edge=0.12, aomin=0.45)
    glowing = em.max(1) > 0
    col = np.where(glowing[:, None], col, lit)
    return col, rough, metal, em


def wire(P, N, ao, cv, part, M):
    strands = NOISE.ridged(aniso(P, M, 20.0, 700.0), 2)
    col = mix(C("#8f8a80"), C("#ece8dd"), np.clip(strands * 1.2 - 0.1, 0, 1))
    root = smoothstep(1.66, 1.60, P[:, 2]) * 0 + smoothstep(1.58, 1.66, P[:, 2])
    col = mix(col, C("#c99a4a"), root * 0.35)                                     # brass at the roots
    col = col * (0.55 + 0.45 * np.clip(ao, 0, 1))[:, None]
    return col, (0.3 + 0.15 * (1 - strands)).astype(F32), np.full(len(P), 0.85, F32)


# ------------------------------------------------------------------------------------------ clock dial
GLYPH = {1: "I", 2: "II", 3: "III", 4: "IIII", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"}


def seg_d(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    t = np.clip(((px - ax) * abx + (py - ay) * aby) / max(abx * abx + aby * aby, 1e-12), 0, 1)
    return np.sqrt((px - ax - t * abx) ** 2 + (py - ay - t * aby) ** 2)


def glyph_d(gx, gy, s, hh=0.0072, cw=0.0072):
    """distance to the strokes of roman numeral string s centred at (0,0) (gx right, gy up)."""
    widths = [0.0034 if ch == "I" else cw for ch in s]
    gap = 0.0018
    tot = sum(widths) + gap * (len(s) - 1)
    x0 = -tot / 2
    d = np.full(gx.shape, 9.0, F32)
    for ch, w in zip(s, widths):
        cx = x0 + w / 2
        if ch == "I":
            d = np.minimum(d, seg_d(gx, gy, cx, -hh, cx, hh))
        elif ch == "V":
            d = np.minimum(d, seg_d(gx, gy, cx - w / 2, hh, cx, -hh))
            d = np.minimum(d, seg_d(gx, gy, cx + w / 2, hh, cx, -hh))
        elif ch == "X":
            d = np.minimum(d, seg_d(gx, gy, cx - w / 2, hh, cx + w / 2, -hh))
            d = np.minimum(d, seg_d(gx, gy, cx + w / 2, hh, cx - w / 2, -hh))
        x0 += w + gap
    return d


def dial_marks(u, v, R=PT.CLOCK_R, num_r=0.054):
    """glow intensity 0..1 of numerals + minute ticks on a dial of radius R at dial coords (u, v)."""
    r = np.sqrt(u * u + v * v)
    ang = np.arctan2(u, v)                      # clockwise from 12
    g = np.zeros(u.shape, F32)
    sc = R / PT.CLOCK_R
    for h in range(1, 13):
        th = math.radians(h * 30)
        d = (math.sin(th), math.cos(th))
        t = (math.cos(th), -math.sin(th))
        cu, cv_ = d[0] * num_r * sc, d[1] * num_r * sc
        gx = (u - cu) * t[0] + (v - cv_) * t[1]
        gy = (u - cu) * d[0] + (v - cv_) * d[1]
        near = (np.abs(gx) < 0.02 * sc) & (np.abs(gy) < 0.012 * sc)
        if near.any():
            dd = glyph_d(gx[near] / sc, gy[near] / sc, GLYPH[h]) * sc
            g[near] = np.maximum(g[near], np.clip(1 - (dd - 0.0007 * sc) / (0.0006 * sc), 0, 1))
    k = np.round(ang / (2 * np.pi / 60))
    da = np.abs(ang - k * (2 * np.pi / 60)) * r
    hour = (np.mod(k, 5) == 0)
    tw = np.where(hour, 0.0013, 0.0006) * sc
    tick = (da < tw) & (r > (R - np.where(hour, 0.012, 0.007) * sc)) & (r < R - 0.002 * sc)
    g = np.maximum(g, tick.astype(F32))
    ring = np.abs(r - 0.036 * sc) < 0.0006 * sc
    g = np.maximum(g, ring.astype(F32) * 0.6)
    return g, r


def dial(P, N, part):
    if part.name == "clock":
        R = PT.clock_frame()
        q = P - PT.CLOCK_C
        u, v, z = q @ R[:, 0], q @ R[:, 1], q @ R[:, 2]
        g, r = dial_marks(u, v)
        front = z > -0.0005
    else:                                          # the little clock on the staff head (both faces)
        gq, ax, sd, top, bot = PT.staff_pts()
        ad = PT.norm(np.cross(ax, sd))
        c = top - ax * 0.07
        q = P - c
        side = np.sign(q @ sd)
        u, v = (q @ ad) * side, q @ ax
        g, r = dial_marks(u, v, 0.044, 0.031)
        front = np.ones(len(P), bool)
    base = mix(C("#0b1428"), C("#1b2b52"), np.clip(0.5 + fbm(P, 50.0) * 0.6, 0, 1))
    fil = np.clip(np.sin(np.arctan2(u, v) * 24 + r * 900) * 0.5 + 0.5, 0, 1) * smoothstep(0.03, 0.02, r) * 0.25
    base = mix(base, C("#b48a3a"), fil)
    glow = g * front
    col = mix(base, C("#c8fbff"), glow)
    em = C(GLOW)[None, :] * glow[:, None]
    return col, np.full(len(P), 0.22, F32), np.zeros(len(P), F32), em


# ------------------------------------------------------------------------------------------ cloth (tinted)
def cloth(P, N, ao, cv, lining=None):
    weave = 0.5 + 0.25 * (np.sin(P[:, 0] * 2200) * np.sin(P[:, 2] * 2200) + np.sin(P[:, 1] * 2200) * np.sin(P[:, 2] * 2100))
    n1 = fbm(P, 4.0)
    v = 0.86 + 0.08 * n1 + 0.04 * (weave - 0.5)
    col = np.stack([v, v, v], 1).astype(F32)
    # faint embroidered gear rosettes (lighter thread) scattered on the robe
    cell = np.floor(P * 7.0)
    h = np.sin(cell[:, 0] * 12.9898 + cell[:, 1] * 78.233 + cell[:, 2] * 37.719) * 43758.5453
    h = h - np.floor(h)
    cc = (cell + 0.5) / 7.0
    d = np.linalg.norm(P - cc, axis=1)
    ang = np.arctan2(P[:, 2] - cc[:, 2], P[:, 0] - cc[:, 0] + (P[:, 1] - cc[:, 1]))
    ros = (np.abs(d - (0.022 + 0.004 * np.cos(ang * 10))) < 0.0018) & (h > 0.55)
    col[ros] = col[ros] * 1.12 + 0.04
    # wear: lighter on folds' crests and the hem, darker in the folds
    col = col * (1 + 0.12 * np.clip(cv * 1.5, -1, 1))[:, None]
    hem = smoothstep(0.35, 0.1, P[:, 2])
    col = col * (1 - 0.18 * hem * np.clip(0.5 + fbm(P, 9.0), 0, 1))[:, None]
    if lining is not None:
        col[lining] = col[lining] * np.array([0.55, 0.5, 0.62], F32)
    col = common_light(col, N, ao, cv, top=0.08, cav=0.5, edge=0.0, aomin=0.5)
    return col, np.full(len(P), 0.88, F32), np.zeros(len(P), F32)


def paint_robe(P, N, ao, cv, part):
    m = part.masks(P, N)
    col, rough, metal = cloth(P, N, ao, cv, m.get("lining"))
    return col, rough, metal, None


def paint_hat(P, N, ao, cv, part):
    m = part.masks(P, N)
    col, rough, metal = cloth(P, N, ao, cv)
    b = m["board"]
    col[b] = col[b] * 0.82                     # stiff board slightly darker
    return col, rough, metal, None


def emboss(P, N):
    """brass trim pattern: running gear teeth + rivet dots (value 0..1)."""
    s = np.sin(P[:, 0] * 340 + P[:, 2] * 220) * np.sin(P[:, 1] * 300 - P[:, 2] * 260)
    teeth = np.clip(s * 3.0, -1, 1) * 0.5 + 0.5
    return teeth


def paint_trim(P, N, ao, cv, part):
    m = part.masks(P, N)
    e = emboss(P, N)
    v = 0.78 + 0.18 * e
    col = np.stack([v, v, v * 0.96], 1).astype(F32)
    col = col * (0.85 + 0.15 * np.clip(0.5 + fbm(P, 30.0), 0, 1))[:, None]
    tarn = np.clip((1 - ao) * 1.4 + np.clip(-cv, 0, 1) - 0.3, 0, 1)
    col = col * (1 - 0.55 * tarn)[:, None]
    col = col + 0.15 * np.clip(cv * 2 - 0.2, 0, 1)[:, None]
    bk = m.get("buckle")
    if bk is not None and bk.any():
        q = P[bk] - PT.BUCKLE_C
        r = np.sqrt(q[:, 0] ** 2 + (q[:, 2]) ** 2)
        col[bk] = col[bk] * (0.85 + 0.25 * (np.abs(r - 0.016) < 0.0015))[:, None]
    col = common_light(col, N, ao, cv, top=0.04, cav=0.3, edge=0.08, aomin=0.55)
    rough = (0.3 + 0.25 * tarn + 0.1 * (1 - e)).astype(F32)
    return col, rough, np.full(len(P), 1.0, F32), None


def paint_tassel(P, N, ao, cv, part):
    m = part.masks(P, N)
    th = 0.5 + 0.5 * np.sin(np.arctan2(P[:, 0] - P[:, 0].mean(), P[:, 1] - P[:, 1].mean()) * 40)
    v = 0.75 + 0.2 * th
    col = np.stack([v, v, v * 0.95], 1).astype(F32)
    col = common_light(col, N, ao, cv, top=0.05, cav=0.4, edge=0.05, aomin=0.5)
    return col, np.full(len(P), 0.5, F32), np.full(len(P), 0.7, F32), None


def paint_body(P, N, ao, cv, part):
    return paint_tagged(P, N, ao, cv, part)


def paint_clock_hand(P, N, ao, cv, part):
    col, rough, metal = steel(P, N, ao, cv)
    rim = np.clip(cv * 2.0, 0, 1)
    col = mix(col, C("#e2bb62"), rim * 0.8)
    return col, rough, metal, None


def paint_beard(P, N, ao, cv, part):
    M = flow_field(P, part.flow(), 0.006)
    col, rough, metal = wire(P, N, ao, cv, part, M)
    col = common_light(col, N, ao, cv, top=0.08, cav=0.4, edge=0.1, aomin=0.5)
    return col, rough, metal, None


PAINTERS = {"robe": paint_robe, "hat": paint_hat, "trim": paint_trim, "tassel": paint_tassel,
            "clock_hour": paint_clock_hand, "clock_min": paint_clock_hand, "beard": paint_beard}


class _Default(dict):
    def __missing__(self, k):
        return paint_body


PAINTERS = _Default(PAINTERS)


# ------------------------------------------------------------------------------------------ detail normals
def height_detail(part, P, M=None):
    a = part.atlas
    if a in ("robe",):
        return 0.00012 * (np.sin(P[:, 0] * 2200) * np.sin(P[:, 2] * 2200) + np.sin(P[:, 1] * 2200) * np.sin(P[:, 2] * 2100))
    if a == "trim":
        return 0.0005 * emboss(P, None)
    if part.name == "beard":
        return 0.0
    return 0.00008 * NOISE.fbm(P * 400.0, 2)


def detail_normals(part, P, N, strength=1.0):
    e = 0.0004
    h0 = height_detail(part, P)
    if np.isscalar(h0):
        return N
    g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3, F32); d[k] = e
        g[:, k] = (height_detail(part, P + d) - height_detail(part, P - d)) / (2 * e)
    gt = g - (g * N).sum(1, keepdims=True) * N
    Nn = N - strength * gt
    return Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-6)
