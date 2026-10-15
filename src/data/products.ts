// Ürün verisi (geçici). Sayfalar ürünleri yalnızca bu dosya üzerinden okur; ileride veri kaynağı değişirse tek nokta burası.
// Kodlar eski siteden alındı. Açıklamalar eski siteden, EN/RU/AR çevirileri yerli çevirmen onayı bekliyor.
// `specs` değerleri ÖRNEKTİR, gerçek teknik veriler gelince değiştirilecek.
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
export interface Product {
  id: string;
  code: string;
  cat: Category;
  name: T;
  desc: T;
  specs: Spec[];
}

const t = (tr: string, en: string, ru: string, ar: string): T => ({ tr, en, ru, ar });

const setSpecs: Spec[] = [
  { k: 'socket', s: '7x2 / 15 pin' },
  { k: 'length', n: 13.6, unit: 'm' },
  { k: 'voltage', s: '24 V' },
  { k: 'protection', s: 'IP67' },
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

export const products: Product[] = [
  {
    id: 'hor100', code: 'HOR-100', cat: 'set', specs: setSpecs,
    name: t('Standart Dorse Aydınlatma Seti', 'Standard Semi-Trailer Lighting Set', 'Комплект освещения для стандартного полуприцепа', 'طقم إضاءة لنصف المقطورة القياسية'),
    desc: t('13,6 m treylerler için eksiksiz aydınlatma ve ana tesisat çözümü.', 'Complete lighting and main wiring solution for 13.6 m trailers.', 'Полное решение по освещению и основной проводке для 13,6-метровых прицепов.', 'حل متكامل للإضاءة والتمديدات الرئيسية للمقطورات بطول 13.6 م.'),
  },
  {
    id: 'hor110', code: 'HOR-110', cat: 'set', specs: setSpecs,
    name: t('ADR Uyumlu Dorse Seti', 'ADR-Compliant Trailer Set', 'Комплект для полуприцепа ADR', 'طقم لنصف المقطورة المتوافق مع ADR'),
    desc: t('Tehlikeli madde taşımacılığına uygun konnektör ve tesisat mimarisi.', 'Connector and wiring architecture suited to dangerous-goods transport.', 'Разъёмы и схема проводки для перевозки опасных грузов.', 'منظومة وصلات وتمديدات مناسبة لنقل البضائع الخطرة.'),
  },
  {
    id: 'hor120', code: 'HOR-120', cat: 'set', specs: setSpecs,
    name: t('Tenteli Treyler Seti', 'Curtainside Trailer Set', 'Комплект для тентованного полуприцепа', 'طقم لمقطورة بستائر جانبية'),
    desc: t('Tenteli ve kayar perdeli dorseler için montaja hazır sistem.', 'Ready-to-install system for curtainside and sliding-curtain trailers.', 'Готовая к монтажу система для тентованных и шторных полуприцепов.', 'نظام جاهز للتركيب للمقطورات ذات الستائر الجانبية والمنزلقة.'),
  },
  {
    id: 'hor130', code: 'HOR-130', cat: 'set', specs: setSpecs,
    name: t('Frigo Treyler Seti', 'Refrigerated Trailer Set', 'Комплект для рефрижераторного полуприцепа', 'طقم لمقطورة مبرّدة'),
    desc: t('Soğuk zincir treylerleri için dayanıklı, sızdırmaz aydınlatma paketi.', 'Durable, sealed lighting package for cold-chain trailers.', 'Прочный герметичный комплект освещения для рефрижераторов.', 'حزمة إضاءة متينة ومحكمة الإغلاق لمقطورات سلسلة التبريد.'),
  },
  {
    id: 'hor140', code: 'HOR-140', cat: 'set', specs: setSpecs,
    name: t('Damper Dorse Seti', 'Tipper Trailer Set', 'Комплект для самосвального полуприцепа', 'طقم لمقطورة قلّابة'),
    desc: t('Titreşimli ve zorlu saha koşullarına uygun ağır hizmet çözümü.', 'Heavy-duty solution for vibration and tough field conditions.', 'Усиленное решение для вибраций и тяжёлых условий эксплуатации.', 'حل شديد التحمل للاهتزازات وظروف العمل القاسية.'),
  },
  {
    id: 'hor150', code: 'HOR-150', cat: 'set', specs: setSpecs,
    name: t('Lowbed Seti', 'Lowbed Trailer Set', 'Комплект для низкорамного трала', 'طقم لمقطورة منخفضة (لوبد)'),
    desc: t('Uzun ve özel ölçülü lowbed uygulamalarına göre hazırlanmış sistem.', 'System prepared for long and special-size lowbed applications.', 'Система для длинных и нестандартных низкорамных тралов.', 'نظام مُعدّ لتطبيقات المقطورات المنخفضة الطويلة وذات المقاسات الخاصة.'),
  },
  {
    id: 'hor160', code: 'HOR-160', cat: 'set', specs: setSpecs,
    name: t('Konteyner Taşıyıcı Set', 'Container Chassis Set', 'Комплект для контейнеровоза', 'طقم لشاسيه نقل الحاويات'),
    desc: t('Konteyner şasileri için kompakt, modüler elektrik tesisatı.', 'Compact, modular electrical wiring for container chassis.', 'Компактная модульная электропроводка для контейнерных шасси.', 'تمديدات كهربائية مدمجة ومعيارية لشاسيهات الحاويات.'),
  },
  {
    id: 'hor170', code: 'HOR-170', cat: 'set', specs: setSpecs,
    name: t('Tanker Aydınlatma Seti', 'Tanker Lighting Set', 'Комплект освещения для цистерны', 'طقم إضاءة للصهريج'),
    desc: t('Tanker gövde yapısına uygun çevresel işaretleme ve bağlantılar.', 'Perimeter marking and connections suited to tanker bodies.', 'Контурная маркировка и соединения для кузовов цистерн.', 'إشارات محيطية ووصلات مناسبة لهياكل الصهاريج.'),
  },
  {
    id: 'hor180', code: 'HOR-180', cat: 'set', specs: setSpecs,
    name: t('Römork Seti', 'Trailer Set', 'Комплект для прицепа', 'طقم للمقطورة'),
    desc: t('Orta ve ağır sınıf römorklar için pratik tak-çalıştır sistem.', 'Practical plug-and-play system for medium and heavy trailers.', 'Практичная система plug-and-play для средних и тяжёлых прицепов.', 'نظام عملي جاهز للتوصيل للمقطورات المتوسطة والثقيلة.'),
  },
  {
    id: 'hor190', code: 'HOR-190', cat: 'set', specs: setSpecs,
    name: t('Özel Proje Seti', 'Custom Project Set', 'Комплект под проект', 'طقم لمشروع خاص'),
    desc: t('Şasi ölçüsüne ve fonksiyonlara göre projelendirilen özel çözüm.', 'Custom solution engineered to chassis size and functions.', 'Индивидуальное решение под размеры шасси и функции.', 'حل مخصص يُصمَّم وفق مقاس الشاسيه والوظائف.'),
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
