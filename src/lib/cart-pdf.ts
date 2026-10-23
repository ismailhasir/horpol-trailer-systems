// Ana sayfadaki teklif listesini (sepet) PDF olarak indirir. Görünüm konfigüratör PDF'iyle aynıdır
// (logo, başlık, tarih, mavi çizgi, ince çizgili tablo); liste uzunsa birden çok sayfa olur.
// Yalnızca "PDF indir"e basılınca yüklenir.
import type { Ui } from '../i18n/ui';
import { isRtl, type Lang } from './labels';
import { loadImg, pdfFromJpegs, saveBlob } from './pdf-core';
import { withBase } from './url';

const W = 1240; // A4 @150 dpi
const H = 1754;
const M = 90;
const INK = '#0d1b30';
const MUTED = '#475870';
const FAINT = '#6f7d93';
const LINE = '#d6e0ed';
const BRAND = '#1c5198';
const FONT = '"IBM Plex Sans", "IBM Plex Sans Arabic", system-ui, sans-serif';
const MONO = '"IBM Plex Mono", ui-monospace, monospace';

export interface CartPdfLine {
  code: string;
  name: string;
  qty: number;
}
export interface CartPdfInput {
  lines: CartPdfLine[];
  /** sipariş adedi (listedeki tüm ürünleri çarpar) */
  mult: number;
  ui: Ui;
  lang: Lang;
}

export async function downloadCartPdf(i: CartPdfInput) {
  const { ui, lang, mult } = i;
  const rtl = isRtl(lang);
  await Promise.all([
    document.fonts.load(`600 40px "IBM Plex Sans"`),
    document.fonts.load(`400 30px "IBM Plex Sans"`),
    document.fonts.load(`500 28px "IBM Plex Mono"`),
    ...(lang === 'ar' ? [document.fonts.load(`600 40px "IBM Plex Sans Arabic"`), document.fonts.load(`400 30px "IBM Plex Sans Arabic"`)] : []),
  ]).catch(() => {});
  const logo = await loadImg(withBase('/brand/logo-blue.png'));

  const pages: HTMLCanvasElement[] = [];
  let ctx!: CanvasRenderingContext2D;
  let y = 0;
  const end = rtl ? M : W - M;
  const endAlign: CanvasTextAlign = rtl ? 'left' : 'right';
  const startAlign: CanvasTextAlign = rtl ? 'right' : 'left';
  const sx = (off: number) => (rtl ? W - M - off : M + off); // başlangıç kenarından off kadar içeride
  const dir = () => (ctx.direction = rtl ? 'rtl' : 'ltr');

  const newPage = (first: boolean) => {
    const c = document.createElement('canvas');
    c.width = W;
    c.height = H;
    pages.push(c);
    ctx = c.getContext('2d')!;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, W, H);
    dir();
    if (logo) {
      const lh = first ? 120 : 70;
      const lw = (logo.width / logo.height) * lh;
      ctx.drawImage(logo, rtl ? W - M - lw : M, M - 10, lw, lh);
    }
    ctx.fillStyle = INK;
    ctx.textAlign = endAlign;
    if (first) {
      ctx.font = `600 54px ${FONT}`;
      ctx.fillText(ui.cart_title, end, M + 62);
      ctx.fillStyle = MUTED;
      ctx.font = `400 28px ${FONT}`;
      ctx.fillText(new Intl.DateTimeFormat(lang === 'ar' ? 'ar-u-nu-latn' : lang, { dateStyle: 'long' }).format(new Date()), end, M + 106);
      ctx.fillStyle = BRAND;
      ctx.fillRect(M, M + 150, W - 2 * M, 4);
      y = M + 250;
    } else {
      ctx.font = `600 36px ${FONT}`;
      ctx.fillText(ui.cart_title, end, M + 40);
      ctx.fillStyle = BRAND;
      ctx.fillRect(M, M + 90, W - 2 * M, 4);
      y = M + 170;
    }
    // sütun başlıkları
    ctx.fillStyle = FAINT;
    ctx.font = `600 22px ${FONT}`;
    ctx.textAlign = startAlign;
    ctx.fillText(ui.pdf_col_code.toUpperCase(), sx(0), y);
    ctx.fillText(ui.pdf_col_name.toUpperCase(), sx(250), y);
    ctx.textAlign = endAlign;
    ctx.fillText(ui.pdf_col_qty.toUpperCase(), end, y);
    ctx.fillStyle = LINE;
    ctx.fillRect(M, y + 18, W - 2 * M, 2);
    y += 70;
  };

  newPage(true);
  const nameW = W - 2 * M - 250 - 220;
  const wrap = (text: string, max: number) => {
    const words = text.split(/\s+/);
    const out: string[] = [];
    let cur = '';
    for (const w of words) {
      const t = cur ? `${cur} ${w}` : w;
      if (cur && ctx.measureText(t).width > max) {
        out.push(cur);
        cur = w;
      } else cur = t;
    }
    if (cur) out.push(cur);
    return out.slice(0, 3);
  };

  const limit = H - M - 150;
  for (const l of i.lines) {
    ctx.font = `400 30px ${FONT}`;
    const nameLines = wrap(l.name, nameW);
    const rowH = Math.max(84, nameLines.length * 40 + 44);
    if (y + rowH > limit) newPage(false);
    // kod (her zaman soldan sağa yazılır)
    ctx.fillStyle = INK;
    ctx.font = `500 30px ${MONO}`;
    ctx.direction = 'ltr';
    ctx.textAlign = rtl ? 'right' : 'left';
    ctx.fillText(l.code, sx(0), y);
    dir();
    // ürün adı
    ctx.fillStyle = MUTED;
    ctx.font = `400 30px ${FONT}`;
    ctx.textAlign = startAlign;
    nameLines.forEach((t, k) => ctx.fillText(t, sx(250), y + k * 40));
    // adet
    ctx.fillStyle = INK;
    ctx.font = `600 32px ${FONT}`;
    ctx.textAlign = endAlign;
    ctx.direction = 'ltr';
    ctx.fillText(mult > 1 ? `${l.qty} × ${mult} = ${l.qty * mult}` : String(l.qty), end, y);
    dir();
    ctx.fillStyle = LINE;
    ctx.fillRect(M, y + rowH - 40, W - 2 * M, 2);
    y += rowH;
  }

  // toplamlar
  const sum = i.lines.reduce((a, l) => a + l.qty, 0) * mult;
  if (y + 190 > H - M - 60) newPage(false);
  y += 24;
  const totals: [string, string][] = [];
  if (mult > 1) totals.push([ui.order_qty, String(mult)]);
  totals.push([ui.pdf_total, String(sum)]);
  for (const [label, value] of totals) {
    ctx.fillStyle = MUTED;
    ctx.font = `400 30px ${FONT}`;
    ctx.textAlign = startAlign;
    ctx.fillText(label, sx(0), y);
    ctx.fillStyle = INK;
    ctx.font = `600 34px ${FONT}`;
    ctx.textAlign = endAlign;
    ctx.direction = 'ltr';
    ctx.fillText(value, end, y);
    dir();
    y += 70;
  }

  // alt bilgi: site adı ve sayfa numarası
  pages.forEach((c, n) => {
    const g = c.getContext('2d')!;
    g.direction = 'ltr';
    g.fillStyle = FAINT;
    g.font = `400 24px ${FONT}`;
    g.textAlign = 'left';
    g.fillText(ui.site_name, M, H - M);
    if (pages.length > 1) {
      g.textAlign = 'right';
      g.fillText(`${n + 1} / ${pages.length}`, W - M, H - M);
    }
  });

  const jpegs: Uint8Array[] = [];
  for (const c of pages) {
    const blob: Blob = await new Promise((res) => c.toBlob((b) => res(b!), 'image/jpeg', 0.92));
    jpegs.push(new Uint8Array(await blob.arrayBuffer()));
  }
  saveBlob(pdfFromJpegs(jpegs, W, H), 'horpol-teklif-listesi.pdf');
}
