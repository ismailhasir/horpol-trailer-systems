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
type WireKind = 'main' | 'side' | 'rear' | 'plate' | 'marker';
/** Kablolar şemada okunabilsin diye gerçek ölçüden kalın çizilir */
const WIRE_SCALE = 1.7;
function tube(group: THREE.Group, pts: THREE.Vector3[], r: number, mat: THREE.Material) {
  const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.1);
  const t = m(new THREE.TubeGeometry(curve, Math.max(12, pts.length * 10), r * WIRE_SCALE, 10, false), mat, false);
  group.add(t);
  return t;
}
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

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

  const wires: { kind: WireKind; pts: THREE.Vector3[]; r: number }[] = [];
  const hy = a.harness.y;
  const jx = a.harness.junctionX;
  const fx = a.harness.frontX;
  const rz = a.harness.railZ;

  // --- arka (stop) lambaları ---
  const stop = c.lamps.stop;
  const stopStyle = productById('stop', stop.product).style;
  const pairs = stop.qty / 2;
  for (let p = 0; p < pairs; p++) {
    for (const s of [1, -1]) {
      const z = s * a.rear.lampZ[p];
      const pos = V(a.rear.x + 0.0, a.rear.lampY, z);
      mount('stop', stopStyle, pos, (o) => {
        o.rotation.y = Math.PI / 2;
        if (s < 0) o.scale.x = -1;
      });
      wires.push({ kind: 'rear', r: 0.011, pts: [V(jx, hy, s * 0.12), V(jx + 0.25, hy, z * 0.8), V(-0.12, a.rear.lampY + 0.02, z), V(-0.01, a.rear.lampY, z)] });
    }
  }

  // --- plaka lambaları ---
  const pl = c.lamps.plate;
  const plStyle = productById('plate', pl.product).style;
  const pzs = pl.qty === 1 ? [0] : [-0.17, 0.17];
  for (const z of pzs) {
    mount('plate', plStyle, V(0.01, a.rear.plateY + 0.085, z), (o) => {
      o.rotation.y = Math.PI / 2;
    });
    wires.push({ kind: 'plate', r: 0.008, pts: [V(jx, hy, 0), V(jx + 0.2, hy - 0.05, z), V(-0.06, a.rear.plateY + 0.12, z), V(0.0, a.rear.plateY + 0.1, z)] });
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
      wires.push({ kind: 'side', r: 0.007, pts: [V(x, hy, s * rz), V(x, hy, s * (a.W / 2 - 0.15)), V(x, y, s * (a.W / 2 - 0.02))] });
    }
  }
  if (per > 0) {
    for (const s of [1, -1]) wires.push({ kind: 'side', r: 0.013, pts: [V(fx, hy, s * 0.08), V(fx + 0.3, hy, s * rz), V(jx, hy, s * rz), V(jx + 0.15, hy, s * 0.1)] });
  }

  // --- ön pozisyon ---
  const fr = c.lamps.front;
  if (fr.qty > 0) {
    const st = productById('front', fr.product).style;
    for (const s of [1, -1]) {
      const p = a.front;
      mount('front', st, V(p.x, p.y, s * p.z), (o) => {
        o.rotation.y = -Math.PI / 2;
      });
      wires.push({ kind: 'marker', r: 0.008, pts: [V(fx, hy, 0), V(fx - 0.15, hy + 0.1, s * (p.z - 0.1)), V(p.x + 0.06, (hy + p.y) / 2, s * (p.z - 0.05)), V(p.x + 0.04, p.y, s * p.z)] });
    }
  }

  // --- gabari (lastik kol) ---
  const ar = c.lamps.arm;
  if (ar.qty > 0) {
    const st = productById('arm', ar.product).style;
    const spots = ar.qty >= 4 ? [a.armRear, a.armFront] : [a.armRear];
    for (const sp of spots) {
      for (const s of [1, -1]) {
        mount('arm', st, V(sp.x, sp.y, s * sp.z), (o) => {
          if (s < 0) o.scale.z = -1;
        });
        const fromX = sp === a.armRear ? jx : fx;
        wires.push({ kind: 'marker', r: 0.008, pts: [V(fromX, hy, s * 0.15), V(sp.x, hy, s * (sp.z - 0.12)), V(sp.x, (hy + sp.y) / 2, s * (sp.z - 0.05)), V(sp.x, sp.y, s * (sp.z - 0.01))] });
      }
    }
  }

  // --- ek lambalar (Additional Lights) ---
  const ex = c.lamps.extra;
  if (ex.qty > 0) {
    const st = productById('extra', ex.product).style;
    const zs = ex.qty >= 4 ? [a.extra.z0, a.extra.z1] : [a.extra.z0];
    for (const z of zs) {
      for (const s of [1, -1]) {
        mount('extra', st, V(a.extra.x, a.extra.y, s * z), (o) => {
          o.rotation.y = Math.PI / 2;
        });
        wires.push({ kind: 'marker', r: 0.008, pts: [V(jx, hy, s * 0.2), V(-0.1, (hy + a.extra.y) / 2, s * (z - 0.05)), V(a.extra.x - 0.04, a.extra.y, s * z)] });
      }
    }
  }

  // --- soketler + ana hat ---
  const kinds: ('7' | '15')[] = c.socket === '7x2' ? ['7', '7'] : c.socket === '15' ? ['15'] : ['7', '15', '7'];
  const spacing = 0.15;
  kinds.forEach((k, i) => {
    const z = (i - (kinds.length - 1) / 2) * spacing;
    const s = socket(mats, k, k === '15' ? mats.socketGrey : i === 0 ? mats.socket : mats.socketGrey);
    s.rotation.y = -Math.PI / 2;
    s.position.set(a.socket.x, a.socket.y, z);
    s.traverse((o) => (o.userData.category = 'socket'));
    group.add(s);
    wires.push({ kind: 'main', r: 0.014, pts: [V(a.socket.x + 0.02, a.socket.y, z), V(a.socket.x + 0.18, a.socket.y - 0.05, z), V(fx - 0.1, hy, z * 0.4), V(fx, hy, 0)] });
  });
  wires.push({ kind: 'main', r: 0.022, pts: [V(fx, hy, 0), V(fx + 0.6, hy, 0), V((fx + jx) / 2, hy, 0), V(jx - 0.4, hy, 0), V(jx, hy, 0)] });

  // dağıtım kutusu
  const jb = m(new THREE.BoxGeometry(0.3, 0.1, 0.24), mats.plastic);
  jb.position.set(jx, hy, 0);
  harness.add(jb);

  for (const w of wires) {
    const t = tube(harness, w.pts, w.r, mats.wire[w.kind]);
    t.userData.kind = w.kind;
    // uçlarda konnektör
    const end = w.pts[w.pts.length - 1];
    const cn = m(new THREE.CylinderGeometry(w.r * WIRE_SCALE * 1.8, w.r * WIRE_SCALE * 1.8, 0.05, 12), mats.plastic, false);
    cn.position.copy(end);
    harness.add(cn);
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
