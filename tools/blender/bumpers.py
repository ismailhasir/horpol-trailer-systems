# Horpol arka tamponları: sac profil ailesi (SolidWorks çizimleri, D:\DİDEBAN OTOMOTİV\...\Tampon Çizimleri). Profil ölçüleri ve
# delikler çizimlerin PDF'indeki vektörlerden okundu (±1 mm): kesit (yükseklik, derinlik, 135° bükümler) ve açınım (büküm çizgileri,
# delikler). Dorse betikleri build_set() / build_mudflap() ile kendi şasilerine ekler; tek başına çalışınca türevleri kontrol için
# dışa aktarır.
#
# Çalıştırma (depo kökünden):
#   blender -b -P tools/blender/bumpers.py -- [--only tek32-lzd3194,hamburger-luna6] [--preview <klasör>] [--lamps]
#   --lamps: önizlemede lambalar da (tools/blender/out/lamp-*.glb) yerine konur (uyum kontrolü)
#
# Profil (kesit, arkadan bakana göre): arka yüz (dış duvarlar) → 135° ile içe çöken orta yuva (lambaların oturduğu web) → üst ve
# alt flanşlar dorseye doğru → uçta içe dönen dudaklar (şasi askılarına cıvatalanan oval delikler burada). Sac kalınlığı çizimde
# yok: 3 mm varsayıldı (doğrulanmadı). İç büküm yarıçapı = kalınlık. Uçlarda 5 mm kapak sacı (lastik kol tabanı buna oturur).
# Yerel koordinat (three.js düzeni, m): x derinlik (0 = arka dış yüz, dorseye doğru −), y yukarı (0 = web ortası), z yanal (±1,2).
import bpy
import bmesh
import math
import os
import sys

from mathutils import Matrix, Vector

if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)  # bl_common sahneyi içe aktarılırken yakalar: önce sıfırla
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bl_common import Parts, bl, box2, cylinder, join, material, prism_xy, prism_zy, select_only, smart_uv  # noqa: E402

MM = 0.001
T = 3.0  # sac kalınlığı (mm, varsayım)
LEN = 2400.0

# Ölçüler mm. h / d: kesitin dış yüksekliği / derinliği (çizim); web: orta yuvanın orta-yüzey yüksekliği; recess: yuvanın
# çökme derinliği (135° büküm: 45° eğik kenar, yatay = dikey); lip: dudak boyu. Açınım büküm çizgilerinden.
BUMPERS = {
    # Tek-240-32cm: dikdörtgen kombine stoplar (LZD 3194, LZD 2854). Açınım 570: dudak 30,3 · flanş 79,8 · duvar 40,2 ·
    # eğik 55 · web 160,2 (simetrik)
    'tek32': {'code': 'Tek-240-32cm', 'h': 323.37, 'd': 84.93, 'web': 164.0, 'recess': 38.9, 'lip': 30.0,
              'cutouts': [], 'screws': []},
    # Tek-240-30cm-Hamburger: yuvarlak stoplar (LUNA). Açınım 470: dudak 30,5 · flanş 50 · duvar 40 · eğik 29,7 · web 170.
    # Web ortasında her yanda 4 × Ø115 kesik (açınımda x 107,2 / 272,3 / 437,4 / 602,5, aynalı), her birinin çevresinde Ø130
    # çember üstünde 120° aralı 3 × Ø5 vida deliği (biri üstte)
    'hamburger': {'code': 'Tek-240-30cm-Hamburger', 'h': 296.15, 'd': 53.29, 'web': 172.0, 'recess': 21.4, 'lip': 30.0,
                  'cutouts': [(x, 115.0) for x in (107.2, 272.3, 437.4, 602.5)],
                  'screws': [(65.0, a, 5.0) for a in (90.0, 210.0, 330.0)]},
}
# dudaklardaki bağlantı ovalleri (iki tampon aynı): açınım x aralıkları, genişlik 10, dudak ucundan 13,4 mm
SLOTS = [(213.5, 468.9), (696.1, 951.5)]
SLOT_W, SLOT_FROM_TIP = 10.0, 13.4


def _fillet(pts, r, n=6):
    """Kırık çizginin iç köşelerini r yarıçaplı yayla yuvarlar (uç noktalar kalır)"""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p, a, b = Vector(pts[i]), Vector(pts[i - 1]), Vector(pts[i + 1])
        u, w = (a - p).normalized(), (b - p).normalized()
        ang = math.acos(max(-1.0, min(1.0, u.dot(w))))
        k = r / math.tan(ang / 2)
        p0, p1 = p + u * k, p + w * k
        c = p + (u + w).normalized() * (r / math.sin(ang / 2))
        a0, a1 = math.atan2(p0.y - c.y, p0.x - c.x), math.atan2(p1.y - c.y, p1.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(c.x + r * math.cos(a0 + da * j / n), c.y + r * math.sin(a0 + da * j / n)) for j in range(n + 1)]
    return out + [pts[-1]]


def _offset(pts, d):
    """Açık kırık çizginin d kadar solundaki paralel (köşelerde açıortay)"""
    out = []
    for i, p in enumerate(pts):
        p = Vector(p)
        ts = []
        if i > 0:
            ts.append((p - Vector(pts[i - 1])).normalized())
        if i < len(pts) - 1:
            ts.append((Vector(pts[i + 1]) - p).normalized())
        t = (ts[0] + ts[-1]).normalized()
        nrm = Vector((-t.y, t.x))
        cosh = max(0.3, nrm.dot(Vector((-ts[0].y, ts[0].x))))
        q = p + nrm * (d / cosh)
        out.append((q.x, q.y))
    return out


def centerline(s):
    """Kesitin orta yüzeyi (mm, yerel x/y): üst dudak ucundan alt dudak ucuna"""
    ht = (s['h'] - T) / 2  # flanş orta yüzeyinin yüksekliği
    xf = -T / 2  # dış duvar orta yüzeyi
    xl = -(s['d'] - T / 2)  # dudak orta yüzeyi
    hw, r = s['web'] / 2, s['recess']
    w = ht - hw - r  # dış duvarın düz boyu
    assert w > 5, s['code']
    pts = [(xl, ht - s['lip']), (xl, ht), (xf, ht), (xf, ht - w), (xf - r, hw), (xf - r, -hw), (xf, -(ht - w)), (xf, -ht), (xl, -ht),
           (xl, -(ht - s['lip']))]
    return _fillet(pts, 1.5 * T)


def outline(s):
    """Kesitin dış çevresi (m): orta yüzeyin iki yanı"""
    c = centerline(s)
    a, b = _offset(c, T / 2), _offset(c, -T / 2)
    return [(x * MM, y * MM) for x, y in a + list(reversed(b))]


def _stadium(z0, z1, yc, w, n=10):
    """Oval delik (z0 … z1 boyunca, y merkezi yc, genişlik w), [z, y] m"""
    r = w / 2
    pts = [(z1 - r + r * math.cos(-math.pi / 2 + math.pi * i / n), yc + r * math.sin(-math.pi / 2 + math.pi * i / n)) for i in range(n + 1)]
    pts += [(z0 + r + r * math.cos(math.pi / 2 + math.pi * i / n), yc + r * math.sin(math.pi / 2 + math.pi * i / n)) for i in range(n + 1)]
    return [(z * MM, y * MM) for z, y in pts]


def _circle(zc, yc, d, n):
    """Daire [z, y] (girdi mm, çıktı m)"""
    return [((zc + d / 2 * math.cos(2 * math.pi * i / n)) * MM, (yc + d / 2 * math.sin(2 * math.pi * i / n)) * MM) for i in range(n)]


def _mirror_x(xs):
    """Açınım x'leri (0 … 2400) → yerel z (mm), simetrik ikizleriyle"""
    return sorted({round(LEN / 2 - x, 2) for x in xs} | {round(x - LEN / 2, 2) for x in xs})


def build_bumper(kind, mat, parts=None, name=None, cutouts=None, holes=()):
    """Tampon sacını yerel koordinatta kurar (bkz. dosya başı). cutouts: kesiklerin açınım x'leri (None: çizimdeki hepsi),
    holes: web'e ek delikler ([z, y] m çokgenler; lamba saplamaları, fiş geçişleri). Döner: nesne"""
    s = BUMPERS[kind]
    half = LEN / 2 * MM
    ob = prism_xy(None, name or f'bumper_{kind}', outline(s), -half, half, mat, 0.0)
    ob.data.set_sharp_from_angle(angle=math.radians(30))
    cut = Parts()
    ht = (s['h'] - T) / 2
    xl = -(s['d'] - T / 2)
    # dudaklardaki bağlantı ovalleri (üst ve alt dudak)
    ys = ht - s['lip'] + SLOT_FROM_TIP
    for za, zb in [(LEN / 2 - b, LEN / 2 - a) for a, b in SLOTS] + [(a - LEN / 2, b - LEN / 2) for a, b in SLOTS]:
        for sy in (1, -1):
            prism_zy(cut, 'slot', _stadium(za, zb, sy * ys, SLOT_W), (xl - 4 * T) * MM, (xl + 4 * T) * MM, mat, 0.0)
    # web kesikleri ve vida delikleri (web orta yüzeyi x = −T/2 − recess)
    xw = -T / 2 - s['recess']
    cx = [x for x, _ in s['cutouts']] if cutouts is None else cutouts
    for zc in _mirror_x(cx):
        dia = s['cutouts'][0][1]
        prism_zy(cut, 'cutout', _circle(zc, 0.0, dia, 64), (xw - 3 * T) * MM, (xw + 3 * T) * MM, mat, 0.0)
        for rr, ang, dd in s['screws']:
            a = math.radians(ang)
            prism_zy(cut, 'screw', _circle(zc + rr * math.cos(a), rr * math.sin(a), dd, 16), (xw - 3 * T) * MM, (xw + 3 * T) * MM, mat, 0.0)
    for poly in holes:
        prism_zy(cut, 'hole', poly, (xw - 3 * T) * MM, (xw + 3 * T) * MM, mat, 0.0)
    if cut.objs:
        cutter = join(cut, 'cutter')
        md = ob.modifiers.new('holes', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = cutter
        md.solver = 'EXACT'
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
        # boolean yeni kenarları düz gölgeler: delik duvarı ile web arası keskin, yoksa web boyunca yumuşak gölge izleri kalır
        ob.data.set_sharp_from_angle(angle=math.radians(30))
    if parts is not None:
        parts.objs.append(ob)
    return ob


def web_x(kind):
    """Lambaların oturduğu web dış yüzünün yerel x'i (m)"""
    return -BUMPERS[kind]['recess'] * MM


def web_height(kind):
    """Webin düz (lamba oturabilen) yüksekliği (m): eğik kenarların iç bükümleri arası"""
    s = BUMPERS[kind]
    return (s['web'] - 2 * 2 * T) * MM


def depth(kind):
    return BUMPERS[kind]['d'] * MM


def arm_x(kind):
    """Lastik kol taban plakasının merkezi (yerel x, m): uç sacın kol yüksekliğindeki DOLU kısmının ortası. Uç sac kesiti birebir
    kapatır; ortada lambaların oturduğu girinti (web) olduğu için dolu kısım ön dudaklarla web arası (kullanıcı 2026-10-23: toplam
    derinliğin ortası plakayı girintinin üstüne, arkaya taşırıyordu)"""
    s = BUMPERS[kind]
    return -(s['recess'] + s['d']) / 2 * MM


# ---------------- tampon türevleri (lambaya göre delinmiş) ----------------
# Gerçek tampon takılan lambaya göre delinir: her türev kendi lambalarının saplama ve fiş delikleri, pul / somun / rakorlarıyla
# ayrı GLB'dir (site seçime göre birini yükler). Lambalar dıştan içe; LUNA 6'lı sette her yanda 3 kesik (boş kesik kalmaz).
VARIANTS = {
    'tek32': ('tek32', [], None),  # stop yok ya da modeli olmayan stop (CUBE): yalnız sac ve bağlantılar
    'tek32-lzd3194': ('tek32', ['lzd3194'], None),
    'tek32-lzd2854': ('tek32', ['lzd2854'], None),
    'tek32-lzd2820': ('tek32', ['lzd2820'], None),
    'tek32-lzd3223': ('tek32', ['lzd3223'], None),
    # CUBE seti (kullanıcı 2026-10-23, LUNA gibi 6 ya da 8): her yanda dıştan 2–3 × LZD 2875 (föy: yalnız üçlü set onaylı) + içte
    # LZD 2876
    'tek32-cube6': ('tek32', ['lzd2875', 'lzd2875', 'lzd2876'], None),
    'tek32-cube8': ('tek32', ['lzd2875', 'lzd2875', 'lzd2875', 'lzd2876'], None),
    'hamburger-luna6': ('hamburger', ['lzd2448', 'lzd2448', 'lzd2452'], 3),
    'hamburger-luna8': ('hamburger', ['lzd2448', 'lzd2448', 'lzd2448', 'lzd2452'], 4),
}
CAP_T = 5.0  # uç sacı (lastik kol tabanı buna cıvatalanır), mm
ARM_HOLE_Y = 0.039  # lastik kol taban plakasının M5 deliklerinin yarı aralığı (m; plaka merkezinden)
REAR_GAP = 0.025  # yan yana dikdörtgen lambalar arası (site equipment.ts ile aynı)
# türeve özel aralık: CUBE üçlüsü çizimde (HOR-164AY-3-razem) 110–116 mm adımla, çerçeveler neredeyse bitişik
GAPS = {'tek32-cube6': 0.004, 'tek32-cube8': 0.004}
RAW = os.path.abspath('tools/blender/out')
_widths = {}


def _scene():
    return bpy.context.scene


def place_lamp(pid, loc, mirror=False):
    """Lamba GLB'sini (lens yerel +Z) arkaya bakacak biçimde yerleştirir (sitedeki stop yerleşimi: y ekseninde +90°, sağ lamba
    x aynası). Döner: [nesneler] (kök boş nesne dahil)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(RAW, f'lamp-{pid}.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(f'lamp_{pid}', None)
    _scene().collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.rotation_euler = (0, 0, math.pi / 2)  # three +90° (y) = Blender z ekseni
    if mirror:
        root.scale = (-1, 1, 1)
    root.location = bl(loc)
    bpy.context.view_layer.update()
    return new + [root]


def _under_bracket(o):
    while o is not None:
        if o.name.startswith('BRACKET'):
            return True
        o = o.parent
    return False


def _remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def lamp_width(pid):
    """Lambanın genişliği (yerel X; montaj plakası BRACKET hariç): sitedeki lampWidth ile aynı kural"""
    if pid not in _widths:
        objs = place_lamp(pid, (0.0, 0.0, 0.0))
        ys = [(o.matrix_world @ v.co).y for o in objs if o.type == 'MESH' and not _under_bracket(o) for v in o.data.vertices]
        _widths[pid] = max(max(ys) - min(ys), 0.05)  # yerel X → three −z → Blender y
        _remove(objs)
    return _widths[pid]


def variant_slots(variant):
    """Türevin lamba merkezleri |z| (m, dıştan içe): kesikli tipte kesiklere, düz tipte uca dayalı genişliğe göre"""
    kind, lamps, ncut = VARIANTS[variant]
    if not lamps:
        return []
    if ncut:
        return [round((LEN / 2 - x) * MM, 4) for x, _ in BUMPERS[kind]['cutouts'][:ncut]]
    out, edge = [], LEN / 2 * MM
    for pid in lamps:
        w = lamp_width(pid)
        out.append(round(edge - w / 2, 4))
        edge -= w + GAPS.get(variant, REAR_GAP)
    return out


def _section_boxes(objs, plane_x):
    """Lamba parçalarının web orta düzlemindeki (three x = plane_x) kesitleri: [(zc, yc, dz, dy)] (three, m). Örtüşen kesitler
    (diş, rakor halkaları) tek kutuda birleşir."""
    boxes = []
    for o in objs:
        if o.type != 'MESH':
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(plane_x, 0, 0), plane_no=(1, 0, 0))
        adj = {}
        for e in res['geom_cut']:
            if isinstance(e, bmesh.types.BMEdge):
                a, b = e.verts
                adj.setdefault(a, []).append(b)
                adj.setdefault(b, []).append(a)
        seen = set()
        for v in adj:
            if v in seen:
                continue
            comp, st = [], [v]
            seen.add(v)
            while st:
                u = st.pop()
                comp.append(u.co.copy())
                for w in adj[u]:
                    if w not in seen:
                        seen.add(w)
                        st.append(w)
            zs, ys = [-c.y for c in comp], [c.z for c in comp]  # three z = −Blender y, three y = Blender z
            boxes.append([min(zs), max(zs), min(ys), max(ys)])
        bm.free()
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] <= b[1] + 0.001 and b[0] <= a[1] + 0.001 and a[2] <= b[3] + 0.001 and b[2] <= a[3] + 0.001:
                    boxes[i] = [min(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3])]
                    boxes.pop(j)
                    merged = True
                    break
            if merged:
                break
    return [((a + b) / 2, (c + d) / 2, b - a, d - c) for a, b, c, d in boxes if max(b - a, d - c) > 0.002]


def _rrect(zc, yc, w, h, r, n=4):
    """Köşeleri yuvarlatılmış dikdörtgen [z, y] (m)"""
    pts = []
    for cz, cy, a0 in ((zc + w / 2 - r, yc + h / 2 - r, 0), (zc - w / 2 + r, yc + h / 2 - r, 90), (zc - w / 2 + r, yc - h / 2 + r, 180),
                       (zc + w / 2 - r, yc - h / 2 + r, 270)):
        pts += [(cz + r * math.cos(math.radians(a0 + 90 * i / n)), cy + r * math.sin(math.radians(a0 + 90 * i / n))) for i in range(n + 1)]
    return pts


def _nut(parts, x0, yc, zc, d, mat, axis='x', sign=-1):
    """Pul + altıgen somun (anma çapı d, m): x0'dan (sac yüzü; axis z ise zc'den) sign yönünde"""
    def p(t):
        return (x0 + sign * t, yc, zc) if axis == 'x' else (x0, yc, zc + sign * t)
    cylinder(parts, 'washer', 1.05 * d, p(0.0), p(0.2 * d), mat, 20, 0.0)
    cylinder(parts, 'nut', 1.625 * d / 2 / math.cos(math.pi / 6), p(0.2 * d), p(1.0 * d), mat, 6, 0.0004)


def build_set(variant, mats, parts):
    """Tampon türevi: sac (lamba delikleriyle), iki uç sacı (içte lastik kol için kaynaklı somunlar), lamba saplamalarına pul ve
    somun, fiş geçişlerine lastik rakor; LUNA'da kesik çevresindeki 3 vidaya somun. Yerel koordinat; mats: sheet, zinc, rubber.
    Döner: {'slots': lamba merkezleri |z| (dıştan içe)}"""
    kind, lamps, ncut = VARIANTS[variant]
    s = BUMPERS[kind]
    half = LEN / 2 * MM
    face = web_x(kind)
    back = face - T * MM  # web iç (dorse tarafı) yüzü
    slots = variant_slots(variant)
    placed = []
    for sz in (1, -1):
        for pid, z in zip(lamps, slots):
            placed += place_lamp(pid, (face, 0.0, sz * z), mirror=sz < 0)
    cut_r = s['cutouts'][0][1] / 2 * MM if s['cutouts'] else 0.0
    holes, hw = [], []
    for zc, yc, dz, dy in _section_boxes(placed, face - T / 2 * MM):
        if cut_r and any(math.hypot(abs(zc) - zk, yc) + max(dz, dy) / 2 < cut_r for zk in slots):
            continue  # kesiğin içinden geçiyor
        m, n = max(dz, dy), min(dz, dy)
        if m < 0.016:  # saplama / cıvata: Ø + 1 mm delik, arkada pul + somun
            holes.append(_circle(zc / MM, yc / MM, (m + 0.001) / MM, 20))
            hw.append(('stud', zc, yc, m))
        elif m < 0.032 and m / max(n, 1e-6) < 1.35:  # yuvarlak fiş / rakor (Ø < 32 mm): + 3 mm delik, arkada lastik rakor
            # (büyük kareye yakın kesitler soket bloğudur, ör. LZD 3194'ün 46 × 40 Superseal plakası: dar dikdörtgen kesik; önceden
            # en/boy oranına bakıldığı için Ø49 daire deliniyordu, kullanıcı 2026-10-23)
            holes.append(_circle(zc / MM, yc / MM, (m + 0.003) / MM, 40))
            hw.append(('grommet', zc, yc, m + 0.003))
        else:
            holes.append(_rrect(zc, yc, dz + 0.004, dy + 0.004, min(0.006, n / 2)))
    # kesikler: kesikli tipte yalnız lambası olanlar (6'lı LUNA'da her yanda 3)
    cutx = [x for x, _ in s['cutouts'][:ncut]] if ncut else []
    build_bumper(kind, mats['sheet'], parts, name=f'bumper_{variant}', cutouts=cutx, holes=holes)
    # uç sacları: kesitin dış çevresiyle kapalı levha (dudaklar arası açıklık da kapanır); lastik kol tabanı dış yüzüne cıvatalı,
    # içte iki kaynaklı somun
    cap = [(x * MM, y * MM) for x, y in _offset(centerline(s), T / 2)]
    for sz in (1, -1):
        z0, z1 = sorted((sz * (half + 0.0005), sz * (half - CAP_T * MM)))  # sacın ucunu 0,5 mm örter (aynı düzlemde titreme olmasın)
        prism_xy(parts, 'end_cap', cap, z0, z1, mats['sheet'], 0.0)
        # lastik kol (LDCC 2698 ve LD 2994 aynı taban: plaka 35 × 105, M5 delikler ±39 mm; kolların CAD'inden ölçüldü
        # 2026-10-23) uç sacın ortasına: iki M5 cıvatanın ucu ve içteki somunları
        xc = arm_x(kind)
        # LZD 3194'te kol lambanın ucundaki adaptöre takılır (MOUNT_arm): uç saçta kol bağlantısı yok
        for yy in (() if 'lzd3194' in lamps else (-ARM_HOLE_Y, ARM_HOLE_Y)):
            cylinder(parts, 'arm_bolt', 0.0024, (xc, yy, sz * (half + 0.0005)), (xc, yy, sz * (half - CAP_T * MM - 0.009)), mats['zinc'], 12, 0.0)
            _nut(parts, xc, yy, sz * (half - CAP_T * MM), 0.005, mats['zinc'], axis='z', sign=-sz)
    # lamba bağlantıları (sacın dorse tarafında)
    for k, zc, yc, d in hw:
        if k == 'stud':
            _nut(parts, back, yc, zc, max(d, 0.005), mats['zinc'])
        else:
            cylinder(parts, 'grommet', d / 2 + 0.004, (back, yc, zc), (back - 0.004, yc, zc), mats['rubber'], 32, 0.001)
    if ncut and lamps:
        for sz in (1, -1):
            for zk in slots:
                for rr, ang, dd in s['screws']:
                    a_ = math.radians(ang)
                    zz, yy = sz * zk + rr * math.cos(a_) * MM, rr * math.sin(a_) * MM
                    cylinder(parts, 'screw', dd / 2 * MM * 0.9, (face, yy, zz), (back - 0.012, yy, zz), mats['zinc'], 12, 0.0)
                    _nut(parts, back, yy, zz, dd * MM, mats['zinc'])
    _remove(placed)
    return {'slots': slots}


RTR_HALF_H = 0.0976  # RTR 3366 çerçevesinin yarı yüksekliği (lamp-rtr3366.glb)


def plate_standoff(kind):
    """RTR 3366 çerçevesi (195 mm) webden yüksek: üst ve alt kenarı 45° eğik kenarlara binmesin diye webden aralayıcıyla uzak
    (eğik kenar, webin düz kenarından taşma kadar geride)"""
    flat = (BUMPERS[kind]['web'] / 2 - 1.5 * T) * MM
    return max(0.006, RTR_HALF_H - flat + 0.004)


def anchors_for(x0):
    """Dorse bağlantı noktası JSON'u için tampon türevleri (x0: tamponun arka dış yüzünün dünya x'i). faceX lambaların oturduğu web
    yüzü, plateX plaka çerçevesinin arka yüzü, armX lastik kolun uç sacındaki yeri, slots lamba merkezleri |z| (dıştan içe)"""
    kinds = {}
    for v, (k, _, _) in VARIANTS.items():
        f = x0 + web_x(k)
        kinds[v] = {'faceX': round(f, 4), 'plateX': round(f + plate_standoff(k), 4), 'armX': round(x0 + arm_x(k), 4), 'slots': variant_slots(v)}
    return {'default': 'tek32', 'kinds': kinds}


def export_variants(trailer, x0, y0, mats, extras, raw_dir):
    """Her türevi dorsedeki yerine (arka dış yüz x0, web ortası y0) taşıyıp dorseye özel parçalarla (extras(parts, kind): askılar,
    dikmeler) birlikte <dorse>-bumper-<türev>.glb olarak dışa aktarır"""
    from bl_common import export_glb
    for v, (k, _, _) in VARIANTS.items():
        Q = Parts()
        build_set(v, mats, Q)
        for o in Q.objs:
            o.data.transform(Matrix.Translation(bl((x0, y0, 0.0))))
        extras(Q, k)
        q = join(Q, f'{trailer}_bumper_{v}')
        smart_uv(q, 0.003)
        export_glb(os.path.join(raw_dir, f'{trailer}-bumper-{v}.glb'), [q])
        bpy.data.objects.remove(q, do_unlink=True)


def build_mudflap(parts, mats, x, y_top, y_bot, half_w, text='TRAILER SYSTEMS', font='C:/Windows/Fonts/arialbd.ttf', holes=(), clamp=0.03,
                  behind=None):
    """Tek parça tozluk (5 mm kauçuk) koruma demirinin arka yüzüne (x) galvaniz lamayla cıvatalı; arkaya bakan yüzünde beyaz yazı
    (baskı kabartması, geometri: her yakınlıkta keskin). mats: rubber, zinc, print. holes: geçiş delikleri [(z, y, r)] (ör. boşaltma
    borusu). clamp: üstte demire kenetlenen bant (y_top − clamp … y_top; tozluk demirin yalnız alt kenarını örter, kullanıcı
    2026-10-22). behind: verilirse tozluk demirin ÖN (dorseye bakan) yüzüne (x) arkadan monte edilir; lama ve somunlar önde
    kalır, demirin arka yüzünde (x = behind) yalnız bombeli cıvata başları görünür (kullanıcı 2026-10-23). Döner: yazı nesnesi (AO
    atlasına girmez)"""
    x0 = x - 0.005 if behind is not None else x
    flap = box2(None, 'mudflap', x0, x0 + 0.005, y_bot, y_top, -half_w, half_w, mats['rubber'], 0.0)
    if holes:
        cut = Parts()
        for zc, yc, r in holes:
            prism_zy(cut, 'flap_hole', [(zc + r * math.cos(2 * math.pi * i / 40), yc + r * math.sin(2 * math.pi * i / 40)) for i in range(40)],
                     x - 0.02, x + 0.025, mats['rubber'], 0.0)
        cutter = join(cut, 'flap_cutter')
        md = flap.modifiers.new('holes', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = cutter
        md.solver = 'EXACT'
        bpy.context.view_layer.objects.active = flap
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
        flap.data.set_sharp_from_angle(angle=math.radians(30))
    parts.objs.append(flap)
    # lama ve somunlar tozluğun demire bakmayan yüzünde (arkadan montajda önde)
    k = -1 if behind is not None else 1
    xs = x0 if behind is not None else x0 + 0.005
    box2(parts, 'mudflap_strip', min(xs, xs + k * 0.004), max(xs, xs + k * 0.004), y_top - clamp + 0.003, y_top - 0.003,
         -(half_w - 0.01), half_w - 0.01, mats['zinc'], 0.001)
    n = 8
    yb = y_top - clamp / 2
    for i in range(n):
        z = -(half_w - 0.08) + 2 * (half_w - 0.08) * i / (n - 1)
        cylinder(parts, 'mudflap_bolt', 0.0095, (xs + k * 0.004, yb, z), (xs + k * 0.011, yb, z), mats['zinc'], 6, 0.0006)
        if behind is not None:
            # demirin arka yüzünde bombeli (gömme omuzlu) cıvata başı
            cylinder(parts, 'mudflap_bolt_head', 0.0085, (behind, yb, z), (behind + 0.003, yb, z), mats['zinc'], 20, 0.0012)
    cu = bpy.data.curves.new('mudflap_text', 'FONT')
    cu.body = text
    if os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.size = 0.11
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.extrude = 0.0004
    ob = bpy.data.objects.new('MudflapText', cu)
    _scene().collection.objects.link(ob)
    ob.data.materials.append(mats['print'])
    bpy.context.view_layer.update()
    fit = 2 * half_w * 0.62
    if ob.dimensions.x > fit:
        cu.size *= fit / ob.dimensions.x
    # yazı düzlemi arkaya (+x) bakar: yerel X → Blender +y (three −z, arkadan bakana sağ), yerel Y → yukarı
    ob.matrix_world = Matrix(((0, 0, 1, x0 + 0.0055), (1, 0, 0, 0), (0, 1, 0, (y_top - clamp + y_bot) / 2), (0, 0, 0, 1)))
    select_only([ob])
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.view_layer.objects.active
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    return ob


# ---------------- lamba bağlantı takımları (plaka lambaları) ----------------
# Plaka lambasının yeri seçime göre değişir (tampon türevine pişirilmez): takım lambanın yerel koordinatında pul + somun (saplamalar)
# ve lastik rakor (kablo geçişi); site lambayla aynı dönüşümle yerleştirir. Yerel: taban düzlemi y = 0, saplamalar −y, sac kalınlığı T.
KITS = ['ltd2834']


def build_kit(pid, mats, parts):
    objs = place_lamp(pid, (0.0, 0.0, 0.0))
    for o in objs:  # lamba yerelinde kesit: kök dönüşümü olmadan
        if o.parent is None:
            o.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    boxes = []
    for o in objs:
        if o.type != 'MESH':
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, -T / 2 * MM), plane_no=(0, 0, 1))
        pts = [v.co.copy() for v in res['geom_cut'] if isinstance(v, bmesh.types.BMVert)]
        bm.free()
        # kesit noktalarını x'te kümele (saplamalar ayrık): 4 mm'den yakın noktalar aynı küme
        pts.sort(key=lambda c: c.x)
        cl = []
        for c in pts:
            if cl and c.x - cl[-1][-1].x < 0.004:
                cl[-1].append(c)
            else:
                cl.append([c])
        for g in cl:
            xs, zs = [c.x for c in g], [-c.y for c in g]
            boxes.append(((min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2, max(xs) - min(xs), max(zs) - min(zs)))
    _remove(objs)
    for xc, zc, dx, dz in boxes:
        d = max(dx, dz)
        if d < 0.0045:  # saplama (kesit diş dibinden ince: anma M5)
            d = 0.005
            # pul + somun: sacın arka yüzünden (y = −T) −y yönünde (three: lamba yerel)
            cylinder(parts, 'washer', 1.05 * d, (xc, -T * MM, zc), (xc, -T * MM - 0.2 * d, zc), mats['zinc'], 20, 0.0)
            cylinder(parts, 'nut', 1.625 * d / 2 / math.cos(math.pi / 6), (xc, -T * MM - 0.2 * d, zc), (xc, -T * MM - 1.0 * d, zc), mats['zinc'], 6, 0.0004)
        else:  # kablo çıkışı: lastik rakor
            cylinder(parts, 'grommet', d / 2 + 0.004, (xc, -T * MM, zc), (xc, -T * MM - 0.004, zc), mats['rubber'], 32, 0.001)
    return boxes


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ONLY = argv[argv.index('--only') + 1].split(',') if '--only' in argv else list(VARIANTS)
    KITS_ONLY = '--kits' in argv  # yalnız plaka lambası bağlantı takımları: tools/blender/out/mount-<id>.glb
    PREVIEW = os.path.abspath(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
    LAMPS = '--lamps' in argv
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    if not scene.world:
        scene.world = bpy.data.worlds.new('World')
    MQ = {'sheet': material('BumperWhite', '#eceef1', 0.32, 0.05, 0.45), 'zinc': material('BumperZinc', '#b8bdc2', 0.3, 1.0),
          'rubber': material('BumperRubber', '#141517', 0.85, 0.0), 'print': material('MudflapPrint', '#f2f3f5', 0.5, 0.0)}
    from bl_common import export_glb, preview_renders  # noqa: E402

    if KITS_ONLY:
        for pid in KITS:
            for o in list(scene.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            P = Parts()
            print('KIT', pid, build_kit(pid, MQ, P))
            ob = join(P, f'mount_{pid}')
            smart_uv(ob, 0.003)
            export_glb(os.path.join(RAW, f'mount-{pid}.glb'), [ob])
        ONLY = []
    for variant in ONLY:
        for o in list(scene.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        P = Parts()
        info = build_set(variant, MQ, P)
        if PREVIEW:
            build_mudflap(P, MQ, 0.03, -0.2, -0.5, 1.15)
        ob = join(P, f'bumper_{variant}')
        smart_uv(ob, 0.003)
        tri = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        export_glb(os.path.join(RAW, f'bumper-{variant}.glb'), [ob])
        print('BUMPER', variant, 'tris', tri, info)
        if LAMPS:
            kind, lamps, _ = VARIANTS[variant]
            for sz in (1, -1):
                for pid, z in zip(lamps, info['slots']):
                    place_lamp(pid, (web_x(kind), 0.0, sz * z), mirror=sz < 0)
        if PREVIEW:
            preview_renders(os.path.join(PREVIEW, variant), [
                ('rear34', (1.6, 0.6, 1.9), (0.0, 0.0, 0.6)),
                ('back34', (-1.0, 0.35, 1.5), (0.0, 0.0, 0.75)),
                ('backnear', (-0.45, 0.12, 1.15), (-0.05, 0.0, 0.85)),
                ('end', (0.25, 0.12, 1.55), (-0.04, 0.0, 1.2)),
            ])
    print('DONE', ONLY)
