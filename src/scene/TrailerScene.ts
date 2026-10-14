import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { byId, lampCategories, setLengths, sockets, trailerTypes, type LampCategoryId } from "../config/catalog";
import type { Configuration } from "../state/config";
import {
  DECK_HEIGHT,
  TRAILER_WIDTH,
  WHEEL_RADIUS,
  axlePositions,
  plateLampPositions,
  platePosition,
  plugPositions,
  sideMarkerPositions,
  stopLampPositions,
  trailerDims,
  type Vec3,
} from "./layout";

// Performans notları:
// - Sürekli render döngüsü yok: yalnızca bir şey değiştiğinde (seçim, kamera
//   hareketi, yeniden boyutlandırma) tek kare çizilir. Boşta GPU/CPU ~0.
// - Lambalar ve tekerlekler InstancedMesh: adet ne olursa olsun kategori başına
//   tek draw call. Adet değişince yalnızca matrisler güncellenir.
// - Dorse boyu değişince geometri yeniden oluşturulmaz, birim kutular ölçeklenir.
// - Gölge haritası yok; zemindeki yumuşak gölge tek bir gradient dokusu.

export type CameraView = "perspective" | "rear" | "side";

const MAX_WHEELS = 3 * 2;
const LAMP_SHAPES: Record<LampCategoryId, Vec3> = {
  stop: [0.05, 0.13, 0.32],
  side: [0.11, 0.05, 0.025],
  plate: [0.04, 0.035, 0.09],
};

export class TrailerScene {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(32, 1, 0.1, 200);
  private controls: OrbitControls;
  private resizeObserver: ResizeObserver;
  private frame = 0;
  private disposables: { dispose(): void }[] = [];

  private body: THREE.Mesh<THREE.BoxGeometry, THREE.MeshStandardMaterial>;
  private bodyEdges: THREE.LineSegments;
  private roofRails: THREE.Mesh;
  private chassis: THREE.Mesh;
  private bumper: THREE.Mesh;
  private plate: THREE.Mesh;
  private landingGear: THREE.InstancedMesh;
  private harness: THREE.Mesh;
  private ground: THREE.Mesh;
  private tyres: THREE.InstancedMesh;
  private rims: THREE.InstancedMesh;
  private plugs: THREE.InstancedMesh;
  private lamps = new Map<LampCategoryId, THREE.InstancedMesh>();

  private fly: { from: THREE.Vector3; to: THREE.Vector3; tFrom: THREE.Vector3; tTo: THREE.Vector3; start: number } | null = null;
  private length = 0;
  private view: CameraView = "perspective";
  /** Kullanıcı kamerayı elle oynattıysa yeniden boyutlandırmada kadrajı bozmayız. */
  private userMoved = false;

  constructor(private container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    this.scene.environment = env;
    this.disposables.push(env);

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8a96a8, 0.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4);
    sun.position.set(6, 12, 8);
    this.scene.add(sun);

    const unitBox = this.own(new THREE.BoxGeometry(1, 1, 1));
    const mat = (color: string, extra: THREE.MeshStandardMaterialParameters = {}) =>
      this.own(new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.1, ...extra }));
    const dark = mat("#20252c", { roughness: 0.8 });

    this.body = new THREE.Mesh(unitBox, mat("#d9dee6", { roughness: 0.55 }));
    this.bodyEdges = new THREE.LineSegments(
      this.own(new THREE.EdgesGeometry(unitBox)),
      this.own(new THREE.LineBasicMaterial({ color: "#173f82", transparent: true, opacity: 0.35 })),
    );
    this.roofRails = new THREE.Mesh(unitBox, mat("#173f82", { metalness: 0.3 }));
    this.chassis = new THREE.Mesh(unitBox, dark);
    this.bumper = new THREE.Mesh(unitBox, dark);
    this.plate = new THREE.Mesh(unitBox, mat("#f2f2f2", { roughness: 0.3 }));
    this.harness = new THREE.Mesh(unitBox, mat("#111317", { roughness: 0.9 }));

    this.landingGear = new THREE.InstancedMesh(unitBox, mat("#3a414b", { metalness: 0.5 }), 2);

    const tyreGeo = this.own(new THREE.CylinderGeometry(WHEEL_RADIUS, WHEEL_RADIUS, 0.38, 28).rotateX(Math.PI / 2));
    const rimGeo = this.own(new THREE.CylinderGeometry(0.3, 0.3, 0.02, 20).rotateX(Math.PI / 2));
    this.tyres = new THREE.InstancedMesh(tyreGeo, mat("#16181b", { roughness: 0.95 }), MAX_WHEELS);
    this.rims = new THREE.InstancedMesh(rimGeo, mat("#c9ced6", { metalness: 0.9, roughness: 0.25 }), MAX_WHEELS);

    const plugGeo = this.own(new THREE.CylinderGeometry(0.07, 0.07, 0.08, 16).rotateZ(Math.PI / 2));
    this.plugs = new THREE.InstancedMesh(plugGeo, mat("#1d4f9e", { metalness: 0.2 }), 4);

    for (const category of lampCategories) {
      const [x, y, z] = LAMP_SHAPES[category.id];
      const lens = this.own(
        // Yanık lamba: ışıktan etkilenmeyen, tonemap dışı saf renk (hem ucuz hem doygun).
        new THREE.MeshBasicMaterial({ color: category.glow, toneMapped: false }),
      );
      const mesh = new THREE.InstancedMesh(this.own(new THREE.BoxGeometry(x, y, z)), lens, category.count.max);
      mesh.count = 0;
      this.lamps.set(category.id, mesh);
    }

    this.ground = new THREE.Mesh(
      this.own(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2)),
      this.own(new THREE.MeshBasicMaterial({ map: this.own(shadowTexture()), transparent: true, depthWrite: false })),
    );

    for (const mesh of [this.tyres, this.rims, this.plugs, this.landingGear, ...this.lamps.values()]) {
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    }
    this.scene.add(
      this.ground,
      this.body,
      this.bodyEdges,
      this.roofRails,
      this.chassis,
      this.bumper,
      this.plate,
      this.harness,
      this.landingGear,
      this.tyres,
      this.rims,
      this.plugs,
      ...this.lamps.values(),
    );

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.12;
    this.controls.minDistance = 4;
    this.controls.maxDistance = 60;
    this.controls.maxPolarAngle = Math.PI / 2 - 0.05;
    this.controls.addEventListener("change", this.requestRender);
    this.controls.addEventListener("start", () => {
      this.fly = null;
      this.userMoved = true;
    });

    this.resizeObserver = new ResizeObserver(this.resize);
    this.resizeObserver.observe(container);
    this.resize();
  }

  update(config: Configuration) {
    const type = byId(trailerTypes, config.trailerTypeId);
    const length = byId(setLengths, config.setLengthId).meters;
    const socket = byId(sockets, config.socketId);
    const { front, rear } = trailerDims(length);
    const w = TRAILER_WIDTH;
    const m = new THREE.Matrix4();

    // Kasa
    const h = type.body.height;
    const bodyLen = length - 0.05;
    this.body.scale.set(bodyLen, h, w);
    this.body.position.set(0, DECK_HEIGHT + h / 2, 0);
    this.body.material.color.set(type.body.color);
    this.bodyEdges.scale.copy(this.body.scale);
    this.bodyEdges.position.copy(this.body.position);
    this.roofRails.visible = type.body.kind === "curtain";
    this.roofRails.scale.set(bodyLen + 0.02, 0.12, w + 0.02);
    this.roofRails.position.set(0, DECK_HEIGHT + h - 0.05, 0);

    this.chassis.scale.set(length, 0.28, w - 0.04);
    this.chassis.position.set(0, DECK_HEIGHT - 0.14, 0);
    this.bumper.scale.set(0.12, 0.16, w - 0.15);
    this.bumper.position.set(rear, 0.92, 0);
    this.plate.scale.set(0.02, 0.11, 0.52);
    this.plate.position.set(...platePosition(length));

    // Kablo seti: ön soketten arkaya şasi altında
    this.harness.scale.set(length - 0.3, 0.04, 0.04);
    this.harness.position.set(0, DECK_HEIGHT - 0.32, 0.55);

    // Ayaklar
    for (const [i, z] of [-0.9, 0.9].entries()) {
      m.compose(new THREE.Vector3(front + 2.4, (DECK_HEIGHT - 0.28) / 2, z), IDENTITY, new THREE.Vector3(0.12, DECK_HEIGHT - 0.28, 0.12));
      this.landingGear.setMatrixAt(i, m);
    }
    this.landingGear.instanceMatrix.needsUpdate = true;

    // Tekerlekler
    const axles = axlePositions(length);
    let n = 0;
    for (const x of axles) {
      for (const side of [1, -1]) {
        const z = side * (w / 2 - 0.22);
        m.makeTranslation(x, WHEEL_RADIUS, z);
        this.tyres.setMatrixAt(n, m);
        m.makeTranslation(x, WHEEL_RADIUS, z + side * 0.2);
        this.rims.setMatrixAt(n, m);
        n++;
      }
    }
    this.tyres.count = this.rims.count = n;
    this.tyres.instanceMatrix.needsUpdate = this.rims.instanceMatrix.needsUpdate = true;

    // Soket fişleri
    setPositions(this.plugs, plugPositions(length, socket.plugs));

    // Lambalar
    setPositions(this.lamps.get("stop")!, stopLampPositions(length, config.lamps.stop.count));
    setPositions(this.lamps.get("side")!, sideMarkerPositions(length, config.lamps.side.count));
    setPositions(this.lamps.get("plate")!, plateLampPositions(length, config.lamps.plate.count));

    this.ground.scale.set(length + 5, 1, w + 5);

    if (length !== this.length) {
      this.length = length;
      this.setView(this.view, this.camera.position.lengthSq() > 0);
    }
    this.requestRender();
  }

  setView(view: CameraView, animate = true) {
    this.view = view;
    this.userMoved = false;
    const L = this.length || 13.6;
    const vfov = THREE.MathUtils.degToRad(this.camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * this.camera.aspect);
    // Görünen yarı genişlik/yüksekliğin kadraja sığması için gereken mesafe.
    const fit = (halfW: number, halfH: number) =>
      Math.max(halfW / Math.tan(hfov / 2), halfH / Math.tan(vfov / 2)) * 1.12;
    const target = new THREE.Vector3(0, 1.9, 0);
    const dir = new THREE.Vector3();
    let dist: number;
    if (view === "rear") {
      target.set(L / 2, 1.9, 0);
      dir.set(1, 0.12, 0.001);
      dist = fit(TRAILER_WIDTH / 2 + 0.3, 2.2) + 0.2;
    } else if (view === "side") {
      dir.set(0, 0.1, 1);
      dist = fit(L / 2 + 0.4, 2.2) + TRAILER_WIDTH / 2;
    } else {
      dir.set(0.75, 0.42, 0.9);
      // Bounding küresi kadraja girsin (yakın uç perspektifte büyüdüğü için kısmıyoruz).
      const r = 0.5 * Math.hypot(L, 4.2, TRAILER_WIDTH);
      dist = (r / Math.sin(Math.min(vfov, hfov) / 2)) * 0.98;
    }
    const pos = dir.normalize().multiplyScalar(dist).add(target);
    if (!animate) {
      this.camera.position.copy(pos);
      this.controls.target.copy(target);
      this.controls.update();
      this.requestRender();
      return;
    }
    this.fly = {
      from: this.camera.position.clone(),
      to: pos,
      tFrom: this.controls.target.clone(),
      tTo: target,
      start: performance.now(),
    };
    this.requestRender();
  }

  dispose() {
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.disposables.forEach((d) => d.dispose());
    this.lamps.forEach((l) => l.dispose());
    [this.tyres, this.rims, this.plugs, this.landingGear].forEach((l) => l.dispose());
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  private requestRender = () => {
    if (!this.frame) this.frame = requestAnimationFrame(this.tick);
  };

  private tick = (now: number) => {
    this.frame = 0;
    let active = false;
    if (this.fly) {
      const t = Math.min(1, (now - this.fly.start) / 700);
      const e = 1 - Math.pow(1 - t, 3);
      this.camera.position.lerpVectors(this.fly.from, this.fly.to, e);
      this.controls.target.lerpVectors(this.fly.tFrom, this.fly.tTo, e);
      if (t < 1) active = true;
      else this.fly = null;
    }
    // Damping sürerken update() true döner ve "change" ile bir sonraki kareyi ister.
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    if (active) this.requestRender();
  };

  private resize = () => {
    const { clientWidth: w, clientHeight: h } = this.container;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    if (this.length && !this.userMoved && !this.fly) this.setView(this.view, false);
    this.requestRender();
  };

  private own<T extends { dispose(): void }>(resource: T): T {
    this.disposables.push(resource);
    return resource;
  }
}

const IDENTITY = new THREE.Quaternion();

function setPositions(mesh: THREE.InstancedMesh, positions: Vec3[]) {
  const m = new THREE.Matrix4();
  const count = Math.min(positions.length, mesh.instanceMatrix.count);
  for (let i = 0; i < count; i++) {
    m.makeTranslation(...positions[i]);
    mesh.setMatrixAt(i, m);
  }
  mesh.count = count;
  mesh.instanceMatrix.needsUpdate = true;
}

function shadowTexture() {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(11,28,57,0.38)");
  g.addColorStop(0.55, "rgba(11,28,57,0.18)");
  g.addColorStop(1, "rgba(11,28,57,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
