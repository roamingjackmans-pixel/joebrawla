"""The Ashen Forge (B5) — volcanic foundry at dusk. Landmark: the great furnace mouth glowing behind the fight.

blender -b --factory-startup --python build_forge.py [-- --no-preview]
Blender coords: fighters on y = 0, camera at y = -9.5 looking +Y (depth), Z up.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector
import stagekit as sk
import texgen as tg
import parts as pt
import dj_common as dj
import dj_mats as djm
from dj_common import M

R = random.Random(5)
S = sk.Stage('forge')
N = 2048


# ============================================================================ textures
def tex_floor():
    """Cast-iron deck plates 2 m x 1 m (tile 4 m): bevelled seams, corner bolts, soot, rust, worn edges."""
    d, bid, lx, ly = tg.bricks(N, 2, 4, offset=0.5, seed=3)
    f1 = tg.fbm(N, 4, 6, seed=1)
    f2 = tg.fbm(N, 8, 5, seed=2)
    f3 = tg.fbm(N, 32, 3, seed=3)
    hammer, _, _ = tg.worley(N, 48, seed=4)
    seam = tg.smooth(0.0, 0.03, d)                      # 0 in the seam, 1 on the plate
    edge = 1 - tg.smooth(0.03, 0.09, d)                 # worn band along the edges
    # bolts at the plate corners (plate = 2 m x 1 m; lx, ly in 0..1)
    bolt = np.zeros_like(d)
    for cx in (0.04, 0.96):
        for cy in (0.1, 0.9):
            r = np.sqrt(((lx - cx) * 2.0) ** 2 + ((ly - cy) * 1.0) ** 2)
            bolt = np.maximum(bolt, tg.smooth(0.04, 0.0, r))
    for cx in (0.5,):
        for cy in (0.1, 0.9):
            r = np.sqrt(((lx - cx) * 2.0) ** 2 + ((ly - cy) * 1.0) ** 2)
            bolt = np.maximum(bolt, tg.smooth(0.035, 0.0, r))
    # cast ribs on some plates
    ribs = (bid > 0.72).astype(np.float32) * tg.smooth(0.35, 0.5, np.abs(np.sin(lx * math.pi * 10))) * tg.smooth(0.08, 0.14, d)
    height = seam * 0.55 + (hammer * 0.06) + f3 * 0.05 + bolt * 0.35 + ribs * 0.12
    # colour
    base = tg.gmap(f1 * 0.7 + f2 * 0.3, [(0.0, '#151312'), (0.45, '#2b2622'), (0.75, '#3d3530'), (1.0, '#51463c')])
    tone = (0.78 + 0.4 * bid)[..., None]
    base = base * tone
    rust = tg.smooth(0.58, 0.72, f2 * 0.6 + tg.fbm(N, 16, 4, seed=9) * 0.4) * (1 - edge * 0.8)
    base = tg.mix(base, tg.gmap(f3, [(0, '#3a2116'), (1, '#6a3c22')]), rust * 0.85)
    worn = edge * tg.smooth(0.35, 0.65, f3) + bolt * 0.8 + ribs * 0.5
    base = tg.mix(base, tg.gmap(f3, [(0, '#5d544d'), (1, '#8a7d70')]), np.clip(worn, 0, 1) * 0.75)
    soot = (1 - seam) * 0.9 + tg.smooth(0.55, 0.8, tg.fbm(N, 6, 4, seed=11)) * 0.5
    base = tg.mix(base, np.full_like(base, 0.03), np.clip(soot, 0, 1) * 0.8)
    rough = np.clip(0.78 - worn * 0.3 + rust * 0.12 + soot * 0.1, 0.3, 1)
    metal = np.clip(0.35 + worn * 0.45 - rust * 0.35 - soot * 0.2, 0, 1)
    ao = 1 - (1 - seam) * 0.6
    orm = np.stack([ao, rough, metal], -1)
    return base, orm, tg.normal_from_height(height, 5.0)


def tex_brick():
    """Firebrick from the Quaternius Medieval Village T_Brick (CC0), recoloured and sooted."""
    src = tg.load_png(sk.MV + r"\T_Brick_BaseColor.png", N)[..., :3]
    L = tg.lum(src)
    lo, hi = np.percentile(L, 3), np.percentile(L, 97)
    t = np.clip((L - lo) / (hi - lo), 0, 1)
    f = tg.fbm(N, 4, 5, seed=21)
    base = tg.gmap(t, [(0.0, '#120c0a'), (0.3, '#2c1812'), (0.55, '#5e2c1e'), (0.75, '#7c3d27'), (1.0, '#b2704c')])
    var = tg.fbm(N, 12, 3, seed=22)
    base = base * (0.75 + 0.45 * var)[..., None]
    soot = tg.smooth(0.45, 0.75, f)
    base = tg.mix(base, base * 0.25, soot * 0.7)
    nrm = tg.load_png(sk.MVT + r"\Normals Godot-Unity\T_Brick_Normal.png", N)[..., :3]
    rough = tg.load_png(sk.MV + r"\T_Brick_Roughness.png", N)[..., 0]
    ao = np.clip(0.55 + 0.45 * t, 0, 1)
    orm = np.stack([ao, np.clip(rough * 0.9 + 0.1, 0, 1), np.zeros_like(rough)], -1)
    return base, orm, nrm


def tex_iron():
    """Structural iron: dark hammered metal, rust runs, soot (tile 3 m)."""
    f1 = tg.fbm(N, 4, 6, seed=31)
    f2 = tg.fbm(N, 10, 4, seed=32)
    streak = tg.fbm(N, 24, 4, seed=33, cells_v=2)
    dent, _, _ = tg.worley(N, 20, seed=34)
    base = tg.gmap(f1, [(0.0, '#151312'), (0.5, '#2a2522'), (1.0, '#433a33')])
    rust = tg.smooth(0.6, 0.75, streak * 0.6 + f2 * 0.4)
    base = tg.mix(base, tg.gmap(f2, [(0, '#3a1f12'), (1, '#7a4426')]), rust * 0.8)
    hi = tg.smooth(0.62, 0.8, tg.fbm(N, 20, 3, seed=35))
    base = tg.mix(base, np.full_like(base, 0.36), hi * 0.35)
    height = dent * 0.15 + f2 * 0.2 + rust * 0.15
    rough = np.clip(0.62 + rust * 0.25 - hi * 0.2, 0, 1)
    metal = np.clip(0.55 - rust * 0.5 + hi * 0.3, 0, 1)
    orm = np.stack([np.ones_like(f1), rough, metal], -1)
    return base, orm, tg.normal_from_height(height, 3.0)


def tex_rock():
    """Basalt with cooled-lava cracks (tile 6 m)."""
    f1, f2, cid = tg.worley(N, 7, seed=41)
    edge = f2 - f1
    crack = 1 - tg.smooth(0.0, 0.07, edge)
    n1 = tg.fbm(N, 6, 6, seed=42)
    n2 = tg.fbm(N, 24, 4, seed=43)
    height = (0.6 + 0.4 * cid) * tg.smooth(0.0, 0.25, edge) + n1 * 0.35 + n2 * 0.15 - crack * 0.4
    base = tg.gmap(n1 * 0.6 + cid * 0.4, [(0.0, '#100d0c'), (0.5, '#231d1a'), (1.0, '#3c322c')])
    base = tg.mix(base, tg.gmap(n2, [(0, '#463a32'), (1, '#6a5a4c')]), tg.smooth(0.55, 0.8, n2 * 0.7 + n1 * 0.3) * 0.45)
    base = tg.mix(base, np.full_like(base, 0.01), crack * 0.9)
    rough = np.clip(0.88 - n2 * 0.1, 0, 1)
    orm = np.stack([1 - crack * 0.6, rough, np.zeros_like(rough)], -1)
    return base, orm, tg.normal_from_height(height, 6.0)


def tex_lava():
    """Molten channel surface: cooling crust plates and bright seams (emissive, tile 4 m)."""
    n = 1024
    f1, f2, cid = tg.worley(n, 6, seed=51)
    w = tg.fbm(n, 4, 5, seed=52)
    g1, g2, _ = tg.worley(n, 14, seed=53)
    edge = f2 - f1
    seam = 1 - tg.smooth(0.0, 0.16, edge)
    seam2 = 1 - tg.smooth(0.0, 0.08, g2 - g1)
    heat = np.clip(seam * 0.95 + seam2 * 0.35 * (1 - cid) + w * 0.35 - 0.12, 0, 1)
    emit = tg.gmap(heat, [(0.0, '#1a0400'), (0.25, '#5a0c00'), (0.5, '#c22d04'), (0.75, '#ff7a14'), (0.92, '#ffc45a'), (1.0, '#fff2c8')])
    crust = tg.gmap(w, [(0, '#140806'), (1, '#2e130a')])
    base = tg.mix(crust, tg.gmap(heat, [(0, '#3a1206'), (1, '#ff8a30')]), tg.smooth(0.35, 0.7, heat))
    return emit, base


# ============================================================================ materials
def build_materials():
    b, o, n = tex_floor()
    S.tile_group('forge_floor', b, o, n, scale=4.0, ao=0.6)
    b, o, n = tex_brick()
    S.tile_group('forge_brick', b, o, n, scale=3.2, ao=0.6)
    b, o, n = tex_iron()
    S.tile_group('forge_iron', b, o, n, scale=3.0, ao=0.55)
    b, o, n = tex_rock()
    S.tile_group('forge_rock', b, o, n, scale=7.0, ao=0.5)
    e, b = tex_lava()
    S.emissive_tile('forge_lava', e, b, scale=4.0, strength=4.0)
    S.palette('forge_pal', [
        ('iron_dark', '#1c1918', 0.7, 0.45), ('iron', '#37312d', 0.6, 0.5), ('rust', '#5a3624', 0.9, 0.0),
        ('brick_far', '#3e1d16', 0.9, 0.0), ('rock_far', '#1d1817', 0.95, 0.0), ('rock_mid', '#2b2421', 0.95, 0.0),
        ('smoke', '#c49488', 1.0, 0.0), ('smoke_dark', '#5e4a50', 1.0, 0.0), ('brass', '#a8823e', 0.4, 0.85),
        ('rubber', '#141313', 0.85, 0.0), ('wood', '#4a3020', 0.85, 0.0), ('coal', '#0d0b0b', 0.8, 0.0),
        ('ash', '#5d5550', 0.95, 0.0), ('paint_yellow', '#c39324', 0.6, 0.0), ('paint_red', '#7a1d15', 0.6, 0.0),
        ('chalk', '#d8d0c0', 0.9, 0.0), ('steel', '#6d6a68', 0.35, 0.9), ('glass_dark', '#1a1410', 0.15, 0.0),
    ])
    S.palette('forge_glow', [
        ('hot', '#fff1c4', 1.0), ('molten', '#ffb347', 1.0), ('fire', '#ff7a1c', 1.0), ('ember', '#e0480e', 0.75),
        ('dim', '#b0300a', 0.45), ('window', '#ffa040', 0.7), ('window_dim', '#ff8a30', 0.42), ('crater', '#ff5a14', 0.9),
        ('lava_far', '#ff4a10', 0.65), ('gauge', '#ffe2a8', 0.55), ('deep', '#8a1c04', 0.35), ('spark', '#ffe9a0', 1.0),
    ], glow=True, strength=5.0)
    S.palette('forge_flicker', [('flame', '#ffb040', 1.0), ('flame_hot', '#fff0b0', 1.0), ('flame_red', '#ff6a18', 0.9)],
              glow=True, strength=5.0)


# ============================================================================ props (baked atlas)
def build_protos():
    P = {}
    P['anvil'] = S.kit(sk.FP + r"\Anvil.gltf")
    P['anvil_log'] = S.kit(sk.FP + r"\Anvil_Log.gltf")
    P['chain_coil'] = S.kit(sk.FP + r"\Chain_Coil.gltf")
    P['crate_metal'] = S.kit(sk.FP + r"\Crate_Metal.gltf")
    P['crate_wood'] = S.kit(sk.FP + r"\Crate_Wooden.gltf")
    P['barrel'] = S.kit(sk.FP + r"\Barrel.gltf")
    P['bucket'] = S.kit(sk.FP + r"\Bucket_Metal.gltf")
    P['workbench'] = S.kit(sk.FP + r"\Workbench.gltf")
    P['torch'] = S.kit(sk.FP + r"\Torch_Metal.gltf")
    P['cauldron'] = S.kit(sk.FP + r"\Cauldron.gltf")
    P['whetstone'] = S.kit(sk.FP + r"\Whetstone.gltf")
    P['pickaxe'] = S.kit(sk.FP + r"\Pickaxe_Bronze.gltf")
    # custom procedural props
    iron = djm.iron('p_iron', base='#3a3633', light='#7a716a', rust='#6a3a20', rust2='#94582c', rustamt=0.45, seed=3, metal=0.6)
    iron2 = djm.iron('p_iron2', base='#2c2826', light='#6a625c', rust='#5a301a', rust2='#7a4a26', rustamt=0.3, seed=7, metal=0.65)
    brass = djm.brass('p_brass', base='#b88a3a', verd=0.12)
    steel = djm.iron('p_steel', base='#5a5856', light='#a8a49e', rust='#5a3a26', rust2='#7a5030', rustamt=0.15, seed=9, metal=0.85)
    wood = djm.wood('p_wood', base='#6a4428', dark='#3a2414', light='#9a6e44', weather=0.3, seed=2)
    refr = djm.stone('p_refractory', base='#5a4a40', light='#7a6658', dark='#2a201a', warm='#8a6a52', moss=0.0, lichen=0.0,
                     edge=0.4, streak=0.3, seed=4, moss_bottom=0.0, patches='#3a2a22')
    # crucible: refractory-lined iron ladle with trunnions and a pouring lip (origin at its base centre)
    prof = [(0.0, 0.0), (0.55, 0.0), (0.72, 0.08), (0.86, 0.5), (0.95, 1.3), (1.0, 1.75), (1.08, 1.82), (1.08, 1.92), (0.96, 1.92),
            (0.9, 1.84), (0.86, 1.4), (0.78, 0.6), (0.0, 0.5)]
    cr = dj.lathe('crucible_body', prof, 28, iron, cap_bottom=False, cap_top=False)
    bands = [dj.cyl('cr_band', 0.94 + 0.04 * k, 0.12, 28, loc=(0, 0, 0.45 + 0.55 * k), mat=iron2) for k in range(3)]
    lip = dj.box('cr_lip', 0.5, 0.5, 0.12, loc=(1.05, 0, 1.8), mat=iron)
    tr = [dj.cyl('cr_trun', 0.16, 0.35, 12, loc=(0, s * 1.05, 1.1), rot=(90, 0, 0), mat=steel) for s in (-1, 1)]
    bosses = [dj.cyl('cr_boss', 0.24, 0.12, 12, loc=(0, s * 0.95, 1.1), rot=(90, 0, 0), mat=iron2) for s in (-1, 1)]
    P['crucible'] = S.proto(dj.join([cr] + bands + [lip] + tr + bosses, 'P_crucible'), weight=3.0)
    dj.smooth(P['crucible'], 35)
    bail_path = [(0, -1.2, 1.1), (0, -1.25, 2.4), (0, -0.9, 3.4), (0, 0, 3.75), (0, 0.9, 3.4), (0, 1.25, 2.4), (0, 1.2, 1.1)]
    bail = dj.tube('P_bail', bail_path, 0.07, 8, iron2)
    P['bail'] = S.proto(bail, weight=1.0)
    # ingot mould: a long iron tray with 4 cavities (glow tops are separate)
    parts = [dj.box('mould_base', 3.4, 1.0, 0.45, loc=(0, 0, 0), mat=iron)]
    for k in range(4):
        parts.append(dj.box('mould_rim', 0.72, 0.8, 0.08, loc=(-1.2 + 0.8 * k, 0, 0.45), mat=iron2))
    m = dj.join(parts, 'P_mould')
    dj.bevel(m, 0.02, 1, 35)
    P['mould'] = S.proto(m, weight=1.2)
    # keys and padlocks (the forge's product)
    P['key_brass'] = S.proto(pt.key_obj('P_key_brass', 0.55, brass), weight=0.6)
    P['key_iron'] = S.proto(pt.key_obj('P_key_iron', 0.5, steel), weight=0.6)
    P['lock'] = S.proto(pt.padlock('P_lock', 0.42, iron2, steel), weight=0.8)
    P['lock_brass'] = S.proto(pt.padlock('P_lock_brass', 0.38, brass, steel), weight=0.8)
    # punch clock on a post ("Clock In")
    parts = [dj.box('pc_post', 0.14, 0.14, 1.25, loc=(0, 0.05, 0), mat=wood),
             dj.box('pc_case', 0.5, 0.32, 0.62, loc=(0, 0, 1.2), mat=wood),
             dj.cyl('pc_bezel', 0.17, 0.05, 24, loc=(0, -0.16, 1.62), rot=(90, 0, 0), mat=brass),
             dj.box('pc_slot', 0.2, 0.06, 0.03, loc=(0, -0.17, 1.3), mat=iron2),
             dj.box('pc_rack', 0.62, 0.08, 0.9, loc=(0.62, 0.02, 0.85), mat=wood)]
    for k in range(6):
        parts.append(dj.box('pc_card', 0.09, 0.02, 0.2, loc=(0.42 + 0.08 * (k % 5), -0.04, 0.95 + 0.25 * (k // 5) + 0.02 * (k % 2)),
                            mat=djm.plain('p_card', '#d9cfb4', 0.9)))
    pcm = dj.join(parts, 'P_punchclock')
    P['punchclock'] = S.proto(pcm, weight=1.5)
    # sign boards with lettering
    P['sign_quota'] = S.proto(sign('P_sign_quota', ['QUOTA', '1000000 KEYS'], 2.4, 1.2), weight=2.5)
    P['sign_days'] = S.proto(sign('P_sign_days', ['NO DAYS OFF'], 3.4, 0.8, bg='#7a1d15', fg='#e8d8b0'), weight=2.5)
    # tongs and a sledge for the anvils
    tong = dj.join([pt.rod('t1', (0, 0, 0), (1.1, 0.04, 0), 0.025, 6, iron2), pt.rod('t2', (0, 0.06, 0), (1.1, 0.0, 0), 0.025, 6, iron2)], 'P_tongs')
    P['tongs'] = S.proto(tong, weight=0.4)
    hm = dj.join([dj.box('hm_head', 0.34, 0.16, 0.16, loc=(0, 0, 0), mat=steel), pt.rod('hm_h', (0, 0, 0.08), (0, 0, 0.08), 0.02, 6, wood),
                  dj.cyl('hm_handle', 0.03, 0.9, 8, loc=(0, 0, 0.12), mat=wood)], 'P_sledge')
    dj.xform(hm, rot=(90, 0, 0))
    P['sledge'] = S.proto(hm, weight=0.4)
    # gauge (brass bezel + dark face; the glowing dial is separate)
    g = dj.join([dj.cyl('g_bez', 0.55, 0.16, 32, loc=(0, 0, 0), rot=(90, 0, 0), mat=brass),
                 dj.cyl('g_back', 0.5, 0.2, 24, loc=(0, 0.2, 0), rot=(90, 0, 0), mat=iron2),
                 pt.rod('g_pipe', (0, 0.1, -0.5), (0, 0.1, -2.2), 0.08, 10, brass)], 'P_gauge')
    P['gauge'] = S.proto(g, weight=1.5)
    return P


def sign(name, lines, w, h, bg='#2b2622', fg='#d8c9a0'):
    """Painted board facing -Y, bottom centre at the origin."""
    strokes = []
    k = len(lines)
    ch = h * 0.6 / k
    for i, ln in enumerate(lines):
        y = h - (i + 1) * (h / k) + (h / k - ch) / 2
        strokes += dj.text_strokes(ln, w / 2, y, ch * (0.85 if len(ln) > 8 else 1.0), width_frac=0.14,
                                   spacing=min(0.78, (w * 0.9) / max(1, len(ln)) / ch))
    img = dj.stroke_image(name + '_txt', w, h, strokes, res=1024)
    m = M(name + '_mat')
    P = djm._P(m, 3)
    n = m.noise(P, 6.0, 4)
    c = m.mix(m.mul(m.mr(n, 0.4, 0.7), 0.5), bg, '#1a1512')
    lm = djm.carve_mask(m, img, -w / 2, 0.0, w, h)
    c = m.mix(m.mul(lm, 0.95), c, fg)
    c = m.mix(m.mul(m.edge_mask(0.01, 0.1, 0.5), 0.6), c, '#6a5a48')
    m.set(color=c, rough=0.8, metal=0.0, height=n, bump=0.2, bump_dist=0.003)
    b = dj.box(name, w, 0.07, h, loc=(0, 0, 0), mat=m, cuts=1)
    dj.bevel(b, 0.02, 2, 35)
    frame = [dj.box(name + '_f', w + 0.1, 0.09, 0.06, loc=(0, 0.005, z), mat=djm.plain(name + '_fm', '#2a2420', 0.7, 0.3)) for z in (-0.03, h - 0.03)]
    return dj.join([b] + frame, name)


# ============================================================================ the set
def floor_and_channel():
    fl = sk.plane_grid('floor_front', -32, 32, -12, 3.0, 64, 15)
    S.add(fl, 'forge_floor', shadow=False)
    # molten channel behind the fighting line (y 3.0 .. 5.0), recessed
    for y0, y1 in ((3.0, 3.4), (4.6, 5.0)):
        c = dj.box('curb', 64, y1 - y0, 0.48, loc=(0, (y0 + y1) / 2, -0.32))
        dj.bevel(c, 0.03, 2, 35)
        sk.subdivide_long(c, 2.0)
        S.add(c, 'forge_iron', uv_scale=2.0)
        # rivets along the curb top
        for x in np.arange(-31.5, 32, 1.0):
            rv = dj.cyl('rivet', 0.035, 0.03, 6, loc=(x, (y0 + y1) / 2, 0.16))
            S.pal(rv, 'iron')
    lava = sk.plane_grid('lava', -32, 32, 3.4, 4.6, 64, 2, z=-0.14)
    S.add(lava, 'forge_lava', shadow=False, uv_scale=3.0)
    # channel inner walls (glow-lit iron)
    for y in (3.4, 4.6):
        w = dj.box('chwall', 64, 0.02, 0.4, loc=(0, y, -0.5))
        S.glow(w, 'deep')
    # two plate bridges with rails (outside the fighting floor)
    for x in (-15.0, 15.0):
        br = dj.box('bridge', 2.0, 2.4, 0.08, loc=(x, 4.0, 0.16))
        S.add(br, 'forge_iron', uv_scale=2.0)
        for s in (-1, 1):
            r = pt.railing('rail', [(x + s * 0.95, 2.95, 0.24), (x + s * 0.95, 5.05, 0.24)], h=0.95, post=1.0, r=0.03)
            S.add(r, 'forge_iron', uv_scale=1.5)
    # back floor
    bf = sk.plane_grid('floor_back', -40, 40, 5.0, 37, 40, 16)
    S.add(bf, 'forge_floor', shadow=False)
    # rails for slag carts set in the floor (flat) at y = 24
    for y in (23.4, 24.6):
        rl = dj.box('track', 80, 0.12, 0.06, loc=(0, y, 0))
        S.pal(rl, 'steel')
    for x in np.arange(-39, 40, 1.1):
        sl = dj.box('sleeper', 0.25, 1.8, 0.03, loc=(x, 24, 0))
        S.pal(sl, 'iron_dark')


def furnace():
    """The great furnace (landmark): brick body on a plinth, iron-framed arched mouth glowing white-hot."""
    # plinth (terrace) with side stairs
    pl = dj.box('plinth', 52, 22, 3.5, loc=(0, 47, 0))
    sk.subdivide_long(pl, 2.5)
    S.add(pl, 'forge_brick')
    cor = dj.box('cornice', 52.4, 0.6, 0.35, loc=(0, 36.1, 3.3))
    S.add(cor, 'forge_iron')
    base_course = dj.box('basecourse', 52.4, 0.5, 0.5, loc=(0, 36.05, 0))
    S.add(base_course, 'forge_iron')
    for x in (-23, -10, 10, 23):
        p = dj.box('pier', 1.4, 0.8, 3.6, loc=(x, 35.9, 0))
        S.add(p, 'forge_brick')
    for s in (-1, 1):
        st = pt.stairs('stairs', s * 17.0, s * 20.0, 30.5, 36.0, 0.0, 3.5, 14)
        if s < 0:
            st = pt.stairs('stairs', -20.0, -17.0, 30.5, 36.0, 0.0, 3.5, 14)
        S.add(st, 'forge_brick', uv_scale=2.0)
        r = pt.railing('srail', [(s * 16.9 if s > 0 else -20.1, 30.5, 0.0), (s * 16.9 if s > 0 else -20.1, 36.0, 3.5)], h=1.0, post=1.4)
        S.add(r, 'forge_iron', uv_scale=1.5)
    # glowing vents in the plinth face
    for x in (-5.0, 5.0):
        v = dj.box('vent_glow', 2.2, 0.1, 0.7, loc=(x, 36.02, 0.6))
        S.glow(v, 'ember')
        for k in range(6):
            b = dj.box('vent_bar', 0.08, 0.12, 0.8, loc=(x - 0.95 + 0.38 * k, 35.94, 0.55))
            S.pal(b, 'iron_dark')
        fr = dj.box('vent_frame', 2.5, 0.16, 0.12, loc=(x, 35.95, 1.32))
        S.add(fr, 'forge_iron')
    # furnace body
    FY = 40.0
    body = dj.box('furnace', 28, 14, 26, loc=(0, FY + 7, 3.5))
    mouth_w, spring = 10.0, 3.5 + 3.6
    cut = pt.cutter_xz('mouthcut', pt.arch_outline(0, mouth_w, spring, 24, bottom=3.4), FY - 1, FY + 4.5)
    pt.boolean(body, cut)
    sk.subdivide_long(body, 3.0)
    S.add(body, 'forge_brick')
    # buttress towers
    for s in (-1, 1):
        bt = dj.box('buttress', 6, 12, 22, loc=(s * 17, FY + 6.5, 3.5))
        dj.xform(bt, scale=(1, 1, 1))
        for v in bt.data.vertices:
            if v.co.z > 20:
                v.co.x = s * 17 + (v.co.x - s * 17) * 0.75
                v.co.y = FY + 6.5 + (v.co.y - FY - 6.5) * 0.85
        sk.subdivide_long(bt, 3.0)
        S.add(bt, 'forge_brick')
        cap = dj.box('bcap', 5.2, 11, 0.6, loc=(s * 17, FY + 6.5, 25.5))
        S.add(cap, 'forge_iron')
        # chimney
        ch = dj.cyl('chimney', 2.0, 34, 20, r2=1.6, loc=(s * 9.0, FY + 9, 29.5))
        sk.subdivide_long(ch, 4.0)
        S.add(ch, 'forge_brick', shadow=False)
        for z in (32, 40, 48, 56, 62.5):
            rg = dj.cyl('chring', 2.15 - (z - 29.5) / 34 * 0.4 + 0.05, 0.5, 20, loc=(s * 9.0, FY + 9, z))
            S.add(rg, 'forge_iron', shadow=False)
        tip = dj.cyl('chtip', 1.7, 0.4, 20, loc=(s * 9.0, FY + 9, 63.3))
        S.glow(tip, 'ember')
    # iron arch frame around the mouth
    ring = pt.ring_xz('archframe', 0, spring, mouth_w / 2, mouth_w / 2 + 1.1, 0, math.pi, 1.0, FY - 0.3, 28)
    S.add(ring, 'forge_iron', uv_scale=2.0)
    for s in (-1, 1):
        jb = dj.box('jamb', 1.1, 1.0, spring - 3.5, loc=(s * (mouth_w / 2 + 0.55), FY - 0.3, 3.5))
        S.add(jb, 'forge_iron', uv_scale=2.0)
    ks = dj.box('keystone', 1.6, 1.4, 1.8, loc=(0, FY - 0.45, spring + mouth_w / 2 - 0.3))
    S.add(ks, 'forge_iron', uv_scale=2.0)
    for i in range(23):
        a = math.pi * (i + 0.5) / 23
        rr = mouth_w / 2 + 0.55
        rv = dj.sphere('arivet', 0.09, 8, 5, loc=(rr * math.cos(a), FY - 0.85, spring + rr * math.sin(a)))
        S.pal(rv, 'iron')
    # mouth interior: glowing tunnel, brighter with depth; molten floor
    for (y0, y1, key) in ((FY - 0.6, FY + 0.6, 'ember'), (FY + 0.6, FY + 2.2, 'fire'), (FY + 2.2, FY + 3.6, 'molten')):
        tun = pt.cutter_xz('tunnel', pt.arch_outline(0, mouth_w - 0.02, spring, 24, bottom=3.45), y0, y1)
        dj.delete_faces(tun, lambda c, n: abs(n.y) > 0.9)
        for p in tun.data.polygons:
            p.flip()
        S.glow(tun, key)
    back = dj.extrude_xz('mouthback', pt.arch_outline(0, mouth_w, spring, 24, bottom=3.4), 0.2, y=FY + 3.6)
    S.glow(back, 'hot')
    pool = sk.plane_grid('pool', -mouth_w / 2, mouth_w / 2, FY - 0.6, FY + 3.6, 10, 4, z=3.55)
    S.add(pool, 'forge_lava', shadow=False, uv_scale=2.5)
    # flames inside the mouth (flicker)
    fl = []
    for i, x in enumerate(np.linspace(-3.8, 3.8, 7)):
        hgt = R.uniform(2.0, 4.2) * (1.0 - abs(x) / 7)
        wdt = R.uniform(0.9, 1.4)
        pts = [(x - wdt / 2, 3.5), (x + wdt / 2, 3.5), (x + wdt * 0.32, 3.5 + hgt * 0.45), (x + wdt * 0.1, 3.5 + hgt * 0.75),
               (x + R.uniform(-0.2, 0.2), 3.5 + hgt), (x - wdt * 0.15, 3.5 + hgt * 0.7), (x - wdt * 0.35, 3.5 + hgt * 0.4)]
        f = dj.extrude_xz('flame', pts, 0.05, y=FY + R.uniform(1.6, 3.2))
        fl.append(f)
    fj = dj.join(fl, 'anim_flicker_furnace')
    S.add(fj, 'forge_flicker', key='flame_hot', shadow=False)
    # open iron doors (hinged at the frame, swung toward the camera)
    for s in (-1, 1):
        dw, dh = mouth_w / 2 + 0.6, spring - 3.5 + mouth_w / 2 + 0.3
        outline = [(0, 0), (dw, 0), (dw, dh - dw * 0.55)]
        for i in range(1, 9):
            a = math.pi / 2 * i / 8
            outline.append((dw - dw * math.sin(a), dh - dw * 0.55 + dw * 0.55 * math.sin(a) * 0 + (dw * 0.55) * (1 - math.cos(a)) * 0 + dw * 0.55 * math.sin(a)))
        outline.append((0, dh))
        door = dj.extrude_xz('door', outline, 0.35, y=0)
        straps = [dj.box('dstrap', dw - 0.2, 0.12, 0.35, loc=(dw / 2, -0.22, z)) for z in (1.0, dh * 0.45, dh * 0.75)]
        door = dj.join([door] + straps, 'door')
        peep = dj.cyl('peep', 0.45, 0.1, 20, loc=(dw * 0.5, -0.2, dh * 0.6), rot=(90, 0, 0))
        S.glow(peep, 'fire')
        if s < 0:
            dj.xform(door, scale=(-1, 1, 1))
            dj.xform(peep, scale=(-1, 1, 1))
            for p in door.data.polygons:
                p.flip()
        hx = s * (mouth_w / 2 + 1.15)
        ang = s * 62.0
        for ob in (door, peep):
            dj.xform(ob, rot=(0, 0, ang))
            dj.xform(ob, loc=(hx, FY - 0.9, 3.5))
        S.add(door, 'forge_iron', uv_scale=2.0)
        for z in (4.5, 3.5 + dh - 2.0):
            hg = dj.cyl('hinge', 0.25, 1.2, 10, loc=(hx, FY - 0.95, z))
            S.pal(hg, 'iron_dark')
    # hood over the mouth
    hood = dj.extrude_xz('hood', [(-8, 0), (8, 0), (6.5, 3.5), (-6.5, 3.5)], 3.2, y=0)
    dj.xform(hood, rot=(-28, 0, 0))
    dj.xform(hood, loc=(0, FY - 1.5, spring + mouth_w / 2 + 1.4))
    S.add(hood, 'forge_iron', uv_scale=2.5)
    # iron straps across the facade
    for z in (spring + mouth_w / 2 + 5.5, 22.5, 28.8):
        st = dj.box('strap', 28.4, 0.4, 0.5, loc=(0, FY - 0.1, z))
        S.add(st, 'forge_iron')
    # gauges and pipes either side of the mouth
    for s in (-1, 1):
        S.inst(P['gauge'], (s * 9.0, FY - 0.15, 9.5), (0, 0, 0), 1.6)
        dial = dj.cyl('dial', 0.72, 0.05, 28, loc=(s * 9.0, FY - 0.42, 9.5), rot=(90, 0, 0))
        S.glow(dial, 'gauge')
        nd = pt.bar('needle', (s * 9.0, FY - 0.47, 9.5), (s * 9.0 + 0.45 * s, FY - 0.47, 9.95), 0.06, 0.02)
        S.pal(nd, 'paint_red')
        pp = dj.tube('fpipe', [(s * 12.5, FY - 0.6, 3.5), (s * 12.5, FY - 0.6, 16), (s * 10.5, FY - 0.6, 18), (s * 10.5, FY - 0.6, 30)], 0.35, 12)
        S.add(pp, 'forge_iron', uv_scale=2.0)
        for z in (6, 11, 15):
            fl_ = dj.cyl('flange', 0.5, 0.2, 12, loc=(s * 12.5, FY - 0.6, z))
            S.pal(fl_, 'iron_dark')
    # glow wash on the plinth top in front of the mouth (fake bounce)
    wash = sk.plane_grid('wash', -6, 6, FY - 3.6, FY - 0.5, 6, 2, z=3.505)
    S.add(wash, 'forge_lava', shadow=False, uv_scale=2.0)


def crane_and_pour():
    """Gantry crane across the midground, a tilted crucible pouring into ingot moulds, hanging chains."""
    Y = 13.0
    top = 11.5
    for s in (-1, 1):
        x = s * 13.5
        for dy in (-2.2, 2.2):
            leg = pt.ibeam('cleg', (x, Y + dy, 0), (x, Y + dy * 0.12, top), 0.6, 0.45, 0.06, up=(1, 0, 0))
            S.add(leg, 'forge_iron', uv_scale=2.0)
        brace = pt.ibeam('cbrace', (x, Y - 1.4, 4.5), (x, Y + 1.4, 4.5), 0.35, 0.3, 0.05)
        S.add(brace, 'forge_iron', uv_scale=2.0)
        foot = dj.box('cfoot', 1.2, 5.6, 0.25, loc=(x, Y, 0))
        S.add(foot, 'forge_iron', uv_scale=2.0)
        whl = dj.box('cwheel', 1.4, 1.2, 0.9, loc=(x, Y, top - 0.4))
        S.add(whl, 'forge_iron', uv_scale=2.0)
    for dz in (0.0, 0.0):
        beam = pt.ibeam('cbeam', (-15, Y, top + 0.5), (15, Y, top + 0.5), 1.2, 0.7, 0.08)
        S.add(beam, 'forge_iron', uv_scale=2.0)
    # trolley + chains to the crucible
    tx = -8.0
    tro = dj.box('trolley', 2.2, 1.6, 1.0, loc=(tx, Y, top - 0.6))
    S.add(tro, 'forge_iron', uv_scale=2.0)
    # crucible tilted toward +x, pouring
    cz = 4.4
    c = S.inst(P['crucible'], (tx, Y, cz), (0, -38, 0), 1.0)
    b = S.inst(P['bail'], (tx, Y, cz), (0, -12, 0), 1.0)
    for dy in (-0.3, 0.3):
        ch = pt.chain('cchain', [(tx + dy * 0.5, Y + dy, top - 0.6), (tx + 0.55 + dy * 0.2, Y + dy, cz + 3.55)], 0.24, 0.035)
        S.add(ch, 'forge_iron', uv_scale=1.0)
    # molten surface in the tilted crucible
    surf = dj.cyl('cr_surf', 0.86, 0.02, 24, loc=(0, 0, 1.55))
    dj.xform(surf, rot=(0, -38, 0))
    dj.xform(surf, loc=(tx, Y, cz))
    # keep the surface level-ish: flatten it toward world horizontal
    S.glow(surf, 'molten')
    # the pour: from the lip down into the mould
    lip = Vector((tx, Y, cz)) + Vector((1.05, 0, 1.85)).copy()
    import mathutils
    rot = mathutils.Euler((0, math.radians(-38), 0)).to_matrix()
    lip = Vector((tx, Y, cz)) + rot @ Vector((1.12, 0, 1.86))
    mx = 1.2
    path = [lip + Vector((0.05, 0, 0.05)), lip + Vector((0.35, 0, -0.1)), lip + Vector((0.55, 0, -0.6))]
    tgt = Vector((tx + 2.2, Y, 0.55))
    for i in range(1, 7):
        t = i / 6
        p = path[-1].lerp(tgt, t)
        p.x += math.sin(t * 9) * 0.04
        path.append(p)
    radii = [0.16, 0.15, 0.13] + [0.12 - 0.03 * (i / 6) + 0.02 * math.sin(i * 2.1) for i in range(1, 7)]
    stream = dj.tube('stream', path, 0.12, 10, radii=radii)
    S.glow(stream, 'hot')
    splash = pt.blob_cluster('splash', (tgt.x, Y, 0.62), 0.22, 6, seed=3, subdiv=1, squash=0.5)
    S.glow(splash, 'molten')
    # ingot moulds under the pour (the receiving cavity bright, the others cooling)
    mx0 = tgt.x - 1.2
    S.inst(P['mould'], (tgt.x + 1.2 - 0.0, Y, 0), (0, 0, 0), 1.0)
    for k, key in enumerate(('molten', 'fire', 'ember', 'dim')):
        g = dj.box('ingot', 0.62, 0.7, 0.02, loc=(tgt.x + 1.2 - 1.2 + 0.8 * k - 0.0, Y, 0.47))
        S.glow(g, key)
    # a second crucible hanging idle on the right, rim glowing
    tx2 = 7.5
    tro2 = dj.box('trolley2', 2.2, 1.6, 1.0, loc=(tx2, Y, top - 0.6))
    S.add(tro2, 'forge_iron', uv_scale=2.0)
    S.inst(P['crucible'], (tx2, Y, 5.6), (0, 0, 15), 0.85)
    S.inst(P['bail'], (tx2, Y, 5.6), (0, 0, 15), 0.85)
    for dy in (-0.25, 0.25):
        ch = pt.chain('cchain2', [(tx2, Y + dy, top - 0.6), (tx2, Y + dy * 0.2, 5.6 + 3.75 * 0.85)], 0.24, 0.035)
        S.add(ch, 'forge_iron', uv_scale=1.0)
    s2 = dj.cyl('cr2_surf', 0.78, 0.02, 24, loc=(tx2, Y, 5.6 + 1.5))
    S.glow(s2, 'ember')
    # hanging chains with hooks (sway)
    for i, (x, bottom) in enumerate(((-3.0, 5.4), (0.6, 6.6), (3.2, 4.8), (11.0, 3.6))):
        parts_ = [pt.chain('hch', [(x, Y, top - 0.1), (x, Y, bottom)], 0.2, 0.03)]
        parts_.append(pt.hook('hk', (x, Y, bottom + 0.05), 0.55))
        ob = dj.join(parts_, f'anim_sway_chain{i}')
        sk.set_origin_top = None
        ob.data.transform(__import__('mathutils').Matrix.Translation((-x, -Y, -(top - 0.1))))
        ob.location = (x, Y, top - 0.1)
        S.add(ob, 'forge_iron', uv_scale=1.0)
    # an ingot hanging from the right chain as a counterweight: a padlock
    S.inst(P['lock'], (11.0 + 0.25, Y, 3.0), (0, 0, 0), 1.6)


def conveyor():
    """Inclined conveyor carrying keys and padlocks up to a hopper on the right tower."""
    y = 9.5
    a = Vector((5.0, y, 1.0))
    b = Vector((13.0, y, 5.2))
    d = (b - a)
    L = d.length
    ang = math.degrees(math.atan2(d.z, d.x))
    # frame rails
    for dy in (-0.75, 0.75):
        r = pt.bar('crail', a + Vector((0, dy, 0)), b + Vector((0, dy, 0)), 0.12, 0.35)
        S.add(r, 'forge_iron', uv_scale=1.5)
    belt = pt.bar('belt', a + Vector((0, 0, 0.02)), b + Vector((0, 0, 0.02)), 1.4, 0.08)
    S.pal(belt, 'rubber')
    n = int(L / 0.6)
    for i in range(n + 1):
        p = a.lerp(b, i / n) + Vector((0, 0, -0.12))
        rl = dj.cyl('roller', 0.1, 1.5, 8, loc=(p.x, p.y - 0.75, p.z), rot=(-90, 0, 0))
        S.pal(rl, 'steel')
    # legs
    for t in (0.05, 0.4, 0.75):
        p = a.lerp(b, t)
        for dy in (-0.7, 0.7):
            lg = pt.bar('cleg', (p.x, y + dy, 0), (p.x, y + dy, p.z - 0.15), 0.14, 0.14)
            S.add(lg, 'forge_iron', uv_scale=1.5)
        xb = pt.bar('cxb', (p.x, y - 0.7, p.z * 0.5), (p.x, y + 0.7, p.z * 0.5), 0.08, 0.08)
        S.add(xb, 'forge_iron', uv_scale=1.5)
    # cargo on the belt
    items = ['key_brass', 'lock', 'key_iron', 'lock_brass', 'key_brass', 'key_iron', 'lock', 'key_brass', 'lock_brass', 'key_iron', 'lock']
    for i, it in enumerate(items):
        t = (i + 0.5) / len(items)
        p = a.lerp(b, t) + Vector((0, R.uniform(-0.3, 0.3), 0.07))
        if it.startswith('key'):
            S.inst(P[it], (p.x - 0.25, p.y, p.z), (0, -ang, R.uniform(-40, 40)), 1.0)
        else:
            S.inst(P[it], (p.x, p.y, p.z), (0, -ang, R.uniform(-25, 25)), 1.0)
    # hopper on the tower
    hop = dj.extrude_xy('hopper', [(-1.2, -1.2), (1.2, -1.2), (1.2, 1.2), (-1.2, 1.2)], 1.8, z=0)
    for v in hop.data.vertices:
        if v.co.z < 0.1:
            v.co.x *= 0.45
            v.co.y *= 0.45
    dj.xform(hop, loc=(14.2, y, 5.2))
    S.add(hop, 'forge_iron', uv_scale=2.0)
    # feeding bin at the bottom with a pile of keys
    S.inst(P['crate_metal'], (3.6, y, 0), (0, 0, 8), 1.3)
    for k in range(5):
        S.inst(P['key_iron' if k % 2 else 'key_brass'], (3.2 + R.uniform(-0.3, 0.5), y + R.uniform(-0.4, 0.4), 1.13 + 0.03 * k),
               (R.uniform(-8, 8), R.uniform(-8, 8), R.uniform(0, 360)), 0.8)


def right_tower():
    """Iron scaffold tower with a riveted tank (right midground)."""
    x0, y0 = 13.2, 7.8
    W, D, Ht = 3.6, 3.4, 12.5
    for dx in (0, W):
        for dy in (0, D):
            p = pt.ibeam('tpost', (x0 + dx, y0 + dy, 0), (x0 + dx, y0 + dy, Ht), 0.35, 0.3, 0.05, up=(1, 0, 0))
            S.add(p, 'forge_iron', uv_scale=2.0)
    for z in (4.0, 7.8):
        pl = dj.box('tplat', W + 0.6, D + 0.6, 0.15, loc=(x0 + W / 2, y0 + D / 2, z))
        S.add(pl, 'forge_iron', uv_scale=2.0)
        r = pt.railing('trail', [(x0 - 0.3, y0 - 0.3, z + 0.15), (x0 + W + 0.3, y0 - 0.3, z + 0.15), (x0 + W + 0.3, y0 + D + 0.3, z + 0.15)], h=1.0, post=1.2)
        S.add(r, 'forge_iron', uv_scale=1.5)
    for z0, z1 in ((0.3, 3.8), (4.2, 7.6)):
        for (pa, pb) in (((x0, y0), (x0 + W, y0)), ((x0 + W, y0), (x0 + W, y0 + D))):
            xb = pt.bar('txb', (pa[0], pa[1], z0), (pb[0], pb[1], z1), 0.1, 0.1)
            S.add(xb, 'forge_iron', uv_scale=1.5)
            xb = pt.bar('txb', (pb[0], pb[1], z0), (pa[0], pa[1], z1), 0.1, 0.1)
            S.add(xb, 'forge_iron', uv_scale=1.5)
    tank = dj.cyl('tank', 2.0, 4.0, 24, loc=(x0 + W / 2, y0 + D / 2, Ht - 0.2))
    sk.subdivide_long(tank, 1.5)
    S.add(tank, 'forge_iron', uv_scale=2.0)
    cap = dj.lathe('tankcap', [(2.05, 0), (1.6, 0.6), (0.6, 1.0), (0, 1.05)], 24, loc=(x0 + W / 2, y0 + D / 2, Ht + 3.8))
    S.add(cap, 'forge_iron', uv_scale=2.0)
    for z in (Ht + 0.4, Ht + 1.8, Ht + 3.2):
        bd = dj.cyl('tband', 2.06, 0.18, 24, loc=(x0 + W / 2, y0 + D / 2, z))
        S.pal(bd, 'iron_dark')
    pp = dj.tube('tpipe', [(x0 + 0.5, y0 + D / 2, Ht - 0.2), (x0 - 1.0, y0 + D / 2, Ht - 1.5), (x0 - 1.0, y0 + 1.0, 0.0)], 0.22, 10)
    S.add(pp, 'forge_iron', uv_scale=2.0)
    # a lantern on the tower
    S.inst(P['torch'], (x0 - 0.2, y0, 5.6), (0, 0, 180), 2.0)
    fl = pt.blob_cluster('tflame', (x0 - 0.2, y0 - 0.45, 6.75), 0.12, 3, seed=8, squash=1.6)
    S.add(fl, 'forge_flicker', key='flame', shadow=False)


def left_hall():
    """Brick foundry hall on the left, arched windows glowing, a NO DAYS OFF sign, a roof stack."""
    x0, x1, y0, y1, Ht = -40.0, -12.0, 19.0, 34.0, 14.0
    hall = dj.box('hall', x1 - x0, y1 - y0, Ht, loc=((x0 + x1) / 2, (y0 + y1) / 2, 0))
    wins = []
    for cx in (-16.5, -23.0, -29.5, -36.0):
        wins.append((cx, pt.arch_outline(cx, 3.2, 8.0, 14, bottom=2.6)))
    for cx, outline in wins:
        cut = pt.cutter_xz('wcut', outline, y0 - 0.5, y0 + 0.6)
        pt.boolean(hall, cut)
    door_cut = pt.cutter_xz('dcut', [(-20.6, -0.1), (-18.0, -0.1), (-18.0, 4.2), (-20.6, 4.2)], y0 - 0.5, y0 + 0.6)
    sk.subdivide_long(hall, 3.0)
    S.add(hall, 'forge_brick')
    for cx, outline in wins:
        pane = dj.extrude_xz('pane', outline, 0.1, y=y0 + 0.55)
        S.glow(pane, 'window')
        # mullions
        for k in (-0.8, 0.0, 0.8):
            m = dj.box('mull', 0.12, 0.14, 8.0 + 1.6 - 2.6, loc=(cx + k, y0 + 0.45, 2.6))
            S.pal(m, 'iron_dark')
        for z in (4.4, 6.2, 8.0):
            m = dj.box('mullh', 3.2, 0.14, 0.12, loc=(cx, y0 + 0.45, z))
            S.pal(m, 'iron_dark')
        sill = dj.box('sill', 3.8, 0.6, 0.25, loc=(cx, y0 - 0.1, 2.4))
        S.add(sill, 'forge_iron', uv_scale=2.0)
    # roof (iron sheet) and a stack
    roof = dj.extrude_xz('roof', [(-1, 0), (1, 0), (0, 0.45)], 1.0, y=0)
    dj.xform(roof, scale=(9.5, x1 - x0 + 1.0, 9.0))
    dj.xform(roof, rot=(0, 0, 90))
    dj.xform(roof, loc=((x0 + x1) / 2, (y0 + y1) / 2, Ht))
    S.add(roof, 'forge_iron', uv_scale=3.0)
    st = dj.cyl('hstack', 1.3, 18, 16, r2=1.1, loc=(-25.0, 27.0, Ht + 2))
    S.add(st, 'forge_brick', shadow=False)
    tip = dj.cyl('hstip', 1.15, 0.3, 16, loc=(-25.0, 27.0, Ht + 20))
    S.glow(tip, 'ember')
    # sign on the hall
    S.inst(P['sign_days'], (-23.0, y0 - 0.15, 10.3), (0, 0, 0), 1.0)
    # wall lanterns
    for x in (-19.8, -26.2):
        S.inst(P['torch'], (x, y0 - 0.15, 5.0), (0, 0, 180), 1.8)
        fl = pt.blob_cluster('hflame', (x, y0 - 0.55, 6.05), 0.11, 3, seed=int(-x), squash=1.6)
        S.add(fl, 'forge_flicker', key='flame', shadow=False)


def back_right():
    """Lock-assembly shed with a sawtooth roof and a big blast stack (right background)."""
    x0, x1, y0, y1 = 18.0, 42.0, 22.0, 34.0
    shed = dj.box('shed', x1 - x0, y1 - y0, 9.0, loc=((x0 + x1) / 2, (y0 + y1) / 2, 0))
    sk.subdivide_long(shed, 3.0)
    S.add(shed, 'forge_brick')
    for i in range(6):
        cx = x0 + 2 + i * 4
        tooth = dj.extrude_xz('saw', [(cx - 2, 9.0), (cx + 2, 9.0), (cx + 2, 12.0)], y1 - y0, y=(y0 + y1) / 2)
        S.add(tooth, 'forge_iron', uv_scale=3.0)
        gl = dj.box('sawglass', 0.1, y1 - y0 - 0.4, 2.6, loc=(cx + 1.93, (y0 + y1) / 2, 9.2))
        S.glow(gl, 'window_dim')
    for i in range(5):
        w = dj.box('shedwin', 2.4, 0.12, 2.2, loc=(x0 + 3 + i * 4.6, y0 - 0.02, 3.0))
        S.glow(w, 'window_dim')
        for k in (-0.6, 0.6):
            m = dj.box('swm', 0.1, 0.16, 2.2, loc=(x0 + 3 + i * 4.6 + k, y0 - 0.06, 3.0))
            S.pal(m, 'iron_dark')
    # blast stack
    bs = dj.lathe('blast', [(5.0, 0), (5.2, 2), (4.6, 12), (3.4, 24), (3.0, 34), (3.0, 36)], 28, loc=(30.0, 46.0, 0))
    sk.subdivide_long(bs, 3.0)
    S.add(bs, 'forge_iron', shadow=False, uv_scale=3.0)
    for z, r in ((6, 5.15), (14, 4.55), (22, 3.65)):
        b = dj.cyl('bsband', r, 0.5, 28, loc=(30.0, 46.0, z))
        S.pal(b, 'iron_dark')
    tuy = dj.cyl('tuyere', 5.25, 0.6, 28, loc=(30.0, 46.0, 3.0))
    S.glow(tuy, 'ember')
    tip = dj.cyl('bstip', 2.9, 0.4, 24, loc=(30.0, 46.0, 36.0))
    S.glow(tip, 'fire')


def yard_props():
    """Props on the foundry floor (outside the flat fighting zone) and framing pieces."""
    # foreground framing (left: anvil on a log with tools; right: coal barrow and crates)
    S.inst(P['anvil_log'], (-12.6, 2.3, 0), (0, 0, 20), 1.7)
    S.inst(P['tongs'], (-12.4, 2.1, 1.82), (0, 0, 25), 1.0)
    S.inst(P['bucket'], (-11.0, 2.4, 0), (0, 0, 40), 1.3)
    S.inst(P['crate_metal'], (12.8, 2.5, 0), (0, 0, -12), 1.35)
    S.inst(P['crate_wood'], (14.1, 2.2, 0), (0, 0, 20), 1.2)
    for k in range(4):
        S.inst(P['key_brass' if k % 2 else 'key_iron'], (12.6 + R.uniform(-0.3, 0.3), 2.4 + R.uniform(-0.3, 0.3), 1.17 + 0.02 * k),
               (R.uniform(-6, 6), R.uniform(-6, 6), R.uniform(0, 360)), 0.8)
    S.inst(P['chain_coil'], (11.4, 2.0, 0), (0, 0, 30), 1.4)
    # behind the channel: work area
    S.inst(P['anvil'], (-3.8, 7.5, 0.0), (0, 0, 8), 2.0)
    stump = dj.cyl('stump', 0.55, 0.55, 14, loc=(-3.8, 7.5, 0))
    S.pal(stump, 'wood')
    # anvil on stump: lift the anvil
    S.inst(P['sledge'], (-2.9, 7.0, 0.05), (0, 90, 30), 1.0)
    S.inst(P['barrel'], (-1.8, 8.4, 0), (0, 0, 10), 1.3)
    water = dj.cyl('quench', 0.4, 0.02, 16, loc=(-1.8, 8.4, 1.05))
    S.pal(water, 'glass_dark')
    S.inst(P['punchclock'], (-9.0, 6.4, 0), (0, 0, 8), 1.3)
    S.inst(P['sign_quota'], (-6.6, 6.6, 1.7), (0, 0, 4), 0.9)
    post = dj.box('qpost', 0.16, 0.16, 1.75, loc=(-6.6, 6.66, 0))
    S.pal(post, 'wood')
    S.inst(P['workbench'], (8.5, 6.8, 0), (0, 0, -6), 1.3)
    for k in range(3):
        S.inst(P['lock'], (7.9 + 0.5 * k, 6.7, 1.16), (0, 0, R.uniform(-30, 30)), 0.8)
    S.inst(P['whetstone'], (11.0, 7.4, 0), (0, 0, -30), 1.3)
    S.inst(P['crate_metal'], (-12.0, 9.5, 0), (0, 0, 14), 1.4)
    S.inst(P['crate_metal'], (-11.2, 10.8, 0), (0, 0, -8), 1.2)
    S.inst(P['crate_wood'], (-11.8, 10.2, 1.2), (0, 0, 30), 1.1)
    S.inst(P['cauldron'], (2.8, 17.0, 0), (0, 0, 0), 1.8)
    coal = pt.blob_cluster('coal', (2.8, 17.0, 1.25), 0.45, 7, seed=4, squash=0.4)
    S.glow(coal, 'ember')
    S.inst(P['chain_coil'], (-5.8, 17.5, 0), (0, 0, -10), 1.6)
    S.inst(P['barrel'], (6.5, 21.0, 0), (0, 0, 0), 1.4)
    S.inst(P['barrel'], (7.5, 21.6, 0), (0, 0, 40), 1.4)
    S.inst(P['pickaxe'], (-14.5, 7.5, 0.6), (0, 20, 70), 1.4)
    # slag carts on the track
    for x in (-9.0, 14.0):
        cart = dj.extrude_xy('cart', [(-1.2, -0.8), (1.2, -0.8), (1.2, 0.8), (-1.2, 0.8)], 1.1, z=0.45)
        for v in cart.data.vertices:
            if v.co.z < 0.6:
                v.co.x *= 0.75
                v.co.y *= 0.75
        dj.xform(cart, loc=(x, 24, 0))
        S.add(cart, 'forge_iron', uv_scale=2.0)
        for dx in (-0.7, 0.7):
            for dy in (-0.6, 0.6):
                wh = dj.cyl('cartwheel', 0.32, 0.12, 12, loc=(x + dx, 24 + dy, 0.32), rot=(90, 0, 0))
                S.pal(wh, 'iron_dark')
        slag = pt.blob_cluster('slag', (x, 24, 1.5), 0.5, 6, seed=int(x + 20), squash=0.45)
        S.glow(slag, 'dim')


def background():
    """Volcanic plain, lava rivers, distant stacks with smoke, the volcano."""
    def hfn(x, y):
        h = 0.0
        d = y - 40
        h += max(0.0, d) * 0.02 * (math.sin(x * 0.05) + 1.3)
        h += 3.5 * (sk_noise(x * 0.03, y * 0.03) - 0.4) * min(1.0, max(0.0, (y - 45) / 30))
        side = max(0.0, abs(x) - 45) * 0.25
        return h + side
    ter = pt.terrain('ground_far', -170, 170, 37, 160, 42, 24, hfn)
    S.add(ter, 'forge_rock', shadow=False, uv_scale=9.0)
    # ridges of basalt (midground-far silhouettes)
    for i, (x, y, w, h) in enumerate(((-60, 75, 40, 14), (-25, 92, 30, 10), (45, 80, 45, 16), (85, 100, 50, 22), (-95, 105, 50, 20))):
        rg = pt.blob_cluster('ridge', (x, y, h * 0.2), w * 0.28, 9, seed=60 + i, subdiv=2, squash=0.55, spread=1.4)
        for v in rg.data.vertices:
            if v.co.z < 0:
                v.co.z = -0.5
        S.add(rg, 'forge_rock', shadow=False, uv_scale=10.0)
    # volcano: broad cone with a glowing crater and lava rivers
    vx, vy, vr, vh = -48.0, 138.0, 52.0, 30.0
    def vfn(x, y):
        r = math.hypot(x - vx, y - vy)
        cone = max(0.0, 1 - r / vr) ** 1.25 * vh
        crater = max(0.0, 1 - r / 8.0) ** 2 * 6.0
        return cone - crater + 2.0 * sk_noise(x * 0.06, y * 0.06)
    vol = pt.terrain('volcano', vx - vr, vx + vr, vy - vr * 0.8, vy + vr * 0.6, 40, 30, vfn)
    S.add(vol, 'forge_rock', shadow=False, uv_scale=12.0)
    cr = dj.cyl('crater_glow', 6.5, 0.3, 24, loc=(vx, vy, vfn(vx, vy) + 1.2))
    S.glow(cr, 'crater')
    # lava rivers down the flank facing the camera, then across the plain
    for k, (ang, ln) in enumerate(((-100, 1.0), (-70, 0.85), (-125, 0.7))):
        pts_ = []
        a = math.radians(ang)
        for i in range(14):
            t = i / 13
            r = 7.0 + t * vr * ln
            x = vx + r * math.cos(a) + math.sin(t * 7 + k) * 2.5
            y = vy + r * math.sin(a)
            pts_.append((x, y, vfn(x, y) + 0.35))
        rv = dj.tube('lavariver', pts_, 1.2 - 0.3 * k, 6)
        dj.xform(rv, scale=(1, 1, 0.25), pivot=(0, 0, 0))
        S.glow(rv, 'lava_far')
    # a lava river winding across the plain toward the foundry (between ridges)
    pts_ = []
    for i in range(30):
        t = i / 29
        y = 125 - t * 70
        x = -40 + t * 32 + math.sin(t * 8) * 9
        pts_.append((x, y, hfn(x, y) + 0.25))
    rv = dj.tube('plainriver', pts_, 2.2, 6)
    for v in rv.data.vertices:
        v.co.z = hfn(v.co.x, v.co.y) + 0.15
    S.add(rv, 'forge_lava', shadow=False, uv_scale=6.0)
    # second, smaller volcano far right
    vx2, vy2 = 75.0, 150.0
    def vfn2(x, y):
        r = math.hypot(x - vx2, y - vy2)
        return max(0.0, 1 - r / 38.0) ** 1.3 * 22 - max(0.0, 1 - r / 5) ** 2 * 4
    v2 = pt.terrain('volcano2', vx2 - 38, vx2 + 38, vy2 - 30, vy2 + 10, 24, 14, vfn2)
    S.add(v2, 'forge_rock', shadow=False, uv_scale=12.0)
    cr2 = dj.cyl('crater2', 4.5, 0.3, 20, loc=(vx2, vy2, 18.5))
    S.glow(cr2, 'lava_far')
    # distant smoke stacks with glowing tips
    for i, (x, y, h, r) in enumerate(((-34, 70, 40, 2.2), (-14, 92, 52, 2.6), (24, 76, 44, 2.4), (55, 96, 38, 2.2), (-70, 88, 30, 2.0))):
        st = dj.cyl('farstack', r, h, 14, r2=r * 0.8, loc=(x, y, -1))
        S.pal(st, 'brick_far', shadow=False)
        for z in np.arange(6, h, 8):
            bd = dj.cyl('fsband', r * (1 - 0.2 * z / h) + 0.12, 0.6, 14, loc=(x, y, z))
            S.pal(bd, 'iron_dark', shadow=False)
        tip = dj.cyl('fstip', r * 0.82, 0.5, 14, loc=(x, y, h - 1.2))
        S.glow(tip, 'fire')
        smoke(f'stsmoke{i}', (x, y, h), 1.0 + 0.1 * i, seed=70 + i)
    # smoke from the furnace chimneys and the hall stack
    for i, (x, y, z) in enumerate(((-9, 49, 64), (9, 49, 64), (-25, 27, 34.5))):
        smoke(f'fsmoke{i}', (x, y, z), 1.3 if i < 2 else 0.8, seed=90 + i)


def smoke(name, base, scale, seed):
    """Stylised rising smoke column: lumpy blobs drifting to +x, lit warm from below (vertex tint)."""
    r = random.Random(seed)
    parts = []
    p = Vector(base)
    for i in range(9):
        rad = scale * (1.6 + i * 0.9) * r.uniform(0.85, 1.1)
        p = p + Vector((scale * (1.0 + i * 0.6) * r.uniform(0.6, 1.2), r.uniform(-0.6, 0.6) * scale, rad * 0.9))
        parts.append(pt.blob_cluster(f'{name}_{i}', tuple(p), rad, 4, seed=seed * 10 + i, subdiv=2, squash=0.8, spread=0.7))
    ob = dj.join(parts, name)
    ob['smoke'] = list(base)
    S.pal(ob, 'smoke', shadow=False)
    return ob


_NOISE_SEED = Vector((3.1, 7.7, 1.3))


def sk_noise(x, y):
    from mathutils import noise
    return 0.5 + 0.5 * noise.noise(Vector((x, y, 0.0)) + _NOISE_SEED)


# ============================================================================ tints (vertex colour)
def tint(grp, P, Nrm, ob):
    """Soot, heat and smoke shading baked into vertex colours (multiplied with AO)."""
    out = np.ones((len(P), 3), np.float32)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if 'smoke' in ob:
        b = np.array(ob['smoke'], np.float32)
        h = np.clip((z - b[2]) / 40.0, 0, 1)
        # warm underside (lit by the glow below), cool purple-grey top
        warm = np.array([1.0, 0.62, 0.45], np.float32)
        cool = np.array([0.32, 0.28, 0.36], np.float32)
        t = np.clip(h * 1.4 + (Nrm[:, 2] * 0.3), 0, 1)[:, None]
        out *= warm * (1 - t) + cool * t
        out *= (0.55 + 0.45 * np.clip(-Nrm[:, 2] * 0.5 + 0.6, 0, 1))[:, None]
        return out
    if grp in ('forge_floor', 'forge_iron', 'forge_brick', 'forge_rock'):
        # heat tint near the channel and the furnace mouth (warmer albedo)
        dch = np.abs(y - 4.0)
        heat = np.clip(1 - dch / 2.2, 0, 1) * (z < 0.6)
        dm = np.sqrt((x / 9.0) ** 2 + ((y - 38.0) / 5.0) ** 2)
        heat = np.maximum(heat, np.clip(1 - dm, 0, 1) * 0.8)
        out *= (1 - heat[:, None] * np.array([0.0, 0.25, 0.45], np.float32))
        # soot creeping up tall structures
        soot = np.clip((z - 8) / 25.0, 0, 1) * 0.55
        out *= (1 - soot)[:, None]
        # floor variation: ash and wear patches (big, soft)
        if grp == 'forge_floor':
            n = np.array([sk_noise(a * 0.18, b * 0.18) for a, b in zip(x, y)], np.float32)
            out *= (0.82 + 0.3 * n)[:, None]
            # the fighting area is a touch lighter (worn by work)
            wear = np.clip(1 - (np.abs(x) / 11.0) ** 2, 0, 1) * np.clip(1 - np.abs(y + 1.0) / 6.0, 0, 1)
            out *= (1 + 0.12 * wear)[:, None].clip(0, 1.12)
    if grp == 'forge_rock':
        far = np.clip((y - 40) / 100, 0, 1)
        out *= (1 - 0.25 * far)[:, None]
    return np.clip(out, 0, 1)


# ============================================================================ main
if __name__ == '__main__':
    build_materials()
    P = build_protos()
    S.bake_props('forge_props', size=2048, samples=40, ao_dist=0.4)
    floor_and_channel()
    furnace()
    crane_and_pour()
    conveyor()
    right_tower()
    left_hall()
    back_right()
    yard_props()
    background()
    S.tint_fn = tint
    S.finalize(ao_dist=2.0, ao_samples=64)
    if '--no-preview' not in sk.args():
        import preview
        preview.render('forge', extra=True)
