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
import { CATEGORIES, productById, type CategoryId, type Config } from '../data';
import type { Mats } from './materials';
import { profileAt, type Anchors } from './trailer';
import { isShared, markShared } from './geo';
import { emitterSpots, lampInstance, type LampFn } from './lampfx';

export interface Glow {
  sprite: THREE.Sprite;
  fn: LampFn;
}
export interface EquipmentBuild {
  group: THREE.Group;
  glows: Glow[];
  harness: THREE.Group;
  lampsByCat: Record<CategoryId, THREE.Object3D[]>;
  /** gerçek modeli henüz yüklenmemiş lamba var mı (Engine yüklenince yeniden kurar) */
  placeholders: number;
}

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
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
  side?: { x0: number; x1: number; y: [number, number][]; z: number; brackets?: { x0: number; x1: number; from: [number, number]; to: [number, number] } | null };
  front?: P3 & { bracket?: Bracket };
  armRear?: P3 & { wallZ?: number; bracket?: Bracket };
  armFront?: P3 & { wallZ?: number; bracket?: Bracket };
  work?: (P3 & { dir?: [number, number, number]; bracket?: Bracket })[];
  beacon?: (P3 & { bracket?: Bracket })[];
  harness?: { trunkY?: number; trunkZ?: number; profile?: [number, number][]; moduleX?: number; rearJunctionX?: number };
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

/** Arka lambaların genişliği (lamba yerel X), dizilim için: modelden ölçülür, yoksa ürüne göre tahmin */
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
    for (const obj of glowLater) {
      for (const sp of emitterSpots(obj)) {
        const mat = new THREE.SpriteMaterial({ map: mats.glow.white.map, color: sp.color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 1 });
        const s = new THREE.Sprite(mat);
        s.position.copy(sp.pos);
        s.scale.setScalar(Math.min(0.34, Math.max(0.09, sp.size * 1.6)));
        s.visible = false;
        s.renderOrder = 10;
        group.add(s);
        glows.push({ sprite: s, fn: sp.fn });
      }
    }
  };
  const lampWidth = (id: string, obj?: THREE.Object3D) => {
    if (obj && !obj.userData.placeholder) {
      const bb = new THREE.Box3().setFromObject(obj, true);
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
      edge = z - w / 2 - 0.025;
      // AMP 7 pin fiş lambanın arkasında; 7×1 dalı arka dağıtımdan
      const back = V(rx - 0.05, ly, s * z);
      amps.push({ pos: back.clone().add(V(-0.02, 0, 0)), dir: V(1, 0, 0) });
      wires.push({ kind: 'rear', r: 0.011, conn: undefined, pts: [V(xd, hy, s * z), V(xd, ly, s * z), V(rx - 0.075, ly, s * z)] });
    }
  }

  // =========================== PLAKA ===========================
  const pl = c.lamps.plate;
  const P = M.plate;
  const pzs = pl.qty === 0 ? [] : pl.qty === 1 ? [0] : (P?.z ?? [-0.17, 0.17]);
  const plateLampY = P?.y ?? a.rear.plateY + 0.085;
  const plateX = P?.x ?? rx + 0.01;
  for (const z of pzs) {
    mount('plate', pl.product, V(plateX, plateLampY, z), (o) => {
      o.rotation.y = Math.PI / 2;
    });
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
  for (let i = 0; i < per; i++) sideXs.push(per === 1 ? (sx0 + sx1) / 2 : sx0 + ((sx1 - sx0) * i) / (per - 1));
  for (const x of sideXs) {
    const y = sideY(x);
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
      mount('arm', ar.product, V(sp.x, sp.y, s * wz), (o) => {
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
    const lo = Math.min(zi, zr);
    const hi = Math.max(zo, zr);
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
    if (needSide) {
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
        const y = sideY(x);
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
    const myPlates = pzs.filter((z) => (z < 0 ? -1 : 1) === s || (pzs.length === 1 && s === 1));
    for (const z of myPlates) {
      const from = inner ? V(rx - 0.035, ly - 0.03, s * (inner.z - inner.hw * 0.6)) : V(xm + PORTS[2], hy, s * zPort);
      const xb = rx - 0.06;
      wires.push({ kind: 'plate', r: 0.008, conn: toLamp, pts: [from, V(xb, from.y, from.z), V(xb, from.y, z), V(xb, plateLampY + 0.04, z), V(plateX - 0.02, plateLampY + 0.04, z)] });
    }
    // --- arka lastik kol: dıştaki lambanın Superseal'inden ---
    if (ar.qty >= 2) {
      const wz = AR.wallZ ?? AR.z;
      const from = outer ? supersealOf(outer) : V(xd, hy, s * zr);
      const xb = Math.min(AR.x, rx) - 0.08;
      wires.push({ kind: 'marker', r: 0.008, conn: toLamp, pts: [from, V(xb, from.y, from.z), V(xb, from.y, s * (wz - 0.04)), V(xb, AR.y, s * (wz - 0.04)), V(AR.x, AR.y, s * (wz - 0.01))] });
    }
  }

  // =========================== ÇALIŞMA / TEPE KABLOLARI (modül yedek portları) ===========================
  const auxTo = (sp: P3, k: number) => {
    const s = sp.z >= 0 ? 1 : -1;
    const xp = xm + PORTS[2 + (k % 2)];
    const zc = s * 0.2;
    wires.push({ kind: 'aux', r: 0.008, conn: toLamp, pts: [V(xp, hy, s * zPort), V(xp, hy, zc), V(Math.max(sp.x - 0.15, xp), hy, zc), V(sp.x - 0.15, hy, sp.z), V(sp.x - 0.15, sp.y - 0.02, sp.z), V(sp.x - 0.02, sp.y - 0.02, sp.z)] });
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

  return { group, glows, harness, lampsByCat, placeholders };
}

let sealMat: THREE.MeshStandardMaterial | null = null;
function ampSealMat() {
  return (sealMat ??= new THREE.MeshStandardMaterial({ color: '#2e7d32', roughness: 0.5 }));
}
function wireMat(mats: Mats, kind: WireKind) {
  const w = mats.wire as Record<string, THREE.Material>;
  return w[kind] ?? w.marker;
}

/** Hangi lamba modelleri gerekiyor (Engine kurmadan önce yükler) */
export function lampIds(c: Config): string[] {
  const ids = new Set<string>();
  for (const cat of CATEGORIES) {
    const ch = c.lamps[cat.id];
    if (ch.qty > 0) ids.add(productById(cat.id, ch.product).id);
  }
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
    if ((o as THREE.Sprite).isSprite) {
      ((o as THREE.Sprite).material as THREE.Material).dispose();
      return;
    }
    const mm = o as THREE.Mesh;
    if (o.userData.lamp) return; // lamba klonlarının geometrisi modelle paylaşılır
    if (mm.geometry && !isShared(mm.geometry)) mm.geometry.dispose();
    if ((o as THREE.InstancedMesh).isInstancedMesh) (o as THREE.InstancedMesh).dispose();
  });
}

export const ALL_CATEGORIES = CATEGORIES.map((c) => c.id);
