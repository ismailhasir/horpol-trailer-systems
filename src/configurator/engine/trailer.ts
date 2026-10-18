// Dorse modelleri: Blender'da betikle modellenip pişirilen GLB'ler (tools/blender/<tip>.py → engine/baked.ts kaydı).
// Burada model sahneye kurulur, tesisat görünümünün kontur çizgileri ve lamba/tesisat bağlantı noktaları (anchors)
// betiğin yazdığı JSON'dan üretilir. Koordinatlar metre: X boyuna (arka uç x=0, ön x=-L), Y yukarı, Z yanal.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { TrailerId } from '../data';
import type { Mats } from './materials';
import { BAKED, bakedContact, bakedSections, type BakedSpec } from './baked';
import { loadedModel } from './models';
import { isShared, markShared, mesh } from './geo';

/** Tipin Blender modeli. Modeli olmayan (gizli) tipler standart dorseyi gösterir. */
function specFor(type: TrailerId): BakedSpec {
  return BAKED[type] ?? (BAKED.standart as BakedSpec);
}

/** Tipin model dosyaları: [şasi + tekerlekler, gövde]. Engine kurmadan önce ikisinin yüklenmesini bekler. */
export function modelUrls(type: TrailerId): [string, string] {
  const b = specFor(type);
  return [b.chassis, b.body];
}

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

export function buildTrailer(type: TrailerId, m: Mats): TrailerBuild {
  const spec = specFor(type);
  const rig = loadedModel(spec.chassis);
  const bodyModel = loadedModel(spec.body);
  if (!rig || !bodyModel) throw new Error(`Dorse modeli yüklenmemiş: ${type}`);
  const S = spec.anchors;
  const L = S.L;
  const topY = S.topY;
  const group = new THREE.Group();
  const body = new THREE.Group();
  const chassisG = new THREE.Group();
  group.add(chassisG, body);
  // gövde tesisat görünümünde gizlenir (yerini kontur çizgileri gösterir); şasi kendi malzemesiyle kalır
  for (const mm of mergedFromModel(bodyModel)) body.add(mm);
  for (const mm of mergedFromModel(rig)) chassisG.add(mm);
  plate(group, S.rear.plateY, S.rear.x + 0.006);

  const edgePos: number[] = [];
  for (const loop of bakedSections(S)) {
    loop.forEach((p, i) => {
      const q = loop[(i + 1) % loop.length];
      edgePos.push(p.x, p.y, p.z, q.x, q.y, q.z);
    });
  }
  const edgeGeo = new THREE.BufferGeometry();
  edgeGeo.setAttribute('position', new THREE.Float32BufferAttribute(edgePos, 3));
  const sys = new THREE.Group();
  sys.add(new THREE.LineSegments(edgeGeo, m.outline));
  sys.visible = false;
  group.add(sys);
  // pişirilmiş zemin temas gölgesi (birleştirmeye girmez)
  group.add(bakedContact(spec));

  const anchors: Anchors = {
    L,
    W,
    topY,
    rear: { x: S.rear.x, lampY: S.rear.lampY, lampZ: [S.rear.lampZ[0], S.rear.lampZ[1]], plateY: S.rear.plateY, dropX: S.rear.dropX },
    side: { x0: S.side.x0, x1: S.side.x1, z: S.side.z, yAt: (x) => profileAt(S.side.profile as [number, number][], x), brackets: S.side.brackets },
    front: S.front,
    extra: S.extra,
    armRear: S.armRear,
    armFront: S.armFront,
    socket: { x: S.socket.x, y: S.socket.y, onWall: true },
    harness: { y: S.harness.y, railZ: 0.4, junctionX: -0.65, frontX: S.harness.frontX, profile: S.harness.profile as [number, number][], trunkZ: S.harness.trunkZ, rearZ: S.harness.rearZ },
    center: new THREE.Vector3(-L / 2, topY / 2, 0),
    size: new THREE.Vector3(L, topY, W),
  };
  return { group, body, outline: sys, anchors };
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
    // uv1: tekrarlanan dokulu yüzeylerde (tank kabuğu) AO ikinci UV'den okunur
    for (const k of Object.keys(g.attributes)) if (k !== 'position' && k !== 'normal' && k !== 'uv' && k !== 'uv1') g.deleteAttribute(k);
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
    // birleştirilecek geometrilerin öznitelik kümesi aynı olmalı: uv1 bazılarında varsa eksiklere sıfır eklenir
    if (b.geos.some((g) => g.attributes.uv1)) {
      for (const g of b.geos) if (!g.attributes.uv1) g.setAttribute('uv1', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    }
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

/** Tesisat görünümü: gövde gizlenir, şasi ve tekerlekler kendi malzemesiyle kalır. */
export function setGhost(t: TrailerBuild, on: boolean) {
  t.body.visible = !on;
}

export function disposeGroup(g: THREE.Object3D) {
  g.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (mm.geometry && !isShared(mm.geometry)) mm.geometry.dispose();
    if ((o as THREE.InstancedMesh).isInstancedMesh) (o as THREE.InstancedMesh).dispose();
  });
}
