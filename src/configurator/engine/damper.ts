// Blender'da modellenen damper: tools/blender/damper_chassis.py → public/models/damper-chassis.glb (şasi + tekerlekler)
// ve damper-body.glb (kasa + logolar). Buradaki ölçüler betikteki sabitlerle aynıdır; biri değişirse diğeri de değişmeli.
// Koordinatlar: x boyuna (arka uç 0, ön -L), y yukarı, z yanal; metre.
import * as THREE from 'three';

export const DAMPER_GLB = '/models/damper-chassis.glb';
export const DAMPER_BODY_GLB = '/models/damper-body.glb';

const L = 9.0;
const XF = -L;
const W2 = 2.55 / 2;
const TOP = 1.5;
// kasa (betikteki BX0, BX1, Y0, YT, HW)
const BX0 = -8.45;
const BX1 = -0.1;
const Y0 = TOP + 0.12;
const YT = Y0 + 1.53;
const HW = W2 - 0.02;

export const DAMPER = {
  L,
  /** şasi üstü: kasa alt çerçevesi buraya oturur */
  top: TOP,
  /** kasanın en üstü (siperlik) */
  bodyTop: YT + 0.2,
  /** tesisat düzlemi: üst flanşın altı, traverslerin üstü */
  harnessY: 1.44,
  lampY: 1.12,
  plateY: 0.88,
  /** soket levhası (ön traversin altında) */
  socket: { x: XF + 0.115, y: 1.12 },
  frontX: XF + 0.45,
  /** yan ana hat üst flanşın hemen dışında kirişe kelepçeli; arka hatlar kirişlerin arasında */
  trunkZ: 0.66,
  rearZ: 0.4,
  front: { x: XF - 0.005, y: 1.31, z: 1.12 },
  armFront: { x: XF + 0.3, y: 1.45, z: W2 },
  armRear: { x: -0.15, y: 1.22, z: W2 },
  /** yan markerlar şasinin tüm boyunca (boyun dahil); braketler hava tankının ve iniş ayağının üstünden geçer */
  side: { x0: XF + 0.6, x1: -0.55, y: 1.36 },
  /** ek lambalar: kasada değil, şasinin arka kapanış traversinin arkaya bakan yüzünde */
  extra: { x: -0.04, y: 1.32, z0: 0.42, z1: 0.18 },
};

/** Kasa kesiti (z, y): betikteki contour() ile aynı (dik duvar → yuvarlatılmış pah → taban) */
function contour(n = 10): [number, number][] {
  const k = 0.85;
  const bez = (t: number, a: number, b: number, c: number, d: number) => (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d;
  const left: [number, number][] = [[-HW, YT]];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    left.push([bez(t, -HW, -HW, -HW + 0.26, -HW + 0.6), bez(t, Y0 + k, Y0 + k * 0.45, Y0, Y0)]);
  }
  const right = [...left].reverse().map(([z, y]) => [-z, y] as [number, number]);
  return [...left, ...right];
}

/** Tesisat görünümünde gizlenen kasanın yerini gösteren kesit çizgileri */
export function damperSections(): THREE.Vector3[][] {
  const c = contour();
  return [BX0, -6.4, -4.3, -2.2, BX1].map((x) => c.map(([z, y]) => new THREE.Vector3(x, y, z)));
}
