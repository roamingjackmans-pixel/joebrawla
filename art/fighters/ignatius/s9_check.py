"""Stage 9: validate the source GLB (pure python): meshes/tris, materials, images, skin joints vs Quaternius UAL1
(names, hierarchy, local rest rotations), influences / weight sums, rest-pose height and foot level, hand_r-only prop.
blender -b --factory-startup --python s9_check.py      (or any python 3)   [path.glb]
"""
import json, struct, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FID = os.path.basename(HERE)
GLB = sys.argv[-1] if sys.argv[-1].endswith(".glb") else os.path.join(HERE, "..", "..", "_work", FID, FID + "_src.glb")
REF = r"C:\dev\AverageJoe\_downloads\quaternius-ual1\x\Universal Animation Library[Standard]\Unreal-Godot\UAL1_Standard.glb"
COMP = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load(p):
    d = open(p, 'rb').read()
    off, js, b = 12, None, b''
    while off < len(d):
        n, t = struct.unpack_from('<II', d, off)
        c = d[off + 8: off + 8 + n]
        if t == 0x4E4F534A:
            js = json.loads(c.decode())
        else:
            b = c
        off += 8 + n
    return js, b


def acc(js, b, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    f, s = COMP[a['componentType']]
    n = NC[a['type']]
    st = bv.get('byteStride', s * n)
    base = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    out = []
    for k in range(a['count']):
        v = struct.unpack_from('<' + f * n, b, base + k * st)
        if a.get('normalized') and f in 'BH':
            v = tuple(x / (255.0 if f == 'B' else 65535.0) for x in v)
        out.append(v)
    return out


js, b = load(GLB)
nodes = js['nodes']
print("CHECK", os.path.abspath(GLB), os.path.getsize(GLB) // 1024, "KB")
tot = 0
for m in js['meshes']:
    t = sum(js['accessors'][p['indices']]['count'] // 3 for p in m['primitives'])
    tot += t
    mats = [js['materials'][p['material']]['name'] for p in m['primitives'] if 'material' in p]
    print("CHECK mesh %-20s tris %6d  materials %s" % (m['name'], t, mats))
print("CHECK total tris %d (budget 20-45k)  materials %d (max 6)" % (tot, len(js['materials'])))
for mt in js['materials']:
    pbr = mt.get('pbrMetallicRoughness', {})
    print("CHECK material %-18s baseColorFactor=%s emissive=%s strength=%s tex=%s" % (
        mt['name'], [round(x, 3) for x in pbr.get('baseColorFactor', [1, 1, 1, 1])], mt.get('emissiveFactor'),
        mt.get('extensions', {}).get('KHR_materials_emissive_strength', {}).get('emissiveStrength'),
        sorted(k for k in list(pbr.keys()) + list(mt.keys()) if k.endswith('Texture'))))
for im in js.get('images', []):
    print("CHECK image %s" % im.get('name'))
# skeleton vs UAL1
rjs, rb = load(REF)
sk = js['skins'][0]
names = [nodes[j]['name'] for j in sk['joints']]
rsk = rjs['skins'][0]
rnames = [rjs['nodes'][j]['name'] for j in rsk['joints']]
print("CHECK joints %d (UAL1 %d) missing %s extra %s" % (len(names), len(rnames), sorted(set(rnames) - set(names)),
                                                          sorted(set(names) - set(rnames))))
rn = {n['name']: n for n in rjs['nodes']}
mdr = 0.0
moved = []
for nm, j in zip(names, sk['joints']):
    A, B = nodes[j], rn[nm]
    ra, rb_ = A.get('rotation', [0, 0, 0, 1]), B.get('rotation', [0, 0, 0, 1])
    mdr = max(mdr, math.degrees(2 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(ra, rb_)))))))
    ta, tb = A.get('translation', [0, 0, 0]), B.get('translation', [0, 0, 0])
    if max(abs(x - y) for x, y in zip(ta, tb)) > 1e-4:
        moved.append(nm)


def parents(j):
    p = {}
    for n in j['nodes']:
        for c in n.get('children', []):
            p[j['nodes'][c]['name']] = n['name']
    return p


pa, pb = parents(js), parents(rjs)
print("CHECK joint rest rotation vs UAL1: max %.4f deg; hierarchy mismatches %s" % (mdr, [n for n in rnames if pa.get(n) != pb.get(n)]))
print("CHECK joints with edited rest translation (%d): %s" % (len(moved), " ".join(moved)))
arm = [n for n in nodes if n['name'] == 'Armature']
S = arm[0].get('scale', [1, 1, 1]) if arm else [1, 1, 1]
print("CHECK Armature node scale %s rotation %s" % ([round(x, 4) for x in S], arm[0].get('rotation') if arm else None))
ymin, ymax = 1e9, -1e9
for m in js['meshes']:
    for p in m['primitives']:
        a = js['accessors'][p['attributes']['POSITION']]
        ymin, ymax = min(ymin, a['min'][1]), max(ymax, a['max'][1])
        W = acc(js, b, p['attributes']['WEIGHTS_0'])
        Jn = acc(js, b, p['attributes']['JOINTS_0'])
        worst = max(abs(1 - sum(w)) for w in W)
        mx = max(sum(1 for x in w if x > 1e-4) for w in W)
        used = sorted({names[jj] for w, jv in zip(W, Jn) for x, jj in zip(w, jv) if x > 1e-4})
        print("CHECK skin %-20s verts %d max influences %d worst |1-sum| %.5f joints used %d %s" % (
            m['name'], len(W), mx, worst, len(used), "(100%% %s)" % used[0] if len(used) == 1 else ""))
print("CHECK rest height: mesh y %.3f .. %.3f (model units) x node scale %.4f = %.3f .. %.3f m" % (
    ymin, ymax, S[1], ymin * S[1], ymax * S[1]))
