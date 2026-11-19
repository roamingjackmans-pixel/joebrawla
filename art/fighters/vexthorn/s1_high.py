"""Stage 1: sculpt every part as an SDF, polygonise (surface nets), smooth, displace -> _work/<id>/high_<part>.npz
blender -b --factory-startup --python s1_high.py -- [part names...]
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fblib as L
L.load_joints()
import parts as PT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ps = PT.all_parts()
if argv:
    ps = [p for p in ps if p.name in argv]
for p in ps:
    t0 = time.time()
    g = L.SDFGrid(p.lo, p.hi, p.h)
    p.build(g)
    t1 = time.time()
    V, Q = g.mesh()
    del g
    E = L.mesh_edges(Q)
    V = L.taubin(V, E, iters=p.smooth_iters)
    N = L.vnormals(V, Q)
    V = p.post(V, N).astype(np.float32)
    N = L.vnormals(V, Q)
    C = L.curvature(V, Q, E, N, smooth=2)
    np.savez(os.path.join(L.WORK, "high_%s.npz" % p.name), V=V, Q=Q, C=C)
    print("PART %-10s verts=%d quads=%d  sculpt %.1fs  mesh %.1fs" % (p.name, len(V), len(Q), t1 - t0, time.time() - t1))
