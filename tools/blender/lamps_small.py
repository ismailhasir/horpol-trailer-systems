# Küçük lambalar: tutuculu yan/ön marker (LD 2774, LD 2773, LD 2765), düz marker (LD 0128, LD 0127),
# plaka lambaları (LTD 2834, LTD 229). lamps.py tarafından exec ile yüklenir (yardımcılar onun globals'ında).
# Ölçüler üretici teknik çizimlerinden (.claude/ref/lamps/<KOD>/attachments), biçim ve ışık desenleri fotoğraflardan.
#
# Yerel koordinatlar (three, metre):
#   Tutuculu marker: tutucu arka dikey plakasının arka yüzü z = 0, lens +Z, X genişlik, Y yukarı; orijin plakanın (sınır kutusu) merkezi.
#     Üst yatay flanş plakadan geriye (-Z) uzanır (montaj flanşı), altında üçgen kaburgalar.
#   Düz marker: taban z = 0, lens +Z, orijin taban merkezi.
#   Plaka lambası: taban düzlemi y = 0 (civatalar -Y), gövde y > 0, difüzör +Z; orijin taban merkezi.

# ---------------------------------------------------------------------
# Yardımcılar (bu modüle özel)
# ---------------------------------------------------------------------


def _s_dedupe(pts, eps=2e-5):
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > eps:
            out.append(p)
    if len(out) > 2 and math.dist(out[0], out[-1]) <= eps:
        out.pop()
    return out


def _s_area(pts):
    n = len(pts)
    return sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2


def _s_ccw(pts):
    pts = _s_dedupe(pts)
    return pts if _s_area(pts) > 0 else list(reversed(pts))


def _s_ring(pts, N):
    """Kapalı çokgeni yay uzunluğuna göre N noktaya yeniden örnekler; alt-orta noktadan başlar, saat yönü tersine.
    Aynı N ile örneklenen iki benzer biçim frame() ile halka yapılabilir."""
    pts = _s_ccw(pts)
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    # başlangıç: merkezin tam altındaki kenar kesişimi
    best = None
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        if (a[0] - cx) * (b[0] - cx) <= 0 and a[0] != b[0]:
            t = (cx - a[0]) / (b[0] - a[0])
            y = a[1] + (b[1] - a[1]) * t
            if y < cy and (best is None or y < best[1]):
                best = (i, y, t)
    i0, _, t0 = best
    a, b = pts[i0], pts[(i0 + 1) % n]
    start = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
    seq = [start] + [pts[(i0 + 1 + k) % n] for k in range(n)] + [start]
    seq = _s_dedupe(seq[:-1]) + [start]
    cum = [0.0]
    for k in range(1, len(seq)):
        cum.append(cum[-1] + math.dist(seq[k - 1], seq[k]))
    total = cum[-1]
    out = []
    j = 0
    for k in range(N):
        s = total * k / N
        while cum[j + 1] < s:
            j += 1
        seg = cum[j + 1] - cum[j] or 1e-12
        t = (s - cum[j]) / seg
        out.append((seq[j][0] + (seq[j + 1][0] - seq[j][0]) * t, seq[j][1] + (seq[j + 1][1] - seq[j][1]) * t))
    return out


def _s_arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _s_loft(group, name, rings, mat_, cap0=True, cap1=True, bevel=0.0, angle=35):
    """Aynı nokta sayılı 3B halkalar arası yüzey (three koordinatı), uçlar ngon kapak"""
    bm = bmesh.new()
    V = [[bm.verts.new(bl(p)) for p in r] for r in rings]
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]])
    if cap0:
        bm.faces.new(V[0])
    if cap1:
        bm.faces.new(V[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat_, group, bevel, 3, angle)


def _s_dome(group, name, pts, z0, z1, rad, mat_, steps=4, bevel=0.0, cap0=True):
    """XY çokgeninden z0..z1 katı; ön kenarı rad yarıçapıyla yuvarlatılmış (lens kubbesi, gövde).
    cap0=False: arka kapak yok (lens tek kat görünsün; içteki ışık kılavuzu daha az örtülür)"""
    pts = _s_ccw(pts)
    rings = [[(x, y, z0) for x, y in pts]]
    for k in range(steps + 1):
        t = math.radians(90 * k / steps)
        d = rad * (1 - math.cos(t))
        z = z1 - rad + rad * math.sin(t)
        o = offset(pts, d) if d > 1e-7 else pts
        rings.append([(x, y, z) for x, y in o])
    return _s_loft(group, name, rings, mat_, cap0, True, bevel)


def _s_dome_frame(group, name, outer, inner, z0, z1, rad, mat_, steps=4, inner_depth=0.0025):
    """Ortası delik lens kabuğu: dış kenar rad ile yuvarlak, üst yüz z1'de iç deliğe kadar, delikte inner_depth kadar iç duvar.
    outer ve inner aynı sayıda ve hizalı noktalı (_s_ring) olmalı. Arka yüz yok."""
    rings = [[(x, y, z0) for x, y in outer]]
    for k in range(steps + 1):
        t = math.radians(90 * k / steps)
        d = rad * (1 - math.cos(t))
        z = z1 - rad + rad * math.sin(t)
        o = offset(outer, d) if d > 1e-7 else outer
        rings.append([(x, y, z) for x, y in o])
    rings.append([(x, y, z1) for x, y in inner])
    rings.append([(x, y, z1 - inner_depth) for x, y in inner])
    return _s_loft(group, name, rings, mat_, False, False)


def _s_tube(group, name, pts, r, mat_, res=2, smooth=False, ures=4):
    """tube() + düşük eğri çözünürlüğü (üçgen bütçesi)"""
    ob = tube(group, name, pts, r, mat_, res, smooth)
    ob.data.resolution_u = ures
    return ob


def _s_prism_axis(group, name, pts, a0, a1, axis, mat_, bevel=0.0):
    """axis 'x': pts (z, y) X boyunca a0..a1; axis 'y': pts (x, z) Y boyunca a0..a1"""
    bm = bmesh.new()

    def P(p, a):
        return bl((a, p[1], p[0])) if axis == 'x' else bl((p[0], a, p[1]))
    A = [bm.verts.new(P(p, a0)) for p in pts]
    B = [bm.verts.new(P(p, a1)) for p in pts]
    bm.faces.new(A)
    bm.faces.new(list(reversed(B)))
    n = len(pts)
    for i in range(n):
        bm.faces.new([A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat_, group, bevel)


def _s_cutter(pts, a0, a1, axis='z'):
    """Boolean kesici (render'da gizli; dışa aktarılmaz). axis 'z': pts (x, y); 'y': pts (x, z)"""
    bm = bmesh.new()

    def P(p, a):
        return bl((p[0], p[1], a)) if axis == 'z' else bl((p[0], a, p[1]))
    A = [bm.verts.new(P(p, a0)) for p in pts]
    B = [bm.verts.new(P(p, a1)) for p in pts]
    bm.faces.new(A)
    bm.faces.new(list(reversed(B)))
    n = len(pts)
    for i in range(n):
        bm.faces.new([A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('cutter')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('cutter', me)
    scene.collection.objects.link(ob)
    ob.hide_render = True
    ob.display_type = 'WIRE'
    return ob


def _s_cut(ob, cutters, bevel=0.0):
    """Delikleri boolean ile açar, ardından kenar pahı (boolean önce uygulanır)"""
    for c in cutters:
        md = ob.modifiers.new('cut', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = c
        md.solver = 'EXACT'
    if bevel > 0:
        md = ob.modifiers.new('bevel', 'BEVEL')
        md.width = bevel
        md.segments = 2
        md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(30)
        md.harden_normals = True
        md.use_clamp_overlap = True
    return ob


def _s_refl(color):
    """Renkli lensin ardındaki iç taban: lens renginde koyu, yarı parlak reflektör (amber için yerel malzeme
    'ReflectorAmber', lamps.py'deki 'ReflectorRed' ile aynı yapı); beyaz/şeffaf lens için ortak 'Reflector'."""
    if color != 'amber':
        return mat('Reflector')
    if 'ReflectorAmber' not in MATS:
        m, p = _principled('ReflectorAmber')
        p.inputs['Base Color'].default_value = srgb('#b8600a')
        p.inputs['Roughness'].default_value = 0.24
        p.inputs['Metallic'].default_value = 0.7
        _normal(m, p, tex('pillow'), 0.35)
        MATS['ReflectorAmber'] = m
    return MATS['ReflectorAmber']


def _s_hex_nut(L, x, y, z0, z1, r):
    cyl(L.body, 'nut', r, (x, y, z0), (x, y, z1), mat('Zinc'), 6)


# ---------------------------------------------------------------------
# Tutuculu marker ortak gövdesi (HOR 123 / HOR 116 ailesi)
# ---------------------------------------------------------------------
T_PLATE = 0.0028  # tutucu plaka kalınlığı (çizimden ~2,7-2,8 mm)


def _s_holder(L, H, outline, flange_w, flange_d, gusset_xs, gusset_drop, plate_holes, flange_holes):
    """Siyah tutucu: arka dikey plaka (z 0..T) + üstte geriye uzanan flanş + altında üçgen kaburgalar.
    plate_holes: [(x, y, r)], flange_holes: [(x, z, r, slot_len)] (slot_len > 0: X boyunca yuva)"""
    t = T_PLATE
    out = _s_ccw(outline)
    plate = prism(L.body, 'holder_plate', out, 0.0, t, mat('Housing'), 0.0)
    cut = [_s_cutter(circle(r, 20 if r > 0.003 else 12, x, y), -0.01, 0.02, 'z') for x, y, r in plate_holes]
    _s_cut(plate, cut, 0.0)
    # ön yüzde ince kenar dudağı (çizimdeki çift çizgi)
    rim_o = _s_ring(out, 56)
    rim_i = offset(rim_o, 0.0022)
    frame(L.body, 'holder_lip', rim_o, rim_i, t - 0.0002, t + 0.0012, mat('Housing'), 0.0)
    # flanş
    tf = 0.003
    fw = flange_w
    fl = box(L.body, 'flange', -fw / 2, fw / 2, H / 2 - tf, H / 2, -flange_d, t, mat('Housing'), 0.0)
    fc = []
    for x, z, r, sl in flange_holes:
        pts = stadium(sl + 2 * r, 2 * r, 6, x, z) if sl > 0 else circle(r, 16, x, z)
        fc.append(_s_cutter(pts, H / 2 - tf - 0.01, H / 2 + 0.01, 'y'))
    _s_cut(fl, fc, 0.0)
    # kaburgalar (flanşın altında, plakanın arkasında)
    for gx in gusset_xs:
        tri = [(-flange_d + 0.0008, H / 2 - tf + 0.0002), (0.0002, H / 2 - tf + 0.0002), (0.0002, H / 2 - tf - gusset_drop)]
        _s_prism_axis(L.body, 'gusset', tri, gx - 0.00125, gx + 0.00125, 'x', mat('Housing'), 0.0)
    return t


def _s_cable_back(L, x, y, z0, drop=0.07):
    """Lamba arkasından tutucu deliğinden geçip aşağı sarkan kablo"""
    _s_tube(L.body, 'cable', [(x, y, z0), (x, y, -0.010), (x, y - 0.012, -0.022), (x + 0.004, y - drop, -0.030)], 0.0028, mat('Cable'), 2, True, 5)


def _s_ld2774_like(L, color):
    """LD 2774 (turuncu yan marker) / LD 2773 (beyaz ön pozisyon): HOR 123 stadyum lamba + L tutucu.
    Lamba 119,6 × 45,9 × 20,4; tutucu 74,9 yükseklik, 47,8 toplam derinlik; flanş delikleri 49 aralık (yuva 9,75 + Ø4,75)"""
    fn, emit_col, lens_key, retro_key = ('marker', 'amber', 'Lens.amber', 'Retro.amber') if color == 'amber' else ('front', 'white', 'Lens.clear', 'Retro.white')
    H = 0.0749
    LW, LH, LD = 0.1196, 0.0459, 0.0204
    yl = -H / 2 + LH / 2  # lamba merkezi (plaka altıyla hizalı)
    fd = 0.0478 - T_PLATE - LD  # flanş derinliği (plaka arka yüzünden geriye)
    # plaka dış hattı: alt kısım ~114 mm, köşeler R20; 32 mm yukarıdan tepeye 84 mm'ye daralan yamuk
    wb, wt, yk, rb = 0.114, 0.084, H / 2 - 0.032, 0.020
    outline = _s_arc(wb / 2 - rb, -H / 2 + rb, rb, -90, 0, 8) + [(wb / 2, yk), (wt / 2, H / 2), (-wt / 2, H / 2), (-wb / 2, yk)] + \
        _s_arc(-wb / 2 + rb, -H / 2 + rb, rb, 180, 270, 8)
    holes = [(0.0, yl, 0.006)] + [(sx * 0.035, yl, 0.0026) for sx in (-1, 1)] + [(sx * 0.017, yl + sy * 0.009, 0.0016) for sx in (-1, 1) for sy in (-1, 1)]
    zb = _s_holder(L, H, outline, wt, fd, (-0.038, 0.0, 0.038), 0.016, holes, [(-0.0245, -fd / 2, 0.002375, 0.005), (0.0245, -fd / 2, 0.002375, 0.0)])
    # lamba gövdesi (siyah taban halkası) ve lens
    st = stadium(LW, LH, 12, 0.0, yl)
    _s_dome(L.body, 'housing', st, zb - 0.0002, zb + 0.0115, 0.0016, mat('Housing'), 3)
    N = 72
    bw, bh = 0.1045, 0.0125
    lens_o = _s_ring(offset(_s_ccw(st), 0.0016), N)
    lens = _s_dome_frame(L.lens, 'lens', lens_o, _s_ring(rrect(bw - 0.0004, bh - 0.0004, 0.0055, 6, 0.0, yl), N), zb + 0.009, zb + 0.0184,
                         0.0045, mat(lens_key), 4, 0.0012)
    set_uv_planar(lens, 0.006)
    # neon çubuğun lens penceresi (hafif kabarık, düz yüzey; tek kat)
    win = _s_dome(L.lens, 'lens_bar', rrect(bw, bh, 0.0055, 6, 0.0, yl), zb + 0.0170, zb + LD, 0.0013, mat(lens_key), 3, cap0=False)
    set_uv_planar(win, 0.004)
    # köşe küp reflektör: lensin içinde, çubuk penceresi dışında kalan tüm alan
    r_o = _s_ring(offset(_s_ccw(st), 0.0034), N)
    r_i = _s_ring(rrect(bw + 0.002, bh + 0.0018, 0.006, 8, 0.0, yl), N)
    retro = frame(L.inner, 'retro', r_o, r_i, zb + 0.0128, zb + 0.0146, mat(retro_key), 0.0)
    set_uv_planar(retro, 0.012)
    # çubuğun krom kanalı ve iç zemini
    ch_o = _s_ring(rrect(bw + 0.0016, bh + 0.0014, 0.0058, 8, 0.0, yl), N)
    ch_i = _s_ring(rrect(bw - 0.0014, bh - 0.0016, 0.0045, 8, 0.0, yl), N)
    frame(L.inner, 'bar_channel', ch_o, ch_i, zb + 0.0118, zb + 0.0168, mat('Chrome'), 0.0)
    prism(L.inner, 'bar_floor', rrect(bw, bh, 0.005, 6, 0.0, yl), zb + 0.0112, zb + 0.0120, _s_refl(emit_col), 0.0)
    # neon ışık kılavuzu: yatay süt beyazı çubuk (yanınca imza ışığı)
    prism(L.E(fn), 'neon_bar', rrect(bw - 0.0030, 0.0084, 0.0042, 6, 0.0, yl), zb + 0.0124, zb + 0.0166, E(fn, emit_col), 0.0009)
    # arka: lamba civataları (M5, 70 mm) plakanın arkasında somunla, kablo merkez delikten
    for sx in (-0.035, 0.035):
        cyl(L.body, 'stud', 0.0024, (sx, yl, zb), (sx, yl, -0.0075), mat('Zinc'), 12)
        _s_hex_nut(L, sx, yl, 0.0, -0.0035, 0.0042)
    _s_cable_back(L, 0.0, yl, zb)


@product('ld2774', 'LD 2774', 'side', 'Turuncu yan marker, neon çubuk, altıgen reflektör, L tutucu')
def build_ld2774(L):
    _s_ld2774_like(L, 'amber')


@product('ld2773', 'LD 2773', 'front', 'Beyaz ön pozisyon, neon çubuk, altıgen reflektör, L tutucu')
def build_ld2773(L):
    _s_ld2774_like(L, 'white')


# ---------------------------------------------------------------------
# LD 2765 — HOR 116/SM1: köşeleri yuvarlak dikdörtgen lamba 110,8 × 52,2 × 20,65, neon çerçeve halka,
# ortada uçları sivri altıgen reflektör; tutucu 71,8 yükseklik, 43,2 derinlik, flanş delikleri 49 aralık,
# lamba vidaları 90 aralık (sac vidası, arkadan çıkar), 2 × 0,75 mm² 0,5 m kablo.
# ---------------------------------------------------------------------
def _s_bowed_rrect(w, h, r, bow, cx=0.0, cy=0.0, step=0.0055):
    """Üst ve alt kenarı hafif dışa bombeli yuvarlak dikdörtgen"""
    base = rrect(w, h - 2 * bow, r, 6)
    dense = []
    n = len(base)
    for i in range(n):
        a, b = base[i], base[(i + 1) % n]
        k = max(1, int(math.ceil(math.dist(a, b) / step)))
        for j in range(k):
            dense.append((a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k))
    out = []
    for x, y in dense:
        f = max(0.0, 1 - (2 * x / w) ** 2)
        out.append((cx + x, cy + y + math.copysign(bow * f, y)))
    return _s_ccw(out)


@product('ld2765', 'LD 2765', 'side', 'Turuncu yan marker, neon çerçeve halka, altıgen reflektör, tutuculu')
def build_ld2765(L):
    H = 0.0718
    LW, LH, LD = 0.1108, 0.0522, 0.02065
    yl = -H / 2 + LH / 2
    fd = 0.0432 - T_PLATE - LD
    # plaka: alt kısım lamba genişliğine yakın (R8 köşe), lamba üstünde S kavisle 77 mm tepeye daralır
    wb, wt, rb = 0.109, 0.077, 0.008
    yk = yl + LH / 2 - 0.004
    outline = _s_arc(wb / 2 - rb, -H / 2 + rb, rb, -90, 0, 6) + [(wb / 2, yk), (wb / 2 - 0.004, yk + 0.006), (wb / 2 - 0.0095, yk + 0.0085),
                                                               (wt / 2, H / 2), (-wt / 2, H / 2), (-wb / 2 + 0.0095, yk + 0.0085),
                                                               (-wb / 2 + 0.004, yk + 0.006), (-wb / 2, yk)] + \
        _s_arc(-wb / 2 + rb, -H / 2 + rb, rb, 180, 270, 6)
    holes = [(0.0, yl, 0.0068)] + [(sx * 0.045, yl, 0.0014) for sx in (-1, 1)] + [(sx * 0.025, yl + sy * 0.010, 0.0013) for sx in (-1, 1) for sy in (-1, 1)]
    zb = _s_holder(L, H, outline, wt, fd, (-0.034, 0.0, 0.034), 0.013, holes, [(-0.0245, -fd / 2, 0.0025, 0.0), (0.0245, -fd / 2, 0.00213, 0.003)])
    # lamba
    ol = _s_bowed_rrect(LW, LH, 0.010, 0.0012, 0.0, yl)
    _s_dome(L.body, 'housing', ol, zb - 0.0002, zb + 0.0118, 0.0018, mat('Housing'), 3)
    lo = offset(ol, 0.0018)
    lens = _s_dome(L.lens, 'lens', lo, zb + 0.009, zb + LD, 0.0040, mat('Lens.amber'), 4, cap0=False)
    set_uv_planar(lens, 0.006)
    # iç zemin: halka ile reflektör arası, lens renginde koyu reflektör
    prism(L.inner, 'floor', offset(ol, 0.0030), zb + 0.0118, zb + 0.0124, _s_refl('amber'), 0.0)
    # neon halka: dış hattın 4..10,5 mm içinde (fotoğrafta reflektöre kadar uzanan geniş ışık kılavuzu)
    ring_o = offset(ol, 0.0040)
    ring_i = offset(ol, 0.0105)
    frame(L.E('marker'), 'neon_ring', ring_o, ring_i, zb + 0.0124, zb + 0.0168, E('marker', 'amber'), 0.0)
    frame(L.inner, 'ring_wall', offset(ol, 0.0034), ring_o, zb + 0.0118, zb + 0.0150, _s_refl('amber'), 0.0)
    # orta reflektör: uçları sivri uzun altıgen (fotoğraf); sivri uçlar halkanın önüne biner
    hx, hy, px = 0.0425, 0.0117, 0.0490  # fotoğraftan: gövde 85 × 23,4 mm, uçlar 99 mm
    hexa = [(-px, yl), (-hx - 0.0012, yl - 0.0050), (-hx, yl - 0.0060), (-hx, yl - hy), (hx, yl - hy), (hx, yl - 0.0060), (hx + 0.0012, yl - 0.0050), (px, yl),
            (hx + 0.0012, yl + 0.0050), (hx, yl + 0.0060), (hx, yl + hy), (-hx, yl + hy), (-hx, yl + 0.0060), (-hx - 0.0012, yl + 0.0050)]
    retro = prism(L.inner, 'retro', hexa, zb + 0.0126, zb + 0.0172, mat('Retro.amber'), 0.0)
    set_uv_planar(retro, 0.012)
    frame(L.inner, 'retro_rim', offset(_s_ccw(hexa), -0.0007), _s_ccw(hexa), zb + 0.0124, zb + 0.0176, mat('HousingGloss'), 0.0)
    # arka: 90 mm aralıklı sac vidaları (plakanın arkasından uçları), kablo
    for sx in (-0.045, 0.045):
        cyl(L.body, 'screw', 0.0019, (sx, yl, zb), (sx, yl, -0.006), mat('Zinc'), 12)
        cyl(L.body, 'screw_tip', 0.0019, (sx, yl, -0.006), (sx, yl, -0.0095), mat('Zinc'), 12, r2=0.0003)
    cyl(L.body, 'grommet', 0.0062, (0.0, yl, 0.0004), (0.0, yl, -0.0025), mat('Rubber'), 24)
    _s_cable_back(L, 0.0, yl, zb)


# ---------------------------------------------------------------------
# LD 0128 / LD 0127 — düz marker 132 × 33 × 13: uçlarda siyah tırnaklar (Ø5,6 delik, 115 mm), solda altıgen reflektör,
# sağda 3 LED'li kare bölme (lens burada 2 mm kabarık), 0,5 m 2 × 0,75 kablo alt kenardan.
# ---------------------------------------------------------------------
def _s_ld0128_like(L, color):
    fn, emit_col, lens_key, retro_key = ('marker', 'amber', 'Lens.amber', 'Retro.amber') if color == 'amber' else ('front', 'white', 'Lens.clear', 'Retro.white')
    W, Hh = 0.132, 0.033
    # uç tırnakları: dış uca doğru incelen eğik ön yüz (yan görünüş), Ø5,6 delik + havşa
    for s in (-1, 1):
        x0, x1 = 0.0515, W / 2
        prof = [(x0, 0.0), (x1, 0.0), (x1, 0.0062), (x1 - 0.0012, 0.0072), (x0 + 0.0022, 0.0104), (x0, 0.0106)]
        if s < 0:
            prof = [(-x, z) for x, z in reversed(prof)]
        tab = _s_prism_axis(L.body, 'tab', prof, -Hh / 2 + 0.0004, Hh / 2 - 0.0004, 'y', mat('Housing'), 0.0)
        hx = s * 0.0575
        _s_cut(tab, [_s_cutter(circle(0.0028, 16, hx, 0.0), -0.01, 0.02, 'z'), _s_cutter(circle(0.0047, 20, hx, 0.0), 0.0058, 0.02, 'z')], 0.0007)
    # taban köprüsü ve lamba gövdesi (ince siyah kenar lensi çevreler)
    box(L.body, 'base', -0.054, 0.054, -Hh / 2 + 0.0015, Hh / 2 - 0.0015, 0.0, 0.0030, mat('Housing'), 0.0005)
    # gövde: lensi saran ince siyah tekne (çerçeve) + taban
    frame(L.body, 'housing', rrect(0.1000, Hh, 0.003, 4), rrect(0.0976, 0.0306, 0.0022, 4), 0.0, 0.0094, mat('Housing'), 0.0006)
    prism(L.body, 'housing_floor', rrect(0.0990, 0.0320, 0.0025, 4), 0.0, 0.0046, mat('Housing'), 0.0)
    lens = _s_dome(L.lens, 'lens', rrect(0.0972, 0.0302, 0.0024, 4), 0.0060, 0.0110, 0.0020, mat(lens_key), 3, cap0=False)
    set_uv_planar(lens, 0.006)
    bump = _s_dome(L.lens, 'lens_bump', rrect(0.0270, 0.0282, 0.0030, 4, 0.0250, 0.0), 0.0098, 0.0130, 0.0018, mat(lens_key), 3, cap0=False)
    set_uv_planar(bump, 0.004)
    # reflektör: sol büyük alan ve LED bölmesinin sağındaki şerit
    for x0, x1 in ((-0.0465, 0.0110), (0.0392, 0.0466)):
        rf = prism(L.inner, 'retro', rrect(x1 - x0, 0.0272, 0.0012, 2, (x0 + x1) / 2, 0.0), 0.0070, 0.0088, mat(retro_key), 0.0)
        set_uv_planar(rf, 0.010)
    # LED bölmesi: krom zemin, siyah ayraç duvarlar, üçgen dizilmiş 3 LED (kabarık Fresnel halkalı kaplar)
    prism(L.inner, 'bay_floor', rrect(0.0270, 0.0272, 0.0015, 2, 0.0250, 0.0), 0.0050, 0.0058, _s_refl(emit_col), 0.0)
    for xw in (0.0113, 0.0389):
        box(L.inner, 'bay_wall', xw - 0.0005, xw + 0.0005, -0.0136, 0.0136, 0.0050, 0.0096, mat('HousingGloss'), 0.0)
    for (x, y) in ((0.0205, 0.0), (0.0295, 0.0052), (0.0295, -0.0052)):
        led(L.E(fn), L.inner, 'led', x, y, 0.0094, 0.0013, E(fn, emit_col), mat('Chrome'), 0.0046, 0.0034)
        cyl(L.inner, 'led_body', 0.0021, (x, y, 0.0058), (x, y, 0.0062), mat('Label'), 12)
    # kablo: tabandaki kanaldan alt kenara çıkar, aşağı sarkar; uçta iki damar
    cx = -0.036
    _s_tube(L.body, 'cable', [(cx, 0.004, 0.0028), (cx, -Hh / 2, 0.0028), (cx, -0.030, 0.0032), (cx + 0.003, -0.055, 0.008), (cx + 0.010, -0.075, 0.016)],
            0.0024, mat('Cable'), 2, True, 5)
    for k, dx in enumerate((-0.0011, 0.0011)):
        _s_tube(L.body, 'wire', [(cx + 0.010 + dx, -0.075, 0.016), (cx + 0.012 + dx * 3, -0.085, 0.020)], 0.0009, mat('Cable'), 1)
        cyl(L.body, 'wire_end', 0.0005, (cx + 0.012 + dx * 3, -0.085, 0.020), (cx + 0.0125 + dx * 3.3, -0.089, 0.0215), mat('Brass'), 8)


@product('ld0128', 'LD 0128', 'side', 'Düz turuncu yan marker, 3 LED, reflektörlü, 2 × Ø5,6 tırnak')
def build_ld0128(L):
    _s_ld0128_like(L, 'amber')


@product('ld0127', 'LD 0127', 'front', 'Düz beyaz ön marker, 3 LED, reflektörlü, 2 × Ø5,6 tırnak')
def build_ld0127(L):
    _s_ld0128_like(L, 'white')


# ---------------------------------------------------------------------
# Plaka lambaları: XY kesitli (önden görünüş) gövdenin Z boyunca loft'u
# ---------------------------------------------------------------------
def _s_hood_profile(w, h, yb, a, b, n=8, p=2.0):
    """Önden görünüş kesiti: taban yb, genişlik w, h - b'ye kadar dik yan, omuz (a yatay, b dikey; p = 2 elips,
    p ≈ 1,1 uçları yuvarlak düz pah), tepe h. Alt-ortadan başlar, saat yönü tersine; nokta sayısı sabit (1 + 2·(n + 2))"""
    R = [(w / 2, yb), (w / 2, h - b)]
    for i in range(1, n + 1):
        t = math.radians(90 * i / n)
        c, s = math.cos(t), math.sin(t)
        R.append((w / 2 - a + a * (abs(c) ** (2 / p)), h - b + b * (abs(s) ** (2 / p))))
    Lp = [(-x, y) for x, y in reversed(R)]
    return [(0.0, yb)] + R + Lp


def _s_hood_loft(group, name, z0, z1, wf, hf, yb, a, b, rad, mat_, n=8, mid=4, bevel=0.0, p=2.0):
    """z0 (arka) → z1 (ön) gövde; wf(z), hf(z) genişlik ve yükseklik; iki uçta rad yarıçaplı yuvarlak kenar"""
    zs = []
    m = 3
    for k in range(m + 1):  # arka uç
        p = math.radians(90 * (m - k) / m)
        zs.append((z0 + rad * (1 - math.sin(p)), rad * (1 - math.cos(p))))
    for k in range(1, mid):
        zs.append((z0 + rad + (z1 - z0 - 2 * rad) * k / mid, 0.0))
    for k in range(m + 1):  # ön uç
        p = math.radians(90 * k / m)
        zs.append((z1 - rad * (1 - math.sin(p)), rad * (1 - math.cos(p))))
    rings = []
    for z, d in zs:
        w, h = wf(z) - 2 * d, hf(z) - d
        prof = _s_hood_profile(w, h, yb, max(a - d, 0.001), max(b - d, 0.001), n, p)
        rings.append([(x, y, z) for x, y in prof])
    return _s_loft(group, name, rings, mat_, True, True, bevel)


def _s_hood_surface(x, w, h, a, b, p=2.0):
    """Kesit dış yüzeyinde x'teki nokta ve dışa normal (x, y, nx, ny)"""
    xa = w / 2 - a
    ax = abs(x)
    if ax <= xa:
        return x, h, 0.0, 1.0
    dx = min(ax - xa, a * 0.999)
    dy = b * (1 - (dx / a) ** p) ** (1 / p)
    y = h - b + dy
    nx, ny = (dx / a) ** (p - 1) / a, (max(dy, 1e-6) / b) ** (p - 1) / b
    ln = math.hypot(nx, ny)
    return x, y, math.copysign(nx / ln, x), ny / ln


# LTD 2834 — HOR 127 sürüm II: plaka lambası + kırmızı pozisyon. 93,5 (G) × 70 (D) × 58 (Y), 2 × M5 civata 46 mm.
@product('ltd2834', 'LTD 2834', 'plate', 'Plaka lambası, beyaz difüzör + kırmızı neon pozisyon şeridi, 2 × M5')
def build_ltd2834(L):
    D = 0.070
    z0, z1 = -D / 2, D / 2

    def wf(z):  # üstten görünüş yamuk: önde 93,5, arkada ~75
        return 0.075 + (z - z0) / D * 0.0185

    def hf(z):  # yandan: arkada ~40, önde 58 (eğik üst)
        return 0.040 + (z - z0) / D * 0.018
    A_, B_, PW = 0.021, 0.020, 1.3  # omuz: düz pah (fotoğraf), uçları yuvarlak
    # taban bandı (13 mm) ve kapak (bandın üstünde, hafif içeride; aralarında ek çizgisi)
    _s_hood_loft(L.body, 'base_band', z0, z1, wf, lambda z: 0.0130, 0.0, 0.002, 0.002, 0.005, mat('Housing'), 2, 3)
    _s_hood_loft(L.body, 'hood', z0 + 0.0006, z1 - 0.0006, lambda z: wf(z) - 0.0016, hf, 0.0125, A_, B_, 0.0030, mat('Housing'), 8, 5, p=PW)
    # difüzör: ön yüzde, kapak hattının 4 mm içinde, alt kenarı bandın üstünde (süt beyazı, plaka ışığı)
    wfr, hfr = wf(z1) - 0.0016, hf(z1)
    din = 0.0040
    prof = _s_hood_profile(wfr - 2 * din, hfr - din, 0.0150, A_ - din * 0.6, B_ - din * 0.6, 8, PW)
    prism(L.body, 'diff_frame', offset(_s_ccw(prof), -0.0012), z1 - 0.004, z1 + 0.0002, mat('HousingGloss'), 0.0006)
    prism(L.E('plate'), 'diffuser', prof, z1 - 0.003, z1 + 0.0009, E('plate', 'white'), 0.0007)
    # kırmızı neon Π şerit üst yüzde (çizim: arka uçtan 16 mm, bacaklar öne doğru açılır), kırmızı lens kılıf
    path = []
    for (x, z) in ((-0.0262, 0.022), (-0.0242, 0.006), (-0.0222, -0.010), (-0.0200, -0.0190), (-0.007, -0.0190), (0.007, -0.0190),
                   (0.0200, -0.0190), (0.0222, -0.010), (0.0242, 0.006), (0.0262, 0.022)):
        sx, sy, nx, ny = _s_hood_surface(x, wf(z) - 0.0016, hf(z), A_, B_, PW)
        path.append((sx, sy, nx, ny, z))
    _s_tube(L.E('position'), 'pos_neon', [(sx + nx * 0.0012, sy + ny * 0.0012, z) for sx, sy, nx, ny, z in path], 0.0016, E('position', 'red'), 2)
    _s_tube(L.lens, 'pos_lens', [(sx + nx * 0.0016, sy + ny * 0.0016, z) for sx, sy, nx, ny, z in path], 0.0028, mat('Lens.red'), 2)
    _s_tube(L.body, 'pos_seat', [(sx - nx * 0.0002, sy - ny * 0.0002, z) for sx, sy, nx, ny, z in path], 0.0030, mat('HousingGloss'), 1)
    # taban: 2 × M5 civata (46 mm) somunlu, köşe vidaları, kablo
    for sx in (-0.023, 0.023):
        cyl(L.body, 'stud', 0.0025, (sx, 0.0, 0.0), (sx, -0.017, 0.0), mat('Zinc'), 12)
        cyl(L.body, 'nut', 0.0046, (sx, 0.0, 0.0), (sx, -0.004, 0.0), mat('Zinc'), 6)
    for sx, sz in ((-0.040, 0.029), (0.033, -0.029)):
        cyl(L.body, 'screw', 0.0022, (sx, 0.0002, sz), (sx, -0.0012, sz), mat('Zinc'), 12)
    _s_tube(L.body, 'cable', [(0.0, 0.002, -0.012), (0.0, -0.012, -0.013), (0.0, -0.024, -0.030), (0.004, -0.030, -0.065)], 0.0028, mat('Cable'), 2, True, 5)


# LTD 229 — HOR 47: klasik LED plaka lambası. 97 (G) × 64,7 (Y) × 62,3 (D), 2 × M5 civata 46 mm, 2 × 0,75 kablo.
@product('ltd229', 'LTD 229', 'plate', 'LED plaka lambası, siyah kapak, şeffaf pencere, 2 × M5')
def build_ltd229(L):
    D = 0.0623
    z0, z1 = -D / 2, D / 2
    W, Hh = 0.097, 0.0647
    # taban bandı (20 mm, tam genişlik, yuvarlak köşeli plan) ve kubbeli kapak (eliptik omuzlar, tepe ~43 mm)
    _s_hood_loft(L.body, 'base_band', z0, z1, lambda z: W, lambda z: 0.0200, 0.0, 0.0025, 0.0025, 0.007, mat('Housing'), 2, 3)
    A_, B_ = 0.027, 0.034
    hood = _s_hood_loft(L.body, 'hood', z0 + 0.0005, z1 - 0.0005, lambda z: W - 0.0012, lambda z: Hh, 0.0195, A_, B_, 0.006, mat('Housing'), 10, 5)
    # LED boşluğu: katı kapağın içine cep (krom kap ve LED'ler kapak gövdesine gömülmesin)
    _s_cut(hood, [_s_cutter(rrect(0.0470, 0.0300, 0.0028, 4, 0.0, 0.0365), z1 - 0.0128, z1 + 0.01, 'z')])
    # ön yüz: kapak çerçevesi içinde açık gri panel, ortada şeffaf pencere (aşağı-öne bakar), arkasında krom + 3 LED
    din = 0.0050
    pan = _s_ring(_s_hood_profile(W - 2 * din, Hh - din, 0.0215, A_ - din, B_ - din, 10), 64)
    win = _s_ring(rrect(0.046, 0.029, 0.0025, 4, 0.0, 0.0365), 64)
    frame(L.body, 'panel', pan, win, z1 - 0.004, z1 + 0.0004, mat('Label'), 0.0)
    lens = prism(L.lens, 'window', rrect(0.046, 0.029, 0.0025, 4, 0.0, 0.0365), z1 - 0.0035, z1 + 0.0002, mat('Lens.clear'), 0.0006)
    set_uv_planar(lens, 0.005)
    box(L.inner, 'cavity_floor', -0.023, 0.023, 0.022, 0.051, z1 - 0.0125, z1 - 0.0115, mat('Reflector'))
    frame(L.inner, 'cavity_wall', _s_ring(rrect(0.0468, 0.0298, 0.0028, 4, 0.0, 0.0365), 48), _s_ring(rrect(0.0452, 0.0282, 0.0022, 4, 0.0, 0.0365), 48),
          z1 - 0.0125, z1 - 0.0035, mat('Reflector'), 0.0)
    for (x, y) in ((-0.0135, 0.0290), (0.0, 0.0445), (0.0135, 0.0290)):
        led(L.E('plate'), L.inner, 'led', x, y, z1 - 0.0062, 0.0016, E('plate', 'white'), mat('Chrome'), 0.0080, 0.0050)
    # civatalar, arka yüzde iki vida başı ve kablo çıkışı
    for sx in (-0.023, 0.023):
        cyl(L.body, 'stud', 0.0025, (sx, 0.0, 0.004), (sx, -0.016, 0.004), mat('Zinc'), 12)
        cyl(L.body, 'nut', 0.0046, (sx, 0.0, 0.004), (sx, -0.004, 0.004), mat('Zinc'), 6)
    for sx in (-0.034, 0.034):
        cyl(L.body, 'screw_head', 0.0036, (sx, 0.034, z0 + 0.0003), (sx, 0.034, z0 - 0.0015), mat('Zinc'), 16)
    cyl(L.body, 'gland', 0.0048, (-0.030, 0.050, z0 + 0.001), (-0.030, 0.050, z0 - 0.003), mat('Rubber'), 16)
    _s_tube(L.body, 'cable', [(-0.030, 0.050, z0 - 0.002), (-0.030, 0.050, z0 - 0.012), (-0.020, 0.030, z0 - 0.030), (0.000, -0.010, z0 - 0.045),
                           (0.012, -0.040, z0 - 0.050)], 0.0026, mat('Cable'), 2, True, 5)
