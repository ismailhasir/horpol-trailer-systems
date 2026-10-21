// 3D motor: sahne, kamera, ışık, istek üzerine çizim (boşta GPU ~0), kamera geçişleri, seçim ve modlar.
// UI'dan bağımsızdır: yalnızca Config alır, olaylarla (onPick) geri bildirir.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import type { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import type { CategoryId, Config, TrailerId } from '../data';
import { createMaterials, fadeTexture, type Mats } from './materials';
import { buildTrailer, disposeGroup, modelUrls, setGhost, type Anchors, type TrailerBuild } from './trailer';
import { loadedModel, loadModel } from './models';
import { buildEquipment, disposeEquipment, lampIds, setHarnessHighlight, type EquipmentBuild } from './equipment';
import { fnGroup, lampFailed, lampReady, lampUrl, loadLamp, needsAnimation, setLampState, tickLamps, type FnToggle } from './lampfx';
import { setPlateLight } from './plateLight';

export type View = 'overview' | 'rear' | 'side' | 'front' | 'top';
export type Theme = 'light' | 'dark';
/** Arayüz düğmeleri dışında motorun kendi kullandığı kamera pozları */
type Pose = View | 'arm' | 'beacon' | 'system' | 'extra';
/** lamba yüklemesi bitince setConfig'i tekrarlamak için */
const LAMP_RETRY = Symbol('lampRetry');

export interface EngineOptions {
  theme: Theme;
  reducedMotion: boolean;
  onPick?: (cat: CategoryId) => void;
  /** seçilen tipin 3D modeli indiriliyor / hazır / indirilemedi (arayüz küçük bir gösterge açar) */
  onModelState?: (s: 'loading' | 'ready' | 'error') => void;
}

// ---------- ortam ışığı (IBL) ----------
// Dış dosya yok: küçük bir "ortam sahnesi" (gökyüzü/zemin gradyanı + yumuşak ışık panelleri) bir kez PMREM'e
// çizilir. Metal (alüminyum, krom), lens ve boya yansımaları buradan gelir; yanında tek yönlü ışık (güneş/ay) gölge verir.
/** Yanan lambaların gövdeye ve zemine düşen ışığı (nokta/spot ışık). Kullanıcı isteğiyle kapalı (2026-10-20): yanıltmasın. */
const LAMP_SPILL = false;
/** Işıklar modunda bloom: eşik HDR parlaklık (yalnız yanan ışık parçaları aşar), şiddet ve yayılım */
const BLOOM = { threshold: 1.05, strength: 0.8, radius: 0.36 };
/**
 * Küçük lambalar (yan marker, ön pozisyon: ~12 cm) genel görünümde 13 m'lik dorsenin yanında kayboluyordu (kullanıcı
 * 2026-10-21). Kameradan uzaklığa göre büyütülür: near metreye kadar gerçek ölçü (yakın çekimde ölçüler doğru), far metrede
 * ve ötesinde max katı (genel görünümde ürün seçilebilir); arası yumuşak geçiş. Sabit büyük model (WAS) yakından kaba
 * görünüyordu. Ölçek montaj noktası çevresinde: yan marker tutucunun üst flanşından rayda asılı kalır, ön pozisyon alt
 * kenarından büyür (şasinin altından taşmaz). Pivot her lambanın kendi sınır kutusundan (LD 2774 ile LD 500 tutucuları farklı).
 */
const MARKER_SCALE = { near: 3.5, far: 16, max: 2.3 };
const MARKER_PIVOT: Partial<Record<CategoryId, 'top' | 'bottom'>> = { side: 'top', front: 'bottom' };

type EnvKind = 'studioLight' | 'studioDark' | 'night';
type RGB = [number, number, number];
interface EnvDef {
  /** doğrusal ışıma (1 = beyaz kâğıdı tam aydınlatan gök) */
  zenith: RGB;
  horizon: RGB;
  ground: RGB;
  /** [yatay açı° (+x arka, +z kameranın tarafı), yükseklik°, genişlik, yükseklik, ışıma, renk] */
  panels: [number, number, number, number, number, string][];
}
const ENVS: Record<EnvKind, EnvDef> = {
  // açık tema: bulutlu gök + stüdyo tavanı; zemin koyu, metallerde ufuk çizgisi okunur
  studioLight: {
    zenith: [0.5, 0.62, 0.86],
    horizon: [1.05, 1.03, 1.0],
    ground: [0.14, 0.135, 0.13],
    panels: [
      [50, 60, 34, 18, 3.2, '#fff6ea'], // ana tepe softbox (güneş yönünde)
      [125, 14, 5, 22, 2.4, '#ffffff'], // yan şerit: tank/krom üzerinde dik yansıma çizgisi
      [-55, 14, 5, 22, 2.0, '#eef4ff'],
      [70, 4, 40, 4, 1.4, '#ffffff'], // kamera tarafında alçak dolgu (yan panel karanlıkta kalmasın)
    ],
  },
  // koyu tema: karanlık stüdyo; kontrastlı, parlak softbox yansımaları
  studioDark: {
    zenith: [0.17, 0.18, 0.21],
    horizon: [0.52, 0.54, 0.58],
    ground: [0.09, 0.09, 0.1],
    panels: [
      [50, 60, 34, 18, 5.0, '#fff4e6'],
      [125, 14, 5, 22, 3.4, '#ffffff'],
      [-55, 14, 5, 22, 2.8, '#e6efff'],
      [70, 4, 40, 4, 1.6, '#ffffff'],
    ],
  },
  // gece: lacivert gök, ufukta hafif şehir ışığı; ay ve arkada zayıf bir şerit siluet kenarını çizer
  night: {
    zenith: [0.006, 0.009, 0.02],
    horizon: [0.05, 0.05, 0.06],
    ground: [0.004, 0.004, 0.005],
    panels: [
      [-125, 38, 3, 3, 30, '#c8d6ff'], // ay
      [-150, 10, 40, 6, 0.35, '#8fa3cc'], // arka kenar ışığı (siluet)
    ],
  },
};

/**
 * Ortam kaynağı ve PMREM üreticisi motor ömrü boyunca bir kez kurulur: tema/gece geçişinde yalnızca gradyan
 * değerleri ve paneller güncellenip yeniden çizilir (~2 ms). Her seferinde yeniden kurmak gölgelendirici
 * derlemesi yüzünden ~50 ms takılma yapıyordu. Bedeli: üreticinin ara hedefi (256 px'te ~8 MB, 128 px'te ~2 MB).
 */
class EnvBaker {
  private pmrem: THREE.PMREMGenerator;
  private scene = new THREE.Scene();
  private sky: THREE.ShaderMaterial;
  private panels: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>[] = [];
  constructor(
    renderer: THREE.WebGLRenderer,
    private size: number,
  ) {
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.sky = new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: { zen: { value: new THREE.Vector3() }, hor: { value: new THREE.Vector3() }, gnd: { value: new THREE.Vector3() } },
      vertexShader: 'varying vec3 vD; void main(){ vD = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader:
        'uniform vec3 zen, hor, gnd; varying vec3 vD; void main(){ float t = normalize(vD).y;' +
        ' vec3 c = t > 0.0 ? mix(hor, zen, pow(smoothstep(0.0, 1.0, t), 0.55)) : mix(hor, gnd, smoothstep(0.0, 0.05, -t));' +
        ' gl_FragColor = vec4(c, 1.0); }',
    });
    this.scene.add(new THREE.Mesh(new THREE.SphereGeometry(50, 32, 16), this.sky));
    const plane = new THREE.PlaneGeometry(1, 1);
    const n = Math.max(...Object.values(ENVS).map((d) => d.panels.length));
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(plane, new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
      this.panels.push(m);
      this.scene.add(m);
    }
  }
  bake(def: EnvDef): THREE.WebGLRenderTarget {
    const u = this.sky.uniforms;
    u.zen.value.set(...def.zenith);
    u.hor.value.set(...def.horizon);
    u.gnd.value.set(...def.ground);
    this.panels.forEach((m, i) => {
      const p = def.panels[i];
      m.visible = !!p;
      if (!p) return;
      const [az, el, w, h, I, col] = p;
      const a = THREE.MathUtils.degToRad(az);
      const e = THREE.MathUtils.degToRad(el);
      m.material.color.set(col).multiplyScalar(I);
      m.position.set(Math.cos(a) * Math.cos(e), Math.sin(e), Math.sin(a) * Math.cos(e)).multiplyScalar(40);
      m.scale.set(w, h, 1);
      m.lookAt(0, 0, 0);
    });
    return this.pmrem.fromScene(this.scene, 0.02, 0.1, 100, { size: this.size });
  }
  dispose() {
    this.pmrem.dispose();
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.geometry.dispose();
      (m.material as THREE.Material).dispose();
    });
  }
}

/** Dorsenin altındaki yumuşak temas gölgesi (gök ışığının kapandığı alan): yumuşak kenarlı dikdörtgen alfa */
function contactTexture(inX: number, inY: number) {
  const W = 128;
  const H = 64;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const ctx = c.getContext('2d')!;
  const img = ctx.createImageData(W, H);
  const f = (d: number) => {
    const t = Math.min(1, Math.max(0, d));
    const s = 1 - t * t * (3 - 2 * t);
    return s * s;
  };
  for (let y = 0; y < H; y++) {
    const dy = Math.max(0, (Math.abs((y + 0.5) / H - 0.5) * 2 - inY) / (1 - inY));
    for (let x = 0; x < W; x++) {
      const dx = Math.max(0, (Math.abs((x + 0.5) / W - 0.5) * 2 - inX) / (1 - inX));
      const v = Math.round(255 * f(Math.hypot(dx, dy)));
      const i = (y * W + x) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return new THREE.CanvasTexture(c);
}

interface Look {
  env: EnvKind;
  envI: number;
  exposure: number;
  /** yönlü ışık (güneş / ay): renk, şiddet, geldiği yön [yatay açı°, yükseklik°] */
  sun: string;
  sunI: number;
  sunDir: [number, number];
  /** arka plan: üst ve ufuk rengi (ufuk = sayfa zemin tonu, zemin buna karışarak kaybolur) */
  bgTop: string;
  bg: string;
  floor: string;
  /** temas gölgesi yoğunluğu */
  contact: number;
}
const LOOKS: Record<Theme, { day: Look; night: Look }> = {
  light: {
    day: { env: 'studioLight', envI: 1.3, exposure: 1.05, sun: '#fff3e2', sunI: 3.4, sunDir: [50, 55], bgTop: '#d9e1ec', bg: '#e8ecf2', floor: '#c9d0d9', contact: 0.45 },
    night: { env: 'night', envI: 4.4, exposure: 1.0, sun: '#a9bce8', sunI: 1.0, sunDir: [-125, 38], bgTop: '#090d15', bg: '#161c27', floor: '#1d232d', contact: 0.6 },
  },
  dark: {
    day: { env: 'studioDark', envI: 1.5, exposure: 1.05, sun: '#fff1de', sunI: 3.4, sunDir: [50, 55], bgTop: '#0b0f15', bg: '#10151d', floor: '#2a313b', contact: 0.5 },
    night: { env: 'night', envI: 4.0, exposure: 1.0, sun: '#a9bce8', sunI: 0.95, sunDir: [-125, 38], bgTop: '#04060a', bg: '#0b0f16', floor: '#121821', contact: 0.6 },
  },
};

/** Arka plan için dikey gradyan (üst → ufuk; alt yarı ufuk rengi, zemin oraya karışarak kaybolur) */
function gradientTexture(top: string, horizon: string) {
  const c = document.createElement('canvas');
  c.width = 2;
  c.height = 256;
  const ctx = c.getContext('2d')!;
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, top);
  g.addColorStop(0.55, horizon);
  g.addColorStop(1, horizon);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 2, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** zayıf cihaz (dokunmatik/küçük ekran/az bellek): daha küçük ortam ve gölge haritası */
function lowEnd() {
  const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8;
  return matchMedia('(pointer: coarse)').matches || Math.min(screen.width, screen.height) < 700 || mem <= 4;
}

export class Engine {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera: THREE.PerspectiveCamera;
  private controls: OrbitControls;
  private mats!: Mats;
  private floor!: THREE.Mesh;
  private sun!: THREE.DirectionalLight;
  private contact!: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  private bgTex: THREE.CanvasTexture | null = null;
  private envKind: EnvKind | null = null;
  private envRT: THREE.WebGLRenderTarget | null = null;
  private envBaker: EnvBaker | null = null;
  private low = lowEnd();
  /** artık boş: arka kırmızı nokta ışıkları kaldırıldı (zemine/arka yüze renkli ışık + her malzemede ışık döngüsü maliyeti) */
  private trailer: TrailerBuild | null = null;
  private equip: EquipmentBuild | null = null;
  private key = '';
  private cfg: Config | null = null;
  private theme: Theme;
  private system = false;
  private lights = false;
  private raf = 0;
  private tween: { from: [THREE.Vector3, THREE.Vector3]; to: [THREE.Vector3, THREE.Vector3]; t0: number; dur: number } | null = null;
  private ro: ResizeObserver;
  private frameTimes: number[] = [];
  private dpr: number;
  private lastFrame = 0;
  private opts: EngineOptions;
  private raycaster = new THREE.Raycaster();
  private down: { x: number; y: number } | null = null;
  private disposed = false;
  /** gölge haritası yalnızca sahne değişince birkaç kare güncellenir */
  private shadowDirty = 3;

  constructor(private canvas: HTMLCanvasElement, opts: EngineOptions) {
    this.opts = opts;
    this.theme = opts.theme;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.renderer.setPixelRatio(this.dpr);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    // Khronos PBR Neutral: ürün renklerini (beyaz boya, logo mavisi) kaydırmadan korur; ACES kırmızıyı turuncuya,
    // sarıya; AgX doygun renkleri soluk pastele çeker. Yanan lambalar ton eşlemesiz (lampfx), bundan etkilenmez.
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap; // r180+: PCFSoft kaldırıldı, yumuşaklık shadow.radius ile
    this.renderer.shadowMap.autoUpdate = false;

    this.camera = new THREE.PerspectiveCamera(34, 1, 0.1, 200);
    this.camera.position.set(4, 4, 14);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.09;
    this.controls.minDistance = 2.5;
    this.controls.maxDistance = 38;
    this.controls.maxPolarAngle = Math.PI * 0.49;
    this.controls.screenSpacePanning = true;
    this.controls.addEventListener('change', () => this.invalidate());
    this.controls.addEventListener('start', () => {
      this.tween = null;
      this.userMoved = true;
    });

    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(canvas.parentElement ?? canvas);
    canvas.addEventListener('pointerdown', this.onDown);
    canvas.addEventListener('pointerup', this.onUp);
    canvas.addEventListener('pointermove', this.onMove);
    canvas.addEventListener('webglcontextlost', (e) => e.preventDefault());
  }

  async init() {
    const loader = new THREE.TextureLoader();
    const load = (u: string) =>
      new Promise<THREE.Texture | null>((res) =>
        loader.load(
          u,
          (t) => {
            t.colorSpace = THREE.SRGBColorSpace;
            t.anisotropy = 8;
            res(t);
          },
          undefined,
          () => res(null),
        ),
      );
    this.mats = createMaterials(await load('/brand/logo-white.png'));

    const fade = fadeTexture();
    this.floor = new THREE.Mesh(
      new THREE.CircleGeometry(48, 96),
      new THREE.MeshStandardMaterial({ color: LOOKS[this.theme].day.floor, roughness: 0.9, metalness: 0, alphaMap: fade, transparent: true }),
    );
    this.floor.rotation.x = -Math.PI / 2;
    this.floor.receiveShadow = true;
    this.scene.add(this.floor);
    // temas gölgesi: zeminin üstünde, tek çizim çağrısı; boyutu fitShadow'da dorseye göre
    this.contact = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 1),
      new THREE.MeshBasicMaterial({ color: '#000000', transparent: true, depthWrite: false }),
    );
    this.contact.rotation.x = -Math.PI / 2;
    this.contact.position.y = 0.004;
    this.contact.renderOrder = 1;
    this.contact.visible = false;
    this.scene.add(this.contact);

    // tek yönlü ışık (gündüz güneş, gece ay); gölge haritası yalnız sahne değişince güncellenir
    this.sun = new THREE.DirectionalLight('#ffffff', 2.5);
    this.sun.castShadow = true;
    const sm = this.low ? 1024 : 2048;
    this.sun.shadow.mapSize.set(sm, sm);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.02;
    this.sun.shadow.radius = this.low ? 2.5 : 4;
    this.scene.add(this.sun, this.sun.target);
    // yanan lambaların gövdeye ve zemine düşen gerçek ışığı: sayı sabit (gölgesiz), yalnız şiddet ve konum değişir
    for (let i = 0; i < 2; i++) {
      const p = new THREE.PointLight('#ff2010', 0, 3.2, 1.6);
      this.rearLights.push(p);
      const s = new THREE.SpotLight('#f1f5ff', 0, 14, 0.62, 0.65, 1.3);
      this.workLights.push(s);
      this.scene.add(p, s, s.target);
    }
    this.applyLook();
    this.resize();
  }

  /**
   * Tipin Blender modelini önceden indirir (ilk görüntüden önce ve listede üzerine gelindiğinde). Süre dolarsa beklemeden
   * dönülür; model gelene kadar setConfig yükleniyor göstergesiyle bekler.
   */
  preload(type: TrailerId, timeout = 8000): Promise<void> {
    const urls = modelUrls(type);
    const all = Promise.all(urls.map(loadModel)).then(
      () => undefined,
      (e) => console.error(e),
    );
    return Promise.race([all, new Promise<void>((r) => setTimeout(r, timeout))]);
  }

  // ---------- yapılandırma ----------
  /** modeli indirilmeyi bekleyen son istek (gelince uygulanır; arada gelen yeni istek bunun yerine geçer) */
  private pending: Config | null = null;

  setConfig(c: Config, keepView = false) {
    if (this.disposed || !this.mats) return;
    // model indirilene kadar ekrandaki dorse olduğu gibi kalır (ara görüntü yok), gelince tek seferde yerine geçer
    const urls = modelUrls(c.trailer);
    if (!urls.every((u) => loadedModel(u))) {
      this.pending = c;
      this.opts.onModelState?.('loading');
      Promise.all(urls.map(loadModel)).then(
        () => {
          if (this.disposed || this.pending !== c) return;
          this.setConfig(c, keepView);
        },
        (e) => {
          console.error(e);
          if (this.pending !== c) return;
          this.pending = null;
          this.opts.onModelState?.('error');
        },
      );
      return;
    }
    if (this.pending) {
      this.pending = null;
      this.opts.onModelState?.('ready');
    }
    const k = `${c.trailer}|${c.length}`;
    const firstBuild = !this.trailer;
    if (k !== this.key) {
      if (this.trailer) {
        this.scene.remove(this.trailer.group);
        disposeGroup(this.trailer.group);
      }
      this.trailer = buildTrailer(c.trailer, this.mats);
      this.scene.add(this.trailer.group);
      this.key = k;
      this.fitShadow(this.trailer.anchors);
      this.applySystem();
      if (!firstBuild && !keepView) this.setView(this.system ? 'top' : 'overview');
    }
    if (this.equip) {
      this.scene.remove(this.equip.group);
      disposeEquipment(this.equip.group);
    }
    this.equip = buildEquipment(c, this.trailer!.anchors, this.mats);
    this.scene.add(this.equip.group);
    // plaka: çerçeve (RTR 3366) seçiliyse yuvasına öne alınır; plakaya düşen ışık lamba yerleşimine göre
    this.trailer!.plate.position.copy(this.equip.plate.pos ?? this.trailer!.plateBase);
    setPlateLight(this.trailer!.plate, this.equip.plate.light);
    this.cfg = c;
    // lamba modelleri ilk kullanımda indirilir; o ana kadar yer tutucu görünür, gelince ekipman yeniden kurulur
    // yalnız modeli VAR olup henüz yüklenmemiş lambalar için (modeli olmayan ürünler yer tutucuyla kalır; döngü yok)
    const missing = lampIds(c).filter((id) => lampUrl(id) && !lampReady(id) && !lampFailed(id));
    if (this.equip.placeholders > 0 && missing.length) {
      const ids = missing;
      const token = ((this as unknown as Record<symbol, number>)[LAMP_RETRY] = ((this as unknown as Record<symbol, number>)[LAMP_RETRY] ?? 0) + 1);
      Promise.all(ids.map(loadLamp)).then(() => {
        if (this.disposed || this.cfg !== c || (this as unknown as Record<symbol, number>)[LAMP_RETRY] !== token) return;
        this.setConfig(c, true);
      });
    }
    this.applySystem();
    this.applyLights();
    this.shadowDirty = 3;
    if (firstBuild) this.setView('overview', true);
    this.invalidate();
  }

  get anchors(): Anchors | null {
    return this.trailer?.anchors ?? null;
  }

  // ---------- kamera ----------
  private viewPose(v: Pose): [THREE.Vector3, THREE.Vector3] {
    const a = this.trailer!.anchors;
    const L = a.L;
    const cx = -L / 2;
    const aspect = this.freeAspect();
    const k = aspect < 1.6 ? Math.pow(1.6 / aspect, 0.85) : 1;
    const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
    switch (v) {
      case 'rear':
        return [V(6.6 * k, 2.2, 3.1 * k), V(-0.8, 1.3, 0)];
      case 'extra': {
        // ek lambalar tipine göre üst arka köşede ya da tamponda: arka görünüm yönünde, lambaların ortasına bakılır
        const y = (a.extra.y + a.rear.lampY) / 2;
        return [V(6.6 * k, y + 0.9, 3.1 * k), V(-0.5, y, 0)];
      }
      case 'side':
        return [V(cx, 2.3, (L * 0.92 + 2.5) * k), V(cx, 1.5, 0)];
      case 'front':
        return [V(-L - 6.2 * k, 2.9, 3.6 * k), V(-L + 0.6, 1.7, 0)];
      case 'top':
        return [V(cx + 0.01, (L * 1.08 + 4) * k, 0.02), V(cx, 0.5, 0)];
      case 'arm': {
        // lastik kollar: takılı kolların gerçek yerine bak (standart dorsede tampon kenarı, eskiden kasanın üst köşesi
        // sanılıyordu); kol yoksa ya da modeli yüklenmemişse arka tampon yüksekliği
        const arms = this.equip?.lampsByCat.arm ?? [];
        const t = new THREE.Vector3();
        if (arms.length) {
          for (const o of arms) t.add(o.getWorldPosition(new THREE.Vector3()));
          t.multiplyScalar(1 / arms.length);
        } else t.set(-0.5, a.rear.lampY, 0);
        const rear = t.x > cx; // arka kollar → arkadan, yalnız önde ise önden
        return [V(t.x + (rear ? 2.9 : -2.9) * k, t.y + 0.55, 2.1 * k), V(t.x, t.y, 0)];
      }
      case 'beacon':
        // tepe lambaları: üst arka köşe (eski "arm" pozu)
        return [V(4.6 * k, a.topY + 1.4, 4.6 * k), V(-0.8, a.topY - 0.6, 0)];
      case 'system':
        return [V(cx + L * 0.28, (L * 0.78 + 2) * k, L * 0.42 * k), V(cx + 0.3, 0.9, 0)];
      default:
        return [V(cx + L * 0.8 * k, 4.6 + (k - 1) * 3, (L * 0.92 + 2.8) * k), V(cx + 0.4, 1.45, 0)];
    }
  }

  /**
   * Dorsenin tamamının panellerin arasındaki boş alana sığdığı en kısa kamera uzaklığı.
   * Gövde kutusunun 8 köşesi ekrana yansıtılır, ikili arama ile boş alanın içine sığan uzaklık bulunur.
   */
  private fitDistance(dir: THREE.Vector3, target: THREE.Vector3, margin = 0.05, box?: THREE.Box3): number {
    const a = this.trailer!.anchors;
    const el = this.canvas.parentElement ?? this.canvas;
    const w = el.clientWidth || 1;
    const h = el.clientHeight || 1;
    const { left, right, top, bottom } = this.insets;
    const xMin = (left / w) * 2 - 1 + margin;
    const xMax = ((w - right) / w) * 2 - 1 - margin;
    const yMax = 1 - (top / h) * 2 - margin;
    const yMin = 1 - ((h - bottom) / h) * 2 + margin;
    const corners: THREE.Vector3[] = [];
    const b = box ?? new THREE.Box3(new THREE.Vector3(-a.L - 0.3, 0, -a.W / 2 - 0.2), new THREE.Vector3(0.35, a.topY, a.W / 2 + 0.2));
    for (const x of [b.min.x, b.max.x]) for (const y of [b.min.y, b.max.y]) for (const z of [b.min.z, b.max.z]) corners.push(new THREE.Vector3(x, y, z));
    const cam = this.camera.clone();
    cam.updateProjectionMatrix();
    const p = new THREE.Vector3();
    let lo = 2;
    let hi = 160;
    for (let i = 0; i < 22; i++) {
      const mid = (lo + hi) / 2;
      cam.position.copy(target).addScaledVector(dir, mid);
      cam.lookAt(target);
      cam.updateMatrixWorld(true);
      const ok = corners.every((c) => {
        p.copy(c).project(cam);
        return p.z < 1 && p.x >= xMin && p.x <= xMax && p.y >= yMin && p.y <= yMax;
      });
      if (ok) hi = mid;
      else lo = mid;
    }
    return hi;
  }

  setView(v: Pose, instant = false) {
    if (!this.trailer) return;
    this.lastView = v;
    this.userMoved = false;
    const [pos, target] = this.viewPose(v);
    // bütün dorseyi gösteren görünümlerde uzaklık boş alana göre hesaplanır (bakış yönü korunur)
    const fit: Partial<Record<string, number>> = { overview: 1, side: 1, top: 1, system: 1 };
    const f = fit[v];
    if (f) {
      const dir = pos.clone().sub(target).normalize();
      pos.copy(target).addScaledVector(dir, this.fitDistance(dir, target) * f);
    } else if (v === 'extra') {
      // arka yüzün stop lambalarından ek lambalara kadar olan kısmı boş alana sığar
      const a = this.trailer.anchors;
      let lo = Math.min(a.rear.plateY, a.extra.y) - 0.35;
      let hi = Math.max(a.rear.lampY, a.extra.y) + 0.35;
      const pad = Math.max(0, 1.8 - (hi - lo)) / 2;
      lo = Math.max(0, lo - pad);
      hi += pad;
      const dir = pos.clone().sub(target).normalize();
      const area = new THREE.Box3(new THREE.Vector3(-1.2, lo, -a.W / 2 - 0.15), new THREE.Vector3(0.3, hi, a.W / 2 + 0.15));
      pos.copy(target).addScaledVector(dir, this.fitDistance(dir, target, 0.08, area));
    }
    if (instant || this.opts.reducedMotion) {
      this.camera.position.copy(pos);
      this.controls.target.copy(target);
      this.controls.update();
      this.invalidate();
      return;
    }
    this.tween = { from: [this.camera.position.clone(), this.controls.target.clone()], to: [pos, target], t0: performance.now(), dur: 750 };
    this.invalidate();
  }

  focusCategory(cat: CategoryId) {
    const map: Record<CategoryId, Pose> = { stop: 'rear', plate: 'rear', side: 'side', front: 'front', arm: 'arm', work: 'extra', beacon: 'beacon' };
    if (this.system) return;
    this.setView(map[cat]);
  }

  // ---------- modlar ----------
  setSystem(on: boolean) {
    this.system = on;
    this.applySystem();
    this.setView(on ? 'system' : 'overview');
  }
  private applySystem() {
    if (!this.trailer) return;
    setGhost(this.trailer, this.system);
    this.trailer.outline.visible = this.system;
    if (this.equip) setHarnessHighlight(this.equip.harness, this.mats, this.system);
    this.shadowDirty = 3;
    this.invalidate();
  }

  setLights(on: boolean) {
    this.lights = on;
    if (on) void this.ensureBloom();
    this.applyLights();
    this.applyLook();
    this.invalidate();
  }
  /** Işıklar modunda yanan işlevler (pozisyon, fren, sinyal, geri vites, sis, çalışma, tepe) */
  private fns: FnToggle[] = ['position'];
  setLampFunctions(fns: FnToggle[]) {
    this.fns = [...fns];
    this.applyLights();
    this.invalidate();
  }
  private applyLights() {
    if (!this.mats) return;
    setLampState(this.lights, this.fns);
    this.syncGlows();
  }
  private syncGlows() {
    this.syncLampLights();
    for (const g of this.equip?.glows ?? []) {
      g.sprite.visible = this.lights && this.fns.includes(fnGroup(g.fn)) && (fnGroup(g.fn) !== 'turn' || this.blinkOn) && (fnGroup(g.fn) !== 'beacon' || this.flashOn);
    }
  }
  private rearLights: THREE.PointLight[] = [];
  private workLights: THREE.SpotLight[] = [];
  /** gerçek ışıkları ekipmanın lamba konumlarına taşır ve yanan işlevlere göre açar (LAMP_SPILL kapalıyken hep 0) */
  private syncLampLights() {
    const L = this.equip?.lights;
    const on = (f: FnToggle) => LAMP_SPILL && this.lights && this.fns.includes(f);
    const red = on('stop') ? 4.2 : on('position') ? 1.4 : 0;
    this.rearLights.forEach((p, i) => {
      // görünürlük değişmez (ışık sayısı değişirse tüm gölgelendiriciler yeniden derlenir): kapalıyken şiddet 0
      const at = L?.rear.find((v) => (i === 0 ? v.z > 0 : v.z < 0));
      if (at) p.position.copy(at);
      p.intensity = at ? red : 0;
    });
    this.workLights.forEach((s, i) => {
      const w = L?.work[i];
      if (!w) {
        s.intensity = 0;
        return;
      }
      s.position.copy(w.pos).addScaledVector(w.dir, 0.06);
      // çalışma lambası dorsenin arkasındaki yükleme alanını aydınlatır: ışık zemine, ~3 m geriye düşer
      const flat = new THREE.Vector3(w.dir.x, 0, w.dir.z);
      if (flat.lengthSq() < 1e-4) flat.set(1, 0, 0);
      flat.normalize();
      s.target.position.set(w.pos.x + flat.x * 3.2, 0, w.pos.z + flat.z * 3.2);
      s.target.updateMatrixWorld();
      s.angle = 0.75;
      s.distance = 16;
      s.intensity = on('work') ? 115 : 0;
    });
  }
  private blinkOn = true;
  private flashOn = true;

  setTheme(t: Theme) {
    this.theme = t;
    this.applyLook();
    this.invalidate();
  }
  private get look(): Look {
    const l = LOOKS[this.theme];
    return this.lights ? l.night : l.day;
  }
  private applyLook() {
    if (!this.floor) return;
    const lk = this.look;
    this.setEnvironment(lk.env);
    this.scene.environmentIntensity = lk.envI;
    this.renderer.toneMappingExposure = lk.exposure;
    // arka plan: üstten ufka dikey gradyan (ton eşlemesiz sRGB doku, tek tam ekran çizim); sis ufuk rengine karışır
    this.bgTex?.dispose();
    this.bgTex = gradientTexture(lk.bgTop, lk.bg);
    this.scene.background = this.bgTex;
    this.scene.fog = new THREE.Fog(lk.bg, 34, 70);
    (this.floor.material as THREE.MeshStandardMaterial).color.set(lk.floor);
    this.contact.material.opacity = lk.contact;
    this.sun.color.set(lk.sun);
    this.sun.intensity = lk.sunI;
    this.placeSun();
    this.shadowDirty = 3;
  }

  /** Ortam haritası: yalnızca etkin olan tutulur (256 px; zayıf cihazda 128 px), değişince yeniden pişirilir */
  private setEnvironment(kind: EnvKind) {
    if (this.envKind === kind) return;
    this.envBaker ??= new EnvBaker(this.renderer, this.low ? 128 : 256);
    const rt = this.envBaker.bake(ENVS[kind]);
    this.envRT?.dispose();
    this.envRT = rt;
    this.envKind = kind;
    this.scene.environment = rt.texture;
  }

  /** Yönlü ışığı görünümün yönüne yerleştirir: gündüz arka-yan üstten (gölge öne ve uzak tarafa), gece aydan (arkadan) */
  private placeSun() {
    const a = this.trailer?.anchors;
    const cx = a ? -a.L / 2 : -6;
    const [az, el] = this.look.sunDir.map(THREE.MathUtils.degToRad);
    const d = new THREE.Vector3(Math.cos(az) * Math.cos(el), Math.sin(el), Math.sin(az) * Math.cos(el));
    this.sun.target.position.set(cx, 0, 0);
    this.sun.position.set(cx, 0, 0).addScaledVector(d, 20);
  }

  private fitShadow(a: Anchors) {
    const cx = -a.L / 2;
    this.placeSun();
    // temas gölgesi: dorse izdüşümünün kenarında yumuşak geçiş (0,3 m içeriden 0,6 m dışarıya)
    const mi = 0.3;
    const mo = 0.6;
    const x0 = -a.L - 0.3;
    const x1 = 0.35;
    const lx = x1 - x0 + 2 * mo;
    const lz = a.W + 2 * mo;
    this.contact.material.alphaMap?.dispose();
    this.contact.material.alphaMap = contactTexture((x1 - x0 - 2 * mi) / lx, (a.W - 2 * mi) / lz);
    this.contact.material.needsUpdate = true;
    this.contact.scale.set(lx, lz, 1);
    this.contact.position.x = (x0 + x1) / 2;
    this.contact.visible = true;
    const cam = this.sun.shadow.camera;
    const half = a.L / 2 + 3;
    cam.left = -half;
    cam.right = half;
    cam.top = half;
    cam.bottom = -half;
    cam.near = 1;
    cam.far = 40;
    cam.updateProjectionMatrix();
    this.controls.maxDistance = Math.max(30, a.L * 2.6);
  }

  // ---------- çizim döngüsü (istek üzerine) ----------
  invalidate() {
    if (this.raf || this.disposed) return;
    this.raf = requestAnimationFrame(this.frame);
  }
  private frame = (now: number) => {
    this.raf = 0;
    let busy = false;
    if (needsAnimation()) {
      const s = now / 1000;
      this.blinkOn = (s * 1.5) % 1 < 0.55;
      const f = (s * 2.1) % 1;
      this.flashOn = f < 0.18 || (f > 0.3 && f < 0.42);
      tickLamps(s);
      this.syncGlows();
      busy = true;
    }
    if (this.tween) {
      const t = Math.min(1, (now - this.tween.t0) / this.tween.dur);
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      this.camera.position.lerpVectors(this.tween.from[0], this.tween.to[0], e);
      this.controls.target.lerpVectors(this.tween.from[1], this.tween.to[1], e);
      if (t >= 1) this.tween = null;
      busy = true;
    }
    if (this.shadowDirty > 0) {
      this.renderer.shadowMap.needsUpdate = true;
      this.shadowDirty--;
      busy = true;
    }
    const moved = this.controls.update();
    this.controls.target.y = Math.max(0.2, this.controls.target.y);
    this.draw();
    this.adapt(now, busy || moved);
    if (busy || moved) this.invalidate();
  };

  /** Küçük lambaları kameradan uzaklığa göre büyütür (MARKER_SCALE); her karede, çizimden önce */
  private scaleMarkers() {
    const e = this.equip;
    if (!e) return;
    const { near, far, max } = MARKER_SCALE;
    const off = new THREE.Vector3();
    for (const [cat, edge] of Object.entries(MARKER_PIVOT) as [CategoryId, 'top' | 'bottom'][]) {
      for (const o of e.lampsByCat[cat]) {
        const base = (o.userData.basePos ??= o.position.clone()) as THREE.Vector3;
        // pivot: lambanın KENDİ ekseninde (ölçeksiz) sınır kutusunun üst / alt kenarı. Dünya kutusundan hesaplanınca lambanın
        // atası (gövde / şasi grubu) kaydırılmış olduğunda pivot metrelerce sapıyor, lamba kasanın içine kaçıyordu.
        if (!o.userData.pivot) {
          const bb = new THREE.Box3();
          o.updateWorldMatrix(true, true);
          const inv = o.matrixWorld.clone().invert();
          const m = new THREE.Matrix4();
          o.traverse((c) => {
            const g = (c as THREE.Mesh).geometry;
            if (!(c as THREE.Mesh).isMesh || !g) return;
            g.boundingBox ?? g.computeBoundingBox();
            bb.union(g.boundingBox!.clone().applyMatrix4(m.multiplyMatrices(inv, c.matrixWorld)));
          });
          o.userData.pivot = new THREE.Vector3(0, bb.isEmpty() ? 0 : edge === 'top' ? bb.max.y : bb.min.y, 0);
        }
        const piv = o.userData.pivot as THREE.Vector3;
        const t = THREE.MathUtils.clamp((this.camera.position.distanceTo(base) - near) / (far - near), 0, 1);
        const k = 1 + (max - 1) * t * t * (3 - 2 * t);
        if (Math.abs(o.scale.y - k) < 1e-3) continue;
        o.scale.setScalar(k);
        // pivot sabit kalır: konum = taban + dönüş × pivot × (1 − k)
        o.position.copy(base).add(off.copy(piv).multiplyScalar(1 - k).applyQuaternion(o.quaternion));
      }
    }
  }

  /** Işıklar modunda sahne bloom ile çizilir: yanan parçaların ışıması kendi biçimini izler (şerit şerit, homojen) */
  private draw() {
    this.scaleMarkers();
    if (this.lights && this.composer) this.composer.render();
    else this.renderer.render(this.scene, this.camera);
  }
  // ---------- ışıklar modu: parlama (bloom) ----------
  private composer: EffectComposer | null = null;
  private bloom: UnrealBloomPass | null = null;
  private bloomLoading = false;
  /** İlk kez ışıklar açılınca yüklenir (gündüz görünümünde ek paket ve çizim maliyeti yok) */
  private async ensureBloom() {
    if (this.composer || this.bloomLoading || this.disposed) return;
    this.bloomLoading = true;
    let mods;
    try {
      mods = await Promise.all([
        import('three/examples/jsm/postprocessing/EffectComposer.js'),
        import('three/examples/jsm/postprocessing/RenderPass.js'),
        import('three/examples/jsm/postprocessing/UnrealBloomPass.js'),
        import('three/examples/jsm/postprocessing/OutputPass.js'),
      ]);
    } catch (err) {
      console.error(err); // ağ hatası: bloomsuz devam (sonraki açılışta yeniden denenir)
      this.bloomLoading = false;
      return;
    }
    const [{ EffectComposer }, { RenderPass }, { UnrealBloomPass }, { OutputPass }] = mods;
    if (this.disposed) return;
    // HDR ara görüntü + MSAA (kenar yumuşatma kaybolmasın); ton eşleme ve sRGB dönüşümü OutputPass'te
    const rt = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: this.low ? 0 : 4 });
    const c = new EffectComposer(this.renderer, rt);
    c.addPass(new RenderPass(this.scene, this.camera));
    const b = new UnrealBloomPass(new THREE.Vector2(256, 256), BLOOM.strength, BLOOM.radius, BLOOM.threshold);
    // eşik parlaklık (luma) yerine en parlak kanal: doygun kırmızı ışığın luması düşük, eşiği geçemiyordu. HDR > 1 yalnız
    // yanan ışık parçalarında olur; gece sahnesinde aydınlanan yüzeyler (beyaz dorse) ışımaz.
    const hp = b.materialHighPassFilter;
    hp.fragmentShader = hp.fragmentShader.replace('float v = luminance( texel.xyz );', 'float v = max( texel.r, max( texel.g, texel.b ) );');
    hp.needsUpdate = true;
    c.addPass(b);
    c.addPass(new OutputPass());
    this.composer = c;
    this.bloom = b;
    this.resize();
    this.invalidate();
  }

  /** Yavaş cihazda çözünürlüğü kademeli düşür */
  private adapt(now: number, active: boolean) {
    if (!active) {
      this.lastFrame = 0;
      return;
    }
    if (this.lastFrame) {
      this.frameTimes.push(now - this.lastFrame);
      if (this.frameTimes.length > 40) this.frameTimes.shift();
      if (this.frameTimes.length === 40) {
        const avg = this.frameTimes.reduce((a, b) => a + b, 0) / 40;
        if (avg > 26 && this.dpr > 1) {
          this.dpr = Math.max(1, this.dpr - 0.25);
          this.renderer.setPixelRatio(this.dpr);
          this.resize();
          this.frameTimes = [];
        }
      }
    }
    this.lastFrame = now;
  }

  /** Sahnenin üstündeki paneller: dorse, panellerin arasında kalan boş alanda ortalanır (px). */
  private insets = { left: 0, right: 0, top: 0, bottom: 0 };
  setInsets(i: { left: number; right: number; top: number; bottom: number }, animate = false) {
    const same = (Object.keys(i) as (keyof typeof i)[]).every((k) => Math.abs(i[k] - this.insets[k]) < 1);
    if (same) return;
    this.insets = i;
    this.resize();
    if (!this.userMoved && this.trailer) this.setView(this.lastView, !animate);
  }
  private lastView: Pose = 'overview';
  private userMoved = false;
  private freeAspect() {
    const el = this.canvas.parentElement ?? this.canvas;
    const w = el.clientWidth - this.insets.left - this.insets.right;
    const h = el.clientHeight - this.insets.top - this.insets.bottom;
    return w > 0 && h > 0 ? w / h : this.camera.aspect || 1.6;
  }

  private resize() {
    const el = this.canvas.parentElement ?? this.canvas;
    const w = el.clientWidth;
    const h = el.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    if (this.composer) {
      this.composer.setPixelRatio(this.renderer.getPixelRatio() * (this.low ? 0.75 : 1));
      this.composer.setSize(w, h);
    }
    this.camera.aspect = w / h;
    const { left, right, top, bottom } = this.insets;
    if (left || right || top || bottom) {
      const cx = left + (w - left - right) / 2;
      const cy = top + (h - top - bottom) / 2;
      this.camera.setViewOffset(w, h, w / 2 - cx, h / 2 - cy, w, h);
    } else {
      this.camera.clearViewOffset();
    }
    this.camera.updateProjectionMatrix();
    this.invalidate();
  }

  // ---------- seçim (lambaya tıkla) ----------
  private pick(e: PointerEvent): CategoryId | null {
    if (!this.equip) return null;
    const r = this.canvas.getBoundingClientRect();
    const p = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(p, this.camera);
    const hits = this.raycaster.intersectObjects(this.equip.group.children, true);
    for (const h of hits) {
      const c = h.object.userData.category;
      if (c && c !== 'socket' && h.object.visible) return c as CategoryId;
    }
    return null;
  }
  private onDown = (e: PointerEvent) => {
    this.down = { x: e.clientX, y: e.clientY };
  };
  private onUp = (e: PointerEvent) => {
    if (!this.down) return;
    const moved = Math.hypot(e.clientX - this.down.x, e.clientY - this.down.y);
    this.down = null;
    if (moved > 5) return;
    const c = this.pick(e);
    if (c) this.opts.onPick?.(c);
  };
  private lastMove = 0;
  private onMove = (e: PointerEvent) => {
    if (e.buttons || e.pointerType !== 'mouse') return;
    const now = performance.now();
    if (now - this.lastMove < 60) return;
    this.lastMove = now;
    this.canvas.style.cursor = this.pick(e) ? 'pointer' : 'grab';
  };

  /** Geliştirme/test: anlık görüntü (PNG data URL) */
  snapshot(): string {
    this.controls.update();
    this.draw();
    return this.renderer.domElement.toDataURL('image/jpeg', 0.9);
  }

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    this.controls.dispose();
    if (this.trailer) disposeGroup(this.trailer.group);
    if (this.equip) disposeEquipment(this.equip.group);
    this.envRT?.dispose();
    this.envBaker?.dispose();
    this.composer?.dispose();
    this.bgTex?.dispose();
    if (this.contact) {
      this.contact.geometry.dispose();
      this.contact.material.alphaMap?.dispose();
      this.contact.material.dispose();
    }
    this.renderer.dispose();
  }
}
