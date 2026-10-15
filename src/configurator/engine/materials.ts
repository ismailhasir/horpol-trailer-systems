// Paylaşılan malzemeler ve basit doku üreticiler. Tüm parçalar aynı malzeme örneklerini kullanır
// (çizim çağrısı ve bellek tasarrufu); ışık açma/kapama yalnızca lens malzemelerini değiştirir.
import * as THREE from 'three';

export type LensColor = 'red' | 'amber' | 'white' | 'redfog' | 'plate';

export interface Mats {
  paint: THREE.MeshPhysicalMaterial;
  paintBlue: THREE.MeshPhysicalMaterial;
  stripe: THREE.MeshStandardMaterial;
  chassis: THREE.MeshStandardMaterial;
  darkMetal: THREE.MeshStandardMaterial;
  alu: THREE.MeshStandardMaterial;
  chrome: THREE.MeshStandardMaterial;
  steel: THREE.MeshStandardMaterial;
  rubber: THREE.MeshStandardMaterial;
  tread: THREE.MeshStandardMaterial;
  plastic: THREE.MeshStandardMaterial;
  curtain: THREE.MeshStandardMaterial;
  deck: THREE.MeshStandardMaterial;
  grille: THREE.MeshStandardMaterial;
  containerBlue: THREE.MeshStandardMaterial;
  plateBg: THREE.MeshStandardMaterial;
  socket: THREE.MeshStandardMaterial;
  socketGrey: THREE.MeshStandardMaterial;
  logo: THREE.MeshStandardMaterial;
  logoWhite: THREE.MeshStandardMaterial;
  lens: Record<LensColor, THREE.MeshPhysicalMaterial>;
  glow: Record<LensColor, THREE.SpriteMaterial>;
  outline: THREE.LineBasicMaterial;
  ghost: THREE.MeshStandardMaterial;
  sysFloor: THREE.MeshStandardMaterial;
  /** konnektör ve modül çerçevesinin açık renk parçası */
  connWhite: THREE.MeshStandardMaterial;
  wire: Record<'main' | 'side' | 'rear' | 'plate' | 'marker' | 'sheath', THREE.MeshStandardMaterial>;
}

const LENS: Record<LensColor, string> = {
  red: '#d4221c',
  amber: '#f29a0c',
  white: '#e9eef6',
  redfog: '#b8160f',
  plate: '#f7f9ff',
};

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

export function glowTexture() {
  return canvasTexture(128, 128, (ctx) => {
    const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.18, 'rgba(255,255,255,0.75)');
    g.addColorStop(0.45, 'rgba(255,255,255,0.18)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
  });
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

function deckTexture() {
  return canvasTexture(
    256,
    256,
    (ctx) => {
      ctx.fillStyle = '#7a5a3c';
      ctx.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 8; i++) {
        const y = i * 32;
        ctx.fillStyle = i % 2 ? '#86654a' : '#6f5036';
        ctx.fillRect(0, y + 1, 256, 30);
        ctx.fillStyle = 'rgba(0,0,0,0.35)';
        ctx.fillRect(0, y, 256, 1.5);
        for (let k = 0; k < 6; k++) {
          ctx.fillStyle = 'rgba(40,25,10,0.12)';
          ctx.fillRect(Math.random() * 256, y + 4 + Math.random() * 22, 40 + Math.random() * 60, 1);
        }
      }
    },
    [6, 1],
  );
}

function grilleTexture() {
  return canvasTexture(
    128,
    128,
    (ctx) => {
      ctx.fillStyle = '#2a2e34';
      ctx.fillRect(0, 0, 128, 128);
      ctx.fillStyle = '#121418';
      for (let y = 4; y < 128; y += 8) ctx.fillRect(6, y, 116, 4);
    },
    [1, 1],
  );
}

export function createMaterials(logoBlue: THREE.Texture | null, logoWhite: THREE.Texture | null): Mats {
  const std = (p: THREE.MeshStandardMaterialParameters) => new THREE.MeshStandardMaterial(p);
  const lens = {} as Mats['lens'];
  const glow = {} as Mats['glow'];
  const gt = glowTexture();
  (Object.keys(LENS) as LensColor[]).forEach((k) => {
    const col = new THREE.Color(LENS[k]);
    lens[k] = new THREE.MeshPhysicalMaterial({
      color: col.clone().multiplyScalar(k === 'white' || k === 'plate' ? 0.9 : 0.75),
      emissive: col,
      emissiveIntensity: 0.08,
      roughness: 0.18,
      metalness: 0,
      clearcoat: 1,
      clearcoatRoughness: 0.08,
    });
    glow[k] = new THREE.SpriteMaterial({
      map: gt,
      color: k === 'plate' ? new THREE.Color('#fff6e0') : col,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      transparent: true,
      opacity: 0.9,
    });
  });
  const wire = (color: string, e = 0.25) =>
    std({ color, roughness: 0.35, metalness: 0.05, emissive: new THREE.Color(color), emissiveIntensity: e * 1.6 });

  return {
    paint: new THREE.MeshPhysicalMaterial({ color: '#f3f5f8', roughness: 0.38, metalness: 0.05, clearcoat: 0.45, clearcoatRoughness: 0.25 }),
    paintBlue: new THREE.MeshPhysicalMaterial({ color: '#1c5198', roughness: 0.35, metalness: 0.15, clearcoat: 0.6, clearcoatRoughness: 0.2 }),
    stripe: std({ color: '#1c5198', roughness: 0.4, metalness: 0.2 }),
    chassis: std({ color: '#262a30', roughness: 0.5, metalness: 0.55 }),
    darkMetal: std({ color: '#383d45', roughness: 0.42, metalness: 0.7 }),
    alu: std({ color: '#c3c9d1', roughness: 0.3, metalness: 0.9 }),
    chrome: std({ color: '#eef2f6', roughness: 0.08, metalness: 1 }),
    steel: std({ color: '#d5dbe2', roughness: 0.2, metalness: 1 }),
    rubber: std({ color: '#141518', roughness: 0.92, metalness: 0 }),
    tread: std({ color: '#0d0e10', roughness: 1, metalness: 0 }),
    plastic: std({ color: '#17191c', roughness: 0.55, metalness: 0.05 }),
    curtain: std({ color: '#eef1f5', roughness: 0.82, metalness: 0, side: THREE.DoubleSide }),
    deck: std({ map: deckTexture(), roughness: 0.85, metalness: 0 }),
    grille: std({ map: grilleTexture(), roughness: 0.6, metalness: 0.3 }),
    containerBlue: std({ color: '#1c5198', roughness: 0.48, metalness: 0.35 }),
    plateBg: std({ color: '#f5f6f2', roughness: 0.4, metalness: 0.1 }),
    socket: std({ color: '#1b1d21', roughness: 0.4, metalness: 0.3 }),
    socketGrey: std({ color: '#8b939e', roughness: 0.4, metalness: 0.5 }),
    logo: std({ map: logoBlue ?? undefined, transparent: true, alphaTest: 0.05, roughness: 0.6, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }),
    logoWhite: std({ map: logoWhite ?? undefined, transparent: true, alphaTest: 0.05, roughness: 0.6, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }),
    lens,
    glow,
    outline: new THREE.LineBasicMaterial({ color: '#7f9cc4', transparent: true, opacity: 0.55 }),
    ghost: std({ color: '#c8d3e2', transparent: true, opacity: 0.12, depthWrite: false, roughness: 1 }),
    connWhite: std({ color: '#d9dee6', roughness: 0.45, metalness: 0.05 }),
    sysFloor: std({ color: '#f3f6fa', roughness: 0.9, metalness: 0, transparent: true, opacity: 0.94 }),
    wire: {
      main: wire('#3b82f6', 0.35),
      side: wire('#f59e0b', 0.3),
      rear: wire('#ef4444', 0.3),
      plate: wire('#e5e7eb', 0.15),
      marker: wire('#22c55e', 0.3),
      sheath: std({ color: '#1b1d20', roughness: 0.6, metalness: 0.1 }),
    },
  };
}

/** Işıklar açık/kapalı: paylaşılan lens malzemelerinin parlaklığı */
export function setLensPower(m: Mats, on: boolean) {
  (Object.keys(m.lens) as LensColor[]).forEach((k) => {
    m.lens[k].emissiveIntensity = on ? (k === 'plate' ? 2.2 : k === 'white' ? 2.4 : 3.2) : 0.08;
    m.lens[k].toneMapped = !on;
  });
}
