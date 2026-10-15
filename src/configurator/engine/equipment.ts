// Lambalar, soketler ve tesisat. Seçimler değiştikçe bu grup baştan kurulur (birkaç düzine parça, çok hızlı).
// Lamba modelleri TEMSİLİDİR (ürün koduna göre farklı biçim); gerçek GLB'ler geldiğinde `lamp()` yerine model yüklenecek.
import * as THREE from 'three';
import { CATEGORIES, productById, type CategoryId, type Config, type LampStyle } from '../data';
import type { LensColor, Mats } from './materials';
import type { Anchors } from './trailer';

export interface EquipmentBuild {
  group: THREE.Group;
  glows: THREE.Sprite[];
  harness: THREE.Group;
  lampsByCat: Record<CategoryId, THREE.Object3D[]>;
}

// ---------- yardımcılar ----------
function rr(w: number, h: number, r: number) {
  const s = new THREE.Shape();
  const x = -w / 2;
  const y = -h / 2;
  r = Math.min(r, w / 2, h / 2);
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
}
function ellipse(w: number, h: number) {
  const s = new THREE.Shape();
  s.absellipse(0, 0, w / 2, h / 2, 0, Math.PI * 2, false, 0);
  return s;
}
const geoCache = new Map<string, THREE.BufferGeometry>();
function ext(key: string, shape: () => THREE.Shape, depth: number, bevel = 0.004) {
  const k = `${key}|${depth}|${bevel}`;
  let g = geoCache.get(k);
  if (!g) {
    g = new THREE.ExtrudeGeometry(shape(), { depth, bevelEnabled: bevel > 0, bevelSize: bevel, bevelThickness: bevel, bevelSegments: 2, curveSegments: 24 });
    geoCache.set(k, g);
  }
  return g;
}
function m(geo: THREE.BufferGeometry, mat: THREE.Material, cast = true) {
  const x = new THREE.Mesh(geo, mat);
  x.castShadow = cast;
  x.receiveShadow = true;
  return x;
}

interface LampOut {
  obj: THREE.Group;
  /** parlama noktaları (yerel), renk, boyut */
  glows: { p: THREE.Vector3; c: LensColor; s: number }[];
}

/** Lens yerel +Z yönüne bakar; genişlik X, yükseklik Y. */
function lensSeg(g: THREE.Group, mats: Mats, out: LampOut, c: LensColor, w: number, h: number, x: number, y: number, z: number, r = 0.012, round = false) {
  const geo = round ? ext(`e${w}x${h}`, () => ellipse(w, h), 0.012) : ext(`r${w}x${h}x${r}`, () => rr(w, h, r), 0.012);
  const l = m(geo, mats.lens[c], false);
  l.position.set(x, y, z);
  g.add(l);
  out.glows.push({ p: new THREE.Vector3(x, y, z + 0.03), c, s: Math.max(w, h) * 2.4 });
}

function lamp(style: LampStyle, mats: Mats): LampOut {
  const g = new THREE.Group();
  const out: LampOut = { obj: g, glows: [] };
  const housing = (w: number, h: number, d: number, r: number) => {
    const hm = m(ext(`h${w}x${h}x${r}`, () => rr(w, h, r), d, 0.006), mats.plastic);
    g.add(hm);
    return d;
  };
  switch (style) {
    case 'block': {
      const d = housing(0.42, 0.16, 0.06, 0.02);
      const z = d + 0.004;
      lensSeg(g, mats, out, 'amber', 0.1, 0.13, -0.15, 0, z);
      lensSeg(g, mats, out, 'red', 0.12, 0.13, -0.035, 0, z);
      lensSeg(g, mats, out, 'red', 0.09, 0.13, 0.075, 0, z);
      lensSeg(g, mats, out, 'white', 0.07, 0.13, 0.163, 0, z);
      break;
    }
    case 'carmen': {
      const d = housing(0.52, 0.12, 0.055, 0.035);
      const z = d + 0.004;
      lensSeg(g, mats, out, 'amber', 0.48, 0.028, 0, 0.037, z, 0.01);
      lensSeg(g, mats, out, 'red', 0.4, 0.05, -0.035, -0.012, z, 0.01);
      lensSeg(g, mats, out, 'white', 0.065, 0.05, 0.205, -0.012, z, 0.01);
      break;
    }
    case 'navia': {
      const d = housing(0.34, 0.18, 0.06, 0.07);
      const z = d + 0.004;
      lensSeg(g, mats, out, 'red', 0.3, 0.09, 0, 0.03, z, 0.04);
      lensSeg(g, mats, out, 'amber', 0.2, 0.04, -0.05, -0.05, z, 0.015);
      lensSeg(g, mats, out, 'white', 0.05, 0.05, 0.11, -0.05, z, 0.025, true);
      break;
    }
    case 'compact': {
      const d = housing(0.26, 0.13, 0.055, 0.02);
      const z = d + 0.004;
      lensSeg(g, mats, out, 'red', 0.15, 0.1, 0.045, 0, z);
      lensSeg(g, mats, out, 'amber', 0.07, 0.1, -0.075, 0, z);
      break;
    }
    case 'round': {
      const d = housing(0.44, 0.15, 0.04, 0.03);
      const z = d + 0.004;
      lensSeg(g, mats, out, 'amber', 0.11, 0.11, -0.14, 0, z, 0, true);
      lensSeg(g, mats, out, 'red', 0.11, 0.11, 0, 0, z, 0, true);
      lensSeg(g, mats, out, 'red', 0.11, 0.11, 0.14, 0, z, 0, true);
      break;
    }
    case 'oval': {
      const d = housing(0.14, 0.06, 0.03, 0.028);
      lensSeg(g, mats, out, 'amber', 0.12, 0.042, 0, 0, d + 0.004, 0, true);
      const br = m(new THREE.BoxGeometry(0.05, 0.025, 0.05), mats.plastic);
      br.position.set(0, 0.035, -0.01);
      g.add(br);
      break;
    }
    case 'rect': {
      const d = housing(0.12, 0.055, 0.028, 0.008);
      lensSeg(g, mats, out, 'amber', 0.1, 0.038, 0, 0, d + 0.004, 0.006);
      break;
    }
    case 'slim': {
      const d = housing(0.17, 0.032, 0.022, 0.012);
      lensSeg(g, mats, out, 'amber', 0.155, 0.02, 0, 0, d + 0.003, 0.008);
      break;
    }
    case 'disc': {
      const hm = m(ext('disc-h', () => ellipse(0.075, 0.075), 0.022, 0.005), mats.plastic);
      g.add(hm);
      lensSeg(g, mats, out, 'amber', 0.058, 0.058, 0, 0, 0.026, 0, true);
      break;
    }
    case 'pos-rect': {
      const d = housing(0.11, 0.055, 0.03, 0.01);
      lensSeg(g, mats, out, 'white', 0.09, 0.038, 0, 0, d + 0.004, 0.008);
      break;
    }
    case 'pos-round': {
      const hm = m(ext('pr-h', () => ellipse(0.08, 0.08), 0.025, 0.005), mats.plastic);
      g.add(hm);
      lensSeg(g, mats, out, 'white', 0.06, 0.06, 0, 0, 0.03, 0, true);
      break;
    }
    case 'plate-wide':
    case 'plate-small': {
      // plaka lambası: lens aşağı bakar (-Y)
      const w = style === 'plate-wide' ? 0.13 : 0.08;
      const hm = m(new THREE.BoxGeometry(w, 0.035, 0.06), mats.plastic);
      g.add(hm);
      const l = m(new THREE.BoxGeometry(w - 0.02, 0.006, 0.04), mats.lens.plate, false);
      l.position.set(0, -0.019, 0.005);
      g.add(l);
      out.glows.push({ p: new THREE.Vector3(0, -0.05, 0.02), c: 'plate', s: w * 2.6 });
      break;
    }
    case 'strip': {
      const d = housing(0.2, 0.034, 0.024, 0.012);
      lensSeg(g, mats, out, 'red', 0.18, 0.02, 0, 0, d + 0.003, 0.008);
      break;
    }
    case 'arm-dragon':
    case 'arm-classic': {
      // lastik kol: gövde yanından dışa (+Z) uzanır, ucunda 3 yönlü lamba başı
      const ang = style === 'arm-dragon' ? 0.55 : 0;
      const arm = new THREE.Group();
      const rod = m(new THREE.CylinderGeometry(0.014, 0.018, 0.17, 12), mats.rubber);
      rod.rotation.x = Math.PI / 2;
      rod.position.z = 0.085;
      arm.add(rod);
      const base = m(new THREE.BoxGeometry(0.06, 0.08, 0.02), mats.plastic);
      g.add(base);
      const head = new THREE.Group();
      head.position.z = 0.17;
      head.add(m(new THREE.BoxGeometry(0.07, 0.06, 0.05), mats.plastic));
      const lf = m(new THREE.BoxGeometry(0.006, 0.045, 0.04), mats.lens.white, false);
      lf.position.x = -0.037;
      const lr = m(new THREE.BoxGeometry(0.006, 0.045, 0.04), mats.lens.red, false);
      lr.position.x = 0.037;
      const ls = m(new THREE.BoxGeometry(0.055, 0.04, 0.006), mats.lens.amber, false);
      ls.position.z = 0.027;
      head.add(lf, lr, ls);
      arm.add(head);
      arm.rotation.x = -ang;
      g.add(arm);
      const hp = new THREE.Vector3(0, Math.sin(ang) * 0.17, Math.cos(ang) * 0.17);
      out.glows.push({ p: hp.clone().add(new THREE.Vector3(-0.05, 0, 0)), c: 'white', s: 0.14 });
      out.glows.push({ p: hp.clone().add(new THREE.Vector3(0.05, 0, 0)), c: 'red', s: 0.14 });
      out.glows.push({ p: hp.clone().add(new THREE.Vector3(0, 0, 0.04)), c: 'amber', s: 0.12 });
      break;
    }
  }
  return out;
}

// ---------- soketler ----------
function socket(mats: Mats, kind: '7' | '15', ccolor: THREE.Material) {
  const g = new THREE.Group();
  const plateM = m(new THREE.BoxGeometry(0.11, 0.11, 0.012), mats.darkMetal);
  g.add(plateM);
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
// Düzen broşür şemalarına göre (HOR-102/111/1001): merkezde Horpol kontrol modülü; öndeki soketlerden modüle besleme hatları,
// modülden iki yana yan ana hatlar ve arkaya dağıtım hatları. Hatlar dik açılı, köşeler yuvarlatılmış; her lamba dalında
// lambadan sabit mesafede siyah-beyaz konnektör. Ölçüler standart kuru yük dorsesine göre dengelendi (kablo uzunluğu bilgisi YOK).
type WireKind = 'main' | 'side' | 'rear' | 'plate' | 'marker';
/** Kablolar şemada okunabilsin diye gerçek ölçüden kalın çizilir */
const WIRE_SCALE = 1.7;
/** köşe yarıçapı */
const BEND = 0.14;
/** konnektörün lamba ucuna uzaklığı (hat boyunca) */
const CONN_FROM_LAMP = 0.3;
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

/** Köşe noktalarından, köşeleri yuvarlatılmış nokta dizisi üretir. */
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

/** Noktaları birebir izleyen eğri: düz kısımlar tek parça, köşeler sık (TubeGeometry'yi gereksiz bölmez). */
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

/** Hat boyunca baştan (ya da sondan) d mesafedeki nokta ve yön */
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

export function buildEquipment(c: Config, a: Anchors, mats: Mats): EquipmentBuild {
  const group = new THREE.Group();
  const harness = new THREE.Group();
  group.add(harness);
  const glows: THREE.Sprite[] = [];
  const lampsByCat = { stop: [], side: [], plate: [], front: [], arm: [], extra: [] } as Record<CategoryId, THREE.Object3D[]>;

  const mount = (cat: CategoryId, style: LampStyle, pos: THREE.Vector3, setup: (o: THREE.Group) => void) => {
    const out = lamp(style, mats);
    setup(out.obj);
    out.obj.position.copy(pos);
    out.obj.traverse((o) => (o.userData.category = cat));
    group.add(out.obj);
    lampsByCat[cat].push(out.obj);
    out.obj.updateMatrixWorld(true);
    for (const gl of out.glows) {
      const sp = new THREE.Sprite(mats.glow[gl.c]);
      sp.position.copy(gl.p).applyMatrix4(out.obj.matrixWorld);
      sp.scale.setScalar(gl.s);
      sp.visible = false;
      sp.renderOrder = 10;
      group.add(sp);
      glows.push(sp);
    }
  };

  // --- şema düzeni (x: arka uç 0, öne doğru eksi; z: genişlik) ---
  const hy = a.harness.y;
  const W2 = a.W / 2;
  const xm = -2.2; // Horpol modülü: arka lambalara ~2 m
  const PORTS = [-0.135, -0.045, 0.045, 0.135]; // modül yan portları (önden arkaya): besleme, yan hat, arka hat, yedek
  const zPort = 0.15; // modül yan yüzü
  const tz = 0.85; // yan ana hat
  const zr = 0.62; // arka hat
  const xd = -0.55; // arka dağıtım (tarak) hattı
  const zp = 0.3; // plaka hattı (arka hattan ayrılıp içe iner)

  type Wire = { kind: WireKind; r: number; pts: THREE.Vector3[]; conn?: { d: number; fromEnd: boolean } };
  const wires: Wire[] = [];
  const toLamp = { d: CONN_FROM_LAMP, fromEnd: true };
  const conns: { pos: THREE.Vector3; dir: THREE.Vector3 }[] = [];

  // arka tarağa bağlanan lambalar (kuyruk: tarak üzerindeki dönüşten sonraki noktalar)
  const rearDrops: { s: number; z: number; kind: WireKind; tail: THREE.Vector3[] }[] = [];
  // yan ana hatta bağlanan lambalar (x: hattan ayrıldığı nokta)
  const sideTaps: { x: number; kind: WireKind; tail: (s: number) => THREE.Vector3[] }[] = [];

  // --- arka (stop) lambaları ---
  const stop = c.lamps.stop;
  const stopStyle = productById('stop', stop.product).style;
  const pairs = stop.qty / 2;
  const ly = a.rear.lampY;
  for (let p = 0; p < pairs; p++) {
    for (const s of [1, -1]) {
      const z = a.rear.lampZ[p];
      mount('stop', stopStyle, V(a.rear.x, ly, s * z), (o) => {
        o.rotation.y = Math.PI / 2;
        if (s < 0) o.scale.x = -1;
      });
      rearDrops.push({ s, z, kind: 'rear', tail: [V(-0.08, hy, s * z), V(-0.08, ly, s * z), V(-0.01, ly, s * z)] });
    }
  }

  // --- plaka lambaları (arka hattın ikinci dönüşünden ayrılır; hat aşağıda arka hatlarla birlikte çizilir) ---
  const pl = c.lamps.plate;
  const plStyle = productById('plate', pl.product).style;
  const pzs = pl.qty === 1 ? [0] : [-0.17, 0.17];
  const py = a.rear.plateY + 0.1;
  for (const z of pzs) {
    mount('plate', plStyle, V(0.01, a.rear.plateY + 0.085, z), (o) => {
      o.rotation.y = Math.PI / 2;
    });
  }

  // --- yan markerlar ---
  const sd = c.lamps.side;
  const sdStyle = productById('side', sd.product).style;
  const per = sd.qty / 2;
  for (let i = 0; i < per; i++) {
    const t = per === 1 ? 0.5 : i / (per - 1);
    const x = a.side.x0 + (a.side.x1 - a.side.x0) * t;
    const y = a.side.yAt(x);
    for (const s of [1, -1]) {
      mount('side', sdStyle, V(x, y, s * a.side.z), (o) => {
        if (s < 0) o.scale.z = -1;
      });
    }
    sideTaps.push({ x, kind: 'side', tail: (s) => [V(x, hy, s * (W2 - 0.06)), V(x, y, s * (W2 - 0.06)), V(x, y, s * (W2 - 0.02))] });
  }

  // --- ön pozisyon (yan hattın ön ucu) ---
  const fr = c.lamps.front;
  if (fr.qty > 0) {
    const st = productById('front', fr.product).style;
    const p = a.front;
    for (const s of [1, -1]) {
      mount('front', st, V(p.x, p.y, s * p.z), (o) => {
        o.rotation.y = -Math.PI / 2;
      });
    }
    const xt = p.x + 0.1;
    sideTaps.push({ x: xt, kind: 'marker', tail: (s) => [V(xt, hy, s * p.z), V(xt, p.y, s * p.z), V(p.x + 0.03, p.y, s * p.z)] });
  }

  // --- gabari (lastik kol): arkadakiler taraktan, öndekiler yan hattan ---
  const ar = c.lamps.arm;
  if (ar.qty > 0) {
    const st = productById('arm', ar.product).style;
    const spots = ar.qty >= 4 ? [a.armRear, a.armFront] : [a.armRear];
    for (const sp of spots) {
      for (const s of [1, -1]) {
        mount('arm', st, V(sp.x, sp.y, s * sp.z), (o) => {
          if (s < 0) o.scale.z = -1;
        });
      }
      const za = W2 - 0.08;
      if (sp === a.armRear) {
        for (const s of [1, -1]) rearDrops.push({ s, z: za, kind: 'marker', tail: [V(sp.x, hy, s * za), V(sp.x, sp.y, s * za), V(sp.x, sp.y, s * (W2 - 0.01))] });
      } else {
        sideTaps.push({ x: sp.x, kind: 'marker', tail: (s) => [V(sp.x, hy, s * za), V(sp.x, sp.y, s * za), V(sp.x, sp.y, s * (W2 - 0.01))] });
      }
    }
  }

  // --- ek lambalar (taraktan) ---
  const ex = c.lamps.extra;
  if (ex.qty > 0) {
    const st = productById('extra', ex.product).style;
    const zs = ex.qty >= 4 ? [a.extra.z0, a.extra.z1] : [a.extra.z0];
    const xe = Math.min(-0.08, a.extra.x - 0.1);
    for (const z of zs) {
      for (const s of [1, -1]) {
        mount('extra', st, V(a.extra.x, a.extra.y, s * z), (o) => {
          o.rotation.y = Math.PI / 2;
        });
        rearDrops.push({ s, z, kind: 'marker', tail: [V(xe, hy, s * z), V(xe, a.extra.y, s * z), V(a.extra.x - 0.04, a.extra.y, s * z)] });
      }
    }
  }

  // --- soketler + besleme hatları (soketten modüle) ---
  const kinds: ('7' | '15')[] = c.socket === '7x2' ? ['7', '7'] : c.socket === '15' ? ['15'] : ['7', '15', '7'];
  const spacing = 0.15;
  const fx = a.harness.frontX;
  let frontPort = false;
  kinds.forEach((k, i) => {
    const z = (i - (kinds.length - 1) / 2) * spacing;
    const so = socket(mats, k, k === '15' ? mats.socketGrey : i === 0 ? mats.socket : mats.socketGrey);
    so.rotation.y = -Math.PI / 2;
    so.position.set(a.socket.x, a.socket.y, z);
    so.traverse((o) => (o.userData.category = 'socket'));
    group.add(so);
    const pts = [V(a.socket.x + 0.02, a.socket.y, z), V(fx, a.socket.y, z), V(fx, hy, z)];
    if (Math.abs(z) < 1e-3) {
      pts.push(V(xm - 0.2, hy, 0));
      frontPort = true;
    } else {
      const s = Math.sign(z);
      pts.push(V(xm - 0.75, hy, z), V(xm - 0.75, hy, s * 0.36), V(xm + PORTS[0], hy, s * 0.36), V(xm + PORTS[0], hy, s * zPort));
    }
    wires.push({ kind: 'main', r: 0.014, pts, conn: { d: 0.25, fromEnd: false } });
  });

  // --- yan ana hatlar: modülden çıkıp öne/arkaya uzanır, lambalar yuvarlatılmış dallarla ayrılır ---
  const xj = xm + PORTS[1];
  if (sideTaps.length) {
    for (const s of [1, -1]) {
      const starts: number[] = [xj - BEND];
      for (const tp of sideTaps) {
        const dir = Math.sign(xj - tp.x) || 1;
        const sx = tp.x + dir * Math.min(BEND, Math.abs(xj - tp.x) || BEND);
        starts.push(sx);
        wires.push({ kind: tp.kind, r: tp.kind === 'side' ? 0.008 : 0.009, conn: toLamp, pts: [V(sx, hy, s * tz), V(tp.x, hy, s * tz), ...tp.tail(s)] });
      }
      wires.push({ kind: 'side', r: 0.013, pts: [V(xj, hy, s * zPort), V(xj, hy, s * tz), V(xj - BEND, hy, s * tz)] });
      const lo = Math.min(...starts);
      const hi = Math.max(...starts);
      if (hi - lo > 1e-3) wires.push({ kind: 'side', r: 0.013, pts: [V(lo, hy, s * tz), V(hi, hy, s * tz)] });
    }
  }

  // --- arka hatlar: modülden arkaya, uçta tarak gibi dağılır ---
  for (const s of [1, -1]) {
    const ds = rearDrops.filter((d) => d.s === s);
    const plates = pzs.filter((z) => (z < 0 ? -1 : 1) === s);
    if (!ds.length && !plates.length) continue;
    // plaka: kırmızı arka hattın ikinci 90° dönüşünden (tarağa vardığı nokta) içe doğru ayrılır
    const xb = xd - 0.1;
    for (const z of plates) {
      wires.push({ kind: 'plate', r: 0.009, conn: toLamp, pts: [V(xb - BEND, hy, s * zr), V(xb, hy, s * zr), V(xb, hy, s * zp), V(-0.12, hy, s * zp), V(-0.12, hy, z), V(-0.12, py, z), V(0, py, z)] });
    }
    if (!ds.length) {
      wires.push({ kind: 'rear', r: 0.013, pts: [V(xm + PORTS[2], hy, s * zPort), V(xm + PORTS[2], hy, s * zr), V(xd, hy, s * zr)] });
      continue;
    }
    const zs = ds.map((d) => d.z);
    const zmin = Math.min(...zs);
    const zmax = Math.max(...zs);
    const bLo = zmin < zr ? zmin + Math.min(BEND, zr - zmin) : zr;
    const bHi = zmax > zr ? zmax - Math.min(BEND, zmax - zr) : zr;
    const xp = xm + PORTS[2];
    const line = [V(xp, hy, s * zPort), V(xp, hy, s * zr), V(xd, hy, s * zr)];
    // tarak, arka hattın bir ucundaysa hat köşeyle tarağa devam eder; ortadaysa T bağlantı
    if (bHi - bLo > 1e-3) {
      if (bLo >= zr - 1e-6) line.push(V(xd, hy, s * bHi));
      else if (bHi <= zr + 1e-6) line.push(V(xd, hy, s * bLo));
      else wires.push({ kind: 'rear', r: 0.013, pts: [V(xd, hy, s * bLo), V(xd, hy, s * bHi)] });
    }
    wires.push({ kind: 'rear', r: 0.013, pts: line, conn: { d: Math.abs(xd - xp) * 0.5, fromEnd: false } });
    for (const d of ds) {
      const dz = d.z - zr;
      const start = Math.abs(dz) < 1e-3 ? V(xd - BEND, hy, s * d.z) : V(xd, hy, s * (d.z - Math.sign(dz) * Math.min(BEND, Math.abs(dz))));
      wires.push({ kind: d.kind, r: 0.009, conn: toLamp, pts: [start, V(xd, hy, s * d.z), ...d.tail] });
    }
  }

  // --- Horpol kontrol modülü + port konnektörleri ---
  const mod = controlModule(mats);
  mod.position.set(xm, hy, 0);
  harness.add(mod);
  for (const s of [1, -1]) for (const px of PORTS) conns.push({ pos: V(xm + px, hy, s * (zPort + 0.03)), dir: V(0, 0, s) });
  if (frontPort) conns.push({ pos: V(xm - 0.23, hy, 0), dir: V(-1, 0, 0) });

  // --- hatları çiz ---
  for (const w of wires) {
    const pts = rounded(w.pts);
    if (pts.length < 2) continue;
    const t = m(new THREE.TubeGeometry(new PolyCurve(pts), pts.length - 1, w.r * WIRE_SCALE, 10, false), mats.wire[w.kind], false);
    t.userData.kind = w.kind;
    harness.add(t);
    if (w.conn) {
      const len = pathLength(pts);
      const d = w.conn.d * 2 > len ? len / 2 : w.conn.d;
      conns.push(along(pts, d, w.conn.fromEnd));
    }
  }

  // --- konnektörler: siyah-beyaz iki parçalı fiş (örnekli çizim: sayıdan bağımsız 2 çizim çağrısı) ---
  if (conns.length) {
    const geo = new THREE.BoxGeometry(0.04, 0.062, 0.062);
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

  return { group, glows, harness, lampsByCat };
}

export function setHarnessHighlight(h: THREE.Group, mats: Mats, on: boolean) {
  h.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (!mm.isMesh || !o.userData.kind) return;
    mm.material = on ? mats.wire[o.userData.kind as WireKind] : mats.wire.sheath;
  });
}

export function disposeEquipment(g: THREE.Object3D) {
  const cached = new Set(geoCache.values());
  g.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (mm.geometry && !cached.has(mm.geometry)) mm.geometry.dispose();
  });
}

export const ALL_CATEGORIES = CATEGORIES.map((c) => c.id);
