// Lamba modelleri (tools/blender/lamps.py → src/assets/models/lamp-<id>.glb) ve ışık işlevlerinin yakılması.
// GLB sözleşmesi: düğümler BODY / INNER / LENS / EMIT.<işlev>; ışık veren malzemelerin adı "E.<işlev>.<renk>".
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
  fn: LampFn;
  color: THREE.Color;
}
const emitMats: EmitMat[] = [];
/** renkli dış lensler: yanan işlevin renginde hafif ışır (gerçek lambada lensin tamamı aydınlanır) */
const lensMats: { mat: THREE.MeshStandardMaterial; color: string }[] = [];
const registered = new WeakSet<THREE.Object3D>();
const GLOW: Record<string, string> = { red: '#ff1408', amber: '#ff7a00', white: '#f4f7ff' };

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
          emitMats.push({ mat: m, fn: p[1] as LampFn, color: new THREE.Color(GLOW[p[2]] ?? '#ffffff') });
        }
        if ((p[0] === 'Lens' || p[0] === 'Dome') && !lensMats.some((l) => l.mat === m)) lensMats.push({ mat: m, color: p[1] });
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

/** Ton eşlemesiz doygun ışık: yanan kırmızı beyaza kaçmasın, ürünün ışık deseni okunsun */
function apply() {
  const litColor = new Map<string, number>();
  for (const e of emitMats) {
    if (!isOn(e.fn)) continue;
    const c = e.mat.name.split('.')[2];
    const k = e.fn === 'stop' || e.fn === 'work' || e.fn === 'beacon' ? 1 : 0.55;
    litColor.set(c, Math.max(litColor.get(c) ?? 0, k));
  }
  for (const l of lensMats) {
    const key = l.color === 'clear' ? 'white' : l.color;
    const k = litColor.get(key) ?? 0;
    // yanınca lens de aynı renkte ışır ve ton eşlemesiz çizilir: yarı saydam renkli lens arkadaki ışığı kısmasın
    l.mat.emissive.set(k ? GLOW[key] ?? '#ffffff' : '#000000');
    l.mat.emissiveIntensity = k * (key === 'white' ? 1.1 : 1.5);
    l.mat.toneMapped = !k;
    l.mat.needsUpdate = true;
  }
  for (const e of emitMats) {
    const o = isOn(e.fn);
    e.mat.emissive.copy(o ? e.color : BLACK);
    e.mat.emissiveIntensity = o ? (e.fn === 'work' ? 3.2 : 2.6) : 0;
    e.mat.toneMapped = !o;
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

/** Bir lamba nesnesinin yanan (EMIT) parçaları: parlama sprite'ları için konum, boyut, renk ve işlev */
export function emitterSpots(root: THREE.Object3D) {
  root.updateMatrixWorld(true);
  const out: { pos: THREE.Vector3; size: number; color: THREE.Color; fn: LampFn }[] = [];
  root.traverse((o) => {
    const mm = o as THREE.Mesh;
    if (!mm.isMesh || !o.name.startsWith('EMIT')) return;
    const m = (Array.isArray(mm.material) ? mm.material[0] : mm.material) as THREE.Material;
    const p = m.name.split('.');
    if (p[0] !== 'E') return;
    mm.geometry.computeBoundingBox();
    const bb = mm.geometry.boundingBox!.clone().applyMatrix4(mm.matrixWorld);
    const size = bb.getSize(new THREE.Vector3());
    out.push({ pos: bb.getCenter(new THREE.Vector3()), size: Math.max(size.x, size.y, size.z), color: new THREE.Color(GLOW[p[2]] ?? '#fff'), fn: p[1] as LampFn });
  });
  return out;
}
export const fnGroup = (fn: LampFn) => GROUP[fn];
export function fnLit(fn: LampFn) {
  return isOn(fn);
}
