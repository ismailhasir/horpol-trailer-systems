// Sahne yerleşimi: saf fonksiyonlar, three.js'e bağımlı değil (test edilebilir).
// Eksenler: x dorse boyunca (arka uç +x), y yukarı, z genişlik. Birim: metre.

export type Vec3 = [number, number, number];

export const TRAILER_WIDTH = 2.55;
export const DECK_HEIGHT = 1.25;
export const WHEEL_RADIUS = 0.54;
const REAR_BUMPER_Y = 0.92;

export interface TrailerDims {
  length: number;
  front: number;
  rear: number;
}

export function trailerDims(length: number): TrailerDims {
  return { length, front: -length / 2, rear: length / 2 };
}

/** Aks konumları (x). Kısa dorselerde iki, diğerlerinde üç aks. */
export function axlePositions(length: number): number[] {
  const { rear } = trailerDims(length);
  const count = length < 10 ? 2 : 3;
  return Array.from({ length: count }, (_, i) => rear - 1.7 - i * 1.31);
}

export function stopLampPositions(length: number, count: number): Vec3[] {
  const { rear } = trailerDims(length);
  const out: Vec3[] = [];
  const half = TRAILER_WIDTH / 2;
  for (let i = 0; i < count / 2; i++) {
    const z = half - 0.3 - i * 0.42;
    out.push([rear + 0.06, REAR_BUMPER_Y, z], [rear + 0.06, REAR_BUMPER_Y, -z]);
  }
  return out;
}

export function platePosition(length: number): Vec3 {
  return [trailerDims(length).rear + 0.06, REAR_BUMPER_Y - 0.08, 0];
}

export function plateLampPositions(length: number, count: number): Vec3[] {
  const [x, y] = platePosition(length);
  const out: Vec3[] = [];
  for (let i = 0; i < count / 2; i++) {
    const z = 0.32 + i * 0.12;
    out.push([x + 0.02, y + 0.17, z], [x + 0.02, y + 0.17, -z]);
  }
  return out;
}

/** Yan markerlar iki yana eşit bölünür ve dorse boyunca eşit aralıklarla dizilir. */
export function sideMarkerPositions(length: number, count: number): Vec3[] {
  const { front, rear } = trailerDims(length);
  const perSide = Math.floor(count / 2);
  const start = front + 0.5;
  const end = rear - 0.4;
  const y = DECK_HEIGHT - 0.12;
  const z = TRAILER_WIDTH / 2 + 0.02;
  const out: Vec3[] = [];
  for (let i = 0; i < perSide; i++) {
    const x = perSide === 1 ? (start + end) / 2 : start + ((end - start) * i) / (perSide - 1);
    out.push([x, y, z], [x, y, -z]);
  }
  return out;
}

/** Ön paneldeki soket fişleri. */
export function plugPositions(length: number, plugs: number): Vec3[] {
  const { front } = trailerDims(length);
  const gap = 0.22;
  return Array.from({ length: plugs }, (_, i) => [front - 0.04, DECK_HEIGHT + 0.35, (i - (plugs - 1) / 2) * gap] as Vec3);
}
