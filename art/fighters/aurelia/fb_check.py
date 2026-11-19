"""Check a fighter GLB against the brief (plain Python + numpy, no Blender).

  py fb_check.py <file.glb> [--height 2.0]
Reports: meshes/triangles, materials (tint factors, textures), skin joints (all 65 UAL names, extras),
influences per vertex <= 4 and normalised, bounding box (feet on the origin, facing +Z), file size.
Meshopt-compressed GLBs (the game files) are reported by structure only.
"""
import json, struct, sys, os
import numpy as np

UAL = ("root pelvis spine_01 spine_02 spine_03 neck_01 Head clavicle_l upperarm_l lowerarm_l hand_l index_01_l "
       "index_02_l index_03_l index_04_leaf_l middle_01_l middle_02_l middle_03_l middle_04_leaf_l pinky_01_l "
       "pinky_02_l pinky_03_l pinky_04_leaf_l ring_01_l ring_02_l ring_03_l ring_04_leaf_l thumb_01_l thumb_02_l "
       "thumb_03_l thumb_04_leaf_l clavicle_r upperarm_r lowerarm_r hand_r index_01_r index_02_r index_03_r "
       "index_04_leaf_r middle_01_r middle_02_r middle_03_r middle_04_leaf_r pinky_01_r pinky_02_r pinky_03_r "
       "pinky_04_leaf_r ring_01_r ring_02_r ring_03_r ring_04_leaf_r thumb_01_r thumb_02_r thumb_03_r "
       "thumb_04_leaf_r thigh_l calf_l foot_l ball_l ball_leaf_l thigh_r calf_r foot_r ball_r ball_leaf_r").split()
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load(path):
    b = open(path, 'rb').read()
    off = 12
    js, binc = None, b''
    while off < len(b):
        ln, typ = struct.unpack('<II', b[off:off + 8])
        chunk = b[off + 8:off + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(chunk)
        else:
            binc = chunk
        off += 8 + ln
    return js, binc


def acc(js, binc, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    n = NC[a['type']]
    dt = CT[a['componentType']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)
    isz = np.dtype(dt).itemsize
    if stride and stride != n * isz:
        raw = np.frombuffer(binc, np.uint8, count=stride * a['count'], offset=start).reshape(a['count'], stride)
        arr = raw[:, :n * isz].copy().view(dt).reshape(a['count'], n)
    else:
        arr = np.frombuffer(binc, dt, count=a['count'] * n, offset=start).reshape(a['count'], n)
    if a.get('normalized') and dt != np.float32:
        arr = arr.astype(np.float32) / np.iinfo(dt).max
    return arr


def main():
    path = sys.argv[1]
    js, binc = load(path)
    ok = True
    print('file', path, '%.2f MB' % (os.path.getsize(path) / 1e6))
    comp = 'EXT_meshopt_compression' in js.get('extensionsUsed', [])
    tris_total = 0
    for m in js['meshes']:
        t = 0
        for p in m['primitives']:
            if 'indices' in p:
                t += js['accessors'][p['indices']]['count'] // 3
        tris_total += t
        print('  mesh %-22s tris %6d  materials %s' % (m['name'], t, [js['materials'][p['material']]['name'] for p in m['primitives']]))
    print('triangles', tris_total, 'OK' if 20000 <= tris_total <= 45000 else 'OUT OF BUDGET')
    ok &= 20000 <= tris_total <= 45000
    mats = js['materials']
    print('materials', len(mats), 'OK' if len(mats) <= 6 else 'TOO MANY')
    ok &= len(mats) <= 6
    for m in mats:
        pbr = m.get('pbrMetallicRoughness', {})
        maps = [k for k in ('baseColorTexture', 'metallicRoughnessTexture') if k in pbr]
        maps += [k for k in ('normalTexture', 'occlusionTexture', 'emissiveTexture') if k in m]
        es = m.get('extensions', {}).get('KHR_materials_emissive_strength', {}).get('emissiveStrength')
        print('  %-14s factor %s maps %s emissive %s strength %s' % (m['name'], [round(x, 3) for x in pbr.get('baseColorFactor', [1, 1, 1, 1])],
                                                                  maps, m.get('emissiveFactor'), es))
        if m['name'].startswith('tint') and pbr.get('baseColorFactor', [1, 1, 1, 1])[:3] == [1, 1, 1]:
            print('    WARNING tint material without a base colour factor')
    for im in js.get('images', []):
        print('  image', im.get('name'), im.get('mimeType'))
    skin = js['skins'][0]
    names = [js['nodes'][j]['name'] for j in skin['joints']]
    missing = [n for n in UAL if n not in names]
    extra = [n for n in names if n not in UAL]
    print('joints', len(names), 'missing UAL', missing or 'none', 'extra', extra)
    ok &= not missing
    if not comp:
        lo = np.array([1e9] * 3)
        hi = -lo
        maxinf, badsum = 0, 0
        for node in js['nodes']:
            if 'mesh' not in node:
                continue
            for p in js['meshes'][node['mesh']]['primitives']:
                pos = acc(js, binc, p['attributes']['POSITION'])
                lo = np.minimum(lo, pos.min(0))
                hi = np.maximum(hi, pos.max(0))
                if 'WEIGHTS_0' in p['attributes']:
                    w = acc(js, binc, p['attributes']['WEIGHTS_0']).astype(np.float64)
                    maxinf = max(maxinf, int((w > 1e-4).sum(1).max()))
                    badsum += int((np.abs(w.sum(1) - 1) > 0.02).sum())
                    if 'WEIGHTS_1' in p['attributes']:
                        maxinf = 8
        print('bbox min', np.round(lo, 3), 'max', np.round(hi, 3), 'height %.3f' % hi[1])
        print('feet on origin', 'OK' if abs(lo[1]) < 0.03 else 'NO (min y %.3f)' % lo[1])
        print('max influences', maxinf, 'OK' if maxinf <= 4 else 'TOO MANY', '| verts with weight sum != 1:', badsum)
        ok &= maxinf <= 4 and badsum == 0
        # facing: the nose / toes should be at +Z: compare the z extent in front of and behind the centre
        print('depth extent  +Z %.3f  -Z %.3f' % (hi[2], -lo[2]))
    print('CHECK', 'OK' if ok else 'FAILED')


if __name__ == '__main__':
    main()
