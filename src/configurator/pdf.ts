// Sipariş özetini PDF olarak indirir. Bağımlılık yoktur: A4 sayfa tarayıcıda canvas'ta çizilir (sayfada yüklü
// IBM Plex yazı tipleriyle, böylece TR/RU/AR karakterleri ve Arapça bağlama doğru çıkar), JPEG'e çevrilir ve
// tek sayfalık minimal bir PDF'in içine konur. PDF'te 3D görüntü yoktur, yalnızca özet. Bu modül yalnızca "PDF indir"e basılınca yüklenir.
import { summaryRows } from './summary';
import { withBase } from '../lib/url';
import type { CUi } from './i18n';
import type { Config } from './data';
import { isRtl, type Lang } from '../lib/labels';
import { loadImg, pdfFromJpegs } from '../lib/pdf-core';

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

export interface PdfInput {
  cfg: Config;
  /** aynı siparişten kaç set */
  qty: number;
  t: CUi;
  lang: Lang;
  url: string;
  siteName: string;
}

export async function downloadSummaryPdf(i: PdfInput) {
  const { cfg, t, lang } = i;
  const rtl = isRtl(lang);
  await Promise.all([
    document.fonts.load(`600 40px "IBM Plex Sans"`),
    document.fonts.load(`400 30px "IBM Plex Sans"`),
    document.fonts.load(`500 28px "IBM Plex Mono"`),
    ...(lang === 'ar' ? [document.fonts.load(`600 40px "IBM Plex Sans Arabic"`), document.fonts.load(`400 30px "IBM Plex Sans Arabic"`)] : []),
  ]).catch(() => {});

  const logo = await loadImg(withBase('/brand/logo-blue.png'));
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);
  ctx.direction = rtl ? 'rtl' : 'ltr';
  const start = rtl ? W - M : M;
  const end = rtl ? M : W - M;
  ctx.textAlign = rtl ? 'right' : 'left';
  const endAlign: CanvasTextAlign = rtl ? 'left' : 'right';

  // başlık
  if (logo) {
    const lh = 120;
    const lw = (logo.width / logo.height) * lh;
    ctx.drawImage(logo, rtl ? W - M - lw : M, M - 10, lw, lh);
  }
  ctx.fillStyle = INK;
  ctx.textAlign = endAlign;
  ctx.font = `600 54px ${FONT}`;
  ctx.fillText(t.summary_title, end, M + 62);
  ctx.fillStyle = MUTED;
  ctx.font = `400 28px ${FONT}`;
  ctx.fillText(new Intl.DateTimeFormat(lang === 'ar' ? 'ar-u-nu-latn' : lang, { dateStyle: 'long' }).format(new Date()), end, M + 106);
  ctx.textAlign = rtl ? 'right' : 'left';

  ctx.fillStyle = BRAND;
  ctx.fillRect(M, M + 150, W - 2 * M, 4);

  // özet tablosu
  const rows = summaryRows(cfg, t, lang, i.qty);
  let y = M + 290;
  const rowH = 84;
  ctx.font = `400 30px ${FONT}`;
  const labelW = Math.min(520, Math.max(300, ...rows.map((r) => ctx.measureText(r.label).width)) + 40);
  rows.forEach((r, idx) => {
    ctx.fillStyle = MUTED;
    ctx.font = `400 30px ${FONT}`;
    ctx.textAlign = rtl ? 'right' : 'left';
    ctx.fillText(r.label, start, y);
    ctx.fillStyle = INK;
    ctx.font = r.mono ? `500 30px ${MONO}` : `600 32px ${FONT}`;
    if (r.mono) ctx.direction = 'ltr';
    ctx.textAlign = rtl ? 'right' : 'left';
    ctx.fillText(r.value, rtl ? start - labelW : start + labelW, y);
    ctx.direction = rtl ? 'rtl' : 'ltr';
    ctx.fillStyle = LINE;
    ctx.fillRect(M, y + 24, W - 2 * M, 2);
    y += rowH;
    void idx;
  });

  // alt bilgi: yapılandırma bağlantısı
  ctx.fillStyle = FAINT;
  ctx.font = `400 24px ${FONT}`;
  ctx.textAlign = rtl ? 'right' : 'left';
  ctx.fillText(t.pdf_link, start, H - M - 60);
  ctx.fillStyle = BRAND;
  ctx.font = `500 22px ${MONO}`;
  ctx.direction = 'ltr';
  const maxW = W - 2 * M;
  let u = i.url;
  while (ctx.measureText(u).width > maxW && u.length > 20) u = u.slice(0, -4);
  if (u !== i.url) u += '…';
  ctx.textAlign = 'left';
  ctx.fillText(u, M, H - M - 22);

  const blob: Blob = await new Promise((res) => c.toBlob((b) => res(b!), 'image/jpeg', 0.92));
  const jpeg = new Uint8Array(await blob.arrayBuffer());
  const pdf = pdfFromJpegs([jpeg], W, H);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(pdf);
  a.download = 'horpol-siparis-ozeti.pdf';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
