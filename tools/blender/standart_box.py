# Standart dorse: kuru yük kapalı kasa (referans: Kässbohrer K.SBT / 20-12/27). Blender'da betikle modellenir, ortam örtmesi
# (AO) dokuya pişirilir, şasi ve kasa ayrı GLB olarak dışa aktarılır; sitenin okuyacağı bağlantı noktaları (lamba, soket,
# tesisat) aynı ölçülerden JSON olarak yazılır (tek kaynak: bu dosya).
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/standart_box.py -- [--fast] [--preview <klasör>]
#   Windows: "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/blender/standart_box.py
#   ardından: npm run models:pack   (Meshopt sıkıştırma: tools/blender/out → src/assets/models)
#   --fast: düşük çözünürlük/örnekleme (yalnız deneme için; yayına girmez)
#   --anchors: yalnız bağlantı noktası JSON'unu yazar (model ve pişirme yok)
# Çıktılar: tools/blender/out/standart-chassis.glb, standart-body.glb (ham), src/assets/models/standart-contact.webp,
#           src/configurator/engine/standart-anchors.json
#
# Ölçü kaynağı (teknik doküman, broşür "K.SBT / 20 - 12 / 27", 2025): toplam boy 13.700, iç boy 13.620, genişlik 2.550,
# iç genişlik 2.490, toplam yükseklik 4.020, iç yükseklik 2.725, arka giriş 2.685, eyer yüksekliği (H5) 1.150,
# dingil mesafesi (king pin → orta aks) 7.455 mm; 3 × 9 t BPW diskli aks, havalı süspansiyon; 385/65 R22,5.
# Broşürdeki ölçekli yan/arka görünüş çiziminden (70,4 px/m, boy ve yükseklikle doğrulandı) alınanlar: king pin ön uca 1,70 m,
# boyun (gooseneck) 2,6 m'de başlayıp 3,9 m'de biter, iniş ayağı ön uca ~4,0 m, travers aralığı ~0,36 m, yan koruma
# 0,48–0,77 m, yatık yedek lastik sepeti (ön uca 5,2–6,3 m), arkada iki hava tankı, alet kutusu, lamba taşıyıcı (0,74–1,05 m),
# plaka (merkez 0,865 m), alt koruma tamponu (0,48–0,57 m). Çizimdeki aks konumu broşür tablosundaki dingil mesafesinden
# ~0,24 m farklı (çizim genel); tablodaki değer esas alındı.
# Yapı: S460MC iki I kiriş, öne basık boyun; traversler kiriş gövdesinden geçer (üstleri taban altıyla aynı düzlemde);
# KTL kaplı şasi (koyu antrasit). Kasa: 20 mm GRP kontrplak yan duvarlar, alüminyum alt/üst köşe profilleri, oluklu çelik
# ön panel, yarı saydam GRP tavan, paslanmaz arka çerçeve, 2 kanatlı alüminyum profil kapı (gizli kilit, kanat başına 5 menteşe).
# Üretici logosu kullanılmaz; yalnız Horpol logosu. Kablolar ve lambalar sitede kodla çizilir.
import bpy
import json
import math
import os
import sys

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in argv
ANCHORS_ONLY = '--anchors' in argv  # yalnız bağlantı noktası JSON'u (modelsiz, saniyeler)
PREVIEW = os.path.abspath(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
OUT_DIR = os.path.abspath('src/assets/models')  # temas gölgesi (WebP)
RAW_DIR = os.path.abspath('tools/blender/out')  # ham GLB; npm run models:pack sıkıştırıp OUT_DIR'e yazar
ANCHORS = os.path.abspath('src/configurator/engine/standart-anchors.json')

# sahne sıfırlandıktan sonra yardımcılar içe aktarılır (modül, o anki sahneyi tutar)
bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import (  # noqa: E402
    Parts, add_obj, bake_ao, beam, bl, box, box2, build_wheel, cylinder, decal_mesh, delete_interior, export_glb, hose, join,
    link_occlusion, logo_from_original, logo_material, material, poly_tube, prism_xy, prism_xz, prism_zy, quad, rear_quad, rect_x, run_bake,
    select_only, side_quad, smart_uv, bez, write_anchors,
)
from bumpers import BUMPERS, LEN as BUMPER_LEN, MM as BMM, T as BT, anchors_for, build_mudflap, export_variants, web_x  # noqa: E402

scene = bpy.context.scene

# ================= ölçüler (metre; x: arka uç 0, ön -L) =================
L = 13.70
W = 2.55
W2 = W / 2
HT = 4.02  # toplam yükseklik
R = 0.536  # 385/65 R22,5
XF = -L  # ön duvarın ön yüzü
XR = 0.0  # arka çerçevenin arka yüzü
FLOOR_TOP = 1.255  # iç yükseklik 2.725 → tavan iç yüzü 3.98
CH_TOP = 1.225  # kiriş ve travers üstü = taban altı
NECK_BOT = 1.15  # king pin plakası altı = H5
PLATE_T = 0.012
DEEP_BOT = 0.895  # derin kiriş altı
XN1 = XF + 2.60  # boyun biter, eğri başlar
XN0 = XF + 3.90  # derin kiriş başlar
KING_X = XF + 1.70
WB = 7.455
AX_MID = KING_X + WB
AXLES = [AX_MID - 1.31, AX_MID, AX_MID + 1.31]  # önden arkaya
LEG_X = XF + 4.02
BZ = 0.55  # ana kiriş gövde ekseni (yanal)
FLANGE = 0.15
WZ = 1.02  # tekerlek merkezi (yanal); iz genişliği ~2,04 m
RAIL_Z = W2 - 0.010  # dış yan ray (C profil) dış yüzü 1,265
BEAM_X1 = -0.16  # ana kirişlerin arka ucu (arka traverse kaynaklı)
SPX = XF + 5.74  # yedek lastik merkezi
LAMP_Y = 0.86  # stop lambası merkezi (çizim: 0,75–0,93) = tamponun web ortası (revize md. 3)
PLATE_Y = LAMP_Y
CARRIER_X = -0.08  # arka tamponun arka dış yüzü (eski lamba taşıyıcının yüzü)
SOCKET_Y = 1.62
HARNESS_Y = 1.18  # tesisat düzlemi: traverslerin gövdesinden geçer, taban altına kelepçeli
Y_RAIL_B = 1.205  # kasa alt köşe profili altı
Y_PANEL0 = 1.29  # yan panel görünen alt kenarı
Y_PANEL1 = 3.93  # yan panel görünen üst kenarı
Y_TOP = HT
CS = (XF - 0.5, XR + 0.5, -W2 - 0.45, W2 + 0.45)  # zemin temas gölgesi alanı (x0, x1, z0, z1)

# ================= lamba montaj haritası (UN R48; yalnız JSON'a yazılır, modeli değiştirmez) =================
# Sabit parçalar: şasi (lamba taşıyıcı, yan C ray) ve SABİT kapalı kasa (köşe dikmeleri, arka başlık). Kapılar lamba yeri değil.
# Arka tampon (2026-10-22, revize md. 1): Horpol sac tamponu (tools/blender/bumpers.py) eski lamba taşıyıcının yerinde. Tipi stop
# lambasından gelir (dikdörtgen stoplar Tek-240-32cm, LUNA Tek-240-30cm-Hamburger); her tip askıları ve alt koruma dikmeleriyle
# ayrı GLB (standart-bumper-<tip>.glb), site seçime göre yükler. Web ortası LAMP_Y'de; lambalar web dış yüzüne oturur.
BUMPER_HALF = BUMPER_LEN / 2 * BMM  # 1,2: tamponun ucu
CARRIER_Z = BUMPER_HALF  # stop lambaları tamponun ucuna dayalı
LRD_HC = 0.077  # LRD 2681 kafa merkezinin civata tabanına yüksekliği (lamps_aux.py hor111): kafa web ortasında
HANGER_Z = 0.79  # askıların z merkezi (dudaktaki dış oval delik 0,73–0,99 içinde)


def bumper_face(kind):
    """Lambaların oturduğu web dış yüzünün dünya x'i"""
    return round(CARRIER_X + web_x(kind), 4)


REAR_ZIN = 0.30  # arka bölgenin iç sınırı: plaka (±0,26) + boşluk; stop iç kenarları arası ≥ 0,60
PLATE_W, PLATE_H = 0.52, 0.11
SIDE_Y = CH_TOP - 0.035  # yan C rayın (y 1,155–1,225) ortası
SIDE_X0, SIDE_X1, SIDE_N = XF + 0.8, -0.5, 10  # ilk/son marker (önden 0,8 / arkadan 0,5 m), yan başına en çok 10 (~1,38 m; revize md. 12)
ARM_Y = Y_PANEL0 + 0.07  # lastik kollar: kasanın 4 ALT köşesi (kullanıcı isteği 2026-10-20), köşe dikmesinin yan yüzü
# revize md. 9 (2026-10-21): ön ALT köşeler, öne bakar, yan markerla aynı seviyede. LD 2773 (CAD) en alt noktası tutucu
# merkezinin 37,6 mm altı; ön traversin (köşeye kadar uzanır) altını (NECK_BOT) geçmez. Tutucu plaka traversin ön yüzüne oturur.
FRONT_LAMP_Y = max(CH_TOP - 0.035, NECK_BOT + 0.038)
FRONT_LAMP_X = XF + 0.01  # ön traversin ön yüzü (box2 'front_cross')
REAR_GAP = 0.0  # stop lambaları taşıyıcının dış ucuna dayalı (kullanıcı 2026-10-20: önceki 0,09 m boşluk geri alındı)
POST_D = 0.13  # ön/arka köşe dikmesinin yan yüz derinliği
WORK_Z = 0.565  # çalışma lambası: plaka lambasının dış kenarı (0,347) ile LZD 3194'ün iç kenarı (0,78) arası
BEACON_Z = 1.0
TRUNK_Z = BZ - 0.035  # ana demet: kiriş gövdesinin iç yanı, üst başlığın altında
MODULE_X = -2.2  # Horpol modülü: hava tanklarının önünde, kirişlerin arasında
REAR_JX = BEAM_X1 - 0.025  # arka dağıtım: arka traversin önü, iniş lamba taşıyıcının içinden
CROSS_XS = [XF + 0.32 + 0.36 * i for i in range(100) if XF + 0.32 + 0.36 * i < -0.32]  # traverslerin ön yüzü (C profil 45 mm)
# tesisat görünümünde yan hatların yana döndüğü x: son traversle arka dağıtım arasındaki boşluğun ortası (kesişmede yan hat
# 7×1'in altından geçer, traverse değmez)
SIDE_TURN_X = round((CROSS_XS[-1] + 0.045 + REAR_JX) / 2, 3)


def mounts_dict():
    side_y = [[XF, SIDE_Y], [XR, SIDE_Y]]
    return {
        'rear': {'x': bumper_face('tek32'), 'y': LAMP_Y, 'zOuter': round(CARRIER_Z - REAR_GAP, 3), 'zInner': REAR_ZIN, 'faceX': bumper_face('tek32')},
        'plate': {'x': bumper_face('tek32'), 'y': round(PLATE_Y + PLATE_H / 2 + 0.03, 3), 'z': [-0.17, 0.17], 'plateY': PLATE_Y,
                  'plateW': PLATE_W, 'plateH': PLATE_H},
        'side': {'x0': SIDE_X0, 'x1': SIDE_X1, 'y': side_y, 'z': RAIL_Z + 0.001, 'maxPerSide': SIDE_N,
                 'rule': {'firstFromFront': 3.0, 'lastFromRear': 1.0, 'maxGap': 3.0}, 'avoid': [], 'brackets': None},
        'front': {'x': FRONT_LAMP_X, 'y': FRONT_LAMP_Y, 'z': W2 - 0.06, 'bracket': None},
        'armFront': {'x': XF + POST_D / 2, 'y': ARM_Y, 'z': W2, 'wallZ': W2, 'bracket': None},
        'armRear': {'x': XR - POST_D / 2, 'y': ARM_Y, 'z': W2, 'wallZ': W2, 'bracket': None},
        'armRearAlt': {'x': CARRIER_X - 0.04, 'y': LAMP_Y, 'z': CARRIER_Z, 'wallZ': CARRIER_Z, 'bracket': None},
        # çalışma lambaları: lamba taşıyıcıda stop ile plaka arasında (kullanıcı 2026-10-22; model gelene kadar). z varsayılan,
        # 'between': site arka lambaların iç kenarı ile plaka lambalarının dış kenarının ortasına yerleştirir (set seçimine göre)
        'work': [{'x': bumper_face('tek32'), 'y': round(LAMP_Y - LRD_HC, 3), 'z': s * WORK_Z, 'dir': [1, 0, 0], 'bracket': None, 'between': True}
                 for s in (1, -1)],
        # arka tampon türevleri (bumpers.py VARIANTS, lambaya göre delinmiş): türev stop lambasından (data.ts BUMPER_BY_STOP)
        'bumper': anchors_for(CARRIER_X),
        'beacon': [{'x': XR - 0.065, 'y': Y_TOP, 'z': s * BEACON_Z, 'bracket': [[XR - 0.13, Y_TOP, s * BEACON_Z], [XR + 0.02, Y_TOP, s * BEACON_Z]]}
                   for s in (1, -1)],
        'harness': {'trunkY': HARNESS_Y, 'trunkZ': TRUNK_Z, 'profile': [[XF, HARNESS_Y], [XR, HARNESS_Y]], 'moduleX': MODULE_X,
                    'rearJunctionX': REAR_JX,
                    # tesisat görünümü: yatay hatlar kiriş ve traverslerin ÜSTÜNDEN (kasa gizli), yan hat dış rayın iç yanında
                    'top': {'y': CH_TOP, 'sideZ': round(RAIL_Z - SIDE_BRANCH, 3), 'turnX': SIDE_TURN_X},
                    'notes': 'Ana hat ve yan hatlar traverslerin gövdesinden (y 1,18) geçer; yan hat kiriş gövdesinin iç yanında, üst '
                             'başlığın altında. Arka dallar arka traversin önünden lamba taşıyıcının içine iner. Tesisat görünümünde '
                             '(top) aynı hatlar şasinin üstünden gösterilir.'},
        'parents': {'rear': 'chassis', 'plate': 'chassis', 'side': 'chassis', 'front': 'body', 'armFront': 'body', 'armRear': 'body',
                    'armRearAlt': 'chassis', 'work': 'chassis', 'beacon': 'body', 'harness': 'chassis'},
        'notes': 'Kapalı kasa sabit (devrilmez), bu yüzden ön pozisyon, lastik kol ve tepe lambaları kasaya bağlanır. '
                 'Ön pozisyon ön traversin ön yüzünde, alt köşede, yan markerla aynı yükseklikte (y 1,19). Lastik kollar köşe dikmelerinin '
                 'yan yüzünde, kasanın alt köşelerinde (y 1,36). Yan markerlar şasinin '
                 'dış C rayında y 1,19: boyun (ön 4 m) ve tekerlek bölgesinde 0,9 m altında sabit yüzey yok (R48 6.18 üst sınır '
                 '1,5 m). Çalışma lambaları lamba taşıyıcıda stop ile plaka arasında, tepe lambaları başlığın üstünde (130 mm derinlik, Ø150 için '
                 'adaptör levhası); tepe lambası toplam yüksekliği ~4,15 m yapar (4,0 m sınırı ülkeye göre kontrol edilmeli).',
    }


# tesisat görünümünde yan hat yan markerlardan bu kadar içte (kullanıcı 2026-10-23: kenara fazla yakındı; marker dalı ~0,6 m)
SIDE_BRANCH = 0.6


def anchors_dict():
    """Sitenin okuyacağı bağlantı noktaları (three.js koordinatları; şema: src/configurator/engine/baked.ts)"""
    sections = [rect_x(x, Y_RAIL_B, HT, W2) for x in [XF + (XR - XF) * i / 6 for i in range(7)]]
    sections += [[[XF, y, z], [XR, y, z]] for y in (Y_RAIL_B, HT) for z in (W2, -W2)]
    return {
        '_source': 'tools/blender/standart_box.py tarafından üretilir; elle düzenleme',
        'L': L,
        'W': W,
        'topY': HT,
        # dropX: lamba dalları arka traversin önünden, lamba taşıyıcının içinden iner
        'rear': {'x': bumper_face('tek32'), 'lampY': LAMP_Y, 'lampZ': [0.925, 0.5], 'plateY': PLATE_Y, 'dropX': BEAM_X1 - 0.025},
        'side': {'x0': XF + 1.0, 'x1': -0.6, 'z': RAIL_Z + 0.001, 'profile': [[XF, CH_TOP - 0.05], [XR, CH_TOP - 0.05]]},
        'front': {'x': XF - 0.002, 'y': Y_PANEL1 - 0.07, 'z': W2 - 0.06},
        'armFront': {'x': XF + 0.3, 'y': Y_PANEL1 - 0.2, 'z': W2},
        'armRear': {'x': -0.3, 'y': Y_PANEL1 - 0.2, 'z': W2},
        'extra': {'x': XR + 0.0, 'y': HT - 0.092, 'z0': 1.1, 'z1': 0.5},
        'socket': {'x': XF - 0.012, 'y': SOCKET_Y},
        'harness': {'y': HARNESS_Y, 'frontX': XF + 0.2, 'trunkZ': 0.86, 'rearZ': 0.7, 'profile': [[XF, HARNESS_Y], [XR, HARNESS_Y]]},
        'contact': {'x0': CS[0], 'x1': CS[1], 'z0': CS[2], 'z1': CS[3]},
        'sections': sections,
        'mounts': mounts_dict(),
    }


if ANCHORS_ONLY:
    write_anchors(ANCHORS, anchors_dict())
    raise SystemExit(0)

# ================= malzemeler =================
M = {
    # KTL kaplama gerçekte siyaha yakın; tesisat görünümünde biçim okunsun diye koyu antrasit
    'ktl': material('KTL', '#40454c', 0.5, 0.2, 0.25),
    'dark': material('DarkSteel', '#1d1f22', 0.5, 0.45),
    'white': material('ChassisWhite', '#eceef1', 0.32, 0.05, 0.45),
    'rubber': material('Rubber', '#141517', 0.85, 0.0),
    'plastic': material('Plastic', '#1a1b1e', 0.55, 0.0),
    'alu': material('Alu', '#c3c8cf', 0.3, 0.8),
    'chrome': material('Chrome', '#e8ebee', 0.08, 1.0),
    'galv': material('Galvanized', '#a9afb6', 0.42, 0.85),
    'red': material('ReflRed', '#c8101a', 0.3, 0.05),
    'amber': material('Amber', '#f29a0c', 0.25, 0.0),
    'air': material('AirLine', '#24262a', 0.6, 0.0),
}
MW = {
    'tire': material('Tire', '#17181a', 0.9, 0.0),
    'rim': material('Rim', '#c2c7cd', 0.32, 0.85),
    'hub': material('Hub', '#25272b', 0.45, 0.5),
    'nut': material('Nut', '#d8dbdf', 0.15, 1.0),
}
MB = {
    'grp': material('GRP', '#f4f5f7', 0.22, 0.0, 0.55),
    'steel': material('FrontSteel', '#eef0f2', 0.34, 0.1, 0.4),
    'door': material('DoorWhite', '#f1f2f4', 0.26, 0.15, 0.5),
    'joint': material('DoorJoint', '#d9dce0', 0.35, 0.2),
    'alu': material('BodyAlu', '#c9cdd3', 0.3, 0.78),
    'inox': material('Stainless', '#b5bbc2', 0.2, 0.95),
    'dark': material('BodyDark', '#1f2124', 0.5, 0.4),
    'rubber': material('BodyRubber', '#151618', 0.8, 0.0),
    'red': material('BodyReflRed', '#c8101a', 0.3, 0.05),
    'yellow': material('BodyReflYellow', '#f4b400', 0.3, 0.05),
    'silver': material('ReflWhite', '#dfe2e6', 0.25, 0.3),
    'floor': material('Phenolic', '#4b3527', 0.6, 0.0),
    'roof': material('Roof', '#eaece7', 0.5, 0.0),
    'console': material('Console', '#3a3e44', 0.4, 0.6),
    'gladRed': material('GladRed', '#c4161c', 0.4, 0.1),
    'gladYellow': material('GladYellow', '#e8b20c', 0.4, 0.1),
}
K = M['ktl']
LOGO = logo_material('Logo', 'public/brand/logo-blue.png')

# =====================================================================
# ŞASİ
# =====================================================================
C = Parts()


def flange_path(name, pts, w, t, z, mat, up=True):
    """Yandan görünüşte (x, y) çizgisini izleyen, z'de w genişlikte, t kalınlıkta şerit (kiriş alt başlığı)"""
    import bmesh
    from mathutils import Vector
    bm = bmesh.new()
    rings = []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln  # sola normal (yukarı)
        if ny < 0:
            nx, ny = -nx, -ny
        k = t if up else -t
        ring = [
            bm.verts.new(bl((x, y, z - w / 2))),
            bm.verts.new(bl((x, y, z + w / 2))),
            bm.verts.new(bl((x + nx * k, y + ny * k, z + w / 2))),
            bm.verts.new(bl((x + nx * k, y + ny * k, z - w / 2))),
        ]
        rings.append(ring)
    for i in range(n - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(4):
            bm.faces.new([A[j], A[(j + 1) % 4], B[(j + 1) % 4], B[j]])
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, 0.003, C)


# --- ana kirişler: alt çizgi (alt başlığın alt yüzü) ---
curve = bez((XN1, NECK_BOT + PLATE_T), (XN1 + 0.75, NECK_BOT + 0.0), (XN0 - 0.06, 1.06), (XN0, DEEP_BOT), 14)
bottom = [(XF + 0.11, NECK_BOT + PLATE_T)] + curve + [(-1.1, DEEP_BOT), (BEAM_X1, 1.0)]
for s in (-1, 1):
    z = s * BZ
    # gövde sacı: üstte üst başlığın altı, altta alt başlığın üstü (boyunda king pin plakası)
    web = [(XF + 0.11, CH_TOP - 0.015), (BEAM_X1, CH_TOP - 0.015)] + [(x, y + (0.015 if x > XN1 + 1e-3 else 0.0)) for x, y in reversed(bottom)]
    prism_xy(C, 'beam_web', web, z - 0.005, z + 0.005, K, 0.0)
    box2(C, 'beam_top', XF + 0.11, BEAM_X1, CH_TOP - 0.015, CH_TOP, z - FLANGE / 2, z + FLANGE / 2, K, 0.003)
    flange_path('beam_bot', [p for p in bottom if p[0] >= XN1 - 1e-3], FLANGE, 0.015, z, K)
    # gövde sacı berkitmeleri (derin bölümde, iki yüzde)
    x = XN0 + 0.4
    while x < BEAM_X1 - 0.5:
        if all(abs(x - a) > 0.25 for a in AXLES):
            for t in (-1, 1):
                box2(C, 'stiff', x - 0.004, x + 0.004, DEEP_BOT + 0.015, CH_TOP - 0.015, z + t * 0.005, z + t * 0.06, K, 0.0)
        x += 0.72

# --- traversler (C profil, kiriş gövdesinden geçer) ---
for x in CROSS_XS:
    h = 0.063 if x < XN1 + 0.05 else 0.08
    y0 = CH_TOP - h
    t = 0.004
    b = 0.045
    pts = [(x, y0), (x + b, y0), (x + b, y0 + t), (x + t, y0 + t), (x + t, CH_TOP - t), (x + b, CH_TOP - t), (x + b, CH_TOP), (x, CH_TOP)]
    prism_xy(C, 'cross', pts, -RAIL_Z + 0.012, RAIL_Z - 0.012, K, 0.0)

# --- dış yan raylar (C profil, ağzı içe) ---
for s in (-1, 1):
    zo = s * RAIL_Z
    zi = s * (RAIL_Z - 0.05)
    zw = s * (RAIL_Z - 0.006)
    y0, y1 = CH_TOP - 0.07, CH_TOP
    pts = [(zo, y0), (zi, y0), (zi, y0 + 0.005), (zw, y0 + 0.005), (zw, y1 - 0.005), (zi, y1 - 0.005), (zi, y1), (zo, y1)]
    prism_zy(C, 'side_rail', pts, XF + 0.11, XR - 0.16, K, 0.0)

# --- ön travers, king pin plakası ve pimi ---
box2(C, 'front_cross', XF + 0.01, XF + 0.11, NECK_BOT, CH_TOP, -RAIL_Z, RAIL_Z, K, 0.005)
box2(C, 'king_plate', XF + 0.2, XN1 + 0.12, NECK_BOT, NECK_BOT + PLATE_T, -0.76, 0.76, M['dark'], 0.003)
prism_xy(C, 'king_ramp', [(XF + 0.11, NECK_BOT + 0.02), (XF + 0.21, NECK_BOT), (XF + 0.21, NECK_BOT + PLATE_T), (XF + 0.11, NECK_BOT + 0.03)], -0.76, 0.76, M['dark'], 0.002)
cylinder(C, 'king_pin', 0.0254, (KING_X, NECK_BOT, 0), (KING_X, NECK_BOT - 0.062, 0), M['chrome'], 24, 0.002)
cylinder(C, 'king_head', 0.0365, (KING_X, NECK_BOT - 0.062, 0), (KING_X, NECK_BOT - 0.084, 0), M['chrome'], 24, 0.004)
cylinder(C, 'king_ring', 0.11, (KING_X, NECK_BOT, 0), (KING_X, NECK_BOT - 0.003, 0), M['dark'], 32, 0.001)

# --- arka travers (kapı eşiği), rampa tamponları, kontur bandı ---
box2(C, 'rear_cross', BEAM_X1, XR - 0.02, 1.06, CH_TOP, -RAIL_Z, RAIL_Z, K, 0.006)
for s in (-1, 1):
    box2(C, 'dock_buffer', XR - 0.02, XR + 0.03, 1.075, 1.175, s * 0.52, s * 0.92, M['rubber'], 0.01)
    box2(C, 'rear_tape', XR - 0.02, XR - 0.017, 1.185, 1.215, s * 0.05, s * 1.24, M['red'], 0.0)

# --- iniş ayakları (ön uca ~4 m), ara mil, dişli kutusu ve kol (+z), çaprazlar ---
LZ = 0.71
for s in (-1, 1):
    z = s * LZ
    box2(C, 'leg_mount', LEG_X - 0.17, LEG_X + 0.17, DEEP_BOT + 0.02, CH_TOP - 0.02, s * (BZ + 0.006), s * (BZ + 0.018), K, 0.003)
    box2(C, 'leg_spacer', LEG_X - 0.09, LEG_X + 0.09, 0.96, 1.17, s * (BZ + 0.018), s * (LZ - 0.07), K, 0.004)
    box(C, 'leg_outer', (0.14, 0.52, 0.14), (LEG_X, 0.86, z), K, 0.008)
    box(C, 'leg_collar', (0.16, 0.05, 0.16), (LEG_X, 0.625, z), K, 0.006)
    box(C, 'leg_inner', (0.11, 0.52, 0.11), (LEG_X, 0.36, z), M['dark'], 0.006)
    box(C, 'leg_ball', (0.09, 0.07, 0.09), (LEG_X, 0.07, z), M['dark'], 0.015)
    box(C, 'leg_foot', (0.26, 0.032, 0.24), (LEG_X, 0.016, z), K, 0.006)
    beam(C, 'leg_brace_l', (LEG_X + 0.07, 0.68, z), (LEG_X + 0.95, DEEP_BOT + 0.01, s * BZ), 0.055, 0.03, K, 0.003)
beam(C, 'leg_brace_x1', (LEG_X + 0.02, 0.66, -LZ + 0.07), (LEG_X + 0.02, 0.86, LZ - 0.07), 0.05, 0.012, K, 0.002)
beam(C, 'leg_brace_x2', (LEG_X + 0.02, 0.86, -LZ + 0.07), (LEG_X + 0.02, 0.66, LZ - 0.07), 0.05, 0.012, K, 0.002)
cylinder(C, 'leg_shaft', 0.02, (LEG_X - 0.02, 0.8, -LZ), (LEG_X - 0.02, 0.8, LZ), M['dark'], 12, 0.0)
box(C, 'leg_gear', (0.2, 0.18, 0.1), (LEG_X, 0.8, LZ + 0.12), K, 0.012)
cylinder(C, 'crank_shaft', 0.016, (LEG_X, 0.8, LZ + 0.17), (LEG_X, 0.8, LZ + 0.3), M['dark'], 12, 0.0)
beam(C, 'crank_arm', (LEG_X, 0.8, LZ + 0.3), (LEG_X - 0.03, 0.52, LZ + 0.33), 0.03, 0.025, M['dark'], 0.004)
cylinder(C, 'crank_grip', 0.019, (LEG_X - 0.03, 0.52, LZ + 0.33), (LEG_X - 0.03, 0.52, LZ + 0.45), M['rubber'], 12, 0.003)
box(C, 'crank_holder', (0.05, 0.06, 0.04), (LEG_X - 0.03, 0.62, LZ + 0.36), K, 0.004)

def brake_xy(xa):
    """Kaliper merkezi (yandan görünüş): diskin ön-üst kenarı"""
    ca, cr = math.radians(140), 0.19
    return xa + math.cos(ca) * cr, R + math.sin(ca) * cr


# --- aks grubu: BPW havalı süspansiyon (askı braketi, salıncak kolu, körük Ø360, amortisör), aks, disk fren ---
for xa in AXLES:
    cylinder(C, 'axle', 0.064, (xa, R, -0.84), (xa, R, 0.84), M['dark'], 24, 0.004)
    for s in (-1, 1):
        zb = s * BZ
        prism_xy(C, 'hanger', [(xa - 0.82, DEEP_BOT), (xa - 0.44, DEEP_BOT), (xa - 0.55, 0.66), (xa - 0.7, 0.63)], zb - 0.075, zb + 0.075, K, 0.008)
        prism_zy(C, 'hanger_gusset', [(zb - s * 0.075, DEEP_BOT), (zb - s * 0.2, DEEP_BOT), (zb - s * 0.075, 0.75)], xa - 0.64, xa - 0.63, K, 0.002)
        cylinder(C, 'hanger_bush', 0.05, (xa - 0.63, 0.68, zb - 0.09), (xa - 0.63, 0.68, zb + 0.09), M['dark'], 20, 0.004)
        beam(C, 'trail_arm_a', (xa - 0.63, 0.68, zb), (xa, 0.44, zb), 0.065, 0.09, M['dark'], 0.008)
        beam(C, 'trail_arm_b', (xa - 0.02, 0.44, zb), (xa + 0.43, 0.48, zb), 0.06, 0.12, M['dark'], 0.008)
        box(C, 'axle_seat', (0.24, 0.07, 0.15), (xa, R - 0.075, zb), M['dark'], 0.008)
        for dx in (-0.07, 0.07):
            for dz in (-0.06, 0.06):
                cylinder(C, 'ubolt', 0.011, (xa + dx, R - 0.12, zb + dz), (xa + dx, R + 0.08, zb + dz), M['dark'], 8, 0.0)
        box(C, 'ubolt_plate', (0.2, 0.025, 0.15), (xa, R + 0.075, zb), M['dark'], 0.004)
        cylinder(C, 'airbag_piston', 0.115, (xa + 0.405, 0.5, zb), (xa + 0.405, 0.62, zb), M['dark'], 32, 0.004)
        cylinder(C, 'airbag', 0.18, (xa + 0.405, 0.6, zb), (xa + 0.405, 0.855, zb), M['rubber'], 48, 0.045)
        cylinder(C, 'airbag_top', 0.17, (xa + 0.405, 0.855, zb), (xa + 0.405, 0.872, zb), M['dark'], 40, 0.003)
        box2(C, 'airbag_pedestal', xa + 0.27, xa + 0.54, 0.872, DEEP_BOT, zb - 0.12, zb + 0.12, K, 0.004)
        # amortisör askı braketinin iç yanında (dışta fren silindiri var)
        zs = s * (BZ - 0.12)
        cylinder(C, 'shock_body', 0.038, (xa + 0.08, 0.5, zs), (xa - 0.12, 0.73, zs), M['dark'], 16, 0.004)
        cylinder(C, 'shock_rod', 0.016, (xa - 0.12, 0.73, zs), (xa - 0.4, 0.86, zs), M['chrome'], 12, 0.0)
        box2(C, 'shock_bracket', xa - 0.46, xa - 0.36, 0.82, DEEP_BOT, s * (BZ - 0.075), s * (BZ - 0.16), K, 0.004)
        # disk fren (jantın içinde): disk, kaliper, fren silindiri (içe bakar)
        cylinder(C, 'brake_disc', 0.215, (xa, R, s * 0.84), (xa, R, s * 0.885), M['galv'], 40, 0.004)
        cylinder(C, 'hub_carrier', 0.1, (xa, R, s * 0.885), (xa, R, s * 0.99), M['dark'], 28, 0.006)
        cx, cy = brake_xy(xa)
        box(C, 'caliper', (0.18, 0.12, 0.12), (cx, cy, s * 0.84), M['dark'], 0.02)
        cylinder(C, 'brake_cyl', 0.088, (cx - 0.03, cy + 0.06, s * 0.78), (cx - 0.03, cy + 0.06, s * 0.54), M['dark'], 28, 0.012)
        cylinder(C, 'brake_cyl_band', 0.092, (cx - 0.03, cy + 0.06, s * 0.67), (cx - 0.03, cy + 0.06, s * 0.655), M['galv'], 28, 0.0)

# --- düz çamurluklar (akslar boyunca tek parça), sıçrama önleyici kenar, taşıyıcılar; arka paçalar ---
FX0 = AXLES[0] - R - 0.12
FX1 = AXLES[-1] + R + 0.12
for s in (-1, 1):
    box2(C, 'fender', FX0, FX1, 1.095, 1.107, s * 0.8, s * 1.245, M['plastic'], 0.004)
    box2(C, 'fender_lip', FX0, FX1, 0.985, 1.107, s * 1.235, s * 1.247, M['plastic'], 0.003)
    for xe in (FX0, FX1):
        box2(C, 'fender_end', xe - 0.006, xe + 0.006, 1.0, 1.107, s * 0.8, s * 1.247, M['plastic'], 0.003)
    for x in (FX0 + 0.35, (FX0 + FX1) / 2, FX1 - 0.35):
        box2(C, 'fender_stay', x - 0.02, x + 0.02, 1.107, CH_TOP - 0.07, s * 0.95, s * 1.15, K, 0.003)
    xm = AXLES[-1] + 0.59
    box2(C, 'mudflap', xm - 0.006, xm + 0.006, 0.28, 0.98, s * 0.77, s * 1.27, M['rubber'], 0.004)
    box2(C, 'mudflap_bar', xm - 0.02, xm + 0.02, 0.97, 1.0, s * 0.77, s * 1.25, K, 0.004)

# --- yan koruma (beyaz profil, logolu), taşıyıcı dikmeler ---
GX0 = LEG_X + 0.28
GX1 = AXLES[0] - R - 0.16
for s in (-1, 1):
    box2(C, 'guard', GX0, GX1, 0.48, 0.77, s * 1.205, s * 1.245, M['white'], 0.012)
    box2(C, 'guard_groove', GX0 + 0.03, GX1 - 0.03, 0.62, 0.628, s * 1.244, s * 1.247, M['alu'], 0.0)
    for x in (GX0 + 0.18, (GX0 + GX1) / 2, GX1 - 0.18):
        box2(C, 'guard_post', x - 0.025, x + 0.025, 0.6, CH_TOP - 0.07, s * 1.16, s * 1.205, K, 0.004)
        beam(C, 'guard_brace', (x, 0.7, s * 1.17), (x, DEEP_BOT + 0.01, s * (BZ + 0.08)), 0.04, 0.03, K, 0.003)

# --- yedek lastik sepeti (yatık), askılar ---
for z in (-0.36, 0.36):
    box2(C, 'spare_rail', SPX - 0.6, SPX + 0.6, 0.38, 0.42, z - 0.02, z + 0.02, K, 0.004)
for x in (SPX - 0.56, SPX + 0.56):
    box2(C, 'spare_cross', x - 0.02, x + 0.02, 0.38, 0.42, -0.42, 0.42, K, 0.004)
    for z in (-0.5, 0.5):
        beam(C, 'spare_hanger', (x, 0.4, z * 0.8), (x, DEEP_BOT, z * 1.1), 0.04, 0.04, K, 0.003)
box2(C, 'spare_lock', SPX + 0.5, SPX + 0.62, 0.42, 0.6, -0.05, 0.05, M['dark'], 0.006)

# --- hava tankları (arkada, kirişlerin arasında), kelepçeler ---
for z in (-0.3, 0.3):
    cylinder(C, 'air_tank', 0.15, (-1.95, 0.97, z), (-1.15, 0.97, z), M['ktl'], 36, 0.03)
    for x in (-1.8, -1.3):
        cylinder(C, 'tank_strap', 0.154, (x - 0.015, 0.97, z), (x + 0.015, 0.97, z), M['galv'], 36, 0.0)
        box2(C, 'tank_hanger', x - 0.015, x + 0.015, 1.1, CH_TOP - 0.08, z - 0.12, z + 0.12, K, 0.002)
    cylinder(C, 'tank_drain', 0.012, (-1.55, 0.82, z), (-1.55, 0.78, z), M['galv'], 8, 0.0)

# --- EBS modülatörü, hava hatları ---
EBS = (-5.2, 1.03, -0.27)
box(C, 'ebs', (0.3, 0.2, 0.3), EBS, M['dark'], 0.015)
box2(C, 'ebs_bracket', EBS[0] - 0.17, EBS[0] + 0.17, 1.13, CH_TOP - 0.08, -0.43, -0.11, K, 0.003)
for i, dz in enumerate((-0.08, 0.0, 0.08)):
    cylinder(C, 'ebs_port', 0.018, (EBS[0] + 0.15, 1.0, EBS[2] + dz), (EBS[0] + 0.19, 1.0, EBS[2] + dz), M['plastic'], 10, 0.0)
# Ön traversten EBS'ye giden kırmızı / sarı hava hatları kaldırıldı (kullanıcı 2026-10-22): tesisat görünümünde sitenin
# renk kodlu kablolarıyla (arka hat kırmızı, yan hat turuncu) karışıyordu.
poly_tube(C, 'air_tank_line', [(-1.95, 0.97, -0.3), (-2.1, 1.12, -0.42), (EBS[0] + 0.4, 1.17, -0.44), (EBS[0] + 0.16, 1.05, -0.3)], 0.008, M['air'], 2)
for xa in AXLES:
    for s in (-1, 1):
        cx, cy = brake_xy(xa)
        hose(C, 'brake_hose', [(EBS[0] + (0.15 if xa > EBS[0] else -0.15), 1.0, EBS[2] + s * 0.1), ((EBS[0] + xa) / 2, 0.98, s * 0.25), (cx - 0.03, cy + 0.12, s * 0.45), (cx - 0.03, cy + 0.07, s * 0.5)], 0.008, M['air'], 2)

# --- alet kutusu (+z, son aksın arkasında) ---
TB = (-2.02, -1.4)
box2(C, 'toolbox', TB[0], TB[1], 0.55, 0.97, 0.79, 1.225, M['plastic'], 0.02)
box2(C, 'toolbox_lid', TB[0] + 0.02, TB[1] - 0.02, 0.6, 0.93, 1.222, 1.232, M['plastic'], 0.01)
for x in (TB[0] + 0.14, TB[1] - 0.14):
    box2(C, 'toolbox_latch', x - 0.03, x + 0.03, 0.86, 0.91, 1.23, 1.245, M['galv'], 0.004)
    box2(C, 'toolbox_hanger', x - 0.02, x + 0.02, 0.97, CH_TOP - 0.07, 0.95, 1.15, K, 0.003)

# --- arka: alt koruma tamponu ve destekleri, tozluk (lamba tamponu, askıları ve dikmeleri ayrı GLB: aşağıda export_variants) ---
box2(C, 'bumper', -0.11, -0.005, 0.475, 0.585, -1.2, 1.2, M['white'], 0.014)
for s in (-1, 1):
    box2(C, 'bumper_cap', -0.115, 0.0, 0.47, 0.59, s * 1.2, s * 1.222, M['rubber'], 0.006)
# şasiden demire inen eğik destekler kaldırıldı (kullanıcı 2026-10-23); demiri lamba tamponunun dikmeleri taşır (bumper_extras)
# logolu levha kaldırıldı (kullanıcı 2026-10-22); tek parça tozluk, üzerinde TRAILER SYSTEMS (revize md. 11). Demirin ön (dorseye
# bakan) yüzüne arkadan monte (kullanıcı 2026-10-23): demirin arka yüzü temiz kalır, yalnız cıvata başları görünür
MF = {'rubber': M['rubber'], 'zinc': M['galv'], 'print': material('MudflapPrint', '#f2f3f5', 0.5, 0.0)}
mudflap_text = build_mudflap(C, MF, -0.11, 0.505, 0.20, 1.15, behind=-0.005)  # demirin (0,475–0,585) alt kenarına kenetli

# --- şasiye ait çıkartmalar: yan koruma ve arka levha logoları ---
lq = []
for s in (-1, 1):
    lh = 0.22
    lq.append(side_quad((GX0 + GX1) / 2, 0.625, lh * 720 / 528, lh, s * 1.2465, s))
chassis_logos = decal_mesh('ChassisLogos', lq, LOGO)

chassis = join(C, 'StdChassis')


# --- arka lamba tamponları: tip başına ayrı GLB (site stop lambasına göre birini yükler). Sac tampon, şasiye askılar (üst dudaktaki
# oval delikten iki M12 cıvatayla; askının ayağı arka traversin altına kaynaklı), alt koruma tamponuna inen dikmeler. Kendi
# malzemeleri (şasinin AO dokusu paylaşılmaz); AO pişirilmez, gölgeyi sahne verir.
from mathutils import Matrix  # noqa: E402
MQ = {'sheet': material('BumperWhite', '#eceef1', 0.32, 0.05, 0.45), 'ktl': material('BumperKTL', '#40454c', 0.5, 0.2, 0.25),
      'zinc': material('BumperZinc', '#b8bdc2', 0.3, 1.0), 'rubber': material('BumperRubber', '#141517', 0.85, 0.0)}


def bumper_extras(Q, kind):
    """Dorseye özel: askılar (üst dudaktaki oval delikten iki M12 cıvata; ayağı arka traversin altına kaynaklı), alt koruma
    tamponuna inen dikmeler"""
    b = BUMPERS[kind]
    lip = CARRIER_X - b['d'] * BMM  # dudağın dorseye bakan yüzü
    ys = LAMP_Y + ((b['h'] - BT) / 2 - b['lip'] + 13.4) * BMM  # dudaktaki oval deliğin ortası (bumpers.py SLOT_FROM_TIP)
    bot = LAMP_Y - b['h'] / 2 * BMM
    for s in (-1, 1):
        z = s * HANGER_Z
        box2(Q, 'hanger', lip - 0.008, lip, ys - 0.035, 1.06, z - 0.04, z + 0.04, MQ['ktl'], 0.002)
        box2(Q, 'hanger_foot', lip - 0.008, lip + 0.07, 1.048, 1.06, z - 0.04, z + 0.04, MQ['ktl'], 0.002)
        for dz in (-0.02, 0.02):
            zb = z + dz
            cylinder(Q, 'bolt', 0.006, (lip - 0.026, ys, zb), (lip + BT * BMM + 0.008, ys, zb), MQ['zinc'], 12, 0.0)
            cylinder(Q, 'bolt_head', 0.0095, (lip + BT * BMM, ys, zb), (lip + BT * BMM + 0.008, ys, zb), MQ['zinc'], 6, 0.001)
            cylinder(Q, 'washer', 0.012, (lip - 0.008, ys, zb), (lip - 0.0105, ys, zb), MQ['zinc'], 20, 0.0)
            cylinder(Q, 'nut', 0.0095, (lip - 0.0105, ys, zb), (lip - 0.0205, ys, zb), MQ['zinc'], 6, 0.001)
        # alt koruma tamponuna (üstü 0,585) inen dikme, lamba tamponunun alt flanşının altında
        box2(Q, 'underrun_post', max(lip + 0.006, -0.11), CARRIER_X - 0.005, 0.585, bot, z - 0.03, z + 0.03, MQ['sheet'], 0.004)


export_variants('standart', CARRIER_X, LAMP_Y, MQ, bumper_extras, RAW_DIR)

# --- tekerlekler (tek model, 6 örnek + yedek) ---
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
spare = bpy.data.objects.new('Wheel', wheel.data)
scene.collection.objects.link(spare)
spare.location = bl((SPX, 0.615, 0))
spare.rotation_euler = (math.pi / 2, 0, 0)
wheels.append(spare)

# =====================================================================
# KASA
# =====================================================================
B = Parts()

# taban (fenolik kontrplak) ve arka giriş sacı
box2(B, 'floor', XF + 0.04, BEAM_X1, CH_TOP, FLOOR_TOP, -RAIL_Z + 0.02, RAIL_Z - 0.02, MB['floor'], 0.0)
box2(B, 'rear_entry', BEAM_X1, XR - 0.06, CH_TOP, FLOOR_TOP + 0.004, -1.18, 1.18, MB['alu'], 0.003)

PX0 = XF + 0.12  # yan panelin görünen ön ucu (köşe dikmesinin arkası)
PX1 = XR - 0.12
for s in (-1, 1):
    zf = s * (W2 - 0.005)
    # yan panel (tek yüz, dışa bakar)
    quad(B, 'side_panel', side_quad((PX0 + PX1) / 2, (Y_PANEL0 + Y_PANEL1) / 2, PX1 - PX0 + 0.02, Y_PANEL1 - Y_PANEL0 + 0.04, zf, s), MB['grp'])
    # alt ve üst alüminyum köşe profilleri (dış köşesi yuvarlak)
    zo = s * W2
    zi = s * (W2 - 0.04)
    bot = [(zi, Y_PANEL0 + 0.0), (s * (W2 - 0.007), Y_PANEL0), (zo, Y_PANEL0 - 0.007), (zo, Y_RAIL_B + 0.007), (s * (W2 - 0.007), Y_RAIL_B), (zi, Y_RAIL_B)]
    top = [(zi, Y_PANEL1), (s * (W2 - 0.007), Y_PANEL1), (zo, Y_PANEL1 + 0.007), (zo, Y_TOP - 0.022), (s * (W2 - 0.012), Y_TOP - 0.004), (s * (W2 - 0.03), Y_TOP), (zi, Y_TOP)]
    if s < 0:
        bot = list(reversed(bot))
        top = list(reversed(top))
    prism_zy(B, 'rail_bottom', bot, XF + 0.1, XR - 0.1, MB['alu'], 0.0)
    prism_zy(B, 'rail_top', top, XF + 0.04, XR - 0.1, MB['alu'], 0.0)
    # alt profilde yan kontur bandı (beyaz reflektif, kesikli: ECE R48)
    x = XF + 0.6
    while x < XR - 0.6:
        box2(B, 'side_tape', x, x + 0.5, Y_PANEL0 - 0.06, Y_PANEL0 - 0.03, s * W2, s * (W2 + 0.0015), MB['silver'], 0.0)
        x += 0.8
    # perçinler: alt/üst profil, ön ve arka dikmeler
    rx = []
    x = XF + 0.25
    while x < XR - 0.2:
        rx.append(x)
        x += 0.15
    for x in rx:
        for y in (Y_PANEL0 - 0.012, Y_PANEL1 + 0.014):
            cylinder(B, 'rivet', 0.0065, (x, y, zo), (x, y, s * (W2 + 0.003)), MB['alu'], 8, 0.0, 0.0045)
    y = Y_PANEL0 + 0.08
    while y < Y_PANEL1 - 0.05:
        for x in (XF + 0.085, XR - 0.075):
            cylinder(B, 'rivet', 0.0065, (x, y, zo), (x, y, s * (W2 + 0.003)), MB['inox'] if x > -1 else MB['alu'], 8, 0.0, 0.0045)
        y += 0.1

# ön köşe dikmeleri (L profil: ön yüz 0,1 m, yan yüz 0,13 m)
for s in (-1, 1):
    pts = [(XF, s * (W2 - 0.1)), (XF, s * (W2 - 0.012)), (XF + 0.012, s * W2), (XF + 0.13, s * W2), (XF + 0.13, s * (W2 - 0.02)), (XF + 0.022, s * (W2 - 0.02)), (XF + 0.022, s * (W2 - 0.1))]
    if s < 0:
        pts = list(reversed(pts))
    prism_xz(B, 'front_post', pts, Y_RAIL_B, Y_TOP - 0.01, MB['alu'], 0.0)
    y = Y_PANEL0 + 0.05
    while y < Y_PANEL1:
        cylinder(B, 'rivet', 0.0065, (XF, y, s * (W2 - 0.05)), (XF - 0.003, y, s * (W2 - 0.05)), MB['alu'], 8, 0.0, 0.0045)
        y += 0.1

# ön panel: oluklu (trapez) çelik sac, beyaz
n = 36
pitch = 2 * (W2 - 0.1) / n
front_pts = []
for i in range(n):
    z0 = -(W2 - 0.1) + i * pitch
    front_pts += [(XF + 0.022, z0), (XF + 0.022, z0 + 0.008), (XF + 0.008, z0 + 0.02), (XF + 0.008, z0 + pitch - 0.02), (XF + 0.022, z0 + pitch - 0.008)]
front_pts += [(XF + 0.022, W2 - 0.1), (XF + 0.03, W2 - 0.1), (XF + 0.03, -(W2 - 0.1))]
prism_xz(B, 'front_panel', front_pts, Y_RAIL_B + 0.03, Y_PANEL1 + 0.04, MB['steel'], 0.0)
box2(B, 'front_top', XF, XF + 0.06, Y_PANEL1 + 0.03, Y_TOP, -(W2 - 0.012), W2 - 0.012, MB['alu'], 0.006)
box2(B, 'front_bottom', XF - 0.002, XF + 0.03, Y_RAIL_B, Y_RAIL_B + 0.06, -(W2 - 0.1), W2 - 0.1, MB['alu'], 0.004)
# bağlantı konsolu: soketler (sitede kodla) + kırmızı/sarı hava kavramaları
box2(B, 'console', XF - 0.006, XF + 0.008, SOCKET_Y - 0.17, SOCKET_Y + 0.17, -0.58, 0.58, MB['console'], 0.006)
for zc, col in ((0.44, MB['gladRed']), (-0.44, MB['gladYellow'])):
    cylinder(B, 'glad_base', 0.035, (XF - 0.006, SOCKET_Y, zc), (XF - 0.05, SOCKET_Y, zc), MB['dark'], 16, 0.003)
    box2(B, 'glad_hand', XF - 0.075, XF - 0.05, SOCKET_Y - 0.03, SOCKET_Y + 0.05, zc - 0.05, zc + 0.05, col, 0.008)
    box2(B, 'glad_seal', XF - 0.08, XF - 0.074, SOCKET_Y - 0.02, SOCKET_Y + 0.02, zc - 0.03, zc + 0.03, MB['rubber'], 0.004)

# tavan: yarı saydam GRP (tek yüz) + üstten görünen galvaniz omega izleri
quad(B, 'roof', [(XF + 0.04, Y_TOP - 0.006, W2 - 0.03), (XR - 0.1, Y_TOP - 0.006, W2 - 0.03), (XR - 0.1, Y_TOP - 0.006, -(W2 - 0.03)), (XF + 0.04, Y_TOP - 0.006, -(W2 - 0.03))], MB['roof'])
x = XF + 0.5
while x < XR - 0.3:
    box2(B, 'roof_bow', x - 0.025, x + 0.025, Y_TOP - 0.0065, Y_TOP - 0.004, -(W2 - 0.04), W2 - 0.04, MB['grp'], 0.0)
    x += 0.6

# arka çerçeve (paslanmaz): köşe dikmeleri + üst başlık; kırmızı kontur bandı (ECE 104)
for s in (-1, 1):
    pts = [(XR - 0.13, s * W2), (XR - 0.012, s * W2), (XR, s * (W2 - 0.012)), (XR, s * (W2 - 0.09)), (XR - 0.06, s * (W2 - 0.09)), (XR - 0.06, s * (W2 - 0.02)), (XR - 0.13, s * (W2 - 0.02))]
    if s < 0:
        pts = list(reversed(pts))
    prism_xz(B, 'rear_post', pts, CH_TOP, Y_TOP - 0.13, MB['inox'], 0.0)
    box2(B, 'rear_tape_v', XR, XR + 0.0015, 1.3, Y_TOP - 0.16, s * (W2 - 0.075), s * (W2 - 0.03), MB['red'], 0.0)
box2(B, 'rear_header', XR - 0.13, XR, Y_TOP - 0.14, Y_TOP, -W2, W2, MB['inox'], 0.008)
box2(B, 'rear_tape_h', XR, XR + 0.0015, Y_TOP - 0.115, Y_TOP - 0.07, -(W2 - 0.03), W2 - 0.03, MB['red'], 0.0)

# arka kapılar: dikey alüminyum profillerden (V oluklu birleşim), menteşeler, conta, gizli kilit kolu
DY0, DY1 = 1.27, Y_TOP - 0.145
DXa, DXb = XR - 0.055, XR - 0.008
leaf = W2 - 0.092
for s in (-1, 1):
    # kanat: düz yüzey (logo uygulanabilir), profil birleşimleri çok ince açık gri çizgiler (~0,2 m aralık)
    box2(B, 'door_leaf', DXa, DXb, DY0, DY1, s * 0.004, s * leaf, MB['door'], 0.004)
    nstrip = 6
    sw = (leaf - 0.004) / nstrip
    for i in range(1, nstrip):
        zc = s * (0.004 + i * sw)
        box2(B, 'door_joint', DXb, DXb + 0.0006, DY0 + 0.02, DY1 - 0.02, zc - 0.001, zc + 0.001, MB['joint'], 0.0)
    for y in (1.45, 2.03, 2.61, 3.19, 3.72):
        box2(B, 'hinge_leaf', DXb - 0.002, DXb + 0.012, y - 0.035, y + 0.035, s * (leaf - 0.16), s * (leaf + 0.005), MB['inox'], 0.004)
        cylinder(B, 'hinge_pin', 0.017, (DXb + 0.018, y - 0.045, s * (leaf + 0.03)), (DXb + 0.018, y + 0.045, s * (leaf + 0.03)), MB['inox'], 14, 0.003)
        box2(B, 'hinge_frame', XR - 0.002, XR + 0.012, y - 0.035, y + 0.035, s * (leaf + 0.03), s * (W2 - 0.03), MB['inox'], 0.004)
    # ECE R70 uzun araç plakaları (alt dış köşe)
    box2(B, 'r70_red', DXb, DXb + 0.002, 1.655 - 0.2825, 1.655 + 0.2825, s * 0.88, s * 1.08, MB['red'], 0.0)
    box2(B, 'r70_yellow', DXb + 0.002, DXb + 0.003, 1.655 - 0.2525, 1.655 + 0.2525, s * 0.91, s * 1.05, MB['yellow'], 0.0)
box2(B, 'door_seal', DXb - 0.004, DXb + 0.004, DY0, DY1, -0.006, 0.006, MB['rubber'], 0.002)
box2(B, 'lock_recess', DXb, DXb + 0.004, 1.88, 2.12, -0.32, -0.2, MB['dark'], 0.004)
box2(B, 'lock_handle', DXb + 0.004, DXb + 0.016, 1.9, 2.1, -0.3, -0.27, MB['inox'], 0.004)
box2(B, 'door_bottom_seal', DXa, DXb, DY0 - 0.012, DY0, -leaf, leaf, MB['rubber'], 0.0)

body = join(B, 'StdBody')
# kasa içi hiç görünmez: içe bakan yüzler silinir
delete_interior(body, XF + 0.025, XR - 0.05, FLOOR_TOP - 0.002, Y_TOP - 0.012, -(W2 - 0.025), W2 - 0.025)

# kasa çıkartmaları: iki yanda büyük logo; arkada iki kapının ortasında büyük logo (revize md. 7)
bq = []
LH = 2.1
for s in (1, -1):
    bq.append(side_quad(-L / 2 + 0.6, Y_PANEL0 + (Y_PANEL1 - Y_PANEL0) * 0.55, LH * 720 / 528, LH, s * (W2 - 0.0035), s))
body_logos = decal_mesh('BodyLogos', bq, LOGO)
# Arka logo: kapı alanının en büyüğü. Genişlik menteşelerle sınırlı (iç uçları z ±1,023 → 2,0 m), alt kenar kilit kolunun
# (y 2,12) üstünde, üst kenar kapı üst kenarının (3,875) altında; dikeyde bu aralığın ortası. Kapı birleşimindeki conta
# logonun ortasından geçer (gerçek araçta da kapılar ayrı açılır). Yakın çekimde keskin olsun diye yüksek çözünürlüklü
# özgün logodan (design/source, 1773 px; beyaz-mavi zemin) mavi + saydam doku üretilir: 886 px/m.
REAR_LOGO_W = 2.0
REAR_LOGO_H = REAR_LOGO_W * 1300 / 1773
REAR_LOGO_Y = (2.17 + DY1) / 2
rear_logo = decal_mesh('RearLogo', [rear_quad(DXb + 0.0015, REAR_LOGO_Y, 0.0, REAR_LOGO_W, REAR_LOGO_H)],
                       logo_from_original('RearLogoMat', 'design/source/horpol-logo-original.png'))

# =====================================================================
# UV, AO, dışa aktarma
# =====================================================================
smart_uv(chassis, 0.003)
smart_uv(wheel, 0.004)
smart_uv(body, 0.003, planar={'FrontSteel': 'x'})
size = 1024 if FAST else 2048
targets = bake_ao([(chassis, size, 'std_chassis_ao'), (wheel, 512 if FAST else 1024, 'std_wheel_ao'), (body, size, 'std_body_ao')], K, samples=16 if FAST else 96, distance=0.6)
decals = [chassis_logos, body_logos, rear_logo, mudflap_text]
for ob, img in targets:
    # şasi ve tekerlekler kasasız pişer (tesisat görünümünde kasa gizli; gölgesi şasiye düşmemeli), kasa şasiyle birlikte
    run_bake(ob, img, hide=decals + ([body] if ob is not body else []))
    print('BAKED', ob.name)
link_occlusion([chassis, wheel, body])

export_glb(os.path.join(RAW_DIR, 'standart-chassis.glb'), [chassis, chassis_logos, mudflap_text] + wheels)
export_glb(os.path.join(RAW_DIR, 'standart-body.glb'), [body, body_logos, rear_logo])
tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)
print(f'TRIS chassis={tri(chassis)} wheel={tri(wheel)} body={tri(body)}')

# --- zemin temas gölgesi: dorsenin altındaki düzleme AO pişir, ters çevir (beyaz = koyu), WebP ---
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
scene.world.light_settings.distance = 1.6
scene.cycles.samples = 32 if FAST else 256
for o in decals:
    o.hide_render = True
select_only([ground])
bpy.ops.object.bake(type='AO', margin=2, use_clear=True)
px = np.array(gimg.pixels[:], dtype=np.float32).reshape(chh, cw, 4)
ao = px[:, :, 0]
print('CONTACT AO range', float(ao.min()), float(ao.max()), 'visible', [o.name for o in scene.objects if not o.hide_render and o.type == 'MESH'][:12])
dark = np.clip((1.0 - ao) * 1.15, 0.0, 1.0) ** 0.9


def blur(a, r):
    # ayrılabilir kutu bulanıklığı (3 geçiş ≈ Gauss)
    for _ in range(3):
        for ax in (0, 1):
            p = np.pad(a, [(r, r) if i == ax else (0, 0) for i in range(2)], mode='edge')
            c = np.cumsum(p, axis=ax, dtype=np.float64)
            c = np.insert(c, 0, 0, axis=ax)
            a = ((np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)).astype(np.float32)
    return a


dark = blur(dark, 1 if FAST else 2)
# kenarlara doğru sıfıra iner (dikdörtgen sınır görünmesin)
yy, xx = np.mgrid[0:chh, 0:cw]
ex = np.minimum(xx, cw - 1 - xx) / (cw * 0.03)
ez = np.minimum(yy, chh - 1 - yy) / (chh * 0.12)
fade = np.clip(np.minimum(ex, ez), 0, 1)
dark = dark * (fade * fade * (3 - 2 * fade))
out = bpy.data.images.new('contact_out', cw, chh, alpha=False)
# renk uzayı piksellerden ÖNCE: sonradan değişirse oluşturulan görüntünün tamponu sıfırlanır
out.colorspace_settings.name = 'Non-Color'
o = np.zeros((chh, cw, 4), dtype=np.float32)
o[:, :, 0] = o[:, :, 1] = o[:, :, 2] = dark
o[:, :, 3] = 1.0
out.pixels[:] = o.ravel()
out.update()
cpath = os.path.join(OUT_DIR, 'standart-contact.webp')
out.filepath_raw = cpath
out.file_format = 'WEBP'
out.save(filepath=cpath, quality=90)
print('CONTACT', cpath, f'{os.path.getsize(cpath) / 1024:.0f} KB')

write_anchors(ANCHORS, anchors_dict())

# ================= önizleme render'ları (yalnızca kontrol) =================
if PREVIEW:
    os.makedirs(PREVIEW, exist_ok=True)
    ground.hide_render = True
    for o in decals:
        o.hide_render = False
    w = scene.world
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    bg.inputs['Color'].default_value = (0.8, 0.82, 0.85, 1)
    bg.inputs['Strength'].default_value = 0.8
    bpy.ops.mesh.primitive_plane_add(size=60, location=(-6.8, 0, 0))
    fl = bpy.context.active_object
    fl.data.materials.append(material('Floor', '#cfd1d4', 0.6, 0.0))
    sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    scene.cycles.samples = 24 if FAST else 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    scene.view_settings.view_transform = 'AgX'
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam

    def shot(name, loc, target, lens=50):
        cam.location = bl(loc)
        d = bl(target) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        scene.render.filepath = os.path.join(PREVIEW, name)
        bpy.ops.render.render(write_still=True)

    shot('rear34.png', (6.0, 2.6, 7.5), (-4.0, 1.6, 0), 40)
    body.hide_render = True
    body_logos.hide_render = True
    rear_logo.hide_render = True
    shot('chassis34.png', (3.5, 5.0, 6.5), (-5.0, 0.9, 0), 32)
    print('PREVIEWS', PREVIEW)
