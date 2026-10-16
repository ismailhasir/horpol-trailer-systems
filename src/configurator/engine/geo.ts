// Dorse modellerinde ortak çizim yardımcıları (kutu, silindir, boru, levha, tekerlek). trailer.ts ve tanker.ts kullanır.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import type { Mats } from './materials';

export function mesh(geo: THREE.BufferGeometry, mat: THREE.Material, cast = true, receive = true) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = cast;
  m.receiveShadow = receive;
  return m;
}
/** Kutu: lx boyuna, ly yükseklik, lz genişlik; konum merkez */
export function box(parent: THREE.Object3D, lx: number, ly: number, lz: number, mat: THREE.Material, x: number, y: number, z: number, r = 0) {
  const geo = r > 0 ? new RoundedBoxGeometry(lx, ly, lz, 2, Math.min(r, lx / 2, ly / 2, lz / 2)) : new THREE.BoxGeometry(lx, ly, lz);
  const m = mesh(geo, mat);
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}
export function cyl(parent: THREE.Object3D, r: number, len: number, mat: THREE.Material, axis: 'x' | 'y' | 'z', x: number, y: number, z: number, seg = 20) {
  const m = mesh(new THREE.CylinderGeometry(r, r, len, seg), mat);
  if (axis === 'x') m.rotation.z = Math.PI / 2;
  if (axis === 'z') m.rotation.x = Math.PI / 2;
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}
/** Aynı kutudan çok sayıda (geometri paylaşılır; sonunda malzemeye göre tek ağa birleştirilir) */
export function boxes(parent: THREE.Object3D, lx: number, ly: number, lz: number, mat: THREE.Material, pts: [number, number, number][]) {
  if (!pts.length) return;
  const geo = new THREE.BoxGeometry(lx, ly, lz);
  for (const p of pts) {
    const b = mesh(geo, mat);
    b.position.set(p[0], p[1], p[2]);
    b.userData.noEdge = true;
    parent.add(b);
  }
}
export const V3 = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
export const UP = V3(0, 1, 0);
/** İki nokta arası boru/çubuk (korkuluk, merdiven, hortum) */
export function rod(parent: THREE.Object3D, a: THREE.Vector3, b: THREE.Vector3, r: number, mat: THREE.Material, seg = 10) {
  const d = b.clone().sub(a);
  const m = mesh(new THREE.CylinderGeometry(r, r, d.length(), seg), mat);
  m.position.copy(a).addScaledVector(d, 0.5);
  m.quaternion.setFromUnitVectors(UP, d.normalize());
  m.userData.noEdge = true;
  parent.add(m);
  return m;
}
/** Kırık çizgi boyunca boru; köşelerde küre (kesintisiz görünür) */
export function pipe(parent: THREE.Object3D, pts: THREE.Vector3[], r: number, mat: THREE.Material, seg = 10) {
  for (let i = 1; i < pts.length; i++) rod(parent, pts[i - 1], pts[i], r, mat, seg);
  for (let i = 1; i < pts.length - 1; i++) {
    const k = mesh(new THREE.SphereGeometry(r, seg, 6), mat);
    k.position.copy(pts[i]);
    k.userData.noEdge = true;
    parent.add(k);
  }
}
/** XY düzleminde çokgen levha, z'de ortalanmış kalınlık (kaide/destek sacları) */
export function slab(parent: THREE.Object3D, pts: [number, number][], depth: number, mat: THREE.Material, z: number) {
  const g = new THREE.ExtrudeGeometry(new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y))), { depth, bevelEnabled: false });
  g.translate(0, 0, z - depth / 2);
  const m = mesh(g, mat);
  parent.add(m);
  return m;
}
/** a-b doğrusu boyunca, `across` yönünde w genişlikte şerit (iki yüzlü malzemeyle) */
export function ribbon(parent: THREE.Object3D, a: THREE.Vector3, b: THREE.Vector3, across: THREE.Vector3, w: number, mat: THREE.Material) {
  const h = across.clone().setLength(w / 2);
  const p = [a.clone().sub(h), a.clone().add(h), b.clone().sub(h), b.clone().add(h)];
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p.flatMap((v) => [v.x, v.y, v.z]), 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 0, 1, 1, 0, 1, 1], 2));
  g.setIndex([0, 2, 1, 1, 2, 3]);
  g.computeVertexNormals();
  const m = mesh(g, mat, false);
  m.userData.noEdge = true;
  parent.add(m);
  return m;
}
export const range = (a: number, b: number, step: number) => {
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
export const wheelCache = new Map<number, WheelKit>();
export function wheelKit(R: number): WheelKit {
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
export function wheel(m: Mats, R: number, side: 1 | -1, hubMat: THREE.Material = m.chrome) {
  const k = wheelKit(R);
  const s = R / 0.53;
  const g = new THREE.Group();
  g.add(mesh(k.tire, m.tire));
  g.add(mesh(k.rim, m.alu, false));
  const face = mesh(k.face, m.alu, false);
  face.position.z = 0.1 * s;
  g.add(face);
  const hub = mesh(k.hub, hubMat, false);
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


export function isCachedWheelGeo(geo: THREE.BufferGeometry) {
  for (const k of wheelCache.values()) if (Object.values(k).includes(geo)) return true;
  return geo === undefined;
}
