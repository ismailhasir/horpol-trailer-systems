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
