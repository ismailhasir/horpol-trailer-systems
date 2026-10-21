// Lamba modelleri (tools/blender/lamps.py → src/assets/models/lamp-<id>.glb) ve ışık işlevlerinin yakılması.
// GLB sözleşmesi: düğümler BODY / INNER / LENS / EMIT.<işlev>; ışık veren malzemelerin adı "E.<işlev>.<renk>[.<etiket>]".
// Birden çok işlevin paylaştığı kılavuz "E.position+stop.red": işlevlerden biri açıksa yanar (pozisyonda sönük, frende parlak).
// Klonlar malzemeyi paylaşır: bir işlevin malzemesini değiştirmek o işlevi tüm lambalarda yakar (tek kaynak).
import * as THREE from 'three';
import { loadedModel, loadModel } from './models';

export type LampFn = 'position' | 'stop' | 'turn' | 'reverse' | 'fog' | 'marker' | 'front' | 'outline' | 'plate' | 'work' | 'beacon';
/** Kullanıcının açıp kapatabildiği işlevler (pozisyon grubu: position + marker + front + outline + plate birlikte) */
export type FnToggle = 'position' | 'stop' | 'turn' | 'reverse' | 'fog' | 'work' | 'beacon';
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
  /** "E.<işlev>.<renk>.g<yüzde>": LED'in ışığını yansıtan krom kap, işlev şiddetinin bu oranında ışır */
  gain: number;
  /** metal yansıtıcı (krom LED kabı): modeldeki pürüzlülük; ışıklar modunda NIGHT_ROUGH'a yükseltilir */
  rough?: number;
}
const emitMats: EmitMat[] = [];
/** renkli dış lensler: yanan işlevin renginde hafif ışır (gerçek lambada lensin tamamı aydınlanır) */
const lensMats: { mat: THREE.MeshStandardMaterial; color: string; gain: number }[] = [];
/** "Lens.<renk>.cad": ışık kılavuzları lensin hemen ardında (üretici CAD modeli), lensin kendisi az parlar */
const LENS_GAIN: Record<string, number> = { cad: 0.25 };
const registered = new WeakSet<THREE.Object3D>();
// yanan ışık rengi: gerçek LED tayfına yakın (kırmızı ~625 nm biraz turuncuya, turuncu ~590 nm, soğuk beyaz)
const GLOW: Record<string, string> = { red: '#ff3a18', amber: '#ff9010', white: '#eef3ff' };

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
          const g = /^g(\d+)$/.exec(p[3] ?? '');
          emitMats.push({ mat: m, fns: p[1].split('+') as LampFn[], color: new THREE.Color(GLOW[p[2]] ?? '#ffffff'), gain: g ? Number(g[1]) / 100 : 1,
            rough: m.metalness > 0.5 ? m.roughness : undefined });
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
  // geri vites: beyaz LED kırmızı kılavuzların yanında sönük kalıyordu (kullanıcı, 2026-10-20); LED kabı .g oranlarıyla ışır
  reverse: 3.0,
  fog: 2.6,
  work: 4.5,
  beacon: 3.6,
};
/**
 * Gece (ışıklar modu) krom LED kaplarının pürüzlülüğü. Ortamdaki ay (gece ortam haritasının en parlak paneli) ve ay ışığı
 * cilalı kaplarda (0,08) iğne ucu yansıma yapıp bloom eşiğini geçiyor, sönük lambada beyaz parlama, yanan lambada ışığın
 * rengine karışan beyaz benek oluyordu (LZD 2854'ün 72 kabı, kullanıcı 2026-10-21). Gerçekte kaplar lensin ardında karanlıkta
 * kalır: gece yansıma yayılır, tepe değeri eşiğin altına iner; LED'in kendi ışıması (emissive) değişmez.
 */
const NIGHT_ROUGH = 0.55;
function apply() {
  for (const l of lensMats) {
    l.mat.emissive.set('#000000');
    l.mat.emissiveIntensity = 0;
    l.mat.toneMapped = true;
    l.mat.needsUpdate = true;
  }
  for (const e of emitMats) {
    const litFns = e.fns.filter(isOn);
    const o = litFns.length > 0;
    e.mat.emissive.copy(o ? e.color : BLACK);
    // paylaşılan kılavuz (pozisyon + fren) en güçlü yanan işlevin şiddetinde
    e.mat.emissiveIntensity = o ? Math.max(...litFns.map((f) => FN_I[f] ?? 3)) * e.gain : 0;
    if (e.rough !== undefined) e.mat.roughness = lit ? Math.max(e.rough, NIGHT_ROUGH) : e.rough;
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

export function fnLit(fn: LampFn) {
  return isOn(fn);
}
