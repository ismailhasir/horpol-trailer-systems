// Akaryakıt tankeri (≈34–39 m³). Referanslar vault'ta `Teknik Data/Tanker Dorse`: üretici 3D çıktıları (gövde, 17 açı),
// çıplak şase çıktıları (18 açı) ve broşür ölçüleri. Ölçüler: toplam uzunluk 11,42 m, eyer yüksekliği 1,22 m,
// king pin → orta aks 6,7 m, 3 × 9 t aks (aralık 1,31 m), 385/65 R22,5 lastik (Ø 1,07 m).
// Yapı: tam boy siyah I-kirişli şasi (önde basık boyun), üstünde beşiklerle oturan tank: üstü yatay, önü konik, arkası
// silindirik, iki ucu bombeli. Üstte açık kaporta ve kapaklar; arkada merdiven; yanlarda hortum borusu; sağda alet dolabı.
// Dorse beyaz, yanlarda site logosu. Şasi `chassisG`'ye, gövde `body`'ye kurulur: tesisat görünümünde gövde silikleşir,
// şasi gerçek malzemesiyle kalır.
import * as THREE from 'three';
import type { Mats } from './materials';
import { box, boxes, cyl, mesh, pipe, range, rod, slab, V3, wheel } from './geo';

const W = 2.55;
const R = 0.536;

/** Set uzunluğundan dorse boyu: 12 ve 13,6 m setler 11,42 m tankere, 9 m set 9,4 m (2 akslı) tankere takılır */
export function tankerLength(setLength: number) {
  return setLength >= 12 ? 11.42 : 9.4;
}

export interface TankerBuild {
  deckY: number;
  topY: number;
  lampY: number;
  plateY: number;
  harnessY: number;
  socket: { x: number; y: number };
  frontX: number;
  front: { x: number; y: number; z: number };
  armRear: { x: number; y: number; z: number };
  armFront: { x: number; y: number; z: number };
  extra: { x: number; y: number; z0: number; z1: number };
  side: { x0: number; x1: number; y: number };
  sections: THREE.Vector3[][];
}

interface Station {
  x: number;
  cy: number;
  ry: number;
  rz: number;
}

/** Eliptik kesitlerden tek parça, pürüzsüz kabuk (x artan sırada istasyonlar; uçlarda yarıçap 0 olabilir) */
function loft(st: Station[], seg = 80) {
  const pos: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  const x0 = st[0].x;
  const x1 = st[st.length - 1].x;
  st.forEach((s, i) => {
    for (let j = 0; j <= seg; j++) {
      const a = (j / seg) * Math.PI * 2;
      pos.push(s.x, s.cy + s.ry * Math.cos(a), s.rz * Math.sin(a));
      uv.push((s.x - x0) / (x1 - x0), j / seg);
    }
    if (i > 0) {
      const p = (i - 1) * (seg + 1);
      const q = i * (seg + 1);
      for (let j = 0; j < seg; j++) idx.push(p + j, p + j + 1, q + j, p + j + 1, q + j + 1, q + j);
    }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

/** YZ düzleminde çokgen ([z, y]), x boyunca `depth` kalınlıkta (beşik ve kaporta uç sacı gibi enine levhalar) */
function crossPlate(parent: THREE.Object3D, pts: [number, number][], x: number, depth: number, mat: THREE.Material) {
  const g = new THREE.ExtrudeGeometry(new THREE.Shape(pts.map(([z, y]) => new THREE.Vector2(z, y))), { depth, bevelEnabled: false });
  g.rotateY(Math.PI / 2);
  const m = mesh(g, mat);
  m.position.x = x - depth / 2;
  parent.add(m);
  return m;
}

/** a→b doğrultusunda (XY düzleminde eğik olabilen) kutu */
function beam(parent: THREE.Object3D, a: THREE.Vector3, b: THREE.Vector3, h: number, w: number, mat: THREE.Material) {
  const d = b.clone().sub(a);
  const m = mesh(new THREE.BoxGeometry(d.length(), h, w), mat);
  m.position.copy(a).addScaledVector(d, 0.5);
  m.rotation.z = Math.atan2(d.y, d.x);
  parent.add(m);
  return m;
}

/** Tank yüzeyine oturan kavisli logo çıkartması (kesiti sabit bölgede) */
function tankDecal(parent: THREE.Object3D, mat: THREE.Material, xc: number, yc: number, h: number, sec: Station, side: 1 | -1) {
  const w = h * (720 / 528);
  const g = new THREE.PlaneGeometry(w, h, 24, 16);
  const p = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < p.count; i++) {
    const u = p.getX(i);
    const y = yc + p.getY(i);
    const k = Math.min(1, Math.abs(y - sec.cy) / sec.ry);
    const z = sec.rz * Math.sqrt(1 - k * k) + 0.006;
    p.setXYZ(i, xc + side * u, y, side * z);
  }
  g.computeVertexNormals();
  const m = mesh(g, mat, false, false);
  m.userData.noEdge = true;
  parent.add(m);
}

export function buildTanker(body: THREE.Group, chassisG: THREE.Group, m: Mats, L: number): TankerBuild {
  const sections: THREE.Vector3[][] = [];
  const long = L >= 11;
  const k = L / 11.42;
  const cb = m.chassisBlack;

  // ---------------- şasi ----------------
  const deckY = 1.36; // şasi üstü (tank beşikleri buraya oturur)
  const deepBot = deckY - 0.4; // ana kirişin derin bölümünün altı
  const neckBot = 1.22; // basık boyun altı = eyer yüksekliği (H5)
  const xCF = -L + 0.45; // şasi ön ucu (tankın ön bombesi bunun önünde)
  const xCR = -0.05;
  const xN1 = -L + 3.3; // boyun burada biter
  const xN0 = -L + 3.8; // derin kiriş burada başlar
  const kingX = -L + 1.96;
  const landingX = -L + 3.97;
  const axles = long ? [-1.45, -2.76, -4.07] : [-1.6, -2.91];
  const axFront = Math.min(...axles);

  // ana kirişler (I profil: gövde sacı + üst/alt başlık)
  for (const z of [-0.5, 0.5]) {
    slab(chassisG, [[xCF, deckY], [xCR, deckY], [xCR, deepBot], [xN0, deepBot], [xN1, neckBot], [xCF, neckBot]], 0.014, cb, z);
    box(chassisG, xCR - xCF, 0.018, 0.17, cb, (xCF + xCR) / 2, deckY - 0.009, z);
    box(chassisG, xCR - xN0, 0.018, 0.17, cb, (xN0 + xCR) / 2, deepBot + 0.009, z);
    box(chassisG, xN1 - xCF, 0.018, 0.17, cb, (xCF + xN1) / 2, neckBot + 0.009, z);
    beam(chassisG, V3(xN1, neckBot + 0.009, z), V3(xN0, deepBot + 0.009, z), 0.018, 0.17, cb);
    // gövde sacı berkitmeleri
    boxes(chassisG, 0.012, 0.34, 0.07, cb, range(xN0 + 0.4, xCR - 0.3, 0.9).map((x) => [x, deckY - 0.2, z * 0.94]));
  }
  // traversler (C profil): derin bölümde kirişlerin arasında, boyunda ince
  boxes(chassisG, 0.07, 0.12, 0.98, cb, range(xN0 + 0.25, xCR - 0.3, 0.62).map((x) => [x, deckY - 0.15, 0]));
  boxes(chassisG, 0.06, 0.05, 0.98, cb, range(xCF + 0.15, xN1 - 0.1, 0.5).map((x) => [x, neckBot + 0.035, 0]));
  // king pin plakası ve pimi
  box(chassisG, 1.5, 0.02, 1.12, m.darkMetal, kingX + 0.2, neckBot + 0.01, 0);
  cyl(chassisG, 0.045, 0.085, m.steel, 'y', kingX, neckBot - 0.04, 0, 16);
  cyl(chassisG, 0.06, 0.02, m.steel, 'y', kingX, neckBot - 0.005, 0, 16);
  // ön travers: uçlarında ön pozisyon lambaları, ortasında soketler
  box(chassisG, 0.1, 0.1, W - 0.06, cb, xCF + 0.05, 1.29, 0);
  // konsollar (kirişten dış raya) ve yan marker rayı
  const railX0 = -0.35;
  const railX1 = xN0 + 0.2;
  for (const z of [-1, 1]) {
    box(chassisG, railX0 - railX1, 0.1, 0.04, cb, (railX0 + railX1) / 2, 1.2, z * (W / 2 - 0.04));
    for (const x of range(railX1 + 0.1, railX0 - 0.1, (railX0 - railX1 - 0.2) / Math.round((railX0 - railX1) / 1.25))) {
      const o = box(chassisG, 0.05, 0.08, W / 2 - 0.56, cb, x, 1.22, z * (0.507 + (W / 2 - 0.56) / 2));
      o.userData.noEdge = true;
    }
  }

  // akslar ve hava süspansiyonu (salıncak kolu, körük, amortisör, askı braketi), fren körükleri, tekerlekler
  for (const x of axles) {
    cyl(chassisG, 0.07, 2.0, m.darkMetal, 'z', x, R, 0, 18);
    for (const z of [-0.5, 0.5]) {
      box(chassisG, 0.14, deepBot - 0.5, 0.12, cb, x - 0.55, (deepBot + 0.5) / 2, z);
      box(chassisG, 1.05, 0.08, 0.1, m.darkMetal, x - 0.075, 0.48, z);
      cyl(chassisG, 0.15, 0.26, m.rubber, 'y', x + 0.38, 0.66, z, 22);
      box(chassisG, 0.32, 0.03, 0.3, m.darkMetal, x + 0.38, 0.805, z);
      box(chassisG, 0.2, deepBot - 0.82, 0.2, cb, x + 0.38, (deepBot + 0.82) / 2, z);
      rod(chassisG, V3(x + 0.12, 0.5, z * 1.12), V3(x - 0.22, deepBot - 0.02, z * 1.12), 0.028, m.darkMetal, 8);
      cyl(chassisG, 0.085, 0.22, m.darkMetal, 'x', x - 0.22, R + 0.06, z * 1.24, 16);
    }
    for (const s of [1, -1] as const) {
      const wh = wheel(m, R, s);
      wh.position.set(x, R, s * (W / 2 - 0.33));
      chassisG.add(wh);
    }
  }
  // çamurluklar: aks başına kavisli kabuk + aralarında düz bağlantı, son aksın arkasında paçalar
  {
    const geo = new THREE.CylinderGeometry(R + 0.07, R + 0.07, 0.5, 32, 1, true, Math.PI - 1.2, 2.4);
    geo.rotateX(Math.PI / 2);
    const xs = [...axles].sort((a, b) => a - b);
    for (const z of [-1, 1]) {
      const zc = z * (W / 2 - 0.33);
      for (const x of xs) {
        const f = mesh(geo, m.fender);
        f.position.set(x, R, zc);
        chassisG.add(f);
      }
      for (let i = 1; i < xs.length; i++) box(chassisG, xs[i] - xs[i - 1] - 0.62, 0.012, 0.5, m.fender, (xs[i] + xs[i - 1]) / 2, R + 0.5, zc);
      const back = Math.max(...xs) + R + 0.12;
      box(chassisG, 0.015, 0.78, 0.56, m.rubber, back, 0.52, zc);
      rod(chassisG, V3(back - 0.05, 0.9, zc), V3(back - 0.05, 1.18, zc), 0.02, cb, 6);
    }
  }
  // yan koruma (alüminyum profiller, siyah dikmeler)
  {
    const x0 = axFront - R - 0.35;
    const x1 = landingX + 0.35;
    for (const z of [-1, 1]) {
      for (const y of [0.55, 0.85]) box(chassisG, x0 - x1, 0.1, 0.03, m.alu, (x0 + x1) / 2, y, z * (W / 2 - 0.06));
      for (const x of [x1 + 0.05, (x0 + x1) / 2, x0 - 0.05]) box(chassisG, 0.05, 1.18 - 0.5, 0.05, cb, x, (1.18 + 0.5) / 2, z * (W / 2 - 0.085));
    }
  }
  // iniş ayakları: gövde, iç bacak, taban, ara mil, kol (sağ tarafta) ve çaprazlar
  for (const z of [-0.62, 0.62]) {
    box(chassisG, 0.13, 0.62, 0.13, cb, landingX, 0.87, z);
    box(chassisG, 0.1, 0.48, 0.1, m.darkMetal, landingX, 0.38, z);
    box(chassisG, 0.3, 0.04, 0.28, cb, landingX, 0.12, z);
    box(chassisG, 0.2, 0.2, 0.012, cb, landingX, deepBot + 0.05, z > 0 ? 0.565 : -0.565);
    rod(chassisG, V3(landingX + 0.06, 0.62, z), V3(landingX + 0.85, deepBot, z * 0.82), 0.025, cb, 8);
  }
  rod(chassisG, V3(landingX, 0.98, -0.62), V3(landingX, 0.98, 0.62), 0.025, m.darkMetal, 8);
  box(chassisG, 0.16, 0.14, 0.1, cb, landingX, 1.0, 0.72);
  pipe(chassisG, [V3(landingX, 0.95, 0.78), V3(landingX, 0.95, 0.95), V3(landingX, 0.75, 1.05)], 0.014, m.darkMetal, 8);
  // hava tankları (kayışlı) ve yedek lastik taşıyıcısı
  for (const z of [-0.28, 0.28]) {
    cyl(chassisG, 0.15, 0.8, m.darkMetal, 'x', landingX + 0.85, 0.78, z, 22);
    for (const dx of [-0.25, 0.25]) cyl(chassisG, 0.155, 0.03, cb, 'x', landingX + 0.85 + dx, 0.78, z, 22);
  }
  {
    const xs = (axFront - R + landingX + 1.3) / 2;
    const sp = wheel(m, R, 1);
    sp.rotation.x = Math.PI / 2;
    sp.position.set(xs, 0.42, 0);
    chassisG.add(sp);
    for (const z of [-0.5, 0.5]) rod(chassisG, V3(xs - 0.55, 0.22, z), V3(xs - 0.55, deepBot, z), 0.02, cb, 6);
    box(chassisG, 0.06, 0.04, 1.0, cb, xs - 0.55, 0.22, 0);
  }
  // EBS modülatörü
  box(chassisG, 0.26, 0.18, 0.3, m.darkMetal, axles[axles.length - 1] - 0.5, deckY - 0.3, 0.2, 0.02);
  // arka: kapanış traversi, arka levha, lamba barı (alüminyum), arka alt koruma tamponu, plaka tutucu
  box(chassisG, 0.12, 0.4, 1.1, cb, xCR - 0.06, deckY - 0.2, 0);
  box(chassisG, 0.05, 0.3, W - 0.04, cb, -0.025, 1.18, 0, 0.01);
  const lampY = 0.92;
  const plateY = 0.7;
  box(chassisG, 0.1, 0.13, W - 0.02, m.alu, -0.06, lampY, 0, 0.012);
  boxes(chassisG, 0.012, 0.03, 0.05, m.darkMetal, range(-0.5, 0.5, 0.25).flatMap((z) => [[-0.004, lampY + 0.03, z], [-0.004, lampY - 0.03, z]] as [number, number, number][]));
  for (const z of [-0.55, 0.55]) box(chassisG, 0.08, deepBot - 0.48, 0.08, cb, -0.2, (deepBot + 0.48) / 2, z);
  box(chassisG, 0.12, 0.1, 2.3, cb, -0.18, 0.53, 0, 0.01);
  for (const z of [-1, 1]) box(chassisG, 0.13, 0.11, 0.04, m.plastic, -0.18, 0.53, z * 1.17);
  box(chassisG, 0.04, 0.17, 0.58, cb, -0.04, plateY, 0);

  // ---------------- tank ----------------
  const yTop = 3.5;
  const ry1 = 1.05;
  const rz1 = 1.15;
  const ry0 = 0.9;
  const rz0 = 1.05;
  const xTip = -L + 0.02;
  const hF = 0.34;
  const hR = 0.33;
  const xF = xTip + hF;
  const xRt = -0.3;
  const xR = xRt - hR;
  const xJ = xF + (xR - xF) * 0.36;
  const sec = (x: number): Station => {
    const t = x >= xJ ? 1 : Math.max(0, (x - xF) / (xJ - xF));
    const ry = ry0 + (ry1 - ry0) * t;
    const rz = rz0 + (rz1 - rz0) * t;
    return { x, cy: yTop - ry, ry, rz };
  };
  const bot = (x: number, z: number) => {
    const s = sec(x);
    return s.cy - s.ry * Math.sqrt(Math.max(0, 1 - (z / s.rz) ** 2));
  };
  const st: Station[] = [];
  const K = 12;
  const front = sec(xF);
  const rear = sec(xR);
  for (let i = 0; i < K; i++) {
    const t = Math.cos(((i / K) * Math.PI) / 2); // uçtan (1) gövdeye (0)
    const s = Math.sqrt(1 - t * t);
    st.push({ x: xF - hF * t, cy: front.cy, ry: front.ry * s, rz: front.rz * s });
  }
  st.push(front, sec(xJ), rear);
  for (let i = K - 1; i >= 0; i--) {
    const t = Math.cos(((i / K) * Math.PI) / 2);
    const s = Math.sqrt(1 - t * t);
    st.push({ x: xR + hR * t, cy: rear.cy, ry: rear.ry * s, rz: rear.rz * s });
  }
  body.add(mesh(loft(st), m.paint));
  // kaynak dikişleri (bölme duvarları) ve tesisat görünümü için kesit çizgileri
  const seams = [xJ, ...range(xJ + (xR - xJ) / 3, xR - 0.2, (xR - xJ) / 3)];
  for (const x of seams) {
    const s = sec(x);
    const ring = mesh(new THREE.TorusGeometry(1, 0.0065, 6, 96), m.paint);
    ring.rotation.y = Math.PI / 2;
    ring.scale.set(s.rz, s.ry, 1);
    ring.position.set(x, s.cy, 0);
    ring.userData.noEdge = true;
    body.add(ring);
  }
  // tesisat görünümünde gövde gizlenir; tankın yerini ince kontur çizgileri gösterir (kesitler + boyuna çizgiler)
  for (const x of [xF, xJ, ...range(xJ + (xR - xJ) / 4, xR - 0.1, (xR - xJ) / 4), xR]) {
    const s = sec(x);
    sections.push(Array.from({ length: 64 }, (_, i) => V3(x, s.cy + Math.cos((i / 64) * Math.PI * 2) * s.ry, Math.sin((i / 64) * Math.PI * 2) * s.rz)));
  }
  for (const a of [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2]) {
    for (let i = 1; i < st.length; i++) {
      const p = st[i - 1];
      const q = st[i];
      sections.push([V3(p.x, p.cy + p.ry * Math.cos(a), p.rz * Math.sin(a)), V3(q.x, q.cy + q.ry * Math.cos(a), q.rz * Math.sin(a))]);
    }
  }

  // beşikler: şasi üstünden tank tabanını saran siyah destek sacları; önde uzun ön beşik (king pin bölgesi)
  const cradleShape = (x: number, half: number): [number, number][] => {
    const pts: [number, number][] = [[-half, deckY], [half, deckY]];
    for (let i = 0; i <= 16; i++) {
      const z = half - (2 * half * i) / 16;
      pts.push([z, bot(x, z) + 0.03]);
    }
    return pts;
  };
  for (const d of [0.95, 2.1, 3.4, 4.75, 6.05, 7.15].map((v) => v * k)) {
    if (-d < xF + 2.4) continue;
    crossPlate(body, cradleShape(-d, 1.02), -d, 0.16, cb);
  }
  {
    const x0 = xCF + 0.05;
    const x1 = xF + 2.35;
    crossPlate(body, cradleShape(x1, 0.95), (x0 + x1) / 2, x1 - x0, cb);
  }

  // üst kaporta (devrilme koruması): eğik yan saclar, uç sacları, üst başlık; içinde kapaklar ve yürüme şeritleri
  const fx0 = xF + 0.3;
  const fx1 = -0.55;
  const fl = fx1 - fx0;
  const fc = (fx0 + fx1) / 2;
  for (const z of [-1, 1]) {
    const wall = box(body, fl, 0.55, 0.012, m.fairingGrey, fc, yTop + 0.13, z * 0.7);
    wall.rotation.x = z * 0.578;
    box(body, fl, 0.03, 0.07, m.alu, fc, yTop + 0.37, z * 0.86, 0.01);
    box(body, fl - 0.4, 0.025, 0.26, m.alu, fc, yTop - 0.04, z * 0.4);
  }
  const endPlate: [number, number][] = [[-0.55, yTop - 0.1], [0.55, yTop - 0.1], [0.87, yTop + 0.38], [-0.87, yTop + 0.38]];
  crossPlate(body, endPlate, fx0, 0.02, m.fairingGrey);
  crossPlate(body, endPlate, fx1, 0.02, m.fairingGrey);
  for (const z of [-1, 1]) cyl(body, 0.055, 0.02, m.reflRed, 'x', fx1 + 0.015, yTop + 0.05, z * 0.56, 20);
  const comp = long ? 5 : 4;
  for (let i = 0; i < comp; i++) {
    const x = fx0 + 0.7 + ((fl - 1.4) * i) / (comp - 1);
    cyl(body, 0.25, 0.1, m.alu, 'y', x, yTop + 0.03, 0, 32);
    cyl(body, 0.27, 0.025, m.steel, 'y', x, yTop + 0.09, 0, 32);
    cyl(body, 0.05, 0.12, m.darkMetal, 'y', x + 0.12, yTop + 0.16, 0.1, 12);
  }

  // arka merdiven (yol tarafının tersi, -Z): tampondan kaportanın üstüne kıvrılır, üstte tutamak
  {
    const lz = -0.46;
    const lx = -0.2;
    for (const dz of [-0.17, 0.17]) pipe(body, [V3(lx, 1.06, lz + dz), V3(lx, yTop - 0.25, lz + dz), V3(fx1 - 0.05, yTop + 0.38, lz + dz), V3(fx1 - 0.05, yTop + 0.78, lz + dz)], 0.02, m.alu, 8);
    for (let y = 1.25; y < yTop - 0.3; y += 0.28) rod(body, V3(lx, y, lz - 0.17), V3(lx, y, lz + 0.17), 0.016, m.alu, 8);
  }

  // hortum boruları (iki yanda), braketleri ve kelepçeleri
  const tubeY = 1.66;
  const tz = W / 2 - 0.13;
  const tx0 = -L + 4.82;
  const tx1 = -0.55;
  for (const z of [-1, 1]) {
    cyl(body, 0.1, tx1 - tx0, m.chrome, 'x', (tx0 + tx1) / 2, tubeY, z * tz, 28);
    for (const x of [tx0, tx1]) cyl(body, 0.105, 0.04, m.darkMetal, 'x', x, tubeY, z * tz, 28);
    for (const x of range(tx0 + 0.6, tx1 - 0.4, (tx1 - tx0 - 1.0) / 3)) {
      cyl(body, 0.106, 0.03, m.alu, 'x', x, tubeY, z * tz, 28);
      box(body, 0.06, tubeY - 1.25, 0.04, cb, x, (tubeY + 1.25) / 2 - 0.05, z * (tz + 0.02));
    }
  }

  // alet / armatür dolabı (sağ, -Z): iniş ayağı ile ön aks arasında
  {
    const d0 = axFront - R - 0.3;
    const d1 = landingX + 0.3;
    const zc = -(W / 2 - 0.25);
    box(body, d0 - d1, 0.72, 0.47, m.alu, (d0 + d1) / 2, 0.77, zc, 0.02);
    box(body, 0.012, 0.66, 0.006, m.darkMetal, (d0 + d1) / 2, 0.77, zc - 0.237);
    for (const f of [0.25, 0.75]) box(body, 0.12, 0.07, 0.012, m.plastic, d1 + (d0 - d1) * f, 0.86, zc - 0.238);
  }

  // yangın tüpü dolapları (arka köşeler), ADR plakaları ve tehlike etiketleri
  for (const z of [-1, 1]) box(body, 0.22, 0.56, 0.2, m.paintRed, -0.16, 1.4, z * 1.1, 0.02);
  const sign = (mat: THREE.Material, w: number, h: number, x: number, y: number, z: number, ry: number) => {
    const p = mesh(new THREE.PlaneGeometry(w, h), mat, false, false);
    p.rotation.y = ry;
    p.position.set(x, y, z);
    p.userData.noEdge = true;
    body.add(p);
  };
  sign(m.adr, 0.4, 0.3, 0.003, 1.18, 0.62, Math.PI / 2);
  sign(m.hazard3, 0.3, 0.3, 0.003, 1.18, 0.98, Math.PI / 2);
  sign(m.logoWhite, 0.4, 0.29, 0.003, 1.18, -0.55, Math.PI / 2);
  for (const z of [-1, 1]) {
    const xs = -L * 0.42;
    rod(body, V3(xs, tubeY + 0.1, z * tz), V3(xs, tubeY + 0.2, z * tz), 0.012, m.darkMetal, 6);
    sign(m.adr, 0.4, 0.3, xs, tubeY + 0.33, z * (tz + 0.01), z > 0 ? 0 : Math.PI);
    sign(m.hazard3, 0.3, 0.3, -1.3 * k, tubeY + 0.3, z * (tz + 0.01), z > 0 ? 0 : Math.PI);
    rod(body, V3(-1.3 * k, tubeY + 0.1, z * tz), V3(-1.3 * k, tubeY + 0.16, z * tz), 0.012, m.darkMetal, 6);
  }

  // logo: tankın iki yanında, silindirik bölümün ortasında
  for (const s of [1, -1] as const) tankDecal(body, m.logo, (xJ + xR) / 2, yTop - ry1 + 0.12, 1.15, rear, s);

  return {
    deckY,
    topY: yTop + 0.38,
    lampY,
    plateY,
    harnessY: 1.305,
    socket: { x: xCF - 0.01, y: 1.29 },
    frontX: xCF + 0.4,
    front: { x: xCF - 0.005, y: 1.29, z: W / 2 - 0.1 },
    armRear: { x: -0.1, y: lampY + 0.09, z: W / 2 },
    armFront: { x: xCF + 0.25, y: 1.36, z: W / 2 },
    extra: { x: fx1 + 0.03, y: yTop + 0.2, z0: 0.72, z1: 0.42 },
    side: { x0: railX1 + 0.1, x1: -0.6, y: 1.2 },
    sections,
  };
}
