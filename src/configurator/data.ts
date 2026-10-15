// Konfigüratör verisi: dorse tipleri, soketler, uzunluklar ve lamba katalogu.
// Ürün kodları gerçek Horpol kodlarıdır (Dideban ürün verisinden). 3D görünümleri TEMSİLİDİR:
// gerçek GLB modeller gelince `style` yerine model dosyası bağlanacak.
// Adet sınırları ve uyumluluk kuralları ÖRNEKTİR, satış ekibiyle doğrulanacak.

export type TrailerId =
  | 'standart'
  | 'kapali'
  | 'frigo'
  | 'flatbed'
  | 'stepdeck'
  | 'lowbed'
  | 'damper'
  | 'tanker'
  | 'arac'
  | 'konteyner';

export type SocketId = '7x2' | '15' | '7x2+15';
export type LengthId = '13.6' | '12' | '9';
export type CategoryId = 'stop' | 'side' | 'plate' | 'front' | 'arm' | 'extra';

export interface TrailerDef {
  id: TrailerId;
  /** izin verilen set uzunlukları */
  lengths: LengthId[];
}

export const TRAILERS: TrailerDef[] = [
  { id: 'standart', lengths: ['13.6', '12', '9'] },
  { id: 'kapali', lengths: ['13.6', '12', '9'] },
  { id: 'frigo', lengths: ['13.6', '12'] },
  { id: 'flatbed', lengths: ['13.6', '12', '9'] },
  { id: 'stepdeck', lengths: ['13.6', '12'] },
  { id: 'lowbed', lengths: ['13.6', '12'] },
  { id: 'damper', lengths: ['12', '9'] },
  { id: 'tanker', lengths: ['13.6', '12', '9'] },
  { id: 'arac', lengths: ['13.6'] },
  { id: 'konteyner', lengths: ['13.6', '12'] },
];

export const SOCKETS: SocketId[] = ['7x2', '15', '7x2+15'];
export const LENGTHS: LengthId[] = ['13.6', '12', '9'];
export const lengthMeters = (l: LengthId) => Number(l);

/** 3D görünüm biçimi (temsili) */
export type LampStyle =
  | 'block'
  | 'carmen'
  | 'navia'
  | 'compact'
  | 'round'
  | 'oval'
  | 'rect'
  | 'slim'
  | 'disc'
  | 'plate-wide'
  | 'plate-small'
  | 'pos-rect'
  | 'pos-round'
  | 'arm-dragon'
  | 'arm-classic'
  | 'strip';

export interface LampProduct {
  id: string;
  code: string;
  style: LampStyle;
}

export interface CategoryDef {
  id: CategoryId;
  /** adet: en az, en çok, adım */
  min: number;
  max: number;
  step: number;
  products: LampProduct[];
  /** sahnede lens rengi (temsili) */
  color: string;
}

export const CATEGORIES: CategoryDef[] = [
  {
    id: 'stop',
    min: 2,
    max: 4,
    step: 2,
    color: '#e0322d',
    products: [
      { id: 'lzd3049', code: 'LZD 3049/H101/AMP1', style: 'block' },
      { id: 'lzd2300', code: 'LZD 2300', style: 'carmen' },
      { id: 'lzd2341', code: 'LZD 2341', style: 'navia' },
      { id: 'lzd2246', code: 'LZD 2246', style: 'compact' },
      { id: 'lzd844', code: 'LZD 844', style: 'round' },
    ],
  },
  {
    id: 'side',
    min: 0,
    max: 20,
    step: 2,
    color: '#f5a00a',
    products: [
      { id: 'ld2774', code: 'LD 2774', style: 'oval' },
      { id: 'ld141', code: 'LD 141', style: 'rect' },
      { id: 'ld180', code: 'LD 180', style: 'slim' },
      { id: 'ld185', code: 'LD 185', style: 'disc' },
    ],
  },
  {
    id: 'plate',
    min: 1,
    max: 2,
    step: 1,
    color: '#f4f7ff',
    products: [
      { id: 'ltd2834', code: 'LTD 2834', style: 'plate-wide' },
      { id: 'ltd665', code: 'LTD 665', style: 'plate-small' },
      { id: 'ltd702', code: 'LTD 702', style: 'plate-wide' },
    ],
  },
  {
    id: 'front',
    min: 0,
    max: 2,
    step: 2,
    color: '#f4f7ff',
    products: [
      { id: 'ld364', code: 'LD 364', style: 'pos-rect' },
      { id: 'ld442', code: 'LD 442', style: 'pos-round' },
    ],
  },
  {
    id: 'arm',
    min: 0,
    max: 4,
    step: 2,
    color: '#f5a00a',
    products: [
      { id: 'ld2994', code: 'LD 2994 Dragon', style: 'arm-dragon' },
      { id: 'ldcc2776', code: 'LDCC 2776', style: 'arm-classic' },
    ],
  },
  {
    // Additional Lights: ÖRNEK kategori ve model (LD 233 dekoratif işaret lambası); gerçek ek lamba grupları sonra eklenecek
    id: 'extra',
    min: 0,
    max: 4,
    step: 2,
    color: '#e0322d',
    products: [{ id: 'ld233', code: 'LD 233', style: 'strip' }],
  },
];

export const categoryById = (id: CategoryId) => CATEGORIES.find((c) => c.id === id)!;
export const productById = (cat: CategoryId, id: string) =>
  categoryById(cat).products.find((p) => p.id === id) ?? categoryById(cat).products[0];

export interface LampChoice {
  product: string;
  qty: number;
}

export interface Config {
  trailer: TrailerId;
  socket: SocketId;
  length: LengthId;
  lamps: Record<CategoryId, LampChoice>;
}

export const DEFAULT_CONFIG: Config = {
  trailer: 'standart',
  socket: '7x2',
  length: '13.6',
  lamps: {
    stop: { product: 'lzd3049', qty: 2 },
    side: { product: 'ld2774', qty: 8 },
    plate: { product: 'ltd2834', qty: 2 },
    front: { product: 'ld364', qty: 2 },
    arm: { product: 'ld2994', qty: 2 },
    extra: { product: 'ld233', qty: 0 },
  },
};

/** Seçimleri kurallara uydurur (uzunluk dorse tipine uygun mu, adetler sınırda mı). */
export function normalize(c: Config): Config {
  const t = TRAILERS.find((x) => x.id === c.trailer) ?? TRAILERS[0];
  const length = t.lengths.includes(c.length) ? c.length : t.lengths[0];
  const socket = SOCKETS.includes(c.socket) ? c.socket : '7x2';
  const lamps = {} as Config['lamps'];
  for (const cat of CATEGORIES) {
    const cur = c.lamps[cat.id] ?? DEFAULT_CONFIG.lamps[cat.id];
    const product = cat.products.some((p) => p.id === cur.product) ? cur.product : cat.products[0].id;
    let qty = Math.round(Number(cur.qty) || 0);
    qty = Math.max(cat.min, Math.min(cat.max, qty));
    qty = cat.min + Math.round((qty - cat.min) / cat.step) * cat.step;
    lamps[cat.id] = { product, qty };
  }
  return { trailer: t.id, socket, length, lamps };
}

// --- adres satırı (paylaşılabilir bağlantı) ---
export function toQuery(c: Config): string {
  const p = new URLSearchParams();
  p.set('t', c.trailer);
  p.set('s', c.socket);
  p.set('l', c.length);
  for (const cat of CATEGORIES) p.set(cat.id, `${c.lamps[cat.id].product}.${c.lamps[cat.id].qty}`);
  return p.toString();
}

export function fromQuery(q: string): Config {
  const p = new URLSearchParams(q);
  const c: Config = structuredClone(DEFAULT_CONFIG);
  if (p.get('t')) c.trailer = p.get('t') as TrailerId;
  if (p.get('s')) c.socket = p.get('s') as SocketId;
  if (p.get('l')) c.length = p.get('l') as LengthId;
  for (const cat of CATEGORIES) {
    const v = p.get(cat.id);
    if (!v) continue;
    const [product, qty] = v.split('.');
    c.lamps[cat.id] = { product, qty: Number(qty) };
  }
  return normalize(c);
}
