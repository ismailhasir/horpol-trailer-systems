# Damper (devirmeli, 3 akslı, U tabanlı Hardox kasa; referans: Kässbohrer K.SKS B / 27 - 12 / 27). Blender'da betikle
# modellenir; şasi, tekerlekler ve kasa AO + yüzey dokusu (toz, kenar aşınması) pişirilerek GLB'ye aktarılır. Sitenin
# okuyacağı bağlantı noktaları aynı ölçülerden JSON olarak yazılır. Belge: docs/Damper Dorse/README.md
# (Önceki sürüm damper_chassis.py yarım boru kasalıydı; bu betik onun yerini alır.)
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/damper.py -- [--fast] [--anchors] [--preview <klasör>]
#   ardından: npm run models:pack -- damper
#
# Ölçü kaynağı (teknik tablo): hacim 27 m³, dingil mesafesi 4.700, eyer yüksekliği H5 1.220, yükseklik 3.130, kasa boyu
# 8.300, kasa yüksekliği 1.700 (iç 1.690); S700MC iki I kiriş + traversler, KTL; BPW AL II havalı süspansiyon, kampanalı
# fren (3 × 9 t); Hardox 450 / TUF500 kasa, U taban; HYVA 5 kademeli ön silindir.
# Broşürün ölçekli yan/arka çiziminden (117,4 px/m; dingil mesafesi 4,70 ve yükseklik 3,13 ile doğrulandı): toplam boy
# 8,84 m (ön merdiven dahil), king pin arka uca 7,56 m, akslar −4,17 / −2,86 / −1,55 m, iniş ayağı −5,15 m, şasi üstü
# 1,43 m, kiriş altı önde 1,22 (H5) → king pinin ~1,1 m arkasından 1,02 m'ye iner, kasa önü −8,0 m, kasanın arka dikmeleri
# eğik (üstte −0,71, altta −0,06 m), üst kuşak 2,74–3,13 m, yanda yatay kırımlar 2,27 ve 1,93 m, alet kutusu −6,0…−5,36 m,
# arkada katlanır alt koruma tamponu. Arka görünüşte lastik dış yüzü ~±1,10–1,14 m (dar iz).
# Kesin olmayanlar (doğrulanmadı): kasa kesitinin alt kavisi, kiriş kesiti, silindir bağlantıları, arka menteşe yeri.
import bpy
import bmesh
import math
import os
import sys

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in argv
ANCHORS_ONLY = '--anchors' in argv
PREVIEW = os.path.abspath(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
OUT_DIR = os.path.abspath('src/assets/models')
RAW_DIR = os.path.abspath('tools/blender/out')
ANCHORS = os.path.abspath('src/configurator/engine/damper-anchors.json')

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import (  # noqa: E402
    Parts, add_obj, arch, bake_ao, bake_surface, beam, bl, box, box2, build_wheel, cylinder, decal_mesh, export_glb,
    flange_path, ground_contact, hose, join, landing_gear, logo_material, loft, material, poly_tube, preview_renders,
    prism_xy, prism_zy, rear_quad, run_bake, running_gear, side_quad, smart_uv, write_anchors,
)

scene = bpy.context.scene

# ================= ölçüler (metre; x: arka uç 0, ön -L) =================
L = 8.84
W = 2.55
W2 = W / 2
XR = 0.0
R = 0.536  # 385/65 R22,5
WZ = 0.95  # dar iz (arka görünüş)
H5 = 1.22
KING_X = -7.56
WB = 4.70
AX_MID = KING_X + WB
AXLES = [AX_MID - 1.31, AX_MID, AX_MID + 1.31]
LEG_X = -5.15
CH_X0 = -8.29  # şasi önü
CH_TOP = 1.43  # şasi üstü = kasa alt çerçevesi altı
DEEP_BOT = 1.02  # derin kiriş altı
XN = -6.45  # boyun biter, kiriş derinleşmeye başlar
XD = -6.0  # derin kiriş başlar
BZ = 0.58  # I kiriş gövde ekseni
FL = 0.12  # başlık genişliği
# kasa
BX0 = -8.0  # ön duvar dış yüzü
BY0 = 1.43  # kasa alt çerçevesi altı
BTOP = 3.13
RAIL_Y = 2.74  # üst kuşak altı
RX_TOP, RX_BOT = -0.71, -0.06  # eğik arka dikmeler: üst ve alt x
HY = 1.32  # tesisat: kiriş gövdesinden geçer
SOCKET_Y = 1.32
LAMP_Y = 1.03
PLATE_Y = 0.92
CS = (CH_X0 - 0.7, XR + 0.5, -W2 - 0.45, W2 + 0.45)

# kasa kesiti (z, y), sağ yarı: dış yüz alttan üste, iç yüz üstten alta (sol yarı ayna)
OUTER = [(0.0, 1.50), (0.55, 1.50), (0.80, 1.51), (0.96, 1.535), (1.07, 1.575), (1.15, 1.645), (1.20, 1.74), (1.218, 1.86),
         (1.245, 2.30), (1.25, 2.70), (1.275, 2.74), (1.275, BTOP)]
INNER = [(1.17, BTOP), (1.165, 3.05), (1.10, 2.30), (1.06, 1.86), (1.03, 1.74), (0.97, 1.655), (0.87, 1.595), (0.72, 1.565), (0.45, 1.555), (0.0, 1.555)]


def rear_x(y):
    """Eğik arka uç: yükseklikte x"""
    return RX_BOT + (RX_TOP - RX_BOT) * (y - BY0) / (BTOP - BY0)


def outer_z(y):
    for (z0, y0), (z1, y1) in zip(OUTER, OUTER[1:]):
        if y0 <= y <= y1 and y1 > y0:
            return z0 + (z1 - z0) * (y - y0) / (y1 - y0)
    return OUTER[-1][0]


def ring_pts():
    """Kapalı kesit halkası (U kabuk): dış sağ (alttan üste) → üst kenar → iç sağ (üstten alta) → iç sol → dış sol"""
    right = OUTER + INNER
    left = [(-z, y) for z, y in reversed(right)]
    pts = right + left
    out = []
    for p in pts:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    if math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    return out


def outline():
    """Kasanın dış çevresi (önden görünüş): dış sağ + üst + dış sol"""
    # sol yarı üstten alta; yalnız alt orta nokta (z 0) tekrarı atılır. Eskiden [1:-1] sol üst köşeyi de atıyordu:
    # tesisat çerçevesinde üstte eğik çizgi ve ön duvarda kesik köşe (revize 2026-10-20)
    right = OUTER
    return right + [(-z, y) for z, y in reversed(right)][:-1]


def open_u(ol):
    """Üstü açık kasa kesiti: kapalı çizgi döngüsünde üst kenar çizilmesin diye U geri izlenir (aynı çizgiler)"""
    return ol + ol[-2:0:-1]


# ================= lamba montaj haritası (UN R48; yalnız JSON'a yazılır, modeli değiştirmez) =================
# Kasa devrilir: lamba, kol ve braketler YALNIZ şasiye bağlanır (kirişler, ön travers, arka lamba levhası, lamba kolları, merdiven).
LP_Z = 1.20  # box2 'lamp_plate' z 0,30–1,20, y 0,96–1,12, x −0,06…0
# revize 2026-10-20: lamba levhanın ortasında (gövde 0,966–1,114 levhanın içinde kalır, alttan taşmaz). LZD 3194 sis
# kanalının üst kenarı ~1,03 m olur (R48 ≤ 1,0; kullanıcı kararı, bilinçli)
REAR_LAMP_Y = 1.04
PLATE_W, PLATE_H = 0.52, 0.11
# plaka tutucu lamba levhasının hemen altında, arka yüzü levhayla aynı düzlemde (x 0): ikisi tek parça görünür
PH_Y0, PH_Y1, PH_Z = 0.78, 0.96, 0.36
PLATE_C = 0.87
# yan markerlar kasanın alt kenar profilinin ('side_bottom', y 1,565–1,655) dış yüzünde: braket/çubuk yok
SIDE_Y = 1.61
SIDE_ZW = round(OUTER[4][0] + (OUTER[5][0] - OUTER[4][0]) * (1.62 - OUTER[4][1]) / (OUTER[5][1] - OUTER[4][1]) + 0.03, 3)
SIDE_X0, SIDE_X1, SIDE_N = -6.19, -0.95, 5  # ilk marker önden 2,65 m, son arkadan 0,95 m
FB_X, FB_Y = CH_X0 + 0.05, 1.33  # ön braket: ön traversin (z ±0,64) ucundan dışa
FB_Z0, FB_Z1 = BZ + 0.06, 1.19
WORK = (-0.10, 1.20, 0.83)  # lamba kolunun (x −0,40…−0,06, y 1,10–1,14, z 0,80–0,86) arka ucunun üstü
BEACON = (-0.12, 1.14, 1.03)  # tepe lambaları: lamba kolu ile levha arasındaki rafta, çalışma lambalarının dışında
TRUNK_Z = BZ - 0.03
REAR_Y = 1.25  # arkada demet menteşe kulaklarının (alt 1,33) altına iner
MODULE_X = -1.3
REAR_JX = -0.50  # arka traversin (−0,45…−0,35) ÖNÜ: arkadan bakınca travers ve lamba levhası kabloları örter
AUX_Y = 1.05  # çalışma/tepe kabloları kirişin altından, levhanın arkasından (arkadan görünmez)
# yan hat: menteşe hizasında lamba kolu ve çalışma lambasının önünden (x −0,20, z 0,83; arkadan levha, kol ve lamba örter)
# kasa altına çıkar, kasa tabanının altını izleyip alt kenar profiline girer
HINGE_X, HINGE_Z = -0.20, 0.83
UNDER = [[0.83, 1.503], [0.96, 1.523], [1.07, 1.563]]


def mounts_dict():
    fb = [[FB_X, FB_Y, FB_Z0], [FB_X, FB_Y, FB_Z1]]
    return {
        'rear': {'x': XR, 'y': REAR_LAMP_Y, 'zOuter': LP_Z, 'zInner': 0.30, 'faceX': XR},
        'plate': {'x': -0.01, 'y': round(PLATE_C + PLATE_H / 2 + 0.02, 3), 'z': [-0.17, 0.17], 'plateY': PLATE_C, 'plateW': PLATE_W,
                  'plateH': PLATE_H},
        'side': {'x0': SIDE_X0, 'x1': SIDE_X1, 'y': [[CH_X0, SIDE_Y], [XR, SIDE_Y]], 'z': SIDE_ZW, 'maxPerSide': SIDE_N,
                 'rule': {'firstFromFront': 3.0, 'lastFromRear': 1.0, 'maxGap': 3.0}, 'avoid': [], 'brackets': None,
                 # yan hat kasanın alt kenar profilinin içinde tek düz hat; şasiden kasaya yalnız menteşe yanında geçer
                 # (kasa devrilince kablo menteşe ekseninde kalır). Ön pozisyon ve ön kol şasi demetinden beslenir.
                 'rail': {'z': round(SIDE_ZW - 0.026, 3), 'y': [[BX0 + 0.1, SIDE_Y], [HINGE_X, SIDE_Y]], 'rise': [HINGE_X, HINGE_Z],
                          'pass': HINGE_Z, 'bend': UNDER, 'frontFromChassis': True}},
        'front': {'x': FB_X - 0.025, 'y': FB_Y, 'z': 1.17, 'bracket': fb},
        'armFront': {'x': FB_X + 0.03, 'y': FB_Y, 'z': FB_Z1, 'wallZ': FB_Z1, 'bracket': fb},
        'armRear': {'x': -0.03, 'y': REAR_LAMP_Y, 'z': LP_Z, 'wallZ': LP_Z, 'bracket': None},
        'work': [{'x': WORK[0], 'y': WORK[1], 'z': s * WORK[2], 'dir': [1, -0.35, 0], 'rise': [REAR_JX, WORK[2], AUX_Y],
                  'bracket': [[WORK[0] - 0.04, 1.14, s * WORK[2]], [WORK[0], WORK[1] - 0.02, s * WORK[2]]]} for s in (1, -1)],
        'beacon': [{'x': BEACON[0], 'y': BEACON[1], 'z': s * BEACON[2], 'bracket': None, 'rise': [REAR_JX, BEACON[2], AUX_Y]}
                   for s in (1, -1)],
        'harness': {'trunkY': HY, 'trunkZ': TRUNK_Z, 'profile': [[CH_X0, HY], [-0.6, HY], [-0.45, REAR_Y], [XR, REAR_Y]],
                    'moduleX': MODULE_X, 'rearJunctionX': REAR_JX, 'rearDrop': {'z': 0.40, 'innerX': -0.08},
                    'notes': 'Demet I kirişin gövdesinin iç yanında (y 1,32), önde traverslerin altından, arkada üstünden geçer. '
                             'Arka 7×1 hatlar arka traversin ÖNÜNDE (x −0,50, z ±0,40) lamba yüksekliğine iner, levhanın '
                             'arkasından lambalara gider: arkadan bakınca travers ve levha kabloyu örter.'},
        'parents': {'rear': 'chassis', 'plate': 'chassis', 'side': 'body', 'front': 'chassis', 'armFront': 'chassis',
                    'armRear': 'chassis', 'work': 'chassis', 'beacon': 'chassis', 'harness': 'chassis'},
        'notes': 'Kasa, kapak ve kasaya bağlı her şey devrilir. Ön pozisyon ve ön lastik kol ön traversten dışa uzanan brakette '
                 '(y 1,33, uç z 1,19; dış kenara 0,05 m). Arka kol lamba levhasının dış ucunda. Revize 2026-10-20 (kullanıcı '
                 'kararı): yan markerlar kasanın alt kenar profilinde (y 1,61, braketsiz; R48 6.18 üst sınır 1,5 m aşılır, kural '
                 'dışı); kablosu menteşe yanından kasaya geçer. Arka lambalar levhanın ortasında y 1,04 (LZD 3194 sis kanalı üstü '
                 '~1,03 m, R48 ≤ 1,0 aşılır). İki tepe lambası çalışma lambalarının dış yanında, lamba kolu ile levha arasındaki '
                 'rafta (y 1,14, z ±1,03); devrilen kasanın altında kalır, çevre görünürlüğü kasa tarafından kısıtlanır.',
    }


def anchors_dict():
    """Sitenin okuyacağı bağlantı noktaları (three.js koordinatları; şema: src/configurator/engine/baked.ts)"""
    ol = outline()
    sections = []
    sections.append([[BX0, y, z] for z, y in ol])  # ön duvar: kapalı
    for x in (-6.0, -4.0, -2.0):
        sections.append([[x, y, z] for z, y in open_u(ol)])  # ara kesitler: üstü açık
    sections.append([[rear_x(y), y, z] for z, y in ol])
    for s in (-1, 1):
        sections.append([[BX0, BTOP, s * W2], [RX_TOP, BTOP, s * W2]])
        sections.append([[BX0, BY0 + 0.07, s * 0.8], [RX_BOT, BY0 + 0.07, s * 0.8]])
    return {
        '_source': 'tools/blender/damper.py tarafından üretilir; elle düzenleme',
        'L': L,
        'W': W,
        'topY': BTOP,
        'rear': {'x': XR, 'lampY': LAMP_Y, 'lampZ': [0.95, 0.42], 'plateY': PLATE_Y, 'dropX': -0.1},
        # şasiye bağlı braketlerde (kasa devrilir); braketler sitede çizilir
        'side': {'x0': -7.9, 'x1': -0.7, 'z': W2 + 0.003, 'profile': [[CH_X0, 1.30], [XR, 1.30]], 'brackets': True},
        'front': {'x': BX0 - 0.005, 'y': 2.95, 'z': 1.1},
        'armFront': {'x': -7.75, 'y': 2.92, 'z': W2},
        'armRear': {'x': -0.95, 'y': 2.92, 'z': W2},
        'extra': {'x': -0.35, 'y': 1.25, 'z0': 0.42, 'z1': 0.18},
        'socket': {'x': CH_X0 - 0.005, 'y': SOCKET_Y},
        'harness': {'y': HY, 'frontX': CH_X0 + 0.25, 'trunkZ': 0.70, 'rearZ': 0.4, 'profile': [[CH_X0, HY], [XR, HY]]},
        'contact': {'x0': CS[0], 'x1': CS[1], 'z0': CS[2], 'z1': CS[3]},
        'sections': sections,
        'mounts': mounts_dict(),
    }


if ANCHORS_ONLY:
    write_anchors(ANCHORS, anchors_dict())
    raise SystemExit(0)

# ================= malzemeler =================
# Renk düzeni: Horpol mavisi kasa (logo rengi #1c5198, saten boya; kenarlarda aşınma), antrasit KTL şasi, siyah
# süspansiyon ve çamurluk, krom silindir kademeleri, cilalı alüminyum jant, alüminyum alt koruma tamponu.
ANTHRACITE = '#373d41'
M = {
    'paint': material('FramePaint', ANTHRACITE, 0.46, 0.05, 0.3),
    'dark': material('DarkSteel', '#1b1d20', 0.5, 0.4),
    'susp': material('Suspension', '#1e2023', 0.48, 0.3, 0.1),
    'rubber': material('Rubber', '#141517', 0.85, 0.0),
    'plastic': material('Plastic', '#121315', 0.4, 0.0, 0.2),
    'alu': material('ChassisAlu', '#c6cbd1', 0.34, 0.9),
    'chrome': material('Chrome', '#e8ebee', 0.08, 1.0),
    'galv': material('Galvanized', '#9fa5ab', 0.45, 0.9),
    'red': material('ReflRed', '#c8101a', 0.3, 0.05),
    'hyd': material('Hydraulic', '#1d1f22', 0.35, 0.2),
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
BLUE = '#1c5198'
MB = {
    'paint': material('BodyPaint', BLUE, 0.38, 0.1, 0.35),
    'inner': material('BodyInner', '#1a4a8c', 0.55, 0.15),
    'trim': material('BodyTrim', '#163f78', 0.4, 0.1, 0.3),
    'dark': material('BodyDark', '#1f2124', 0.5, 0.4),
    'chrome': material('BodyChrome', '#e6e9ec', 0.06, 1.0),
    'cyl': material('CylinderBlack', '#141517', 0.35, 0.3, 0.3),
    'red': material('BodyReflRed', '#c8101a', 0.3, 0.05),
    'yellow': material('BodyReflYellow', '#f2b600', 0.3, 0.05),
    'alu': material('LadderAlu', '#c3c8ce', 0.34, 0.9),
}
PROFILES = {
    'FramePaint': {'grime': 0.6, 'wear': 0.3},
    'Suspension': {'grime': 0.95, 'low_h': 1.0},
    'DarkSteel': {'grime': 0.85},
    'Rubber': {'grime': 0.65},
    'Plastic': {'grime': 0.6, 'low_h': 1.2},
    'ChassisAlu': {'grime': 0.5},
    'Galvanized': {'grime': 0.5},
    'Chrome': {'grime': 0.15},
    'Hydraulic': {'grime': 0.6},
    'Tire': {'grime': 0.6, 'dust_mix': 0.45, 'low_h': 0.5},
    'Rim': {'grime': 0.55, 'low_h': 0.8},
    'Hub': {'grime': 0.85},
    'BodyPaint': {'grime': 0.35, 'wear': 0.4, 'low_h': 2.0, 'dust_mix': 0.45},
    'BodyInner': {'grime': 0.9, 'wear': 0.6, 'low_h': 2.4, 'dust_mix': 0.7},
    'BodyTrim': {'grime': 0.4, 'wear': 0.45},
    'BodyChrome': {'grime': 0.15},
    'CylinderBlack': {'grime': 0.5},
    'LadderAlu': {'grime': 0.4},
}
P = M['paint']
LOGO_W = logo_material('LogoWhite', 'public/brand/logo-white.png')

# =====================================================================
# ŞASİ (tesisat görünümünde görünür; kasa devrildiğinde yerinde kalan her şey)
# =====================================================================
C = Parts()

# --- iki I kiriş: önde sığ (H5), king pinin arkasında derinleşir; üst/alt başlıklar ---
bot = [(CH_X0 + 0.02, H5 + 0.015), (XN, H5 + 0.015), (XN + 0.15, H5 - 0.01), (XD - 0.12, DEEP_BOT + 0.03), (XD, DEEP_BOT), (-0.75, DEEP_BOT), (-0.40, 1.12)]
for s in (-1, 1):
    z = s * BZ
    web = [(CH_X0 + 0.02, CH_TOP - 0.015), (-0.40, CH_TOP - 0.015)] + [(x, y + 0.015) for x, y in reversed(bot)]
    prism_xy(C, 'beam_web', web, z - 0.004, z + 0.004, P, 0.0)
    box2(C, 'beam_top', CH_X0 + 0.02, -0.40, CH_TOP - 0.015, CH_TOP, z - FL / 2, z + FL / 2, P, 0.003)
    flange_path(C, 'beam_bot', bot, FL, 0.015, z, P)
    x = XD + 0.3
    while x < -0.9:
        if all(abs(x - a) > 0.3 for a in AXLES):
            for t in (-1, 1):
                box2(C, 'stiff', x - 0.004, x + 0.004, DEEP_BOT + 0.015, CH_TOP - 0.015, z + t * 0.004, z + t * 0.055, P, 0.0)
        x += 0.7
# traversler (boru ve C profil), ön travers, king pin plakası
for x in (-7.9, -7.2, -6.6, XD + 0.1, -5.4, AXLES[0] - 0.95, (AXLES[0] + AXLES[1]) / 2, (AXLES[1] + AXLES[2]) / 2, -0.9):
    # tesisat (y 1,32) traverslerin altından/üstünden geçer: önde sığ kirişte üst, derin kirişte alt yarıda
    yc_ = 1.385 if x < XN else DEEP_BOT + 0.16
    cylinder(C, 'cross_tube', 0.045, (x, yc_, -BZ), (x, yc_, BZ), P, 20, 0.003)
    for s in (-1, 1):
        box2(C, 'cross_gusset', x - 0.08, x + 0.08, yc_ - 0.07, min(yc_ + 0.07, CH_TOP - 0.015), s * (BZ - 0.004), s * (BZ - 0.012), P, 0.0)
box2(C, 'front_cross', CH_X0, CH_X0 + 0.1, H5 + 0.02, CH_TOP, -(BZ + 0.06), BZ + 0.06, P, 0.006)
box2(C, 'king_plate', CH_X0 + 0.02, XN, H5, H5 + 0.015, -(BZ + 0.08), BZ + 0.08, M['dark'], 0.003)
prism_xy(C, 'king_ramp', [(CH_X0 - 0.12, H5 + 0.07), (CH_X0 + 0.02, H5), (CH_X0 + 0.02, H5 + 0.015), (CH_X0 - 0.12, H5 + 0.09)], -(BZ + 0.06), BZ + 0.06, M['dark'], 0.003)
cylinder(C, 'king_pin', 0.0254, (KING_X, H5, 0), (KING_X, H5 - 0.062, 0), M['chrome'], 24, 0.002)
cylinder(C, 'king_head', 0.0365, (KING_X, H5 - 0.062, 0), (KING_X, H5 - 0.084, 0), M['chrome'], 24, 0.004)
cylinder(C, 'king_ring', 0.11, (KING_X, H5, 0), (KING_X, H5 - 0.003, 0), M['dark'], 32, 0.001)

# --- ön: silindir alt yatağı (şasi önünde), hidrolik rakor, ön merdiven (şasiye bağlı) ---
CYL_X = -8.2
box2(C, 'cyl_base', CYL_X - 0.16, CYL_X + 0.16, CH_TOP, CH_TOP + 0.1, -0.24, 0.24, P, 0.008)
for s in (-1, 1):
    box2(C, 'cyl_lug', CYL_X - 0.08, CYL_X + 0.08, CH_TOP + 0.1, CH_TOP + 0.24, s * 0.16, s * 0.18, P, 0.006)
cylinder(C, 'cyl_trunnion', 0.035, (CYL_X, CH_TOP + 0.18, -0.2), (CYL_X, CH_TOP + 0.18, 0.2), M['chrome'], 16, 0.0)
cylinder(C, 'hyd_coupling', 0.03, (CH_X0 - 0.04, 1.36, 0.36), (CH_X0 + 0.06, 1.36, 0.36), M['galv'], 16, 0.004)
hose(C, 'hyd_hose', [(CH_X0 + 0.06, 1.36, 0.36), (CYL_X + 0.05, 1.42, 0.3), (CYL_X + 0.02, CH_TOP + 0.12, 0.14)], 0.016, M['hyd'], 2)
LZ0, LZ1 = 0.42, 0.78
for z in (LZ0, LZ1):
    box2(C, 'ladder_rail', -8.62, -8.58, 1.30, 2.66, z - 0.02, z + 0.02, M['alu'], 0.004)
y = 1.42
while y < 2.6:
    box2(C, 'ladder_step', -8.66, -8.56, y - 0.015, y + 0.015, LZ0, LZ1, M['alu'], 0.003)
    y += 0.28
# iki ayak da aynı boyda tutamağa uzanır, üstte birleşir (eskiden yalnız bir ayak tepe lambası direği olarak 3,08'e çıkıyordu)
for z in (LZ0, LZ1):
    cylinder(C, 'ladder_pole', 0.018, (-8.6, 2.66, z), (-8.6, 2.94, z), M['alu'], 12, 0.0)
cylinder(C, 'ladder_grab', 0.018, (-8.6, 2.94, LZ0 - 0.018), (-8.6, 2.94, LZ1 + 0.018), M['alu'], 12, 0.0)
for y in (1.36, 1.9):
    beam(C, 'ladder_stay', (-8.58, y, (LZ0 + LZ1) / 2), (CH_X0 + 0.02, min(y, CH_TOP - 0.05), (LZ0 + LZ1) / 2), 0.04, 0.04, M['alu'], 0.003)

# --- iniş ayakları, alet kutusu (+z), hava tankları ---
landing_gear(C, LEG_X, 0.80, BZ + 0.06, 1.28, M, mount_y0=DEEP_BOT + 0.02)
TB = (-6.0, -5.36)
box2(C, 'toolbox', TB[0], TB[1], 1.03, 1.40, 0.78, 1.18, M['plastic'], 0.02)
box2(C, 'toolbox_lid', TB[0] + 0.02, TB[1] - 0.02, 1.06, 1.37, 1.177, 1.187, M['plastic'], 0.01)
for x in (TB[0] + 0.12, TB[1] - 0.12):
    box2(C, 'toolbox_latch', x - 0.03, x + 0.03, 1.31, 1.35, 1.185, 1.2, M['galv'], 0.004)
    box2(C, 'toolbox_hanger', x - 0.02, x + 0.02, 1.40, CH_TOP - 0.02, BZ + 0.004, 1.12, P, 0.003)
for z in (-0.27, 0.27):
    cylinder(C, 'air_tank', 0.13, (-7.15, 1.06, z), (-6.55, 1.06, z), P, 32, 0.025)
    for x in (-7.0, -6.7):
        cylinder(C, 'tank_strap', 0.134, (x - 0.012, 1.06, z), (x + 0.012, 1.06, z), M['galv'], 32, 0.0)
        box2(C, 'tank_hanger', x - 0.012, x + 0.012, 1.17, CH_TOP - 0.02, z - 0.1, z + 0.1, P, 0.002)

# --- aks grubu: BPW AL II havalı süspansiyon, kampanalı fren ---
CHAMBERS = running_gear(C, AXLES, R, 0.56, DEEP_BOT, M, brake='drum')

# --- tekerlek başına kavisli çamurluk, taşıyıcılar; paçalar ---
for xa in AXLES:
    for s in (-1, 1):
        za, zb = sorted((s * 0.73, s * 1.17))
        arch(C, 'fender', xa, R, 0.585, 0.012, math.radians(14), math.radians(166), za, zb, M['plastic'], 28)
        box2(C, 'fender_stay', xa - 0.02, xa + 0.02, R + 0.59, R + 0.62, s * (BZ + 0.06), s * 1.05, M['dark'], 0.003)
        beam(C, 'fender_strut', (xa, R + 0.6, s * (BZ + 0.06)), (xa, DEEP_BOT + 0.1, s * (BZ + 0.004)), 0.03, 0.03, M['dark'], 0.002)
for s in (-1, 1):
    xm = AXLES[-1] + 0.66
    box2(C, 'mudflap', xm - 0.006, xm + 0.006, 0.2, 1.0, s * 0.73, s * 1.17, M['rubber'], 0.004)
    box2(C, 'mudflap_bar', xm - 0.02, xm + 0.02, 0.98, DEEP_BOT, s * (BZ + 0.06), s * 1.17, P, 0.004)

# --- EBS ve hava hatları ---
EBS = (-4.75, 1.14, -0.32)
box(C, 'ebs', (0.28, 0.18, 0.26), EBS, M['dark'], 0.015)
box2(C, 'ebs_bracket', EBS[0] - 0.15, EBS[0] + 0.15, EBS[1] + 0.09, CH_TOP - 0.015, -0.47, -0.22, P, 0.002)
for col, dz in ((M['airRed'], 0.0), (M['airYellow'], 0.022)):
    poly_tube(C, 'air_line', [(CH_X0 + 0.05, 1.30, -0.32 - dz), (CH_X0 + 0.3, 1.30, -0.46 - dz), (EBS[0] - 0.4, 1.30, -0.46 - dz), (EBS[0] - 0.16, 1.17, -0.30 - dz)], 0.007, col, 2)
poly_tube(C, 'air_tank_line', [(-6.55, 1.06, -0.27), (-6.3, 1.2, -0.4), (EBS[0] - 0.3, 1.2, -0.4), (EBS[0] - 0.15, 1.14, -0.3)], 0.008, M['air'], 2)
for cx, cy_, cz in CHAMBERS:
    s = 1 if cz > 0 else -1
    hose(C, 'brake_hose', [(EBS[0] + 0.15, 1.12, EBS[2] + s * 0.08), ((EBS[0] + cx) / 2, 1.0, s * 0.35), (cx, cy_ + 0.12, s * 0.58), (cx, cy_ + 0.06, s * 0.62)], 0.008, M['air'], 2)

# --- arka: kapanış traversi, devirme menteşesi (şasi kulakları), lamba taşıyıcıları, plaka tutucu, katlanır alt koruma ---
box2(C, 'rear_cross', -0.45, -0.35, DEEP_BOT + 0.05, CH_TOP - 0.015, -(BZ + 0.06), BZ + 0.06, P, 0.006)
for s in (-1, 1):
    zl = s * BZ
    prism_xy(C, 'hinge_lug', [(-0.40, CH_TOP - 0.1), (-0.05, CH_TOP - 0.1), (-0.05, CH_TOP + 0.02), (-0.40, CH_TOP - 0.03)], zl - s * 0.05, zl + s * 0.05, P, 0.004)
    cylinder(C, 'hinge_pin', 0.03, (-0.12, CH_TOP - 0.03, zl - s * 0.09), (-0.12, CH_TOP - 0.03, zl + s * 0.09), M['chrome'], 16, 0.002)
    # lamba taşıyıcıları: traversten arkaya uzanan kollar, lamba levhası (x = 0)
    box2(C, 'lamp_arm', -0.40, -0.06, 1.10, 1.14, s * 0.80, s * 0.86, P, 0.004)
    box2(C, 'lamp_plate', -0.06, XR, 0.96, 1.12, s * 0.30, s * 1.20, P, 0.006)
    # tepe lambası rafı: lamba kolundan levhanın üstüne uzanan sac (çalışma lambasının dış yanı)
    box2(C, 'beacon_shelf', -0.20, XR, 1.12, 1.14, s * 0.86, s * 1.12, P, 0.004)
    # katlanır alt koruma: kirişten eğik kollar, bar
    beam(C, 'underrun_arm', (-0.62, DEEP_BOT + 0.05, s * (BZ + 0.08)), (-0.20, 0.52, s * (BZ + 0.08)), 0.07, 0.05, P, 0.005)
    cylinder(C, 'underrun_pivot', 0.035, (-0.62, DEEP_BOT + 0.05, s * (BZ + 0.02)), (-0.62, DEEP_BOT + 0.05, s * (BZ + 0.14)), M['dark'], 14, 0.002)
    box2(C, 'underrun_cap', -0.25, -0.13, 0.44, 0.56, s * 1.19, s * 1.215, M['rubber'], 0.005)
box2(C, 'underrun_bar', -0.25, -0.13, 0.44, 0.56, -1.19, 1.19, M['alu'], 0.012)
box2(C, 'plate_holder', -0.06, XR, PH_Y0, PH_Y1 + 0.004, -PH_Z, PH_Z, P, 0.006)  # levhayla aynı arka düzlem, altına bitişik
for s in (-1, 1):
    box2(C, 'rear_refl', -0.13, -0.127, 0.47, 0.53, s * 0.5, s * 0.9, M['red'], 0.0)
chassis_logos = decal_mesh('ChassisLogos', [side_quad((TB[0] + TB[1]) / 2, 1.22, 0.16 * 720 / 528, 0.16, 1.188, 1)], LOGO_W)
chassis = join(C, 'DmChassis')

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
# KASA (tesisat görünümünde gizlenir; devrilen parça)
# =====================================================================
B = Parts()
ring = ring_pts()
front_ring = [(BX0 + 0.012, y, z) for z, y in ring]
mid = [[(x, y, z) for z, y in ring] for x in (-6.0, -4.0, -2.0)]
back_ring = [(rear_x(y) - 0.012, y, z) for z, y in ring]
shell = loft(B, 'shell', [front_ring] + mid + [back_ring], MB['paint'], (1.0, 1.0))
# iç yüzler ayrı malzeme (aşınmış, tozlu)
me = shell.data
me.materials.append(MB['inner'])
n = len(ring)
right_inner = {i for i, (z, y) in enumerate(ring) if (z, y) in INNER or (-z, y) in INNER}
for poly in me.polygons:
    vi = [v % n for v in poly.vertices]
    if all(v in right_inner for v in vi):
        poly.material_index = 1
# ön duvar (dış çevre), dikmeler, silindir üst yatağı
prism_zy(B, 'front_wall', outline(), BX0, BX0 + 0.014, MB['paint'], 0.006)
for z in (-0.95, -0.5, 0.5, 0.95):
    box2(B, 'front_rib', BX0 - 0.05, BX0, 1.52, BTOP - 0.05, z - 0.04, z + 0.04, MB['paint'], 0.006)
box2(B, 'front_band', BX0 - 0.06, BX0, RAIL_Y, BTOP, -W2, W2, MB['paint'], 0.01)
box2(B, 'cyl_bracket', CYL_X - 0.12, BX0 - 0.05, 2.78, 2.98, -0.2, 0.2, MB['paint'], 0.01)
# HYVA 5 kademeli teleskopik silindir (kapalı): dış gövde, kademe uçları (krom), üst göz
stages = [(0.135, 1.62, 2.40), (0.118, 2.40, 2.52), (0.102, 2.52, 2.62), (0.088, 2.62, 2.71), (0.074, 2.71, 2.80)]
for i, (r, y0, y1) in enumerate(stages):
    cylinder(B, 'cyl_stage', r, (CYL_X, y0, 0), (CYL_X, y1, 0), MB['cyl'] if i == 0 else MB['chrome'], 32, 0.006)
cylinder(B, 'cyl_eye', 0.06, (CYL_X, 2.86, -0.1), (CYL_X, 2.86, 0.1), MB['dark'], 20, 0.004)
cylinder(B, 'cyl_foot', 0.09, (CYL_X, CH_TOP + 0.18, 0), (CYL_X, 1.62, 0), MB['cyl'], 24, 0.006)
# üst kuşak kabuğun kendi kesitinde; tente kancaları, yatay kırımlar (dış takviye), alt kenar profili
for s in (-1, 1):
    zo = s * W2
    x = BX0 + 0.5
    while x < RX_TOP - 0.3:
        box2(B, 'tarp_hook', x - 0.04, x + 0.04, RAIL_Y + 0.08, RAIL_Y + 0.13, zo, zo + s * 0.025, MB['dark'], 0.004)
        x += 0.9
    for y, hgt in ((2.27, 0.05), (1.93, 0.05)):
        zz = s * outer_z(y)
        box2(B, 'side_crease', BX0, rear_x(y) - 0.02, y - hgt / 2, y + hgt / 2, zz, zz + s * 0.022, MB['trim'], 0.008)
    zz = s * outer_z(1.62)
    box2(B, 'side_bottom', BX0, RX_BOT - 0.04, 1.565, 1.655, zz - s * 0.02, zz + s * 0.03, MB['trim'], 0.008)
# kasa alt çerçevesi (boylamalar ve traversler, şasinin üstüne oturur), menteşe kulakları
for s in (-1, 1):
    box2(B, 'sub_rail', BX0 + 0.05, RX_BOT - 0.08, BY0, BY0 + 0.075, s * (BZ - 0.06), s * (BZ + 0.06), MB['dark'], 0.006)
    prism_xy(B, 'body_hinge', [(-0.30, BY0 + 0.07), (-0.06, BY0 + 0.07), (-0.08, CH_TOP - 0.06), (-0.16, CH_TOP - 0.07)], s * (BZ + 0.055), s * (BZ + 0.075), MB['dark'], 0.004)
x = BX0 + 0.3
while x < -0.4:
    box2(B, 'sub_cross', x - 0.04, x + 0.04, BY0 + 0.02, 1.505, -(BZ + 0.06), BZ + 0.06, MB['dark'], 0.004)
    x += 0.6
# eğik arka dikmeler, üst menteşe borusu, arka kapak (eğik), kapak kilitleri
for s in (-1, 1):
    zc = s * 1.21
    beam(B, 'rear_post', (RX_TOP - 0.06, BTOP - 0.01, zc), (RX_BOT - 0.06, BY0 + 0.05, zc), 0.11, 0.13, MB['paint'], 0.01)
    beam(B, 'post_gusset', (RX_TOP - 0.35, BTOP - 0.25, s * 1.26), (RX_TOP - 0.06, BTOP - 0.25, s * 1.26), 0.42, 0.02, MB['paint'], 0.006)
    box2(B, 'gate_lock', rear_x(1.7) - 0.1, rear_x(1.7) + 0.02, 1.64, 1.76, s * 1.06, s * 1.16, MB['dark'], 0.008)
    beam(B, 'lock_lever', (rear_x(1.7) + 0.02, 1.7, s * 1.17), (rear_x(1.35) + 0.04, 1.35, s * 1.2), 0.03, 0.03, MB['dark'], 0.004)
cylinder(B, 'gate_hinge', 0.045, (RX_TOP - 0.02, BTOP - 0.02, -1.18), (RX_TOP - 0.02, BTOP - 0.02, 1.18), MB['dark'], 20, 0.004)
# kabuğun arka ağzı: dış ve iç yüz arasındaki duvar kalınlığı kapatılır (arkadan bakınca kabuğun içi görünmesin)
cm = bmesh.new()
rim = cm.faces.new([cm.verts.new(bl((rear_x(y) - 0.012, y, z))) for z, y in ring])
rim.normal_update()
if rim.normal.x < 0:  # arkaya (+x; bl() x eksenini korur) baksın
    rim.normal_flip()
add_obj('shell_rim', cm, MB['paint'], 0.0, B)
# arka kapak: iç U çevresinden duvar kalınlığının yarısı kadar dışa taşar (ağzı tam örter, revize 2026-10-20),
# eğik düzlemde kalınlıklı levha + yatay takviyeler
gate_out = INNER[::-1] + [(-z, y) for z, y in INNER[:-1]]  # eskiden [1:-1]: sol üst köşe kesikti
gate_out = [(z * 1.03 + (0.03 if abs(z) > 0.3 else 0.0) * (1 if z >= 0 else -1), min(y, BTOP - 0.05) - (0.035 if y < 1.9 else 0.0))
            for z, y in gate_out]
gm = bmesh.new()
fa = [gm.verts.new(bl((rear_x(y) - 0.03, y, z))) for z, y in gate_out]
fb = [gm.verts.new(bl((rear_x(y) + 0.015, y, z))) for z, y in gate_out]
gm.faces.new(fa)
gm.faces.new(list(reversed(fb)))
for i in range(len(fa)):
    gm.faces.new([fa[i], fa[(i + 1) % len(fa)], fb[(i + 1) % len(fb)], fb[i]])
bmesh.ops.recalc_face_normals(gm, faces=gm.faces)
add_obj('tailgate', gm, MB['paint'], 0.006, B)
for y in (1.95, 2.25, 2.85):
    hw = outer_z(y) - 0.12
    beam(B, 'gate_rib', (rear_x(y) + 0.015, y, -hw), (rear_x(y) + 0.015, y, hw), 0.06, 0.04, MB['trim'], 0.006)
for s in (-1, 1):
    box2(B, 'gate_refl', rear_x(2.05) + 0.03, rear_x(2.05) + 0.035, 2.0, 2.1, s * 0.35, s * 0.85, MB['yellow'], 0.0)
body = join(B, 'DmBody')

# logolar: kasa yanlarında (beyaz), arka kapakta
bq = []
for s in (1, -1):
    hh = 0.42
    bq.append(side_quad(-4.6, 2.52, hh * 720 / 528, hh, s * (outer_z(2.52) + 0.004), s))
body_logos = decal_mesh('BodyLogos', bq, LOGO_W)
gy, gh = 2.55, 0.4
gw = gh * 720 / 528 / 2
gate_logo = decal_mesh('GateLogo', [[(rear_x(gy - gh / 2) + 0.0165, gy - gh / 2, gw), (rear_x(gy - gh / 2) + 0.0165, gy - gh / 2, -gw),
                                     (rear_x(gy + gh / 2) + 0.0165, gy + gh / 2, -gw), (rear_x(gy + gh / 2) + 0.0165, gy + gh / 2, gw)]], LOGO_W)

# =====================================================================
# UV, AO, dışa aktarma
# =====================================================================
smart_uv(chassis, 0.003)
smart_uv(wheel, 0.004)
smart_uv(body, 0.003, angle=50.0)
size = 1024 if FAST else 2048
decals = [chassis_logos, body_logos, gate_logo]
targets = bake_ao([(chassis, size, 'dm_chassis_ao'), (wheel, 512 if FAST else 1024, 'dm_wheel_ao'), (body, size, 'dm_body_ao')],
                  P, samples=16 if FAST else 96, distance=0.6)
for ob, img in targets:
    run_bake(ob, img, hide=decals + ([body] if ob in (chassis, wheel) else []))
    print('BAKED', ob.name)
bake_surface([(chassis, size, 'dm_chassis'), (wheel, 512 if FAST else 1024, 'dm_wheel'), (body, size, 'dm_body')], PROFILES, samples=8 if FAST else 16)

export_glb(os.path.join(RAW_DIR, 'damper-chassis.glb'), [chassis, chassis_logos] + wheels)
export_glb(os.path.join(RAW_DIR, 'damper-body.glb'), [body, body_logos, gate_logo])
tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)
print(f'TRIS chassis={tri(chassis)} wheel={tri(wheel)} body={tri(body)}')

ground = ground_contact(os.path.join(OUT_DIR, 'damper-contact.webp'), CS, decals, FAST)
write_anchors(ANCHORS, anchors_dict())

if PREVIEW:
    ground.hide_render = True
    preview_renders(PREVIEW, [('side', (-4.2, 2.0, 12.5), (-4.2, 1.6, 0)), ('front34', (-13.0, 3.2, 6.5), (-6.0, 1.7, 0)), ('rear34', (4.0, 3.4, 6.5), (-2.5, 1.6, 0)),
                              ('top', (-2.0, 7.5, 4.5), (-4.0, 1.8, 0)), ('under', (-4.5, 0.35, 5.0), (-4.0, 1.0, 0))])
