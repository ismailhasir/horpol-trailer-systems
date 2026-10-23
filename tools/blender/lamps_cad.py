# Üretici CAD verisinden (STEP → tools/cad/step_to_stl.py → STL) lamba modelleri. lamps.py içine exec edilir
# (_load_modules): bpy, bmesh, math, np, Vector, Matrix, bl, mat, E, prism, frame, cyl, box, cup, tube, amp7, product …
#
# LZD 3194/AMP MAVIC (sol). Kaynaklar (vault: Dideban Otomotiv/LZD-3194AMP.zip ve 3d-files_2026-10-02_1139.zip):
#   - STEP "LZD 3194_H101_AMP_4SS": dış zarf modeli. Lens (dış + iç kabuk), gövde, Superseal yuvaları, M8 saplamalar,
#     AMP rakoru ve 9 lens vidası VAR; iç optik parçalar (ışık kılavuzları, LED'ler, reflektörler, geri vites yuvaları) YOK.
#   - Bu yüzden: lens dış yüzeyi ve gövde CAD'den; iç parçalar ürün fotoğraflarından (lzd-2650-lzd-2651-mavic-horpol-72-dpi-*.jpg)
#     ölçülür. Fotoğraf → lamba koordinatı dönüşümü: lensin ardından görünen 9 vida (CAD'de ayrı parçalar) kontrol noktası,
#     3B kamera matrisi (DLT; kavisli lens yüzünde düzlemsel homografi yetmiyor). İç parçalar lens dış yüzeyini izler.
#   - İşlev haritası ürün videosundaki etiketlerden: neon kılavuzlar pozisyonda boydan boya sönük; frende büyük üçgenin sağ
#     kenarının solundaki bölüm parlak (aynı kılavuz: malzeme "E.position+stop.red", sağı "E.position.red"); frende ayrıca sol iç üçgen; sağ uçta 2 × 4 hücre SİS; turuncu kama SİNYAL;
#     sol üstte 2 pencere GERİ VİTES; büyük üçgen ve alt şerit reflektör.
# CAD ekseni (mm): x genişlik (geniş uç −x), yukarı = −z, lens yönü = +y, arka montaj düzlemi y = −78.
import os
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

CAD_ROOT = os.environ.get('LAMP_CAD_DIR', os.path.abspath('tools/blender/cad'))
CAD_BACK_Y = -78.0  # mm, arka montaj düzlemi
# CAD (m, Blender'a STL olarak gelir) → Blender'da lamba yereli: three (x, −z, y+0,078) = Blender (x, −(y+0,078), −z)
CAD_M = Matrix(((1, 0, 0, 0), (0, -1, 0, CAD_BACK_Y / 1000), (0, 0, -1, 0), (0, 0, 0, 1)))


def _stl(path, M=None):
    """STL'yi içe al, M ile (varsayılan: LZD 3194 CAD → lamba yereli) Blender koordinatına çevir; bmesh (metre).
    M=False: CAD ekseninde bırak (metre)."""
    bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
    ob = bpy.context.selected_objects[0]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world if M is False else (CAD_M if M is None else M) @ ob.matrix_world)
    bpy.data.objects.remove(ob, do_unlink=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
    return bm


def _three(v):
    """Blender vektörü → three (x, y, z) mm"""
    return (v.x * 1000, v.z * 1000, -v.y * 1000)


def _exterior(bm):
    """Dışarıdan görünen yüzler (26 yönde ışın, en az biri kaçarsa dış)"""
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    dirs = [Vector((x, y, z)).normalized() for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]
    out = []
    for f in bm.faces:
        c = f.calc_center_median()
        n = f.normal
        vis = False
        for d in dirs:
            if d.dot(n) < 0.15:
                continue
            if tree.ray_cast(c + d * 0.0003, d, 2.0)[0] is None:
                vis = True
                break
        out.append(vis)
    return out


def _front_faces(bm):
    """Önden (yerel +Z yarı küre, Blender −Y) görünen yüzler: saydam lensin arka yüzü atılır (iki kat renk koyulaşmasın)"""
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    dirs = [Vector((x, y, z)).normalized() for x in (-1, -0.5, 0, 0.5, 1) for y in (-1, -0.5) for z in (-1, -0.5, 0, 0.5, 1)]
    out = []
    for f in bm.faces:
        c, n = f.calc_center_median(), f.normal
        out.append(any(d.dot(n) > 0.15 and tree.ray_cast(c + d * 0.0003, d, 2.0)[0] is None for d in dirs))
    return out


def _subset(bm, keep):
    """keep(face) doğru olan yüzlerden yeni bmesh"""
    b = bm.copy()
    b.faces.ensure_lookup_table()
    flags = [keep(f) for f in bm.faces]
    bmesh.ops.delete(b, geom=[f for f, k in zip(b.faces, flags) if not k], context='FACES')
    return b


def _simplify(bm, angle=0.6):
    """Düzlemsel yüzleri birleştir (CAD fasetleri düz: biçim bozulmaz)"""
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle), use_dissolve_boundaries=False, verts=bm.verts[:], edges=bm.edges[:],
                             delimit={'MATERIAL'})
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')


def _mesh_obj(name, bm, mats, group, angle=32, decimate=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m_ in mats:
        me.materials.append(m_)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    print('CADPART', name, len(me.polygons), '→', decimate if decimate and len(me.polygons) > decimate else len(me.polygons))
    if decimate and len(me.polygons) > decimate:
        md = ob.modifiers.new('dec', 'DECIMATE')
        md.ratio = decimate / len(me.polygons)
        md.use_collapse_triangulate = True
    group.objs.append(ob)
    return ob


# ---------------- fotoğraf → lamba koordinatı ----------------
def _homography(src, dst):
    A = []
    for (u, v), (x, y) in zip(src, dst):
        A.append([u, v, 1, 0, 0, 0, -x * u, -x * v, -x])
        A.append([0, 0, 0, u, v, 1, -y * u, -y * v, -y])
    _, _, vt = np.linalg.svd(np.array(A, float))
    return vt[-1].reshape(3, 3)


def _dlt(uv, xyz):
    """3B noktalar (mm) → fotoğraf (px) 3×4 kamera matrisi (doğrudan doğrusal dönüşüm, en küçük kareler)"""
    A = []
    for (u, v), (x, y, z) in zip(uv, xyz):
        A.append([x, y, z, 1, 0, 0, 0, 0, -u * x, -u * y, -u * z, -u])
        A.append([0, 0, 0, 0, x, y, z, 1, -v * x, -v * y, -v * z, -v])
    _, _, vt = np.linalg.svd(np.array(A, float))
    return vt[-1].reshape(3, 4)


def _drape(group, name, poly, zfun, dz, thick, material, res=3.0):
    """Lensin iç yüzünü kesintisiz izleyen ince plaka (ışık kılavuzu): çokgen ≤res mm üçgenlere bölünür (kısıtlı Delaunay),
    her köşe kendi lens derinliğinin dz gerisinde; arka yüz thick kadar geride. Eski yöntem (12 mm'lik düz dilimler) dilim
    sınırlarında basamak ve dikiş izi bırakıyordu."""
    n = len(poly)
    ring = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        k = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / res)))
        ring += [(x0 + (x1 - x0) * t / k, y0 + (y1 - y0) * t / k) for t in range(k)]
    pts = list(ring)
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    gx = min(xs) + res * 0.5
    while gx < max(xs):
        gy = min(ys) + res * 0.5
        while gy < max(ys):
            if _inside(poly, gx, gy) and min(_seg_dist((gx, gy), poly[i], poly[(i + 1) % n]) for i in range(n)) > res * 0.45:
                pts.append((gx, gy))
            gy += res
        gx += res
    m = len(ring)
    vo, _, fo, _, _, _ = delaunay_2d_cdt([Vector(p) for p in pts], [(i, (i + 1) % m) for i in range(m)], [list(range(m))], 1, 1e-5, True)
    bm = bmesh.new()
    zf = [zfun(v.x, v.y) - dz for v in vo]
    F = [bm.verts.new(bl((v.x / 1000, v.y / 1000, z / 1000))) for v, z in zip(vo, zf)]
    B = [bm.verts.new(bl((v.x / 1000, v.y / 1000, (z - thick) / 1000))) for v, z in zip(vo, zf)]
    cnt = {}
    for f in fo:
        bm.faces.new([F[i] for i in f])
        bm.faces.new([B[i] for i in reversed(f)])
        for a, b in zip(f, f[1:] + f[:1]):
            cnt[(min(a, b), max(a, b))] = cnt.get((min(a, b), max(a, b)), 0) + 1
    for f in fo:
        for a, b in zip(f, f[1:] + f[:1]):
            if cnt[(min(a, b), max(a, b))] == 1:
                bm.faces.new([F[b], F[a], B[a], B[b]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, material, group, 0.0)


def _poly_clip_x(poly, x0, x1):
    """Çokgeni x0 ≤ x ≤ x1 şeridine kırp (Sutherland–Hodgman)"""
    def clip(pts, inside, inter):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q):
                    out.append(inter(q, p))
                out.append(p)
            elif inside(q):
                out.append(inter(q, p))
        return out

    def ix(a, b, x):
        t = (x - a[0]) / (b[0] - a[0])
        return (x, a[1] + (b[1] - a[1]) * t)
    p = clip(poly, lambda p: p[0] >= x0, lambda a, b: ix(a, b, x0))
    if p:
        p = clip(p, lambda p: p[0] <= x1, lambda a, b: ix(a, b, x1))
    return p


def _clip_line(poly, a, b, ref, same):
    """Çokgeni a–b doğrusuyla kırp: same=True → ref noktasının bulunduğu yarı düzlem, False → öbür yarı (Sutherland–Hodgman;
    doğruyu bir kez kesen içbükey çokgenlerde de doğru)"""
    side = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    s = (1 if side(ref) > 0 else -1) * (1 if same else -1)
    out = []
    for i in range(len(poly)):
        p, q = poly[i - 1], poly[i]
        sp, sq = s * side(p), s * side(q)
        if (sp >= 0) != (sq >= 0):
            t = sp / (sp - sq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        if sq >= 0:
            out.append(q)
    return out


def _inside(poly, x, y):
    c = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def _grow(poly, d):
    return offset(poly, -d)


def _emat(fn, color, off_hex, tag='mavic'):
    """Ürüne özel sönük renkli ışık malzemesi: E.<işlev>.<renk>.<etiket> (site ilk iki alanı okur; kütüphanedeki ortak
    E.<işlev>.<renk> başka lambalarda kullanıldığı için değiştirilmez)"""
    key = f'E.{fn}.{color}.{tag}'
    if key not in MATS:
        m = mat(f'E.{fn}.{color}').copy()
        m.name = key
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = srgb(off_hex)
        MATS[key] = m
    return MATS[key]


def _refl(fn, color, gain):
    """Işığı yansıtan krom (LED kabı): sönükken krom, işlev yanınca LED'in ışığını yansıtıp gain oranında ışır.
    Ad: E.<işlev>.<renk>.g<yüzde> (site ve simge işlev şiddetini bu oranla çarpar)"""
    key = f'E.{fn}.{color}.g{int(round(gain * 100))}'
    if key not in MATS:
        m = mat('Chrome').copy()
        m.name = key
        p = m.node_tree.nodes['Principled BSDF']
        p.inputs['Emission Color'].default_value = (*GLOW[color], 1.0)
        p.inputs['Emission Strength'].default_value = 0.0
        m['fn'] = fn
        m['gain'] = gain
        MATS[key] = m
    return MATS[key]


def _refl_tint(fn, color, gain, tint, rough):
    """Renkli lensin ardındaki krom kap: yansıması lens renginde (metal taban rengi) ve saten (rough). Cilalı beyaz krom
    renkli lensin ardında ayı / ay ışığını beyaz yansıtıp ışığın rengine karışıyordu (LZD 2854). Ad: E.<işlev>.<renk>.g<yüzde>.t"""
    key = f'E.{fn}.{color}.g{int(round(gain * 100))}.t'
    if key not in MATS:
        m = _refl(fn, color, gain).copy()
        m.name = key
        p = m.node_tree.nodes['Principled BSDF']
        p.inputs['Base Color'].default_value = srgb(tint)
        p.inputs['Roughness'].default_value = rough
        m['fn'] = fn
        m['gain'] = gain
        MATS[key] = m
    return MATS[key]


def _cup_bands(group, x, y, z, r_front, r_back, depth, gains, fn, color, tint=None, rough=0.3, seg=28):
    """İçi önden görünen krom LED kabı, dipten ağza bantlara bölünmüş: her bant kendi oranında ışır (LED'e yakın dip parlak,
    ağız sönük; yansıyan ışığın düşüşü). Normaller içe: sitede tek yüzlü çizim, dış yüz arkada kalır. tint: lens renginde krom.
    seg: az kenar (ör. 8) fasetli reflektör (yaprak biçimli yüzeyler)"""
    n = len(gains)
    for i, g in enumerate(gains):
        z0 = z - depth + depth * i / n
        z1 = z - depth + depth * (i + 1) / n
        r0 = r_back + (r_front - r_back) * i / n
        r1 = r_back + (r_front - r_back) * (i + 1) / n
        mt = _refl_tint(fn, color, g, tint, rough) if tint else _refl(fn, color, g)
        ob = cyl(group, 'cup', r0, (x, y, z0), (x, y, z1), mt, seg, r2=r1, caps=False)
        bm_ = bmesh.new()
        bm_.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm_, faces=bm_.faces[:])
        bm_.to_mesh(ob.data)
        bm_.free()


def _lmat(color, tag='cad'):
    """Lens.<renk>.cad: sitede lens az parlar (kılavuzlar lensin hemen ardında, lensin kendisinin ışıması deseni örter)"""
    key = f'Lens.{color}.{tag}'
    if key not in MATS:
        m = mat(f'Lens.{color}').copy()
        m.name = key
        MATS[key] = m
    return MATS[key]


def _drop_small(bm, cond):
    """Bağlı bileşenlerden cond(min, max, yüz sayısı) doğru olanları sil (mm, three ekseni)"""
    bm.faces.ensure_lookup_table()
    seen = set()
    kill = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, cur = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            cur.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        vs = [_three(v.co) for g in cur for v in g.verts]
        mn = [min(v[i] for v in vs) for i in range(3)]
        mx = [max(v[i] for v in vs) for i in range(3)]
        if cond(mn, mx, len(cur)):
            kill += cur
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    print('DROPPED', len(kill))


@product('lzd3194', 'LZD 3194/AMP', 'stop', 'MAVIC sol (sağ: LZD 3195/AMP, ayna) — üretici CAD + ürün fotoğrafları')
def build_lzd3194_cad(L):
    cad = os.path.join(CAD_ROOT, 'lzd3194')
    if not os.path.exists(os.path.join(cad, 'p001.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_lzd3194(L)

    # ===== 1) CAD ana kabuk: dış yüzler; lens (flanş önü) / gövde =====
    bm = _stl(os.path.join(cad, 'p001.stl'))
    ext = _exterior(bm)
    SEAM = 34.5  # mm (yerel z): lens flanşı ile gövde birleşimi (CAD y −43,5)
    def zone(f, e):
        x, y, z = _three(f.calc_center_median())
        if e and -219.3 <= x < -203.0 and abs(y) <= 56.0 and 5.0 <= z <= 60.0:
            return 'bracket'  # geniş uçta lastik kol adaptörü (lambanın parçası; dışındaki kol plakası ve kol CAD'de LDCC 2698)
        if not e or z < -26.0 or x > 207.0 or x < -203.0 or abs(y) > 84.0:
            return None  # iç yüzeyler, kablo, CAD'deki kolun kendisi (sitede seçilen ürün takılır) ve kablo artıkları atılır
        if abs(abs(x) - SS_X) < 23.0 and abs(y) < 21.0 and z < -0.8:
            return None  # Superseal blokları: aşağıda ürün fotoğraflarına göre yeniden modellenir
        return 'lens' if z > SEAM and -205.0 < x < 205.0 else 'body'
    zones = [zone(f, e) for f, e in zip(bm.faces, ext)]
    lens_bm = _subset(bm, lambda f: zones[f.index] == 'lens')
    body_bm = _subset(bm, lambda f: zones[f.index] == 'body')
    bracket_bm = _subset(bm, lambda f: zones[f.index] == 'bracket')
    bm.free()

    # ===== 2) lens derinliği: dış yüzeye önden ışın (fotoğraf eşlemesi ve iç parçalar lensi izler) =====
    lens_bm.faces.ensure_lookup_table()
    ltree = BVHTree.FromBMesh(lens_bm)
    def zlens(x, y):
        h = ltree.ray_cast(Vector((x / 1000, -0.5, y / 1000)), Vector((0, 1, 0)), 1.0)
        return -h[0].y * 1000 if h[0] is not None else 40.0

    # ===== 3) fotoğraf → lamba: 3B kamera (lzd-2650-…-72-dpi-*.jpg, 160,120'den 920×360 kırpılıp ×2: tüm çekimler aynı kadraj) =====
    # Lens kavisli (ortada z 55 mm, dar uçta 41 mm): düzlemsel homografi ortada 7 mm'ye kadar kaydırıyordu (fotoğrafta vidalar ve
    # üst çubuk eğri hatta). 9 vida başının CAD konumu (x, y, z) ile 3×4 kamera matrisi kurulur; fotoğraf noktası, kamera ışınının
    # "lens dış yüzeyi − 4 mm" (kılavuz yüzü) ile kesiştiği yere taşınır. Vida hatası: homografi 11 px → kamera 4 px (~1 mm).
    photo_screws = [(170, 95), (877, 128), (1288, 180), (1663, 232), (1640, 665), (1255, 655), (845, 630), (130, 575), (65, 330)]
    cad_screws = [(-171.83, 53.11, 50.06), (-15.84, 54.98, 53.23), (76.1, 53.11, 47.66), (162.32, 49.32, 39.71), (162.32, -49.32, 39.71),
                  (76.1, -53.11, 47.66), (-15.84, -54.98, 53.23), (-171.83, -53.11, 50.06), (-190.5, 0.0, 53.0)]
    P = _dlt(photo_screws, cad_screws)
    err = 0
    for (u, v), X in zip(photo_screws, cad_screws):
        w = P @ np.array([*X, 1.0])
        err = max(err, math.hypot(w[0] / w[2] - u, w[1] / w[2] - v))
    print(f'CAMERA max err {err:.1f} px')
    def ph(pts, dz=4.0):
        out = []
        for u, v in pts:
            r1, r2 = P[0] - u * P[2], P[1] - v * P[2]
            A = np.array([[r1[0], r1[1]], [r2[0], r2[1]]])
            z = 45.0
            for _ in range(8):
                x, y = np.linalg.solve(A, -np.array([r1[2] * z + r1[3], r2[2] * z + r2[3]]))
                z = zlens(x, y) - dz
            out.append((float(x), float(y)))
        return out

    # ölçülen biçimler (fotoğraf kırpma koordinatı, px). Kılavuz kenarları pozisyon fotoğrafında (72-dpi-2) sütun/satır parlaklık
    # profilinden; sinyal kaması sinyal fotoğrafında (72-dpi-4); fren üçgeni sönük fotoğrafta (72-dpi-6) koyu üçgen olarak
    TRI = [(520, 62), (722, 447), (283, 438)]
    LOWER = [(190, 541), (780, 571), (816, 650), (808, 662), (780, 663), (500, 646), (160, 622), (151, 607)]
    # sinyal kaması: üst kenarı üst çubuğa paralel kavis (arada ~5 mm koyu bant), alt kenar düz
    WEDGE = [(666, 268), (700, 271), (800, 282), (1000, 303), (1200, 329), (1400, 363), (1600, 395), (1700, 413), (1776, 428), (1776, 439),
             (1700, 443), (1600, 446), (1400, 447), (1200, 449), (1000, 447), (800, 444), (745, 444), (740, 440), (713, 400), (689, 350),
             (667, 300)]
    WEDGE_CUT = [(666, 268), (800, 282), (1200, 329), (1600, 395), (1776, 428), (1776, 439), (1400, 447), (800, 444), (745, 444)]
    # neon üst çubuk: kavisli (dar uca doğru aşağı kıvrılır), sol ucu lamba kenarına paralel eğik
    TOPBAR = [(88, 141), (200, 148), (400, 163), (600, 180), (800, 199), (1000, 222), (1200, 249), (1400, 280), (1600, 314), (1700, 331),
              (1784, 346), (1784, 407), (1700, 394), (1600, 374), (1400, 340), (1200, 309), (1000, 282), (800, 259), (600, 240), (400, 219),
              (200, 203), (78, 196)]
    # alt iki şerit: iç ve dış "<" kılavuzların yatay kolları. Boydan boya ayrı kalırlar: kollar arasında koyu yarık, büyük üçgenin
    # altında noktalı yazı şeridi (G: 486 + 0,0592·(u − 250), ±3 px), sağda siyah ayırıcı (SEP)
    CHEV_IN = [(147, 218), (189, 218), (287, 444), (400, 450), (500, 455), (600, 459), (700, 464), (760, 466), (900, 469), (1100, 473),
               (1300, 474), (1500, 472), (1700, 467), (1780, 466), (1780, 507), (1700, 509), (1500, 514.5), (1300, 517), (1100, 516.5),
               (900, 512.5), (800, 509.5), (746, 508), (740, 512), (550, 500.8), (400, 491.9), (259, 483.5)]
    CHEV_OUT = [(90, 218), (133, 218), (245, 489), (400, 498), (550, 506.8), (740, 518), (752, 522), (800, 521.5), (900, 524.5),
                (1100, 528.5), (1300, 529), (1500, 526.5), (1700, 521), (1780, 519), (1780, 561), (1700, 565), (1500, 569), (1300, 572),
                (1100, 571), (900, 567), (800, 565), (740, 567), (224, 537)]
    SEP = [(746, 508), (800, 509.5), (900, 512.5), (1100, 516.5), (1300, 517), (1500, 514.5), (1700, 509), (1776, 507.5), (1776, 519),
           (1700, 521), (1500, 526.5), (1300, 529), (1100, 528.5), (900, 524.5), (800, 521.5), (752, 522)]
    SLOT = [(134, 218), (148, 218), (241, 462), (234, 462)]
    # noktalı yazı: üç grup, 9 px aralık
    DOTS = [(u, 486 + 0.0592 * (u - 250)) for a, b in ((252, 413), (434, 550), (571, 738)) for u in range(a, b + 1, 9)]
    STOP_TRI = [(217, 230), (379, 242), (281, 381)]
    FOG = []
    for xs, (t0, t1), (b0, b1) in (([1320, 1442, 1548, 1652, 1770], (185, 228), (262, 318)), ([1290, 1412, 1517, 1625, 1755], (580, 583), (655, 668))):
        X0, X1 = xs[0], xs[-1]
        top = lambda x: t0 + (t1 - t0) * (x - X0) / (X1 - X0)
        bot = lambda x: b0 + (b1 - b0) * (x - X0) / (X1 - X0)
        for a, b in zip(xs, xs[1:]):
            FOG.append([(a, top(a)), (b, top(b)), (b, bot(b)), (a, bot(a))])
    TRI, LOWER, WEDGE, WEDGE_CUT, TOPBAR = ph(TRI), ph(LOWER), ph(WEDGE), ph(WEDGE_CUT), ph(TOPBAR)
    # geri vites pencereleri lamba eksenine hizalı (fotoğraftan dönüştürülen çokgen perspektifle eğiliyordu): üst kenar lensin
    # üst kenarına paralel (y 66), dış pencerenin iç ucu ve iç pencerenin dış ucu ok biçimli, aralarında üçgenin tepesi
    REV = [[(-165.0, 46.0), (-162.0, 43.0), (-113.0, 43.0), (-106.0, 54.5), (-113.0, 66.0), (-162.0, 66.0), (-165.0, 63.0)],
           [(-77.0, 43.0), (-29.0, 43.0), (-26.0, 46.0), (-26.0, 63.0), (-29.0, 66.0), (-77.0, 66.0), (-84.0, 54.5)]]
    REV_LED = [[(-150.0, 54.5), (-125.0, 54.5)], [(-64.0, 54.5), (-39.0, 54.5)]]
    CHEV_IN, CHEV_OUT, SEP, SLOT, STOP_TRI = ph(CHEV_IN), ph(CHEV_OUT), ph(SEP), ph(SLOT), ph(STOP_TRI)
    DOTS = ph(DOTS, 3.0)
    FOG = [ph(p) for p in FOG]
    for nm, poly in (('TOPBAR', TOPBAR), ('CHEV_IN', CHEV_IN), ('CHEV_OUT', CHEV_OUT), ('SEP', SEP), ('STOP_TRI', STOP_TRI), ('WEDGE', WEDGE)):
        print('FEAT', nm, [(round(x, 1), round(y, 1)) for x, y in poly])

    def zmin(poly, n=3):
        pts = list(poly)
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        pts += [(cx + (p[0] - cx) * 0.5, cy + (p[1] - cy) * 0.5) for p in poly] + [(cx, cy)]
        return min(zlens(*p) for p in pts)
    m_ = lambda pts: [(x / 1000, y / 1000) for x, y in pts]
    follow = lambda group, name, poly, dz, thick, material: _drape(group, name, poly, zlens, dz, thick, material)

    # ===== 4) iç parçalar =====
    # lensin iç kenarı (CAD lens iç kabuğundan ölçüldü, mm): geniş uçta pahlı köşeler, −25'te basamak, dar uç yuvarlatılmış
    sil = [(-198.75, -46.25), (-163.0, -70.0), (-27.5, -70.0), (-21.25, -62.5), (180.0, -58.75), (200.0, -37.5), (200.0, 37.5),
           (180.0, 56.0), (-21.25, 62.5), (-27.5, 70.0), (-163.0, 70.0), (-198.75, 46.25)]
    # gövde lens flanşından 4–6 mm dar: taban ve duvar gövdenin içinde kalsın (dışarıdan görünmesin)
    inset = offset(sil, 6.5)
    Z_FLOOR = 27.0
    prism(L.inner, 'cad_floor', m_(inset), (Z_FLOOR - 2) / 1000, Z_FLOOR / 1000, mat('ReflectorRed'), 0.0)
    set_uv_planar(L.inner.objs[-1], 0.03)
    frame(L.inner, 'cad_wall', m_(offset(sil, 4.5)), m_(inset), (Z_FLOOR - 2) / 1000, 44.0 / 1000, mat('ReflectorRed'), 0.0)
    set_uv_planar(L.inner.objs[-1], 0.03)
    # reflektörler: büyük üçgen (üstünden neon üst çubuk geçer) ve alt şerit
    for nm, poly in (('tri', TRI), ('lower_refl', LOWER)):
        print('ZMIN', nm, round(zmin(poly), 1))
        prism(L.inner, nm, m_(poly), Z_FLOOR / 1000, (zmin(poly) - 4.0) / 1000, mat('Retro.red'), 0.0008)
        set_uv_planar(L.inner.objs[-1], 0.010)
    # geri vites: iki pencere, ikişer LED; krom yuva + krom kaplar + koyu çerçeve. Videoda (0:50) yanınca kapların tamamı LED'in
    # ışığını yansıtıp beyaz parlar, LED ortada en parlak nokta: kaplar ve yuva geri viteste kendi oranlarında ışır (_refl).
    # Oranlar bloom eşiğinin altında (sitede şiddet 3,0 × oran ≤ 1): kap yapısı okunur, haleyi yalnız LED verir
    for poly, leds in zip(REV, REV_LED):
        zf = zmin(poly) - 3.6
        prism(L.E('reverse'), 'rev_bay', m_(offset(poly, 1.0)), Z_FLOOR / 1000, (Z_FLOOR + 2) / 1000, _refl('reverse', 'white', 0.13), 0.0)
        frame(L.inner, 'rev_frame', m_(poly), m_(offset(poly, 1.6)), Z_FLOOR / 1000, zf / 1000, mat('HousingGloss'), 0.0)
        for (lx, ly) in leds:
            _cup_bands(L.E('reverse'), lx / 1000, ly / 1000, (zf - 1.0) / 1000, 0.0105, 0.0045, (zf - 1.0 - Z_FLOOR - 2) / 1000,
                       (0.33, 0.26, 0.19), 'reverse', 'white')
            box(L.E('reverse'), 'rev_led', (lx - 3.2) / 1000, (lx + 3.2) / 1000, (ly - 3.2) / 1000, (ly + 3.2) / 1000, (Z_FLOOR + 2.2) / 1000,
                (Z_FLOOR + 3.8) / 1000, E('reverse', 'white'))
    # sis: 2 × 4 hücre — krom hücre, LED, önde tırtıklı optik
    for poly in FOG:
        zf = zmin(poly) - 3.4
        frame(L.inner, 'fog_cell', m_(poly), m_(offset(poly, 1.2)), Z_FLOOR / 1000, zf / 1000, mat('HousingGloss'), 0.0)
        prism(L.inner, 'fog_back', m_(offset(poly, 1.0)), Z_FLOOR / 1000, (Z_FLOOR + 1.5) / 1000, mat('ReflectorRed'), 0.0)
        # hücrenin tırtıklı optiği ışığı yayar: yanınca bütün hücre aydınlanır (fotoğraf), sönükken koyu kırmızı
        prism(L.E('fog'), 'fog_optic', m_(offset(poly, 1.6)), (zf - 1.2) / 1000, (zf - 0.4) / 1000, _emat('fog', 'red', '#6b1714'), 0.0)
        set_uv_planar(L.E('fog').objs[-1], 0.006)
    # sinyal: turuncu ışık kılavuzu (kama), lensin 4,5 mm gerisinde
    follow(L.E('turn'), 'turn_guide', WEDGE, 4.5, 4.0, _emat('turn', 'amber', '#f39a3a'))
    # neon üst çubuk, iç ve dış "<" kılavuzlar: pozisyonda boydan boya sönük yanar. Frende yalnız büyük üçgenin sağ kenarı
    # doğrultusunun solundaki (geniş uç) bölüm parlar; sağı (sinyal tarafı) pozisyonda kalır (kullanıcı, 2026-10-20)
    BRAKE_CUT = (TRI[0], TRI[1])  # üçgenin tepesi → sağ alt köşesi
    for nm, poly in (('neon_top', TOPBAR), ('neon_in', CHEV_IN), ('neon_out', CHEV_OUT)):
        follow(L.E('position+stop'), nm, _clip_line(poly, *BRAKE_CUT, (-200.0, 0.0), True), 4.2, 3.5,
               _emat('position+stop', 'red', '#d98f8a'))
        follow(L.E('position'), nm + '_r', _clip_line(poly, *BRAKE_CUT, (-200.0, 0.0), False), 4.2, 3.5,
               _emat('position', 'red', '#d98f8a'))
    # frende ayrıca sol iç üçgen panel yanar (kılavuzlarla aynı düzlemde)
    follow(L.E('stop'), 'stop_tri', STOP_TRI, 4.4, 2.0, _emat('stop', 'red', '#9c2a27'))
    # alt şeritler arası ayırıcılar: kollar arasında koyu yarık, sağda siyah ayırıcı, büyük üçgenin altında lensteki noktalı yazı
    follow(L.inner, 'sep', SEP, 3.8, 0.8, mat('HousingGloss'))
    follow(L.inner, 'slot', SLOT, 3.8, 0.8, mat('HousingGloss'))
    bmd = bmesh.new()
    for cx, cy in DOTS:
        zc = zlens(cx, cy) - 3.0
        ring_ = [bmd.verts.new(bl(((cx + 0.7 * math.cos(a * math.pi / 4)) / 1000, (cy + 0.7 * math.sin(a * math.pi / 4)) / 1000, zc / 1000)))
                 for a in range(8)]
        bmd.faces.new(ring_)
    _obj('lens_dots', bmd, mat('HousingGloss'), L.inner, 0.0)
    # sol orta lens vidası (CAD ana kabuğun içinde kalan tek vida)
    cyl(L.inner, 'screw_boss', 0.0043, (-0.1905, 0.0, 0.040), (-0.1905, 0.0, 0.053), mat('Housing'), 20)

    # ===== 5) lens: bölgeler (renksiz geri vites pencereleri, turuncu kama), sadeleştirme =====
    _simplify(lens_bm, 0.5)
    cuts = [_grow(p, 1.0) for p in REV] + [_grow(WEDGE_CUT, 1.5)]
    for poly in cuts:
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            d = Vector((x1 - x0, 0, y1 - y0)).normalized()  # Blender düzleminde (x, z) doğrultusu
            nrm = Vector((-d.z, 0, d.x))
            geom = lens_bm.verts[:] + lens_bm.edges[:] + lens_bm.faces[:]
            bmesh.ops.bisect_plane(lens_bm, geom=geom, plane_co=Vector((x0 / 1000, 0, y0 / 1000)), plane_no=nrm)
    bmesh.ops.triangulate(lens_bm, faces=lens_bm.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    for f in lens_bm.faces:
        x, y, z = _three(f.calc_center_median())
        f.material_index = 1 if any(_inside(p, x, y) for p in cuts[:2]) else 2 if _inside(cuts[2], x, y) else 0
    _mesh_obj('cad_lens', lens_bm, [_lmat('red'), _lmat('clear'), _lmat('amber')], L.lens, 40, decimate=None if FAST else 30000)

    # ===== 6) gövde: kesik kablo artıklarını at, sadeleştir, malzeme (M8 saplamalar ±75 mm, çinko) =====
    _drop_small(body_bm, lambda mn, mx, n: n < 400 and mx[0] < -195.0)
    _simplify(body_bm, 1.0)
    for f in body_bm.faces:
        x, y, z = _three(f.calc_center_median())
        f.material_index = 1 if z < -1.0 and abs(abs(x) - 75.0) < 6.0 and abs(y) < 6.0 else 0
    _mesh_obj('cad_body', body_bm, [mat('Housing'), mat('Zinc')], L.body, 35, decimate=None if FAST else 30000)
    # arka lastik kol montajı: plaka ayrı düğüm (BRACKET; site lamba genişliğini plakasız ölçer) + kolun takıldığı nokta
    _simplify(bracket_bm, 1.0)
    for f in bracket_bm.faces:
        x, y, z = _three(f.calc_center_median())
        f.material_index = 0
    L.bracket = Group('BRACKET')
    _mesh_obj('cad_bracket', bracket_bm, [mat('Housing'), mat('Zinc')], L.bracket, 35, decimate=None if FAST else 6000)
    mnt = bpy.data.objects.new('MOUNT_arm', None)
    # kol plakasının duvar yüzü: STEP'teki LDCC 2698 vidaları kolun kendi CAD'iyle eşlenerek bulundu (x −219,1 mm), plaka
    # merkezi y 0, z 20 mm. Kol buraya DÖNDÜRMEDEN oturur (kolun kendi biçimi yukarı eğik)
    mnt.location = bl((-0.2191, 0.0, 0.020))
    scene.collection.objects.link(mnt)
    L.empties = [mnt]
    # lens vidaları (ayrı CAD parçaları): lensin ardında görünen koyu vida gövdeleri
    for i in range(4, 13):
        p = os.path.join(cad, f'p{i:03d}.stl')
        if os.path.exists(p):
            sb = _stl(p)
            _simplify(sb, 2.0)
            _mesh_obj(f'cad_screw{i}', sb, [mat('Housing')], L.inner, 35, decimate=None if FAST else 160)
    # AMP 7 pin soket rakorun somununa doğrudan oturur (kablosuz; kullanıcı 2026-10-22). Ürün föyündeki 0,3 m kablo kullanılmaz.
    amp_socket(L, 0.0, 0.0, -0.026)
    # 4 Superseal çıkış (Horpol ürün föyü: 2 × pozisyon, sinyal yanıp sönmeli pozisyon, geri vites): iki ikili blok, eksenler
    # ±125 mm (çizim 250), blok genişliği 39, gövdeden 25 mm çıkıntı. Dış uçtaki blok POSITION / POSITION, içteki ? / REVERSE
    # (ürün fotoğraflarındaki kabartma yazılar)
    for sx in (-1, 1):
        superseal_pair(L, sx * SS_X * MM, 0.0)


SS_X = 125.0  # mm: Superseal bloklarının ekseni (yerel |x|)


def amp_socket(L, x, y, z0):
    """AMP 7 pin yuvarlak soket (lamba tarafı): rakor somununa kenetli altıgen flanş, sırtlı gövde, iki yeşil conta halkası, ağzın
    içinde 7 pin. Ağız z0 − 0,046'da, −Z'ye bakar (tesisatın dişi fişi buraya takılır)."""
    blk = mat('ConnBlack')
    cyl(L.body, 'amp_flange', 0.0128, (x, y, z0), (x, y, z0 - 0.006), blk, 6, bevel=0.0006)
    prof = [(0.0005, -0.006), (0.0136, -0.006), (0.0136, -0.0095)]
    for i in range(6):
        h = -0.0105 - i * 0.0036
        prof += [(0.0158, h), (0.0158, h - 0.0021), (0.0146, h - 0.0024), (0.0146, h - 0.0036)]
    prof += [(0.0150, -0.0335), (0.0162, -0.0345), (0.0162, -0.0455), (0.0150, -0.046), (0.0118, -0.046), (0.0118, -0.040),
             (0.0005, -0.040)]
    lathe(L.body, 'amp_body', [(r, h) for r, h in prof], blk, 40, axis='z', center=(x, y, z0))
    for h0 in (-0.0355, -0.0405):
        cyl(L.body, 'amp_seal', 0.0168, (x, y, z0 + h0), (x, y, z0 + h0 - 0.0022), mat('ConnGreen'), 40, bevel=0.0004)
    for k in range(7):
        a = 2 * math.pi * k / 6
        px, py = (0.0, 0.0) if k == 6 else (0.0072 * math.cos(a), 0.0072 * math.sin(a))
        cyl(L.body, 'amp_pin', 0.0009, (x + px, y + py, z0 - 0.040), (x + px, y + py, z0 - 0.0445), mat('Brass'), 10)
    # kodlama dili (ağızda, üstte)
    box(L.body, 'amp_key', x - 0.0015, x + 0.0015, y + 0.0108, y + 0.0122, z0 - 0.046, z0 - 0.036, blk, 0.0002)


def superseal_pair(L, cx, cy):
    """İkili Superseal 1.5 soket bloğu (lamba tarafı, ürün fotoğrafları LZD3194AMP_3 / _4): gövdeye gömülü kare oturma plakası,
    iki soket kulesi (her birinde tek oval ağız, içinde 2 pin), ağızda conta, üstte kilit dili, kuleleri saran yaylı U klips.
    Ağızlar z −0,025'te, −Z'ye bakar."""
    blk, seal = mat('ConnBlack'), mat('Seal')
    X, Y = cx / MM, cy / MM
    frame(L.body, 'ss_base', mp(rrect(46, 40, 5, 4, X, Y)), mp(rrect(41, 35, 3, 4, X, Y)), -0.0016, 0.0, blk, 0.0003, 1)
    prism(L.body, 'ss_plate', mp(rrect(41, 35, 3, 4, X, Y)), -0.0008, 0.0, blk)
    for dx in (-9.75, 9.75):
        tx = X + dx
        prism(L.body, 'ss_tower', mp(rrect(17.0, 15.0, 3.2, 4, tx, Y - 0.5)), -0.0215, -0.0008, blk, 0.0006, 2)
        frame(L.body, 'ss_mouth', mp(rrect(16.2, 14.2, 3.0, 4, tx, Y - 0.5)), mp(stadium(6.9, 12.6, 4, tx, Y - 0.5)), -0.025, -0.0215, blk, 0.0004, 1)
        prism(L.body, 'ss_cavity', mp(stadium(6.9, 12.6, 6, tx, Y - 0.5)), -0.0215, -0.020, seal)
        frame(L.body, 'ss_lip', mp(stadium(6.9, 12.6, 6, tx, Y - 0.5)), mp(stadium(5.4, 11.1, 6, tx, Y - 0.5)), -0.0235, -0.0225, seal)
        for py in (-3.0, 3.0):
            cyl(L.inner, 'ss_pin', 0.0005, ((tx) * MM, (Y - 0.5 + py) * MM, -0.0205), ((tx) * MM, (Y - 0.5 + py) * MM, -0.0225), mat('Brass'), 8)
        # kilit dili (fişin mandalı buna takılır)
        box(L.body, 'ss_latch', (tx - 2.5) * MM, (tx + 2.5) * MM, (Y + 7.0) * MM, (Y + 9.2) * MM, -0.0235, -0.0125, blk, 0.0003)
        box(L.body, 'ss_ramp', (tx - 2.5) * MM, (tx + 2.5) * MM, (Y + 9.2) * MM, (Y + 10.0) * MM, -0.0215, -0.0175, blk, 0.0002)
    # yaylı U klips: iki kulenin dışını saran bant ve yan kulakları
    box(L.body, 'ss_clip', (X - 19.8) * MM, (X + 19.8) * MM, (Y - 8.5) * MM, (Y - 7.2) * MM, -0.0225, -0.0160, blk, 0.0002)
    for sx in (-1, 1):
        box(L.body, 'ss_ear', (X + sx * 19.0 - 0.8) * MM, (X + sx * 19.0 + 0.8) * MM, (Y - 8.5) * MM, (Y + 6.5) * MM, -0.0225, -0.0160, blk, 0.0002)
        box(L.body, 'ss_ear_tab', (X + sx * 20.6 - 0.8) * MM, (X + sx * 20.6 + 0.8) * MM, (Y - 2.5) * MM, (Y + 2.5) * MM, -0.0215, -0.0185, blk, 0.0002)


# =====================================================================
# Lastik kollar (rubber arm) — üretici STEP'lerinden (3d-files_2026-10-02_1139.zip)
# Kol sözleşmesi (lamps.py): orijin taban plakasının DUVAR yüzü merkezi, Y yukarı, kol +Z (dışa); kafada beyaz −X (öne),
# kırmızı +X (arkaya), turuncu uçta (+Z). Hepsi 'outline' işlevi (ürün föyü: arka/ön pozisyon + yan marker, tek devre).
# Işık parçaları CAD'in kendi yüzlerinden ayrılır: biçim birebir (LDCC halka bandı ve LED'ler, LD 2994 ">—<" kanalları).
# =====================================================================
def _move(bm, v):
    bmesh.ops.translate(bm, vec=Vector(v), verts=bm.verts)
    return bm


def _xf(bm, M):
    bm.transform(M)
    return bm


# LDCC 2698 CAD: dışa +x, yukarı +y, lens yüzleri ±z (beyaz +z), plaka duvar yüzü x −127,7, plaka merkezi y −95,7
LDCC_M = Matrix(((0, 0, -1, 0), (-1, 0, 0, -0.1277), (0, 1, 0, 0.0957), (0, 0, 0, 1)))


@product('ldcc2698', 'LDCC 2698', 'arm', 'Lastik kol, uzun (versiyon 1) — üretici CAD')
def build_ldcc2698_cad(L):
    cad = os.path.join(CAD_ROOT, 'ldcc2698')
    if not os.path.exists(os.path.join(cad, 'p000.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_ldcc2698(L)
    body = _stl(os.path.join(cad, 'p000.stl'), LDCC_M)
    _simplify(body, 1.0)
    _mesh_obj('cad_arm', body, [mat('Rubber')], L.body, 35, decimate=None if FAST else 14000)
    off = {'white': '#dde1e6', 'red': '#9c1f1b'}
    for part, side, leds in (('p022', 'white', range(12, 22)), ('p011', 'red', range(1, 11))):
        sg = 1.0 if side == 'white' else -1.0  # lensin dış normali (CAD z)
        raw = _stl(os.path.join(cad, part + '.stl'), False)
        # lens: uçtaki turuncu pencere (x > 36 mm) ve yüz (beyaz: renksiz, kırmızı)
        lens = raw.copy()
        for f in lens.faces:
            f.material_index = 2 if f.calc_center_median().x > 0.036 else (1 if side == 'white' else 0)
        _simplify(lens, 0.8)
        _mesh_obj('cad_lens_' + side, _xf(lens, LDCC_M), [_lmat('red'), _lmat('clear'), _lmat('amber')], L.lens, 40, decimate=None if FAST else 5000)
        # halka bandı (z ±18,5 düzlemi: pencereyi çevreleyen, LED'lerin oturduğu bant) lensin 0,6 mm altında ışır
        ring = _subset(raw, lambda f: f.normal.z * sg > 0.995 and abs(f.calc_center_median().z - 0.0185 * sg) < 0.0004)
        _mesh_obj('ring_' + side, _xf(_move(ring, (0, 0, -0.0006 * sg)), LDCC_M), [_emat('outline', side, off[side], 'cad')], L.E('outline'), 40)
        # iç pencere (z ±17): ardında koyu panel (beyaz yüzde füme, kırmızı yüzde kırmızı reflektör)
        win = _subset(raw, lambda f: f.normal.z * sg > 0.995 and abs(f.calc_center_median().z - 0.0170 * sg) < 0.0004)
        _mesh_obj('window_' + side, _xf(_move(win, (0, 0, -0.0012 * sg)), LDCC_M), [mat('HousingGloss' if side == 'white' else 'ReflectorRed')], L.inner, 40)
        # uçtaki turuncu pencere ışığı (yan marker)
        end = _subset(raw, lambda f: f.calc_center_median().x > 0.038 and f.normal.x > 0.8)
        _mesh_obj('amber_' + side, _xf(_move(end, (-0.0006, 0, 0)), LDCC_M), [_emat('outline', 'amber', '#e39a35', 'cad')], L.E('outline'), 40)
        raw.free()
        for i in leds:
            p = os.path.join(cad, f'p{i:03d}.stl')
            if os.path.exists(p):
                _mesh_obj(f'led_{side}{i}', _stl(p, LDCC_M), [_emat('outline', side, off[side], 'cad')], L.E('outline'), 40)
    for i in (23, 24):
        p = os.path.join(cad, f'p{i:03d}.stl')
        if os.path.exists(p):
            sb = _stl(p, LDCC_M)
            _simplify(sb, 2.0)
            _mesh_obj(f'screw{i}', sb, [mat('Zinc')], L.body, 35, decimate=None if FAST else 300)


# LD 2994 CAD: montaj yüzü yatay modellenmiş — dışa +z, yukarı −x, lens yüzleri ±y (beyaz −y), plaka duvar yüzü z −197,7,
# plaka merkezi x 406,4 y 166,4. Kafa merkezi: x 304,7, z −35,3 (kanalların simetri ekseni).
LD_M = Matrix(((0, 1, 0, -0.1664), (0, 0, -1, -0.1977), (-1, 0, 0, 0.4064), (0, 0, 0, 1)))
# ">—<" kanalının orta çizgisi (yüz düzleminde mm: u dışa, v yukarı; kafa merkezinden), alt kanal v'nin aynası
LD_CHEV = [(-25.0, 15.2), (-17.2, 7.6), (17.0, 7.6), (25.0, 15.2)]


def _seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1e-9)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


@product('ld2994', 'LD 2994', 'arm', 'DRAGON lastik kol — üretici CAD')
def build_ld2994_cad(L):
    cad = os.path.join(CAD_ROOT, 'ld2994')
    if not os.path.exists(os.path.join(cad, 'p000.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_ld2994(L)
    raw = _stl(os.path.join(cad, 'p000.stl'), False)
    chev = [LD_CHEV, [(u, -v) for u, v in LD_CHEV]]

    def zone(f):
        c = f.calc_center_median()
        x, y, z = c.x * 1000, c.y * 1000, c.z * 1000
        if z < -237.7:
            return None  # kablo: duvarın 40 mm ötesi atılır
        if x < 331.0 and z > -75.0:
            u, v = z + 35.3, 304.7 - x
            if abs(y - 166.4) > 14.0 and any(min(_seg_dist((u, v), a, b) for a, b in zip(ch, ch[1:])) <= 2.3 for ch in chev):
                return 'white' if y < 166.4 else 'red'
            if z > -3.0 and f.normal.z > 0.5 and abs(y - 166.4) <= 9.8 and min(abs(v - 5.3), abs(v + 5.3)) <= 1.8:
                return 'amber'
            return 'head'
        return 'arm'
    zones = [zone(f) for f in raw.faces]
    for key, mats_, grp, dec in (('arm', [mat('Rubber')], L.body, 10000), ('head', [mat('Housing')], L.body, 5000)):
        b = _subset(raw, lambda f: zones[f.index] == key)
        _simplify(b, 1.0)
        _mesh_obj('cad_' + key, _xf(b, LD_M), mats_, grp, 35, decimate=None if FAST else dec)
    off = {'white': '#dde1e6', 'red': '#a3201b', 'amber': '#e39a35'}
    for key in ('white', 'red', 'amber'):
        b = _subset(raw, lambda f: zones[f.index] == key)
        print('LD2994', key, len(b.faces))
        _simplify(b, 1.0)
        _mesh_obj('neon_' + key, _xf(b, LD_M), [_emat('outline', key, off[key], 'cad')], L.E('outline'), 40, decimate=None if FAST else 2500)
    raw.free()
    # montaj: taban plakasının iki M5 deliğinde (±39 mm, plakadan Ø5,1 kanal, dış yüz z ~13; STEP'te vida yok) yuvarlak başlı
    # vidalar (LDCC 2698'in STEP vidalarıyla aynı yerde; tampon uç sacındaki somunlara girer)
    for y in (-0.039, 0.039):
        cyl(L.body, 'screw_head', 0.0042, (0.0, y, 0.0126), (0.0, y, 0.0148), mat('Zinc'), 20, bevel=0.0008)


# =====================================================================
# Plaka aydınlatması — üretici STEP'lerinden (3d-files_2026-10-02_1139.zip) ve ürün paketlerinden (vault LTD-229.zip,
# LTD-2834.zip, RTR-3366.zip: föy, teknik çizim, fotoğraf, video).
# Lamba sözleşmesi (site equipment.ts): taban y = 0 (civatalar −y, taşıyıcının dikey yüzüne girer), +Y tabandan yukarı (sitede
# arkaya bakar), ışık penceresi +Z'ye (sitede plakanın ortasına) bakar, orijin lambanın derinlik ortasında. Çizim HOR 47:
# lambalar plakanın iki yanında, kenardan 40–80 mm, ışık içe.
# RTR 3366 çerçeve: arka yüz z = 0 (taşıyıcıya), +Z dışa, Y yukarı, X genişlik; plaka yuvası MOUNT_plate boşluğunda.
# =====================================================================
def _cad_parts(cad, M, names, angle=0.5):
    """Var olan STL parçaları → {ad: bmesh} (Blender yerel, düzlemsel yüzler birleştirilmiş)"""
    out = {}
    for nm in names:
        p = os.path.join(cad, nm + '.stl')
        if os.path.exists(p):
            b = _stl(p, M)
            if angle:
                _simplify(b, angle)
            out[nm] = b
    return out


def _assembly_exterior(parts):
    """Parçalar birlikte: her parçanın dışarıdan görünen yüzleri {ad: [bool]} (öbür parçalar ışını keser)"""
    big = bmesh.new()
    me = bpy.data.meshes.new('_asm')
    spans = {}
    for nm, b in parts.items():
        b.faces.index_update()
        n0 = len(big.faces)
        b.to_mesh(me)
        big.from_mesh(me)
        spans[nm] = (n0, len(big.faces))
    bpy.data.meshes.remove(me)
    flags = _exterior(big)
    big.free()
    return {nm: flags[a:b] for nm, (a, b) in spans.items()}


def _loc(f):
    """Yüz merkezi, three yerel mm"""
    return _three(f.calc_center_median())


def _glow(fn, color, off_hex, gain):
    """Işık geçiren buzlu/optik yüzey: sönükken off_hex, işlev yanınca şiddetin gain oranında ışır (E.<işlev>.<renk>.g<yüzde>)"""
    m = _emat(fn, color, off_hex, f'g{int(round(gain * 100))}')
    m['gain'] = gain
    return m


def _plate_parts(L, parts, ext, spec, prefix):
    """spec: {ad: (malzemeler, grup, üçgen hedefi)}; dış yüzler alınır, sadeleştirilir"""
    for nm, b in parts.items():
        if nm not in spec:
            b.free()
            continue
        mats_, grp, dec = spec[nm]
        sb = _subset(b, lambda f: ext[nm][f.index])
        b.free()
        _mesh_obj(f'{prefix}_{nm}', sb, mats_, grp, 35, decimate=None if FAST else dec)


# LTD 229 (HOR 47) CAD: x genişlik, +y yukarı (taban y −33,5), lens +z (z −42,25…19,95; derinlik ortası −11,15)
LTD229_M = Matrix(((1, 0, 0, 0), (0, 0, -1, -0.01115), (0, 1, 0, 0.0335), (0, 0, 0, 1)))


@product('ltd229', 'LTD 229', 'plate', 'LED plaka lambası (HOR 47), 3 LED — üretici CAD')
def build_ltd229_cad(L):
    cad = os.path.join(CAD_ROOT, 'ltd229')
    if not os.path.exists(os.path.join(cad, 'p009.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_ltd229(L)
    parts = _cad_parts(cad, LTD229_M, [f'p{i:03d}' for i in range(13)])
    # lens sadeleştirilmez: kavisli ön yüzde birleştirilen uzun üçgenlerin merkezi yüzeyin altına düşüyor, ön yüz testi şaşıyordu
    parts['p009'].free()
    parts['p009'] = _stl(os.path.join(cad, 'p009.stl'), LTD229_M)
    # kapakta (p008) gövdeden kopuk küçük artıklar var (sınır kutusu ±70 mm): lamba zarfı dışındakiler atılır
    _drop_small(parts['p008'], lambda mn, mx, n: n < 500 and (mn[0] < -49.5 or mx[0] > 49.5 or mn[2] < -32.0 or mx[2] > 32.5))
    # kablo: tabandan 30 mm (gerisini site çizer)
    cab = parts['p012']
    parts['p012'] = _subset(cab, lambda f: _loc(f)[1] > -30.0)
    cab.free()
    ext = _assembly_exterior(parts)
    lens = parts.pop('p009')
    zinc, steel = mat('Zinc'), mat('Stainless')
    _plate_parts(L, parts, ext, {
        'p000': ([mat('Housing')], L.body, 2500), 'p008': ([mat('Housing')], L.body, 6000), 'p001': ([mat('Rubber')], L.body, 300),
        'p002': ([zinc], L.body, 300), 'p003': ([zinc], L.body, 300), 'p004': ([zinc], L.body, 200), 'p005': ([zinc], L.body, 200),
        'p006': ([zinc], L.body, 120), 'p007': ([zinc], L.body, 120), 'p010': ([steel], L.body, 300), 'p011': ([steel], L.body, 300),
        'p012': ([mat('Cable')], L.body, 400)}, 'ltd229')

    # lens: buzlu ön panel (fotoğrafta açık gri, yanınca bütünü ışır), ortada şeffaf pencere, pencerenin iç yüzünde nervürlü
    # silindirik optik + 3 LED konisi (CAD'de var), arkasında 3 LED
    cs = [_loc(f) for f in lens.faces]
    zfront = max(c[2] for c in cs)
    tun = [c for c in cs if c[2] < zfront - 6.0]  # pencerenin ardındaki tünel duvarları (lensin parçası)
    wx0, wx1 = min(c[0] for c in tun), max(c[0] for c in tun)
    wy0, wy1 = min(c[1] for c in tun), max(c[1] for c in tun)
    zback = min(c[2] for c in tun)
    print(f'LTD229 window x {wx0:.1f}..{wx1:.1f} y {wy0:.1f}..{wy1:.1f} zfront {zfront:.1f} zback {zback:.1f}')
    # ön yüz neredeyse düz: CAD tessellasyonu büyük üçgenler, pencere sınırını kesiyor. Lens pencere kenarlarından bölünür
    for co, no in (((wx0, 0, 0), (1, 0, 0)), ((wx1, 0, 0), (1, 0, 0)), ((0, 0, wy0), (0, 0, 1)), ((0, 0, wy1), (0, 0, 1))):
        geom = lens.verts[:] + lens.edges[:] + lens.faces[:]
        bmesh.ops.bisect_plane(lens, geom=geom, plane_co=Vector(co) / 1000, plane_no=Vector(no))
    bmesh.ops.triangulate(lens, faces=lens.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    lens.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(lens)
    out = Vector((0, -1, 0))  # yerel +Z (Blender −Y)
    inwin = lambda c: wx0 - 0.05 <= c[0] <= wx1 + 0.05 and wy0 - 0.05 <= c[1] <= wy1 + 0.05
    for f in lens.faces:
        c = _loc(f)
        if not inwin(c):
            f.material_index = 0  # buzlu panel (kabartma yazılar dahil)
        elif tree.ray_cast(f.calc_center_median() + f.normal * 0.0002, out, 1.0)[0] is None:
            f.material_index = 1  # pencerenin ön yüzü: şeffaf
        elif c[2] > zfront - 4.5:
            f.material_index = 2  # pencerenin iç yüzündeki optik
        else:
            f.material_index = 1  # tünel duvarları
    # LED konilerinin tepeleri (lens CAD'inin iç yüzünden ölçüldü, simetrik): üst orta, alt sol ve sağ; optik yüzü z ≈ 29,6
    leds = [(0.0, 43.4, 29.6), (16.4, 27.5, 29.6), (-16.4, 27.5, 29.6)]
    _mesh_obj('ltd229_lens', lens, [_glow('plate', 'white', '#c9cdd2', 0.45), _lmat('clear'), _glow('plate', 'white', '#eef0f2', 0.7)], L.lens, 40,
              decimate=None if FAST else 12000)
    # LED sıcak noktaları (koni tepesinin 0,4 mm önünde) ve arkada LED kartı
    bmd = bmesh.new()
    for x, y, z in leds:
        ring_ = [bmd.verts.new(bl(((x + 1.5 * math.cos(a * math.pi / 6)) / 1000, (y + 1.5 * math.sin(a * math.pi / 6)) / 1000, (z + 0.4) / 1000)))
                 for a in range(12)]
        bmd.faces.new(ring_)
    _obj('led', bmd, E('plate', 'white'), L.E('plate'), 0.0)
    box(L.inner, 'pcb', (wx0 + 0.6) / 1000, (wx1 - 0.6) / 1000, (wy0 + 0.6) / 1000, (wy1 - 0.6) / 1000, (zback - 1.2) / 1000, zback / 1000, mat('Pcb'))


# LTD 2834 (HOR 127) CAD: x genişlik, +z yukarı (Π neon tepede), difüzör −y (y merkezi −3,66). Gövdenin alt yüzü z −37,6; altındaki
# 14 mm (z −52'ye kadar) iki M5 saplama. Yerel y = 0 gövdenin alt yüzü (tampona oturan yüz; önceden saplamaların ucuydu ve lamba
# webden 14 mm havada kalıyordu, kullanıcı 2026-10-23)
LTD2834_M = Matrix(((1, 0, 0, 0), (0, 1, 0, 0.00366), (0, 0, 1, 0.0376), (0, 0, 0, 1)))


@product('ltd2834', 'LTD 2834', 'plate', 'Plaka lambası + kırmızı neon pozisyon (HOR 127), 12 LED — üretici CAD')
def build_ltd2834_cad(L):
    cad = os.path.join(CAD_ROOT, 'ltd2834')
    if not os.path.exists(os.path.join(cad, 'p005.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_ltd2834(L)
    parts = _cad_parts(cad, LTD2834_M, [f'p{i:03d}' for i in range(7)])
    ext = _assembly_exterior(parts)
    zinc = mat('Zinc')
    # süt beyazı difüzör yanınca homojen ışır (video); Π ışık kılavuzu kırmızı (sönükken parlak koyu kırmızı, fotoğraf)
    _plate_parts(L, parts, ext, {
        'p000': ([mat('Rubber')], L.body, 300), 'p001': ([mat('Housing')], L.body, 3000), 'p002': ([zinc], L.body, 300),
        'p003': ([zinc], L.body, 300), 'p004': ([mat('Housing')], L.body, 8000),
        'p005': ([_emat('plate', 'white', '#eef1f4', 'cad')], L.E('plate'), 2500),
        'p006': ([_emat('position', 'red', '#a8121b', 'cad')], L.E('position'), 3000)}, 'ltd2834')
    # kablo: tabandan taşıyıcıya (gerisini site çizer)
    tube(L.body, 'cable', [(0.0, 0.003, -0.020), (0.0, -0.012, -0.021), (0.0, -0.030, -0.026)], 0.0028, mat('Cable'), 3, smooth=True)


# RTR 3366 (HOR 160) CAD: x genişlik (merkez −48,86), y yukarı (merkez 20,78), +z dışa (arka yüz z 984,86); 530,6 × 158,7 × 42,9
RTR_M = Matrix(((1, 0, 0, 0.048855), (0, 0, -1, 0.98486), (0, 1, 0, -0.02078), (0, 0, 0, 1)))
# plaka yuvası (mm, yerel; plakanın ön yüzü): taşıyıcı yüzü z 14,7, üzerinde 6 yaylı tırnak z 17,2'ye çıkar ve plakayı üst
# dudağa (z 18,7…20,2, plakanın üst kenarını 5 mm örter) bastırır: plaka 17,2…18,4 arasında. Alt bandın üst kenarı y −53,0 ile
# ışık modüllerinin alt yüzü y 60,7 arası 113,7 mm açıklık, 110 mm'lik plaka ortada
RTR_SEAT = (0.0, 3.85, 18.4)


@product('rtr3366', 'RTR 3366', 'plate', 'LED aydınlatmalı plaka çerçevesi (HOR 160), 12 LED — üretici CAD')
def build_rtr3366_cad(L):
    cad = os.path.join(CAD_ROOT, 'rtr3366')
    if not os.path.exists(os.path.join(cad, 'p002.stl')):
        print('CAD YOK (RTR 3366 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    parts = _cad_parts(cad, RTR_M, [f'p{i:03d}' for i in range(10)])
    ext = _assembly_exterior(parts)
    # ışık modülleri (üst saçağın altında 3 adet, 4'er LED): alta bakan pencere ışır, gerisi siyah gövde
    for nm in ('p004', 'p005', 'p006'):
        b = parts.pop(nm)
        sb = _subset(b, lambda f: ext[nm][f.index])
        b.free()
        ys = [_loc(f)[1] for f in sb.faces]
        ylo = min(ys)
        for f, y in zip(sb.faces, ys):
            f.material_index = 1 if (f.normal.z < -0.7 and y < ylo + 1.0) else 0  # Blender −Z = yerel −Y (aşağı)
        print('RTR module', nm, 'window faces', sum(1 for f in sb.faces if f.material_index == 1), 'y', round(ylo, 1))
        _mesh_obj('rtr_' + nm, sb, [mat('Housing'), _emat('plate', 'white', '#e3e7ea', 'cad')], L.E('plate'), 35, decimate=None if FAST else 1200)
    _plate_parts(L, parts, ext, {
        'p002': ([mat('Housing')], L.body, 26000), 'p003': ([mat('Housing')], L.body, 2500),
        'p007': ([mat('HousingGloss')], L.body, 1000), 'p008': ([mat('HousingGloss')], L.body, 1000)}, 'rtr')
    # plaka yuvası (MOUNT_plate): plakanın arka yüzünün merkezi
    mnt = bpy.data.objects.new('MOUNT_plate', None)
    mnt.location = bl(tuple(v / 1000 for v in RTR_SEAT))
    scene.collection.objects.link(mnt)
    L.empties = [mnt]
    # kablo: alt kenarın ortasından aşağı (çizim), arka yüze yakın
    tube(L.body, 'cable', [(0.0, -0.0790, 0.0045), (0.0, -0.1000, 0.0045), (0.0, -0.1150, 0.0020)], 0.0030, mat('Cable'), 3, smooth=True)


# =====================================================================
# Tutuculu marker LD 2774 (turuncu yan) / LD 2773 (beyaz ön) — HOR 123. Üretici STEP "LD 2773, 2774, 2775" (tek geometri,
# lens rengi değişir) + ürün paketleri (Downloads/LD-2774.zip, LD-2773.zip: 12 fotoğraf, teknik çizim).
# STEP'te: tutucu (p000, L biçim: arka dikey plaka + üstte geriye flanş, kaburga), lamba taban halkası (p001), iç taban (p002),
# lens (p003: dış kabuk, ön yüzde kabartma yazılar, İÇ YÜZDE GERÇEK altıgen retro prizmalar ~2,5 mm, neon çubuğun oturduğu cep),
# 2 × M5 saplama (p004, p005). Neon ışık kılavuzu YOK: fotoğraflara göre cebin tavanını izleyen süt beyazı kılavuz.
# Yanınca (foto 2, 3): çubuk parlak, lensin dış kenar halkası ışık iletir (parlak halka), retro alanı hafif aydınlanır.
# CAD ekseni (mm): x genişlik, y yukarı, z dışa (lens yönü); tutucu plakanın arka yüzü z = 0, plaka merkezi y −0,56.
# Site sözleşmesi (lamps_small.py ile aynı): plaka arka yüzü z = 0, lens +Z, Y yukarı, orijin plakanın sınır kutusu merkezi.
# =====================================================================
LD277X_M = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0.00056), (0, 0, 0, 1)))
LD277X_LAMP = (0.0, -15.2)  # lamba (stadyum) merkezi, CAD mm
LD277X_R, LD277X_A = 23.07, 36.85  # stadyum yarıçapı ve düz kısmın yarı uzunluğu (lens dış hattı 119,8 × 46,1)


def _stadium_sd(x, y, cx=0.0, cy=0.0, a=LD277X_A, r=LD277X_R):
    """Stadyum dış hattına işaretli uzaklık (mm; içeride negatif)"""
    dx = max(abs(x - cx) - a, 0.0)
    return math.hypot(dx, y - cy) - r


def _retro_cad(fn, color, gain):
    """CAD'deki gerçek retro prizma yüzleri: opak renkli, kaplamalı (prizma yüzleri ışığı geometriden yansıtır; normal doku yok,
    STL'de UV yok). Lensin iç yüzü önden arkasından görülür: çift yüzlü. Yanınca LED ışığıyla gain oranında aydınlanır."""
    key = f'E.{fn}.{color}.g{int(round(gain * 100))}'
    if key not in MATS:
        m = mat(f'Retro.{color}').copy()
        m.name = key
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.type in ('NORMAL_MAP', 'TEX_IMAGE')]:
            nt.nodes.remove(n)
        p = nt.nodes['Principled BSDF']
        p.inputs['Emission Color'].default_value = (*GLOW[color], 1.0)
        p.inputs['Emission Strength'].default_value = 0.0
        m.use_backface_culling = False
        m['fn'] = fn
        m['gain'] = gain
        MATS[key] = m
    return MATS[key]


def _ld277x_cad(L, fn, color):
    cad = os.path.join(CAD_ROOT, 'ld277x')
    if not os.path.exists(os.path.join(cad, 'p003.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return _s_ld2774_like(L, color)
    lens_col = 'amber' if color == 'amber' else 'clear'
    cx, cy = LD277X_LAMP
    # --- opak parçalar: dışarıdan görünen yüzler (lens ışını kesmez: arkasındaki taban ve halka görünür kalır) ---
    parts = {nm: _stl(os.path.join(cad, nm + '.stl'), False) for nm in ('p000', 'p001', 'p002', 'p004', 'p005')}
    for b in parts.values():
        _simplify(b, 0.5)
    ext = _assembly_exterior(parts)
    spec = {'p000': ([mat('Housing')], L.body, 4000), 'p001': ([mat('Housing')], L.body, 1800), 'p002': ([mat('Housing')], L.inner, 1200),
            'p004': ([mat('Zinc')], L.body, 160), 'p005': ([mat('Zinc')], L.body, 160)}
    for nm, b in parts.items():
        mats_, grp, dec = spec[nm]
        sb = _subset(b, lambda f: ext[nm][f.index])
        b.free()
        _mesh_obj(f'ld277x_{nm}', _xf(sb, LD277X_M), mats_, grp, 35, decimate=None if FAST else dec)

    # --- lens: yüz yüz sınıflandırma (CAD mm) ---
    lens = _stl(os.path.join(cad, 'p003.stl'), False)
    # lens zarfının dışındaki artıklar (sınır kutusu z 35,3'e uzanıyor; lens ön yüzü 23,4'te biter)
    lens.faces.ensure_lookup_table()
    stray = [f for f in lens.faces if f.calc_center_median().z * 1000 > 24.0]
    print('LD277X lens stray faces z>24:', len(stray))
    if stray:
        bmesh.ops.delete(lens, geom=stray, context='FACES')
    bar = lambda x, y: abs(x - cx) <= 52.6 and -22.4 <= y <= -8.0
    pocket, retro, rim, clear = [], [], [], []
    lens.faces.index_update()
    for f in lens.faces:
        c = f.calc_center_median() * 1000
        n = f.normal
        sd = _stadium_sd(c.x, c.y, cx, cy)
        if bar(c.x, c.y) and abs(c.x - cx) <= 50.6 and -21.8 <= c.y <= -9.4 and n.z < -0.3 and 19.2 < c.z < 21.4:
            pocket.append(f.index)  # cebin tavanı: neon kılavuz bunu izler
            f.material_index = 0
        elif not bar(c.x, c.y) and sd < -2.6 and 17.7 < c.z < 19.7 and n.z < 0.97:
            f.material_index = 1  # iç yüzdeki retro prizmalar
            retro.append(f)
        elif sd > -3.2 and c.z > 13.6 and n.z < 0.97 and (n.x * (c.x - cx) + n.y * (c.y - cy)) > 0.0:
            f.material_index = 2  # dış kenar halkası ve yuvarlatılmış kenar: ışık iletir
            rim.append(f)
        else:
            f.material_index = 0
    print(f'LD277X lens faces: pocket {len(pocket)} retro {len(retro)} rim {len(rim)} total {len(lens.faces)}')
    # neon kılavuz: cebin tavanının 0,3 mm altında, ışık veren ince levha + kenarlarında 2,4 mm'lik süt beyazı duvar
    pk = set(pocket)
    neon = _subset(lens, lambda f: f.index in pk)
    # düzlemsel yüzler birleşir (sınıflar ayrı kalır): prizma yüzleri zaten düz, yazılar ve ön yüz sadeleşir
    _simplify(lens, 0.5)
    _move(neon, (0, 0, -0.0003))
    edges = [e for e in neon.edges if e.is_boundary]
    ext_ = bmesh.ops.extrude_edge_only(neon, edges=edges)
    _move_v = [v for v in ext_['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(neon, vec=Vector((0, 0, -0.0024)), verts=_move_v)
    bmesh.ops.recalc_face_normals(neon, faces=neon.faces)
    _mesh_obj('neon', _xf(neon, LD277X_M), [_emat(fn, color, OFF[color], 'cad')], L.E(fn), 40, decimate=None if FAST else 900)
    _mesh_obj('ld277x_lens', _xf(lens, LD277X_M),
              [_lmat(lens_col), _retro_cad(fn, color, 0.16), _glow(fn, color, '#e6832a' if color == 'amber' else '#e9edf2', 0.55)],
              L.lens, 40, decimate=None if FAST else 9000)
    # tabanın ortasındaki kablo deliği: arkasında kablo rakoru (CAD'de yok; delikten arka plan görünüyordu)
    yl = (cy + 0.56) / 1000
    cyl(L.inner, 'grommet', 0.0098, (0.0, yl, 0.0028), (0.0, yl, 0.0102), mat('Rubber'), 24)
    # kablo: lambanın arkasından tutucunun orta deliğine, oradan rayın / dikmenin içine (sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, yl, 0.0035), (0.0, yl, -0.004), (0.0, yl - 0.004, -0.016)], 0.0028, mat('Cable'), 3, smooth=True)


@product('ld2774', 'LD 2774', 'side', 'Turuncu yan marker (HOR 123), neon çubuk, retro reflektör, L tutucu — üretici CAD')
def build_ld2774_cad(L):
    _ld277x_cad(L, 'marker', 'amber')


@product('ld2773', 'LD 2773', 'front', 'Beyaz ön pozisyon (HOR 123), neon çubuk, retro reflektör, L tutucu — üretici CAD')
def build_ld2773_cad(L):
    _ld277x_cad(L, 'front', 'white')


# =====================================================================
# LZD 2854 HEAVY DUTY (sol; sağ: LZD 2855, ayna) — HOR 129. Kaynaklar: üretici STEP "LZD 2854 - LZD 2857 - HOR 129",
# ürün paketi (Downloads/LZD-2854.zip: föy, teknik çizim, 13 fotoğraf), ürün sayfası (horpolautomotive.com).
# Föy: pozisyon 4 W, fren 10 W, sinyal 5,5 W, geri vites 4 W, sis 5,5 W, reflektör; 139 LED; DEĞİŞTİRİLEBİLİR LED modülleri.
# STEP'te: arka gövde (p000, modül yuvaları), ön çerçeve (p001, 4 pencere), 8 çerçeve vidası, 2 × M8 saplama + pul + somun,
# kablo rakoru (p18). Modüller (lens + LED) YOK: pencereler CAD çerçevesinden, modül içleri ürün fotoğraflarından.
#   Dıştan içe (lambanın geniş/dış ucu yerel −X): turuncu SİNYAL | büyük kırmızı (POZİSYON ışık kılavuzları + FREN LED'leri +
#   retro reflektör) | beyaz GERİ VİTES | kırmızı SİS. Küçük modüllerde 3-4-3-4-3-4-3 dizili 24 LED (yuvarlak optik).
#   Büyük modül (foto 5-2 sönük, 13 pozisyon, 12 fren): bütün alan retro prizma, içinden 4 düz kanal (kılavuz): üstte iki iç içe
#   "⌴", altta aynası; frende kanalların arasındaki 5-7-9-7-5 LED retronun ardından parlar.
# CAD ekseni (mm): lens +x, genişlik y (turuncu uç −y), yukarı z. Arka montaj yüzü x −50 (gövdenin büyük arka düzlemi).
# Yerel (site sözleşmesi, LZD 3194 ile aynı): X = CAD y, Y = CAD z, Z = CAD x + 50 (arka montaj yüzü z = 0, lens +Z).
# Lastik kol: lambaya değil tampona monte (kullanıcı 2026-10-21, Revizeler/Standart Dorse md. 14): adaptör ve MOUNT_arm yok.
# =====================================================================
LZD2854_M = Matrix(((0, 1, 0, 0), (-1, 0, 0, -0.050), (0, 0, 1, 0), (0, 0, 0, 1)))
LZD2854_H, LZD2854_C = 54.8, 18.5  # pencere yarı yüksekliği ve köşe pahı (ön çerçevenin x 20,5 kesiti)
LZD2854_WIN = {'turn': (-198.3, -130.7), 'big': (-114.3, 30.3), 'reverse': (46.7, 114.3), 'fog': (130.7, 198.3)}


def _oct(x0, x1, h=LZD2854_H, c=LZD2854_C, grow=0.0):
    x0, x1, h, c = x0 - grow, x1 + grow, h + grow, c + grow * 0.414
    return [(x0 + c, -h), (x1 - c, -h), (x1, -h + c), (x1, h - c), (x1 - c, h), (x0 + c, h), (x0, h - c), (x0, -h + c)]


def _band(pts, w):
    """Çoklu çizgiden w genişliğinde şerit çokgeni (köşelerde açıortay birleşim)"""
    n = len(pts)
    L_, R_ = [], []
    for i in range(n):
        ds = []
        for a, b in ((i - 1, i), (i, i + 1)):
            if 0 <= a and b < n:
                dx, dy = pts[b][0] - pts[a][0], pts[b][1] - pts[a][1]
                ln = math.hypot(dx, dy)
                ds.append((dx / ln, dy / ln))
        tx, ty = sum(d[0] for d in ds), sum(d[1] for d in ds)
        ln = math.hypot(tx, ty)
        tx, ty = tx / ln, ty / ln
        nx, ny = -ty, tx
        k = 1.0 / max(0.3, (nx * -ds[0][1] + ny * ds[0][0]))  # açıortayda kalınlık korunur
        L_.append((pts[i][0] + nx * w / 2 * k, pts[i][1] + ny * w / 2 * k))
        R_.append((pts[i][0] - nx * w / 2 * k, pts[i][1] - ny * w / 2 * k))
    return L_ + list(reversed(R_))


@product('lzd2854', 'LZD 2854', 'stop', 'HEAVY DUTY sol (sağ: LZD 2855, ayna), HOR 129, 139 LED — üretici CAD + ürün fotoğrafları')
def build_lzd2854_cad(L):
    cad = os.path.join(CAD_ROOT, 'lzd2854')
    if not os.path.exists(os.path.join(cad, 'p001.stl')):
        print('CAD YOK (LZD 2854 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    m_ = lambda pts: [(x / 1000, y / 1000) for x, y in pts]

    # ===== 1) CAD: gövde, çerçeve, vidalar, saplamalar; dışarıdan görünen yüzler =====
    # p16/17: arka yüzdeki iki kare modül kapağı (gövdenin arka açıklıklarını kapatır; tampon arkasından bakınca görünür)
    names = [f'p{i:03d}' for i in range(19)]
    parts = _cad_parts(cad, LZD2854_M, names, angle=0.5)
    ext = _assembly_exterior(parts)
    steel, zinc = mat('Stainless'), mat('Zinc')
    spec = {'p000': ([mat('Housing')], L.body, 26000), 'p001': ([mat('Housing')], L.body, 9000), 'p018': ([mat('Rubber')], L.body, 300)}
    for i in range(2, 10):
        spec[f'p{i:03d}'] = ([steel], L.body, 220)
    for i in range(10, 16):
        spec[f'p{i:03d}'] = ([zinc], L.body, 260)
    for i in (16, 17):
        spec[f'p{i:03d}'] = ([mat('HousingGloss')], L.body, 700)
    _plate_parts(L, parts, ext, spec, 'lzd2854')

    # ===== 2) fotoğraf → lamba: 8 çerçeve vidası (aynı düzlemde: düzlemsel eşleme; foto 5-2 neredeyse dik çekim) =====
    photo = [(76.9, 457.3), (408.2, 445.5), (1022.8, 445.2), (1678.5, 453.2), (75.2, 867.4), (405.7, 878.4), (1022.4, 876.9), (1679.3, 866.1)]
    lamp = [(-209.56, 53.56), (-122.5, 56.0), (38.5, 56.0), (209.56, 53.55), (-209.56, -53.56), (-122.5, -56.0), (38.5, -56.0), (209.56, -53.55)]
    Hm = _homography(photo, lamp)
    def ph(pts):
        out = []
        for u, v in pts:
            w = Hm @ np.array([u, v, 1.0])
            out.append((float(w[0] / w[2]), float(w[1] / w[2])))
        return out
    err = max(math.dist(p, q) for p, q in zip(ph(photo), lamp))
    print(f'LZD2854 homography max err {err:.2f} mm')

    # ===== 3) lensler (modül önleri): çerçeve penceresinin 1,5 mm dışına (kenarı çerçevenin ardında), z 65…67,5 =====
    ZL0, ZL1 = 65.0, 67.5
    lens_col = {'turn': 'amber', 'big': 'red', 'reverse': 'clear', 'fog': 'red'}
    for key, (x0, x1) in LZD2854_WIN.items():
        ob = prism(L.lens, 'lens_' + key, m_(_oct(x0, x1, grow=1.5)), ZL0 / 1000, ZL1 / 1000, _lmat(lens_col[key]), 0.0)
        set_uv_planar(ob, 0.013)  # lensin ince kare deseni ~1,6 mm (foto 5-2; doku döşemede 8 hücre)

    # ===== 4) küçük modüller: 24 LED, yuvarlak optik (krom kap, yanınca LED'in ışığıyla bantlar halinde parlar) =====
    # Kap dipten ağza üç bantta ışır (LZD 3194 geri vites kaplarıyla aynı yaklaşım): yanınca bütün daire aydınlanır, ortadaki LED
    # optiği en parlak (foto 8, 12); sönükken kaplar renkli lensin ardında krom (foto 5-2). Oranlar föy güçlerini izler: sinyal ve
    # sis 5,5 W, geri vites 4 W (fren 10 W: büyük modül en baskın).
    fn_col = {'turn': ('turn', 'amber'), 'reverse': ('reverse', 'white'), 'fog': ('fog', 'red')}
    rows = [(44.7, (-18.1, 0.0, 18.1)), (29.8, (-27.15, -9.05, 9.05, 27.15)), (14.9, (-18.1, 0.0, 18.1)), (0.0, (-27.15, -9.05, 9.05, 27.15)),
            (-14.9, (-18.1, 0.0, 18.1)), (-29.8, (-27.15, -9.05, 9.05, 27.15)), (-44.7, (-18.1, 0.0, 18.1))]
    ZF = 57.0  # modül tabanı
    for key, (fn, col) in fn_col.items():
        x0, x1 = LZD2854_WIN[key]
        cx = (x0 + x1) / 2
        prism(L.inner, 'mod_floor_' + key, m_(_oct(x0, x1, grow=1.0)), (ZF - 1.0) / 1000, ZF / 1000, mat('HousingGloss'), 0.0)
        gains = (0.50, 0.38, 0.27) if col == 'white' else (0.62, 0.46, 0.32)
        # kap yansıması lensin renginde (turuncu / kırmızı lensin ardında beyaz yansıma olmaz), geri viteste koyu satenli krom
        tint = {'amber': '#c98a3c', 'red': '#9c3a34', 'white': '#a9aeb4'}[col]
        # LED'in önündeki küçük optik kubbe: sönükken fosfor sarısı (beyaz) / lens renginin açığı, yanınca tam şiddet
        core = _emat(fn, col, {'amber': '#f2a548', 'white': '#e9d98f', 'red': '#c83a30'}[col], 'core')
        for yy, xs in rows:
            for xx in xs:
                x, y = (cx + xx) / 1000, yy / 1000
                _cup_bands(L.E(fn), x, y, 63.8 / 1000, 0.0058, 0.0022, (63.8 - ZF - 0.4) / 1000, gains, fn, col, tint, 0.3)
                box(L.E(fn), 'led', x - 0.0013, x + 0.0013, y - 0.0013, y + 0.0013, (ZF + 0.1) / 1000, (ZF + 0.9) / 1000, E(fn, col))
                cyl(L.E(fn), 'optic_core', 0.0021, (x, y, 63.2 / 1000), (x, y, 63.6 / 1000), core, 16)

    # ===== 5) büyük modül: retro prizma levha, 4 ışık kılavuzu kanalı (pozisyon), fren LED'leri =====
    bx0, bx1 = LZD2854_WIN['big']
    bc = (bx0 + bx1) / 2
    # kılavuz orta çizgileri (foto 5-2, üst yarı ölçüldü; alt yarı ve sol-sağ simetrik): B1 üst kenardan, B2 yan kenardan iner
    B1 = ph([(505, 470), (575, 535), (855, 535), (910, 470)])
    B2 = ph([(446, 522), (560, 607), (870, 607), (982, 522)])
    def sym(poly):
        # orta çizgiye göre simetrik: sol yarının ve sağ yarının aynalı ortalaması (ölçüm gürültüsü)
        n = len(poly)
        out = []
        for i in range(n):
            a, b = poly[i], poly[n - 1 - i]
            dx = ((a[0] - bc) - (b[0] - bc)) / 2
            out.append((bc + dx, (a[1] + b[1]) / 2))
        return out
    B1, B2 = sym(B1), sym(B2)
    # uçlar pencere kenarının 3 mm ötesine uzatılır (çerçevenin ardında biter)
    def extend(poly, d=4.0):
        p = list(poly)
        for i, j in ((0, 1), (-1, -2)):
            dx, dy = p[i][0] - p[j][0], p[i][1] - p[j][1]
            ln = math.hypot(dx, dy)
            p[i] = (p[i][0] + dx / ln * d, p[i][1] + dy / ln * d)
        return p
    B1, B2 = extend(B1), extend(B2)
    guides = [B1, B2, [(x, -y) for x, y in B2], [(x, -y) for x, y in B1]]
    print('LZD2854 B1', [(round(x, 1), round(y, 1)) for x, y in B1])
    print('LZD2854 B2', [(round(x, 1), round(y, 1)) for x, y in B2])
    ZR = 63.6  # retro prizmaların ön yüzü (lensin 1,4 mm gerisi)
    win_big = _oct(bx0, bx1, grow=0.5)
    chans = [_band(g, 5.2) for g in guides]
    # fren LED'leri: 5-7-9-7-5, kılavuzların arasında (foto 12), yatay aralık 15,5 mm
    yB1, yB2 = B1[1][1], B2[1][1]
    rows_b = [((LZD2854_H + yB1) / 2, 5), ((yB1 + yB2) / 2, 7), (0.0, 9), (-(yB1 + yB2) / 2, 7), (-(LZD2854_H + yB1) / 2, 5)]
    print('LZD2854 brake rows', [(round(y, 1), n) for y, n in rows_b])
    bleds = [(bc + (k - (n - 1) / 2) * 15.5, yy) for yy, n in rows_b for k in range(n)]
    # Fren ışığı prizmaların kendisinden: LED retronun ardında, ışığı prizma hücrelerinden geçer (foto 12: her LED parlak bir
    # prizma kümesi, çevresi kademeli sönen kırmızı). LED'e uzaklığa göre dört bant; şiddet × oran: iki yakın bant bloom eşiğinin
    # üstünde (ışır), dış bantlar altında (kırmızı dolgu). Sönükken hepsi aynı retro: desen kesintisiz (önceki düz LED/hale
    # diskleri sönükken leke gibi görünüyordu). Föy: fren 10 W, geri vites 4 W: fren bölmesi baskın (kullanıcı: fren zayıftı).
    # Hücre ~2,2 mm (fotoğrafta ~1,5 mm; üçgen bütçesi için biraz iri)
    dmin = lambda x, y: min(math.hypot(x * 1000 - a, y * 1000 - b) for a, b in bleds)
    for lo, hi, g in ((0.0, 3.2, 0.95), (3.2, 6.2, 0.64), (6.2, 9.5, 0.42), (9.5, 1e9, 0.27)):
        _s_hex_retro(L.inner, 'big_retro', m_(win_big), [m_(c) for c in chans], ZR / 1000, 0.0022, 0.0008, _retro_cad('stop', 'red', g),
                     keep=lambda x, y, lo=lo, hi=hi: lo <= dmin(x, y) < hi)
    prism(L.inner, 'big_floor', m_(_oct(bx0, bx1, grow=1.0)), (ZF - 1.0) / 1000, ZF / 1000, mat('ReflectorRed'), 0.0)
    # kılavuz: kanal tabanında ışık veren şerit (sönükken koyu kırmızı, düz; foto 5-2'de prizmasız koyu bant)
    # kılavuz şeridi pozisyon şiddetinin %85'inde (bloom eşiğinin üstü, foto 13'te parlak çizgi); içindeki LED'ler ~9 mm aralıkla tam şiddette nokta (kılavuz boyunca
    # parlak noktalar)
    gmat = _glow('position', 'red', '#6e1612', 0.85)
    dots = bmesh.new()
    for i, g in enumerate(guides):
        prism(L.E('position'), f'guide{i}', m_(_band(g, 4.0)), (ZR - 2.6) / 1000, (ZR - 0.6) / 1000, gmat, 0.0004)
        prism(L.inner, f'chan{i}', m_(_band(g, 5.4)), (ZR - 3.0) / 1000, (ZR - 2.6) / 1000, mat('HousingGloss'), 0.0)
        for (ax, ay), (bx_, by_) in zip(g, g[1:]):
            ln = math.hypot(bx_ - ax, by_ - ay)
            for k in range(int(ln // 9.0) + 1):
                t = (k + 0.5) * 9.0 / ln
                if t > 1:
                    break
                px, py = ax + (bx_ - ax) * t, ay + (by_ - ay) * t
                if not _inside(_oct(bx0, bx1, grow=-1.5), px, py):
                    continue
                ring_ = [dots.verts.new(bl(((px + 1.3 * math.cos(a * math.pi / 6)) / 1000, (py + 1.3 * math.sin(a * math.pi / 6)) / 1000, (ZR - 0.5) / 1000)))
                         for a in range(12)]
                dots.faces.new(ring_)
    print('LZD2854 guide dots', len(dots.faces), 'brake LED', len(bleds))  # kılavuz noktaları görsel (ışık çıkış izleri; föyün 139 LED'inin dağılımı doğrulanmadı)
    _obj('guide_leds', dots, _emat('position', 'red', '#7a1a16', 'hdled'), L.E('position'), 0.0)  # sönükken kılavuz renginde (fotoğrafta görünmez)
    # LED'in kendisi: retronun ardında (prizmaların arasından seçilir; sönükken görünmez)
    bmd = bmesh.new()
    for xx, yy in bleds:
        bmd.faces.new([bmd.verts.new(bl(((xx + 1.6 * math.cos(a * math.pi / 6)) / 1000, (yy + 1.6 * math.sin(a * math.pi / 6)) / 1000, (ZR - 1.2) / 1000)))
                       for a in range(12)])
    _obj('brake_led', bmd, E('stop', 'red'), L.E('stop'), 0.0)

    # lastik kol lambaya takılmaz: tampona (stop taşıyıcı plakasının dış kenarı) monte (kullanıcı 2026-10-21, revize md. 14)
    # kablo: arkadaki rakordan 6 × 0,5 kablo (sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, 0.0, -0.004), (0.0, 0.0, -0.020), (0.0, -0.010, -0.034)], 0.0040, mat('Cable'), 3, smooth=True)


# =====================================================================
# LUNA — LZD 2448 (HOR 96A: pozisyon + sinyal + fren) / LZD 2452 (HOR 96B: pozisyon + sis + geri vites), sol (sağ: 2449 /
# 2453, ayna). Kaynaklar: üretici STEP "LZD 2448, 2449, 2452, 2453" (ortak gövde), ürün paketleri (Downloads/LZD-2448.zip,
# LZD-2452.zip: föy, teknik çizim, 7 + 6 fotoğraf).
# STEP'te: kırmızı lens (p000, ortası D delikli kubbe), D penceresi (p001: lens + 9 mm derin ışık kutusu duvarları), krom çerçeve
# (p003, Ø167,6; çizimde Ø155: eski sürüm, CAD esas), gövde (p004), kablo rakoru (p002). İç parçalar YOK: fotoğraflardan.
#   Fotoğraf → lamba: lens kenarının elipsi (görünen yarıçap 56,3 mm) ve D penceresi (çizim: X −44…19, Y ±19; fotoğrafta
#   genişlik 64 mm, birebir). Kaplar fren / sis fotoğrafındaki LED noktalarından: 7 kap, merkezden 34,5 mm, 40° arayla
#   (0, ±40, ±80, ±120; fotoğrafın ~4° dönmesi simetriden düzeltildi), ağız Ø18,5, fasetli. Föy: 41 LED = 7 kap + D'de 12
#   (üstte 6 ışık kılavuzunun ardında + ortada 6 SMD) + halkada 22 (kılavuzun ardında, görünmez).
#   Kenarda kırmızı ışık kılavuzu halkası (pozisyon). D: üstte 6 dikey kılavuz dilimi (7 koyu ayraç), ortada beyaz devre
#   bandı + 6 SMD, altta eğik koyu reflektör, sağ yuvarlak uçta krom çanak. 2448'de turuncu lens içi turuncuya boyar.
#   Arkada siyah montaj halkası (fotoğraf; CAD'de yok): Ø167 / Ø113, 21 mm, gövdeyi örter (yüzey montajı).
# CAD ekseni (mm): lens +y, önden bakınca sağ = −x, yukarı +z. Yerel: X = −x, Y = z, Z = y + 21,7 (montaj halkasının arka yüzü
# z = 0). Lastik kol: tampona monte (kullanıcı kuralı, Revizeler/Standart Dorse md. 14), lambada bağlantı yok.
# =====================================================================
LUNA_M = Matrix(((-1, 0, 0, 0), (0, -1, 0, -0.0217), (0, 0, 1, 0), (0, 0, 0, 1)))


def _luna_D(d=0.0, n=10):
    """D penceresi (yerel mm), d kadar içeri: sol kenar hafif yay (X −44,9 + 4,6 (Y/20)²), sağ uç R13 köşeli"""
    h = 20.0 - d
    pts = []
    for i in range(n + 1):  # sol kenar, aşağıdan yukarı
        y = -h + 2 * h * i / n
        pts.append((-44.9 + d + 4.6 * (y / 20.0) ** 2, y))
    r = 13.0 - d
    for a in range(90, -91, -15):  # sağ üst köşe → sağ alt köşe
        t = math.radians(a)
        cy = 7.0 if a >= 0 else -7.0
        pts.append((6.0 + r * math.cos(t), cy + r * math.sin(t)))
    return _s_ccw(pts)


def _quad(group, name, pts, material, toward):
    """Tek dörtgen yüz (yerel mm köşeler), normali toward yönüne çevrilir"""
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new(bl(tuple(c / 1000 for c in p))) for p in pts])
    f.normal_update()
    if f.normal.dot(bl(toward)) < 0:
        f.normal_flip()
    return _obj(name, bm, material, group, 0.0)


def _luna(L, var):
    cad = os.path.join(CAD_ROOT, 'lzd2448')
    if not os.path.exists(os.path.join(cad, 'p004.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_lzd2448(L) if var == '2448' else 'skip'
    amb = var == '2448'
    dfn, dcol = ('turn', 'amber') if amb else ('reverse', 'white')
    cfn = 'stop' if amb else 'fog'
    m_ = lambda pts: [(x / 1000, y / 1000) for x, y in pts]
    Zm = lambda z: z / 1000

    # ===== 1) CAD: çerçeve, gövde, rakor (dış yüzler; lensler ışını kesmez), lensler =====
    parts = _cad_parts(cad, LUNA_M, ['p002', 'p003', 'p004'], angle=0.5)
    _drop_small(parts['p004'], lambda mn, mx, n: mx[0] > 80.0 or mn[0] < -80.0)  # gövdeden kopuk artık (sınır kutusu ±109)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p003': ([mat('Chrome')], L.body, 5000), 'p004': ([mat('Housing')], L.body, 9000),
                                 'p002': ([mat('Rubber')], L.body, 400)}, 'luna')
    # lensler: yalnız dışarıdan görünen yüzler (arka yüz de çizilince kırmızı iki kat koyulaşıyor, kaplar seçilmiyordu)
    for nm, key, col, dec in (('p000', 'luna_lens', 'red', 9000), ('p001', 'luna_dlens', 'amber' if amb else 'clear', 4000)):
        b = _stl(os.path.join(cad, nm + '.stl'), LUNA_M)
        _simplify(b, 0.4)
        ex = _front_faces(b)
        sb = _subset(b, lambda f: ex[f.index])
        b.free()
        _mesh_obj(key, sb, [_lmat(col)], L.lens, 40, decimate=None if FAST else dec)

    # ===== 2) montaj halkası (yüzey montajı; ürün fotoğrafları) =====
    frame(L.body, 'mount_ring', m_(circle(83.4, 72)), m_(circle(56.6, 72)), 0.0, Zm(20.9), mat('Housing'), 0.0012, 2)

    # ===== 3) kaplar (fren / sis): fasetli kırmızı krom, LED dipte =====
    ZP = 22.4  # kapların ve reflektör tabanının dibi (gövde iç tabanının önü)
    prism(L.inner, 'luna_floor', m_(circle(49.2, 64)), Zm(ZP - 0.6), Zm(ZP), mat('ReflectorRed'), 0.0)
    set_uv_planar(L.inner.objs[-1], 0.03)
    frame(L.inner, 'luna_wall', m_(circle(50.2, 64)), m_(circle(49.2, 64)), Zm(ZP - 0.6), Zm(30.4), mat('ReflectorRed'), 0.0)
    core = _emat(cfn, 'red', '#c83a30', 'core')
    for k in range(7):
        a = math.radians(-120 + 40 * k)
        x, y = 34.5 * math.cos(a), 34.5 * math.sin(a)
        _cup_bands(L.E(cfn), x / 1000, y / 1000, Zm(31.2), 0.00925, 0.0030, Zm(31.2 - ZP - 0.2), (0.62, 0.46, 0.32), cfn, 'red',
                   '#b8483e', 0.3, seg=12)
        # kap ağzının çemberi (fotoğrafta kaplar belirgin daireler)
        frame(L.inner, 'cup_rim', m_(circle(9.9, 24, x, y)), m_(circle(9.2, 24, x, y)), Zm(30.6), Zm(31.3), mat('ReflectorRed'), 0.0)
        box(L.E(cfn), 'led', (x - 1.3) / 1000, (x + 1.3) / 1000, (y - 1.3) / 1000, (y + 1.3) / 1000, Zm(ZP), Zm(ZP + 0.8), E(cfn, 'red'))
        cyl(L.E(cfn), 'optic_core', 0.0019, (x / 1000, y / 1000, Zm(ZP + 0.8)), (x / 1000, y / 1000, Zm(ZP + 1.4)), core, 16)

    # ===== 4) pozisyon: kenardaki ışık kılavuzu halkası (lensin iç yüzünün hemen gerisinde) =====
    frame(L.E('position'), 'luna_ring', m_(circle(55.4, 96)), m_(circle(49.8, 96)), Zm(28.6), Zm(30.6),
          _emat('position', 'red', '#d98f8a', 'luna'), 0.0006, 2)

    # ===== 5) D modülü: ışık kutusu (Z 27,6 … 35,8; D lensinin iç yüzü Z 36,3) =====
    ZD0, ZD1 = 27.6, 35.8
    light = '#e6b26a' if amb else '#e9e8e3'   # beyaz devre bandı / kılavuz (turuncu lensin ardında turuncu görünür)
    chrome_t = '#d6a35a' if amb else '#c3c8ce'
    dark_t = '#7a4a1c' if amb else '#5b5f66'
    Dw = _luna_D(2.2)
    frame(L.inner, 'd_liner', m_(Dw), m_(offset(Dw, 0.6)), Zm(ZD0), Zm(ZD1), mat('Reflector'), 0.0)
    prism(L.inner, 'd_back', m_(_luna_D(2.4)), Zm(ZD0 - 0.4), Zm(ZD0), mat('Reflector'), 0.0)
    X0, X1, XC, P = -40.0, 2.5, -19.0, 5.3
    smd = _emat(dfn, dcol, '#f0b45a' if amb else '#e8d58a', 'smd')  # sönükken SMD'nin fosfor / lens rengi (fotoğraf 6, 7)
    # orta bant: beyaz devre kartı, 6 SMD (yanınca bant da LED ışığıyla aydınlanır)
    box(L.E(dfn), 'd_band', X0 / 1000, X1 / 1000, -0.0065, 0.0080, Zm(ZD0), Zm(ZD0 + 0.4), _glow(dfn, dcol, light, 0.45))
    for i in range(6):
        x = XC + (i - 2.5) * P
        box(L.E(dfn), 'd_led', (x - 1.7) / 1000, (x + 1.7) / 1000, -0.0007, 0.0027, Zm(ZD0 + 0.4), Zm(ZD0 + 1.2), smd)
    # üst bant: 6 dikey ışık kılavuzu dilimi (ardında 6 LED), arada 7 koyu ayraç
    prism(L.E(dfn), 'd_guides', [(X0 / 1000, 0.0095), (X1 / 1000, 0.0095), (X1 / 1000, 0.0172), (X0 / 1000, 0.0172)], Zm(ZD0), Zm(ZD1 - 0.6),
          _glow(dfn, dcol, light, 0.85), 0.0)
    for i in range(7):
        x = XC + (i - 3) * P
        box(L.inner, 'd_sep', (x - 0.35) / 1000, (x + 0.35) / 1000, 0.0095, 0.0172, Zm(ZD1 - 3.5), Zm(ZD1 - 0.5), mat('HousingGloss'))
    # alt: eğik koyu reflektör (bandın altından lense doğru), önden-yukarıdan görülür
    _quad(L.E(dfn), 'd_floor', [(X0, -6.5, ZD0 + 0.4), (X1, -6.5, ZD0 + 0.4), (X1, -17.6, ZD1 - 0.8), (X0, -17.6, ZD1 - 0.8)],
          _refl_tint(dfn, dcol, 0.35, dark_t, 0.35), (0, 0.7, 0.7))
    # sağ uç: krom çanak (D'nin yuvarlak ucunu izleyen, dipte daralan yüzey; yanınca LED'in ışığını yansıtır)
    rim = [p for p in _luna_D(2.4, 16) if p[0] >= X1 - 0.01]
    rim.sort(key=lambda p: -math.atan2(p[1], p[0] - X1))  # üstten alta
    bm = bmesh.new()
    top = [bm.verts.new(bl((x / 1000, y / 1000, Zm(ZD1)))) for x, y in rim]
    bot = [bm.verts.new(bl(((X1 + (x - X1) * 0.35) / 1000, y * 0.62 / 1000, Zm(ZD0 + 0.4)))) for x, y in rim]
    for i in range(len(rim) - 1):
        bm.faces.new([top[i], top[i + 1], bot[i + 1], bot[i]])
    for f in bm.faces:
        f.normal_update()
        c = f.calc_center_median()
        # iç yüz D'nin içine (merkeze ve öne) bakar
        if f.normal.dot(bl((X1 / 1000, 0, Zm(ZD1 + 6))) - c) < 0:
            f.normal_flip()
    _obj('d_scoop', bm, _refl_tint(dfn, dcol, 0.45, chrome_t, 0.25), L.E(dfn), 0.0)

    # ===== 6) kablo: rakordan arkaya (sitede tesisat sürer) =====
    tube(L.body, 'cable', [(0.0, -0.0320, -0.0010), (0.0, -0.0320, -0.0120), (0.0, -0.0400, -0.0220)], 0.0028, mat('Cable'), 3, smooth=True)


@product('lzd2448', 'LZD 2448', 'stop', 'LUNA sol (sağ: LZD 2449, ayna), HOR 96A: pozisyon, sinyal, fren — üretici CAD + fotoğraflar')
def build_lzd2448_cad(L):
    return _luna(L, '2448')


@product('lzd2452', 'LZD 2452', 'stop', 'LUNA sol (sağ: LZD 2453, ayna), HOR 96B: pozisyon, sis, geri vites — üretici CAD + fotoğraflar')
def build_lzd2452_cad(L):
    return _luna(L, '2452')


# =====================================================================
# LDO 2660 — tepe (uyarı) lambası, HOR 110A, vidalı montaj, turuncu flaş 2,1 Hz, 24 LED, 14 W. Kaynaklar: üretici STEP
# "LDO 2660", ürün paketi (Downloads/LDO-2660.zip: föy, teknik çizim, 4 fotoğraf, video).
# STEP'te: siyah taban (p000), turuncu kubbe (p001; alt bandın iç yüzünde dikey Fresnel kaburgalar), yan tırnak (p002), alt
# montaj levhası Ø160 (p003), conta halkası Ø141 (p004). LED modülü YOK: fotoğraflardan (foto 1 sönük, foto 3 yanık):
#   alt bant (y 43…66) Fresnel'in ardında turuncu reflektör; y 66'da LED tablası; y 68…86 arasında 12 dışa bakan reflektör kap
#   (üst kenarları fotoğraftaki dalgalı / taraklı çizgi), her kapta 2 LED (24); üstte krom kapak. Yanınca kap halkası en
#   parlak bant (foto 3), alt bant ve kubbe turuncuyla aydınlanır.
# CAD ekseni (mm): y yukarı (montaj levhasının altı y −2,5), lamba ekseni y. Yerel: three (x, y + 2,5, z); taban y = 0.
# =====================================================================
LDO_M = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0.0025), (0, 0, 0, 1)))


def _radial_cup(group, ang, r_in, r_out, y, mouth, back, gains, fn, color, tint, rough, seg=20):
    """Dışa (yatay, ang yönünde) bakan LED kabı: r_in'de dip, r_out'ta ağız; içi önden görülür, bantlar halinde ışır"""
    c, s = math.cos(ang), math.sin(ang)
    n = len(gains)
    for i, g in enumerate(gains):
        t0, t1 = i / n, (i + 1) / n
        ra, rb = r_in + (r_out - r_in) * t0, r_in + (r_out - r_in) * t1
        wa, wb = back + (mouth - back) * t0, back + (mouth - back) * t1
        ob = cyl(group, 'cup', wa / 1000, (ra * c / 1000, y / 1000, ra * s / 1000), (rb * c / 1000, y / 1000, rb * s / 1000),
                 _refl_tint(fn, color, g, tint, rough), seg, r2=wb / 1000, caps=False)
        bm_ = bmesh.new()
        bm_.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm_, faces=bm_.faces[:])
        bm_.to_mesh(ob.data)
        bm_.free()


@product('ldo2660', 'LDO 2660', 'beacon', 'Tepe lambası HOR 110A, turuncu flaş, 24 LED, vidalı — üretici CAD + fotoğraflar')
def build_ldo2660_cad(L):
    cad = os.path.join(CAD_ROOT, 'ldo2660')
    if not os.path.exists(os.path.join(cad, 'p001.stl')):
        print('CAD YOK, eski el modeli:', cad)
        return build_ldo2660(L)
    mY = lambda y: y / 1000
    # ===== 1) CAD: taban, tırnak, levha, conta (dış yüzler), kubbe (iki yüz: iç Fresnel kaburgaları görünsün) =====
    parts = _cad_parts(cad, LDO_M, ['p000', 'p002', 'p003', 'p004'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p000': ([mat('Housing')], L.body, 6000), 'p002': ([mat('Housing')], L.body, 400),
                                 'p003': ([mat('Housing')], L.body, 2500), 'p004': ([mat('Rubber')], L.body, 2500)}, 'ldo')
    # kubbe: yalnız dış kabuk (iki kat turuncu kubbeyi opaklaştırıyordu; iç Fresnel kaburgaları malzemenin dikey kaburga
    # dokusundan)
    raw = _stl(os.path.join(cad, 'p001.stl'), LDO_M)
    _simplify(raw, 0.3)
    # dış kabuk: normali eksenin (yerel y 40'taki nokta) dışına bakan yüzler; içe bakan iç kabuk atılır (ışın testi açık
    # tabandan kaçtığı için iç kabuğu da dış sayıyordu)
    o = Vector((0.0, 0.0, 0.040))  # Blender (x, −z, y): yerel (0, 40 mm, 0)
    dome = _subset(raw, lambda f: f.normal.dot(f.calc_center_median() - o) > 0.0)
    raw.free()
    ob = _mesh_obj('ldo_dome', dome, [mat('Dome.amber')], L.lens, 40, decimate=None if FAST else 9000)
    set_uv_cyl(ob, 0.025)

    # ===== 2) iç: alt bant reflektörü, LED tablası, 12 kap × 2 LED, merkez kolon, üst krom kapak =====
    tint, rough = '#d39040', 0.3
    # alt bant: Fresnel'in ardında turuncu reflektör (yanınca LED ışığıyla aydınlanır)
    lathe(L.E('beacon'), 'band', mp([(51.2, 44.0), (51.2, 66.5)]), _glow('beacon', 'amber', '#c8741e', 0.45), 72, axis='y')
    lathe(L.inner, 'floor', mp([(0.01, 44.5), (51.0, 44.5)]), mat('HousingGloss'), 48, axis='y')
    lathe(L.inner, 'tray', mp([(0.01, 66.5), (50.6, 66.5), (50.6, 68.0), (0.01, 68.0)]), mat('HousingGloss'), 72, axis='y')
    # kap halkası: 12 dışa bakan kap (ağız Ø25, ağızları dalgalı üst kenarı verir), her kapta 2 LED
    YC, R0, R1 = 77.0, 36.5, 49.5
    for i in range(12):
        a = math.radians(15 + 30 * i)
        _radial_cup(L.E('beacon'), a, R0, R1, YC, 12.8, 3.6, (0.95, 0.70, 0.48), 'beacon', 'amber', tint, rough)
        c, s = math.cos(a), math.sin(a)
        for dy in (-2.4, 2.4):
            cyl(L.E('beacon'), 'led', 0.0022, ((R0 - 0.4) * c / 1000, mY(YC + dy), (R0 - 0.4) * s / 1000),
                ((R0 + 0.6) * c / 1000, mY(YC + dy), (R0 + 0.6) * s / 1000), E('beacon', 'amber'), 12)
    lathe(L.inner, 'column', mp([(0.01, 68.0), (36.4, 68.0), (36.4, 86.0), (0.01, 86.0)]), mat('HousingGloss'), 48, axis='y')
    # üst kapak: hafif konik krom (yukarıdan bakınca kubbenin içinde parlak), kenarı kapların üstünü örter
    lathe(L.E('beacon'), 'cap', mp([(0.01, 90.5), (30.0, 89.5), (49.0, 86.8), (49.0, 86.0), (0.01, 86.0)]),
          _refl_tint('beacon', 'amber', 0.30, '#cfd3d8', 0.2), 72, axis='y')
    # kablo: alt levhanın ortasından (sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, 0.001, 0.0), (0.0, -0.010, 0.0), (0.0, -0.022, 0.006)], 0.0030, mat('Cable'), 3, smooth=True)
