# Silobas (devrilmeyen alüminyum silo, 33 m³, 3 akslı; referans: Kässbohrer K.SSL 33 / 2 - 10 / 24_EU). Blender'da betikle
# modellenir; şasi/tekerlek/üst yapı AO + yüzey dokusu pişirilir, tank kabuğu tekrarlanan fırçalanmış alüminyum dokusu ve
# ikinci UV'deki AO ile dışa aktarılır. Sitenin okuyacağı bağlantı noktaları aynı ölçülerden JSON olarak yazılır.
# Belge: docs/Silobas Dorse/README.md
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/silo.py -- [--fast] [--anchors] [--preview <klasör>]
#   ardından: npm run models:pack -- silo
#
# Ölçü kaynağı (teknik tablo, "K.SSL 33 / 2 - 10 / 24_EU"): dış boy 9.385, tank çapı 2.550, eyer yüksekliği (H5) 1.220,
# hacim 33 m³, 1 bölme, 2 × DN450 basınçlı kapak, arkadan boşaltma, 2 × NW100 5 m hortum taşıyıcı (arka kapaklı),
# alüminyum ekstrüzyon şasi (destek konsolunun içine kaynaklı), 3 BPW havalı süspansiyonlu 9 t aks, 385/65 R22,5.
# Broşürün ölçekli çizimi piksel ölçümüyle okundu: 80,8 px/m (L = 9.385 ölçü çizgisi; akslar arası 1.310 ve H5 ile tutarlı).
# Çizimden: king pin önden 0,50 m (DLRv), dingil mesafesi (king pin → orta aks) 6,49 m, akslar -3,71 / -2,40 / -1,10,
# tank üstü 3,87 m (ekvator 2,59), silindir -7,45 … -1,40, ön bombe ucu ~-7,97, arka bombe ucu ~-0,98, kapaklar -6,13 / -2,78,
# iki huni: tank alt yarısı uçlarda ekvatordan içeri çekilir, ortada (-5,35 … -3,55) tam silindir. Önde king pin
# konsolundan ön bombeye çıkan eğik burun kulesi (ön çizgi (-8,79; 1,45) → (-7,92; 3,40)), arkada 1,48 m genişliğinde,
# üstü 2,78 m'de yuvarlatılmış dikey arka kule (boşaltma dolabı kapağı), sol arkada (+z) merdiven, iniş ayağı -6,81.
# Kesin olmayanlar (doğrulanmadı): huni kesitinin biçimi, boşaltma ağızlarının yeri, şasi profillerinin kesiti, kulelerin
# derinliği, hortum taşıyıcının kesiti.
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
ANCHORS = os.path.abspath('src/configurator/engine/silo-anchors.json')

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import (  # noqa: E402
    Parts, add_obj, arch, bake_ao, bake_surface, beam, bl, box, box2, build_wheel, ground_contact, landing_gear, preview_renders, running_gear, cylinder,
    decal_mesh, export_glb, galvanized_checker_tile, hose, join, logo_material, loft, material, np_image, pchip, planar_uv, poly_tube,
    prism_xy, prism_zy, rear_quad, run_bake, smart_uv, tank_metal_tile, tex_material, tiled_ao_finish, tiled_ao_setup, write_anchors,
)

scene = bpy.context.scene

# ================= ölçüler (metre; x: arka uç 0, ön -L) =================
L = 9.385
W = 2.55
W2 = W / 2
XF = -L  # king pin konsolunun ön yüzü (soketler)
XR = 0.0
R = 0.536  # 385/65 R22,5
WZ = 1.04  # tekerlek merkezi (yanal); dış yüz ~1,23
H5 = 1.22
KING_X = XF + 0.50
WB = 6.49
AX_MID = KING_X + WB
AXLES = [AX_MID - 1.31, AX_MID, AX_MID + 1.31]
LEG_X = -6.81
# tank: Ø2,55 silindir + bombeli uçlar. Alt yarı uçlarda huniye döner: kesit üstte daire yayı, kırılma noktasından (yan
# görünüşte ekvatordan orta alta inen çizgi) tabana hafif dışbükey yanlarla iner ("V"); ortada kesit tam daire.
RT = 1.275
YC = 2.59
TOP = YC + RT
XHF, DF = -7.45, 0.52  # ön kapak tabanı, bombe derinliği
XHR, DR = -1.40, 0.42  # arka kapak tabanı, bombe derinliği
XM0, XM1 = -5.35, -3.55  # tam silindir bölgesi (hunilerin bittiği yer)
OUT = [-6.25, -2.65]  # boşaltma ağızları (huni tabanının en alt noktası)
DOMES = [-6.13, -2.78]
DOME_TOP = 3.95
PHI_MIN = 0.12
f_keel = pchip([XHF, OUT[0], XM0, XM1, OUT[1], XHR], [1.42, 1.03, YC - RT, YC - RT, 1.03, 1.42])
f_wb = pchip([XHF, OUT[0], XM0, XM1, OUT[1], XHR], [0.36, 0.14, 0.03, 0.03, 0.14, 0.36])
# burun kulesi (king pin konsolundan ön bombeye; önden görünüşte üstü yuvarlak dik levha)
NOSE_A, NOSE_B = (-8.79, 1.45), (-7.92, 3.40)  # ön yüzün alt ve üst ucu (orta düzlem)
NOSE_Z, NOSE_BACK = 0.42, -7.05
# arka kule (boşaltma dolabı): x0 … x1, y0 … üst, yarı genişlik, köşe yarıçapı
RTW = (-2.05, -0.62, 1.06, 2.78, 0.74, 0.28)
# şasi: alüminyum kutu ana kirişler (tankın altında), aks bölgesinde alt çerçeve
BZ = 0.55
BOT, BTOP = 1.27, 1.41
SUB_BOT = 1.00
SUB_X0, SUB_X1 = AXLES[0] - 0.95, AXLES[-1] + 0.62
SX0, SX1 = -6.62, -4.48  # yan koruma + hortum taşıyıcı
FR0, FR1 = AXLES[0] - 0.62, -0.40  # çamurluk rayı (yan markerlar bunun üstünde)
HY = 1.45  # tesisat düzlemi (kirişlerin üstü, tankın altı)
SOCKET_Y = 1.36
LAMP_Y = 0.62
PLATE_Y = 0.62
FRONT_Y, FRONT_Z = 2.05, 0.30  # ön pozisyon lambaları: burun kulesinin ön yüzünde
CS = (XF - 0.5, XR + 0.5, -W2 - 0.45, W2 + 0.45)
NU, NL = 56, 14  # halka: üst yay ve alt yan (her yan) nokta sayısı


def hopper_t(x):
    """Huni payı: 1 kapak tabanında (kırılma ekvatorda), 0 tam silindir bölgesinde"""
    if x <= XHF or x >= XHR:
        return 1.0
    if x < XM0:
        u = (XM0 - x) / (XM0 - XHF)
    elif x > XM1:
        u = (x - XM1) / (XHR - XM1)
    else:
        return 0.0
    return u


def ring2d(x, nu=NU, nl=NL):
    """Kesit halkası [(z, y)]: sağ taban ucundan başlar, sağ huni yanı → kırılma → üst yay → sol kırılma → sol taban ucu"""
    t = hopper_t(x)
    phi = max(PHI_MIN, math.acos(max(-1.0, min(1.0, 1.0 - 0.98 * t))))
    pz, py = RT * math.sin(phi), YC - RT * math.cos(phi)
    kz, ky = f_wb(x), min(f_keel(x), py - 0.004)
    # huni yanı: K → P ikinci derece Bézier, hafif içbükey (referanstaki "kaşık" yüzey; kırılmada keskin kenar)
    mz, my = (kz + pz) / 2, (ky + py) / 2
    dz, dy = pz - kz, py - ky
    ln = math.hypot(dz, dy) or 1.0
    nz, ny = dy / ln, -dz / ln  # dışa dik
    bow = -0.045 * ln * min(1.0, t * 3.0)
    cz, cy = mz + nz * bow, my + ny * bow
    low = []
    for j in range(nl):
        s = j / nl
        low.append(((1 - s) ** 2 * kz + 2 * (1 - s) * s * cz + s * s * pz, (1 - s) ** 2 * ky + 2 * (1 - s) * s * cy + s * s * py))
    a0 = phi - math.pi / 2
    a1 = math.pi + (math.pi / 2 - phi)
    up = [(RT * math.cos(a0 + (a1 - a0) * i / nu), YC + RT * math.sin(a0 + (a1 - a0) * i / nu)) for i in range(nu + 1)]
    return low + up + [(-z, y) for z, y in reversed(low)]


def head_rings(x0, d, sign, n=12, p=2.0):
    """Bombeli kapak: taban halkası (x0) ekvator merkezine doğru küçülür; x = x0 + sign·d·sin φ"""
    base = ring2d(x0)
    out = []
    for i in range(1, n + 1):
        ph = (math.pi / 2) * i / (n + 0.6)
        e = math.sin(ph)
        sg = (1.0 - e ** p) ** (1.0 / p)
        out.append([(x0 + sign * d * e, YC + (y - YC) * sg, z * sg) for z, y in base])
    return out, (x0 + sign * d, YC, 0.0)


def under(x, z):
    """Tank alt yüzeyinin yanal z'deki yüksekliği (gövde bölgesinde)"""
    pts = ring2d(x, 24, 12)
    z = abs(z)
    best = YC
    for (z1, y1), (z2, y2) in zip(pts, pts[1:]):
        if y1 < YC + 0.01 and (z1 - z) * (z2 - z) <= 0 and z1 != z2:
            best = min(best, y1 + (y2 - y1) * (z - z1) / (z2 - z1))
    return best


def dome_x(y, z, front=True):
    """Bombe yüzeyinin (y, z) noktasındaki x'i (yaklaşık: silindir kesitli bölge için)"""
    r = math.hypot(y - YC, z) / RT
    e = math.sqrt(max(0.0, 1.0 - min(1.0, r) ** 2))
    return XHF - DF * e if front else XHR + DR * e


def nose_point(y):
    """Burun kulesinin ön yüzünde (orta düzlem) y yüksekliğindeki x"""
    (xa, ya), (xb, yb) = NOSE_A, NOSE_B
    return xa + (xb - xa) * (y - ya) / (yb - ya)


def side_y_profile():
    # yan markerlar: önde yan koruma üst rayı, aks bölgesinde çamurluk rayı
    return [[SX0, 1.03], [SX1, 1.03], [FR0, 1.14], [XR, 1.14]]


# ================= lamba montaj haritası (UN R48; yalnız JSON'a yazılır, modeli değiştirmez) =================
# Sabit parçalar: şasi (lamba barı, yan koruma rayı, çamurluk rayı, kirişler), arka kule ve yürüme yolu. Tank kabuğu lamba yeri değil.
BAR_Z = 1.24  # box2 'lamp_bar' z ±1,24, y 0,50–0,74, arka yüz x = 0
PLATE_W, PLATE_H = 0.52, 0.11
SIDE_Y_GUARD = 1.025  # yan koruma üst rayı (0,99–1,06) ortası
SIDE_Y_RAIL = 1.14  # çamurluk rayı (1,10–1,18) ortası
SIDE_ZW = 1.272  # rayların dış yüzü
SIDE_N = 5
# Revize 2026-10-20: arkadan öne ilk 3 marker lastiklerin (aksların) ortasında çamurluk rayında, sonraki 2 marker yan korumanın
# iki penceresinin (dikmeler SX0+0,03 / orta / SX1−0,03) ortasında üst rayda. Daha az marker seçilirse yuvalar uçlar korunarak seyreltilir.
_SX_MID = (SX0 + SX1) / 2
SIDE_SLOTS = [[round(x, 3), SIDE_Y_RAIL] for x in reversed(AXLES)] + \
             [[round((SX1 + _SX_MID) / 2, 3), SIDE_Y_GUARD], [round((SX0 + _SX_MID) / 2, 3), SIDE_Y_GUARD]]
SIDE_X0, SIDE_X1 = SIDE_SLOTS[-1][0], SIDE_SLOTS[0][0]
FB_X, FB_Y = -7.20, 1.34  # ön braket (yalnız ön pozisyon): iniş ayağının (−6,81) önünde, kirişin (−7,35…) dış yüzünden dışa
FB_Z0, FB_Z1 = BZ + 0.05, 1.19
ARM_FRONT_X = SX0 + 0.05  # ön lastik kol: yan korumanın en ön üst ucu (üst ray dış yüzü)
WORK_Y, WORK_Z = 2.55, 0.50  # arka kulenin arka yüzü (x −0,62), üst köşe yuvarlağının içinde
BEACON_X, BEACON_Z = RTW[1] - 0.17, 0.40  # tepe lambaları: arka kulenin düz üstünde, çalışma lambalarının üstünde
TRUNK_Y, TRUNK_Z = 1.34, BZ - 0.08  # alüminyum kutu kirişin (y 1,27–1,41) iç yüzü
MODULE_X = -0.95  # −1,775 ve −0,62 traversleri arasında
REAR_JX = -0.50  # arka traversin (−0,42…−0,30) ÖNÜ: arkadan bakınca kablo traversin arkasında kalır
# yan hat rayın içinde (tek düz hat): çamurluk rayı (1,10–1,18) ve yan koruma üst rayı (0,99–1,06) iç yüzünde
RAIL_Z = 1.215
RAIL_PROFILE = [[SX0, 1.055], [SX1, 1.055], [FR0, 1.17], [-0.425, 1.17]]


def mounts_dict():
    fb = [[FB_X, FB_Y, FB_Z0], [FB_X, FB_Y, FB_Z1]]
    return {
        'rear': {'x': XR, 'y': LAMP_Y, 'zOuter': BAR_Z, 'zInner': 0.30, 'faceX': XR},
        'plate': {'x': XR, 'y': round(PLATE_Y + PLATE_H / 2 + 0.025, 3), 'z': [-0.17, 0.17], 'plateY': PLATE_Y,
                  'plateW': PLATE_W, 'plateH': PLATE_H},
        'side': {'x0': SIDE_X0, 'x1': SIDE_X1, 'y': side_y_profile(), 'z': SIDE_ZW, 'maxPerSide': SIDE_N, 'slots': SIDE_SLOTS,
                 'rule': {'firstFromFront': 3.0, 'lastFromRear': 1.0, 'maxGap': 3.0}, 'avoid': [], 'brackets': None,
                 # yan hat: arka lambadan bar içinde içe (z 0,785, paçanın iç yanı) ve öne, paçanın ÖNÜNDE (x −0,425) yükselir:
                 # arkadan bakınca paça örter. Rayın içinde düz öne gider; ön pozisyon için yan koruma kolu (SX0+0,2) boyunca kirişe girer
                 'rail': {'z': RAIL_Z, 'y': RAIL_PROFILE, 'rise': [-0.425, None], 'pass': 0.785, 'exit': [SX0 + 0.2, 1.058]}},
        'front': {'x': FB_X - 0.025, 'y': FB_Y, 'z': 1.17, 'bracket': fb},
        'armFront': {'x': ARM_FRONT_X, 'y': SIDE_Y_GUARD, 'z': SIDE_ZW - 0.002, 'wallZ': SIDE_ZW - 0.002, 'bracket': None},
        'armRear': {'x': -0.07, 'y': LAMP_Y, 'z': BAR_Z, 'wallZ': BAR_Z, 'bracket': None},
        'armRearAlt': {'x': FR1 - 0.06, 'y': SIDE_Y_RAIL, 'z': SIDE_ZW, 'wallZ': SIDE_ZW, 'bracket': None},
        # kablo arka kulenin içinden (x −0,70) yükselir: kule dar olduğu için dış köşeden gitmez
        'work': [{'x': RTW[1] + 0.005, 'y': WORK_Y, 'z': s * WORK_Z, 'dir': [1, -0.35, 0], 'bracket': None, 'rise': [-0.70, WORK_Z]}
                 for s in (1, -1)],
        'beacon': [{'x': BEACON_X, 'y': RTW[3], 'z': s * BEACON_Z, 'bracket': None, 'rise': [BEACON_X + 0.06, BEACON_Z]} for s in (1, -1)],
        'harness': {'trunkY': TRUNK_Y, 'trunkZ': TRUNK_Z, 'profile': [[XF, TRUNK_Y], [XR, TRUNK_Y]], 'moduleX': MODULE_X,
                    'rearJunctionX': REAR_JX, 'rearDrop': {'z': 0.73, 'innerX': -0.16},
                    'notes': 'Demet king pin konsolunun içinden ve kutu kirişlerin iç yüzünde (y 1,34) arkaya gider; traverslerin '
                             'uçlarından geçer. Arka 7×1 hatlar arka traversin ÖNÜNDE (x −0,50) lamba barı dikmesinin hizasına '
                             '(z ±0,73) iner, dikmenin ve bar kolunun içinden bara girer: arkadan bakınca travers ve dikme kabloyu örter.'},
        'parents': {'rear': 'chassis', 'plate': 'chassis', 'side': 'chassis', 'front': 'chassis', 'armFront': 'chassis',
                    'armRear': 'chassis', 'armRearAlt': 'chassis', 'work': 'body', 'beacon': 'body', 'harness': 'chassis'},
        'notes': 'Tank kabuğu ince yüzey olduğu için lamba ve kol taşımaz. Burun kulesi orta düzlemde dar (z ±0,42): ön pozisyon orada '
                 'dış kenara ~0,9 m kalır; bu yüzden ön pozisyon kirişten dışa uzanan sabit ön brakette (x −7,20, y 1,34, uç z 1,19). '
                 'Ön lastik kol yan korumanın en ön üst ucunda (revize 2026-10-20). Yan markerlar (en çok 5/yan, revize): arkadan öne '
                 '3 tanesi aksların ortasında çamurluk rayında (1,14), 2 tanesi yan koruma pencerelerinin ortasında üst rayda (1,025). '
                 'İlk marker önden ~3,3 m (R48 6.18 ≤ 3 m, kullanıcı kararı; ön kolun turuncu yüzü önden ~2,8 m). Yan hat rayların '
                 'içinde tek düz hat, markerlara kısa düz uç. Arka kule yarı genişliği 0,74: kontur için dış kenara 0,53 m, kural dışı; '
                 'arka kol lamba barının dış ucunda. Çalışma lambaları arka kulenin arka yüzünde, tepe lambaları kulenin düz üstünde '
                 '(çalışma lambalarının üstünde); kabloları kulenin içinden çıkar.',
    }


def tank_rings(step_body, n_head):
    xs = []
    x = XHF
    while x < XHR - 1e-6:
        xs.append(x)
        x += step_body
    xs.append(XHR)
    fr, fc = head_rings(XHF, DF, -1, n_head)
    rr, rc = head_rings(XHR, DR, 1, n_head)
    return list(reversed(fr)) + [[(x, y, z) for z, y in ring2d(x)] for x in xs] + rr, fc, rc


def anchors_dict():
    """Sitenin okuyacağı bağlantı noktaları (three.js koordinatları; şema: src/configurator/engine/baked.ts)"""
    sections = []
    for x in (XHF, -6.9, OUT[0], XM0, -4.45, XM1, OUT[1], -2.0, XHR):
        sections.append([[x, y, z] for z, y in ring2d(x, 24, 6)])
    # orta düzlemde yan siluet: ön bombe, üst çizgi, arka bombe, alt huni çizgisi
    rings, fc, rc = tank_rings(0.25, 8)
    top_i = NL + NU // 2
    sil = [[r[top_i][0], r[top_i][1], 0.0] for r in rings]
    sil += [[rc[0], rc[1], 0.0]]
    sil += [[r[0][0], r[0][1], 0.0] for r in reversed(rings)]
    sil += [[fc[0], fc[1], 0.0]]
    sections.append(sil)
    # ekvator çevresi (üstten görünüş)
    eq = [[r[0][0], YC, max(p[2] for p in r)] for r in rings]
    sections.append(eq + [[x, y, -z] for x, y, z in reversed(eq)])
    # burun kulesi ve arka kule (yan konturları)
    for s in (-1, 1):
        sections.append([[NOSE_A[0], NOSE_A[1], s * NOSE_Z], [NOSE_B[0], NOSE_B[1], s * NOSE_Z], [dome_x(NOSE_B[1], NOSE_Z), NOSE_B[1], s * NOSE_Z],
                         [NOSE_BACK, 1.45, s * NOSE_Z]])
        sections.append([[RTW[1], RTW[2], s * RTW[4]], [RTW[1], RTW[3], s * RTW[4]], [XHR + 0.1, RTW[3], s * RTW[4]], [XHR + 0.1, RTW[2], s * RTW[4]]])
    for xd in DOMES:
        sections.append([[xd + 0.3 * math.cos(t), DOME_TOP - 0.05, 0.3 * math.sin(t)] for t in [i * math.pi / 8 for i in range(16)]])
    return {
        '_source': 'tools/blender/silo.py tarafından üretilir; elle düzenleme',
        'L': L,
        'W': W,
        'topY': DOME_TOP,
        'rear': {'x': XR, 'lampY': LAMP_Y, 'lampZ': [0.96, 0.56], 'plateY': PLATE_Y, 'dropX': -0.2},
        'side': {'x0': SX0 + 0.05, 'x1': -0.55, 'z': W2 + 0.003, 'profile': side_y_profile()},
        'front': {'x': nose_point(FRONT_Y) - 0.03, 'y': FRONT_Y, 'z': FRONT_Z},
        'armFront': {'x': -7.25, 'y': 2.7, 'z': W2},
        'armRear': {'x': -1.6, 'y': 2.7, 'z': W2},
        'extra': {'x': RTW[1], 'y': 2.55, 'z0': 0.55, 'z1': 0.30},
        'socket': {'x': XF - 0.005, 'y': SOCKET_Y},
        'harness': {'y': HY, 'frontX': XF + 0.25, 'trunkZ': 0.66, 'rearZ': 0.4,
                    'profile': [[XF, SOCKET_Y], [-8.75, SOCKET_Y], [-8.45, HY], [XR, HY]]},
        'contact': {'x0': CS[0], 'x1': CS[1], 'z0': CS[2], 'z1': CS[3]},
        'sections': sections,
        'mounts': mounts_dict(),
    }


if ANCHORS_ONLY:
    write_anchors(ANCHORS, anchors_dict())
    raise SystemExit(0)

# ================= malzemeler =================
# Renk düzeni (Horpol): doğal fırçalanmış alüminyum tank ve kuleler, antrasit şasi ve konsol (RAL 7016, saten), çıplak
# alüminyum yan koruma, tampon ve boru hatları, siyah çamurluk ve hortum taşıyıcılar, cilalı alüminyum jant. Tesisat
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
    'amber': material('BodyReflAmber', '#d98a0b', 0.3, 0.05),
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


def slab(parts, name, front, depth, mat, bevel=0.006):
    """Ön yüz çokgeninin ([(x, y, z)], dışbükey değil olabilir) +x yönünde `depth` kadar uzatılmış katı"""
    bm = bmesh.new()
    f = [bm.verts.new(bl(p)) for p in front]
    b = [bm.verts.new(bl((p[0] + depth, p[1], p[2]))) for p in front]
    n = len(front)
    bm.faces.new(f)
    bm.faces.new(list(reversed(b)))
    for i in range(n):
        bm.faces.new([f[i], b[i], b[(i + 1) % n], f[(i + 1) % n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj(name, bm, mat, bevel, parts)


def round_top(z, y0, y1, r, n=8):
    """Önden/arkadan görünüşte üst köşeleri yuvarlatılmış dikdörtgen [(z, y)] (alttan saat yönü tersine)"""
    pts = [(-z, y0), (z, y0)]
    for i in range(n + 1):
        t = i / n * math.pi / 2
        pts.append((z - r + r * math.cos(t), y1 - r + r * math.sin(t)))
    for i in range(n + 1):
        t = math.pi / 2 + i / n * math.pi / 2
        pts.append((-z + r + r * math.cos(t), y1 - r + r * math.sin(t)))
    return pts


# =====================================================================
# ŞASİ (tesisat görünümünde görünür)
# =====================================================================
C = Parts()

# --- king pin konsolu: kavrama plakası, kutu konsol (burun kulesinin altında), soket levhası ---
CON_X1 = -8.35
box2(C, 'king_plate', XF + 0.02, CON_X1, H5, H5 + 0.02, -0.56, 0.56, M['dark'], 0.003)
cylinder(C, 'king_pin', 0.0254, (KING_X, H5, 0), (KING_X, H5 - 0.062, 0), M['chrome'], 24, 0.002)
cylinder(C, 'king_head', 0.0365, (KING_X, H5 - 0.062, 0), (KING_X, H5 - 0.084, 0), M['chrome'], 24, 0.004)
cylinder(C, 'king_ring', 0.11, (KING_X, H5, 0), (KING_X, H5 - 0.003, 0), M['dark'], 32, 0.001)
con = [(XF, H5 + 0.02), (CON_X1, H5 + 0.02), (CON_X1 + 0.35, BOT), (NOSE_BACK, BOT), (NOSE_BACK, BTOP + 0.04), (XF, 1.47)]
for s in (-1, 1):
    prism_xy(C, 'con_side', con, s * (BZ - 0.006), s * (BZ + 0.006), P, 0.0)
    for x in (-9.05, -8.7, -8.35, -7.9):
        box2(C, 'con_rib', x - 0.005, x + 0.005, H5 + 0.03, 1.44, s * (BZ + 0.006), s * (BZ + 0.05), P, 0.0)
    beam(C, 'con_flange', (CON_X1, H5 + 0.026, s * BZ), (CON_X1 + 0.35, BOT + 0.006, s * BZ), 0.012, 0.12, P, 0.002)
box2(C, 'con_front', XF, XF + 0.012, H5 + 0.02, 1.47, -BZ - 0.006, BZ + 0.006, P, 0.002)
box2(C, 'con_cover', XF, NOSE_BACK, 1.455, 1.47, -BZ, BZ, P, 0.002)
box2(C, 'con_cross', -8.42, -8.36, H5 + 0.02, 1.455, -BZ, BZ, P, 0.002)
# soket levhası ve palm kavramalar (konsolun ön yüzünde)
box2(C, 'socket_plate', XF - 0.012, XF, 1.27, 1.45, -0.42, 0.42, M['alu'], 0.003)
for z, col in ((-0.3, M['red']), (0.3, M['dark'])):
    box2(C, 'palm', XF - 0.09, XF - 0.012, 1.30, 1.40, z - 0.06, z + 0.06, col, 0.012)

# --- ana kirişler (alüminyum kutu profil, antrasit boyalı) ve traversler ---
for s in (-1, 1):
    box2(C, 'beam', NOSE_BACK - 0.3, -0.30, BOT, BTOP, s * (BZ - 0.05), s * (BZ + 0.05), P, 0.006)
    box2(C, 'beam_groove', NOSE_BACK, -0.35, BOT + 0.065, BOT + 0.075, s * (BZ + 0.049), s * (BZ + 0.052), M['dark'], 0.0)
for x in (-7.0, -6.25, -5.45, -4.55, -3.55, AXLES[0] + 0.62, AXLES[1] + 0.62, -0.62):
    if abs(x - OUT[0]) < 0.2 or abs(x - OUT[1]) < 0.2:
        continue
    box2(C, 'cross', x - 0.04, x + 0.04, BOT + 0.02, BTOP - 0.02, -(BZ - 0.05), BZ - 0.05, P, 0.004)
box2(C, 'rear_cross', -0.42, -0.30, 1.14, BTOP, -1.05, 1.05, P, 0.006)
# aks bölgesi alt çerçevesi (askı braketleri ve körükler buna bağlanır)
for s in (-1, 1):
    box2(C, 'sub_beam', SUB_X0, SUB_X1, SUB_BOT, BOT, s * (BZ - 0.05), s * (BZ + 0.05), P, 0.006)
    for x in (SUB_X0 + 0.04, SUB_X1 - 0.04):
        prism_xy(C, 'sub_end', [(x - 0.18 if x < -2 else x - 0.04, BOT), (x + 0.04 if x < -2 else x + 0.18, BOT), (x + 0.04, SUB_BOT), (x - 0.04, SUB_BOT)],
                 s * (BZ - 0.05), s * (BZ + 0.05), P, 0.004)
for x in (AXLES[0] - 0.55, AXLES[1] - 0.55, AXLES[2] - 0.55):
    box2(C, 'sub_cross', x - 0.035, x + 0.035, SUB_BOT + 0.03, BOT, -(BZ - 0.05), BZ - 0.05, P, 0.004)
# tank yatakları: kirişin üstünde tankın altına oturan kısa takozlar (tank konsolun içine kaynaklı; yalnız ortada)
for x in (XM0 + 0.25, -4.45, XM1 - 0.25):
    for s in (-1, 1):
        y1 = under(x, BZ)
        box2(C, 'saddle', x - 0.08, x + 0.08, BTOP, max(BTOP + 0.01, y1 + 0.02), s * (BZ - 0.06), s * (BZ + 0.06), P, 0.003)

# --- yan koruma + hortum taşıyıcı (iniş ayağı ile ön aks arası): alüminyum üst/alt ray, dikmeler, kirişe kollar ---
for s in (-1, 1):
    zi, zo = s * 1.222, s * 1.27
    box2(C, 'side_top', SX0, SX1, 0.99, 1.06, zi, zo, M['alu'], 0.006)
    box2(C, 'side_bot', SX0, SX1, 0.50, 0.60, zi, zo, M['alu'], 0.006)
    for x in (SX0 + 0.03, (SX0 + SX1) / 2, SX1 - 0.03):
        box2(C, 'side_post', x - 0.03, x + 0.03, 0.60, 0.99, s * 1.226, s * 1.262, M['alu'], 0.004)
    for x in (SX0 + 0.2, SX1 - 0.2):
        box2(C, 'side_arm', x - 0.03, x + 0.03, 1.0, 1.05, s * (BZ + 0.05), zi, M['alu'], 0.004)
        prism_zy(C, 'side_hanger', [(s * (BZ + 0.05), BOT), (s * (BZ + 0.05), 0.98), (s * (BZ + 0.2), 0.98)], x - 0.006, x + 0.006, M['alu'], 0.0)

# --- iniş ayakları (konsolun arkasında; JOST, 2 × 12 t) ---
landing_gear(C, LEG_X, 0.64, BZ, BOT, M, mount_y0=0.9)

# --- aks grubu: BPW havalı süspansiyon, aks, 22,5" disk fren ---
CHAMBERS = running_gear(C, AXLES, R, BZ, SUB_BOT, M, brake='disc')

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

# --- hava tankları (iniş ayağının arkasında, kirişlerin arasında), EBS, hava hatları ---
for z in (-0.25, 0.25):
    cylinder(C, 'air_tank', 0.12, (-5.75, 1.10, z), (-5.0, 1.10, z), P, 32, 0.025)
    for x in (-5.6, -5.15):
        cylinder(C, 'tank_strap', 0.124, (x - 0.012, 1.10, z), (x + 0.012, 1.10, z), M['galv'], 32, 0.0)
for x in (-5.6, -5.15):
    box2(C, 'tank_bar', x - 0.025, x + 0.025, 1.22, BOT, -(BZ + 0.04), BZ + 0.04, P, 0.003)
    for z in (-0.25, 0.25):
        box2(C, 'tank_hanger', x - 0.02, x + 0.02, 1.10, 1.22, z - 0.02, z + 0.02, M['galv'], 0.002)
EBS = (-4.35, 1.12, -0.24)
box(C, 'ebs', (0.28, 0.18, 0.26), EBS, M['dark'], 0.015)
box2(C, 'ebs_bracket', EBS[0] - 0.15, EBS[0] + 0.15, 1.21, BOT, -0.47, -0.1, P, 0.002)
for col, dz in ((M['airRed'], 0.0), (M['airYellow'], 0.022)):
    poly_tube(C, 'air_line', [(XF + 0.05, 1.40, -0.30 - dz), (XF + 0.3, 1.40, -0.40 - dz), (-8.75, 1.40, -0.42 - dz), (-8.45, 1.20, -0.42 - dz),
                             (EBS[0] - 0.4, 1.20, -0.42 - dz), (EBS[0] - 0.16, 1.14, -0.30 - dz)], 0.007, col, 2)
poly_tube(C, 'air_tank_line', [(-5.0, 1.10, -0.25), (-4.8, 1.17, -0.33), (EBS[0] - 0.3, 1.17, -0.33), (EBS[0] - 0.15, 1.12, -0.26)], 0.008, M['air'], 2)
for cx, cy, cz in CHAMBERS:
    s = 1 if cz > 0 else -1
    hose(C, 'brake_hose', [(EBS[0] + 0.15, 1.10, EBS[2] + s * 0.08), ((EBS[0] + cx) / 2, 1.0, s * 0.3), (cx, cy + 0.06, s * 0.47), (cx, cy + 0.01, s * 0.52)], 0.008, M['air'], 2)

# --- boşaltma: huni ağızları (havalandırma konisi, kelebek vana, pnömatik tahrik), alt boşaltma borusu, arkada rakor ---
DL_Y = 0.80
for xo in OUT:
    yk = f_keel(xo)
    cylinder(C, 'outlet_flange', 0.17, (xo, yk + 0.01, 0), (xo, yk - 0.02, 0), M['pipe'], 32, 0.004)
    cylinder(C, 'aeration_cone', 0.15, (xo, yk - 0.02, 0), (xo, yk - 0.09, 0), M['pipe'], 32, 0.006, r2=0.07)
    cylinder(C, 'valve_body', 0.075, (xo, yk - 0.09, 0), (xo, DL_Y + 0.05, 0), M['pipe'], 24, 0.004)
    ym = (yk - 0.09 + DL_Y + 0.05) / 2
    box(C, 'valve_actuator', (0.14, 0.09, 0.1), (xo, ym, 0.14), M['dark'], 0.01)
    cylinder(C, 'actuator_rod', 0.012, (xo, ym, 0.075), (xo, ym, 0.09), M['chrome'], 10, 0.0)
    cylinder(C, 'tee', 0.065, (xo - 0.12, DL_Y, 0), (xo + 0.12, DL_Y, 0), M['pipe'], 24, 0.004)
dl = [(OUT[0] - 0.3, DL_Y, 0.0), (-0.75, DL_Y, 0.0), (-0.45, 0.42, 0.0), (-0.2, 0.40, -0.22), (0.02, 0.40, -0.22)]
poly_tube(C, 'discharge_line', dl, 0.057, M['pipe'], 3)
cylinder(C, 'discharge_cap', 0.07, (OUT[0] - 0.28, DL_Y, 0), (OUT[0] - 0.35, DL_Y, 0), M['pipe'], 24, 0.006)
for x in (-5.6, -4.45, -3.3, -1.8):
    box2(C, 'pipe_hanger', x - 0.02, x + 0.02, DL_Y + 0.05, (SUB_BOT if SUB_X0 < x < SUB_X1 else BOT) + 0.02, -0.035, 0.035, M['dark'], 0.002)
cylinder(C, 'rear_coupling', 0.075, (-0.03, 0.40, -0.22), (0.035, 0.40, -0.22), M['pipe'], 28, 0.006)
cylinder(C, 'rear_cap', 0.08, (0.035, 0.40, -0.22), (0.05, 0.40, -0.22), M['dark'], 28, 0.004)

# --- arka: lamba barı (alüminyum), alt koruma tamponu, paçalı levha, askılar ---
for s in (-1, 1):
    box2(C, 'bar_post', -0.36, -0.30, 0.28, SUB_BOT + 0.02, s * 0.70, s * 0.76, M['alu'], 0.004)
    box2(C, 'bar_arm', -0.30, -0.14, 0.58, 0.66, s * 0.70, s * 0.76, M['alu'], 0.004)
    box2(C, 'bar_arm_low', -0.30, -0.13, 0.32, 0.38, s * 0.70, s * 0.76, M['alu'], 0.004)
box2(C, 'lamp_bar', -0.14, XR, 0.50, 0.74, -1.24, 1.24, M['alu'], 0.01)
box2(C, 'lamp_bar_lip', -0.14, XR - 0.005, 0.49, 0.505, -1.22, 1.22, M['alu'], 0.003)
box2(C, 'underrun', -0.13, -0.01, 0.30, 0.42, -1.18, 1.18, M['alu'], 0.012)
for s in (-1, 1):
    box2(C, 'underrun_cap', -0.135, -0.005, 0.295, 0.425, s * 1.18, s * 1.2, M['rubber'], 0.005)
box2(C, 'rear_flap', -0.07, -0.06, 0.12, 0.50, -1.2, 1.2, M['rubber'], 0.003)
for s in (-1, 1):
    box2(C, 'refl', -0.06, -0.057, 0.20, 0.27, s * 0.86, s * 1.12, M['red'], 0.0)

chassis_logos = decal_mesh('ChassisLogos', [rear_quad(-0.0565, 0.20, 0.35, 0.10 * 720 / 528, 0.10)], LOGO_W)
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
# TANK KABUĞU + KULELER (tekrarlanan fırçalanmış alüminyum, AO ikinci UV'de)
# =====================================================================
TK = Parts()
rings, fcap, rcap = tank_rings(0.07 if FAST else 0.05, 10 if FAST else 14)
shell = loft(TK, 'tank_shell', rings, MT['tank'], (TT, TT), (fcap, rcap))
# huni kırılma çizgisi (silindir yayı ile huni yanının birleştiği kenar) keskin: uçlarda belirgin, ortada söner
nr = len(rings[0])
want = set()
for r in range(len(rings) - 1):
    xr = rings[r][0][0]
    if hopper_t(xr) > 0.08:
        for i in (NL, NL + NU):
            want.add(frozenset((r * nr + i, (r + 1) * nr + i)))
sharp_attr = shell.data.attributes.get('sharp_edge') or shell.data.attributes.new('sharp_edge', 'BOOLEAN', 'EDGE')
for e in shell.data.edges:
    if frozenset(e.vertices) in want:
        sharp_attr.data[e.index].value = True


def seam(x, mat):
    cu = bpy.data.curves.new('seam', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.0045
    cu.bevel_resolution = 1
    sp = cu.splines.new('POLY')
    pts = ring2d(x, 64, 16)
    sp.points.add(len(pts) - 1)
    for p, (z, y) in zip(sp.points, pts):
        v = bl((x, y, z))
        p.co = (v.x, v.y, v.z, 1.0)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new('seam', cu)
    scene.collection.objects.link(ob)
    cu.materials.append(mat)
    TK.objs.append(ob)


for x in (XHF, -5.45, -3.45, XHR):
    seam(x, MT['weld'])


def tank_part(ob):
    planar_uv(ob, {'TankAlu': (TT, TT)})
    return ob


# kapak boyunları (DN450)
for xd in DOMES:
    tank_part(cylinder(TK, 'dome_neck', 0.29, (xd, TOP - 0.06, 0), (xd, TOP + 0.015, 0), MT['tank'], 48, 0.006))
# burun kulesi: king pin konsolundan ön bombeye çıkan eğik ön yüz, önden görünüşte üstü yuvarlak, arkası tankın içinde
(xa, ya), (xb, yb) = NOSE_A, NOSE_B
nose_face = []
for z, y in round_top(NOSE_Z, ya, yb, NOSE_Z * 0.95, 10):
    nose_face.append((nose_point(y), y, z))
tank_part(slab(TK, 'nose_tower', nose_face, NOSE_BACK - xa, MT['tank'], 0.012))
# arka kule (boşaltma dolabı): dikey, üst köşeleri yuvarlak, önü tankın içinde
tank_part(prism_zy(TK, 'rear_tower', round_top(RTW[4], RTW[2], RTW[3], RTW[5], 9), RTW[0], RTW[1], MT['tank'], 0.012))
tank = join(TK, 'SiloTank')
print('TANK uv layers', [u.name for u in tank.data.uv_layers])

# hacim (yalnız kontrol): tank halkalarının kesit alanı integrali
def area(pts):
    return abs(sum(z1 * y2 - z2 * y1 for (z1, y1), (z2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


vol = 0.0
for ra, rb in zip(rings, rings[1:]):
    vol += (area([(p[2], p[1]) for p in ra]) + area([(p[2], p[1]) for p in rb])) / 2 * abs(rb[0][0] - ra[0][0])
print(f'VOLUME tank ≈ {vol:.1f} m3 (tablo 33,0)')

# =====================================================================
# ÜST YAPI (tesisat görünümünde gizlenir)
# =====================================================================
B = Parts()
# kapaklar: kapak, kenet civataları, menteşe
LID_Y = TOP + 0.015
for xd in DOMES:
    cylinder(B, 'lid', 0.305, (xd, LID_Y, 0), (xd, LID_Y + 0.04, 0), MB['lid'], 48, 0.008)
    cylinder(B, 'lid_cap', 0.24, (xd, LID_Y + 0.04, 0), (xd, DOME_TOP - 0.004, 0), MB['lid'], 40, 0.012, r2=0.17)
    cylinder(B, 'lid_gasket', 0.31, (xd, LID_Y - 0.005, 0), (xd, LID_Y + 0.002, 0), MB['rubber'], 48, 0.0)
    for i in range(6):
        t = (i + 0.5) * math.pi / 3
        cx_, cz_ = xd + 0.33 * math.cos(t), 0.33 * math.sin(t)
        box(B, 'clamp', (0.05, 0.07, 0.05), (cx_, LID_Y + 0.015, cz_), MB['galv'], 0.006)
        cylinder(B, 'clamp_wing', 0.012, (cx_, LID_Y + 0.05, cz_), (cx_, LID_Y + 0.07, cz_), MB['galv'], 8, 0.0)
    box2(B, 'lid_hinge', xd - 0.04, xd + 0.04, LID_Y - 0.02, LID_Y + 0.04, -0.37, -0.3, MB['galv'], 0.006)
# yürüme yolu taşıyıcıları
WALK = []
x0 = -7.45
for xd in DOMES + [-1.70]:
    x1 = xd - 0.36 if xd != -1.70 else xd
    if x1 - x0 > 0.2:
        WALK.append((x0, x1))
    x0 = xd + 0.36
WALK_Y = TOP + 0.02
for a, b in WALK:
    x = a + 0.1
    while x < b:
        for s in (-1, 1):
            box2(B, 'walk_stand', x - 0.015, x + 0.015, TOP - 0.03, WALK_Y, s * 0.18, s * 0.21, MB['alu'], 0.002)
        x += 0.6
# katlanmış korkuluk (+z): menteşe braketleri tankın üst yanında, dikmeler yatık, üst ve diz rayı
POSTS = [-7.27, -5.45, -3.56, -1.79]
hz, hy_ = 1.03, YC + math.sqrt(RT ** 2 - 1.0 ** 2) + 0.03
rz, ry = 0.42, TOP + 0.055
for x in POSTS:
    box(B, 'rail_hinge', (0.08, 0.06, 0.05), (x, hy_ - 0.02, hz - 0.02), MB['alu'], 0.006)
    cylinder(B, 'rail_post', 0.02, (x, hy_ + 0.02, hz), (x, ry, rz), MB['alu'], 12, 0.0)
cylinder(B, 'rail_top', 0.021, (POSTS[0] - 0.15, ry, rz), (POSTS[-1] + 0.12, ry, rz), MB['alu'], 12, 0.0)
mz, my = (hz + rz) / 2, (hy_ + 0.02 + ry) / 2
cylinder(B, 'rail_knee', 0.017, (POSTS[0] - 0.1, my, mz), (POSTS[-1] + 0.1, my, mz), MB['alu'], 12, 0.0)
cylinder(B, 'rail_cyl', 0.025, (POSTS[1] + 0.4, hy_ + 0.05, hz - 0.08), (POSTS[1] + 0.4, ry - 0.04, rz + 0.08), MB['dark'], 14, 0.004)
# merdiven (sol arka, +z): arka kulenin yanında, lamba barının üstünden tepeye; iki ray, basamaklar, üstte tutamak.
# Alt uç barın üst yüzünde biter (0,76): stop lambası ve plaka yüzüne inmez.
LAD = [(-0.02, 0.76), (-0.22, 1.30), (-0.52, 2.25), (-0.80, 3.05), (-1.12, 3.65), (-1.45, TOP + 0.06)]
for z in (0.82, 1.20):
    poly_tube(B, 'ladder_rail', [(x, y, z) for x, y in LAD], 0.02, MB['alu'], 2)
for i in range(len(LAD) - 1):
    (xa_, ya_), (xb_, yb_) = LAD[i], LAD[i + 1]
    n = max(1, int(math.hypot(xb_ - xa_, yb_ - ya_) / 0.28))
    for j in range(n):
        t = (j + 0.5) / n
        x, y = xa_ + (xb_ - xa_) * t, ya_ + (yb_ - ya_) * t
        cylinder(B, 'rung', 0.016, (x, y, 0.82), (x, y, 1.20), MB['alu'], 10, 0.0)
for (x, y) in ((-0.22, 1.30), (-0.80, 3.05)):
    beam(B, 'ladder_stay', (x - 0.02, y, 0.84), (RTW[1] - 0.02 if y < RTW[3] else dome_x(y, 0.9, False) - 0.05, y, 0.70), 0.03, 0.03, MB['alu'], 0.003)
hose(B, 'ladder_grab', [(-1.45, TOP + 0.06, 0.82), (-1.62, TOP + 0.42, 0.82), (-1.95, TOP + 0.45, 0.82)], 0.017, MB['alu'], 2)
hose(B, 'ladder_grab', [(-1.45, TOP + 0.06, 1.20), (-1.62, TOP + 0.42, 1.20), (-1.95, TOP + 0.45, 1.20)], 0.017, MB['alu'], 2)
# hortum taşıyıcılar (her yanda bir NW100 boru, yan korumanın içinde; arkada kapaklı)
HT0, HT1 = SX0 + 0.06, SX1 - 0.06
for s in (-1, 1):
    zt = s * 1.08
    cylinder(B, 'hose_tube', 0.115, (HT0, 0.80, zt), (HT1, 0.80, zt), MB['black'], 32, 0.004)
    cylinder(B, 'hose_tube_end', 0.115, (HT0 - 0.04, 0.80, zt), (HT0, 0.80, zt), MB['black'], 32, 0.03, r2=0.095)
    cylinder(B, 'hose_cover', 0.125, (HT1, 0.80, zt), (HT1 + 0.06, 0.80, zt), MB['black'], 32, 0.012)
    box2(B, 'hose_lock', HT1 + 0.06, HT1 + 0.075, 0.76, 0.84, s * 1.06, s * 1.10, MB['galv'], 0.004)
    for x in (HT0 + 0.3, HT1 - 0.3):
        box2(B, 'hose_strap', x - 0.03, x + 0.03, 0.66, 0.99, s * 1.0, s * 1.03, MB['dark'], 0.003)
# havalandırma borusu (sağ, -z: hava hattı tarafı): şasiden yukarı U biçimli dönüş
UZ = -1.02
poly_tube(B, 'vent_pipe', [(-4.58, 1.42, UZ), (-4.58, 2.05, UZ), (-4.52, 2.15, UZ), (-4.40, 2.15, UZ), (-4.34, 2.05, UZ), (-4.34, 1.42, UZ)], 0.035, MB['alu'], 2)
box2(B, 'vent_bracket', -4.62, -4.30, 1.40, 1.44, UZ - 0.05, -BZ - 0.05, MB['alu'], 0.003)
# yan hava hattı (sağ, -z): konsol önünden kiriş boyunca, iki huniye vanalı inişler, manometre
AZ = -0.66
poly_tube(B, 'side_airline', [(XF + 0.2, 1.42, -0.5), (-9.0, 1.46, AZ), (-6.6, 1.46, AZ), (OUT[1] + 0.35, 1.46, AZ)], 0.035, MB['alu'], 2)
for xo in OUT:
    poly_tube(B, 'aeration_feed', [(xo + 0.4, 1.46, AZ), (xo + 0.25, f_keel(xo) + 0.25, -0.30), (xo + 0.12, f_keel(xo) + 0.08, -0.12)], 0.022, MB['alu'], 2)
    cylinder(B, 'feed_valve', 0.032, (xo + 0.4, 1.40, AZ), (xo + 0.4, 1.52, AZ), MB['brass'], 14, 0.006)
cylinder(B, 'air_inlet', 0.05, (XF + 0.2, 1.42, -0.5), (XF + 0.06, 1.42, -0.5), MB['brass'], 20, 0.008)
cylinder(B, 'check_valve', 0.055, (-8.95, 1.46, AZ), (-8.8, 1.46, AZ), MB['brass'], 20, 0.01)
cylinder(B, 'gauge', 0.06, (-8.55, 1.62, AZ - 0.02), (-8.55, 1.62, AZ - 0.06), MB['galv'], 24, 0.006)
cylinder(B, 'gauge_face', 0.05, (-8.55, 1.62, AZ - 0.061), (-8.55, 1.62, AZ - 0.064), MB['glass'], 24, 0.0)
# ön üst hava hattı: burun kulesinin yanından ön bombe boyunca tepeye (bombeden 6 cm açıkta)
zt = -0.52
top_air = [(-8.62, 1.55, zt)]
for y in (1.9, 2.3, 2.7, 3.1, 3.45):
    top_air.append((min(nose_point(y) + 0.05, dome_x(y, zt) - 0.06), y, zt))
top_air += [(dome_x(3.72, zt) - 0.05, 3.72, zt), (XHF + 0.05, TOP + 0.06, zt * 0.6), (DOMES[0] - 0.45, TOP + 0.06, -0.25)]
poly_tube(B, 'top_airline', top_air, 0.03, MB['alu'], 2)
for y in (2.1, 2.9, 3.55):
    xs_ = min(nose_point(y) + 0.05, dome_x(y, zt) - 0.06)
    box2(B, 'air_clip', xs_ - 0.02, xs_ + 0.07, y - 0.02, y + 0.02, zt - 0.025, zt + 0.025, MB['dark'], 0.003)
# ön pozisyon lambası pabuçları (burun kulesinin ön yüzünde)
for s in (-1, 1):
    fx = nose_point(FRONT_Y)
    box2(B, 'front_lamp_pad', fx - 0.03, fx + 0.06, FRONT_Y - 0.08, FRONT_Y + 0.08, s * (FRONT_Z - 0.07), s * (FRONT_Z + 0.07), MB['alu'], 0.004)
# arka kule ayrıntıları: dolap kapağı, kulplar, menteşeler, gösterge penceresi, reflektörler
DX = RTW[1]
box2(B, 'cab_door', DX, DX + 0.012, 1.24, 1.98, -0.50, 0.50, MB['alu'], 0.008)
box2(B, 'cab_seal', DX - 0.002, DX + 0.004, 1.22, 2.0, -0.52, 0.52, MB['rubber'], 0.004)
for z in (-0.30, 0.30):
    box2(B, 'cab_handle', DX + 0.012, DX + 0.03, 1.30, 1.38, z - 0.03, z + 0.03, MB['dark'], 0.004)
box2(B, 'cab_lock', DX + 0.012, DX + 0.035, 1.55, 1.70, -0.03, 0.03, MB['dark'], 0.005)
for y in (1.40, 1.85):
    box2(B, 'cab_hinge', DX, DX + 0.02, y - 0.04, y + 0.04, 0.50, 0.54, MB['galv'], 0.003)
box2(B, 'cab_window', DX, DX + 0.008, 2.30, 2.42, -0.12, 0.12, MB['glass'], 0.004)
for s in (-1, 1):
    box2(B, 'cab_refl', DX, DX + 0.004, 1.09, 1.18, s * 0.08, s * 0.66, MB['red'], 0.0)
# yan kontur bandı (ECE 104, sarı): ekvatorun hemen altında, silindir boyunca kesikli
for x in [-7.2 + 0.62 * i for i in range(10)]:
    if x + 0.42 > XHR:
        break
    for s in (-1, 1):
        y = YC - 0.16
        z = math.sqrt(RT ** 2 - (y - YC) ** 2) + 0.003
        box2(B, 'contour', x, x + 0.42, y - 0.025, y + 0.025, s * (z - 0.004), s * (z + 0.002), MB['amber'], 0.0)
body = join(B, 'SiBody')

# yürüme yolu (kaymaz sac, tekrarlanan doku)
D = Parts()
for a, b in WALK:
    box2(D, 'walkway', a, b, WALK_Y, WALK_Y + 0.022, -0.22, 0.22, MD['checker'], 0.0)
walk = join(D, 'SiWalk')
planar_uv(walk, {'WalkChecker': (0.3, 0.3)})


# logolar: tankın iki yanında silindir yüzeyine oturan ızgara, arka kulenin üstünde
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
                z = math.sqrt(max(RT * RT - (y - YC) ** 2, 0.0))
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


tank_logos = tank_decal('TankLogos', -4.45, 3.0, 0.62, LOGO)
cab_logos = decal_mesh('CabLogos', [rear_quad(DX + 0.0015, 2.18, 0.0, 0.16 * 720 / 528, 0.16)], LOGO)

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
tri = lambda ob: sum(len(p.vertices) - 2 for p in ob.data.polygons)  # noqa: E731
print(f'TRIS chassis={tri(chassis)} wheel={tri(wheel)} tank={tri(tank)} body={tri(body)} walk={tri(walk)}')

# --- zemin temas gölgesi ---
ground = ground_contact(os.path.join(OUT_DIR, 'silo-contact.webp'), CS, decals, FAST)

write_anchors(ANCHORS, anchors_dict())

# ================= önizleme render'ları (yalnızca kontrol) =================
if PREVIEW:
    ground.hide_render = True
    preview_renders(PREVIEW, [('side', (-4.7, 2.0, 13.0), (-4.7, 1.9, 0)), ('front34', (-14.0, 3.5, 7.0), (-6.0, 1.9, 0)), ('rear34', (4.0, 3.0, 7.0), (-3.0, 1.9, 0)),
                              ('front', (-17.0, 2.2, 0.0), (-4.7, 2.0, 0)), ('rear', (8.0, 2.0, 0.0), (-4.7, 1.9, 0)),
                              ('under', (-5.5, 0.35, 5.0), (-4.5, 1.1, 0))])
    # tesisat görünümündeki gibi: tank ve üst yapı gizli
    preview_renders(PREVIEW, [('chassis', (-3.0, 4.0, 7.5), (-4.7, 1.0, 0))], hide=[tank, body, walk, tank_logos, cab_logos])
