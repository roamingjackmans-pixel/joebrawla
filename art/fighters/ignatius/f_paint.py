"""Texture-space painting for Foreman Ignatius (every texel knows its high-poly position P, object normal N, AO and
curvature; per-part functions return albedo (sRGB), roughness, metalness, emission).  DJ3D storybook look: clear
local colours, big soft value shifts, painted light from above, warm cavities, worn light edges.  Foundry palette:
soot, blackened iron, scorched leather, ember orange glow.
"""
import math
import numpy as np
import jb_lib as L
from jb_lib import F32, hexc, smoothstep, NOISE, NOISE2, NOISE3
import f_parts as CP
import f_props as PR


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


def common_light(col, N, ao, curv, top=0.10, cav=0.55, edge=0.18, aopow=1.0, aomin=0.42, P=None, warm_low=True):
    """painted lighting: soft top light, AO with cool shadow tint, cavity darkening, edge highlight, + a faint
    warm forge bounce from below (he lives next to a furnace)."""
    nz = N[:, 2]
    col = col * (1.0 + top * 1.6 * nz)[:, None]
    col = col * (1.0 + 0.10 * np.clip(nz, 0, 1)[:, None] * np.array([1.0, 0.8, 0.5], F32))
    if warm_low:
        col = col + (0.05 * np.clip(-nz, 0, 1))[:, None] * C("#ff7a2a") * (0.4 + 0.6 * col)
    if P is not None:
        col = col * (0.84 + 0.18 * smoothstep(0.15, 1.55, P[:, 2]))[:, None]
    a = np.clip(ao, 0, 1) ** aopow
    col = mix(col, col * np.array([0.82, 0.86, 1.08], F32), (1 - a) * 0.55)
    col = col * (aomin + (1 - aomin) * a)[:, None]
    cv = np.clip(curv, -1, 1)
    col = col * (1.0 - cav * np.clip(-cv * 1.6, 0, 1) * 0.5)[:, None]
    col = col + edge * np.clip(cv * 1.8 - 0.15, 0, 1)[:, None] * (0.55 + 0.45 * col)
    return col


def soot(P, N, amt=0.5, scale=6.0):
    """soot smudges: darker on downward faces and in blotches."""
    s = np.clip(fbm(P + 3.3, scale, 3, NOISE3) * 1.3 + 0.25, 0, 1)
    s = s * (0.6 + 0.4 * np.clip(-N[:, 2] + 0.3, 0, 1))
    return np.clip(s * amt, 0, 1)


# ------------------------------------------------------------------------------------------ chainmail
RING_DU = 0.0165
RING_DV = 0.0115
RING_R = 0.0072
RING_W = 0.0021


def ring_height(u, v):
    """interlocking ring lattice in a (u, v) chart (metres) -> height 0..1 (ring tops = 1, gaps = 0)."""
    k0 = np.floor(v / RING_DV)
    best = np.zeros_like(u)
    for dk in (-1, 0, 1):
        k = k0 + dk
        off = np.where((k % 2) == 0, 0.0, RING_DU * 0.5)
        j0 = np.floor((u - off) / RING_DU)
        for dj in (0, 1):
            cu = (j0 + dj) * RING_DU + off
            cv = k * RING_DV
            d = np.sqrt(((u - cu) * 0.85) ** 2 + (v - cv) ** 2)
            h = np.clip(1 - ((d - RING_R) / RING_W) ** 2, 0, 1)
            best = np.maximum(best, h)
    return best


def mail_uv(P, part="torso"):
    """chart for the ring lattice: around the body axis on the torso/skirt, around the arm on the sleeves."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    th = np.arctan2(x, -(y - 0.02))
    u = th * 0.27
    v = z.copy()
    if part == "torso":
        sf = CP.sleeve_factor(P)
        for side in ("l", "r"):
            sh, el, wr = CP.arm_pts(side)
            ad = L.norm(el - sh)
            R = L.frame_from(ad)
            q = P - sh
            t = q @ ad
            ang = np.arctan2(q @ R[:, 2], q @ R[:, 0])
            s = 1 if side == "l" else -1
            sel = (sf > 0.5) & (s * x > 0)
            u = np.where(sel, ang * 0.11, u)
            v = np.where(sel, -t, v)
    return u, v


def paint_mail(P, N, ao, curv, part="torso"):
    u, v = mail_uv(P, part)
    h = ring_height(u, v)
    base = mix(C("#2e2c2a"), C("#4d4a46"), np.clip(0.5 + fbm(P, 9.0), 0, 1))
    col = mix(C("#121110"), base, smoothstep(0.0, 0.35, h))            # dark gaps between rings
    col = mix(col, C("#8a857c"), smoothstep(0.75, 1.0, h) * 0.55)       # polished ring tops
    rust = np.clip(fbm(P + 7.0, 11.0, 3, NOISE2) * 1.6 - 0.15 + 0.4 * (1 - ao), 0, 1)
    col = mix(col, mix(C("#5e3018"), C("#8a4a22"), np.clip(NOISE(P * 90) + 0.5, 0, 1)), rust * 0.55 * (1 - 0.6 * smoothstep(0.7, 1, h)))
    col = mix(col, C("#151312"), soot(P, N, 0.55))
    rough = (0.38 + 0.4 * rust + 0.2 * (1 - h)).astype(F32)
    metal = (0.85 * smoothstep(0.2, 0.6, h) * (1 - 0.8 * rust)).astype(F32)
    return col, rough, metal


# ------------------------------------------------------------------------------------------ skin
SKIN = C("#30251f")


def paint_skin(P, N, ao, curv):
    """soot-black skin: dark warm brown under ash-grey soot, sweat-shine, faint ember warmth in creases."""
    n1 = fbm(P, 22.0)
    col = mix(SKIN, C("#2a201b"), np.clip(0.5 + n1, 0, 1) * 0.7)
    col = mix(col, C("#4a3626"), np.clip(fbm(P + 4.4, 8.0, 2, NOISE3), 0, 1) * 0.5)      # warmer blotches
    col = mix(col, C("#17120f"), soot(P, N, 0.7, 9.0))                                # soot
    ash = np.clip(NOISE2.fbm(P * 60.0, 2) * 2.0 - 0.4, 0, 1) * np.clip(curv * 2 + 0.3, 0, 1)
    col = mix(col, C("#6e675e"), ash * 0.18)                                           # ash dust on ridges
    col = col * (1 + 0.07 * brush(P, 110))[:, None]
    col = common_light(col, N, ao, curv, top=0.10, cav=0.8, edge=0.10, aopow=1.1, aomin=0.38)
    crease = np.clip(-curv * 2.0, 0, 1) * (1 - ao) ** 0.5
    col = col + crease[:, None] * C("#8a2c08") * 0.25                                  # forge-warm creases
    rough = (0.52 + 0.25 * np.clip(fbm(P + 2, 15.0) + 0.5, 0, 1)).astype(F32)           # sweaty sheen
    return col, rough


# ------------------------------------------------------------------------------------------ iron
def black_iron(P, N, ao, curv, rust_amt=0.4, heat=None):
    col = mix(C("#211f1d"), C("#3a3734"), np.clip(0.5 + fbm(P, 14.0), 0, 1))
    col = mix(col, C("#4a4743"), np.clip(fbm(P + 2.0, 50.0, 2, NOISE2), 0, 1) * 0.35)
    rust = np.clip(fbm(P + 9.0, 16.0, 3, NOISE3) * 1.5 - 0.2 + 0.35 * (1 - ao), 0, 1) * rust_amt
    col = mix(col, mix(C("#5a2d16"), C("#93501f"), np.clip(NOISE2(P * 120) + 0.5, 0, 1)), rust)
    e = np.clip(curv * 2.2 - 0.35, 0, 1)
    col = mix(col, C("#9a958c"), e * 0.55)                                              # worn bright edges
    metal = np.clip(0.9 * (1 - rust) - 0.2 * (1 - e) * 0.3, 0, 1).astype(F32)
    rough = (0.48 + 0.4 * rust - 0.2 * e).astype(F32)
    return col, rough, metal


def heat_tint(t):
    """temper colours for a 0..1 heat parameter: straw -> bronze -> purple -> blue -> grey"""
    stops = [(0.0, C("#3a3734")), (0.25, C("#4c5a7c")), (0.45, C("#6a4a82")), (0.65, C("#a0603a")), (0.85, C("#c8a45a")),
             (1.0, C("#e0c890"))]
    t = np.clip(t, 0, 1)
    out = np.zeros((len(t), 3), F32)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (t >= a) & (t <= b)
        f = ((t[m] - a) / (b - a))[:, None]
        out[m] = ca * (1 - f) + cb * f
    return out


GLOW_LO = C("#a82a06")
GLOW_MID = C("#ff6410")
GLOW_HI = C("#ffc860")


def glow_ramp(t):
    t = np.clip(t, 0, 1)[:, None]
    return np.where(t < 0.5, GLOW_LO * (1 - t * 2) + GLOW_MID * (t * 2), GLOW_MID * (2 - t * 2) + GLOW_HI * (t * 2 - 1))


# ------------------------------------------------------------------------------------------ leather
def leather(P, N, ao, curv, base, dark="#1c120c", light="#9a6a42", scorch=0.6):
    n1 = fbm(P, 6.0)
    col = mix(base, C(light), np.clip(0.45 + n1, 0, 1) * 0.35)
    col = col * (1 + 0.06 * brush(P, 45))[:, None]
    # scorch marks: blackened blotches with a brown burn halo
    s = fbm(P + 5.5, 4.5, 3, NOISE3) + 0.4 * fbm(P + 1.2, 13.0, 2, NOISE2)
    halo = smoothstep(0.05, 0.25, s) * scorch
    core = smoothstep(0.22, 0.42, s) * scorch
    col = mix(col, col * np.array([0.55, 0.42, 0.32], F32), halo * 0.7)
    col = mix(col, C(dark), core * 0.92)
    col = col + 0.16 * np.clip(curv * 2 - 0.2, 0, 1)[:, None] * C(light)                 # worn edges
    rough = (0.62 + 0.25 * core - 0.1 * np.clip(curv, 0, 1)).astype(F32)
    return col, rough, core


# ------------------------------------------------------------------------------------------ parts
def paint_torso(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = len(P)
    col, rough, metal = paint_mail(P, N, ao, curv, "torso")
    sk = m["skin"]
    sc, sr = paint_skin(P[sk], N[sk], ao[sk], curv[sk])
    col = common_light(col, N, ao, curv, top=0.10, cav=0.5, edge=0.10, P=P)
    col[sk] = sc
    rough[sk] = sr
    metal[sk] = 0.0
    cl = m["collar"]
    col[cl] = col[cl] * 0.8
    return col, rough, metal, None


def paint_bib(P, N, ao, curv, part):
    m = part.masks(P, N)
    col, rough, core = leather(P, N, ao, curv, C("#6e4226"), scorch=0.75)
    hem = m["hem"]
    col[hem] = col[hem] * 0.78
    # stitch line inside the hem
    r = CP.bib_region(P)
    st = (r > -0.019) & (r < -0.0155) & (np.sin((P[:, 0] + P[:, 2]) * 330.0) > 0.1)
    col[st] = C("#c9b08a")
    pk = m["pocket"]
    col[pk] = col[pk] * 0.88
    col = common_light(col, N, ao, curv, top=0.10, cav=0.6, edge=0.14, P=P)
    return col, rough, None, None


def paint_mask(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = len(P)
    q = m["q"]
    col, rough, metal = black_iron(P, N, ao, curv, rust_amt=0.25)
    em = np.zeros((n, 3), F32)
    # heat tint fanning out round the eye slits
    sd = m["sd"]
    ht = smoothstep(0.034, 0.0, sd) * (0.6 + 0.4 * np.clip(NOISE(P * 40) + 0.6, 0, 1))
    tint = heat_tint(0.35 + 0.6 * ht)
    col = mix(col, tint, smoothstep(0.05, 0.4, ht) * 0.5)
    # soot streaks rising from the slits and vents
    up = np.clip(q[:, 2] - 0.004, 0, 0.08) / 0.08
    streak = np.clip(NOISE(P * np.array([90, 90, 8], F32)) * 1.5 + 0.2, 0, 1) * smoothstep(0.06, 0.0, np.abs(np.abs(q[:, 0]) - 0.052) - 0.03) * up
    col = mix(col, C("#0d0b0a"), streak * 0.6)
    rv = m["rivet"] | m["bolt"]
    col[rv] = mix(col[rv], C("#8c857a"), 0.45)
    # the dark face behind the plate: glowing furnace-orange where seen through the slits
    face = m["face"]
    col[face] = C("#1a0d07")
    g = m["glow"] | m["slit_wall"]
    gt = np.maximum(smoothstep(0.012, 0.0, sd), smoothstep(0.003, -0.006, CP.slit2d_d(q)))
    gc = glow_ramp(0.22 + 0.5 * gt)
    col[g] = gc[g]
    em[g] = gc[g] * (0.55 + 0.45 * gt[g])[:, None]
    rough[g] = 0.4
    metal[g] = 0.0
    # faint glow from the breathing vents
    vt = m["vent"]
    col[vt] = mix(col[vt], C("#5a1c08"), 0.5)
    em[vt] = C("#ff5a10") * 0.08
    col[~g & ~vt] = common_light(col[~g & ~vt], N[~g & ~vt], ao[~g & ~vt], curv[~g & ~vt], top=0.10, cav=0.7, edge=0.22,
                                 aomin=0.42)
    return col, rough, metal, em


def paint_hardhat(P, N, ao, curv, part):
    """painted enamel hardhat (tint2): chipped, sooty, scorched brim edge."""
    m = part.masks(P, N)
    col = mix(C("#d89a22"), C("#efb83a"), np.clip(0.5 + fbm(P, 9.0), 0, 1))
    col = col * (1 + 0.05 * brush(P, 50))[:, None]
    chips = np.clip(NOISE2.fbm(P * 38.0, 3) * 2.2 - 0.55 + 0.9 * np.clip(curv * 2, 0, 1), 0, 1)
    chips = smoothstep(0.35, 0.55, chips)
    col = mix(col, C("#3c3a37"), chips)
    rough = (0.42 + 0.35 * chips).astype(F32)
    metal = (0.7 * chips).astype(F32)
    col = mix(col, C("#2a221a"), soot(P, N, 0.55, 7.0))
    b = m["band"]
    col[b] = mix(C("#2a1d14"), C("#43301f"), np.clip(0.5 + fbm(P[b], 30.0), 0, 1))
    rough[b] = 0.65
    metal[b] = 0.0
    bd = m["badge"]
    col[bd] = mix(C("#8a6a2c"), C("#c49a48"), np.clip(0.5 + fbm(P[bd], 60.0), 0, 1))
    metal[bd] = 0.9
    rough[bd] = 0.35
    under = m["under"]
    col[under] = col[under] * 0.55
    col = common_light(col, N, ao, curv, top=0.10, cav=0.6, edge=0.18)
    return col, rough, metal, None


def paint_flap(P, N, ao, curv, part):
    col, rough, core = leather(P, N, ao, curv, C("#3e2a1c"), scorch=0.55)
    col = common_light(col, N, ao, curv, top=0.08, cav=0.6, edge=0.12)
    return col, rough, None, None


def paint_beard(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = len(P)
    strand = NOISE(P * np.array([260, 260, 9], F32)) + 0.5 * NOISE2(P * np.array([520, 520, 18], F32))
    col = mix(C("#141110"), C("#4a3c32"), np.clip(0.4 + 0.8 * strand, 0, 1))
    col = mix(col, C("#151110"), np.clip(-strand, 0, 1) * 0.6)
    col = mix(col, C("#6a6058"), np.clip(NOISE2(P * 70.0) * 1.5 - 0.7, 0, 1) * 0.2)          # ash grey streaks
    rough = (0.45 + 0.2 * np.clip(strand + 0.5, 0, 1)).astype(F32)
    metal = np.zeros(n, F32)
    em = np.zeros((n, 3), F32)
    rg = m["ring"]
    rc, rr, rm = black_iron(P[rg], N[rg], ao[rg], curv[rg], 0.15)
    col[rg] = mix(rc, C("#a07a3a"), 0.45)                                                  # brass-faced iron rings
    rough[rg] = 0.35
    metal[rg] = 0.9
    col = common_light(col, N, ao, curv, top=0.12, cav=0.9, edge=0.14, aopow=1.2, aomin=0.32)
    # ember tips: hair smoulders toward the ends
    e = m["ember"]
    flick = np.clip(0.55 + 0.6 * NOISE3(P * 140.0), 0, 1)
    t = e * flick
    ec = glow_ramp(t)
    sel = (e > 0.02) & ~rg
    col[sel] = mix(col[sel], mix(C("#3a1206"), ec[sel], np.clip(t[sel] * 1.4, 0, 1)), np.clip(e[sel] * 1.6, 0, 1))
    em[sel] = ec[sel] * (t[sel] ** 1.3 * 1.4)[:, None]
    return col, rough, metal, em


def paint_arm_r(P, N, ao, curv, part):
    m = part.masks(P, N)
    col, rough = paint_skin(P, N, ao, curv)
    metal = np.zeros(len(P), F32)
    w = m["wrap"]
    lc, lr, _ = leather(P[w], N[w], ao[w], curv[w], C("#4a3222"), scorch=0.3)
    col[w] = common_light(lc, N[w], ao[w], curv[w], top=0.08, cav=0.8, edge=0.1)
    rough[w] = lr
    nl = m["nail"]
    col[nl] = C("#4a3e36")
    rough[nl] = 0.4
    # knuckles/fingertips greyer with ash, palm a little lighter
    return col, rough, metal, None


def paint_gauntlet(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = len(P)
    col, rough, metal = black_iron(P, N, ao, curv, rust_amt=0.35)
    # heat discolouration toward the knuckles (it grabs hot metal)
    w0 = CP.H("hand_l")
    d = np.linalg.norm(P - w0, axis=1)
    ht = smoothstep(0.05, 0.2, d) * np.clip(0.6 + NOISE(P * 25), 0, 1)
    col = mix(col, heat_tint(0.3 + 0.5 * ht), ht * 0.35)
    gl = m["glove"]
    lc, lr, _ = leather(P[gl], N[gl], ao[gl], curv[gl], C("#3a2618"), scorch=0.4)
    col[gl] = lc
    rough[gl] = lr
    metal[gl] = 0.0
    rv = m["rivet"]
    col[rv] = mix(col[rv], C("#a49c90"), 0.5)
    metal[rv] = 0.95
    rough[rv] = 0.3
    b = m["band"]
    col[b] = col[b] * 0.85
    sk = m["skin"]
    if sk.any():
        sc, sr = paint_skin(P[sk], N[sk], ao[sk], curv[sk])
        col[sk] = sc
        rough[sk] = sr
        metal[sk] = 0.0
    nsk = ~sk
    col[nsk] = common_light(col[nsk], N[nsk], ao[nsk], curv[nsk], top=0.10, cav=0.7, edge=0.22, aomin=0.4)
    return col, rough, metal, None


def paint_chains(P, N, ao, curv, part):
    m = part.masks(P, N)
    col, rough, metal = black_iron(P, N, ao, curv, rust_amt=0.55)
    col = common_light(col, N, ao, curv, top=0.08, cav=0.8, edge=0.25, aomin=0.38)
    return col, rough, metal, None


def paint_belt(P, N, ao, curv, part):
    m = part.masks(P, N)
    col, rough, core = leather(P, N, ao, curv, C("#2e1f15"), scorch=0.3)
    metal = np.zeros(len(P), F32)
    i = m["iron"]
    ic, ir, im = black_iron(P[i], N[i], ao[i], curv[i], 0.4)
    col[i], rough[i], metal[i] = ic, ir, im
    col = common_light(col, N, ao, curv, top=0.08, cav=0.7, edge=0.2)
    return col, rough, metal, None


def paint_straps(P, N, ao, curv, part):
    """tint2 straps: same enamel yellow family as the hardhat would be odd on leather -> painted canvas webbing."""
    col = mix(C("#c88e2a"), C("#e0a83a"), np.clip(0.5 + fbm(P, 30.0), 0, 1))
    weave = np.sin(P[:, 2] * 900.0) * np.sin((P[:, 0] + P[:, 1]) * 900.0)
    col = col * (1 + 0.06 * weave)[:, None]
    col = mix(col, C("#2a2016"), soot(P, N, 0.5, 10.0))
    col = common_light(col, N, ao, curv, top=0.08, cav=0.7, edge=0.12)
    rough = np.full(len(P), 0.85, F32)
    return col, rough, None, None


def paint_apron(P, N, ao, curv, part):
    m = part.masks(P, N)
    col, rough, core = leather(P, N, ao, curv, C("#6e4226"), scorch=0.85)
    e = m["edge"]
    col[e] = col[e] * 0.8
    x, z = P[:, 0], P[:, 2]
    hw = 0.235 + 0.04 * np.clip((0.98 - z) / 0.6, 0, 1)
    edge = np.minimum(hw - np.abs(x), z - 0.46 - 0.03 * (np.abs(x) / 0.25) ** 2)
    st = (edge > 0.016) & (edge < 0.0195) & (np.sin((x + z) * 330.0) > 0.1)
    col[st] = C("#c9b08a")
    # burnt hole rims + spark burns peppering the front
    hl = m["holes"]
    col = mix(col, C("#120a06"), hl * 0.95)
    sp = np.clip(NOISE(P * 160.0) * 3.0 - 2.1, 0, 1)
    col = mix(col, C("#1a0f08"), sp * 0.8)
    inner = m["inner"]
    col[inner] = col[inner] * 0.55
    col = common_light(col, N, ao, curv, top=0.10, cav=0.6, edge=0.14, P=P)
    # ash and slag splashes lower down
    lo = smoothstep(0.75, 0.46, z) * np.clip(0.5 + fbm(P, 9.0), 0, 1)
    col = mix(col, C("#5a5048"), lo * 0.35)
    return col, rough, None, None


def paint_mskirt(P, N, ao, curv, part):
    col, rough, metal = paint_mail(P, N, ao, curv, "skirt")
    col = common_light(col, N, ao, curv, top=0.10, cav=0.5, edge=0.1, P=P)
    return col, rough, metal, None


def paint_legs(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = len(P)
    # boots: dark oiled leather
    col = mix(C("#2a1c14"), C("#3f2a1c"), np.clip(0.5 + fbm(P, 14.0), 0, 1))
    col = col + 0.2 * np.clip(curv * 2 - 0.1, 0, 1)[:, None] * C("#8a6040")
    rough = np.full(n, 0.55, F32)
    metal = np.zeros(n, F32)
    tr = m["trousers"]
    tc = mix(C("#2f2b27"), C("#4a443c"), np.clip(0.5 + fbm(P[tr], 10.0), 0, 1))
    tc = mix(tc, C("#151210"), soot(P[tr], N[tr], 0.55, 8.0))
    col[tr] = tc
    rough[tr] = 0.92
    kn = m["knee"]
    kc, kr, _ = leather(P[kn], N[kn], ao[kn], curv[kn], C("#4a3020"), scorch=0.5)
    col[kn] = kc
    rough[kn] = kr
    so = m["sole"]
    col[so] = C("#16110d")
    rough[so] = 0.8
    stp = m["strap"]
    col[stp] = C("#1e140e")
    tt = m["toe"]
    ic, ir, im = black_iron(P[tt], N[tt], ao[tt], curv[tt], 0.25)
    col[tt], rough[tt], metal[tt] = mix(ic, C("#6e6a63"), 0.25), ir, im
    col = common_light(col, N, ao, curv, top=0.08, cav=0.6, edge=0.10, P=P)
    ash = smoothstep(0.18, 0.02, P[:, 2]) * np.clip(0.55 + fbm(P, 12.0), 0, 1)
    col = mix(col, C("#4e4842"), ash * 0.5)
    return col, rough, metal, None


def paint_hammer(P, N, ao, curv, part):
    m = part.masks(P, N)
    n = len(P)
    col = np.zeros((n, 3), F32)
    rough = np.full(n, 0.7, F32)
    metal = np.zeros(n, F32)
    em = np.zeros((n, 3), F32)
    z = P[:, 2]
    # charred oak haft
    wd = m["wood"]
    grain = NOISE(P * np.array([420, 420, 9], F32)) + 0.5 * NOISE2(P * np.array([150, 150, 3], F32))
    wc = mix(C("#3a2618"), C("#5a3c24"), np.clip(0.5 + 0.6 * grain, 0, 1))
    char = smoothstep(PR.HEAD_Z - 0.40, PR.HEAD_Z - 0.12, z) * np.clip(0.6 + fbm(P, 20.0), 0, 1)
    wc = mix(wc, C("#120b07"), char * 0.9)
    ember_w = char * np.clip(NOISE3(P * 60.0) * 2.5 - 1.6, 0, 1)                          # smouldering char cracks
    col[wd] = wc[wd]
    rough[wd] = 0.75
    em[wd] = (GLOW_LO[None] * (ember_w[:, None] * 0.8))[wd]
    col[wd] = mix(col[wd], GLOW_LO[None].repeat(wd.sum(), 0), np.clip(ember_w[wd] * 1.2, 0, 1))
    lw = m["leather"]
    lc, lr, _ = leather(P[lw], N[lw], ao[lw], curv[lw], C("#2c1d14"), scorch=0.2)
    col[lw] = lc
    rough[lw] = lr
    ir = m["iron"]
    ic, irr, im = black_iron(P[ir], N[ir], ao[ir], curv[ir], 0.35)
    col[ir], rough[ir], metal[ir] = ic, irr, im
    # the hot head: white-hot striking face, orange body, dull-red pein, dark scale crust, bright cracks
    hd = m["head"]
    if hd.any():
        Ph = P[hd]
        yy = Ph[:, 1] / PR.HEAD_HL                                  # -1 pein .. +1 face
        heat = np.clip(0.30 + 0.62 * smoothstep(-0.6, 0.95, yy) + 0.08 * fbm(Ph, 8.0), 0, 1)
        heat = np.maximum(heat, smoothstep(0.80, 1.0, yy))
        # cooling scale: solid on the pein half, breaking up into islands toward the hot face
        crust = fbm(Ph + 3.0, 7.0, 3, NOISE3) * 1.6 + 0.62 - 1.25 * smoothstep(-0.3, 0.7, yy)
        crust = smoothstep(0.30, 0.50, crust)
        hc = glow_ramp(heat)
        cc = mix(C("#1b1512"), C("#3a2f28"), np.clip(0.5 + fbm(Ph, 50.0), 0, 1))
        cr = m["crack"][hd]
        c = mix(hc, cc, crust * (1 - cr))
        col[hd] = c
        e = hc * ((0.15 + 0.75 * heat ** 1.5) * (1 - crust * 0.95 * (1 - cr)))[:, None]
        e[cr] = glow_ramp(np.clip(heat[cr] + 0.3, 0, 1)) * 1.1
        em[hd] = e
        rough[hd] = 0.55 + 0.35 * crust
        metal[hd] = 0.3 * crust
    nh = ~hd
    col[nh] = common_light(col[nh], N[nh], ao[nh], curv[nh], top=0.08, cav=0.7, edge=0.18, aomin=0.42)
    # glow spill onto the iron near the head
    spill = smoothstep(PR.HEAD_Z - 0.28, PR.HEAD_Z - 0.08, z) * (~hd)
    col = col + spill[:, None] * C("#ff6a1a") * 0.12
    return col, rough, metal, em


PAINTERS = {"torso": paint_torso, "bib": paint_bib, "mask": paint_mask, "hardhat": paint_hardhat, "flap": paint_flap,
            "beard": paint_beard, "arm_r": paint_arm_r, "gauntlet": paint_gauntlet, "chains": paint_chains,
            "belt": paint_belt, "straps": paint_straps, "apron": paint_apron, "mskirt": paint_mskirt,
            "legs": paint_legs, "hammer": paint_hammer}


# ------------------------------------------------------------------------------------------ detail normals
def height_detail(name, P):
    if name in ("torso", "mskirt"):
        u, v = mail_uv(P, "torso" if name == "torso" else "skirt")
        h = ring_height(u, v)
        return 0.0012 * h
    if name in ("bib", "apron", "flap", "belt", "knee"):
        return 0.00035 * NOISE.ridged(P * 160.0, 2) + 0.0002 * NOISE2(P * 420.0)
    if name in ("arm_r",):
        return 0.0003 * NOISE.ridged(P * 260.0, 2)
    if name == "beard":
        return 0.0005 * NOISE(P * np.array([520, 520, 40], F32))
    if name in ("mask", "gauntlet", "chains", "hammer"):
        return 0.00025 * NOISE.fbm(P * 220.0, 2)
    if name == "legs":
        return 0.0003 * NOISE.ridged(P * 200.0, 2)
    return 0.00015 * NOISE(P * 300.0)


def detail_normals(name, P, N, strength=1.0):
    e = 0.0005
    h0 = height_detail(name, P)
    if np.isscalar(h0):
        return N
    g = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3, F32)
        d[k] = e
        g[:, k] = (height_detail(name, P + d) - height_detail(name, P - d)) / (2 * e)
    gt = g - (g * N).sum(1, keepdims=True) * N
    Nn = N - strength * gt
    return Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-6)
