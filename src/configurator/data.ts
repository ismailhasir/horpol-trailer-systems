// Konfigüratör verisi: dorse tipleri, soketler, uzunluklar ve lamba katalogu.
// Lamba ürünleri vault'taki ürün listesidir (Kablolama ve Işıklandırma/Ürün Data/Ürün Listesi.md, tek doğru kaynak; 2026-10-21).
// 3D modeli olmayan ürünler (STEP bekleniyor) sahnede yer tutucuyla, panelde sönük lamba çizgili kartla görünür.
// Kurallar tests/data.test.mjs ile korunur (npm test).
// Adet tavanları kurala ve fiziksel yuvaya dayalı önerimizdir, satış ekibiyle doğrulanacak.

export type TrailerId =
  | 'standart'
  | 'kapali'
  | 'frigo'
  | 'flatbed'
  | 'stepdeck'
  | 'lowbed'
  | 'damper'
  | 'tanker'
  | 'silo'
  | 'arac'
  | 'konteyner';

export type SocketId = '7x2' | '15' | '7x2+15';
export type LengthId = '13.6' | '12' | '9';
export type CategoryId = 'stop' | 'side' | 'plate' | 'front' | 'arm' | 'work' | 'beacon';

export interface TrailerDef {
  id: TrailerId;
  /** izin verilen set uzunlukları */
  lengths: LengthId[];
  /** listede gösterilmez (model kodda hazır, ileride açılabilir) */
  hidden?: boolean;
}

// Sıra = konfigüratör listesindeki sıra: en çok istenen altı tip en üstte.
// Silobas uzunlukları ÖRNEK (doğrulanmadı), satış ekibiyle kesinleşecek.
export const TRAILERS: TrailerDef[] = [
  { id: 'standart', lengths: ['13.6', '12', '9'] },
  { id: 'frigo', lengths: ['13.6', '12'], hidden: true },
  { id: 'lowbed', lengths: ['13.6', '12'] },
  { id: 'silo', lengths: ['12', '9'] },
  { id: 'tanker', lengths: ['13.6', '12', '9'] },
  { id: 'damper', lengths: ['12', '9'] },
  { id: 'kapali', lengths: ['13.6', '12', '9'], hidden: true },
  { id: 'flatbed', lengths: ['13.6', '12', '9'], hidden: true },
  { id: 'stepdeck', lengths: ['13.6', '12'], hidden: true },
  { id: 'arac', lengths: ['13.6'], hidden: true },
  { id: 'konteyner', lengths: ['13.6', '12'], hidden: true },
];
/** Konfigüratör listesinde görünen tipler */
export const TRAILER_LIST = TRAILERS.filter((t) => !t.hidden);

export const SOCKETS: SocketId[] = ['7x2', '15', '7x2+15'];
export const LENGTHS: LengthId[] = ['13.6', '12', '9'];
export const lengthMeters = (l: LengthId) => Number(l);

/**
 * Lamba ürünü. 3D modeli tools/blender/lamps.py üretir (src/assets/models/lamp-<id>.glb); simgesi src/assets/lamps/<id>-off|on.webp.
 * codeR: sağ yandaki ayna lambanın kodu (sol/sağ çift). max: ürünün fiziksel tavanı (kategori tavanından küçükse geçerli).
 * fixed: sabit adet (seçilince bu adet; − / + yalnız 0 ile bu adet arasında geçer). Ör. plaka lambaları çift, plaka çerçevesi tek.
 */
export interface LampProduct {
  id: string;
  code: string;
  codeR?: string;
  max?: number;
  fixed?: number;
  /** yan marker: eşleşen ön pozisyon lambası (dorse kuralı frontFromSide ise ön lamba bundan seçilir) */
  front?: string;
  /**
   * set: birlikte takılan lambalar (her yanda dıştan içe bu sırayla yinelenir); setCodes: özetteki kodları. Ör. LUNA: LZD 2448
   * (pozisyon + fren + sinyal) ile LZD 2452 (pozisyon + sis + geri vites) tek başına eksik işlevli, çift olarak tam set.
   */
  set?: string[];
  setCodes?: string[];
  /** adet adımı (kategorininkinden farklıysa) */
  step?: number;
  /**
   * yanda lamba sayısına göre dizilim (dıştan içe): yalnız bu sayılar seçilebilir (toplam adet = 2 × anahtar). Ör. LUNA seti:
   * 3 → 2448, 2448, 2452; 4 → 2448, 2448, 2448, 2452
   */
  layouts?: Record<number, string[]>;
}

/** Ürünün seçilebilir toplam adetleri (dizilimli ürün: 0 ve dizilimler; yoksa null) */
export function qtyOptions(p: LampProduct): number[] | null {
  return p.layouts ? [0, ...Object.keys(p.layouts).map((k) => 2 * Number(k)).sort((a, b) => a - b)] : null;
}
/** Dizilimli üründe bir yandaki lambalar (dıştan içe) */
export function layoutOf(p: LampProduct, perSide: number): string[] | null {
  return p.layouts?.[perSide] ?? null;
}

export interface CategoryDef {
  id: CategoryId;
  /** adet: en az, en çok (genel tavan), adım. Alt sınır her kategoride 0 (kullanıcı isteği). */
  min: number;
  max: number;
  step: number;
  products: LampProduct[];
  /** sahnede ışık rengi (temsili) */
  color: string;
}

// Tavanlar (2026-10-19): arka lambalar çift (sol + sağ); büyük kombine lambalar tek çift, yuvarlak/küçük lambalar lamba
// barında her yanda 4'e (Lucy/Luna) ya da 2'ye (CUBE) kadar. Yan marker tavanı dorseye göre (sideMax); ön pozisyon ve
// plaka 2; lastik kol 4 (önde ve arkada birer çift; standart dorsede yalnız arka çift, armMax 2); çalışma ve tepe lambası 2
// (modülün boş portları ve sabit yuvalar).
export const CATEGORIES: CategoryDef[] = [
  {
    id: 'stop',
    min: 0,
    max: 8,
    step: 2,
    color: '#e0322d',
    products: [
      // tavanlar ürün ailesinden: LZD 2854 büyük kombine (tek çift), Luna (2448, 2452) her yanda 4, CUBE (2875, 2876) her
      // yanda 2. LZD 2854'ün sağ eşi LZD 2855 (ürün sayfası: "Side right").
      { id: 'lzd3194', code: 'LZD 3194/AMP', codeR: 'LZD 3195/AMP', max: 2 },
      { id: 'lzd2854', code: 'LZD 2854', codeR: 'LZD 2855', max: 2 },
      // LUNA seti (kullanıcı 2026-10-21): her yanda en az 3 (dıştan 2 × LZD 2448, en içte LZD 2452), en çok 4 (3 × LZD 2448 +
      // LZD 2452); sağda aynaları LZD 2449 / LZD 2453. Seçilebilir toplam: 0, 6, 8
      { id: 'luna', code: 'LZD 2448 + LZD 2452', codeR: 'LZD 2449 + LZD 2453', set: ['lzd2448', 'lzd2452'], setCodes: ['LZD 2448', 'LZD 2452'], max: 8,
        layouts: { 3: ['lzd2448', 'lzd2448', 'lzd2452'], 4: ['lzd2448', 'lzd2448', 'lzd2448', 'lzd2452'] } },
      { id: 'lzd2875', code: 'LZD 2875/GRAPHITE', max: 4 },
      { id: 'lzd2876', code: 'LZD 2876', max: 4 },
    ],
  },
  {
    id: 'side',
    min: 0,
    max: 20,
    step: 2,
    color: '#f5a00a',
    products: [
      // front: eşleşen ön pozisyon (revize Standart Dorse md. 10)
      { id: 'ld2774', code: 'LD 2774', front: 'ld2773' },
      { id: 'ld500', code: 'LD 500', front: 'ld499' },
    ],
  },
  {
    id: 'front',
    min: 0,
    max: 2,
    step: 2,
    color: '#f4f7ff',
    products: [
      { id: 'ld2773', code: 'LD 2773' },
      { id: 'ld499', code: 'LD 499' },
    ],
  },
  {
    id: 'plate',
    min: 0,
    max: 2,
    step: 1,
    color: '#f4f7ff',
    products: [
      // plaka lambaları plakanın iki yanında çift (çizim HOR 47); LED aydınlatmalı plaka çerçevesi (HOR 160) plakanın yerine tek.
      // LTD 669 da çift varsayıldı (montaj biçimi doğrulanmadı).
      { id: 'ltd2834', code: 'LTD 2834', fixed: 2 },
      { id: 'ltd669', code: 'LTD 669', fixed: 2 },
      { id: 'rtr3366', code: 'RTR 3366', fixed: 1 },
    ],
  },
  {
    id: 'arm',
    min: 0,
    max: 4,
    step: 2,
    color: '#f5a00a',
    products: [
      { id: 'ldcc2698', code: 'LDCC 2698' },
      { id: 'ld2994', code: 'LD 2994 Dragon' },
    ],
  },
  {
    id: 'work',
    min: 0,
    max: 2,
    step: 1,
    color: '#f4f7ff',
    products: [{ id: 'lrd2681', code: 'LRD 2681' }],
  },
  {
    id: 'beacon',
    min: 0,
    max: 2,
    step: 1,
    color: '#f5a00a',
    products: [{ id: 'ldo2660', code: 'LDO 2660' }],
  },
];

/** Dorse başına yan marker tavanı (iki yan toplamı): yan rayda çakışmasız yuva sayısı (~1,5 m'de bir). */
export const SIDE_MAX: Partial<Record<TrailerId, number>> = { standart: 20, lowbed: 18, silo: 10, tanker: 10, damper: 10 };

/**
 * Dorseye özel seçim kuralları (vault Revizeler/<Dorse>.md). hide: listede gösterilmeyen, adedi 0 tutulan kategoriler.
 * frontFromSide: ön pozisyon modeli seçilmez, yan markerın eşinden gelir (yalnız aç/kapa). plateFrame: plaka çerçevesi
 * her zaman takılı; plaka kategorisi yalnız çerçeveye ek, isteğe bağlı yan plaka lambalarıdır.
 */
export interface TrailerRules {
  hide?: CategoryId[];
  frontFromSide?: boolean;
  plateFrame?: string;
  /** plakada site adresi yazar (src/config/site.ts plateText) */
  sitePlate?: boolean;
  /**
   * arka lastik kol, lambada takma noktası (MOUNT_arm: LZD 3194, LZD 2854) yoksa kasaya değil stop lambalarının taşıyıcı
   * plakasının (tamponun) dış kenarına (montaj haritası armRearAlt). Revizeler/Standart Dorse md. 14
   */
  armOnCarrier?: boolean;
  /** lastik kol tavanı (ör. 2: yalnız arka çift, seçim 0 ya da 2) */
  armMax?: number;
  /** stop lambası → zorunlu lastik kol modeli (lambaya takılan kol; ör. LZD 3194 → LDCC 2698), panelde model seçilmez */
  armForStop?: Record<string, string>;
}
/** Bu yapılandırmada lastik kol modeli stop lambasından geliyorsa o modelin id'si */
export function lockedArm(c: Pick<Config, 'trailer' | 'lamps'>): string | undefined {
  const st = c.lamps.stop;
  return st && st.qty > 0 ? rulesFor(c.trailer).armForStop?.[st.product] : undefined;
}
export const TRAILER_RULES: Partial<Record<TrailerId, TrailerRules>> = {
  // armForStop / armMax: kullanıcı 2026-10-21 (LZD 3194'ün kol adaptörü LDCC 2698 ile; lastik kol yalnız arka çift)
  standart: { hide: ['beacon'], frontFromSide: true, plateFrame: 'rtr3366', sitePlate: true, armOnCarrier: true, armMax: 2, armForStop: { lzd3194: 'ldcc2698' } },
};
export const rulesFor = (t: TrailerId): TrailerRules => TRAILER_RULES[t] ?? {};
/** Konfigüratör listesinde bu dorse için görünen kategoriler */
export const categoriesFor = (t: TrailerId) => CATEGORIES.filter((c) => !rulesFor(t).hide?.includes(c.id));
/** Kategoride seçilebilen ürünler (sabit plaka çerçevesi seçenek değildir) */
export const productsFor = (t: TrailerId, cat: CategoryId) => {
  const ps = categoryById(cat).products;
  const frame = cat === 'plate' ? rulesFor(t).plateFrame : undefined;
  return frame ? ps.filter((p) => p.id !== frame) : ps;
};

/** Dorse modellerinin boyu (m; tools/blender/<tip>.py). R48 yan marker hesabı için. */
export const TRAILER_L: Partial<Record<TrailerId, number>> = { standart: 13.7, lowbed: 13.19, silo: 9.385, tanker: 12.41, damper: 8.84 };
/**
 * UN R48 yan marker: uzunluk > 6 m ise zorunlu; ilki önden ≤ 3 m, sonuncusu arkadan ≤ 1 m, ardışık aralık ≤ 3 m.
 * Site markerları montaj haritasındaki yan rayın (x0 … x1) boyuna eşit aralıkla dizer; açıklık SIDE_SPAN (tools/check-lighting.mjs).
 * Döner: her yanda en az kaç adet (alt sınır DEĞİL; arayüzde uyarı yok, kullanıcı isteği 2026-10-21: tools/check-lighting.mjs).
 */
const SIDE_SPAN: Partial<Record<TrailerId, number>> = { standart: 12.4, lowbed: 10.4, silo: 5.0, tanker: 6.16, damper: 5.24 };
export function sideMinPerSide(t: TrailerId): number {
  const L = TRAILER_L[t] ?? 13.6;
  if (L <= 6) return 1;
  return Math.ceil((SIDE_SPAN[t] ?? L - 1.5) / 3) + 1;
}
/** Tepe lambası yuvası (montaj haritası) kategori tavanından azsa dorseye özel tavan */
const BEACON_MAX: Partial<Record<TrailerId, number>> = {};

/** Kategorinin bu yapılandırmadaki tavanı (ürün ve dorse sınırları dahil) */
export function maxQty(c: Pick<Config, 'trailer' | 'lamps'>, cat: CategoryId): number {
  const def = categoryById(cat);
  const prod = productById(cat, c.lamps[cat]?.product ?? def.products[0].id);
  let m = Math.min(def.max, prod.fixed ?? prod.max ?? def.max);
  if (cat === 'side') m = Math.min(m, SIDE_MAX[c.trailer] ?? def.max);
  if (cat === 'arm') m = Math.min(m, rulesFor(c.trailer).armMax ?? def.max);
  if (cat === 'beacon') m = Math.min(m, BEACON_MAX[c.trailer] ?? def.max);
  return m;
}

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
    stop: { product: 'lzd3194', qty: 2 },
    side: { product: 'ld2774', qty: 12 },
    plate: { product: 'ltd2834', qty: 2 },
    front: { product: 'ld2773', qty: 2 },
    arm: { product: 'ldcc2698', qty: 2 }, // varsayılan stop LZD 3194: kolu lambaya takılı LDCC 2698
    work: { product: 'lrd2681', qty: 0 },
    beacon: { product: 'ldo2660', qty: 0 },
  },
};

/** Seçimleri kurallara uydurur (uzunluk dorse tipine uygun mu, adetler sınırda mı). */
export function normalize(c: Config): Config {
  const t = TRAILER_LIST.find((x) => x.id === c.trailer) ?? TRAILER_LIST[0];
  const length = t.lengths.includes(c.length) ? c.length : t.lengths[0];
  const socket = SOCKETS.includes(c.socket) ? c.socket : '7x2';
  const lamps = {} as Config['lamps'];
  const rules = rulesFor(t.id);
  for (const cat of CATEGORIES) {
    const cur = c.lamps[cat.id] ?? DEFAULT_CONFIG.lamps[cat.id];
    const opts = productsFor(t.id, cat.id);
    let product = opts.some((p) => p.id === cur.product) ? cur.product : opts[0].id;
    let qty = Math.round(Number(cur.qty) || 0);
    if (rules.hide?.includes(cat.id)) qty = 0;
    // ön pozisyon yan markerın eşi (yan marker ön kategoriden önce işlenir)
    if (cat.id === 'front' && rules.frontFromSide) {
      const f = productById('side', lamps.side.product).front;
      product = f && cat.products.some((p) => p.id === f) ? f : cat.products[0].id;
    }
    // lastik kol modeli stop lambasından (stop kategorisi kol kategorisinden önce işlenir)
    if (cat.id === 'arm') {
      const la = lockedArm({ trailer: t.id, lamps });
      if (la && cat.products.some((p) => p.id === la)) product = la;
    }
    // sabit çerçeveli dorseye çerçeve seçili gelirse (başka dorseden geçiş): ek plaka lambası yok
    if (cat.id === 'plate' && rules.plateFrame && cur.product === rules.plateFrame) qty = 0;
    const fixed = productById(cat.id, product).fixed;
    if (fixed) {
      qty = qty > 0 ? fixed : 0; // sabit adetli ürün: ürün değişince de adet ürüne oturur (RTR 3366 → LTD 2834: 1 → 2)
    } else {
      const pr = productById(cat.id, product);
      const step = pr.step ?? cat.step;
      const opts = qtyOptions(pr);
      qty = Math.max(cat.min, Math.min(maxQty({ trailer: t.id, lamps: { ...c.lamps, [cat.id]: { product, qty } } }, cat.id), qty));
      if (opts) qty = qty > 0 ? opts.filter((v) => v > 0).reduce((b, v) => (Math.abs(v - qty) < Math.abs(b - qty) ? v : b)) : 0;
      else qty = qty > 0 ? Math.max(step, cat.min + Math.round((qty - cat.min) / step) * step) : qty;
    }
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
