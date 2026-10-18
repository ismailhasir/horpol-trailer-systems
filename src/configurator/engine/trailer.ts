// Dorse geometrisi (prosedürel). Koordinatlar metre: X boyuna (arka yüz x=0, ön x=-L), Y yukarı, Z yanal (+Z sağ).
// Her tip ortak şasiyi kullanır, üstüne kendi gövdesini kurar ve lamba/tesisat için bağlantı noktalarını (anchors) döndürür.
// Gerçek GLB modeller geldiğinde bu dosya, model + adlandırılmış bağlantı noktası okuyan bir yükleyiciyle değişecek.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { TrailerId } from '../data';
import type { Mats } from './materials';
import { buildTanker, tankerLength, type TankerBuild } from './tanker';
import { DAMPER, DAMPER_BODY_GLB, DAMPER_GLB, damperSections } from './damper';
import { STANDART, STANDART_BODY_GLB, STANDART_GLB, standartContact, standartSections } from './standart';
import { loadedModel } from './models';
import { box, boxes, cyl, isShared, markShared, mesh, pipe, range, ribbon, rod, slab, V3, wheel } from './geo';

/** Blender'da modellenen tipler: [şasi + tekerlekler, kasa]. Yüklenene kadar kodla çizilen yedek görünür. */
const MODELS: Partial<Record<TrailerId, [string, string]>> = {
  damper: [DAMPER_GLB, DAMPER_BODY_GLB],
  standart: [STANDART_GLB, STANDART_BODY_GLB],
};
export const modelUrls = (type: TrailerId) => MODELS[type] ?? null;

export interface Pt {
  x: number;
  y: number;
  z: number;
}

export interface Anchors {
  L: number;
  W: number;
  topY: number;
  /** dropX: arka lambalara ve plakaya inen kablo dallarının x'i (verilmezse x - 0.08) */
  rear: { x: number; lampY: number; lampZ: [number, number]; plateY: number; dropX?: number };
  /** brackets: markerlar şasiye kendi braketleriyle bağlanır (gövdede yan duvar/ray yok) */
  side: { x0: number; x1: number; z: number; yAt: (x: number) => number; brackets?: boolean };
  front: Pt;
  armRear: Pt;
  armFront: Pt;
  /** ek lambalar: arka üst köşeler (kapalı gövdeli tipler) ya da tampon uçları; z0 dış, z1 iç sıra */
  extra: { x: number; y: number; z0: number; z1: number };
  socket: { x: number; y: number; onWall: boolean };
  /** profile: tesisatın taban boyunca izlediği yükseklik [x, y] (x artan); boyunlu/basamaklı tiplerde kademeli */
  /** trunkZ / rearZ: yan ana hattın ve arka hatların yanal konumu (verilmezse 0,85 / 0,62) */
  harness: { y: number; railZ: number; junctionX: number; frontX: number; profile: [number, number][]; trunkZ?: number; rearZ?: number };
  center: THREE.Vector3;
  size: THREE.Vector3;
}

export interface TrailerBuild {
  group: THREE.Group;
  body: THREE.Group;
  /** sistem (tesisat) görünümünde açılan gövde çizgileri + zemin plakası */
  outline: THREE.Group;
  /** tesisat görünümünde yarı saydam çizilen gövde, şasi ve tekerlek parçaları */
  solids: THREE.Mesh[];
  /** true: tesisat görünümünde gövde gizlenir, şasi gerçek malzemesiyle kalır (tanker) */
  realChassis: boolean;
  anchors: Anchors;
}

/** Profil üzerinde x'teki yükseklik (doğrusal ara değer) */
export function profileAt(prof: [number, number][], x: number) {
  if (x <= prof[0][0]) return prof[0][1];
  for (let i = 1; i < prof.length; i++) {
    const [x1, y1] = prof[i];
    if (x <= x1) {
      const [x0, y0] = prof[i - 1];
      return x1 === x0 ? y1 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
    }
  }
  return prof[prof.length - 1][1];
}

const W = 2.55;

// ---------- temsilî otomobil (araç taşıyıcı yükü) ----------
function car(g: THREE.Object3D, m: Mats, x: number, y: number, paint: THREE.Material) {
  const c = new THREE.Group();
  // gövde (kaput ve bagaj biraz alçak), gövde renginde kabin, kabini çevreleyen koyu cam bandı
  box(c, 3.9, 0.5, 1.72, paint, 0, 0.57, 0, 0.16);
  box(c, 2.5, 0.12, 1.66, paint, -0.1, 0.86, 0, 0.05);
  box(c, 1.9, 0.44, 1.46, paint, -0.2, 1.1, 0, 0.14);
  box(c, 1.96, 0.24, 1.5, m.plastic, -0.2, 1.08, 0, 0.08);
  for (const wx of [-1.3, 1.25]) for (const s of [-1, 1]) cyl(c, 0.31, 0.2, m.tread, 'z', wx, 0.31, s * 0.74, 18);
  c.position.set(x, y, 0);
  c.traverse((o) => (o.userData.cargo = true));
  g.add(c);
}

// ---------- şasi ----------
interface ChassisOpts {
  L: number;
  deckY: number;
  R: number;
  axles: number[];
  landingX: number;
  sideGuard: boolean;
  rail: boolean;
  lampY: number;
  plateY: number;
  beamFrom?: number;
  /** yükseltilmiş ön boyun (king pin ve iniş ayağı buna göre) */
  frontDeckY?: number;
  /** traversler: aralık ve genişlik (iskelet şasilerde seyrek ve dar) */
  crossStep?: number;
  crossW?: number;
  /** yan ray malzemesi ve üstündeki reflektif kontur bandı (yoksa mavi şerit) */
  railMat?: THREE.Material;
  tape?: THREE.Material;
  /** çamurluk: tek parça düz (tenteli/frigo), aks başına kavisli (damper/silobas), yok (tabla tekerleği örter) */
  fender?: 'flat' | 'arch' | 'none';
  hubMat?: THREE.Material;
  /** arka lamba barı malzemesi (lowbed: gövde boyası) */
  barMat?: THREE.Material;
  /** kiriş ve travers boyası (silobas: beyaz) */
  frameMat?: THREE.Material;
  /** king pin plakasının yüksekliği (verilmezse ana kirişlerin altı) */
  kingY?: number;
}
function chassis(g: THREE.Group, m: Mats, o: ChassisOpts) {
  const { L, deckY, R } = o;
  const fy = o.frontDeckY ?? deckY;
  const beamH = Math.min(0.42, deckY - 2 * R + 0.05);
  const beamY = deckY - 0.08 - beamH / 2;
  const from = o.beamFrom ?? -L + 0.25;
  // ana kirişler
  const fm = o.frameMat ?? m.chassis;
  for (const z of [-0.5, 0.5]) box(g, -0.15 - from, beamH, 0.1, fm, (from - 0.15) / 2, beamY, z);
  // traversler
  boxes(g, 0.06, 0.1, o.crossW ?? 2.2, fm, range(from + 0.3, -0.4, o.crossStep ?? 0.55).map((x) => [x, deckY - 0.13, 0]));
  // dış yan ray + kontur bandı (kesik sarı reflektif şerit) ya da marka şeridi
  if (o.rail) {
    for (const z of [-1, 1]) {
      box(g, L - 0.04, 0.22, 0.05, o.railMat ?? m.alu, -L / 2, deckY - 0.12, z * (W / 2 - 0.025));
      if (o.tape) boxes(g, 0.5, 0.035, 0.006, o.tape, range(-L + 0.4, -0.4, 0.78).map((x) => [x, deckY - 0.055, z * (W / 2 + 0.0005)]));
      else box(g, L - 0.06, 0.035, 0.006, m.stripe, -L / 2, deckY - 0.06, z * (W / 2 + 0.0005));
    }
  }
  // akslar, hava körükleri, salıncak kolları, amortisörler, tekerlekler
  for (const x of o.axles) {
    cyl(g, 0.065, 2.05, m.darkMetal, 'z', x, R, 0);
    for (const z of [-0.52, 0.52]) {
      cyl(g, 0.13, 0.22, m.rubber, 'y', x - 0.35, R + 0.2, z, 18);
      box(g, 0.75, 0.08, 0.1, m.darkMetal, x - 0.15, R + 0.04, z);
      rod(g, V3(x + 0.12, R + 0.02, z * 1.12), V3(x + 0.2, R + 0.34, z * 1.12), 0.03, m.darkMetal, 8);
    }
    for (const s of [1, -1] as const) {
      const wh = wheel(m, R, s, o.hubMat);
      wh.position.set(x, R, s * (W / 2 - 0.33));
      g.add(wh);
    }
  }
  if (o.axles.length) {
    const xs = o.axles;
    const front = Math.min(...xs) - R - 0.2;
    const back = Math.max(...xs) + R + 0.2;
    const fender = o.fender ?? 'flat';
    for (const z of [-1, 1]) {
      const zc = z * (W / 2 - 0.33);
      if (fender === 'flat') {
        box(g, back - front, 0.025, 0.62, m.plastic, (front + back) / 2, 2 * R + 0.09, zc);
        box(g, back - front, 0.1, 0.02, m.plastic, (front + back) / 2, 2 * R + 0.04, zc + z * 0.3);
      } else if (fender === 'arch') {
        // aks başına kavisli çamurluk: üstü saran açık silindir kabuk
        const geo = new THREE.CylinderGeometry(R + 0.07, R + 0.07, 0.5, 28, 1, true, Math.PI - 1.15, 2.3);
        geo.rotateX(Math.PI / 2);
        for (const x of xs) {
          const f = mesh(geo, m.fender);
          f.position.set(x, R, zc);
          g.add(f);
        }
      }
      // son aksın arkasında çamurluk paçası (alçak tablalarda tablanın altında kalır)
      const top = Math.min(2 * R + 0.07, deckY - 0.38);
      const bot = 2 * R - 0.475;
      box(g, 0.02, top - bot, 0.6, m.rubber, back + 0.02, (top + bot) / 2, zc);
    }
  }
  // iniş ayağı (üst ucu tablanın altında kalır)
  for (const z of [-0.62, 0.62]) {
    const h = fy - 0.72;
    box(g, 0.14, h, 0.14, m.darkMetal, o.landingX, 0.6 + h / 2, z);
    box(g, 0.1, 0.5, 0.1, m.alu, o.landingX, 0.38, z);
    box(g, 0.32, 0.04, 0.3, m.darkMetal, o.landingX, 0.12, z);
  }
  box(g, 0.06, 0.06, 1.2, m.darkMetal, o.landingX, 0.75, 0);
  cyl(g, 0.05, 0.1, m.darkMetal, 'z', o.landingX, fy - 0.35, 0.72, 16);
  // king pin plakası (şasinin altına oturur)
  const ky = o.kingY ?? (o.frontDeckY !== undefined ? fy - 0.52 : beamY - beamH / 2 - 0.025);
  box(g, 1.6, 0.05, 1.6, m.darkMetal, -L + 1.0, ky, 0);
  cyl(g, 0.045, 0.1, m.steel, 'y', -L + 1.2, ky - 0.075, 0, 16);
  // yan koruma (alüminyum ray)
  if (o.sideGuard && o.axles.length) {
    const x0 = o.landingX + 0.45;
    const x1 = Math.min(...o.axles) - R - 0.35;
    if (x1 - x0 > 1) {
      for (const z of [-1, 1]) {
        for (const y of [0.62, 0.92]) box(g, x1 - x0, 0.1, 0.03, m.alu, (x0 + x1) / 2, y, z * (W / 2 - 0.06));
        for (const x of [x0 + 0.05, (x0 + x1) / 2, x1 - 0.05]) box(g, 0.05, deckY - 0.6, 0.05, m.darkMetal, x, (deckY + 0.55) / 2, z * (W / 2 - 0.09));
      }
    }
  }
  // arka koruma tamponu (alüminyum boru, uç kapaklı) + taşıyıcılar + lamba barı + plaka tutucu
  cyl(g, 0.055, 2.3, m.alu, 'z', -0.2, 0.5, 0, 24);
  for (const z of [-1, 1]) cyl(g, 0.06, 0.04, m.plastic, 'z', -0.2, 0.5, z * 1.17, 24);
  for (const z of [-0.55, 0.55]) box(g, 0.08, o.lampY - 0.5, 0.08, m.darkMetal, -0.24, (o.lampY + 0.5) / 2, z);
  box(g, 0.1, 0.24, W - 0.06, o.barMat ?? m.chassis, -0.07, o.lampY, 0, 0.01);
  box(g, 0.04, 0.2, 0.62, m.chassis, -0.04, o.plateY, 0);
}

// ---------- plaka ----------
let plateTex: THREE.CanvasTexture | null = null;
function plateTexture() {
  if (plateTex) return plateTex;
  const c = document.createElement('canvas');
  c.width = 520;
  c.height = 110;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#f6f6f1';
  ctx.fillRect(0, 0, 520, 110);
  ctx.fillStyle = '#1f4fa8';
  ctx.fillRect(0, 0, 46, 110);
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 30px Arial';
  ctx.fillText('TR', 4, 92);
  ctx.fillStyle = '#111';
  ctx.font = 'bold 76px Arial';
  ctx.fillText('34 HRP 2026', 62, 84);
  ctx.strokeStyle = '#222';
  ctx.lineWidth = 4;
  ctx.strokeRect(2, 2, 516, 106);
  plateTex = new THREE.CanvasTexture(c);
  plateTex.colorSpace = THREE.SRGBColorSpace;
  plateTex.anisotropy = 8;
  return plateTex;
}
let plateMat: THREE.MeshStandardMaterial | null = null;
const PLATE_GEO = markShared(new THREE.PlaneGeometry(0.52, 0.11));
function plate(g: THREE.Group, y: number, x = -0.015) {
  plateMat ??= new THREE.MeshStandardMaterial({ map: plateTexture(), roughness: 0.35, metalness: 0.1 });
  const p = mesh(PLATE_GEO, plateMat, false);
  p.rotation.y = Math.PI / 2;
  p.position.set(x, y, 0);
  g.add(p);
}

// ---------- logo ----------
function logos(g: THREE.Group, mat: THREE.Material, x: number, y: number, zHalf: number, h = 2.3) {
  const w = h * (720 / 528);
  for (const s of [1, -1]) {
    const p = mesh(new THREE.PlaneGeometry(w, h), mat, false, false);
    p.position.set(x, y, s * (zHalf + 0.004));
    if (s < 0) p.rotation.y = Math.PI;
    g.add(p);
  }
}

// ---------- arka kapılar ----------
/** ECE R70 uzun araç plakası (dikey); `rotZ` ile yatay */
function r70(g: THREE.Object3D, m: Mats, x: number, y: number, z: number, rotZ = 0) {
  const p = mesh(new THREE.PlaneGeometry(0.2, 0.565), m.r70, false, false);
  p.rotation.set(0, Math.PI / 2, rotZ);
  p.position.set(x, y, z);
  p.userData.noEdge = true;
  g.add(p);
}
function rearDoors(g: THREE.Group, m: Mats, y0: number, H: number, mat: THREE.Material, frame: THREE.Material = m.alu) {
  const dw = (W - 0.12) / 2;
  for (const s of [-1, 1]) {
    box(g, 0.05, H - 0.1, dw - 0.02, mat, 0.005, y0 + H / 2, s * (dw / 2 + 0.01), 0.01);
    for (const zz of [0.22, 0.62]) {
      cyl(g, 0.018, H - 0.25, m.chrome, 'y', 0.05, y0 + H / 2, s * zz, 12);
      box(g, 0.05, 0.04, 0.06, m.darkMetal, 0.04, y0 + 0.25, s * zz);
      box(g, 0.05, 0.04, 0.06, m.darkMetal, 0.04, y0 + H - 0.25, s * zz);
    }
    for (const yy of [0.35, H * 0.36, H * 0.64, H - 0.35]) box(g, 0.05, 0.08, 0.14, m.darkMetal, 0.035, y0 + yy, s * (W / 2 - 0.1));
    box(g, 0.07, 0.07, 0.12, m.darkMetal, 0.05, y0 + H * 0.45, s * 0.42);
    // ECE R70 plakaları (kapı dış kenarlarında)
    r70(g, m, 0.032, y0 + H * 0.42, s * 0.95);
  }
  // kasa çerçevesi (dikmeler + üst kiriş) ve üzerinde kırmızı reflektif kontur
  box(g, 0.08, H, 0.06, frame, 0.0, y0 + H / 2, W / 2 - 0.03);
  box(g, 0.08, H, 0.06, frame, 0.0, y0 + H / 2, -W / 2 + 0.03);
  box(g, 0.08, 0.12, W, frame, 0.0, y0 + H - 0.06, 0);
  for (const s of [-1, 1]) box(g, 0.004, H - 0.3, 0.04, m.reflRed, 0.042, y0 + H / 2 - 0.05, s * (W / 2 - 0.03));
  box(g, 0.004, 0.05, W - 0.1, m.reflRed, 0.042, y0 + H - 0.06, 0);
  // kapı contası
  box(g, 0.02, H - 0.08, 0.012, m.rubber, 0.03, y0 + H / 2, 0);
}

/** Frigorifik soğutma ünitesi (ön duvara asılı): yuvarlatılmış gövde, ön menfez ızgarası, kondenser girişi, yan panjurlar, kontrol paneli. */
function reefer(body: THREE.Group, m: Mats, L: number, topY: number) {
  const u = new THREE.Group();
  box(u, 0.5, 1.75, 2.15, m.paint, 0, 0, 0, 0.09);
  box(u, 0.03, 0.95, 1.62, m.grille, -0.255, 0.22, 0, 0.01);
  box(u, 0.035, 0.05, 1.7, m.alu, -0.255, 0.73, 0);
  box(u, 0.03, 0.36, 1.86, m.plastic, -0.255, -0.6, 0, 0.03);
  box(u, 0.02, 0.1, 0.32, m.plastic, -0.268, -0.28, 0.66, 0.01);
  for (const s of [-1, 1]) boxes(u, 0.28, 0.02, 0.01, m.plastic, range(-0.45, 0.45, 0.075).map((y) => [-0.05, y, s * 1.076]));
  u.position.set(-L - 0.26, topY - 1.05, 0);
  body.add(u);
}

/** V tipi silobas kabuğu: x ekseni boyunca, üst çizgisi `top`'ta sabit, yarıçapı ra→rb doğrusal değişen kesik koni (analitik normal). */
function siloCone(xa: number, xb: number, ra: number, rb: number, top: number, seg = 72) {
  const pos: number[] = [];
  const nor: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  const dr = (rb - ra) / (xb - xa);
  const n = new THREE.Vector3();
  for (let j = 0; j <= 1; j++) {
    const x = j ? xb : xa;
    const r = j ? rb : ra;
    for (let i = 0; i <= seg; i++) {
      const a = (i / seg) * Math.PI * 2;
      pos.push(x, top - r + Math.cos(a) * r, Math.sin(a) * r);
      n.set(-dr * (1 - Math.cos(a)), Math.cos(a), Math.sin(a)).normalize();
      nor.push(n.x, n.y, n.z);
      uv.push(i / seg, j);
    }
  }
  for (let i = 0; i < seg; i++) {
    const c = seg + 1 + i;
    idx.push(i, i + 1, c, i + 1, c + 1, c);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

// ---------- gövde tipleri ----------
export function buildTrailer(type: TrailerId, L: number, m: Mats): TrailerBuild {
  // tanker: gerçek dorse boyu (set uzunluğu kablo setinindir, dorseyle birebir değil)
  if (type === 'tanker') L = tankerLength(L);
  // damper: Blender'da modellenen şasi yüklendiyse onu kullan (yoksa kodla çizilen yedek)
  const damperRig = type === 'damper' ? loadedModel(DAMPER_GLB) : null;
  const damperBody = damperRig ? loadedModel(DAMPER_BODY_GLB) : null;
  if (damperRig) L = DAMPER.L;
  // standart (kapalı kasa): Blender modeli tek boyda (13,7 m; set uzunluğundan bağımsız). Yüklenene kadar ya da
  // yüklenemezse aynı biçimde kodla çizilen kapalı kasa görünür.
  const stdRig = type === 'standart' ? loadedModel(STANDART_GLB) : null;
  const stdBody = stdRig ? loadedModel(STANDART_BODY_GLB) : null;
  if (type === 'standart' && !stdBody) type = 'kapali';
  if (stdBody) L = STANDART.L;
  const group = new THREE.Group();
  const body = new THREE.Group();
  const chassisG = new THREE.Group();
  group.add(chassisG, body);

  let deckY = 1.3;
  let R = 0.53;
  let topY = 4.0;
  let lampY = 1.02;
  let plateY = 0.74;
  let landingX = -L + 2.6;
  let sideGuard = true;
  let rail = true;
  let onWall = true;
  let socketY = deckY + 0.42;
  let frontPos: Pt | null = null;
  let armRearY = topY - 0.25;
  let armFrontY = topY - 0.25;
  let sideYAt = (_x: number) => deckY - 0.12;
  let harnessY = deckY - 0.04;
  let beamFrom: number | undefined;
  let frontDeckY: number | undefined;
  let crossStep: number | undefined;
  let crossW: number | undefined;
  let profile: [number, number][] | null = null;
  const n = L >= 12 ? 3 : 2;
  let axles = Array.from({ length: n }, (_, i) => -1.75 - i * 1.31);

  let railMat: THREE.Material | undefined;
  let tape: THREE.Material | undefined = m.reflYellow;
  let fender: ChassisOpts['fender'] = 'flat';
  let hubMat: THREE.Material | undefined;
  let barMat: THREE.Material | undefined;
  let frameMat: THREE.Material | undefined;
  let kingY: number | undefined;
  let sideX0 = -L + 1.0;
  let extraY: number | undefined;

  if (type === 'lowbed') {
    R = 0.4;
    deckY = 1.0;
    lampY = 0.8;
    plateY = 0.55;
    axles = [-1.4, -2.65, -3.9];
    landingX = -L + 1.7;
    sideGuard = false;
    rail = false;
    onWall = false;
    topY = 2.0;
    fender = 'none';
    barMat = m.paint;
  }
  if (type === 'tanker' || type === 'silo') {
    deckY = type === 'silo' ? 1.25 : 1.22;
    lampY = 0.96;
    plateY = 0.7;
    topY = 3.45;
    onWall = false;
    rail = false;
  }
  if (type === 'tanker') {
    kingY = deckY - 0.225;
    sideGuard = false;
    fender = 'arch';
    frameMat = m.paint;
    barMat = m.paint;
  }
  if (type === 'silo') {
    sideGuard = false;
    fender = 'arch';
    frameMat = m.paint;
    barMat = m.paint;
    kingY = deckY - 0.265;
  }
  if (type === 'arac') {
    deckY = 0.95;
    R = 0.4;
    lampY = 0.8;
    plateY = 0.55;
    topY = 4.1;
    onWall = false;
    sideGuard = false;
    rail = false;
    landingX = -L + 2.2;
    axles = [-1.35, -2.5, -3.65];
  }
  if (type === 'konteyner') {
    crossStep = 1.45;
    crossW = 1.15;
  }
  if (type === 'flatbed' || type === 'stepdeck' || type === 'konteyner') {
    onWall = false;
    tape = undefined;
  }
  if (type === 'damper') {
    topY = 3.0;
    railMat = m.chassis;
    fender = 'arch';
    if (damperRig) {
      deckY = DAMPER.top;
      topY = DAMPER.top + 1.6;
      lampY = DAMPER.lampY;
      plateY = DAMPER.plateY;
      harnessY = DAMPER.harnessY;
      sideYAt = () => DAMPER.side.y;
    }
  }

  const H = topY - deckY;
  /** Tesisat görünümünde kavisli gövdelerin biçimi okunsun diye çizilen ek kesit çizgileri (kapalı çokgenler) */
  const sections: THREE.Vector3[][] = [];
  /** ayrıntılı tanker modeli (engine/tanker.ts): kendi şasisini kurar, tesisat görünümünde şasi gerçek malzemesiyle kalır */
  let tanker: TankerBuild | null = null;

  // --- gövde ---
  if (type === 'standart' && stdBody) {
    // Blender kasası (yan paneller, profiller, oluklu ön panel, arka çerçeve ve kapılar, logolar); tesisatta gizlenir
    for (const mm of mergedFromModel(stdBody)) body.add(mm);
    topY = STANDART.topY;
    sections.push(...standartSections());
  } else if (type === 'kapali' || type === 'frigo') {
    const r = type === 'frigo' ? 0.07 : 0.025;
    box(body, L, H, W, m.paint, -L / 2, deckY + H / 2, 0, r);
    if (type === 'kapali') {
      boxes(body, 0.05, H - 0.1, W + 0.03, m.alu, range(-L + 0.6, -0.6, 1.2).map((x) => [x, deckY + H / 2, 0]));
      for (const y of [deckY + 0.06, topY - 0.06]) box(body, L + 0.01, 0.12, W + 0.03, m.alu, -L / 2, y, 0);
    } else {
      // Frigorifik: yekpare yalıtımlı gövde, alt ve üst alüminyum köşe profilleri, önde soğutma ünitesi,
      // şasi altında ünite yakıt deposu ve alet kutusu
      box(body, L + 0.01, 0.1, W + 0.03, m.alu, -L / 2, deckY + 0.05, 0);
      box(body, L - 0.12, 0.035, W + 0.012, m.alu, -L / 2, topY - 0.05, 0);
      reefer(body, m, L, topY);
      box(body, 0.7, 0.42, 0.5, m.alu, landingX + 0.9, deckY - 0.5, -(W / 2 - 0.4), 0.06);
      box(body, 0.9, 0.45, 0.45, m.paint, landingX + 1.4, deckY - 0.62, W / 2 - 0.35, 0.03);
    }
    rearDoors(body, m, deckY, H, m.paint, type === 'frigo' ? m.chassis : m.alu);
    logos(body, m.logo, -L / 2 + 0.6, deckY + H * 0.55, W / 2 + 0.024, 2.2);
    for (const z of [-1, 1]) box(body, L - 0.3, 0.06, 0.006, m.stripe, -L / 2, deckY + 0.25, z * (W / 2 + 0.017));
  } else if (type === 'flatbed' || type === 'stepdeck') {
    const upper = type === 'stepdeck' ? 3.4 : 0;
    const upY = 1.58;
    // ana platform
    box(body, L - upper - (upper ? 0.4 : 0), 0.12, W, m.deck, -(L - upper - (upper ? 0.4 : 0)) / 2, deckY - 0.06, 0);
    for (const z of [-1, 1]) {
      box(body, L - upper - (upper ? 0.4 : 0), 0.18, 0.06, m.chassis, -(L - upper - (upper ? 0.4 : 0)) / 2, deckY - 0.1, z * (W / 2 - 0.03));
      boxes(body, 0.06, 0.08, 0.05, m.darkMetal, range(-L + upper + 0.7, -0.4, 0.75).map((x) => [x, deckY - 0.09, z * (W / 2 + 0.01)]));
    }
    let headY = deckY;
    if (upper) {
      box(body, upper, 0.12, W, m.deck, -L + upper / 2, upY - 0.06, 0);
      box(body, upper, upY - deckY + 0.1, 1.2, m.chassis, -L + upper / 2, (upY + deckY) / 2 - 0.1, 0);
      const ramp = box(body, 0.6, 0.1, W, m.chassis, -L + upper + 0.2, (upY + deckY) / 2 - 0.08, 0);
      ramp.rotation.z = -0.68;
      for (const z of [-1, 1]) box(body, upper, 0.18, 0.06, m.chassis, -L + upper / 2, upY - 0.1, z * (W / 2 - 0.03));
      headY = upY;
      beamFrom = -L + upper + 0.3;
    }
    // ön duvar (başlık)
    const hh = 1.4;
    for (const z of [-1, 1]) box(body, 0.08, hh, 0.08, m.chassis, -L + 0.06, headY + hh / 2, z * (W / 2 - 0.05));
    box(body, 0.08, 0.08, W, m.chassis, -L + 0.06, headY + hh, 0);
    boxes(body, 0.03, hh - 0.1, 0.03, m.alu, range(-0.9, 0.9, 0.3).map((z) => [-L + 0.06, headY + hh / 2, z]));
    topY = headY + hh;
    frontPos = { x: -L + 0.02, y: headY + hh - 0.1, z: W / 2 - 0.06 };
    armRearY = deckY + 0.28;
    armFrontY = headY + 0.28;
    sideYAt = (x) => (upper && x < -L + upper ? upY - 0.12 : deckY - 0.12);
    socketY = (upper ? upY : deckY) - 0.12;
    // yük bağlama vinçleri (yan ray altında)
    for (const z of [-1, 1]) boxes(body, 0.16, 0.12, 0.12, m.darkMetal, range(-L + upper + 1.2, -1.0, 1.1).map((x) => [x, deckY - 0.3, z * (W / 2 - 0.12)]));
    if (upper) {
      frontDeckY = upY;
      profile = [
        [-L, upY - 0.04],
        [-L + upper, upY - 0.04],
        [-L + upper + 0.45, deckY - 0.04],
        [0, deckY - 0.04],
      ];
    }
  } else if (type === 'lowbed') {
    // Yarı lowbed: korkuluklu yükseltilmiş ön boyun (stepne üstünde), kaymaz çıtalı iniş rampası, küçük tekerlekler üzerinde
    // düz alçak ana tabla (kauçuk pedler, bağlama halkaları, yan cepler), arkada hidrolik pistonlu dik duran iki rampa.
    const pm = m.paint;
    const neck = 3.0;
    const nY = 1.55;
    const slope = 0.75;
    const xn = -L + neck;
    const xs = xn + slope;
    const sideBeam = (len: number, x: number, y: number) => {
      for (const z of [-1, 1]) box(body, len, 0.32, 0.1, pm, x, y - 0.2, z * (W / 2 - 0.05));
    };
    // boyun
    box(body, neck, 0.12, W, pm, -L + neck / 2, nY - 0.06, 0);
    sideBeam(neck, -L + neck / 2, nY);
    box(body, neck - 0.3, 0.42, 1.0, pm, -L + neck / 2 + 0.15, nY - 0.33, 0);
    box(body, 0.08, 0.42, W - 0.06, pm, -L + 0.04, nY - 0.27, 0);
    // ön tabla korkuluğu (yatay oluklu alçak duvar) ve stepne
    const bh = 0.5;
    box(body, 0.06, bh, W, pm, -L + 0.03, nY + bh / 2, 0);
    for (const z of [-1, 1]) {
      box(body, 1.6, bh, 0.05, pm, -L + 0.8, nY + bh / 2, z * (W / 2 - 0.025));
      for (const y of [0.17, 0.34]) box(body, 1.5, 0.025, 0.012, m.chassis, -L + 0.82, nY + y, z * (W / 2 + 0.001));
    }
    for (const y of [0.17, 0.34]) box(body, 0.012, 0.025, W - 0.1, m.chassis, -L - 0.001, nY + y, 0);
    const spare = wheel(m, R, 1);
    spare.position.set(-L + 0.62, nY + R + 0.01, 0.15);
    body.add(spare);
    // boyun rampası (kaymaz çıtalı)
    const ang = Math.atan2(nY - deckY, slope);
    const sl = Math.hypot(nY - deckY, slope);
    const rp = box(body, sl + 0.02, 0.12, W, pm, (xn + xs) / 2, (nY + deckY) / 2 - 0.06, 0);
    rp.rotation.z = -ang;
    for (const z of [-1, 1]) {
      const sb = box(body, sl + 0.02, 0.32, 0.1, pm, (xn + xs) / 2, (nY + deckY) / 2 - 0.2, z * (W / 2 - 0.05));
      sb.rotation.z = -ang;
    }
    for (let i = 0; i < 4; i++) {
      const t = (i + 0.5) / 4;
      for (const z of [-0.55, 0.55]) {
        const bar = box(body, 0.05, 0.025, 0.85, m.plastic, xn + t * slope, nY - t * (nY - deckY) + 0.01, z);
        bar.rotation.z = -ang;
      }
    }
    // ana tabla
    const dl = -xs;
    box(body, dl, 0.12, W, pm, xs / 2, deckY - 0.06, 0);
    sideBeam(dl, xs / 2, deckY);
    boxes(body, 0.95, 0.012, 0.55, m.plastic, range(xs + 0.6, -0.6, 1.3).flatMap((x): [number, number, number][] => [[x, deckY + 0.006, 0.66], [x, deckY + 0.006, -0.66]]));
    const ringGeo = new THREE.TorusGeometry(0.045, 0.009, 6, 16);
    for (const x of range(xs + 0.5, -0.6, 1.1)) {
      for (const z of [-1, 1]) {
        const ring = mesh(ringGeo, m.darkMetal);
        ring.position.set(x, deckY + 0.04, z * (W / 2 - 0.12));
        ring.userData.noEdge = true;
        body.add(ring);
      }
    }
    for (const z of [-1, 1]) boxes(body, 0.1, 0.07, 0.06, pm, range(xs + 0.3, -0.3, 0.8).map((x) => [x, deckY - 0.045, z * (W / 2 + 0.03)]));
    // arka rampalar: dik (hafif öne yatık), merdiven görünümlü; önlerinde hidrolik piston
    const tilt = 0.1;
    const rl = 2.5;
    const rw = 0.6;
    const hx = -0.08;
    for (const zr of [-0.68, 0.68]) {
      const rg = new THREE.Group();
      for (const zz of [-1, 1]) box(rg, 0.12, rl, 0.07, pm, 0, rl / 2, zz * (rw / 2 - 0.035));
      box(rg, 0.03, rl - 0.1, rw - 0.12, m.chassis, -0.02, rl / 2, 0);
      for (let y = 0.16; y < rl - 0.1; y += 0.32) box(rg, 0.1, 0.07, rw - 0.1, pm, 0, y, 0);
      box(rg, 0.12, 0.1, rw, pm, 0, rl - 0.05, 0);
      const wp = mesh(new THREE.PlaneGeometry(0.26, 0.42), m.warn, false, false);
      wp.rotation.y = Math.PI / 2;
      wp.position.set(0.062, 0.42, Math.sign(zr) * (rw / 2 - 0.15));
      rg.add(wp);
      box(rg, 0.02, 0.1, 0.1, m.reflYellow, 0.065, rl - 0.25, Math.sign(zr) * (rw / 2 - 0.1));
      rg.position.set(hx, deckY, zr);
      rg.rotation.z = tilt;
      body.add(rg);
      const at = (lx: number, ly: number) => V3(hx + lx * Math.cos(tilt) - ly * Math.sin(tilt), deckY + lx * Math.sin(tilt) + ly * Math.cos(tilt), zr);
      const base = V3(-0.95, deckY + 0.08, zr);
      const tip = at(-0.1, 1.5);
      const mid = base.clone().lerp(tip, 0.58);
      rod(body, base, mid, 0.055, m.plastic, 14);
      rod(body, mid, tip, 0.03, m.chrome, 12);
      box(body, 0.14, 0.08, 0.14, m.darkMetal, base.x, deckY + 0.04, zr);
    }
    beamFrom = xs + 0.1;
    topY = deckY + rl * Math.cos(tilt);
    frontPos = { x: -L - 0.005, y: nY + bh - 0.08, z: W / 2 - 0.08 };
    armRearY = deckY - 0.1;
    armFrontY = nY + 0.3;
    sideYAt = (x) => (x < xn ? nY - 0.12 : x < xs ? nY - 0.12 - ((x - xn) / slope) * (nY - deckY) : deckY - 0.12);
    socketY = nY - 0.25;
    harnessY = deckY - 0.1;
    frontDeckY = nY;
    profile = [
      [-L, nY - 0.2],
      [xn, nY - 0.2],
      [xs + 0.1, deckY - 0.1],
      [0, deckY - 0.1],
    ];
  } else if (type === 'damper' && damperBody) {
    // Blender kasası (siperlik, merdiven, arka kapak, logolar dahil)
    for (const mm of mergedFromModel(damperBody)) body.add(mm);
    topY = DAMPER.bodyTop;
    onWall = false;
    sections.push(...damperSections());
  } else if (type === 'damper') {
    // Yarım boru (half-pipe) çelik damper kasası: dikey yanlar, elips taban; önde teleskopik hidrolik piston ve
    // kabin siperliği, arkada üstten menteşeli kapak; kasa devirme alt çerçevesine oturur.
    const t = 0.05;
    const wt = W / 2 - 0.03;
    const y0 = deckY + 0.1;
    const Hb = topY - y0;
    const ey = 0.75;
    const x0 = -L + 0.45;
    const tl = -0.08 - x0;
    const contour = (s: THREE.Shape | THREE.Path) => {
      s.moveTo(-wt, Hb);
      s.lineTo(-wt, ey);
      s.absellipse(0, ey, wt, ey, Math.PI, Math.PI * 2, false, 0);
      s.lineTo(wt, Hb);
    };
    const shell = new THREE.Shape();
    contour(shell);
    shell.lineTo(wt - t, Hb);
    shell.lineTo(wt - t, ey);
    shell.absellipse(0, ey, wt - t, ey - t, 0, -Math.PI, true, 0);
    shell.lineTo(-wt + t, Hb);
    shell.closePath();
    const solid = new THREE.Shape();
    contour(solid);
    solid.closePath();
    const along = (shape: THREE.Shape, d: number) => {
      const g = new THREE.ExtrudeGeometry(shape, { depth: d, bevelEnabled: false, curveSegments: 28 });
      g.rotateY(Math.PI / 2);
      return g;
    };
    const pm = m.paint;
    const tub = mesh(along(shell, tl), pm);
    tub.position.set(x0, y0, 0);
    body.add(tub);
    const sp = solid.getPoints(16);
    for (const x of range(x0, x0 + tl, tl / 5)) sections.push(sp.map((p) => new THREE.Vector3(x, y0 + p.y, -p.x)));
    const fw = mesh(along(solid, 0.06), pm);
    fw.position.set(x0, y0, 0);
    body.add(fw);
    const tg = mesh(along(solid, 0.07), pm);
    tg.position.set(x0 + tl - 0.02, y0, 0);
    body.add(tg);
    for (const s of [-1, 1]) {
      // üst kenar kutu profili ve yan kırım çizgisi
      box(body, tl + 0.02, 0.14, 0.12, pm, x0 + tl / 2, y0 + Hb - 0.05, s * (wt + 0.01), 0.015);
      box(body, tl - 0.3, 0.035, 0.014, pm, x0 + tl / 2, y0 + ey + 0.06, s * (wt + 0.005));
      box(body, 0.12, 0.12, 0.12, m.darkMetal, x0 + tl + 0.04, y0 + Hb - 0.06, s * (wt - 0.08));
      box(body, 0.08, Hb - 0.3, 0.04, m.darkMetal, x0 + tl + 0.07, y0 + Hb / 2 + 0.1, s * (wt - 0.25));
      // devirme alt çerçevesi
      box(body, tl, 0.16, 0.12, m.chassis, x0 + tl / 2, deckY + 0.02, s * 0.5);
    }
    // kabin siperliği
    const canopy = box(body, 0.55, 0.05, W - 0.1, pm, x0 - 0.2, y0 + Hb + 0.05, 0);
    canopy.rotation.z = 0.22;
    // arka devirme menteşesi ve ön teleskopik piston (Blender şasisinde ikisi de var)
    if (!damperRig) {
      box(body, 0.22, 0.22, 1.25, m.darkMetal, -0.3, deckY + 0.04, 0);
      const px = x0 - 0.15;
      cyl(body, 0.14, 0.14, m.darkMetal, 'y', px, deckY + 0.02, 0, 20);
      cyl(body, 0.115, 0.7, m.darkMetal, 'y', px, deckY + 0.42, 0, 20);
      cyl(body, 0.095, 0.62, m.chrome, 'y', px, deckY + 1.05, 0, 20);
      cyl(body, 0.075, 0.55, m.chrome, 'y', px, deckY + 1.6, 0, 20);
      box(body, 0.2, 0.12, 0.34, m.darkMetal, px + 0.05, deckY + 1.9, 0);
    }
    logos(body, m.logo, x0 + tl / 2, y0 + ey + (Hb - ey) / 2 + 0.05, wt, 0.62);
    // arka kapak: yatay ve dikey takviyeler, kırmızı reflektif kontur, R70 plakaları, alt kilit kancaları
    const xr = x0 + tl + 0.05;
    for (const y of [y0 + ey + 0.12, y0 + Hb - 0.38]) box(body, 0.06, 0.1, 2 * wt - 0.12, pm, xr + 0.03, y, 0, 0.01);
    for (const z of [-0.55, 0.55]) box(body, 0.06, Hb - 0.3, 0.1, pm, xr + 0.03, y0 + Hb / 2 + 0.05, z, 0.01);
    box(body, 0.004, 0.05, 2 * wt - 0.16, m.reflRed, xr + 0.002, y0 + Hb - 0.16, 0);
    for (const z of [-1, 1]) {
      box(body, 0.004, Hb - ey - 0.3, 0.05, m.reflRed, xr + 0.002, y0 + ey + (Hb - ey) / 2 - 0.05, z * (wt - 0.08));
      r70(body, m, xr + 0.065, y0 + ey - 0.12, z * 0.62, Math.PI / 2);
      box(body, 0.1, 0.12, 0.08, m.darkMetal, xr + 0.02, y0 + 0.28, z * 0.3);
    }
    // ön duvar dikey takviyeleri
    for (const z of [-0.65, 0.65]) box(body, 0.05, Hb - 0.2, 0.1, pm, x0 - 0.025, y0 + Hb / 2 + 0.08, z);
    // ön merdiven (sürücü tarafı)
    const zl = wt + 0.03;
    const la = x0 + 0.05;
    const lb = x0 + 0.4;
    for (const x of [la, lb]) rod(body, V3(x, deckY - 0.3, zl), V3(x, y0 + Hb + 0.12, zl), 0.016, m.alu, 8);
    for (let y = deckY - 0.18; y < y0 + Hb; y += 0.3) rod(body, V3(la, y, zl), V3(lb, y, zl), 0.013, m.alu, 8);
    topY = y0 + Hb;
    onWall = false;
    socketY = deckY - 0.12;
    frontPos = { x: x0 - 0.01, y: topY - 0.16, z: wt - 0.12 };
  } else if (type === 'tanker') {
    tanker = buildTanker(body, chassisG, m, L);
    deckY = tanker.deckY;
    topY = tanker.topY;
    lampY = tanker.lampY;
    plateY = tanker.plateY;
    harnessY = tanker.harnessY;
    socketY = tanker.socket.y;
    const sy = tanker.side.y;
    sideYAt = () => sy;
    sections.push(...tanker.sections);
  } else if (type === 'silo') {
    // V tipi silobas: üst çizgisi yatay, iki kesik koniden oluşan kendinden taşıyıcı tank; en alçak nokta (boşaltma ağzı)
    // ortanın biraz önünde. Önde kompresörlü platform ve büyük destek sacları (king pin alt çerçevesi), arkada aks çerçevesi;
    // tankın altından boşaltma borusu geçer. Ortada şasi yok; yan koruma rayı tanka bağlı dikmelerle taşınır.
    const top = deckY + 2.5;
    const xF = -L + 1.15;
    const xR = -0.4;
    const xV = xF + (xR - xF) * 0.46;
    const rF = 0.72;
    const rV = 1.2;
    const rR = 0.86;
    const rAt = (x: number) => (x <= xV ? rF + ((rV - rF) * (x - xF)) / (xV - xF) : rV + ((rR - rV) * (x - xV)) / (xR - xV));
    const cyAt = (x: number) => top - rAt(x);
    const botAt = (x: number, z: number) => cyAt(x) - Math.sqrt(Math.max(0, rAt(x) ** 2 - z * z));
    body.add(mesh(siloCone(xF, xV, rF, rV, top), m.paint), mesh(siloCone(xV, xR, rV, rR, top), m.paint));
    for (const [x, r, s] of [
      [xF, rF, 1],
      [xR, rR, -1],
    ] as const) {
      const cap = mesh(new THREE.SphereGeometry(r, 48, 16, 0, Math.PI * 2, 0, Math.PI / 2), m.paint);
      cap.scale.set(1, 0.3, 1);
      cap.rotation.z = (s * Math.PI) / 2;
      cap.position.set(x, top - r, 0);
      body.add(cap);
    }
    // kaynak dikişleri (çevresel), boşaltma konisi çizgisi ve turuncu yan şerit
    const seams = [xF + 0.02, xF + (xV - xF) / 3, xF + ((xV - xF) * 2) / 3, xV, xV + (xR - xV) / 3, xV + ((xR - xV) * 2) / 3, xR - 0.02];
    for (const x of seams) {
      const ring = mesh(new THREE.TorusGeometry(rAt(x) + 0.004, 0.007, 6, 72), m.paint);
      ring.rotation.y = Math.PI / 2;
      ring.position.set(x, cyAt(x), 0);
      ring.userData.noEdge = true;
      body.add(ring);
    }
    for (const x of range(xF + 0.05, xR - 0.05, (xR - xF - 0.1) / 6)) {
      const r = rAt(x);
      sections.push(Array.from({ length: 48 }, (_, i) => V3(x, cyAt(x) + Math.cos((i / 48) * Math.PI * 2) * r, Math.sin((i / 48) * Math.PI * 2) * r)));
    }
    for (const s of [-1, 1]) {
      const a = Math.PI / 2 + 0.22;
      const on = (x: number) => V3(x, cyAt(x) + Math.cos(a) * (rAt(x) + 0.004), s * Math.sin(a) * (rAt(x) + 0.004));
      const across = V3(0, -Math.sin(a), s * Math.cos(a));
      ribbon(body, on(xF + 0.15), on(xV), across, 0.07, m.accent);
      ribbon(body, on(xV), on(xR - 0.15), across, 0.07, m.accent);
    }
    // üst: dolum kapakları, kapak arası yürüme yolu, katlanmış korkuluk
    const nm = L >= 12 ? 3 : 2;
    const mh = Array.from({ length: nm }, (_, i) => xF + 1.4 + ((xR - 1.0 - (xF + 1.4)) * i) / Math.max(1, nm - 1));
    for (const x of mh) {
      cyl(body, 0.25, 0.14, m.paint, 'y', x, top + 0.04, 0, 32);
      cyl(body, 0.275, 0.05, m.alu, 'y', x, top + 0.13, 0, 32);
      for (const k of [0, 1, 2, 3]) box(body, 0.05, 0.08, 0.05, m.darkMetal, x + Math.cos((k * Math.PI) / 2 + 0.6) * 0.27, top + 0.11, Math.sin((k * Math.PI) / 2 + 0.6) * 0.27);
    }
    for (let i = 1; i < mh.length; i++) box(body, mh[i] - mh[i - 1] - 0.62, 0.03, 0.36, m.alu, (mh[i] + mh[i - 1]) / 2, top + 0.025, 0);
    for (const z of [-0.5, 0.5]) {
      const ps = range(xF + 0.6, xR - 0.3, (xR - 0.3 - xF - 0.6) / Math.round((xR - xF) / 1.6));
      for (const x of ps) rod(body, V3(x, cyAt(x) + Math.sqrt(rAt(x) ** 2 - z * z) - 0.02, z), V3(x, top + 0.32, z), 0.016, m.alu, 8);
      rod(body, V3(ps[0], top + 0.32, z), V3(ps[ps.length - 1], top + 0.32, z), 0.018, m.alu, 8);
    }
    // arka merdiven: dikey kısım + tank üstüne kıvrılan uç
    const lz = 0.58;
    for (const dz of [-0.18, 0.18]) pipe(body, [V3(-0.05, deckY + 0.2, lz + dz), V3(-0.05, top - 0.55, lz + dz), V3(-0.55, top + 0.2, lz + dz)], 0.02, m.alu, 8);
    for (let y = deckY + 0.4; y < top - 0.55; y += 0.3) rod(body, V3(-0.05, y, lz - 0.18), V3(-0.05, y, lz + 0.18), 0.015, m.alu, 8);
    // ön alt çerçeve: platform, ön kiriş, kirişler ve tankı taşıyan destek sacları
    const xf1 = -L + 3.3;
    for (const z of [-0.5, 0.5]) box(body, xf1 + L, 0.24, 0.12, m.paint, (-L + xf1) / 2, deckY - 0.12, z);
    box(body, 0.1, 0.3, W - 0.06, m.paint, -L + 0.05, deckY - 0.15, 0);
    box(body, xF - 0.25 + L, 0.06, W - 0.2, m.paint, (-L + xF - 0.25) / 2, deckY - 0.03, 0);
    const saddle = (xa: number, xb: number, yb: number) => {
      const xs = range(xa, xb, (xb - xa) / 6);
      for (const z of [-0.5, 0.5]) slab(body, [[xa, yb], [xb, yb], ...xs.reverse().map((x) => [x, botAt(x, 0.5) + 0.03] as [number, number])], 0.08, m.paint, z);
    };
    saddle(xF + 0.05, xf1, deckY - 0.02);
    // kompresör (kasnaklı), hava filtresi, kumanda dolabı
    box(body, 0.55, 0.42, 0.62, m.darkMetal, -L + 0.45, deckY + 0.21, 0.22, 0.03);
    cyl(body, 0.2, 0.06, m.alu, 'z', -L + 0.45, deckY + 0.3, 0.6, 28);
    box(body, 0.46, 0.46, 0.04, m.paint, -L + 0.45, deckY + 0.3, 0.66, 0.02);
    cyl(body, 0.13, 0.4, m.paintYellow, 'y', -L + 0.4, deckY + 0.22, -0.38, 24);
    box(body, 0.25, 0.45, 0.35, m.alu, -L + 0.85, deckY + 0.24, -0.85, 0.02);
    // arka alt çerçeve destek sacları
    beamFrom = Math.min(...axles) - R - 0.9;
    saddle(beamFrom + 0.1, xR - 0.05, deckY - 0.08);
    // boşaltma: V ağzından inen boru + kelebek vana, kompresörden arkaya uzanan hat
    const pz = 0.68;
    const pv = deckY + 0.02;
    pipe(body, [V3(-L + 0.75, deckY + 0.3, pz), V3(-L + 0.95, deckY + 0.3, pz), V3(xV, pv, pz), V3(xR - 0.3, deckY + 0.06, pz), V3(-0.1, deckY + 0.06, pz)], 0.05, m.alu, 12);
    pipe(body, [V3(xV, botAt(xV, 0) + 0.02, 0), V3(xV, pv, 0), V3(xV, pv, pz)], 0.07, m.alu, 14);
    box(body, 0.2, 0.08, 0.2, m.darkMetal, xV, (botAt(xV, 0) + pv) / 2, 0);
    cyl(body, 0.075, 0.05, m.darkMetal, 'x', -0.08, deckY + 0.06, pz, 16);
    // arka travers (ek lambalar bunun üstünde)
    box(body, 0.06, 0.1, W - 0.06, m.paint, -0.05, lampY + 0.17, 0, 0.01);
    // yangın tüpü dolabı (kırmızı)
    box(body, 0.22, 0.5, 0.2, m.paintRed, -1.0, deckY + 0.55, 0.64, 0.02);
    // yan koruma rayı (yan markerlar bunun üstünde) ve taşıyıcıları
    for (const s of [-1, 1]) {
      box(body, L - 0.3, 0.1, 0.05, m.paint, -L / 2 + 0.0, deckY - 0.12, s * (W / 2 - 0.025), 0.01);
      for (const x of [-L + 1.0, xf1 - 0.2, beamFrom + 0.3, -0.5]) box(body, 0.06, 0.06, 0.7, m.paint, x, deckY - 0.12, s * 0.9);
      for (const t of [0.33, 0.66]) {
        const x = xf1 + (beamFrom - xf1) * t;
        rod(body, V3(x, deckY - 0.08, s * 1.2), V3(x, botAt(x, 0.75) + 0.02, s * 0.75), 0.025, m.paint, 8);
      }
    }
    topY = top + 0.4;
    frontPos = { x: -L - 0.005, y: deckY - 0.12, z: W / 2 - 0.1 };
    armRearY = deckY - 0.1;
    armFrontY = deckY - 0.1;
    socketY = deckY - 0.15;
  } else if (type === 'arac') {
    // Araç taşıyıcı: yükseltilmiş ön boyun, alçak alt kat, iki şeritli ray platformları, dikmeler + hidrolik pistonlar,
    // arkada katlanmış rampalar; yük olarak temsilî otomobiller.
    const neck = 3.2;
    const nY = 1.4;
    const upY = 2.6;
    const xn = -L + neck;
    box(body, neck, 0.35, 1.1, m.chassis, -L + neck / 2, nY - 0.22, 0);
    const nr = box(body, 0.8, 0.3, 1.1, m.chassis, xn + 0.3, (nY + deckY) / 2 - 0.18, 0);
    nr.rotation.z = -0.55;
    for (const zz of [-0.68, 0.68]) {
      box(body, -0.3 - (xn + 0.6), 0.05, 0.5, m.alu, (xn + 0.6 - 0.3) / 2, deckY + 0.02, zz);
      box(body, neck - 0.2, 0.05, 0.5, m.alu, -L + 0.1 + (neck - 0.2) / 2, nY + 0.02, zz);
      const rr = box(body, 0.85, 0.05, 0.5, m.alu, xn + 0.3, (nY + deckY) / 2 + 0.02, zz);
      rr.rotation.z = -0.5;
      box(body, L - 0.8, 0.06, 0.5, m.alu, -L / 2 - 0.05, upY, zz);
      // arkada katlanmış rampalar
      const rp = box(body, 1.2, 0.04, 0.45, m.alu, 0.12, deckY + 0.62, zz);
      rp.rotation.z = 1.15;
    }
    for (const s of [-1, 1]) {
      box(body, -0.2 - xn, 0.22, 0.1, m.paintBlue, (xn - 0.2) / 2, deckY - 0.1, s * (W / 2 - 0.05));
      box(body, neck, 0.22, 0.1, m.paintBlue, -L + neck / 2, nY - 0.1, s * (W / 2 - 0.05));
      box(body, L - 0.6, 0.18, 0.1, m.paintBlue, -L / 2 - 0.1, upY - 0.06, s * (W / 2 - 0.05));
      for (const x of range(-L + 0.4, -0.5, (L - 0.9) / 4)) {
        const base = x < xn ? nY : deckY;
        box(body, 0.14, upY - base, 0.12, m.paintBlue, x, (base + upY) / 2, s * (W / 2 - 0.07));
        cyl(body, 0.04, (upY - base) * 0.75, m.chrome, 'y', x + 0.17, base + (upY - base) * 0.45, s * (W / 2 - 0.1), 12);
      }
    }
    box(body, 0.08, 0.6, W - 0.1, m.paintBlue, -L + 0.05, nY + 0.3, 0);
    const paints = [m.paint, m.paintBlue, m.alu, m.chassis, m.containerBlue, m.paint];
    let k = 0;
    const fill = (a: number, b: number, y: number) => {
      const cnt = Math.floor((b - a) / 4.15);
      for (let i = 0; i < cnt; i++) car(body, m, a + ((b - a) * (i + 0.5)) / cnt, y + 0.03, paints[k++ % paints.length]);
    };
    fill(-L + 0.4, -0.4, upY + 0.03);
    fill(xn + 0.6, -0.4, deckY + 0.04);
    topY = upY + 1.5;
    frontPos = { x: -L, y: nY + 0.48, z: W / 2 - 0.12 };
    armRearY = upY;
    armFrontY = upY;
    sideYAt = (x) => (x < xn ? nY - 0.12 : deckY - 0.12);
    socketY = nY - 0.15;
    harnessY = deckY - 0.1;
    beamFrom = xn + 0.3;
    frontDeckY = nY;
    profile = [
      [-L, nY - 0.1],
      [xn, nY - 0.1],
      [xn + 0.75, deckY - 0.1],
      [0, deckY - 0.1],
    ];
  } else if (type === 'konteyner') {
    // İskelet konteyner şasisi: tabla yok; seyrek dar traversler, köşe kilitli (twistlock) tam genişlik travers kirişleri,
    // yan lamba çubuğu; üstünde 40' konteyner.
    const cl = Math.min(12.19, L - 0.5);
    const ch = 2.59;
    const cw = 2.44;
    const cx = -0.25 - cl / 2;
    const c0 = deckY + 0.1;
    const bolsters = [-0.25 - cl + 0.1, -0.25 - cl / 2, -0.35];
    for (const x of bolsters) {
      box(body, 0.22, 0.18, W - 0.08, m.chassis, x, deckY + 0.0, 0);
      for (const s of [-1, 1]) cyl(body, 0.05, 0.08, m.steel, 'y', x, deckY + 0.12, s * (cw / 2 - 0.1), 12);
    }
    for (const s of [-1, 1]) box(body, L - 0.6, 0.06, 0.04, m.darkMetal, -L / 2, deckY - 0.12, s * (W / 2 - 0.03));
    box(body, cl, ch, cw, m.containerBlue, cx, c0 + ch / 2, 0, 0.01);
    for (const z of [-1, 1]) boxes(body, 0.09, ch - 0.18, 0.03, m.containerBlue, range(-0.25 - cl + 0.25, -0.5, 0.28).map((x) => [x, c0 + ch / 2, z * (cw / 2 + 0.012)]));
    for (const x of [-0.25 - cl, -0.25]) for (const z of [-1, 1]) for (const y of [c0 + 0.08, c0 + ch - 0.08]) box(body, 0.18, 0.16, 0.18, m.darkMetal, x + (x < -1 ? 0.09 : -0.09), y, z * (cw / 2 - 0.09));
    for (const z of [-1, 1]) for (const y of [c0 + 0.06, c0 + ch - 0.06]) box(body, cl, 0.12, 0.08, m.containerBlue, cx, y, z * (cw / 2 - 0.04));
    for (const zz of [-0.95, -0.4, 0.4, 0.95]) cyl(body, 0.02, ch - 0.3, m.chrome, 'y', -0.22, c0 + ch / 2, zz, 12);
    logos(body, m.logoWhite, cx + 0.4, c0 + ch * 0.55, cw / 2 + 0.03, 1.9);
    rail = false;
    topY = c0 + ch;
    frontPos = { x: -0.25 - cl - 0.01, y: topY - 0.15, z: cw / 2 - 0.1 };
    armRearY = topY - 0.3;
    armFrontY = topY - 0.3;
    socketY = deckY - 0.12;
  }

  if (damperRig) socketY = DAMPER.socket.y;
  const S = stdBody ? STANDART : null;
  if (S) {
    lampY = S.rear.lampY;
    plateY = S.rear.plateY;
    harnessY = S.harness.y;
  }
  /** gerçek şasi: tesisat görünümünde gövde gizlenir, şasi kendi malzemesiyle görünür, zemin şeridi yok */
  const real = !!tanker || !!damperRig || !!S;
  if (damperRig) for (const mm of mergedFromModel(damperRig)) chassisG.add(mm);
  else if (S && stdRig) for (const mm of mergedFromModel(stdRig)) chassisG.add(mm);
  else if (!tanker) chassis(chassisG, m, { L, deckY, R, axles, landingX, sideGuard, rail, lampY, plateY, beamFrom, frontDeckY, crossStep, crossW, railMat, tape, fender, hubMat, barMat, frameMat, kingY });
  plate(group, plateY, S ? S.rear.x + 0.006 : -0.015);

  const prof: [number, number][] = profile ?? [
    [-L, harnessY],
    [0, harnessY],
  ];

  // Tesisat görünümü: gövde gizlenmez, yarı saydam çizilir (setGhost); burada yalnızca gövde çizgileri ve
  // tesisatın okunacağı, tipin taban profilini izleyen açık renkli zemin şeridi kurulur.
  group.updateMatrixWorld(true);
  const edgePos: number[] = [];
  const tmp = new THREE.Vector3();
  for (const root of real ? [] : [body, chassisG]) {
    root.traverse((o) => {
      const mm = o as THREE.Mesh;
      if (!mm.isMesh || o.userData.noEdge || o.userData.cargo || (o as THREE.InstancedMesh).isInstancedMesh) return;
      const eg = new THREE.EdgesGeometry(mm.geometry, 35);
      const pa = eg.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < pa.count; i++) {
        tmp.fromBufferAttribute(pa, i).applyMatrix4(mm.matrixWorld);
        edgePos.push(tmp.x, tmp.y, tmp.z);
      }
      eg.dispose();
    });
  }
  for (const loop of sections) {
    loop.forEach((p, i) => {
      const q = loop[(i + 1) % loop.length];
      edgePos.push(p.x, p.y, p.z, q.x, q.y, q.z);
    });
  }
  // Kenarlar çıkarıldıktan sonra yüzlerce parça malzemeye göre birkaç ağa birleştirilir (çizim çağrısı ~10 kat azalır).
  // Lastikler ve yük (otomobiller) dahil her parça tesisat görünümünde yarı saydam olur.
  const bodyMerged = mergeByMaterial(body);
  const chassisMerged = mergeByMaterial(chassisG);
  const solids = real ? bodyMerged : [...bodyMerged, ...chassisMerged];
  for (const mm of solids) {
    mm.userData.mat = mm.material;
    mm.userData.cast = mm.castShadow;
  }

  const edgeGeo = new THREE.BufferGeometry();
  edgeGeo.setAttribute('position', new THREE.Float32BufferAttribute(edgePos, 3));
  const outline = new THREE.LineSegments(edgeGeo, m.outline);

  // zemin şeridi: profil boyunca (kademeli tiplerde rampalarla)
  const fw = W / 2 - 0.1;
  const fxs = [-L + 0.1, ...prof.map((p) => p[0]).filter((x) => x > -L + 0.1 && x < -0.1), -0.1];
  const fv: number[] = [];
  const fi: number[] = [];
  fxs.forEach((x, i) => {
    const y = profileAt(prof, x) - 0.035;
    fv.push(x, y, -fw, x, y, fw);
    if (i > 0) {
      const a = (i - 1) * 2;
      fi.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  });
  const floorGeo = new THREE.BufferGeometry();
  floorGeo.setAttribute('position', new THREE.Float32BufferAttribute(fv, 3));
  floorGeo.setIndex(fi);
  floorGeo.computeVertexNormals();
  const sysFloor = mesh(floorGeo, m.sysFloor, false, true);
  const sys = new THREE.Group();
  sys.add(outline);
  // tanker: zemin şeridi yok, tesisatın altında gerçek şasi görünür
  if (!real) sys.add(sysFloor);
  sys.visible = false;
  group.add(sys);
  // pişirilmiş zemin temas gölgesi (birleştirmeye ve yarı saydamlığa girmez)
  if (S) group.add(standartContact());

  const anchors: Anchors = S ? {
    L,
    W,
    topY,
    rear: { x: S.rear.x, lampY: S.rear.lampY, lampZ: [S.rear.lampZ[0], S.rear.lampZ[1]], plateY: S.rear.plateY, dropX: S.rear.dropX },
    side: { x0: S.side.x0, x1: S.side.x1, z: S.side.z, yAt: () => S.side.y },
    front: S.front,
    extra: S.extra,
    armRear: S.armRear,
    armFront: S.armFront,
    socket: { x: S.socket.x, y: S.socket.y, onWall: true },
    harness: { y: S.harness.y, railZ: 0.4, junctionX: -0.65, frontX: S.harness.frontX, profile: prof, trunkZ: S.harness.trunkZ, rearZ: S.harness.rearZ },
    center: new THREE.Vector3(-L / 2, topY / 2, 0),
    size: new THREE.Vector3(L, topY, W),
  } : {
    L,
    W,
    topY,
    rear: { x: 0.0, lampY, lampZ: [W / 2 - 0.33, 0.48], plateY },
    side: {
      x0: tanker ? tanker.side.x0 : damperRig ? DAMPER.side.x0 : sideX0,
      x1: tanker ? tanker.side.x1 : damperRig ? DAMPER.side.x1 : -0.6,
      z: W / 2 + 0.005,
      yAt: sideYAt,
      brackets: !!damperRig,
    },
    front: tanker?.front ?? (damperRig ? DAMPER.front : null) ?? frontPos ?? { x: -L - 0.01, y: topY - 0.14, z: W / 2 - 0.12 },
    extra: tanker?.extra ?? (damperBody ? DAMPER.extra : null) ?? (() => {
      const roofed = type === 'standart' || type === 'kapali' || type === 'frigo' || type === 'damper' || type === 'konteyner';
      return roofed
        ? { x: type === 'konteyner' ? -0.23 : type === 'damper' ? 0.0 : 0.05, y: topY - 0.14, z0: W / 2 - 0.13, z1: 0.72 }
        : // açık/tanklı tiplerde lamba barının üstünde (stop lambalarıyla çakışmaz)
          { x: 0.0, y: extraY ?? lampY + 0.17, z0: W / 2 - 0.15, z1: 0.72 };
    })(),
    armRear: tanker?.armRear ?? (damperRig ? DAMPER.armRear : null) ?? { x: -0.2, y: armRearY, z: W / 2 },
    armFront: tanker?.armFront ?? (damperRig ? DAMPER.armFront : null) ?? { x: -L + 0.25, y: armFrontY, z: W / 2 },
    socket: { x: tanker ? tanker.socket.x : damperRig ? DAMPER.socket.x : onWall ? -L - 0.01 : -L - 0.03, y: socketY, onWall },
    harness: { y: harnessY, railZ: 0.4, junctionX: -0.65, frontX: tanker ? tanker.frontX : damperRig ? DAMPER.frontX : -L + 0.35, profile: prof, ...(damperRig ? { trunkZ: DAMPER.trunkZ, rearZ: DAMPER.rearZ } : {}) },
    center: new THREE.Vector3(-L / 2, topY / 2, 0),
    size: new THREE.Vector3(L, topY, W),
  };
  return { group, body, outline: sys, solids, realChassis: real, anchors };
}

/**
 * Kökün altındaki düz ağları (malzeme + gölge ayarı aynı olanlar) tek geometride birleştirir; yeni ağları döndürür.
 * Kovadaki geometrilerin hepsi indeksliyse indeksli birleşir (köşe verisi şişmez). Önceden birleştirilmiş
 * (userData.merged) ve örnekli ağlar olduğu gibi kalır; paylaşılan geometriler dispose edilmez.
 */
function mergeByMaterial(root: THREE.Object3D): THREE.Mesh[] {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert();
  const buckets = new Map<string, { mat: THREE.Material; cast: boolean; receive: boolean; geos: THREE.BufferGeometry[] }>();
  const done: THREE.Mesh[] = [];
  const out: THREE.Mesh[] = [];
  const mtx = new THREE.Matrix4();
  root.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (!mm.isMesh || o.userData.merged || (mm as THREE.InstancedMesh).isInstancedMesh || Array.isArray(mm.material)) return;
    const mat = mm.material as THREE.Material;
    const key = `${mat.uuid}|${+mm.castShadow}|${+mm.receiveShadow}`;
    let b = buckets.get(key);
    if (!b) buckets.set(key, (b = { mat, cast: mm.castShadow, receive: mm.receiveShadow, geos: [] }));
    const g = mm.geometry.clone();
    for (const k of Object.keys(g.attributes)) if (k !== 'position' && k !== 'normal' && k !== 'uv') g.deleteAttribute(k);
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    g.clearGroups();
    g.applyMatrix4(mtx.multiplyMatrices(inv, mm.matrixWorld));
    b.geos.push(g);
    done.push(mm);
  });
  const used = new Set<THREE.BufferGeometry>();
  for (const mm of done) {
    mm.removeFromParent();
    if (!isShared(mm.geometry)) used.add(mm.geometry);
  }
  for (const g of used) g.dispose();
  for (const b of buckets.values()) {
    const indexed = b.geos.every((g) => g.index);
    const list = indexed
      ? b.geos
      : b.geos.map((g) => {
          if (!g.index) return g;
          const n = g.toNonIndexed();
          g.dispose();
          return n;
        });
    const g = mergeGeometries(list, false);
    for (const x of list) x.dispose();
    if (!g) {
      if (import.meta.env.DEV) console.warn('mergeByMaterial: birleştirilemedi', b.mat.name);
      continue;
    }
    const m = new THREE.Mesh(g, b.mat);
    m.castShadow = b.cast;
    m.receiveShadow = b.receive;
    root.add(m);
    out.push(m);
  }
  return out;
}

interface MergedPart {
  geo: THREE.BufferGeometry;
  mat: THREE.Material;
  cast: boolean;
  receive: boolean;
  /** varsa örnekli çizim: model köküne göre örnek matrisleri */
  inst?: THREE.Matrix4[];
}
const mergedCache = new WeakMap<THREE.Object3D, MergedPart[]>();

/**
 * Yüklenmiş GLB modeli: ilk çağrıda malzemeye göre birleştirilir, aynı geometriyi paylaşan tekrarlı parçalar (tekerlekler)
 * örnekli çizime çevrilir; sonuç önbellekte (paylaşılan) kalır. Sonraki kurulumlarda yalnız yeni Mesh nesneleri üretilir:
 * yeniden birleştirme, GPU'ya yeniden yükleme ve önbellekteki geometrinin dispose edilmesi yok.
 */
function mergedFromModel(model: THREE.Object3D): THREE.Mesh[] {
  let parts = mergedCache.get(model);
  if (!parts) {
    parts = [];
    const root = model.clone();
    root.updateMatrixWorld(true);
    const inv = root.matrixWorld.clone().invert();
    const byGeo = new Map<string, THREE.Mesh[]>();
    root.traverse((o) => {
      const mm = o as THREE.Mesh;
      if (!mm.isMesh || Array.isArray(mm.material)) return;
      const k = `${mm.geometry.uuid}|${(mm.material as THREE.Material).uuid}`;
      const list = byGeo.get(k);
      if (list) list.push(mm);
      else byGeo.set(k, [mm]);
    });
    for (const list of byGeo.values()) {
      if (list.length < 2) continue;
      const m0 = list[0];
      parts.push({ geo: m0.geometry, mat: m0.material as THREE.Material, cast: m0.castShadow, receive: m0.receiveShadow, inst: list.map((mm) => new THREE.Matrix4().multiplyMatrices(inv, mm.matrixWorld)) });
      for (const mm of list) mm.removeFromParent();
    }
    for (const mm of mergeByMaterial(root)) {
      parts.push({ geo: markShared(mm.geometry), mat: mm.material as THREE.Material, cast: mm.castShadow, receive: mm.receiveShadow });
    }
    mergedCache.set(model, parts);
  }
  return parts.map((p) => {
    let m: THREE.Mesh;
    if (p.inst) {
      const im = new THREE.InstancedMesh(p.geo, p.mat, p.inst.length);
      p.inst.forEach((mx, i) => im.setMatrixAt(i, mx));
      im.computeBoundingSphere();
      m = im;
    } else m = new THREE.Mesh(p.geo, p.mat);
    m.castShadow = p.cast;
    m.receiveShadow = p.receive;
    m.userData.merged = true;
    return m;
  });
}

/** Tesisat görünümü: gövde, şasi ve tekerlekler yarı saydam (tipin silueti görünür, tesisat okunur). */
export function setGhost(t: TrailerBuild, mats: Mats, on: boolean) {
  if (t.realChassis) {
    t.body.visible = !on;
    return;
  }
  for (const mm of t.solids) {
    mm.material = on ? mats.ghost : (mm.userData.mat as THREE.Material);
    mm.castShadow = on ? false : (mm.userData.cast as boolean);
  }
}

export function disposeGroup(g: THREE.Object3D) {
  g.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (mm.geometry && !isShared(mm.geometry)) mm.geometry.dispose();
    if ((o as THREE.InstancedMesh).isInstancedMesh) (o as THREE.InstancedMesh).dispose();
  });
}
