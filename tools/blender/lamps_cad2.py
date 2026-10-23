# Üretici CAD verisinden arka lambalar, ikinci paket (STEP'ler 2026-10-22: Downloads/Product-3D-Step-Files/3d-model-ek-urunler).
# lamps.py içine lamps_cad.py'den SONRA exec edilir: lamps.py ve lamps_cad.py'nin yardımcıları (prism, frame, _stl, _cad_parts,
# _plate_parts, _band, _inside, _emat, _glow, _retro_cad, _refl, _cup_bands …) ve lamps_small.py'nin _s_hex_retro'su kullanılır.
#
# Dört üründe de STEP yalnız dış zarf: gövde, lens (iç desensiz düz kabuk), saplamalar / çerçeveler. İç optik (ışık kılavuzları,
# LED optikleri, reflektörler) YOK: ürün paketlerindeki önden çekilmiş fotoğraflardan ölçüldü (lens kenarı ölçek, ±1 mm).
# Işık şiddeti (LZD 3194 ile aynı ilke, kullanıcı 2026-10-23: "ışık şeritleri birbirine karışıyor"): sitede ışıma = işlev çarpanı
# (lampfx.ts FN_I: pozisyon 1,45, fren 2,7, sinyal / sis 2,6, geri vites 3,0) × malzeme oranı (.g); bloom eşiği 1,05. Büyük yüzeyler
# (kılavuz gövdeleri, kristal yüzeyin LED'den uzak hücreleri, yansıtıcılar) eşiğin altında kalır: biçimleri okunur, birbirine
# karışmaz; haleyi yalnız LED noktaları ve LED'in hemen önündeki hücreler verir.
# Yerel eksen (site sözleşmesi, LZD 3194 ile aynı): X genişlik (dış uç −X: sol lambada sinyal tarafı), Y yukarı, Z lens yönü,
# arka montaj yüzü Z = 0. Blender'da (x, −z, y).
import os


def _m(pts):
    return [(x / 1000, y / 1000) for x, y in pts]


def _z(v):
    return v / 1000


def _mirror_red(p, base_hex='#a8111a'):
    """Retro reflektör renkli ayna gibi yansıtır: metalik kırmızı, kaplamasız (kaplama gökyüzünü beyaz yansıtıp kırmızıyla
    karışınca yüzey pembe okunuyordu, kullanıcı 2026-10-23)"""
    p.inputs['Base Color'].default_value = srgb(base_hex)
    p.inputs['Metallic'].default_value = 0.75
    p.inputs['Roughness'].default_value = 0.35
    p.inputs['Coat Weight'].default_value = 0.0


def _crystal(fn, color, gain, base_hex):
    """Kristal (köşe küp / piramit) LED optiği: _s_hex_retro geometrisinin malzemesi. Sönükken base_hex renginde parlak kaplamalı,
    yanınca işlevin renginde gain oranında ışır. Ad E.<işlev>.<renk>.g<yüzde>.x<renk kodu> (site ilk dört alanı okur)."""
    key = f'E.{fn}.{color}.g{int(round(gain * 100))}.x{base_hex.lstrip("#")}'
    if key not in MATS:
        m = mat('Retro.white').copy()
        m.name = key
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.type in ('NORMAL_MAP', 'TEX_IMAGE')]:
            nt.nodes.remove(n)
        p = nt.nodes['Principled BSDF']
        p.inputs['Base Color'].default_value = srgb(base_hex)
        rr, gg = int(base_hex[1:3], 16), int(base_hex[3:5], 16)
        if rr > 1.6 * gg:
            _mirror_red(p, base_hex)  # kırmızı kristal (HORUS fren / sis): renkli ayna
        p.inputs['Emission Color'].default_value = (*GLOW[color], 1.0)
        p.inputs['Emission Strength'].default_value = 0.0
        m.use_backface_culling = False
        m['fn'] = fn
        m['gain'] = gain
        MATS[key] = m
    return MATS[key]


def _retro_plain(color):
    """Işımayan retro reflektör (üçgen): kütüphanedeki Retro.<renk> dokusuz (hücreler geometri)"""
    key = f'Retro.{color}.cad'
    if key not in MATS:
        m = mat(f'Retro.{color}').copy()
        m.name = key
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.type in ('NORMAL_MAP', 'TEX_IMAGE')]:
            nt.nodes.remove(n)
        # fotoğraflarda koyu kırmızı (kütüphanedeki açık retro kırmızısı renksiz lensin ardında pembe okunuyordu)
        p = nt.nodes['Principled BSDF']
        if color == 'red':
            _mirror_red(p)
        m.use_backface_culling = False
        MATS[key] = m
    return MATS[key]


def _retro_dark(fn, color, gain):
    """Arkasında LED olan retro (STRADA yan panelleri): dokusuz retro (hücreler geometri), koyu kırmızı (renksiz lensin ardında),
    yanınca gain oranında ışır. Kendi adıyla kurulur: _retro_cad / _glow ile aynı ad (E.<işlev>.<renk>.g<yüzde>) önbellekte başka
    ürünün malzemesini döndürüyordu (CUBE'un gri fren gövdesi STRADA retrosuna geçti)"""
    key = f'E.{fn}.{color}.g{int(round(gain * 100))}.d'
    if key not in MATS:
        m = mat(f'Retro.{color}').copy()
        m.name = key
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.type in ('NORMAL_MAP', 'TEX_IMAGE')]:
            nt.nodes.remove(n)
        p = nt.nodes['Principled BSDF']
        _mirror_red(p)
        p.inputs['Emission Color'].default_value = (*GLOW[color], 1.0)
        p.inputs['Emission Strength'].default_value = 0.0
        m.use_backface_culling = False
        m['fn'] = fn
        m['gain'] = gain
        MATS[key] = m
    return MATS[key]


def _gl(fn, color, off_hex, gain):
    """_glow'un bu dosyaya özel adlısı (E.<işlev>.<renk>.g<yüzde>.c2): ad çakışmasında önbellek başka ürünün malzemesini vermesin"""
    m = _emat(fn, color, off_hex, f'g{int(round(gain * 100))}.c2')
    m['gain'] = gain
    return m


def _lens_rib(color):
    """Dikey kaburgalı şeffaf optik (HORUS altıgenleri; fotoğraf: kaburgaların ardında krom kap ve LED). Lens.<renk>.cad.rib"""
    key = f'Lens.{color}.cad.rib'
    if key not in MATS:
        m = mat(f'Lens.{color}').copy()
        m.name = key
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.image = tex('rib')
            if n.type == 'NORMAL_MAP':
                n.inputs['Strength'].default_value = 0.9
        p = m.node_tree.nodes['Principled BSDF']
        p.inputs['Alpha'].default_value = {'clear': 0.22, 'amber': 0.5}.get(color, 0.4)
        MATS[key] = m
    return MATS[key]


def _lmat_flat(color):
    """Lens.<renk>.cad.flat: optik dokusuz düz şeffaf pencere"""
    key = f'Lens.{color}.cad.flat'
    if key not in MATS:
        m = mat(f'Lens.{color}').copy()
        m.name = key
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.type in ('NORMAL_MAP', 'TEX_IMAGE')]:
            nt.nodes.remove(n)
        MATS[key] = m
    return MATS[key]


def _frame_poly(group, name, outer, hole, z0, z1, material):
    """Delikli düz levha (dış ve iç çokgen nokta sayısı farklı olabilir): ön ve arka yüz üçgenlenir (CDT), kenarlar duvar"""
    bm = bmesh.new()
    for z in (z0, z1):
        vo = [bm.verts.new(bl((x / 1000, y / 1000, z))) for x, y in outer]
        vi = [bm.verts.new(bl((x / 1000, y / 1000, z))) for x, y in hole]
        cut = delaunay_2d_cdt([Vector(p) for p in outer + hole], [(i, (i + 1) % len(outer)) for i in range(len(outer))] +
                              [(len(outer) + i, len(outer) + (i + 1) % len(hole)) for i in range(len(hole))], [], 2, 1e-6, True)
        vs = vo + vi
        for f in cut[2]:
            c = sum((Vector(cut[0][k]) for k in f), Vector((0, 0))) / len(f)
            if _inside(outer, c.x, c.y) and not _inside(hole, c.x, c.y):
                try:
                    bm.faces.new([vs[cut[3][k][0]] for k in f])
                except ValueError:
                    pass
    n = len(outer) + len(hole)
    bm.verts.ensure_lookup_table()
    for ring, off in ((outer, 0), (hole, len(outer))):
        for i in range(len(ring)):
            j = (i + 1) % len(ring)
            bm.faces.new([bm.verts[off + i], bm.verts[off + j], bm.verts[n + off + j], bm.verts[n + off + i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, material, group, 0.0)


def _lmat_alpha(color, alpha, tag):
    """Lens.<renk>.cad.<etiket>: aynı renkte daha açık / koyu füme (site üçüncü alanı 'cad' okur: lens az parlar)"""
    key = f'Lens.{color}.cad.{tag}'
    if key not in MATS:
        m = mat(f'Lens.{color}').copy()
        m.name = key
        m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = alpha
        MATS[key] = m
    return MATS[key]


def _round_poly(pts, r, n=4):
    """Kapalı dışbükey çokgenin köşelerini r yarıçapıyla yuvarlar (her köşe n+1 nokta; aynı n ile benzer çokgenler eşleşir)"""
    out = []
    k = len(pts)
    for i in range(k):
        p, a, b = Vector((*pts[i], 0)), Vector((*pts[i - 1], 0)), Vector((*pts[(i + 1) % k], 0))
        u, w = (a - p).normalized(), (b - p).normalized()
        ang = math.acos(max(-1.0, min(1.0, u.dot(w))))
        d = r / math.tan(ang / 2)
        c = p + (u + w).normalized() * (r / math.sin(ang / 2))
        p0, p1 = p + u * d, p + w * d
        a0, a1 = math.atan2(p0.y - c.y, p0.x - c.x), math.atan2(p1.y - c.y, p1.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(c.x + r * math.cos(a0 + da * j / n), c.y + r * math.sin(a0 + da * j / n)) for j in range(n + 1)]
    return _s_ccw(out)


def _hexf(cx, cy, a):
    """Düz üst / alt kenarlı altıgen (sivri uçlar yanlarda), köşe yarıçapı a"""
    return [(cx + a * math.cos(math.pi / 3 * k), cy + a * math.sin(math.pi / 3 * k)) for k in range(6)]


def _ehex(cx, cy, w, h, p):
    """Yatay uzun altıgen (uçlar sivri, p uç derinliği)"""
    return [(cx - w / 2, cy), (cx - w / 2 + p, cy - h / 2), (cx + w / 2 - p, cy - h / 2), (cx + w / 2, cy), (cx + w / 2 - p, cy + h / 2),
            (cx - w / 2 + p, cy + h / 2)]


def _slot(group, poly, z0, z1, w=0.9):
    """Işık elemanının çevresinde koyu yuva duvarı (ışık sızmasın; fotoğraflarda her eleman siyah çerçeve içinde)"""
    frame(group, 'slot', _m(offset(poly, -w)), _m(poly), _z(z0), _z(z1), mat('HousingGloss'), 0.0)


def _polyline_pts(pl, step):
    """Çoklu çizgi boyunca step aralıklı noktalar (LED yerleri)"""
    out = []
    for (ax, ay), (bx, by) in zip(pl, pl[1:]):
        ln = math.hypot(bx - ax, by - ay)
        k = max(1, int(round(ln / step)))
        for i in range(k):
            t = (i + 0.5) / k
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    return out


def _banded(group, name, region, holes, z, cell, depth, leds, mat_of, bands=((0.0, 2.6, 0.95), (2.6, 5.0, 0.68), (5.0, 8.0, 0.46), (8.0, 1e9, 0.3))):
    """LED'in ardında ışıyan kristal / retro yüzey: hücreler LED'e uzaklığa göre bantlara ayrılır (LZD 2854 fren yaklaşımı);
    mat_of(gain) bandın malzemesi. Yerel mm girdi."""
    dmin = lambda x, y: min(math.hypot(x * 1000 - a, y * 1000 - b) for a, b in leds) if leds else 1e9
    for lo, hi, g in bands:
        _s_hex_retro(group, name, _m(region), [_m(h) for h in holes], _z(z), cell / 1000, depth / 1000, mat_of(g),
                     keep=lambda x, y, lo=lo, hi=hi: lo <= dmin(x, y) < hi)


def _cad_lens(L, cad, M, nm, mats_, name, dec, region_of=None):
    """CAD lensi: yalnız önden görünen yüzler (arka yüz çizilince renk iki kat koyulaşıyor); region_of(x, y, z) malzeme indeksi"""
    b = _stl(os.path.join(cad, nm + '.stl'), M)
    _simplify(b, 0.4)
    ex = _front_faces(b)
    sb = _subset(b, lambda f: ex[f.index])
    b.free()
    if region_of:
        for f in sb.faces:
            f.material_index = region_of(*_three(f.calc_center_median()))
    _mesh_obj(name, sb, mats_, L.lens, 40, decimate=None if FAST else dec)


# =====================================================================
# CUBE — LZD 2875/GRAPHITE (HOR 164AY: neon pozisyon, fren, neon sinyal; 98 LED) ve LZD 2876 (HOR 164: sis, geri vites; 31 LED).
# İkisi de "universal" (sol / sağ aynı), yalnız dikey takılır. Föy: LZD 2875 yalnız ÜÇLÜ set olarak onaylı (kategori Y, ardışık
# sinyal). Kaynaklar: üretici STEP "LZD 2875_GRAPHITE" / "LZD 2876" (ortak gövde 734F1, ön çerçeve "osłona" 731F1, arka aralayıcı
# 732F1; lensler 733F3 / 733F2), ürün paketleri (Downloads/LZD-2875GRAPHITE.zip, LZD-2876.zip: föy, çizim HOR 164AY / 164B, 17 + 13
# fotoğraf). STEP'te: p000 lens, p001 gövde, p002 ön çerçeve, p003 aralayıcı. Ölçü 115 × 138 (çerçeve), derinlik 27,9 + kablo
# rakoru Ø15,4; alt ve üst ortada Ø4,5 vida deliği.
#   İç düzen (fotoğraflar 3, 9, 13 / 3-1, 4-1; ölçek çerçeve genişliği 115 mm): kenarlarda 8 ışık kılavuzu çubuğu (üstte ve altta
#   iki yatay, yanlarda iki dikey), ortada 5 yatay şerit (6 LED), 2875'te üst ve alttaki çubukların arasında "gülümseme" biçimli
#   kristal fren şeritleri. 2875: çubuklar neon POZİSYON, şeritler SİNYAL, gülümsemeler FREN. 2876: çubuklar kristal GERİ VİTES,
#   şeritler kristal SİS. 2875 lensi koyu füme (GRAPHITE), 2876 hafif füme.
# CAD ekseni (mm): lens +x, genişlik y, yukarı z (doğrulanmadı: lamba simetrik), arka aralayıcının arka yüzü x 0. Yerel: X = y,
# Y = z, Z = x.
# =====================================================================
CUBE_M = Matrix(((0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
CUBE_BARS = [(0.0, 44.3, 53.2, 4.4), (0.0, 38.6, 43.2, 3.8), (0.0, -44.3, 53.2, 4.4), (0.0, -38.6, 43.2, 3.8),
             (-36.9, 0.0, 4.7, 68.0), (-30.7, 0.0, 4.2, 58.0), (36.9, 0.0, 4.7, 68.0), (30.7, 0.0, 4.2, 58.0)]
CUBE_ROWS = [18.7, 10.1, 1.5, -7.1, -15.7]
CUBE_SMILE = [(-33.5, 40.8), (-22.8, 31.9), (22.8, 31.9), (33.5, 40.8)]
CUBE_SCREW_Y = 64.0


def _cube(L, var):
    cad = os.path.join(CAD_ROOT, 'lzd' + var)
    if not os.path.exists(os.path.join(cad, 'p003.stl')):
        print('CAD YOK (CUBE yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    g2875 = var == '2875'

    # ===== 1) CAD: gövde, ön çerçeve (parlak siyah), aralayıcı; lens =====
    parts = _cad_parts(cad, CUBE_M, ['p001', 'p002', 'p003'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p001': ([mat('Housing')], L.body, 9000), 'p002': ([mat('HousingGloss')], L.body, 5000),
                                 'p003': ([mat('Housing')], L.body, 2500)}, 'cube')
    lens = _lmat('smoke') if g2875 else _lmat_alpha('smoke', 0.38, 'l38')
    _cad_lens(L, cad, CUBE_M, 'p000', [lens], 'cube_lens', 6000)

    # ===== 2) iç taban (lensin iç yüzü Z 20,5; gövde tabanı Z 12) =====
    ZF = 12.2
    prism(L.inner, 'cube_floor', _m(rrect(88.0, 102.0, 8.0)), _z(11.4), _z(ZF), mat('HousingGloss'), 0.0)

    # ===== 3) kenar çubukları: 2875 neon pozisyon (pürüzsüz kılavuz), 2876 kristal geri vites (LED'ler ~5 mm arayla) =====
    for i, (cx, cy, w, h) in enumerate(CUBE_BARS):
        poly = rrect(w, h, min(w, h) / 2, 4, cx, cy)
        _slot(L.inner, poly, ZF, 18.9)
        if g2875:
            # neon kılavuz: 1,45 × 0,85 (eşiğin hemen üstü): yumuşak hale, iç ve dış çubuk ayrı okunur
            prism(L.E('position'), f'neon{i}', _m(offset(poly, 0.15)), _z(ZF), _z(19.3), _gl('position', 'red', '#cdbfbc', 0.85), 0.0008)
        else:
            # gövde eşiğin altında (3,0 × 0,15), kristalde yalnız LED'in önündeki hücreler parlak (fotoğraf 4-1: çubuk boyunca LED
            # noktaları, aralarında sönük beyaz)
            prism(L.E('reverse'), f'rev_bar{i}', _m(poly), _z(ZF), _z(17.8), _gl('reverse', 'white', '#d2d4d8', 0.15), 0.0)
            ax = [(cx - w / 2 + 1.0, cy), (cx + w / 2 - 1.0, cy)] if w > h else [(cx, cy - h / 2 + 1.0), (cx, cy + h / 2 - 1.0)]
            _banded(L.E('reverse'), f'rev_xtal{i}', poly, [], 19.2, 1.7, 0.7, _polyline_pts(ax, 5.0),
                    lambda g: _crystal('reverse', 'white', g, '#e4e6ea'), ((0.0, 1.5, 0.8), (1.5, 2.8, 0.3), (2.8, 1e9, 0.16)))

    # ===== 4) orta şeritler: 2875 sinyal (buzlu kılavuz + 6 LED noktası), 2876 sis (kristal blok, 5 LED) =====
    led_core = _emat('turn', 'amber', '#b2aca3', 'cubeled')
    for i, cy in enumerate(CUBE_ROWS):
        poly = rrect(39.0, 6.0, 1.4, 4, 0.0, cy)
        _slot(L.inner, poly, ZF, 18.6)
        if g2875:
            prism(L.E('turn'), f'turn{i}', _m(poly), _z(ZF), _z(18.6), _gl('turn', 'amber', '#a9a39b', 0.5), 0.0005)
            for k in range(6):
                x = -16.25 + 6.5 * k
                cyl(L.E('turn'), 'turn_led', 0.0013, (_z(x), _z(cy), _z(18.55)), (_z(x), _z(cy), _z(18.75)), led_core, 12)
        else:
            prism(L.E('fog'), f'fog{i}', _m(poly), _z(ZF), _z(17.6), _gl('fog', 'red', '#8e898b', 0.15), 0.0)
            leds = [(-16.0 + 8.0 * k, cy) for k in range(5)]
            _banded(L.E('fog'), f'fog_xtal{i}', poly, [], 19.0, 1.5, 0.6, leds, lambda g: _crystal('fog', 'red', g, '#c9c3c5'),
                    ((0.0, 1.8, 0.85), (1.8, 3.5, 0.38), (3.5, 1e9, 0.18)))

    # ===== 5) 2875: üst ve alt "gülümseme" fren şeritleri (kristal; LED'ler 4 mm arayla) =====
    if g2875:
        for sy, nm in ((1, 'smile_t'), (-1, 'smile_b')):
            pl = [(x, sy * y) for x, y in CUBE_SMILE]
            band = _s_ccw(_band(pl, 5.0))
            _slot(L.inner, band, ZF, 18.4)
            prism(L.E('stop'), nm, _m(band), _z(ZF), _z(17.8), _gl('stop', 'red', '#9d9799', 0.2), 0.0)
            _banded(L.E('stop'), nm + '_xtal', band, [], 19.0, 1.5, 0.6, _polyline_pts(pl, 4.0),
                    lambda g: _crystal('stop', 'red', g, '#cfc9cb'), ((0.0, 1.6, 0.85), (1.6, 3.0, 0.4), (3.0, 1e9, 0.2)))

    # ===== 6) montaj: ön çerçevenin üst ve alt ortasındaki vidalar (Ø4,5 delik; aralayıcı ve tamponun webinden geçer) =====
    for sy in (1, -1):
        y = sy * CUBE_SCREW_Y
        cyl(L.body, 'screw_head', 0.0036, (0.0, _z(y), _z(25.5)), (0.0, _z(y), _z(27.2)), mat('Stainless'), 20, bevel=0.0006)
        cyl(L.body, 'screw', 0.0020, (0.0, _z(y), _z(25.5)), (0.0, _z(y), _z(-14.0)), mat('Stainless'), 12)
    # kablo: arka rakordan (5 × 0,5 / 3 × 0,5, 1 m; sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, 0.0, -0.010), (0.0, 0.0, -0.022), (0.0, -0.010, -0.034)], 0.0033, mat('Cable'), 3, smooth=True)


@product('lzd2875', 'LZD 2875/GRAPHITE', 'stop', 'CUBE (universal), HOR 164AY: neon pozisyon, fren, neon sinyal; üçlü set — üretici CAD + fotoğraflar')
def build_lzd2875_cad(L):
    return _cube(L, '2875')


@product('lzd2876', 'LZD 2876', 'stop', 'CUBE (universal), HOR 164: sis, geri vites — üretici CAD + fotoğraflar')
def build_lzd2876_cad(L):
    return _cube(L, '2876')


# =====================================================================
# STRADA — LZD 2820 (sol; sağ: LZD 2821, ayna), HOR 124, 71 LED. Föy: neon pozisyon, fren, geri vites, sis, sinyal, reflektör
# üçgen (föyde plaka aydınlatması da geçiyor; kullanıcı 2026-10-23: LZD 2820'de yok, modelde yok); 7 × 0,5 kablo 2 m. Kaynaklar: üretici STEP "LZD 2820, 2821" (gövde 548F1, lens 549F1, 2 saplama),
# ürün paketi (Downloads/LZD-2820.zip: föy, çizim, 15 fotoğraf). Ölçü 240 × 141 × 49,6 (saplamalar hariç), saplamalar ±76 mm.
#   İç düzen (önden fotoğraf 2-1; ölçek lens 239,6 mm): ortada büyük kırmızı retro üçgen ("yol"), kenarlarında neon "yol
#   çizgileri" (üstte iki eğik çizgi, altta dışa ayaklı iki eğik çizgi, ortada kesik orta çizgi) POZİSYON; ortada boydan boya
#   turuncu SİNYAL çubuğu; üstte iki beyaz pencere (3'er LED, krom kap) GERİ VİTES; yanlarda ">" biçimli kırmızı retro paneller,
#   arkalarında panelin orta çizgisine dizili 10 LED (fotoğraf 5-1): iç uçta FREN, dış uçta SİS (kullanıcı 2026-10-23). Panelin
#   dış kenarında siyah "bumerang" (gövde; ışımaz).
#   Biçimler fotoğraf 2-1'in piksel satırlarından ölçüldü (2026-10-23): üçgen kenarı eğimi 0,555 (tepe lensin üstünde, taban ±76,9),
#   neon şeritlerin iç kenarı üçgene 3 mm aralıkla PARALEL, dış kenarı daha dik (şerit aşağı doğru genişler).
# CAD ekseni (mm): x genişlik (sağ +x, önden), y yukarı (0 … 140,8), lens +z, arka yüz z −7. Yerel: X = x, Y = y − 70,4, Z = z + 7.
# =====================================================================
STRADA_M = Matrix(((1, 0, 0, 0), (0, 0, -1, -0.007), (0, 1, 0, -0.0704), (0, 0, 0, 1)))


@product('lzd2820', 'LZD 2820', 'stop', 'STRADA sol (sağ: LZD 2821, ayna), HOR 124, 71 LED — üretici CAD + fotoğraflar')
def build_lzd2820_cad(L):
    cad = os.path.join(CAD_ROOT, 'lzd2820')
    if not os.path.exists(os.path.join(cad, 'p003.stl')):
        print('CAD YOK (LZD 2820 yalnız CAD verisinden kurulur):', cad)
        return 'skip'

    # ===== 1) CAD: gövde, saplamalar (çinko), lens (renksiz) =====
    parts = _cad_parts(cad, STRADA_M, ['p000', 'p001', 'p002'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p002': ([mat('Housing')], L.body, 9000), 'p000': ([mat('Zinc')], L.body, 300),
                                 'p001': ([mat('Zinc')], L.body, 300)}, 'strada')
    _cad_lens(L, cad, STRADA_M, 'p003', [_lmat('clear')], 'strada_lens', 6000)

    # ===== 2) iç panel (lensin iç yüzü Z 47,5) =====
    ZP = 30.5
    prism(L.inner, 'strada_panel', _m(rrect(229.0, 131.0, 8.0)), _z(29.5), _z(ZP), mat('HousingGloss'), 0.0)

    # ===== 3) ölçülen biçimler (yerel mm) =====
    mx = lambda pl: [(-x, y) for x, y in pl]
    # orta üçgen: sol kenar x = 0,555·y − 40,78 (tepe y 73,5 lensin üstünde: yamuk), taban y −65
    tri_x = lambda y: 0.555 * y - 40.78
    TRI = _round_poly([(tri_x(63.8), 63.8), (-tri_x(63.8), 63.8), (-tri_x(-65.0), -65.0), (tri_x(-65.0), -65.0)], 2.5)
    # neon şeritler (sol yarı): iç kenar üçgene paralel (3 mm), dış kenar daha dik; üstteki sinyal çubuğunun üstünde biter, alttaki
    # dışa ayakla lens kenarına uzanır
    up_in = lambda y: tri_x(y) - 3.0
    up_out = lambda y: -17.9 - 0.702 * (59.6 - y)
    lo_in = lambda y: tri_x(y) - 3.2
    lo_out = lambda y: -68.7 - 0.694 * (-12.4 - y)
    NEON = [[(up_out(63.5), 63.5), (up_in(63.5), 63.5), (up_in(8.0), 8.0), (up_out(8.0), 8.0)],
            [(lo_out(-8.5), -8.5), (lo_in(-8.5), -8.5), (lo_in(-64.0), -64.0), (-114.0, -64.0), (-114.0, -52.0), (lo_out(-52.0), -52.0)]]
    NEON = [_s_ccw(p) for p in NEON] + [_s_ccw(mx(p)) for p in NEON]
    CENTER = [[(0.0, 32.5), (0.0, 8.0)], [(0.0, -9.0), (0.0, -56.0)]]
    BAR = rrect(143.0, 8.8, 1.5, 4, 0.0, -0.8)
    # geri vites penceresi: sağ kenar üçgene paralel, sol kenar şeridin dış kenarına paralel, sol üst köşe pahlı
    WIN = [(-98.8, 63.0), (-25.9, 63.0), (-53.4, 14.5), (-70.8, 14.5), (-98.3, 54.0)]
    WIN_LED = [(-79.5, 51.0), (-45.5, 51.0), (-62.0, 30.5)]
    # yan panel ">" biçimi: iç kenar pencereye ve alt şeride ~4 mm aralıkla paralel; dış kenarda siyah bumerang (y ±37,5 … ±22,5
    # arası eğik, ortada x −104,2'ye kadar içe girer)
    PANEL = [(-114.0, 50.0), (-99.3, 50.0), (-74.6, 14.5), (-74.6, -15.0), (-98.9, -50.0), (-114.0, -50.0), (-114.0, -38.7),
             (-104.2, -25.0), (-104.2, 22.5), (-114.0, 37.5)]
    # LED'ler panelin orta çizgisinde (fotoğraf 5-1: ">" dizili 10 LED)
    PANEL_LED = _polyline_pts([(-106.5, 45.0), (-97.0, 30.0), (-89.4, 12.0), (-89.4, -12.0), (-96.4, -30.0), (-106.0, -45.0)], 10.0)

    # ===== 4) retro üçgen (ışımaz): orta çizgi ve sinyal çubuğu delerek geçer =====
    neon_c = [_s_ccw(_band(p, 8.4)) for p in CENTER]
    holes = [offset(p, -1.0) for p in neon_c] + [offset(BAR, -1.0)]
    prism(L.inner, 'tri_base', _m(TRI), _z(ZP), _z(43.8), mat('ReflectorRed'), 0.0)
    _s_hex_retro(L.inner, 'tri_retro', _m(TRI), [_m(h) for h in holes], _z(44.6), 0.0021, 0.0008, _retro_plain('red'))

    # ===== 5) neon yol çizgileri (pozisyon): koyu yuvada süt beyazı kılavuz, retronun 1 mm önünde =====
    # sönükken kırmızı ışık borusu (fotoğraf 2-1; renksiz lensin ardında soluk pembe okunmasın)
    neon_m = _emat('position', 'red', '#b8302c', 'strada')
    for i, band in enumerate(NEON):
        _slot(L.inner, band, ZP, 45.0)
        prism(L.E('position'), f'neon{i}', _m(band), _z(ZP), _z(45.6), neon_m, 0.0008)
    for i, band in enumerate(neon_c):
        _slot(L.inner, band, ZP, 45.0)
        prism(L.E('position'), f'neon_c{i}', _m(band), _z(ZP), _z(45.6), neon_m, 0.0008)

    # ===== 6) sinyal çubuğu =====
    _slot(L.inner, BAR, ZP, 45.0)
    # kılavuz 2,6 × 0,55 (turuncu kalır, beyaza doymaz) + önünde 13 LED noktası (fotoğraf 2-1: çubuk boyunca LED izleri)
    prism(L.E('turn'), 'turn_bar', _m(BAR), _z(ZP), _z(45.6), _gl('turn', 'amber', '#e8963a', 0.55), 0.0008)
    for k in range(13):
        x = -66.0 + 11.0 * k
        cyl(L.E('turn'), 'turn_led', 0.0011, (_z(x), _z(-0.8), _z(45.55)), (_z(x), _z(-0.8), _z(45.75)), _emat('turn', 'amber', '#f1b766', 'strled'), 12)

    # ===== 7) geri vites pencereleri: krom yuva, 3 krom kap + LED (LZD 3194 geri vites yaklaşımı) =====
    for sx in (1, -1):
        poly = WIN if sx > 0 else _s_ccw(mx(WIN))
        leds = WIN_LED if sx > 0 else mx(WIN_LED)
        prism(L.E('reverse'), 'rev_bay', _m(offset(poly, 1.0)), _z(ZP), _z(ZP + 1.5), _refl('reverse', 'white', 0.13), 0.0)
        frame(L.inner, 'rev_frame', _m(poly), _m(offset(poly, 1.4)), _z(ZP), _z(45.0), mat('HousingGloss'), 0.0)
        for lx, ly in leds:
            _cup_bands(L.E('reverse'), _z(lx), _z(ly), _z(44.0), 0.0088, 0.0036, _z(44.0 - ZP - 1.5), (0.33, 0.26, 0.19), 'reverse', 'white')
            box(L.E('reverse'), 'rev_led', _z(lx - 2.6), _z(lx + 2.6), _z(ly - 2.6), _z(ly + 2.6), _z(ZP + 1.6), _z(ZP + 3.0), E('reverse', 'white'))

    # ===== 8) yan paneller: ">" biçimli kırmızı retro, ardında 10 LED (iç uç FREN, dış uç SİS; kullanıcı 2026-10-23) =====
    for sx, fn in ((1, 'fog'), (-1, 'stop')):  # sx 1: dış (−X) panel
        poly = _s_ccw(PANEL) if sx > 0 else _s_ccw(mx(PANEL))
        leds = PANEL_LED if sx > 0 else mx(PANEL_LED)
        frame(L.inner, 'panel_frame', _m(poly), _m(offset(poly, 1.0)), _z(ZP), _z(44.8), mat('HousingGloss'), 0.0)
        prism(L.inner, 'panel_base', _m(offset(poly, 0.8)), _z(ZP), _z(43.8), mat('ReflectorRed'), 0.0)
        # yalnız LED'lerin önündeki hücreler parlak (fotoğraf 5 / 6: LED dizisi seçik, panelin geri kalanı koyu kırmızı)
        _banded(L.E(fn), f'panel_{fn}', offset(poly, 1.0), [], 44.6, 2.1, 0.8, leds, lambda g, fn=fn: _retro_dark(fn, 'red', g),
                ((0.0, 2.4, 0.95), (2.4, 4.5, 0.45), (4.5, 7.0, 0.2), (7.0, 1e9, 0.07)))

    # ===== 9) ön vidalar (panelde) ve kablo =====
    for x, y in ((-109.5, 58.4), (-63.0, 8.8), (63.0, 8.8), (109.5, 58.4)):
        cyl(L.inner, 'screw', 0.0028, (_z(x), _z(y), _z(ZP)), (_z(x), _z(y), _z(ZP + 2.2)), mat('HousingGloss'), 16, bevel=0.0005)
    tube(L.body, 'cable', [(0.0, 0.0, -0.002), (0.0, 0.0, -0.016), (0.0, -0.010, -0.028)], 0.0036, mat('Cable'), 3, smooth=True)


# =====================================================================
# HORUS — LZD 3223 (sol; HOR 153A, 6 işlev, plaka aydınlatmasız), 42 LED, 12 V (föy). STEP'in içindeki ürün LZD 3215 (aynı aile,
# HOR 153; 3215'te ek olarak plaka aydınlatması var, kullanıcı ürün sayfasından doğruladı 2026-10-23): gövde ve lens aynı.
# Kaynaklar: üretici STEP "LZD 3223" (gövde 695F1, lens 694F1, 2 × M6 saplama ±76 mm), ürün paketi (Downloads/LZD-3223.zip: föy,
# çizim HOR 153A, 10 fotoğraf). Ölçü 200 × 140 × 51.
#   İç düzen (önden fotoğraf 3-1; ölçek lens 200 mm, kırpılmış ayrıntı): siyah parlak iç panel, 4 vida; ortada katmanlı retro üçgen
#   (dış bant ve en içteki küçük üçgen önde, aradaki bant geride; sınırlarında çift ince parlak sırt); üst köşelerde uzun altıgen
#   neon POZİSYON modülleri (9 + 9); yanlarda altıgen LED optikleri: solda 6 turuncu SİNYAL (dikey kaburgalı) + 6 kırmızı FREN
#   (piramit desen), sağda 6 beyaz GERİ VİTES + 6 kırmızı SİS (fotoğraflar 0, 2, 8, 9, 10: işlev başına ayrı yanan hücreler).
# CAD ekseni (mm): x genişlik, lens +y, aşağı +z (lensteki üçgen CAD'de ters), arka çerçeve y −23. Yerel: X = x, Y = −z, Z = y + 23.
# =====================================================================
HORUS_M = Matrix(((1, 0, 0, 0), (0, -1, 0, -0.023), (0, 0, -1, 0), (0, 0, 0, 1)))
HORUS_POS = [(-72.7, 62.0), (-57.5, 62.0), (-42.3, 62.0), (-26.9, 62.0), (-57.5, 54.1), (-42.3, 54.1), (-26.9, 54.1), (-42.3, 46.0),
             (-26.9, 46.0)]
HORUS_A = 7.3  # altıgen optik köşe yarıçapı
# sol yan altıgen sütunlar (x, [y …]); ilk ikisi turuncu (sinyal), kalanlar kırmızı (fren); sağ yan aynası beyaz / kırmızı (sis)
HORUS_COLS = [(-74.8, [46.3, 30.0, 13.7, -2.6, -18.9, -35.2]), (-60.5, [38.15, 21.85, 5.55, -10.75]), (-46.2, [30.0, 13.7])]


@product('lzd3223', 'LZD 3223', 'stop', 'HORUS sol, HOR 153A, 6 işlev (plaka ışıksız), 42 LED — üretici CAD (LZD 3215) + fotoğraflar')
def build_lzd3223_cad(L):
    cad = os.path.join(CAD_ROOT, 'lzd3223')
    if not os.path.exists(os.path.join(cad, 'p004.stl')):
        print('CAD YOK (LZD 3223 yalnız CAD verisinden kurulur):', cad)
        return 'skip'

    # ===== 1) CAD: gövde, M6 saplamalar, lens =====
    parts = _cad_parts(cad, HORUS_M, ['p000', 'p001', 'p002'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p002': ([mat('Housing')], L.body, 9000), 'p000': ([mat('Zinc')], L.body, 300),
                                 'p001': ([mat('Zinc')], L.body, 300)}, 'horus')
    # lens tek parça: üçgen bölgede retro prizmalar lense kalıplı (CAD'de var). Renksiz çizilince prizmalar beyaz benek gibi
    # parlıyordu; bölge kırmızı lens (gerçekte kırmızı malzeme)
    tri_lens = _round_poly([(0.0, 66.0), (-75.5, -62.0), (75.5, -62.0)], 4.0)
    _cad_lens(L, cad, HORUS_M, 'p004', [_lmat('clear'), _lmat('red')], 'horus_lens', 9000,
              region_of=lambda x, y, z: 1 if _inside(tri_lens, x, y) else 0)

    # ===== 2) iç panel (lensin iç yüzü Z 48) ve 4 vida =====
    ZP = 31.0
    prism(L.inner, 'horus_panel', _m(rrect(193.0, 133.0, 9.0)), _z(29.8), _z(ZP), mat('HousingGloss'), 0.0)
    for x, y in ((-87.0, 54.0), (87.0, 54.0), (-87.5, -48.0), (87.5, -48.0)):
        cyl(L.inner, 'screw', 0.0029, (_z(x), _z(y), _z(ZP)), (_z(x), _z(y), _z(ZP + 2.2)), mat('HousingGloss'), 16, bevel=0.0005)

    # ===== 3) katmanlı retro üçgen (ışımaz) =====
    TO = _round_poly([(0.0, 66.0), (-75.5, -62.0), (75.5, -62.0)], 4.0)
    TM = _round_poly([(0.0, 39.6), (-50.7, -45.1), (50.7, -45.1)], 3.0)
    TI = _round_poly([(0.0, 2.8), (-18.4, -26.7), (18.4, -26.7)], 2.0)
    prism(L.inner, 'tri_base', _m(TO), _z(ZP), _z(41.6), mat('ReflectorRed'), 0.0)
    frame(L.inner, 'tri_outer_band', _m(TO), _m(offset(TM, -2.4)), _z(41.6), _z(43.8), mat('ReflectorRed'), 0.0)
    prism(L.inner, 'tri_inner_base', _m(offset(TI, 0.4)), _z(41.6), _z(43.8), mat('ReflectorRed'), 0.0)
    rp = _retro_plain('red')
    _s_hex_retro(L.inner, 'tri_retro_o', _m(TO), [_m(offset(TM, -2.6))], _z(44.6), 0.0021, 0.0008, rp)
    _s_hex_retro(L.inner, 'tri_retro_m', _m(offset(TM, 0.5)), [_m(offset(TI, -2.6))], _z(42.4), 0.0021, 0.0008, rp)
    _s_hex_retro(L.inner, 'tri_retro_i', _m(offset(TI, 0.5)), [], _z(44.6), 0.0021, 0.0008, rp)
    # katman sınırlarında çift ince parlak sırt (fotoğrafta beyazımsı iki çizgi)
    for T, nm in ((TM, 'm'), (TI, 'i')):
        frame(L.inner, 'ridge_' + nm, _m(offset(T, -2.4)), _m(offset(T, 0.4)), _z(42.4), _z(45.4), mat('ReflectorRed'), 0.0)
        for a, b in ((-2.4, -1.6), (-0.4, 0.4)):
            frame(L.inner, 'ridge_line_' + nm, _m(offset(T, a)), _m(offset(T, b)), _z(45.4), _z(45.7), mat('Reflector'), 0.0)

    # ===== 4) üst köşeler: uzun altıgen neon pozisyon modülleri =====
    pos_m = _gl('position', 'red', '#b2242b', 0.9)
    for sx in (1, -1):
        for i, (x, y) in enumerate(HORUS_POS):
            poly = _ehex(sx * x, y, 13.6, 5.9, 2.0)
            _slot(L.inner, poly, ZP, 44.0, 0.8)
            prism(L.E('position'), f'pos{i}', _m(poly), _z(ZP), _z(44.8), pos_m, 0.0006)

    # ===== 5) altıgen LED optikleri =====
    for sx, (fn_a, col_a, off_a, tint_a), fn_r in ((1, ('turn', 'amber', '#e0953a', '#c98a3c'), 'stop'),
                                                   (-1, ('reverse', 'white', '#dfe2e6', '#a9aeb4'), 'fog')):
        for ci, (x, ys) in enumerate(HORUS_COLS):
            for ri, y in enumerate(ys):
                cx, cy = sx * x, y
                hexp = _hexf(cx, cy, HORUS_A)
                frame(L.inner, 'hex_wall', _m(hexp), _m(offset(hexp, 0.8)), _z(ZP), _z(43.8), mat('HousingGloss'), 0.0)
                inner = offset(hexp, 0.8)
                if ri < 2:
                    # turuncu / beyaz (fotoğraf 3-1, ayrıntı): şeffaf dikey kaburgalı optik, ardında altı fasetli krom kap, dipte LED.
                    # Kap eşiğin altında ışır (yapısı okunur), haleyi LED verir
                    gains = (0.32, 0.24, 0.16) if col_a == 'white' else (0.38, 0.28, 0.19)
                    prism(L.E(fn_a), 'hex_floor', _m(inner), _z(ZP), _z(ZP + 0.5), _refl_tint(fn_a, col_a, 0.12, tint_a, 0.4), 0.0)
                    _cup_bands(L.E(fn_a), _z(cx), _z(cy), _z(42.8), 0.0064, 0.0024, _z(42.8 - ZP - 0.6), gains, fn_a, col_a, tint_a, 0.3, seg=6)
                    box(L.E(fn_a), 'hex_led', _z(cx - 1.4), _z(cx + 1.4), _z(cy - 1.4), _z(cy + 1.4), _z(ZP + 0.5), _z(ZP + 1.3), E(fn_a, col_a))
                    cyl(L.E(fn_a), 'optic_core', 0.0018, (_z(cx), _z(cy), _z(ZP + 1.3)), (_z(cx), _z(cy), _z(ZP + 1.9)),
                        _emat(fn_a, col_a, off_a, 'core3223'), 16)
                    ob = prism(L.lens, 'hex_optic', _m(offset(hexp, 0.9)), _z(43.2), _z(44.2), _lens_rib('amber' if col_a == 'amber' else 'clear'), 0.0003)
                    set_uv_planar(ob, 0.024)
                else:
                    # kırmızı: piramit desenli kristal optik (iri hücre: fotoğrafta tek tek seçilen piramitler), ortadaki LED'den
                    # dışa sönen; taban eşiğin altında
                    prism(L.E(fn_r), 'hex_base', _m(inner), _z(ZP), _z(43.2), _gl(fn_r, 'red', '#4a1416', 0.12), 0.0)
                    _banded(L.E(fn_r), 'hex_xtal', inner, [], 44.0, 3.2, 1.1, [(cx, cy)], lambda g, fn_r=fn_r: _crystal(fn_r, 'red', g, '#6a2023'),
                            ((0.0, 3.0, 0.8), (3.0, 5.2, 0.38), (5.2, 1e9, 0.18)))

    # kablo: arka ortadaki rakordan (6 × 0,5, 2 m; sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, 0.0, -0.002), (0.0, 0.0, -0.016), (0.0, -0.010, -0.028)], 0.0034, mat('Cable'), 3, smooth=True)



# =====================================================================
# REAR STRIPS (kullanıcı 2026-10-23: yalnız standart dorse, kasanın arka üst köşeleri). İkisi de "universal" (sol / sağ aynı;
# sağda lens ekseni çevresinde 180° döndürülür: −X ucu iki yanda dışta). Kaynaklar: üretici STEP'leri (ek paket 2026-10-22),
# ürün paketleri (Downloads/LZD-2246.zip, LZD-3141.zip: föy, çizim, fotoğraflar).
# Yerel: X uzunluk (önden bakınca sağ +X; dış uç −X), Y yukarı, Z lens yönü, montaj yüzü Z = 0.
# =====================================================================
# LZD 2246 (HOR 86): 257 × 27 × 20, 2 × Ø4,5 delik (230), 12 LED: 6 kırmızı (pozisyon + fren), 6 turuncu (sinyal); 4 × 0,5 kablo
# 1 m, arka ortadan. STEP'te: lens gövde (p000, içi dolu kabuk: CAD x ±126, derinlik y 0 … 18), lastik conta (p001, montaj yüzü
# y −2). İç (kaplar, LED'ler) ürün fotoğraflarından: 12 fasetli krom kap Ø13, 16,2 mm aralık; uçlarda vida cepleri.
# CAD ekseni (mm): x uzunluk, lens +y, yukarı +z. Yerel: X = −x, Y = z, Z = y + 2.
LZD2246_M = Matrix(((-1, 0, 0, 0), (0, -1, 0, -0.002), (0, 0, 1, 0), (0, 0, 0, 1)))


@product('lzd2246', 'LZD 2246', 'strip', 'Arka şerit lamba (HOR 86), 12 LED: pozisyon, fren, sinyal — üretici CAD + fotoğraflar')
def build_lzd2246_cad(L):
    cad = os.path.join(CAD_ROOT, 'lzd2246')
    if not os.path.exists(os.path.join(cad, 'p001.stl')):
        print('CAD YOK (LZD 2246 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    # ===== 1) CAD: lastik conta (montaj yüzü), lens kabuğu (hafif füme) =====
    parts = _cad_parts(cad, LZD2246_M, ['p001'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p001': ([mat('Rubber')], L.body, 1500)}, 'lzd2246')
    _cad_lens(L, cad, LZD2246_M, 'p000', [_lmat_alpha('smoke', 0.3, 'l30')], 'lzd2246_lens', 5000)

    # ===== 2) iç: siyah taban (lensin iç yüzü Z 18,5; boşluğun tabanı Z 8,5), uçlarda vida cepleri =====
    ZF = 8.6
    prism(L.inner, 'strip_floor', _m(rrect(196.0, 17.6, 3.0)), _z(7.8), _z(ZF), mat('HousingGloss'), 0.0)
    for sx in (1, -1):
        x = sx * 115.0
        frame(L.inner, 'screw_pocket', _m(circle(5.2, 24, x, 0.0)), _m(circle(4.4, 24, x, 0.0)), _z(2.0), _z(9.0), mat('HousingGloss'), 0.0)
        cyl(L.inner, 'screw_head', 0.0036, (_z(x), 0.0, _z(2.0)), (_z(x), 0.0, _z(4.2)), mat('Stainless'), 20, bevel=0.0007)
        box(L.inner, 'screw_slot', _z(x - 0.4), _z(x + 0.4), -0.0025, 0.0025, _z(4.2), _z(4.4), mat('HousingGloss'))
    # ===== 3) 12 fasetli krom kap: −X'te (dış uç) 6 turuncu (sinyal), +X'te (iç uç) 6 kırmızı (pozisyon + fren); kullanıcı 2026-10-23 =====
    for k in range(12):
        x = (k - 5.5) * 16.2
        fn, col = ('turn', 'amber') if k < 6 else ('position+stop', 'red')
        tint = '#c3c7cc'
        gains = (0.42, 0.3, 0.2)
        _cup_bands(L.E(fn), _z(x), 0.0, _z(16.2), 0.0065, 0.0021, _z(16.2 - ZF - 0.3), gains, fn, col, tint, 0.28, seg=10)
        box(L.E(fn), 'led', _z(x - 1.1), _z(x + 1.1), -0.0011, 0.0011, _z(ZF + 0.2), _z(ZF + 0.9), E(fn, col))
        cyl(L.E(fn), 'optic_core', 0.0015, (_z(x), 0.0, _z(ZF + 0.9)), (_z(x), 0.0, _z(ZF + 1.4)),
            _emat(fn, col, '#e7d9c2' if col == 'red' else '#f2c27a', 'core2246'), 16)
    # kablo: arka ortadan (sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, 0.0, -0.012), (0.0, 0.0, -0.024), (0.0, -0.010, -0.034)], 0.0028, mat('Cable'), 3, smooth=True)


# LZD 3141 LIZARD (HOR 145AD): 252 × 27 × 21, 34 LED: pozisyon (22 üçgen ışık kılavuzu), fren (uçlarda 2 + 2 altıgen), dinamik
# sinyal (ortada 8 altıgen; sitede sabit yanar). STEP'te: renksiz lens (p000), uçlarda dolgu kapakları (p001, p003), siyah arka
# kapak + kablo rakoru (p002), mikro kauçuk taban (p004, montaj yüzü y −2,8). İç ürün fotoğraflarından (lzd-3141_3, _4_white,
# www-3): 12 altıgen bal peteği optik (köşe yarıçapı 6,9, 16,6 mm aralık), her aralıkta üstte ve altta birer üçgen.
# CAD ekseni (mm): x uzunluk, lens +y, yukarı +z. Yerel: X = −x, Y = z, Z = y + 2,8.
LZD3141_M = Matrix(((-1, 0, 0, 0), (0, -1, 0, -0.0028), (0, 0, 1, 0), (0, 0, 0, 1)))


@product('lzd3141', 'LZD 3141', 'strip', 'LIZARD arka şerit lamba (HOR 145AD), 34 LED: pozisyon, fren, dinamik sinyal — üretici CAD + fotoğraflar')
def build_lzd3141_cad(L):
    cad = os.path.join(CAD_ROOT, 'lzd3141')
    if not os.path.exists(os.path.join(cad, 'p004.stl')):
        print('CAD YOK (LZD 3141 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    # ===== 1) CAD: uç kapakları, arka kapak, taban (siyah); lens (renksiz) =====
    parts = _cad_parts(cad, LZD3141_M, ['p001', 'p002', 'p003', 'p004'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p001': ([mat('Housing')], L.body, 1000), 'p003': ([mat('Housing')], L.body, 1000),
                                 'p002': ([mat('Housing')], L.body, 3000), 'p004': ([mat('Rubber')], L.body, 400)}, 'lzd3141')
    _cad_lens(L, cad, LZD3141_M, 'p000', [_lmat('clear')], 'lzd3141_lens', 7000)

    # ===== 2) iç: koyu füme panel (lensin iç yüzü Z 19,3) =====
    ZP = 8.6
    win = [(-105.0, 0.0), (-98.5, -11.0), (98.5, -11.0), (105.0, 0.0), (98.5, 11.0), (-98.5, 11.0)]
    prism(L.inner, 'lizard_panel', _m(win), _z(ZP - 0.8), _z(ZP), mat('HousingGloss'), 0.0)
    # ===== 3) 12 altıgen bal peteği optik: uçlarda 2'şer kırmızı (fren), ortada 8 turuncu (sinyal) =====
    A = 6.9
    for k in range(12):
        x = (k - 5.5) * 16.6
        red = k < 2 or k > 9
        fn, col, base = ('stop', 'red', '#a8121a') if red else ('turn', 'amber', '#e3932a')
        hexp = _hexf(x, 0.0, A)
        frame(L.inner, 'hex_wall', _m(offset(hexp, -0.7)), _m(hexp), _z(ZP), _z(17.6), mat('HousingGloss'), 0.0)
        prism(L.E(fn), 'hex_base', _m(hexp), _z(ZP), _z(15.6), _gl(fn, col, '#3a1a12' if not red else '#3d0d10', 0.12), 0.0)
        box(L.E(fn), 'hex_led', _z(x - 1.2), _z(x + 1.2), -0.0012, 0.0012, _z(15.6), _z(16.3), E(fn, col))
        _banded(L.E(fn), 'hex_xtal', offset(hexp, 0.3), [], 17.4, 1.6, 0.6, [(x, 0.0)],
                lambda g, fn=fn, col=col, base=base: _crystal(fn, col, g, base), ((0.0, 2.4, 0.85), (2.4, 4.4, 0.4), (4.4, 1e9, 0.2)))
    # ===== 4) pozisyon: her aralıkta üstte (tepesi aşağı) ve altta (tepesi yukarı) kırmızı üçgen ışık kılavuzu =====
    tri_m = _gl('position', 'red', '#6e1a1e', 0.85)
    for k in range(11):
        x = (k - 5.0) * 16.6
        for sy in (1, -1):
            tri = _s_ccw([(x - 3.4, sy * 10.0), (x + 3.4, sy * 10.0), (x, sy * 4.6)])
            _slot(L.inner, tri, ZP, 17.2, 0.6)
            prism(L.E('position'), 'pos_tri', _m(tri), _z(ZP), _z(17.8), tri_m, 0.0003)
    # kablo: arka kapaktaki rakordan (sitede tesisat sürer)
    tube(L.body, 'cable', [(0.0, 0.0, -0.014), (0.0, 0.0, -0.026), (0.0, -0.010, -0.036)], 0.0028, mat('Cable'), 3, smooth=True)


# =====================================================================
# LRD 2681 — geri vites işlevli çalışma lambası (HOR 111; föy: 15 LED, AR 1,1 / 1,3 W, WL 12 W, 3 × 0,75 mm² kablo).
# STEP'i yok; aynı HOR 111 gövdesinin STEP'i var: "LRD 2679" (Downloads/Product-3D-Step-Files; içindeki ön çerçevenin adı
# "Outer_Lens_Black (usunięte przesłona na środku)": 2679'da orta perde çıkarılmış). Gövde, ön çerçeve, braket, cıvata, pul,
# somun ve braket pedi CAD'den; 2681'in ortadaki beyaz bloğu (3 büyük LED, geri vites) ve 12 LED'lik halka ürün fotoğraflarından
# (Downloads/LRD-2681.zip: lrd-2681-1-1 sönük, _3-1 çalışma, _3-2 hepsi). Lens CAD'de prizmalı (700 bin köşe): sitede düz lens +
# yastık optik dokusu (aynı görüntü, bütçe içinde).
# CAD ekseni (mm): lens +x (ön yüz −1,2; çerçeve 0,5), genişlik y, yukarı +z; mafsal ekseni x −36; braket pedinin altı z −76,5.
# Yerel (eski geçici modelle aynı sözleşme, sitedeki L braket değişmez): taban (ped altı) Y = 0, saplama −Y, lens +Z.
# X = y, Y = z + 76,5, Z = x + 36.
# =====================================================================
LRD2681_M = Matrix(((0, 1, 0, 0), (-1, 0, 0, -0.036), (0, 0, 1, 0.0765), (0, 0, 0, 1)))


@product('lrd2681', 'LRD 2681', 'work', 'Geri vites işlevli çalışma lambası HOR 111, 15 LED — üretici CAD (LRD 2679 gövdesi) + fotoğraflar')
def build_lrd2681_cad(L):
    cad = os.path.join(CAD_ROOT, 'lrd2679')
    if not os.path.exists(os.path.join(cad, 'p010.stl')):
        print('CAD YOK, geçici model:', cad)
        return build_lrd2681(L)
    Hc = 76.5
    # ===== 1) CAD: gövde, ön çerçeve, C braket, mafsal ve taban cıvataları, pul / somun, braket pedi =====
    names = [f'p{i:03d}' for i in range(11) if i != 1]
    parts = _cad_parts(cad, LRD2681_M, names, angle=0.5)
    _drop_small(parts['p000'], lambda mn, mx, n: n < 60)
    ext = _assembly_exterior(parts)
    zinc = mat('Zinc')
    spec = {'p000': ([mat('Housing')], L.body, 12000), 'p002': ([mat('Housing')], L.body, 5000), 'p003': ([mat('Stainless')], L.body, 1500),
            'p010': ([mat('Seal')], L.body, 400)}
    for i in range(4, 10):
        spec[f'p{i:03d}'] = ([zinc], L.body, 500)
    _plate_parts(L, parts, ext, spec, 'lrd2681')

    # ===== 2) iç: reflektör taban (Z 23,3), 12 LED'lik halka (çalışma) =====
    W = rrect(80, 80, 13, 6, 0, Hc)
    prism(L.inner, 'refl', _m(offset(W, 0.5)), _z(22.1), _z(23.3), mat('Reflector'))
    ring = [(x, 29.5) for x in (-27, -9, 9, 27)] + [(x, -29.5) for x in (-27, -9, 9, 27)] + \
           [(sx * 31.0, sy * 13.5) for sx in (1, -1) for sy in (1, -1)]
    for x, y in ring:
        mini_led(L, L.E('work'), _z(x), _z(Hc + y), _z(26.6), 0.0015, E('work', 'white'), 0.0050, 0.0032, 8)
    # ===== 3) orta beyaz blok (2681'e özgü): 3 krom kap, büyük LED'ler çalışma + geri vites =====
    blk = rrect(56.0, 30.0, 5.0, 4, 0.0, Hc + 4.0)
    # blok: yan duvar + kap delikli üst plaka (dolu blok kapların üstünü örtüyordu)
    frame(L.inner, 'center_block', _m(blk), _m(offset(blk, 1.2)), _z(23.3), _z(28.0), mat('Reflector'), 0.0)
    with Xf(L, None, (0.0, 0.0, _z(28.0))):
        profile_solid(L.inner, 'block_top', _m(blk), [_m(circle(7.6, 28, x, Hc + 4.0)) for x in (-17.0, 0.0, 17.0)], 0.0012,
                      mat('Reflector'), 0.0, 1)
    for x in (-17.0, 0.0, 17.0):
        cx, cy = _z(x), _z(Hc + 4.0)
        _cup_bands(L.E('work+reverse'), cx, cy, _z(28.7), 0.0076, 0.0027, _z(28.7 - 23.6), (0.36, 0.27, 0.18), 'work+reverse', 'white',
                   '#c3c8ce', 0.25, seg=24)
        box(L.E('work+reverse'), 'chip', cx - 0.0016, cx + 0.0016, cy - 0.0016, cy + 0.0016, _z(23.6), _z(24.3), E('work+reverse', 'white'))
        cyl(L.E('work+reverse'), 'optic_core', 0.0022, (cx, cy, _z(24.3)), (cx, cy, _z(25.0)), _emat('work+reverse', 'white', '#e9e1c4', 'core2681'), 16)
    # blok üstündeki ve altındaki baskı plakaları (fotoğraf: E işareti ve güç değerleri)
    prism(L.inner, 'mark_plate', _m(rrect(34.0, 7.0, 1.5, 3, 0.0, Hc + 24.0)), _z(23.3), _z(26.0), mat('Reflector'), 0.0004, 1)
    prism(L.inner, 'text_plate', _m(rrect(40.0, 8.0, 1.5, 3, 0.0, Hc - 17.0)), _z(23.3), _z(26.0), mat('Reflector'), 0.0004, 1)
    for w_, yy in ((26.0, Hc + 24.0), (30.0, Hc - 16.0), (20.0, Hc - 18.6)):
        box(L.inner, 'print', _z(-w_ / 2), _z(w_ / 2), _z(yy - 0.5), _z(yy + 0.5), _z(26.0), _z(26.2), mat('HousingGloss'))
    # ===== 4) lens: düz, yastık optik dokulu (CAD lensinin ön yüzü Z 34,8, iç yüzü ~31) =====
    # orta bloğun önü düz şeffaf pencere (fotoğraf 1-1: kaplar net görünür), çevresi yastık optikli
    win = rrect(58.0, 32.0, 6.0, 4, 0.0, Hc + 4.0)
    lw = _s_ccw(offset(W, -1.0))
    ob = _frame_poly(L.lens, 'lens', lw, _s_ccw(win), _z(31.0), _z(34.8), _lmat('clear'))
    set_uv_planar(ob, 0.010)
    prism(L.lens, 'lens_window', _m(win), _z(33.6), _z(34.6), _lmat_flat('clear'), 0.0)
    # kablo: gövdenin arka ortasındaki rakordan aşağı (sitede tesisat sürer; bağlantı noktası equipment.ts LAMP_PORTS)
    cable(L, [(0, _z(Hc - 10.0), -0.0140), (0, _z(Hc - 14.0), -0.0300), (0, 0.040, -0.058)], 0.0030)


# =====================================================================
# Tutuculu marker LD 500 (turuncu yan, HOR 55/SM1, 3 LED) / LD 499 (beyaz ön, HOR 55, 1 LED). Üretici STEP'leri (ek paket
# 2026-10-22): "LD 500, 522" ve "LD 499". İkisinde de siyah gövde tabanı + arkada kablo yakası (p000), lens (p001), L tutucu
# (p002: dikey plaka + üstte geriye flanş, 2 kaburga, 2 delik) ve 2 lens vidası (p003, p004); tutucu, gövde ve vidalar iki STEP'te
# aynı. LD 500'ün lensinin İÇ YÜZÜNDE GERÇEK altıgen retro prizmalar, penceresinde 3 LED'lik Fresnel dilimleri var; LD 499'un lensi
# sadeleştirilmiş (retrosuz düz levha). Fotoğraf ve çizimlere göre iki lens aynı kalıp, yalnız pencere optiği farklı: LD 499
# LD 500'ün lensinden kurulur, penceresinde tek LED'in önünde iç içe halkalar (fotoğraf). Pencerenin ardındaki LED kartı, kablo
# yakasındaki dolgu ve kablo CAD'de yok (fotoğraf; çizim: 2 × 0,75 kablo yakadan çıkar).
# Kaynaklar: Downloads/LD-500.zip, LD-499.zip (2 fotoğraf, teknik çizim, homologasyon).
# CAD ekseni (mm): x genişlik, y yukarı, z GERİYE (lens ön yüzü −5,9; tutucu plakası 2,0 … 4,5; flanş z 21'e uzanır).
# Yerel (eski geçici modelle aynı sözleşme: yan markerin sitedeki yeri değişmez): tutucu plakasının arka yüzü Z = 0, lens +Z,
# Y yukarı, orijin toplam yüksekliğin ortası (lens altı −15,5 … flanş üstü 34,5: y 9,5). X = −x, Y = y − 9,5, Z = 4,5 − z.
# =====================================================================
LD500_M = Matrix(((-1, 0, 0, 0), (0, 0, 1, -0.0045), (0, 1, 0, -0.0095), (0, 0, 0, 1)))
LD500_YW = -9.5  # pencere (lamba) merkezinin yerel Y'si, mm
LD500_SCREW = 37.8  # lens vidalarının x'i (CAD, ±)


def _ld500_cad(L, fn, color):
    cad = os.path.join(CAD_ROOT, 'ld500')
    if not os.path.exists(os.path.join(cad, 'p004.stl')):
        print('CAD YOK, geçici model:', cad)
        return _s_ld500_like(L, color)
    amber = color == 'amber'
    lens_col = 'amber' if amber else 'clear'
    yw = LD500_YW
    # ===== 1) opak parçalar: dışarıdan görünen yüzler (saydam lens ışını kesmez: ardındaki gövde görünür kalır) =====
    parts = _cad_parts(cad, LD500_M, ['p000', 'p002', 'p003', 'p004'], angle=0.5)
    ext = _assembly_exterior(parts)
    _plate_parts(L, parts, ext, {'p000': ([mat('Housing')], L.body, 1800), 'p002': ([mat('Housing')], L.body, 4000),
                                 'p003': ([mat('Zinc')], L.body, 400), 'p004': ([mat('Zinc')], L.body, 400)}, 'ld500')

    # ===== 2) lens: yüz yüz sınıflandırma (CAD mm) =====
    lens = _stl(os.path.join(cad, 'p001.stl'), False)
    if not amber:
        # LD 499: pencerenin 3 LED'lik Fresnel dilimleri ve tabanı (z −4,5 … −4,0) silinir, delik düz tabanla kapanır
        lens.faces.ensure_lookup_table()
        kill = []
        for f in lens.faces:
            c = f.calc_center_median() * 1000
            if abs(c.x) < 10.2 and abs(c.y) < 9.2 and -4.95 < c.z < -3.45:
                kill.append(f)
        bmesh.ops.delete(lens, geom=kill, context='FACES')
        hole = [e for e in lens.edges if e.is_boundary]
        zs = [v.co.z * 1000 for e in hole for v in e.verts]
        print(f'LD499 window: removed {len(kill)} faces, hole edges {len(hole)}, z {min(zs):.2f}..{max(zs):.2f}')
        bmesh.ops.holes_fill(lens, edges=hole, sides=0)
        bmesh.ops.recalc_face_normals(lens, faces=lens.faces[:])
    win = lambda c: abs(c.x) <= 10.0 and abs(c.y) <= 9.0
    frm = lambda c: abs(c.x) <= 11.4 and abs(c.y) <= 10.4  # pencere tüneli (duvarları x ±11, y ±10)
    n_r = n_o = 0
    for f in lens.faces:
        c = f.calc_center_median() * 1000
        n = f.normal
        f.material_index = 0
        if win(c) and -4.95 < c.z < -3.45 and abs(n.z) < 0.97:
            f.material_index = 2  # pencere optiğinin eğik yüzleri (Fresnel dilimleri): ışır
            n_o += 1
        elif (not frm(c) and abs(c.x) < 46.6 and abs(c.y) < 12.9 and -3.8 < c.z < -1.9 and abs(n.z) < 0.97
              and math.hypot(abs(c.x) - LD500_SCREW, c.y) > 4.6):
            f.material_index = 1  # iç yüzdeki retro prizmalar
            n_r += 1
    print(f'LD500 lens faces: retro {n_r} optic {n_o} total {len(lens.faces)}')
    _simplify(lens, 0.5)
    glow_off = '#e6832a' if amber else '#e9edf2'
    # pencere lambanın ışık veren yüzü (LD 2774'ün neon çubuğu gibi); beyazda düşük: hale halkaları örtüyordu
    optic = _gl(fn, color, glow_off, 0.55 if amber else 0.4)
    _mesh_obj(f'ld500_lens_{lens_col}', _xf(lens, LD500_M), [_lmat_flat(lens_col), _retro_cad(fn, color, 0.16), optic], L.lens, 40,
              decimate=None if FAST else 9000)
    if not amber:
        # LD 499: tek LED'in önünde iç içe Fresnel halkaları, pencerenin iç yüzünde (Z 9,0) arkaya 0,6 mm
        for r in (1.6, 2.9, 4.2, 5.5, 6.8):
            frame(L.lens, 'fresnel', _m(circle(r + 0.35, 40, 0.0, yw)), _m(circle(r - 0.35, 40, 0.0, yw)), _z(8.4), _z(9.0), optic, 0.0)

    # ===== 3) pencerenin ardı: gövde tabanının açıklığında (CAD z 0,5 … 1,1) beyaz LED kartı, SMD LED'ler =====
    prism(L.inner, 'led_board', _m(rrect(16.4, 16.4, 1.6, 4, 0.0, yw)), _z(3.4), _z(4.0), _gl(fn, color, '#efeee9', 0.45 if amber else 0.3), 0.0)
    # LED'ler Fresnel dilimlerinin merkezlerinde (CAD: üstte ±4,8, altta orta; LD 499 tek LED ortada)
    leds = [(-4.8, 3.5), (4.8, 3.5), (0.0, -3.5)] if amber else [(0.0, 0.0)]
    for x, y in leds:
        X, Y = -x, y + yw
        box(L.inner, 'led_pkg', _z(X - 1.7), _z(X + 1.7), _z(Y - 1.4), _z(Y + 1.4), _z(4.0), _z(4.6), mat('Reflector'))
        cyl(L.E(fn), 'led', 0.0010, (_z(X), _z(Y), _z(4.6)), (_z(X), _z(Y), _z(4.75)), E(fn, color), 16)
    # kablo yakası (CAD z 2 … 13): içi dolgu reçinesi, ortasından 2 × 0,75 kablo (sitede tesisat sürer)
    cyl(L.body, 'potting', 0.0101, (0.0, _z(yw), -0.0035), (0.0, _z(yw), -0.0043), mat('Seal'), 32)
    tube(L.body, 'cable', [(0.0, _z(yw), -0.0043), (0.0, _z(yw), -0.0120), (0.0, _z(yw - 6.0), -0.0200)], 0.0028, mat('Cable'), 3, smooth=True)


@product('ld500', 'LD 500', 'side', 'Turuncu yan marker (HOR 55/SM1), 3 LED, retro reflektör, L tutucu — üretici CAD + fotoğraflar')
def build_ld500_cad(L):
    _ld500_cad(L, 'marker', 'amber')


@product('ld499', 'LD 499', 'front', 'Beyaz ön pozisyon (HOR 55), 1 LED, retro reflektör, L tutucu — üretici CAD (LD 500 lensi) + fotoğraflar')
def build_ld499_cad(L):
    _ld500_cad(L, 'front', 'white')


# =====================================================================
# LTD 669 — evrensel plaka lambası + arka pozisyon (çizim: plaka 3 LED 0,25 / 0,5 W, pozisyon 2 LED 0,6 / 1,2 W; 93 × 30 × 47;
# 2 × M5 saplama, 52,5 mm; 2 × 0,75 kablo 500 mm). Üretici STEP "LTD 669" (ek paket 2026-10-22): kırmızı yarı saydam kubbe
# (p000, içi boş kabuk, 2 mm duvar, tepesinde kabartma E işareti), yan yüzdeki şeffaf plaka penceresi (p001: önü kapalı, arkası
# açık kutu), siyah taban (p013), kablo rakoru (p002), uçlarda iki yıldız vida (p003, p004), 2 × M5 saplama (p005, p006).
# Saplamaların pul + somunu (p007 … p010) ve tabanın altındaki etiket (p011, p012) alınmaz: lamba tampona oturunca somunlar
# webin arkasında (bağlantı takımı, bumpers.py KITS). İç parçalar CAD'de yok: beyaz LED kartı, 3 beyaz SMD LED ve elemanlar
# fotoğraftan (Downloads/LTD-669.zip, picture-scaled-2); 2 kırmızı pozisyon LED'i kubbenin tepesinin altında (çizim, ayrıntı B:
# pozisyon ışığı üstten görünür).
# Evrensel: pencere tek yanda, aynı lamba plakanın iki yanına takılır (sitede çift, LTD 2834 gibi: taban tampona, kubbe arkaya,
# pencere plakaya). CAD ekseni (mm): x genişlik, pencere −y (taban ortası y 45,34), yukarı +z (taban altı −6,0).
# Yerel (LTD 2834 ile aynı sözleşme): taban altı Y = 0 (saplamalar −Y), pencere +Z. Blender'da (x, y − 45,34, z + 6,0).
# =====================================================================
LTD669_M = Matrix(((1, 0, 0, 0), (0, 1, 0, -0.04534), (0, 0, 1, 0.0060), (0, 0, 0, 1)))


def _ltd669_dome(gain=0.3):
    """Kubbe: yoğun kırmızı yarı saydam (fotoğraf: Lens.red'den koyu ve az geçirgen); kubbenin kendisi pozisyon ışığı veren yüzey:
    yanınca bütünü gain oranında kırmızı ışır (sitede Lens.* ışımıyor; alttaki ışık katmanı tek başına %60 opak kubbenin ardında
    sönük kalıyordu). Ad E.position.red.g<yüzde>.dome: site işlev malzemesi olarak yakar, saydamlık GLB'den gelir."""
    key = f'E.position.red.g{int(round(gain * 100))}.dome'
    if key not in MATS:
        m = _lmat_flat('red').copy()
        m.name = key
        p = m.node_tree.nodes['Principled BSDF']
        p.inputs['Base Color'].default_value = srgb('#b3070f')
        p.inputs['Alpha'].default_value = 0.6
        p.inputs['Emission Color'].default_value = (*GLOW['red'], 1.0)
        p.inputs['Emission Strength'].default_value = 0.0
        m['fn'] = 'position'
        m['gain'] = gain
        if 'lens' in m:
            del m['lens']  # set_icon_glass lens saydamlığını tablodan (kırmızı 0,32) yazmasın
        MATS[key] = m
    return MATS[key]


@product('ltd669', 'LTD 669', 'plate', 'Evrensel plaka lambası + kırmızı arka pozisyon, 3 + 2 LED, 2 × M5 — üretici CAD + fotoğraflar')
def build_ltd669_cad(L):
    cad = os.path.join(CAD_ROOT, 'ltd669')
    if not os.path.exists(os.path.join(cad, 'p013.stl')):
        print('CAD YOK (LTD 669 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    # ===== 1) opak parçalar (saydam kubbe ve pencere ışını kesmez: içleri görünür) =====
    parts = _cad_parts(cad, LTD669_M, ['p002', 'p003', 'p004', 'p005', 'p006', 'p013'], angle=0.5)
    ext = _assembly_exterior(parts)
    zinc, steel = mat('Zinc'), mat('Stainless')
    _plate_parts(L, parts, ext, {'p013': ([mat('Housing')], L.body, 4000), 'p002': ([mat('Rubber')], L.body, 300),
                                 'p003': ([zinc], L.body, 300), 'p004': ([zinc], L.body, 300),
                                 'p005': ([steel], L.body, 200), 'p006': ([steel], L.body, 200)}, 'ltd669')

    # ===== 2) kubbe (iç yüzü pencereden ve duvardan görünür: bütünü) + tepenin altında pozisyon ışığı katmanı =====
    dome = _stl(os.path.join(cad, 'p000.stl'), LTD669_M)
    _drop_small(dome, lambda mn, mx, n: n < 10)
    # tepenin iç yüzü (CAD z 39; taban altından 45 mm): aşağı bakan yüzler. Kopyası 0,4 mm altta, kubbeye (yukarı) bakar
    top = _subset(dome, lambda f: f.normal.z < -0.25 and f.calc_center_median().z > 0.040)
    bmesh.ops.reverse_faces(top, faces=top.faces[:])
    _move(top, (0, 0, -0.0004))
    print('LTD669 dome top faces', len(top.faces))
    _simplify(dome, 0.5)
    _mesh_obj('ltd669_dome', dome, [_ltd669_dome()], L.E('position'), 35, decimate=None if FAST else 9000)
    _simplify(top, 0.5)
    _mesh_obj('ltd669_pos', top, [_gl('position', 'red', '#5a0b10', 0.7)], L.E('position'), 35, decimate=None if FAST else 1500)
    # plaka penceresi: şeffaf kutu (iç yüzü kaburgalı)
    win = _stl(os.path.join(cad, 'p001.stl'), LTD669_M)
    _simplify(win, 0.5)
    _mesh_obj('ltd669_window', win, [_lmat_flat('clear')], L.lens, 35, decimate=None if FAST else 3000)

    # ===== 3) iç: pencerenin ardında dikey beyaz LED kartı (CAD y 45,6 … 46,6), 3 beyaz SMD LED, elemanlar; tepesinde pozisyon kartı =====
    prism(L.inner, 'pcb', _m(rrect(45.0, 23.5, 1.0, 3, 0.0, 20.25)), _z(-1.26), _z(-0.26), _gl('plate', 'white', '#e9eae5', 0.5), 0.0)
    yl = 22.0  # pencerenin ortası (CAD z 16)
    for x in (-12.5, 0.0, 12.5):
        box(L.inner, 'led_pkg', _z(x - 1.75), _z(x + 1.75), _z(yl - 1.4), _z(yl + 1.4), _z(-0.26), _z(0.6), mat('Reflector'))
        box(L.E('plate'), 'led', _z(x - 1.1), _z(x + 1.1), _z(yl - 1.1), _z(yl + 1.1), _z(0.6), _z(0.75), E('plate', 'white'))
    for x, w, h in ((-6.5, 3.0, 5.0), (16.5, 3.2, 5.5), (5.5, 2.0, 1.2)):
        box(L.inner, 'chip', _z(x - w / 2), _z(x + w / 2), _z(yl - h / 2), _z(yl + h / 2), _z(-0.26), _z(0.9), mat('HousingGloss'))
    for dy in (-3.6, 3.6):
        cyl(L.inner, 'pad', 0.0012, (_z(-17.5), _z(yl + dy), _z(-0.26)), (_z(-17.5), _z(yl + dy), _z(0.1)), mat('Zinc'), 16)
    box(L.inner, 'pos_board', _z(-14.0), _z(14.0), _z(33.0), _z(34.0), _z(-3.5), _z(0.5), _gl('position', 'red', '#e2e3df', 0.25))
    for x in (-9.0, 9.0):
        box(L.inner, 'led_pkg', _z(x - 1.6), _z(x + 1.6), _z(34.0), _z(34.6), _z(-3.1), _z(0.1), mat('Reflector'))
        box(L.E('position'), 'led', _z(x - 1.0), _z(x + 1.0), _z(34.6), _z(34.75), _z(-2.5), _z(-0.5), E('position', 'red'))
    # kablo: tabanın altındaki rakordan webin içinden geriye (sitede tesisat sürer; bağlantı noktası equipment.ts LAMP_PORTS)
    tube(L.body, 'cable', [(0.0, -0.0002, 0.0), (0.0, -0.0140, 0.0), (0.0, -0.0300, -0.0060)], 0.0029, mat('Cable'), 3, smooth=True)


# =====================================================================
# Kısa saplı gabari lambaları (kullanıcı 2026-10-23: lastik kol kategorisinde, LD 2994 / LDCC 2698 ile aynı yerleşim).
# Sözleşme (lamps_cad.py LD_M / LDCC_M ile aynı): taban plakasının duvar yüzü Z = 0, Z dışa, Y yukarı, beyaz yüz −X (öne),
# kırmızı +X (arkaya), uçta turuncu (yana); orijin plakanın merkezi.
# =====================================================================
# LD 3065 DRAGON kısa (LD 2994'ün kısa saplı kardeşi). Üretici STEP "LD 3065" (ek paket 2026-10-22): taban plakası + sap + fasetli
# kafa gövdesi (p002), beyaz yüzün ⟨ ⟩ ışık kılavuzları ve uçtaki iki turuncu blok (p000), kırmızı yüzün kılavuzları (p001),
# 2 cıvata (p003, p004), kablo (p005, duvarın içinde: alınmaz). Kaynak: Downloads/LD-3065.zip (fotoğraflar; yanık: beyaz çift
# şevron + turuncu uç).
# CAD ekseni (mm): dışa +x (plakanın duvar yüzü x 209,7), plaka yüksekliği z (±52,6), kafanın iki yüzü ±y (beyaz +y; merkez
# y −57,35). Yerel: X = −(y + 57,35), Y = −z (model z'de simetrik), Z = x − 209,7.
LD3065_M = Matrix(((0, -1, 0, -0.05735), (-1, 0, 0, 0.2097), (0, 0, -1, 0), (0, 0, 0, 1)))


@product('ld3065', 'LD 3065', 'arm', 'DRAGON kısa saplı gabari lambası: beyaz / kırmızı neon şevron, turuncu uç — üretici CAD')
def build_ld3065_cad(L):
    cad = os.path.join(CAD_ROOT, 'ld3065')
    if not os.path.exists(os.path.join(cad, 'p004.stl')):
        print('CAD YOK (LD 3065 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    parts = _cad_parts(cad, False, ['p000', 'p001', 'p002', 'p003', 'p004'], angle=0.5)
    ext = _assembly_exterior(parts)
    # gövde: sap ve plaka kauçuk, kafa (x > 233) sert plastik
    body = parts.pop('p002')
    keep = ext['p002']
    for nm, sel, mats_, dec in (('arm', lambda c: c.x < 0.233, [mat('Rubber')], 6000), ('head', lambda c: c.x >= 0.233, [mat('Housing')], 6000)):
        sb = _subset(body, lambda f: keep[f.index] and sel(f.calc_center_median()))
        _simplify(sb, 1.0)
        _mesh_obj('ld3065_' + nm, _xf(sb, LD3065_M), mats_, L.body, 35, decimate=None if FAST else dec)
    body.free()
    off = {'white': '#dde1e6', 'red': '#a3201b', 'amber': '#e39a35'}
    guides = {'white': (parts.pop('p000'), ext['p000']), 'red': (parts.pop('p001'), ext['p001'])}
    for side, (b, ex) in guides.items():
        # uçtaki turuncu bloklar merkeze yakın (|z| < 10,8 mm); şevronların uç kolları daha dışta (|z| ≥ 12)
        amb = lambda c: c.x > 0.2960 and abs(c.z) < 0.0108
        for key, sel in ((side, lambda c: not amb(c)), ('amber', amb)):
            sb = _subset(b, lambda f: ex[f.index] and sel(f.calc_center_median()))
            if not sb.faces:
                sb.free()
                continue
            print('LD3065', side, key, len(sb.faces))
            _simplify(sb, 1.0)
            _mesh_obj(f'neon_{side}_{key}', _xf(sb, LD3065_M), [_emat('outline', key, off[key], 'cad')], L.E('outline'), 40,
                      decimate=None if FAST else 2500)
        b.free()
    for nm in ('p003', 'p004'):
        sb = _subset(parts[nm], lambda f: ext[nm][f.index])
        parts[nm].free()
        _simplify(sb, 2.0)
        _mesh_obj('ld3065_' + nm, _xf(sb, LD3065_M), [mat('Zinc')], L.body, 35, decimate=None if FAST else 300)


# LDCC 2776 kısa saplı gabari lambası. Üretici STEP "LDCC 2776, 2777" (ek paket 2026-10-22): TEK parça dış zarf (p000: plaka,
# sap, kafa; lens yüzleri, LED piramitleri, uçtaki turuncu pencere aynı kabukta) + uçta iki ince iç levha (p001, p002; alınmaz).
# Yüzler sınıflanır; lensin ardındaki katmanlar fotoğraflardan (Downloads/LDCC-2776.zip): iki yüzde de şeffaf lens, ardında
# gümüş reflektör, iki uçta 5'er LED piramidi; ortadaki pencere beyaz yüzde logolu gümüş panel, kırmızı yüzde kırmızı
# reflektör + 2 LED; uçta turuncu lens.
# CAD ekseni (mm): dışa +x (plakanın duvar yüzü x −52,7; ardındaki pimler duvarın içinde, alınmaz), yukarı +y (plaka merkezi
# y −0,2), lens yüzleri ±z (beyaz +z; yüz düzlemi ±18,5, orta pencere ±17, LED piramitleri ±20'ye çıkar).
LDCC2776_M = Matrix(((0, 0, -1, 0), (-1, 0, 0, -0.0527), (0, 1, 0, 0.0002), (0, 0, 0, 1)))


@product('ldcc2776', 'LDCC 2776', 'arm', 'Kısa saplı gabari lambası: beyaz / kırmızı, turuncu uç, LED piramitleri — üretici CAD + fotoğraflar')
def build_ldcc2776_cad(L):
    cad = os.path.join(CAD_ROOT, 'ldcc2776')
    if not os.path.exists(os.path.join(cad, 'p000.stl')):
        print('CAD YOK (LDCC 2776 yalnız CAD verisinden kurulur):', cad)
        return 'skip'
    raw = _stl(os.path.join(cad, 'p000.stl'), False)
    # lensin dış hattı yüz düzleminin (±18,5; x −25,7 … 35,4, y ±23,7) 4 mm içinde, köşeleri 6 mm pahlı (fotoğraf: kauçuk çerçeve).
    # Düzlem bu hattan kesilir: yüz merkeziyle sınıflama büyük üçgenlerde dişli kenar bırakıyordu
    LX0, LX1, LY, CH = -21.7, 31.4, 19.7, 6.0
    cuts = [((LX0, 0, 0), (1, 0, 0)), ((LX1, 0, 0), (1, 0, 0)), ((0, LY, 0), (0, 1, 0)), ((0, -LY, 0), (0, 1, 0))]
    for sx, x in ((1, LX1), (-1, LX0)):
        for sy in (1, -1):
            cuts.append(((x - sx * CH, sy * LY, 0), (sx, sy, 0)))
    for co, no in cuts:
        bmesh.ops.bisect_plane(raw, geom=raw.verts[:] + raw.edges[:] + raw.faces[:], plane_co=Vector(co) / 1000, plane_no=Vector(no).normalized())
    bmesh.ops.triangulate(raw, faces=raw.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    raw.faces.ensure_lookup_table()

    def in_lens(c):
        if not (LX0 <= c.x <= LX1 and abs(c.y) <= LY):
            return False
        return all(sx * (c.x - (LX1 if sx > 0 else LX0)) + sy * (c.y - sy * LY) <= -CH + 1e-3 for sx in (1, -1) for sy in (1, -1)) or             (LX0 + CH <= c.x <= LX1 - CH) or abs(c.y) <= LY - CH

    def zone(f):
        c = f.calc_center_median() * 1000
        n = f.normal
        if c.x < -52.9:
            return None  # duvarın içindeki pimler
        sg = 1 if c.z > 0 else -1
        side = 'white' if sg > 0 else 'red'
        zs = c.z * sg
        if zs > 18.65 and in_lens(c):
            return 'led_' + side  # LED piramitleri (yüz düzleminin üstünde)
        if n.z * sg > 0.99 and abs(zs - 17.0) < 0.15:
            return 'win_' + side  # orta pencere (x −15,5 … 25,3, y ±13,2): logo paneli / kırmızı reflektör
        if 16.95 < zs < 18.45 and abs(n.z) < 0.99 and -15.8 < c.x < 25.6 and abs(c.y) < 13.5:
            return 'lens_' + side  # pencerenin duvarları: lensin parçası
        if n.z * sg > 0.99 and abs(zs - 18.5) < 0.2 and in_lens(c):
            return 'lens_' + side
        return 'body'
    zones = [zone(f) for f in raw.faces]
    counts = {}
    for z in zones:
        counts[z] = counts.get(z, 0) + 1
    print('LDCC2776 zones', counts)
    sub = lambda key: _subset(raw, lambda f: zones[f.index] == key)
    b = sub('body')
    _simplify(b, 1.0)
    _mesh_obj('ldcc2776_body', _xf(b, LDCC2776_M), [mat('Rubber')], L.body, 35, decimate=None if FAST else 12000)
    off = {'white': '#dde1e6', 'red': '#a3201b'}
    for side, sg in (('white', 1.0), ('red', -1.0)):
        # lens yüzü (pencere, duvarları ve piramitler dahil): şeffaf
        lens = _subset(raw, lambda f: zones[f.index] in (f'lens_{side}', f'win_{side}', f'led_{side}'))
        _simplify(lens, 1.0)
        _mesh_obj(f'ldcc2776_lens_{side}', _xf(lens, LDCC2776_M), [_lmat_flat('clear')], L.lens, 40, decimate=None if FAST else 3000)
        # lensin 0,8 mm ardında gümüş reflektör: yanınca LED'in ışığını yansıtır
        refl = sub(f'lens_{side}')
        _simplify(refl, 1.0)
        _mesh_obj(f'ldcc2776_refl_{side}', _xf(_move(refl, (0, 0, -0.0008 * sg)), LDCC2776_M), [_refl('outline', side, 0.3)], L.inner, 40,
                  decimate=None if FAST else 2000)
        # orta pencere 1 mm geride: beyaz yüzde logolu gümüş panel, kırmızı yüzde kırmızı reflektör
        win = sub(f'win_{side}')
        _simplify(win, 1.0)
        wm = _refl('outline', 'white', 0.45) if side == 'white' else _gl('outline', 'red', '#b0141c', 0.5)
        _mesh_obj(f'ldcc2776_win_{side}', _xf(_move(win, (0, 0, -0.0010 * sg)), LDCC2776_M), [wm], L.inner, 40)
        # LED piramitleri: ışık veren optik
        led_ = sub(f'led_{side}')
        _mesh_obj(f'ldcc2776_led_{side}', _xf(led_, LDCC2776_M), [_emat('outline', side, off[side], 'cad')], L.E('outline'), 40)
    # kırmızı yüzün ortasında 2 kırmızı LED (fotoğraf 3-1), lens penceresi (yerel X 17) ile kırmızı reflektörün (X 16) arasında
    for x in (8.0, 14.0):
        cyl(L.E('outline'), 'led_red_center', 0.0012, (0.0166, 0.0, x / 1000 + 0.0527), (0.0161, 0.0, x / 1000 + 0.0527),
            E('outline', 'red'), 16)
    # uçtaki turuncu lens STEP'te yok: yalnız yuvası var (CAD x 39,2 … 45, y ±14, z ±8; 6 mm derin). Fotoğraftaki gibi yuvayı
    # dolduran, uçtan 0,8 mm taşan turuncu lens; dibinde ışık veren katman. Yerel: X = −z, Y = y + 0,2, Z = x + 52,7
    box(L.E('outline'), 'amber_glow', _z(-7.7), _z(7.7), _z(-13.6), _z(14.0), _z(91.95), _z(92.5), _emat('outline', 'amber', '#e39a35', 'cad'))
    # lensin ön yüzünün 1 mm ardında ikinci ışık katmanı: dipteki tek başına 6 mm turuncu lensin ardında sönük kalıyordu
    box(L.E('outline'), 'amber_glow_front', _z(-7.0), _z(7.0), _z(-12.9), _z(13.3), _z(97.2), _z(97.5), _gl('outline', 'amber', '#e8892a', 0.6))
    box(L.lens, 'amber_lens', _z(-7.85), _z(7.85), _z(-13.75), _z(14.15), _z(92.5), _z(98.5), _lmat_flat('amber'), 0.0012)
    raw.free()
