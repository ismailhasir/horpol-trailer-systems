# Silobas (devrilmeyen "W" tipi alüminyum silo, 3 akslı; referans: Kässbohrer K.SSL 38 / 2 - 10 / 24). Blender'da betikle
# modellenir; şasi/tekerlek/üst yapı AO + yüzey dokusu pişirilir, tank kabuğu tekrarlanan fırçalanmış alüminyum dokusu ve
# ikinci UV'deki AO ile dışa aktarılır. Sitenin okuyacağı bağlantı noktaları aynı ölçülerden JSON olarak yazılır.
# Belge: docs/Silobas Dorse/README.md
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/silo.py -- [--fast] [--anchors] [--preview <klasör>]
#   ardından: npm run models:pack -- silo
#
# Ölçü kaynağı (teknik tablo, "K.SSL 38 / 2 - 10 / 24"): tank çapı 2.550, eyer yüksekliği (H5) 1.220, hacim 38 m³,
# 1 bölme, 3 × DN450 basınçlı kapak, arkadan boşaltma, 2 × NW100 5 m hortum borusu, alüminyum ekstrüzyon şasi (destek
# konsolunun içine kaynaklı), 3 BPW havalı süspansiyonlu aks, 385/65 R22,5. Tabloda dingil mesafesi 7.615 ve boy 10.605;
# broşürün ölçekli çiziminde 7.815 ve 10.823 yazar: model çizimi izler (79,92 px/m; akslar arası 1.310 ile doğrulandı).
# Çizimden: king pin → iniş ayağı 2.250, tank üstü 3,79 m, kapak üstü 3,934 m, kapaklar x = -7,27 / -5,12 / -2,97,
# ön bombeli kapak (en önü ~-9,6 m, yükseklik ~2,6 m), konsolun eğik ön çizgisi (~56°), iki boşaltma konisinin ağzı
# x ≈ -7,17 ve -4,40 (alt ~1,0 m), arkada boşaltma dolabı (1,5 m genişlik, 1,1–2,8 m), sol arkada merdiven.
# Kesin olmayanlar (doğrulanmadı): koni eğimleri, konsolun genişliği, ana kirişlerin kesiti, hortum borularının boyu.
import bpy
import math
import os
import sys

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in argv
ANCHORS_ONLY = '--anchors' in argv
PREVIEW = os.path.abspath(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
OUT_DIR = os.path.abspath('src/assets/models')
RAW_DIR = os.path.abspath('tools/blender/out')
ANCHORS = os.path.abspath('src/configurator/engine/silo-anchors.json')

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import (  # noqa: E402
    Parts, arch, bake_ao, bake_surface, beam, bl, box, box2, build_wheel, ground_contact, landing_gear, preview_renders, running_gear, cylinder, decal_mesh,
    export_glb, galvanized_checker_tile, hose, join, logo_material, loft, material, np_image, pchip, planar_uv, poly_tube,
    prism_xy, prism_zy, rear_quad, run_bake, select_only, smart_uv, tank_metal_tile, tex_material, tiled_ao_finish, tiled_ao_setup,
    write_anchors,
)

scene = bpy.context.scene

# ================= ölçüler (metre; x: arka uç 0, ön -L) =================
L = 10.82  # çizimdeki toplam boy (ön hava hattı tutamağı dahil)
W = 2.55
W2 = W / 2
XF = -10.64  # konsolun ön yüzü
XR = 0.0
R = 0.536  # 385/65 R22,5
WZ = 1.04  # tekerlek merkezi (yanal); dış yüz ~1,23
H5 = 1.22
KING_X = -10.315
WB = 7.815
AX_MID = KING_X + WB
AXLES = [AX_MID - 1.31, AX_MID, AX_MID + 1.31]
LEG_X = KING_X + 2.25
# tank: üst yarı elips (silindir bölgesinde Ø2,55 daire), alt yarı x boyunca derinliği değişen süper elips ("W": iki koni,
# yanlarda düzleme yakın eğik yüzler). Önde king pin konsoluna inen eğik burun konisi, arkada bombeli kapak.
RT = 1.275
YC = 2.515
TOP = YC + RT
XN = -10.58  # burnun ön ucu (konsolun üstündeki küçük ön levha)
XH = -1.42  # arka kapak tabanı
D_R = 0.76
HC_R = 2.95
OUT = [-7.17, -4.40]  # boşaltma ağızları
DOMES = [-7.27, -5.12, -2.97]
DOME_TOP = 3.934
f_top = pchip([XN, -10.1, -9.6, -9.25, -9.0, -8.7, XH], [1.98, 2.58, 3.22, 3.66, 3.785, TOP, TOP])
f_a = pchip([XN, -10.35, -10.0, -9.6, -9.2, -8.95, XH], [0.56, 0.92, 1.13, 1.235, 1.268, RT, RT])
f_yc = pchip([XN, -10.1, -9.6, -9.2, -8.9, XH], [1.70, 1.90, 2.18, 2.42, YC, YC])
f_keel = pchip([XN, -9.9, -9.0, -8.1, OUT[0], -6.47, -5.78, -5.09, OUT[1], -3.40, -2.40, XH],
               [1.47, 1.45, 1.38, 1.22, 0.98, 1.47, 1.86, 1.47, 1.00, 1.54, 2.06, 2.55])
f_k = pchip([XN, -9.6, -8.4, OUT[0], -5.78, OUT[1], -2.40, XH], [2.0, 1.8, 1.4, 1.25, 1.5, 1.25, 1.45, 1.8])
f_wb = pchip([XN, -9.6, OUT[0], -5.78, OUT[1], XH], [0.28, 0.25, 0.15, 0.24, 0.15, 0.20])
# şasi
BZ = 0.52  # ana kiriş ekseni (yanal)
BOT = 0.88  # ana kiriş altı
BTOP = 1.08
CON_TOP = 1.42  # destek konsolu üstü
CON_X1 = -7.80  # konsolun arka ucu (kirişlere bağlanır)
SX0, SX1 = -7.85, -4.62  # yan çerçeve (alüminyum, yan koruma)
FR0, FR1 = -4.55, -0.40  # çamurluk rayı (yan markerlar bunun üstünde)
HY = 1.18  # tesisat düzlemi (kirişlerin üstü, tankın altı)
SOCKET_Y = 1.33
LAMP_Y = 0.81
PLATE_Y = 0.81
CAB = (-1.45, -0.60, 1.12, 2.80, 0.75)  # arka boşaltma dolabı: x0, x1, y0, y1, z yarı genişlik
FRONT_Y, FRONT_Z = 1.95, 0.62  # ön pozisyon lambaları: burnun alt köşelerinde
CS = (XF - 0.5, XR + 0.5, -W2 - 0.45, W2 + 0.45)
NU, NL = 48, 20  # halka: üst yay ve alt yarı (her yan) nokta sayısı


def sec(x):
    """x'teki kesit parametreleri: ekvator yüksekliği, yarı genişlik, üst/alt yükseklik, alt süper elips üssü, taban yarı genişliği"""
    yc = f_yc(x)
    return yc, f_a(x), f_top(x) - yc, yc - f_keel(x), f_k(x), f_wb(x)


def ring2d(x, nu=NU, nl=NL):
    """Kesit halkası [(z, y)]: alttaki düz tabanın sağ ucundan başlar, sağ yan → üst → sol yan → sol uç"""
    yc, a, hu, hl, k, wb = sec(x)
    e = 2.0 / k
    pts = []
    for j in range(nl, 0, -1):
        f = j / nl * math.pi / 2
        pts.append((wb + (a - wb) * math.cos(f) ** e, yc - hl * math.sin(f) ** e))
    for i in range(nu + 1):
        t = math.pi * i / nu
        pts.append((a * math.cos(t), yc + hu * math.sin(t)))
    for j in range(1, nl + 1):
        f = j / nl * math.pi / 2
        pts.append((-(wb + (a - wb) * math.cos(f) ** e), yc - hl * math.sin(f) ** e))
    return pts


def under(x, z):
    """Tankın alt yüzeyinin yanal z'deki yüksekliği (silindir bölgesinde)"""
    yc, a, hu, hl, k, wb = sec(x)
    z = abs(z)
    if z <= wb:
        return yc - hl
    q = min((z - wb) / (a - wb), 1.0)
    return yc - hl * (1.0 - q ** k) ** (1.0 / k)


def head_rings(x0, d, cy, sign, n=12, p=2.0):
    """Bombeli kapak: taban halkası (x0) merkez yüksekliğe (cy) doğru küçülür; x = x0 + sign·d·sin φ"""
    base = ring2d(x0)
    out = []
    for i in range(1, n + 1):
        ph = (math.pi / 2) * i / (n + 0.6)
        e = math.sin(ph)
        sg = (1.0 - e ** p) ** (1.0 / p)
        out.append([(x0 + sign * d * e, cy + (y - cy) * sg, z * sg) for z, y in base])
    return out, (x0 + sign * d, cy, 0.0)


def side_y_profile():
    # yan markerlar: önde yan çerçevenin üst rayı, aks bölgesinde çamurluk rayı
    return [[SX0, 0.90], [SX1, 0.90], [FR0, 1.14], [XR, 1.14]]


def inside(poly, z, y):
    c = False
    for i in range(len(poly)):
        (z1, y1), (z2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and z < z1 + (y - y1) * (z2 - z1) / (y2 - y1):
            c = not c
    return c


def nose_x(z, y):
    """Burun yüzeyinin (z, y) noktasındaki x'i: kesiti noktayı ilk içine alan x (önden arkaya tarama)"""
    x = XN
    while x < -8.5 and not inside(ring2d(x, 24, 12), z, y):
        x += 0.005
    return x


def anchors_dict():
    """Sitenin okuyacağı bağlantı noktaları (three.js koordinatları; şema: src/configurator/engine/baked.ts)"""
    sections = []
    for x in (XN, -9.6, -8.1, OUT[0], -5.78, OUT[1], -3.0, XH):
        sections.append([[x, y, z] for z, y in ring2d(x, 24, 8)])
    # orta düzlemde yan siluet: burun, üst çizgi, arka kapak, alt "W" çizgisi
    sil = []
    rr, rc = head_rings(XH, D_R, HC_R, 1, 8, p=2.4)
    top_i = NL + NU // 2
    x = XN
    while x < XH:
        sil.append([x, f_top(x), 0.0])
        x += 0.2 if x > -8.8 else 0.1
    for ring in rr:
        sil.append([ring[top_i][0], ring[top_i][1], 0.0])
    sil.append([rc[0], rc[1], 0.0])
    for ring in reversed(rr):
        sil.append([ring[0][0], ring[0][1], 0.0])
    x = XH
    while x > XN:
        sil.append([x, f_keel(x), 0.0])
        x -= 0.2
    sil.append([XN, f_keel(XN), 0.0])
    sections.append(sil)
    # ekvator çevresi (üstten görünüş) ve kapaklar
    eq = [[x, f_yc(x), f_a(x)] for x in [XN + (XH - XN) * i / 40 for i in range(41)]]
    sections.append(eq + [[x, y, -z] for x, y, z in reversed(eq)])
    for xd in DOMES:
        sections.append([[xd + 0.3 * math.cos(t), DOME_TOP - 0.05, 0.3 * math.sin(t)] for t in [i * math.pi / 8 for i in range(16)]])
    fx = nose_x(FRONT_Z, FRONT_Y)
    return {
        '_source': 'tools/blender/silo.py tarafından üretilir; elle düzenleme',
        'L': L,
        'W': W,
        'topY': DOME_TOP,
        'rear': {'x': XR, 'lampY': LAMP_Y, 'lampZ': [0.96, 0.56], 'plateY': PLATE_Y, 'dropX': -0.2},
        'side': {'x0': -7.6, 'x1': -0.55, 'z': W2 + 0.003, 'profile': side_y_profile()},
        'front': {'x': fx - 0.035, 'y': FRONT_Y, 'z': FRONT_Z},
        'armFront': {'x': -8.8, 'y': 2.7, 'z': W2},
        'armRear': {'x': -1.55, 'y': 2.7, 'z': W2},
        'extra': {'x': CAB[1], 'y': 2.62, 'z0': 0.62, 'z1': 0.32},
        'socket': {'x': XF - 0.005, 'y': SOCKET_Y},
        'harness': {'y': HY, 'frontX': XF + 0.25, 'trunkZ': 0.66, 'rearZ': 0.4,
                    'profile': [[XF, SOCKET_Y], [-9.25, SOCKET_Y], [-8.55, HY], [XR, HY]]},
        'contact': {'x0': CS[0], 'x1': CS[1], 'z0': CS[2], 'z1': CS[3]},
        'sections': sections,
    }


if ANCHORS_ONLY:
    write_anchors(ANCHORS, anchors_dict())
    raise SystemExit(0)

# ================= malzemeler =================
# Renk düzeni (Horpol): doğal fırçalanmış alüminyum tank ve dolap, antrasit şasi ve konsol (RAL 7016, saten), çıplak
# alüminyum yan çerçeve, tampon ve boru hatları, siyah çamurluk ve hortum boruları, cilalı alüminyum jant. Tesisat
# görünümünde antrasit şasi üzerinde renkli hatlar okunaklıdır.
ANTHRACITE = '#373d41'
M = {
    'paint': material('FramePaint', ANTHRACITE, 0.44, 0.05, 0.35),
    'dark': material('DarkSteel', '#1b1d20', 0.5, 0.4),
    'susp': material('Suspension', '#1e2023', 0.48, 0.3, 0.1),
    'rubber': material('Rubber', '#141517', 0.85, 0.0),
    'plastic': material('Plastic', '#121315', 0.38, 0.0, 0.2),
    'alu': material('ChassisAlu', '#c6cbd1', 0.34, 0.9),
    'pipe': material('PipeAlu', '#b9bfc6', 0.3, 0.9),
    'chrome': material('Chrome', '#e8ebee', 0.08, 1.0),
    'galv': material('Galvanized', '#9fa5ab', 0.45, 0.9),
    'red': material('ReflRed', '#c8101a', 0.3, 0.05),
    'air': material('AirLine', '#24262a', 0.6, 0.0),
    'airRed': material('AirLineRed', '#9c1d1d', 0.55, 0.0),
    'airYellow': material('AirLineYellow', '#b58a12', 0.55, 0.0),
}
MW = {
    'tire': material('Tire', '#161719', 0.88, 0.0),
    'rim': material('Rim', '#cfd3d8', 0.22, 1.0),
    'hub': material('Hub', '#222427', 0.45, 0.5),
    'nut': material('Nut', '#c4c7cb', 0.25, 1.0),
}
MB = {
    'alu': material('BodyAlu', '#c3c8ce', 0.32, 0.9),
    'lid': material('LidAlu', '#cdd2d8', 0.28, 0.95),
    'dark': material('BodyDark', '#1f2124', 0.5, 0.4),
    'black': material('HoseTube', '#141517', 0.32, 0.0, 0.3),
    'rubber': material('BodyRubber', '#151618', 0.8, 0.0),
    'brass': material('Brass', '#b4914f', 0.3, 1.0),
    'galv': material('BodyGalv', '#a4aab0', 0.4, 0.9),
    'red': material('BodyReflRed', '#c8101a', 0.3, 0.05),
    'glass': material('Gauge', '#20262c', 0.1, 0.0),
}
PROFILES = {
    'FramePaint': {'grime': 0.55, 'wear': 0.3},
    'Suspension': {'grime': 0.9, 'low_h': 1.0},
    'DarkSteel': {'grime': 0.8},
    'Rubber': {'grime': 0.6},
    'Plastic': {'grime': 0.55, 'low_h': 1.1},
    'ChassisAlu': {'grime': 0.5},
    'PipeAlu': {'grime': 0.55},
    'Galvanized': {'grime': 0.45},
    'Chrome': {'grime': 0.12},
    'Tire': {'grime': 0.55, 'dust_mix': 0.4, 'low_h': 0.5},
    'Rim': {'grime': 0.5, 'low_h': 0.8},
    'Hub': {'grime': 0.8},
    'BodyAlu': {'grime': 0.3},
    'LidAlu': {'grime': 0.25},
    'HoseTube': {'grime': 0.35, 'low_h': 1.4},
    'BodyGalv': {'grime': 0.3},
}
# tekrarlanan dokular: tank kabuğu fırçalanmış alüminyum (u = boyuna), yürüme yolu kaymaz sac
TT = 0.9
acol, aorm = tank_metal_tile(256 if FAST else 512, rough=0.36)
gcol, gnor, gorm = galvanized_checker_tile(256 if FAST else 512)
MT = {
    'tank': tex_material('TankAlu', '#ffffff', 0.34, 1.0, albedo=np_image('tank_alu_albedo', acol), orm=np_image('tank_alu_orm', aorm, non_color=True)),
    'weld': material('Weld', '#a9aeb4', 0.5, 0.85),
}
MD = {
    'checker': tex_material('WalkChecker', '#ffffff', 0.45, 0.85, albedo=np_image('walk_checker_albedo', gcol), normal=np_image('walk_checker_normal', gnor, non_color=True),
                            orm=np_image('walk_checker_orm', gorm, non_color=True)),
}
P = M['paint']
LOGO = logo_material('Logo', 'public/brand/logo-blue.png')
LOGO_W = logo_material('LogoWhite', 'public/brand/logo-white.png')

# =====================================================================
# ŞASİ (tesisat görünümünde görünür)
# =====================================================================
C = Parts()

# --- destek konsolu: king pin plakası, alt kutu (kirişlere iner), tankın ön kapağına çıkan eğik boyun ---
box2(C, 'king_plate', XF + 0.02, -9.30, H5, H5 + 0.02, -0.62, 0.62, M['dark'], 0.003)
cylinder(C, 'king_pin', 0.0254, (KING_X, H5, 0), (KING_X, H5 - 0.062, 0), M['chrome'], 24, 0.002)
cylinder(C, 'king_head', 0.0365, (KING_X, H5 - 0.062, 0), (KING_X, H5 - 0.084, 0), M['chrome'], 24, 0.004)
cylinder(C, 'king_ring', 0.11, (KING_X, H5, 0), (KING_X, H5 - 0.003, 0), M['dark'], 32, 0.001)
con = [(XF, H5 + 0.02), (-9.30, H5 + 0.02), (CON_X1 - 0.15, BOT), (CON_X1, BOT), (CON_X1, CON_TOP), (XF, CON_TOP)]
for s in (-1, 1):
    prism_xy(C, 'con_side', con, s * (BZ - 0.006), s * (BZ + 0.006), P, 0.0)
    box2(C, 'con_top_lip', XF, CON_X1, CON_TOP - 0.012, CON_TOP, s * (BZ - 0.06), s * (BZ + 0.012), P, 0.002)
    # alt başlık (eğimli bölüm)
    beam(C, 'con_flange', (-9.30, H5 + 0.026, s * BZ), (CON_X1 - 0.15, BOT + 0.006, s * BZ), 0.012, 0.12, P, 0.002)
    for x in (-9.9, -9.0, -8.45):
        yb = H5 + 0.02 if x < -9.3 else H5 + 0.02 - (H5 + 0.02 - BOT) * (x + 9.3) / (9.3 + CON_X1 - 0.15)
        box2(C, 'con_rib', x - 0.005, x + 0.005, yb + 0.01, CON_TOP - 0.012, s * (BZ + 0.006), s * (BZ + 0.05), P, 0.0)
box2(C, 'con_front', XF, XF + 0.012, H5 + 0.02, CON_TOP, -BZ - 0.006, BZ + 0.006, P, 0.002)
# üst kapak yalnız burnun altında (arkada koni kirişlerin arasına iner)
box2(C, 'con_cover', XF, -9.5, CON_TOP - 0.012, CON_TOP, -BZ, BZ, P, 0.002)
box2(C, 'con_cross', -9.32, -9.26, H5 + 0.02, CON_TOP - 0.012, -BZ, BZ, P, 0.002)
# burun yatağı: konsolun üstünde burnun ön alt ucunu taşıyan eğik levhalar
for s in (-1, 1):
    prism_xy(C, 'nose_saddle', [(XF + 0.02, CON_TOP), (-9.6, CON_TOP), (-9.6, under(-9.6, 0.42) + 0.04), (XF + 0.02, f_keel(XN) + 0.05)], s * 0.40, s * 0.412, P, 0.0)

# --- ana kirişler (alüminyum kutu profil, antrasit boyalı) ve traversler ---
for s in (-1, 1):
    box2(C, 'beam', CON_X1 - 0.3, -0.30, BOT, BTOP, s * (BZ - 0.05), s * (BZ + 0.05), P, 0.006)
    box2(C, 'beam_groove', CON_X1, -0.35, BOT + 0.095, BOT + 0.105, s * (BZ + 0.049), s * (BZ + 0.052), M['dark'], 0.0)
for x in (-7.45, -5.6, AXLES[0] - 0.95, (AXLES[0] + AXLES[1]) / 2 + 0.05, (AXLES[1] + AXLES[2]) / 2 + 0.05, -0.62):
    box2(C, 'cross', x - 0.04, x + 0.04, BOT + 0.03, BTOP - 0.03, -(BZ - 0.05), BZ - 0.05, P, 0.004)
box2(C, 'rear_cross', -0.42, -0.30, BOT, 1.10, -1.05, 1.05, P, 0.006)

# --- tank yatakları: koni ağızlarının iki yanında ve arkada kirişten tankın altına kutu dikmeler (berkitmeli) ---
for x in (-7.75, -6.55, -4.98, -3.15, -1.85, -0.85):
    y1 = under(x, BZ) if x < XH else 2.6
    if x > XH:
        y1 = min(y1, CAB[2])
    for s in (-1, 1):
        box2(C, 'saddle', x - 0.06, x + 0.06, BTOP, y1 + 0.03, s * (BZ - 0.05), s * (BZ + 0.05), P, 0.004)
        box2(C, 'saddle_pad', x - 0.1, x + 0.1, y1 - 0.01, y1 + 0.03, s * (BZ - 0.08), s * (BZ + 0.08), M['rubber'], 0.0)
        prism_zy(C, 'saddle_gusset', [(s * (BZ + 0.05), BTOP), (s * (BZ + 0.14), BTOP), (s * (BZ + 0.05), min(y1, BTOP + 0.24))], x - 0.005, x + 0.005, P, 0.0)

# --- yan çerçeve (alüminyum, yan koruma): üst ve alt ray, dikmeler, kirişe bağlantı kolları ---
for s in (-1, 1):
    zi, zo = s * 1.225, s * 1.272
    box2(C, 'side_top', SX0, SX1, 0.86, 0.94, zi, zo, M['alu'], 0.006)
    box2(C, 'side_bot', SX0, SX1, 0.49, 0.61, zi, zo, M['alu'], 0.006)
    for x in (SX0 + 0.03, -6.62, -5.66, SX1 - 0.03):
        box2(C, 'side_post', x - 0.03, x + 0.03, 0.61, 0.86, s * 1.23, s * 1.265, M['alu'], 0.004)
    for x in (SX0 + 0.25, -6.2, SX1 - 0.25):
        box2(C, 'side_arm', x - 0.025, x + 0.025, 0.875, 0.925, s * (BZ + 0.05), zi, M['alu'], 0.004)
        beam(C, 'side_brace', (x, 0.55, s * 1.22), (x, BOT + 0.02, s * (BZ + 0.05)), 0.04, 0.03, M['alu'], 0.003)

# --- iniş ayakları (konsolun yanlarında; JOST, 2 × 12 t) ---
landing_gear(C, LEG_X, 0.64, BZ, 1.30, M, mount_y0=0.86)

# --- aks grubu: BPW havalı süspansiyon, aks, 22,5" disk fren (silo serisi tablosu) ---
CHAMBERS = running_gear(C, AXLES, R, BZ, BOT, M, brake='disc')

# --- tekerlek başına kavisli çamurluk (siyah plastik, paslanmaz kenar), çamurluk rayı, paçalar ---
FZ0, FZ1 = 0.80, 1.24
for xa in AXLES:
    for s in (-1, 1):
        za, zb = sorted((s * FZ0, s * FZ1))
        arch(C, 'fender', xa, R, 0.585, 0.012, math.radians(18), math.radians(162), za, zb, M['plastic'], 28)
        ze = s * FZ1
        arch(C, 'fender_trim', xa, R, 0.597, 0.006, math.radians(18), math.radians(162), min(ze, ze - s * 0.03), max(ze, ze - s * 0.03), M['chrome'], 28)
        box2(C, 'fender_stay', xa - 0.02, xa + 0.02, 1.135, 1.16, s * (BZ + 0.05), s * 1.244, M['dark'], 0.003)
for s in (-1, 1):
    box2(C, 'fender_rail', FR0, FR1, 1.10, 1.18, s * 1.244, s * 1.272, M['alu'], 0.005)
    for x in (FR0 + 0.06, (AXLES[0] + AXLES[1]) / 2, (AXLES[1] + AXLES[2]) / 2, FR1 - 0.06):
        box2(C, 'rail_arm', x - 0.025, x + 0.025, 1.11, 1.16, s * (BZ + 0.05), s * 1.244, M['dark'], 0.003)
    xm = AXLES[-1] + 0.69
    box2(C, 'mudflap', xm - 0.006, xm + 0.006, 0.22, 0.98, s * 0.80, s * 1.25, M['rubber'], 0.004)
    box2(C, 'mudflap_bar', xm - 0.02, xm + 0.02, 0.97, 1.10, s * 0.80, s * 1.26, M['dark'], 0.004)

# --- hava tankları (koniler arasında, kirişlerin arasında), EBS, hava hatları ---
for z in (-0.27, 0.27):
    cylinder(C, 'air_tank', 0.13, (-6.75, 0.97, z), (-5.95, 0.97, z), P, 32, 0.025)
    for x in (-6.6, -6.1):
        cylinder(C, 'tank_strap', 0.134, (x - 0.012, 0.97, z), (x + 0.012, 0.97, z), M['galv'], 32, 0.0)
for x in (-6.6, -6.1):
    box2(C, 'tank_bar', x - 0.025, x + 0.025, BTOP, BTOP + 0.04, -(BZ + 0.04), BZ + 0.04, P, 0.003)
EBS = (-4.95, 0.99, -0.26)
box(C, 'ebs', (0.28, 0.18, 0.26), EBS, M['dark'], 0.015)
box2(C, 'ebs_bracket', EBS[0] - 0.15, EBS[0] + 0.15, 1.08, 1.09, -0.47, -0.1, P, 0.002)
for col, dz in ((M['airRed'], 0.0), (M['airYellow'], 0.022)):
    poly_tube(C, 'air_line', [(XF + 0.05, 1.30, -0.30 - dz), (XF + 0.3, 1.30, -0.40 - dz), (-9.25, 1.30, -0.42 - dz), (-8.55, 1.02, -0.42 - dz),
                             (EBS[0] - 0.4, 1.02, -0.42 - dz), (EBS[0] - 0.16, 1.0, -0.30 - dz)], 0.007, col, 2)
poly_tube(C, 'air_tank_line', [(-5.95, 0.97, -0.27), (-5.7, 1.03, -0.36), (EBS[0] - 0.3, 1.03, -0.36), (EBS[0] - 0.15, 0.99, -0.28)], 0.008, M['air'], 2)
for cx, cy, cz in CHAMBERS:
    s = 1 if cz > 0 else -1
    hose(C, 'brake_hose', [(EBS[0] + 0.15, 0.97, EBS[2] + s * 0.08), ((EBS[0] + cx) / 2, 0.95, s * 0.3), (cx, cy + 0.06, s * 0.47), (cx, cy + 0.01, s * 0.52)], 0.008, M['air'], 2)

# --- boşaltma: koni ağızları (havalandırma konisi, kelebek vana, pnömatik tahrik), alt boşaltma borusu, arkada rakor ---
DL_Y = 0.80
for xo in OUT:
    yk = f_keel(xo)
    cylinder(C, 'outlet_flange', 0.19, (xo, yk + 0.01, 0), (xo, yk - 0.02, 0), M['pipe'], 32, 0.004)
    cylinder(C, 'aeration_cone', 0.17, (xo, yk - 0.02, 0), (xo, yk - 0.10, 0), M['pipe'], 32, 0.006, r2=0.075)
    cylinder(C, 'valve_body', 0.085, (xo, yk - 0.10, 0), (xo, DL_Y + 0.05, 0), M['pipe'], 24, 0.004)
    box(C, 'valve_actuator', (0.14, 0.09, 0.1), (xo, (yk - 0.10 + DL_Y + 0.05) / 2, 0.15), M['dark'], 0.01)
    cylinder(C, 'actuator_rod', 0.012, (xo, (yk - 0.10 + DL_Y + 0.05) / 2, 0.08), (xo, (yk - 0.10 + DL_Y + 0.05) / 2, 0.1), M['chrome'], 10, 0.0)
    cylinder(C, 'tee', 0.07, (xo - 0.12, DL_Y, 0), (xo + 0.12, DL_Y, 0), M['pipe'], 24, 0.004)
dl = [(OUT[0] - 0.35, DL_Y, 0.0), (-0.75, DL_Y, 0.0), (-0.45, 0.62, 0.0), (-0.2, 0.60, 0.18), (0.02, 0.60, 0.18)]
poly_tube(C, 'discharge_line', dl, 0.057, M['pipe'], 3)
cylinder(C, 'discharge_cap', 0.07, (OUT[0] - 0.33, DL_Y, 0), (OUT[0] - 0.4, DL_Y, 0), M['pipe'], 24, 0.006)
for x in (-6.1, -3.0, -1.8):
    box2(C, 'pipe_hanger', x - 0.02, x + 0.02, DL_Y + 0.05, BOT + 0.03, -0.035, 0.035, M['dark'], 0.002)
cylinder(C, 'rear_coupling', 0.075, (-0.03, 0.60, 0.18), (0.035, 0.60, 0.18), M['pipe'], 28, 0.006)
cylinder(C, 'rear_cap', 0.08, (0.035, 0.60, 0.18), (0.05, 0.60, 0.18), M['dark'], 28, 0.004)

# --- arka: lamba barı (alüminyum), alt koruma tamponu, paçalı levha, askılar ---
for s in (-1, 1):
    box2(C, 'bar_post', -0.36, -0.30, 0.42, BOT, s * 0.72, s * 0.78, M['alu'], 0.004)
    box2(C, 'bar_arm', -0.30, -0.14, 0.76, 0.82, s * 0.72, s * 0.78, M['alu'], 0.004)
    box2(C, 'bar_arm_low', -0.30, -0.13, 0.45, 0.51, s * 0.72, s * 0.78, M['alu'], 0.004)
    beam(C, 'bar_brace', (-0.34, 0.5, s * 0.75), (-0.85, BOT + 0.02, s * BZ), 0.05, 0.04, M['alu'], 0.003)
box2(C, 'lamp_bar', -0.14, XR, 0.70, 0.92, -1.24, 1.24, M['alu'], 0.01)
box2(C, 'lamp_bar_lip', -0.14, XR - 0.005, 0.69, 0.705, -1.22, 1.22, M['alu'], 0.003)
box2(C, 'underrun', -0.13, -0.01, 0.42, 0.54, -1.18, 1.18, M['alu'], 0.012)
for s in (-1, 1):
    box2(C, 'underrun_cap', -0.135, -0.005, 0.415, 0.545, s * 1.18, s * 1.2, M['rubber'], 0.005)
box2(C, 'rear_flap', -0.07, -0.06, 0.16, 0.70, -1.2, 1.2, M['rubber'], 0.003)
for s in (-1, 1):
    box2(C, 'refl', -0.06, -0.057, 0.30, 0.38, s * 0.86, s * 1.12, M['red'], 0.0)

chassis_logos = decal_mesh('ChassisLogos', [rear_quad(-0.0565, 0.30, -0.35, 0.12 * 720 / 528, 0.12)], LOGO_W)
chassis = join(C, 'SiChassis')

# --- tekerlekler (tek model, 6 örnek) ---
wheel = build_wheel(MW)
wheels = [wheel]
first = True
for xa in AXLES:
    for s in (-1, 1):
        ob = wheel if first else bpy.data.objects.new('Wheel', wheel.data)
        if not first:
            scene.collection.objects.link(ob)
            wheels.append(ob)
        first = False
        ob.location = bl((xa, R, s * WZ))
        ob.rotation_euler = (0, 0, math.pi if s > 0 else 0)

# =====================================================================
# TANK KABUĞU (tekrarlanan fırçalanmış alüminyum, AO ikinci UV'de)
# =====================================================================
TK = Parts()
xs = []
x = XN
while x < XH - 1e-6:
    xs.append(x)
    x += (0.07 if FAST else 0.055) if x > -9.0 else 0.04
xs.append(XH)
body_rings = [[(x, y, z) for z, y in ring2d(x)] for x in xs]
rr, rc = head_rings(XH, D_R, HC_R, 1, 10 if FAST else 14, p=2.4)
rings = body_rings + rr
# ön uç: burnun küçük ön levhası (düz kapak)
loft(TK, 'tank_shell', rings, MT['tank'], (TT, TT), ((XN - 0.004, f_yc(XN) - 0.02, 0.0), rc))


def seam(x, mat):
    cu = bpy.data.curves.new('seam', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.0045
    cu.bevel_resolution = 1
    sp = cu.splines.new('POLY')
    pts = ring2d(x, 64, 24)
    sp.points.add(len(pts) - 1)
    for p, (z, y) in zip(sp.points, pts):
        v = bl((x, y, z))
        p.co = (v.x, v.y, v.z, 1.0)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new('seam', cu)
    scene.collection.objects.link(ob)
    cu.materials.append(mat)
    TK.objs.append(ob)


for x in (-9.05, -7.9, -6.15, -4.0, -2.55, XH):
    seam(x, MT['weld'])


def tank_part(ob):
    planar_uv(ob, {'TankAlu': (TT, TT)})
    return ob


# kapak boyunları (DN450)
for xd in DOMES:
    tank_part(cylinder(TK, 'dome_neck', 0.29, (xd, TOP - 0.06, 0), (xd, 3.86, 0), MT['tank'], 48, 0.006))
# arka boşaltma dolabı (üst köşeleri yuvarlatılmış)
cz, cr = CAB[4], 0.22
prof = [(-cz, CAB[2]), (cz, CAB[2])]
for i in range(9):
    t = i / 8 * math.pi / 2
    prof.append((cz - cr + cr * math.cos(t), CAB[3] - cr + cr * math.sin(t)))
for i in range(9):
    t = math.pi / 2 + i / 8 * math.pi / 2
    prof.append((-cz + cr + cr * math.cos(t), CAB[3] - cr + cr * math.sin(t)))
tank_part(prism_zy(TK, 'cabinet', prof, CAB[0], CAB[1], MT['tank'], 0.012))
tank = join(TK, 'SiloTank')
print('TANK uv layers', [u.name for u in tank.data.uv_layers])

# =====================================================================
# ÜST YAPI (tesisat görünümünde gizlenir)
# =====================================================================
B = Parts()
# kapaklar: kapak, kenet civataları, menteşe
for xd in DOMES:
    cylinder(B, 'lid', 0.305, (xd, 3.86, 0), (xd, 3.90, 0), MB['lid'], 48, 0.008)
    cylinder(B, 'lid_cap', 0.24, (xd, 3.90, 0), (xd, DOME_TOP - 0.004, 0), MB['lid'], 40, 0.012, r2=0.17)
    cylinder(B, 'lid_gasket', 0.31, (xd, 3.855, 0), (xd, 3.862, 0), MB['rubber'], 48, 0.0)
    for i in range(6):
        t = (i + 0.5) * math.pi / 3
        cx_, cz_ = xd + 0.33 * math.cos(t), 0.33 * math.sin(t)
        box(B, 'clamp', (0.05, 0.07, 0.05), (cx_, 3.875, cz_), MB['galv'], 0.006)
        cylinder(B, 'clamp_wing', 0.012, (cx_, 3.91, cz_), (cx_, 3.93, cz_), MB['galv'], 8, 0.0)
    box2(B, 'lid_hinge', xd - 0.04, xd + 0.04, 3.84, 3.9, -0.37, -0.3, MB['galv'], 0.006)
# yürüme yolu taşıyıcıları
WALK = []
x0 = -8.85
for xd in DOMES + [-1.75]:
    x1 = xd - 0.36 if xd != -1.75 else xd
    if x1 - x0 > 0.2:
        WALK.append((x0, x1))
    x0 = xd + 0.36
for a, b in WALK:
    x = a + 0.1
    while x < b:
        for s in (-1, 1):
            box2(B, 'walk_stand', x - 0.015, x + 0.015, TOP - 0.03, 3.808, s * 0.18, s * 0.21, MB['alu'], 0.002)
        x += 0.6
# katlanmış korkuluk (+z): menteşe braketleri tankın üst yanında, dikmeler yatık, üst ve diz rayı
POSTS = [-8.64, -6.97, -5.14, -3.51, -1.78]
hz, hy_ = 1.03, YC + math.sqrt(RT ** 2 - 1.0 ** 2) + 0.03
rz, ry = 0.42, 3.92
for x in POSTS:
    box(B, 'rail_hinge', (0.08, 0.06, 0.05), (x, hy_ - 0.02, hz - 0.02), MB['alu'], 0.006)
    cylinder(B, 'rail_post', 0.02, (x, hy_ + 0.02, hz), (x, ry, rz), MB['alu'], 12, 0.0)
cylinder(B, 'rail_top', 0.021, (POSTS[0] - 0.15, ry, rz), (POSTS[-1] + 0.12, ry, rz), MB['alu'], 12, 0.0)
mz, my = (hz + rz) / 2, (hy_ + 0.02 + ry) / 2
cylinder(B, 'rail_knee', 0.017, (POSTS[0] - 0.1, my, mz), (POSTS[-1] + 0.1, my, mz), MB['alu'], 12, 0.0)
cylinder(B, 'rail_cyl', 0.025, (POSTS[2] + 0.4, hy_ + 0.05, hz - 0.08), (POSTS[2] + 0.4, ry - 0.04, rz + 0.08), MB['dark'], 14, 0.004)
# merdiven (sol arka, +z): iki ray, basamaklar, üstte tutamak
LAD = [(-0.22, 0.95), (-0.55, 2.05), (-0.75, 2.9), (-1.0, 3.45), (-1.32, 3.78), (-1.62, 3.9)]
for z in (0.80, 1.17):
    poly_tube(B, 'ladder_rail', [(x, y, z) for x, y in LAD], 0.02, MB['alu'], 2)
for i in range(len(LAD) - 1):
    (xa_, ya), (xb, yb) = LAD[i], LAD[i + 1]
    n = max(1, int(math.hypot(xb - xa_, yb - ya) / 0.28))
    for j in range(n):
        t = (j + 0.5) / n
        x, y = xa_ + (xb - xa_) * t, ya + (yb - ya) * t
        cylinder(B, 'rung', 0.016, (x, y, 0.80), (x, y, 1.17), MB['alu'], 10, 0.0)
beam(B, 'ladder_stay', (-0.56, 2.05, 0.82), (-0.70, 2.05, 0.74), 0.03, 0.03, MB['alu'], 0.003)
beam(B, 'ladder_stay', (-0.97, 3.42, 0.985), (-1.12, 3.24, 0.985), 0.03, 0.03, MB['alu'], 0.003)
box2(B, 'ladder_foot', -0.31, -0.19, 0.93, 0.97, 0.76, 1.21, MB['alu'], 0.004)
# hortum boruları (her yanda iki DN200 boru üst üste, üç parça, arka kapaklı kutu, tanka askılar)
HT0, HT1 = -7.78, -4.62
for s in (-1, 1):
    zt = s * 1.11
    for yt in (1.245, 1.47):
        cylinder(B, 'hose_tube', 0.107, (HT0, yt, zt), (HT1, yt, zt), MB['black'], 32, 0.004)
        cylinder(B, 'hose_tube_end', 0.107, (HT0 - 0.04, yt, zt), (HT0, yt, zt), MB['black'], 32, 0.03, r2=0.09)
        for k in (1, 2):
            x = HT0 + (HT1 - HT0) * k / 3
            cylinder(B, 'hose_joint', 0.112, (x - 0.03, yt, zt), (x + 0.03, yt, zt), MB['black'], 32, 0.006)
    box2(B, 'hose_box', HT1, HT1 + 0.16, 1.11, 1.61, s * 0.99, s * 1.235, MB['black'], 0.02)
    box2(B, 'hose_lock', HT1 + 0.16, HT1 + 0.175, 1.33, 1.39, s * 1.08, s * 1.14, MB['galv'], 0.004)
    for x in (HT0 + 0.35, (HT0 + HT1) / 2, HT1 - 0.35):
        yt = under(x, 1.0)
        box2(B, 'hose_strap', x - 0.03, x + 0.03, 1.55, yt + 0.05, s * 0.98, s * 1.02, MB['dark'], 0.003)
        box2(B, 'hose_saddle', x - 0.035, x + 0.035, 1.12, 1.6, s * 0.99, s * 1.0, MB['dark'], 0.002)
# hava hatları: yan hat (3", sağ, çek valfli) ve ön üst hat (2", konsol önünden tepeye)
poly_tube(B, 'side_airline', [(XF + 0.2, 1.30, -0.62), (-9.4, 1.33, -0.62), (-8.0, 1.36, -0.62), (-7.7, 1.27, -0.62), (OUT[1] + 0.3, 1.27, -0.62),
                              (OUT[1] + 0.1, f_keel(OUT[1]) + 0.08, -0.25)], 0.045, MB['alu'], 2)
cylinder(B, 'air_inlet', 0.05, (XF + 0.2, 1.30, -0.62), (XF + 0.06, 1.30, -0.62), MB['brass'], 20, 0.008)
cylinder(B, 'check_valve', 0.06, (-9.9, 1.315, -0.62), (-9.72, 1.32, -0.62), MB['brass'], 20, 0.01)
poly_tube(B, 'aeration_feed', [(OUT[0] + 0.45, 1.27, -0.62), (OUT[0] + 0.15, f_keel(OUT[0]) + 0.06, -0.22)], 0.025, MB['alu'], 2)
box2(B, 'air_bracket', XF - 0.18, XF, 1.36, 1.40, -0.33, -0.23, MB['alu'], 0.003)
# ön üst hava hattı: ön levhadaki rakordan burun yüzeyi boyunca tepeye (yüzeyden 6 cm açıkta)
zt = -0.28
top_air = [(XF - 0.1, 1.5, zt)]
x = XN + 0.06
while x < -8.95:
    yc_, a_, hu_, *_ = sec(x)
    top_air.append((x, yc_ + hu_ * math.sqrt(max(0.0, 1 - (zt / a_) ** 2)) + 0.06, zt))
    x += 0.12
top_air.append((DOMES[0] - 0.45, TOP + 0.07, zt))
poly_tube(B, 'top_airline', top_air, 0.03, MB['alu'], 2)
cylinder(B, 'air_coupling', 0.045, (XF - 0.1, 1.5, zt), (XF - 0.1, 1.43, zt), MB['brass'], 16, 0.006)
for x in (-10.3, -9.7, -9.15):
    yc_, a_, hu_, *_ = sec(x)
    ys = yc_ + hu_ * math.sqrt(max(0.0, 1 - (zt / a_) ** 2))
    box2(B, 'air_clip', x - 0.02, x + 0.02, ys - 0.02, ys + 0.065, zt - 0.025, zt + 0.025, MB['dark'], 0.003)
hose(B, 'front_handle', [(XF + 0.04, 1.55, 0.3), (XF - 0.16, 1.75, 0.3), (XF - 0.16, 2.1, 0.3), (nose_x(0.3, 2.2) - 0.02, 2.2, 0.3)], 0.017, MB['alu'], 2)
# ön pozisyon lambası pabuçları (burnun alt köşelerinde)
fxl = nose_x(FRONT_Z, FRONT_Y)
for s in (-1, 1):
    box2(B, 'front_lamp_pad', fxl - 0.035, fxl + 0.08, FRONT_Y - 0.08, FRONT_Y + 0.08, s * (FRONT_Z - 0.07), s * (FRONT_Z + 0.07), MB['alu'], 0.004)
# dolap ayrıntıları: kapak, kulplar, gösterge penceresi, menteşeler
box2(B, 'cab_door', CAB[1], CAB[1] + 0.012, 1.30, 2.02, -0.5, 0.5, MB['alu'], 0.006)
for z in (-0.32, 0.32):
    box2(B, 'cab_handle', CAB[1] + 0.012, CAB[1] + 0.03, 1.36, 1.44, z - 0.03, z + 0.03, MB['dark'], 0.004)
box2(B, 'cab_window', CAB[1], CAB[1] + 0.008, 2.29, 2.43, -0.13, 0.13, MB['glass'], 0.004)
for y in (1.45, 1.9):
    box2(B, 'cab_hinge', CAB[1], CAB[1] + 0.02, y - 0.04, y + 0.04, 0.5, 0.54, MB['galv'], 0.003)
for s in (-1, 1):
    box2(B, 'cab_refl', CAB[1], CAB[1] + 0.004, 1.18, 1.24, s * 0.1, s * 0.7, MB['red'], 0.0)
body = join(B, 'SiBody')

# yürüme yolu (kaymaz sac, tekrarlanan doku)
D = Parts()
for a, b in WALK:
    box2(D, 'walkway', a, b, 3.808, 3.83, -0.22, 0.22, MD['checker'], 0.0)
walk = join(D, 'SiWalk')
planar_uv(walk, {'WalkChecker': (0.3, 0.3)})

# logolar: tankın iki yanında eğik yüzeye oturan ızgara, dolabın arkasında
import bmesh  # noqa: E402


def tank_decal(name, xc, yc, h, mat):
    w = h * 720 / 528
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    nx, ny = 10, 6
    for s in (1, -1):
        grid = []
        for j in range(ny + 1):
            row = []
            for i in range(nx + 1):
                u, v = i / nx, j / ny
                x = xc + (u - 0.5) * w * (1 if s > 0 else -1)
                y = yc + (v - 0.5) * h
                z = math.sqrt(max(RT * RT - (y - YC) ** 2, 0.0)) if y >= YC else None
                if z is None:
                    yc_, a, hu, hl, k, wb = sec(x)
                    q = min((YC - y) / hl, 1.0)
                    z = wb + (a - wb) * (1 - q ** k) ** (1 / k)
                row.append((bm.verts.new(bl((x, y, s * (z + 0.003)))), (u, v)))
            grid.append(row)
        for j in range(ny):
            for i in range(nx):
                q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
                f = bm.faces.new([c[0] for c in q])
                for lp, c in zip(f.loops, q):
                    lp[uvl].uv = c[1]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


tank_logos = tank_decal('TankLogos', -5.45, 2.78, 0.62, LOGO)
cab_logos = decal_mesh('CabLogos', [rear_quad(CAB[1] + 0.0015, 2.62, 0.0, 0.2 * 720 / 528, 0.2)], LOGO)

# =====================================================================
# UV, AO, dışa aktarma
# =====================================================================
smart_uv(chassis, 0.003)
smart_uv(wheel, 0.004)
smart_uv(body, 0.003)
size = 1024 if FAST else 2048
tank_ao = tiled_ao_setup(tank, 512 if FAST else 2048, 'si_tank_ao')
targets = bake_ao([(chassis, size, 'si_chassis_ao'), (wheel, 512 if FAST else 1024, 'si_wheel_ao'), (body, size // 2, 'si_body_ao')],
                  P, samples=16 if FAST else 96, distance=0.6)
decals = [chassis_logos, tank_logos, cab_logos]
upper = [tank, body, walk]
for ob, img in targets:
    # şasi ve tekerlekler üst yapısız pişer (tesisat görünümünde tank ve üst yapı gizli), üst yapı her şeyle birlikte
    run_bake(ob, img, hide=decals + (upper if ob in (chassis, wheel) else []))
    print('BAKED', ob.name)
run_bake(tank, tank_ao, hide=decals)
tiled_ao_finish(tank, tank_ao)
print('BAKED', tank.name)
bake_surface([(chassis, size, 'si_chassis'), (wheel, 512 if FAST else 1024, 'si_wheel'), (body, size // 2, 'si_body')],
             PROFILES, samples=8 if FAST else 16)

export_glb(os.path.join(RAW_DIR, 'silo-chassis.glb'), [chassis, chassis_logos] + wheels)
export_glb(os.path.join(RAW_DIR, 'silo-body.glb'), [tank, body, walk, tank_logos, cab_logos])
tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)
print(f'TRIS chassis={tri(chassis)} wheel={tri(wheel)} tank={tri(tank)} body={tri(body)} walk={tri(walk)}')

# --- zemin temas gölgesi ---
ground = ground_contact(os.path.join(OUT_DIR, 'silo-contact.webp'), CS, decals, FAST)

write_anchors(ANCHORS, anchors_dict())

# ================= önizleme render'ları (yalnızca kontrol) =================
if PREVIEW:
    ground.hide_render = True
    preview_renders(PREVIEW, [('side', (-5.0, 2.0, 14.0), (-5.0, 1.8, 0)), ('front34', (-15.0, 3.5, 7.0), (-7.0, 1.8, 0)), ('rear34', (4.0, 3.0, 7.0), (-3.0, 1.8, 0)),
                              ('under', (-6.0, 0.35, 5.5), (-5.0, 1.0, 0))])
