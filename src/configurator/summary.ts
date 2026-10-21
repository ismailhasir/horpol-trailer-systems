// Sipariş özeti: ekran, teklif listesi ve gönderim aynı fonksiyonu kullanır (tek kaynak).
import { categoriesFor, layoutOf, productById, rulesFor, type Config } from './data';
import { categoryName, socketName, summaryLabel, trailerName, type CUi } from './i18n';
import { numberLocale, type Lang } from '../lib/labels';

export interface SummaryRow {
  label: string;
  value: string;
  mono?: boolean;
  /** soldan sağa yazılan değer (kod, "15 pin"): Arapça sayfada yönü yalıtılır, sırası bozulmaz */
  ltr?: boolean;
}

/** setQty: aynı siparişten kaç set istendiği (1 ise satır eklenmez) */
export function summaryRows(c: Config, t: CUi, lang: Lang, setQty = 1): SummaryRow[] {
  const nf = new Intl.NumberFormat(numberLocale(lang), { minimumFractionDigits: c.length === '13.6' ? 2 : 0 });
  const rows: SummaryRow[] = [
    { label: t.sum_trailer, value: trailerName(t, c.trailer) },
    { label: t.sum_socket, value: socketName(t, c.socket), ltr: true },
    { label: t.sum_length, value: `${nf.format(Number(c.length))} ${t.length_unit}` },
  ];
  const frame = rulesFor(c.trailer).plateFrame;
  for (const cat of categoriesFor(c.trailer)) {
    const ch = c.lamps[cat.id];
    // sabit plaka çerçevesi (ör. standart dorsede RTR 3366): her zaman 1 adet, ek plaka lambalarından önce
    if (cat.id === 'plate' && frame) rows.push({ label: t.sum_plate_frame, value: `1 × ${productById('plate', frame).code}`, mono: true });
    if (!ch.qty) continue;
    const pr = productById(cat.id, ch.product);
    // set: bileşenler ayrı ayrı (ör. 2 × LZD 2448 + 2 × LZD 2452)
    const lay = layoutOf(pr, ch.qty / 2);
    const value = lay && pr.set && pr.setCodes
      ? pr.set.map((id, i) => `${2 * lay.filter((x) => x === id).length} × ${pr.setCodes![i]}`).join(' + ')
      : `${ch.qty} × ${pr.code}`;
    rows.push({ label: summaryLabel(t, cat.id), value, mono: true });
  }
  if (setQty > 1) rows.push({ label: t.set_qty, value: String(setQty) });
  return rows;
}

/** Düz metin (e-posta / teklif formu için) */
export function summaryText(c: Config, t: CUi, lang: Lang, setQty = 1): string {
  return [t.summary_title, ...summaryRows(c, t, lang, setQty).map((r) => `${r.label}: ${r.value}`)].join('\n');
}

export { categoryName };
