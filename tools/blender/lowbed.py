# Lowbed (sabit, uzamaz, 3 akslı alçak yükleyici; referans: Kässbohrer K.SLS 3 / 0N - 18/30). Blender'da betikle modellenir,
# ortam örtmesi (AO) dokuya pişirilir, şasi ve üst yapı ayrı GLB olarak dışa aktarılır; sitenin okuyacağı bağlantı noktaları
# (lamba, soket, tesisat) aynı ölçülerden JSON olarak yazılır (tek kaynak: bu dosya). Belge: docs/Lowbed Dorse/README.md
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/lowbed.py -- [--fast] [--anchors] [--preview <klasör>]
#   ardından: npm run models:pack   (Meshopt sıkıştırma: tools/blender/out → src/assets/models)
#
# Ölçü kaynağı (teknik doküman, broşür "K.SLS 3 / 0N - 18/30"): toplam boy 13.190, boyun boyu 3.950, platform boyu 9.240,
# genişlik 2.550, platform yüksekliği 875, eyer yüksekliği (H5) 1.250, dingil mesafesi (king pin → orta aks) 8.100 mm;
# 3 sabit BPW kampanalı aks, havalı süspansiyon; 245/70 R17,5 (yük hesabı ve fotoğraf: yan başına çift lastik);
# 45 mm sert ağaç taban, yalnız tekerleklerin üstünde damla desenli sac; S700MC şasi.
# Broşürdeki ölçekli yan/arka çizimden (76,95 px/m; boyun/platform oranı ve dingil mesafesiyle doğrulandı): king pin ön uca
# 1,31 m, aks aralığı 1,36 m, boyun üstü 1,507 m (arkada pahla 1,33 m'ye iner), boyun altı eğimi 2,9 m'den sonra, iniş ayağı
# ön uca 3,74 m, yan koruma 0,26–0,46 m, dik duran iki rampa (üstü 3,46 m, genişlik 0,86 m, z ≈ ±0,78), önde başlık ve
# önüne dik bağlı yedek lastik, boyun önünde saklama kutusu, arkada destek ayakları.
# Fotoğraftan: tekerlek üstünde kemerli yan kiriş eteği, sarı kesikli kontur bandı, kazık cepleri, rampa altında hidrolik
# silindirler, köşelerde kırmızı-beyaz uyarı levhaları. Renk düzeni antrasit gövde + dokulu taban (aşağıda "malzemeler");
# üretici kırmızısı ve logosu kullanılmaz, yalnız Horpol logosu.
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
ANCHORS = os.path.abspath('src/configurator/engine/lowbed-anchors.json')

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import (  # noqa: E402
    Parts, arc, bake_ao, bake_surface, beam, bez, bl, box, box2, brushed_alu_tile, build_wheel_set, cylinder, decal_mesh,
    export_glb, flange_path, galvanized_checker_tile, hardwood_tile, hose, join, logo_material, material, np_image, planar_uv,
    poly_tube, prism_xy, prism_zy, rear_quad, rect_x, rect_y, run_bake, select_only, side_quad, smart_uv, tex_material,
    write_anchors,
)

scene = bpy.context.scene

# ================= ölçüler (metre; x: arka uç 0, ön -L) =================
L = 13.19
W = 2.55
W2 = W / 2
XF = -L
XR = 0.0
R = 0.394  # 245/70 R17,5: Ø 787,5 mm
HW = 0.1225  # lastik yarı genişliği
RIM_R = 0.222  # 17,5" jant
TWIN = 0.28  # çift lastik merkezleri arası
WZ = 0.97  # çift tekerlek göbeği (yanal)
DECK = 0.875  # platform yüksekliği (PH)
PLANK = 0.045  # sert ağaç
FR_TOP = DECK - PLANK  # platform şasi üstü
NECK_TOP = 1.507  # boyun tabanı üstü
NFR_TOP = NECK_TOP - PLANK
H5 = 1.25  # eyer yüksekliği = king pin plakası altı
NECK_BOT = H5 + 0.015
XG = XF + 3.95  # boyun arka duvarı = platform önü (GL)
XN_T = -10.0  # boyun üst pahı başlar
CH_Y = 1.33  # pahın alt ucu (arka duvar üstü)
XN_B = -10.30  # boyun altı eğimi başlar
KING_X = XF + 1.31
WB = 8.10
AX_MID = KING_X + WB
AXLES = [AX_MID - 1.36, AX_MID, AX_MID + 1.36]
LEG_X = XF + 3.74
BZ = 0.45  # ana kiriş gövde ekseni (yanal)
FL = 0.15  # başlık genişliği
BEAM_BOT = 0.50  # platform ana kiriş altı
SIDE_BOT = 0.676  # yan kiriş altı (etek dışında)
SKIRT_Y = 0.385  # etek alt kenarı (akslar arası)
ARCH_R = 0.415
ARCH_CY = 0.38
SK0 = AXLES[0] - 0.62
SK1 = AXLES[-1] + 0.62
CHK0 = AXLES[0] - 0.55  # damla desenli sac (tekerlek üstü)
CHK1 = AXLES[-1] + 0.55
LAMP_Y = 0.45
PLATE_Y = 0.47
SOCKET_Y = 1.39
HARNESS_Y = 0.80  # platformda tesisat düzlemi (traverslerin gövdesinden geçer)
NECK_H = 1.40  # boyunda tesisat yüksekliği
RAMP_Z = 0.78
RAMP_W = 0.86
RAMP_TOP = 3.46
RAMP_X0 = 0.03
RAMP_X1 = 0.19
BOX_X1 = -11.65  # boyun önündeki saklama kutusunun arka yüzü
BOX_TOP = 1.87
HEAD_TOP = 2.0
SPARE = (XF - 0.14, 1.975, 0.0)
CS = (XF - 0.6, XR + 0.6, -W2 - 0.45, W2 + 0.45)


def side_y_profile():
    # yan kiriş levhasının ortası: boyunda düz, kaz boynunda eğimli kenarlar arasında, platformda kemer üstündeki şerit
    return [[XF, 1.39], [XN_B, 1.39], [-9.62, 1.22], [-9.30, 0.95], [XG + 0.04, 0.82], [XR, 0.82]]


# ================= lamba montaj haritası (UN R48; yalnız JSON'a yazılır, modeli değiştirmez) =================
# Sabit parçalar: şasi (lamba ve plaka tutucuları, dış yan kiriş levhası) ve kaynaklı başlık / uyarı direkleri. Rampalar lamba yeri değil.
HOLDER_Z0, HOLDER_Z1 = 0.36, 1.25  # box2 'lamp_holder' z (her yan), y 0,33–0,56
PLATE_HOLDER_X = -0.005  # plaka tutucunun arka yüzü (y 0,405–0,56)
PLATE_W, PLATE_H = 0.52, 0.11
SIDE_Y_DECK = 0.74  # platform yan kirişinde (0,676–0,875) kazık ceplerinin (≥ 0,785) altı
SIDE_Y_NECK = 1.39  # boyun yan kirişinin ortası (1,265–1,507)
SIDE_X0, SIDE_X1, SIDE_N = -11.0, -0.6, 9  # ilk marker boyunda (önden 2,19 m), son arkadan 0,6 m; yan başına en çok 9 (1,3 m)
# Yan markerlar iki sabit seviyede (kullanıcı 2026-10-22): platformda 0,74, boyunda 1,39. Tekerlek kemerlerinin (yay ± marker yarı
# boyu) ve kaz boynu eğiminin üstüne marker konmaz; eşit aralıklı yer bu bölgelere düşerse site en yakın kenara kaydırır (avoid).
MARKER_HL = 0.055  # LD 2774 yarı boyu
# kaz boynunda (pahın başladığı XN_T'den boyun arka duvarına, XG) marker yok (kullanıcı 2026-10-22)
SIDE_NECK_X1 = round(XN_T - MARKER_HL - 0.005, 3)  # boyun seviyesinin son x'i: marker pahın başlangıcından önce biter
SIDE_DECK_X0 = round(XG + 0.06, 3)  # platform seviyesinin ilk x'i: marker boyun arka duvarının arkasında başlar
# ön pozisyon: boynun ön ALT köşeleri, öne bakar (standart dorse gibi; kullanıcı 2026-10-22). LD 2773 en alt noktası tutucu
# merkezinin 37,6 mm altı: yan kirişin altını (NECK_BOT) geçmez; tutucu boyun ön kirişinin ön yüzüne oturur
FRONT_LAMP_Y = NECK_BOT + 0.038
ARM_FRONT_Y = NECK_BOT + 0.10  # lastik kollar kasanın 4 ALT köşesi: önde boyun yan kirişinin alt köşesi
ARM_REAR_X, ARM_REAR_Y = -0.06, SIDE_BOT + 0.08  # arkada platform yan kirişinin alt köşesi
# arka uyarı levhaları (direkli) kullanıcı isteğiyle kaldırıldı (2026-10-20)
# çalışma lambaları: lamba tutucusunda stop ile plaka arası (standart dorse gibi; site seçime göre z'yi hesaplar). WORK_Z yalnız
# yedek değer (LZD 3194 + RTR 3366 ile çıkan yer)
WORK_X, WORK_Z = XR + 0.016, 0.555
# tepe lambaları: başlığın üst köşelerinde kaynaklı taban sacı (alçak yükleyicilerde yaygın yer: önden ve arkadan görünür,
# rampa hareketli olduğu için arkada sabit yüksek yer yok); taban Ø150 dorse genişliğini geçmez
BEACON_X, BEACON_Z, BEACON_PLATE = XF + 0.04, W2 - 0.08, 0.01
TRUNK_Z = BZ - 0.035  # kiriş gövdesinin iç yanı
MODULE_X = -1.05  # son aksın arkasında, -1,0 traversinin üstüne oturur (tesisat görünümü)
REAR_JX = -0.16  # arka traversin önü
LAST_CROSS_X = -0.45  # son platform traversinin arka yüzü (x -0,5 … -0,45)
SIDE_TURN_X = round((LAST_CROSS_X + REAR_JX) / 2, 3)  # yan hatların yana döndüğü x: son traversle arka dağıtım arasının ortası


def side_marker_profile():
    """Yan marker yükseklik profili: boyunda levha ortası, platformda kazık ceplerinin altı (iki düz seviye; arası avoid)"""
    return [[XF, SIDE_Y_NECK], [SIDE_NECK_X1, SIDE_Y_NECK], [SIDE_DECK_X0, SIDE_Y_DECK], [XR, SIDE_Y_DECK]]


def side_avoid():
    """Marker merkezinin giremeyeceği x aralıkları: kaz boynu eğimi, tekerlek kemerleri (yay + marker yarı boyu + pay)"""
    return [[SIDE_NECK_X1, SIDE_DECK_X0]] + [[round(a - ARCH_R - MARKER_HL, 3), round(a + ARCH_R + MARKER_HL, 3)] for a in AXLES]


def top_profile():
    """Şasi üstü (tesisat görünümünde yatay hatların yüzeyi): boyun traversleri, pahlı kiriş başlığı, arka duvarın arkasından
    platform traverslerine iniş"""
    return [[XF, NFR_TOP], [XN_T, NFR_TOP], [XG - 0.03, CH_Y], [XG + 0.02, CH_Y], [XG + 0.12, FR_TOP], [XR, FR_TOP]]


def mounts_dict():
    hp = [[XF, NECK_H], [XN_B, NECK_H], [-9.90, 1.25], [-9.62, 1.08], [-9.45, 0.9], [XG - 0.06, HARNESS_Y], [XR, HARNESS_Y]]
    return {
        'rear': {'x': XR, 'y': LAMP_Y, 'zOuter': HOLDER_Z1, 'zInner': HOLDER_Z0, 'faceX': XR},
        'plate': {'x': PLATE_HOLDER_X, 'y': round(PLATE_Y + PLATE_H / 2 + 0.02, 3), 'z': [-0.17, 0.17], 'plateY': PLATE_Y,
                  'plateW': PLATE_W, 'plateH': PLATE_H},
        'side': {'x0': SIDE_X0, 'x1': SIDE_X1, 'y': side_marker_profile(), 'z': W2 + 0.001, 'maxPerSide': SIDE_N,
                 'rule': {'firstFromFront': 3.0, 'lastFromRear': 1.0, 'maxGap': 3.0}, 'avoid': side_avoid(), 'brackets': None},
        'front': {'x': XF, 'y': round(FRONT_LAMP_Y, 3), 'z': W2 - 0.06, 'bracket': None},
        'armFront': {'x': XF + 0.04, 'y': ARM_FRONT_Y, 'z': W2, 'wallZ': W2, 'bracket': None},
        'armRear': {'x': ARM_REAR_X, 'y': ARM_REAR_Y, 'z': W2, 'wallZ': W2, 'bracket': None},
        'armRearAlt': {'x': -0.05, 'y': LAMP_Y, 'z': HOLDER_Z1, 'wallZ': HOLDER_Z1, 'bracket': None},
        'work': [{'x': WORK_X, 'y': LAMP_Y, 'z': s * WORK_Z, 'dir': [1, 0, 0], 'bracket': None, 'between': True} for s in (1, -1)],
        'beacon': [{'x': BEACON_X, 'y': HEAD_TOP + BEACON_PLATE, 'z': s * BEACON_Z, 'bracket': None} for s in (1, -1)],
        'harness': {'trunkY': HARNESS_Y, 'trunkZ': TRUNK_Z, 'profile': hp, 'moduleX': MODULE_X, 'rearJunctionX': REAR_JX,
                    'top': {'y': FR_TOP, 'sideZ': round(W2 - 0.115, 3), 'turnX': SIDE_TURN_X, 'profile': top_profile()},
                    'notes': 'Boyunda traverslerin gövdesinden (y 1,40), kaz boynunda kiriş alt eğrisinin ~0,1 m üstünden iner, '
                             'platformda traverslerin gövdesinden (y 0,80) geçer; yan hat kiriş gövdesinin iç yanında. Tesisat '
                             'görünümünde yatay hatlar şasinin üstünde (top.profile: boyun, pah, platform).'},
        'parents': {'rear': 'chassis', 'plate': 'chassis', 'side': 'chassis', 'front': 'chassis', 'armFront': 'body', 'armRear': 'body',
                    'armRearAlt': 'chassis', 'work': 'chassis', 'beacon': 'body', 'harness': 'chassis'},
        'notes': 'Rampalar hareketli; lamba konmaz. Arka köşe uyarı levhaları kaldırıldı (kullanıcı, 2026-10-20). Arka lambalar alçak '
                 'tutucularda y 0,45. Yan markerlar dış yan kiriş levhasında iki düz seviyede (platform 0,74, boyun 1,39); kemer ve '
                 'kaz boynu üstüne gelmez. Ön pozisyon boynun ön alt köşelerinde, öne bakar. Lastik kollar arkada lamba tutucusunun '
                 'iki ucunda ya da stop lambasının kol yuvasında (standart dorse kuralı, yalnız arka çift). Çalışma lambaları lamba '
                 'tutucusunda stop ile plaka arasında. Tepe lambaları başlığın üst köşelerindeki taban saclarında; kabloları başlığın '
                 'arkasından köşe dikmesini izler (önden görünmez).',
    }


def anchors_dict():
    """Sitenin okuyacağı bağlantı noktaları (three.js koordinatları; şema: src/configurator/engine/baked.ts)"""
    h = RAMP_W / 2
    sections = [
        rect_y(DECK, XG, XR, W2),
        rect_y(NECK_TOP, XF, XN_T, W2),
        [[XN_T, NECK_TOP, W2], [XG, CH_Y, W2], [XG, CH_Y, -W2], [XN_T, NECK_TOP, -W2]],
        rect_x(XF, NECK_TOP, HEAD_TOP, W2),
        rect_x(BOX_X1, NECK_TOP, BOX_TOP, W2 - 0.05),
    ]
    for s in (-1, 1):
        zc = s * RAMP_Z
        sections.append([[0.11, DECK, zc + h], [0.11, RAMP_TOP, zc + h], [0.11, RAMP_TOP, zc - h], [0.11, DECK, zc - h]])
    # tesisat: boyunda traverslerin gövdesinden, kaz boynunda kiriş alt eğrisinin ~0,1 m üstünden iner
    hp = [[XF, NECK_H], [XN_B, NECK_H], [-9.90, 1.25], [-9.62, 1.08], [-9.45, 0.9], [XG - 0.06, HARNESS_Y], [XR, HARNESS_Y]]
    return {
        '_source': 'tools/blender/lowbed.py tarafından üretilir; elle düzenleme',
        'L': L,
        'W': W,
        'topY': RAMP_TOP,
        # lambalar alçak arka lamba tutucularında; dallar arka traversin önünden iner
        'rear': {'x': XR, 'lampY': LAMP_Y, 'lampZ': [1.02, 0.58], 'plateY': PLATE_Y, 'dropX': -0.2},
        'side': {'x0': XF + 0.35, 'x1': -0.5, 'z': W2 + 0.003, 'profile': side_y_profile()},
        'front': {'x': XF - 0.004, 'y': HEAD_TOP - 0.08, 'z': W2 - 0.1},
        'armFront': {'x': XF + 0.35, 'y': 1.39, 'z': W2},
        'armRear': {'x': -0.75, 'y': 0.80, 'z': W2},
        'extra': {'x': XR, 'y': 0.66, 'z0': 1.0, 'z1': 0.6},
        'socket': {'x': XF - 0.008, 'y': SOCKET_Y},
        # frontX: soket kablolarının boyuna indiği x (boyun ön kirişi ile ilk travers arası)
        'harness': {'y': HARNESS_Y, 'frontX': XF + 0.2, 'trunkZ': 0.6, 'rearZ': 0.38, 'profile': hp},
        'contact': {'x0': CS[0], 'x1': CS[1], 'z0': CS[2], 'z1': CS[3]},
        'sections': sections,
        'mounts': mounts_dict(),
    }


if ANCHORS_ONLY:
    write_anchors(ANCHORS, anchors_dict())
    raise SystemExit(0)

# ================= malzemeler =================
# Renk düzeni (Horpol): antrasit gövde (RAL 7016, saten), siyah süspansiyon/aks, galvaniz bağlantı parçaları, fırçalanmış
# alüminyum kutu ve yan koruma, gümüş jant, apitong benzeri sert ağaç taban, galvaniz damla sac. Sarı kontur bandı ve
# kırmızı-beyaz levhalar koyu zeminde öne çıkar; koyu yüzeylerde logo beyaz. Tesisat görünümünde antrasit şasi üzerinde
# renkli hatlar okunaklıdır (standart dorseyle aynı ilke).
ANTHRACITE = '#373d41'
M = {
    'paint': material('FramePaint', ANTHRACITE, 0.44, 0.05, 0.35),
    'dark': material('DarkSteel', '#1b1d20', 0.5, 0.4),
    'susp': material('Suspension', '#1e2023', 0.48, 0.3, 0.1),
    'rubber': material('Rubber', '#141517', 0.85, 0.0),
    'plastic': material('Plastic', '#17181a', 0.6, 0.0),
    'chrome': material('Chrome', '#e8ebee', 0.08, 1.0),
    'galv': material('Galvanized', '#9fa5ab', 0.45, 0.9),
    'red': material('ReflRed', '#c8101a', 0.3, 0.05),
    'yellow': material('ReflYellow', '#f2b600', 0.3, 0.05),
    'air': material('AirLine', '#24262a', 0.6, 0.0),
}
MW = {
    'tire': material('Tire', '#161719', 0.88, 0.0),
    'rim': material('Rim', '#9fa3a7', 0.4, 0.7),
    'hub': material('Hub', '#222427', 0.45, 0.5),
    'nut': material('Nut', '#c4c7cb', 0.25, 1.0),
}
# yedek lastik ayrı nesne, ayrı AO dokusu: malzemeleri de ayrı olmalı
MS = {
    'tire': material('SpareTire', '#161719', 0.88, 0.0),
    'rim': material('SpareRim', '#9fa3a7', 0.4, 0.7),
    'hub': material('SpareHub', '#222427', 0.45, 0.5),
    'nut': material('SpareNut', '#c4c7cb', 0.25, 1.0),
}
MB = {
    'paint': material('BodyPaint', ANTHRACITE, 0.44, 0.05, 0.35),
    'dark': material('BodyDark', '#1f2124', 0.5, 0.4),
    'cyl': material('CylinderBlack', '#121315', 0.35, 0.3, 0.3),
    'chrome': material('RodChrome', '#e8ebee', 0.06, 1.0),
    'red': material('BodyReflRed', '#c8101a', 0.3, 0.05),
    'yellow': material('BodyReflYellow', '#f4b400', 0.3, 0.05),
    'warnRed': material('WarnRed', '#c8141b', 0.35, 0.05),
    'warnWhite': material('WarnWhite', '#eceeef', 0.3, 0.05),
    'lensRed': material('LensRed', '#b8160f', 0.2, 0.0),
    'lensAmber': material('LensAmber', '#f29a0c', 0.2, 0.0),
    'lensWhite': material('LensWhite', '#dfe6f0', 0.2, 0.0),
    'galv': material('BodyGalv', '#9fa5ab', 0.45, 0.9),
}
# yüzey pişirme profilleri: toz (grime), kenar aşınması (wear), tozun başladığı yükseklik (low_h)
PROFILES = {
    'FramePaint': {'grime': 0.55, 'wear': 0.35},
    'BodyPaint': {'grime': 0.4, 'wear': 0.35},
    'Suspension': {'grime': 0.9, 'low_h': 1.0},
    'DarkSteel': {'grime': 0.8},
    'Rubber': {'grime': 0.6},
    'Plastic': {'grime': 0.6},
    'Galvanized': {'grime': 0.45},
    'BodyGalv': {'grime': 0.3},
    'Chrome': {'grime': 0.12},
    'RodChrome': {'grime': 0.1},
    'Tire': {'grime': 0.55, 'dust_mix': 0.4, 'low_h': 0.5},
    'Rim': {'grime': 0.7, 'low_h': 0.8},
    'Hub': {'grime': 0.8},
    'SpareTire': {'grime': 0.3},
    'SpareRim': {'grime': 0.3},
    'CylinderBlack': {'grime': 0.4},
    'WarnRed': {'grime': 0.2},
    'WarnWhite': {'grime': 0.25},
}
# tekrarlanan dokular: taban kalasları 4 × 0,9 m karo (0,15 m'lik 6 kalas), cıvata sıraları platform traverslerine (0,5 m) hizalı
BOLT_U = sorted({round(((XG + 0.275 + 0.5 * k) / 4.0) % 1.0, 5) for k in range(8)})
wcol, wnor, worm = hardwood_tile(*((768, 288) if FAST else (1536, 576)), planks=6, tile=(4.0, 0.9), bolt_u=BOLT_U)
gcol, gnor, gorm = galvanized_checker_tile(256 if FAST else 512)
acol, aorm = brushed_alu_tile(256 if FAST else 512)
MD = {
    'wood': tex_material('Hardwood', '#ffffff', 0.78, 0.0, albedo=np_image('hardwood_albedo', wcol), normal=np_image('hardwood_normal', wnor, non_color=True),
                         orm=np_image('hardwood_orm', worm, non_color=True)),
    'checker': tex_material('GalvChecker', '#ffffff', 0.45, 0.85, albedo=np_image('galv_checker_albedo', gcol), normal=np_image('galv_checker_normal', gnor, non_color=True),
                            orm=np_image('galv_checker_orm', gorm, non_color=True)),
    'alu': tex_material('BrushedAlu', '#ffffff', 0.32, 1.0, albedo=np_image('brushed_alu_albedo', acol), orm=np_image('brushed_alu_orm', aorm, non_color=True)),
}
DECK_UV = {'Hardwood': (4.0, 0.9), 'GalvChecker': (0.3, 0.3), 'BrushedAlu': (0.5, 0.5)}
P = M['paint']
LOGO = logo_material('Logo', 'public/brand/logo-blue.png')
LOGO_W = logo_material('LogoWhite', 'public/brand/logo-white.png')

# =====================================================================
# ŞASİ (tesisat görünümünde görünür)
# =====================================================================
C = Parts()
# ince yansıtıcı bantlar AO atlasına girmez (bir pikselden ince ada komşu siyahı örnekler): ayrı, pişirmesiz nesne
N = Parts()
# fırçalanmış alüminyum gibi tekrarlanan dokulu şasi parçaları (yan koruma): AO'suz, düzlemsel UV
T = Parts()

# --- ana kirişler: boyundan platforma tek parça gövde sacı (kaz boynu), alt ve üst başlıklar ---
bot = [(XF + 0.10, NECK_BOT), (XN_B, NECK_BOT)]
bot += [(-9.95, 1.17), (-9.72, 1.03), (-9.56, 0.88), (-9.46, 0.72), (-9.38, 0.59), (-9.28, 0.52), (-9.08, BEAM_BOT)]
bot += [(-0.75, BEAM_BOT), (-0.12, 0.56)]
for s in (-1, 1):
    z = s * BZ
    top = [(XF + 0.10, NFR_TOP - 0.015), (XN_T, NFR_TOP - 0.015), (XG - 0.03, CH_Y - 0.03), (XG, CH_Y - 0.03), (XG, FR_TOP - 0.015), (-0.12, FR_TOP - 0.015)]
    web = top + [(x, y + (0.015 if x > XN_B + 1e-3 else 0.0)) for x, y in reversed(bot)]
    prism_xy(C, 'beam_web', web, z - 0.005, z + 0.005, P, 0.0)
    box2(C, 'beam_top_neck', XF + 0.10, XN_T, NFR_TOP - 0.015, NFR_TOP, z - FL / 2, z + FL / 2, P, 0.003)
    beam(C, 'beam_top_ch', (XN_T, NFR_TOP - 0.0075, z), (XG - 0.03, CH_Y - 0.0225, z), 0.015, FL, P, 0.002)
    box2(C, 'beam_top', XG, -0.12, FR_TOP - 0.015, FR_TOP, z - FL / 2, z + FL / 2, P, 0.003)
    flange_path(C, 'beam_bot', [p for p in bot if p[0] >= XN_B - 1e-3], FL, 0.015, z, P)
    x = XG + 0.6
    while x < -0.6:
        if all(abs(x - a) > 0.5 for a in AXLES):
            for t in (-1, 1):
                box2(C, 'stiff', x - 0.004, x + 0.004, BEAM_BOT + 0.015, FR_TOP - 0.015, z + t * 0.005, z + t * 0.06, P, 0.0)
        x += 0.9

# --- boyun: king pin plakası ve pimi, ön kiriş, traversler, arka duvar ---
box2(C, 'king_plate', XF + 0.12, XN_B + 0.05, H5, H5 + 0.015, -1.15, 1.15, P, 0.003)
cylinder(C, 'king_pin', 0.0254, (KING_X, H5, 0), (KING_X, H5 - 0.062, 0), M['chrome'], 24, 0.002)
cylinder(C, 'king_head', 0.0365, (KING_X, H5 - 0.062, 0), (KING_X, H5 - 0.084, 0), M['chrome'], 24, 0.004)
cylinder(C, 'king_ring', 0.11, (KING_X, H5, 0), (KING_X, H5 - 0.003, 0), M['dark'], 32, 0.001)
box2(C, 'neck_front', XF, XF + 0.10, H5, NECK_TOP, -(W2 - 0.005), W2 - 0.005, P, 0.008)
x = XF + 0.3
while x < XN_T - 0.1:
    t, b = 0.004, 0.05
    y0 = NFR_TOP - 0.147
    pts = [(x, y0), (x + b, y0), (x + b, y0 + t), (x + t, y0 + t), (x + t, NFR_TOP - t), (x + b, NFR_TOP - t), (x + b, NFR_TOP), (x, NFR_TOP)]
    prism_xy(C, 'neck_cross', pts, -(W2 - 0.012), W2 - 0.012, P, 0.0)
    x += 0.45
box2(C, 'neck_rear_wall', XG - 0.03, XG, FR_TOP, CH_Y, -(W2 - 0.006), W2 - 0.006, P, 0.006)

# --- dış yan kirişler: boyundan platforma tek levha; tekerlek bölgesinde kemerli etek ---
outline = [(XF, NECK_TOP), (XN_T, NECK_TOP), (XG - 0.03, CH_Y), (XG, CH_Y), (XG, DECK), (XR, DECK), (XR, SIDE_BOT), (SK1, SIDE_BOT), (SK1, SKIRT_Y)]
for a in reversed(AXLES):
    outline += [(a + ARCH_R, SKIRT_Y)] + arc(a, ARCH_CY, ARCH_R, 0.0, math.pi, 18)[1:-1] + [(a - ARCH_R, SKIRT_Y)]
outline += [(SK0, SKIRT_Y), (SK0, SIDE_BOT), (XG, SIDE_BOT), (-9.40, 0.80), (-9.62, 1.0), (XN_B, NECK_BOT), (XF, NECK_BOT)]
for s in (-1, 1):
    prism_xy(C, 'side_plate', outline, s * (W2 - 0.008), s * W2, P, 0.0)
    zi, zo = s * (W2 - 0.06), s * (W2 - 0.008)
    box2(C, 'side_top_neck', XF, XN_T, NECK_TOP - 0.012, NECK_TOP, zi, zo, P, 0.002)
    box2(C, 'side_top', XG, XR, DECK - 0.012, DECK, zi, zo, P, 0.002)
    box2(C, 'side_bot_neck', XF, XN_B, NECK_BOT, NECK_BOT + 0.012, zi, zo, P, 0.002)
    for xa, xb in ((XG, SK0), (SK1, XR)):
        box2(C, 'side_bot', xa, xb, SIDE_BOT, SIDE_BOT + 0.012, zi, zo, P, 0.002)
    # etek takviyeleri (aks araları ve etek uçları)
    for xm in [SK0 + 0.02, (AXLES[0] + AXLES[1]) / 2, (AXLES[1] + AXLES[2]) / 2, SK1 - 0.02]:
        box2(C, 'skirt_rib', xm - 0.006, xm + 0.006, SKIRT_Y + 0.01, DECK - 0.012, s * (W2 - 0.07), zo, P, 0.0)
        box2(C, 'skirt_foot', xm - 0.08, xm + 0.08, SKIRT_Y, SKIRT_Y + 0.012, s * (W2 - 0.06), zo, P, 0.002)
    # sarı kontur bandı (ECE 104, kesikli), kazık cepleri, bağlama halkaları
    x = XG + 0.3
    while x < XR - 0.4:
        box2(N, 'tape', x, x + 0.5, DECK - 0.03, DECK - 0.006, s * W2, s * (W2 + 0.0015), M['yellow'], 0.0)
        x += 0.75
    x = XF + 0.3
    while x < XN_T - 0.3:
        box2(N, 'tape', x, x + 0.5, NECK_TOP - 0.03, NECK_TOP - 0.006, s * W2, s * (W2 + 0.0015), M['yellow'], 0.0)
        x += 0.75
    for i in range(7):
        x = -8.75 + i * (8.25 / 6)
        box2(C, 'stake_pocket', x - 0.055, x + 0.055, DECK - 0.09, DECK - 0.002, s * W2, s * (W2 + 0.032), M['galv'], 0.004)
        box2(C, 'stake_hole', x - 0.03, x + 0.03, DECK - 0.0035, DECK - 0.0015, s * (W2 + 0.006), s * (W2 + 0.026), M['dark'], 0.0)
    for x in (-8.6, -7.6, -6.7, -1.45, -0.65, XF + 0.9, XF + 2.2):
        yb = NECK_BOT if x < XN_B else SIDE_BOT
        hose(C, 'lash_ring', [(x - 0.05, yb + 0.004, s * (W2 - 0.03)), (x, yb - 0.06, s * (W2 - 0.015)), (x + 0.05, yb + 0.004, s * (W2 - 0.03))], 0.009, M['galv'], 2)

# --- platform traversleri (C profil, ana kirişlerden geçer); tekerlek üstünde ince sac traversler ---
x = XG + 0.25
while x < -0.3:
    thin = any(abs(x - a) < 0.5 for a in AXLES)
    h = 0.03 if thin else 0.10
    y0 = FR_TOP - h
    t, b = 0.004, 0.05
    pts = [(x, y0), (x + b, y0), (x + b, y0 + t), (x + t, y0 + t), (x + t, FR_TOP - t), (x + b, FR_TOP - t), (x + b, FR_TOP), (x, FR_TOP)] if not thin else [(x, y0), (x + 0.07, y0), (x + 0.07, FR_TOP), (x, FR_TOP)]
    prism_xy(C, 'cross', pts, -(W2 - 0.01), W2 - 0.01, P, 0.0)
    x += 0.5
box2(C, 'front_cross', XG, XG + 0.08, FR_TOP - 0.10, FR_TOP, -(W2 - 0.01), W2 - 0.01, P, 0.004)

# --- arka: arka travers, rampa menteşe kulakları, lamba ve plaka tutucuları, kontur bandı, destek ayakları ---
box2(C, 'rear_cross', -0.12, XR, 0.55, DECK, -(W2 - 0.005), W2 - 0.005, P, 0.008)
for s in (-1, 1):
    zc = s * RAMP_Z
    for dz in (-0.36, 0.36):
        box2(C, 'ramp_lug', XR, XR + 0.07, 0.80, 0.93, zc + dz - 0.02, zc + dz + 0.02, P, 0.006)
        cylinder(C, 'ramp_pin', 0.018, (XR + 0.045, 0.89, zc + dz - 0.04), (XR + 0.045, 0.89, zc + dz + 0.04), M['chrome'], 12, 0.0)
    box2(C, 'lamp_holder', -0.10, XR, 0.33, 0.56, s * 0.36, s * 1.25, P, 0.01)
    box2(N, 'rear_tape', XR, XR + 0.0015, 0.70, 0.73, s * 0.08, s * 1.2, M['red'], 0.0)
    # destek ayakları (rampayla yüklemede): dış boru kirişe bağlı, iç ayak ve taban yerde
    zl = s * 0.64
    box2(C, 'sup_mount', -0.54, -0.30, 0.56, 0.80, s * (BZ + 0.006), s * (BZ + 0.018), P, 0.003)
    box2(C, 'sup_spacer', -0.48, -0.36, 0.60, 0.74, s * (BZ + 0.018), s * 0.58, P, 0.003)
    box(C, 'sup_outer', (0.12, 0.48, 0.12), (-0.42, 0.48, zl), P, 0.008)
    box(C, 'sup_inner', (0.09, 0.26, 0.09), (-0.42, 0.16, zl), M['dark'], 0.005)
    box(C, 'sup_foot', (0.2, 0.025, 0.2), (-0.42, 0.0125, zl), P, 0.005)
box2(C, 'plate_holder', -0.09, -0.005, 0.405, 0.56, -0.3, 0.3, P, 0.008)

# --- iniş ayakları (boyun arkasında), ara mil, dişli kutusu ve kol (+z), çaprazlar ---
LZ = 0.62
for s in (-1, 1):
    z = s * LZ
    box2(C, 'leg_mount', LEG_X - 0.15, LEG_X + 0.15, 0.76, 1.10, s * (BZ + 0.006), s * (BZ + 0.018), P, 0.003)
    box2(C, 'leg_spacer', LEG_X - 0.08, LEG_X + 0.08, 0.80, 1.05, s * (BZ + 0.018), s * (LZ - 0.07), P, 0.004)
    box(C, 'leg_outer', (0.14, 0.58, 0.14), (LEG_X, 0.71, z), M['dark'], 0.008)
    box(C, 'leg_collar', (0.16, 0.05, 0.16), (LEG_X, 0.445, z), M['dark'], 0.006)
    box(C, 'leg_inner', (0.11, 0.42, 0.11), (LEG_X, 0.25, z), M['dark'], 0.006)
    box(C, 'leg_ball', (0.09, 0.07, 0.09), (LEG_X, 0.07, z), M['dark'], 0.015)
    box(C, 'leg_foot', (0.26, 0.032, 0.24), (LEG_X, 0.016, z), M['dark'], 0.006)
beam(C, 'leg_brace_x1', (LEG_X + 0.02, 0.48, -LZ + 0.07), (LEG_X + 0.02, 0.74, LZ - 0.07), 0.05, 0.012, M['dark'], 0.002)
beam(C, 'leg_brace_x2', (LEG_X + 0.02, 0.74, -LZ + 0.07), (LEG_X + 0.02, 0.48, LZ - 0.07), 0.05, 0.012, M['dark'], 0.002)
cylinder(C, 'leg_shaft', 0.02, (LEG_X - 0.02, 0.62, -LZ), (LEG_X - 0.02, 0.62, LZ), M['dark'], 12, 0.0)
box(C, 'leg_gear', (0.2, 0.18, 0.1), (LEG_X, 0.62, LZ + 0.12), M['dark'], 0.012)
cylinder(C, 'crank_shaft', 0.016, (LEG_X, 0.62, LZ + 0.17), (LEG_X, 0.62, LZ + 0.3), M['dark'], 12, 0.0)
beam(C, 'crank_arm', (LEG_X, 0.62, LZ + 0.3), (LEG_X - 0.03, 0.36, LZ + 0.33), 0.03, 0.025, M['dark'], 0.004)
cylinder(C, 'crank_grip', 0.019, (LEG_X - 0.03, 0.36, LZ + 0.33), (LEG_X - 0.03, 0.36, LZ + 0.45), M['rubber'], 12, 0.003)


# --- aks grubu: BPW alçak havalı süspansiyon (askı braketi, salıncak kolu, alçak körük, amortisör), aks, kampanalı fren ---
def chamber_xy(xa):
    return xa - 0.30, 0.30


for xa in AXLES:
    cylinder(C, 'axle', 0.06, (xa, R, -0.84), (xa, R, 0.84), M['susp'], 24, 0.004)
    for s in (-1, 1):
        zb = s * BZ
        prism_xy(C, 'hanger', [(xa - 0.74, BEAM_BOT), (xa - 0.42, BEAM_BOT), (xa - 0.52, 0.255), (xa - 0.64, 0.235)], zb - 0.07, zb + 0.07, M['susp'], 0.008)
        prism_zy(C, 'hanger_gusset', [(zb - s * 0.07, BEAM_BOT), (zb - s * 0.18, BEAM_BOT), (zb - s * 0.07, 0.40)], xa - 0.59, xa - 0.58, M['susp'], 0.002)
        cylinder(C, 'hanger_bush', 0.045, (xa - 0.58, 0.27, zb - 0.085), (xa - 0.58, 0.27, zb + 0.085), M['dark'], 20, 0.004)
        beam(C, 'trail_arm_a', (xa - 0.58, 0.27, zb), (xa, 0.30, zb), 0.055, 0.085, M['dark'], 0.008)
        beam(C, 'trail_arm_b', (xa - 0.02, 0.30, zb), (xa + 0.40, 0.31, zb), 0.05, 0.11, M['dark'], 0.008)
        box(C, 'axle_seat', (0.2, 0.05, 0.13), (xa, 0.345, zb), M['dark'], 0.006)
        for dx in (-0.065, 0.065):
            for dz in (-0.055, 0.055):
                cylinder(C, 'ubolt', 0.01, (xa + dx, 0.27, zb + dz), (xa + dx, R + 0.07, zb + dz), M['dark'], 8, 0.0)
        box(C, 'ubolt_plate', (0.18, 0.02, 0.14), (xa, R + 0.065, zb), M['dark'], 0.004)
        cylinder(C, 'airbag_piston', 0.095, (xa + 0.38, 0.33, zb), (xa + 0.38, 0.375, zb), M['dark'], 28, 0.004)
        cylinder(C, 'airbag', 0.15, (xa + 0.38, 0.365, zb), (xa + 0.38, 0.485, zb), M['rubber'], 40, 0.035)
        cylinder(C, 'airbag_top', 0.14, (xa + 0.38, 0.485, zb), (xa + 0.38, BEAM_BOT, zb), M['dark'], 32, 0.002)
        zs = s * (BZ - 0.12)
        cylinder(C, 'shock_body', 0.034, (xa + 0.08, 0.31, zs), (xa - 0.12, 0.40, zs), M['dark'], 14, 0.004)
        cylinder(C, 'shock_rod', 0.014, (xa - 0.12, 0.40, zs), (xa - 0.36, 0.48, zs), M['chrome'], 10, 0.0)
        box2(C, 'shock_bracket', xa - 0.42, xa - 0.32, 0.45, BEAM_BOT, s * (BZ - 0.075), s * (BZ - 0.16), M['susp'], 0.004)
        # kampanalı fren: kampana (iç jantın içinde), göbek taşıyıcı, fren körüğü (aksın önünde, ileri bakar)
        cylinder(C, 'brake_drum', 0.165, (xa, R, s * 0.66), (xa, R, s * 0.8), M['susp'], 36, 0.006)
        cylinder(C, 'hub_carrier', 0.08, (xa, R, s * 0.8), (xa, R, s * 0.97), M['dark'], 24, 0.004)
        cx, cy = chamber_xy(xa)
        cylinder(C, 'brake_chamber', 0.075, (xa - 0.16, cy, s * 0.6), (cx - 0.12, cy, s * 0.6), M['dark'], 24, 0.01)
        cylinder(C, 'chamber_band', 0.078, (cx + 0.02, cy, s * 0.6), (cx + 0.005, cy, s * 0.6), M['galv'], 24, 0.0)
        beam(C, 'slack_adjuster', (xa - 0.1, 0.33, s * 0.62), (xa - 0.16, 0.24, s * 0.62), 0.03, 0.02, M['galv'], 0.003)

# --- son aksın arkasında paçalar ---
for s in (-1, 1):
    xm = AXLES[-1] + 0.47
    box2(C, 'mudflap', xm - 0.006, xm + 0.006, 0.10, 0.72, s * 0.70, s * 1.24, M['rubber'], 0.004)
    box2(C, 'mudflap_bar', xm - 0.02, xm + 0.02, 0.70, 0.74, s * 0.70, s * 1.24, P, 0.004)

# --- yan koruma (alüminyum geniş profil, logolu) ve taşıyıcıları ---
GX0, GX1 = XG + 0.04, -6.42
for s in (-1, 1):
    box2(T, 'guard', GX0, GX1, 0.26, 0.46, s * 1.20, s * 1.245, MD['alu'], 0.0)
    box2(C, 'guard_groove', GX0 + 0.04, GX1 - 0.04, 0.355, 0.362, s * 1.244, s * 1.2465, M['dark'], 0.0)
    for x in (GX0 + 0.3, GX1 - 0.3):
        box2(C, 'guard_post', x - 0.025, x + 0.025, 0.40, SIDE_BOT, s * 1.15, s * 1.20, P, 0.004)
        box2(C, 'guard_strut', x - 0.02, x + 0.02, 0.60, 0.64, s * (BZ + 0.08), s * 1.16, P, 0.003)

# --- alet kutusu (+z, ön aksın önünde) ---
TB = (-6.36, -5.86)
box2(C, 'toolbox', TB[0], TB[1], 0.40, 0.67, 0.80, 1.22, M['plastic'], 0.02)
box2(C, 'toolbox_lid', TB[0] + 0.02, TB[1] - 0.02, 0.43, 0.64, 1.217, 1.227, M['plastic'], 0.01)
for x in (TB[0] + 0.12, TB[1] - 0.12):
    box2(C, 'toolbox_latch', x - 0.03, x + 0.03, 0.59, 0.63, 1.225, 1.24, M['galv'], 0.004)
    box2(C, 'toolbox_hanger', x - 0.02, x + 0.02, 0.67, SIDE_BOT, 0.95, 1.15, P, 0.003)

# --- hava tankları (kirişlerin arasında, önde), EBS, hava hatları ---
for z in (-0.2, 0.2):
    cylinder(C, 'air_tank', 0.12, (-8.9, 0.64, z), (-8.1, 0.64, z), P, 32, 0.025)
    for x in (-8.75, -8.25):
        cylinder(C, 'tank_strap', 0.124, (x - 0.012, 0.64, z), (x + 0.012, 0.64, z), M['galv'], 32, 0.0)
        box2(C, 'tank_hanger', x - 0.012, x + 0.012, 0.75, FR_TOP - 0.10, z - 0.1, z + 0.1, P, 0.002)
EBS = (-6.9, 0.64, -0.22)
box(C, 'ebs', (0.28, 0.18, 0.26), EBS, M['dark'], 0.015)
box2(C, 'ebs_bracket', EBS[0] - 0.15, EBS[0] + 0.15, 0.725, 0.735, -0.36, -0.08, P, 0.002)
# kırmızı / sarı hava hatları kaldırıldı (kullanıcı 2026-10-22: tesisatla ilgisiz ek kablo; standart dorseyle aynı)
poly_tube(C, 'air_tank_line', [(-8.1, 0.64, -0.2), (-7.9, 0.74, -0.3), (EBS[0] - 0.3, 0.74, -0.3), (EBS[0] - 0.15, 0.66, -0.22)], 0.008, M['air'], 2)
for xa in AXLES:
    for s in (-1, 1):
        cx, cy = chamber_xy(xa)
        hose(C, 'brake_hose', [(EBS[0] + 0.15, 0.62, EBS[2] + s * 0.08), ((EBS[0] + xa) / 2, 0.58, s * 0.3), (cx - 0.1, cy + 0.08, s * 0.52), (cx - 0.12, cy + 0.04, s * 0.56)], 0.008, M['air'], 2)

# --- şasiye ait çıkartmalar: yan koruma logoları ---
lq = []
for s in (-1, 1):
    lh = 0.15
    lq.append(side_quad((GX0 + GX1) / 2, 0.36, lh * 720 / 528, lh, s * 1.2475, s))
chassis_logos = decal_mesh('ChassisLogos', lq, LOGO)
chassis = join(C, 'LbChassis')
decor = join(N, 'LbChassisDecor')
tiled = join(T, 'LbChassisTiled')
planar_uv(tiled, DECK_UV)

# --- çift tekerlekler (tek model, 6 örnek) ---
wheel = build_wheel_set(MW, 'TwinWheel', R, HW, RIM_R, twin=True, spacing=TWIN, holes=8, steps=96 if FAST else 144)
wheels = [wheel]
first = True
for xa in AXLES:
    for s in (-1, 1):
        ob = wheel if first else bpy.data.objects.new('TwinWheel', wheel.data)
        if not first:
            scene.collection.objects.link(ob)
            wheels.append(ob)
        first = False
        ob.location = bl((xa, R, s * WZ))
        ob.rotation_euler = (0, 0, math.pi if s > 0 else 0)

# =====================================================================
# ÜST YAPI (tesisat görünümünde gizlenir): başlık, saklama kutusu, rampalar, uyarı levhaları; ayrıca dokulu taban
# =====================================================================
B = Parts()
# başlık (ön duvar): köşe ve ara dikmeler, üst kuşak, panel, yatay takviyeler
for z0, z1 in ((W2 - 0.08, W2), (-W2, -(W2 - 0.08)), (0.39, 0.45), (-0.45, -0.39)):
    box2(B, 'head_post', XF, XF + 0.08, NECK_TOP - 0.01, HEAD_TOP, z0, z1, MB['paint'], 0.008)
box2(B, 'head_top', XF, XF + 0.08, HEAD_TOP - 0.07, HEAD_TOP, -W2, W2, MB['paint'], 0.01)
# tepe lambası taban sacları (üst köşeler, kaynaklı; lamba seçilmese de yerinde)
for s in (-1, 1):
    box2(B, 'beacon_plate', BEACON_X - 0.08, BEACON_X + 0.08, HEAD_TOP, HEAD_TOP + BEACON_PLATE, s * (BEACON_Z - 0.08), s * (BEACON_Z + 0.075), MB['paint'], 0.003)
box2(B, 'head_panel', XF + 0.03, XF + 0.05, NECK_TOP, HEAD_TOP - 0.07, -(W2 - 0.08), W2 - 0.08, MB['paint'], 0.002)
for y in (1.66, 1.8):
    box2(B, 'head_rib', XF + 0.01, XF + 0.03, y - 0.02, y + 0.02, -(W2 - 0.08), W2 - 0.08, MB['paint'], 0.004)
# yedek lastik bağlantısı (başlığın önünde)
box2(B, 'spare_bracket', XF - 0.03, XF, SPARE[1] - 0.12, SPARE[1] + 0.12, -0.07, 0.07, MB['dark'], 0.006)
cylinder(B, 'spare_stud', 0.03, (XF - 0.03, SPARE[1], 0), (XF - 0.12, SPARE[1], 0), MB['dark'], 16, 0.003)
# saklama kutusu (boyun önü, tüm genişlik): alüminyum paneller, beyaz kuşaklar, iki kapak, kulplar
for z in (-(W2 - 0.06), 0.0, W2 - 0.06):
    box2(B, 'box_post', BOX_X1 - 0.05, BOX_X1, NECK_TOP, BOX_TOP - 0.03, z - 0.03, z + 0.03, MB['paint'], 0.005)
for z in (-0.6, 0.6):
    box2(B, 'box_handle', BOX_X1, BOX_X1 + 0.02, 1.70, 1.73, z - 0.1, z + 0.1, MB['galv'], 0.006)
    box2(B, 'box_lock', BOX_X1, BOX_X1 + 0.015, 1.60, 1.66, z - 0.02, z + 0.02, MB['dark'], 0.004)
# rampalar (dik duran iki rampa): yan raylar, uç sacı, alt çerçeve, orta ray, hidrolik silindir, R70 plakası. Silindirin
# hortumları kaldırıldı (kullanıcı 2026-10-22: çalışma lambalarının önüne sarkıyordu)
h = RAMP_W / 2
for s in (-1, 1):
    zc = s * RAMP_Z
    for e in (-1, 1):
        box2(B, 'ramp_rail', RAMP_X0, RAMP_X1, DECK, RAMP_TOP - 0.06, zc + e * (h - 0.07), zc + e * h, MB['paint'], 0.008)
    box2(B, 'ramp_tip', RAMP_X0 - 0.02, RAMP_X1, RAMP_TOP - 0.06, RAMP_TOP, zc - h, zc + h, MB['paint'], 0.01)
    for y in (1.0, 1.32, 1.66, 2.0, 2.44):
        box2(B, 'ramp_bar', RAMP_X0 + 0.02, RAMP_X1 - 0.02, y - 0.035, y + 0.035, zc - h + 0.07, zc + h - 0.07, MB['paint'], 0.006)
    box2(B, 'ramp_spine', RAMP_X0 + 0.03, RAMP_X1 - 0.03, DECK, 2.04, zc - 0.03, zc + 0.03, MB['paint'], 0.005)
    box2(B, 'ramp_plate', RAMP_X1 - 0.012, RAMP_X1, 1.04, 1.28, zc - h + 0.07, zc + h - 0.07, MB['paint'], 0.003)
    zy = s * 0.31
    box2(B, 'cyl_lug_low', XR, 0.27, 0.52, 0.60, zy - 0.04, zy + 0.04, MB['paint'], 0.006)
    cylinder(B, 'cyl_body', 0.045, (0.235, 0.58, zy), (0.235, 1.24, zy), MB['cyl'], 20, 0.006)
    cylinder(B, 'cyl_rod', 0.024, (0.235, 1.24, zy), (0.235, 1.78, zy), MB['chrome'], 16, 0.0)
    box2(B, 'cyl_lug_top', RAMP_X1, 0.27, 1.74, 1.82, zy - 0.035, zy + 0.035, MB['paint'], 0.006)
    box2(B, 'r70_red', RAMP_X1, RAMP_X1 + 0.002, 1.495, 1.635, zc - 0.2825, zc + 0.2825, MB['red'], 0.0)
    box2(B, 'r70_yellow', RAMP_X1 + 0.002, RAMP_X1 + 0.003, 1.51, 1.62, zc - 0.2525, zc + 0.2525, MB['yellow'], 0.0)


def clip(poly, a, b, c):
    """Çokgeni a*p0 + b*p1 <= c yarı düzlemine kırpar (Sutherland-Hodgman)"""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


# (arka köşe uyarı levhaları kullanıcı isteğiyle kaldırıldı, 2026-10-20)

body = join(B, 'LbBody')

# dokulu taban nesnesi (AO atlası dışında, tekrarlanan UV): sert ağaç kalaslar, tekerlek üstü ve pahta damla desenli sac,
# rampa dolguları
D = Parts()
box2(D, 'box_body', XF + 0.08, BOX_X1, NECK_TOP, BOX_TOP - 0.03, -(W2 - 0.05), W2 - 0.05, MD['alu'], 0.0)
# kutu kapağı üstüne basılır: galvaniz damla sac
box2(D, 'box_top', XF + 0.08, BOX_X1, BOX_TOP - 0.03, BOX_TOP, -(W2 - 0.04), W2 - 0.04, MD['checker'], 0.0)
box2(D, 'deck_center', XG + 0.0, -0.12, FR_TOP, DECK, -0.66, 0.66, MD['wood'], 0.0)
for s in (-1, 1):
    za, zb = s * 0.66, s * (W2 - 0.06)
    for xa, xb in ((XG, CHK0), (CHK1, -0.12)):
        box2(D, 'deck_side', xa, xb, FR_TOP, DECK, za, zb, MD['wood'], 0.0)
    box2(D, 'deck_checker', CHK0, CHK1, FR_TOP, DECK, za, zb, MD['checker'], 0.0)
box2(D, 'neck_deck', BOX_X1, XN_T, NFR_TOP, NECK_TOP, -(W2 - 0.06), W2 - 0.06, MD['wood'], 0.0)
prism_xy(D, 'neck_chamfer', [(XN_T, NECK_TOP), (XG - 0.03, CH_Y), (XG - 0.03, CH_Y - 0.012), (XN_T, NECK_TOP - 0.012)], -(W2 - 0.008), W2 - 0.008, MD['checker'], 0.0)
for s in (-1, 1):
    zc = s * RAMP_Z
    box2(D, 'ramp_wood', 0.095, 0.125, 2.48, RAMP_TOP - 0.06, zc - h + 0.07, zc + h - 0.07, MD['wood'], 0.0)
    box2(D, 'ramp_checker', 0.095, 0.125, 2.04, 2.48, zc - h + 0.07, zc + h - 0.07, MD['checker'], 0.0)
deck = join(D, 'LbDeck')
planar_uv(deck, DECK_UV)

# yedek lastik (başlığın önünde dik; ayrı malzemeli tek lastik)
spare = build_wheel_set(MS, 'SpareWheel', R, HW, RIM_R, twin=False, holes=8, steps=96 if FAST else 144)
spare.location = bl(SPARE)
spare.rotation_euler = (0, 0, math.pi / 2)

# üst yapı çıkartmaları: saklama kutusunun iki yanı, rampaların arka yüzü
bq = []
for s in (1, -1):
    bq.append(side_quad((XF + 0.08 + BOX_X1) / 2, (NECK_TOP + BOX_TOP) / 2 - 0.01, 0.28 * 720 / 528, 0.28, s * (W2 - 0.05 + 0.0015), s))
body_logos = decal_mesh('BodyLogos', bq, LOGO)
# rampalar antrasit: logo beyaz
ramp_logos = decal_mesh('RampLogos', [rear_quad(RAMP_X1 + 0.0015, 1.17, s * RAMP_Z, 0.16 * 720 / 528, 0.16) for s in (-1, 1)], LOGO_W)

# =====================================================================
# UV, AO, dışa aktarma
# =====================================================================
smart_uv(chassis, 0.003)
smart_uv(wheel, 0.004)
smart_uv(spare, 0.004)
smart_uv(body, 0.003)
size = 1024 if FAST else 2048
targets = bake_ao([(chassis, size, 'lb_chassis_ao'), (wheel, 512 if FAST else 1024, 'lb_wheel_ao'), (body, size // 2, 'lb_body_ao'), (spare, 256 if FAST else 512, 'lb_spare_ao')],
                  P, samples=16 if FAST else 96, distance=0.6)
decals = [chassis_logos, body_logos, ramp_logos, decor]
upper = [body, deck, spare]
for ob, img in targets:
    # şasi ve tekerlekler üst yapısız pişer (tesisat görünümünde üst yapı ve taban gizli), üst yapı her şeyle birlikte
    run_bake(ob, img, hide=decals + ([u for u in upper if u is not ob] if ob in (chassis, wheel) else []))
    print('BAKED', ob.name)
# renk + ORM: toz, kenar aşınması, pürüzlülük değişimi (güneş ışığında da görünür)
bake_surface([(chassis, size, 'lb_chassis'), (wheel, 512 if FAST else 1024, 'lb_wheel'), (body, size // 2, 'lb_body'), (spare, 256 if FAST else 512, 'lb_spare')],
             PROFILES, samples=8 if FAST else 16)

export_glb(os.path.join(RAW_DIR, 'lowbed-chassis.glb'), [chassis, chassis_logos, decor, tiled] + wheels)
export_glb(os.path.join(RAW_DIR, 'lowbed-body.glb'), [body, deck, spare, body_logos, ramp_logos])
tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)
print(f'TRIS chassis={tri(chassis)} twin={tri(wheel)} body={tri(body)} deck={tri(deck)} spare={tri(spare)}')

# --- zemin temas gölgesi ---
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
bm = bmesh.new()
uvl = bm.loops.layers.uv.new()
vs = [bm.verts.new(bl((CS[0], 0.0, CS[3]))), bm.verts.new(bl((CS[1], 0.0, CS[3]))), bm.verts.new(bl((CS[1], 0.0, CS[2]))), bm.verts.new(bl((CS[0], 0.0, CS[2])))]
f = bm.faces.new(vs)
for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    loop[uvl].uv = uv
me = bpy.data.meshes.new('Ground')
bm.to_mesh(me)
ground = bpy.data.objects.new('Ground', me)
scene.collection.objects.link(ground)
gm = material('GroundAO', '#ffffff', 1.0, 0.0)
ground.data.materials.append(gm)
cw, chh = (512, 128) if FAST else (1024, 256)
gimg = bpy.data.images.new('contact', cw, chh, alpha=False)
gn = gm.node_tree.nodes.new('ShaderNodeTexImage')
gn.image = gimg
gm.node_tree.nodes.active = gn
scene.world.light_settings.distance = 1.2
scene.cycles.samples = 32 if FAST else 256
for o in decals:
    o.hide_render = True
select_only([ground])
bpy.ops.object.bake(type='AO', margin=2, use_clear=True)
px = np.array(gimg.pixels[:], dtype=np.float32).reshape(chh, cw, 4)
dark = np.clip((1.0 - px[:, :, 0]) * 1.15, 0.0, 1.0) ** 0.9


def blur(a, r):
    for _ in range(3):
        for ax in (0, 1):
            p = np.pad(a, [(r, r) if i == ax else (0, 0) for i in range(2)], mode='edge')
            c = np.cumsum(p, axis=ax, dtype=np.float64)
            c = np.insert(c, 0, 0, axis=ax)
            a = ((np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)).astype(np.float32)
    return a


dark = blur(dark, 1 if FAST else 2)
yy, xx = np.mgrid[0:chh, 0:cw]
fade = np.clip(np.minimum(np.minimum(xx, cw - 1 - xx) / (cw * 0.03), np.minimum(yy, chh - 1 - yy) / (chh * 0.12)), 0, 1)
dark = dark * (fade * fade * (3 - 2 * fade))
out = bpy.data.images.new('contact_out', cw, chh, alpha=False)
out.colorspace_settings.name = 'Non-Color'
o = np.zeros((chh, cw, 4), dtype=np.float32)
o[:, :, 0] = o[:, :, 1] = o[:, :, 2] = dark
o[:, :, 3] = 1.0
out.pixels[:] = o.ravel()
out.update()
cpath = os.path.join(OUT_DIR, 'lowbed-contact.webp')
out.filepath_raw = cpath
out.file_format = 'WEBP'
out.save(filepath=cpath, quality=90)
print('CONTACT', cpath, f'{os.path.getsize(cpath) / 1024:.0f} KB')

write_anchors(ANCHORS, anchors_dict())

# ================= önizleme render'ları (yalnızca kontrol) =================
if PREVIEW:
    os.makedirs(PREVIEW, exist_ok=True)
    ground.hide_render = True
    for o_ in decals:
        o_.hide_render = False
    w = scene.world
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.8, 0.82, 0.85, 1)
    bg.inputs['Strength'].default_value = 0.8
    sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    scene.cycles.samples = 24
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = bl((5.0, 3.0, 7.0))
    cam.rotation_euler = (bl((-4.0, 1.0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(PREVIEW, 'rear34.png')
    bpy.ops.render.render(write_still=True)
