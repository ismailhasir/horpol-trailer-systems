// Dorse geometrisi (prosedürel). Koordinatlar metre: X boyuna (arka yüz x=0, ön x=-L), Y yukarı, Z yanal (+Z sağ).
// Her tip ortak şasiyi kullanır, üstüne kendi gövdesini kurar ve lamba/tesisat için bağlantı noktalarını (anchors) döndürür.
// Gerçek GLB modeller geldiğinde bu dosya, model + adlandırılmış bağlantı noktası okuyan bir yükleyiciyle değişecek.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import type { TrailerId } from '../data';
import type { Mats } from './materials';

export interface Pt {
  x: number;
  y: number;
  z: number;
}

export interface Anchors {
  L: number;
  W: number;
  topY: number;
  rear: { x: number; lampY: number; lampZ: [number, number]; plateY: number };
  side: { x0: number; x1: number; z: number; yAt: (x: number) => number };
  front: Pt;
  armRear: Pt;
  armFront: Pt;
  /** ek lambalar: arka üst köşeler (kapalı gövdeli tipler) ya da tampon uçları; z0 dış, z1 iç sıra */
  extra: { x: number; y: number; z0: number; z1: number };
  socket: { x: number; y: number; onWall: boolean };
  /** profile: tesisatın taban boyunca izlediği yükseklik [x, y] (x artan); boyunlu/basamaklı tiplerde kademeli */
  harness: { y: number; railZ: number; junctionX: number; frontX: number; profile: [number, number][] };
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

function mesh(geo: THREE.BufferGeometry, mat: THREE.Material, cast = true, receive = true) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = cast;
  m.receiveShadow = receive;
  return m;
}
/** Kutu: lx boyuna, ly yükseklik, lz genişlik; konum merkez */
function box(parent: THREE.Object3D, lx: number, ly: number, lz: number, mat: THREE.Material, x: number, y: number, z: number, r = 0) {
  const geo = r > 0 ? new RoundedBoxGeometry(lx, ly, lz, 2, Math.min(r, lx / 2, ly / 2, lz / 2)) : new THREE.BoxGeometry(lx, ly, lz);
  const m = mesh(geo, mat);
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}
function cyl(parent: THREE.Object3D, r: number, len: number, mat: THREE.Material, axis: 'x' | 'y' | 'z', x: number, y: number, z: number, seg = 20) {
  const m = mesh(new THREE.CylinderGeometry(r, r, len, seg), mat);
  if (axis === 'x') m.rotation.z = Math.PI / 2;
  if (axis === 'z') m.rotation.x = Math.PI / 2;
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}
/** Aynı kutudan çok sayıda (InstancedMesh) */
function boxes(parent: THREE.Object3D, lx: number, ly: number, lz: number, mat: THREE.Material, pts: [number, number, number][]) {
  if (!pts.length) return;
  const im = new THREE.InstancedMesh(new THREE.BoxGeometry(lx, ly, lz), mat, pts.length);
  const m4 = new THREE.Matrix4();
  pts.forEach((p, i) => im.setMatrixAt(i, m4.makeTranslation(p[0], p[1], p[2])));
  im.castShadow = true;
  im.receiveShadow = true;
  parent.add(im);
  return im;
}
const range = (a: number, b: number, step: number) => {
  const out: number[] = [];
  for (let v = a; v <= b + 1e-6; v += step) out.push(v);
  return out;
};

// ---------- tekerlek ----------
interface WheelKit {
  tire: THREE.BufferGeometry;
  rim: THREE.BufferGeometry;
  face: THREE.BufferGeometry;
  hub: THREE.BufferGeometry;
  nut: THREE.BufferGeometry;
}
const wheelCache = new Map<number, WheelKit>();
function wheelKit(R: number): WheelKit {
  const hit = wheelCache.get(R);
  if (hit) return hit;
  const s = R / 0.53;
  const hw = 0.19 * s;
  const prof: [number, number][] = [
    [0.3, -0.165],
    [0.36, -0.185],
    [0.47, -0.19],
    [0.515, -0.165],
    [0.53, -0.11],
    [0.533, 0],
    [0.53, 0.11],
    [0.515, 0.165],
    [0.47, 0.19],
    [0.36, 0.185],
    [0.3, 0.165],
  ];
  const tire = new THREE.LatheGeometry(
    prof.map(([r, y]) => new THREE.Vector2(r * s, y * s * (hw / (0.19 * s)))),
    56,
  );
  tire.rotateX(Math.PI / 2);
  const rim = new THREE.CylinderGeometry(0.3 * s, 0.3 * s, 0.31 * s, 40, 1, true);
  rim.rotateX(Math.PI / 2);
  // jant yüzü: delikli disk
  const shape = new THREE.Shape();
  shape.absarc(0, 0, 0.3 * s, 0, Math.PI * 2, false);
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    const hole = new THREE.Path();
    hole.absellipse(Math.cos(a) * 0.205 * s, Math.sin(a) * 0.205 * s, 0.03 * s, 0.045 * s, 0, Math.PI * 2, true, a);
    shape.holes.push(hole);
  }
  const face = new THREE.ExtrudeGeometry(shape, { depth: 0.02 * s, bevelEnabled: true, bevelSize: 0.008 * s, bevelThickness: 0.008 * s, bevelSegments: 2, curveSegments: 40 });
  const hub = new THREE.CylinderGeometry(0.1 * s, 0.12 * s, 0.09 * s, 28);
  hub.rotateX(Math.PI / 2);
  const nut = new THREE.CylinderGeometry(0.016 * s, 0.016 * s, 0.035 * s, 6);
  nut.rotateX(Math.PI / 2);
  const kit = { tire, rim, face, hub, nut };
  wheelCache.set(R, kit);
  return kit;
}
function wheel(m: Mats, R: number, side: 1 | -1) {
  const k = wheelKit(R);
  const s = R / 0.53;
  const g = new THREE.Group();
  g.add(mesh(k.tire, m.rubber));
  g.add(mesh(k.rim, m.alu, false));
  const face = mesh(k.face, m.alu, false);
  face.position.z = 0.1 * s;
  g.add(face);
  const hub = mesh(k.hub, m.chrome, false);
  hub.position.z = 0.15 * s;
  g.add(hub);
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2 + Math.PI / 10;
    const n = mesh(k.nut, m.chrome, false);
    n.position.set(Math.cos(a) * 0.075 * s, Math.sin(a) * 0.075 * s, 0.135 * s);
    g.add(n);
  }
  if (side < 0) g.rotation.y = Math.PI;
  g.traverse((o) => (o.userData.noEdge = true));
  return g;
}

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
}
function chassis(g: THREE.Group, m: Mats, o: ChassisOpts) {
  const { L, deckY, R } = o;
  const fy = o.frontDeckY ?? deckY;
  const beamH = Math.min(0.42, deckY - 2 * R + 0.05);
  const beamY = deckY - 0.08 - beamH / 2;
  const from = o.beamFrom ?? -L + 0.25;
  // ana kirişler
  for (const z of [-0.5, 0.5]) box(g, -0.15 - from, beamH, 0.1, m.chassis, (from - 0.15) / 2, beamY, z);
  // traversler
  boxes(g, 0.06, 0.1, o.crossW ?? 2.2, m.chassis, range(from + 0.3, -0.4, o.crossStep ?? 0.55).map((x) => [x, deckY - 0.13, 0]));
  // dış yan ray
  if (o.rail) {
    for (const z of [-1, 1]) {
      box(g, L - 0.04, 0.22, 0.05, m.alu, -L / 2, deckY - 0.12, z * (W / 2 - 0.025));
      box(g, L - 0.06, 0.035, 0.006, m.stripe, -L / 2, deckY - 0.06, z * (W / 2 + 0.0005));
    }
  }
  // akslar, süspansiyon, tekerlekler, çamurluk
  for (const x of o.axles) {
    cyl(g, 0.065, 2.05, m.darkMetal, 'z', x, R, 0);
    for (const z of [-0.52, 0.52]) {
      cyl(g, 0.13, 0.22, m.rubber, 'y', x - 0.35, R + 0.2, z, 18);
      box(g, 0.75, 0.08, 0.1, m.darkMetal, x - 0.15, R + 0.04, z);
    }
    for (const s of [1, -1] as const) {
      const wh = wheel(m, R, s);
      wh.position.set(x, R, s * (W / 2 - 0.33));
      g.add(wh);
    }
  }
  if (o.axles.length) {
    const xs = o.axles;
    const front = Math.min(...xs) - R - 0.2;
    const back = Math.max(...xs) + R + 0.2;
    for (const z of [-1, 1]) {
      box(g, back - front, 0.025, 0.62, m.plastic, (front + back) / 2, 2 * R + 0.09, z * (W / 2 - 0.33));
      box(g, 0.02, 0.55, 0.6, m.rubber, back + 0.02, 2 * R - 0.2, z * (W / 2 - 0.33));
    }
  }
  // iniş ayağı
  for (const z of [-0.62, 0.62]) {
    box(g, 0.14, fy - 0.55, 0.14, m.darkMetal, o.landingX, (fy + 0.45) / 2 + 0.1, z);
    box(g, 0.1, 0.5, 0.1, m.alu, o.landingX, 0.38, z);
    box(g, 0.32, 0.04, 0.3, m.darkMetal, o.landingX, 0.12, z);
  }
  box(g, 0.06, 0.06, 1.2, m.darkMetal, o.landingX, 0.75, 0);
  // king pin plakası
  box(g, 1.6, 0.05, 1.6, m.darkMetal, -L + 1.0, fy - 0.52, 0);
  cyl(g, 0.045, 0.1, m.steel, 'y', -L + 1.2, fy - 0.6, 0, 16);
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
  // arka koruma tamponu + lamba barı + plaka tutucu
  box(g, 0.12, 0.13, 2.36, m.darkMetal, -0.22, 0.52, 0, 0.01);
  for (const z of [-0.55, 0.55]) box(g, 0.08, o.lampY - 0.52, 0.08, m.darkMetal, -0.24, (o.lampY + 0.52) / 2, z);
  box(g, 0.1, 0.24, W - 0.06, m.chassis, -0.07, o.lampY, 0, 0.01);
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
function plate(g: THREE.Group, y: number) {
  const p = mesh(new THREE.PlaneGeometry(0.52, 0.11), new THREE.MeshStandardMaterial({ map: plateTexture(), roughness: 0.35, metalness: 0.1 }), false);
  p.rotation.y = Math.PI / 2;
  p.position.set(-0.015, y, 0);
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
function rearDoors(g: THREE.Group, m: Mats, y0: number, H: number, mat: THREE.Material) {
  const dw = (W - 0.12) / 2;
  for (const s of [-1, 1]) {
    box(g, 0.05, H - 0.1, dw - 0.02, mat, 0.005, y0 + H / 2, s * (dw / 2 + 0.01), 0.01);
    for (const zz of [0.22, 0.62]) {
      cyl(g, 0.018, H - 0.25, m.chrome, 'y', 0.05, y0 + H / 2, s * zz, 12);
      box(g, 0.05, 0.04, 0.06, m.darkMetal, 0.04, y0 + 0.25, s * zz);
      box(g, 0.05, 0.04, 0.06, m.darkMetal, 0.04, y0 + H - 0.25, s * zz);
    }
    for (const yy of [0.35, H / 2, H - 0.35]) box(g, 0.05, 0.08, 0.14, m.darkMetal, 0.035, y0 + yy, s * (W / 2 - 0.1));
    box(g, 0.07, 0.07, 0.12, m.darkMetal, 0.05, y0 + H * 0.45, s * 0.42);
  }
  box(g, 0.08, H, 0.06, m.alu, 0.0, y0 + H / 2, W / 2 - 0.03);
  box(g, 0.08, H, 0.06, m.alu, 0.0, y0 + H / 2, -W / 2 + 0.03);
  box(g, 0.08, 0.12, W, m.alu, 0.0, y0 + H - 0.06, 0);
}

// ---------- perde (tente) ----------
function curtain(g: THREE.Group, m: Mats, L: number, y0: number, H: number) {
  const seg = Math.round(L * 14);
  for (const s of [1, -1]) {
    const geo = new THREE.PlaneGeometry(L - 0.16, H, seg, 1);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      pos.setZ(i, 0.012 * Math.sin(x * 34) + 0.005 * Math.sin(x * 9.3));
    }
    geo.computeVertexNormals();
    const p = mesh(geo, m.curtain);
    p.position.set(-L / 2, y0 + H / 2, s * (W / 2 - 0.02));
    if (s < 0) p.rotation.y = Math.PI;
    g.add(p);
    // tokalar / gergi kayışları
    boxes(
      g,
      0.04,
      0.34,
      0.014,
      m.darkMetal,
      range(-L + 0.5, -0.5, 0.62).map((x) => [x, y0 + 0.2, s * (W / 2 + 0.002)]),
    );
  }
}

// ---------- gövde tipleri ----------
export function buildTrailer(type: TrailerId, L: number, m: Mats): TrailerBuild {
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
  }
  if (type === 'tanker') {
    deckY = 1.22;
    lampY = 0.96;
    plateY = 0.7;
    topY = 3.45;
    onWall = false;
    rail = false;
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
  if (type === 'flatbed' || type === 'stepdeck' || type === 'konteyner') onWall = false;
  if (type === 'damper') topY = 3.0;

  const H = topY - deckY;
  /** Tesisat görünümünde kavisli gövdelerin biçimi okunsun diye çizilen ek kesit çizgileri (kapalı çokgenler) */
  const sections: THREE.Vector3[][] = [];

  // --- gövde ---
  if (type === 'standart') {
    box(body, L, 0.1, W - 0.02, m.deck, -L / 2, deckY - 0.05, 0);
    box(body, 0.08, H, W, m.paint, -L + 0.04, deckY + H / 2, 0, 0.02);
    box(body, L, 0.07, W + 0.02, m.alu, -L / 2, topY - 0.035, 0, 0.02);
    box(body, L - 0.1, 0.03, W - 0.04, m.curtain, -L / 2, topY + 0.01, 0);
    for (const z of [-1, 1]) box(body, L, 0.14, 0.05, m.alu, -L / 2, topY - 0.12, z * (W / 2 - 0.02));
    curtain(body, m, L, deckY + 0.02, H - 0.2);
    rearDoors(body, m, deckY, H - 0.07, m.paint);
    logos(body, m.logo, -L / 2 + 0.6, deckY + H * 0.55, W / 2 - 0.005, 2.1);
  } else if (type === 'kapali' || type === 'frigo') {
    const r = type === 'frigo' ? 0.07 : 0.025;
    box(body, L, H, W, m.paint, -L / 2, deckY + H / 2, 0, r);
    if (type === 'kapali') {
      boxes(body, 0.05, H - 0.1, W + 0.03, m.alu, range(-L + 0.6, -0.6, 1.2).map((x) => [x, deckY + H / 2, 0]));
      for (const y of [deckY + 0.06, topY - 0.06]) box(body, L + 0.01, 0.12, W + 0.03, m.alu, -L / 2, y, 0);
    } else {
      for (const y of [deckY + 0.05]) box(body, L + 0.01, 0.1, W + 0.03, m.alu, -L / 2, y, 0);
      // soğutma ünitesi
      const u = new THREE.Group();
      box(u, 0.5, 1.75, 2.15, m.paint, 0, 0, 0, 0.09);
      box(u, 0.02, 1.2, 1.7, m.grille, -0.26, 0.05, 0);
      box(u, 0.02, 0.18, 1.7, m.stripe, -0.26, -0.72, 0);
      u.position.set(-L - 0.26, topY - 1.05, 0);
      body.add(u);
    }
    rearDoors(body, m, deckY, H, m.paint);
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
    const neck = 3.0;
    const wellStart = -L + neck + 0.6;
    const wellEnd = -4.6;
    const wellY = 0.62;
    box(body, neck, 0.14, W, m.deck, -L + neck / 2, 1.45 - 0.07, 0);
    box(body, neck, 0.4, 1.2, m.chassis, -L + neck / 2, 1.18, 0);
    const n1 = box(body, 0.9, 0.14, W - 0.1, m.chassis, -L + neck + 0.3, 1.05, 0);
    n1.rotation.z = -0.85;
    box(body, wellEnd - wellStart, 0.12, W, m.deck, (wellStart + wellEnd) / 2, wellY, 0);
    for (const z of [-1, 1]) box(body, wellEnd - wellStart, 0.32, 0.12, m.paintBlue, (wellStart + wellEnd) / 2, wellY - 0.16, z * (W / 2 - 0.06));
    const n2 = box(body, 0.7, 0.14, W - 0.1, m.chassis, wellEnd + 0.2, 0.8, 0);
    n2.rotation.z = 0.6;
    box(body, -wellEnd, 0.12, W, m.deck, wellEnd / 2, deckY - 0.06, 0);
    for (const z of [-1, 1]) box(body, -wellEnd, 0.22, 0.08, m.paintBlue, wellEnd / 2, deckY - 0.12, z * (W / 2 - 0.04));
    for (const z of [-0.7, 0.7]) {
      const ramp = box(body, 0.06, 2.0, 0.55, m.alu, 0.25, deckY + 0.85, z);
      ramp.rotation.z = 0.32;
    }
    beamFrom = wellEnd + 0.4;
    topY = deckY + 1.85;
    frontPos = { x: -L + 0.02, y: 1.52, z: W / 2 - 0.06 };
    armRearY = deckY + 0.3;
    armFrontY = 1.75;
    sideYAt = (x) => (x < -L + neck ? 1.3 : x < wellEnd ? wellY - 0.12 : deckY - 0.12);
    socketY = 1.3;
    harnessY = 0.6;
    frontDeckY = 1.45;
    profile = [
      [-L, 1.25],
      [-L + neck, 1.25],
      [wellStart, 0.6],
      [wellEnd, 0.6],
      [wellEnd + 0.6, deckY - 0.04],
      [0, deckY - 0.04],
    ];
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
    const tub = mesh(along(shell, tl), m.paint);
    tub.position.set(x0, y0, 0);
    body.add(tub);
    const sp = solid.getPoints(16);
    for (const x of range(x0, x0 + tl, tl / 5)) sections.push(sp.map((p) => new THREE.Vector3(x, y0 + p.y, -p.x)));
    const fw = mesh(along(solid, 0.06), m.paint);
    fw.position.set(x0, y0, 0);
    body.add(fw);
    const tg = mesh(along(solid, 0.07), m.paint);
    tg.position.set(x0 + tl - 0.02, y0, 0);
    body.add(tg);
    for (const s of [-1, 1]) {
      box(body, tl, 0.09, 0.1, m.stripe, x0 + tl / 2, y0 + Hb - 0.03, s * (wt - 0.02));
      box(body, tl - 0.4, 0.07, 0.006, m.stripe, x0 + tl / 2, y0 + ey + 0.18, s * (wt + 0.003));
      box(body, 0.12, 0.12, 0.12, m.darkMetal, x0 + tl + 0.04, y0 + Hb - 0.06, s * (wt - 0.08));
      box(body, 0.08, Hb - 0.3, 0.04, m.darkMetal, x0 + tl + 0.07, y0 + Hb / 2 + 0.1, s * (wt - 0.25));
      // devirme alt çerçevesi
      box(body, tl, 0.16, 0.12, m.chassis, x0 + tl / 2, deckY + 0.02, s * 0.5);
    }
    // kabin siperliği
    const canopy = box(body, 0.55, 0.05, W - 0.1, m.paint, x0 - 0.2, y0 + Hb + 0.05, 0);
    canopy.rotation.z = 0.22;
    // arka devirme menteşesi
    box(body, 0.22, 0.22, 1.25, m.darkMetal, -0.3, deckY + 0.04, 0);
    // ön teleskopik piston (3 kademe)
    const px = x0 - 0.15;
    cyl(body, 0.14, 0.14, m.darkMetal, 'y', px, deckY + 0.02, 0, 20);
    cyl(body, 0.115, 0.7, m.darkMetal, 'y', px, deckY + 0.42, 0, 20);
    cyl(body, 0.095, 0.62, m.chrome, 'y', px, deckY + 1.05, 0, 20);
    cyl(body, 0.075, 0.55, m.chrome, 'y', px, deckY + 1.6, 0, 20);
    box(body, 0.2, 0.12, 0.34, m.darkMetal, px + 0.05, deckY + 1.9, 0);
    logos(body, m.logo, x0 + tl / 2, y0 + ey + (Hb - ey) / 2 + 0.05, wt, 0.62);
    topY = y0 + Hb;
    onWall = false;
    socketY = deckY - 0.12;
    frontPos = { x: x0 - 0.01, y: topY - 0.16, z: wt - 0.12 };
  } else if (type === 'tanker') {
    // Kendinden taşıyıcı oval kesitli tank: uzun şasi kirişi yok; yalnızca ön (king pin) ve arka (yürüyen aksam) alt çerçeveleri.
    const r = 1.0;
    const sz = 1.22;
    const tl = L - 0.9;
    const cy = deckY + r;
    const tank = mesh(new THREE.CylinderGeometry(r, r, tl, 64, 1, true), m.steel);
    tank.rotation.z = Math.PI / 2;
    tank.scale.z = sz;
    tank.position.set(-L / 2, cy, 0);
    body.add(tank);
    for (const s of [-1, 1]) {
      const cap = mesh(new THREE.SphereGeometry(r, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), m.steel);
      cap.scale.set(1, 0.32, sz);
      cap.rotation.z = (s * Math.PI) / 2;
      cap.position.set(-L / 2 - (s * tl) / 2, cy, 0);
      body.add(cap);
    }
    for (const x of range(-L + 0.45, -0.45, (L - 0.9) / 5)) {
      sections.push(Array.from({ length: 48 }, (_, i) => new THREE.Vector3(x, cy + Math.sin((i / 48) * Math.PI * 2) * r, Math.cos((i / 48) * Math.PI * 2) * r * sz)));
    }
    for (const x of range(-L + 1.2, -1.2, 2.3)) {
      const ring = mesh(new THREE.TorusGeometry(r + 0.01, 0.025, 8, 64), m.chrome);
      ring.rotation.y = Math.PI / 2;
      ring.scale.x = sz;
      ring.position.set(x, cy, 0);
      body.add(ring);
    }
    // yürüme yolu, kapaklar, korkuluk
    box(body, tl - 0.6, 0.04, 0.5, m.alu, -L / 2, cy + r + 0.02, 0);
    for (const x of range(-L + 2, -1.5, 2.6)) cyl(body, 0.24, 0.12, m.steel, 'y', x, cy + r + 0.06, 0, 28);
    for (const z of [-0.3, 0.3]) {
      boxes(body, 0.03, 0.4, 0.03, m.alu, range(-L + 1, -1, 1.5).map((x) => [x, cy + r + 0.24, z]));
      box(body, tl - 0.9, 0.03, 0.03, m.alu, -L / 2, cy + r + 0.44, z);
    }
    // arka merdiven
    for (const z of [-0.18, 0.18]) box(body, 0.04, r * 2, 0.04, m.alu, -0.06, cy, z);
    boxes(body, 0.04, 0.03, 0.4, m.alu, range(cy - r + 0.2, cy + r, 0.3).map((y) => [-0.06, y, 0]));
    for (const s of [-1, 1]) {
      box(body, tl - 0.4, 0.05, 0.006, m.stripe, -L / 2, cy - 0.15, s * (r * sz + 0.012));
      // hortum boruları (yan alt; yan markerlar bunun üstünde)
      cyl(body, 0.08, L - 3.6, m.alu, 'x', -L / 2 - 0.4, deckY - 0.1, s * (W / 2 - 0.12), 16);
    }
    // ön alt çerçeve (king pin eyeri) ve arka yürüyen aksam çerçevesi
    box(body, 2.4, 0.3, 1.2, m.chassis, -L + 1.4, deckY - 0.12, 0);
    for (const x of [-L + 0.6, -L + 2.4]) box(body, 0.2, 0.3, 1.9, m.darkMetal, x, deckY + 0.02, 0);
    beamFrom = Math.min(...axles) - R - 0.8;
    topY = cy + r + 0.45;
    frontPos = { x: -L + 0.06, y: deckY + 0.05, z: W / 2 - 0.12 };
    armRearY = deckY + 0.6;
    armFrontY = deckY + 0.6;
    socketY = deckY - 0.12;
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

  chassis(chassisG, m, { L, deckY, R, axles, landingX, sideGuard, rail, lampY, plateY, beamFrom, frontDeckY, crossStep, crossW });
  plate(group, plateY);

  const prof: [number, number][] = profile ?? [
    [-L, harnessY],
    [0, harnessY],
  ];

  // Tesisat görünümü: gövde gizlenmez, yarı saydam çizilir (setGhost); burada yalnızca gövde çizgileri ve
  // tesisatın okunacağı, tipin taban profilini izleyen açık renkli zemin şeridi kurulur.
  const solids: THREE.Mesh[] = [];
  group.updateMatrixWorld(true);
  const edgePos: number[] = [];
  const tmp = new THREE.Vector3();
  for (const root of [body, chassisG]) {
    root.traverse((o) => {
      const mm = o as THREE.Mesh;
      // lastikler ve yük (otomobiller) dahil her parça yarı saydam olur
      if (!mm.isMesh) return;
      solids.push(mm);
      mm.userData.mat = mm.material;
      mm.userData.cast = mm.castShadow;
      if (o.userData.noEdge || o.userData.cargo || (o as THREE.InstancedMesh).isInstancedMesh) return;
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
  sys.add(outline, sysFloor);
  sys.visible = false;
  group.add(sys);

  const anchors: Anchors = {
    L,
    W,
    topY,
    rear: { x: 0.0, lampY, lampZ: [W / 2 - 0.33, 0.48], plateY },
    side: { x0: -L + 1.0, x1: -0.6, z: W / 2 + 0.005, yAt: sideYAt },
    front: frontPos ?? { x: -L - 0.01, y: topY - 0.14, z: W / 2 - 0.12 },
    extra: (() => {
      const roofed = type === 'standart' || type === 'kapali' || type === 'frigo' || type === 'damper' || type === 'konteyner';
      return roofed
        ? { x: type === 'konteyner' ? -0.23 : type === 'damper' ? 0.0 : 0.05, y: topY - 0.14, z0: W / 2 - 0.13, z1: 0.72 }
        : { x: 0.0, y: lampY, z0: W / 2 - 0.12, z1: 0.76 };
    })(),
    armRear: { x: -0.2, y: armRearY, z: W / 2 },
    armFront: { x: -L + 0.25, y: armFrontY, z: W / 2 },
    socket: { x: onWall ? -L - 0.01 : -L - 0.03, y: socketY, onWall },
    harness: { y: harnessY, railZ: 0.4, junctionX: -0.65, frontX: -L + 0.35, profile: prof },
    center: new THREE.Vector3(-L / 2, topY / 2, 0),
    size: new THREE.Vector3(L, topY, W),
  };
  return { group, body, outline: sys, solids, anchors };
}

/** Tesisat görünümü: gövde, şasi ve tekerlekler yarı saydam (tipin silueti görünür, tesisat okunur). */
export function setGhost(t: TrailerBuild, mats: Mats, on: boolean) {
  for (const mm of t.solids) {
    mm.material = on ? mats.ghost : (mm.userData.mat as THREE.Material);
    mm.castShadow = on ? false : (mm.userData.cast as boolean);
  }
}

export function disposeGroup(g: THREE.Object3D) {
  g.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (mm.geometry && !isCachedWheelGeo(mm.geometry)) mm.geometry.dispose();
  });
}
function isCachedWheelGeo(geo: THREE.BufferGeometry) {
  for (const k of wheelCache.values()) if (Object.values(k).includes(geo)) return true;
  return geo === undefined;
}
