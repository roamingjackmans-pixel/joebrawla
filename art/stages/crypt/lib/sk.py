"""JoeBrawla stage kit (Blender 5.2, headless). Shared by art/stages/{crypt,hollows,drowned,forest,landing}.

Builds a fighting-game set on top of the Dungeon Joe 3D prop pipeline (dj_common / dj_mats, copied here):
  * templates: imported GLB/glTF assets (DJ3D custom props, Quaternius / KayKit CC0 packs) or procedural parts,
    each joined into one mesh in the hidden LIB collection; the set places linked copies of them (put()).
  * atlases: groups of templates (or unique in-place pieces) re-baked with Cycles into one PBR atlas
    (BaseColor / ORM / Normal / optional Emission), the way dj_common.finish bakes a single prop.
  * tiles: seamless procedural textures (noise evaluated on a 4D torus) for ground and other large surfaces,
    used with world-scale UVs and multiplied by vertex colour (COLOR_0) for broad variation.
  * export: everything placed is realised and joined per material (and per shadow class), checked against the
    keep-clear zone of art/STAGE_BRIEF.md, exported as glTF (Y-up), and compressed with tools/assets.mjs.

Coordinates: Blender X = glTF x (along the fighting line), Blender Y = -glTF z (depth, + is away from the camera),
Blender Z = glTF y (up). The fighters stand on Y = 0; the camera sits at Y ~ -9.5; the background is +Y.
"""
import bpy, bmesh, math, os, sys, json, random, time, subprocess
import numpy as np
from mathutils import Vector, Matrix, Euler, noise as mnoise
import dj_common as dj
from dj_common import M, col

JB = r"C:\dev\JoeBrawla"
DJ3D = r"C:\dev\AverageJoe\DungeonJoe3D"
DL = r"C:\dev\AverageJoe\_downloads"
P_PROPS = os.path.join(DJ3D, 'assets', 'custom', 'props')
P_HUB = os.path.join(DJ3D, 'assets', 'custom', 'hub')
P_NATURE = os.path.join(DL, 'quaternius-stylized-nature-megakit', 'x', 'glTF')
P_VILLAGE = os.path.join(DL, 'quaternius-medieval-village-megakit', 'x', 'Medieval Village MegaKit[Standard]', 'glTF')
P_FPROPS = os.path.join(DL, 'quaternius-fantasy-props-megakit', 'x', 'Exports', 'glTF')
P_KK_HALLOWEEN = os.path.join(DL, 'kaykit-halloween-bits', 'x', 'KayKit_HalloweenBits_1.0_FREE', 'Assets', 'gltf')
P_KK_FOREST = os.path.join(DL, 'kaykit-forest-nature-pack', 'x', 'KayKit_Forest_Nature_Pack_1.0_FREE', 'Assets', 'gltf')
P_KENNEY_GY = os.path.join(DL, 'kenney-graveyard-kit', 'x', 'Models', 'GLB format')
NODE = r"C:\Program Files\nodejs\node.exe"

# keep-clear zone (Blender coords): nothing above KEEP_H in y in [KEEP_Y0, KEEP_Y1] (glTF z in [-1.5, +6])
KEEP_Y0, KEEP_Y1, KEEP_H = -6.0, 1.5, 0.25

dj.M.DEFAULTS['aomul'] = (1.0, 1.0, 1.0, 1.0)
dj.M.DEFAULTS['alpha'] = (1.0, 1.0, 1.0, 1.0)


def work_dir(sid):
    d = os.path.join(JB, 'art', '_work', 'stages', sid)
    os.makedirs(d, exist_ok=True)
    return d


def stage_dir(sid):
    d = os.path.join(JB, 'art', 'stages', sid)
    os.makedirs(d, exist_ok=True)
    return d


def log(*a):
    print('[sk]', *a, flush=True)


# ----------------------------------------------------------------------------- scene / collections
def reset(sid):
    dj.reset()
    dj.BAKE_DIR = os.path.join(work_dir(sid), 'bake')
    os.makedirs(dj.BAKE_DIR, exist_ok=True)
    _LIB.clear()
    _WRAPPED.clear()
    sc = bpy.context.scene
    for name in ('LIB', 'SET'):
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    sc.render.engine = 'CYCLES'
    return sc


def coll(name):
    return bpy.data.collections[name]


def _link(ob, cname):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll(cname).objects.link(ob)
    return ob


def set_objects():
    return [o for o in coll('SET').all_objects if o.type == 'MESH']


# ----------------------------------------------------------------------------- templates
_LIB = {}
_WRAPPED = {}


def load(path, name=None, scale=1.0, wrap=True, keep_mats=False):
    """Import a GLB/glTF once and return a single joined mesh object in LIB (origin = asset origin)."""
    key = (path, scale)
    if key in _LIB:
        return _LIB[key]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    bpy.context.view_layer.update()
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        if o.data.users > 1:
            o.data = o.data.copy()
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o)
    nm = name or os.path.splitext(os.path.basename(path))[0]
    ob = dj.join(meshes, 'T_' + nm)
    if scale != 1.0:
        ob.data.transform(Matrix.Scale(scale, 4))
    _link(ob, 'LIB')
    if wrap and not keep_mats:
        wrap_materials(ob)
    _LIB[key] = ob
    return ob


def template(parts, name, rest=True, smooth_angle=None):
    """Procedural parts -> one LIB template (stores the 'rest' attribute for the procedural materials)."""
    for o in parts:
        if rest and o.data.attributes.get('rest') is None:
            dj.store_rest(o)
    ob = dj.join(parts, 'T_' + name)
    if smooth_angle is not None:
        dj.smooth(ob, smooth_angle)
    _link(ob, 'LIB')
    return ob


def copy_template(t, name, fn=None):
    ob = t.copy()
    ob.data = t.data.copy()
    ob.name = 'T_' + name
    ob.data.name = ob.name
    _link(ob, 'LIB')
    if fn:
        fn(ob)
    return ob


def lod(t, ratio, name=None):
    """Decimated copy of a template (same materials / UVs)."""
    def f(o):
        m = o.modifiers.new('Dec', 'DECIMATE')
        m.ratio = ratio
        m.use_collapse_triangulate = True
        dj.apply_mods(o)
    return copy_template(t, name or (t.name[2:] + '_lod'), f)


def put(t, x, y, z=0.0, rz=0.0, s=1.0, rx=0.0, ry=0.0, name=None, cname='SET'):
    """Place a linked copy of template t. Angles in degrees; s scalar or (sx,sy,sz)."""
    ob = bpy.data.objects.new(name or t.name[2:], t.data)
    ob.location = (x, y, z)
    ob.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    ob.scale = (s, s, s) if isinstance(s, (int, float)) else s
    coll(cname).objects.link(ob)
    return ob


def unique(ob, name=None, cname='SET'):
    """A one-off procedural object placed directly in the set (stores rest = its own mesh coords)."""
    if ob.data.attributes.get('rest') is None:
        dj.store_rest(ob)
    if name:
        ob.name = name
        ob.data.name = name
    _link(ob, cname)
    return ob


# ----------------------------------------------------------------------------- imported materials -> bakeable M
def _upstream(sock, types):
    """Follow links upstream from a socket to the first node of one of the given bl_idnames."""
    seen = set()
    stack = [sock]
    while stack:
        s = stack.pop()
        for l in s.links:
            n = l.from_node
            if n.name in seen:
                continue
            seen.add(n.name)
            if n.bl_idname in types:
                return n
            for i in n.inputs:
                if i.is_linked:
                    stack.append(i)
    return None


def wrap_material(mat, uvname='UVMap'):
    """Rebuild an imported (glTF) material as a dj M with color/rough/metal/emit channels + normal map."""
    if mat.name in _WRAPPED:
        return _WRAPPED[mat.name]
    nt = mat.node_tree
    b = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    m = M('w_' + mat.name)
    m.ch['aomul'] = m.S(0.0)
    uv = m.uvmap(uvname)

    def tex(sock):
        n = _upstream(sock, ('ShaderNodeTexImage',)) if sock is not None else None
        return n.image if n is not None else None

    if b is None:
        m.set(color=(0.5, 0.5, 0.5, 1), rough=0.8)
        _WRAPPED[mat.name] = m
        return m
    bc = b.inputs['Base Color']
    im = tex(bc)
    if im is not None:
        im.colorspace_settings.name = 'sRGB'
        c = m.image(im, uv, 'REPEAT')
        # vertex colour or factor multiply (Quaternius uses plain factors)
        fac = tuple(bc.default_value)
        mixn = _upstream(bc, ('ShaderNodeMix', 'ShaderNodeMixRGB'))
        if mixn is not None:
            for s in mixn.inputs:
                if s.type == 'RGBA' and not s.is_linked and s.name in ('B', 'Color2') and s.identifier in ('B_Color', 'Color2'):
                    fac = tuple(s.default_value)
        if fac[:3] != (1.0, 1.0, 1.0) and mixn is not None:
            c = m.mix(1.0, c, fac, 'MULTIPLY')
        color = c
    else:
        color = tuple(bc.default_value)
    rough_in, metal_in = b.inputs['Roughness'], b.inputs['Metallic']
    orm = tex(rough_in) or tex(metal_in)
    if orm is not None:
        orm.colorspace_settings.name = 'Non-Color'
        sep = m.N.new('ShaderNodeSeparateColor')
        m.L(m.image(orm, uv, 'REPEAT'), sep.inputs[0])
        rough = m.mul(sep.outputs['Green'], 1.0)
        metal = sep.outputs['Blue'] if tex(metal_in) is not None else m.S(float(metal_in.default_value))
    else:
        rough = float(rough_in.default_value)
        metal = float(metal_in.default_value)
    emit = None
    ec = b.inputs.get('Emission Color')
    es = float(b.inputs['Emission Strength'].default_value) if 'Emission Strength' in b.inputs else 0.0
    eim = tex(ec)
    if eim is not None:
        emit = m.image(eim, uv, 'REPEAT')
    elif ec is not None and es > 0 and max(ec.default_value[:3]) > 0:
        emit = tuple(ec.default_value)
    m.set(color=color, rough=rough, metal=metal, emit=emit)
    nmn = _upstream(b.inputs['Normal'], ('ShaderNodeNormalMap',))
    if nmn is not None:
        nim = tex(nmn.inputs['Color'])
        if nim is not None:
            nim.colorspace_settings.name = 'Non-Color'
            nm = m.N.new('ShaderNodeNormalMap')
            nm.uv_map = uvname
            nm.inputs['Strength'].default_value = nmn.inputs['Strength'].default_value
            m.L(m.image(nim, uv, 'REPEAT'), nm.inputs['Color'])
            m.L(nm.outputs['Normal'], m.bumpn.inputs['Normal'])
    a = b.inputs['Alpha']
    aim = _upstream(a, ('ShaderNodeTexImage',))
    if aim is not None:
        m.ch['alpha'] = m.N.new('ShaderNodeTexImage').outputs[0]
    _WRAPPED[mat.name] = m
    return m


def wrap_materials(ob):
    me = ob.data
    if me.uv_layers:
        me.uv_layers[0].name = 'UVMap'
    for i, s in enumerate(me.materials):
        if s is None or s.name.startswith('w_') or s.name in dj.PROC:
            continue
        me.materials[i] = wrap_material(s).mat
    return ob


# ----------------------------------------------------------------------------- tiles (seamless 4D-torus noise)
class TileM(M):
    """M whose noise / voronoi are periodic in x and y with period L (rest coordinates): seamless tiles."""

    def __init__(self, name, L=1.0, glow=False):
        super().__init__(name, glow)
        self.Lp = L

    def _torus(self, vec):
        x, y, z = self.sep(vec)
        k = 2 * math.pi / self.Lp
        R = self.Lp / (2 * math.pi)
        a = self.mul(x, k)
        b = self.mul(y, k)
        X = self.mul(self.math('COSINE', a), R)
        Y = self.mul(self.math('SINE', a), R)
        Z = self.add(self.mul(self.math('COSINE', b), R), self.mul(z, 0.0))
        W = self.mul(self.math('SINE', b), R)
        return self.comb(X, Y, Z), W

    def noise(self, vec, scale=1.0, detail=2.0, rough=0.5, dist=0.0, ntype='FBM', lac=2.0):
        v, w = self._torus(vec)
        n = self.N.new('ShaderNodeTexNoise')
        n.noise_dimensions = '4D'
        n.noise_type = ntype
        self.inp(n.inputs['Vector'], v)
        self.inp(n.inputs['W'], w)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Detail'], detail)
        self.inp(n.inputs['Roughness'], rough)
        self.inp(n.inputs['Distortion'], dist)
        self.inp(n.inputs['Lacunarity'], lac)
        return n.outputs['Fac']

    def noisec(self, vec, scale=1.0, detail=2.0, rough=0.5):
        v, w = self._torus(vec)
        n = self.N.new('ShaderNodeTexNoise')
        n.noise_dimensions = '4D'
        self.inp(n.inputs['Vector'], v)
        self.inp(n.inputs['W'], w)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Detail'], detail)
        self.inp(n.inputs['Roughness'], rough)
        return n.outputs['Color']

    def voronoi(self, vec, scale=5.0, feature='F1', metric='EUCLIDEAN', rand=1.0):
        v, w = self._torus(vec)
        n = self.N.new('ShaderNodeTexVoronoi')
        n.voronoi_dimensions = '4D'
        n.feature = feature
        n.distance = metric
        self.inp(n.inputs['Vector'], v)
        self.inp(n.inputs['W'], w)
        self.inp(n.inputs['Scale'], scale)
        self.inp(n.inputs['Randomness'], rand)
        outs = {s.identifier: s for s in n.outputs}
        return outs.get('Distance'), outs.get('Color')

    def wave(self, *a, **k):
        raise RuntimeError('wave is not periodic; use noise/voronoi in tiles')


def tile_plane(L, n=1):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=n, y_segments=n, size=L / 2)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(L / 2, L / 2, 0))
    uvl = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x / L, l.vert.co.y / L)
    me = bpy.data.meshes.new('tileplane')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('tileplane', me)
    bpy.context.scene.collection.objects.link(ob)
    dj.store_rest(ob)
    return ob


def bake_tile(m, name, size=1024, emission=False, samples=16):
    """Bake TileM m on an L x L plane (UV 0..1) -> dict of images (base, orm, normal[, emit])."""
    L = m.Lp
    ob = tile_plane(L)
    ob.data.materials.append(m.mat)
    me = ob.data
    uv = me.uv_layers['UVMap']
    uv.name = 'atlas'
    hidden = []
    for o in bpy.context.scene.objects:
        if o is not ob and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    imgs = bake_objs([ob], name, size=size, emission=emission, ao_dist=0.01, samples=samples, ao_strength=0.0,
                     margin_px=0)
    for o in hidden:
        o.hide_render = False
    bpy.data.objects.remove(ob)
    return imgs


def image_material(name, imgs, uv='UVMap', vcol=None, double_sided=False, emission_strength=1.0, alpha_clip=None,
                   rough_scale=1.0, base_tint=None, normal_strength=1.0, nm_uv=None):
    """Export-ready Principled material from baked images (base/orm/normal/emit), optional vertex colour multiply."""
    mt = bpy.data.materials.new(name)
    nt = mt.node_tree
    N = nt.nodes
    L = nt.links.new
    N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    b = N.new('ShaderNodeBsdfPrincipled')
    L(b.outputs[0], out.inputs['Surface'])
    uvn = N.new('ShaderNodeUVMap')
    uvn.uv_map = uv
    tb = N.new('ShaderNodeTexImage')
    tb.image = imgs['base']
    L(uvn.outputs[0], tb.inputs['Vector'])
    basec = tb.outputs['Color']
    if vcol:
        ca = N.new('ShaderNodeVertexColor')
        ca.layer_name = vcol
        mx = N.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0
        L(basec, mx.inputs[6])
        L(ca.outputs['Color'], mx.inputs[7])
        basec = mx.outputs[2]
    L(basec, b.inputs['Base Color'])
    if 'orm' in imgs:
        to = N.new('ShaderNodeTexImage')
        to.image = imgs['orm']
        L(uvn.outputs[0], to.inputs['Vector'])
        sp = N.new('ShaderNodeSeparateColor')
        L(to.outputs['Color'], sp.inputs[0])
        L(sp.outputs['Green'], b.inputs['Roughness'])
        L(sp.outputs['Blue'], b.inputs['Metallic'])
        g = N.new('ShaderNodeGroup')
        g.node_tree = dj._gltf_output_group()
        L(sp.outputs['Red'], g.inputs['Occlusion'])
    else:
        b.inputs['Roughness'].default_value = 0.85
    if 'normal' in imgs:
        tn = N.new('ShaderNodeTexImage')
        tn.image = imgs['normal']
        L(uvn.outputs[0], tn.inputs['Vector'])
        nm = N.new('ShaderNodeNormalMap')
        nm.uv_map = nm_uv or uv
        nm.inputs['Strength'].default_value = normal_strength
        L(tn.outputs['Color'], nm.inputs['Color'])
        L(nm.outputs['Normal'], b.inputs['Normal'])
    if 'emit' in imgs:
        te = N.new('ShaderNodeTexImage')
        te.image = imgs['emit']
        L(uvn.outputs[0], te.inputs['Vector'])
        L(te.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emission_strength
    if alpha_clip is not None:
        L(tb.outputs['Alpha'], b.inputs['Alpha'])
        mt.surface_render_method = 'DITHERED'
        mt['alpha_clip'] = alpha_clip
    mt.use_backface_culling = not double_sided
    return mt


def color_material(name, color='#ffffff', rough=0.85, metal=0.0, vcol='Col', emit=None, emit_strength=1.0,
                   double_sided=False):
    """Untextured material (vertex colour x factor), e.g. grass blades, far silhouettes, glows."""
    mt = bpy.data.materials.new(name)
    nt = mt.node_tree
    N = nt.nodes
    L = nt.links.new
    N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    b = N.new('ShaderNodeBsdfPrincipled')
    L(b.outputs[0], out.inputs['Surface'])
    b.inputs['Base Color'].default_value = col(color)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if vcol:
        ca = N.new('ShaderNodeVertexColor')
        ca.layer_name = vcol
        if color.lower() in ('#ffffff', '#fff'):
            L(ca.outputs['Color'], b.inputs['Base Color'])
        else:
            mx = N.new('ShaderNodeMix')
            mx.data_type = 'RGBA'
            mx.blend_type = 'MULTIPLY'
            mx.inputs['Factor'].default_value = 1.0
            mx.inputs[6].default_value = col(color)
            L(ca.outputs['Color'], mx.inputs[7])
            L(mx.outputs[2], b.inputs['Base Color'])
    if emit:
        b.inputs['Emission Color'].default_value = col(emit)
        b.inputs['Emission Strength'].default_value = emit_strength
    mt.use_backface_culling = not double_sided
    return mt


def save_img(im, path, fmt='PNG'):
    im.filepath_raw = path
    im.file_format = fmt
    im.save()
    return im


def scale_img(im, size):
    if im.size[0] > size:
        im.scale(size, max(1, int(size * im.size[1] / im.size[0])))
    return im


# ----------------------------------------------------------------------------- vertex colours
def vcol_layer(ob, name='Col', fill=(1, 1, 1, 1)):
    me = ob.data
    a = me.color_attributes.get(name)
    if a is None:
        a = me.color_attributes.new(name, 'BYTE_COLOR', 'CORNER')
        n = len(a.data)
        a.data.foreach_set('color', np.tile(np.array(fill, np.float32), n))
    me.color_attributes.active_color = a
    me.color_attributes.render_color_index = me.color_attributes.find(name)
    return a


def vcol_from_points(ob, fn, name='Col'):
    """fn(world co Vector, normal Vector) -> (r,g,b) linear; written per corner."""
    a = vcol_layer(ob, name)
    me = ob.data
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    vals = []
    for v in me.vertices:
        vals.append(fn(mw @ v.co, (nm @ v.normal).normalized()))
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    arr = np.ones((len(me.loops), 4), np.float32)
    arr[:, :3] = np.array(vals, np.float32)[vi]
    a.data.foreach_set('color', arr.ravel())
    return a


def vcol_multiply(ob, arr_per_vertex, name='Col'):
    a = vcol_layer(ob, name)
    me = ob.data
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    cur = np.empty(len(me.loops) * 4, np.float32)
    a.data.foreach_get('color', cur)
    cur = cur.reshape(-1, 4)
    cur[:, :3] *= np.asarray(arr_per_vertex, np.float32)[vi][:, :3] if np.ndim(arr_per_vertex) == 2 else \
        np.asarray(arr_per_vertex, np.float32)[vi][:, None]
    a.data.foreach_set('color', cur.ravel())


def bake_vertex_ao(obs, dist=1.5, samples=64, strength=1.0, lo=0.0):
    """Cycles AO -> per-vertex multiply on each object's Col (everything else in the scene occludes)."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    if sc.world is None:
        sc.world = bpy.data.worlds.new('BakeWorld')
    sc.world.light_settings.distance = dist
    sc.cycles.samples = samples
    for ob in obs:
        me = ob.data
        tmp = me.color_attributes.new('_ao', 'FLOAT_COLOR', 'CORNER')
        me.color_attributes.active_color = tmp
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
        n = len(tmp.data)
        ao = np.empty(n * 4, np.float32)
        tmp.data.foreach_get('color', ao)
        ao = ao.reshape(-1, 4)[:, 0]
        ao = 1 - strength * (1 - np.clip(ao, lo, 1))
        me.color_attributes.remove(tmp)
        a = vcol_layer(ob)
        cur = np.empty(n * 4, np.float32)
        a.data.foreach_get('color', cur)
        cur = cur.reshape(-1, 4)
        cur[:, :3] *= ao[:, None]
        a.data.foreach_set('color', cur.ravel())


# ----------------------------------------------------------------------------- heightfield terrain
def axis_samples(segments):
    """segments: [(a, b, step), ...] contiguous ranges -> sorted unique coordinates."""
    out = []
    for a, b, st in segments:
        n = max(1, int(round((b - a) / st)))
        out += list(np.linspace(a, b, n + 1))
    return np.unique(np.round(np.array(out), 5))


def heightfield(name, xs, ys, hfn, mat=None, uv_scale=0.25, cut=None):
    """Grid over xs x ys (Blender coords); z = hfn(X, Y) (numpy arrays). UV = world XY * uv_scale.
    cut(cx, cy) -> True drops that quad (holes)."""
    X, Y = np.meshgrid(xs, ys)
    Z = hfn(X, Y)
    nx, ny = len(xs), len(ys)
    co = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    quads = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            if cut is not None and cut((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2):
                continue
            a = j * nx + i
            quads.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new(name)
    me.from_pydata(co.tolist(), [], quads)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    uvs = co[vi, :2] * uv_scale
    uvl.data.foreach_set('uv', uvs.ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    me.shade_smooth()
    # drop unused verts (holes)
    if cut is not None:
        bm = bmesh.new()
        bm.from_mesh(me)
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(me)
        bm.free()
    return ob


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def fbm2(X, Y, scale=0.05, oct=4, seed=0):
    """Vectorised-ish 2D fbm through mathutils noise (slow per point but fine for ~50k samples)."""
    out = np.zeros_like(X, dtype=np.float64)
    flat_x, flat_y = X.ravel(), Y.ravel()
    o = np.empty(flat_x.shape[0])
    off = Vector((seed * 17.3, seed * 5.1, seed * 2.7))
    for i in range(flat_x.shape[0]):
        o[i] = mnoise.fractal(Vector((flat_x[i] * scale, flat_y[i] * scale, 0)) + off, 0.5, 2.0, oct)
    return o.reshape(X.shape)


def noise_at(x, y, scale=0.1, seed=0, oct=3):
    return mnoise.fractal(Vector((x * scale + seed * 17.3, y * scale + seed * 5.1, seed * 2.7)), 0.5, 2.0, oct)


# ----------------------------------------------------------------------------- scattering
def poisson(n, x0, x1, y0, y1, rmin, rng, accept=None, tries=30, existing=None):
    pts = list(existing or [])
    out = []
    for _ in range(n * tries):
        if len(out) >= n:
            break
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if accept and not accept(x, y):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < rmin * rmin for px, py in pts):
            continue
        pts.append((x, y))
        out.append((x, y))
    return out


def in_keep(x, y, h=KEEP_H):
    return KEEP_Y0 <= y <= KEEP_Y1 and h > KEEP_H


# ----------------------------------------------------------------------------- small procedural set dressing
def grass_tuft(name, rng, n=9, h=(0.12, 0.24), spread=0.09, base='#3f6a26', tip='#a8c25a', lean=0.35, w=0.018):
    """Clump of tapered blades (3 verts each, double sided) with a root-to-tip vertex gradient."""
    bm = bmesh.new()
    cl = bm.loops.layers.color.new('Col')
    cb, ct = Vector(col(base)[:3]), Vector(col(tip)[:3])
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, spread)
        px, py = math.cos(a) * r, math.sin(a) * r
        hh = rng.uniform(*h)
        yaw = rng.uniform(0, 2 * math.pi)
        lx, ly = math.cos(a) * lean * hh * rng.uniform(0.3, 1), math.sin(a) * lean * hh * rng.uniform(0.3, 1)
        dx, dy = math.cos(yaw) * w, math.sin(yaw) * w
        v1 = bm.verts.new((px - dx, py - dy, 0))
        v2 = bm.verts.new((px + dx, py + dy, 0))
        v3 = bm.verts.new((px + lx * 0.5 + dx * 0.4, py + ly * 0.5 + dy * 0.4, hh * 0.55))
        v4 = bm.verts.new((px + lx * 0.5 - dx * 0.4, py + ly * 0.5 - dy * 0.4, hh * 0.55))
        v5 = bm.verts.new((px + lx, py + ly, hh))
        k = rng.uniform(0.75, 1.15)
        for f in (bm.faces.new((v1, v2, v3, v4)), bm.faces.new((v4, v3, v5))):
            for l in f.loops:
                t = l.vert.co.z / hh
                c = cb.lerp(ct, t ** 0.8) * k
                l[cl] = (c.x, c.y, c.z, 1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def flower_clump(name, rng, n=5, h=(0.1, 0.22), petal='#f2e8a0', centre='#e0a020', stem='#4a7a2a', size=0.035):
    bm = bmesh.new()
    cl = bm.loops.layers.color.new('Col')
    cs, cp, cc = col(stem), col(petal), col(centre)
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, 0.1)
        px, py = math.cos(a) * r, math.sin(a) * r
        hh = rng.uniform(*h)
        tx, ty = px + rng.uniform(-0.03, 0.03), py + rng.uniform(-0.03, 0.03)
        # stem: thin quad
        v = [bm.verts.new((px - 0.004, py, 0)), bm.verts.new((px + 0.004, py, 0)),
             bm.verts.new((tx + 0.003, ty, hh)), bm.verts.new((tx - 0.003, ty, hh))]
        f = bm.faces.new(v)
        for l in f.loops:
            l[cl] = cs
        # head: small star of petals facing up/camera
        s = size * rng.uniform(0.8, 1.2)
        k = 5
        ctr = bm.verts.new((tx, ty, hh + 0.004))
        ring = []
        tilt = rng.uniform(0.2, 0.6)
        for j in range(k * 2):
            ang = j * math.pi / k + rng.uniform(-0.1, 0.1)
            rr = s if j % 2 == 0 else s * 0.45
            ring.append(bm.verts.new((tx + math.cos(ang) * rr, ty + math.sin(ang) * rr * math.cos(tilt) - 0.0,
                                      hh + math.sin(ang) * rr * math.sin(tilt) * -1)))
        for j in range(k * 2):
            f = bm.faces.new((ctr, ring[j], ring[(j + 1) % (k * 2)]))
            for l in f.loops:
                l[cl] = cc if l.vert is ctr else cp
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


GLYPH_Q = [[(0.5 + 0.38 * math.cos(2 * math.pi * i / 14), 0.5 + 0.5 * math.sin(2 * math.pi * i / 14)) for i in range(15)],
           [(0.6, 0.25), (0.92, -0.05)]]


def text_image(name, lines, w, h, res=512, stroke=0.12, ink=(0.08, 0.06, 0.05), paper=(0.86, 0.82, 0.68),
               seed=0, border=True, extra=None):
    """Paper texture with stroked text lines [(text, y_frac, size_frac)] (+ scribble lines) -> sRGB image."""
    import hub_lib  # glyph table extension (B, C, D, ... digits)
    dj._GLYPHS.setdefault('Q', GLYPH_Q)
    strokes = []
    for (txt, yf, hf) in lines:
        if txt == '~':
            strokes += [s[:3] for s in dj.scribble_strokes(w * 0.1, w * 0.9, h * yf, h * hf, seed=seed + int(yf * 100))]
        else:
            strokes += dj.text_strokes(txt, w / 2, h * yf, h * hf, width_frac=stroke)
    if extra:
        strokes += extra
    mask = dj.stroke_image(name + '_mask', w, h, strokes, res)
    rx, ry = mask.size
    a = np.empty(rx * ry * 4, np.float32)
    mask.pixels.foreach_get(a)
    a = a.reshape(ry, rx, 4)[:, :, 0]
    bpy.data.images.remove(mask)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:ry, 0:rx]
    stain = 0.92 + 0.08 * np.sin(xx / rx * 7 + seed) * np.cos(yy / ry * 5 + seed * 2)
    stain *= 1 - 0.18 * np.clip(1 - np.minimum(np.minimum(xx, rx - xx) / (rx * 0.08), np.minimum(yy, ry - yy) / (ry * 0.08)), 0, 1)
    stain *= 0.97 + 0.03 * rng.random((ry, rx))
    pap = np.array(paper)[None, None, :] * stain[..., None]
    ik = np.array(ink)[None, None, :]
    out = pap * (1 - a[..., None]) + ik * a[..., None]
    if border:
        bw = int(rx * 0.04)
        bd = np.zeros((ry, rx), bool)
        bd[bw:bw + 2, bw:rx - bw] = True
        bd[ry - bw - 2:ry - bw, bw:rx - bw] = True
        bd[bw:ry - bw, bw:bw + 2] = True
        bd[bw:ry - bw, rx - bw - 2:rx - bw] = True
        out[bd] = out[bd] * 0.4 + ik[0, 0] * 0.6
    img = bpy.data.images.new(name, rx, ry, alpha=False)
    px = np.ones((ry, rx, 4), np.float32)
    lin = np.where(out <= 0.04045, out / 12.92, ((out + 0.055) / 1.055) ** 2.4)
    px[..., :3] = lin
    img.pixels.foreach_set(px.ravel())
    img.colorspace_settings.name = 'sRGB'
    img.update()
    return img


# ----------------------------------------------------------------------------- atlas bake
def bake_objs(objs, name, size=1024, emission=False, ao_dist=0.6, samples=32, ao_strength=0.35,
              emission_strength=3.0, margin_px=None):
    """dj_common.bake with an 'aomul' mask (imported textures already carry their AO) -> images dict."""
    t0 = time.time()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    if sc.world is None:
        sc.world = bpy.data.worlds.new('BakeWorld')
    sc.world.light_settings.distance = ao_dist
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    margin = max(8, size // 64) if margin_px is None else margin_px
    sc.render.bake.margin = margin
    mats = []
    for o in objs:
        for s in o.material_slots:
            if s.material and s.material not in mats:
                mats.append(s.material)
    need_mask = any('aomul' in dj.PROC[m.name].ch for m in mats)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    passes = [('color', True, 'EMIT'), ('rough', False, 'EMIT'), ('metal', False, 'EMIT'),
              ('normal', False, 'NORMAL'), ('ao', False, 'AO')]
    if need_mask:
        passes.append(('aomul', False, 'EMIT'))
    if emission:
        passes.append(('emit', True, 'EMIT'))
    raw = {}
    for key, iscol, btype in passes:
        im = bpy.data.images.new(f"{name}_{key}_raw", size, size, alpha=False, float_buffer=(key == 'emit'))
        im.colorspace_settings.name = 'sRGB' if (iscol and key != 'emit') else 'Non-Color'
        for mt in mats:
            pm = dj.PROC[mt.name]
            pm.wire(key)
            pm.target.image = im
            mt.node_tree.nodes.active = pm.target
        kw = dict(type=btype, margin=margin, use_clear=True)
        if btype == 'NORMAL':
            kw['normal_space'] = 'TANGENT'
        bpy.ops.object.bake(**kw)
        raw[key] = im
        log(f"  baked {name}.{key} ({time.time() - t0:.1f}s)")
    for mt in mats:
        dj.PROC[mt.name].wire('final')
    base = dj._px(raw['color']).copy()
    ao = dj._px(raw['ao'])[:, :, 0]
    k = ao_strength * (dj._px(raw['aomul'])[:, :, 0] if need_mask else 1.0)
    base[:, :, :3] *= (1.0 - k * (1.0 - ao))[:, :, None]
    base[:, :, 3] = 1.0
    orm = np.ones_like(base)
    orm[:, :, 0] = ao
    orm[:, :, 1] = np.clip(dj._px(raw['rough'])[:, :, 0], 0.04, 1.0)
    orm[:, :, 2] = dj._px(raw['metal'])[:, :, 0]

    def mk(key, arr, srgb):
        im = bpy.data.images.new(f"{name}_{key}", size, size, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        im.pixels.foreach_set(arr.ravel())
        save_img(im, os.path.join(dj.BAKE_DIR, f"{name}_{key}.png"))
        return im

    out = {'base': mk('BaseColor', base, True), 'orm': mk('ORM', orm, False)}
    nrm = dj._px(raw['normal']).copy()
    nrm[:, :, 3] = 1.0
    out['normal'] = mk('Normal', nrm, False)
    if emission:
        e = dj._px(raw['emit']).copy()
        mx = float(e[:, :, :3].max())
        scale = 1.0 if mx <= 1.0 else 1.0 / mx
        e[:, :, :3] *= scale
        e[:, :, 3] = 1.0
        out['emit'] = mk('Emission', e, True)
        out['emit_scale'] = 1.0 / scale
    for im in raw.values():
        bpy.data.images.remove(im)
    log(f"  bake {name} done {time.time() - t0:.1f}s")
    return out


class Atlas:
    """A set of templates (instanced) and/or unique set objects baked into one PBR material.
    mode 'iso': templates are moved apart (isolated AO, shared by every copy); 'inplace': objects bake where
    they stand with the rest of the set as occluders (unique pieces: terrain features, architecture)."""

    def __init__(self, name, size=2048, emission=False, mode='iso', ao_dist=0.6, ao_strength=0.35, samples=32,
                 emission_strength=3.0, double_sided=False, margin=0.004):
        self.name, self.size, self.emission, self.mode = name, size, emission, mode
        self.ao_dist, self.ao_strength, self.samples = ao_dist, ao_strength, samples
        self.emission_strength, self.double_sided, self.margin = emission_strength, double_sided, margin
        self.items = []
        self.mat = None

    def add(self, ob, weight=1.0):
        self.items.append((ob, weight))
        return ob

    def bake(self):
        objs = [o for o, _ in self.items]
        sc = bpy.context.scene
        hidden, moved = [], []
        if self.mode == 'iso':
            for o in sc.objects:
                if o not in objs and not o.hide_render:
                    o.hide_render = True
                    hidden.append(o)
            x = 0.0
            for o in objs:
                bb = [Vector(c) for c in o.bound_box]
                w = max(c.x for c in bb) - min(c.x for c in bb)
                moved.append((o, o.location.copy()))
                o.location = (x - min(c.x for c in bb), -2000.0, 0)
                x += w + 6.0
        for o in objs:
            o.hide_render = False
            if o.name not in bpy.context.view_layer.objects:
                continue
        bpy.context.view_layer.update()
        # weight texel density: scale mesh data while unwrapping
        for o, w in self.items:
            for i, s in enumerate(o.data.materials):
                if s is not None and s.name not in dj.PROC:
                    o.data.materials[i] = wrap_material(s).mat
            if w != 1.0:
                o.data.transform(Matrix.Scale(w, 4))
        _unwrap(objs, margin=self.margin)
        for o, w in self.items:
            if w != 1.0:
                o.data.transform(Matrix.Scale(1.0 / w, 4))
        imgs = bake_objs(objs, self.name, size=self.size, emission=self.emission, ao_dist=self.ao_dist,
                         samples=self.samples, ao_strength=self.ao_strength,
                         emission_strength=self.emission_strength)
        es = self.emission_strength * imgs.get('emit_scale', 1.0)
        self.mat = image_material('M_' + self.name, imgs, uv='atlas', double_sided=self.double_sided,
                                  emission_strength=es)
        for o in objs:
            me = o.data
            me.materials.clear()
            me.materials.append(self.mat)
            me.polygons.foreach_set('material_index', [0] * len(me.polygons))
            for uv in list(me.uv_layers):
                if uv.name != 'atlas':
                    me.uv_layers.remove(uv)
            for an in ('rest', 'grain', 'pid'):
                a = me.attributes.get(an)
                if a is not None:
                    me.attributes.remove(a)
            me.update()
        for o, loc in moved:
            o.location = loc
        for o in hidden:
            o.hide_render = False
        self.imgs = imgs
        return self.mat


def _unwrap(objs, margin=0.004, angle=62):
    for o in objs:
        me = o.data
        uv = me.uv_layers.get('atlas') or me.uv_layers.new(name='atlas')
        me.uv_layers.active = uv
        uv.active_render = True
    bpy.ops.object.select_all(action='DESELECT')
    vis = []
    for o in objs:
        if o.hide_get():
            o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=margin, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')


# ----------------------------------------------------------------------------- export
def realize(objs):
    """Linked copies -> single-user meshes with transforms applied (in place)."""
    out = []
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        out.append(o)
    return out


def _fix_uv_names(ob):
    me = ob.data
    if len(me.uv_layers) == 1:
        me.uv_layers[0].name = 'UVMap'


def _retarget_uv(mat):
    """Point UV Map / Normal Map nodes at 'UVMap' (the single UV layer of every exported mesh)."""
    for n in mat.node_tree.nodes:
        if n.bl_idname == 'ShaderNodeUVMap':
            n.uv_map = 'UVMap'
        elif n.bl_idname == 'ShaderNodeNormalMap':
            n.uv_map = 'UVMap'


def keep_clear_report(objs, xlim=16.0):
    bad = []
    for o in objs:
        mw = o.matrix_world
        me = o.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        M4 = np.array(mw)
        co = co @ M4[:3, :3].T + M4[:3, 3]
        m = (co[:, 1] >= KEEP_Y0) & (co[:, 1] <= KEEP_Y1) & (co[:, 2] > KEEP_H + 1e-3) & (np.abs(co[:, 0]) < xlim)
        if m.any():
            bad.append((o.name, int(m.sum()), float(co[m, 2].max())))
    return bad


def floor_report(objs):
    """Highest geometry at the flat floor region (x in [-10,10], glTF z in [-2,6]) other than 0.25 m props."""
    pass


def export(sid, extra_objects=(), tex=1024, run_assets=True, drop_names=()):
    """Join SET per (material, shadow class) + anim_ objects as-is, check, export GLB, compress."""
    sc = bpy.context.scene
    t0 = time.time()
    objs = [o for o in coll('SET').all_objects if o.type == 'MESH']
    bad = keep_clear_report(objs)
    if bad:
        log('KEEP-CLEAR VIOLATIONS:', bad[:30])
    realize(objs)
    groups = {}
    anims = []
    for o in objs:
        _fix_uv_names(o)
        if o.name.startswith('anim_'):
            anims.append(o)
            continue
        ns = 'noshadow' in o.name or o.get('noshadow')
        for i, m in enumerate(o.data.materials):
            pass
        key = (tuple(m.name for m in o.data.materials if m), bool(ns))
        groups.setdefault(key, []).append(o)
    final = []
    for (mats, ns), lst in groups.items():
        # ensure same colour attributes across the group
        names = set()
        for o in lst:
            names |= {a.name for a in o.data.color_attributes}
        for o in lst:
            for nm in names:
                if o.data.color_attributes.get(nm) is None:
                    a = o.data.color_attributes.new(nm, 'BYTE_COLOR', 'CORNER')
                    a.data.foreach_set('color', np.ones(len(a.data) * 4, np.float32))
        nm = ('set_' + '_'.join(m.replace('M_', '') for m in mats))[:48] + ('_noshadow' if ns else '')
        j = dj.join(lst, nm)
        final.append(j)
    for o in anims:
        o.data.name = o.name
        final.append(o)
    for o in final:
        for m in o.data.materials:
            if m:
                _retarget_uv(m)
        for an in ('rest', 'grain', 'pid'):
            a = o.data.attributes.get(an)
            if a is not None:
                o.data.attributes.remove(a)
    # stats
    tris = 0
    per = {}
    for o in final:
        me = o.data
        me.calc_loop_triangles()
        t = len(me.loop_triangles)
        tris += t
        per[o.name] = t
    mats = sorted({m.name for o in final for m in o.data.materials if m})
    log('EXPORT', sid, 'objects', len(final), 'tris', tris, 'materials', len(mats))
    for k, v in sorted(per.items(), key=lambda kv: -kv[1]):
        log('   %-50s %7d' % (k, v))
    # hide LIB from export
    bpy.ops.object.select_all(action='DESELECT')
    for o in final:
        o.select_set(True)
    bpy.context.view_layer.objects.active = final[0]
    path = os.path.join(work_dir(sid), sid + '_src.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials='EXPORT', export_image_format='AUTO', export_cameras=False,
                              export_lights=False, export_extras=False, export_animations=False,
                              export_vertex_color='MATERIAL', export_all_vertex_colors=False)
    stats = {'tris': tris, 'materials': mats, 'objects': {k: v for k, v in per.items()},
             'keep_clear_violations': bad, 'src_glb_kb': os.path.getsize(path) // 1024}
    if run_assets:
        r = subprocess.run([NODE, 'tools/assets.mjs', 'prop', os.path.relpath(path, JB).replace('\\', '/'),
                            f'stages/{sid}.glb', '--tex', str(tex)], cwd=JB, capture_output=True, text=True)
        log(r.stdout.strip(), r.stderr.strip()[-800:])
        out = os.path.join(JB, 'public', 'assets', 'stages', sid + '.glb')
        if os.path.exists(out):
            stats['glb_kb'] = os.path.getsize(out) // 1024
    json.dump(stats, open(os.path.join(work_dir(sid), 'stats.json'), 'w'), indent=1)
    log('export done %.1fs' % (time.time() - t0), stats.get('glb_kb'), 'KB')
    return stats


def write_stage_json(sid, data):
    p = os.path.join(stage_dir(sid), 'stage.json')
    with open(p, 'w') as f:
        json.dump(data, f, indent=2)
    return p
