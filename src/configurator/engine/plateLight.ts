// Plakaya düşen ışık: plaka lambalarının yerleşimine göre üretilen aydınlatma haritası (MeshStandardMaterial.lightMap).
// Yansıma efekti değil: plakanın kendi yüzeyi aydınlanır (albedo × ışık; harfler koyu kalır). Yalnız ışıklar modunda ve
// pozisyon grubu yanınca (plaka lambası işlevi 'plate'). Tepe değer bloom eşiğinin altında: plaka parlar ama ışımaz.
// - Yanda lamba (LTD 229, LTD 2834; çizim HOR 47: plakanın iki yanında, ışık içe): lambaya yakın kenar parlak, ortaya doğru azalır.
// - Üstte modül (RTR 3366: saçağın altında 3 modül, ışık aşağı): üst kenar parlak, aşağı doğru azalır.
// Düşüş eğrileri görsel (fotometrik ölçüm yok); R4/R148 tek düzelik sınırını (en çok / en az ≤ 20) aşmayacak kadar yumuşak.
import * as THREE from 'three';
import { fnLit, onLampChange } from './lampfx';

/** z: lamba ışık pencerelerinin / modüllerin plaka eksenindeki yeri (dünya z, plaka merkezi 0) */
export type PlateLight = { kind: 'side' | 'top'; z: number[] } | null;

const W = 128;
const H = 32;
const PLATE_W = 0.52;
const PLATE_H = 0.11;
/** tepe ışık (lightMapIntensity): plaka beyazı (doğrusal albedo ~0,92) en parlak yerde ~0,8'e çıkar */
const PEAK = 2.7;

function bake(layout: NonNullable<PlateLight>) {
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d')!;
  const img = g.createImageData(W, H);
  const vals = new Float32Array(W * H);
  let max = 1e-6;
  for (let j = 0; j < H; j++) {
    const y = (0.5 - (j + 0.5) / H) * PLATE_H; // tuvalin üstü plakanın üstü (flipY), plaka merkezine göre
    for (let i = 0; i < W; i++) {
      const z = PLATE_W / 2 - ((i + 0.5) / W) * PLATE_W; // u = 0 → dünya +z (plaka düzlemi Y ekseninde π/2 dönük)
      let e = 0;
      if (layout.kind === 'side') {
        for (const zl of layout.z) e += 1 / (1 + Math.pow(Math.abs(z - zl) / 0.09, 1.6));
        e *= 1 - 0.22 * (y / (PLATE_H / 2)) ** 2; // lamba plaka ortası yüksekliğinde: üst ve alt kenar biraz sönük
      } else {
        let across = 0;
        for (const zl of layout.z) across += 1 / (1 + ((z - zl) / 0.13) ** 2);
        e = across / (1 + Math.pow((PLATE_H / 2 - y) / 0.05, 1.5)); // üst kenardan aşağı
      }
      vals[j * W + i] = e;
      max = Math.max(max, e);
    }
  }
  for (let k = 0; k < W * H; k++) {
    const b = Math.round((255 * vals[k]) / max);
    img.data[k * 4] = img.data[k * 4 + 1] = img.data[k * 4 + 2] = b;
    img.data[k * 4 + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.NoColorSpace; // doğrusal ışık değeri
  return tex;
}

let mat: THREE.MeshStandardMaterial | null = null;
let key = '';
let unsub: (() => void) | null = null;

function update() {
  if (mat) mat.lightMapIntensity = mat.lightMap && fnLit('plate') ? PEAK : 0;
}

/** Plaka ve lamba yerleşimi değişince çağrılır (Engine.setConfig); yanma durumu lampfx olaylarından izlenir */
export function setPlateLight(plate: THREE.Mesh, layout: PlateLight) {
  const m = plate.material as THREE.MeshStandardMaterial;
  const k = layout ? `${layout.kind}:${layout.z.map((v) => v.toFixed(3)).join(',')}` : '';
  if (m !== mat || k !== key) {
    m.lightMap?.dispose();
    m.lightMap = layout ? bake(layout) : null;
    m.needsUpdate = true;
    mat = m;
    key = k;
  }
  update();
  unsub ??= onLampChange(update) as () => void;
}
