// Lambalar, soketler, montaj braketleri ve tesisat. Seçimler değiştikçe bu grup baştan kurulur.
// Lambalar gerçek ürünlerin Blender modelleridir (lampfx.ts → lamp-<id>.glb); yüklenene kadar sade bir yer tutucu görünür.
//
// Tesisat düzeni Horpol şemasına göre (vault: Kablolama ve Işıklandırma/Kablolama Şeması - Yeni). Dorse betiği harness.top
// veriyorsa (standart, 2026-10-22) yeni şema (schemeHarness):
//   ön soket → 0,5 m kablo → yuvarlak ara fiş → 16,5 m ana hat → Horpol modülünün ön yüzü
//   modülün arka yüzü: 7×1 çıkış → Y ayırıcı → 2 × 2,5 m arka lambaların AMP 7 pin fişine
//                      2 × 17 m yan hat 2×0,5 (her yanda): önce arkaya, yana, sonra öne; yan markerlar 0,6 m dallarla
//                      (hatta T bağlantı), ucunda ön pozisyon; çalışma / tepe lambaları kendi portlarından (HOR-1001'den)
//   arka lambanın Superseal soketlerinden: plaka lambası (1,5 m) ve arka lastik kol
// Gizli güzergâh (normal görünüm) ve gösterim güzergâhı (tesisat görünümü: yatay hatlar şasinin üstünde) ayrı iki grup.
// Diğer dorseler eski şemada: yan hat arka lambanın Superseal'inden; çalışma / tepe için ayrı 2×1 besleme.
// Montaj noktaları dorse betiğinin yazdığı `mounts` (R48 haritası) varsa ondan, yoksa eski bağlantı noktalarından.
import * as THREE from 'three';
import { CATEGORIES, layoutOf, productById, rulesFor, type CategoryId, type Config } from '../data';
import type { Mats } from './materials';
import { profileAt, type Anchors } from './trailer';
import { isShared, markShared } from './geo';
import { lampInstance } from './lampfx';
import type { PlateLight } from './plateLight';
import { ALL_CATS, CAT_BIT, drawHarness, MODULE, modulePort, moduleModel, socketModel, wireMat, type Conn, type ConnType, type Wire, type WireKind } from './harness';

export interface EquipmentBuild {
  group: THREE.Group;
  harness: THREE.Group;
  lampsByCat: Record<CategoryId, THREE.Object3D[]>;
  /** gerçek modeli henüz yüklenmemiş lamba var mı (Engine yüklenince yeniden kurar) */
  placeholders: number;
  /** plaka: çerçeve seçiliyse plakanın yeni yeri (null: taşıyıcıdaki yerinde) ve plakaya düşen ışığın yerleşimi */
  plate: { pos: THREE.Vector3 | null; light: PlateLight };
}

/** RTR 3366 plaka yuvası, çerçeve yerelinde (m): tools/blender/lamps_cad.py RTR_SEAT ile aynı; model yüklenince MOUNT_plate esas */
const RTR_SEAT = { y: 0.00385, z: 0.0184 };
/** RTR 3366 çerçevesinin yarı genişliği (m; lamp-rtr3366.glb sınır kutusu) */
const RTR_HALF_W = 0.2653;

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
/** art arda çakışan noktaları atar (kısa düz uçlarda iki nokta aynı yere düşebilir) */
const dedupe = (pts: THREE.Vector3[]) => pts.filter((p, i) => i === 0 || p.distanceTo(pts[i - 1]) > 1e-4);
function m(geo: THREE.BufferGeometry, mat: THREE.Material, cast = true) {
  const x = new THREE.Mesh(geo, mat);
  x.castShadow = cast;
  x.receiveShadow = true;
  return x;
}

// ---------- montaj haritası (dorse betiğinin `mounts` alanı; şema baked.ts → BakedMounts) ----------
type P3 = { x: number; y: number; z: number };
type Bracket = [number, number, number][] | null | undefined;
interface MountsLike {
  rear?: { x: number; y: number; zOuter: number; zInner?: number; faceX?: number };
  plate?: { x: number; y: number; z: number[]; plateY?: number };
  side?: {
    x0: number;
    x1: number;
    y: [number, number][];
    z: number;
    brackets?: { x0: number; x1: number; from: [number, number]; to: [number, number] } | null;
    /** marker merkezinin giremeyeceği x aralıkları (ör. tekerlek kemeri): eşit aralıklı yer buraya düşerse en yakın kenara kayar */
    avoid?: [number, number][];
    /** ayrı düz kesimler [x0, x1] (önden arkaya): markerlar kesimlere boylarıyla orantılı dağılır, her kesimde eşit aralıklı */
    segments?: [number, number][];
    /** sabit marker yuvaları [x, y], arkadan öne (ör. lastik ortaları); verilirse eşit aralık yerine bunlar kullanılır */
    slots?: [number, number][];
    /** yan hat rayın/rafın içinde tek düz hat: z (iç yüz), y profili, arkada yükselme [x, z|null], önde kirişe giriş [x, y] */
    rail?: {
      z: number;
      y: [number, number][];
      rise: [number, number | null];
      pass?: number | null;
      exit?: [number, number];
      /** yükseldikten sonra raya kadar izlenen [|z|, y] noktaları (ör. damper kasa tabanının altı) */
      bend?: [number, number][];
      /** ön pozisyon ve ön kol raydan değil şasi demetinden (devrilen kasada kablo kasadan şasiye önde geçmez) */
      frontFromChassis?: boolean;
    };
  };
  front?: P3 & { bracket?: Bracket };
  armRear?: P3 & { wallZ?: number; bracket?: Bracket };
  armRearAlt?: P3 & { wallZ?: number; bracket?: Bracket };
  armFront?: P3 & { wallZ?: number; bracket?: Bracket };
  /** rise: kablonun dikey çıktığı [x, |z|, yanal geçiş y?] (dar kule/travers önü gibi; yoksa en yakın köşe) */
  /** between: lamba taşıyıcıda stop ile plaka arasında (z sitede seçime göre hesaplanır) */
  work?: (P3 & { dir?: [number, number, number]; bracket?: Bracket; rise?: number[]; between?: boolean })[];
  beacon?: (P3 & { bracket?: Bracket; rise?: number[] })[];
  harness?: {
    trunkY?: number;
    trunkZ?: number;
    profile?: [number, number][];
    moduleX?: number;
    rearJunctionX?: number;
    /** arka 7×1 hattın lamba barına indiği yer (|z|) ve barın içinde yanal gittiği x: arkadan bakınca dikme kabloyu örter */
    rearDrop?: { z: number; innerX: number };
    /** yeni şema: tesisat görünümünde yatay hatların gösterildiği şasi üstü (y; değişkense profile [x, y]) ve yan hattın |z|'si */
    top?: { y: number; sideZ: number; turnX?: number; profile?: [number, number][] };
  };
}

// ---------- yer tutucu (model yüklenene kadar) ----------
const PH_GEO = markShared(new THREE.BoxGeometry(1, 1, 1));
const PH_SIZE: Record<CategoryId, [number, number, number]> = {
  stop: [0.3, 0.12, 0.05],
  side: [0.11, 0.045, 0.02],
  plate: [0.09, 0.05, 0.06],
  front: [0.11, 0.045, 0.02],
  arm: [0.04, 0.16, 0.18],
  work: [0.11, 0.11, 0.06],
  beacon: [0.15, 0.12, 0.15],
};
function placeholder(cat: CategoryId, mats: Mats) {
  const g = new THREE.Group();
  const [w, h, d] = PH_SIZE[cat];
  const b = m(PH_GEO, mats.plastic);
  b.scale.set(w, h, d);
  b.position.set(0, cat === 'beacon' ? h / 2 : 0, cat === 'beacon' ? 0 : d / 2);
  g.add(b);
  g.userData.placeholder = true;
  return g;
}

// ---------- tesisat ----------
/** lambaya giden dalın konnektörü lambadan bu kadar önce (m) */
const CONN_FROM_LAMP = 0.3;
/** kesişmede alttan geçen kablonun çukur derinliği (m): iki kablonun çizim yarıçapları toplamı (~0,04) + boşluk */
const DIP = 0.055;

/** Eski şema (harness.top olmayan dorseler) Horpol modülü: siyah gövde, açık renk çerçeve ve kulaklar, üstte logo; portlar yanlarda. */
function controlModule(mats: Mats) {
  const g = new THREE.Group();
  g.add(m(new THREE.BoxGeometry(0.4, 0.075, 0.3), mats.plastic));
  const rim = m(new THREE.BoxGeometry(0.42, 0.045, 0.32), mats.connWhite);
  rim.position.y = -0.018;
  g.add(rim);
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      const ear = m(new THREE.CylinderGeometry(0.024, 0.024, 0.02, 16), mats.connWhite);
      ear.position.set(sx * 0.205, -0.02, sz * 0.155);
      g.add(ear);
    }
  }
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(0.25, (0.25 * 528) / 720), mats.logoWhite);
  logo.rotation.set(-Math.PI / 2, 0, Math.PI / 2);
  logo.position.y = 0.0385;
  g.add(logo);
  return g;
}

// Işıma (hale, zemin ışığı) Engine'deki bloom ile yanan parçanın kendi biçiminden gelir (2026-10-20); sprite efektleri kaldırıldı.
/** Arka lambaların genişliği (lamba yerel X), dizilim için: modelden ölçülür, yoksa ürüne göre tahmin */
const LAMP_W: Record<string, number> = { lzd3194: 0.405, lzd2854: 0.449, lzd2448: 0.168, lzd2452: 0.168 };

export function buildEquipment(c: Config, a: Anchors, mats: Mats): EquipmentBuild {
  const group = new THREE.Group();
  const harness = new THREE.Group();
  group.add(harness);
  const lampsByCat = Object.fromEntries(CATEGORIES.map((k) => [k.id, []])) as unknown as Record<CategoryId, THREE.Object3D[]>;
  const M: MountsLike = (a.mounts as MountsLike) ?? {};
  let placeholders = 0;
  const brackets: Bracket[] = [];

  /** Lambayı kurar: yerel çerçeve (lens +Z) → dünya. setup döndürme/aynalama uygular. */
  const mount = (cat: CategoryId, id: string, pos: THREE.Vector3, setup: (o: THREE.Object3D) => void) => {
    const inst = lampInstance(id);
    const obj = inst ?? placeholder(cat, mats);
    if (!inst) placeholders++;
    setup(obj);
    obj.position.copy(pos);
    obj.traverse((o) => (o.userData.category = cat));
    group.add(obj);
    lampsByCat[cat].push(obj);
    return obj;
  };
  const lampWidth = (id: string, obj?: THREE.Object3D) => {
    if (obj && !obj.userData.placeholder) {
      // montaj plakası (BRACKET, ör. lastik kol plakası) lambanın genişliğine sayılmaz: lamba kenara dayanır, plaka dışa taşar
      const bb = new THREE.Box3();
      obj.updateMatrixWorld(true);
      obj.traverse((m) => {
        if (!(m as THREE.Mesh).isMesh) return;
        for (let q: THREE.Object3D | null = m; q && q !== obj; q = q.parent) if (q.name.startsWith('BRACKET')) return;
        bb.expandByObject(m, true);
      });
      const sz = bb.getSize(V(0, 0, 0));
      return Math.max(sz.z, 0.05); // dünyada yanal (arka lambalar +X'e döndürülür)
    }
    return LAMP_W[id] ?? 0.3;
  };

  // --- tesisat düzlemi ---
  const hy = M.harness?.trunkY ?? a.harness.y;
  const prof = (M.harness?.profile as [number, number][] | undefined) ?? a.harness.profile;
  const hyAt = (x: number) => profileAt(prof, x);
  const follow = (pts: THREE.Vector3[]) => {
    const out: THREE.Vector3[] = [];
    pts.forEach((p, i) => {
      const q = pts[i - 1];
      if (q && Math.abs(q.y - hy) < 1e-6 && Math.abs(p.y - hy) < 1e-6 && Math.abs(p.x - q.x) > 1e-6) {
        const lo = Math.min(q.x, p.x);
        const hi = Math.max(q.x, p.x);
        const bx = prof.map((b) => b[0]).filter((x) => x > lo + 1e-6 && x < hi - 1e-6);
        if (p.x < q.x) bx.reverse();
        for (const x of bx) out.push(V(x, hy, q.z + ((p.z - q.z) * (x - q.x)) / (p.x - q.x)));
      }
      out.push(p.clone());
    });
    for (const v of out) if (Math.abs(v.y - hy) < 1e-6) v.y = hyAt(v.x);
    return out;
  };
  const W2 = a.W / 2;
  const xm = M.harness?.moduleX ?? -2.2;
  const PORTS = [-0.135, -0.045, 0.045, 0.135]; // modül yan portları (önden arkaya): besleme, arka hat, yedek (çalışma), yedek (tepe)
  const zPort = 0.15;
  const tz = M.harness?.trunkZ ?? a.harness.trunkZ ?? 0.85; // yan hatların boyuna güzergâhı (kirişin yanı)
  const zr = a.harness.rearZ ?? 0.62; // arka hatların yanal konumu
  const xd = M.harness?.rearJunctionX ?? -0.55; // arka dağıtım
  const zMain = 0.06; // ana hat: orta eksenin hemen yanı (kirişlerin arası, korumalı)

  // eski şemanın kabloları ve konnektörleri (yeni şema schemeHarness içinde kendi listelerini kurar)
  const wires: Wire[] = [];
  const toLamp = { d: CONN_FROM_LAMP, fromEnd: true };
  const conns: Conn[] = [];

  // =========================== ARKA LAMBALAR ===========================
  const stop = c.lamps.stop;
  const R = M.rear;
  const rx = R?.faceX ?? R?.x ?? a.rear.x;
  const ly = R?.y ?? a.rear.lampY;
  // set (ör. LUNA): her yanda dıştan içe bileşenler sırayla
  const perSide = Math.floor(stop.qty / 2);
  // dizilimli set (LUNA: dıştan 2–3 × LZD 2448, en içte LZD 2452); yoksa tek ürün
  const stopSet = layoutOf(productById('stop', stop.product), perSide) ?? productById('stop', stop.product).set ?? [stop.product];
  const zEdge = R ? R.zOuter : Math.min(W2 - 0.03, a.rear.lampZ[0] + (LAMP_W[stopSet[0]] ?? 0.3) / 2);
  // her yan: dıştan içe dizilen lambalar [z merkezi, yarı genişlik]
  const rearLamps: { s: number; z: number; hw: number }[] = [];
  /** dıştaki arka lambanın lastik kol takma noktası (modelde MOUNT_arm varsa; ör. LZD 3194 MAVIC) */
  const armMount: Record<number, THREE.Vector3> = {};
  for (const s of [1, -1]) {
    let edge = zEdge;
    for (let k = 0; k < perSide; k++) {
      const sid = stopSet[k % stopSet.length];
      const o = mount('stop', sid, V(rx, ly, 0), (obj) => {
        obj.rotation.y = Math.PI / 2;
        if (s < 0) obj.scale.x = -1; // sağ lamba: ayna (LZD 3195 / 2857)
      });
      const w = lampWidth(sid, o);
      const z = edge - w / 2;
      o.position.z = s * z;
      const mp = k === 0 ? o.getObjectByName('MOUNT_arm') : undefined;
      if (mp) {
        o.updateMatrixWorld(true);
        armMount[s] = mp.getWorldPosition(V(0, 0, 0)); // grup ekseni (grup henüz sahnede değil, birim dönüşüm)
      }
      rearLamps.push({ s, z, hw: w / 2 });
      edge = z - w / 2 - 0.025;
    }
  }

  // =========================== PLAKA ===========================
  const pl = c.lamps.plate;
  const P = M.plate;
  const plateCy = P?.plateY ?? a.rear.plateY; // plakanın merkez yüksekliği
  const plateFace = a.rear.x + 0.006; // plakanın arka yüzü (trailer.ts ile aynı)
  const PLATE_HALF_W = 0.26;
  /** Her plaka lambası: konum, yönlendirme (lens plakaya bakar) ve kablonun girdiği nokta */
  type PlateSpot = { id: string; pos: THREE.Vector3; q: THREE.Quaternion; entry: THREE.Vector3 };
  const plateSpots: PlateSpot[] = [];
  let plateLight: PlateLight = null;
  /** plaka çerçevesinde plakanın yeni yeri (yoksa taşıyıcıdaki yerinde kalır) */
  let platePos: THREE.Vector3 | null = null;
  const basis = (x: THREE.Vector3, y: THREE.Vector3, z: THREE.Vector3) => new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
  // dorse kuralı plateFrame (ör. standart: RTR 3366): çerçeve her zaman takılı, seçilen plaka lambaları onun iki yanına eklenir
  const frameId = rulesFor(c.trailer).plateFrame;
  const frameOn = frameId ?? (pl.qty > 0 && pl.product === 'rtr3366' ? pl.product : undefined);
  const sideId = pl.qty > 0 && pl.product !== frameOn ? pl.product : undefined;
  if (frameOn) {
    // RTR 3366 (HOR 160): LED aydınlatmalı plaka çerçevesi, plakanın yerine taşıyıcıya vidalanır; plaka çerçevenin yuvasına
    // oturur, saçağın altındaki 3 modül plakaya aşağı ışık verir. Yerel: Z dışa (dünya +X), Y yukarı, X = dünya −Z.
    // Kablo alt kenarın ortasından çıkar.
    const base = V(plateFace - 0.001, plateCy - RTR_SEAT.y, 0);
    plateSpots.push({ id: frameOn, pos: base, q: basis(V(0, 0, -1), V(0, 1, 0), V(1, 0, 0)), entry: V(base.x + 0.002, base.y - 0.115, 0) });
    plateLight = { top: [-0.171, 0, 0.171] };
  }
  if (sideId) {
    // LTD 2834 ve LTD 229: plakanın İKİ YANINDA (çizim HOR 47: lamba ekseni plaka kenarından 40–80 mm), TABANI taşıyıcının
    // dikey arka yüzüne vidalı (civatalar öne, taşıyıcıya girer), ışık penceresi plakanın ortasına bakar. Yerel eksenler:
    // Y (taban → üst) = dünya +X (arkaya), Z (pencere) = plakaya doğru (∓z), X = Y × Z.
    // Çerçeve varsa lamba çerçevenin dış kenarının dışına (RTR yarı genişliği 265 mm + lamba yarı derinliği 35 mm + 12 mm pay).
    const zl = frameOn ? RTR_HALF_W + 0.035 + 0.012 : PLATE_HALF_W + 0.04;
    const zs = pl.qty === 1 ? [zl] : [zl, -zl];
    for (const z of zs) {
      const s = z > 0 ? 1 : -1;
      const Yw = V(1, 0, 0);
      const Zw = V(0, 0, -s);
      const base = V(plateFace - 0.002, plateCy, z);
      plateSpots.push({ id: sideId, pos: base, q: basis(Yw.clone().cross(Zw), Yw, Zw), entry: V(base.x - 0.02, base.y, z) });
    }
    // ışık penceresi lambanın derinlik ortasından ~31 mm plakaya doğru
    plateLight = { ...plateLight, side: zs.map((z) => z - Math.sign(z) * 0.031) };
  }
  for (const sp of plateSpots) {
    const o = mount('plate', sp.id, sp.pos, (obj) => {
      obj.quaternion.copy(sp.q);
    });
    if (sp.id === frameOn) {
      const mp = o.getObjectByName('MOUNT_plate');
      o.updateMatrixWorld(true);
      platePos = mp ? mp.getWorldPosition(V(0, 0, 0)) : V(sp.pos.x + RTR_SEAT.z, plateCy, 0);
    }
  }

  // =========================== YAN MARKERLAR ===========================
  const sd = c.lamps.side;
  const S = M.side;
  const sx0 = S?.x0 ?? a.side.x0;
  const sx1 = S?.x1 ?? a.side.x1;
  const sideY = (x: number) => (S?.y ? profileAt(S.y, x) : a.side.yAt(x));
  const sideZ = S?.z ?? a.side.z;
  const per = Math.floor(sd.qty / 2);
  const sideXs: number[] = [];
  const slotY = new Map<number, number>();
  const slots = S?.slots;
  if (slots?.length) {
    // sabit yuvalar (arkadan öne); az marker seçilince uçlar korunarak seyreltilir
    const n = Math.min(per, slots.length);
    const idx = n === 1 ? [Math.floor((slots.length - 1) / 2)] : Array.from({ length: n }, (_, i) => Math.round((i * (slots.length - 1)) / (n - 1)));
    for (const i of idx) {
      sideXs.push(slots[i][0]);
      slotY.set(slots[i][0], slots[i][1]);
    }
    sideXs.sort((p, q) => p - q);
  } else {
    const avoid = S?.avoid ?? [];
    const snap = (x: number) => {
      for (let k = 0; k < avoid.length; k++) {
        const r = avoid.find(([p, q]) => x > p && x < q);
        if (!r) break;
        x = x - r[0] < r[1] - x ? r[0] : r[1];
      }
      return x;
    };
    const even = (a: number, b: number, n: number) => Array.from({ length: n }, (_, i) => (n === 1 ? (a + b) / 2 : a + ((b - a) * i) / (n - 1)));
    const segs = S?.segments;
    if (segs?.length && per > 1) {
      // ayrı düz kesimler (ör. lowbed boyun ve platform): adet boylarıyla orantılı (her kesime en az 1), her kesimde eşit aralık
      const len = segs.map(([p, q]) => q - p);
      const tot = len.reduce((u, v) => u + v, 0);
      const cnt = len.map((l) => Math.max(1, Math.floor((per * l) / tot)));
      while (cnt.reduce((u, v) => u + v, 0) < per) {
        const k = len.map((l, i) => (per * l) / tot - cnt[i]).reduce((b, v, i, r) => (v > r[b] ? i : b), 0);
        cnt[k]++;
      }
      while (cnt.reduce((u, v) => u + v, 0) > per) cnt[cnt.indexOf(Math.max(...cnt))]--;
      segs.forEach(([p, q], i) => sideXs.push(...even(p, q, cnt[i]).map(snap)));
    } else {
      sideXs.push(...even(sx0, sx1, per).map(snap));
    }
  }
  const markerY = (x: number) => slotY.get(x) ?? sideY(x);
  for (const x of sideXs) {
    const y = markerY(x);
    for (const s of [1, -1]) {
      mount('side', sd.product, V(x, y, s * sideZ), (o) => {
        if (s < 0) o.rotation.y = Math.PI;
      });
    }
    // marker braketi (tanker önü, damper): kirişten (from: [y, z]) yan düzleme (to: [y, z]) uzanan kol + lamba tablası
    const sb = S?.brackets;
    if (sb && x >= sb.x0 && x <= sb.x1) {
      for (const s of [1, -1]) {
        const p = V(x, sb.from[0], s * sb.from[1]);
        const q = V(x, sb.to[0], s * (sb.to[1] - 0.012));
        const arm = m(new THREE.BoxGeometry(0.045, 0.035, p.distanceTo(q)), mats.chassis);
        arm.position.copy(p).add(q).multiplyScalar(0.5);
        arm.lookAt(q);
        group.add(arm);
        const pad = m(new THREE.BoxGeometry(0.13, 0.075, 0.008), mats.chassis);
        pad.position.set(x, sb.to[0], s * (sb.to[1] - 0.004));
        group.add(pad);
      }
    }
    if (a.side.brackets && !S) {
      for (const s of [1, -1]) {
        const arm = m(new THREE.BoxGeometry(0.05, 0.05, W2 - 0.52), mats.chassis);
        arm.position.set(x, y + 0.045, s * (0.52 + (W2 - 0.52) / 2));
        group.add(arm);
      }
    }
  }

  // =========================== ÖN POZİSYON ===========================
  const fr = c.lamps.front;
  const F: P3 & { bracket?: Bracket } = M.front ?? a.front;
  if (fr.qty > 0) {
    for (const s of [1, -1]) {
      mount('front', fr.product, V(F.x, F.y, s * F.z), (o) => {
        o.rotation.y = -Math.PI / 2;
      });
    }
    if (F.bracket) brackets.push(F.bracket);
  }

  // =========================== LASTİK KOL ===========================
  const ar = c.lamps.arm;
  // lambada kol takma noktası yoksa (LUNA, CUBE …) dorse kuralına göre taşıyıcı plakanın dış kenarı (kasa köşesi değil)
  const onCarrier = rulesFor(c.trailer).armOnCarrier && !Object.keys(armMount).length && M.armRearAlt;
  const AR: P3 & { wallZ?: number; bracket?: Bracket } = onCarrier ? M.armRearAlt! : (M.armRear ?? a.armRear);
  const AF: P3 & { wallZ?: number; bracket?: Bracket } = M.armFront ?? a.armFront;
  const armSpots = ar.qty >= 4 ? [AR, AF] : ar.qty >= 2 ? [AR] : [];
  for (const sp of armSpots) {
    const wz = sp.wallZ ?? sp.z;
    for (const s of [1, -1]) {
      // arka kol: lambada takma noktası (MOUNT_arm) varsa kol plakası lambanın ucundaki adaptöre DÖNDÜRMEDEN oturur (kolun
      // kendi biçimi yukarı eğik; LZD 3194 STEP'indeki LDCC 2698 montajıyla aynı); yoksa montaj haritasındaki yerine (duvara dik)
      const lm = sp === AR ? armMount[s] : undefined;
      mount('arm', ar.product, lm ? lm.clone() : V(sp.x, sp.y, s * wz), (o) => {
        if (s < 0) o.scale.z = -1;
      });
    }
    if (sp.bracket) brackets.push(sp.bracket);
  }

  // =========================== ÇALIŞMA ve TEPE ===========================
  const wk = c.lamps.work;
  const workSpots = (M.work ?? [{ x: a.extra.x, y: a.extra.y, z: a.extra.z0, dir: [1, -0.25, 0] as [number, number, number] }, { x: a.extra.x, y: a.extra.y, z: -a.extra.z0, dir: [1, -0.25, 0] as [number, number, number] }])
    .slice(0, wk.qty)
    .map((sp) => {
      if (!sp.between) return sp;
      // stop ile plaka arası (standart): o yandaki arka lambaların iç kenarı ile plaka lambalarının dış kenarının ortası
      const s = sp.z >= 0 ? 1 : -1;
      const inner = Math.min(...rearLamps.filter((r) => r.s === s).map((r) => r.z - r.hw), R?.zOuter ?? W2);
      const plateOuter = Math.max(0, ...plateSpots.map((p) => Math.abs(p.pos.z) + (p.id === frameOn ? RTR_HALF_W : 0.035)));
      return { ...sp, z: s * (inner + plateOuter) / 2 };
    });
  for (const sp of workSpots) {
    const d0 = sp.dir ?? [1, -0.25, 0];
    // yatay yön korunur, aşağı eğim hafifletilir (dik montajlı braket); yuvarlanma yok: lambanın üstü dünya Y'ye bakar
    const d = V(d0[0], Math.max(-0.12, Math.min(0, d0[1] * 0.5)), d0[2]).normalize();
    mount('work', wk.product, V(sp.x, sp.y, sp.z), (o) => {
      o.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(d, V(0, 0, 0), V(0, 1, 0)));
    });
    if (sp.bracket) brackets.push(sp.bracket);
  }
  const bc = c.lamps.beacon;
  const beaconSpots = (M.beacon ?? [{ x: Math.min(-0.3, a.extra.x - 0.2), y: a.topY, z: 0.9 }, { x: Math.min(-0.3, a.extra.x - 0.2), y: a.topY, z: -0.9 }]).slice(0, bc.qty);
  for (const sp of beaconSpots) {
    mount('beacon', bc.product, V(sp.x, sp.y, sp.z), () => {});
    if (sp.bracket) brackets.push(sp.bracket);
  }

  // =========================== BRAKETLER (sabit montaj) ===========================
  const addBrackets = () => {
    for (const b of brackets) {
      if (!b || b.length < 2) continue;
      for (let i = 0; i < b.length - 1; i++) {
        const p = V(...b[i]);
        const q = V(...b[i + 1]);
        const len = p.distanceTo(q);
        if (len < 1e-3) continue;
        const bar = m(new THREE.BoxGeometry(0.04, 0.04, len), mats.darkMetal);
        bar.position.copy(p).add(q).multiplyScalar(0.5);
        bar.lookAt(q);
        bar.userData.category = 'bracket';
        group.add(bar);
      }
    }
  };

  // =========================== SOKETLER ===========================
  const kinds: ('7' | '15')[] = c.socket === '7x2' ? ['7', '7'] : c.socket === '15' ? ['15'] : ['7', '15', '7'];
  const spacing = 0.15;
  const fx = a.harness.frontX;
  const aux = wk.qty + bc.qty > 0;
  const socketZ = (i: number) => (i - (kinds.length - 1) / 2) * spacing;
  kinds.forEach((k, i) => {
    const so = socketModel(mats, k, k === '15' ? mats.socketGrey : i === 0 ? mats.socket : mats.socketGrey);
    so.rotation.y = -Math.PI / 2;
    so.position.set(a.socket.x, a.socket.y, socketZ(i));
    so.traverse((o) => (o.userData.category = 'socket'));
    group.add(so);
  });

  // =========================== YENİ ŞEMA (dorse betiğinde harness.top) ===========================
  const TOP = M.harness?.top;
  if (TOP) {
    const hidden = schemeHarness(false);
    const shown = schemeHarness(true);
    harness.add(hidden, shown);
    harness.userData.views = { hidden, shown };
    addBrackets();
    return { group, harness, lampsByCat, placeholders, plate: { pos: platePos, light: plateLight } };
  }

  /**
   * Yeni şemanın tesisatı. show = tesisat görünümü: yatay hatlar şasinin (kiriş ve travers) üstünde, yan hat dış rayın iç
   * yanında; değilse gizli güzergâh (traverslerin gövdesinden, kirişin iç yanından). İniş ve lambaya giden uçlar ikisinde aynı.
   * Yalnız seçili lambaların kablosu kurulur.
   */
  function schemeHarness(show: boolean) {
    const out = new THREE.Group();
    const B = CAT_BIT;
    // Yatay hatların seviyesi x'e göre değişebilir (lowbed: boyun, kaz boynu, platform). Noktalar Y = LV yer tutucusuyla kurulur;
    // y'si LV'ye yakın her nokta sonunda lvl(x) + (y − LV) olur, iki seviye noktası arasına profil kırılmaları eklenir.
    const LV = 100;
    const Y = LV;
    const lvlProf: [number, number][] = show ? (TOP!.profile ?? [[-a.L, TOP!.y], [0, TOP!.y]]).map(([x, y]) => [x, y + 0.03]) : prof;
    const lvl = (x: number) => profileAt(lvlProf, x);
    const onLv = (p: THREE.Vector3) => Math.abs(p.y - LV) < 1;
    const lift = (p: THREE.Vector3) => (onLv(p) ? V(p.x, lvl(p.x) + p.y - LV, p.z) : p);
    const level = (pts: THREE.Vector3[]) => {
      const res: THREE.Vector3[] = [];
      pts.forEach((p, i) => {
        const q = pts[i - 1];
        if (q && onLv(q) && onLv(p) && Math.abs(p.y - q.y) < 1e-6 && Math.abs(p.x - q.x) > 1e-6) {
          const bx = lvlProf.filter(([x]) => x > Math.min(q.x, p.x) + 1e-6 && x < Math.max(q.x, p.x) - 1e-6);
          if (p.x < q.x) bx.reverse();
          for (const [x, y] of bx) res.push(V(x, y + p.y - LV, q.z + ((p.z - q.z) * (x - q.x)) / (p.x - q.x)));
        }
        res.push(lift(p));
      });
      return res;
    };
    const busZ = show ? TOP!.sideZ : tz;
    const ws: Wire[] = [];
    const cn: Conn[] = [];
    const wire = (kind: WireKind, r: number, pts: THREE.Vector3[], cats: number, level: number, conn?: Wire['conn']) =>
      ws.push({ kind, r, pts: dedupe(pts), cats, level, conn });
    const plug = (type: ConnType, pos: THREE.Vector3, dir: THREE.Vector3, side?: THREE.Vector3, scale?: number) => cn.push({ type, pos, dir, side, scale });

    // --- modül: port ağızları kablo yüksekliğinde ---
    const mod = moduleModel(mats);
    mod.position.set(xm, lvl(xm) - modulePort('front', 0).y, 0);
    out.add(mod);
    const port = (face: 'front' | 'rear', z: number) => modulePort(face, z).add(mod.position);
    const toModule = V(1, 0, 0);
    const fromModule = V(-1, 0, 0); // arka yüzdeki fiş modüle doğru (−X)

    // Port eşleşmesi (modülün iki yüzünde soldan sağa 3 Superseal + en sağda büyük soket; sağ = −z):
    //   ön yüz büyük soket: ana besleme; arka yüz büyük soket: 7×1 arka hat
    //   arka yüz Superseal: sol (+z) yan hat · orta çalışma lambaları · sağ (−z) yan hat
    // Arkaya giden şeritler (z): sol yan hat 0,165 · çalışma 0,085 · sağ yan hat 0,005 · 7×1 −0,13 (modülün hemen arkasındaki
    // Y ayırıcıdan sonra iki kol: −0,095 ve −0,165). Sağ yan hat 7×1 kollarını iki travers arasındaki boşlukta (top.turnX)
    // altlarından kısa bir çukurla geçer: yukarıdan bakınca çukur kırmızı hatların arkasında kalır, kırmızılar düz görünür.
    const [zS1, zS2, zS3] = MODULE.small;
    const zR = MODULE.big;
    const rearLanes = rearLamps.length ? [zR - 0.035, zR + 0.035] : [];
    /**
     * Önden gelip x'te yana dönen koşu (zA → zB); crossings'teki z'lerde üstteki kablonun altından geçer (yakın kesişmeler tek
     * çukur). Kesişme dönüş noktasına yakınsa kablo dönmeden hemen önce (son traversin arkasında) alçalır, yana alçaktan döner.
     * ax: kablonun x'te geliş yönü (1: önden arkaya, −1: arkadan öne).
     */
    const lateral = (x: number, y: number, zA: number, zB: number, crossings: number[] = [], ax = 1) => {
      const d = Math.sign(zB - zA);
      const pts = [V(x, y, zA)];
      // gizli güzergâhta kablolar şasinin içinde, kesişme görünmez: çukur yalnız tesisat görünümünde
      const cs = (show ? crossings : []).filter((q) => (q - zA) * d > 0 && (zB - q) * d > 0.2).sort((p, q) => (p - q) * d);
      for (let i = 0; i < cs.length; ) {
        let j = i;
        while (j + 1 < cs.length && (cs[j + 1] - cs[j]) * d < 0.25) j++;
        // düz dip üstteki kablonun iki yanından taşar (köşe yuvarlaması dibi yükseltmesin), çıkış yokuşu yumuşak
        if ((cs[i] - zA) * d > 0.2) pts.push(V(x, y, cs[i] - d * 0.2), V(x, y - DIP, cs[i] - d * 0.075));
        else pts.splice(0, 1, V(x - ax * 0.08, y, zA), V(x, y - DIP, zA));
        pts.push(V(x, y - DIP, cs[j] + d * 0.075), V(x, y, cs[j] + d * 0.2));
        i = j + 1;
      }
      pts.push(V(x, y, zB));
      return pts;
    };

    // --- ana besleme: modülün ön yüzündeki büyük soketten öne tek kalın kablo; önde büyük ara fişte soket seçimine göre
    // (7×2: 2, 15: 1, 7×2 + 15: 3) kollara ayrılır, her kol 0,5 m ile kendi soketine ---
    const PF = port('front', zR);
    plug('roundPlug', PF, toModule);
    const J = V(fx + 0.75, Y, zR); // ayrılma noktasındaki büyük ara fiş
    const JH = 0.16 * 1.5 * 0.65; // fiş çiftinin yarı boyu (ölçek 1,3)
    plug('round', J, V(1, 0, 0), undefined, 1.3);
    wire('main', 0.018, [V(J.x + JH, Y, zR), V(PF.x - 0.3, Y, zR), PF], ALL_CATS, 1);
    kinds.forEach((_, i) => {
      const z = socketZ(i);
      // kollar ayırıcının girişine yan yana (demet) girer
      const off = (i - (kinds.length - 1) / 2) * 0.016;
      const xi = J.x - JH;
      wire('main', 0.009, [V(a.socket.x + 0.02, a.socket.y, z), V(fx, a.socket.y, z), V(fx, Y, z), V(xi - 0.32, Y, z), V(xi - 0.07, Y, zR + off), V(xi + 0.01, Y, zR + off)], ALL_CATS, 0);
    });

    // --- arka lambalar lamba taşıyıcı kutusunun içine oturur: 7×1 hat arka dağıtımda (xd) kutunun üstünden iner, AMP fişi ve
    // Superseal soketleri kutunun içinde (görünmez; çizilmez), plaka ve kol kabloları kutunun içinden çıkar ---
    const xDrop = xd;
    const ssOut = (r: (typeof rearLamps)[number]) => V(rx - 0.035, ly - 0.03, r.s * (r.z + r.hw * 0.6));
    const ssIn = (r: (typeof rearLamps)[number]) => V(rx - 0.035, ly - 0.03, r.s * (r.z - r.hw * 0.6));
    const needSide = sideXs.length > 0 || fr.qty > 0 || ar.qty >= 4;
    /** yan hatların yana döndüğü x: dorse betiğinin verdiği travers boşluğu; yoksa en arkadaki markerın arkası */
    const xb = TOP!.turnX ?? (sideXs.length ? Math.min(Math.max(...sideXs) + 0.12, xDrop - 0.2) : xDrop - 0.25);

    // --- 7×1 arka hat: modül → (şerit −0,13) → Y ayırıcı → her yanda dıştaki lambaya (içtekiler hattaki T'den) ---
    const R0 = port('rear', zR);
    const ySplit = R0.x + 0.3;
    if (rearLamps.length) {
      plug('roundPlug', R0, fromModule);
      plug('ysplit', V(ySplit, Y, zR), V(1, 0, 0));
      wire('rear', 0.014, [R0, V(ySplit - 0.045, Y, zR)], B.stop | B.plate | B.arm, 2);
    }
    for (const s of [1, -1]) {
      const mine = rearLamps.filter((r) => r.s === s).sort((p, q) => q.z - p.z);
      if (!mine.length) continue;
      const lane = zR + s * 0.035;
      const o = mine[0];
      wire(
        'rear',
        0.013,
        [V(ySplit + 0.06, Y, zR + s * 0.032), V(xDrop - 0.06, Y, lane), ...lateral(xDrop, Y, lane, s * o.z), V(xDrop, ly, s * o.z), V(rx - 0.075, ly, s * o.z)],
        B.stop | B.plate | B.arm,
        2,
      );
      for (const r of mine.slice(1)) {
        // içteki lambalar (LUNA): hattın yanal kısmındaki T bağlantıdan iner
        plug('tee', V(xDrop, Y, s * r.z), V(0, 0, s), V(0, -1, 0));
        wire('rear', 0.011, [V(xDrop, Y - 0.02, s * r.z), V(xDrop, ly, s * r.z), V(rx - 0.075, ly, s * r.z)], B.stop, 3);
      }
    }

    // --- yan hatlar (2×0,5): modülün arka yüzünden önce arkaya, yana ve öne; markerlar T bağlantıdan 0,6 m dalla ---
    if (needSide) {
      const xFront = fr.qty > 0 ? F.x + 0.45 : Math.min(...sideXs, ar.qty >= 4 ? AF.x : 0) - 0.15;
      for (const s of [1, -1]) {
        const pz = s > 0 ? zS1 : zS3;
        const P = port('rear', pz);
        plug('ssPlug', P, fromModule);
        // sağ yan hat (−z) 7×1 şeridinin üstünden geçer
        wire('side', 0.01, [P, ...lateral(xb, Y, pz, s * busZ, s < 0 ? rearLanes : []), V(xFront, Y, s * busZ)], B.side | B.front | (ar.qty >= 4 ? B.arm : 0), 2);
        const zp = s * (sideZ - 0.03);
        for (const x of sideXs) {
          const y = markerY(x);
          plug('tee', V(x, Y, s * busZ), V(-1, 0, 0), V(0, 0, s));
          wire('side', 0.007, [V(x, Y, s * (busZ + 0.03)), V(x, Y, zp), V(x, y, zp), V(x, y, s * (sideZ + 0.005))], B.side, 3);
        }
        if (fr.qty > 0) {
          // ön pozisyon: hattın ucundaki Superseal'den kısa dal
          const fz = s * (F.z - 0.02);
          wire('marker', 0.008, [V(xFront, Y, s * busZ), V(F.x + 0.12, Y, s * busZ), V(F.x + 0.12, Y, fz), V(F.x + 0.12, F.y, fz), V(F.x + 0.03, F.y, fz)], B.front, 3, { d: 0.05, fromEnd: false, type: 'ss' });
        }
        if (ar.qty >= 4) {
          const wz = AF.wallZ ?? AF.z;
          plug('tee', V(AF.x + 0.05, Y, s * busZ), V(-1, 0, 0), V(0, 0, s));
          wire('marker', 0.008, [V(AF.x + 0.05, Y, s * (busZ + 0.03)), V(AF.x + 0.05, Y, s * (wz - 0.04)), V(AF.x + 0.05, AF.y, s * (wz - 0.04)), V(AF.x, AF.y, s * (wz - 0.01))], B.arm, 3);
        }
      }
    }

    // --- plaka (1,5 m) ve arka lastik kol: arka lambanın arkasındaki Superseal'den ---
    for (const s of [1, -1]) {
      const mine = rearLamps.filter((r) => r.s === s);
      const outer = [...mine].sort((p, q) => q.z - p.z)[0];
      const inner = [...mine].sort((p, q) => p.z - q.z)[0];
      const myPlates = plateSpots.filter((sp) => (sp.entry.z < 0 ? -1 : 1) === s || (plateSpots.length === 1 && s === 1));
      for (const sp of myPlates) {
        const z = sp.entry.z;
        if (inner) {
          const from = ssIn(inner);
          const xl = rx - 0.06;
          wire('plate', 0.008, [from, V(xl, from.y, from.z), V(xl, from.y, z), V(xl, sp.entry.y, z), sp.entry.clone()], B.plate, 3);
        } else {
          // arka lamba yoksa plaka modülün 7×1 çıkışından
          plug('roundPlug', R0, fromModule);
          wire('plate', 0.008, [R0, V(xDrop, Y, R0.z), V(xDrop, Y, z), V(xDrop, sp.entry.y, z), sp.entry.clone()], B.plate, 1);
        }
      }
      if (ar.qty >= 2 && outer) {
        const from = ssOut(outer);
        const mp = armMount[s];
        if (mp) {
          // lambaya takılı kol (LZD 3194 + LDCC 2698): lambanın arkasından kolun plakasına kısa kablo
          wire('marker', 0.006, [from, V(from.x - 0.012, from.y, from.z), V(from.x - 0.012, mp.y, mp.z - s * 0.008)], B.arm, 3);
        } else {
          const wz = AR.wallZ ?? AR.z;
          const xb = Math.min(AR.x, rx) - 0.08;
          wire('marker', 0.008, [from, V(xb, from.y, from.z), V(xb, from.y, s * (wz - 0.04)), V(xb, AR.y, s * (wz - 0.04)), V(AR.x, AR.y, s * (wz - 0.01))], B.arm, 3);
        }
      }
    }

    // --- çalışma lambaları (HOR-1001'den): modülün arka yüzündeki orta Superseal'den tek hat arkaya; 7×1'in yanal kolunun
    // önünde (kesişmeden) iner, lamba taşıyıcının içine girer, içeride ikiye ayrılıp stop ile plaka arasındaki lambalara ---
    const yIn = ly + 0.1; // taşıyıcının içindeki yanal koşu (7×1 inişlerinden yüksekte, kutunun tavanının altında)
    const inCarrier = workSpots.filter((sp) => sp.between);
    if (inCarrier.length) {
      const P = port('rear', zS2);
      plug('ssPlug', P, fromModule);
      const xw = xDrop - 0.075;
      wire('aux', 0.009, [P, V(xw, Y, zS2), V(xw, yIn, zS2), V(xDrop, yIn, zS2)], B.work, 2);
      for (const sp of inCarrier) wire('aux', 0.008, [V(xDrop, yIn, zS2), V(xDrop, yIn, sp.z), V(xDrop, sp.y, sp.z), V(rx - 0.03, sp.y, sp.z)], B.work, 3);
    }
    // yüksekteki çalışma / tepe lambası (başlık üstü): aynı porttan yan hatla arka hat arasında yana, arka köşe dikmesi boyunca
    // yukarı; tepe lambası çalışma hattından biraz içeride
    const auxRoute = (sp: P3, cat: 'work' | 'beacon', k: number) => {
      const s = sp.z >= 0 ? 1 : -1;
      if (sp.x < -a.L / 2) {
        // öndeki (başlık üstü) lamba: modülün ön yüzündeki Superseal'den (sol +z, sağ −z en sağdaki küçük port) öne; sağdaki ana
        // beslemenin altından geçer, yan hattın içinde (traverslerin üstünde) öne gider, başlığın arkasında yükselir
        const pz = s > 0 ? zS1 : zS3;
        const P = port('front', pz);
        plug('ssPlug', P, toModule);
        const x1 = P.x - 0.25;
        const lane = s * (show ? busZ - 0.45 : tz - 0.1); // gizli güzergâhta kirişlerin arasında
        const xr = sp.x + 0.06;
        const top = sp.y - 0.04;
        wire('aux', 0.008, [P, ...lateral(x1, Y, pz, lane, s < 0 ? [zR] : [], -1), V(xr, Y, lane), V(xr, top, lane), V(xr, top, sp.z), V(sp.x + 0.03, sp.y + 0.005, sp.z)], B[cat], 2, { ...toLamp, type: 'ss' });
        return;
      }
      const P = port('rear', zS2);
      plug('ssPlug', P, fromModule);
      const xa = (xb + xDrop) / 2;
      const cx = Math.min(sp.x, rx) - 0.04 - k * 0.03;
      const cz = s * (W2 - 0.05 - k * 0.035);
      const top = sp.y > lvl(sp.x) + 0.6 ? sp.y - 0.04 : sp.y + 0.04;
      wire('aux', 0.008, [P, V(xa, Y, zS2), ...lateral(xa, Y, zS2, cz, s < 0 ? rearLanes : []), V(cx, Y, cz), V(cx, top, cz), V(cx, top, sp.z), V(sp.x - 0.01, top, sp.z)], B[cat], 2, { ...toLamp, type: 'ss' });
    };
    workSpots.filter((sp) => !sp.between).forEach((sp) => auxRoute(sp, 'work', 0));
    beaconSpots.forEach((sp) => auxRoute(sp, 'beacon', 1));

    out.add(drawHarness(ws.map((w) => ({ ...w, pts: level(w.pts) })), cn.map((q) => ({ ...q, pos: lift(q.pos) })), mats, { sheath: !show, pickers: show }));
    return out;
  }

  // =========================== ESKİ ŞEMA: SOKET → ANA HAT ===========================
  // soket → 0,5 m kablo → konnektör → 16,5 m ana hat (kirişlerin arası) → modül
  kinds.forEach((_, i) => {
    const z = socketZ(i);
    const zz = zMain + (i - (kinds.length - 1) / 2) * 0.03;
    const lead = [V(a.socket.x + 0.02, a.socket.y, z), V(fx, a.socket.y, z), V(fx, hy, z), V(fx + 0.5, hy, zz)];
    wires.push({ kind: 'main', r: 0.012, pts: lead });
    conns.push({ type: 'round', pos: V(fx + 0.5, hyAt(fx + 0.5), zz), dir: V(1, 0, 0) });
    wires.push({ kind: 'main', r: 0.014, pts: [V(fx + 0.5, hy, zz), V(xm - 0.75, hy, zz), V(xm - 0.75, hy, 0.36), V(xm + PORTS[0], hy, 0.36), V(xm + PORTS[0], hy, zPort)] });
  });
  // arka lambalara 7×1 dallar (arka dağıtımdan) ve AMP 7 pin fişler
  for (const r of rearLamps) {
    const { s, z } = r;
    const rd = M.harness?.rearDrop;
    // AMP 7 pin fiş lambanın arkasında (gövdesi lambanın / taşıyıcının içinde kalır)
    conns.push({ type: 'amp', pos: V(rx - 0.02, ly, s * z), dir: V(1, 0, 0) });
    wires.push({
      kind: 'rear',
      r: 0.011,
      // rearDrop: dikmenin arkasında iner, bar kolunun ve barın içinden lambaya (arkadan görünmez)
      pts: rd
        ? [V(xd, hy, s * rd.z), V(xd, ly, s * rd.z), V(rd.innerX, ly, s * rd.z), V(rd.innerX, ly, s * z), V(rx - 0.075, ly, s * z)]
        : [V(xd, hy, s * z), V(xd, ly, s * z), V(rx - 0.075, ly, s * z)],
    });
  }
  // çalışma/tepe lambaları için ayrı 2×1 besleme (HOR-1001 şeması)
  if (aux) {
    wires.push({ kind: 'aux', r: 0.011, pts: [V(a.socket.x + 0.02, a.socket.y - 0.05, -0.02), V(fx, a.socket.y - 0.05, -0.02), V(fx, hy, -0.02), V(xm - 0.75, hy, -0.02), V(xm - 0.75, hy, -0.36), V(xm + PORTS[0], hy, -0.36), V(xm + PORTS[0], hy, -zPort)] });
  }

  // =========================== MODÜL → ARKA HATLAR (2 × 7×1 2,5 m) ===========================
  for (const s of [1, -1]) {
    const mine = rearLamps.filter((r) => r.s === s);
    const xp = xm + PORTS[1];
    if (!mine.length) continue;
    const zs = mine.map((r) => r.z);
    const zo = Math.max(...zs);
    const zi = Math.min(...zs);
    // 7×1 hat: modülden arka dağıtıma, orada dıştaki lambaya; birden çok lamba varsa dağıtım boyunca
    const line = [V(xp, hy, s * zPort), V(xp, hy, s * zr), V(xd, hy, s * zr)];
    wires.push({ kind: 'rear', r: 0.013, pts: line, conn: { d: Math.abs(xd - xp) * 0.5, fromEnd: false } });
    const rdz = M.harness?.rearDrop?.z;
    const lo = rdz !== undefined ? Math.min(rdz, zr) : Math.min(zi, zr);
    const hi = rdz !== undefined ? Math.max(rdz, zr) : Math.max(zo, zr);
    if (hi - lo > 1e-3) wires.push({ kind: 'rear', r: 0.012, pts: [V(xd, hy, s * lo), V(xd, hy, s * hi)] });
  }

  // =========================== ARKA LAMBADAN: YAN HAT, PLAKA, ARKA KOL ===========================
  // Superseal çıkışı: arka lambanın arkasında, dış ucuna yakın
  const supersealOf = (r: { s: number; z: number; hw: number }) => V(rx - 0.035, ly - 0.03, r.s * (r.z + r.hw * 0.6));
  const frontEndX = Math.min(...[fr.qty > 0 ? F.x + 0.12 : 0, ar.qty >= 4 ? AF.x : 0, sideXs.length ? sideXs[0] : 0]);
  for (const s of [1, -1]) {
    const outer = rearLamps.filter((r) => r.s === s).sort((p, q) => q.z - p.z)[0];
    const inner = rearLamps.filter((r) => r.s === s).sort((p, q) => p.z - q.z)[0];
    // --- yan hat (2×0,5): lambadan içe ve aşağı → yan güzergâh → öne ---
    const needSide = sideXs.length > 0 || fr.qty > 0 || ar.qty >= 4;
    const RL = S?.rail;
    if (needSide && RL) {
      // Ray/raf içi yan hat: tek düz hat rayın iç yüzünde öne gider, markerlara ve ön kola kısa düz uç; dışarıda dal yok.
      const rz = s * RL.z;
      const ryAt = (x: number) => profileAt(RL.y, x);
      const [xr, riseZ] = RL.rise;
      // yükselişin sonu: bend varsa (ör. kasa tabanının altı) onu izler, yoksa doğrudan raya
      const climb = (cz: number) =>
        RL.bend?.length
          ? [...RL.bend.map(([bz, by]) => V(xr, by, s * bz)), V(xr, ryAt(xr), rz)]
          : [V(xr, ryAt(xr), cz), V(xr, ryAt(xr), rz)];
      let start: THREE.Vector3[];
      if (outer) {
        const ss = supersealOf(outer);
        conns.push({ type: 'ss', pos: ss.clone().add(V(-0.03, 0, 0)), dir: V(-1, 0, 0) });
        const cz = riseZ != null ? s * riseZ : ss.z;
        // pass: lamba hizasında öne giderken engelin (çamurluk paçası) iç yanından geçilecek |z|
        const via = RL.pass != null ? [V(ss.x, ss.y, s * RL.pass), V(xr, ss.y, s * RL.pass)] : [V(xr, ss.y, ss.z)];
        start = [ss, ...via, V(xr, ss.y, cz), ...climb(cz)];
      } else {
        const cz = riseZ != null ? s * riseZ : s * tz;
        start = [V(xm + PORTS[2], hy, s * zPort), V(xm + PORTS[2], hy, s * tz), V(xr, hy, s * tz), V(xr, hy, cz), ...climb(cz)];
      }
      const ex = RL.exit;
      const viaChassis = !!RL.frontFromChassis;
      const armOnRail = ar.qty >= 4 && !viaChassis;
      const xEnd = Math.min(...sideXs, armOnRail ? AF.x : 0, fr.qty > 0 && ex && !viaChassis ? ex[0] : 0, xr);
      const run = RL.y.map((p) => p[0]).filter((x) => x < xr - 1e-6 && x > xEnd + 1e-6).sort((p, q) => q - p);
      wires.push({ kind: 'side', r: 0.010, pts: dedupe([...start, ...run.map((x) => V(x, ryAt(x), rz)), V(xEnd, ryAt(xEnd), rz)]) });
      for (const x of sideXs) {
        const y = markerY(x);
        wires.push({ kind: 'side', r: 0.007, conn: toLamp, pts: dedupe([V(x, ryAt(x), rz), V(x, y, rz), V(x, y, s * (sideZ + 0.005))]) });
      }
      if (armOnRail) {
        const wz = AF.wallZ ?? AF.z;
        wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: dedupe([V(AF.x, ryAt(AF.x), rz), V(AF.x, AF.y, rz), V(AF.x, AF.y, s * (wz - 0.01))]) });
      }
      if (viaChassis && (fr.qty > 0 || ar.qty >= 4)) {
        // ön pozisyon ve ön kol: modülün yedek portundan kiriş içinden öne (kasa devrilir, kasadaki hatla bağlanmaz)
        const fx = Math.min(fr.qty > 0 ? F.x + 0.12 : 0, ar.qty >= 4 ? AF.x + 0.05 : 0);
        wires.push({ kind: 'side', r: 0.010, pts: [V(xm + PORTS[2], hy, s * zPort), V(xm + PORTS[2], hy, s * tz), V(fx, hy, s * tz)] });
        if (fr.qty > 0) {
          const fz = s * (F.z - 0.02);
          wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: [V(F.x + 0.5, hy, s * tz), V(F.x + 0.12, hy, s * tz), V(F.x + 0.12, hy, fz), V(F.x + 0.12, F.y, fz), V(F.x + 0.03, F.y, fz)] });
        }
        if (ar.qty >= 4) {
          const wz = AF.wallZ ?? AF.z;
          wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: [V(AF.x + 0.5, hy, s * tz), V(AF.x + 0.05, hy, s * tz), V(AF.x + 0.05, hy, s * (wz - 0.04)), V(AF.x + 0.05, AF.y, s * (wz - 0.04)), V(AF.x, AF.y, s * (wz - 0.01))] });
        }
      }
      // ön pozisyon: raydan kol boyunca kirişin dışına, kirişin içinden ana güzergâha (hy, tz) ve öne
      if (fr.qty > 0 && ex && !viaChassis) {
        const [exX, exY] = ex;
        const zo = s * (tz + 0.18);
        const fz = s * (F.z - 0.02);
        wires.push({
          kind: 'marker',
          r: 0.008,
          conn: toLamp,
          pts: dedupe([V(exX, ryAt(exX), rz), V(exX, exY, rz), V(exX, exY, zo), V(exX, hy, zo), V(exX, hy, s * tz), V(F.x + 0.12, hy, s * tz), V(F.x + 0.12, hy, fz), V(F.x + 0.12, F.y, fz), V(F.x + 0.03, F.y, fz)]),
        });
      }
    } else if (needSide) {
      const xs = xd - 0.18;
      let start: THREE.Vector3[];
      if (outer) {
        const ss = supersealOf(outer);
        conns.push({ type: 'ss', pos: ss.clone().add(V(-0.03, 0, 0)), dir: V(-1, 0, 0) });
        start = [ss, V(xs, ss.y, ss.z), V(xs, hy, ss.z), V(xs, hy, s * tz)];
      } else {
        // arka lamba yoksa yan hat modülün yedek portundan
        start = [V(xm + PORTS[2], hy, s * zPort), V(xm + PORTS[2], hy, s * tz)];
      }
      const xEnd = Math.min(frontEndX, ...sideXs) - 0.0;
      const trunk = [...start, V(Math.min(xEnd, start[start.length - 1].x), hy, s * tz)];
      wires.push({ kind: 'side', r: 0.010, pts: trunk });
      // markerlar: 0,6 m dal
      for (const x of sideXs) {
        const y = markerY(x);
        const zl = s * (sideZ - 0.03);
        wires.push({ kind: 'side', r: 0.007, conn: toLamp, pts: [V(x + 0.14, hy, s * tz), V(x, hy, s * tz), V(x, hy, zl), V(x, y, zl), V(x, y, s * (sideZ + 0.005))] });
      }
      // ön pozisyon: hattın ucunda
      if (fr.qty > 0) {
        const fz = s * (F.z - 0.02);
        wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: [V(F.x + 0.5, hy, s * tz), V(F.x + 0.12, hy, s * tz), V(F.x + 0.12, hy, fz), V(F.x + 0.12, F.y, fz), V(F.x + 0.03, F.y, fz)] });
      }
      if (ar.qty >= 4) {
        const wz = AF.wallZ ?? AF.z;
        wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: [V(AF.x + 0.5, hy, s * tz), V(AF.x + 0.05, hy, s * tz), V(AF.x + 0.05, hy, s * (wz - 0.04)), V(AF.x + 0.05, AF.y, s * (wz - 0.04)), V(AF.x, AF.y, s * (wz - 0.01))] });
      }
    }
    // --- plaka (1,5 m): içteki lambanın Superseal'inden ---
    const myPlates = plateSpots.filter((sp) => (sp.entry.z < 0 ? -1 : 1) === s || (plateSpots.length === 1 && s === 1));
    for (const sp of myPlates) {
      const from = inner ? V(rx - 0.035, ly - 0.03, s * (inner.z - inner.hw * 0.6)) : V(xm + PORTS[2], hy, s * zPort);
      const xb = rx - 0.06;
      const z = sp.entry.z;
      wires.push({ kind: 'plate', r: 0.008, conn: toLamp, pts: [from, V(xb, from.y, from.z), V(xb, from.y, z), V(xb, sp.entry.y, z), sp.entry.clone()] });
    }
    // --- arka lastik kol: dıştaki lambanın Superseal'inden ---
    if (ar.qty >= 2 && armMount[s] && outer) {
      // lambaya takılı kol: kablosu lambanın Superseal'inden plakaya (kısa, lambanın arkasında)
      const from = supersealOf(outer);
      const mp = armMount[s];
      wires.push({ kind: 'marker', r: 0.006, conn: toLamp, pts: [from, V(from.x - 0.012, from.y, from.z), V(from.x - 0.012, mp.y, mp.z - s * 0.008)] });
    } else if (ar.qty >= 2) {
      const wz = AR.wallZ ?? AR.z;
      const from = outer ? supersealOf(outer) : V(xd, hy, s * zr);
      const xb = Math.min(AR.x, rx) - 0.08;
      wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: [from, V(xb, from.y, from.z), V(xb, from.y, s * (wz - 0.04)), V(xb, AR.y, s * (wz - 0.04)), V(AR.x, AR.y, s * (wz - 0.01))] });
    }
  }

  // =========================== ÇALIŞMA / TEPE KABLOLARI (modül yedek portları) ===========================
  const auxTo = (sp: P3 & { rise?: number[] }, k: number) => {
    const s = sp.z >= 0 ? 1 : -1;
    const xp = xm + PORTS[2 + (k % 2)];
    const zc = s * 0.2;
    const start = [V(xp, hy, s * zPort), V(xp, hy, zc)];
    if (sp.rise && sp.rise[2] != null) {
      // alçak geçiş: x'te y seviyesine iner, o seviyede yana ve lambanın altına gider (kiriş altı, levhanın arkası)
      const [cx, rz, ry] = sp.rise;
      const zd = s * Math.min(rz, 0.36); // iniş: lamba levhasının (z ≥ 0,30) arkasında, kirişlerin arasında
      wires.push({
        kind: 'aux',
        r: 0.008,
        conn: toLamp,
        pts: dedupe([...start, V(cx, hy, zc), V(cx, hy, zd), V(cx, ry, zd), V(cx, ry, s * rz), V(sp.x - 0.04, ry, sp.z), V(sp.x - 0.04, sp.y + 0.01, sp.z), V(sp.x - 0.005, sp.y + 0.01, sp.z)]),
      });
      return;
    }
    if (sp.rise) {
      // belirli dikey güzergâh (dar kulenin içi, travers önü): oradan yükselir, lambanın arkasına girer
      const [cx, rz] = sp.rise;
      const cz = s * rz;
      const top = sp.y > hy + 0.6 ? sp.y - 0.04 : sp.y + 0.04;
      const end = sp.y > hy + 0.6 ? V(sp.x - 0.01, sp.y + 0.005, sp.z) : V(sp.x - 0.02, top, sp.z);
      wires.push({ kind: 'aux', r: 0.008, conn: toLamp, pts: dedupe([...start, V(cx, hy, zc), V(cx, hy, cz), V(cx, top, cz), V(cx, top, sp.z), end]) });
      return;
    }
    if (sp.y > hy + 0.6) {
      // yüksekteki lamba (kasa/başlık üstü): kablo kapıdan ya da ön panelden geçmez, en yakın uçtaki KÖŞE DİKMESİNİ izler.
      // Arkada dikmenin içinden (kapı kanatları köşe dikmelerinin arasında), önde başlığın arkasından (önden görünmez).
      const rearEnd = sp.x > -a.L / 2;
      const cx = rearEnd ? Math.min(sp.x, rx) - 0.04 : sp.x + 0.09;
      const cz = s * (W2 - 0.05);
      const top = sp.y - 0.04;
      wires.push({ kind: 'aux', r: 0.008, conn: toLamp, pts: [...start, V(cx, hy, zc), V(cx, hy, cz), V(cx, top, cz), V(cx, top, sp.z), V(sp.x - 0.01, sp.y + 0.005, sp.z)] });
      return;
    }
    // alçaktaki lamba (ör. lowbed arka travers): arka dağıtımın arkasından yukarı, lambanın arkasına
    wires.push({ kind: 'aux', r: 0.008, conn: toLamp, pts: [...start, V(Math.max(sp.x - 0.15, xp), hy, zc), V(sp.x - 0.15, hy, sp.z), V(sp.x - 0.15, sp.y + 0.04, sp.z), V(sp.x - 0.02, sp.y + 0.04, sp.z)] });
  };
  workSpots.forEach((sp) => auxTo(sp, 0));
  beaconSpots.forEach((sp) => auxTo(sp, 1));

  // =========================== MODÜL ===========================
  const mod = controlModule(mats);
  const my = hyAt(xm);
  mod.position.set(xm, my, 0);
  harness.add(mod);
  // yalnız kullanılan portlara fiş (boş port boş kalır): besleme ve arka hat her zaman, yedekler yalnız o lamba seçiliyse
  const used = [0, 1, ...(wk.qty > 0 ? [2] : []), ...(bc.qty > 0 ? [3] : [])];
  for (const s of [1, -1]) for (const i of used) conns.push({ type: 'ssPlug', pos: V(xm + PORTS[i], my, s * (zPort + 0.012)), dir: V(0, 0, -s) });
  harness.add(drawHarness(wires.map((w) => ({ ...w, pts: follow(w.pts) })), conns, mats, { pickers: true }));

  addBrackets();
  return { group, harness, lampsByCat, placeholders, plate: { pos: platePos, light: plateLight } };
}

/** Hangi lamba modelleri gerekiyor (Engine kurmadan önce yükler) */
export function lampIds(c: Config): string[] {
  const ids = new Set<string>();
  for (const cat of CATEGORIES) {
    const ch = c.lamps[cat.id];
    if (ch.qty > 0) for (const id of productById(cat.id, ch.product).set ?? [productById(cat.id, ch.product).id]) ids.add(id);
  }
  const frame = rulesFor(c.trailer).plateFrame;
  if (frame) ids.add(frame);
  return [...ids];
}

/** Tesisat görünümü aç/kapa: yeni şemada iki güzergâh grubu arasında geçiş, eski şemada kablo malzemesi değişimi */
export function setHarnessHighlight(h: THREE.Group, mats: Mats, on: boolean) {
  const views = h.userData.views as { hidden: THREE.Object3D; shown: THREE.Object3D } | undefined;
  if (views) {
    views.hidden.visible = !on;
    views.shown.visible = on;
    return;
  }
  h.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (!mm.isMesh || !o.userData.kind) return;
    mm.material = on ? wireMat(mats, o.userData.kind as WireKind) : mats.wire.sheath;
  });
}

export function disposeEquipment(g: THREE.Object3D) {
  g.traverse((o) => {
    if ((o as THREE.Sprite).isSprite) return; // hale malzemeleri paylaşılır
    const mm = o as THREE.Mesh;
    if (o.userData.lamp) return; // lamba klonlarının geometrisi modelle paylaşılır
    if (mm.geometry && !isShared(mm.geometry)) mm.geometry.dispose();
    if ((o as THREE.InstancedMesh).isInstancedMesh) (o as THREE.InstancedMesh).dispose();
  });
}

export const ALL_CATEGORIES = CATEGORIES.map((c) => c.id);
