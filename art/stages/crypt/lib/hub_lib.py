"""Shared helpers for The Landing (hub) art: wraps the props pipeline (tools/blender/props/dj_common.py, dj_mats.py)
with hub output folders, JPEG textures inside the GLBs, extra stroke glyphs, rough stone blocks and ivy.

Run any hub script headless:
    blender.exe -b --factory-startup --python tools/blender/hub/<script>.py -- [asset names] [--no-preview]
"""
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, noise as mnoise
import dj_common as dj
import dj_mats as mats

ROOT = dj.ROOT
HUB = os.path.join(ROOT, 'art', '_work', 'stages', '_hub')
PREV = os.path.join(HUB, 'previews')
WORK = os.path.join(HUB, '_work')
for _d in (HUB, PREV, WORK):
    os.makedirs(_d, exist_ok=True)
dj.PREV_DIR = os.path.join(WORK, 'asset_previews')
os.makedirs(dj.PREV_DIR, exist_ok=True)


def set_out(sub):
    d = os.path.join(HUB, sub)
    os.makedirs(d, exist_ok=True)
    dj.OUT_DIR = d
    return d


def _export_glb_jpeg(objs, name):
    """Same as dj.export_glb, but textures are stored as JPEG (keeps the LFS footprint down)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    path = os.path.join(dj.OUT_DIR, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_texcoords=True, export_normals=True, export_tangents=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=88,
                              export_cameras=False, export_lights=False, export_extras=False,
                              export_animations=False, export_attributes=False)
    return path


dj.export_glb = _export_glb_jpeg


def args():
    return [a for a in dj.script_args() if not a.startswith('--')]


def want(name, names):
    return not names or name in names


# ----------------------------------------------------------------------------- glyphs for engraved / painted text
_G = dj._GLYPHS
_G.update({
    'B': [[(0.2, 0), (0.2, 1), (0.62, 1), (0.78, 0.88), (0.78, 0.66), (0.62, 0.54), (0.2, 0.54)],
          [(0.62, 0.54), (0.82, 0.42), (0.82, 0.14), (0.64, 0), (0.2, 0)]],
    'C': [[(0.85, 0.85), (0.65, 1), (0.35, 1), (0.15, 0.8), (0.15, 0.2), (0.35, 0), (0.65, 0), (0.85, 0.15)]],
    'D': [[(0.2, 0), (0.2, 1), (0.55, 1), (0.82, 0.78), (0.82, 0.22), (0.55, 0), (0.2, 0)]],
    'G': [[(0.85, 0.85), (0.65, 1), (0.35, 1), (0.15, 0.8), (0.15, 0.2), (0.35, 0), (0.65, 0), (0.85, 0.18), (0.85, 0.45), (0.55, 0.45)]],
    'L': [[(0.2, 1), (0.2, 0), (0.8, 0)]],
    'M': [[(0.12, 0), (0.12, 1), (0.5, 0.45), (0.88, 1), (0.88, 0)]],
    'T': [[(0.1, 1), (0.9, 1)], [(0.5, 1), (0.5, 0)]],
    'S': [[(0.82, 0.86), (0.62, 1), (0.36, 1), (0.18, 0.84), (0.2, 0.62), (0.4, 0.52), (0.64, 0.48), (0.82, 0.36), (0.82, 0.14), (0.62, 0), (0.34, 0), (0.15, 0.14)]],
    'U': [[(0.18, 1), (0.18, 0.25), (0.35, 0), (0.65, 0), (0.82, 0.25), (0.82, 1)]],
    'W': [[(0.08, 1), (0.28, 0), (0.5, 0.65), (0.72, 0), (0.92, 1)]],
    'Y': [[(0.12, 1), (0.5, 0.5), (0.88, 1)], [(0.5, 0.5), (0.5, 0)]],
    'K': [[(0.2, 0), (0.2, 1)], [(0.82, 1), (0.2, 0.42)], [(0.4, 0.58), (0.85, 0)]],
    'V': [[(0.1, 1), (0.5, 0), (0.9, 1)]],
    'H': [[(0.18, 0), (0.18, 1)], [(0.82, 0), (0.82, 1)], [(0.18, 0.52), (0.82, 0.52)]],
    'F': [[(0.82, 1), (0.2, 1), (0.2, 0)], [(0.2, 0.52), (0.65, 0.52)]],
    '1': [[(0.32, 0.8), (0.55, 1), (0.55, 0)], [(0.3, 0), (0.8, 0)]],
    '2': [[(0.18, 0.8), (0.35, 1), (0.65, 1), (0.82, 0.8), (0.82, 0.6), (0.18, 0), (0.85, 0)]],
    '3': [[(0.18, 0.88), (0.38, 1), (0.66, 1), (0.82, 0.84), (0.8, 0.62), (0.55, 0.52), (0.82, 0.4), (0.84, 0.16), (0.65, 0), (0.36, 0), (0.16, 0.12)]],
    '4': [[(0.7, 0), (0.7, 1), (0.15, 0.32), (0.88, 0.32)]],
    '5': [[(0.82, 1), (0.25, 1), (0.2, 0.55), (0.55, 0.62), (0.8, 0.45), (0.82, 0.18), (0.62, 0), (0.35, 0), (0.15, 0.12)]],
    '6': [[(0.8, 0.92), (0.6, 1), (0.36, 1), (0.18, 0.75), (0.18, 0.22), (0.36, 0), (0.64, 0), (0.82, 0.2), (0.82, 0.42), (0.62, 0.58), (0.36, 0.58), (0.18, 0.4)]],
    '7': [[(0.15, 1), (0.85, 1), (0.42, 0)]],
    '8': [[(0.5, 0.54), (0.24, 0.66), (0.22, 0.88), (0.38, 1), (0.62, 1), (0.78, 0.88), (0.76, 0.66), (0.5, 0.54), (0.2, 0.4), (0.18, 0.14), (0.36, 0), (0.64, 0), (0.82, 0.14), (0.8, 0.4), (0.5, 0.54)]],
    '9': [[(0.82, 0.6), (0.64, 0.42), (0.36, 0.42), (0.18, 0.6), (0.18, 0.82), (0.36, 1), (0.64, 1), (0.82, 0.8), (0.82, 0.22), (0.62, 0), (0.36, 0), (0.2, 0.08)]],
    '0': [[(0.5 + 0.34 * math.cos(2 * math.pi * i / 14), 0.5 + 0.5 * math.sin(2 * math.pi * i / 14)) for i in range(15)]],
    "'": [[(0.5, 1.0), (0.45, 0.72)]],
})


def text_image(name, lines, w, h, res=512, stroke=0.12):
    """lines: list of (text, cx, baseline_y, cap_h) in a w x h (metres) box -> stroke image."""
    st = []
    for (t, cx, y, ch) in lines:
        st += dj.text_strokes(t, cx, y, ch, width_frac=stroke)
    return dj.stroke_image(name, w, h, st, res=res)


# ----------------------------------------------------------------------------- geometry helpers
def box_span(name, x0, x1, y0, y1, z0, z1, mat, bev=0.03, segs=2, cuts=0):
    b = dj.box(name, x1 - x0, y1 - y0, z1 - z0, loc=((x0 + x1) / 2, (y0 + y1) / 2, z0), mat=mat, cuts=cuts)
    if bev > 0:
        dj.bevel(b, bev, segs, 35)
    return b


def rough_block(R, name, sx, sy, sz, loc, mat, bev=0.04, warp=0.1, lean=2.0, segs=1, cuts=1):
    b = dj.box(name, sx, sy, sz, loc=loc, mat=mat, cuts=cuts)
    if bev > 0:
        dj.bevel(b, min(bev, sx * 0.3, sy * 0.3, sz * 0.3), segs, 35)
    dj.warp(b, min(sx, sy, sz) * warp, 2.6, seed=R.randint(0, 9999))
    if lean:
        dj.lean(b, rx=R.uniform(-lean, lean), ry=R.uniform(-lean, lean), rz=R.uniform(-lean * 1.3, lean * 1.3), pivot=loc)
    return b


def rubble(R, n, x0, x1, y0, y1, z, mat, smin=0.08, smax=0.22, name='rub'):
    out = []
    for i in range(n):
        s = R.uniform(smin, smax)
        c = dj.ico(name, s, 1, loc=(R.uniform(x0, x1), R.uniform(y0, y1), z + s * 0.25),
                   scale=(R.uniform(1.0, 1.5), R.uniform(0.8, 1.2), R.uniform(0.55, 0.8)), mat=mat)
        dj.warp(c, s * 0.25, 4.0, seed=R.randint(0, 999))
        out.append(c)
    return out


def moss_pads(R, n, x0, x1, y0, y1, z, mat, rmin=0.12, rmax=0.3, hmin=0.04, hmax=0.09):
    return [dj.cushion('moss', R.uniform(rmin, rmax), R.uniform(hmin, hmax), (R.uniform(x0, x1), R.uniform(y0, y1), z), mat,
                       seed=R.randint(0, 999)) for _ in range(n)]


def leaves_bm(R, pts, out_dir, mat, per=3, size=(0.06, 0.11), spread=0.12, name='leaves'):
    """Ivy leaves (small pyramids, as the mausoleum ivy) along points, all in ONE mesh (fast)."""
    bm = bmesh.new()
    pidl = bm.faces.layers.float.new('pid') if False else None
    od = Vector(out_dir).normalized()
    for p in pts:
        p = Vector(p)
        for _ in range(per):
            o = p + Vector((R.uniform(-spread, spread), R.uniform(-spread, spread), R.uniform(-spread * 0.8, spread * 0.8))) + od * 0.04
            nrm = (od + Vector((R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), R.uniform(-0.2, 0.8)))).normalized()
            sz = R.uniform(*size)
            tang = nrm.cross(Vector((0, 0, 1)))
            if tang.length < 1e-3:
                tang = Vector((1, 0, 0))
            tang.normalize()
            tang = Matrix.Rotation(R.uniform(-0.8, 0.8), 3, nrm) @ tang
            bit = nrm.cross(tang).normalized()
            tip = -bit
            c0 = bm.verts.new(o + tip * sz * 0.9)
            c1 = bm.verts.new(o + tang * sz * 0.5)
            c2 = bm.verts.new(o - tip * sz * 0.35)
            c3 = bm.verts.new(o - tang * sz * 0.5)
            cc = bm.verts.new(o + nrm * sz * 0.18)
            for a_, b_ in ((c0, c1), (c1, c2), (c2, c3), (c3, c0)):
                bm.faces.new((a_, b_, cc))
    ob = dj.mesh_obj(name, bm, mat)
    dj.pid(ob, R.random())
    return ob


def smooth_path(pts, n=5, wob=0.03, seed=0):
    pts = [Vector(p) for p in pts]
    out = []
    off = Vector((seed * 1.7, seed * 0.3, seed * 2.1))
    for a, b in zip(pts[:-1], pts[1:]):
        for i in range(n):
            p = a.lerp(b, i / n)
            p += Vector((mnoise.noise(p * 3.0 + off) * wob, mnoise.noise(p * 3.0 + off + Vector((5, 0, 0))) * wob, 0))
            out.append(p)
    out.append(pts[-1])
    return out


def ivy(R, paths, out_dir, leaf_mat, stem_mat, per=3, size=(0.07, 0.12)):
    """Ivy runs: list of point lists -> [stems..., leaves]."""
    P = []
    allpts = []
    for i, br in enumerate(paths):
        sp = smooth_path(br, 4, seed=R.randint(0, 99))
        s = dj.tube('ivystem', sp, 0.016, 4, stem_mat, cap=True)
        dj.grain(s, (0, 0, 1))
        P.append(s)
        allpts += sp
    P.append(leaves_bm(R, allpts, out_dir, leaf_mat, per=per, size=size))
    return P


def hanging_ivy(R, x0, x1, ztop, y, depth_range=(0.6, 2.2), n=5, out=(0, -1, 0)):
    """Paths hanging down a wall face from ztop between x0 and x1 at face y."""
    paths = []
    for i in range(n):
        x = R.uniform(x0, x1)
        L = R.uniform(*depth_range)
        k = max(3, int(L / 0.3))
        paths.append([(x + R.uniform(-0.12, 0.12) * j / k, y + out[1] * 0.02, ztop - L * j / k) for j in range(k + 1)])
    return paths


# ----------------------------------------------------------------------------- materials used across the hub
def hub_stone(name, seed=0, moss=0.45, blocks=(0.62, 0.34, 0.016), **kw):
    kw.setdefault('base', '#7c8573')
    kw.setdefault('light', '#a3a892')
    kw.setdefault('warm', '#b9ae8a')
    kw.setdefault('dark', '#3a4234')
    return mats.stone(name, seed=seed, moss=moss, blocks=blocks, **kw)


def finish(objs, name, tex=1024, **kw):
    kw.setdefault('ao_dist', 0.6)
    return dj.finish(objs, name, tex=tex, **kw)
