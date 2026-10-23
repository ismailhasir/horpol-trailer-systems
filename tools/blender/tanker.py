# Akaryakıt tankeri (alüminyum, 6 bölmeli, 3 akslı; referans: Kässbohrer K.STB E 45 / 6 - 14 / 24). Blender'da betikle
# modellenir; şasi, tekerlekler, tank ve üst yapı AO + yüzey dokusu (toz, kenar aşınması) pişirilerek GLB'ye aktarılır.
# Sitenin okuyacağı bağlantı noktaları aynı ölçülerden JSON olarak yazılır. Belge: docs/Tanker Dorse/README.md
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/tanker.py -- [--fast] [--anchors] [--preview <klasör>]
#   ardından: npm run models:pack -- tanker
#
# Ölçü kaynağı (teknik tablo): eyer yüksekliği H5 1.250, tank çapı 2.350, dingil mesafesi 7.750, yükseklik (boş) 3.330,
# 45 m³ brüt / 42 m³ net, 6 × 7.000 l bölme, iki ekstrüzyon alüminyum kutu profil şasi + alüminyum çapraz bağlantılar,
# BPW havalı süspansiyon ve kampanalı fren (3 × 9 t), 385/65 R22,5, havuz tipi hortum taşıyıcı, üstten ve alttan dolum.
# Broşürün ölçekli yan/arka çiziminden (133,4 px/m; dingil mesafesi ve genişlik 2.550 ile doğrulandı): toplam boy ~12,41 m,
# king pin arka uca 10,88 m, iniş ayağı king pinin 2,54 m arkasında, akslar arası 1,31 m, tank üstü 3,20 m, devrilme
# korkuluğu üstü 3,33 m, arka görünüşte tank Ø2,35 (merkez 2,025 m, alt 0,85 m). Ön kapak altı ~1,36 m: tank önde daralan
# konik (Ø~1,84 → Ø2,35, üst çizgi yatay), kapak ve ön konik bölüm king pin plakasının üstünde. Fotoğraftan: tankın alt
# yanlarında havuz tipi beyaz hortum rafı (eğik arka uç), damla desenli alüminyum çamurluklar, ön aksın önünde API dolum
# dolabı, arkada yangın tüpü ve dökülme kiti kutuları, ADR levhaları. Kesin olmayanlar (doğrulanmadı): konikliğin bittiği
# yer, kirişlerin kesiti, dolap içi düzen; tablo boyu (K.STB E 39 için 11.420) bu model için verilmemiş.
import bpy
import math
import os
import sys

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in argv
ANCHORS_ONLY = '--anchors' in argv
BUMPERS_ONLY = '--bumpers' in argv  # yalnız tampon türevleri: tools/blender/out/<tip>-bumper-*.glb
PREVIEW = os.path.abspath(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
OUT_DIR = os.path.abspath('src/assets/models')
RAW_DIR = os.path.abspath('tools/blender/out')
ANCHORS = os.path.abspath('src/configurator/engine/tanker-anchors.json')

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import (  # noqa: E402
    Parts, arch, bake_ao, bake_surface, beam, bl, box, box2, build_wheel, cylinder, decal_mesh, export_glb,
    galvanized_checker_tile, ground_contact, hose, join, landing_gear, logo_material, loft, material, np_image, pchip,
    planar_uv, poly_tube, preview_renders, prism_xy, prism_zy, rear_quad, run_bake, running_gear, smart_uv, tex_material,
    write_anchors,
)
from bumpers import BUMPERS, LEN as BUMPER_LEN, MM as BMM, T as BT, anchors_for, build_mudflap, export_variants, web_x  # noqa: E402

scene = bpy.context.scene

# ================= ölçüler (metre; x: arka uç 0, ön -L) =================
L = 12.41  # çizimdeki toplam boy (ön havalandırma rakoru dahil)
W = 2.55
W2 = W / 2
XR = 0.0
R = 0.536  # 385/65 R22,5
WZ = 1.02
H5 = 1.25
KING_X = -10.88
WB = 7.75
AX_MID = KING_X + WB
AXLES = [AX_MID - 1.31, AX_MID, AX_MID + 1.31]
LEG_X = KING_X + 2.54
# tank: üst çizgi yatay; önde konik (yarıçap 0,92 → 1,175), arkada silindir; bombeli kapaklar
TOP = 3.20
XT0 = -11.87  # ön kapak tabanı
XT1 = -8.20  # konikliğin bittiği yer (doğrulanmadı)
XT2 = -0.76  # arka kapak tabanı
DF, DR = 0.36, 0.54  # kapak derinlikleri
XF = XT0 - DF  # tankın en önü
f_r = pchip([XT0, (XT0 + XT1) / 2, XT1 - 0.35, XT1 + 0.35, XT2], [0.92, 1.0475, 1.162, 1.175, 1.175])
RAIL_TOP = 3.33  # devrilme korkuluğu (ADR) üstü
RAIL_Z = 0.68
RAIL_X0, RAIL_X1 = -10.97, XT2
BZ = 0.50  # ana kiriş ekseni (yanal)
PLATE_X0, PLATE_X1 = -12.0, -9.75  # king pin plakası
TR_X0, TR_X1 = -7.47, -0.81  # hortum rafı (havuz tipi)
TR_Y0, TR_Y1 = 1.18, 1.36
CAB_X0, CAB_X1 = -7.47, -5.20  # API dolum dolabı (+z)
HY = 1.16  # tesisat: hortum rafının altında
SOCKET_Y = 1.36
LAMP_Y = 0.56
PLATE_Y = 0.56
FRONT_X, FRONT_Y, FRONT_Z = -11.48, 1.80, 1.02  # ön pozisyon lambaları: yan ADR panolarının ön ucunda
CS = (XF - 0.4, XR + 0.5, -W2 - 0.45, W2 + 0.45)
NR = 72  # tank halkası nokta sayısı


def cy(x):
    return TOP - f_r(x)


def under(x, z):
    """Tankın alt yüzeyinin yanal z'deki yüksekliği"""
    r = f_r(x)
    return cy(x) - math.sqrt(max(r * r - z * z, 0.0))


def surf_z(x, y):
    """Tank yan yüzeyinin y yüksekliğindeki z'si"""
    r = f_r(x)
    return math.sqrt(max(r * r - (y - cy(x)) ** 2, 0.0))


def ring(x, n=NR):
    """Kesit halkası (altta başlar): [(z, y)]"""
    r, c = f_r(x), cy(x)
    return [(r * math.sin(2 * math.pi * i / n), c - r * math.cos(2 * math.pi * i / n)) for i in range(n)]


def head(x0, d, sign, n, p):
    base = ring(x0)
    c = cy(x0)
    out = []
    for i in range(1, n + 1):
        e = math.sin((math.pi / 2) * i / (n + 0.6))
        sg = (1.0 - e ** p) ** (1.0 / p)
        out.append([(x0 + sign * d * e, c + (y - c) * sg, z * sg) for z, y in base])
    return out, (x0 + sign * d, c, 0.0)


def head_x(x0, d, sign, z, y, p):
    """Bombeli kapak yüzeyinin (z, y) noktasındaki x'i (taban halkası daire)"""
    sg = min(math.hypot(z, y - cy(x0)) / f_r(x0), 1.0)
    return x0 + sign * d * (1.0 - sg ** p) ** (1.0 / p)


def compartments():
    """6 eşit hacimli bölme: [(x0, x1)] (kapaklar dahil yaklaşık)"""
    xs, vol = [], []
    v = math.pi * f_r(XT0) ** 2 * DF * 0.55  # ön kapak
    x = XT0
    dx = 0.01
    while x < XT2:
        xs.append(x)
        vol.append(v)
        v += math.pi * f_r(x + dx / 2) ** 2 * dx
        x += dx
    total = v + math.pi * f_r(XT2) ** 2 * DR * 0.55
    cuts = [XF]
    k = 1
    for x, vv in zip(xs, vol):
        if k < 6 and vv >= total * k / 6:
            cuts.append(x)
            k += 1
    cuts.append(XT2 + DR)
    return [(cuts[i], cuts[i + 1]) for i in range(6)], total


COMP, VOLUME = compartments()
DOMES = [max((a + b) / 2, RAIL_X0 + 0.45) if i == 0 else min((a + b) / 2, XT2 - 0.4) if i == 5 else (a + b) / 2 for i, (a, b) in enumerate(COMP)]
VALVES = [max(min(b - 0.3, XT2 - 0.35), XT0 + 0.3) for a, b in COMP]  # dip vanaları: bölmenin arka ucunda, tank altında


# ================= lamba montaj haritası (UN R48; yalnız JSON'a yazılır, modeli değiştirmez) =================
# Sabit parçalar: şasi (tampon, arka çerçeve, hortum rafı, kirişler) ve devrilme korkuluğu. Tank kabuğu lamba yeri değil.
# Arka tampon (2026-10-22): Horpol sac tamponu (tools/blender/bumpers.py; türev stop lambasından, sitede seçilir) eski kutu
# tamponun yerinde; arka dikmeler üst dudağa askı lamalarıyla bağlı, tozluk tamponun alt dudağına asılı.
BUMPER_X = XR  # tamponun arka dış yüzü
BUMPER_Z = 1.20  # tamponun ucu


def bumper_face(kind):
    return round(BUMPER_X + web_x(kind), 4)
PLATE_W, PLATE_H = 0.52, 0.11
SIDE_Y, SIDE_Y_END = 1.27, 1.30  # hortum rafı dış dudağı (1,18–1,36); eğik arka uçta biraz yukarı
SIDE_ZW = 1.273
# revize 2026-10-20: markerlar YALNIZ hortum rafının (beyaz koruma) dudağında; rafın önündeki braketli markerlar kaldırıldı
SIDE_X0, SIDE_X1, SIDE_N = TR_X0 + 0.35, -0.96, 5  # ilk marker raf önünden 0,35 m geride, son arkadan 0,96 m (raf ucu)
ARM_FRONT_X = TR_X0 + 0.05  # ön lastik kol: rafın en ön noktası
FRONT_X, FRONT_Z = PLATE_X0 - 0.004, 0.50  # ön pozisyon: soket plakasının (con_front, z ±0,56) iki dış kenarında, öne bakar
WORK_Z = 0.60
BEACON_Z = 0.86  # tepe lambaları: üst kuşakta çalışma lambalarının dış yanında (dorse yanına doğru)
LINE_Z, LINE_Y = 1.20, 1.215  # yan hat rafın içinde, taban (1,18–1,20) üstünde dış dudağın arkasında
TRUNK_Z = BZ - 0.08  # kutu kirişin iç yüzü
TRUNK_REAR = 0.80  # orta ve arkada: kiriş alt başlığı hizası, tankın en altının (0,85) altında
MODULE_X = -0.80  # −1,16 ve −0,45 beşikleri arasında, tankın altında
REAR_JX = -0.25  # arka traversin (−0,30…−0,20) altı, arka dikmelerin önü


def beam_bottom(x):
    t = under(x, BZ + 0.05) - 0.005
    return max(H5 + 0.02, t - 0.16) if x < PLATE_X1 else t - 0.16


def trunk_profile():
    """Önde king pin plakasının üstünden (1,30), plaka bitince kiriş alt başlığına iner, ortada ve arkada 0,80."""
    p = [[PLATE_X0, 1.30], [PLATE_X1, 1.30]]
    x = PLATE_X1 + 0.25
    while x < -7.0:
        p.append([round(x, 3), round(max(TRUNK_REAR, min(1.30, beam_bottom(x) - 0.02)), 3)])
        x += 0.25
    return p + [[-7.0, TRUNK_REAR], [XR, TRUNK_REAR]]


def mounts_dict():
    return {
        'rear': {'x': bumper_face('tek32'), 'y': LAMP_Y, 'zOuter': BUMPER_Z, 'zInner': 0.30, 'faceX': bumper_face('tek32')},
        'plate': {'x': bumper_face('tek32'), 'y': round(PLATE_Y + PLATE_H / 2 + 0.03, 3), 'z': [-0.17, 0.17], 'plateY': PLATE_Y,
                  'plateW': PLATE_W, 'plateH': PLATE_H},
        'side': {'x0': SIDE_X0, 'x1': SIDE_X1, 'y': [[-L, SIDE_Y], [TR_X1 - 0.35, SIDE_Y], [SIDE_X1, SIDE_Y_END], [XR, SIDE_Y_END]],
                 'z': SIDE_ZW, 'maxPerSide': SIDE_N, 'rule': {'firstFromFront': 3.0, 'lastFromRear': 1.0, 'maxGap': 3.0},
                 'avoid': [], 'brackets': None,
                 # yan hat: arka lambadan arka çerçevenin dış ucunda (x −0,14, z 1,06) rafın yüksekliğine çıkar, rafın içinde
                 # düz öne gider; ön pozisyon için rafın ön kolu (TR_X0+0,2) altından kirişe girer
                 'rail': {'z': LINE_Z, 'y': [[TR_X0, LINE_Y], [XR, LINE_Y]], 'rise': [-0.14, 1.06], 'exit': [TR_X0 + 0.2, 1.12]}},
        'front': {'x': FRONT_X, 'y': SOCKET_Y, 'z': FRONT_Z, 'bracket': None},
        'armFront': {'x': ARM_FRONT_X, 'y': SIDE_Y, 'z': SIDE_ZW, 'wallZ': SIDE_ZW, 'bracket': None},
        'armRear': {'x': BUMPER_X - 0.04, 'y': LAMP_Y, 'z': BUMPER_Z, 'wallZ': BUMPER_Z, 'bracket': None, 'onBumper': True},
        'bumper': anchors_for(BUMPER_X),
        'armRearAlt': {'x': -0.14, 'y': 1.08, 'z': 1.0, 'wallZ': 1.0, 'bracket': None},
        # çalışma/tepe kablosu arka traversin (−0,30…−0,20) önünde yükselir, üst kuşağın üstünden lambaya
        'work': [{'x': -0.08, 'y': 1.18, 'z': s * WORK_Z, 'dir': [1, -0.35, 0], 'rise': [-0.33, WORK_Z],
                  'bracket': [[-0.14, 1.12, s * WORK_Z], [-0.10, 1.17, s * WORK_Z]]} for s in (1, -1)],
        'beacon': [{'x': -0.14, 'y': 1.12, 'z': s * BEACON_Z, 'bracket': None, 'rise': [-0.33, BEACON_Z]} for s in (1, -1)],
        'harness': {'trunkY': TRUNK_REAR, 'trunkZ': TRUNK_Z, 'profile': trunk_profile(), 'moduleX': MODULE_X, 'rearJunctionX': REAR_JX,
                    'notes': 'Yan hatlar kutu kirişin iç yüzünde. Önde king pin plakasının üstünde tank ile plaka arası dar: orta ana hat '
                             '(z ≈ 0) x < −9,75 bölgesinde tank kabuğunun altından geçer (bilinen sınırlama, tank tesisat görünümünde '
                             'gizli). Plaka bitince demet kiriş alt başlığına iner (0,80); modül tankın en alt noktasının (0,85) altında.'},
        'parents': {'rear': 'chassis', 'plate': 'chassis', 'side': 'chassis', 'front': 'chassis', 'armFront': 'chassis',
                    'armRear': 'chassis', 'armRearAlt': 'chassis', 'work': 'chassis', 'beacon': 'body', 'harness': 'chassis'},
        'notes': 'Tank kabuğu lamba taşımaz. Revize 2026-10-20 (kullanıcı kararı): ön pozisyon soket plakasının iki dış kenarında '
                 '(x −12,004, y 1,36, z ±0,50), öne bakar, braket yok; dış kenara ~0,78 m (R48 6.9 ≤ 0,4 m, kural dışı). Yan markerlar '
                 'yalnız hortum rafının dudağında (y 1,27, z 1,273), en çok 5/yan; rafın önündeki braketli markerlar kaldırıldı. İlk '
                 'marker önden ~5,3 m, ön lastik kol rafın ön ucunda (~5,0 m; R48 6.18 ≤ 3 m, kural dışı). Yan hat rafın içinde tek '
                 'düz hat. Arka lastik kol tamponun dış ucunda (stop lambaları hizası, y 0,56; eski üst kuşak ucu armRearAlt). Çalışma '
                 'lambaları üst kuşağın üstünde, tepe lambaları aynı kuşakta onların dış yanında (z ±0,86).',
    }


def anchors_dict():
    """Sitenin okuyacağı bağlantı noktaları (three.js koordinatları; şema: src/configurator/engine/baked.ts)"""
    sections = []
    for x in (XT0, (XT0 + XT1) / 2, XT1, -6.0, -4.0, -2.0, XT2):
        sections.append([[x, y, z] for z, y in ring(x, 32)])
    # orta düzlem siluet ve ekvator çevresi
    fr, fc = head(XT0, DF, -1, 6, 2.2)
    rr, rc = head(XT2, DR, 1, 6, 2.4)
    top_i, bot_i = NR // 2, 0
    sil = [[r_[top_i][0], r_[top_i][1], 0.0] for r_ in reversed(fr)]
    x = XT0
    while x < XT2:
        sil.append([x, TOP, 0.0])
        x += 0.5
    sil += [[r_[top_i][0], r_[top_i][1], 0.0] for r_ in rr] + [[rc[0], rc[1], 0.0]]
    sil += [[r_[bot_i][0], r_[bot_i][1], 0.0] for r_ in reversed(rr)]
    x = XT2
    while x > XT0:
        sil.append([x, under(x, 0.0), 0.0])
        x -= 0.5
    sil += [[r_[bot_i][0], r_[bot_i][1], 0.0] for r_ in fr] + [[fc[0], fc[1], 0.0]]
    sections.append(sil)
    eq = [[x, cy(x), f_r(x)] for x in [XT0 + (XT2 - XT0) * i / 30 for i in range(31)]]
    sections.append(eq + [[x, y, -z] for x, y, z in reversed(eq)])
    for s in (-1, 1):
        sections.append([[RAIL_X0, RAIL_TOP, s * RAIL_Z], [RAIL_X1, RAIL_TOP, s * RAIL_Z]])
    return {
        '_source': 'tools/blender/tanker.py tarafından üretilir; elle düzenleme',
        'L': L,
        'W': W,
        'topY': RAIL_TOP,
        'rear': {'x': bumper_face('tek32'), 'lampY': LAMP_Y, 'lampZ': [0.98, 0.6], 'plateY': PLATE_Y, 'dropX': -0.16},
        'side': {'x0': -7.2, 'x1': -1.3, 'z': W2 + 0.003, 'profile': [[TR_X0, 1.27], [XR, 1.27]]},
        'front': {'x': FRONT_X - 0.005, 'y': FRONT_Y, 'z': FRONT_Z},
        'armFront': {'x': -7.3, 'y': 1.27, 'z': W2},
        'armRear': {'x': -1.25, 'y': 1.27, 'z': W2},
        'extra': {'x': -0.08, 'y': 1.04, 'z0': 0.95, 'z1': 0.6},
        'socket': {'x': PLATE_X0 - 0.005, 'y': SOCKET_Y},
        'harness': {'y': HY, 'frontX': PLATE_X0 + 0.25, 'trunkZ': 0.86, 'rearZ': 0.4,
                    'profile': [[PLATE_X0, SOCKET_Y], [-9.6, SOCKET_Y], [-9.0, HY], [-1.15, HY], [-0.95, 0.85], [XR, 0.85]]},
        'contact': {'x0': CS[0], 'x1': CS[1], 'z0': CS[2], 'z1': CS[3]},
        'sections': sections,
        'mounts': mounts_dict(),
    }


if ANCHORS_ONLY:
    write_anchors(ANCHORS, anchors_dict())
    raise SystemExit(0)

print(f'BÖLMELER {[(round(a, 2), round(b, 2)) for a, b in COMP]} hacim ~{VOLUME:.1f} m3')

# ================= malzemeler =================
# Renk düzeni: parlak beyaz tank ve üst yapı (ince gri şerit), antrasit şasi ve arka çerçeve, damla desenli alüminyum
# çamurluklar, cilalı alüminyum jant, turuncu ADR levhaları, kırmızı yangın tüpü kutusu.
ANTHRACITE = '#373d41'
M = {
    'paint': material('FramePaint', ANTHRACITE, 0.44, 0.05, 0.35),
    'dark': material('DarkSteel', '#1b1d20', 0.5, 0.4),
    'susp': material('Suspension', '#1e2023', 0.48, 0.3, 0.1),
    'rubber': material('Rubber', '#141517', 0.85, 0.0),
    'plastic': material('Plastic', '#17181a', 0.6, 0.0),
    'white': material('ChassisWhite', '#eef0f2', 0.3, 0.05, 0.5),
    'alu': material('ChassisAlu', '#c3c8ce', 0.34, 0.9),
    'pipe': material('PipeAlu', '#b9bfc6', 0.3, 0.9),
    'chrome': material('Chrome', '#e8ebee', 0.08, 1.0),
    'galv': material('Galvanized', '#9fa5ab', 0.45, 0.9),
    'red': material('ReflRed', '#c8101a', 0.3, 0.05),
    'capRed': material('CapRed', '#b3171c', 0.4, 0.0),
    'capGreen': material('CapGreen', '#1f7a3a', 0.4, 0.0),
    'grey': material('BoxGrey', '#8d9399', 0.5, 0.1),
    'fire': material('FireRed', '#c41a1f', 0.35, 0.05, 0.3),
    'orange': material('AdrOrange', '#e86a12', 0.4, 0.0),
    'black': material('AdrBlack', '#141414', 0.5, 0.0),
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
MT = {
    'paint': material('TankPaint', '#f1f2f3', 0.22, 0.0, 0.6),
    'rail': material('RailPaint', '#eceeef', 0.3, 0.05, 0.4),
    'board': material('BoardWhite', '#eceeef', 0.35, 0.05, 0.3),
    'lid': material('LidAlu', '#c7ccd2', 0.3, 0.9),
    'dark': material('TopDark', '#1f2124', 0.5, 0.4),
    'brass': material('Brass', '#b4914f', 0.3, 1.0),
    'orange': material('TopOrange', '#e86a12', 0.4, 0.0),
    'black': material('TopBlack', '#141414', 0.5, 0.0),
}
PROFILES = {
    'FramePaint': {'grime': 0.55, 'wear': 0.3},
    'Suspension': {'grime': 0.9, 'low_h': 1.0},
    'DarkSteel': {'grime': 0.8},
    'Rubber': {'grime': 0.6},
    'Plastic': {'grime': 0.6},
    'ChassisWhite': {'grime': 0.45, 'low_h': 1.3},
    'ChassisAlu': {'grime': 0.5},
    'PipeAlu': {'grime': 0.6},
    'Galvanized': {'grime': 0.45},
    'Chrome': {'grime': 0.12},
    'BoxGrey': {'grime': 0.4},
    'FireRed': {'grime': 0.3},
    'AdrOrange': {'grime': 0.25},
    'Tire': {'grime': 0.55, 'dust_mix': 0.4, 'low_h': 0.5},
    'Rim': {'grime': 0.5, 'low_h': 0.8},
    'Hub': {'grime': 0.8},
    'TankPaint': {'grime': 0.3, 'low_h': 1.5, 'dust_mix': 0.4},
    'RailPaint': {'grime': 0.3},
    'BoardWhite': {'grime': 0.3},
    'LidAlu': {'grime': 0.3},
}
gcol, gnor, gorm = galvanized_checker_tile(256 if FAST else 512)
MD = {
    'checker': tex_material('AluChecker', '#ffffff', 0.4, 0.9, albedo=np_image('alu_checker_albedo', gcol), normal=np_image('alu_checker_normal', gnor, non_color=True),
                            orm=np_image('alu_checker_orm', gorm, non_color=True)),
    'stripe': material('Stripe', '#8a9097', 0.35, 0.1),
}
P = M['paint']
LOGO = logo_material('Logo', 'public/brand/logo-blue.png')
LOGO_W = logo_material('LogoWhite', 'public/brand/logo-white.png')

# =====================================================================
# ŞASİ (tesisat görünümünde görünür)
# =====================================================================
C = Parts()
T = Parts()  # damla desenli alüminyum çamurluklar (tekrarlanan doku, AO'suz)

# --- king pin plakası, ön konsol ---
box2(C, 'king_plate', PLATE_X0, PLATE_X1, H5, H5 + 0.02, -0.62, 0.62, M['dark'], 0.003)
cylinder(C, 'king_pin', 0.0254, (KING_X, H5, 0), (KING_X, H5 - 0.062, 0), M['chrome'], 24, 0.002)
cylinder(C, 'king_head', 0.0365, (KING_X, H5 - 0.062, 0), (KING_X, H5 - 0.084, 0), M['chrome'], 24, 0.004)
cylinder(C, 'king_ring', 0.11, (KING_X, H5, 0), (KING_X, H5 - 0.003, 0), M['dark'], 32, 0.001)
box2(C, 'con_front', PLATE_X0, PLATE_X0 + 0.012, H5 + 0.02, under(PLATE_X0 + 0.1, 0.0) + 0.02, -0.56, 0.56, P, 0.002)
for s in (-1, 1):
    pts = [(PLATE_X0, H5 + 0.02), (PLATE_X1, H5 + 0.02)]
    x = PLATE_X1
    while x > PLATE_X0:
        pts.append((x, under(x, 0.56) + 0.01))
        x -= 0.25
    pts.append((PLATE_X0, under(PLATE_X0, 0.56) + 0.01))
    prism_xy(C, 'con_side', pts, s * 0.55, s * 0.562, P, 0.0)

# --- ana kirişler: tankın altını izleyen iki kutu profil (önde king pin plakasına iner) ---
for s in (-1, 1):
    top, bot = [], []
    x = PLATE_X0 + 0.05
    while x < -0.30:
        t = under(x, BZ + 0.05) - 0.005
        top.append((x, t))
        bot.append((x, max(H5 + 0.02, t - 0.16) if x < PLATE_X1 else t - 0.16))
        x += 0.2
    top.append((-0.30, under(-0.30 - 0.0, BZ + 0.05) - 0.005 if -0.30 < XT2 else 0.96))
    bot.append((-0.30, top[-1][1] - 0.16))
    prism_xy(C, 'beam', top + list(reversed(bot)), s * (BZ - 0.05), s * (BZ + 0.05), P, 0.004)
    box2(C, 'beam_groove', XT1, -0.4, 0.875, 0.885, s * (BZ + 0.049), s * (BZ + 0.052), M['dark'], 0.0)

# --- çapraz bağlantılar: tankın altını izleyen beşikler (alüminyum, antrasit) ---
CRADLES = [-11.2, -10.2, -9.2, -8.0, -6.6, -5.35, AXLES[0] + 0.62, AXLES[1] + 0.62, AXLES[2] + 0.66, -0.45]
for x in CRADLES:
    zs = [-BZ + 0.05 + (2 * BZ - 0.1) * i / 12 for i in range(13)]
    yb = under(x, BZ) - 0.17
    pts = [(z, under(x, z) - 0.005) for z in zs] + [(BZ - 0.05, yb), (-BZ + 0.05, yb)]
    prism_zy(C, 'cradle', pts, x - 0.03, x + 0.03, P, 0.0)
    for s in (-1, 1):
        box2(C, 'cradle_pad', x - 0.09, x + 0.09, under(x, s * 0.35) - 0.01, under(x, s * 0.35) + 0.012, s * 0.2, s * 0.44, M['rubber'], 0.0)

# --- yan tesisat kolları: dolabın önünde ana hat (z ±0,86) kirişten dışa uzanan kelepçe kollarına bağlı ---
for x in (-11.3, -10.4, -9.5, -8.75, -7.85):
    hy = SOCKET_Y if x < -9.6 else HY
    yb = max(under(x, BZ + 0.05) - 0.06, H5 + 0.03) if x < -9.0 else min(hy - 0.03, under(x, BZ + 0.05) - 0.06)
    for s in (-1, 1):
        box2(C, 'harness_arm', x - 0.015, x + 0.015, hy - 0.035, hy - 0.019, s * (BZ + 0.05), s * 0.92, M['dark'], 0.002)
        box2(C, 'harness_drop', x - 0.015, x + 0.015, min(yb, hy - 0.035), hy - 0.019, s * (BZ + 0.05), s * (BZ + 0.08), M['dark'], 0.002)

# --- iniş ayakları ---
landing_gear(C, LEG_X, 0.70, BZ + 0.05, under(LEG_X, BZ + 0.05) - 0.02, M, mount_y0=under(LEG_X, BZ + 0.05) - 0.17, braces=False)

# --- aks grubu: BPW havalı süspansiyon, kampanalı fren ---
CHAMBERS = running_gear(C, AXLES, R, BZ, under(AXLES[1], BZ + 0.05) - 0.165, M, brake='drum')

# --- hortum rafı (havuz tipi, beyaz): taban, dış ve iç dudak, eğik arka uç; taşıyıcı kollar ---
for s in (-1, 1):
    zo, zl, zi = s * 1.272, s * 1.248, s * 0.78
    prism_xy(C, 'trough_lip', [(TR_X0, TR_Y0), (TR_X1 - 0.19, TR_Y0), (TR_X1, TR_Y1), (TR_X0, TR_Y1)], zl, zo, M['white'], 0.004)
    prism_xy(C, 'trough_floor', [(TR_X0, TR_Y0), (TR_X1 - 0.19, TR_Y0), (TR_X1 - 0.17, TR_Y0 + 0.02), (TR_X0, TR_Y0 + 0.02)], zi, zl, M['white'], 0.0)
    box2(C, 'trough_inner', TR_X0, TR_X1 - 0.2, TR_Y0, TR_Y0 + 0.1, zi, zi + s * 0.02, M['white'], 0.002)
    box2(C, 'trough_front', TR_X0, TR_X0 + 0.02, TR_Y0, TR_Y1, zi, zl, M['white'], 0.002)
    box2(C, 'trough_edge', TR_X0, TR_X1 - 0.02, TR_Y1 - 0.015, TR_Y1, s * 1.235, zo, M['white'], 0.003)
    for x in (TR_X0 + 0.2, -5.4, AXLES[0] + 0.66, AXLES[1] + 0.66, -1.15):
        box2(C, 'trough_arm', x - 0.03, x + 0.03, TR_Y0 - 0.05, TR_Y0, s * (BZ + 0.05), s * 1.24, P, 0.003)
        if s > 0 and CAB_X0 <= x <= CAB_X1:
            continue
        beam(C, 'trough_brace', (x, TR_Y0 - 0.05, s * 1.0), (x, under(x, BZ + 0.05) - 0.12, s * (BZ + 0.05)), 0.04, 0.03, P, 0.002)

# --- damla desenli alüminyum çamurluklar (tekerlek başına kemer), taşıyıcılar; son aksın arkasında paçalar ---
for xa in AXLES:
    for s in (-1, 1):
        za, zb = sorted((s * 0.82, s * 1.245))
        arch(T, 'fender', xa, R, 0.585, 0.008, math.radians(-4), math.radians(184), za, zb, MD['checker'], 32)
        box2(C, 'fender_stay', xa - 0.025, xa + 0.025, R + 0.593, TR_Y0, s * 0.95, s * 1.0, P, 0.003)
for s in (-1, 1):
    xm = AXLES[-1] + 0.68
    box2(C, 'mudflap', xm - 0.006, xm + 0.006, 0.2, 1.0, s * 0.8, s * 1.24, M['rubber'], 0.004)
    box2(C, 'mudflap_bar', xm - 0.02, xm + 0.02, 0.98, TR_Y0, s * 0.8, s * 1.24, P, 0.004)

# --- API dolum dolabı (+z): çerçeve, kapak, altı API rakoru (kapaklı), dip vana kolları, koruma rayları ---
for x in (CAB_X0, CAB_X1):
    for z in (0.62, 1.22):
        box2(C, 'cab_post', x, x + (0.05 if x == CAB_X0 else -0.05), 0.46, TR_Y0, z, z + 0.04, P, 0.003)
box2(C, 'cab_bottom', CAB_X0, CAB_X1, 0.46, 0.49, 0.62, 1.26, P, 0.003)
box2(C, 'cab_back', CAB_X0, CAB_X1, 0.49, TR_Y0, 0.6, 0.62, P, 0.0)
for y0, y1 in ((0.50, 0.56), (0.64, 0.68)):
    box2(C, 'cab_rail', CAB_X0, CAB_X1, y0, y1, 1.24, 1.268, M['alu'], 0.004)
SLOTS = [CAB_X0 + 0.25 + i * 0.36 for i in range(6)]
box2(C, 'cab_manifold_bar', CAB_X0 + 0.05, CAB_X1 - 0.05, 0.92, 0.96, 0.95, 1.12, M['dark'], 0.003)
for i, x in enumerate(SLOTS):
    cylinder(C, 'api_body', 0.055, (x, 1.04, 0.95), (x, 1.04, 1.16), M['pipe'], 24, 0.004)
    cylinder(C, 'api_coupling', 0.065, (x, 1.04, 1.16), (x, 1.04, 1.215), M['pipe'], 24, 0.004)
    cylinder(C, 'api_cap', 0.06, (x, 1.04, 1.215), (x, 1.04, 1.235), M['capRed'] if i % 2 == 0 else M['capGreen'], 24, 0.004)
    beam(C, 'valve_lever', (x - 0.02, 0.86, 1.1), (x + 0.12, 0.80, 1.17), 0.025, 0.02, M['capRed'], 0.003)
    cylinder(C, 'valve_body', 0.06, (x, 0.74, 0.95), (x, 1.0, 0.95), M['pipe'], 20, 0.004)
# alttan boşaltma boruları: dip vanalarından dolaba (kirişler arasında, şeritler kesişmez)
front = [i for i in range(6) if VALVES[i] < SLOTS[0]]
rear = [i for i in range(6) if i not in front]
LANES = [0.25, 0.15, 0.05, -0.05, -0.15, -0.25]
assign = {}
for k, i in enumerate(front):  # öndekiler dolabın ön yuvalarına; ilk dönen en dış şeritte
    assign[i] = (SLOTS[k], LANES[k])
for k, i in enumerate(reversed(rear)):  # arkadakiler arka yuvalara; ilk dönen (en arka yuva) en dış şeritte
    assign[i] = (SLOTS[5 - k], LANES[k])
PY = 0.70
for i in range(6):
    xv = VALVES[i]
    xs_, zl = assign[i]
    yv = under(xv, 0.0)
    cylinder(C, 'foot_valve', 0.075, (xv, yv + 0.02, 0), (xv, yv - 0.1, 0), M['pipe'], 24, 0.006)
    poly_tube(C, 'bottom_pipe', [(xv, yv - 0.1, 0.0), (xv, PY, zl), (xs_, PY, zl), (xs_, PY, 0.95), (xs_, 0.74, 0.95)], 0.042, M['pipe'], 2)
for x in (-9.6, -8.6, -4.9, -3.4, -2.3):
    box2(C, 'pipe_hanger', x - 0.02, x + 0.02, PY + 0.04, under(x, BZ) - 0.17, -0.3, 0.3, M['dark'], 0.002)

# --- -z yanı: hava tankları, EBS, koruma rayları ---
for x0, x1 in ((-7.35, -6.55),):
    cylinder(C, 'air_tank', 0.14, (x0, 0.80, -0.92), (x1, 0.80, -0.92), P, 32, 0.025)
    cylinder(C, 'air_tank2', 0.10, (x0, 0.78, -0.66), (x1, 0.78, -0.66), P, 32, 0.02)
    for x in (x0 + 0.15, x1 - 0.15):
        cylinder(C, 'tank_strap', 0.144, (x - 0.012, 0.80, -0.92), (x + 0.012, 0.80, -0.92), M['galv'], 32, 0.0)
        box2(C, 'tank_hanger', x - 0.02, x + 0.02, 0.92, TR_Y0, -1.05, -0.58, P, 0.002)
EBS = (-5.75, 0.86, -0.82)
box(C, 'ebs', (0.28, 0.18, 0.26), EBS, M['dark'], 0.015)
box2(C, 'ebs_bracket', EBS[0] - 0.15, EBS[0] + 0.15, EBS[1] + 0.09, TR_Y0, -0.98, -0.94, P, 0.002)
for y0, y1 in ((0.50, 0.56), (0.64, 0.68)):
    box2(C, 'side_rail', CAB_X0, CAB_X1, y0, y1, -1.268, -1.24, M['alu'], 0.004)
for x in (CAB_X0 + 0.05, CAB_X1 - 0.05):
    box2(C, 'side_post', x - 0.025, x + 0.025, 0.5, TR_Y0, -1.24, -1.2, P, 0.003)
# (revize 2026-10-20: önden EBS'ye giden kırmızı/sarı hava hatları kaldırıldı; tesisat görünümünde demetle karışıyordu)
poly_tube(C, 'air_tank_line', [(-6.55, 0.80, -0.92), (-6.3, 0.95, -0.9), (EBS[0] - 0.3, 0.95, -0.9), (EBS[0] - 0.15, 0.88, -0.84)], 0.008, M['air'], 2)
for cx, cy_, cz in CHAMBERS:
    s = 1 if cz > 0 else -1
    hose(C, 'brake_hose', [(EBS[0] + 0.15, 0.84, -0.82 if s < 0 else -0.7), ((EBS[0] + cx) / 2, 0.8, s * 0.6), (cx, cy_ + 0.12, s * 0.6), (cx, cy_ + 0.06, s * 0.62)], 0.008, M['air'], 2)

# --- arka çerçeve: travers, dikmeler, üst kuşak, ADR levhası; tampon (damla sac üstlü), paça levhası; kutular ---
box2(C, 'rear_cross', -0.30, -0.20, 0.88, 1.04, -1.0, 1.0, P, 0.006)
for s in (-1, 1):
    box2(C, 'rear_post', -0.20, -0.08, 0.735, 1.12, s * 0.75, s * 0.81, P, 0.005)  # altı tampon askısının ayağında
box2(C, 'rear_top', -0.20, -0.08, 1.04, 1.12, -1.0, 1.0, P, 0.005)
box2(C, 'adr_panel', -0.09, -0.075, 0.74, 1.035, -0.32, 0.32, M['white'], 0.004)  # tamponun (üstü 0,722) üstünde
box2(C, 'adr_plate', -0.075, -0.068, 0.76, 1.015, -0.2, 0.2, M['orange'], 0.004)
box2(C, 'adr_line', -0.068, -0.066, 0.86, 0.875, -0.19, 0.19, M['black'], 0.0)
prism_zy(C, 'adr_diamond', [(0.26, 0.865), (0.31, 0.915), (0.36, 0.865), (0.31, 0.815)], -0.075, -0.07, M['red'], 0.0)
# (eski kutu tampon, damla sac üstü, paça levhası ve logosu kaldırıldı: lamba tamponu ve tozluk ayrı GLB, aşağıda export_variants)
# arka sol (+z): dökülme kiti kutusu (gri) ve yangın tüpü kutusu (kırmızı); tesisat tarağının altında
box2(C, 'spill_box', -1.08, -0.66, 0.32, 0.78, 0.86, 1.2, M['grey'], 0.02)
box2(C, 'spill_lid', -1.06, -0.68, 0.34, 0.76, 1.2, 1.21, M['grey'], 0.01)
box2(C, 'spill_label', -0.95, -0.79, 0.62, 0.70, 1.21, 1.213, M['airYellow'], 0.0)
box2(C, 'fire_box', -0.62, -0.32, 0.36, 0.78, 0.88, 1.18, M['fire'], 0.02)
box2(C, 'fire_latch', -0.5, -0.44, 0.66, 0.70, 1.18, 1.195, M['dark'], 0.003)
for x in (-0.9, -0.45):
    box2(C, 'box_hanger', x - 0.02, x + 0.02, 0.775, 0.805, 0.55, 1.15, P, 0.003)

chassis = join(C, 'TkChassis')

# --- arka lamba tamponu türevleri (ayrı GLB, site stop lambasına göre birini yükler): askılar, tozluk ---
MQ = {'sheet': material('BumperPaint', ANTHRACITE, 0.44, 0.05, 0.35), 'ktl': material('BumperDark', '#1b1d20', 0.5, 0.4),
      'zinc': material('BumperZinc', '#b8bdc2', 0.3, 1.0), 'rubber': material('BumperRubber', '#141517', 0.85, 0.0),
      'print': material('MudflapPrint', '#f2f3f5', 0.5, 0.0)}


def bumper_extras(Q, kind):
    """Arka dikmelerin altındaki ayak sacından üst dudağa askı lamaları (oval delikten iki M12), alt dudakta tozluk"""
    b = BUMPERS[kind]
    lip = BUMPER_X - b['d'] * BMM
    dy = ((b['h'] - BT) / 2 - b['lip'] + 13.4) * BMM
    for s in (-1, 1):
        z = s * 0.78
        box2(Q, 'post_foot', min(lip - 0.008, -0.12), lip, 0.723, 0.735, z - 0.03, z + 0.03, MQ['ktl'], 0.002)
        box2(Q, 'hanger', lip - 0.008, lip, LAMP_Y + dy - 0.035, 0.723, z - 0.03, z + 0.03, MQ['ktl'], 0.002)
        for dz in (-0.015, 0.015):
            cylinder(Q, 'bolt_head', 0.0095, (lip + BT * BMM, LAMP_Y + dy, z + dz), (lip + BT * BMM + 0.008, LAMP_Y + dy, z + dz), MQ['zinc'], 6, 0.001)
    Q.objs.append(build_mudflap(Q, MQ, lip - 0.0145, LAMP_Y - dy + 0.014, 0.14, BUMPER_LEN / 2 * BMM))  # tampon genişliğinde


export_variants('tanker', BUMPER_X, LAMP_Y, MQ, bumper_extras, RAW_DIR)
if BUMPERS_ONLY:  # yalnız tampon türevleri (lamba eklenince; AO pişirme ve render yok, dakikalar yerine saniyeler)
    raise SystemExit(0)
tiled = join(T, 'TkChassisTiled')
planar_uv(tiled, {'AluChecker': (0.3, 0.3)})

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
# TANK VE ÜST YAPI (tesisat görünümünde gizlenir)
# =====================================================================
TK = Parts()
xs = []
x = XT0
while x < XT2 - 1e-6:
    xs.append(x)
    x += 0.12 if x < XT1 + 0.4 else 0.4
xs.append(XT2)
body_rings = [[(x, y, z) for z, y in ring(x)] for x in xs]
fr, fc = head(XT0, DF, -1, 9 if FAST else 12, 2.2)
rr, rc = head(XT2, DR, 1, 9 if FAST else 12, 2.4)
loft(TK, 'tank_shell', list(reversed(fr)) + body_rings + rr, MT['paint'], (1.0, 1.0), (fc, rc))
# bölme perdeleri dışarıdan görünmez; kaynak dikişleri (bölme sınırları ve kapak birleşimleri)
for x in [b for a, b in COMP[:-1]] + [XT0, XT2]:
    if XT0 <= x <= XT2:
        cu = bpy.data.curves.new('seam', 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 0.004
        cu.bevel_resolution = 1
        sp = cu.splines.new('POLY')
        pts = ring(x, 64)
        sp.points.add(len(pts) - 1)
        for p_, (z, y) in zip(sp.points, pts):
            v = bl((x, y, z))
            p_.co = (v.x, v.y, v.z, 1.0)
        sp.use_cyclic_u = True
        ob = bpy.data.objects.new('seam', cu)
        scene.collection.objects.link(ob)
        cu.materials.append(MT['paint'])
        TK.objs.append(ob)
# devrilme korkuluğu (ADR): iki yan levha, eğik ön uç, üst başlık; kapaklar; bölme numara levhaları
for s in (-1, 1):
    zr = s * RAIL_Z
    pts = [(RAIL_X0 - 0.12, cy(RAIL_X0) + surf_z(RAIL_X0, 0) * 0 + math.sqrt(max(f_r(RAIL_X0) ** 2 - RAIL_Z ** 2, 0)) - 0.02), (RAIL_X0, RAIL_TOP)]
    x = RAIL_X0
    top_pts = [(RAIL_X1 + 0.06, RAIL_TOP)]
    bot_pts = []
    while x <= RAIL_X1 + 1e-6:
        bot_pts.append((x, cy(x) + math.sqrt(max(f_r(x) ** 2 - RAIL_Z ** 2, 0.0)) - 0.02))
        x += 0.5
    bot_pts.append((RAIL_X1 + 0.06, cy(RAIL_X1) + math.sqrt(max(f_r(RAIL_X1) ** 2 - RAIL_Z ** 2, 0.0)) - 0.02))
    poly = [pts[0]] + bot_pts + top_pts + [pts[1]]
    prism_xy(TK, 'rail_plate', poly, zr - s * 0.006, zr + s * 0.006, MT['rail'], 0.0)
    box2(TK, 'rail_cap', RAIL_X0, RAIL_X1 + 0.06, RAIL_TOP - 0.012, RAIL_TOP, zr - s * 0.05, zr + s * 0.01, MT['rail'], 0.003)
    x = RAIL_X0 + 0.6
    while x < RAIL_X1 - 0.2:
        prism_zy(TK, 'rail_rib', [(zr - s * 0.006, RAIL_TOP - 0.012), (zr - s * 0.12, RAIL_TOP - 0.012), (zr - s * 0.006, cy(x) + math.sqrt(max(f_r(x) ** 2 - RAIL_Z ** 2, 0.0)))],
                 x - 0.005, x + 0.005, MT['rail'], 0.0)
        x += 1.1
for i, xd in enumerate(DOMES):
    yt = TOP
    cylinder(TK, 'dome_neck', 0.29, (xd, yt - 0.05, 0), (xd, 3.22, 0), MT['paint'], 48, 0.006)
TK_obj = join(TK, 'TkTank')

B = Parts()
for i, xd in enumerate(DOMES):
    cylinder(B, 'lid', 0.30, (xd, 3.22, 0), (xd, 3.25, 0), MT['lid'], 48, 0.008)
    cylinder(B, 'lid_cap', 0.22, (xd, 3.25, 0), (xd, 3.285, 0), MT['lid'], 40, 0.01, r2=0.16)
    cylinder(B, 'vent_valve', 0.05, (xd + 0.12, 3.25, -0.12), (xd + 0.12, 3.31, -0.12), MT['dark'], 16, 0.006)
    cylinder(B, 'dip_cap', 0.035, (xd - 0.14, 3.25, 0.1), (xd - 0.14, 3.29, 0.1), MT['brass'], 16, 0.004)
    for k in range(6):
        t = (k + 0.5) * math.pi / 3
        box(B, 'clamp', (0.045, 0.05, 0.045), (xd + 0.315 * math.cos(t), 3.235, 0.315 * math.sin(t)), MT['dark'], 0.005)
    for s in (-1, 1):
        box2(B, 'comp_plate', xd - 0.12, xd + 0.12, RAIL_TOP - 0.11, RAIL_TOP - 0.04, s * (RAIL_Z + 0.006), s * (RAIL_Z + 0.009), MT['black'], 0.0)
# yürüme yolu (kapakların yanında, devrilme korkuluğu içinde)
for s in (-1, 1):
    box2(B, 'walk_strip', RAIL_X0 + 0.1, RAIL_X1 - 0.1, TOP + 0.015, TOP + 0.03, s * 0.36, s * 0.52, MT['lid'], 0.003)
# ön: ADR levha panoları (yanlarda), havalandırma rakoru, ön pozisyon lambası pabuçları
for s in (-1, 1):
    zb = s * 1.0
    box2(B, 'adr_board', -11.45, -10.45, 1.42, 1.92, zb - s * 0.012, zb, MT['board'], 0.006)
    box2(B, 'adr_plate', -11.35, -10.95, 1.52, 1.82, zb, zb + s * 0.006, MT['orange'], 0.004)
    box2(B, 'adr_line', -11.34, -10.96, 1.665, 1.675, zb + s * 0.006, zb + s * 0.008, MT['black'], 0.0)
    prism_xy(B, 'adr_diamond', [(-10.72, 1.52), (-10.57, 1.67), (-10.72, 1.82), (-10.87, 1.67)], zb, zb + s * 0.006, MT['orange'], 0.0)
    for x in (-11.3, -10.6):
        box2(B, 'board_stay', x - 0.02, x + 0.02, 1.62, 1.68, s * surf_z(x, 1.65) - s * 0.02, zb - s * 0.012, MT['dark'], 0.002)
    box2(B, 'front_lamp_pad', FRONT_X, FRONT_X + 0.06, FRONT_Y - 0.07, FRONT_Y + 0.07, s * (FRONT_Z - 0.06), s * (FRONT_Z + 0.06), MT['board'], 0.004)
vx = head_x(XT0, DF, -1, 0.3, 1.75, 2.2)
poly_tube(B, 'front_vent', [(vx + 0.05, 1.75, 0.3), (vx - 0.12, 1.75, 0.3), (XF - 0.12, 1.82, 0.3)], 0.03, MT['lid'], 2)
cylinder(B, 'front_coupling', 0.05, (XF - 0.12, 1.82, 0.3), (L * -1 + 0.01, 1.82, 0.3), MT['brass'], 20, 0.006)
body = join(B, 'TkBody')

# ince gri şerit (pişirmesiz, tankın yan yüzeyinde)
N = Parts()
import bmesh  # noqa: E402


def band(name, y0, y1, x0, x1, mat):
    bm = bmesh.new()
    for s in (-1, 1):
        rows = []
        x = x0
        while x <= x1 + 1e-6:
            rows.append([bm.verts.new(bl((x, y, s * (surf_z(x, y) + 0.002)))) for y in (y0, y1)])
            x += 0.25
        for a, b in zip(rows, rows[1:]):
            bm.faces.new([a[0], b[0], b[1], a[1]] if s > 0 else [a[0], a[1], b[1], b[0]])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    me.materials.append(mat)
    N.objs.append(ob)
    return ob


band('stripe', 2.33, 2.36, XT0 + 0.3, XT2 - 0.1, MD['stripe'])
decor = join(N, 'TkDecor')


# logolar: tank yanlarında (eğik yüzeye oturan ızgara) ve arka kapakta
def surface_decal(name, xc, yc, h, side_fn, mat, sides=(1, -1), rear=False):
    w = h * 720 / 528
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    nx, ny = 10, 6
    for s in sides:
        grid = []
        for j in range(ny + 1):
            row = []
            for i in range(nx + 1):
                u, v = i / nx, j / ny
                y = yc + (v - 0.5) * h
                if rear:
                    z = (u - 0.5) * w * -1
                    x = head_x(XT2, DR, 1, z, y, 2.4) + 0.004
                    p_ = (x, y, z)
                else:
                    x = xc + (u - 0.5) * w * (1 if s > 0 else -1)
                    p_ = (x, y, s * (side_fn(x, y) + 0.003))
                row.append((bm.verts.new(bl(p_)), (u, v)))
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


tank_logos = surface_decal('TankLogos', -5.2, 2.72, 0.62, surf_z, LOGO)
rear_logo = surface_decal('RearLogo', 0, 2.3, 0.55, None, LOGO, sides=(1,), rear=True)

# =====================================================================
# UV, AO, dışa aktarma
# =====================================================================
smart_uv(chassis, 0.003)
smart_uv(wheel, 0.004)
smart_uv(body, 0.004)
smart_uv(TK_obj, 0.003, angle=32.0)
size = 1024 if FAST else 2048
decals = [tank_logos, rear_logo, decor]
targets = bake_ao([(chassis, size, 'tk_chassis_ao'), (wheel, 512 if FAST else 1024, 'tk_wheel_ao'), (TK_obj, size, 'tk_tank_ao'), (body, size // 4, 'tk_body_ao')],
                  P, samples=16 if FAST else 96, distance=0.6)
upper = [TK_obj, body]
for ob, img in targets:
    run_bake(ob, img, hide=decals + (upper if ob in (chassis, wheel) else []))
    print('BAKED', ob.name)
bake_surface([(chassis, size, 'tk_chassis'), (wheel, 512 if FAST else 1024, 'tk_wheel'), (TK_obj, size, 'tk_tank'), (body, size // 4, 'tk_body')],
             PROFILES, samples=8 if FAST else 16)

export_glb(os.path.join(RAW_DIR, 'tanker-chassis.glb'), [chassis, tiled] + wheels)
export_glb(os.path.join(RAW_DIR, 'tanker-body.glb'), [TK_obj, body, decor, tank_logos, rear_logo])
tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)
print(f'TRIS chassis={tri(chassis)} wheel={tri(wheel)} tank={tri(TK_obj)} body={tri(body)} tiled={tri(tiled)}')

ground = ground_contact(os.path.join(OUT_DIR, 'tanker-contact.webp'), CS, decals, FAST)
write_anchors(ANCHORS, anchors_dict())

if PREVIEW:
    ground.hide_render = True
    preview_renders(PREVIEW, [('side', (-6.0, 2.0, 15.0), (-6.0, 1.7, 0)), ('front34', (-17.0, 3.5, 7.5), (-8.0, 1.7, 0)), ('rear34', (4.5, 3.0, 7.0), (-3.0, 1.6, 0)),
                              ('under', (-6.5, 0.35, 5.5), (-5.0, 0.9, 0))])
