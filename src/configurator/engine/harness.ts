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
export const CAT_BIT: Record<CategoryId, number> = { stop: 1, side: 2, plate: 4, front: 8, arm: 16, work: 32, beacon: 64, strip: 128 };
export const ALL_CATS = 255;
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
export type ConnType = 'round' | 'roundPlug' | 'ss' | 'ssPlug' | 'ssCap' | 'amp' | 'ampPair' | 'tee' | 'ysplit';
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

// Kablolar ve konnektörler gerçek ölçüde (kullanıcı 2026-10-22; önceden okunurluk için 1,7 / 1,5 kat büyüktü). Çaplar
// equipment.ts'de: koruge boru dış çapı (NW17 ana hat, NW10 7×1, NW7 yan hat; doğrulanmadı)
export const WIRE_SCALE = 1;
const BEND = 0.14;
const RIBS_PER_M = 75;
const CLIP_STEP = 0.5;
const RADIAL = 10;
const CONN_SCALE = 1;

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
  rear: CAT_BIT.stop | CAT_BIT.plate | CAT_BIT.arm | CAT_BIT.strip,
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
    if (w.r >= 0.0065) {
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
      im.name = `conn:${type}:${key}`;
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
type PartMat = 'black' | 'grey' | 'green' | 'white' | 'yellow' | 'nylon';
function connMat(mats: Mats, k: PartMat): THREE.Material {
  if (k === 'grey') return mats.socketGrey;
  if (k === 'white') return mats.connWhite;
  if (k === 'green') return (sealMat ??= new THREE.MeshStandardMaterial({ color: '#4caf2a', roughness: 0.55 }));
  // Superseal kablo contaları sarı (Horpol TLA02318 seti)
  if (k === 'yellow') return (yellowMat ??= new THREE.MeshStandardMaterial({ color: '#e9c21b', roughness: 0.6 }));
  // konnektör gövdeleri: yarı parlak siyah poliamid (kablo kılıfı ve modül plastiğinden daha parlak: kalıp kenarları okunur)
  if (k === 'nylon') return (nylonMat ??= new THREE.MeshStandardMaterial({ color: '#141518', roughness: 0.34, metalness: 0.05 }));
  return mats.plastic;
}
let sealMat: THREE.MeshStandardMaterial | null = null;
let yellowMat: THREE.MeshStandardMaterial | null = null;
let nylonMat: THREE.MeshStandardMaterial | null = null;

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
  return latheX(p, 10);
}

/** Köşeleri r yarıçaplı dikdörtgen (yerel z genişlik w, y yükseklik h; r = h/2: oval / stadyum) */
function rrectShape(w: number, h: number, r: number, cz = 0, cy = 0) {
  const sh = new THREE.Shape();
  const x0 = cz - w / 2, x1 = cz + w / 2, y0 = cy - h / 2, y1 = cy + h / 2;
  r = Math.min(r, w / 2, h / 2) * 0.999; // tam stadyumda sıfır uzunluklu kenar (çift nokta) kapak üçgenlemesini bozar
  sh.moveTo(x0 + r, y0);
  sh.lineTo(x1 - r, y0);
  sh.absarc(x1 - r, y0 + r, r, -Math.PI / 2, 0, false);
  sh.lineTo(x1, y1 - r);
  sh.absarc(x1 - r, y1 - r, r, 0, Math.PI / 2, false);
  sh.lineTo(x0 + r, y1);
  sh.absarc(x0 + r, y1 - r, r, Math.PI / 2, Math.PI, false);
  sh.lineTo(x0, y0 + r);
  sh.absarc(x0 + r, y0 + r, r, Math.PI, Math.PI * 1.5, false);
  return sh;
}
/** Kesit (yerel z / y düzleminde, kenarları pahlı) x0 … x1 boyunca uzatılır; dış çizgi kesitin kendisi (pah içe) */
function extrudeX(shape: THREE.Shape, x0: number, x1: number, bevel = 0.0006, seg = 2) {
  const b = Math.min(bevel, (x1 - x0) / 3);
  const g = new THREE.ExtrudeGeometry(shape, {
    depth: x1 - x0 - 2 * b,
    bevelEnabled: b > 0,
    bevelThickness: b,
    bevelSize: b,
    bevelOffset: -b,
    bevelSegments: 1,
    curveSegments: seg,
  });
  g.rotateY(Math.PI / 2); // şekil x → −z (simetrik), uzatma z → +x
  g.translate(x0 + b, 0, 0);
  return g;
}
/** z ekseninde ötelenmiş X dönel parça */
function latheAt(profile: [number, number][], z: number, seg = 12) {
  const g = latheX(profile, seg);
  g.translate(0, 0, z);
  return g;
}
/** Eksenel (boyuna) kanallı somun kesiti: n diş, dış r, kanal derinliği dr */
function flutedShape(r: number, dr: number, n: number) {
  const sh = new THREE.Shape();
  const steps = n * 4;
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    const ph = (i % 4) / 4;
    const rr = ph === 0 || ph === 0.25 ? r : r - dr;
    const x = rr * Math.cos(a), y = rr * Math.sin(a);
    if (i === 0) sh.moveTo(x, y);
    else sh.lineTo(x, y);
  }
  return sh;
}

/**
 * Superseal 1.5 ikili konnektörün parçaları (Horpol TLA02318 seti: fiş + soket gövdesi, sarı kablo contaları; ölçüler TE
 * 282080 / 282104 ailesinden, ±1 mm). İç pinler yok (hep takılı). x0: fişin arka (kablo) yüzü; dir: gövdenin +X'e mi −X'e mi
 * uzandığı (fiş gövdesi x0'dan dir yönünde 16 mm). Kilit köprüsü gövdenin ön ucundan karşı parçanın kilit çıkıntısının üstüne
 * uzanır (reach: ön uçtan öteye mm).
 */
function supersealPlug(x0: number, dir: 1 | -1, reach: number, top: number) {
  const X = (v: number) => x0 + dir * v; // fişin arkasından öne mm → m
  const span = (a: number, b: number): [number, number] => (dir > 0 ? [X(a), X(b)] : [X(b), X(a)]);
  const black: THREE.BufferGeometry[] = [];
  const yellow: THREE.BufferGeometry[] = [];
  // gövde: oval kesitli, arkası iki kablo yuvasına bölünmüş (iki yuvarlak lob)
  black.push(extrudeX(rrectShape(0.0195, 0.0132, 0.0045), ...span(0.0025, 0.016), 0.0008));
  for (const z of [-0.0039, 0.0039]) {
    black.push(latheAt(dir > 0 ? [[X(0), 0], [X(0), 0.0044], [X(0.0026), 0.0049], [X(0.0026), 0]] : [[X(0.0026), 0], [X(0.0026), 0.0049], [X(0), 0.0044], [X(0), 0]], z, 12));
    // sarı kablo contası: yuvanın ağzından taşan sırtlı halka
    const c0 = X(-0.0002), c1 = X(0.0016);
    const [a, b] = dir > 0 ? [c0, c1] : [c1, c0];
    yellow.push(latheAt([[a, 0], [a, 0.0028], [(a + b) / 2, 0.0031], [b, 0.0029], [b, 0]], z, 8));
  }
  // kilit köprüsü (U): iki ray, öndeki kanca çubuğu, arkada basma dili; raylar gövdenin üstünden yükselen iki ayaktan çıkar
  const yb = top + 0.0016, yt = top + 0.0032;
  const [r0, r1] = span(0.0115, 0.016 + reach);
  for (const z of [-0.0046, 0.0046]) {
    black.push(box(r1 - r0, yt - yb, 0.0022, (r0 + r1) / 2, (yb + yt) / 2, z));
    const [p0, p1] = span(0.0115, 0.0145);
    black.push(box(p1 - p0, yt - 0.0062, 0.0022, (p0 + p1) / 2, (0.0062 + yt) / 2, z));
  }
  const [h0, h1] = span(0.016 + reach - 0.0026, 0.016 + reach);
  black.push(new RoundedBoxGeometry(h1 - h0, yt - top + 0.0006, 0.0114, 1, 0.0004).translate((h0 + h1) / 2, (top - 0.0006 + yt) / 2, 0));
  const [g0, g1] = span(0.0105, 0.0135);
  black.push(new RoundedBoxGeometry(g1 - g0, 0.0016, 0.0114, 1, 0.0005).translate((g0 + g1) / 2, yt + 0.0007, 0));
  return { black, yellow };
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
  } else if (type === 'ssPlug' || type === 'ssCap') {
    // Superseal 1.5 fiş (Horpol TLA02318, lambadaki 16 × 14 mm soket ağzına): ön yüz x = 0'da sokete dayanır, gövde −X'e 16 mm;
    // kilit köprüsü sokete doğru 12 mm uzanır, lambadaki soketin kilit dilinin üstünden geçip arkasına kancalanır. Arkada iki sarı
    // kablo contası, iki tel ve koruge ucu. ssCap: kablosuz kör tapa (boş çıkış), arkası kapalı
    if (type === 'ssPlug') {
      const pl = supersealPlug(-0.016, 1, 0.012, 0.0066);
      const wires = [-0.0039, 0.0039].map((z) => new THREE.CylinderGeometry(0.0013, 0.0013, 0.007, 6, 1, true).rotateZ(Math.PI / 2).translate(-0.0195, 0, z));
      const tail = boot(-0.0225, -0.038, 0.0058, 0.0040);
      c.nylon = merge(pl.black);
      c.black = merge([...wires, tail]);
      c.yellow = merge(pl.yellow);
    } else {
      const capBody = extrudeX(rrectShape(0.0195, 0.0132, 0.0045), -0.009, 0, 0.0008);
      const pull = extrudeX(rrectShape(0.010, 0.0042, 0.0021), -0.0135, -0.0085, 0.0006);
      const ring = latheX([[-0.0162, 0], [-0.0162, 0.0038], [-0.0128, 0.0038], [-0.0128, 0]], 18);
      const yb = 0.0082, yt = 0.0098;
      const bridge = [-0.0046, 0.0046].map((z) => new RoundedBoxGeometry(0.0175, yt - yb, 0.0022, 1, 0.0004).translate(0.0012, (yb + yt) / 2, z));
      const hook = new RoundedBoxGeometry(0.0026, yt - 0.006, 0.0114, 1, 0.0004).translate(0.0087, (0.006 + yt) / 2, 0);
      c.nylon = merge([capBody, pull, ring, ...bridge, hook]);
    }
  } else if (type === 'ss') {
    // Superseal 1.5 hat içi çift (Horpol TLA02318; lambanın kısa kablosunun ucunda), takılı: −X'te soket gövdesi (oval ağızlı
    // kılıf, üstte kilit çıkıntısı, arkada iki kablo yuvası + sarı contalar), +X'te fiş (gövdenin içine giren oval burun, U kilit
    // köprüsü çıkıntının üstünden kancalanmış, arkada sarı contalar). Uçlarda iki tel ve koruge ucu: x ±0,038'de kablo çapında
    const nylon: THREE.BufferGeometry[] = [];
    const yellow: THREE.BufferGeometry[] = [];
    // soket gövdesi: arkada ikiz yuva (iki silindir + uç flanşı), önde kılıf (ağız tarafı içi oyuk: fiş burnu içine girer)
    for (const z of [-0.0039, 0.0039]) {
      nylon.push(latheAt([[-0.0255, 0], [-0.0255, 0.0047], [-0.0238, 0.0047], [-0.0236, 0.0042], [-0.013, 0.0042], [-0.013, 0]], z, 12));
      yellow.push(latheAt([[-0.0262, 0], [-0.0262, 0.0028], [-0.0257, 0.0031], [-0.0252, 0.0029], [-0.0252, 0]], z, 8));
    }
    nylon.push(extrudeX(rrectShape(0.0186, 0.0098, 0.0049), -0.0145, -0.012, 0.0004));
    const shroud = rrectShape(0.0222, 0.0158, 0.0052);
    nylon.push(extrudeX(shroud, -0.0125, -0.003, 0.0008));
    const mouth = rrectShape(0.0222, 0.0158, 0.0052);
    mouth.holes.push(rrectShape(0.0200, 0.0136, 0.0045) as unknown as THREE.Path);
    nylon.push(extrudeX(mouth, -0.0035, 0.004, 0.0002));
    // kilit çıkıntısı (rampa) ve yan kodlama kaburgaları
    nylon.push(new RoundedBoxGeometry(0.0042, 0.0018, 0.005, 1, 0.0005).translate(0.0013, 0.0086, 0));
    for (const z of [-0.0115, 0.0115]) nylon.push(box(0.009, 0.0034, 0.0014, -0.0075, 0, z));
    // fiş: burun (kılıfın ağzında görünen kısım) + gövde, kilit köprüsü soket gövdesinin kilit çıkıntısına uzanır
    nylon.push(extrudeX(rrectShape(0.0199, 0.0135, 0.0045), -0.001, 0.0045, 0.0003));
    const pl = supersealPlug(0.0205, -1, 0.0055, 0.0066);
    nylon.push(...pl.black);
    yellow.push(...pl.yellow);
    // teller ve koruge uçları
    const wire = (x: number) => [-0.0039, 0.0039].map((z) => new THREE.CylinderGeometry(0.0013, 0.0013, 0.0075, 6, 1, true).rotateZ(Math.PI / 2).translate(x, 0, z));
    const black = [...wire(-0.029), ...wire(0.0245), boot(-0.0285, -0.038, 0.0058, 0.0042), boot(0.025, 0.038, 0.0058, 0.0042)];
    c.nylon = merge(nylon);
    c.yellow = merge(yellow);
    c.black = merge(black);
  } else if (type === 'amp' || type === 'ampPair') {
    // AMP 7 pin (Horpol TWTAMP7P fiş seti ve lambalardaki AMP soketi, ürün fotoğrafları amp-7-pin / twtamp7p): fişte boyuna
    // kanallı bağlantı somunu, ince halkalı arka kabuk, iki parçalı kablo kelepçesi (kafes) ve koruge ucu. 'amp': lambanın soketine
    // takılı fiş, ön yüz x = 0, gövde −X (Ø 13 kabloya). 'ampPair': hat içi çift, ortası x = 0: −X'te soket (bayonet sırtlı gövde,
    // yeşil contalı flanş, kulaklar), +X'te fiş. İç pinler yok (hep takılı)
    // fiş +X yönünde kurulur (dönel profiller artan x ile: yüzeyler dışa bakar); −X için Y ekseninde 180° döndürülür (aynalama yok)
    const plug = (s: 1 | -1) => {
      // kanallı kesitte pah içe kaydırılınca kapak üçgenlenmesi bozuluyordu: pahsız uzatma, uçlarda pahı dönel halkalar verir
      const nut = extrudeX(flutedShape(0.0186, 0.0013, 14), 0.0012, 0.0238, 0, 4);
      const nutEnds = [latheX([[0, 0], [0, 0.0168], [0.0012, 0.018], [0.0012, 0]], 32), latheX([[0.0238, 0], [0.0238, 0.018], [0.025, 0.0168], [0.025, 0]], 32)];
      const lip = latheX([[0, 0], [0, 0.0172], [0.0025, 0.0176], [0.0025, 0]], 32);
      const kp: [number, number][] = [[0.025, 0], [0.025, 0.0158]];
      for (let i = 1; i <= 5; i++) {
        const x = 0.025 + (0.019 * i) / 6;
        const r = 0.0158 - 0.0004 * i;
        kp.push([x - 0.0011, r], [x - 0.0004, r - 0.0009], [x + 0.0004, r - 0.0009], [x + 0.0011, r - 0.0002]);
      }
      kp.push([0.044, 0.0134], [0.044, 0]);
      const shell = latheX(kp, 28);
      // kablo kelepçesi: iki yarım kabuk (ortada ayrım çizgisi), yanlarda geçme dilleri
      const clamp = latheX([[0.044, 0], [0.044, 0.0128], [0.046, 0.0124], [0.062, 0.0112], [0.064, 0.0102], [0.064, 0]], 24);
      const tabs = [-1, 1].map((z) => new RoundedBoxGeometry(0.0085, 0.0036, 0.0034, 1, 0.0006).translate(0.054, 0, z * 0.0124));
      const seam = [-1, 1].map((y) => new THREE.BoxGeometry(0.017, 0.0006, 0.0262).translate(0.054, y * 0.0003, 0));
      const tail = boot(0.0635, 0.075, 0.0096, 0.0072);
      const out = { nylon: [nut, ...nutEnds, lip, shell, clamp, ...tabs], black: [tail], seam };
      if (s < 0) for (const g of [...out.nylon, ...out.black, ...out.seam]) g.rotateY(Math.PI);
      return out;
    };
    if (type === 'amp') {
      const p = plug(-1);
      // tek fişte gövde lambanın soketine kadar (somun ağzı soketin yeşil contalarının üstüne): kuyruk 0,08'e uzar
      const tail2 = boot(-0.072, -0.08, 0.0080, 0.0068);
      c.nylon = merge(p.nylon);
      c.black = merge([...p.black, tail2]);
      c.grey = merge(p.seam);
    } else {
      const p = plug(1);
      // soket: bayonet sırtlı ön gövde (somunun içine girer, ağızda görünür), yeşil conta + kulaklı flanş, arka kabuk, kelepçe
      const front = latheX([[-0.004, 0], [-0.004, 0.0168], [0, 0.0168], [0, 0]], 28);
      const flange = extrudeX(rrectShape(0.047, 0.036, 0.016), -0.0075, -0.004, 0.0006);
      const seal = latheX([[-0.0042, 0], [-0.0042, 0.0206], [-0.0036, 0.0212], [-0.0008, 0.0212], [-0.0002, 0.0206], [-0.0002, 0]], 36);
      const body = latheX([[-0.03, 0], [-0.03, 0.0152], ...ribs(-0.0295, -0.0085, 0.0152, 0.0011, 5), [-0.0075, 0.0158], [-0.0075, 0]], 28);
      const back = latheX([[-0.047, 0], [-0.047, 0.0128], [-0.045, 0.0136], [-0.032, 0.0142], [-0.03, 0.0145], [-0.03, 0]], 24);
      const clamp = latheX([[-0.0635, 0], [-0.0635, 0.0102], [-0.0615, 0.0112], [-0.049, 0.0124], [-0.047, 0.0128], [-0.047, 0]], 24);
      const tabs = [-1, 1].map((z) => new RoundedBoxGeometry(0.0085, 0.0036, 0.0034, 1, 0.0006).translate(-0.055, 0, z * 0.0122));
      const tail = boot(-0.075, -0.0635, 0.0072, 0.0096);
      c.nylon = merge([...p.nylon, front, flange, body, back, clamp, ...tabs]);
      c.black = merge([...p.black, tail]);
      c.green = merge([seal]);
      c.grey = merge(p.seam);
    }
  } else if (type === 'tee') {
    // yan hat bağlantısı (kalıplanmış T ek): hat üzerinde yuvarlatılmış gövde, üstte vidalı kapak, dal (+Z) lambanın kablosuna;
    // üç koruge ucu
    const body = new RoundedBoxGeometry(0.032, 0.019, 0.026, 2, 0.0055);
    const neck = extrudeX(rrectShape(0.016, 0.014, 0.006), -0.007, 0.007, 0.0008).rotateY(Math.PI / 2).translate(0, 0, 0.012);
    const lid = new RoundedBoxGeometry(0.022, 0.003, 0.017, 1, 0.0012).translate(0, 0.0098, -0.001);
    const screws = [-0.0075, 0.0075].map((x) => new THREE.CylinderGeometry(0.0017, 0.0017, 0.0012, 12).translate(x, 0.0118, -0.001));
    const br = boot(0.019, 0.03, 0.0062, 0.0042);
    br.rotateY(-Math.PI / 2);
    const end = [boot(-0.028, -0.0155, 0.0068, 0.0084), boot(0.028, 0.0155, 0.0068, 0.0084)];
    c.nylon = merge([body, neck, lid]);
    c.black = merge([br, ...end]);
    c.grey = merge(screws);
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
 * Gerçek ölçü (kablolar artık gerçek çapta; önceki 1,35 kat büyütme kalktı, ölçüler doğrulanmadı). Şemadaki gibi iki yüzde de
 * soldan sağa 3 Superseal ve en sağda büyük yuvarlak soket. Üstten bakışta (ön yukarıda) sağ = dünya −z.
 */
const MK = 0.74;
export const MODULE = {
  hx: 0.15 * MK,
  hz: 0.25 * MK,
  h: 0.085 * MK,
  /** Superseal portlarının z'si (soldan sağa) ve büyük soketin z'si (en sağ) */
  small: [0.165 * MK, 0.085 * MK, 0.005 * MK] as const,
  big: -0.13 * MK,
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
  add(new RoundedBoxGeometry(hx * 2, h, hz * 2, 3, 0.018 * MK), mats.plastic);
  add(new RoundedBoxGeometry(hx * 2 + 0.018 * MK, 0.03 * MK, hz * 2 + 0.018 * MK, 2, 0.012 * MK), mats.connWhite, 0, -h * 0.18);
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) add(new RoundedBoxGeometry(0.066 * MK, h * 0.86, 0.066 * MK, 2, 0.016 * MK), mats.connWhite, sx * (hx - 0.016 * MK), -0.002, sz * (hz - 0.016 * MK));
    // vida kulakları (yan uçların ortasında)
    add(new THREE.CylinderGeometry(0.021 * MK, 0.021 * MK, 0.014 * MK, 16), mats.connWhite, 0, -h / 2 + 0.007 * MK, sx * (hz + 0.024 * MK));
  }
  add(new RoundedBoxGeometry(hx * 1.3, 0.008 * MK, hz * 1.3, 2, 0.004 * MK), mats.socket, 0, h / 2);
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(0.27 * MK, (0.27 * MK * 528) / 720), mats.logoWhite);
  logo.rotation.set(-Math.PI / 2, 0, Math.PI / 2);
  logo.position.y = h / 2 + 0.0045 * MK;
  g.add(logo);
  // port ağızları: Superseal dikdörtgen yuva, yuvarlak 7 pin yuva (fişler kablo yüksekliğinde, y = PORT_Y)
  const ports = [...MODULE.small.map((z) => ({ z, t: 'S' })), { z: MODULE.big, t: 'R' }];
  for (const face of [-1, 1]) {
    for (const p of ports) {
      // port: gövdeden MODULE.lip kadar çıkan yuva; dış yüz gövdeden uzakta (fiş buraya dayanır)
      const [x0, x1] = face > 0 ? [hx - 0.002, hx + MODULE.lip] : [-(hx + MODULE.lip), -(hx - 0.002)];
      const outer = face > 0 ? x1 : x0;
      const inn = (d: number): [number, number] => (face > 0 ? [outer - d, outer] : [outer, outer + d]);
      if (p.t === 'S') {
        // Superseal soket kılıfı (lambadaki LZD 3194 soketiyle aynı aile): oval ağız (16,2 × 14,2), et 2,6 mm, ağızda dibe kadar
        // oyuk; dipte gri kontak tabanı; üstte fişin kilit köprüsünün kancalandığı çıkıntı; tabanda gövdeye geçen kare flanş
        add(extrudeX(rrectShape(0.029, 0.025, 0.004, -p.z, PORT_Y), ...(face > 0 ? [hx - 0.002, hx + 0.003] : [-(hx + 0.003), -(hx - 0.002)]) as [number, number], 0.0008), mats.plastic);
        const mouth = rrectShape(0.0214, 0.0194, 0.0058, -p.z, PORT_Y);
        mouth.holes.push(rrectShape(0.0162, 0.0142, 0.0045, -p.z, PORT_Y) as unknown as THREE.Path);
        add(extrudeX(mouth, x0, x1, 0.0004), mats.plastic);
        // ağzın dibi (dış yüzden 13 mm içeride, 0,8 mm kalınlık)
        const fd = MODULE.lip - 0.001;
        const floor: [number, number] = face > 0 ? [outer - fd - 0.0008, outer - fd] : [outer + fd, outer + fd + 0.0008];
        add(extrudeX(rrectShape(0.0162, 0.0142, 0.0045, -p.z, PORT_Y), ...floor, 0), mats.socketGrey);
        const [r0, r1] = inn(0.0075);
        add(new RoundedBoxGeometry(r1 - r0, 0.002, 0.005, 1, 0.0005), mats.plastic, (r0 + r1) / 2, PORT_Y + 0.0107, p.z);
      } else {
        // yuvarlak 7 pin soket (ISO 1185 fişi Ø 35): sırtlı bayonet halkası, ağızda gri kontak tabanı, tabanda flanş
        const flangeX: [number, number] = face > 0 ? [hx - 0.002, hx + 0.003] : [-(hx + 0.003), -(hx - 0.002)];
        add(latheX([[flangeX[0], 0], [flangeX[0], 0.0285], [flangeX[1], 0.0285], [flangeX[1], 0]], 32).translate(0, PORT_Y, p.z), mats.plastic);
        add(latheX([[x0, 0], [x0, 0.0232], ...ribs(x0 + 0.0015, x1 - 0.0015, 0.0232, 0.0012, 4), [x1, 0.0232], [x1, 0]], 32).translate(0, PORT_Y, p.z), mats.plastic);
        const [g0, g1] = inn(0.0012);
        add(latheX([[g0, 0], [g0, 0.0186], [g1, 0.0186], [g1, 0]], 28).translate(face * 0.0002, PORT_Y, p.z), mats.socketGrey);
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
const PORT_Y = -0.012 * MK;

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
