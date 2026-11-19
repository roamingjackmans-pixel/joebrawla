"""Mother Spore -- procedural materials (baked into texture sets by fblib.Kit)."""
import math
import bpy
from mathutils import Vector
import fblib as F
from fblib import NB, srgb

V = Vector
TEAL = srgb('#3dffd2')
TEAL_DIM = srgb('#1fb89a')
VIOLET = srgb('#c27bff')


def _m(name):
    m = bpy.data.materials.new(name)
    return m, NB(m)


def lin(c, k=1.0):
    s = srgb(c)
    return (s[0] * k, s[1] * k, s[2] * k, 1.0)


def angle_xy(nb, co, cy=0.035):
    """atan2 of the horizontal position around a vertical axis (front = -Y)."""
    s = nb.sep(co)
    return nb.math('ARCTAN2', s[0], nb.sub(cy, s[1]))


def spots(nb, co, scale, frac=0.25, size=0.35, seed=0.0):
    """random round spots (0..1)."""
    c = nb.mapping(co, loc=(seed, seed * 1.3, seed * 0.7))
    d = nb.voronoi(c, scale, 'F1', out='Distance')
    rc = nb.voronoi(c, scale, 'F1', out='Color')
    sel = nb.mr(nb.sep(rc)[0], 1.0 - frac - 0.02, 1.0 - frac + 0.02, 0.0, 1.0)
    return nb.mul(nb.mr(d, size, size * 0.6, 0.0, 1.0), sel)


# ================================================================================================ skin
def skin(body, L, base_img, nrm_img, tips):
    m, nb = _m('ms_skin_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    tex = nb.img(base_img, 'UVMap')
    bw = nb.node('ShaderNodeRGBToBW')
    nb.link(tex, bw.inputs[0])
    detail = nb.mr(bw.outputs[0], 0.02, 0.45, 0.25, 1.95, 'LINEAR')
    detail = nb.add(nb.mul(detail, 0.8), 0.2)
    base = srgb('#c3a6bd')
    c = nb.mix(1.0, base, nb.comb(detail, detail, detail), 'MULTIPLY')
    # mottled lilac / warmer variation
    mot = nb.noise(co, 9.0, 4, 0.6)
    c = nb.mix(nb.mr(mot, 0.35, 0.7, 0.0, 0.35), c, srgb('#a98aa8'))
    c = nb.mix(nb.mr(nb.noise(co, 3.0, 3, 0.5), 0.5, 0.75, 0.0, 0.25), c, srgb('#d7b8c4'))
    el, er, nose, chin = L['eye_l'], L['eye_r'], L['nose'], L['chin']
    mouth = V((0, nose.y + 0.030, (nose.z + chin.z) * 0.5 + 0.006))
    eye_z = (el.z + er.z) * 0.5
    # face: plum lips, deep violet eye shadow, rosy-violet cheeks
    c = nb.paint(c, nb.ell(co, mouth, (0.023, 0.022, 0.0085), soft=0.45), '#6e2f58', 0.85)
    for e, sx in ((el, 1), (er, -1)):
        sh = nb.ell(co, (e.x + sx * 0.004, e.y + 0.006, e.z + 0.004), (0.026, 0.03, 0.017), soft=0.75)
        c = nb.paint(c, sh, '#4a2a5c', 0.62)
        lid = nb.ell(co, (e.x, e.y + 0.003, e.z + 0.009), (0.019, 0.02, 0.006), soft=0.6)
        c = nb.paint(c, lid, '#7c4f97', 0.45)
        ch = nb.ell(co, (sx * 0.046, e.y + 0.014, eye_z - 0.036), (0.026, 0.03, 0.02), soft=0.9)
        c = nb.paint(c, ch, '#b07090', 0.25)
    # long fingers: ink-dipped plum fingertips
    tipm = None
    for tp in tips:
        mk = nb.ell(co, tp, (0.036, 0.036, 0.036), soft=0.9)
        tipm = mk if tipm is None else nb.mx(tipm, mk)
    c = nb.paint(c, tipm, '#3e2140', 0.85)
    # neck gills: three slits per side
    neckz = L['neck_01'].z
    gill_e = None
    gill_d = None
    for sx in (1, -1):
        reg = nb.ell(co, (sx * 0.050, L['neck_01'].y - 0.005, neckz + 0.035), (0.022, 0.04, 0.034), soft=0.5)
        lines = nb.mr(nb.wave(nb.mapping(co, rot=(0, 0.45 * sx, 0)), 95.0, 0.3, 0.0, 'BANDS', 'Z'), 0.80, 0.97, 0.0, 1.0)
        g = nb.mul(reg, lines)
        gill_d = g if gill_d is None else nb.mx(gill_d, g)
    c = nb.paint(c, gill_d, '#3a1d3a', 0.85)
    # fine gill-like ridges everywhere (rings around the limbs, bands on the body)
    arm = nb.mr(nb.math('ABSOLUTE', s[0]), 0.22, 0.30, 0.0, 1.0)
    rid_body = nb.wave(nb.mapping(co, scale=(1, 1, 1)), 140.0, 4.0, 2.0, 'BANDS', 'Z')
    rid_arm = nb.wave(co, 140.0, 4.0, 2.0, 'BANDS', 'X')
    ridges = nb.mixf(arm, rid_body, rid_arm)
    face = nb.ell(co, L['head_c'] + V((0, -0.05, -0.01)), (0.075, 0.07, 0.11), soft=0.6)
    rid_amt = nb.mul(nb.sub(1.0, nb.mul(face, 0.8)), nb.mr(nb.noise(co, 4.0, 2, 0.5), 0.3, 0.7, 0.4, 1.0))
    c = nb.mix(nb.mul(nb.mr(ridges, 0.65, 0.95, 0.0, 0.16), rid_amt), c, srgb('#6e4c74'))
    # bioluminescent spots: cheeks/temples, shoulders, outer arms, backs of hands, shins, feet
    reg = None
    for cen, r in (((0.052, el.y + 0.02, eye_z - 0.03), (0.03, 0.04, 0.022)),
                   ((-0.052, er.y + 0.02, eye_z - 0.03), (0.03, 0.04, 0.022)),
                   ((0.07, el.y + 0.05, eye_z + 0.035), (0.025, 0.05, 0.03)),
                   ((-0.07, er.y + 0.05, eye_z + 0.035), (0.025, 0.05, 0.03))):
        mk = nb.ell(co, cen, r, soft=0.7)
        reg = mk if reg is None else nb.mx(reg, mk)
    limbs = nb.mul(nb.mr(nb.math('ABSOLUTE', s[0]), 0.26, 0.34, 0.0, 1.0), nb.mr(s[1], -0.02, 0.05, 1.0, 0.25))
    shins = nb.mul(nb.mr(s[2], 0.60, 0.45, 0.0, 1.0), nb.mr(s[1], 0.04, -0.02, 0.0, 1.0))
    clus = nb.mr(nb.noise(co, 7.0, 2, 0.5), 0.45, 0.62, 0.0, 1.0)
    reg = nb.mx(reg, nb.mul(nb.mx(limbs, shins), clus))
    sp = nb.mx(spots(nb, co, 160.0, 0.30, 0.30, 1.0), spots(nb, co, 75.0, 0.12, 0.28, 7.0))
    spm = nb.mul(sp, reg)
    c = nb.paint(c, spm, '#9ff5e2', 0.9)
    emit = nb.mix(nb.mx(spm, nb.mul(gill_d, 0.55)), (0, 0, 0, 1), TEAL)
    rough = nb.add(0.46, nb.mul(nb.noise(co, 30.0, 3, 0.6), 0.12))
    rough = nb.mixf(nb.ell(co, mouth, (0.023, 0.022, 0.0085), soft=0.45), rough, 0.30)
    nm = nb.normal_map(nb.img(nrm_img, 'UVMap'), 1.0)
    h = nb.add(nb.mul(nb.mul(ridges, rid_amt), 0.6), nb.mul(nb.noise(co, 260.0, 2, 0.5), 0.25))
    h = nb.sub(h, nb.mul(gill_d, 1.2))
    n = nb.bump(h, 0.22, 0.0015, nm)
    nb.finish(c, rough, n, emit)
    return m


# ================================================================================================ cap
def cap_top():
    """tint1: light, nearly neutral; the rust red comes from the base colour factor."""
    m, nb = _m('ms_cap_top_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    pv = nb.attr('pv')
    streak = nb.wave(nb.comb(nb.mul(pv, 1.0), pu, 0.0), 160.0, 6.0, 2.0, 'BANDS', 'X')
    mott = nb.noise(co, 14.0, 5, 0.62)
    blot = nb.noise(co, 4.5, 3, 0.5)
    val = nb.add(0.80, nb.mul(nb.sub(streak, 0.5), 0.10))
    val = nb.sub(val, nb.mul(nb.mr(blot, 0.45, 0.75, 0.0, 1.0), 0.16))
    val = nb.add(val, nb.mul(nb.sub(mott, 0.5), 0.12))
    val = nb.sub(val, nb.mul(nb.mr(pu, 0.30, 0.0, 0.0, 1.0), 0.18))           # deeper centre
    rings = nb.wave(nb.comb(pu, 0.0, 0.0), 42.0, 3.0, 1.0, 'BANDS', 'X')
    val = nb.sub(val, nb.mul(nb.mul(nb.mr(pu, 0.62, 0.9, 0.0, 1.0), nb.mr(rings, 0.6, 0.9, 0.0, 1.0)), 0.12))
    val = nb.add(val, nb.mul(nb.mr(pu, 0.93, 0.985, 0.0, 1.0), 0.18))           # pale margin
    c = nb.comb(val, nb.mul(val, 0.96), nb.mul(val, 0.93))
    c = nb.mix(nb.mr(nb.noise(co, 2.5, 2, 0.5), 0.45, 0.7, 0.0, 0.5), c, nb.comb(val, nb.mul(val, 0.86), nb.mul(val, 0.82)))
    rough = nb.add(0.36, nb.mul(mott, 0.22))
    h = nb.add(nb.mul(streak, 0.35), nb.mul(nb.noise(co, 60.0, 3, 0.6), 0.5))
    n = nb.bump(h, 0.25, 0.002)
    nb.finish(c, rough, n, None)
    return m


def gills():
    m, nb = _m('ms_gills_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')          # 0 rim .. 1 hole
    pv = nb.attr('pv')
    g = nb.wave(nb.comb(pv, 0.0, 0.0), 210.0, 0.6, 1.0, 'BANDS', 'X', 'SAW')
    g2 = nb.wave(nb.comb(pv, 0.0, 0.0), 420.0, 0.4, 1.0, 'BANDS', 'X', 'SIN')
    groove = nb.mr(g, 0.75, 1.0, 0.0, 1.0)
    groove = nb.mx(groove, nb.mul(nb.mr(g2, 0.85, 1.0, 0.0, 1.0), nb.mr(pu, 0.5, 0.2, 0.0, 0.7)))
    c = nb.mix(nb.mr(pu, 0.0, 0.25, 1.0, 0.0), srgb('#e3d5dc'), srgb('#cdb6c8'))
    c = nb.mix(nb.mul(groove, 0.85), c, srgb('#4a2c4c'))
    c = nb.mix(nb.mr(pu, 0.08, 0.0, 0.0, 1.0), c, srgb('#f2e8dc'))
    glow = nb.mul(groove, nb.mr(pu, 0.15, 0.85, 0.15, 1.0))
    glow = nb.mul(glow, nb.mr(nb.noise(co, 18.0, 2, 0.5), 0.3, 0.6, 0.35, 1.0))
    emit = nb.mix(glow, (0, 0, 0, 1), TEAL_DIM)
    h = nb.sub(1.0, groove)
    n = nb.bump(h, 0.6, 0.004)
    nb.finish(c, 0.62, n, emit)
    return m


def band():
    m, nb = _m('ms_band_proc')
    co = nb.coord('Object')
    f = nb.noise(nb.mapping(co, scale=(40, 40, 400)), 1.0, 3, 0.6)
    c = nb.mix(nb.mr(f, 0.4, 0.65, 0.0, 1.0), srgb('#e7dac6'), srgb('#bfa9b4'))
    sp = spots(nb, co, 220.0, 0.25, 0.3, 3.0)
    emit = nb.mix(sp, (0, 0, 0, 1), TEAL)
    n = nb.bump(f, 0.4, 0.002)
    nb.finish(c, 0.7, n, emit)
    return m


def warts():
    m, nb = _m('ms_warts_proc')
    co = nb.coord('Object')
    cr = nb.voronoi(co, 140.0, 'DISTANCE_TO_EDGE', out='Distance')
    crack = nb.mr(cr, 0.0, 0.06, 1.0, 0.0)
    c = nb.mix(nb.mr(nb.noise(co, 40.0, 3, 0.5), 0.4, 0.7, 0.0, 1.0), srgb('#f1e7d2'), srgb('#e2cfb6'))
    c = nb.mix(nb.mul(crack, 0.6), c, srgb('#a88f80'))
    n = nb.bump(nb.sub(nb.noise(co, 90.0, 3, 0.6), nb.mul(crack, 0.5)), 0.5, 0.002)
    nb.finish(c, 0.78, n, None)
    return m


# ================================================================================================ hair, eyes, brows
def hair():
    m, nb = _m('ms_hair_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')          # 0 root .. 1 tip
    pv = nb.attr('pv')
    fib = nb.wave(nb.comb(pv, nb.mul(pu, 0.1), 0.0), 9.0 * 6, 3.0, 2.0, 'BANDS', 'X')
    fib2 = nb.noise(nb.mapping(co, scale=(220, 220, 18)), 1.0, 3, 0.6)
    c = nb.mix(nb.mr(fib, 0.3, 0.8, 0.0, 1.0), srgb('#a98aa6'), srgb('#e8dbe4'))
    c = nb.mix(nb.mr(fib2, 0.45, 0.7, 0.0, 0.5), c, srgb('#f3ece6'))
    c = nb.mix(nb.mr(pu, 0.25, 0.0, 0.0, 0.7), c, srgb('#6f4f72'))
    tip = nb.mr(pu, 0.72, 0.98, 0.0, 1.0)
    c = nb.mix(nb.mul(tip, 0.7), c, srgb('#9ff5e2'))
    beads = nb.mul(spots(nb, co, 120.0, 0.18, 0.32, 5.0), nb.mr(pu, 0.35, 0.6, 0.0, 1.0))
    emit = nb.mix(nb.mx(nb.mul(tip, 0.8), beads), (0, 0, 0, 1), TEAL)
    n = nb.bump(nb.add(fib, nb.mul(fib2, 0.6)), 0.45, 0.0015)
    nb.finish(c, 0.58, n, emit)
    return m


def eyes(fronts):
    """fronts: [(front_point, iris_r)] per eye. Glowing violet iris, plum sclera, slit pupil."""
    m, nb = _m('ms_eyes_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    iris = None
    pupil = None
    ring = None
    for fp, r in fronts:
        dx = nb.sub(s[0], fp.x)
        dz = nb.sub(s[2], fp.z)
        d = nb.math('SQRT', nb.add(nb.mul(dx, dx), nb.mul(dz, dz)))
        ir = nb.mr(d, r, r * 0.88, 0.0, 1.0)
        rg = nb.mul(nb.mr(d, r * 1.02, r * 0.92, 0.0, 1.0), nb.mr(d, r * 0.80, r * 0.92, 0.0, 1.0))
        dp = nb.math('SQRT', nb.add(nb.mul(nb.mul(dx, 3.2), nb.mul(dx, 3.2)), nb.mul(nb.mul(dz, 0.9), nb.mul(dz, 0.9))))
        pp = nb.mr(dp, r * 0.42, r * 0.32, 0.0, 1.0)
        iris = ir if iris is None else nb.mx(iris, ir)
        ring = rg if ring is None else nb.mx(ring, rg)
        pupil = pp if pupil is None else nb.mx(pupil, pp)
    rays = nb.wave(co, 900.0, 3.0, 2.0, 'RINGS', 'Y')
    c = srgb('#3c2347')
    c = nb.mix(iris, c, nb.mix(nb.mr(rays, 0.3, 0.8, 0.0, 1.0), srgb('#9a4fe0'), srgb('#e3b6ff')))
    c = nb.mix(ring, c, srgb('#24112e'))
    c = nb.mix(pupil, c, srgb('#0b0510'))
    e = nb.mix(iris, (0.10, 0.03, 0.16, 1), VIOLET)
    e = nb.mix(nb.mx(pupil, nb.mul(ring, 0.7)), e, (0.0, 0.0, 0.0, 1))
    nb.finish(c, 0.15, None, e)
    return m


def brows():
    m, nb = _m('ms_brows_proc')
    co = nb.coord('Object')
    c = nb.mix(nb.mr(nb.noise(co, 300.0, 2, 0.5), 0.4, 0.7, 0.0, 1.0), srgb('#2e1a2c'), srgb('#4a2c44'))
    nb.finish(c, 0.7, None, None)
    return m


# ================================================================================================ staff, roots
def stalk():
    m, nb = _m('ms_stalk_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    pv = nb.attr('pv')
    fib = nb.wave(nb.comb(pv, nb.mul(pu, 0.05), 0.0), 14.0, 5.0, 2.0, 'BANDS', 'X')
    scal = nb.voronoi(nb.mapping(co, scale=(1.0, 1.0, 0.35)), 60.0, 'DISTANCE_TO_EDGE', out='Distance')
    scale_e = nb.mr(scal, 0.0, 0.08, 1.0, 0.0)
    c = nb.mix(nb.mr(fib, 0.2, 0.8, 0.0, 1.0), srgb('#8a6f74'), srgb('#d6c6bb'))
    c = nb.mix(nb.mul(scale_e, 0.55), c, srgb('#5a3c48'))
    c = nb.mix(nb.mr(nb.noise(co, 6.0, 3, 0.5), 0.5, 0.75, 0.0, 0.6), c, srgb('#6e4a52'))
    c = nb.mix(nb.mr(pu, 0.08, 0.0, 0.0, 1.0), c, srgb('#4a3034'))
    sp = nb.mul(spots(nb, co, 110.0, 0.12, 0.3, 9.0), nb.mr(nb.noise(co, 5.0, 2, 0.5), 0.45, 0.6, 0.0, 1.0))
    emit = nb.mix(sp, (0, 0, 0, 1), TEAL)
    n = nb.bump(nb.add(fib, nb.mul(scale_e, -0.8)), 0.55, 0.002)
    nb.finish(c, 0.72, n, emit)
    return m


def mini_caps():
    m, nb = _m('ms_minicaps_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    top = nb.mr(pu, 0.86, 0.80, 0.0, 1.0)       # 1 on the cap top
    stem = nb.mr(pu, 0.88, 0.9, 0.0, 1.0)
    sp = spots(nb, co, 70.0, 0.4, 0.38, 2.0)
    capc = nb.mix(sp, srgb('#a5381f'), srgb('#efe3cc'))
    capc = nb.mix(nb.mr(pu, 0.0, 0.35, 0.35, 0.0), capc, srgb('#6e1f14'))
    gl = nb.wave(co, 600.0, 1.0, 1.0, 'RINGS', 'Z')
    gillc = nb.mix(nb.mr(gl, 0.4, 0.9, 0.0, 1.0), srgb('#d6c4cc'), srgb('#5a3a58'))
    c = nb.mix(top, gillc, capc)
    emit = nb.mix(nb.mul(nb.inv(top), 0.8), (0, 0, 0, 1), TEAL_DIM)
    n = nb.bump(nb.mul(sp, top), 0.4, 0.003)
    nb.finish(c, 0.42, n, emit)
    return m


def bulb():
    m, nb = _m('ms_bulb_proc')
    co = nb.coord('Object')
    v = nb.voronoi(co, 180.0, 'F1', out='Distance')
    c = nb.mix(nb.mr(v, 0.1, 0.4, 0.0, 1.0), srgb('#c9fff0'), srgb('#5fe0c4'))
    emit = nb.mix(nb.mr(v, 0.1, 0.45, 1.0, 0.6), (0, 0, 0, 1), TEAL)
    nb.finish(c, 0.25, None, emit)
    return m


def wrap():
    m, nb = _m('ms_wrap_proc')
    co = nb.coord('Object')
    f = nb.noise(nb.mapping(co, scale=(300, 300, 40)), 1.0, 3, 0.6)
    c = nb.mix(nb.mr(f, 0.4, 0.65, 0.0, 1.0), srgb('#e4d6c2'), srgb('#b49aa8'))
    n = nb.bump(f, 0.4, 0.001)
    nb.finish(c, 0.75, n, None)
    return m


def roots():
    m, nb = _m('ms_roots_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    pv = nb.attr('pv')
    fib = nb.wave(nb.comb(pv, nb.mul(pu, 0.08), 0.0), 9.0, 4.0, 2.0, 'BANDS', 'X')
    c = nb.mix(nb.mr(fib, 0.2, 0.8, 0.0, 1.0), srgb('#3e2630'), srgb('#7a5866'))
    tip = nb.mr(pu, 0.7, 1.0, 0.0, 1.0)
    c = nb.mix(nb.mul(tip, 0.6), c, srgb('#9ff5e2'))
    emit = nb.mix(nb.mul(tip, 0.9), (0, 0, 0, 1), TEAL)
    n = nb.bump(fib, 0.5, 0.002)
    nb.finish(c, 0.7, n, emit)
    return m


# ================================================================================================ dress (tint2: light, mild colour)
def threads(sk_center_y=0.035, hem_z=0.32):
    m, nb = _m('ms_threads_proc')
    co = nb.coord('Object')
    s = nb.sep(co)
    ang = angle_xy(nb, co, sk_center_y)
    warp = nb.mul(nb.noise(co, 6.0, 3, 0.5), 2.5)
    th = nb.math('SINE', nb.add(nb.mul(ang, 190.0), warp))
    th2 = nb.math('SINE', nb.add(nb.mul(ang, 61.0), nb.mul(warp, 1.6)))
    thread = nb.mr(nb.add(th, nb.mul(th2, 0.5)), -1.2, 1.4, 0.0, 1.0)
    clumps = nb.noise(nb.mapping(co, scale=(24, 24, 3)), 1.0, 4, 0.6)
    val = nb.add(0.56, nb.mul(thread, 0.30))
    val = nb.add(val, nb.mul(nb.sub(clumps, 0.5), 0.25))
    # fading into roots at the hem
    hem = nb.mr(s[2], hem_z + 0.22, hem_z, 0.0, 1.0)
    val = nb.sub(val, nb.mul(hem, 0.22))
    warm = nb.mr(nb.noise(co, 3.0, 2, 0.5), 0.4, 0.7, 0.0, 1.0)
    c = nb.comb(val, nb.mul(val, 0.95), nb.mul(val, 0.97))
    c = nb.mix(nb.mul(warm, 0.6), c, nb.comb(nb.mul(val, 1.04), val, nb.mul(val, 0.9)))
    c = nb.mix(hem, c, nb.comb(nb.mul(val, 0.85), nb.mul(val, 0.72), nb.mul(val, 0.72)))
    sp = nb.mul(spots(nb, co, 130.0, 0.10, 0.34, 4.0), nb.add(nb.mul(hem, 0.9), 0.1))
    sp = nb.mul(sp, nb.mr(nb.noise(co, 5.0, 2, 0.5), 0.42, 0.58, 0.0, 1.0))
    emit = nb.mix(sp, (0, 0, 0, 1), TEAL)
    h = nb.add(thread, nb.mul(clumps, 0.6))
    n = nb.bump(h, 0.45, 0.002)
    nb.finish(c, nb.add(0.68, nb.mul(clumps, 0.15)), n, emit)
    return m


def frill():
    """turkey-tail zones on top, fine gill lines underneath, pale rim with teal glow dots."""
    m, nb = _m('ms_frill_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')          # 0 attach .. 1 edge
    pv = nb.attr('pv')
    nrm = nb.sep(nb.geo('Normal'))
    under = nb.mr(nrm[2], 0.1, -0.25, 0.0, 1.0)
    wob = nb.mul(nb.noise(co, 9.0, 3, 0.5), 0.12)
    zones = nb.wave(nb.comb(nb.add(pu, wob), 0.0, 0.0), 30.0, 2.0, 2.0, 'BANDS', 'X')
    zv = nb.mr(zones, 0.25, 0.85, 0.0, 1.0)
    val = nb.add(0.48, nb.mul(zv, 0.40))
    val = nb.add(val, nb.mul(nb.mr(pu, 0.86, 0.97, 0.0, 1.0), 0.25))
    vel = nb.noise(nb.mapping(co, scale=(140, 140, 140)), 1.0, 3, 0.6)
    val = nb.add(val, nb.mul(nb.sub(vel, 0.5), 0.10))
    gl = nb.wave(nb.comb(nb.mul(pv, 1.0), 0.0, 0.0), 120.0, 1.0, 1.0, 'BANDS', 'X')
    uval = nb.add(0.62, nb.mul(nb.mr(gl, 0.3, 0.9, 0.0, 1.0), 0.25))
    v = nb.mixf(under, val, uval)
    c = nb.comb(v, nb.mul(v, 0.95), nb.mul(v, 0.96))
    cream = nb.mul(nb.mr(pu, 0.88, 0.98, 0.0, 1.0), nb.inv(under))
    c = nb.mix(nb.mul(cream, 0.6), c, nb.comb(nb.mul(v, 1.06), nb.mul(v, 1.0), nb.mul(v, 0.88)))
    dots = nb.mul(spots(nb, co, 150.0, 0.30, 0.34, 6.0), nb.mr(pu, 0.78, 0.95, 0.0, 1.0))
    emit = nb.mix(dots, (0, 0, 0, 1), TEAL)
    h = nb.add(nb.mul(zv, 0.5), nb.mul(vel, 0.4))
    h = nb.mixf(under, h, gl)
    n = nb.bump(h, 0.4, 0.002)
    nb.finish(c, nb.add(0.55, nb.mul(vel, 0.15)), n, emit)
    return m


def collar():
    m, nb = _m('ms_collar_proc')
    co = nb.coord('Object')
    pu = nb.attr('pu')
    pv = nb.attr('pv')
    pl = nb.math('SINE', nb.mul(pv, 2 * math.pi))
    fine = nb.wave(nb.comb(pv, 0.0, 0.0), 40.0, 0.5, 1.0, 'BANDS', 'X')
    val = nb.add(0.62, nb.mul(pl, 0.12))
    val = nb.add(val, nb.mul(nb.sub(fine, 0.5), 0.12))
    val = nb.add(val, nb.mul(nb.mr(pu, 0.8, 0.98, 0.0, 1.0), 0.2))
    c = nb.comb(val, nb.mul(val, 0.95), nb.mul(val, 0.95))
    edge = nb.mr(pu, 0.85, 1.0, 0.0, 1.0)
    emit = nb.mix(nb.mul(nb.mul(edge, nb.mr(pl, 0.2, 0.9, 0.0, 1.0)), 0.75), (0, 0, 0, 1), TEAL)
    n = nb.bump(nb.add(pl, nb.mul(fine, 0.4)), 0.5, 0.003)
    nb.finish(c, 0.6, n, emit)
    return m
