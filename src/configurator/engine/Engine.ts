// 3D motor: sahne, kamera, ışık, istek üzerine çizim (boşta GPU ~0), kamera geçişleri, seçim ve modlar.
// UI'dan bağımsızdır: yalnızca Config alır, olaylarla (onPick) geri bildirir.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import type { CategoryId, Config, TrailerId } from '../data';
import { createMaterials, fadeTexture, setLensPower, type Mats } from './materials';
import { buildTrailer, disposeGroup, modelUrls, setGhost, type Anchors, type TrailerBuild } from './trailer';
import { loadedModel, loadModel } from './models';
import { buildEquipment, disposeEquipment, setHarnessHighlight, type EquipmentBuild } from './equipment';

export type View = 'overview' | 'rear' | 'side' | 'front' | 'top';
export type Theme = 'light' | 'dark';
/** Arayüz düğmeleri dışında motorun kendi kullandığı kamera pozları */
type Pose = View | 'arm' | 'system' | 'extra';

export interface EngineOptions {
  theme: Theme;
  reducedMotion: boolean;
  onPick?: (cat: CategoryId) => void;
  /** seçilen tipin 3D modeli indiriliyor / hazır / indirilemedi (arayüz küçük bir gösterge açar) */
  onModelState?: (s: 'loading' | 'ready' | 'error') => void;
}

const THEMES = {
  light: { bg: '#e8ecf2', floor: '#d6dde6', bgNight: '#141a24', floorNight: '#1b222d' },
  dark: { bg: '#10151d', floor: '#18202a', bgNight: '#070a10', floorNight: '#0e131a' },
};

export class Engine {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera: THREE.PerspectiveCamera;
  private controls: OrbitControls;
  private mats!: Mats;
  private floor!: THREE.Mesh;
  private hemi!: THREE.HemisphereLight;
  private sun!: THREE.DirectionalLight;
  private rearGlow: THREE.PointLight[] = [];
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
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
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

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();

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
      new THREE.MeshStandardMaterial({ color: THEMES[this.theme].floor, roughness: 0.92, metalness: 0, alphaMap: fade, transparent: true }),
    );
    this.floor.rotation.x = -Math.PI / 2;
    this.floor.receiveShadow = true;
    this.scene.add(this.floor);

    this.hemi = new THREE.HemisphereLight('#ffffff', '#7d8794', 0.6);
    this.scene.add(this.hemi);
    this.sun = new THREE.DirectionalLight('#ffffff', 2.3);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.02;
    this.sun.shadow.radius = 4;
    this.scene.add(this.sun, this.sun.target);
    for (const z of [-0.9, 0.9]) {
      const p = new THREE.PointLight('#ff2a1a', 0, 5, 2);
      p.position.set(0.6, 0.9, z);
      this.rearGlow.push(p);
      this.scene.add(p);
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
    this.cfg = c;
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
      case 'arm':
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
    const map: Record<CategoryId, Pose> = { stop: 'rear', plate: 'rear', side: 'side', front: 'front', arm: 'arm', extra: 'extra' };
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
    this.applyLights();
    this.applyLook();
    this.invalidate();
  }
  private applyLights() {
    if (!this.mats) return;
    setLensPower(this.mats, this.lights);
    Object.values(this.mats.lens).forEach((mm) => (mm.needsUpdate = true));
    this.equip?.glows.forEach((g) => (g.visible = this.lights));
    this.equip?.pools.forEach((p) => (p.visible = this.lights));
    const hasStop = (this.cfg?.lamps.stop.qty ?? 0) > 0;
    this.rearGlow.forEach((p) => (p.intensity = this.lights && hasStop ? 2.2 : 0));
  }

  setTheme(t: Theme) {
    this.theme = t;
    this.applyLook();
    this.invalidate();
  }
  private applyLook() {
    if (!this.floor) return;
    const th = THEMES[this.theme];
    const night = this.lights;
    const bg = new THREE.Color(night ? th.bgNight : th.bg);
    this.scene.background = bg;
    this.scene.fog = new THREE.Fog(bg, 34, 70);
    (this.floor.material as THREE.MeshStandardMaterial).color.set(night ? th.floorNight : th.floor);
    // gece: ay ışığı (soğuk, zayıf) + yerden yansıyan dolgu; dorsenin alt yarısı karanlıkta kaybolmasın
    this.scene.environmentIntensity = night ? 0.3 : 0.75;
    this.hemi.color.set(night ? '#9db2dc' : '#ffffff');
    this.hemi.groundColor.set(night ? '#4a5568' : '#7d8794');
    this.hemi.intensity = night ? 0.5 : 0.42;
    this.sun.color.set(night ? '#c3d0f5' : '#ffffff');
    this.sun.intensity = night ? 0.55 : 2.7;
    this.renderer.toneMappingExposure = night ? 1.15 : 1.0;
    this.shadowDirty = 3;
  }

  private fitShadow(a: Anchors) {
    const cx = -a.L / 2;
    // ışık yukarıdan ve hafif arkadan: gölge dorsenin altına ve kameraya doğru düşer (zemine oturma hissi)
    this.sun.position.set(cx + 3, 20, -5);
    this.sun.target.position.set(cx, 0, 0);
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
    this.renderer.render(this.scene, this.camera);
    this.adapt(now, busy || moved);
    if (busy || moved) this.invalidate();
  };

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
    this.renderer.render(this.scene, this.camera);
    return this.renderer.domElement.toDataURL('image/jpeg', 0.9);
  }

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    this.controls.dispose();
    if (this.trailer) disposeGroup(this.trailer.group);
    if (this.equip) disposeEquipment(this.equip.group);
    this.renderer.dispose();
  }
}
