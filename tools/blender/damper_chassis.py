# Damper (devirmeli) dorse şasisi: Blender'da betikle modellenir, ortam örtmesi (AO) dokuya pişirilir, GLB olarak dışa aktarılır.
# Çalıştırma (depo kökünden):
#   "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/blender/damper_chassis.py -- public/models/damper-chassis.glb [önizleme-klasörü]
#
# Referanslar (vault: Teknik Data/Damper Dorse): Kässbohrer K.SKS broşürü (dingil mesafesi 4,7 m, eyer yüksekliği 1,22 m,
# 3 × 9 t BPW aks), çıplak şase görselleri (yan, ön, üst). Kablolar ve cıvatalar modellenmez: tesisat sitede kodla çizilir.
#
# Koordinatlar: kod three.js düzeninde düşünülür (x boyuna: arka uç 0, ön -L; y yukarı; z yanal). bl() Blender'a çevirir
# (Blender Z yukarı); glTF dışa aktarıcı tekrar Y-yukarıya döndürür, yani sitede aynı sayılar geçerlidir.
import bpy
import bmesh
import math
import os
import sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else 'public/models/damper-chassis.glb')
PREVIEW = os.path.abspath(argv[1]) if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------- ölçüler (metre) ----------------
L = 9.0  # şasi boyu (ön traversin ön yüzünden arka uca)
W = 2.55
R = 0.536  # 385/65 R22,5
TOP = 1.50  # şasi üstü (kasa alt çerçevesi buraya oturur)
NECK_BOT = 1.22  # boyun altı = eyer yüksekliği H5
DEEP_BOT = 1.02  # derin kiriş altı
XF = -L  # ön uç
XN1 = -L + 2.35  # boyun biter
XN0 = -L + 2.95  # derin kiriş başlar
XR = -0.05  # arka uç
BZ = 0.5  # kiriş gövde sacı ekseni
KING_X = -7.11  # king pin (orta aksa 4,7 m)
AXLES = [-1.10, -2.41, -3.72]
LEG_X = -L + 3.25
WZ = W / 2 - 0.31  # tekerlek merkezi (yanal)


def bl(p):
    x, y, z = p
    return Vector((x, -z, y))


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


def material(name, color, rough, metal, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = srgb(color)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if coat:
        p.inputs['Coat Weight'].default_value = coat
        p.inputs['Coat Roughness'].default_value = 0.25
    return m


# şasi malzemeleri (birleşik şasi ağı) ve tekerlek malzemeleri ayrı: her ağın AO'su kendi dokusuna pişer
M = {
    'paint': material('Paint', '#3a3e44', 0.42, 0.35, 0.35),
    'dark': material('DarkSteel', '#1c1e21', 0.5, 0.45),
    'rubber': material('Rubber', '#151618', 0.85, 0.0),
    'flap': material('MudflapWhite', '#f2f3f4', 0.7, 0.0),
    'alu': material('LightGrey', '#c4c9cf', 0.32, 0.55),
    'chrome': material('Chrome', '#e8ebee', 0.06, 1.0),
    'refl': material('Reflector', '#d9dde1', 0.25, 0.3),
    'amber': material('AmberLens', '#f29a0c', 0.25, 0.0),
    'red': material('CouplingRed', '#c4161c', 0.4, 0.05),
    'blue': material('CouplingBlue', '#1f4fb8', 0.4, 0.05),
}
MW = {
    'tire': material('Tire', '#17181a', 0.9, 0.0),
    'rim': material('Rim', '#b8bdc4', 0.3, 0.85),
    'hub': material('Hub', '#25272b', 0.45, 0.5),
    'nut': material('Nut', '#d8dbdf', 0.15, 1.0),
}

PARTS = []  # şasi parçaları (sonda tek ağda birleşir)


def add_obj(name, bm, mat, bevel=0.0, parts=PARTS, seg=2):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
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
        me.set_sharp_from_angle(angle=math.radians(35))
    if parts is not None:
        parts.append(ob)
    return ob


def box(name, size, center, mat, bevel=0.006, parts=PARTS):
    lx, ly, lz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    c = bl(center)
    for v in bm.verts:
        v.co = Vector((v.co.x * lx, v.co.y * lz, v.co.z * ly)) + c
    return add_obj(name, bm, mat, bevel, parts)


def prism_xy(name, pts, z0, z1, mat, bevel=0.005, parts=PARTS):
    """Yandan görünüşte çokgen ([x, y]), z0..z1 arasında kalınlık (kiriş gövde sacı, braketler)"""
    bm = bmesh.new()
    a = [bm.verts.new(bl((x, y, z0))) for x, y in pts]
    b = [bm.verts.new(bl((x, y, z1))) for x, y in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, bevel, parts)


def prism_zy(name, pts, x0, x1, mat, bevel=0.005, parts=PARTS):
    """Önden görünüşte çokgen ([z, y]), x0..x1 arasında kalınlık (traversler, ön tampon, braket sacları)"""
    bm = bmesh.new()
    a = [bm.verts.new(bl((x0, y, z))) for z, y in pts]
    b = [bm.verts.new(bl((x1, y, z))) for z, y in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, bevel, parts)


def cylinder(name, r, a, b, mat, seg=28, bevel=0.003, r2=None, parts=PARTS, caps=True):
    a = bl(a)
    b = bl(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length)
    q = d.to_track_quat('Z', 'Y')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return add_obj(name, bm, mat, bevel, parts)


def beam(name, a, b, h, w, mat, bevel=0.004, parts=PARTS):
    """a→b yönünde dikdörtgen kesitli çubuk (h: dikey, w: yatay kalınlık); yönden bağımsız"""
    A = bl(a)
    B = bl(b)
    d = B - A
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * h, v.co.z * d.length))
    q = d.to_track_quat('Z', 'Y')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((A + B) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return add_obj(name, bm, mat, bevel, parts)


def hose(name, pts, r, mat, parts=PARTS):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = bl(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    cu.materials.append(mat)
    parts.append(ob)
    return ob


P = M['paint']
D = M['dark']

# ================= ana kirişler (I profil, önde basık boyun) =================
for s in (-1, 1):
    z = s * BZ
    prism_xy('beam_web', [(XF + 0.12, TOP - 0.02), (XR, TOP - 0.02), (XR, DEEP_BOT + 0.02), (XN0, DEEP_BOT + 0.02), (XN1, NECK_BOT + 0.02), (XF + 0.12, NECK_BOT + 0.02)], z - 0.006, z + 0.006, P, 0.002)
    box('beam_top', (XR - XF - 0.12, 0.022, 0.2), ((XF + 0.12 + XR) / 2, TOP - 0.011, z), P, 0.004)
    box('beam_bot_deep', (XR - XN0, 0.022, 0.2), ((XN0 + XR) / 2, DEEP_BOT + 0.011, z), P, 0.004)
    box('beam_bot_neck', (XN1 - XF - 0.12, 0.022, 0.2), ((XF + 0.12 + XN1) / 2, NECK_BOT + 0.011, z), P, 0.004)
    beam('beam_bot_slope', (XN1 - 0.01, NECK_BOT + 0.011, z), (XN0 + 0.01, DEEP_BOT + 0.011, z), 0.022, 0.2, P)
    # gövde sacı berkitmeleri (iki yüzde)
    x = XN0 + 0.35
    while x < XR - 0.2:
        for t in (-1, 1):
            box('stiff', (0.012, TOP - DEEP_BOT - 0.05, 0.085), (x, (TOP + DEEP_BOT) / 2, z + t * 0.05), P, 0.002)
        x += 0.78

# ================= traversler ve çaprazlar =================
CY = 1.30  # travers ekseni (kabloların altında kalır)


def cross(x, depth=0.1, h=0.14):
    # kutu profil + uçlarda kaynak köşebentleri
    box('cross', (depth, h, 2 * BZ - 0.012), (x, CY, 0), P, 0.005)
    for s in (-1, 1):
        prism_zy('gusset', [(s * (BZ - 0.006), CY + h / 2), (s * (BZ - 0.006), CY + h / 2 + 0.11), (s * (BZ - 0.12), CY + h / 2)], x - 0.006, x + 0.006, P, 0.002)


for x in (-8.75, -8.15, -7.6, -6.75, -5.9, -5.15, -4.4, -3.06, -1.76, -0.62):
    cross(x)
# aks bölgesinde X çaprazlar (üstten görünüş)
for xa, xb in ((-3.06, -1.76), (-1.76, -0.62)):
    for s in (-1, 1):
        beam('xbrace', (xa + 0.06, CY - 0.04, s * (BZ - 0.02)), (xb - 0.06, CY - 0.04, -s * (BZ - 0.02)), 0.012, 0.11, P, 0.002)
    box('xplate', (0.26, 0.012, 0.26), ((xa + xb) / 2, CY - 0.03, 0), P, 0.003)

# ================= ön travers (tampon), soket levhası, kavramalar =================
prism_zy('front_bar', [(-W / 2 + 0.02, 1.36), (W / 2 - 0.02, 1.36), (W / 2 - 0.02, 1.5), (W / 2 - 0.18, 1.56), (-W / 2 + 0.18, 1.56), (-W / 2 + 0.02, 1.5)], XF, XF + 0.14, P, 0.006)
for s in (-1, 1):
    box('front_refl', (0.004, 0.06, 0.32), (XF - 0.001, 1.47, s * 1.0), M['refl'], 0.0)
    box('front_lamp_bracket', (0.08, 0.05, 0.12), (XF + 0.04, 1.33, s * 1.12), P, 0.003)
box('socket_plate', (0.012, 0.2, 0.62), (XF + 0.13, 1.12, 0.0), P, 0.003)
# kingpin plakası ve pimi
box('king_plate', (1.6, 0.022, 1.12), (KING_X + 0.25, NECK_BOT + 0.011, 0), P, 0.004)
cylinder('king_pin', 0.0445, (KING_X, NECK_BOT, 0), (KING_X, NECK_BOT - 0.085, 0), M['chrome'], 32, 0.004)
cylinder('king_collar', 0.07, (KING_X, NECK_BOT + 0.0, 0), (KING_X, NECK_BOT - 0.02, 0), M['chrome'], 32, 0.003)
# fren havası kavramaları (palm) ve hortum askısı
for z, col in ((0.38, M['red']), (0.52, M['blue'])):
    cylinder('coupling', 0.045, (XF + 0.06, 1.42, z), (XF - 0.04, 1.42, z), col, 20, 0.004)

# ================= devirme pistonu ve ön platform =================
PX = XF + 0.36
for s in (-1, 1):
    prism_xy('cyl_bracket', [(XF + 0.14, TOP), (XF + 0.62, TOP), (XF + 0.5, 1.86), (XF + 0.24, 1.86)], s * 0.16 - 0.012, s * 0.16 + 0.012, P, 0.004)
cylinder('cyl_trunnion', 0.05, (PX, 1.78, -0.2), (PX, 1.78, 0.2), D, 24, 0.003)
lean = math.radians(5)
base = Vector((PX, 1.66, 0.0))
up = Vector((-math.sin(lean), math.cos(lean), 0.0))
stages = [(r, a * 0.8, b * 0.8, mt) for r, a, b, mt in [(0.125, 0.0, 0.95, D), (0.108, 0.95, 1.17, M['chrome']), (0.092, 1.17, 1.37, M['chrome']), (0.077, 1.37, 1.55, M['chrome']), (0.062, 1.55, 1.71, M['chrome'])]]
for r, a, b, mt in stages:
    pa = base + up * a
    pb = base + up * b
    cylinder('cyl_stage', r, tuple(pa), tuple(pb), mt, 36, 0.004)
    if mt is not D:
        cylinder('cyl_ring', r + 0.009, tuple(base + up * (a - 0.02)), tuple(base + up * a), D, 36, 0.003)
top = base + up * 1.37
box('cyl_eye', (0.14, 0.12, 0.2), tuple(top + up * 0.05), D, 0.01)
box('valve_block', (0.18, 0.14, 0.2), (XF + 0.6, 1.63, 0.42), D, 0.01)
for dz in (0.04, -0.04):
    hose('hyd_hose', [(XF + 0.6, 1.63, 0.32 + dz), (XF + 0.48, 1.6, 0.18 + dz), (PX + 0.12, 1.7, 0.05 + dz)], 0.012, M['rubber'])
hose('hyd_supply', [(XF + 0.68, 1.6, 0.52), (XF + 0.5, 1.45, 0.62), (XF + 0.2, 1.38, 0.6)], 0.014, M['rubber'])

box('oil_tank', (0.42, 0.42, 0.72), (XF + 0.33, TOP + 0.21, -0.72), D, 0.02)
box('oil_tank_lid', (0.44, 0.012, 0.74), (XF + 0.33, TOP + 0.425, -0.72), M['alu'], 0.004)
cylinder('oil_cap', 0.045, (XF + 0.3, TOP + 0.43, -0.55), (XF + 0.3, TOP + 0.48, -0.55), D, 20)
for dz in (-0.5, -0.94):
    box('oil_tank_foot', (0.46, 0.04, 0.06), (XF + 0.33, TOP + 0.02, dz), P, 0.004)

# ================= iniş ayakları =================
for s in (-1, 1):
    z = s * 0.63
    box('leg_mount', (0.26, 0.3, 0.012), (LEG_X, DEEP_BOT + 0.12, s * (BZ + 0.015)), P, 0.003)
    box('leg_outer', (0.15, 0.68, 0.15), (LEG_X, 0.98, z), P, 0.008)
    box('leg_inner', (0.115, 0.52, 0.115), (LEG_X, 0.42, z), D, 0.006)
    box('leg_foot', (0.3, 0.035, 0.26), (LEG_X, 0.13, z), P, 0.006)
    beam('leg_foot_web', (LEG_X, 0.15, z), (LEG_X, 0.21, z), 0.06, 0.12, P)
    beam('leg_brace_l', (LEG_X + 0.07, 0.8, z), (LEG_X + 0.95, DEEP_BOT + 0.015, s * (BZ - 0.02)), 0.06, 0.045, P)
    beam('leg_brace_x', (LEG_X, 0.72, z), (LEG_X, 1.12, -s * 0.12), 0.06, 0.04, P)
box('leg_gear', (0.2, 0.18, 0.12), (LEG_X, 1.14, 0.74), D, 0.01)
cylinder('leg_shaft', 0.024, (LEG_X, 1.1, -0.63), (LEG_X, 1.1, 0.63), D, 16)
for p in (((LEG_X, 1.14, 0.8), (LEG_X, 1.14, 0.97)),):
    cylinder('crank_shaft', 0.016, p[0], p[1], D, 12)
beam('crank_arm', (LEG_X, 1.14, 0.97), (LEG_X - 0.06, 0.88, 1.0), 0.03, 0.03, D)
cylinder('crank_grip', 0.02, (LEG_X - 0.06, 0.88, 1.0), (LEG_X - 0.06, 0.88, 1.1), M['rubber'], 12)

# ================= aks grubu: hava süspansiyonu, akslar, fren körükleri =================
for xa in AXLES:
    cylinder('axle', 0.064, (xa, R, -0.86), (xa, R, 0.86), D, 24, 0.004)
    for s in (-1, 1):
        zb = s * BZ
        prism_xy('hanger', [(xa - 0.78, DEEP_BOT), (xa - 0.42, DEEP_BOT), (xa - 0.5, 0.6), (xa - 0.64, 0.56)], zb - 0.07, zb + 0.07, P, 0.006)
        cylinder('hanger_pin', 0.035, (xa - 0.57, 0.62, zb - 0.09), (xa - 0.57, 0.62, zb + 0.09), M['chrome'], 16)
        beam('trail_arm', (xa - 0.57, 0.6, zb), (xa + 0.42, 0.47, zb), 0.075, 0.1, D, 0.006)
        box('axle_seat', (0.22, 0.18, 0.13), (xa, R - 0.02, zb), D, 0.01)
        cylinder('airbag_piston', 0.11, (xa + 0.42, 0.5, zb), (xa + 0.42, 0.6, zb), D, 32)
        cylinder('airbag', 0.155, (xa + 0.42, 0.6, zb), (xa + 0.42, 0.86, zb), M['rubber'], 40, 0.03)
        box('airbag_top', (0.3, 0.025, 0.28), (xa + 0.42, 0.875, zb), D, 0.005)
        prism_xy('airbag_bracket', [(xa + 0.3, DEEP_BOT), (xa + 0.54, DEEP_BOT), (xa + 0.5, 0.89), (xa + 0.34, 0.89)], zb - 0.08, zb + 0.08, P, 0.004)
        cylinder('shock', 0.032, (xa + 0.12, 0.5, s * (BZ + 0.12)), (xa - 0.3, 0.95, s * (BZ + 0.12)), D, 16)
        cylinder('shock_body', 0.042, (xa + 0.03, 0.6, s * (BZ + 0.12)), (xa - 0.12, 0.76, s * (BZ + 0.12)), D, 16)
        cylinder('brake_chamber', 0.09, (xa - 0.12, R + 0.14, s * 0.7), (xa - 0.34, R + 0.14, s * 0.7), D, 28, 0.01)
        cylinder('brake_drum', 0.215, (xa, R, s * 0.79), (xa, R, s * 0.95), D, 40, 0.006)

# ================= çamurluklar ve paçalar =================
def fender(x, s):
    zc = s * WZ
    bm = bmesh.new()
    ri, ro = R + 0.07, R + 0.085
    a0, a1, n = math.radians(18), math.radians(162), 28
    rings = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        ca, sa = -math.cos(a), math.sin(a)
        ring = []
        for rr, zz in ((ri, -0.25), (ro, -0.25), (ro, 0.25), (ri, 0.25)):
            ring.append(bm.verts.new(bl((x + rr * ca, R + rr * sa, zc + zz))))
        rings.append(ring)
    for k in range(n):
        A, B = rings[k], rings[k + 1]
        for i in range(4):
            bm.faces.new([A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add_obj('fender', bm, P, 0.003)
    # dış kenar şeridi ve taşıyıcılar
    for a in (math.radians(50), math.radians(130)):
        p = (x - (ri - 0.01) * math.cos(a), R + (ri - 0.01) * math.sin(a), zc - s * 0.18)
        beam('fender_stay', p, (x - 0.25 * math.cos(a), DEEP_BOT - 0.02, s * (BZ + 0.02)), 0.035, 0.035, P)


for xa in AXLES:
    for s in (-1, 1):
        fender(xa, s)
for s in (-1, 1):
    box('mudflap', (0.012, 0.6, 0.5), (AXLES[0] + R + 0.13, 0.6, s * WZ), M['flap'], 0.004)
    box('mudflap_bar', (0.04, 0.04, 0.6), (AXLES[0] + R + 0.13, 0.96, s * WZ), P, 0.004)
    beam('mudflap_stay', (AXLES[0] + R + 0.13, 0.96, s * (WZ - 0.2)), (AXLES[0] + R + 0.05, DEEP_BOT, s * BZ), 0.04, 0.04, P)

# ================= yan koruma, yan marker rayı =================
GX0, GX1 = LEG_X + 0.38, AXLES[-1] - R - 0.22
for s in (-1, 1):
    z = s * (W / 2 - 0.05)
    for y in (0.6, 0.86):
        box('guard_rail', (GX1 - GX0, 0.09, 0.035), ((GX0 + GX1) / 2, y, z), M['alu'], 0.006)
    for x in (GX0 + 0.03, GX1 - 0.03):
        box('guard_post', (0.045, 0.34, 0.035), (x, 0.73, z), M['alu'], 0.005)
        beam('guard_arm', (x, 0.84, z - s * 0.02), (x, DEEP_BOT, s * (BZ + 0.02)), 0.05, 0.04, P)

# ================= hava tankı, yedek lastik taşıyıcısı, EBS =================
cylinder('air_tank', 0.16, (-5.42, 1.18, 0.82), (-4.62, 1.18, 0.82), D, 36, 0.02)
for x in (-5.25, -4.8):
    cylinder('tank_strap', 0.168, (x - 0.02, 1.18, 0.82), (x + 0.02, 1.18, 0.82), P, 36, 0.002)
    beam('tank_hanger', (x, 1.34, 0.82), (x, DEEP_BOT + 0.05, BZ + 0.02), 0.04, 0.04, P)
box('ebs', (0.28, 0.2, 0.3), (-4.15, 1.2, 0.25), D, 0.015)
SPX = -4.86
for z in (-0.42, 0.42):
    box('spare_rail', (1.05, 0.05, 0.05), (SPX, 0.28, z), P, 0.004)
    for x in (SPX - 0.48, SPX + 0.48):
        beam('spare_hanger', (x, 0.3, z), (x, DEEP_BOT, z * 1.19), 0.05, 0.05, P)
for x in (SPX - 0.48, SPX + 0.48):
    box('spare_cross', (0.05, 0.05, 0.9), (x, 0.28, 0), P, 0.004)

# ================= arka: kapanış traversi, devirme menteşesi, lamba barı, alt koruma tamponu =================
box('rear_cross', (0.12, TOP - DEEP_BOT, 2 * BZ + 0.2), (XR - 0.06, (TOP + DEEP_BOT) / 2, 0), P, 0.006)
for s in (-1, 1):
    prism_xy('hinge_bracket', [(XR - 0.36, TOP), (XR - 0.02, TOP), (XR - 0.02, TOP + 0.09), (XR - 0.13, TOP + 0.13), (XR - 0.24, TOP + 0.09)], s * 0.3 - 0.025, s * 0.3 + 0.025, P, 0.004)
cylinder('hinge_pin', 0.04, (XR - 0.13, TOP + 0.07, -0.4), (XR - 0.13, TOP + 0.07, 0.4), M['chrome'], 24)
LAMP_Y = 1.12
box('lamp_bar', (0.1, 0.13, W - 0.06), (-0.06, LAMP_Y, 0), P, 0.006)
for s in (-1, 1):
    box('lamp_bar_hanger', (0.08, DEEP_BOT - LAMP_Y + 0.12, 0.08), (-0.1, (DEEP_BOT + LAMP_Y) / 2, s * 0.6), P, 0.004)
box('plate_holder', (0.035, 0.17, 0.58), (-0.04, 0.88, 0), P, 0.004)
beam('plate_hanger', (-0.05, 0.96, 0), (-0.08, LAMP_Y - 0.05, 0), 0.04, 0.12, P)
box('bumper', (0.1, 0.12, 2.36), (0.02, 0.5, 0), M['alu'], 0.012)
for s in (-1, 1):
    beam('bumper_arm', (0.0, 0.54, s * 0.62), (-0.42, DEEP_BOT + 0.01, s * 0.62), 0.07, 0.06, P)
    cylinder('bumper_cap', 0.07, (0.02, 0.5, s * 1.17), (0.02, 0.5, s * 1.19), M['rubber'], 20)

# ================= birleştirme (şasi tek ağ, çok malzeme) =================
def select_only(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


select_only(PARTS)
bpy.ops.object.convert(target='MESH')
chassis_objs = [o for o in scene.objects if o.type == 'MESH']
select_only(chassis_objs)
bpy.ops.object.join()
chassis = bpy.context.view_layer.objects.active
chassis.name = 'DamperChassis'
chassis.data.name = 'DamperChassis'

# ================= tekerlek (tek model, örneklenir) =================
WPARTS = []


def lathe(name, prof, mat, steps=96):
    """Profil (yarıçap, yanal) Blender'ın Y ekseni (aks) etrafında döndürülür"""
    bm = bmesh.new()
    vs = [bm.verts.new((r, w, 0.0)) for r, w in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 1, 0), angle=math.pi * 2, steps=steps, use_merge=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, 0.0, WPARTS)


# lastik: yanak şişkinliği, omuz yuvarlatması, 3 boyuna diş kanalı (dorse lastiği ribli desen)
shoulder = [(0.292, -0.148), (0.33, -0.17), (0.39, -0.188), (0.45, -0.193), (0.495, -0.186), (0.52, -0.172), (0.531, -0.155), (0.536, -0.138)]
tp = list(shoulder)
for g in (-0.074, 0.0, 0.074):
    tp += [(0.536, g - 0.012), (0.533, g - 0.009), (0.521, g - 0.006), (0.521, g + 0.006), (0.533, g + 0.009), (0.536, g + 0.012)]
tp += [(r, -w) for r, w in reversed(shoulder)]


def tread(bm):
    # sırt deseni: omuzlarda enine bloklar (48 adım, iki omuz yarım adım kaydırılmış), orta riblerde ince lameller
    period = 2 * math.pi / 48
    for v in bm.verts:
        x, w, z = v.co
        r = math.hypot(x, z)
        if r < 0.529:
            continue
        a = math.atan2(z, x) % (2 * math.pi)
        if 0.088 < abs(w) < 0.15:
            f = ((a / period) + (0.5 if w > 0 else 0.0)) % 1.0
            cut = 0.014 if f < 0.34 else 0.0
        elif abs(w) < 0.062:
            f = ((a / period) * 2 + 0.25) % 1.0
            cut = 0.006 if f < 0.2 else 0.0
        else:
            cut = 0.0
        if cut:
            k = (r - cut) / r
            v.co.x *= k
            v.co.z *= k


bm = bmesh.new()
vs = [bm.verts.new((r, w, 0.0)) for r, w in tp]
es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 1, 0), angle=math.pi * 2, steps=288, use_merge=True)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
tread(bm)
tire = add_obj('tire', bm, MW['tire'], 0.0, WPARTS)
# jant: kenar, gövde, el delikli disk, göbek, bijonlar; arkada fren kampanası
lathe('rim_barrel', [(0.3, -0.152), (0.286, -0.145), (0.276, -0.12), (0.272, -0.04), (0.255, 0.0), (0.272, 0.04), (0.276, 0.12), (0.286, 0.145), (0.3, 0.152)], MW['rim'], 64)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=0.268, radius2=0.268, depth=0.014)
bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 0.035, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bm.verts)
disc = add_obj('rim_disc', bm, MW['rim'], 0.003, WPARTS)
holes = []
for k in range(10):
    a = 2 * math.pi * (k + 0.5) / 10
    bmh = bmesh.new()
    bmesh.ops.create_cone(bmh, cap_ends=True, segments=20, radius1=0.032, radius2=0.032, depth=0.1)
    bmesh.ops.transform(bmh, matrix=Matrix.Rotation(a, 4, 'Y') @ Matrix.Translation((0.2, 0.035, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bmh.verts)
    me = bpy.data.meshes.new('hole')
    bmh.to_mesh(me)
    ho = bpy.data.objects.new('hole', me)
    scene.collection.objects.link(ho)
    holes.append(ho)
for ho in holes:
    md = disc.modifiers.new('hole', 'BOOLEAN')
    md.operation = 'DIFFERENCE'
    md.object = ho
    md.solver = 'EXACT'
lathe('hub', [(0.0, 0.16), (0.07, 0.16), (0.08, 0.15), (0.085, 0.11), (0.12, 0.1), (0.125, 0.045), (0.14, 0.04)], MW['hub'], 48)
for k in range(10):
    a = 2 * math.pi * k / 10
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.016, radius2=0.016, depth=0.035)
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(a, 4, 'Y') @ Matrix.Translation((0.1675, 0.06, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bm.verts)
    add_obj('nut', bm, MW['nut'], 0.002, WPARTS)
lathe('hub_cap', [(0.0, 0.17), (0.04, 0.17), (0.055, 0.165), (0.06, 0.155)], MW['nut'], 32)

select_only(WPARTS)
bpy.ops.object.convert(target='MESH')
for ho in holes:
    bpy.data.objects.remove(ho, do_unlink=True)
wobjs = [o for o in WPARTS]
select_only(wobjs)
bpy.ops.object.join()
wheel = bpy.context.view_layer.objects.active
wheel.name = 'Wheel'
wheel.data.name = 'Wheel'

# ================= damper kasası (ayrı dosya: tesisat görünümünde gizlenir) =================
# Referans: üretici 3D çıktıları (Teknik Data/Damper Dorse, HDR-670): dik yan duvarlar, altta içe kıvrılan trapez taban,
# kalın üst kenar profili, yan takviye kırımı ve branda kancaları, öne çıkan siperlik (kaldırma kulaklı), pistonu saran
# kanal sacları, ön merdiven; arkada köşe dikmeleri ve üstten menteşeli, çerçeveli kapak (ECE 70 reflektörleri).
MB = {
    'paint': material('BodyPaint', '#f1f2f4', 0.28, 0.05, 0.6),
    'dark': material('BodyDark', '#1c1e21', 0.5, 0.45),
    'alu': material('BodyAlu', '#c9cdd3', 0.3, 0.7),
    'red': material('ReflRed', '#d0121c', 0.3, 0.05),
    'yellow': material('ReflYellow', '#f4b400', 0.3, 0.05),
    'plate': material('LogoPlate', '#fbfbfb', 0.35, 0.05),
}
BODY = []
BP = MB['paint']
BX0 = -8.45  # ön duvarın ön yüzü
BX1 = -0.10  # yan duvarların / köşe dikmelerinin arka ucu
Y0 = TOP + 0.12  # kasa tabanı (alt çerçevenin üstü)
YT = Y0 + 1.53  # yan duvar üstü (üst profil bunun üstüne oturur)
HW = W / 2 - 0.02  # yan duvar dış yüzü


def bez(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def contour(hw, y0, yt, t=0.0, n=12):
    """Kasa kesiti (z, y): sol üst → sol dik duvar → yuvarlatılmış pah → taban → sağ; t içe kaydırma"""
    k = Y0 + 0.85 - y0
    hw -= t
    y0 += t
    left = [(-hw, yt)] + bez((-hw, y0 + k), (-hw, y0 + k * 0.45), (-hw + 0.26, y0), (-hw + 0.6, y0), n)
    right = [(-z, y) for z, y in reversed(left)]
    return left + right


outer = contour(HW, Y0, YT)
inner = contour(HW, Y0, YT, 0.012)
# kabuk (yan duvarlar + pahlar + taban), 12 mm sac
prism_zy('tub_shell', outer + list(reversed(inner)), BX0 + 0.012, BX1 - 0.06, BP, 0.003, BODY)
# arka çerçeve: kesiti birebir izleyen kalın U profil (kabuğun ucunu kapatır, kapak buna oturur)
prism_zy('rear_frame', contour(HW, Y0, YT, -0.03) + list(reversed(inner)), BX1 - 0.1, BX1, BP, 0.008, BODY)
# ön duvar ve arka kapak paneli (kesitin içi dolu)
prism_zy('front_wall', outer, BX0, BX0 + 0.012, BP, 0.003, BODY)
# üst kenar profilleri (kutu) ve ön üst profil
for s in (-1, 1):
    box('top_rail', (BX1 - BX0 + 0.08, 0.12, 0.1), ((BX0 + BX1) / 2 + 0.03, YT + 0.04, s * (W / 2 - 0.05)), BP, 0.01, BODY)
    # yan takviye kırımı (logonun altında) ve pah başlangıcındaki kırım
    box('side_rib', (BX1 - BX0 - 0.5, 0.05, 0.018), ((BX0 + BX1) / 2 + 0.05, Y0 + 1.0, s * (HW + 0.009)), BP, 0.006, BODY)
    box('side_rib_low', (BX1 - BX0 - 0.5, 0.03, 0.012), ((BX0 + BX1) / 2 + 0.05, Y0 + 0.82, s * (HW + 0.006)), BP, 0.004, BODY)
    # ön ve arka köşe dikmeleri
    box('front_post', (0.12, YT - Y0 - 0.85, 0.06), (BX0 + 0.06, (YT + Y0 + 0.85) / 2, s * (HW + 0.02)), BP, 0.01, BODY)
    # branda kancaları: üst kırım ve alt kırım boyunca
    for i in range(9):
        x = BX0 + 0.6 + (BX1 - BX0 - 1.2) * i / 8
        hose('hook', [(x - 0.035, Y0 + 1.02, s * (HW + 0.018)), (x, Y0 + 0.97, s * (HW + 0.05)), (x + 0.035, Y0 + 1.02, s * (HW + 0.018))], 0.007, MB['dark'], BODY)
    for i in range(10):
        x = BX0 + 0.45 + (BX1 - BX0 - 0.9) * i / 9
        hose('hook', [(x - 0.03, Y0 + 0.84, s * (HW + 0.012)), (x, Y0 + 0.79, s * (HW + 0.04)), (x + 0.03, Y0 + 0.84, s * (HW + 0.012))], 0.006, MB['dark'], BODY)
box('front_rail', (0.1, 0.12, W - 0.02), (BX0 + 0.05, YT + 0.04, 0), BP, 0.01, BODY)
# ön duvar: dikey takviyeler ve pistonu saran kanal sacları
for z in (-0.72, 0.72):
    box('front_stiff', (0.07, YT - Y0 - 0.5, 0.1), (BX0 - 0.035, (YT + Y0 + 0.5) / 2, z), BP, 0.008, BODY)
for z in (-0.27, 0.27):
    prism_xy('tunnel', [(BX0, Y0 + 0.15), (BX0, YT), (BX0 - 0.3, YT), (BX0 - 0.3, Y0 + 0.75)], z - 0.006, z + 0.006, BP, 0.003, BODY)
# siperlik (kabin koruması): öne hafif yükselen sac, ön dudak, yan köşebentler, kaldırma kulakları
CAN = 0.62
prism_xy('canopy', [(BX0 + 0.1, YT + 0.1), (BX0 - CAN, YT + 0.16), (BX0 - CAN, YT + 0.2), (BX0 + 0.1, YT + 0.135)], -W / 2, W / 2, BP, 0.006, BODY)
box('canopy_lip', (0.03, 0.1, W), (BX0 - CAN + 0.015, YT + 0.13, 0), BP, 0.006, BODY)
for s in (-1, 1):
    prism_xy('canopy_gusset', [(BX0, YT - 0.45), (BX0, YT + 0.1), (BX0 - CAN + 0.05, YT + 0.15)], s * (W / 2 - 0.03) - 0.006, s * (W / 2 - 0.03) + 0.006, BP, 0.003, BODY)
    hose('lift_loop', [(BX0 - 0.42, YT + 0.19, s * 0.62 - 0.07), (BX0 - 0.42, YT + 0.29, s * 0.62), (BX0 - 0.42, YT + 0.19, s * 0.62 + 0.07)], 0.014, BP, BODY)
# piston üst bağlantı braketi (siperliğin altında)
box('cyl_head_bracket', (0.24, 0.16, 0.34), (BX0 - 0.3, YT + 0.0, 0), MB['dark'], 0.01, BODY)
# alt çerçeve: kirişlerin üstünde iki boyuna kutu profil + taban altı traversleri; arkada menteşe kulakları
for s in (-1, 1):
    box('sub_beam', (BX1 - BX0 - 0.55, 0.12, 0.14), ((BX0 + BX1) / 2 - 0.2, TOP + 0.06, s * BZ), MB['dark'], 0.008, BODY)
    prism_xy('hinge_lug', [(-0.36, Y0), (-0.06, Y0), (-0.1, TOP + 0.02), (-0.2, TOP)], s * 0.36 - 0.015, s * 0.36 + 0.015, MB['dark'], 0.004, BODY)
x = BX0 + 0.5
while x < BX1 - 0.4:
    box('floor_cross', (0.08, 0.06, 1.25), (x, Y0 - 0.03, 0), MB['dark'], 0.006, BODY)
    x += 0.95
# arka kapak: arka çerçevenin üstüne binen dolu panel (açıklığı tamamen kapatır), kesiti izleyen çevre profili,
# genişliği bulunduğu yüksekliğe göre hesaplanan yatay takviyeler, ECE 70 reflektörleri, logo levhası, menteşe, kilitler, taşma dudağı
GX = BX1  # kapağın iç yüzü (çerçevenin arka yüzü)
GT = YT - 0.03  # kapak üstü (üst profilin altı)


def half_width(poly, y):
    # kesitin sol yarısında, verilen yükseklikteki yanal yarı genişlik
    left = poly[: len(poly) // 2]
    for (z0, y0), (z1, y1) in zip(left, left[1:]):
        if min(y0, y1) <= y <= max(y0, y1) and y0 != y1:
            return -(z0 + (z1 - z0) * (y - y0) / (y1 - y0))
    return -left[-1][0]


gate = contour(HW, Y0, GT, 0.012)
gate_in = contour(HW, Y0, GT, 0.1)
prism_zy('gate_panel', gate, GX, GX + 0.012, BP, 0.003, BODY)
prism_zy('gate_frame', gate + list(reversed(gate_in)), GX + 0.012, GX + 0.06, BP, 0.008, BODY)
box('gate_top', (0.048, 0.09, 2 * (HW - 0.012)), (GX + 0.036, GT - 0.045, 0), BP, 0.008, BODY)
for yy in (Y0 + 0.98, Y0 + 0.4):
    hw = half_width(gate_in, yy)
    box('gate_rib', (0.032, 0.06, 2 * hw), (GX + 0.028, yy, 0), BP, 0.006, BODY)
for s in (-1, 1):
    cylinder('gate_pin', 0.035, (GX + 0.035, GT + 0.04, s * (HW - 0.16)), (GX + 0.035, GT + 0.04, s * (HW + 0.02)), MB['dark'], 16, 0.002, None, BODY)
    box('gate_hinge', (0.09, 0.08, 0.06), (GX + 0.03, GT + 0.02, s * (HW - 0.11)), MB['dark'], 0.008, BODY)
    box('gate_lock', (0.06, 0.12, 0.08), (GX + 0.075, Y0 + 0.16, s * 0.35), MB['dark'], 0.008, BODY)
    box('gate_lock_hook', (0.05, 0.05, 0.06), (GX + 0.04, Y0 + 0.07, s * 0.35), MB['dark'], 0.006, BODY)
    box('ece70_red', (0.006, 0.2, 0.565), (GX + 0.015, Y0 + 0.68, s * 0.52), MB['red'], 0.0, BODY)
    box('ece70_yellow', (0.006, 0.14, 0.505), (GX + 0.019, Y0 + 0.68, s * 0.52), MB['yellow'], 0.0, BODY)
box('logo_plate', (0.006, 0.24, 0.66), (GX + 0.015, GT - 0.25, 0), MB['plate'], 0.003, BODY)
prism_xy('spill_lip', [(GX, Y0 + 0.02), (GX + 0.06, Y0 + 0.02), (GX + 0.17, Y0 - 0.08), (GX + 0.15, Y0 - 0.1)], -0.6, 0.6, BP, 0.003, BODY)

select_only(BODY)
bpy.ops.object.convert(target='MESH')
bodies = [o for o in BODY]
select_only(bodies)
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = 'DamperBody'
body.data.name = 'DamperBody'

# logolar (ayrı ağ, saydam doku; AO almaz): iki yan + arka kapak levhası
logo_img = bpy.data.images.load(os.path.abspath('public/brand/logo-blue.png'))
lm = bpy.data.materials.new('Logo')
lm.use_nodes = True
lnt = lm.node_tree
lp = lnt.nodes['Principled BSDF']
lt = lnt.nodes.new('ShaderNodeTexImage')
lt.image = logo_img
lnt.links.new(lt.outputs['Color'], lp.inputs['Base Color'])
lnt.links.new(lt.outputs['Alpha'], lp.inputs['Alpha'])
lp.inputs['Roughness'].default_value = 0.3
if hasattr(lm, 'blend_method'):
    lm.blend_method = 'BLEND'
if hasattr(lm, 'surface_render_method'):
    lm.surface_render_method = 'BLENDED'
def decal_mesh(name, quads):
    dm = bmesh.new()
    uvl = dm.loops.layers.uv.new()
    for corners in quads:
        vs = [dm.verts.new(bl(p)) for p in corners]
        f = dm.faces.new(vs)
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uvl].uv = uv
    me = bpy.data.meshes.new(name)
    dm.to_mesh(me)
    dm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    me.materials.append(lm)
    return ob


quads = []

lh = 0.42
lw = lh * 720 / 528
lx = (BX0 + BX1) / 2 - 0.4
ly = Y0 + 1.27
for s in (1, -1):
    z = s * (HW + 0.004)
    a, b = (lx - lw / 2, lx + lw / 2) if s > 0 else (lx + lw / 2, lx - lw / 2)
    quads.append([(a, ly - lh / 2, z), (b, ly - lh / 2, z), (b, ly + lh / 2, z), (a, ly + lh / 2, z)])
ph = 0.2
pw = ph * 720 / 528
xg = GX + 0.02
yg = GT - 0.25
quads.append([(xg, yg - ph / 2, pw / 2), (xg, yg - ph / 2, -pw / 2), (xg, yg + ph / 2, -pw / 2), (xg, yg + ph / 2, pw / 2)])
logos = decal_mesh('DamperLogos', quads)
# son aksın arkasındaki çamurluk paçaları: beyaz, arka yüzde logo (şasi dosyasında)
fx = AXLES[0] + R + 0.137
fh = 0.26
fw = fh * 720 / 528
paw = []
for s in (-1, 1):
    zc = s * WZ
    paw.append([(fx, 0.66 - fh / 2, zc + fw / 2), (fx, 0.66 - fh / 2, zc - fw / 2), (fx, 0.66 + fh / 2, zc - fw / 2), (fx, 0.66 + fh / 2, zc + fw / 2)])
flap_logos = decal_mesh('MudflapLogos', paw)


# ================= UV açma ve AO pişirme =================
def smart_uv(ob, margin):
    select_only([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


smart_uv(chassis, 0.002)
smart_uv(wheel, 0.004)
smart_uv(body, 0.002)

# tekerlek örnekleri (6 aks tekerleği + yedek)
wheels = [wheel]
inst = []
for xa in AXLES:
    for s in (-1, 1):
        inst.append((xa, s))
first = True
for xa, s in inst:
    ob = wheel if first else bpy.data.objects.new('Wheel', wheel.data)
    if not first:
        scene.collection.objects.link(ob)
        wheels.append(ob)
    first = False
    ob.location = bl((xa, R, s * WZ))
    # model dış yüzü Blender +Y'ye (three -z) bakar; +z tarafındakiler 180° döner
    ob.rotation_euler = (0, 0, math.pi if s > 0 else 0)
spare = bpy.data.objects.new('Wheel', wheel.data)
scene.collection.objects.link(spare)
spare.location = bl((SPX, 0.5, 0))
spare.rotation_euler = (math.pi / 2, 0, 0)
wheels.append(spare)


def bake_target(ob, size, name):
    # birleştirmede malzemesiz kalan yuva olursa varsayılanla doldur (dışa aktarımda gri malzeme çıkmasın)
    fallback = M['paint'] if ob is chassis else MB['paint'] if ob is body else MW['rim']
    for i, mt in enumerate(ob.data.materials):
        if mt is None:
            print('EMPTY SLOT', ob.name, i)
            ob.data.materials[i] = fallback
    seen = set()
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.generated_color = (1, 1, 1, 1)
    for mat in ob.data.materials:
        if mat.name in seen:
            continue
        seen.add(mat.name)
        nt = mat.node_tree
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        n.name = 'AO'
        nt.nodes.active = n
    return img


scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64
if scene.world is None:
    scene.world = bpy.data.worlds.new('World')
scene.world.light_settings.distance = 0.6
ao_c = bake_target(chassis, 2048, 'chassis_ao')
ao_w = bake_target(wheel, 1024, 'wheel_ao')
ao_b = bake_target(body, 2048, 'body_ao')
# şasi ve tekerlekler kasasız pişer (tesisat görünümünde kasa gizli; gölgesi şasiye düşmemeli), kasa şasiyle birlikte
for ob, img, hide in ((chassis, ao_c, True), (wheel, ao_w, True), (body, ao_b, False)):
    body.hide_render = hide
    logos.hide_render = True
    flap_logos.hide_render = True
    select_only([ob])
    bpy.ops.object.bake(type='AO', margin=4, use_clear=True)
    img.pack()
body.hide_render = False
logos.hide_render = False
flap_logos.hide_render = False

# glTF malzeme çıkışı: AO → occlusionTexture
grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
for ob in (chassis, wheel, body):
    for mat in set(ob.data.materials):
        nt = mat.node_tree
        img_node = nt.nodes['AO']
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(img_node.outputs['Color'], sep.inputs['Color'])
        g = nt.nodes.new('ShaderNodeGroup')
        g.node_tree = grp
        nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])

# ================= dışa aktarma =================
os.makedirs(os.path.dirname(OUT), exist_ok=True)
select_only([chassis, flap_logos] + wheels)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_image_format='WEBP',
    export_cameras=False,
    export_lights=False,
)
tris = sum(len(p.vertices) - 2 for p in chassis.data.polygons) + sum(len(p.vertices) - 2 for p in wheel.data.polygons)
print(f'EXPORTED {OUT} size={os.path.getsize(OUT) / 1024:.0f} KB tris(chassis+1 wheel)={tris}')
OUT_BODY = OUT.replace('chassis', 'body')
select_only([body, logos])
bpy.ops.export_scene.gltf(
    filepath=OUT_BODY,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_image_format='WEBP',
    export_cameras=False,
    export_lights=False,
)
btris = sum(len(p.vertices) - 2 for p in body.data.polygons)
print(f'EXPORTED {OUT_BODY} size={os.path.getsize(OUT_BODY) / 1024:.0f} KB tris={btris}')

# ================= önizleme render'ları (yalnızca kontrol için) =================
if PREVIEW:
    os.makedirs(PREVIEW, exist_ok=True)
    w = scene.world
    w.use_nodes = True
    nt = w.node_tree
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    studio = os.path.join(os.path.dirname(bpy.app.binary_path), f'{bpy.app.version[0]}.{bpy.app.version[1]}', 'datafiles', 'studiolights', 'world', 'studio.exr')
    env.image = bpy.data.images.load(studio)
    bg = nt.nodes['Background']
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.9
    # açık gri stüdyo zemini
    bpy.ops.mesh.primitive_plane_add(size=60, location=(-4.5, 0, 0))
    floor = bpy.context.active_object
    fm = material('Floor', '#cfd1d4', 0.6, 0.0)
    floor.data.materials.append(fm)
    sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'AREA'))
    sun.data.energy = 2500
    sun.data.size = 8
    sun.location = (-3, -6, 9)
    sun.rotation_euler = (math.radians(35), 0, math.radians(-25))
    scene.collection.objects.link(sun)
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 800
    scene.view_settings.view_transform = 'AgX'
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam

    def shot(name, loc, target, lens=50, ortho=None):
        cam.location = bl(loc)
        d = bl(target) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'ORTHO' if ortho else 'PERSP'
        if ortho:
            cam.data.ortho_scale = ortho
        cam.data.lens = lens
        scene.render.filepath = os.path.join(PREVIEW, name)
        bpy.ops.render.render(write_still=True)

    shot('full_side.png', (-4.4, 1.9, 14.5), (-4.4, 1.6, 0), 50)
    shot('full_front34.png', (-14.0, 3.4, -6.2), (-5.8, 1.5, 0), 50)
    shot('full_rear34.png', (4.6, 3.2, 6.6), (-3.2, 1.6, 0), 45)
    body.hide_render = True
    logos.hide_render = True
    shot('side.png', (-4.4, 1.2, 13.5), (-4.4, 1.0, 0), 50)
    shot('rear34.png', (4.2, 2.4, 5.0), (-2.6, 0.8, 0), 45)
    cam.data.type = 'ORTHO'
    cam.location = bl((-4.5, 12, 0))
    cam.rotation_euler = (0, 0, 0)
    cam.data.ortho_scale = 10.5
    scene.render.filepath = os.path.join(PREVIEW, 'top.png')
    bpy.ops.render.render(write_still=True)
    print('PREVIEWS', PREVIEW)
