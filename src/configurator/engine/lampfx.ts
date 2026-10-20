// Lamba modelleri (tools/blender/lamps.py → src/assets/models/lamp-<id>.glb) ve ışık işlevlerinin yakılması.
// GLB sözleşmesi: düğümler BODY / INNER / LENS / EMIT.<işlev>; ışık veren malzemelerin adı "E.<işlev>.<renk>[.<etiket>]".
// Birden çok işlevin paylaştığı kılavuz "E.position+stop.red": işlevlerden biri açıksa yanar (pozisyonda sönük, frende parlak).
// Klonlar malzemeyi paylaşır: bir işlevin malzemesini değiştirmek o işlevi tüm lambalarda yakar (tek kaynak).
import * as THREE from 'three';
import { loadedModel, loadModel } from './models';

export type LampFn = 'position' | 'stop' | 'turn' | 'reverse' | 'fog' | 'marker' | 'front' | 'outline' | 'plate' | 'work' | 'beacon';
/** Kullanıcının açıp kapatabildiği işlevler (pozisyon grubu: position + marker + front + outline + plate birlikte) */
export type FnToggle = 'position' | 'stop' | 'turn' | 'reverse' | 'fog' | 'work' | 'beacon';
export const FN_TOGGLES: FnToggle[] = ['position', 'stop', 'turn', 'reverse', 'fog', 'work', 'beacon'];
const GROUP: Record<LampFn, FnToggle> = {
  position: 'position',
  marker: 'position',
  front: 'position',
  outline: 'position',
  plate: 'position',
  stop: 'stop',
  turn: 'turn',
  reverse: 'reverse',
  fog: 'fog',
  work: 'work',
  beacon: 'beacon',
};

const urls = import.meta.glob('../../assets/models/lamp-*.glb', { query: '?url', import: 'default', eager: true }) as Record<string, string>;
const URL_BY_ID = new Map<string, string>();
for (const [k, v] of Object.entries(urls)) URL_BY_ID.set(k.replace(/^.*lamp-/, '').replace(/\.glb$/, ''), v);

export function lampUrl(id: string): string | undefined {
  return URL_BY_ID.get(id);
}
export function lampReady(id: string): boolean {
  const u = URL_BY_ID.get(id);
  return !!u && !!loadedModel(u);
}
const failed = new Set<string>();
/** Yüklenemeyen lamba (ağ hatası): tekrar denenmez, yer tutucu kalır */
export function lampFailed(id: string) {
  return failed.has(id);
}
export function loadLamp(id: string): Promise<unknown> {
  const u = URL_BY_ID.get(id);
  return u
    ? loadModel(u).catch((e) => {
        failed.add(id);
        console.error(e);
        return null;
      })
    : Promise.resolve(null);
}

interface EmitMat {
  mat: THREE.MeshStandardMaterial;
  fns: LampFn[];
  color: THREE.Color;
}
const emitMats: EmitMat[] = [];
/** renkli dış lensler: yanan işlevin renginde hafif ışır (gerçek lambada lensin tamamı aydınlanır) */
const lensMats: { mat: THREE.MeshStandardMaterial; color: string; gain: number }[] = [];
/** "Lens.<renk>.cad": ışık kılavuzları lensin hemen ardında (üretici CAD modeli), lensin kendisi az parlar */
const LENS_GAIN: Record<string, number> = { cad: 0.25 };
const registered = new WeakSet<THREE.Object3D>();
// yanan ışık rengi: gerçek LED tayfına yakın (kırmızı ~625 nm biraz turuncuya, turuncu ~590 nm, soğuk beyaz)
const GLOW: Record<string, string> = { red: '#ff3a18', amber: '#ff9010', white: '#eef3ff' };
/** paylaşılan kılavuzda tam güç işlevler: yalnız pozisyon/kontur yanıyorsa kılavuz sönük */
const STRONG = new Set<LampFn>(['stop', 'turn', 'reverse', 'fog', 'work', 'beacon']);

/** Yüklenmiş lamba modelinin klonu (malzemeler paylaşılır); yüklenmemişse null */
export function lampInstance(id: string): THREE.Object3D | null {
  const u = URL_BY_ID.get(id);
  const model = u ? loadedModel(u) : null;
  if (!model) return null;
  if (!registered.has(model)) {
    registered.add(model);
    model.traverse((o) => {
      const mm = o as THREE.Mesh;
      if (!mm.isMesh) return;
      // dokulu malzeme UV'siz ağda gölgelendiriciyi bozar: eksikse boş UV kanalı
      if (!mm.geometry.attributes.uv) mm.geometry.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(mm.geometry.attributes.position.count * 2), 2));
      const mats = Array.isArray(mm.material) ? mm.material : [mm.material];
      for (const m of mats as THREE.MeshStandardMaterial[]) {
        const p = m.name.split('.');
        if (p[0] === 'E' && p.length >= 3 && !emitMats.some((e) => e.mat === m)) {
          emitMats.push({ mat: m, fns: p[1].split('+') as LampFn[], color: new THREE.Color(GLOW[p[2]] ?? '#ffffff') });
        }
        if ((p[0] === 'Lens' || p[0] === 'Dome') && !lensMats.some((l) => l.mat === m)) lensMats.push({ mat: m, color: p[1], gain: LENS_GAIN[p[2]] ?? 1 });
        // lens: ince yüzey, iki yüzü de görünsün; gölge atmasın (ışığı kesmez)
        if (m.transparent) {
          m.depthWrite = false;
          mm.castShadow = false;
        }
      }
    });
    apply();
  }
  const c = model.clone(true);
  c.traverse((o) => {
    o.userData.lamp = id;
  });
  return c;
}

// ---------- durum ----------
let lit = false;
const on = new Set<FnToggle>(['position']);
let blinkPhase = true;

/** Işıklar modu açık mı ve hangi işlevler yanıyor */
export function setLampState(lights: boolean, fns?: Iterable<FnToggle>) {
  lit = lights;
  if (fns) {
    on.clear();
    for (const f of fns) on.add(f);
  }
  apply();
}
export function lampState() {
  return { lit, fns: new Set(on) };
}
/** Sinyal ve tepe lambası yanıp söner: Engine sürekli çizim gerektiğini buradan öğrenir */
export function needsAnimation() {
  return lit && (on.has('turn') || on.has('beacon'));
}
/** Yanıp sönme (sinyal ~1,5 Hz, tepe lambası 2,1 Hz flaş) */
export function tickLamps(t: number) {
  if (!needsAnimation()) return false;
  const blink = (t * 1.5) % 1 < 0.55;
  const flash = (t * 2.1) % 1 < 0.18 || ((t * 2.1) % 1 > 0.3 && (t * 2.1) % 1 < 0.42);
  const changed = blink !== blinkPhase || flash !== flashPhase;
  blinkPhase = blink;
  flashPhase = flash;
  if (changed) apply();
  return changed;
}
let flashPhase = true;

function isOn(fn: LampFn) {
  if (!lit) return false;
  const g = GROUP[fn];
  if (!on.has(g)) return false;
  if (g === 'turn') return blinkPhase;
  if (g === 'beacon') return flashPhase;
  return true;
}

/**
 * Yanan parçanın HDR ışıması (Engine ışıklar modunda bloom ile çizer; ton eşleme sonda tek seferde). Işık yalnız yanan
 * parçadan gelir: lensin kendisi ışımaz (eskiden lens de yanan işlevin renginde parlıyordu; işlevler birbirine karışıyordu).
 * Şiddetler ürün föyündeki güç oranlarını izler (MAVIC: pozisyon 2 W, fren 10 W, sinyal 4/13 W, sis 4 W, geri vites 2/4,5 W).
 */
const FN_I: Record<LampFn, number> = {
  position: 1.45,
  marker: 2.6,
  front: 2.4,
  outline: 2.4,
  plate: 1.8,
  stop: 2.7,
  turn: 2.6,
  reverse: 2.5,
  fog: 2.6,
  work: 4.5,
  beacon: 3.6,
};
function apply() {
  for (const l of lensMats) {
    l.mat.emissive.set('#000000');
    l.mat.emissiveIntensity = 0;
    l.mat.toneMapped = true;
    l.mat.needsUpdate = true;
  }
  for (const e of emitMats) {
    const lit = e.fns.filter(isOn);
    const o = lit.length > 0;
    e.mat.emissive.copy(o ? e.color : BLACK);
    // paylaşılan kılavuz (pozisyon + fren) en güçlü yanan işlevin şiddetinde
    e.mat.emissiveIntensity = o ? Math.max(...lit.map((f) => FN_I[f] ?? 3)) : 0;
    e.mat.toneMapped = true;
    e.mat.needsUpdate = true;
  }
  for (const fn of listeners) fn();
}
const BLACK = new THREE.Color(0, 0, 0);
const listeners = new Set<() => void>();
export function onLampChange(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/**
 * Bir lamba nesnesinin yanan (EMIT) parçaları: parlama sprite'ları için konum, boyut, renk ve işlev.
 * Büyük ışık parçaları (neon kılavuz, sinyal kaması) 6 cm'lik ızgara hücrelerine bölünür: tek büyük hale lambayı kaplamasın.
 * split: bölünmüş parça; weak: paylaşılan kılavuzun zayıf (pozisyon) işlevi.
 */
export function emitterSpots(root: THREE.Object3D) {
  root.updateMatrixWorld(true);
  const out: { pos: THREE.Vector3; size: number; color: THREE.Color; fn: LampFn; split: boolean; weak: boolean }[] = [];
  const CELL = 0.06;
  root.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (!mm.isMesh || !o.name.startsWith('EMIT')) return;
    const m = (Array.isArray(mm.material) ? mm.material[0] : mm.material) as THREE.Material;
    const p = m.name.split('.');
    if (p[0] !== 'E') return;
    const fns = p[1].split('+') as LampFn[];
    const color = new THREE.Color(GLOW[p[2]] ?? '#fff');
    mm.geometry.computeBoundingBox();
    const bb = mm.geometry.boundingBox!.clone().applyMatrix4(mm.matrixWorld);
    const size = bb.getSize(new THREE.Vector3());
    const spots: { pos: THREE.Vector3; size: number }[] = [];
    if (Math.max(size.x, size.y, size.z) <= CELL * 1.6) {
      spots.push({ pos: bb.getCenter(new THREE.Vector3()), size: Math.max(size.x, size.y, size.z) });
    } else {
      // en büyük iki eksende ızgara; her dolu hücre bir hale
      const ax = (['x', 'y', 'z'] as const).slice().sort((a, b) => size[b] - size[a]).slice(0, 2);
      const pa = mm.geometry.attributes.position;
      const v = new THREE.Vector3();
      const cells = new Map<string, THREE.Box3>();
      for (let i = 0; i < pa.count; i++) {
        v.fromBufferAttribute(pa, i).applyMatrix4(mm.matrixWorld);
        const key = `${Math.floor((v[ax[0]] - bb.min[ax[0]]) / CELL)}|${Math.floor((v[ax[1]] - bb.min[ax[1]]) / CELL)}`;
        let b = cells.get(key);
        if (!b) cells.set(key, (b = new THREE.Box3()));
        b.expandByPoint(v);
      }
      for (const b of cells.values()) {
        const s = b.getSize(new THREE.Vector3());
        spots.push({ pos: b.getCenter(new THREE.Vector3()), size: Math.max(s.x, s.y, s.z) });
      }
    }
    for (const sp of spots) {
      for (const fn of fns) out.push({ ...sp, pos: sp.pos.clone(), color, fn, split: spots.length > 1, weak: fns.length > 1 && !STRONG.has(fn) });
    }
  });
  return out;
}
export const fnGroup = (fn: LampFn) => GROUP[fn];
export function fnLit(fn: LampFn) {
  return isOn(fn);
}
