"""Tileable texture generation in numpy (runs inside Blender's Python; no PIL needed).

Arrays are indexed [v, u] with v = 0 at the BOTTOM (Blender image pixel order), so UV space and array space agree.
Every generator wraps at the edges, so the results tile seamlessly.
"""
import math
import numpy as np

try:
    import bpy
except ImportError:  # pragma: no cover
    bpy = None


# ----------------------------------------------------------------------------- colour
def s2l(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(np.asarray(c, np.float32), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def gmap(t, stops):
    """Gradient map: t (HxW, 0..1) through stops [(pos, '#hex'), ...] -> sRGB HxWx3 (interpolated in linear)."""
    t = np.clip(t, 0, 1)
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.stack([s2l(hexrgb(c)) for _, c in stops])
    out = np.empty(t.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(t, pos, cols[:, k])
    return l2s(out)


def mix(a, b, f):
    f = np.asarray(f, np.float32)
    if f.ndim == a.ndim - 1:
        f = f[..., None]
    return a * (1 - f) + b * f


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------- noise
def _grid(n):
    v, u = np.mgrid[0:n, 0:n].astype(np.float32)
    return (u + 0.5) / n, (v + 0.5) / n


def sample(arr, u, v):
    """Bilinear sample of a tileable HxW array at UV (any shape, wraps)."""
    h, w = arr.shape[:2]
    x = (np.asarray(u) % 1.0) * w - 0.5
    y = (np.asarray(v) % 1.0) * h - 0.5
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0).astype(np.float32)
    fy = (y - y0).astype(np.float32)
    x0 %= w
    y0 %= h
    x1 = (x0 + 1) % w
    y1 = (y0 + 1) % h
    if arr.ndim == 3:
        fx = fx[..., None]
        fy = fy[..., None]
    a = arr[y0, x0] * (1 - fx) + arr[y0, x1] * fx
    b = arr[y1, x0] * (1 - fx) + arr[y1, x1] * fx
    return a * (1 - fy) + b * fy


def value_noise(n, cells, seed=0, cells_v=None):
    """Smooth tileable value noise in [0,1], `cells` lattice cells across (cells_v vertically)."""
    cv = cells_v or cells
    r = np.random.default_rng(seed)
    lat = r.random((cv, cells)).astype(np.float32)
    u, v = _grid(n)
    x = u * cells
    y = v * cv
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = x - x0
    fy = y - y0
    fx = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    fy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    x0 %= cells
    y0 %= cv
    x1 = (x0 + 1) % cells
    y1 = (y0 + 1) % cv
    a = lat[y0, x0] * (1 - fx) + lat[y0, x1] * fx
    b = lat[y1, x0] * (1 - fx) + lat[y1, x1] * fx
    return a * (1 - fy) + b * fy


def fbm(n, cells=4, octaves=5, gain=0.5, seed=0, cells_v=None):
    tot = np.zeros((n, n), np.float32)
    amp, norm = 1.0, 0.0
    c, cv = cells, (cells_v or cells)
    for o in range(octaves):
        if c > n // 2:
            break
        tot += value_noise(n, c, seed + o * 101, cv) * amp
        norm += amp
        amp *= gain
        c *= 2
        cv *= 2
    return tot / norm


def ridged(n, cells=4, octaves=5, gain=0.5, seed=0):
    tot = np.zeros((n, n), np.float32)
    amp, norm, c = 1.0, 0.0, cells
    for o in range(octaves):
        if c > n // 2:
            break
        v = 1.0 - np.abs(value_noise(n, c, seed + o * 77) * 2 - 1)
        tot += v * v * amp
        norm += amp
        amp *= gain
        c *= 2
    return tot / norm


def warp_fbm(n, cells=4, octaves=5, seed=0, amt=0.08):
    """Domain-warped fbm (marbled, organic)."""
    wx = fbm(n, cells, 4, seed=seed + 11)
    wy = fbm(n, cells, 4, seed=seed + 23)
    base = fbm(n, cells, octaves, seed=seed)
    u, v = _grid(n)
    return sample(base, u + (wx - 0.5) * amt * 2, v + (wy - 0.5) * amt * 2)


def worley(n, cells, seed=0, jitter=0.85, cells_v=None, metric='euclid'):
    """Tileable cellular noise. Returns F1, F2 (in cell units), cell id (0..1 random per cell), nearest-point offset."""
    cv = cells_v or cells
    r = np.random.default_rng(seed)
    pts = (0.5 + (r.random((cv, cells, 2)) - 0.5) * jitter).astype(np.float32)
    ids = r.random((cv, cells)).astype(np.float32)
    u, v = _grid(n)
    x = u * cells
    y = v * cv
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    f1 = np.full((n, n), 9.0, np.float32)
    f2 = np.full((n, n), 9.0, np.float32)
    cid = np.zeros((n, n), np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx = (xi + dx)
            cy = (yi + dy)
            px = pts[cy % cv, cx % cells, 0] + cx
            py = pts[cy % cv, cx % cells, 1] + cy
            if metric == 'manhattan':
                d = np.abs(px - x) + np.abs(py - y)
            elif metric == 'cheb':
                d = np.maximum(np.abs(px - x), np.abs(py - y))
            else:
                d = np.sqrt((px - x) ** 2 + (py - y) ** 2)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, ids[cy % cv, cx % cells], cid)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid


def bricks(n, cols, rows, offset=0.5, mortar=0.04, seed=0, jitter=0.0):
    """Running-bond bricks. Returns (edge distance in brick-height units, brick id 0..1, local u 0..1, local v 0..1)."""
    r = np.random.default_rng(seed)
    u, v = _grid(n)
    y = v * rows
    row = np.floor(y).astype(np.int64)
    x = u * cols + (row % 2) * offset * 1.0
    if jitter:
        sh = r.random(rows).astype(np.float32) * jitter
        x = x + sh[row % rows]
    col = np.floor(x).astype(np.int64)
    lx = x - col
    ly = y - row
    ids = r.random((rows, cols * 2 + 2)).astype(np.float32)
    bid = ids[row % rows, col % (cols)]
    aspect = (1.0 / cols) / (1.0 / rows)  # brick width / height in UV units (for square textures)
    dx = np.minimum(lx, 1 - lx) * aspect
    dy = np.minimum(ly, 1 - ly)
    d = np.minimum(dx, dy)
    return d, bid, lx, ly


def normal_from_height(h, strength=4.0):
    """OpenGL tangent-space normal map (RGB 0..1) from a tileable height field (units: texture = 1)."""
    n = h.shape[0]
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * n / 512.0
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * n / 512.0
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], -1).astype(np.float32)


def blur(a, r=2):
    """Cheap tileable box blur (repeated) for soft masks."""
    out = a.astype(np.float32)
    for _ in range(2):
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            acc += np.roll(out, k, axis=1)
        out = acc / (2 * r + 1)
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            acc += np.roll(out, k, axis=0)
        out = acc / (2 * r + 1)
    return out


def resize(a, n):
    """Nearest-ish resample of a square array to n x n (bilinear via sample)."""
    u, v = _grid(n)
    return sample(a, u, v)


# ----------------------------------------------------------------------------- image IO (Blender)
def save_png(arr, path, srgb=True):
    """arr: HxW (grey) or HxWx3/4 in 0..1 (already in the target colour space). Saves an 8-bit PNG."""
    a = np.asarray(arr, np.float32)
    if a.ndim == 2:
        a = np.stack([a, a, a], -1)
    h, w = a.shape[:2]
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones((h, w, 1), np.float32)], -1)
    name = '_tg_' + str(abs(hash(path)) % 10 ** 8)
    im = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    im.pixels.foreach_set(np.clip(a, 0, 1).ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    return path


def load_png(path, n=None):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    bpy.data.images.remove(im)
    if n is not None and (w != n or h != n):
        a = np.stack([resize(a[..., k], n) for k in range(4)], -1)
    return a


def lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
