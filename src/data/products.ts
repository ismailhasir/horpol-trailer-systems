// Ürün verisi. Sayfalar ürünleri yalnızca bu dosya üzerinden okur; ileride veri kaynağı değişirse tek nokta burası.
// SETLER (HOR-101/102/111/1001) gerçektir. Kaynak: vault `Kablolama ve Işıklandırma/Ürün Data/Set-Ürün Kaynaklar.md`
// (içerik kodları), set listeleri ve şemaları `HOR-<kod>-Liste.jpeg` / `-Diagram.jpeg` (lamba adetleri),
// `Kablolama Şeması - Yeni.md` (kablo tesisatı). Lamba renkleri/işlevleri ürün PDF'lerinden (.claude/ref/lamps).
// Set dosyası LD 2773'ü yan marker, LD 2774'ü ön lamba diye yazıyor; ürün verisine göre tersidir
// (LD 2774 turuncu yan marker, LD 2773 beyaz ön pozisyon). Burada ürün verisi esas alındı.
// Ara kablo ve soket kodları eski siteden; `specs` değerleri ÖRNEKTİR.
// EN çevirileri bizden; RU/AR metinleri yerli çevirmen onayı bekliyor.
import type { Lang } from '../lib/labels';

export type Category = 'set' | 'cable' | 'socket';
export type SpecKey = 'socket' | 'length' | 'voltage' | 'protection' | 'pins';
export interface Spec {
  k: SpecKey;
  /** Metin değer ya da sayı (+ birim). Sayılar dile göre biçimlenir. */
  s?: string;
  n?: number;
  unit?: string;
}
type T = Record<Lang, string>;

/** Setlerde kullanılan Horpol lambaları. id = simge dosyası adı (src/assets/lamps/<id>-off.webp) ve konfigüratör kimliği. */
export type LampId = 'lzd3194' | 'lzd2423' | 'ld2774' | 'ld2773' | 'ld0128' | 'ld0127' | 'ltd2834' | 'ltd229' | 'ldcc2698' | 'lrd2679' | 'ldo2660';
export interface Lamp {
  code: string;
  /** sağ eşin kodu (sol/sağ çift lambalar) */
  codeR?: string;
  name: T;
}
/** Set içindeki bir lamba satırı. qty: setteki toplam adet. */
export interface SetLamp {
  lamp: LampId;
  qty: number;
}
/** Kablo tesisatı parçası (şemadan). core: damar düzeni (ör. 7×1, ondalık noktayla; dile göre biçimlenir); len: metre. */
export interface HarnessPart {
  name: T;
  core?: string;
  len?: number;
  qty: number;
}
export interface SetContent {
  lamps: SetLamp[];
  harness: HarnessPart[];
}
export interface Product {
  id: string;
  code: string;
  cat: Category;
  name: T;
  desc: T;
  specs: Spec[];
  /** yalnızca setlerde: içerik */
  set?: SetContent;
}

const t = (tr: string, en: string, ru: string, ar: string): T => ({ tr, en, ru, ar });

// RU/AR: çevirmen onayı bekliyor.
export const lamps: Record<LampId, Lamp> = {
  lzd3194: {
    code: 'LZD 3194/AMP',
    codeR: 'LZD 3195/AMP',
    name: t('MAVIC kombine arka lamba (sol + sağ)', 'MAVIC rear combination lamp (left + right)', 'Задний комбинированный фонарь MAVIC (левый + правый)', 'مصباح خلفي متعدد الوظائف MAVIC (يسار + يمين)'),
  },
  lzd2423: { code: 'LZD 2423', name: t('LUCY yuvarlak arka lamba', 'LUCY round rear lamp', 'Круглый задний фонарь LUCY', 'مصباح خلفي دائري LUCY') },
  ld2774: { code: 'LD 2774', name: t('Yan marker lambası, turuncu', 'Side marker light, amber', 'Боковой габаритный фонарь, оранжевый', 'مصباح تحديد جانبي، برتقالي') },
  ld2773: { code: 'LD 2773', name: t('Ön pozisyon lambası, beyaz', 'Front position light, white', 'Передний габаритный фонарь, белый', 'مصباح الموضع الأمامي، أبيض') },
  ld0128: { code: 'LD 0128', name: t('Yan marker lambası, turuncu', 'Side marker light, amber', 'Боковой габаритный фонарь, оранжевый', 'مصباح تحديد جانبي، برتقالي') },
  ld0127: { code: 'LD 0127', name: t('Ön pozisyon lambası, beyaz', 'Front position light, white', 'Передний габаритный фонарь, белый', 'مصباح الموضع الأمامي، أبيض') },
  ltd2834: { code: 'LTD 2834', name: t('Plaka lambası, pozisyonlu', 'Number plate lamp with position light', 'Фонарь номерного знака с габаритом', 'مصباح لوحة الأرقام مع ضوء موضع') },
  ltd229: { code: 'LTD 229', name: t('Plaka lambası', 'Number plate lamp', 'Фонарь номерного знака', 'مصباح لوحة الأرقام') },
  ldcc2698: { code: 'LDCC 2698', name: t('Lastik kollu marker lambası', 'Rubber-arm marker light', 'Габаритный фонарь на резиновом кронштейне', 'مصباح تحديد بذراع مطاطية') },
  lrd2679: { code: 'LRD 2679', name: t('Çalışma lambası', 'Work light', 'Рабочая фара', 'مصباح عمل') },
  ldo2660: { code: 'LDO 2660', name: t('Tepe lambası, turuncu', 'Beacon light, amber', 'Проблесковый маячок, оранжевый', 'منارة تحذيرية، برتقالية') },
};

// Kablo tesisatı parçaları (RU/AR: çevirmen onayı bekliyor).
const P = {
  socketLead: t('Soket bağlantı kablosu', 'Socket lead', 'Кабель от розетки', 'كابل المقبس'),
  mainLine: t('Ana hat', 'Main line', 'Основная линия', 'الخط الرئيسي'),
  module: t('Horpol kontrol modülü', 'Horpol control module', 'Модуль управления Horpol', 'وحدة التحكم Horpol'),
  rearLine: t('Arka hat', 'Rear line', 'Задняя линия', 'الخط الخلفي'),
  sideLine: t('Yan hat', 'Side line', 'Боковая линия', 'الخط الجانبي'),
  markerBranch: t('Yan marker dalı', 'Side marker branch', 'Отвод бокового габарита', 'فرع المصباح الجانبي'),
  plateLead: t('Plaka lambası kablosu', 'Plate lamp lead', 'Кабель фонаря номерного знака', 'كابل مصباح اللوحة'),
  feedLine: t('Besleme hattı', 'Feed line', 'Питающая линия', 'خط التغذية'),
  rearBranch: t('Arka dağıtım hattı', 'Rear distribution line', 'Задняя распределительная линия', 'خط التوزيع الخلفي'),
};

// Yeni şema (kablolama-şeması yeni.jpeg): soket → 0,5 m → 16,5 m ana hat → modül → 2 × 7×1 2,5 m arka hat;
// arka lambalardan 2 × 2×0,5 17 m yan hat; yan marker dalı 600 mm; plaka 1,5 m.
const harnessNew: HarnessPart[] = [
  { name: P.socketLead, len: 0.5, qty: 1 },
  { name: P.mainLine, len: 16.5, qty: 1 },
  { name: P.module, qty: 1 },
  { name: P.rearLine, core: '7×1', len: 2.5, qty: 2 },
  { name: P.sideLine, core: '2×0.5', len: 17, qty: 2 },
  { name: P.markerBranch, len: 0.6, qty: 8 },
  { name: P.plateLead, len: 1.5, qty: 2 },
];
// HOR-1001 şeması (mevcut şema, WhatsApp 2026-10-19 14.40.12 / HOR-1001-Diagram): 7×1 ve 2×1 17 m besleme, modül, 2 m arka dağıtım.
const harness1001: HarnessPart[] = [
  { name: P.feedLine, core: '7×1', len: 17, qty: 1 },
  { name: P.feedLine, core: '2×1', len: 17, qty: 1 },
  { name: P.module, qty: 1 },
  { name: P.rearBranch, len: 2, qty: 2 },
];

const cableSpecs = (pins: string): Spec[] => [
  { k: 'pins', s: pins },
  { k: 'length', n: 3.5, unit: 'm' },
  { k: 'voltage', s: '24 V' },
];
const socketSpecs = (pins: string): Spec[] => [
  { k: 'pins', s: pins },
  { k: 'voltage', s: '24 V' },
  { k: 'protection', s: 'IP65' },
];

// Setler. Lamba adetleri set listelerinden (HOR-<kod>-Liste.jpeg) ve şemalardan; ikisi tutarlı.
// Set adları ve açıklamaları içerikten türetildi (pazarlama iddiası yok). RU/AR: çevirmen onayı bekliyor.
export const products: Product[] = [
  {
    id: 'hor101', code: 'HOR-101', cat: 'set', specs: [],
    name: t('HOR-101', 'HOR-101', 'HOR-101', 'HOR-101'),
    desc: t(
      'İki MAVIC kombine arka lamba, neon yan marker lambaları, ön pozisyon ve pozisyonlu plaka lambaları; Horpol modüllü kablo tesisatıyla.',
      'Two MAVIC rear combination lamps, neon side markers, front position lights and plate lamps with position light, with a Horpol module harness.',
      'Два задних комбинированных фонаря MAVIC, неоновые боковые габариты, передние габариты и фонари номерного знака с габаритом; проводка с модулем Horpol.',
      'مصباحان خلفيان متعددا الوظائف MAVIC، ومصابيح جانبية نيون، ومصابيح موضع أمامية، ومصابيح لوحة مع ضوء موضع؛ مع تمديدات بوحدة Horpol.',
    ),
    set: {
      lamps: [
        { lamp: 'lzd3194', qty: 2 },
        { lamp: 'ld2774', qty: 8 },
        { lamp: 'ld2773', qty: 2 },
        { lamp: 'ltd2834', qty: 2 },
      ],
      harness: harnessNew,
    },
  },
  {
    id: 'hor102', code: 'HOR-102', cat: 'set', specs: [],
    name: t('HOR-102', 'HOR-102', 'HOR-102', 'HOR-102'),
    desc: t(
      'İki MAVIC kombine arka lamba, LD 0128 yan marker, LD 0127 ön pozisyon ve LTD 229 plaka lambaları; Horpol modüllü kablo tesisatıyla.',
      'Two MAVIC rear combination lamps, LD 0128 side markers, LD 0127 front position lights and LTD 229 plate lamps, with a Horpol module harness.',
      'Два задних комбинированных фонаря MAVIC, боковые габариты LD 0128, передние габариты LD 0127 и фонари номерного знака LTD 229; проводка с модулем Horpol.',
      'مصباحان خلفيان متعددا الوظائف MAVIC، ومصابيح جانبية LD 0128، ومصابيح موضع أمامية LD 0127، ومصابيح لوحة LTD 229؛ مع تمديدات بوحدة Horpol.',
    ),
    set: {
      lamps: [
        { lamp: 'lzd3194', qty: 2 },
        { lamp: 'ld0128', qty: 8 },
        { lamp: 'ld0127', qty: 2 },
        { lamp: 'ltd229', qty: 2 },
      ],
      harness: harnessNew,
    },
  },
  {
    id: 'hor111', code: 'HOR-111', cat: 'set', specs: [],
    name: t('HOR-111', 'HOR-111', 'HOR-111', 'HOR-111'),
    desc: t(
      'Sekiz LUCY yuvarlak arka lamba, neon yan marker lambaları, ön pozisyon ve pozisyonlu plaka lambaları, iki lastik kollu marker.',
      'Eight LUCY round rear lamps, neon side markers, front position lights, plate lamps with position light and two rubber-arm markers.',
      'Восемь круглых задних фонарей LUCY, неоновые боковые габариты, передние габариты, фонари номерного знака с габаритом и два габарита на резиновых кронштейнах.',
      'ثمانية مصابيح خلفية دائرية LUCY، ومصابيح جانبية نيون، ومصابيح موضع أمامية، ومصابيح لوحة مع ضوء موضع، ومصباحا تحديد بذراع مطاطية.',
    ),
    set: {
      lamps: [
        { lamp: 'lzd2423', qty: 8 },
        { lamp: 'ld2774', qty: 8 },
        { lamp: 'ld2773', qty: 2 },
        { lamp: 'ltd2834', qty: 2 },
        { lamp: 'ldcc2698', qty: 2 },
      ],
      harness: harnessNew,
    },
  },
  {
    id: 'hor1001', code: 'HOR-1001', cat: 'set', specs: [],
    name: t('HOR-1001', 'HOR-1001', 'HOR-1001', 'HOR-1001'),
    desc: t(
      'Sekiz LUCY yuvarlak arka lamba, neon yan marker, ön pozisyon ve plaka lambaları, lastik kollu markerlar; ek olarak iki çalışma ve iki tepe lambası.',
      'Eight LUCY round rear lamps, neon side markers, front position and plate lamps, rubber-arm markers, plus two work lights and two beacons.',
      'Восемь круглых задних фонарей LUCY, неоновые боковые габариты, передние габариты и фонари номерного знака, габариты на резиновых кронштейнах, а также две рабочие фары и два маячка.',
      'ثمانية مصابيح خلفية دائرية LUCY، ومصابيح جانبية نيون، ومصابيح موضع أمامية ولوحة، ومصابيح بذراع مطاطية، إضافة إلى مصباحَي عمل ومنارتين تحذيريتين.',
    ),
    set: {
      lamps: [
        { lamp: 'lzd2423', qty: 8 },
        { lamp: 'ld2774', qty: 8 },
        { lamp: 'ld2773', qty: 2 },
        { lamp: 'ltd2834', qty: 2 },
        { lamp: 'ldcc2698', qty: 2 },
        { lamp: 'lrd2679', qty: 2 },
        { lamp: 'ldo2660', qty: 2 },
      ],
      harness: harness1001,
    },
  },
  {
    id: 'hk7', code: 'HK-7P', cat: 'cable', specs: cableSpecs('7'),
    name: t('7 Pin Ara Kablo', '7-Pin Extension Cable', 'Соединительный кабель 7 pin', 'كابل توصيل 7 دبابيس'),
    desc: t('Spiral korumalı ağır vasıta tipi bağlantı kablosu.', 'Spiral-protected heavy-duty connection cable.', 'Спиральный кабель для тяжёлой техники с защитой.', 'كابل توصيل للخدمة الشاقة بحماية حلزونية.'),
  },
  {
    id: 'hk15', code: 'HK-15P', cat: 'cable', specs: cableSpecs('15'),
    name: t('15 Pin Ara Kablo', '15-Pin Extension Cable', 'Соединительный кабель 15 pin', 'كابل توصيل 15 دبوسًا'),
    desc: t('Modern treyler bağlantısı için yüksek dayanımlı kablo.', 'High-durability cable for modern trailer connections.', 'Высокопрочный кабель для современных соединений прицепов.', 'كابل عالي المتانة لوصلات المقطورات الحديثة.'),
  },
  {
    id: 'hkebs', code: 'HK-EBS', cat: 'cable', specs: cableSpecs('EBS'),
    name: t('EBS Ara Kablo', 'EBS Extension Cable', 'Соединительный кабель EBS', 'كابل توصيل EBS'),
    desc: t('Fren ve kontrol sistemi için güvenli veri ve güç aktarımı.', 'Safe data and power transfer for brake and control systems.', 'Безопасная передача данных и питания для тормозных систем и систем управления.', 'نقل آمن للبيانات والطاقة لأنظمة الفرامل والتحكم.'),
  },
  {
    id: 'hs7', code: 'HS-7P', cat: 'socket', specs: socketSpecs('7'),
    name: t('7 Pin Soket', '7-Pin Socket', 'Разъём 7 pin', 'مقبس 7 دبابيس'),
    desc: t('Metal gövdeli ağır hizmet tipi soket.', 'Metal-body heavy-duty socket.', 'Металлический разъём для тяжёлых условий.', 'مقبس معدني للخدمة الشاقة.'),
  },
  {
    id: 'hs15', code: 'HS-15P', cat: 'socket', specs: socketSpecs('15'),
    name: t('15 Pin Soket', '15-Pin Socket', 'Разъём 15 pin', 'مقبس 15 دبوسًا'),
    desc: t('Su ve toza dayanıklı ana bağlantı soketi.', 'Main connection socket resistant to water and dust.', 'Основной разъём, защищённый от воды и пыли.', 'مقبس اتصال رئيسي مقاوم للماء والغبار.'),
  },
  {
    id: 'hsebs', code: 'HS-EBS', cat: 'socket', specs: socketSpecs('EBS'),
    name: t('EBS Soketi', 'EBS Socket', 'Разъём EBS', 'مقبس EBS'),
    desc: t('Fren elektroniği için kilitli bağlantı çözümü.', 'Locking connection solution for brake electronics.', 'Разъём с фиксацией для электроники тормозной системы.', 'حل توصيل بقفل لإلكترونيات الفرامل.'),
  },
];
