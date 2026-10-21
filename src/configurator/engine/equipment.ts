// Lambalar, soketler, montaj braketleri ve tesisat. Seçimler değiştikçe bu grup baştan kurulur.
// Lambalar gerçek ürünlerin Blender modelleridir (lampfx.ts → lamp-<id>.glb); yüklenene kadar sade bir yer tutucu görünür.
//
// Tesisat düzeni yeni Horpol şemasına göre (vault: Kablolama ve Işıklandırma/Kablolama Şeması - Yeni):
//   ön soket → 0,5 m kablo → konnektör → 16,5 m ana hat → Horpol modülü (arkada, kirişlerin arasında)
//   modül → 2 × 7×1 2,5 m arka hat → arka lambaların AMP 7 pin fişi
//   arka lambanın Superseal soketlerinden: yan hat 2×0,5 (öne doğru; yan markerlar 0,6 m dallarla, ucunda ön pozisyon),
//   plaka lambası (1,5 m), arka lastik kol. Ön lastik kollar yan hattın ön ucundan.
//   Çalışma ve tepe lambaları (HOR-1001 şeması): modülün boş portlarından; ayrı 2×1 besleme hattı soketten modüle.
// Montaj noktaları dorse betiğinin yazdığı `mounts` (R48 haritası) varsa ondan, yoksa eski bağlantı noktalarından.
import * as THREE from 'three';
import { CATEGORIES, productById, rulesFor, type CategoryId, type Config } from '../data';
import type { Mats } from './materials';
import { profileAt, type Anchors } from './trailer';
import { isShared, markShared } from './geo';
import { emitterSpots, lampInstance, type LampFn } from './lampfx';
import type { PlateLight } from './plateLight';

/** Yanınca görünen ışık efekti: lens önünde hale (sprite) ya da zemine düşen renkli ışık (pool) */
export interface Glow {
  sprite: THREE.Object3D;
  fn: LampFn;
}
/** Sahnedeki gerçek ışıkların yerleşimi (Engine sabit sayıda ışığı buraya taşır: gölgelendirici yeniden derlenmez) */
export interface LampLightAnchors {
  rear: THREE.Vector3[];
  work: { pos: THREE.Vector3; dir: THREE.Vector3 }[];
}
export interface EquipmentBuild {
  group: THREE.Group;
  glows: Glow[];
  harness: THREE.Group;
  lampsByCat: Record<CategoryId, THREE.Object3D[]>;
  lights: LampLightAnchors;
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
  armFront?: P3 & { wallZ?: number; bracket?: Bracket };
  /** rise: kablonun dikey çıktığı [x, |z|, yanal geçiş y?] (dar kule/travers önü gibi; yoksa en yakın köşe) */
  work?: (P3 & { dir?: [number, number, number]; bracket?: Bracket; rise?: number[] })[];
  beacon?: (P3 & { bracket?: Bracket; rise?: number[] })[];
  harness?: {
    trunkY?: number;
    trunkZ?: number;
    profile?: [number, number][];
    moduleX?: number;
    rearJunctionX?: number;
    /** arka 7×1 hattın lamba barına indiği yer (|z|) ve barın içinde yanal gittiği x: arkadan bakınca dikme kabloyu örter */
    rearDrop?: { z: number; innerX: number };
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

// ---------- soketler ----------
function socket(mats: Mats, kind: '7' | '15', ccolor: THREE.Material) {
  const g = new THREE.Group();
  g.add(m(new THREE.BoxGeometry(0.11, 0.11, 0.012), mats.darkMetal));
  const body = m(new THREE.CylinderGeometry(kind === '15' ? 0.042 : 0.038, 0.045, 0.06, 24), ccolor);
  body.rotation.x = Math.PI / 2;
  body.position.z = 0.035;
  g.add(body);
  const lid = m(new THREE.CylinderGeometry(0.047, 0.047, 0.012, 24), ccolor);
  lid.rotation.x = Math.PI / 2 - 0.5;
  lid.position.set(0, 0.03, 0.07);
  g.add(lid);
  return g;
}

// ---------- tesisat ----------
// Kablo türleri (tesisat görünümündeki renk kodu; eğitsel görselleştirme, gerçek kablo renkleri değildir):
// main = soket→modül ana hat, rear = modül→arka lamba 7×1, side = 2×0,5 yan hat, plate = plaka, marker = ön/kontur dalları, aux = çalışma/tepe
type WireKind = 'main' | 'side' | 'rear' | 'plate' | 'marker' | 'aux';
const WIRE_SCALE = 1.7;
const BEND = 0.14;
const RIBS_PER_M = 75;
const CLIP_STEP = 0.5;
const CONN_FROM_LAMP = 0.3;

function rounded(pts: THREE.Vector3[], r = BEND) {
  const out: THREE.Vector3[] = [pts[0].clone()];
  const n = pts.length;
  for (let i = 1; i < n - 1; i++) {
    const p = pts[i];
    const da = pts[i - 1].clone().sub(p);
    const db = pts[i + 1].clone().sub(p);
    const la = da.length();
    const lb = db.length();
    if (la < 1e-6 || lb < 1e-6 || da.dot(db) / (la * lb) < -0.999) {
      out.push(p.clone());
      continue;
    }
    const k = Math.min(r, i === 1 ? la : la / 2, i === n - 2 ? lb : lb / 2);
    const q = new THREE.QuadraticBezierCurve3(p.clone().addScaledVector(da, k / la), p.clone(), p.clone().addScaledVector(db, k / lb));
    for (let j = 0; j <= 8; j++) out.push(q.getPoint(j / 8));
  }
  out.push(pts[n - 1].clone());
  return out.filter((v, i) => i === 0 || v.distanceToSquared(out[i - 1]) > 1e-10);
}

class PolyCurve extends THREE.Curve<THREE.Vector3> {
  private p: THREE.Vector3[];
  constructor(p: THREE.Vector3[]) {
    super();
    this.p = p;
  }
  override getPoint(t: number, target = new THREE.Vector3()) {
    const f = Math.min(Math.max(t, 0), 1) * (this.p.length - 1);
    const i = Math.min(Math.floor(f), this.p.length - 2);
    return target.copy(this.p[i]).lerp(this.p[i + 1], f - i);
  }
  override getPointAt(u: number, target?: THREE.Vector3) {
    return this.getPoint(u, target);
  }
  override getTangentAt(u: number, target?: THREE.Vector3) {
    return this.getTangent(u, target);
  }
}

function along(pts: THREE.Vector3[], d: number, fromEnd: boolean) {
  const p = fromEnd ? [...pts].reverse() : pts;
  let rest = d;
  for (let i = 0; i < p.length - 1; i++) {
    const seg = p[i].distanceTo(p[i + 1]);
    if (seg >= rest || i === p.length - 2) {
      return { pos: p[i].clone().lerp(p[i + 1], Math.min(1, rest / seg)), dir: p[i + 1].clone().sub(p[i]).normalize() };
    }
    rest -= seg;
  }
  return { pos: p[0].clone(), dir: V(1, 0, 0) };
}
function pathLength(pts: THREE.Vector3[]) {
  let s = 0;
  for (let i = 1; i < pts.length; i++) s += pts[i].distanceTo(pts[i - 1]);
  return s;
}

/** Horpol kontrol modülü: siyah gövde, açık renk çerçeve ve bağlantı kulakları, üstte beyaz logo. Uzun kenarı dorse ekseninde. */
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

// ---------- yanan lamba efektleri ----------
/** hale boyu tavanı (m) */
const HALO_MAX: Record<CategoryId, number> = { stop: 0.7, side: 0.32, plate: 0.26, front: 0.36, arm: 0.34, work: 0.9, beacon: 0.75 };
/** zemine düşen ışığın boyu ve eni (m); plaka zemine düşmez */
// tepe lambası zemine düşmez (kullanıcı isteği 2026-10-20); plaka da düşmez
const POOL: Partial<Record<CategoryId, [number, number]>> = { stop: [3.2, 2.0], side: [1.2, 0.9], front: [1.8, 1.3], arm: [1.0, 0.8], work: [6.5, 4.2] };
const POOL_GEO = markShared(new THREE.PlaneGeometry(1, 1));
const haloMats = new Map<string, THREE.SpriteMaterial>();
function haloMaterial(mats: Mats, c: THREE.Color) {
  const k = c.getHexString();
  let m = haloMats.get(k);
  if (!m) {
    m = new THREE.SpriteMaterial({ map: mats.glow.white.map, color: c, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.95, toneMapped: false, fog: false });
    haloMats.set(k, m);
  }
  return m;
}
const poolMats = new Map<string, THREE.MeshBasicMaterial>();
let poolTex: THREE.CanvasTexture | null = null;
function poolTexture() {
  if (poolTex) return poolTex;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d')!;
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.55)');
  g.addColorStop(0.7, 'rgba(255,255,255,0.15)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  poolTex = new THREE.CanvasTexture(c);
  return poolTex;
}
function poolMaterial(c: THREE.Color, cat: CategoryId) {
  const k = `${c.getHexString()}|${cat}`;
  let m = poolMats.get(k);
  if (!m) {
    const op = cat === 'work' ? 0.7 : cat === 'stop' ? 0.5 : 0.42;
    m = new THREE.MeshBasicMaterial({ map: poolTexture(), color: c, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: op, toneMapped: false, fog: false, polygonOffset: true, polygonOffsetFactor: -2 });
    poolMats.set(k, m);
  }
  return m;
}

/** Arka lambaların genişliği (lamba yerel X), dizilim için: modelden ölçülür, yoksa ürüne göre tahmin */
/** Eski hale/zemin ışığı sprite'ları (bloom öncesi). Kapalı: yansıma efektleri yanıltmasın (kullanıcı, 2026-10-20) */
const GLOW_SPRITES = false;
const LAMP_W: Record<string, number> = { lzd3194: 0.405, lzd2856: 0.451, lzd2423: 0.155, lzd2448: 0.145, lzd2877: 0.115, lzd2880: 0.115 };

export function buildEquipment(c: Config, a: Anchors, mats: Mats): EquipmentBuild {
  const group = new THREE.Group();
  const harness = new THREE.Group();
  group.add(harness);
  const glows: Glow[] = [];
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
    if (inst) glowLater.push(obj);
    return obj;
  };
  // parlamalar lambalar son yerlerine oturduktan sonra (arka lambalar kurulduktan sonra kaydırılır)
  const glowLater: THREE.Object3D[] = [];
  const makeGlows = () => {
    // hale ve zemin ışığı sprite'ları kapalı (2026-10-20): ışıma artık Engine'deki bloom ile yanan parçanın kendi biçiminden gelir
    if (!GLOW_SPRITES) return;
    for (const obj of glowLater) {
      const cat = obj.userData.category as CategoryId;
      obj.updateMatrixWorld(true);
      const facing = V(0, 0, 1).applyQuaternion(obj.getWorldQuaternion(new THREE.Quaternion())).normalize();
      const pooled = new Set<string>();
      for (const sp of emitterSpots(obj)) {
        // 1) hale: lensin hemen önünde, ton eşlemesiz; yanınca lambanın çevresi parlar
        const halo = new THREE.Sprite(haloMaterial(mats, sp.color));
        halo.position.copy(sp.pos).addScaledVector(facing, 0.02);
        // bölünmüş büyük parça (neon kılavuz): küçük ve çok sayıda hale; paylaşılan kılavuzun pozisyon işlevi sönük
        const hs = sp.split ? Math.min(HALO_MAX[cat], Math.max(0.13, sp.size * 2.2)) : Math.min(HALO_MAX[cat], Math.max(0.16, sp.size * 2.4));
        halo.scale.setScalar(sp.weak ? hs * 0.55 : hs);
        halo.visible = false;
        halo.renderOrder = 10;
        group.add(halo);
        glows.push({ sprite: halo, fn: sp.fn });
        // 2) zemine düşen ışık: lamba başına renk + işlev için bir tane
        const key = `${sp.fn}|${sp.color.getHexString()}`;
        if (pooled.has(key) || !POOL[cat] || sp.weak) continue; // sönük pozisyon zemine ışık düşürmez
        pooled.add(key);
        // lastik kolun yüzleri farklı yönlere bakar: beyaz öne, kırmızı arkaya, turuncu yana
        let dir = facing.clone();
        if (cat === 'arm') dir = sp.color.r > 0.9 && sp.color.g > 0.9 ? V(-1, 0, 0) : sp.color.g < 0.2 ? V(1, 0, 0) : V(0, 0, Math.sign(sp.pos.z) || 1);
        const flat = V(dir.x, 0, dir.z);
        if (cat !== 'beacon' && flat.lengthSq() < 1e-4) flat.set(1, 0, 0);
        flat.normalize();
        const [len, wid] = POOL[cat]!;
        const pool = new THREE.Mesh(POOL_GEO, poolMaterial(sp.color, cat));
        const hgt = Math.max(0, sp.pos.y);
        // lamba yükseldikçe ışık zeminde uzağa düşer ve yayılır
        const reach = cat === 'beacon' ? 0 : cat === 'work' ? 3.2 : len * 0.42 + hgt * 0.35;
        pool.position.set(sp.pos.x + flat.x * reach, 0.013, sp.pos.z + flat.z * reach);
        pool.scale.set(len * (1 + hgt * 0.15), wid * (1 + hgt * 0.1), 1);
        pool.rotation.set(-Math.PI / 2, 0, cat === 'beacon' ? 0 : Math.atan2(-flat.z, flat.x));
        pool.visible = false;
        pool.renderOrder = 9;
        pool.userData.noEdge = true;
        group.add(pool);
        glows.push({ sprite: pool, fn: sp.fn });
      }
    }
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

  type Wire = { kind: WireKind; r: number; pts: THREE.Vector3[]; conn?: { d: number; fromEnd: boolean } };
  const wires: Wire[] = [];
  const toLamp = { d: CONN_FROM_LAMP, fromEnd: true };
  const conns: { pos: THREE.Vector3; dir: THREE.Vector3 }[] = [];
  const amps: { pos: THREE.Vector3; dir: THREE.Vector3 }[] = [];
  const clips: { pos: THREE.Vector3; dir: THREE.Vector3; r: number }[] = [];

  // =========================== ARKA LAMBALAR ===========================
  const stop = c.lamps.stop;
  const R = M.rear;
  const rx = R?.faceX ?? R?.x ?? a.rear.x;
  const ly = R?.y ?? a.rear.lampY;
  const zEdge = R ? R.zOuter : Math.min(W2 - 0.03, a.rear.lampZ[0] + (LAMP_W[stop.product] ?? 0.3) / 2);
  const perSide = Math.floor(stop.qty / 2);
  // her yan: dıştan içe dizilen lambalar [z merkezi, yarı genişlik]
  const rearLamps: { s: number; z: number; hw: number }[] = [];
  /** dıştaki arka lambanın lastik kol takma noktası (modelde MOUNT_arm varsa; ör. LZD 3194 MAVIC) */
  const armMount: Record<number, THREE.Vector3> = {};
  for (const s of [1, -1]) {
    let edge = zEdge;
    for (let k = 0; k < perSide; k++) {
      const o = mount('stop', stop.product, V(rx, ly, 0), (obj) => {
        obj.rotation.y = Math.PI / 2;
        if (s < 0) obj.scale.x = -1; // sağ lamba: ayna (LZD 3195 / 2857)
      });
      const w = lampWidth(stop.product, o);
      const z = edge - w / 2;
      o.position.z = s * z;
      rearLamps.push({ s, z, hw: w / 2 });
      const mp = k === 0 ? o.getObjectByName('MOUNT_arm') : undefined;
      if (mp) {
        o.updateMatrixWorld(true);
        armMount[s] = mp.getWorldPosition(V(0, 0, 0)); // grup ekseni (grup henüz sahnede değil, birim dönüşüm)
      }
      edge = z - w / 2 - 0.025;
      // AMP 7 pin fiş lambanın arkasında; 7×1 dalı arka dağıtımdan
      const back = V(rx - 0.05, ly, s * z);
      amps.push({ pos: back.clone().add(V(-0.02, 0, 0)), dir: V(1, 0, 0) });
      const rd = M.harness?.rearDrop;
      wires.push({
        kind: 'rear',
        r: 0.011,
        conn: undefined,
        // rearDrop: dikmenin arkasında iner, bar kolunun ve barın içinden lambaya (arkadan görünmez)
        pts: rd
          ? [V(xd, hy, s * rd.z), V(xd, ly, s * rd.z), V(rd.innerX, ly, s * rd.z), V(rd.innerX, ly, s * z), V(rx - 0.075, ly, s * z)]
          : [V(xd, hy, s * z), V(xd, ly, s * z), V(rx - 0.075, ly, s * z)],
      });
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
    for (let i = 0; i < per; i++) sideXs.push(per === 1 ? (sx0 + sx1) / 2 : sx0 + ((sx1 - sx0) * i) / (per - 1));
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
  const AR: P3 & { wallZ?: number; bracket?: Bracket } = M.armRear ?? a.armRear;
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
  const workSpots = (M.work ?? [{ x: a.extra.x, y: a.extra.y, z: a.extra.z0, dir: [1, -0.25, 0] as [number, number, number] }, { x: a.extra.x, y: a.extra.y, z: -a.extra.z0, dir: [1, -0.25, 0] as [number, number, number] }]).slice(0, wk.qty);
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

  // =========================== SOKETLER + ANA HAT ===========================
  // soket → 0,5 m kablo → konnektör → 16,5 m ana hat (kirişlerin arası) → modül
  const kinds: ('7' | '15')[] = c.socket === '7x2' ? ['7', '7'] : c.socket === '15' ? ['15'] : ['7', '15', '7'];
  const spacing = 0.15;
  const fx = a.harness.frontX;
  const aux = wk.qty + bc.qty > 0;
  kinds.forEach((k, i) => {
    const z = (i - (kinds.length - 1) / 2) * spacing;
    const so = socket(mats, k, k === '15' ? mats.socketGrey : i === 0 ? mats.socket : mats.socketGrey);
    so.rotation.y = -Math.PI / 2;
    so.position.set(a.socket.x, a.socket.y, z);
    so.traverse((o) => (o.userData.category = 'socket'));
    group.add(so);
    const zz = zMain + (i - (kinds.length - 1) / 2) * 0.03;
    const lead = [V(a.socket.x + 0.02, a.socket.y, z), V(fx, a.socket.y, z), V(fx, hy, z), V(fx + 0.5, hy, zz)];
    wires.push({ kind: 'main', r: 0.012, pts: lead });
    conns.push({ pos: V(fx + 0.5, hyAt(fx + 0.5), zz), dir: V(1, 0, 0) });
    wires.push({ kind: 'main', r: 0.014, pts: [V(fx + 0.5, hy, zz), V(xm - 0.75, hy, zz), V(xm - 0.75, hy, 0.36), V(xm + PORTS[0], hy, 0.36), V(xm + PORTS[0], hy, zPort)] });
  });
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
        conns.push({ pos: ss.clone().add(V(-0.03, 0, 0)), dir: V(-1, 0, 0) });
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
        conns.push({ pos: ss.clone().add(V(-0.03, 0, 0)), dir: V(-1, 0, 0) });
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
  for (const s of [1, -1]) for (const px of PORTS) conns.push({ pos: V(xm + px, my, s * (zPort + 0.03)), dir: V(0, 0, s) });

  // =========================== BRAKETLER (sabit montaj) ===========================
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

  makeGlows();

  // =========================== HATLARI ÇİZ ===========================
  for (const w of wires) {
    const pts = rounded(follow(w.pts));
    if (pts.length < 2) continue;
    const tg = new THREE.TubeGeometry(new PolyCurve(pts), pts.length - 1, w.r * WIRE_SCALE, 10, false);
    const uv = tg.attributes.uv as THREE.BufferAttribute;
    let acc = 0;
    for (let i = 0; i < pts.length; i++) {
      if (i > 0) acc += pts[i].distanceTo(pts[i - 1]);
      for (let j = 0; j <= 10; j++) uv.setX(i * 11 + j, acc * RIBS_PER_M);
    }
    uv.needsUpdate = true;
    const t = m(tg, wireMat(mats, w.kind), false);
    t.userData.kind = w.kind;
    harness.add(t);
    if (w.r >= 0.012) {
      for (let d = 0.35; d < acc - 0.3; d += CLIP_STEP) clips.push({ ...along(pts, d, false), r: w.r * WIRE_SCALE });
    }
    if (w.conn) {
      const len = pathLength(pts);
      const d = w.conn.d * 2 > len ? len / 2 : w.conn.d;
      conns.push(along(pts, d, w.conn.fromEnd));
    }
  }

  // --- kelepçeler ---
  if (clips.length) {
    const geo = new THREE.CylinderGeometry(1, 1, 0.024, 14, 1, true);
    const cm = new THREE.InstancedMesh(geo, mats.plastic, clips.length);
    const q = new THREE.Quaternion();
    const Y = V(0, 1, 0);
    const mtx = new THREE.Matrix4();
    clips.forEach((cl, i) => {
      q.setFromUnitVectors(Y, cl.dir);
      cm.setMatrixAt(i, mtx.compose(cl.pos, q, V(cl.r * 1.3, 1, cl.r * 1.3)));
    });
    harness.add(cm);
  }
  // --- konnektörler (Superseal / ara fiş): siyah-beyaz iki parça ---
  if (conns.length) {
    const geo = new THREE.BoxGeometry(0.04, 0.05, 0.05);
    const black = new THREE.InstancedMesh(geo, mats.plastic, conns.length);
    const white = new THREE.InstancedMesh(geo, mats.connWhite, conns.length);
    const q = new THREE.Quaternion();
    const X = V(1, 0, 0);
    const one = V(1, 1, 1);
    const mtx = new THREE.Matrix4();
    conns.forEach((cn, i) => {
      q.setFromUnitVectors(X, cn.dir);
      black.setMatrixAt(i, mtx.compose(cn.pos.clone().addScaledVector(cn.dir, -0.02), q, one));
      white.setMatrixAt(i, mtx.compose(cn.pos.clone().addScaledVector(cn.dir, 0.02), q, one));
    });
    harness.add(black, white);
  }
  // --- AMP 7 pin fişler (arka lamba arkası): yuvarlak, yeşil contalı ---
  if (amps.length) {
    const body = new THREE.CylinderGeometry(0.019, 0.019, 0.05, 20);
    body.rotateZ(Math.PI / 2);
    const seal = new THREE.CylinderGeometry(0.0205, 0.0205, 0.008, 20);
    seal.rotateZ(Math.PI / 2);
    const b = new THREE.InstancedMesh(body, mats.plastic, amps.length);
    const g = new THREE.InstancedMesh(seal, ampSealMat(), amps.length);
    const mtx = new THREE.Matrix4();
    amps.forEach((ap, i) => {
      b.setMatrixAt(i, mtx.makeTranslation(ap.pos.x, ap.pos.y, ap.pos.z));
      g.setMatrixAt(i, mtx.makeTranslation(ap.pos.x + 0.012, ap.pos.y, ap.pos.z));
    });
    harness.add(b, g);
  }

  const lights: LampLightAnchors = {
    rear: rearLamps.map((r) => V(rx + 0.25, ly, r.s * r.z)),
    work: lampsByCat.work.map((o) => ({ pos: o.position.clone(), dir: V(0, 0, 1).applyQuaternion(o.quaternion).normalize() })),
  };
  return { group, glows, harness, lampsByCat, lights, placeholders, plate: { pos: platePos, light: plateLight } };
}

let sealMat: THREE.MeshStandardMaterial | null = null;
function ampSealMat() {
  return (sealMat ??= new THREE.MeshStandardMaterial({ color: '#2e7d32', roughness: 0.5 }));
}
let auxWire: THREE.Material | null = null;
function wireMat(mats: Mats, kind: WireKind) {
  const w = mats.wire as Record<string, THREE.Material>;
  if (kind === 'aux') {
    // çalışma / tepe hatları: lejanttaki mor (diğer hatlarla aynı koruge dokusu)
    if (!auxWire) {
      const m = (mats.wire.marker as THREE.MeshStandardMaterial).clone();
      m.color.set('#a855f7');
      m.emissive.set('#a855f7');
      auxWire = m;
    }
    return auxWire;
  }
  return w[kind] ?? w.marker;
}

/** Hangi lamba modelleri gerekiyor (Engine kurmadan önce yükler) */
export function lampIds(c: Config): string[] {
  const ids = new Set<string>();
  for (const cat of CATEGORIES) {
    const ch = c.lamps[cat.id];
    if (ch.qty > 0) ids.add(productById(cat.id, ch.product).id);
  }
  const frame = rulesFor(c.trailer).plateFrame;
  if (frame) ids.add(frame);
  return [...ids];
}

export function setHarnessHighlight(h: THREE.Group, mats: Mats, on: boolean) {
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
