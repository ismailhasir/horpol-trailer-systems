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


def _cup_bands(group, x, y, z, r_front, r_back, depth, gains, fn, color):
    """İçi önden görünen krom LED kabı, dipten ağza bantlara bölünmüş: her bant kendi oranında ışır (LED'e yakın dip parlak,
    ağız sönük; yansıyan ışığın düşüşü). Normaller içe: sitede tek yüzlü çizim, dış yüz arkada kalır"""
    n = len(gains)
    for i, g in enumerate(gains):
        z0 = z - depth + depth * i / n
        z1 = z - depth + depth * (i + 1) / n
        r0 = r_back + (r_front - r_back) * i / n
        r1 = r_back + (r_front - r_back) * (i + 1) / n
        ob = cyl(group, 'cup', r0, (x, y, z0), (x, y, z1), _refl(fn, color, g), 28, r2=r1, caps=False)
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
    # AMP 7 pin: CAD rakorun bittiği yerden kısa koruge + fiş (CAD fişi 0,3 m kablonun ucunda; sitede kısa tutulur)
    tube(L.body, 'conduit', [(0.0, -0.004, -0.024), (-0.004, -0.018, -0.042), (-0.026, -0.034, -0.056), (-0.042, -0.040, -0.060)], 0.0055,
         mat('Conduit'), 4, smooth=True)
    amp7(L, -0.052, -0.040, -0.060, 0.045)


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
