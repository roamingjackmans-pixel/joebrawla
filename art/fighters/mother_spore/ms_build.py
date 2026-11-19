"""Mother Spore (JoeBrawla fighter) -- full build: body, outfit, weights, bakes, GLB.

  blender -b --factory-startup --python ms_build.py -- [--look]
  --look   quick look: no bakes, procedural materials, EEVEE renders to art/_work/mother_spore/look_*.jpg
Output: art/_work/mother_spore/mother_spore_src.glb, mother_spore.blend, tex/*.png, build_report.json
"""
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import numpy as np
from mathutils import Vector, Matrix
import fblib as F
import ms_geo as G
import ms_mats as M

V = Vector
ID = 'mother_spore'
WORK = os.path.join(F.JB, 'art', '_work', ID)
TEX = os.path.join(WORK, 'tex')
os.makedirs(TEX, exist_ok=True)
A = F.args()
LOOK = '--look' in A

SCALE = 1.06          # UBC female 1.767 m -> 1.873 m body; the cap brings her to 2.0 m
HEAD_K = 1.08
HAND_K = 1.08
FINGERS = 1.28        # long fingers
CAP_TINT = '#9b3420'  # rust red (tint1 default)
DRESS_TINT = '#64405f'  # dusky plum-mauve (tint2 default)

ARMS = {'lowerarm_l', 'lowerarm_r', 'hand_l', 'hand_r'} | {f'{f}_{i:02d}_{s}' for f in F.FINGERS for i in (1, 2, 3)
                                                           for s in 'lr'}
LEGS = {'pelvis', 'spine_01', 'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r'}


def staff_grip(body):
    """Fist centre and grip axis in the hand_r rest frame, measured on the Sword_Idle clip's closed hand."""
    src, act = F.load_clip_source('Sword_Idle')
    F.pose_from(src, [body.arm], 12)
    pb = body.arm.pose.bones
    Mh = body.arm.matrix_world @ pb['hand_r'].matrix
    pts = []
    for f in ('index', 'middle', 'ring', 'pinky'):
        for i in (1, 2, 3):
            pts.append(pb[f'{f}_{i:02d}_r'].head)
        pts.append(pb[f'{f}_03_r'].tail)
    g = sum((body.arm.matrix_world @ p for p in pts), V()) / len(pts)
    palm = body.arm.matrix_world @ pb['hand_r'].head
    g = g.lerp(palm, 0.12)
    a = (pb['index_01_r'].head - pb['pinky_01_r'].head).normalized()
    g_loc = Mh.inverted() @ g
    a_loc = (Mh.to_3x3().inverted() @ a).normalized()
    F.rest_pose(body.arm)
    F.delete([src])
    for ac in list(bpy.data.actions):
        bpy.data.actions.remove(ac)
    Mr = body.arm.matrix_world @ body.arm.data.bones['hand_r'].matrix_local
    gw = Mr @ g_loc
    aw = (Mr.to_3x3() @ a_loc).normalized()
    F.log('grip', tuple(round(x, 3) for x in gw), 'axis', tuple(round(x, 3) for x in aw))
    return gw, aw


def add_bone(arm, name, parent, head, tail):
    F.activate(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones.new(name)
    eb.head, eb.tail = V(head), V(tail)
    eb.parent = arm.data.edit_bones[parent]
    eb.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')


def skirt_weights(sp, body_ws):
    zk = 0.0

    def fn(c):
        top = body_ws.at(c)
        x, z = c.x, c.z
        lw = F.sstep(-0.09, 0.09, x)
        calf = 0.45 * F.sstep(0.62, 0.36, z)
        leg = {'thigh_l': lw * (1 - calf), 'thigh_r': (1 - lw) * (1 - calf), 'calf_l': lw * calf, 'calf_r': (1 - lw) * calf}
        pel = 0.55 * F.sstep(0.70, sp.z_hip, z)
        legw = F.blend(leg, 1 - pel, {'pelvis': 1.0}, pel)
        k = F.sstep(sp.z_hip - 0.02, sp.z_top - 0.02, z)          # waist: follow the body itself
        return F.blend(legw, 1 - k, top, k)
    return fn


def hair_weights(L):
    zh, zn, zs = L['Head'].z + 0.04, L['neck_01'].z, L['spine_03'].z + 0.05

    def fn(c):
        z = c.z
        a = F.sstep(zh - 0.03, zh + 0.05, z)
        b = F.sstep(zs, zn, z)
        return F.blend({'Head': 1.0}, a, F.blend({'neck_01': 1.0}, b, {'spine_03': 1.0}, 1 - b), 1 - a)
    return fn


def covered_faces(body, cloth_bvh, keep_bones):
    me = body.mesh.data
    dom = body.dominant()
    cov = []
    for v in me.vertices:
        if dom[v.index] in keep_bones:
            cov.append(False)
            continue
        n = v.normal
        hit = cloth_bvh.ray_cast(v.co + n * 0.001, n, 0.09)
        ok = hit[0] is not None
        if ok:   # also need cover slightly off-normal (silhouette edges)
            for d in (V((0, 0, 1)), V((0, 0, -1))):
                nd = (n + d * 0.35).normalized()
                if cloth_bvh.ray_cast(v.co + nd * 0.001, nd, 0.12)[0] is None:
                    ok = False
                    break
        cov.append(ok)
    return cov


def main():
    F.reset()
    bpy.context.scene.render.fps = 30
    body = F.Body(F.FEMALE)
    body.scale_all(SCALE)
    body.bigger_head(HEAD_K)
    body.bigger_hands(HAND_K, FINGERS)
    L = body.landmarks()
    arm = body.arm
    tips = [body.t(f'{f}_04_leaf_{s}') for f in F.FINGERS for s in 'lr']
    grip, gaxis = staff_grip(body)

    head_bvh = body.bvh(lambda d, c: d in ('Head', 'neck_01'))
    torso_bvh = body.bvh(lambda d, c: d not in ARMS and not (d.startswith('upperarm') and abs(c.x) > 0.24))
    legs_bvh = body.bvh(lambda d, c: d in LEGS)

    # ---------------------------------------------------------------- cap
    cf = G.CapFrame(L, tilt_deg=-18.0, R=0.43, top=2.0)
    hole = G.cap_hole(head_bvh, cf)
    cap_top, cap_under, cap_band = G.build_cap(cf, hole)
    warts = G.build_warts(cf)
    # ---------------------------------------------------------------- dress
    bodice = G.build_bodice(body, L)
    sp = G.SkirtSpec(L)
    collar = G.build_collar(F.bvh_objs([body.mesh, bodice]), L, bodice)
    skirt_bvh = F.bvh_objs([bodice])
    dom = body.dominant()
    sk_src = F.BVHTree.FromPolygons(
        [v.co for v in body.mesh.data.vertices] + [v.co for v in bodice.data.vertices],
        [list(p.vertices) for p in body.mesh.data.polygons if all(dom[i] in LEGS for i in p.vertices)] +
        [[len(body.mesh.data.vertices) + i for i in p.vertices] for p in bodice.data.polygons])
    skirt, prof = G.build_skirt(sk_src, sp)
    tiers = [G.build_tier(sp, prof, za, h, fl, math.radians(p0), lob, i, 'ms_tier%d' % i)
             for i, (za, h, fl, p0, lob) in enumerate([(1.085, 0.13, 0.045, 0, 12), (0.905, 0.15, 0.060, 0, 13),
                                                       (0.715, 0.16, 0.070, 22, 13), (0.525, 0.16, 0.080, 30, 14)])]
    roots = G.build_roots(sp, prof)
    sh_bvh = F.bvh_objs([body.mesh, bodice])
    shoulders = G.build_shoulder_shelves(sh_bvh, L)
    hb = F.BVHTree.FromPolygons(
        [v.co for v in body.mesh.data.vertices] + [v.co for v in collar.data.vertices],
        [list(p.vertices) for p in body.mesh.data.polygons
         if all((dom[i] not in ARMS) and not (dom[i].startswith('upperarm')) for i in p.vertices)] +
        [[len(body.mesh.data.vertices) + i for i in p.vertices] for p in collar.data.polygons])
    hair = G.build_hood(hb, L, cf, hole)
    belt, hipcaps = G.build_belt(prof, sp, L)
    cuffs = G.build_cuffs(L, body.bvh(lambda d, c: d.startswith('lowerarm') or d.startswith('hand')))
    # ---------------------------------------------------------------- staff
    staff_parts, staff_top = G.staff_local()
    Rz = gaxis.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    Ms = Matrix.Translation(grip) @ Rz
    for o in staff_parts:
        o.data.transform(Ms)
        o.data.update()
    staff_tip = Ms @ (staff_top + V((0, 0, 0.12)))

    # ---------------------------------------------------------------- weights
    body_ws = F.WeightSource(body.mesh)
    for o in (cap_top, cap_under, cap_band, warts):
        F.weights_rigid(o, 'Head')
    for o in staff_parts:
        F.weights_rigid(o, 'hand_r')
    F.weights_fn(hair, hair_weights(L))
    F.weights_transfer(cuffs, body_ws, smooth_iters=1)
    F.weights_transfer(collar, body_ws, smooth_iters=4)
    F.weights_transfer(shoulders, body_ws, smooth_iters=8, smooth_factor=0.6)
    F.weights_fn(skirt, skirt_weights(sp, body_ws))
    sk_ws = F.WeightSource(skirt)
    for t in tiers:
        F.weights_transfer(t, sk_ws, smooth_iters=2)
    F.weights_transfer(roots, sk_ws, smooth_iters=2)
    F.weights_transfer(belt, sk_ws, smooth_iters=3)
    hipw = sk_ws.at(sum((v.co for v in hipcaps.data.vertices), V()) / len(hipcaps.data.vertices))
    F.write_weights(hipcaps, [hipw] * len(hipcaps.data.vertices))

    # ---------------------------------------------------------------- hide the covered body
    cloth = F.bvh_objs([bodice, skirt, collar] + tiers)
    keep = ARMS | {'Head', 'neck_01', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r'}
    cov = covered_faces(body, cloth, keep)
    me = body.mesh.data
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if all(cov[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    F.log('covered body faces removed', len(kill), 'body tris', F.tri_count(body.mesh))

    # ---------------------------------------------------------------- materials
    base_img = bpy.data.images.load(os.path.join(F.UBC_TEX, 'T_Superhero_Female_Dark_BaseColor.png'))
    nrm_img = bpy.data.images.load(os.path.join(F.UBC_TEX, 'T_Superhero_Female_Normal.png'))
    nrm_img.colorspace_settings.name = 'Non-Color'
    m_skin = M.skin(body, L, base_img, nrm_img, tips)
    eye_fronts = []
    if body.eyes:
        ev = [v.co.copy() for v in body.eyes.data.vertices]
        for sgn in (1, -1):
            side = [p for p in ev if p.x * sgn > 0]
            fp = min(side, key=lambda p: p.y)
            eye_fronts.append((fp, 0.0105))
    mats = dict(top=M.cap_top(), gills=M.gills(), band=M.band(), warts=M.warts(), hair=M.hair(),
                eyes=M.eyes(eye_fronts), brows=M.brows(), stalk=M.stalk(), caps=M.mini_caps(), bulb=M.bulb(),
                wrap=M.wrap(), roots=M.roots(), threads=M.threads(sp.center.y, sp.z_hem), frill=M.frill(),
                collar=M.collar(), bodice=M.bodice(sp.center.y))

    def setm(o, m):
        o.data.materials.clear()
        o.data.materials.append(m)
    body.mesh.data.materials.clear()
    body.mesh.data.materials.append(m_skin)
    for o, k in ((cap_top, 'top'), (cap_under, 'gills'), (cap_band, 'band'), (warts, 'warts'),
                 (roots, 'roots'), (bodice, 'bodice'), (skirt, 'threads'), (collar, 'band'), (belt, 'wrap'), (hipcaps, 'caps'), (cuffs, 'wrap'), (hair, 'threads'),
                 (shoulders, 'frill')):
        setm(o, mats[k])
    for t in tiers:
        setm(t, mats['frill'])
    for o, k in zip(staff_parts, ('stalk', 'caps', 'bulb', 'wrap')):
        setm(o, mats[k])
    if body.eyes:
        setm(body.eyes, mats['eyes'])
    if body.brows:
        setm(body.brows, mats['brows'])

    sockets = {'socket_staff': ('hand_r', staff_tip), 'socket_cap': ('Head', cf.w(V((0, 0, cf.h + 0.02))))}
    for n, (par, p) in sockets.items():
        add_bone(arm, n, par, p, p + V((0, 0, 0.08)))

    if LOOK:
        for k, hx in (('top', CAP_TINT), ('threads', DRESS_TINT), ('frill', DRESS_TINT), ('bodice', DRESS_TINT)):
            preview_tint(mats[k], hx)
        look(body, [cap_top, cap_under, cap_band, warts, hair, roots, bodice, skirt, collar, shoulders, belt, hipcaps, cuffs] + tiers + staff_parts)
        return

    # ---------------------------------------------------------------- bake + assemble
    rep = {}
    k_body = F.Kit('MotherSpore_Body', 2048)
    k_body.add(body.mesh)
    LO_body = k_body.build(TEX, arm, keep_uv=True, ao_dist=0.08, ao_in_color=0.45, emit_strength=5.0)
    LO_body.data.materials[0].name = 'ms_skin'

    k_cap = F.Kit('MotherSpore_Cap', 2048)
    k_cap.add(cap_top, uvw=1.0)
    LO_cap = k_cap.build(TEX, arm, ao_dist=0.12, ao_in_color=0.35, emit=False)
    set_tint(LO_cap, 'tint1_cap', CAP_TINT)

    k_dress = F.Kit('MotherSpore_Dress', 2048)
    for o in [bodice, skirt, shoulders, hair] + tiers:
        k_dress.add(o, uvw=1.0)
    LO_dress = k_dress.build(TEX, arm, ao_dist=0.10, ao_in_color=0.5, emit_strength=5.0, double_sided=True)
    set_tint(LO_dress, 'tint2_dress', DRESS_TINT)

    k_misc = F.Kit('MotherSpore_Misc', 2048)
    for o, w in ((cap_under, 0.8), (cap_band, 1.0), (warts, 1.6), (roots, 1.0), (collar, 1.0), (belt, 1.0), (hipcaps, 2.0), (cuffs, 1.0)):
        k_misc.add(o, uvw=w)
    for o, w in zip(staff_parts, (1.5, 2.0, 1.5, 1.0)):
        k_misc.add(o, uvw=w)
    if body.eyes:
        k_misc.add(body.eyes, uvw=6.0)
    if body.brows:
        k_misc.add(body.brows, uvw=1.0)
    LO_misc = k_misc.build(TEX, arm, ao_dist=0.08, ao_in_color=0.45, emit_strength=6.0, double_sided=True)
    LO_misc.data.materials[0].name = 'ms_misc'

    objs = [LO_body, LO_cap, LO_dress, LO_misc]
    for o in objs:
        F.triangulate(o)
    tris = {o.name: F.tri_count(o) for o in objs}
    F.log('TRIS', tris, 'total', sum(tris.values()))
    out = os.path.join(WORK, ID + '_src.glb')
    F.export_glb(out, [arm] + objs)
    rep.update(dict(tris=tris, total=sum(tris.values()), materials=[o.data.materials[0].name for o in objs],
                    height=max((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices),
                    bones=len(arm.data.bones), extra_bones=list(sockets), scale=SCALE,
                    pelvis_rest_z=body.h('pelvis').z, glb_mb=os.path.getsize(out) / 1e6))
    json.dump(rep, open(os.path.join(WORK, 'build_report.json'), 'w'), indent=1)
    F.save_blend(os.path.join(WORK, ID + '.blend'))


def set_tint(LO, name, hex_target):
    """Make the baked texture's mean the neutral 1.0 and put the default colour in the base colour factor."""
    m = LO.data.materials[0]
    m.name = name
    nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.endswith('_color'))
    a = F.img_np(tex.image)[:, :, :3]
    luma = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    used = luma > 0.02
    mean = float(luma[used].mean()) if used.any() else 0.7
    tgt = F.srgb(hex_target)
    fac = tuple(min(1.0, c / mean) for c in tgt[:3]) + (1.0,)
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mx.inputs[6])
    mx.inputs[7].default_value = fac
    nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    F.log('tint', name, 'texture mean', round(mean, 3), 'factor', tuple(round(x, 3) for x in fac))


def preview_tint(m, hx, mean=0.68):
    nt = m.node_tree
    p = nt.nodes['BSDF']
    src = p.inputs['Base Color'].links[0].from_socket
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    nt.links.new(src, mx.inputs[6])
    mx.inputs[7].default_value = tuple(min(1, c / mean) for c in F.srgb(hx)[:3]) + (1,)
    nt.links.new(mx.outputs[2], p.inputs['Base Color'])


def look(body, parts):
    import fbview as FV
    show = [body.mesh, body.eyes, body.brows] + parts
    show = [o for o in show if o]
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o not in show:
            o.hide_render = True
    cam, g = FV.studio(900, samples=32)
    for v in A[A.index('--look') + 1:] or ['front', 'side', 'threeq', 'face']:
        if v == 'face':
            FV.frame(cam, show, (-20, -4), focus=(body.L['head_c'] + V((0, -0.03, -0.01)), 0.17), lens=85, pad=1.0)
        else:
            FV.frame(cam, show, v)
        FV.render(os.path.join(WORK, 'look_%s.jpg' % v))


if __name__ == '__main__':
    main()
