# Blender betikleri için ortak yardımcılar (standart_box.py, lowbed.py, silo.py, tanker.py, damper.py).
# Koordinatlar three.js düzenindedir (x boyuna: arka uç 0, ön -L; y yukarı; z yanal). bl() Blender'a çevirir (Blender Z yukarı);
# glTF dışa aktarıcı tekrar Y-yukarıya döndürür, yani sitede aynı sayılar geçerlidir.
import bpy
import bmesh
import math
import os
from mathutils import Matrix, Vector

scene = bpy.context.scene


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


class Parts:
    """Birleştirilecek parça listesi (sonunda tek ağ)"""

    def __init__(self):
        self.objs = []


def add_obj(name, bm, mat, bevel, parts, seg=2, sharp=35):
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
        me.set_sharp_from_angle(angle=math.radians(sharp))
    if parts is not None:
        parts.objs.append(ob)
    return ob


def box(parts, name, size, center, mat, bevel=0.004):
    lx, ly, lz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    c = bl(center)
    for v in bm.verts:
        v.co = Vector((v.co.x * lx, v.co.y * lz, v.co.z * ly)) + c
    return add_obj(name, bm, mat, bevel, parts)


def box2(parts, name, x0, x1, y0, y1, z0, z1, mat, bevel=0.004):
    """Köşe koordinatlarıyla kutu"""
    return box(parts, name, (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat, bevel)


def quad(parts, name, corners, mat, uv=None):
    """Tek yüzlü dörtgen (yalnızca dışı görünen büyük paneller)"""
    bm = bmesh.new()
    vs = [bm.verts.new(bl(p)) for p in corners]
    f = bm.faces.new(vs)
    if uv:
        uvl = bm.loops.layers.uv.new()
        for loop, t in zip(f.loops, uv):
            loop[uvl].uv = t
    return add_obj(name, bm, mat, 0.0, parts)


def prism_xy(parts, name, pts, z0, z1, mat, bevel=0.004):
    """Yandan görünüşte çokgen ([x, y]), z0..z1 arasında kalınlık"""
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


def prism_zy(parts, name, pts, x0, x1, mat, bevel=0.004):
    """Önden görünüşte çokgen ([z, y]), x0..x1 arasında kalınlık"""
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


def prism_xz(parts, name, pts, y0, y1, mat, bevel=0.004):
    """Üstten görünüşte çokgen ([x, z]), y0..y1 arasında kalınlık"""
    bm = bmesh.new()
    a = [bm.verts.new(bl((x, y0, z))) for x, z in pts]
    b = [bm.verts.new(bl((x, y1, z))) for x, z in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, bevel, parts)


def cylinder(parts, name, r, a, b, mat, seg=28, bevel=0.003, r2=None, caps=True):
    a = bl(a)
    b = bl(b)
    d = b - a
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length)
    q = d.to_track_quat('Z', 'Y')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return add_obj(name, bm, mat, bevel, parts)


def beam(parts, name, a, b, h, w, mat, bevel=0.004):
    """a→b yönünde dikdörtgen kesitli çubuk (h: dikey, w: yatay kalınlık)"""
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


def hose(parts, name, pts, r, mat, res=3):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = bl(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    cu.materials.append(mat)
    parts.objs.append(ob)
    return ob


def poly_tube(parts, name, pts, r, mat, res=2):
    """Köşeleri hafif yuvarlatılmış kırık çizgi boru (hava hatları)"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        v = bl(q)
        p.co = (v.x, v.y, v.z, 1.0)
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    cu.materials.append(mat)
    parts.objs.append(ob)
    return ob


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


def select_only(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def join(parts, name):
    select_only(parts.objs)
    bpy.ops.object.convert(target='MESH')
    objs = [o for o in bpy.context.selected_objects]
    select_only(objs)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def smart_uv(ob, margin, planar=None, angle=66.0):
    """AO atlası: akıllı açma + eşit doku yoğunluğu + paketleme.
    planar: {malzeme adı: 'x' | 'y' | 'z'} → bu malzemeli yüzler o eksene dik düzleme izdüşürülür (oluklu sac gibi
    bir pikselden dar yüzlerin ince ada olup dikiş çizgisi bırakmaması için)."""
    import bmesh
    planar = planar or {}
    select_only([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(ob.data)
    names = [m.name if m else '' for m in ob.data.materials]
    for f in bm.faces:
        f.select = names[f.material_index] not in planar
    bmesh.update_edit_mesh(ob.data)
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bm = bmesh.from_edit_mesh(ob.data)
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        ax = planar.get(names[f.material_index])
        if not ax:
            continue
        for lp in f.loops:
            p = lp.vert.co  # Blender koordinatı: three (x, y, z) = (X, Z, -Y)
            if ax == 'x':
                lp[uvl].uv = (-p.y, p.z)
            elif ax == 'z':
                lp[uvl].uv = (p.x, p.z)
            else:
                lp[uvl].uv = (p.x, -p.y)
    for f in bm.faces:
        f.select = True
    bmesh.update_edit_mesh(ob.data)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def delete_interior(ob, x0, x1, y0, y1, z0, z1):
    """Kutu iç hacminde kalan ve içe bakan yüzleri siler (kasa içi hiç görünmez; atlas ve üçgen tasarrufu)"""
    import bmesh
    from mathutils import Vector
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    c = bl(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    lo = bl((x0, y0, z1))
    hi = bl((x1, y1, z0))
    kill = []
    for f in bm.faces:
        p = f.calc_center_median()
        if lo.x <= p.x <= hi.x and lo.y <= p.y <= hi.y and lo.z <= p.z <= hi.z and f.normal.dot(c - p) > 0.2:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(ob.data)
    bm.free()
    print(f'INTERIOR {ob.name}: {len(kill)} yüz silindi')


# ---------------- tekerlek (385/65 R22,5, çelik disk jant) ----------------
def build_wheel(MW):
    """Tek tekerlek modeli (örneklenir). Dış yüz Blender +Y'ye (three -z) bakar."""
    wp = Parts()

    def lathe(name, prof, mat, steps=96):
        bm = bmesh.new()
        vs = [bm.verts.new((r, w, 0.0)) for r, w in prof]
        es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
        bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 1, 0), angle=math.pi * 2, steps=steps, use_merge=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return add_obj(name, bm, mat, 0.0, wp)

    shoulder = [(0.292, -0.148), (0.33, -0.17), (0.39, -0.188), (0.45, -0.193), (0.495, -0.186), (0.52, -0.172), (0.531, -0.155), (0.536, -0.138)]
    tp = list(shoulder)
    for g in (-0.074, 0.0, 0.074):
        tp += [(0.536, g - 0.012), (0.533, g - 0.009), (0.521, g - 0.006), (0.521, g + 0.006), (0.533, g + 0.009), (0.536, g + 0.012)]
    tp += [(r, -w) for r, w in reversed(shoulder)]

    def tread(bm):
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
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 1, 0), angle=math.pi * 2, steps=192, use_merge=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    tread(bm)
    add_obj('tire', bm, MW['tire'], 0.0, wp)
    lathe('rim_barrel', [(0.3, -0.152), (0.286, -0.145), (0.276, -0.12), (0.272, -0.04), (0.255, 0.0), (0.272, 0.04), (0.276, 0.12), (0.286, 0.145), (0.3, 0.152)], MW['rim'], 64)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=0.268, radius2=0.268, depth=0.014)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 0.035, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bm.verts)
    disc = add_obj('rim_disc', bm, MW['rim'], 0.003, wp)
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
        add_obj('nut', bm, MW['nut'], 0.002, wp)
    lathe('hub_cap', [(0.0, 0.17), (0.04, 0.17), (0.055, 0.165), (0.06, 0.155)], MW['nut'], 32)
    select_only(wp.objs)
    bpy.ops.object.convert(target='MESH')
    for ho in holes:
        bpy.data.objects.remove(ho, do_unlink=True)
    select_only(wp.objs)
    bpy.ops.object.join()
    wheel = bpy.context.view_layer.objects.active
    wheel.name = 'Wheel'
    wheel.data.name = 'Wheel'
    return wheel


def build_wheel_set(MW, name, R, hw, rim_r, twin=False, spacing=0.28, holes=8, steps=160):
    """Parametrik tekerlek (örneklenir): R dış yarıçap, hw lastik yarı genişliği, rim_r jant yarıçapı.
    twin=True: aynı göbekte çift lastik (iç/dış), merkezleri ±spacing/2. Dış yüz Blender +Y'ye (three -z) bakar."""
    wp = Parts()
    sh = R - rim_r  # yanak yüksekliği

    def lathe(nm, prof, mat, st=64, dy=0.0):
        bm = bmesh.new()
        vs = [bm.verts.new((r, w + dy, 0.0)) for r, w in prof]
        es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
        bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 1, 0), angle=math.pi * 2, steps=st, use_merge=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return add_obj(nm, bm, mat, 0.0, wp)

    # lastik kesiti: topuk → şişkin yanak → omuz → 3 boyuna kanallı sırt
    k = [(0.04, 0.78), (0.2, 0.93), (0.45, 1.0), (0.72, 0.97), (0.88, 0.88), (0.96, 0.77), (1.0, 0.68)]
    side = [(rim_r + 0.01 + sh * a, -hw * b) for a, b in k]
    tp = list(side)
    for g in (-0.38, 0.0, 0.38):
        gw = 0.06
        tp += [(R, hw * (g - gw)), (R - 0.006, hw * (g - gw * 0.6)), (R - 0.006, hw * (g + gw * 0.6)), (R, hw * (g + gw))]
    tp += [(r, -w) for r, w in reversed(side)]

    def tire(dy):
        bm = bmesh.new()
        vs = [bm.verts.new((r, w + dy, 0.0)) for r, w in tp]
        es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
        bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 1, 0), angle=math.pi * 2, steps=steps, use_merge=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        period = 2 * math.pi / 40
        for v in bm.verts:
            x, w, z = v.co
            r = math.hypot(x, z)
            if r < R - 0.004 or abs(w - dy) < hw * 0.5:
                continue
            a = math.atan2(z, x) % (2 * math.pi)
            f = ((a / period) + (0.5 if w > dy else 0.0)) % 1.0
            if f < 0.3:
                kk = (r - 0.011) / r
                v.co.x *= kk
                v.co.z *= kk
        add_obj('tire', bm, MW['tire'], 0.0, wp)

    centers = (-spacing / 2, spacing / 2) if twin else (0.0,)
    for c in centers:
        tire(c)
        lathe('rim_barrel', [(rim_r + 0.008, c - hw * 0.8), (rim_r - 0.004, c - hw * 0.72), (rim_r - 0.012, c - hw * 0.4), (rim_r - 0.022, c), (rim_r - 0.012, c + hw * 0.4), (rim_r - 0.004, c + hw * 0.72), (rim_r + 0.008, c + hw * 0.8)], MW['rim'], 48)
    # disk: çiftte iki jantın birleştiği yerde (göbek), tekte jantın dışa yakın kısmında; el delikleri
    dz = 0.0 if twin else hw * 0.25
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=rim_r - 0.02, radius2=rim_r - 0.02, depth=0.012)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, dz, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bm.verts)
    disc = add_obj('rim_disc', bm, MW['rim'], 0.002, wp)
    cutters = []
    for i in range(holes):
        a = 2 * math.pi * (i + 0.5) / holes
        bmh = bmesh.new()
        bmesh.ops.create_cone(bmh, cap_ends=True, segments=16, radius1=rim_r * 0.12, radius2=rim_r * 0.12, depth=0.1)
        bmesh.ops.transform(bmh, matrix=Matrix.Rotation(a, 4, 'Y') @ Matrix.Translation((rim_r * 0.68, dz, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bmh.verts)
        me = bpy.data.meshes.new('hole')
        bmh.to_mesh(me)
        ho = bpy.data.objects.new('hole', me)
        scene.collection.objects.link(ho)
        cutters.append(ho)
    for ho in cutters:
        md = disc.modifiers.new('hole', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = ho
        md.solver = 'EXACT'
    hub_out = (spacing / 2 + hw * 0.7) if twin else hw * 0.85
    lathe('hub', [(0.0, hub_out), (0.05, hub_out), (0.06, hub_out - 0.01), (0.065, dz + 0.04), (0.09, dz + 0.03), (0.095, dz + 0.008)], MW['hub'], 40)
    for i in range(10 if R > 0.45 else 8):
        n = 10 if R > 0.45 else 8
        a = 2 * math.pi * i / n
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.013, radius2=0.013, depth=0.03)
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(a, 4, 'Y') @ Matrix.Translation((0.075, dz + 0.02, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bm.verts)
        add_obj('nut', bm, MW['nut'], 0.002, wp)
    select_only(wp.objs)
    bpy.ops.object.convert(target='MESH')
    for ho in cutters:
        bpy.data.objects.remove(ho, do_unlink=True)
    select_only(wp.objs)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    # bool kesicilerden kalan boş malzeme yuvaları jantın malzemesiyle dolar
    for i, mt in enumerate(ob.data.materials):
        if mt is None:
            ob.data.materials[i] = MW['rim']
    return ob


def flange_path(parts, name, pts, w, t, z, mat, bevel=0.003):
    """Yandan görünüşte (x, y) çizgisini izleyen, z'de w genişlikte, t kalınlıkta şerit (kiriş başlığı)"""
    bm = bmesh.new()
    rings = []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        if ny < 0:
            nx, ny = -nx, -ny
        rings.append([
            bm.verts.new(bl((x, y, z - w / 2))),
            bm.verts.new(bl((x, y, z + w / 2))),
            bm.verts.new(bl((x + nx * t, y + ny * t, z + w / 2))),
            bm.verts.new(bl((x + nx * t, y + ny * t, z - w / 2))),
        ])
    for i in range(n - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(4):
            bm.faces.new([A[j], A[(j + 1) % 4], B[(j + 1) % 4], B[j]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, bevel, parts)


def arc(cx, cy, r, a0, a1, n):
    """(x, y) yay noktaları, a0 → a1 (radyan)"""
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def pchip(xs, ys):
    """Monoton kübik ara değerleme (aşma yapmaz): kontrol noktalarından pürüzsüz profil fonksiyonu f(x)"""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]

    def f(x):
        x = min(max(x, xs[0]), xs[-1])
        i = 0
        while i < n - 2 and x > xs[i + 1]:
            i += 1
        t = (x - xs[i]) / h[i]
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h[i] * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h[i] * m[i + 1])
    return f


def loft(parts, name, rings, mat, tile=(1.0, 1.0), caps=(None, None)):
    """Aynı nokta sayılı kapalı halkalar ([(x, y, z), ...]) arasında yüzey (tank kabuğu). Tekrarlanan doku UV'si:
    u = x / tile[0], v = halka boyunca yay uzunluğu / tile[1] (dikiş ilk ve son nokta arasında: halkayı altta başlat).
    caps: uçları kapatan yelpazenin merkez noktaları (None: açık)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    n = len(rings[0])
    V = [[bm.verts.new(bl(p)) for p in ring] for ring in rings]
    arcs = []
    for ring in rings:
        s = [0.0]
        for i in range(1, n + 1):
            s.append(s[-1] + math.dist(ring[i - 1], ring[i % n]))
        arcs.append(s)

    def uv(r, i):
        return (rings[r][i % n][0] / tile[0], arcs[r][i] / tile[1])
    for r in range(len(rings) - 1):
        for i in range(n):
            f = bm.faces.new([V[r][i], V[r][(i + 1) % n], V[r + 1][(i + 1) % n], V[r + 1][i]])
            for lp, t in zip(f.loops, (uv(r, i), uv(r, i + 1), uv(r + 1, i + 1), uv(r + 1, i))):
                lp[uvl].uv = t
    for r, c in ((0, caps[0]), (len(rings) - 1, caps[1])):
        if c is None:
            continue
        cv = bm.verts.new(bl(c))
        for i in range(n):
            f = bm.faces.new([cv, V[r][i], V[r][(i + 1) % n]])
            a, b = uv(r, i), uv(r, i + 1)
            for lp, t in zip(f.loops, ((c[0] / tile[0], (a[1] + b[1]) / 2), a, b)):
                lp[uvl].uv = t
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, 0.0, parts, sharp=60)


def arch(parts, name, cx, cy, r, t, a0, a1, z0, z1, mat, n=24):
    """Yandan görünüşte yay biçimli şerit (çamurluk): merkez (cx, cy), iç yarıçap r, kalınlık t, açı a0 → a1, z0..z1"""
    bm = bmesh.new()
    rings = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new(bl((cx + rr * c, cy + rr * s, z))) for rr, z in ((r, z0), (r, z1), (r + t, z1), (r + t, z0))])
    for i in range(n):
        A, B = rings[i], rings[i + 1]
        for j in range(4):
            bm.faces.new([A[j], A[(j + 1) % 4], B[(j + 1) % 4], B[j]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, 0.003, parts)


# ---------------- tekrarlanan dokular (numpy ile üretilir, GLB'ye gömülür) ----------------
def np_image(name, arr, non_color=False):
    """arr: (yükseklik, genişlik, 3) 0..1; satır 0 = görüntünün altı (Blender düzeni)"""
    import numpy as np
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(arr[:, :, :3], 0, 1)
    img.pixels[:] = rgba.ravel()
    img.update()
    img.pack()
    return img


def _periodic_noise(n, size, rng, octaves=6):
    """[0,1) aralığında tekrarlanan (dikişsiz) 1B gürültü"""
    import numpy as np
    t = np.arange(size) / size
    out = np.zeros(size)
    for k in range(1, octaves + 1):
        out += np.sin(2 * np.pi * (k * n * t) + rng.uniform(0, 2 * np.pi)) / k
    return out / 1.6


def height_to_normal(hmap, strength):
    """Yükseklik haritasından teğet uzayı normal haritası (OpenGL / glTF düzeni, dikişsiz)"""
    import numpy as np
    dx = (np.roll(hmap, -1, axis=1) - np.roll(hmap, 1, axis=1)) * 0.5
    dy = (np.roll(hmap, -1, axis=0) - np.roll(hmap, 1, axis=0)) * 0.5
    n = np.dstack([-dx * strength, -dy * strength, np.ones_like(hmap)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def wood_tile(w=1024, h=512, planks=4, base=(0.6, 0.5, 0.4), seed=3, joints_per_plank=(1, 2), tint=0.05):
    """Boyuna sert ağaç kalasları (u boyunca), dikişsiz. Döner: (renk, normal). Kalas aralarında koyu derz, uç birleşimleri."""
    import numpy as np
    rng = np.random.default_rng(seed)
    col = np.zeros((h, w, 3), dtype=np.float32)
    hgt = np.ones((h, w), dtype=np.float32)
    ph = h // planks
    u = np.arange(w) / w
    for p in range(planks):
        rows = slice(p * ph, (p + 1) * ph)
        t = (np.arange(ph) + 0.5) / ph  # kalas içinde enine
        # uç birleşimleri: kalas başına 1-2 derz, her parça kendi tonunda
        joints = sorted(rng.uniform(0, 1, rng.integers(*joints_per_plank)))
        seg = np.searchsorted(joints, u) % len(joints)
        tints = rng.uniform(-tint, tint * 0.8, len(joints))
        warm = rng.uniform(-0.02, 0.02, len(joints))
        n1 = _periodic_noise(2 + p, w, rng)
        n2 = _periodic_noise(9 + p, w, rng)
        tt, nn = np.meshgrid(t, n1)
        _, nn2 = np.meshgrid(t, n2)
        grain = 0.5 + 0.5 * np.sin(2 * np.pi * (tt * rng.uniform(7, 11) + 0.55 * nn + 0.12 * nn2))
        grain = grain ** 3
        fine = rng.normal(0, 0.02, (w, ph))
        # yıpranma: kalas boyunca düşük frekanslı açık/koyu lekeler
        stain = 0.06 * _periodic_noise(3 + p, w, rng, 3)[:, None]
        shade = (0.9 + 0.1 * grain + fine + stain).T  # (ph, w)
        tn = tints[seg][None, :]
        wr = warm[seg][None, :]
        for c, b in enumerate(base):
            col[rows, :, c] = (b + tn + (wr if c == 0 else -wr * 0.5)) * shade
        hgt[rows, :] = 1.0 - 0.025 * grain.T
        # derzler (kalas arası) ve uç birleşimleri
        col[p * ph:p * ph + 2, :, :] *= 0.32
        hgt[p * ph:p * ph + 2, :] = 0.0
        for j in joints:
            jx = int(j * w) % w
            col[rows, jx:jx + 2, :] *= 0.38
            hgt[rows, jx:jx + 2] = 0.1
    return np.clip(col, 0, 1), height_to_normal(hgt, 6.0)


def teardrop_tile(n=256, cells=4, strength=5.0):
    """Gözyaşı desenli (damla) çelik sac normal haritası: hücre başına 45° eğik uzun kabartma, yönler dama gibi değişir"""
    import numpy as np
    y, x = np.mgrid[0:n, 0:n] / n * cells
    cx = np.floor(x) + 0.5
    cy = np.floor(y) + 0.5
    flip = ((np.floor(x) + np.floor(y)) % 2) * 2 - 1
    dx, dy = x - cx, y - cy
    a = np.pi / 4 * flip
    u = dx * np.cos(a) + dy * np.sin(a)
    v = -dx * np.sin(a) + dy * np.cos(a)
    d = (u / 0.36) ** 2 + (v / 0.1) ** 2
    hgt = np.clip(1 - d, 0, 1) ** 0.5
    return height_to_normal(hgt.astype(np.float32), strength)


def _wrap_noise2d(h, w, rng, fu, fv, octaves=4):
    """Dikişsiz 2B düşük frekanslı gürültü (periyodik sinüs toplamı), yaklaşık -1..1"""
    import numpy as np
    v, u = np.mgrid[0:h, 0:w]
    u = u / w
    v = v / h
    out = np.zeros((h, w), dtype=np.float32)
    for k in range(1, octaves + 1):
        for _ in range(2):
            a = rng.integers(1, fu * k + 1)
            b = rng.integers(0, fv * k + 1)
            out += np.sin(2 * np.pi * (a * u + b * v) + rng.uniform(0, 2 * np.pi)) / k
    return out / (1.2 * octaves ** 0.5)


def _blur_axis(a, r, axis):
    """Dikişsiz kutu bulanıklığı (tek eksen)"""
    import numpy as np
    out = np.zeros_like(a)
    for d in range(-r, r + 1):
        out += np.roll(a, d, axis=axis)
    return out / (2 * r + 1)


def hardwood_tile(w=2048, h=512, planks=4, tile=(4.0, 0.6), bolt_u=(), seed=7, fresh=(0.42, 0.29, 0.19), weathered=(0.49, 0.45, 0.39), weather=(0.3, 0.75)):
    """Lowbed sert ağaç tabanı (apitong benzeri), dikişsiz karo. Kalaslar u boyunca; uzun kalaslar, kalas başına bir uç birleşimi.
    Kalas başına farklı yıpranma (kızıl kahveden griye), damar, lif çizgileri, lekeler, kirli derzler, traverslere hizalı cıvata
    sıraları (bolt_u: karo içinde u konumları, 0..1). Döner: (renk, normal, ORM[R=1, G=pürüzlülük, B=metallik])."""
    import numpy as np
    rng = np.random.default_rng(seed)
    col = np.zeros((h, w, 3), dtype=np.float32)
    hgt = np.ones((h, w), dtype=np.float32)
    rough = np.zeros((h, w), dtype=np.float32)
    metal = np.zeros((h, w), dtype=np.float32)
    ph = h // planks
    u = np.arange(w) / w
    fresh = np.array(fresh, dtype=np.float32)
    weathered = np.array(weathered, dtype=np.float32)
    smudge = _wrap_noise2d(h, w, rng, 6, 3, 4)
    for p in range(planks):
        r0 = p * ph
        rows = slice(r0, r0 + ph)
        t = (np.arange(ph) + 0.5) / ph
        joints = [rng.uniform(0, 1)]
        if rng.uniform() < 0.35:
            joints.append((joints[0] + rng.uniform(0.3, 0.7)) % 1.0)
        joints.sort()
        seg = np.searchsorted(joints, u) % len(joints)
        wk = rng.uniform(weather[0], weather[1], len(joints))  # yıpranma (griye dönüş)
        dk = rng.uniform(-0.07, 0.05, len(joints))  # ton
        rk = rng.uniform(-0.03, 0.04, len(joints))  # kızıllık
        n1 = _periodic_noise(2 + p, w, rng)
        n2 = _periodic_noise(11 + p, w, rng)
        tt, nn = np.meshgrid(t, n1)
        _, nn2 = np.meshgrid(t, n2)
        grain = 0.5 + 0.5 * np.sin(2 * np.pi * (tt * rng.uniform(6, 10) + 0.6 * nn + 0.15 * nn2))
        grain = (grain ** 2).T  # (ph, w)
        fibre = _blur_axis(rng.normal(0, 1, (ph, w)).astype(np.float32), 9, 1) * 0.11
        wgt = wk[seg][None, :]
        base = fresh[None, None, :] * (1 - wgt[..., None]) + weathered[None, None, :] * wgt[..., None]
        base = base + dk[seg][None, :, None]
        base[..., 0] += rk[seg][None, :]
        shade = 0.8 + 0.2 * (1 - grain) + fibre + 0.07 * smudge[rows]
        c = base * shade[..., None]
        # kalas kenarları kirli/koyu (derze doğru), uç birleşimleri
        edge = np.minimum(t, 1 - t)[:, None]
        c *= (0.72 + 0.28 * np.clip(edge * 18, 0, 1))[..., None]
        col[rows] = c
        hgt[rows] = 1.0 - 0.02 * grain - 0.5 * np.clip(1 - edge * 25, 0, 1)
        rough[rows] = 0.74 + 0.12 * wgt - 0.05 * grain
        for j in joints:
            jx = int(j * w) % w
            col[rows, jx:jx + 3] *= 0.35
            hgt[rows, jx:jx + 3] = 0.2
        # derz (kalas arası boşluk)
        col[r0:r0 + 3] = col[r0:r0 + 3] * 0.15
        hgt[r0:r0 + 3] = 0.0
        rough[r0:r0 + 3] = 0.95
    # cıvata sıraları (kalas başına iki gömme baş): u ve v ölçeği farklı, elips mesafe
    pu, pv = w / tile[0], h / tile[1]
    rr = 0.012
    vv, uu = np.mgrid[0:h, 0:w]
    for bu in bolt_u:
        cx = bu * w
        for p in range(planks):
            for tv in (0.28, 0.72):
                cy = (p + tv) * ph
                dxu = (uu - cx + w / 2) % w - w / 2
                d = np.sqrt((dxu / (rr * pu)) ** 2 + ((vv - cy) / (rr * pv)) ** 2)
                head = d < 1.0
                rim = (d >= 1.0) & (d < 1.35)
                col[head] = col[head] * 0.25 + np.array([0.29, 0.28, 0.27]) * 0.75
                col[rim] *= 0.45
                hgt[head] = np.maximum(hgt[head], 1.02 - 0.03 * d[head])
                hgt[rim] = 0.85
                rough[head] = 0.45
                metal[head] = 0.6
    orm = np.dstack([np.ones_like(rough), np.clip(rough, 0, 1), metal])
    return np.clip(col, 0, 1), height_to_normal(hgt, 7.0), orm


def galvanized_checker_tile(n=512, cells=4, seed=5):
    """Sıcak daldırma galvaniz damla desenli sac (0,3 m karo): kristal (çiçeklenme) deseni, damlalar trafikten parlak,
    aralar kirli. Döner: (renk, normal, ORM)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n * cells
    cx = np.floor(x) + 0.5
    cy = np.floor(y) + 0.5
    flip = ((np.floor(x) + np.floor(y)) % 2) * 2 - 1
    dx, dy = x - cx, y - cy
    a = np.pi / 4 * flip
    uu = dx * np.cos(a) + dy * np.sin(a)
    vv = -dx * np.sin(a) + dy * np.cos(a)
    d = (uu / 0.36) ** 2 + (vv / 0.1) ** 2
    drop = np.clip(1 - d, 0, 1) ** 0.5
    # galvaniz kristalleri: dikişsiz Voronoi hücreleri, hücre başına ton
    pts = rng.uniform(0, 1, (36, 2))
    tone = rng.uniform(-0.07, 0.07, 36)
    gy, gx = np.mgrid[0:n, 0:n] / n
    best = np.full((n, n), 9.0)
    idx = np.zeros((n, n), dtype=np.int32)
    for i, (px, py) in enumerate(pts):
        ddx = np.abs(gx - px)
        ddy = np.abs(gy - py)
        dd = np.minimum(ddx, 1 - ddx) ** 2 + np.minimum(ddy, 1 - ddy) ** 2
        m = dd < best
        best[m] = dd[m]
        idx[m] = i
    span = 0.6 + tone[idx]
    fine = _blur_axis(rng.normal(0, 1, (n, n)).astype(np.float32), 2, 1) * 0.02
    dirt = np.clip(1 - drop * 2.5, 0, 1) * (0.5 + 0.5 * _wrap_noise2d(n, n, rng, 3, 3, 3))
    base = span + fine - 0.12 * dirt
    col = np.dstack([base * 0.97, base * 0.99, base * 1.02])
    rough = 0.5 - 0.18 * np.clip(drop * 2, 0, 1) + 0.15 * dirt
    orm = np.dstack([np.ones((n, n)), np.clip(rough, 0, 1), np.full((n, n), 0.85)])
    return np.clip(col, 0, 1).astype(np.float32), height_to_normal(drop.astype(np.float32), 5.0), orm.astype(np.float32)


def brushed_alu_tile(n=512, seed=9):
    """Fırçalanmış alüminyum (u boyunca çizgiler), dikişsiz. Döner: (renk, ORM)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    streak = _blur_axis(rng.normal(0, 1, (n, n)).astype(np.float32), 40, 1)
    streak = streak / (np.abs(streak).max() + 1e-6)
    scratch = (rng.uniform(0, 1, (n, n)) > 0.997).astype(np.float32)
    scratch = _blur_axis(scratch, 25, 1) * 6
    soft = _wrap_noise2d(n, n, rng, 2, 2, 2)
    b = 0.74 + 0.035 * streak + 0.03 * scratch + 0.025 * soft
    col = np.dstack([b * 0.985, b * 0.995, b * 1.01])
    rough = 0.42 + 0.06 * np.abs(streak) - 0.05 * scratch + 0.03 * soft
    orm = np.dstack([np.ones((n, n)), np.clip(rough, 0.05, 1), np.ones((n, n))])
    return np.clip(col, 0, 1).astype(np.float32), orm.astype(np.float32)


def tank_metal_tile(n=512, seed=21, tone=0.77, rough=0.3):
    """Büyük metal yüzey (alüminyum tank kabuğu) için ince fırça izi: yalnız u boyunca çizgiler, iki boyutlu leke yok
    (geniş metal yüzeyde pürüzlülük lekeleri yansımada dalga gibi görünür). Döner: (renk, ORM)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    streak = _blur_axis(rng.normal(0, 1, (n, n)).astype(np.float32), 60, 1)
    streak = streak / (np.abs(streak).max() + 1e-6)
    fine = _blur_axis(rng.normal(0, 1, (n, n)).astype(np.float32), 8, 1)
    fine = fine / (np.abs(fine).max() + 1e-6)
    b = tone + 0.018 * streak + 0.01 * fine
    col = np.dstack([b * 0.99, b * 0.997, b * 1.01])
    r = rough + 0.025 * np.abs(streak) + 0.012 * fine
    orm = np.dstack([np.ones((n, n)), np.clip(r, 0.05, 1), np.ones((n, n))])
    return np.clip(col, 0, 1).astype(np.float32), orm.astype(np.float32)


def tex_material(name, color, rough, metal, albedo=None, normal=None, normal_strength=1.0, coat=0.0, orm=None):
    """Principled + isteğe bağlı renk, normal ve ORM (G=pürüzlülük, B=metallik) dokusu (tekrarlanan UV ile kullanılır)"""
    m = material(name, color, rough, metal, coat)
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    if orm is not None:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = orm
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], p.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], p.inputs['Metallic'])
    if albedo is not None:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = albedo
        nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    if normal is not None:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = normal
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    return m


def planar_uv(ob, scales):
    """Tekrarlanan dokulu nesne: her yüz baskın normal eksenine göre düzlemsel UV alır.
    scales: {malzeme adı: (u metresi, v metresi)}; ağaç kalasları yatay yüzlerde x, dikey (x'e bakan) yüzlerde y boyuncadır."""
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(ob.data)
    # adı sabit: birleştirilen (join) parçaların UV katmanları ada göre eşleşir
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new('UVMap')
    names = [m.name for m in ob.data.materials]
    for f in bm.faces:
        su, sv = scales.get(names[f.material_index], (1.0, 1.0))
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            p = lp.vert.co  # Blender: three (x, y, z) = (X, Z, -Y)
            if ax == 2:  # yatay yüz (three y): u = x, v = z
                uv = (p.x / su, -p.y / sv)
            elif ax == 0:  # x'e bakan dikey yüz: u = y, v = z
                uv = (p.z / su, -p.y / sv)
            else:  # z'ye bakan dikey yüz: u = x, v = y
                uv = (p.x / su, p.z / sv)
            lp[uvl].uv = uv
    bm.to_mesh(ob.data)
    bm.free()


# ---------------- logo/çıkartma ----------------
def logo_material(name, path):
    img = bpy.data.images.load(os.path.abspath(path))
    lm = bpy.data.materials.new(name)
    lm.use_nodes = True
    nt = lm.node_tree
    p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    nt.links.new(t.outputs['Alpha'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = 0.3
    if hasattr(lm, 'blend_method'):
        lm.blend_method = 'BLEND'
    if hasattr(lm, 'surface_render_method'):
        lm.surface_render_method = 'BLENDED'
    return lm


def decal_mesh(name, quads, mat):
    """quads: her biri 4 köşe (sol alt, sağ alt, sağ üst, sol üst; dışarıdan bakınca)"""
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
    me.materials.append(mat)
    return ob


def side_quad(xc, yc, w, h, z, s):
    """+z (s=1) ya da -z (s=-1) yan yüzünde, dışarıdan okunur dörtgen"""
    a, b = (xc - w / 2, xc + w / 2) if s > 0 else (xc + w / 2, xc - w / 2)
    return [(a, yc - h / 2, z), (b, yc - h / 2, z), (b, yc + h / 2, z), (a, yc + h / 2, z)]


def rear_quad(x, yc, zc, w, h):
    """Arkaya (+x) bakan yüzde, arkadan okunur dörtgen (arkadan bakınca sağ = -z)"""
    return [(x, yc - h / 2, zc + w / 2), (x, yc - h / 2, zc - w / 2), (x, yc + h / 2, zc - w / 2), (x, yc + h / 2, zc + w / 2)]


# ---------------- sitenin okuyacağı bağlantı noktaları ----------------
def write_anchors(path, d):
    """src/configurator/engine/<tip>-anchors.json (şema: src/configurator/engine/baked.ts → BakedAnchors).
    Sayılar 4 basamağa yuvarlanır (kayan nokta gürültüsü dosyayı kirletmesin)."""
    import json

    def rnd(v):
        if isinstance(v, float):
            return round(v, 4)
        if isinstance(v, (list, tuple)):
            return [rnd(x) for x in v]
        if isinstance(v, dict):
            return {k: rnd(x) for k, x in v.items()}
        return v

    import re
    text = json.dumps(rnd(d), indent=2, ensure_ascii=False)
    # yalnız sayı içeren dizileri tek satıra topla ([x, y] / [x, y, z])
    text = re.sub(r'\[\s+([-0-9.e,\s]+?)\s+\]', lambda m: '[' + ', '.join(t.strip() for t in m.group(1).split(',')) + ']', text)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text + '\n')
    print('ANCHORS', path)


def rect_x(x, y0, y1, h):
    """x düzleminde (önden görünüş) dikdörtgen kontur: [z, y] köşeleri"""
    return [[x, y0, h], [x, y1, h], [x, y1, -h], [x, y0, -h]]


def rect_y(y, x0, x1, h):
    """y düzleminde (üstten görünüş) dikdörtgen kontur"""
    return [[x0, y, h], [x1, y, h], [x1, y, -h], [x0, y, -h]]


# ---------------- AO pişirme ve glTF çıkışı ----------------
def bake_ao(objs_imgs, fallback, samples=64, distance=0.6):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World')
    scene.world.light_settings.distance = distance
    targets = []
    for ob, size, name in objs_imgs:
        # boş yuva (bool kesicilerden kalır) nesnenin kendi malzemesiyle dolar: başka nesnenin malzemesi verilirse o
        # malzemenin etkin pişirme düğümü bu nesnenin dokusuna döner ve asıl nesnesi yanlış dokuya pişer
        own = next((m for m in ob.data.materials if m is not None), fallback)
        for i, mt in enumerate(ob.data.materials):
            if mt is None:
                ob.data.materials[i] = own
        img = bpy.data.images.new(name, size, size, alpha=False)
        img.generated_color = (1, 1, 1, 1)
        seen = set()
        for mat in ob.data.materials:
            if mat.name in seen:
                continue
            seen.add(mat.name)
            nt = mat.node_tree
            n = nt.nodes.new('ShaderNodeTexImage')
            n.image = img
            n.name = 'AO'
            nt.nodes.active = n
        targets.append((ob, img))
    # aynı malzeme iki pişirme hedefinde olamaz (etkin düğüm tek): olursa uyar
    owners = {}
    for ob, _ in targets:
        for m in set(ob.data.materials):
            if m.name in owners and owners[m.name] != ob.name:
                print(f'UYARI: {m.name} malzemesi hem {owners[m.name]} hem {ob.name} nesnesinde; AO yanlış dokuya pişer')
            owners[m.name] = ob.name
    return targets


def run_bake(ob, img, hide=()):
    for h in hide:
        h.hide_render = True
    select_only([ob])
    bpy.ops.object.bake(type='AO', margin=6, use_clear=True)
    img.pack()
    for h in hide:
        h.hide_render = False


def tiled_ao_setup(ob, size, name, angle=35.0, margin=0.003):
    """Tekrarlanan dokulu büyük yüzey (tank kabuğu) için ikinci UV ('AOUV', akıllı açma) ve AO görüntü düğümü.
    Renk/pürüzlülük ilk UV'deki tekrarlanan dokudan gelir; AO ikinci UV'den (glTF occlusion texCoord 1).
    Pişirme etkin UV'ye yazılır: AOUV etkin bırakılır, dışa aktarımda render UV'si ilk katmandır."""
    me = ob.data
    me.uv_layers[0].active_render = True
    lay = me.uv_layers.new(name='AOUV')
    me.uv_layers.active = lay
    select_only([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.generated_color = (1, 1, 1, 1)
    for mat in dict.fromkeys(m for m in me.materials if m):
        nt = mat.node_tree
        uvn = nt.nodes.new('ShaderNodeUVMap')
        uvn.uv_map = 'AOUV'
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        n.name = 'AO'
        nt.links.new(uvn.outputs['UV'], n.inputs['Vector'])
        nt.nodes.active = n
    return img


def tiled_ao_finish(ob, img, gamma=0.75):
    """Pişen AO'ya üs uygular (bake_surface ile aynı yumuşatma) ve glTF occlusion girişine bağlar"""
    import numpy as np
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)
    a = np.clip(px[:, 0], 0.0, 1.0) ** gamma
    px[:, 0] = px[:, 1] = px[:, 2] = a
    img.pixels[:] = px.ravel()
    img.update()
    img.pack()
    link_occlusion([ob])


def link_occlusion(objs):
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    for ob in objs:
        for mat in set(ob.data.materials):
            nt = mat.node_tree
            if 'AO' not in nt.nodes or 'AOLinked' in nt.nodes:
                continue
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(nt.nodes['AO'].outputs['Color'], sep.inputs['Color'])
            g = nt.nodes.new('ShaderNodeGroup')
            g.node_tree = grp
            g.name = 'AOLinked'
            nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])


# ---------------- yüzey pişirme: renk (toz, kenar aşınması) + ORM ----------------
SURFACE_DEFAULT = {'grime': 0.5, 'wear': 0.0, 'low_h': 0.9, 'dust_mix': 0.55}
DUST = (0.15, 0.135, 0.11)  # doğrusal: açık toprak grisi yol tozu
BARE = (0.3, 0.3, 0.31)  # doğrusal: boyası aşınmış çelik


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _vmix(nt, a, b, f):
    """a + (b - a) * f; a, b: soket ya da (r, g, b); f: skaler soket"""
    def vec(v):
        if isinstance(v, (tuple, list)):
            c = nt.nodes.new('ShaderNodeCombineXYZ')
            for i, x in enumerate(v):
                c.inputs[i].default_value = x
            return c.outputs[0]
        return v
    a, b = vec(a), vec(b)
    sub = nt.nodes.new('ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    nt.links.new(b, sub.inputs[0])
    nt.links.new(a, sub.inputs[1])
    sc = nt.nodes.new('ShaderNodeVectorMath')
    sc.operation = 'SCALE'
    nt.links.new(sub.outputs[0], sc.inputs[0])
    nt.links.new(f, sc.inputs['Scale'])
    add = nt.nodes.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    nt.links.new(a, add.inputs[0])
    nt.links.new(sc.outputs[0], add.inputs[1])
    return add.outputs[0]


def bake_surface(targets, profiles, samples=16, ao_gamma=0.75):
    """AO'su pişirilmiş nesnelere renk (albedo) ve ORM (R=AO, G=pürüzlülük, B=metallik) dokusu pişirir, malzemeleri bu
    dokularla glTF'e uygun bağlar. targets: [(nesne, boyut, ad öneki)] (malzemelerde 'AO' görüntü düğümü olmalı).
    profiles: {malzeme adı: {'grime': toz 0..1, 'wear': kenar aşınması 0..1, 'low_h': tozun başladığı yükseklik (m),
    'dust_mix': tozun renge karışma oranı}}. Toz: çukurlarda (AO) ve yere yakın yüzeylerde; aşınma: dışbükey kenarlarda,
    gürültüyle seyrek. Sitede güneş ışığında da görünür (AO yalnız dolaylı ışığı etkiler)."""
    scene.cycles.samples = samples
    grp = bpy.data.node_groups.get('glTF Material Output')
    if grp is None:
        grp = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    for ob, size, prefix in targets:
        alb = bpy.data.images.new(prefix + '_albedo', size, size, alpha=False)
        orm = bpy.data.images.new(prefix + '_orm', size, size, alpha=False)
        orm.colorspace_settings.name = 'Non-Color'
        info = []
        for mat in dict.fromkeys(m for m in ob.data.materials if m):
            nt = mat.node_tree
            p = nt.nodes['Principled BSDF']
            out = nt.nodes['Material Output']
            base = tuple(p.inputs['Base Color'].default_value)[:3]
            r0 = p.inputs['Roughness'].default_value
            m0 = p.inputs['Metallic'].default_value
            pr = {**SURFACE_DEFAULT, **profiles.get(mat.name, {})}
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(nt.nodes['AO'].outputs['Color'], sep.inputs['Color'])
            ao = sep.outputs['Red']
            geo = nt.nodes.new('ShaderNodeNewGeometry')
            xyz = nt.nodes.new('ShaderNodeSeparateXYZ')
            nt.links.new(geo.outputs['Position'], xyz.inputs[0])
            nlo = nt.nodes.new('ShaderNodeTexNoise')
            nlo.inputs['Scale'].default_value = 1.4
            nlo.inputs['Detail'].default_value = 4.0
            nt.links.new(geo.outputs['Position'], nlo.inputs['Vector'])
            nhi = nt.nodes.new('ShaderNodeTexNoise')
            nhi.inputs['Scale'].default_value = 28.0
            nhi.inputs['Detail'].default_value = 2.0
            nt.links.new(geo.outputs['Position'], nhi.inputs['Vector'])
            # toz maskesi
            cav = _math(nt, 'POWER', _math(nt, 'SUBTRACT', 1.0, ao, True), 1.3)
            low = _math(nt, 'DIVIDE', _math(nt, 'SUBTRACT', pr['low_h'], xyz.outputs['Z']), pr['low_h'])
            low = _math(nt, 'MAXIMUM', _math(nt, 'MINIMUM', low, 1.0), 0.0)
            mix = _math(nt, 'ADD', _math(nt, 'MULTIPLY', cav, 0.6), _math(nt, 'MULTIPLY', low, 0.5))
            g = _math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', mix, pr['grime']), _math(nt, 'ADD', nlo.outputs['Fac'], 0.5), True)
            # kenar aşınması
            bev = nt.nodes.new('ShaderNodeBevel')
            bev.samples = 8
            bev.inputs['Radius'].default_value = 0.006
            dot = nt.nodes.new('ShaderNodeVectorMath')
            dot.operation = 'DOT_PRODUCT'
            nt.links.new(bev.outputs['Normal'], dot.inputs[0])
            nt.links.new(geo.outputs['Normal'], dot.inputs[1])
            edge = _math(nt, 'SUBTRACT', _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', 1.0, dot.outputs['Value']), 40.0), 0.15, True)
            spot = _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', nhi.outputs['Fac'], 0.47), 8.0, True)
            wear = _math(nt, 'MULTIPLY', _math(nt, 'MULTIPLY', edge, spot), pr['wear'], True)
            col = _vmix(nt, _vmix(nt, base, DUST, _math(nt, 'MULTIPLY', g, pr['dust_mix'])), BARE, wear)
            rough = _math(nt, 'ADD', _math(nt, 'ADD', r0, _math(nt, 'MULTIPLY', g, 0.28)), _math(nt, 'MULTIPLY', _math(nt, 'SUBTRACT', nlo.outputs['Fac'], 0.5), 0.08))
            rough = _math(nt, 'ADD', rough, _math(nt, 'MULTIPLY', wear, 0.38 - r0), True)
            metal = _math(nt, 'ADD', _math(nt, 'MULTIPLY', m0, _math(nt, 'SUBTRACT', 1.0, _math(nt, 'MULTIPLY', g, 0.6))), _math(nt, 'MULTIPLY', wear, 0.85 - m0), True)
            comb = nt.nodes.new('ShaderNodeCombineColor')
            nt.links.new(_math(nt, 'POWER', ao, ao_gamma), comb.inputs[0])
            nt.links.new(rough, comb.inputs[1])
            nt.links.new(metal, comb.inputs[2])
            emit = nt.nodes.new('ShaderNodeEmission')
            n_alb = nt.nodes.new('ShaderNodeTexImage')
            n_alb.image = alb
            n_orm = nt.nodes.new('ShaderNodeTexImage')
            n_orm.image = orm
            nt.links.new(emit.outputs[0], out.inputs['Surface'])
            info.append((nt, p, out, col, comb.outputs[0], emit, n_alb, n_orm))
        for target_img, pick in ((alb, 3), (orm, 4)):
            for row in info:
                nt, emit = row[0], row[5]
                nt.links.new(row[pick], emit.inputs['Color'])
                nt.nodes.active = row[6] if target_img is alb else row[7]
            select_only([ob])
            bpy.ops.object.bake(type='EMIT', margin=6, use_clear=True)
            target_img.pack()
        # glTF bağlantısı: renk dokusu, ORM'den pürüzlülük/metallik, AO (glTF Material Output → occlusion)
        for nt, p, out, col, ormc, emit, n_alb, n_orm in info:
            nt.links.new(p.outputs['BSDF'], out.inputs['Surface'])
            nt.links.new(n_alb.outputs['Color'], p.inputs['Base Color'])
            s2 = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(n_orm.outputs['Color'], s2.inputs['Color'])
            nt.links.new(s2.outputs['Green'], p.inputs['Roughness'])
            nt.links.new(s2.outputs['Blue'], p.inputs['Metallic'])
            gn = nt.nodes.new('ShaderNodeGroup')
            gn.node_tree = grp
            nt.links.new(s2.outputs['Red'], gn.inputs['Occlusion'])
        print('SURFACE', ob.name, size)


def export_glb(path, objs, quality=82):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_image_format='WEBP',
        export_image_quality=quality,
        export_cameras=False,
        export_lights=False,
    )
    print(f'EXPORTED {path} {os.path.getsize(path) / 1024:.0f} KB')


# ---------------- ortak alt takımlar (silo.py, tanker.py, ...) ----------------
def landing_gear(C, x, lz, bz, top, M, mount_y0=None, braces=True):
    """JOST tipi iki iniş ayağı (z = ±lz), ara mil, dişli kutusu ve kol (+z), çaprazlar; ayak üstü `top`, ayaklar yerde.
    bz: bağlandığı kirişin yanal ekseni (bağlantı plakası dış yüzüne). M: 'paint', 'dark', 'rubber'."""
    y0 = (mount_y0 if mount_y0 is not None else top - 0.42)
    for s in (-1, 1):
        z = s * lz
        box2(C, 'leg_mount', x - 0.16, x + 0.16, y0, top + 0.02, s * (bz + 0.006), s * (bz + 0.018), M['paint'], 0.003)
        box2(C, 'leg_spacer', x - 0.08, x + 0.08, y0 + 0.05, top - 0.02, s * (bz + 0.018), s * (lz - 0.07), M['paint'], 0.004)
        h_out = top - 0.42
        box(C, 'leg_outer', (0.14, h_out, 0.14), (x, top - h_out / 2, z), M['dark'], 0.008)
        box(C, 'leg_collar', (0.16, 0.05, 0.16), (x, top - h_out - 0.005, z), M['dark'], 0.006)
        box(C, 'leg_inner', (0.11, top - h_out - 0.08, 0.11), (x, (top - h_out - 0.03) / 2 + 0.045, z), M['dark'], 0.006)
        box(C, 'leg_ball', (0.09, 0.07, 0.09), (x, 0.07, z), M['dark'], 0.015)
        box(C, 'leg_foot', (0.26, 0.032, 0.24), (x, 0.016, z), M['dark'], 0.006)
    ym = top - 0.12
    if braces:
        beam(C, 'leg_brace_x1', (x + 0.02, ym - 0.28, -lz + 0.07), (x + 0.02, ym, lz - 0.07), 0.05, 0.012, M['dark'], 0.002)
        beam(C, 'leg_brace_x2', (x + 0.02, ym, -lz + 0.07), (x + 0.02, ym - 0.28, lz - 0.07), 0.05, 0.012, M['dark'], 0.002)
    else:
        # ortası boru geçişine açık: her ayak kendi kirişine çaprazla bağlanır
        for s in (-1, 1):
            beam(C, 'leg_brace', (x + 0.06, top - 0.45, s * lz), (x + 0.75, top - 0.02, s * (bz - 0.02)), 0.05, 0.03, M['dark'], 0.003)
    cylinder(C, 'leg_shaft', 0.02, (x - 0.02, ym - 0.08, -lz), (x - 0.02, ym - 0.08, lz), M['dark'], 12, 0.0)
    yg = ym - 0.08
    box(C, 'leg_gear', (0.2, 0.18, 0.1), (x, yg, lz + 0.12), M['dark'], 0.012)
    cylinder(C, 'crank_shaft', 0.016, (x, yg, lz + 0.17), (x, yg, lz + 0.3), M['dark'], 12, 0.0)
    beam(C, 'crank_arm', (x, yg, lz + 0.3), (x - 0.03, yg - 0.28, lz + 0.33), 0.03, 0.025, M['dark'], 0.004)
    cylinder(C, 'crank_grip', 0.019, (x - 0.03, yg - 0.28, lz + 0.33), (x - 0.03, yg - 0.28, lz + 0.45), M['rubber'], 12, 0.003)


def running_gear(C, axles, R, bz, bot, M, brake='disc', track=0.86, lift=False):
    """BPW havalı süspansiyonlu aks grubu (askı braketi, salıncak kolu, körük, amortisör, aks) ve fren (disk ya da
    kampana). bot: askı braketlerinin bağlandığı kiriş altı. M: 'susp', 'dark', 'rubber', 'chrome', 'galv'.
    Döner: fren silindiri konumları [(x, y, z)] (hava hortumları için)."""
    chambers = []
    bag_h = max(0.18, bot - 0.62)
    for xa in axles:
        cylinder(C, 'axle', 0.064, (xa, R, -track), (xa, R, track), M['susp'], 24, 0.004)
        for s in (-1, 1):
            zb = s * bz
            hb = bot - 0.26
            prism_xy(C, 'hanger', [(xa - 0.82, bot), (xa - 0.44, bot), (xa - 0.55, hb), (xa - 0.7, hb - 0.03)], zb - 0.075, zb + 0.075, M['susp'], 0.008)
            prism_zy(C, 'hanger_gusset', [(zb - s * 0.075, bot), (zb - s * 0.2, bot), (zb - s * 0.075, bot - 0.14)], xa - 0.64, xa - 0.63, M['susp'], 0.002)
            hy = hb + 0.02
            cylinder(C, 'hanger_bush', 0.05, (xa - 0.63, hy, zb - 0.09), (xa - 0.63, hy, zb + 0.09), M['dark'], 20, 0.004)
            beam(C, 'trail_arm_a', (xa - 0.63, hy, zb), (xa, R - 0.1, zb), 0.065, 0.09, M['dark'], 0.008)
            beam(C, 'trail_arm_b', (xa - 0.02, R - 0.1, zb), (xa + 0.43, R - 0.06, zb), 0.06, 0.12, M['dark'], 0.008)
            box(C, 'axle_seat', (0.24, 0.07, 0.15), (xa, R - 0.075, zb), M['dark'], 0.008)
            for dx in (-0.07, 0.07):
                for dz in (-0.06, 0.06):
                    cylinder(C, 'ubolt', 0.011, (xa + dx, R - 0.12, zb + dz), (xa + dx, R + 0.08, zb + dz), M['dark'], 8, 0.0)
            box(C, 'ubolt_plate', (0.2, 0.025, 0.15), (xa, R + 0.075, zb), M['dark'], 0.004)
            yb0 = R - 0.04
            cylinder(C, 'airbag_piston', 0.115, (xa + 0.405, yb0, zb), (xa + 0.405, yb0 + 0.1, zb), M['dark'], 32, 0.004)
            cylinder(C, 'airbag', 0.17, (xa + 0.405, yb0 + 0.08, zb), (xa + 0.405, bot - 0.035, zb), M['rubber'], 48, 0.045)
            cylinder(C, 'airbag_top', 0.16, (xa + 0.405, bot - 0.035, zb), (xa + 0.405, bot - 0.02, zb), M['dark'], 40, 0.003)
            box2(C, 'airbag_pedestal', xa + 0.28, xa + 0.53, bot - 0.02, bot, zb - 0.11, zb + 0.11, M['susp'], 0.004)
            zs = s * (bz - 0.12)
            cylinder(C, 'shock_body', 0.038, (xa + 0.08, R - 0.04, zs), (xa - 0.12, bot - 0.15, zs), M['dark'], 16, 0.004)
            cylinder(C, 'shock_rod', 0.016, (xa - 0.12, bot - 0.15, zs), (xa - 0.4, bot - 0.03, zs), M['chrome'], 12, 0.0)
            box2(C, 'shock_bracket', xa - 0.46, xa - 0.36, bot - 0.07, bot, s * (bz - 0.075), s * (bz - 0.16), M['susp'], 0.004)
            if brake == 'disc':
                cylinder(C, 'brake_disc', 0.215, (xa, R, s * 0.84), (xa, R, s * 0.885), M['galv'], 40, 0.004)
                cylinder(C, 'hub_carrier', 0.1, (xa, R, s * 0.885), (xa, R, s * 0.99), M['dark'], 28, 0.006)
                ca, cr = math.radians(140), 0.19
                cx, cy = xa + math.cos(ca) * cr, R + math.sin(ca) * cr
                box(C, 'caliper', (0.18, 0.12, 0.12), (cx, cy, s * 0.84), M['dark'], 0.02)
                ch = (cx - 0.03, cy + 0.06)
                cylinder(C, 'brake_cyl', 0.088, (ch[0], ch[1], s * 0.78), (ch[0], ch[1], s * 0.56), M['dark'], 28, 0.012)
                cylinder(C, 'brake_cyl_band', 0.092, (ch[0], ch[1], s * 0.67), (ch[0], ch[1], s * 0.655), M['galv'], 28, 0.0)
                chambers.append((ch[0], ch[1], s * 0.6))
            else:
                cylinder(C, 'brake_drum', 0.21, (xa, R, s * 0.7), (xa, R, s * 0.86), M['susp'], 40, 0.006)
                cylinder(C, 'hub_carrier', 0.1, (xa, R, s * 0.86), (xa, R, s * 0.99), M['dark'], 28, 0.006)
                cx, cy = xa - 0.34, R - 0.18
                cylinder(C, 'brake_chamber', 0.085, (xa - 0.16, cy, s * 0.62), (cx - 0.1, cy, s * 0.62), M['dark'], 24, 0.01)
                cylinder(C, 'chamber_band', 0.088, (cx + 0.02, cy, s * 0.62), (cx + 0.005, cy, s * 0.62), M['galv'], 24, 0.0)
                beam(C, 'slack_adjuster', (xa - 0.1, R - 0.2, s * 0.64), (xa - 0.16, R - 0.3, s * 0.64), 0.03, 0.02, M['galv'], 0.003)
                cylinder(C, 'cam_shaft', 0.022, (xa - 0.1, R - 0.2, s * 0.64), (xa - 0.1, R - 0.2, s * 0.72), M['dark'], 10, 0.0)
                chambers.append((cx, cy, s * 0.62))
    return chambers


def ground_contact(path, CS, hide, fast):
    """Zemin temas gölgesi: dorsenin altındaki düzleme AO pişirilir, ters çevrilip yumuşatılır, kenarlarda söner (WebP)"""
    import numpy as np
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    vs = [bm.verts.new(bl((CS[0], 0.0, CS[3]))), bm.verts.new(bl((CS[1], 0.0, CS[3]))), bm.verts.new(bl((CS[1], 0.0, CS[2]))), bm.verts.new(bl((CS[0], 0.0, CS[2])))]
    f = bm.faces.new(vs)
    for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uvl].uv = uv
    me = bpy.data.meshes.new('Ground')
    bm.to_mesh(me)
    ground = bpy.data.objects.new('Ground', me)
    scene.collection.objects.link(ground)
    gm = material('GroundAO', '#ffffff', 1.0, 0.0)
    ground.data.materials.append(gm)
    cw, chh = (512, 128) if fast else (1024, 256)
    gimg = bpy.data.images.new('contact', cw, chh, alpha=False)
    gn = gm.node_tree.nodes.new('ShaderNodeTexImage')
    gn.image = gimg
    gm.node_tree.nodes.active = gn
    scene.world.light_settings.distance = 1.2
    scene.cycles.samples = 32 if fast else 256
    for o in hide:
        o.hide_render = True
    select_only([ground])
    bpy.ops.object.bake(type='AO', margin=2, use_clear=True)
    for o in hide:
        o.hide_render = False
    px = np.array(gimg.pixels[:], dtype=np.float32).reshape(chh, cw, 4)
    dark = np.clip((1.0 - px[:, :, 0]) * 1.15, 0.0, 1.0) ** 0.9

    def blur(a, r):
        for _ in range(3):
            for ax in (0, 1):
                p = np.pad(a, [(r, r) if i == ax else (0, 0) for i in range(2)], mode='edge')
                c = np.cumsum(p, axis=ax, dtype=np.float64)
                c = np.insert(c, 0, 0, axis=ax)
                a = ((np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)).astype(np.float32)
        return a

    dark = blur(dark, 1 if fast else 2)
    yy, xx = np.mgrid[0:chh, 0:cw]
    fade = np.clip(np.minimum(np.minimum(xx, cw - 1 - xx) / (cw * 0.03), np.minimum(yy, chh - 1 - yy) / (chh * 0.12)), 0, 1)
    dark = dark * (fade * fade * (3 - 2 * fade))
    out = bpy.data.images.new('contact_out', cw, chh, alpha=False)
    out.colorspace_settings.name = 'Non-Color'
    o = np.zeros((chh, cw, 4), dtype=np.float32)
    o[:, :, 0] = o[:, :, 1] = o[:, :, 2] = dark
    o[:, :, 3] = 1.0
    out.pixels[:] = o.ravel()
    out.update()
    out.filepath_raw = path
    out.file_format = 'WEBP'
    out.save(filepath=path, quality=90)
    print('CONTACT', path, f'{os.path.getsize(path) / 1024:.0f} KB')
    return ground


def preview_renders(folder, views, hide=()):
    """Kontrol amaçlı Cycles görüntüleri: views = [(ad, kamera konumu, hedef)] (three koordinatı)"""
    os.makedirs(folder, exist_ok=True)
    for o in hide:
        o.hide_render = True
    w = scene.world
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.8, 0.82, 0.85, 1)
    bg.inputs['Strength'].default_value = 0.8
    sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    scene.cycles.samples = 24
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    for nm, loc, tgt in views:
        cam.location = bl(loc)
        cam.rotation_euler = (bl(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(folder, nm + '.png')
        bpy.ops.render.render(write_still=True)
