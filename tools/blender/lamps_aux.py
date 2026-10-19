# Yardımcı lambalar: lastik kollar (LD 2994 DRAGON, LDCC 2698), çalışma lambası (LRD 2679), tepe lambası (LDO 2660).
# lamps.py tarafından exec ile yüklenir (lamps.py'nin global yardımcıları burada doğrudan kullanılır).
# Ölçüler teknik çizimlerden (.claude/ref/lamps/<KOD>/attachments), biçim ve ışık desenleri fotoğraflardan.
# Tüm ölçüler builder içinde mm yazılır, MM ile metreye çevrilir.

MM = 0.001

# Üç (three.js) uzayında dönüşüm matrisleri: three = R @ yerel
R_SIDE = ((0, 0, -1), (0, 1, 0), (1, 0, 0))   # yerel (u, v, w) → (X = -w, Y = v, Z = u): kol yan profili / beyaz yüz (-X)
R_RED = ((0, 0, 1), (0, 1, 0), (-1, 0, 0))    # yerel (u, v, w) → (X = w, Y = v, Z = -u): kırmızı yüz (+X)
R_HOR = ((1, 0, 0), (0, 0, 1), (0, -1, 0))    # yerel (u, v, w) → (X = u, Y = w, Z = -v): yatay plaka (Y yönünde kalınlık)


def R_Y(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


_PB = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # three → Blender


def _groups(L):
    return [L.body, L.inner, L.lens] + list(L.emit.values())


class Xf:
    """Bağlam içinde üretilen parçaları three uzayında R ve t ile taşır (parçalar yerel çerçevede kurulur)."""

    def __init__(self, L, R=None, t=(0.0, 0.0, 0.0)):
        self.L = L
        self.R = Matrix(R) if R is not None else Matrix.Identity(3)
        self.t = t

    def __enter__(self):
        self.marks = {id(g): len(g.objs) for g in _groups(self.L)}
        return self

    def __exit__(self, *exc):
        M = Matrix.Translation(bl(self.t)) @ (_PB @ self.R @ _PB.transposed()).to_4x4()
        for g in _groups(self.L):
            for ob in g.objs[self.marks.get(id(g), 0):]:
                ob.data.transform(M)
        return False


def mp(pts):
    return [(x * MM, y * MM) for x, y in pts]


def ellipse(a, b, ang=0.0, cx=0.0, cy=0.0, n=28):
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = a * math.cos(t), b * math.sin(t)
        out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return out


def bezier2(p0, c, p1, n=12):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
    return out


def loft(group, name, A, zA, B, zB, mat_, bevel=0.0, seg=2):
    """İki farklı XY çokgeni (aynı nokta sayısı) arasında kesik gövde (zA → zB)"""
    assert len(A) == len(B)
    bm = bmesh.new()
    a = [bm.verts.new(bl((x, y, zA))) for x, y in A]
    b = [bm.verts.new(bl((x, y, zB))) for x, y in B]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(A)
    for i in range(n):
        bm.faces.new([a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat_, group, bevel, seg)


def profile_solid(group, name, outer, holes, w, mat_, bev=0.0, res=2):
    """Delikli düz profil (yerel XY), yerel Z'de ±w/2 kalınlık; kenarları yuvarlatılmış (2B eğri doldurma)"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = max(w / 2 - bev, 1e-5)
    cu.bevel_depth = bev
    cu.bevel_resolution = res
    for poly in [outer] + list(holes):
        sp = cu.splines.new('POLY')
        sp.points.add(len(poly) - 1)
        for p, (u, v) in zip(sp.points, poly):
            p.co = (u, v, 0.0, 1.0)
        sp.use_cyclic_u = True
    tmp = bpy.data.objects.new(name + '_c', cu)
    scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    me.transform(_PB.to_4x4())
    me.materials.clear()
    me.materials.append(mat_)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    group.objs.append(ob)
    return ob


def ribbed_lathe(group, name, prof, mat_, n=160, ribs=80, amp=0.0006):
    """Dik eksenli döndürme, çevrede dikey kaburgalar (Fresnel kubbe). prof [(r, y)] metre, son nokta eksende olabilir."""
    bm = bmesh.new()
    rings = []
    r0 = prof[0][0]
    for r, h in prof:
        if r < 1e-6:
            rings.append(bm.verts.new(bl((0.0, h, 0.0))))
            continue
        k = max(0.0, min(1.0, (r - 0.4 * r0) / (0.6 * r0)))
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r + amp * k * math.cos(ribs * a)
            ring.append(bm.verts.new(bl((rr * math.cos(a), h, rr * math.sin(a)))))
        rings.append(ring)
    for j in range(len(rings) - 1):
        A, B = rings[j], rings[j + 1]
        for i in range(n):
            i2 = (i + 1) % n
            if isinstance(B, list):
                bm.faces.new([A[i], A[i2], B[i2], B[i]])
            else:
                bm.faces.new([A[i], A[i2], B])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # dışa bakmalı: alt halkanın bir yüzü
    ob = _obj(name, bm, mat_, group, 0.0, angle=60)
    me = ob.data
    f = me.polygons[0]
    c = f.center
    if f.normal.x * c.x + f.normal.y * c.y < 0:
        me.flip_normals()
    return ob


def uv_box(ob, s):
    """Baskın normal eksenine göre düzlemsel UV (doku normal haritaları için)"""
    if ob.type != 'MESH':
        return
    me = ob.data
    if me.uv_layers:
        return
    uvl = me.uv_layers.new(name='UVMap').data
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = co.y, co.z
            elif ax == 1:
                u, v = co.x, co.z
            else:
                u, v = co.x, co.y
            uvl[li].uv = (u / s, v / s)


def uv_all(L):
    """Yalnız lens düğümüne UV (yastık optik deseni); gövdede UV yok (GLB boyutu: köşe başına 8 bayt tasarruf)"""
    for ob in L.lens.objs:
        uv_box(ob, 0.014)


def clip(poly, a, b, c):
    """Sutherland–Hodgman: a·x + b·y <= c yarı düzlemiyle kırp"""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp <= 0) != (fq <= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def flat(group, name, pts, z, mat_, up=True):
    """Tek yüzlü düz çokgen (+Z'ye bakar): ince desen, yuva, LED diski (az köşe)"""
    bm = bmesh.new()
    vs = [bm.verts.new(bl((x, y, z))) for x, y in pts]
    f = bm.faces.new(vs)
    f.normal_update()
    if (f.normal.dot(bl((0, 0, 1))) < 0) == up:
        f.normal_flip()
    return _obj(name, bm, mat_, group, 0.0)


def pan_screw(L, x, y, z, r=0.0045, h=0.0022):
    """Yıldız başlı galvaniz vida (+Z yönünde): kubbeli baş (döndürme profili) + yıldız oyuk"""
    prof = [(r, 0.0), (r, h * 0.35), (r * 0.82, h * 0.85), (r * 0.45, h), (0.0, h)]
    bm = bmesh.new()
    vs = [bm.verts.new(bl((x + rr, y, z + hh))) for rr, hh in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=bl((x, y, z)), axis=bl((0, 0, 1)), angle=math.pi * 2, steps=16, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _obj('screw', bm, mat('Zinc'), L.body, 0.0, angle=50)
    c = r * 0.5
    box(L.body, 'screw_x', x - c, x + c, y - 0.00042, y + 0.00042, z + h - 0.0006, z + h + 0.00005, mat('Gasket'))
    box(L.body, 'screw_x', x - 0.00042, x + 0.00042, y - c, y + c, z + h - 0.0006, z + h + 0.00005, mat('Gasket'))


def cable(L, pts, r, mat_name='Cable'):
    ob = tube(L.body, 'cable', pts, r, mat(mat_name), 2, smooth=True)
    ob.data.resolution_u = 5
    return ob


def back_cable(L, y=0.0, r=0.0024):
    """Taban plakasının arkasından çıkan çift damarlı kablo (duvarın içine, -Z)"""
    cyl(L.body, 'grommet', r * 1.9, (0, y, 0.0005), (0, y, -0.004), mat('Rubber'), 16)
    cable(L, [(0, y, -0.002), (0, y - 0.004, -0.022), (0, y - 0.014, -0.042)], r)


def mini_led(L, gE, x, y, z, r, matE, cup_r, depth, seg=10):
    """Hafif LED: yayan disk + krom kap (az üçgen)"""
    cyl(L.inner, 'led_cup', r * 1.2, (x, y, z - depth), (x, y, z), mat('Chrome'), seg + 4, r2=cup_r, caps=False)
    flat(gE, 'led', circle(r, seg, x, y), z - depth + 0.0003, matE)


# ---------------------------------------------------------------------
# LD 2994 — DRAGON lastik kol (HOR 134, versiyon 1). Uzanım 200, yükseklik 179, kafa genişliği 50 (lens çıkıntılarıyla).
# Taban plakası 35 × 105, 2 × Ø5 (78 mm ara). Tırtıklı (yatay kanatlı) eğik kol, sekizgen pahlı kafa.
# Kafa: -X beyaz, +X kırmızı ">—<" çift şevron neon; +Z ucunda iki turuncu çubuk. Hepsi 'outline' işlevi.
# Yerel: plaka arka yüz merkezi orijin; Y yukarı; kol +Z.
# ---------------------------------------------------------------------
@product('ld2994', 'LD 2994', 'arm', 'DRAGON lastik kol, kontur lambası (beyaz/kırmızı/turuncu)')
def build_ld2994(L):
    Y0 = 52.5                       # plaka merkezinin yüksekliği (H: plaka altından mm)
    Zc, Hc = 163.5, 154.5           # kafa merkezi (Z: duvardan mm)
    rub, hous, gloss = mat('Rubber'), mat('Housing'), mat('HousingGloss')

    def S(z, h):
        return (z * MM, (h - Y0) * MM)

    # --- taban plakası (XY, +Z): pahlı uçlar, yükseltilmiş iç yastık, 2 vida
    pl = chamfer_rect(35, 105, 11)
    prism(L.body, 'plate', mp(pl), 0.0, 0.0062, rub, 0.0014, 2)
    prism(L.body, 'plate_pad', mp(offset(pl, 2.6)), 0.0058, 0.0088, rub, 0.0009, 2)
    for yy in (-39.0, 39.0):
        cyl(L.body, 'hole', 0.0042, (0, yy * MM, 0.0084), (0, yy * MM, 0.0090), mat('Gasket'), 14)
        pan_screw(L, 0.0, yy * MM, 0.0088, 0.0043, 0.0021)
    back_cable(L)

    # --- kol: çekirdek + üst sırt + kola dik kanatlar (yan profil düzleminde kurulur, X kalınlık)
    # kol ekseni d (48°), dik n; O alt kenarın başı; üst kenar O'dan T uzakta
    d = (79 / 118.26, 88 / 118.26)
    n = (-d[1], d[0])
    O = (37.0, 22.0)
    T = n[1] * 63.0
    nO = n[0] * O[0] + n[1] * O[1]

    def st(s, t):
        return (O[0] + s * d[0] + t * n[0], O[1] + s * d[1] + t * n[1])

    with Xf(L, R_SIDE):
        core = [(8.5, 22), (37, 22), (131, 127), (131, 173), (116, 173), (37, 85), (8.5, 85)]
        prism(L.body, 'arm_core', [S(*p) for p in core], -0.0100, 0.0100, mat('Seal'), 0.0018, 2)
        spine = [(8.5, 78.5), (39.9, 78.5), (120, 167.8), (120, 177.4), (37, 85), (8.5, 85)]
        prism(L.body, 'arm_spine', [S(*p) for p in spine], -0.0135, 0.0135, rub, 0.0018, 2)
        s0 = -14.0
        while s0 < 138:
            q = [st(s0, -3.2), st(s0 + 5.4, -3.2), st(s0 + 5.4, 75), st(s0, 75)]
            q = clip(q, 0, -1, -21.5)                      # H >= 21.5
            q = clip(q, -1, 0, -9.0)                       # Z >= 9
            if s0 >= 44:
                q = clip(q, n[0], n[1], T - 5.5 + nO)      # sırtın altında
            else:
                q = clip(q, 0, 1, 79.0)                    # kök: rafın altında
            if len(q) >= 3:
                prism(L.body, 'fin', [S(*p) for p in q], -0.0155, 0.0155, rub, 0.0008, 1)
            s0 += 8.6
        # kafa boynu (yaka)
        prism(L.body, 'collar', [S(*p) for p in [(115, 124), (131, 124), (131, 177), (115, 177)]], -0.019, 0.019, hous, 0.0025, 2)
        # kafa: sekizgen profil, X ±22, kenarlar pahlı
        head = [(128, 142), (139, 130), (188, 130), (199, 142), (199, 167), (188, 179), (139, 179), (128, 167)]
        hd = prism(L.body, 'head', [S(*p) for p in head], -0.022, 0.022, hous, 0.0052, 1)
        md = hd.modifiers.new('round', 'BEVEL')
        md.width = 0.0006
        md.segments = 2
        md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(20)

    # kafa çevresinde orta derz (yatay sırt)
    with Xf(L, R_HOR):
        o = chamfer_rect(44.9, 71.9, 5.6, 0, -Zc)
        i = chamfer_rect(43.0, 70.0, 4.6, 0, -Zc)
        frame(L.body, 'seam', mp(o), mp(i), (Hc - 1.3 - Y0) * MM, (Hc + 1.3 - Y0) * MM, gloss, 0.0004, 1)

    # --- lens yüzleri: -X beyaz, +X kırmızı; çift şevron neon
    up = [(Zc - 25.5, Hc + 12.0), (Zc - 18.0, Hc + 5.0), (Zc + 18.0, Hc + 5.0), (Zc + 25.5, Hc + 12.0)]
    dn = [(z, 2 * Hc - h) for z, h in up]
    for s, R, col, lens in ((1, R_SIDE, 'white', 'Lens.clear'), (-1, R_RED, 'red', 'Lens.red')):
        def F(z, h, s=s):
            return (s * z * MM, (h - Y0) * MM)

        with Xf(L, R):
            # orta kuşak (parlak koyu şerit) ve dikey ek yeri
            band = [(131, Hc - 2.4), (196, Hc - 2.4), (196, Hc + 2.4), (131, Hc + 2.4)]
            prism(L.body, 'face_band', [F(*p) for p in band], 0.0216, 0.0225, gloss, 0.0004, 1)
            seam = [(Zc - 0.35, 135), (Zc + 0.35, 135), (Zc + 0.35, 174), (Zc - 0.35, 174)]
            prism(L.body, 'face_seam', [F(*p) for p in seam], 0.0217, 0.0222, mat('Seal'))
            for k, pts in enumerate((up, dn)):
                P = [F(*p) for p in pts]
                ribbon(L.body, 'neon_chan', P, 0.0070, 0.0219, gloss, 0.0009)
                ribbon(L.E('outline'), 'neon', P, 0.0040, 0.0226, E('outline', col), 0.0011)
                ribbon(L.lens, 'neon_lens', P, 0.0052, 0.0232, mat(lens), 0.0009)

    # --- +Z ucu: iki turuncu çubuk
    for dh in (-4.3, 4.3):
        yc = Hc + dh - Y0
        prism(L.body, 'amb_frame', mp(stadium(24, 7.2, 4, 0, yc)), 0.1984, 0.1996, gloss)
        prism(L.E('outline'), 'amb', mp(stadium(19, 3.4, 4, 0, yc)), 0.1990, 0.2003, E('outline', 'amber'))
        prism(L.lens, 'amb_lens', mp(stadium(20.5, 4.8, 4, 0, yc)), 0.1993, 0.2008, mat('Lens.amber'), 0.0006, 1)
    uv_all(L)


# ---------------------------------------------------------------------
# LDCC 2698 — lastik kol versiyon 1 (HOR 101, uzun). Uzanım ~169, yükseklik ~178, genişlik ~37.
# Kolda 3 oval boşluk; yuvarlatılmış oval kafa: -X beyaz (şeffaf lens, LED noktalı neon halka), +X kırmızı, +Z turuncu.
# ---------------------------------------------------------------------
@product('ldcc2698', 'LDCC 2698', 'arm', 'Lastik kol, uzun (versiyon 1), neon halkalı')
def build_ldcc2698(L):
    Y0 = 53.0
    Zc, Hc = 128.5, 150.0
    rub = mat('Rubber')

    def S(z, h):
        return (z * MM, (h - Y0) * MM)

    # --- taban plakası 37 × 106
    pl = chamfer_rect(37, 106, 9.5)
    prism(L.body, 'plate', mp(pl), 0.0, 0.0078, rub, 0.0016, 2)
    box(L.body, 'plate_rib', -0.0062, 0.0062, -0.031, 0.031, 0.0074, 0.0094, rub, 0.0009)
    for yy in (-39.5, 39.5):
        cyl(L.body, 'hole', 0.0042, (0, yy * MM, 0.0074), (0, yy * MM, 0.0080), mat('Gasket'), 14)
        pan_screw(L, 0.0, yy * MM, 0.0078, 0.0043, 0.0021)
    back_cable(L)

    # --- kol: iki raylı kafes (düz üst ray, kavisli alt ray), aralarında 3 oval boşluk (fotoğraftan, H × 1,1 ölçekli)
    lower = [(8.5, 9.0), (11.0, 12.5), (16.0, 19.5), (26.8, 37.4), (37.0, 53.5), (48.0, 68.0), (58.5, 80.5), (69.4, 91.3),
             (80.0, 101.0), (90.6, 110.0), (101.0, 118.4), (106.0, 124.0)]
    outer = lower + [(106.0, 152.0), (97.0, 148.0), (8.5, 74.6)]

    def hu(z):
        return 75.0 + (z - 10.9) * (147.0 - 75.0) / (97.0 - 10.9)

    def hl(z):
        for (z0, h0), (z1, h1) in zip(lower, lower[1:]):
            if z0 <= z <= z1:
                return h0 + (h1 - h0) * (z - z0) / (z1 - z0)
        return lower[-1][1]

    holes = []
    for zc, a, b, k in ((30.0, 21.5, 12.5, 0.50), (59.5, 17.0, 8.8, 0.50), (84.0, 12.5, 7.8, 0.50)):
        hc = hl(zc) + k * (hu(zc) - hl(zc))
        holes.append(ellipse(a, b, 40.0, zc, hc, 24))
    with Xf(L, R_SIDE):
        profile_solid(L.body, 'arm', [S(*p) for p in outer], [[S(*p) for p in hh] for hh in holes], 0.020, rub, 0.0020, 1)
        # üst kenar boyunca küçük yuvalar (iki yan)
        for zc in (24.0, 44.0, 64.0, 84.0):
            hc = hu(zc) - 5.5
            sl = [S(*p) for p in chamfer_rect(1.8, 6.0, 0.5, zc, hc)]
            for w0 in (0.0108, -0.0111):
                flat(L.body, 'slot', sl, w0 + 0.0003 if w0 > 0 else w0, mat('Gasket'), w0 > 0)
        # kafa gövdesi (yuvarlatılmış oval). Katı kısım iç reflektörün ARKASINDA biter (±11,5); lense kadar yalnız çerçeve uzanır.
        head = rrect(73, 54, 14, 5, Zc, Hc)
        prism(L.body, 'head', [S(*p) for p in head], -0.0115, 0.0115, rub, 0.0025, 2)

    # --- lens yüzleri
    ring_o = rrect(46, 30, 8.5, 4, Zc, Hc)
    ring_i = rrect(41, 25, 6.0, 4, Zc, Hc)
    badge = [(-13, -8), (-6, -5.6), (6, -5.6), (13, -8), (13, 8), (6, 5.6), (-6, 5.6), (-13, 8)]
    badge = [(Zc + x, Hc + y) for x, y in badge]
    dia_o = [(Zc - 7.5, Hc), (Zc, Hc - 3.8), (Zc + 7.5, Hc), (Zc, Hc + 3.8)]
    dia_i = offset(dia_o, 0.9)
    for s, R, col, lens in ((1, R_SIDE, 'white', 'Lens.clear'), (-1, R_RED, 'red', 'Lens.red')):
        def F(z, h, s=s):
            return (s * z * MM, (h - Y0) * MM)

        def FP(pts):
            return [F(*p) for p in pts]

        with Xf(L, R):
            # yumuşak lastik çerçeve
            frame(L.body, 'bezel', FP(offset(head, -0.2)), FP(offset(head, 5.6)), 0.0108, 0.0186, rub, 0.0016, 1)
            # iç: reflektör zemin, neon halka, tüy kanatlar, LED noktaları, rozet
            prism(L.inner, 'refl', FP(offset(head, 5.4)), 0.0113, 0.0120, mat('ReflectorRed' if col == 'red' else 'Reflector'))
            frame(L.E('outline'), 'ring', FP(ring_o), FP(ring_i), 0.0120, 0.0133, E('outline', col))
            for zz in [Zc - 18 + 4 * i for i in range(10)]:
                for sgn in (1, -1):
                    h0, h1 = Hc + sgn * 15.2, Hc + sgn * 19.8
                    q = [(zz - 0.4, h0), (zz + 0.4, h0), (zz + 0.4 - 1.2, h1), (zz - 0.4 - 1.2, h1)]
                    flat(L.E('outline'), 'feather', FP(q), 0.0126, E('outline', col))
            for zz in (Zc - 24.2, Zc + 24.2):
                for hh in (-7.5, -2.5, 2.5, 7.5):
                    u, v = F(zz, Hc + hh)
                    mini_led(L, L.E('outline'), u, v, 0.0133, 0.0009, E('outline', col), 0.0021, 0.0012, 8)
            frame(L.inner, 'badge_frame', FP(offset(badge, -1.6)), FP(badge), 0.0120, 0.0136, mat('HousingGloss'), 0.0003, 1)
            prism(L.inner, 'badge', FP(badge), 0.0120, 0.0138, mat('Zinc'), 0.0004, 1)
            frame(L.inner, 'logo', FP(dia_o), FP(dia_i), 0.0138, 0.0141, mat('HousingGloss'))
            prism(L.lens, 'lens', FP(offset(head, 5.0)), 0.0142, 0.0176, mat(lens), 0.0012, 2)

    # --- +Z ucu: turuncu yan lens
    yc = Hc - Y0
    frame(L.body, 'amb_bezel', mp(rrect(18, 35, 6, 4, 0, yc)), mp(rrect(13, 30, 4, 4, 0, yc)), 0.1630, 0.1668, rub, 0.0010, 1)
    prism(L.inner, 'amb_refl', mp(rrect(13.5, 30.5, 4, 4, 0, yc)), 0.1635, 0.1645, mat('Reflector'))
    for hh in (-8, 0, 8):
        cyl(L.E('outline'), 'amb_led', 0.0012, (0, (yc + hh) * MM, 0.1645), (0, (yc + hh) * MM, 0.1652), E('outline', 'amber'), 12)
    prism(L.E('outline'), 'amb_guide', mp(rrect(9, 26, 3, 4, 0, yc)), 0.1646, 0.1656, E('outline', 'amber'))
    prism(L.lens, 'amb_lens', mp(rrect(13.4, 30.4, 4, 4, 0, yc)), 0.1640, 0.1688, mat('Lens.amber'), 0.0016, 2)
    uv_all(L)


# ---------------------------------------------------------------------
# LRD 2679 — çalışma lambası HOR 111 (12 W). Gövde 101 × 100, derinlik 50,5; toplam yükseklik 127 (civata tabanından).
# Ön: şeffaf yastık optikli lens, ortada 3 büyük LED (krom reflektör, alüminyum şerit), çevrede 12 küçük LED.
# Arka: soğutma kanatları. Altta paslanmaz U braket, M8 × 30 civata (-Y).
# Yerel: orijin civatanın tabanı (lastik pul altı), lens +Z.
# ---------------------------------------------------------------------
@product('lrd2679', 'LRD 2679', 'work', 'Çalışma lambası HOR 111, 12 W, 12/24 V')
def build_lrd2679(L):
    Hc = 77.0
    hous, ss = mat('Housing'), mat('Stainless')
    O = rrect(101, 100, 14, 6, 0, Hc)
    W = rrect(80, 80, 13, 6, 0, Hc)
    # --- ön gövde: katı kısım reflektörün arkasında biter (z 21,5), lense kadar yalnız duvar (frame)
    prism(L.body, 'front', mp(O), 0.0128, 0.0216, hous, 0.0020, 2)
    frame(L.body, 'wall', mp(O), mp(offset(W, -1.5)), 0.0210, 0.0312, hous, 0.0)
    frame(L.body, 'rim', mp(offset(O, 0.4)), mp(W), 0.0308, 0.0340, hous, 0.0010, 1)
    # köşe yastıkları (çerçevede yükseltilmiş köşeler)
    oc, orad = (50.5 - 14, 50 - 14), 14
    ic, irad = (40 - 13, 40 - 13), 13
    pad = [(50.5, 30.0)]
    pad += [(oc[0] + orad * math.cos(math.radians(a)), oc[1] + orad * math.sin(math.radians(a))) for a in range(0, 91, 15)]
    pad += [(30.0, 50.0), (30.0, 40.0)]
    inner_arc = [(ic[0] + irad * math.cos(math.radians(a)), ic[1] + irad * math.sin(math.radians(a))) for a in range(90, -1, -15)]
    pad += [p for p in inner_arc if p[0] > 30.3 and p[1] > 30.3]
    pad += [(40.0, 30.0)]
    for sx in (1, -1):
        for sy in (1, -1):
            q = [(sx * x * 0.995, Hc + sy * y * 0.995) for x, y in pad]
            prism(L.body, 'corner_pad', mp(q), 0.0336, 0.0355, hous, 0.0007, 1)
    # çerçeve yuvaları (üst/alt/yanlar, 3'er)
    for d in (-9.0, 0.0, 9.0):
        for sy in (1, -1):
            prism(L.body, 'slot', mp(chamfer_rect(2.6, 8.0, 0.8, d, Hc + sy * 45.5)), 0.0339, 0.0342, mat('Seal'))
        for sx in (1, -1):
            prism(L.body, 'slot', mp(chamfer_rect(8.0, 2.6, 0.8, sx * 46.0, Hc + d)), 0.0339, 0.0342, mat('Seal'))
    # --- iç: reflektör zemin, 12 küçük LED halkası
    prism(L.inner, 'refl', mp(offset(W, 0.5)), 0.0220, 0.0232, mat('Reflector'))
    ring = [(x, 29.5) for x in (-27, -9, 9, 27)] + [(x, -29.5) for x in (-27, -9, 9, 27)] + \
           [(sx * 31.0, sy * 13.5) for sx in (1, -1) for sy in (1, -1)]
    for x, y in ring:
        mini_led(L, L.E('work'), x * MM, (Hc + y) * MM, 0.0262, 0.0015, E('work', 'white'), 0.0048, 0.0030, 8)
    # orta alüminyum şerit, 3 büyük LED
    bar = stadium(54, 18.5, 8, 0, Hc + 3)
    frame(L.inner, 'bar_wall', mp(bar), mp(offset(bar, 1.2)), 0.0232, 0.0272, ss, 0.0)
    with Xf(L, None, (0.0, 0.0, 0.0274)):
        profile_solid(L.inner, 'bar_top', mp(bar), [mp(circle(7.4, 28, x, Hc + 3)) for x in (-17.0, 0.0, 17.0)], 0.0013, ss, 0.0, 1)
    top = [(-17, Hc + 11), (17, Hc + 11), (17, Hc + 17), (13, Hc + 20.5), (-13, Hc + 20.5), (-17, Hc + 17)]
    prism(L.inner, 'logo_plate', mp(top), 0.0232, 0.0272, ss, 0.0006, 2)
    dia = [(-6.5, Hc + 16), (0, Hc + 13.4), (6.5, Hc + 16), (0, Hc + 18.6)]
    frame(L.inner, 'logo', mp(dia), mp(offset(dia, 0.8)), 0.0272, 0.0275, mat('HousingGloss'))
    prism(L.inner, 'text_plate', mp(rrect(38, 10, 2, 3, 0, Hc - 11)), 0.0232, 0.0270, ss, 0.0006, 2)
    for w_, yy in ((8.0, -9.0), (12.0, -12.6)):
        box(L.inner, 'text', -w_ / 2 * MM, w_ / 2 * MM, (Hc + yy - 0.5) * MM, (Hc + yy + 0.5) * MM, 0.0270, 0.0273, mat('HousingGloss'))
    for x in (-17.0, 0.0, 17.0):
        p = (x * MM, (Hc + 3) * MM)
        cyl(L.inner, 'cup_big', 0.0026, (p[0], p[1], 0.0233), (p[0], p[1], 0.0276), mat('Chrome'), 32, r2=0.0076, caps=False)
        cyl(L.inner, 'chip_base', 0.0026, (p[0], p[1], 0.0231), (p[0], p[1], 0.0235), mat('Pcb'), 12)
        box(L.E('work'), 'chip', p[0] - 0.0015, p[0] + 0.0015, p[1] - 0.0015, p[1] + 0.0015, 0.0234, 0.0240, E('work', 'white'))
    # şeffaf yastık optikli lens
    prism(L.lens, 'lens', mp(offset(W, -0.8)), 0.0310, 0.0334, mat('Lens.clear'), 0.0008, 2)

    # --- arka gövde (kesik) ve soğutma kanatları
    loft(L.body, 'back', mp(rrect(66, 76, 10, 6, 0, Hc)), 0.0130, mp(rrect(52, 60, 8, 6, 0, Hc)), -0.0150, hous, 0.0015)
    with Xf(L, R_HOR):
        fin = [(-29, 14.0), (29, 14.0), (47, -12.8), (-47, -12.8)]
        for dy in (-30, -20, -10, 0, 10, 20, 30):
            prism(L.body, 'fin', mp(fin), (Hc + dy - 1.4) * MM, (Hc + dy + 1.4) * MM, hous, 0.0006, 1)
    # kablo rakoru ve kablo
    cyl(L.body, 'gland', 0.0062, (0, 0.062, -0.0148), (0, 0.062, -0.0215), hous, 16)
    cyl(L.body, 'gland_nut', 0.0072, (0, 0.062, -0.0160), (0, 0.062, -0.0185), hous, 6)
    cable(L, [(0, 0.062, -0.020), (0, 0.058, -0.040), (0, 0.040, -0.058)], 0.0030)

    # --- montaj: gövde altı kulak, U braket, mafsal cıvatası, lastik pul, M8 civata
    box(L.body, 'lug', -0.0140, 0.0140, 0.0170, 0.0300, -0.0085, 0.0085, hous, 0.0015)
    cyl(L.body, 'lug_r', 0.0085, (-0.0140, 0.0216, 0), (0.0140, 0.0216, 0), hous, 20)
    cheek = [(-10.0, 4.0), (10.0, 4.0), (10.0, 21.6)]
    cheek += [(10.0 * math.cos(math.radians(a)), 21.6 + 10.0 * math.sin(math.radians(a))) for a in range(30, 180, 30)]
    cheek += [(-10.0, 21.6)]
    with Xf(L, R_SIDE):
        for w0, w1 in ((0.0145, 0.0170), (-0.0170, -0.0145)):
            prism(L.body, 'cheek', mp(cheek), w0, w1, ss, 0.0005, 1)
    box(L.body, 'bracket_base', -0.0170, 0.0170, 0.0038, 0.0063, -0.0110, 0.0110, ss, 0.0005)
    lathe(L.body, 'grommet', mp([(0, 10.5), (5.5, 10.2), (9.5, 8.2), (10.8, 6.3), (0.01, 6.3)]), mat('Seal'), 28, axis='y')
    for sx in (1, -1):
        cyl(L.body, 'washer', 0.0082, (sx * 0.0170, 0.0216, 0), (sx * 0.0183, 0.0216, 0), mat('Zinc'), 28)
        cyl(L.body, 'bolt_head' if sx > 0 else 'nut', 0.0066, (sx * 0.0183, 0.0216, 0), (sx * 0.0236, 0.0216, 0), mat('Zinc'), 6)
    cyl(L.body, 'bolt_tip', 0.0040, (-0.0236, 0.0216, 0), (-0.0262, 0.0216, 0), mat('Zinc'), 16)
    cyl(L.body, 'pad', 0.0155, (0, 0.0, 0), (0, 0.0038, 0), mat('Seal'), 24)
    cyl(L.body, 'stud', 0.0039, (0, 0.0, 0), (0, -0.0235, 0), mat('Zinc'), 16)
    for i in range(8):
        y = -0.0010 - i * 0.0027
        cyl(L.body, 'thread', 0.0043, (0, y, 0), (0, y - 0.0009, 0), mat('Zinc'), 12, caps=False)
    cyl(L.body, 'washer_b', 0.0085, (0, -0.0120, 0), (0, -0.0132, 0), mat('Zinc'), 28)
    cyl(L.body, 'nut_b', 0.0072, (0, -0.0132, 0), (0, -0.0196, 0), mat('Zinc'), 6, bevel=0.0005)
    uv_all(L)


# ---------------------------------------------------------------------
# LDO 2660 — turuncu tepe lambası HOR 110A, versiyon 1 (3 × Ø7 vida, Ø130 üzerinde 120°).
# Taban flanşı Ø150,5; kubbe Ø114; yükseklik 122,5. Dikey Fresnel kaburgalı turuncu kubbe, içte 16 LED'li reflektör halkası.
# Yerel: taban merkezi orijin, taban y = 0 düzleminde, kubbe +Y.
# ---------------------------------------------------------------------
@product('ldo2660', 'LDO 2660', 'beacon', 'Turuncu tepe lambası HOR 110A, 3 vidalı taban')
def build_ldo2660(L):
    hous = mat('Housing')
    base = [(0.01, 0.0), (73.4, 0.0), (75.25, 1.4), (75.25, 4.6), (74.3, 6.6), (71.0, 8.9), (66.0, 12.0), (62.4, 16.8),
            (60.4, 23.0), (59.7, 30.0), (59.5, 40.6), (58.8, 42.9), (56.4, 43.2), (55.6, 40.0)]
    lathe(L.body, 'base', mp(base), hous, 64, axis='y')
    # 3 dikey kaburga + vida yuvası (biri +Z'de)
    for ang in (0.0, 120.0, 240.0):
        with Xf(L, R_Y(ang)):
            prism(L.body, 'rib', [(-0.0031, 0.0140), (0.0031, 0.0140), (0.0031, 0.0425), (-0.0031, 0.0425)], 0.0560, 0.0620, hous, 0.0009, 1)
            cyl(L.body, 'boss', 0.0050, (0, 0.0080, 0.0655), (0, 0.0128, 0.0655), hous, 16)
            cyl(L.body, 'hole', 0.0037, (0, 0.0126, 0.0655), (0, 0.0131, 0.0655), mat('Gasket'), 12)
            pan_screw(L, 0.0, 0.0, 0.0, 0.0031, 0.0016)
            # pan_screw +Z yönünde kurar; dikeye çevir
            for ob in L.body.objs[-3:]:
                ob.data.transform((Matrix.Translation(bl((0, 0.0112, 0.0655))) @ (_PB @ Matrix(R_HOR) @ _PB.transposed()).to_4x4()))
    # kablo girişi çıkıntısı (arka, -Z)
    with Xf(L, R_Y(180.0)):
        box(L.body, 'cable_boss', -0.0060, 0.0060, 0.0, 0.0090, 0.0600, 0.0690, hous, 0.0025)
    # alt kablo
    cable(L, [(0, 0.004, 0), (0, -0.010, 0.002), (0, -0.026, 0.010)], 0.0028)

    # --- iç: taban, reflektörlü bant, LED halkası, üst reflektör
    lathe(L.inner, 'floor', mp([(0.01, 42.6), (56.0, 42.6)]), hous, 48, axis='y')
    uv_box(lathe(L.inner, 'band', mp([(51.5, 42.8), (51.5, 66.0), (49.0, 68.0)]), mat('Retro.amber'), 64, axis='y'), 0.012)
    lathe(L.inner, 'column', mp([(0.01, 66.0), (34.5, 66.0), (34.5, 90.0), (0.01, 90.0)]), mat('Reflector'), 48, axis='y')
    uv_box(lathe(L.inner, 'top_refl', mp([(30.0, 90.0), (44.0, 91.5), (47.0, 93.0), (0.01, 95.0)]), mat('Retro.amber'), 64, axis='y'), 0.012)
    lathe(L.inner, 'skirt_refl', mp([(47.0, 66.5), (36.0, 69.0)]), mat('Chrome'), 64, axis='y')
    for i in range(16):
        with Xf(L, R_Y(i * 22.5 + 11.25)):
            cyl(L.inner, 'cup', 0.0022, (0, 0.0785, 0.0346), (0, 0.0785, 0.0418), mat('Chrome'), 14, r2=0.0074, caps=False)
            cyl(L.E('beacon'), 'led', 0.0032, (0, 0.0785, 0.0343), (0, 0.0785, 0.0355), E('beacon', 'amber'), 10)
    # --- kubbe (Fresnel kaburgalı, turuncu)
    dome = [(57.0, 41.5), (57.0, 68.0), (56.7, 71.0), (56.2, 92.0), (55.0, 99.0), (52.6, 105.5), (48.6, 111.0), (42.6, 115.8),
            (35.0, 119.3), (26.0, 121.4), (15.0, 122.3), (0.0, 122.5)]
    d = ribbed_lathe(L.lens, 'dome', [(r * MM, h * MM) for r, h in dome], mat('Dome.amber'), 144, 72, 0.00055)
    set_uv_cyl(d, 0.025)
    # üstte havalandırma / etiket noktası
    cyl(L.body, 'vent', 0.0040, (0, 0.1222, 0), (0, 0.1228, 0), mat('Seal'), 24)
    uv_all(L)
