# Blender betikleri için ortak yardımcılar (standart_box.py kullanır; damper_chassis.py kendi kopyasıyla kalır).
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


def smart_uv(ob, margin, planar=None):
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin)
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


def export_glb(path, objs):
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
        export_cameras=False,
        export_lights=False,
    )
    print(f'EXPORTED {path} {os.path.getsize(path) / 1024:.0f} KB')
