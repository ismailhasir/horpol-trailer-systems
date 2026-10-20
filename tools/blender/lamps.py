# Horpol lamba ürünlerinin fotorealistik 3D modelleri (konfigüratör + ürün simgeleri). Her ürün ayrı GLB.
# Ölçüler üreticinin teknik çizimlerinden (zip arşivleri / horpolautomotive.com); biçim ve ışık desenleri ürün fotoğraflarından.
# Belge: docs/Lambalar/README.md
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/lamps.py -- [--only lzd3194,ld2774] [--preview <klasör>] [--icons] [--fast]
#   ardından: npm run models:pack -- lamp
#
# Lamba yerel koordinatları (three.js düzeni, metre): lens +Z'ye bakar (dışarı), X genişlik, Y yukarı; montaj yüzeyi z = 0.
#   Arka lamba: +X = arkadan bakana göre sağ (sol lamba için dış uç -X). Sağ lamba sitede x aynalanır.
#   Lastik kol (rubber arm): taban plakası duvarda (z = 0), kol +Z yönünde dışarı uzanır; kafada beyaz lens -X'e (öne),
#   kırmızı lens +X'e (arkaya), turuncu lens +Z'ye (yana) bakar. Diğer yan sitede z aynalanır.
#   Tepe lambası (beacon): taban y = 0'da yatay yüzeyde, kubbe +Y.
# Düğüm adları (sitenin okuduğu sözleşme):
#   BODY  : opak gövde, braket, vida, kablo (çok malzemeli)
#   INNER : opak iç parçalar (krom reflektör, LED yuvası, reflektör deseni)
#   EMIT.<işlev> : ışık veren parçalar; malzeme adı "E.<işlev>.<renk>" (site yanınca emissive'i bu renkle açar)
#   LENS  : şeffaf renkli dış lens (alfa karışımı)
# İşlevler: position, stop, turn, reverse, fog, marker, front, outline, plate, work, beacon
import bpy
import bmesh
import math
import os
import sys

import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in argv
ONLY = argv[argv.index('--only') + 1].split(',') if '--only' in argv else None
PREVIEW = os.path.abspath(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
ICONS = '--icons' in argv
RAW_DIR = os.path.abspath('tools/blender/out')
ICON_DIR = os.path.abspath('src/assets/lamps')

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import bl, srgb  # noqa: E402

scene = bpy.context.scene

# =====================================================================
# Geometri yardımcıları (three koordinatı; bl() Blender'a çevirir)
# =====================================================================


class Group:
    def __init__(self, name):
        self.name = name
        self.objs = []


def _obj(name, bm, mat, group, bevel=0.0, seg=3, angle=35, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    me.materials.append(mat)
    if bevel > 0:
        md = ob.modifiers.new('bevel', 'BEVEL')
        md.width = bevel
        md.segments = seg
        md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(30)
        md.harden_normals = True
        md.use_clamp_overlap = True
    else:
        me.set_sharp_from_angle(angle=math.radians(angle))
    group.objs.append(ob)
    return ob


def rrect(w, h, r, n=6, cx=0.0, cy=0.0):
    """Köşeleri yuvarlatılmış dikdörtgen [(x, y)], saat yönü tersine"""
    r = min(r, w / 2 - 1e-5, h / 2 - 1e-5)
    pts = []
    for (qx, qy, a0) in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a)))
    return pts


def chamfer_rect(w, h, c, cx=0.0, cy=0.0):
    """Köşeleri pahlı dikdörtgen (sekizgen pencere)"""
    x, y = w / 2, h / 2
    return [(cx + p, cy + q) for p, q in ((-x + c, -y), (x - c, -y), (x, -y + c), (x, y - c), (x - c, y), (-x + c, y), (-x, y - c), (-x, -y + c))]


def circle(r, n=48, cx=0.0, cy=0.0):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def stadium(w, h, n=12, cx=0.0, cy=0.0):
    return rrect(w, h, h / 2, n, cx, cy)


def prism(group, name, pts, z0, z1, mat, bevel=0.0, seg=3):
    """XY çokgeni z0..z1 arasında uzatılmış katı (lens yönü +Z)"""
    bm = bmesh.new()
    a = [bm.verts.new(bl((x, y, z0))) for x, y in pts]
    b = [bm.verts.new(bl((x, y, z1))) for x, y in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, group, bevel, seg)


def frame(group, name, outer, inner, z0, z1, mat, bevel=0.0, seg=3):
    """Çerçeve: dış ve iç çokgen (aynı nokta sayısı) arası halka, z0..z1"""
    assert len(outer) == len(inner)
    bm = bmesh.new()
    n = len(outer)
    oa = [bm.verts.new(bl((x, y, z0))) for x, y in outer]
    ob_ = [bm.verts.new(bl((x, y, z1))) for x, y in outer]
    ia = [bm.verts.new(bl((x, y, z0))) for x, y in inner]
    ib = [bm.verts.new(bl((x, y, z1))) for x, y in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([oa[i], oa[j], ob_[j], ob_[i]])
        bm.faces.new([ib[i], ib[j], ia[j], ia[i]])
        bm.faces.new([ob_[i], ob_[j], ib[j], ib[i]])
        bm.faces.new([ia[i], ia[j], oa[j], oa[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, group, bevel, seg)


def offset(pts, d):
    """Kapalı çokgeni d kadar içe (+) / dışa (-) kaydırır (köşe açıortayı; dışbükeye yakın biçimler için)"""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1 = math.hypot(*e1) or 1e-9
        l2 = math.hypot(*e2) or 1e-9
        n1 = (-e1[1] / l1 * s, e1[0] / l1 * s)
        n2 = (-e2[1] / l2 * s, e2[0] / l2 * s)
        b = (n1[0] + n2[0], n1[1] + n2[1])
        bl_ = math.hypot(*b) or 1e-9
        cos = max(0.3, (n1[0] * n2[0] + n1[1] * n2[1] + 1) / 2) ** 0.5
        k = d / cos
        out.append((p1[0] + b[0] / bl_ * k, p1[1] + b[1] / bl_ * k))
    return out


def cyl(group, name, r, a, b, mat, seg=32, r2=None, caps=True, bevel=0.0):
    A, B = bl(a), bl(b)
    d = B - A
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length)
    q = d.to_track_quat('Z', 'Y')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((A + B) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return _obj(name, bm, mat, group, bevel)


def box(group, name, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
    return prism(group, name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, bevel)


def tube(group, name, pts, r, mat, res=3, smooth=False, caps=True):
    """Nokta dizisi boyunca boru (neon ışık kılavuzu, kablo). smooth: Bezier"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    if smooth:
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = bl(p)
            bp.handle_left_type = bp.handle_right_type = 'AUTO'
    else:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for p, q in zip(sp.points, pts):
            v = bl(q)
            p.co = (v.x, v.y, v.z, 1.0)
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    cu.materials.append(mat)
    group.objs.append(ob)
    return ob


def ribbon(group, name, pts, w, z, mat, t=0.0015):
    """Düz şerit ışık kılavuzu: XY polyline boyunca w genişliğinde, z'de t kalınlığında (neon çizgi)"""
    out, inn = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / ln * w / 2, dx / ln * w / 2
        out.append((x + nx, y + ny))
        inn.append((x - nx, y - ny))
    poly = out + list(reversed(inn))
    return prism(group, name, poly, z - t / 2, z + t / 2, mat, 0.0)


def lathe(group, name, prof, mat, steps=64, axis='z', center=(0, 0, 0)):
    """Profil [(r, h)] döndürme: axis 'z' → lens eksenli (h = z), 'y' → dik (h = y)"""
    bm = bmesh.new()
    if axis == 'z':
        vs = [bm.verts.new(bl((center[0] + r, center[1], center[2] + h))) for r, h in prof]
        ax = bl((0, 0, 1))
    else:
        vs = [bm.verts.new(bl((center[0] + r, center[1] + h, center[2]))) for r, h in prof]
        ax = bl((0, 1, 0))
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=bl(center), axis=ax, angle=math.pi * 2, steps=steps, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, group, 0.0)


def led(groupE, groupI, name, x, y, z, r, matE, matCup=None, cup_r=None, depth=0.004):
    """LED: yayan küçük disk + öne açılan krom reflektör kabı (z: kabın ağzı)"""
    if matCup is not None:
        cr = cup_r or r * 2.6
        cyl(groupI, name + '_cup', r * 1.15, (x, y, z - depth), (x, y, z), matCup, 24, r2=cr, caps=False)
    cyl(groupE, name, r, (x, y, z - depth - 0.0004), (x, y, z - depth + 0.0008), matE, 16)


def cup(groupI, x, y, z, r_front, r_back, depth, mat):
    """Krom reflektör kabı (öne açılan koni)"""
    return cyl(groupI, 'cup', r_back, (x, y, z - depth), (x, y, z), mat, 28, r2=r_front, caps=False)


def set_uv_planar(ob, s, axis='z', off=(0.0, 0.0)):
    """Düzlemsel UV (three ekseni boyunca izdüşüm), s metre = 1 doku"""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co  # Blender: three (x, y, z) = (X, Z, -Y)
            x, y, z = v.x, v.z, -v.y
            if axis == 'z':
                uv[li].uv = (x / s + off[0], y / s + off[1])
            elif axis == 'x':
                uv[li].uv = (z / s + off[0], y / s + off[1])
            else:
                uv[li].uv = (x / s + off[0], z / s + off[1])


def set_uv_cyl(ob, s, center=(0, 0)):
    """Dik eksenli silindirik UV (tepe lambası kubbesi): u = çevre / s, v = y / s"""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            x, y, z = v.x, v.z, -v.y
            a = math.atan2(z - center[1], x - center[0])
            uv[li].uv = (a * 0.06 / s, y / s)


# =====================================================================
# Dokular (numpy, dikişsiz)
# =====================================================================
def np_img(name, arr, non_color=True):
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.ones((h, w), np.float32)])
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.pack()
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    return img


def hex_retro_normal(n=256, cells=4):
    """Köşe küp (cube-corner) reflektör: altıgen hücre, her biri üç eğimli yüz. Döner tanjant uzayı normal haritası."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    s = n / cells
    # altıgen ızgara: eksenel koordinat
    q = (xs * math.sqrt(3) / 3 - ys / 3) / s
    r = ys * 2 / 3 / s
    x, z = q, r
    y = -x - z
    rx, ry, rz = np.round(x), np.round(y), np.round(z)
    dx, dy, dz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
    m1 = (dx > dy) & (dx > dz)
    m2 = (~m1) & (dy > dz)
    rx = np.where(m1, -ry - rz, rx)
    ry = np.where(m2, -rx - rz, ry)
    rz = np.where(~m1 & ~m2, -rx - ry, rz)
    fx, fz = x - rx, z - rz
    fy = -fx - fz
    sector = np.argmax(np.stack([fx, fy, fz]), axis=0)
    tilt = 0.55
    nrm = np.zeros((n, n, 3), np.float32)
    dirs = [(1, 0.3), (-0.5, 0.95), (-0.5, -0.95)]
    for k, (a, b) in enumerate(dirs):
        m = sector == k
        nrm[m, 0] = a * tilt
        nrm[m, 1] = b * tilt * 0.6
    edge = np.clip(1 - np.maximum(np.abs(fx), np.maximum(np.abs(fy), np.abs(fz))) * 3.0, 0, 1)
    nrm[..., 2] = 1.0
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    col = nrm * 0.5 + 0.5
    del edge
    return col


def pillow_normal(n=256, cells=8, k=0.9):
    """Yastık optik (küçük kare kubbeler): lensin içi"""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    s = n / cells
    u = (xs % s) / s - 0.5
    v = (ys % s) / s - 0.5
    nx = -u * k
    ny = -v * k
    nrm = np.dstack([nx, ny, np.ones_like(nx)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return nrm * 0.5 + 0.5


def rib_normal(n=256, ribs=16, k=0.8):
    """Dikey kaburgalar (tepe lambası kubbesi, Fresnel)"""
    xs = (np.arange(n, dtype=np.float32) + 0.5) / n * ribs
    d = np.sin(xs * 2 * math.pi) * k
    nx = np.tile(d, (n, 1))
    nrm = np.dstack([nx, np.zeros_like(nx), np.ones_like(nx)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return nrm * 0.5 + 0.5


def grain_normal(n=256, seed=3, k=0.25):
    """İnce plastik doku (gövde)"""
    rng = np.random.default_rng(seed)
    h = rng.normal(0, 1, (n, n)).astype(np.float32)
    for _ in range(2):
        h = (h + np.roll(h, 1, 0) + np.roll(h, -1, 0) + np.roll(h, 1, 1) + np.roll(h, -1, 1)) / 5
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * k
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * k
    nrm = np.dstack([-gx, -gy, np.ones_like(gx)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return nrm * 0.5 + 0.5


TEX = {}


def tex(kind):
    if kind not in TEX:
        n = 128 if FAST else 256
        arr = {'hex': lambda: hex_retro_normal(n), 'pillow': lambda: pillow_normal(n), 'rib': lambda: rib_normal(n),
               'grain': lambda: grain_normal(n)}[kind]()
        TEX[kind] = np_img('nrm_' + kind, arr)
    return TEX[kind]


# =====================================================================
# Malzemeler
# =====================================================================
MATS = {}
LENS_ALPHA = {'red': 0.32, 'amber': 0.38, 'clear': 0.1, 'smoke': 0.55, 'white': 0.14}
COL = {'red': '#d00a14', 'amber': '#ff8c0a', 'clear': '#f2f4f7', 'white': '#f4f6fa', 'smoke': '#25272b'}
# yanan ışık rengi (lineer, emissive). Kırmızı ve turuncu doygun kalsın diye yeşil/mavi çok düşük.
GLOW = {'red': (1.0, 0.012, 0.006), 'amber': (1.0, 0.30, 0.0), 'white': (0.92, 0.95, 1.0)}
# sönükken ışık kılavuzunun/LED'in rengi (sRGB onaltılık): süt beyazı ışık kılavuzu, kırmızı lensin ardında açık kırmızı okunur
OFF = {'red': '#f3dcd9', 'amber': '#ffd79a', 'white': '#f4f1e6'}


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes['Principled BSDF']


def _normal(m, p, img, strength):
    nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    t.interpolation = 'Linear'
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = strength
    nt.links.new(t.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])


def mat(key):
    """Ortak malzeme kütüphanesi (ad = sitenin tanıdığı anahtar)"""
    if key in MATS:
        return MATS[key]
    kind, _, arg = key.partition('.')
    if kind == 'E':  # E.<işlev>.<renk>
        fn, color = arg.split('.')
        m, p = _principled(key)
        p.inputs['Base Color'].default_value = srgb(OFF[color])
        p.inputs['Roughness'].default_value = 0.35
        p.inputs['Emission Color'].default_value = (*GLOW[color], 1.0)
        p.inputs['Emission Strength'].default_value = 0.0  # sitede yanınca açılır; simgede ayarlanır
        m['fn'] = fn
    elif kind == 'Lens':
        m, p = _principled(key)
        p.inputs['Base Color'].default_value = srgb(COL[arg])
        p.inputs['Roughness'].default_value = 0.04
        p.inputs['Alpha'].default_value = LENS_ALPHA[arg]
        p.inputs['IOR'].default_value = 1.49
        p.inputs['Coat Weight'].default_value = 0.6
        p.inputs['Coat Roughness'].default_value = 0.03
        _normal(m, p, tex('pillow'), 0.18)
        m.blend_method = 'BLEND'
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
        m.use_backface_culling = False
        m['lens'] = arg
    elif kind == 'Dome':  # tepe lambası kubbesi
        m, p = _principled(key)
        p.inputs['Base Color'].default_value = srgb(COL[arg])
        p.inputs['Roughness'].default_value = 0.05
        p.inputs['Alpha'].default_value = 0.62
        p.inputs['Coat Weight'].default_value = 0.5
        _normal(m, p, tex('rib'), 0.6)
        m.blend_method = 'BLEND'
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
        m['lens'] = arg
    elif kind == 'Retro':  # opak köşe küp reflektör
        m, p = _principled(key)
        base = {'red': '#ff3b3f', 'amber': '#ffb04a', 'white': '#f6f7f9'}[arg]
        p.inputs['Base Color'].default_value = srgb(base)
        p.inputs['Roughness'].default_value = 0.3
        p.inputs['Metallic'].default_value = 0.0
        p.inputs['Coat Weight'].default_value = 1.0
        p.inputs['Coat Roughness'].default_value = 0.02
        _normal(m, p, tex('hex'), 0.7)
    else:
        spec = {
            'Housing': ('#141518', 0.52, 0.0, 0.0, 'grain'),
            'HousingGloss': ('#121315', 0.28, 0.0, 0.3, None),
            'Rubber': ('#17181a', 0.78, 0.0, 0.0, 'grain'),
            'Chrome': ('#eef1f4', 0.08, 1.0, 0.0, None),
            'Reflector': ('#eceef0', 0.32, 0.45, 0.0, 'pillow'),
            'ReflectorRed': ('#8a1016', 0.22, 0.75, 0.0, 'pillow'),
            'Ribbed': ('#3a0a0c', 0.35, 0.3, 0.0, 'rib'),
            'Stainless': ('#c9ced3', 0.22, 1.0, 0.0, None),
            'Zinc': ('#a9aeb3', 0.35, 1.0, 0.0, None),
            'Brass': ('#b48a4a', 0.3, 1.0, 0.0, None),
            'Cable': ('#101113', 0.55, 0.0, 0.0, None),
            'Conduit': ('#0f1012', 0.5, 0.0, 0.0, None),
            'ConnBlack': ('#0d0e10', 0.45, 0.0, 0.0, None),
            'ConnGreen': ('#2e7d32', 0.45, 0.0, 0.0, None),
            'Seal': ('#0b0b0c', 0.85, 0.0, 0.0, None),
            'Pcb': ('#1a2a1d', 0.5, 0.0, 0.0, None),
            'Gasket': ('#080808', 0.9, 0.0, 0.0, None),
            'Label': ('#d8dade', 0.6, 0.0, 0.0, None),
        }[kind]
        m, p = _principled(key)
        p.inputs['Base Color'].default_value = srgb(spec[0])
        p.inputs['Roughness'].default_value = spec[1]
        p.inputs['Metallic'].default_value = spec[2]
        if spec[3]:
            p.inputs['Coat Weight'].default_value = spec[3]
            p.inputs['Coat Roughness'].default_value = 0.1
        if spec[4]:
            _normal(m, p, tex(spec[4]), 0.35)
    MATS[key] = m
    return m


def E(fn, color):
    return mat(f'E.{fn}.{color}')


# =====================================================================
# Ürün kurulum bağlamı
# =====================================================================
class Lamp:
    """Bir ürünün parça grupları. Builder fonksiyonu bunları doldurur."""

    def __init__(self, pid):
        self.pid = pid
        self.body = Group('BODY')
        self.inner = Group('INNER')
        self.lens = Group('LENS')
        self.emit = {}

    def E(self, fn):
        if fn not in self.emit:
            self.emit[fn] = Group('EMIT.' + fn)
        return self.emit[fn]


def _join(group, name):
    objs = [o for o in group.objs]
    if not objs:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')
    objs = list(bpy.context.selected_objects)
    # her parçanın UV'si olmalı: normal haritalı malzemeler (yastık optik, altıgen reflektör, gövde dokusu) UV'siz ağda
    # glTF'te geçersiz texCoord üretir ve sitede gölgelendirici derlenmez
    for o in objs:
        if not o.data.uv_layers:
            set_uv_planar(o, 0.012, 'z')
        elif o.data.uv_layers.active.name != 'UVMap':
            o.data.uv_layers.active.name = 'UVMap'
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def finalize(L):
    """Grupları adlı düğümlere birleştirir. Döner: [nesne]"""
    out = []
    for g, name in ((L.body, 'BODY'), (L.inner, 'INNER'), (L.lens, 'LENS')):
        ob = _join(g, name)
        if ob:
            out.append(ob)
    for fn, g in L.emit.items():
        ob = _join(g, 'EMIT.' + fn)
        if ob:
            out.append(ob)
    # ürüne özel ek düğümler: BRACKET (montaj plakası), MOUNT_* boş nesneler (sitede takma noktası)
    b = getattr(L, 'bracket', None)
    if b is not None:
        ob = _join(b, b.name)
        if ob:
            out.append(ob)
    out += getattr(L, 'empties', [])
    return out


def clear_scene():
    for o in list(scene.collection.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for cu in list(bpy.data.curves):
        if cu.users == 0:
            bpy.data.curves.remove(cu)


def export(pid, objs):
    path = os.path.join(RAW_DIR, f'lamp-{pid}.glb')
    os.makedirs(RAW_DIR, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='WEBP',
                              export_image_quality=90, export_cameras=False, export_lights=False, export_extras=True)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH')
    print(f'EXPORTED {pid} {os.path.getsize(path) / 1024:.0f} KB tris={tris}')


# =====================================================================
# Ortak alt parçalar
# =====================================================================
def cable_out(L, start, end, r=0.0028, conduit=True):
    """Arkadan çıkan kablo (koruge kılıflı) — yumuşak eğri"""
    tube(L.body, 'cable', [start, ((start[0] + end[0]) / 2, start[1], (start[2] + end[2]) / 2 - 0.02), end], r * (1.5 if conduit else 1),
         mat('Conduit' if conduit else 'Cable'), 4, smooth=True)


def superseal(L, x, y, z, rot_z=False, color='ConnBlack'):
    """Superseal 2 pin fiş (küçük dikdörtgen gövde)"""
    w, h, d = 0.012, 0.009, 0.026
    box(L.body, 'superseal', x - w / 2, x + w / 2, y - h / 2, y + h / 2, z - d, z, mat(color), 0.0012)


def amp7(L, x, y, z, length=0.045):
    """AMP 7 pin yuvarlak fiş (yeşil contalı), -Z yönünde"""
    cyl(L.body, 'amp_body', 0.017, (x, y, z), (x, y, z - length), mat('ConnBlack'), 32, bevel=0.0015)
    cyl(L.body, 'amp_seal', 0.0185, (x, y, z - length * 0.35), (x, y, z - length * 0.45), mat('ConnGreen'), 32)
    cyl(L.body, 'amp_nut', 0.021, (x, y, z), (x, y, z - 0.006), mat('ConnBlack'), 6, bevel=0.001)


def screw(L, x, y, z, r=0.004, h=0.003, axis='z'):
    if axis == 'z':
        cyl(L.body, 'screw', r, (x, y, z), (x, y, z + h), mat('Zinc'), 20, bevel=0.0006)
    else:
        cyl(L.body, 'screw', r, (x, y, z), (x, y + h, z), mat('Zinc'), 20, bevel=0.0006)


def stud(L, x, y, z0, length=0.025, r=0.004):
    """Arkadan çıkan M8/M5 civata (-Z yönünde)"""
    cyl(L.body, 'stud', r, (x, y, z0), (x, y, z0 - length), mat('Zinc'), 16)
    cyl(L.body, 'nut', r * 1.9, (x, y, z0 - length * 0.55), (x, y, z0 - length * 0.55 - r * 1.6), mat('Zinc'), 6, bevel=0.0005)


# =====================================================================
# ÜRÜNLER
# Her builder: def build_<id>(L): ... ; KATALOG'a kaydedilir.
# =====================================================================
CATALOG = {}


def product(pid, code, cat, desc=''):
    def deco(fn):
        CATALOG[pid] = {'fn': fn, 'code': code, 'cat': cat, 'desc': desc}
        return fn
    return deco


# ---------------------------------------------------------------------
# LZD 3194/AMP — MAVIC (sol) arka kombine lamba: 405 × ~148 × 63 mm, 2 × M8 (250 mm), AMP 7 pin + 4 Superseal.
# İşlevler: neon pozisyon, stop (4+4 LED blok), neon sinyal (turuncu kama), geri vites (2 beyaz pencere), sis, üçgen reflektör.
# LZD 3195/AMP sağ lamba = bunun aynası (sitede x ölçeği -1).
# ---------------------------------------------------------------------
@product('lzd3194', 'LZD 3194/AMP', 'stop', 'MAVIC sol (sağ: LZD 3195/AMP, ayna)')
def build_lzd3194(L):
    # Yerleşim resmî ürün fotoğrafından (gallery/LZD-3194-amp.jpg): dış uçta (−X) iki geri vites penceresi (2'şer LED) ve aralarında
    # küçük üçgen çentik, altta büyük üçgen reflektör; turuncu sinyal kılavuzu dış uçta geniş, iç uca doğru incelir; üst ve
    # alt kenar boyunca kırmızı neon pozisyon çizgileri; iç uçta (+X) stop LED hücreleri; iç uçta üst köşe pahlı.
    W, H, D = 0.405, 0.148, 0.063
    x0, x1 = -W / 2, W / 2
    y0, y1 = -H / 2, H / 2
    face = [(x0, y0 + 0.010), (x0 + 0.010, y0), (x1 - 0.014, y0), (x1, y0 + 0.016), (x1, y1 - 0.030), (x1 - 0.030, y1), (x0 + 0.010, y1), (x0, y1 - 0.010)]
    zf = D
    zr = D - 0.024  # iç reflektör düzlemi
    # gövde reflektörün ARKASINDA biter (iç parçaları örtmemeli); kenarda lense kadar uzanan çerçeve
    prism(L.body, 'housing', offset(face, 0.002), 0.0, zr - 0.003, mat('Housing'), 0.004)
    frame(L.body, 'bezel', face, offset(face, 0.005), zr - 0.004, D - 0.011, mat('HousingGloss'), 0.0015)
    # arka yüzdeki çevre vidaları (fotoğraf: kenar boyunca 10 vida)
    for x in (-0.17, -0.09, 0.0, 0.09, 0.17):
        for y in (-0.058, 0.058):
            cyl(L.body, 'back_screw', 0.0035, (x, y, 0.0), (x, y, -0.0012), mat('Zinc'), 12)
    # iç taban: kırmızı lensin ardında derin kırmızı metalize reflektör (açık gri reflektör lensi pembe gösterir)
    prism(L.inner, 'reflector', offset(face, 0.006), zr - 0.003, zr, mat('ReflectorRed'), 0.0)
    set_uv_planar(L.inner.objs[-1], 0.03)
    # alt kenarda koyu tırtıklı optik bant (fotoğrafta lensin altında)
    box(L.inner, 'rib_band', -0.040, 0.198, -0.071, -0.064, zr, zr + 0.004, mat('Ribbed'))
    set_uv_planar(L.inner.objs[-1], 0.006)
    # lensin ardından görünen çevre vidaları
    for (sx, sy) in ((-0.185, 0.064), (-0.040, 0.066), (0.060, 0.066), (0.150, 0.066), (-0.185, -0.064), (-0.020, -0.064), (0.110, -0.064), (0.196, 0.030)):
        cyl(L.inner, 'face_screw', 0.0032, (sx, sy, zr), (sx, sy, zr + 0.003), mat('Chrome'), 16)
    # üçgen reflektör (büyük, dış alt)
    tri = [(-0.178, -0.054), (-0.068, -0.054), (-0.123, 0.024)]
    prism(L.inner, 'tri', tri, zr, zr + 0.006, mat('Retro.red'), 0.0008)
    set_uv_planar(L.inner.objs[-1], 0.010)
    # üçgenin çevresinde ince kırmızı neon çerçeve (fotoğrafta tırnak biçimi)
    ribbon(L.E('position'), 'tri_neon', [(-0.190, -0.062), (-0.123, 0.040), (-0.056, -0.062)], 0.0025, zr + 0.007, E('position', 'red'), 0.002)
    # geri vites: iki pencere, ikişer LED; aralarında üçgen çentik
    for cx in (-0.158, -0.084):
        prism(L.inner, 'rev_bay', rrect(0.052, 0.026, 0.006, 4, cx, 0.052), zr - 0.002, zr, mat('Chrome'), 0.0)
        for k in (-1, 1):
            cup(L.inner, cx + k * 0.012, 0.052, zr + 0.008, 0.0085, 0.004, 0.008, mat('Chrome'))
            box(L.E('reverse'), 'rev_led', cx + k * 0.012 - 0.004, cx + k * 0.012 + 0.004, 0.052 - 0.004, 0.052 + 0.004, zr + 0.0005, zr + 0.003, E('reverse', 'white'))
        frame(L.inner, 'rev_frame', rrect(0.056, 0.030, 0.007, 4, cx, 0.052), rrect(0.050, 0.024, 0.006, 4, cx, 0.052), zr, zr + 0.010, mat('Housing'), 0.0)
    prism(L.inner, 'notch', [(-0.128, 0.040), (-0.114, 0.040), (-0.121, 0.064)], zr, zr + 0.006, mat('Retro.red'), 0.0)
    # sinyal: turuncu ışık kılavuzu, dış uçta geniş (0,040), iç uçta incelir
    wedge = [(-0.062, -0.014), (0.192, 0.016), (0.192, 0.028), (-0.062, 0.028)]
    prism(L.E('turn'), 'turn_guide', wedge, zr + 0.002, zr + 0.008, E('turn', 'amber'), 0.0015)
    # pozisyon neonu: üst kenar (geri vites altından iç uca), alt kenar boyunca, iç uçta dikey
    ribbon(L.E('position'), 'pos_top', [(-0.050, 0.036), (0.150, 0.036), (0.176, 0.052)], 0.0035, zr + 0.009, E('position', 'red'), 0.0025)
    ribbon(L.E('position'), 'pos_bot', [(-0.045, -0.050), (0.192, -0.050)], 0.0035, zr + 0.009, E('position', 'red'), 0.0025)
    ribbon(L.E('position'), 'pos_end', [(0.196, -0.050), (0.196, 0.020)], 0.003, zr + 0.009, E('position', 'red'), 0.0025)
    # sis: alt kenarda ikinci kanal (iç yarı)
    ribbon(L.E('fog'), 'fog_line', [(0.020, -0.060), (0.192, -0.060)], 0.003, zr + 0.009, E('fog', 'red'), 0.0025)
    # stop: iç uçta üst ve alt LED hücreleri (lens ardında yapılı hücreler)
    for yy, nn in ((0.052, 4), (-0.040, 4)):
        for i in range(nn):
            cx = 0.070 + i * 0.030
            frame(L.inner, 'stop_cell', rrect(0.027, 0.014, 0.002, 2, cx, yy), rrect(0.023, 0.010, 0.0015, 2, cx, yy), zr, zr + 0.005, mat('Chrome'), 0.0)
            box(L.E('stop'), 'stop_led', cx - 0.010, cx + 0.010, yy - 0.004, yy + 0.004, zr + 0.0005, zr + 0.0025, E('stop', 'red'))
    # dış lens (kırmızı) + renksiz geri vites pencereleri + turuncu pencere
    prism(L.lens, 'lens', face, D - 0.012, zf, mat('Lens.red'), 0.006, 4)
    for cx in (-0.158, -0.084):
        prism(L.lens, 'lens_clear', rrect(0.050, 0.024, 0.006, 4, cx, 0.052), zf - 0.0005, zf + 0.0006, mat('Lens.clear'), 0.0)
    prism(L.lens, 'lens_amber', offset(wedge, -0.002), zf - 0.0005, zf + 0.0006, mat('Lens.amber'), 0.0)
    # arka: 2 × M8 (kauçuk kapaklı), ortada koruge kılıflı kısa AMP 7 pin kablo, iki uçta çift Superseal yuvası
    for sx in (-0.125, 0.125):
        stud(L, sx, 0.0, 0.0, 0.025, 0.004)
        cyl(L.body, 'stud_cap', 0.011, (sx, 0.0, 0.0), (sx, 0.0, -0.010), mat('Gasket'), 24, bevel=0.002)
    cyl(L.body, 'grommet', 0.011, (0.0, 0.004, 0.0), (0.0, 0.004, -0.008), mat('Gasket'), 24, bevel=0.002)
    tube(L.body, 'conduit', [(0.0, 0.004, -0.006), (0.0, -0.010, -0.030), (-0.020, -0.030, -0.050), (-0.040, -0.040, -0.060)], 0.0055, mat('Conduit'), 4, smooth=True)
    amp7(L, -0.052, -0.040, -0.060, 0.045)
    for sx in (-0.168, 0.168):
        box(L.body, 'ss_bay', sx - 0.020, sx + 0.020, -0.016, 0.014, -0.004, 0.0, mat('ConnBlack'), 0.001)
        for k in (-1, 1):
            box(L.body, 'ss_port', sx + k * 0.008 - 0.0045, sx + k * 0.008 + 0.0045, -0.010, 0.006, -0.010, -0.004, mat('ConnBlack'), 0.0008)


# ---------------------------------------------------------------------
# Diğer ürünler ayrı modüllerde (alt ajanlar): lamps_rear.py, lamps_small.py, lamps_aux.py
# Her modül bu dosyadaki yardımcıları `from lamps import *` ile değil, aşağıdaki register() çağrısıyla kullanır.
# ---------------------------------------------------------------------
def _load_modules():
    here = os.path.dirname(os.path.abspath(__file__))
    for mod in ('lamps_rear', 'lamps_small', 'lamps_aux', 'lamps_cad'):  # lamps_cad: üretici CAD verisi varsa el modelinin yerine geçer
        p = os.path.join(here, mod + '.py')
        if os.path.exists(p):
            try:
                code = compile(open(p, encoding='utf-8').read(), p, 'exec')
                exec(code, globals())
            except Exception as e:  # bir modüldeki hata diğer ürünleri durdurmasın
                import traceback
                print('MODULE ERROR', mod, e)
                traceback.print_exc()


# =====================================================================
# Önizleme ve simge render'ı (Cycles)
# =====================================================================
def studio():
    w = bpy.data.worlds.new('studio') if not scene.world else scene.world
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    grad = nt.nodes.new('ShaderNodeTexGradient')
    grad.gradient_type = 'LINEAR'
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].color = (0.55, 0.56, 0.58, 1)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.1
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    for nm, loc, energy, size in (('key', (0.6, 0.7, 0.9), 60, 0.6), ('fill', (-0.8, 0.3, 0.6), 25, 0.8), ('rim', (0.0, 0.9, -0.8), 40, 0.4)):
        lt = bpy.data.lights.new(nm, 'AREA')
        lt.energy = energy
        lt.size = size
        ob = bpy.data.objects.new(nm, lt)
        scene.collection.objects.link(ob)
        ob.location = bl(loc)
        ob.rotation_euler = (bl((0, 0, 0)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32 if FAST else 96
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def set_emission(objs, on, strength=6.0, fns=None):
    for o in objs:
        if o.type != 'MESH':
            continue
        for m in o.data.materials:
            if m and m.name.startswith('E.'):
                fn = m.name.split('.')[1].split('+')  # "position+stop": işlevlerden biri açıksa yanar
                p = m.node_tree.nodes['Principled BSDF']
                p.inputs['Emission Strength'].default_value = strength if (on and (fns is None or any(f in fns for f in fn))) else 0.0


def set_icon_glass(on):
    """Simgede lensler gerçek cam (iletim) olarak görünür; GLB dışa aktarımında kapalı"""
    for m in MATS.values():
        if m.get('lens'):
            p = m.node_tree.nodes['Principled BSDF']
            p.inputs['Transmission Weight'].default_value = 0.0
            p.inputs['Alpha'].default_value = LENS_ALPHA.get(m['lens'], 0.62)


def render_views(pid, objs, folder, views, size=900, lit_fns=None, fmt='PNG'):
    os.makedirs(folder, exist_ok=True)
    lo, hi = bounds(objs)
    c = (lo + hi) / 2
    r = (hi - lo).length / 2
    cam = bpy.data.objects.get('Cam') or bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    if cam.name not in scene.collection.objects:
        scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 85
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    for nm, d, lit in views:
        dv = bl(d).normalized()
        dist = r / math.tan(cam.data.angle / 2) * 1.08
        cam.location = c + dv * dist
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        set_emission(objs, lit, 11.0 if fmt == 'WEBP' else 6.0, lit_fns)
        scene.render.image_settings.file_format = fmt
        if fmt == 'WEBP':
            scene.render.image_settings.quality = 88
            scene.render.image_settings.color_mode = 'RGBA'
        scene.render.filepath = os.path.join(folder, f'{pid}-{nm}.{fmt.lower()}')
        bpy.ops.render.render(write_still=True)
    set_emission(objs, False)


ICON_LIT = {  # simgenin "yanık" hâlinde açık işlevler (ürünü tanıtan imza)
    'stop': ('position', 'turn', 'stop'),
    'side': ('marker',),
    'front': ('front',),
    'plate': ('plate', 'position'),
    'arm': ('outline',),
    'work': ('work',),
    'beacon': ('beacon',),
}
ICON_DIR_VEC = {'arm': (0.55, 0.25, 0.8), 'beacon': (0.45, 0.45, 1.0), 'plate': (-0.35, 0.55, 1.0)}


def icons(pid, objs, cat):
    """Konfigüratör ürün simgeleri: 3/4 açı, şeffaf zemin, sönük ve yanık (WEBP)"""
    os.makedirs(ICON_DIR, exist_ok=True)
    set_icon_glass(True)
    d = ICON_DIR_VEC.get(cat, (-0.45, 0.28, 1.0))
    render_views(pid, objs, ICON_DIR, [('off', d, False), ('on', d, True)], size=384 if FAST else 512, lit_fns=ICON_LIT.get(cat), fmt='WEBP')
    set_icon_glass(False)
    print('ICONS', pid)


# =====================================================================
# Ana akış
# =====================================================================
if __name__ == '__main__':
    _load_modules()
    studio()
    ids = ONLY or list(CATALOG)
    for pid in ids:
        if pid not in CATALOG:
            print('UNKNOWN', pid)
            continue
        clear_scene()
        L = Lamp(pid)
        CATALOG[pid]['fn'](L)
        objs = finalize(L)
        export(pid, objs)
        if PREVIEW:
            render_views(pid, objs, PREVIEW, [('front', (0, 0.05, 1), False), ('front-lit', (0, 0.05, 1), True), ('34', (-0.5, 0.3, 0.9), False),
                                              ('34-lit', (-0.5, 0.3, 0.9), True), ('back', (0.3, 0.3, -1), False)])
        if ICONS:
            icons(pid, objs, CATALOG[pid]['cat'])
    print('DONE', len(ids))
