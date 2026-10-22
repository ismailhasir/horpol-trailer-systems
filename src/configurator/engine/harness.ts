// Tesisatın çizimi: koruge kablolar, konnektörler (Superseal, yuvarlak 7/15 pin, AMP, T ve Y bağlantı), Horpol modülü ve
// ön soketler. Güzergâhları equipment.ts kurar; burada yalnız biçim ve tesisat görünümündeki efektler var:
//   devre vurgusu: bir kategori seçilince ya da kablo / lamba üzerine gelince o devre parlar, diğerleri söner
//   akım akışı: ışıklar açıkken yanan işlevlerin kablolarında soketten lambaya ilerleyen ışık darbeleri
// Kablonun her köşesinde (tepe noktası) iki öznitelik taşınır: flow = [soketten uzaklık (m), kategori bit maskesi].
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import type { CategoryId } from '../data';
import { WIRE_COLORS } from '../colors';
import { markShared } from './geo';
import type { Mats } from './materials';

// ---------- devreler (kategori bitleri) ----------
export const CAT_BIT: Record<CategoryId, number> = { stop: 1, side: 2, plate: 4, front: 8, arm: 16, work: 32, beacon: 64 };
export const ALL_CATS = 127;
/** Kabloya tıklanınca açılacak kategori: devrenin asıl kategorisi (en küçük bit: 7×1 → stop, yan hat → yan marker).
 *  Ana hat bütün devreleri taşır, bir kategoriye ait değil (null). */
export function pickCategory(mask: number): CategoryId | null {
  if (!mask || mask === ALL_CATS) return null;
  return (Object.keys(CAT_BIT) as CategoryId[]).reduce<CategoryId | null>((best, c) => (mask & CAT_BIT[c] && (!best || CAT_BIT[c] < CAT_BIT[best]) ? c : best), null);
}

/** Vurgu ve akış: tüm kablo malzemeleri bu tek uniform kümesini paylaşır (Engine günceller) */
export const harnessFx = {
  uTime: { value: 0 },
  /** akış açık (tesisat görünümü + ışıklar) */
  uFlow: { value: 0 },
  /** akımın aktığı kategoriler (yanan işlevler) */
  uActive: { value: 0 },
  /** vurgulanan kategoriler (0: vurgu yok) */
  uHi: { value: 0 },
};
/** darbe aralığı (m) ve hızı (m/s) */
const FLOW_GAP = 1.4;
const FLOW_SPEED = 2.2;

const patched = new WeakSet<THREE.Material>();
function flowMaterial<T extends THREE.MeshStandardMaterial>(m: T): T {
  if (patched.has(m)) return m;
  patched.add(m);
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, harnessFx);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec2 flow;\nvarying vec2 vFlow;')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\nvFlow = flow;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uTime;\nuniform float uFlow;\nuniform int uActive;\nuniform int uHi;\nvarying vec2 vFlow;')
      .replace(
        '#include <emissivemap_fragment>',
        `#include <emissivemap_fragment>
        int cm = int(vFlow.y + 0.5);
        if (uHi != 0) {
          if ((cm & uHi) == 0) { diffuseColor.rgb *= 0.14; totalEmissiveRadiance *= 0.06; }
          else totalEmissiveRadiance *= 2.6;
        }
        if (uFlow > 0.5 && (cm & uActive) != 0 && (uHi == 0 || (cm & uHi) != 0)) {
          // darbe: arkada yumuşak kuyruk, önde keskin baş; soketten lambaya doğru ilerler
          float ph = fract(vFlow.x * ${(1 / FLOW_GAP).toFixed(4)} - uTime * ${(FLOW_SPEED / FLOW_GAP).toFixed(4)});
          float p = smoothstep(0.0, 0.26, ph) * (1.0 - smoothstep(0.26, 0.3, ph));
          totalEmissiveRadiance += emissive * p * 7.0;
        }`,
      );
  };
  m.customProgramCacheKey = () => 'harness-flow';
  return m;
}

// ---------- kablolar ----------
// Kablo türleri (tesisat görünümündeki renk kodu; eğitsel görselleştirme, gerçek kablo renkleri değildir):
// main = soket→modül ana hat, rear = modül→arka lamba 7×1, side = 2×0,5 yan hat, plate = plaka, marker = ön/kontur dalları, aux = çalışma/tepe
export type WireKind = 'main' | 'side' | 'rear' | 'plate' | 'marker' | 'aux';
export type ConnType = 'round' | 'roundPlug' | 'ss' | 'ssPlug' | 'amp' | 'tee' | 'ysplit';
export interface Wire {
  kind: WireKind;
  r: number;
  pts: THREE.Vector3[];
  /** taşıdığı devreler (CAT_BIT); verilmezse türüne göre (eski şema) */
  cats?: number;
  /** besleme sırası: 0 soketten, 1 modülden, 2+ dallar (akış uzaklığı üst seviyedeki kablodan devam eder); verilmezse türüne göre */
  level?: number;
  /** kablo üzerinde konnektör: uçtan d metre */
  conn?: { d: number; fromEnd: boolean; type?: ConnType };
}
/** Konnektör: yerel +X kablo yönü; side verilirse yerel +Z o yöne (T bağlantının dalı) */
export interface Conn {
  type: ConnType;
  pos: THREE.Vector3;
  dir: THREE.Vector3;
  side?: THREE.Vector3;
  /** boyut çarpanı (ör. ana hattın büyük ara fişi) */
  scale?: number;
}

export const WIRE_SCALE = 1.7;
const BEND = 0.14;
const RIBS_PER_M = 75;
const CLIP_STEP = 0.5;
const RADIAL = 10;
/** konnektörler kablolarla aynı oranda belirgin (gerçek ölçünün katı) */
const CONN_SCALE = 1.5;

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

export function rounded(pts: THREE.Vector3[], r = BEND) {
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

export function along(pts: THREE.Vector3[], d: number, fromEnd: boolean) {
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

let auxWire: THREE.MeshStandardMaterial | null = null;
export function wireMat(mats: Mats, kind: WireKind) {
  if (kind === 'aux') {
    // çalışma / tepe hatları: lejanttaki mor (diğer hatlarla aynı koruge dokusu)
    if (!auxWire) {
      auxWire = mats.wire.marker.clone();
      auxWire.color.set(WIRE_COLORS.aux);
      auxWire.emissive.set(WIRE_COLORS.aux);
    }
    return flowMaterial(auxWire);
  }
  return flowMaterial(mats.wire[kind] ?? mats.wire.marker);
}

/** Polyline üzerindeki en yakın noktanın baştan uzaklığı ve o noktaya mesafe */
function nearestOn(pts: THREE.Vector3[], cum: number[], p: THREE.Vector3) {
  let best = { dist: Infinity, at: 0 };
  const ab = new THREE.Vector3();
  const ap = new THREE.Vector3();
  for (let i = 0; i < pts.length - 1; i++) {
    ab.subVectors(pts[i + 1], pts[i]);
    const l2 = ab.lengthSq();
    const t = l2 > 0 ? THREE.MathUtils.clamp(ap.subVectors(p, pts[i]).dot(ab) / l2, 0, 1) : 0;
    const q = pts[i].clone().addScaledVector(ab, t);
    const d = q.distanceTo(p);
    if (d < best.dist) best = { dist: d, at: cum[i] + Math.sqrt(l2) * t };
  }
  return best;
}

/** eski şema kabloları için tür → devre */
const KIND_CATS: Record<WireKind, number> = {
  main: ALL_CATS,
  rear: CAT_BIT.stop | CAT_BIT.plate | CAT_BIT.arm,
  side: CAT_BIT.side | CAT_BIT.front | CAT_BIT.arm,
  plate: CAT_BIT.plate,
  marker: CAT_BIT.front | CAT_BIT.arm,
  aux: CAT_BIT.work | CAT_BIT.beacon,
};

export interface HarnessOpts {
  /** kablolar koyu kılıf malzemesiyle (gizli güzergâh); değilse renkli devre malzemesi */
  sheath?: boolean;
  /** üzerine gelme seçimi için görünmez kalın kopya kablolar */
  pickers?: boolean;
}

/**
 * Kabloları (yuvarlatılmış köşeli boru), kelepçeleri ve konnektörleri tek grupta kurar. Kablolar besleme sırasıyla
 * (level) işlenir: her kablonun akış uzaklığı, başladığı noktaya en yakın üst seviye kablonun o noktadaki uzaklığından devam eder.
 */
export function drawHarness(input: Wire[], conns: Conn[], mats: Mats, opts: HarnessOpts = {}) {
  const g = new THREE.Group();
  const done: { pts: THREE.Vector3[]; cum: number[]; d0: number; level: number }[] = [];
  const clips: { pos: THREE.Vector3; dir: THREE.Vector3; r: number }[] = [];
  const all = [...conns];
  const pickGeo: THREE.BufferGeometry[] = [];
  const wires = input.map((w) => ({ ...w, cats: w.cats ?? KIND_CATS[w.kind], level: w.level ?? (w.kind === 'main' ? 0 : w.r >= 0.01 ? 1 : 2) }));
  for (const w of wires.sort((p, q) => p.level - q.level)) {
    const pts = rounded(w.pts);
    if (pts.length < 2) continue;
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
    let d0 = 0;
    if (w.level > 0) {
      let best = { dist: 0.6, at: 0 };
      for (const o of done) {
        if (o.level >= w.level) continue;
        const n = nearestOn(o.pts, o.cum, pts[0]);
        if (n.dist < best.dist) best = { dist: n.dist, at: o.d0 + n.at + n.dist };
      }
      d0 = best.at;
    }
    done.push({ pts, cum, d0, level: w.level });

    const tg = new THREE.TubeGeometry(new PolyCurve(pts), pts.length - 1, w.r * WIRE_SCALE, RADIAL, false);
    const uv = tg.attributes.uv as THREE.BufferAttribute;
    const flow = new Float32Array(uv.count * 2);
    for (let i = 0; i < pts.length; i++) {
      for (let j = 0; j <= RADIAL; j++) {
        const k = i * (RADIAL + 1) + j;
        uv.setX(k, cum[i] * RIBS_PER_M);
        flow[k * 2] = d0 + cum[i];
        flow[k * 2 + 1] = w.cats;
      }
    }
    uv.needsUpdate = true;
    tg.setAttribute('flow', new THREE.BufferAttribute(flow, 2));
    const t = new THREE.Mesh(tg, opts.sheath ? mats.wire.sheath : wireMat(mats, w.kind));
    t.receiveShadow = true;
    t.userData.kind = w.kind;
    t.userData.cats = w.cats;
    g.add(t);
    if (opts.pickers) {
      const pg = new THREE.TubeGeometry(new PolyCurve(pts), pts.length - 1, Math.max(0.045, w.r * 3.5), 5, false);
      pg.userData.cats = w.cats;
      pickGeo.push(pg);
    }
    const len = cum[cum.length - 1];
    if (w.r >= 0.012) {
      for (let d = 0.35; d < len - 0.3; d += CLIP_STEP) clips.push({ ...along(pts, d, false), r: w.r * WIRE_SCALE });
    }
    if (w.conn) {
      const d = w.conn.d * 2 > len ? len / 2 : w.conn.d;
      const at = along(pts, d, w.conn.fromEnd);
      all.push({ type: w.conn.type ?? 'ss', pos: at.pos, dir: w.conn.fromEnd ? at.dir.negate() : at.dir });
    }
  }
  // seçim kopyaları: görünmez (çizilmez), yalnız ışın testine girer
  for (const pg of pickGeo) {
    const p = new THREE.Mesh(pg, pickMat());
    p.visible = false;
    p.userData.cats = pg.userData.cats;
    p.userData.picker = true;
    g.add(p);
  }

  // --- kelepçeler (kablo bağı) ---
  if (clips.length) {
    const cm = new THREE.InstancedMesh(clipGeo(), mats.plastic, clips.length);
    const q = new THREE.Quaternion();
    const mtx = new THREE.Matrix4();
    clips.forEach((cl, i) => {
      q.setFromUnitVectors(V(0, 1, 0), cl.dir);
      cm.setMatrixAt(i, mtx.compose(cl.pos, q, V(cl.r * 1.35, 1, cl.r * 1.35)));
    });
    g.add(cm);
  }
  // --- konnektörler: tür başına, malzeme başına tek örneklenmiş ağ ---
  const byType = new Map<ConnType, Conn[]>();
  for (const c of all) byType.set(c.type, [...(byType.get(c.type) ?? []), c]);
  const mtx = new THREE.Matrix4();
  const S = V(1, 1, 1);
  for (const [type, list] of byType) {
    for (const [key, geo] of Object.entries(connGeo(type))) {
      const im = new THREE.InstancedMesh(geo, connMat(mats, key as PartMat), list.length);
      list.forEach((c, i) => im.setMatrixAt(i, mtx.compose(c.pos, basisQ(c.dir, c.side), S.setScalar(CONN_SCALE * (c.scale ?? 1)))));
      im.castShadow = true;
      im.receiveShadow = true;
      g.add(im);
    }
  }
  return g;
}

let pickM: THREE.MeshBasicMaterial | null = null;
const pickMat = () => (pickM ??= new THREE.MeshBasicMaterial({ visible: false }));

/** yerel X → dir, yerel Z → side (dik bileşeni); side yoksa yatay düzlemde rastgele değil, dünya Y yukarı kalacak şekilde */
function basisQ(dir: THREE.Vector3, side?: THREE.Vector3) {
  const x = dir.clone().normalize();
  let z = side ? side.clone() : V(0, 1, 0).cross(x);
  if (z.lengthSq() < 1e-8) z = V(0, 0, 1);
  z.addScaledVector(x, -z.dot(x)).normalize();
  const y = z.clone().cross(x).normalize();
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
}

// ---------- konnektör biçimleri (gerçek ölçü, m; yerel +X kablo yönü) ----------
type PartMat = 'black' | 'grey' | 'green' | 'white';
function connMat(mats: Mats, k: PartMat): THREE.Material {
  if (k === 'grey') return mats.socketGrey;
  if (k === 'white') return mats.connWhite;
  if (k === 'green') return (sealMat ??= new THREE.MeshStandardMaterial({ color: '#2e7d32', roughness: 0.5 }));
  return mats.plastic;
}
let sealMat: THREE.MeshStandardMaterial | null = null;

/** X ekseni etrafında döner profil: [x, yarıçap] çiftleri */
function latheX(profile: [number, number][], seg = 20) {
  const g = new THREE.LatheGeometry(
    profile.map(([x, r]) => new THREE.Vector2(r, x)),
    seg,
  );
  g.rotateZ(-Math.PI / 2);
  return g;
}
/** sırtlı (kanallı) bölüm: x0..x1 arasında n sırt, yarıçap r ile r+dr arasında */
function ribs(x0: number, x1: number, r: number, dr: number, n: number): [number, number][] {
  const out: [number, number][] = [];
  const step = (x1 - x0) / n;
  for (let i = 0; i < n; i++) {
    const a = x0 + i * step;
    out.push([a, r], [a + step * 0.2, r + dr], [a + step * 0.6, r + dr], [a + step * 0.8, r]);
  }
  out.push([x1, r]);
  return out;
}
function box(w: number, h: number, d: number, x = 0, y = 0, z = 0) {
  const b = new THREE.BoxGeometry(w, h, d);
  b.translate(x, y, z);
  return b;
}
/** parçaları tek geometride birleştirir (konum, normal, uv) ve önbellekte tutulduğu için paylaşılan işaretler.
 *  RoundedBoxGeometry indekssiz: karışık kümede hepsi indekssize çevrilir. */
function merge(parts: THREE.BufferGeometry[]) {
  const mixed = parts.some((p) => !p.index);
  return markShared(mergeGeometries(mixed ? parts.map((p) => (p.index ? p.toNonIndexed() : p)) : parts)!);
}

/** kablo kılıfı ucu (sırtlı lastik çizme): x0'da r0, x1'de r1 yarıçap. Profil hep artan x ile kurulur (yüzey dışa baksın). */
function boot(x0: number, x1: number, r0: number, r1: number): THREE.BufferGeometry {
  if (x1 < x0) return boot(x1, x0, r1, r0);
  const n = 4;
  const p: [number, number][] = [[x0, 0], [x0, r0]];
  for (let i = 0; i < n; i++) {
    const a = x0 + ((x1 - x0) * i) / n;
    const r = r0 + ((r1 - r0) * i) / n;
    p.push([a + (x1 - x0) * 0.1, r + 0.0012], [a + (x1 - x0) * 0.2, r]);
  }
  p.push([x1, r1], [x1, 0]);
  return latheX(p, 16);
}

const geoCache = new Map<ConnType, Partial<Record<PartMat, THREE.BufferGeometry>>>();
function connGeo(type: ConnType) {
  let c = geoCache.get(type);
  if (c) return c;
  c = {};
  if (type === 'round' || type === 'roundPlug') {
    // ISO 1185 / 3731 kablo fişi: sırtlı tutma gövdesi, gri bayonet somunu; çift: karşısında dişi gövde
    const plugBody = latheX([[0, 0], [0, 0.0075], [0.012, 0.0085], [0.028, 0.0145], ...ribs(0.03, 0.058, 0.0165, 0.0018, 6), [0.06, 0.0175], [0.06, 0]]);
    const nut = latheX([[0.06, 0], [0.06, 0.02], ...ribs(0.061, 0.079, 0.0205, 0.0015, 5), [0.08, 0.019], [0.08, 0]], 24);
    if (type === 'round') {
      const mate = latheX([[0.08, 0], [0.08, 0.0185], [0.084, 0.0185], [0.086, 0.017], ...ribs(0.088, 0.118, 0.016, 0.0016, 6), [0.132, 0.0145], [0.148, 0.0085], [0.16, 0.0075], [0.16, 0]]);
      for (const g of [plugBody, nut, mate]) g.translate(-0.08, 0, 0);
      c.black = merge([plugBody, mate]);
      c.grey = merge([nut]);
    } else {
      for (const g of [plugBody, nut]) g.translate(-0.08, 0, 0);
      c.black = merge([plugBody]);
      c.grey = merge([nut]);
    }
  } else if (type === 'ss' || type === 'ssPlug') {
    // Superseal 1.5 (2 pin): dişi gövde + kilit dili, erkek gövde + gri kilit yuvası, iki uçta sırtlı conta
    const bootA = boot(0, 0.014, 0.0045, 0.0062);
    const fem = box(0.028, 0.016, 0.021, 0.028);
    const latch = box(0.012, 0.0035, 0.008, 0.033, 0.0095);
    const ramp = box(0.004, 0.0025, 0.012, 0.04, 0.0088);
    if (type === 'ss') {
      const male = box(0.02, 0.019, 0.024, 0.052);
      const lock = box(0.006, 0.02, 0.025, 0.044);
      const bootB = boot(0.076, 0.062, 0.0045, 0.0062);
      for (const g of [bootA, fem, latch, ramp, male, lock, bootB]) g.translate(-0.038, 0, 0);
      c.black = merge([bootA, fem, male, bootB]);
      c.grey = merge([latch, ramp, lock]);
    } else {
      for (const g of [bootA, fem, latch, ramp]) g.translate(-0.042, 0, 0);
      c.black = merge([bootA, fem]);
      c.grey = merge([latch, ramp]);
    }
  } else if (type === 'amp') {
    // AMP 7 pin (arka lamba fişi): sırtlı yuvarlak gövde, yeşil conta; ön yüz x = 0'da lambaya dayanır
    const body = latheX([[-0.075, 0], [-0.075, 0.0062], [-0.062, 0.0075], [-0.05, 0.0135], ...ribs(-0.048, -0.012, 0.0158, 0.0014, 7), [-0.01, 0.0158], [-0.01, 0]]);
    const seal = latheX([[-0.01, 0], [-0.01, 0.0168], [-0.004, 0.0172], [-0.004, 0.0152], [0, 0.0152], [0, 0]], 24);
    c.black = merge([body]);
    c.green = merge([seal]);
  } else if (type === 'tee') {
    // yan hat bağlantısı: hat üzerinde kelepçeli gövde, dal (+Z) lambanın 0,6 m kablosuna gider
    const body = box(0.03, 0.02, 0.024);
    const cap = box(0.018, 0.004, 0.016, 0, 0.012);
    const br = boot(0.012, 0.026, 0.0062, 0.0042);
    br.rotateY(-Math.PI / 2);
    const end = [boot(-0.028, -0.015, 0.0068, 0.0082), boot(0.028, 0.015, 0.0068, 0.0082)];
    c.black = merge([body, br, ...end]);
    c.grey = merge([cap]);
  } else if (type === 'ysplit') {
    // 7×1 ayırıcı: tek giriş (−X), iki çıkış (+X, ±Z yönünde açılı)
    const body = new RoundedBoxGeometry(0.05, 0.026, 0.05, 2, 0.006);
    const band = box(0.012, 0.028, 0.052, -0.012);
    const inp = boot(-0.044, -0.025, 0.0085, 0.012);
    const outs = [-1, 1].map((s) => {
      const b = boot(0.02, 0.0, 0.0085, 0.011);
      b.rotateY(-s * 0.6); // +X → (cos, 0, s·sin): çıkış ±Z yönünde açılır
      b.translate(0.026, 0, s * 0.012);
      return b;
    });
    c.black = merge([body, inp, ...outs]);
    c.grey = merge([band]);
  }
  geoCache.set(type, c);
  return c;
}

let clipG: THREE.BufferGeometry | null = null;
const clipGeo = () => (clipG ??= markShared(new THREE.CylinderGeometry(1, 1, 0.012, 14, 1, true)));

// ---------- Horpol kontrol modülü (yeni şema) ----------
/** Modülün port düzeni: ön yüz (sokete bakan) ve arka yüz; z yanal. R: yuvarlak 7 pin, S: Superseal */
/**
 * Kablolar 1,7 kat kalın çizildiği için modül de gerçeğinden ~1,35 kat büyük (orantı bozulmasın). Şemadaki gibi iki yüzde de
 * soldan sağa 3 Superseal ve en sağda büyük yuvarlak soket. Üstten bakışta (ön yukarıda) sağ = dünya −z.
 */
export const MODULE = {
  hx: 0.15,
  hz: 0.25,
  h: 0.085,
  /** Superseal portlarının z'si (soldan sağa) ve büyük soketin z'si (en sağ) */
  small: [0.165, 0.085, 0.005] as const,
  big: -0.13,
  /** port ağzının yüzden çıkıntısı */
  lip: 0.014,
};

/** Gövde: siyah, yuvarlatılmış köşeli; çevresinde açık renk tampon kuşak ve köşe takozları; üstte panel ve logo; yüzlerde portlar */
export function moduleModel(mats: Mats) {
  const g = new THREE.Group();
  const { hx, hz, h } = MODULE;
  const add = (geo: THREE.BufferGeometry, mat: THREE.Material, x = 0, y = 0, z = 0) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    m.castShadow = true;
    m.receiveShadow = true;
    g.add(m);
    return m;
  };
  add(new RoundedBoxGeometry(hx * 2, h, hz * 2, 3, 0.018), mats.plastic);
  add(new RoundedBoxGeometry(hx * 2 + 0.018, 0.03, hz * 2 + 0.018, 2, 0.012), mats.connWhite, 0, -h * 0.18);
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) add(new RoundedBoxGeometry(0.066, h * 0.86, 0.066, 2, 0.016), mats.connWhite, sx * (hx - 0.016), -0.002, sz * (hz - 0.016));
    // vida kulakları (yan uçların ortasında)
    add(new THREE.CylinderGeometry(0.021, 0.021, 0.014, 16), mats.connWhite, 0, -h / 2 + 0.007, sx * (hz + 0.024));
  }
  add(new RoundedBoxGeometry(hx * 1.3, 0.008, hz * 1.3, 2, 0.004), mats.socket, 0, h / 2);
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(0.27, (0.27 * 528) / 720), mats.logoWhite);
  logo.rotation.set(-Math.PI / 2, 0, Math.PI / 2);
  logo.position.y = h / 2 + 0.0045;
  g.add(logo);
  // port ağızları: Superseal dikdörtgen yuva, yuvarlak 7 pin yuva (fişler kablo yüksekliğinde, y = PORT_Y)
  const ports = [...MODULE.small.map((z) => ({ z, t: 'S' })), { z: MODULE.big, t: 'R' }];
  for (const face of [-1, 1]) {
    for (const p of ports) {
      const x = face * (hx + MODULE.lip / 2);
      if (p.t === 'S') {
        add(new THREE.BoxGeometry(MODULE.lip, 0.034, 0.042), mats.plastic, x, PORT_Y, p.z);
        add(new THREE.BoxGeometry(MODULE.lip + 0.002, 0.022, 0.03), mats.socketGrey, x, PORT_Y, p.z);
      } else {
        const r = add(new THREE.CylinderGeometry(0.034, 0.034, MODULE.lip, 24), mats.plastic, x, PORT_Y, p.z);
        r.rotation.z = Math.PI / 2;
        const ring = add(new THREE.CylinderGeometry(0.026, 0.026, MODULE.lip + 0.002, 24), mats.socketGrey, x, PORT_Y, p.z);
        ring.rotation.z = Math.PI / 2;
      }
    }
  }
  g.userData.category = 'module';
  return g;
}
/** port ağzının dünya konumu (modül merkezine göre): kablo buradan girer */
export function modulePort(face: 'front' | 'rear', z: number) {
  return V((face === 'front' ? -1 : 1) * (MODULE.hx + MODULE.lip), PORT_Y, z);
}
/** port ağızlarının modül merkezine göre yüksekliği (gövdenin alt yarısında: modül şasiye oturur, kablolar şasinin üstünde) */
const PORT_Y = -0.012;

// ---------- ön soket (ISO 1185 / 3731) ----------
/** Ön duvara vidalı soket: kare flanş ve 4 vida, gövde, yaylı kapak (üstten menteşeli, hafif aralık), arkada kablo rakoru. Yerel +Z dışa. */
export function socketModel(mats: Mats, kind: '7' | '15', body: THREE.Material) {
  const g = new THREE.Group();
  const add = (geo: THREE.BufferGeometry, mat: THREE.Material) => {
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    g.add(m);
    return m;
  };
  const big = kind === '15' ? 1.12 : 1;
  const fl = add(new RoundedBoxGeometry(0.1 * big, 0.1 * big, 0.008, 2, 0.006), body);
  fl.position.z = 0.004;
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      const sc = add(new THREE.CylinderGeometry(0.0055, 0.0055, 0.004, 12), mats.socketGrey);
      sc.rotation.x = Math.PI / 2;
      sc.position.set(sx * 0.036 * big, sy * 0.036 * big, 0.01);
    }
  }
  const housing = add(latheX([[0, 0], [0, 0.034 * big], [0.04, 0.032 * big], [0.046, 0.036 * big], [0.05, 0.036 * big], [0.05, 0]], 28), body);
  housing.rotation.y = -Math.PI / 2;
  housing.position.z = 0.008;
  // kapak: üstte menteşe, ~12° açık
  const lidG = new THREE.Group();
  const lid = new THREE.Mesh(latheX([[0, 0], [0, 0.04 * big], [0.008, 0.04 * big], [0.012, 0.03 * big], [0.012, 0]], 28), body);
  lid.rotation.y = -Math.PI / 2;
  lid.position.y = -0.04 * big;
  lid.castShadow = true;
  lidG.add(lid);
  const hinge = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.03, 10), mats.socketGrey);
  hinge.rotation.z = Math.PI / 2;
  lidG.add(hinge);
  lidG.position.set(0, 0.04 * big, 0.058);
  lidG.rotation.x = -0.21;
  g.add(lidG);
  // arkada rakor (kablo girişi; duvarın içinde)
  const gland = add(latheX([[0, 0], [0, 0.012], [0.02, 0.012], [0.03, 0.008], [0.03, 0]], 16), mats.plastic);
  gland.rotation.y = Math.PI / 2;
  gland.position.z = 0;
  return g;
}
