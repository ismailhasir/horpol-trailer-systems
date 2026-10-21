// Paylaşılan malzemeler ve basit doku üreticiler (kodla çizilen parçalar: soketler, modül, tesisat, braketler). Tüm parçalar
// aynı malzeme örneklerini kullanır (çizim çağrısı ve bellek tasarrufu). Dorse ve lambalar kendi GLB malzemeleriyle gelir.
import * as THREE from 'three';
import { WIRE_COLORS as W } from '../colors';

export interface Mats {
  chassis: THREE.MeshStandardMaterial;
  darkMetal: THREE.MeshStandardMaterial;
  plastic: THREE.MeshStandardMaterial;
  socket: THREE.MeshStandardMaterial;
  socketGrey: THREE.MeshStandardMaterial;
  logoWhite: THREE.MeshStandardMaterial;
  outline: THREE.LineBasicMaterial;
  /** konnektör ve modül çerçevesinin açık renk parçası */
  connWhite: THREE.MeshStandardMaterial;
  wire: Record<'main' | 'side' | 'rear' | 'plate' | 'marker' | 'sheath', THREE.MeshStandardMaterial>;
}

function canvasTexture(w: number, h: number, draw: (ctx: CanvasRenderingContext2D) => void, repeat?: [number, number]) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const ctx = c.getContext('2d')!;
  draw(ctx);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) {
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(...repeat);
  }
  return t;
}

/** Koruge boru halkaları: u yönünde tekrarlayan açık sırt / koyu oluk (renk ve kabartma için) */
function ribTexture() {
  return canvasTexture(
    64,
    4,
    (ctx) => {
      for (let x = 0; x < 64; x++) {
        const v = Math.round(255 * (0.88 + 0.12 * Math.cos((x / 64) * Math.PI * 2)));
        ctx.fillStyle = `rgb(${v},${v},${v})`;
        ctx.fillRect(x, 0, 1, 4);
      }
    },
    [1, 1],
  );
}

export function fadeTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const ctx = c.getContext('2d')!;
  const g = ctx.createRadialGradient(256, 256, 60, 256, 256, 256);
  g.addColorStop(0, '#ffffff');
  g.addColorStop(0.55, '#ffffff');
  g.addColorStop(1, '#000000');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 512, 512);
  const t = new THREE.CanvasTexture(c);
  return t;
}

export function createMaterials(logoWhite: THREE.Texture | null): Mats {
  const std = (p: THREE.MeshStandardMaterialParameters) => new THREE.MeshStandardMaterial(p);
  // kablo: oluklu koruge boru görünümü (doku boyunca halkalar); renk okunsun diye hafif ışıma
  const rib = ribTexture();
  const wire = (color: string, e = 0.25) =>
    std({ color, map: rib, bumpMap: rib, bumpScale: 1.2, roughness: 0.5, metalness: 0.05, emissive: new THREE.Color(color), emissiveIntensity: e * 0.75 });

  return {
    chassis: std({ color: '#262a30', roughness: 0.5, metalness: 0.55 }),
    darkMetal: std({ color: '#383d45', roughness: 0.42, metalness: 0.7 }),
    plastic: std({ color: '#17191c', roughness: 0.55, metalness: 0.05 }),
    socket: std({ color: '#1b1d21', roughness: 0.4, metalness: 0.3 }),
    socketGrey: std({ color: '#8b939e', roughness: 0.4, metalness: 0.5 }),
    logoWhite: std({ map: logoWhite ?? undefined, transparent: true, alphaTest: 0.05, roughness: 0.6, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }),
    outline: new THREE.LineBasicMaterial({ color: '#6f8fbd', transparent: true, opacity: 0.7 }),
    connWhite: std({ color: '#d9dee6', roughness: 0.45, metalness: 0.05 }),
    wire: {
      main: wire(W.main, 0.35),
      side: wire(W.side, 0.3),
      rear: wire(W.rear, 0.3),
      plate: wire(W.plate, 0.15),
      marker: wire(W.marker, 0.3),
      sheath: std({ color: '#1b1d20', map: rib, bumpMap: rib, bumpScale: 1.2, roughness: 0.6, metalness: 0.1 }),
    },
  };
}
