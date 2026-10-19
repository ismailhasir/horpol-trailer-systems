# Arka kombine lambalar: LZD 2856 (Heavy Duty), LZD 2423 (LUCY), LZD 2448 (LUNA), LZD 2877 / 2880 (CUBE).
# lamps.py'nin globals'ı içinde exec edilir (prism, frame, lathe, mat, E, product ... buradan gelir).
# Ölçüler: üretici teknik çizimleri (.claude/ref/lamps/<KOD>/attachments), desenler: galeri fotoğrafları.
# Sözleşme: lens +Z, X genişlik (+X arkadan bakana göre sağ), Y yukarı, montaj yüzeyi z = 0, civata/fiş −Z.


# ---------------------------------------------------------------------
# Modüle özel yardımcılar
# ---------------------------------------------------------------------
def _uv(ob, s):
    if ob is not None and ob.type == 'MESH':
        set_uv_planar(ob, s)
    return ob


def holed(group, name, outer, holes, z0, z1, m, bevel=0.0, seg=2):
    """Delikli levha: dış çokgen + iç delik çokgenleri (scanfill), z0..z1"""
    bm = bmesh.new()
    loops = [outer] + list(holes)
    layers = []
    for z in (z0, z1):
        edges = []
        vl = []
        for lp in loops:
            vs = [bm.verts.new(bl((x, y, z))) for x, y in lp]
            n = len(vs)
            edges += [bm.edges.new((vs[i], vs[(i + 1) % n])) for i in range(n)]
            vl.append(vs)
        bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges, normal=bl((0, 0, 1)))
        layers.append(vl)
    for a, b in zip(layers[0], layers[1]):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, m, group, bevel, seg)


def rot_pts(pts, a, cx=0.0, cy=0.0):
    c, s = math.cos(a), math.sin(a)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def disc(group, name, x, y, z, r, m, n=8):
    """Tek yüzlü düz disk (+Z'ye bakar): LED yayıcı yüzeyi"""
    bm = bmesh.new()
    vs = [bm.verts.new(bl((x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n), z))) for i in range(n)]
    f = bm.faces.new(vs)
    f.normal_update()
    if f.normal.dot(bl((0, 0, 1))) < 0:
        f.normal_flip()
    return _obj(name, bm, m, group, 0.0)


def ledq(L, fn, color, x, y, z, r=0.0018, cup_r=0.0045, depth=0.0035, cupmat='Chrome', seg=8):
    """Ucuz LED: öne açılan reflektör kabı (INNER) + dipte ışık veren disk (EMIT). z: kabın ağzı"""
    ob = cyl(L.inner, 'cup', r * 1.25, (x, y, z - depth), (x, y, z), mat(cupmat), seg, r2=cup_r, caps=False)
    ob.data.set_sharp_from_angle(angle=math.radians(80))  # az segmentte de yuvarlak gölgelensin (köşe tepe bölünmesin)
    if cupmat.startswith('Retro'):
        _uv(ob, 0.004)
    elif cupmat == 'ReflectorRed':
        _uv(ob, 0.008)
    disc(L.E(fn), 'led', x, y, z - depth + 0.0008, r, E(fn, color), 8)


def conduit(L, pts, r, m='Conduit', res=2, ures=5):
    """Düşük çözünürlüklü kablo / koruge (ham GLB bütçesi için)"""
    ob = tube(L.body, 'conduit', pts, r, mat(m), res, smooth=True)
    ob.data.resolution_u = ures
    return ob


def amp7_lite(L, x, y, z, length=0.045):
    """AMP 7 pin yuvarlak fiş (yeşil contalı, kanallı gövde), -Z yönünde; düşük çokgen"""
    cyl(L.body, 'amp_body', 0.016, (x, y, z), (x, y, z - length), mat('ConnBlack'), 16)
    cyl(L.body, 'amp_seal', 0.0178, (x, y, z - length * 0.30), (x, y, z - length * 0.40), mat('ConnGreen'), 16)
    cyl(L.body, 'amp_nut', 0.0195, (x, y, z - length * 0.55), (x, y, z - length * 0.75), mat('ConnBlack'), 8)
    cyl(L.body, 'amp_tail', 0.009, (x, y, z), (x, y, z + 0.012), mat('ConnBlack'), 12)


def chip(L, fn, color, x, y, z, w=0.0022, h=0.0016, t=0.0008):
    box(L.E(fn), 'chip', x - w / 2, x + w / 2, y - h / 2, y + h / 2, z, z + t, E(fn, color))


# =====================================================================
# LZD 2856 — HEAVY DUTY (sol): 451 × 139 × 74 mm, 2 × M8 (152 mm), AMP 7 pin koruge kablo (0,3 m), 8 vida, 4 sekizgen pencere.
# Soldan (arkadan bakınca): turuncu LED ızgara (sinyal) | büyük kırmızı: stop LED'leri + 4 neon şevron (pozisyon) + reflektör
# | beyaz LED ızgara (geri vites) | kırmızı LED ızgara (sis).
# =====================================================================
@product('lzd2856', 'LZD 2856', 'stop', 'Heavy Duty sol (sağ: LZD 2857, ayna)')
def build_lzd2856(L):
    W, H, D = 0.451, 0.139, 0.074
    out = rrect(W, H, 0.011, 4)
    WH = 0.104
    wins = [(-0.168, 0.060, 'turn'), (-0.0436, 0.140, 'big'), (0.086, 0.060, 'reverse'), (0.168, 0.060, 'fog')]

    def octo(cx, w, d=0.0):
        c = 0.010 if w < 0.1 else 0.014
        return offset(chamfer_rect(w, WH, c, cx, 0.0), d)

    # arka gövde (ortak tekne) + pencere başına LED modülü sırtı
    _uv(prism(L.body, 'tub', offset(out, 0.009), 0.008, 0.060, mat('Housing'), 0.004, 2), 0.03)
    for cx, w, _ in wins:
        _uv(prism(L.body, 'module', octo(cx, w, 0.004), 0.0, 0.012, mat('Housing')), 0.03)
    # ön çerçeve (delikli levha, 8 vida)
    fr = holed(L.body, 'frame', out, [octo(cx, w) for cx, w, _ in wins], 0.058, D, mat('Housing'), 0.0025)
    _uv(fr, 0.03)
    # çerçeve kaburgaları: uçlarda ve pencere araları yatay, üst/alt kenarda dikey çentikler
    zr0, zr1 = D - 0.0004, D + 0.0014
    for sx in (-1, 1):
        for yy in (-0.006, 0.006):
            box(L.body, 'rib_end', sx * 0.2185 - 0.0075, sx * 0.2185 + 0.0075, yy - 0.0016, yy + 0.0016, zr0, zr1, mat('Housing'))
    gaps = [(-0.138, -0.1136), (0.0264, 0.056), (0.116, 0.138)]
    for g0, g1 in gaps:
        for yy in (-0.005, 0.005):
            box(L.body, 'rib_mid', g0 - 0.001, g1 + 0.001, yy - 0.0014, yy + 0.0014, zr0, zr1, mat('Housing'))
    for xs in ((-0.168,), (-0.062, -0.050), (0.086,), (0.168,)):
        for x in xs:
            for sy in (-1, 1):
                box(L.body, 'rib_top', x - 0.0018, x + 0.0018, sy * 0.0648 - 0.003, sy * 0.0648 + 0.003, zr0, zr1, mat('Housing'))
    # vidalar (paslanmaz, kubbe başlı, altıgen yuva, parlak siyah oturma halkası)
    for x in (-0.213, -0.1235, 0.0385, 0.215):
        for y in (-0.0535, 0.0535):
            cyl(L.body, 'screw_seat', 0.0056, (x, y, D - 0.002), (x, y, D + 0.0004), mat('HousingGloss'), 10, caps=False)
            cyl(L.body, 'screw', 0.0037, (x, y, D - 0.001), (x, y, D + 0.0016), mat('Stainless'), 12, r2=0.0030)
            disc(L.body, 'screw_hex', x, y, D + 0.00165, 0.0014, mat('ConnBlack'), 6)

    zf = 0.0615  # pencere tabanı (önü)
    zc = 0.0655  # LED kabı ağzı
    for cx, w, kind in wins:
        win = octo(cx, w, 0.0005)
        floor_mat = {'turn': 'Housing', 'big': 'ReflectorRed', 'reverse': 'Reflector', 'fog': 'ReflectorRed'}[kind]
        ob = prism(L.inner, 'floor', win, zf - 0.003, zf, mat(floor_mat), 0.0)
        _uv(ob, 0.03 if floor_mat == 'ReflectorRed' else 0.02)
        lens_key = {'turn': 'Lens.amber', 'big': 'Lens.red', 'reverse': 'Lens.clear', 'fog': 'Lens.red'}[kind]
        _uv(prism(L.lens, 'lens', win, 0.0685, 0.0708, mat(lens_key), 0.0006, 1), 0.010)
        if kind == 'big':
            continue
        fn, color = {'turn': ('turn', 'amber'), 'reverse': ('reverse', 'white'), 'fog': ('fog', 'red')}[kind]
        rows = [0.0435, 0.029, 0.0145, 0.0, -0.0145, -0.029, -0.0435]
        for i, yy in enumerate(rows):
            xs = (-0.015, 0.0, 0.015) if i % 2 == 0 else (-0.0225, -0.0075, 0.0075, 0.0225)
            for dx in xs:
                ledq(L, fn, color, cx + dx, yy, zc, r=0.0036, cup_r=0.0058, depth=0.004)

    # büyük pencere: stop LED'leri (5-7-9-7-5) + neon şevronlar (pozisyon)
    bx = -0.0436
    for yy, n in ((0.044, 5), (0.0235, 7), (0.0, 9), (-0.0235, 7), (-0.044, 5)):
        for i in range(n):
            ledq(L, 'stop', 'red', bx + (i - (n - 1) / 2) * 0.0148, yy, zc, r=0.0021, cup_r=0.0046, depth=0.0035)
    # reflektör (köşe küp) alanları: neon şevronların dışındaki üst/alt yamuklar
    for sy in (1, -1):
        trap = [(-0.0540, sy * 0.0505), (0.0540, sy * 0.0505), (0.0595, sy * 0.0465), (0.0460, sy * 0.0367), (-0.0460, sy * 0.0367),
                (-0.0595, sy * 0.0465)]
        _uv(prism(L.inner, 'retro', [(bx + x, y) for x, y in trap], zf, zf + 0.0008, mat('Retro.red')), 0.006)
    for sy in (1, -1):
        a = [(-0.0625, sy * 0.0455), (-0.0465, sy * 0.034), (0.0465, sy * 0.034), (0.0625, sy * 0.0455)]
        b = [(-0.0695, sy * 0.031), (-0.053, sy * 0.0135), (0.053, sy * 0.0135), (0.0695, sy * 0.031)]
        for nm, pts in (('neon_a', a), ('neon_b', b)):
            ribbon(L.E('position'), nm, [(bx + x, y) for x, y in pts], 0.0034, 0.0665, E('position', 'red'), 0.0026)

    # arka: 2 × M8 (152 mm), koruge kablo + AMP 7 pin
    for sx in (-0.076, 0.076):
        stud(L, sx, 0.0, -0.0015, 0.025, 0.004)
    cyl(L.body, 'grommet', 0.0075, (0.0, 0.012, 0.0), (0.0, 0.012, -0.008), mat('Rubber'), 16)
    conduit(L, [(0.0, 0.012, -0.004), (0.0, 0.016, -0.038), (0.03, 0.05, -0.052), (0.065, 0.062, -0.054), (0.075, 0.062, -0.060)], 0.0045)
    amp7_lite(L, 0.075, 0.062, -0.072, 0.045)


# =====================================================================
# Yuvarlak lambalar için ortak gövde (Ø121,4 siyah gövde + Ø155 halka, versiyon 2)
# =====================================================================
def _round_body(L, ring_mat, z_body, z_ring, ring_r=0.0775):
    lathe(L.body, 'housing', [(0.0, 0.0), (0.050, 0.0), (0.0555, 0.0012), (0.0590, 0.0045), (0.0607, 0.0095),
                              (0.0607, z_body), (0.0560, z_body), (0.0, z_body)], mat('Housing'), 48)
    # arka yüzde dairesel takviye halkası ve üç ayak
    frame(L.body, 'back_rib', circle(0.042, 36), circle(0.039, 36), -0.0012, 0.001, mat('Housing'))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        cyl(L.body, 'back_pad', 0.004, (0.047 * math.cos(a), 0.047 * math.sin(a), -0.0012), (0.047 * math.cos(a), 0.047 * math.sin(a), 0.001),
            mat('Housing'), 12)
    # halka (paslanmaz / krom), hafif konik
    zr = z_ring
    lathe(L.body, 'ring', [(0.0574, z_body - 0.001), (ring_r, z_body - 0.001), (ring_r + 0.0002, z_body + 0.0008),
                           (ring_r - 0.0012, z_body + 0.0022), (0.0605, zr), (0.0578, zr - 0.0002), (0.0574, z_body - 0.001)], mat(ring_mat), 72)
    frame(L.body, 'gasket', circle(0.0580, 48), circle(0.0550, 48), z_body - 0.001, zr - 0.0003, mat('Gasket'))
    prism(L.inner, 'base', circle(0.0556, 36), z_body - 0.0025, z_body - 0.001, mat('Housing'))
    # arka: 2 civata (45 mm), kablo rakoru ve kablo
    for sx in (-0.0225, 0.0225):
        stud(L, sx, 0.0, -0.001, 0.022, 0.003)
    cyl(L.body, 'gland', 0.0062, (0.0, -0.03, 0.0), (0.0, -0.03, -0.007), mat('Rubber'), 12)
    conduit(L, [(0.0, -0.03, -0.005), (0.0, -0.034, -0.025), (0.008, -0.06, -0.045), (0.02, -0.085, -0.05)], 0.0028, 'Cable')


# =====================================================================
# LZD 2423 — LUCY: gövde Ø121,4, derinlik 33,5, paslanmaz halka Ø155 (versiyon 2, HOR-1001 seti), 2 civata 45 mm.
# Orta: turuncu fan reflektör (sinyal, 2a) — çevresinde neon halka + 4 teğet kol (pozisyon, R1) — kollar arası 4 cepte 3'er LED (stop, S1).
# =====================================================================
@product('lzd2423', 'LZD 2423', 'stop', 'LUCY yuvarlak, paslanmaz halka')
def build_lzd2423(L):
    zb, zr = 0.0205, 0.0272
    _round_body(L, 'Stainless', zb, zr)
    # kırmızı fasetli reflektör halkası (stop cepleri)
    _uv(frame(L.inner, 'red_refl', circle(0.0552, 48), circle(0.0255, 48), zb - 0.001, zb + 0.0008, mat('ReflectorRed')), 0.03)
    # turuncu fan reflektör: konik çanak + 8 kıvrık kanat + krom orta koni
    _uv(lathe(L.inner, 'fan_bowl', [(0.0045, zb - 0.0005), (0.0150, zb + 0.0012), (0.0252, zb + 0.0042), (0.0256, zb + 0.0042)],
              mat('Retro.amber'), 32), 0.005)
    for k in range(8):
        a0 = k * math.pi / 4
        pts = []
        for r, da in ((0.0085, 0.0), (0.0245, 0.42)):
            pts.append((r, da))
        (r0, d0), (r1, d1) = pts
        hw = 0.0009
        poly = [(r0 * math.cos(a0 + d0) - hw * math.sin(a0 + d0), r0 * math.sin(a0 + d0) + hw * math.cos(a0 + d0)),
                (r1 * math.cos(a0 + d1) - hw * math.sin(a0 + d1), r1 * math.sin(a0 + d1) + hw * math.cos(a0 + d1)),
                (r1 * math.cos(a0 + d1) + hw * math.sin(a0 + d1), r1 * math.sin(a0 + d1) - hw * math.cos(a0 + d1)),
                (r0 * math.cos(a0 + d0) + hw * math.sin(a0 + d0), r0 * math.sin(a0 + d0) - hw * math.cos(a0 + d0))]
        prism(L.inner, 'blade', poly, zb, zb + 0.0052, mat('Chrome'))
        am = a0 + math.pi / 8 + 0.2
        ledq(L, 'turn', 'amber', 0.0170 * math.cos(am), 0.0170 * math.sin(am), zb + 0.0040, r=0.0020, cup_r=0.0036, depth=0.0028)
    lathe(L.inner, 'cone', [(0.0088, zb), (0.0078, zb + 0.0055), (0.0050, zb + 0.0062), (0.0030, zb + 0.0030), (0.0018, zb + 0.0026)],
          mat('Chrome'), 20)
    disc(L.E('turn'), 'led_c', 0.0, 0.0, zb + 0.0027, 0.0016, E('turn', 'amber'), 10)
    # neon halka + 4 teğet kol (pozisyon), dörtlü dönel simetri
    zn0, zn1 = zb + 0.0030, zb + 0.0062
    frame(L.E('position'), 'neon_ring', circle(0.0352, 48), circle(0.0258, 48), zn0, zn1, E('position', 'red'), 0.0008, 2)
    arm = [(-0.0372, 0.012), (-0.0272, 0.012), (-0.0272, 0.0455), (-0.0372, 0.0384)]
    for k in range(4):
        prism(L.E('position'), 'neon_arm', rot_pts(arm, -k * math.pi / 2), zn0, zn1, E('position', 'red'), 0.0008, 2)
    # stop: kollar arasındaki 4 cepte 3'er LED
    for c in (91.7, 1.7, -88.3, -178.3):
        for d in (-22, 0, 22):
            a = math.radians(c + d)
            ledq(L, 'stop', 'red', 0.0445 * math.cos(a), 0.0445 * math.sin(a), zb + 0.0042, r=0.0026, cup_r=0.0052, depth=0.0040,
                 cupmat='ReflectorRed')
    # lens: kırmızı halka kubbe + turuncu orta
    _uv(lathe(L.lens, 'lens_red', [(0.0254, 0.0329), (0.040, 0.0322), (0.050, 0.0303), (0.0556, 0.0274), (0.0556, 0.0264),
                                  (0.050, 0.0290), (0.040, 0.0308), (0.0254, 0.0314), (0.0254, 0.0329)], mat('Lens.red'), 48), 0.010)
    _uv(lathe(L.lens, 'lens_amber', [(0.0, 0.0335), (0.0254, 0.0329), (0.0254, 0.0314), (0.0, 0.0320)], mat('Lens.amber'), 32), 0.008)


# =====================================================================
# LZD 2448 — LUNA: gövde Ø121,4, derinlik 36,2, krom halka Ø155,6 (versiyon 2), 2 civata 45 mm.
# Lens kenarında neon halka (pozisyon), solda düz / sağda yuvarlak "D" turuncu sinyal modülü (dikey ışık kılavuzları + LED sırası),
# D'nin çevresinde "C" dizilimli 7 fasetli kırmızı kap (stop).
# =====================================================================
@product('lzd2448', 'LZD 2448', 'stop', 'LUNA yuvarlak, krom halka')
def build_lzd2448(L):
    zb, zr = 0.0225, 0.0292
    _round_body(L, 'Chrome', zb, zr, 0.0778)
    # neon halka (lens kenarı)
    frame(L.E('position'), 'neon_ring', circle(0.0546, 56), circle(0.0476, 56), zb + 0.0028, zb + 0.0062, E('position', 'red'), 0.0012, 2)
    # kırmızı fasetli kaplar (stop)
    for deg in (130, 90, 45, 0, -45, -90, -130):
        a = math.radians(deg)
        ledq(L, 'stop', 'red', 0.0370 * math.cos(a), 0.0370 * math.sin(a), zb + 0.0062, r=0.0036, cup_r=0.0085, depth=0.0062,
             cupmat='ReflectorRed', seg=12)
    # D biçimli sinyal modülü
    Dp = [(-0.041, -0.019), (0.008, -0.019)] + [(0.008 + 0.019 * math.cos(math.radians(a)), 0.019 * math.sin(math.radians(a)))
                                                 for a in range(-75, 90, 15)] + [(0.008, 0.019), (-0.041, 0.019)]
    _uv(prism(L.inner, 'd_tray', Dp, zb - 0.001, zb + 0.0012, mat('Reflector'), 0.0), 0.006)
    _uv(frame(L.inner, 'd_rim', offset(Dp, -0.0014), Dp, zb - 0.001, zb + 0.0062, mat('Retro.amber'), 0.0004), 0.004)
    # alt yarı: eğik turuncu reflektör yüzeyi
    # alt yarı ve sağ yuvarlak uç: turuncu ışık kılavuzu yüzeyi (sinyal yanınca D bütünüyle parlar)
    low = [(-0.0395, -0.0176), (0.008, -0.0176)] + [(0.008 + 0.0176 * math.cos(math.radians(a)), 0.0176 * math.sin(math.radians(a)))
                                                    for a in range(-75, 61, 15)] + [(0.008, -0.004), (-0.0395, -0.004)]
    prism(L.E('turn'), 'd_low', low, zb + 0.0012, zb + 0.0022, E('turn', 'amber'), 0.0)
    # üstte 7 dikey ışık kılavuzu + ortada 8 LED çip (sinyal)
    for i in range(7):
        cx = -0.0355 + i * 0.0062
        prism(L.E('turn'), 'turn_fin', rrect(0.0030, 0.0105, 0.0007, 3, cx, 0.0115), zb + 0.0012, zb + 0.0050, E('turn', 'amber'))
    for i in range(8):
        chip(L, 'turn', 'amber', -0.0350 + i * 0.0058, 0.0012, zb + 0.0024)
    # lens: kırmızı (D delikli) + turuncu D
    hole = offset(Dp, -0.0006)
    _uv(holed(L.lens, 'lens_red', circle(0.0556, 56), [hole], zb + 0.0080, zb + 0.0112, mat('Lens.red'), 0.0008), 0.010)
    _uv(prism(L.lens, 'lens_amber', hole, zb + 0.0080, zb + 0.0112, mat('Lens.amber'), 0.0006), 0.008)


# =====================================================================
# CUBE — LZD 2877 (siyah çerçeve) / LZD 2880 (krom çerçeve): 115 × 138 mm, gövde 27,9, toplam 40,3 (kablo rakoru Ø15,4),
# 2 vida deliği Ø4,5 (116 mm, dikey). Füme lens; neon çerçeve çubukları (pozisyon), üst/alt kristal şevron bant (stop),
# ortada 5 yatay turuncu çubuk (sinyal). 2a R1 S1.
# =====================================================================
def _build_cube(L, bezel_mat):
    W, H, D = 0.115, 0.138, 0.0279
    # arka flanş (vida delikli) ve gövde
    flange = rrect(W - 0.004, H - 0.004, 0.013, 5)
    _uv(holed(L.body, 'flange', flange, [circle(0.00225, 16, 0.0, 0.058), circle(0.00225, 16, 0.0, -0.058)], 0.0, 0.004,
              mat('Housing'), 0.001), 0.03)
    _uv(prism(L.body, 'housing', rrect(0.103, 0.124, 0.010, 4), 0.003, 0.0150, mat('Housing'), 0.002), 0.03)
    # arka panel: çevre sırtı, havalandırma membranı
    frame(L.body, 'back_ridge', rrect(0.084, 0.100, 0.006, 3), rrect(0.080, 0.096, 0.005, 3), -0.0012, 0.0005, mat('Housing'))
    for dx, dy in ((-0.0012, -0.0012), (0.0012, -0.0012), (-0.0012, 0.0012), (0.0012, 0.0012)):
        cyl(L.body, 'vent', 0.0006, (0.036 + dx, 0.046 + dy, -0.0006), (0.036 + dx, 0.046 + dy, 0.0002), mat('ConnBlack'), 8)
    cyl(L.body, 'vent_ring', 0.0035, (0.036, 0.046, -0.0004), (0.036, 0.046, 0.0002), mat('Housing'), 16)
    # kablo rakoru Ø15,4 (12,4 mm) + yuvarlak kablo
    cyl(L.body, 'gland', 0.0077, (0.0, 0.0, 0.0), (0.0, 0.0, -0.0090), mat('ConnBlack'), 16)
    cyl(L.body, 'gland_nut', 0.0062, (0.0, 0.0, -0.0090), (0.0, 0.0, -0.0124), mat('ConnBlack'), 6, bevel=0.0005)
    conduit(L, [(0.0, 0.0, -0.011), (0.0, -0.002, -0.025), (0.015, -0.03, -0.04), (0.035, -0.07, -0.045)], 0.003, 'Cable')
    # ön çerçeve (kalın, yuvarlak kenarlı)
    win = rrect(0.086, 0.101, 0.008, 5)
    frame(L.body, 'bezel', rrect(W, H, 0.015, 5), win, 0.014, D, mat(bezel_mat), 0.0035, 3)
    # iç çerçeve basamağı (lens tutucu)
    frame(L.body, 'inner_step', win, offset(win, 0.0025), 0.016, D - 0.0035, mat('HousingGloss'), 0.0006)
    # iç taban (parlak siyah)
    prism(L.inner, 'floor', offset(win, 0.002), 0.015, 0.0178, mat('HousingGloss'), 0.0)
    zg0, zg1 = 0.0178, 0.0212
    # pozisyon ışık kılavuzları: üst/alt iki stadyum, yanlarda iki dikey çubuk
    pos = E('position', 'red')
    for sy in (1, -1):
        prism(L.E('position'), 'pos_tb_o', stadium(0.054, 0.0038, 4, 0.0, sy * 0.0447), zg0, zg1, pos, 0.0007, 2)
        prism(L.E('position'), 'pos_tb_i', stadium(0.044, 0.0030, 4, 0.0, sy * 0.0384), zg0, zg1, pos, 0.0007, 2)
    for sx in (1, -1):
        prism(L.E('position'), 'pos_s_o', rrect(0.0038, 0.069, 0.0019, 4, sx * 0.0375, 0.0), zg0, zg1, pos, 0.0007, 2)
        prism(L.E('position'), 'pos_s_i', rrect(0.0030, 0.060, 0.0015, 4, sx * 0.0320, 0.0), zg0, zg1, pos, 0.0007, 2)
    # stop: kristal şevron bantlar (üst/alt) + bant arkasında krom şerit ve LED çipleri
    for sy in (1, -1):
        band = [(-0.0350, sy * 0.0428), (-0.0236, sy * 0.0300), (0.0236, sy * 0.0300), (0.0350, sy * 0.0428)]
        ribbon(L.inner, 'stop_back', band, 0.0060, zg0 + 0.0002, mat('Chrome'), 0.0004)
        ribbon(L.E('stop'), 'stop_band', band, 0.0046, zg0 + 0.0022, E('stop', 'red'), 0.0026)
        for i in range(9):
            chip(L, 'stop', 'red', -0.020 + i * 0.005, sy * 0.0300, zg0 + 0.0004, 0.0018, 0.0014, 0.0006)
        for sx in (1, -1):
            for t in (0.3, 0.7):
                chip(L, 'stop', 'red', sx * (0.0236 + t * 0.0114), sy * (0.0300 + t * 0.0128), zg0 + 0.0004, 0.0018, 0.0014, 0.0006)
        # kristal (fasetli şeffaf) ışık kılavuzu kapağı
        _uv(ribbon(L.lens, 'stop_crystal', band, 0.0050, zg0 + 0.0042, mat('Lens.clear'), 0.0010), 0.0025)
    # sinyal: 5 yatay çubuk + uç kapakları
    for k in range(-2, 3):
        y = 0.0015 + k * 0.0082
        prism(L.E('turn'), 'turn_bar', rrect(0.0370, 0.0052, 0.0008, 2, 0.0, y), zg0, zg1 + 0.0004, E('turn', 'amber'), 0.0006, 2)
        for sx in (1, -1):
            box(L.inner, 'bar_cap', sx * 0.0185 - 0.0015, sx * 0.0185 + 0.0015, y - 0.0030, y + 0.0030, zg0, zg1 + 0.0002, mat('HousingGloss'))
    # füme lens
    _uv(prism(L.lens, 'lens', offset(win, 0.0024), D - 0.0060, D - 0.0034, mat('Lens.smoke'), 0.0008), 0.008)


@product('lzd2877', 'LZD 2877', 'stop', 'CUBE siyah çerçeve')
def build_lzd2877(L):
    _build_cube(L, 'HousingGloss')


@product('lzd2880', 'LZD 2880', 'stop', 'CUBE krom çerçeve')
def build_lzd2880(L):
    _build_cube(L, 'Chrome')
