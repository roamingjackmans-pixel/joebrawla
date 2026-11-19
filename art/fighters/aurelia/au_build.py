"""Saint Aurelia the Unthawed (JoeBrawla fighter) -- full build: body, robes, weights, bakes, GLB.

  blender -b --factory-startup --python au_build.py -- [--look [views..]]
Output: art/_work/aurelia/aurelia_src.glb, aurelia.blend, tex/*.png, build_report.json
"""
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import fblib as F
import au_geo as G
import au_mats as M

V = Vector
ID = 'aurelia'
WORK = os.path.join(F.JB, 'art', '_work', ID)
TEX = os.path.join(WORK, 'tex')
os.makedirs(TEX, exist_ok=True)
A = F.args()
LOOK = '--look' in A

SCALE = 1.035         # UBC female 1.767 m -> 1.85 m with the bigger head
HEAD_K = 1.08
HAND_K = 1.08
FINGERS = 1.06
ROBE_TINT = '#ece5d8'   # warm liturgical white (tint1 default)
GOLD_TINT = '#c99f45'   # gold (tint2 default)
HAIR = F.UBC + r"\Hairstyles\Rigged to Head Bone\glTF (Godot -Unreal)\Hair_Long.gltf"

ARMS = {'lowerarm_l', 'lowerarm_r', 'hand_l', 'hand_r'} | {f'{f}_{i:02d}_{s}' for f in F.FINGERS for i in (1, 2, 3)
                                                           for s in 'lr'}
LEGS = {'pelvis', 'spine_01', 'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r'}
TORSO = {'pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r', 'neck_01', 'upperarm_l',
         'upperarm_r', 'thigh_l', 'thigh_r'}


def staff_grip(body):
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
    g = g.lerp(body.arm.matrix_world @ pb['hand_r'].head, 0.12)
    a = (pb['index_01_r'].head - pb['pinky_01_r'].head).normalized()
    g_loc = Mh.inverted() @ g
    a_loc = (Mh.to_3x3().inverted() @ a).normalized()
    F.rest_pose(body.arm)
    F.delete([src])
    for ac in list(bpy.data.actions):
        bpy.data.actions.remove(ac)
    Mr = body.arm.matrix_world @ body.arm.data.bones['hand_r'].matrix_local
    return Mr @ g_loc, (Mr.to_3x3() @ a_loc).normalized()


def add_bone(arm, name, parent, head, tail):
    F.activate(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones.new(name)
    eb.head, eb.tail = V(head), V(tail)
    eb.parent = arm.data.edit_bones[parent]
    eb.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')


def adopt_hair(body):
    objs = F.import_gltf(HAIR)
    hair = next(o for o in objs if o.type == 'MESH')
    mw = hair.matrix_world.copy()
    hair.parent = body.arm
    hair.matrix_world = mw
    for md in hair.modifiers:
        if md.type == 'ARMATURE':
            md.object = body.arm
    for o in objs:
        if o.type == 'ARMATURE':
            bpy.data.objects.remove(o, do_unlink=True)
    # bake the object transform into the mesh so world == local like the body
    if hair.matrix_world != Matrix.Identity(4):
        hair.data.transform(hair.matrix_world)
        hair.matrix_parent_inverse = Matrix.Identity(4)
        hair.matrix_world = Matrix.Identity(4)
    uvl = hair.data.uv_layers
    while len(uvl) > 1:
        uvl.remove(uvl[-1])
    body.meshes.append(hair)
    return hair


def drop_lashes(brows, eye_z):
    bm = bmesh.new()
    bm.from_mesh(brows.data)
    seen, kill = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        isl, st = [], [v]
        seen.add(v.index)
        while st:
            x = st.pop()
            isl.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    st.append(o)
        if sum(p.co.z for p in isl) / len(isl) < eye_z + 0.010:
            kill += isl
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(brows.data)
    bm.free()


def leg_split_fn(z_hip, z_top, src_ws, calf_max=0.55, z_knee=0.58, pel=0.5):
    def fn(c):
        top = src_ws.at(c)
        lw = F.sstep(-0.09, 0.09, c.x)
        calf = calf_max * F.sstep(z_knee + 0.06, z_knee - 0.30, c.z)
        leg = {'thigh_l': lw * (1 - calf), 'thigh_r': (1 - lw) * (1 - calf), 'calf_l': lw * calf, 'calf_r': (1 - lw) * calf}
        p = pel * F.sstep(0.72, z_hip, c.z)
        legw = F.blend(leg, 1 - p, {'pelvis': 1.0}, p)
        k = F.sstep(z_hip - 0.02, z_top - 0.02, c.z)
        return F.blend(legw, 1 - k, top, k)
    return fn


def grad_weights(L):
    zh, zn, zs = L['Head'].z + 0.04, L['neck_01'].z, L['spine_03'].z + 0.05

    def fn(c):
        a = F.sstep(zh - 0.03, zh + 0.05, c.z)
        b = F.sstep(zs, zn, c.z)
        return F.blend({'Head': 1.0}, a, F.blend({'neck_01': 1.0}, b, {'spine_03': 1.0}, 1 - b), 1 - a)
    return fn


def covered(body, cloth_bvh, keep_bones):
    me = body.mesh.data
    dom = body.dominant()
    cov = []
    for v in me.vertices:
        if dom[v.index] in keep_bones:
            cov.append(False)
            continue
        n = v.normal
        ok = cloth_bvh.ray_cast(v.co + n * 0.001, n, 0.10)[0] is not None
        if ok:
            for d in (V((0, 0, 1)), V((0, 0, -1)), V((1, 0, 0)), V((-1, 0, 0))):
                nd = (n + d * 0.35).normalized()
                if cloth_bvh.ray_cast(v.co + nd * 0.001, nd, 0.14)[0] is None:
                    ok = False
                    break
        cov.append(ok)
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


def set_tint(LO, name, hex_target):
    m = LO.data.materials[0]
    m.name = name
    nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.endswith('_color'))
    a = F.img_np(tex.image)[:, :, :3]
    luma = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    used = luma > 0.02
    mean = float(luma[used].mean()) if used.any() else 0.7
    fac = tuple(min(1.0, c / mean) for c in F.srgb(hex_target)[:3]) + (1.0,)
    p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.blend_type = 'MULTIPLY'
    mx.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mx.inputs[6])
    mx.inputs[7].default_value = fac
    nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    F.log('tint', name, 'texture mean', round(mean, 3), 'factor', tuple(round(x, 3) for x in fac))


def preview_tint(m, hx, mean=0.80):
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


def main():
    F.reset()
    bpy.context.scene.render.fps = 30
    body = F.Body(F.FEMALE)
    hair = adopt_hair(body)
    body.scale_all(SCALE)
    body.bigger_head(HEAD_K)
    body.bigger_hands(HAND_K, FINGERS)
    L = body.landmarks()
    arm = body.arm
    tips = [body.t(f'{f}_04_leaf_{s}') for f in F.FINGERS for s in 'lr']
    grip, gaxis = staff_grip(body)
    if body.brows:
        drop_lashes(body.brows, L['eye_l'].z)
    dom = body.dominant()

    # ---------------------------------------------------------------- robes
    za = L['upperarm_l'].z
    wx = abs(L['hand_l'].x) - 0.035
    shell = G.build_shell(body, L, 'au_shell', TORSO | {'lowerarm_l', 'lowerarm_r'},
                          [(V((0, 0, L['thigh_l'].z - 0.07)), (0, 0, 1), True),
                           (V((0, 0, L['neck_01'].z + 0.030)), (0, -0.4, 1), False),
                           (V((wx, 0, za)), (1, 0, 0), False), (V((-wx, 0, za)), (-1, 0, 0), False)],
                          inflate=0.009)
    sp = G.SkirtSpec(L, z_hem=0.115)
    shell_co = [v.co for v in shell.data.vertices]
    nb_ = len(body.mesh.data.vertices)
    alb_src = F.BVHTree.FromPolygons(
        [v.co for v in body.mesh.data.vertices] + shell_co,
        [list(p.vertices) for p in body.mesh.data.polygons if all(dom[i] in LEGS for i in p.vertices)] +
        [[nb_ + i for i in p.vertices] for p in shell.data.polygons])
    alb, prof = G.build_skirt(alb_src, sp)
    up_src = F.BVHTree.FromPolygons(
        [v.co for v in body.mesh.data.vertices] + shell_co,
        [list(p.vertices) for p in body.mesh.data.polygons
         if all(dom[i] not in ARMS and dom[i] not in ('Head', 'neck_01') for i in p.vertices)] +
        [[nb_ + i for i in p.vertices] for p in shell.data.polygons
         if all(shell_co[i].z < L['neck_01'].z - 0.01 and abs(shell_co[i].x) < 0.30 for i in p.vertices)])
    hang = F.bvh_objs([shell, alb])
    W = 0.185
    chas = G.build_chasuble(up_src, hang, L, W=W)
    collar = G.build_collar(F.bvh_objs([shell, body.mesh]), L)
    sleeves = G.build_bell_sleeves(L)
    stole = G.build_stole(F.bvh_objs([chas]), F.bvh_objs([alb]), L)
    frost = G.build_frost(sp, prof, chas)

    # ---------------------------------------------------------------- head things
    back_y = max(v.co.y for v in hair.data.vertices)
    halo, halo_c = G.build_halo(L, back_y)
    icicles = G.build_icicle_hair(hair, L)
    parts, sun_c = G.crozier_local()
    Ms = Matrix.Translation(grip) @ gaxis.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    for o in parts:
        o.data.transform(Ms)
        o.data.update()
    sun_w = Ms @ sun_c

    # ---------------------------------------------------------------- weights
    body_ws = F.WeightSource(body.mesh)
    F.weights_fn(alb, leg_split_fn(sp.z_hip, sp.z_top, body_ws, calf_max=0.6))
    F.weights_fn(chas, leg_split_fn(sp.z_hip, sp.z_hip + 0.12, body_ws, calf_max=0.25, pel=0.6))
    chas_w = F.smooth_weights(chas, F.read_weights(chas), 3, 0.5)
    F.write_weights(chas, chas_w)
    F.weights_transfer(collar, body_ws, smooth_iters=3)

    def sleeve_w(c):
        side = 'l' if c.x > 0 else 'r'
        u = F.sstep(abs(L['lowerarm_l'].x) + 0.07, abs(L['lowerarm_l'].x) - 0.01, abs(c.x)) * 0.5
        return {'lowerarm_' + side: 1 - u, 'upperarm_' + side: u}
    F.weights_fn(sleeves, sleeve_w)
    ch_ws = F.WeightSource(chas)
    al_ws = F.WeightSource(alb)

    def stole_w(c):
        w1 = ch_ws.at(c)
        if c.z < 0.62:
            return F.blend(w1, 0.5, al_ws.at(c), 0.5)
        return w1
    F.weights_fn(stole, stole_w)
    F.write_weights(stole, F.smooth_weights(stole, F.read_weights(stole), 3, 0.5))

    def frost_w(c):
        return ch_ws.at(c) if c.z > sp.z_hem + 0.12 and abs(c.y - 0.035) < 0.40 and chas_dist(c) < 0.06 else al_ws.at(c)

    def chas_dist(c):
        loc, nrm, idx, d = ch_ws.bvh.find_nearest(c)
        return d if d is not None else 1.0
    F.weights_fn(frost, frost_w)
    F.weights_rigid(halo, 'Head')
    hz = L['Head'].z

    def icicle_w(c):
        t = F.sstep(hz + 0.06, hz - 0.12, c.z) * 0.45
        return {'Head': 1 - t, 'neck_01': t}
    F.weights_fn(icicles, icicle_w)
    for o in parts:
        F.weights_rigid(o, 'hand_r')

    # ---------------------------------------------------------------- hide the covered body
    covered(body, F.bvh_objs([shell, alb, chas, collar]),
            {'Head', 'hand_l', 'hand_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r', 'calf_l', 'calf_r'} |
            {b for b in ARMS if not b.startswith('lowerarm')})

    # ---------------------------------------------------------------- split gold trims
    def chas_trim(c, f):
        zb = (0.50 if c.y < 0.035 else 0.46) + 0.17 * (abs(c.x) / W) ** 2
        if abs(c.x) > W - 0.026 or c.z < zb + 0.040:
            return True
        if c.y > 0.035 and abs(c.x) < 0.030 and c.z < 1.47:          # orphrey column on the back only
            return True
        if c.y > 0.035 and abs(c.z - 1.22) < 0.026 and abs(c.x) < 0.13:  # ... crossed by a bar
            return True
        return False
    chas_gold = G.split_faces(chas, chas_trim, 'au_chas_gold')
    cuffs = G.split_faces(sleeves, lambda c, f: abs(c.x) > abs(L['hand_l'].x) - 0.065, 'au_cuffs')

    # ---------------------------------------------------------------- materials
    base_img = bpy.data.images.load(os.path.join(F.UBC_TEX, 'T_Superhero_Female_Dark_BaseColor.png'))
    nrm_img = bpy.data.images.load(os.path.join(F.UBC_TEX, 'T_Superhero_Female_Normal.png'))
    nrm_img.colorspace_settings.name = 'Non-Color'
    spheres = G.eye_spheres(body.eyes)
    mats = dict(skin=M.skin(L, base_img, nrm_img, tips), lids=M.lids(spheres), brows=M.brows(), hair=M.hair(),
                icicle=M.icicle(), halo=M.halo(), shaft=M.croz_shaft(), gold_metal=M.croz_gold(), sun=M.croz_sun(),
                ice=M.icicle(0.55), alb=M.robe('alb', sp.z_hem), chas=M.robe('chas', 0.50),
                stole=M.gold('stole'), trim=M.gold('trim'))

    def setm(o, m):
        o.data.materials.clear()
        o.data.materials.append(m)
    setm(body.mesh, mats['skin'])
    for o, k in ((body.eyes, 'lids'), (body.brows, 'brows'), (hair, 'hair'), (icicles, 'icicle'), (halo, 'halo'),
                 (frost, 'icicle'), (shell, 'alb'), (alb, 'alb'), (chas, 'chas'), (sleeves, 'chas'),
                 (stole, 'stole'), (chas_gold, 'trim'), (cuffs, 'trim'), (collar, 'trim')):
        setm(o, mats[k])
    for o, k in zip(parts, ('shaft', 'gold_metal', 'sun', 'ice')):
        setm(o, mats[k])

    sockets = {'socket_staff': ('hand_r', sun_w), 'socket_halo': ('Head', halo_c)}
    for n, (par, p) in sockets.items():
        add_bone(arm, n, par, p, p + V((0, 0, 0.08)))

    if LOOK:
        for k, hx in (('alb', ROBE_TINT), ('chas', ROBE_TINT), ('stole', GOLD_TINT), ('trim', GOLD_TINT)):
            preview_tint(mats[k], hx)
        look(body, [hair, icicles, halo, frost, shell, alb, chas, chas_gold, sleeves, cuffs, stole, collar] + parts)
        return

    # ---------------------------------------------------------------- bake + assemble
    k_body = F.Kit('Aurelia_Body', 2048)
    k_body.add(body.mesh)
    LO_body = k_body.build(TEX, arm, keep_uv=True, ao_dist=0.08, ao_in_color=0.4, emit_strength=3.0)
    LO_body.data.materials[0].name = 'au_skin'

    k_robe = F.Kit('Aurelia_Robes', 2048)
    for o, w in ((shell, 1.0), (alb, 1.0), (chas, 1.0), (sleeves, 1.0)):
        k_robe.add(o, uvw=w)
    LO_robe = k_robe.build(TEX, arm, ao_dist=0.10, ao_in_color=0.5, emit_strength=4.0, double_sided=True)
    set_tint(LO_robe, 'tint1_robes', ROBE_TINT)

    k_gold = F.Kit('Aurelia_Gold', 2048)
    for o, w in ((stole, 1.4), (chas_gold, 1.0), (cuffs, 1.0), (collar, 1.2)):
        k_gold.add(o, uvw=w)
    LO_gold = k_gold.build(TEX, arm, ao_dist=0.08, ao_in_color=0.45, emit_strength=3.0, double_sided=True, metal=True)
    set_tint(LO_gold, 'tint2_gold', GOLD_TINT)

    k_misc = F.Kit('Aurelia_Misc', 2048)
    for o, w in ((hair, 1.0), (icicles, 1.2), (halo, 1.5), (frost, 1.5)):
        k_misc.add(o, uvw=w)
    for o, w in zip(parts, (1.0, 1.6, 2.0, 1.6)):
        k_misc.add(o, uvw=w)
    k_misc.add(body.eyes, uvw=6.0)
    k_misc.add(body.brows, uvw=2.0)
    LO_misc = k_misc.build(TEX, arm, ao_dist=0.06, ao_in_color=0.35, emit_strength=6.0, double_sided=True, metal=True)
    LO_misc.data.materials[0].name = 'au_misc'

    objs = [LO_body, LO_robe, LO_gold, LO_misc]
    for o in objs:
        F.triangulate(o)
    tris = {o.name: F.tri_count(o) for o in objs}
    F.log('TRIS', tris, 'total', sum(tris.values()))
    out = os.path.join(WORK, ID + '_src.glb')
    F.export_glb(out, [arm] + objs)
    rep = dict(tris=tris, total=sum(tris.values()), materials=[o.data.materials[0].name for o in objs],
               height=max((o.matrix_world @ v.co).z for o in objs[:3] for v in o.data.vertices),
               halo_top=max(v.co.z for v in LO_misc.data.vertices), bones=len(arm.data.bones), extra_bones=list(sockets),
               scale=SCALE, pelvis_rest_z=body.h('pelvis').z, glb_mb=os.path.getsize(out) / 1e6)
    json.dump(rep, open(os.path.join(WORK, 'build_report.json'), 'w'), indent=1)
    F.save_blend(os.path.join(WORK, ID + '.blend'))


def look(body, parts):
    import fbview as FV
    show = [o for o in [body.mesh, body.eyes, body.brows] + parts if o]
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o not in show:
            o.hide_render = True
    cam, g = FV.studio(900, samples=32)
    for v in A[A.index('--look') + 1:] or ['front', 'side', 'threeq', 'face']:
        if v == 'face':
            FV.frame(cam, show, (-20, -2), focus=(body.L['head_c'] + V((0, -0.03, 0.0)), 0.17), lens=85, pad=1.0)
        else:
            FV.frame(cam, show, v)
        FV.render(os.path.join(WORK, 'look_%s.jpg' % v))


if __name__ == '__main__':
    main()
