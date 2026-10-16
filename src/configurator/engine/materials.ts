// Paylaşılan malzemeler ve basit doku üreticiler. Tüm parçalar aynı malzeme örneklerini kullanır
// (çizim çağrısı ve bellek tasarrufu); ışık açma/kapama yalnızca lens malzemelerini değiştirir.
import * as THREE from 'three';

export type LensColor = 'red' | 'amber' | 'white' | 'redfog' | 'plate';

export interface Mats {
  paint: THREE.MeshPhysicalMaterial;
  paintBlue: THREE.MeshPhysicalMaterial;
  /** silobas hava filtresi sarısı, yangın dolabı kırmızısı */
  paintYellow: THREE.MeshPhysicalMaterial;
  paintRed: THREE.MeshPhysicalMaterial;
  /** silobas şeridi */
  accent: THREE.MeshStandardMaterial;
  stripe: THREE.MeshStandardMaterial;
  chassis: THREE.MeshStandardMaterial;
  /** parlak siyah boyalı şasi (KTL + boya) */
  chassisBlack: THREE.MeshPhysicalMaterial;
  /** tanker üst kaportası: saten gri alüminyum */
  fairingGrey: THREE.MeshPhysicalMaterial;
  darkMetal: THREE.MeshStandardMaterial;
  alu: THREE.MeshStandardMaterial;
  chrome: THREE.MeshStandardMaterial;
  steel: THREE.MeshStandardMaterial;
  rubber: THREE.MeshStandardMaterial;
  /** lastik: diş kanalları bump haritasıyla */
  tire: THREE.MeshStandardMaterial;
  /** çamurluk (açık silindir kabuk, iki yüzlü) */
  fender: THREE.MeshStandardMaterial;
  tread: THREE.MeshStandardMaterial;
  plastic: THREE.MeshStandardMaterial;
  curtain: THREE.MeshStandardMaterial;
  strap: THREE.MeshStandardMaterial;
  tankAlu: THREE.MeshStandardMaterial;
  /** tanker üst kaportası: açık gümüş boya (düz yüzeyler metal gibi kararmasın) */
  fairing: THREE.MeshPhysicalMaterial;
  /** reflektif kontur bantları (ECE R48) */
  reflRed: THREE.MeshStandardMaterial;
  reflYellow: THREE.MeshStandardMaterial;
  /** ECE R70 uzun araç plakası, ADR turuncu plaka, rampa uyarı plakası */
  r70: THREE.MeshStandardMaterial;
  adr: THREE.MeshStandardMaterial;
  /** ADR sınıf 3 (yanıcı sıvı) tehlike etiketi, dönüş seferi "BOŞ" levhası */
  hazard3: THREE.MeshStandardMaterial;
  emptySign: THREE.MeshStandardMaterial;
  warn: THREE.MeshStandardMaterial;
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

/** Lastik dişi: v (profil) boyunca boyuna kanallar, u (çevre) boyunca enine yarıklar. Beyaz yüksek, siyah kanal. */
function treadTexture() {
  const t = canvasTexture(
    64,
    256,
    (ctx) => {
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, 64, 256);
      ctx.fillStyle = '#000';
      // profil noktaları 0..10 (v=0..1); sırt 3..7 arası. Boyuna kanallar:
      for (const v of [0.36, 0.45, 0.55, 0.64]) ctx.fillRect(0, v * 256 - 3, 64, 6);
      // enine yarıklar (omuz blokları)
      for (const [a, b] of [
        [0.29, 0.355],
        [0.645, 0.71],
      ])
        ctx.fillRect(28, a * 256, 6, (b - a) * 256);
      ctx.fillStyle = '#444';
      for (const [a, b] of [
        [0.37, 0.44],
        [0.46, 0.54],
        [0.56, 0.63],
      ])
        ctx.fillRect(12, a * 256, 3, (b - a) * 256);
    },
    [56, 1],
  );
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

/** ECE R70: sarı zemin, kırmızı (floresan) kenar */
function r70Texture() {
  return canvasTexture(128, 384, (ctx) => {
    ctx.fillStyle = '#d8231a';
    ctx.fillRect(0, 0, 128, 384);
    ctx.fillStyle = '#f6c400';
    ctx.fillRect(18, 18, 92, 348);
  });
}
/** ADR turuncu plaka: üstte tehlike numarası, altta UN numarası (33 / 1203: benzin) */
function adrTexture() {
  return canvasTexture(256, 192, (ctx) => {
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, 256, 192);
    ctx.fillStyle = '#f27a00';
    ctx.fillRect(8, 8, 240, 176);
    ctx.fillStyle = '#111';
    ctx.fillRect(8, 92, 240, 8);
    ctx.font = 'bold 72px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('33', 128, 52);
    ctx.fillText('1203', 128, 142);
  });
}
function hazard3Texture() {
  return canvasTexture(256, 256, (ctx) => {
    ctx.translate(128, 128);
    ctx.rotate(Math.PI / 4);
    ctx.fillStyle = '#d21d19';
    ctx.fillRect(-88, -88, 176, 176);
    ctx.strokeStyle = '#111';
    ctx.lineWidth = 5;
    ctx.strokeRect(-80, -80, 160, 160);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    // alev
    ctx.fillStyle = '#111';
    ctx.beginPath();
    ctx.moveTo(128, 46);
    ctx.bezierCurveTo(150, 80, 166, 96, 156, 122);
    ctx.bezierCurveTo(150, 138, 106, 138, 100, 122);
    ctx.bezierCurveTo(94, 104, 112, 96, 114, 76);
    ctx.bezierCurveTo(124, 88, 126, 96, 124, 104);
    ctx.bezierCurveTo(134, 90, 134, 66, 128, 46);
    ctx.fill();
    ctx.fillRect(98, 132, 60, 8);
    ctx.font = 'bold 34px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('3', 128, 212);
  });
}
function emptySignTexture() {
  return canvasTexture(256, 192, (ctx) => {
    ctx.fillStyle = '#c9ccd0';
    ctx.fillRect(0, 0, 256, 192);
    ctx.fillStyle = '#111';
    ctx.font = 'bold 84px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('BOŞ', 128, 100);
  });
}
/** Kırmızı-beyaz çapraz şeritli uyarı plakası */
function warnTexture() {
  return canvasTexture(128, 128, (ctx) => {
    ctx.fillStyle = '#f3f3f3';
    ctx.fillRect(0, 0, 128, 128);
    ctx.fillStyle = '#d31f1a';
    for (let i = -4; i < 6; i += 2) {
      ctx.beginPath();
      ctx.moveTo(i * 32, 128);
      ctx.lineTo(i * 32 + 32, 128);
      ctx.lineTo(i * 32 + 160, 0);
      ctx.lineTo(i * 32 + 128, 0);
      ctx.fill();
    }
  });
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
  // kablo: oluklu koruge boru görünümü (doku boyunca halkalar); renk okunsun diye hafif ışıma
  const rib = ribTexture();
  const wire = (color: string, e = 0.25) =>
    std({ color, map: rib, bumpMap: rib, bumpScale: 1.2, roughness: 0.5, metalness: 0.05, emissive: new THREE.Color(color), emissiveIntensity: e * 0.75 });

  return {
    paint: new THREE.MeshPhysicalMaterial({ color: '#f3f5f8', roughness: 0.38, metalness: 0.05, clearcoat: 0.45, clearcoatRoughness: 0.25 }),
    paintBlue: new THREE.MeshPhysicalMaterial({ color: '#1c5198', roughness: 0.35, metalness: 0.15, clearcoat: 0.6, clearcoatRoughness: 0.2 }),
    paintYellow: new THREE.MeshPhysicalMaterial({ color: '#f0b90b', roughness: 0.4, metalness: 0.05, clearcoat: 0.5, clearcoatRoughness: 0.25 }),
    paintRed: new THREE.MeshPhysicalMaterial({ color: '#c5161d', roughness: 0.38, metalness: 0.05, clearcoat: 0.55, clearcoatRoughness: 0.2 }),
    accent: std({ color: '#f08a00', roughness: 0.45, metalness: 0.05, side: THREE.DoubleSide }),
    stripe: std({ color: '#1c5198', roughness: 0.4, metalness: 0.2 }),
    chassis: std({ color: '#262a30', roughness: 0.5, metalness: 0.55 }),
    fairingGrey: new THREE.MeshPhysicalMaterial({ color: '#9ea5ae', roughness: 0.38, metalness: 0.55, clearcoat: 0.3, clearcoatRoughness: 0.3, side: THREE.DoubleSide }),
    chassisBlack: new THREE.MeshPhysicalMaterial({ color: '#111215', roughness: 0.42, metalness: 0.25, clearcoat: 0.55, clearcoatRoughness: 0.3 }),
    darkMetal: std({ color: '#383d45', roughness: 0.42, metalness: 0.7 }),
    alu: std({ color: '#c3c9d1', roughness: 0.3, metalness: 0.9 }),
    chrome: std({ color: '#eef2f6', roughness: 0.08, metalness: 1 }),
    steel: std({ color: '#d5dbe2', roughness: 0.2, metalness: 1 }),
    rubber: std({ color: '#141518', roughness: 0.92, metalness: 0 }),
    tire: (() => {
      const tt = treadTexture();
      return std({ color: '#17181b', roughness: 0.9, metalness: 0, bumpMap: tt, bumpScale: 2.5, roughnessMap: tt });
    })(),
    fender: std({ color: '#1a1c20', roughness: 0.6, metalness: 0.05, side: THREE.DoubleSide }),
    tread: std({ color: '#0d0e10', roughness: 1, metalness: 0 }),
    plastic: std({ color: '#17191c', roughness: 0.55, metalness: 0.05 }),
    curtain: std({ color: '#eef1f5', roughness: 0.82, metalness: 0, side: THREE.DoubleSide }),
    strap: std({ color: '#cfd4da', roughness: 0.7, metalness: 0 }),
    tankAlu: std({ color: '#dce1e7', roughness: 0.2, metalness: 1 }),
    fairing: new THREE.MeshPhysicalMaterial({ color: '#d6dbe1', roughness: 0.32, metalness: 0.35, clearcoat: 0.6, clearcoatRoughness: 0.2 }),
    reflRed: std({ color: '#c8141b', roughness: 0.3, metalness: 0.1, emissive: new THREE.Color('#5a0000'), emissiveIntensity: 0.25 }),
    reflYellow: std({ color: '#f2b800', roughness: 0.3, metalness: 0.1, emissive: new THREE.Color('#4a3300'), emissiveIntensity: 0.25 }),
    r70: std({ map: r70Texture(), roughness: 0.35, metalness: 0.05 }),
    adr: std({ map: adrTexture(), roughness: 0.4, metalness: 0.1 }),
    hazard3: std({ map: hazard3Texture(), roughness: 0.4, metalness: 0.05, alphaTest: 0.5, side: THREE.DoubleSide }),
    emptySign: std({ map: emptySignTexture(), roughness: 0.4, metalness: 0.2 }),
    warn: std({ map: warnTexture(), roughness: 0.4, metalness: 0.05 }),
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
    outline: new THREE.LineBasicMaterial({ color: '#6f8fbd', transparent: true, opacity: 0.7 }),
    ghost: std({ color: '#b9c6d8', transparent: true, opacity: 0.2, depthWrite: false, roughness: 1 }),
    connWhite: std({ color: '#d9dee6', roughness: 0.45, metalness: 0.05 }),
    sysFloor: std({ color: '#f3f6fa', roughness: 0.9, metalness: 0, transparent: true, opacity: 0.94 }),
    wire: {
      main: wire('#3b82f6', 0.35),
      side: wire('#f59e0b', 0.3),
      rear: wire('#ef4444', 0.3),
      plate: wire('#e5e7eb', 0.15),
      marker: wire('#22c55e', 0.3),
      sheath: std({ color: '#1b1d20', map: rib, bumpMap: rib, bumpScale: 1.2, roughness: 0.6, metalness: 0.1 }),
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
