// Ürün verisini sayfa/ada bileşenlerinin ihtiyaç duyduğu, dile göre çözülmüş biçime çevirir.
import { lamps, type LampId, type Product, type SpecKey } from '../data/products';
import { numberLocale, type Lang } from './labels';
import type { Ui } from '../i18n/ui';

export interface Img {
  src: string;
  srcset: string;
}
/** Set içindeki lamba (gösterim için). icon yoksa arayüz yer tutucu çizer (simge henüz üretilmemiş olabilir). */
export interface LampView {
  id: LampId;
  code: string;
  codeR?: string;
  name: string;
  qty: number;
  icon?: Img;
}
export interface HarnessView {
  name: string;
  /** damar düzeni ve uzunluk, dile göre biçimli (ör. "7×1 · 2,5 m") */
  spec: string;
  qty: number;
}
export interface CardItem {
  id: string;
  code: string;
  cat: Product['cat'];
  name: string;
  desc: string;
  /** ürün fotoğrafı (setlerde yok: kart, lamba simgelerinden kompozisyon gösterir) */
  img?: Img;
  /** arama için ek metin (setlerde içerikteki lamba kodları ve adları) */
  keys: string;
  /** yalnızca setlerde */
  lamps?: LampView[];
}
export interface DetailItem extends CardItem {
  specs: { label: string; value: string }[];
  /** yalnızca setlerde */
  harness?: HarnessView[];
}

const specLabel: Record<SpecKey, keyof Ui> = {
  socket: 'spec_socket',
  length: 'spec_length',
  voltage: 'spec_voltage',
  protection: 'spec_protection',
  pins: 'spec_pins',
};

const numFmt = (lang: Lang) => new Intl.NumberFormat(numberLocale(lang), { maximumFractionDigits: 2 });

/** "LD 2774" → "LD 2774 LD2774": boşluksuz yazılan kodlar da eşleşsin. */
const codeKeys = (code: string) => `${code} ${code.replace(/\s+/g, '')}`;

export function toCard(p: Product, lang: Lang, img: Img | undefined, icons: Partial<Record<LampId, Img>> = {}): CardItem {
  const lampViews = p.set?.lamps.map(({ lamp, qty }): LampView => {
    const l = lamps[lamp];
    return { id: lamp, code: l.code, codeR: l.codeR, name: l.name[lang], qty, icon: icons[lamp] };
  });
  const keys = (lampViews ?? []).map((l) => `${codeKeys(l.code)} ${l.codeR ? codeKeys(l.codeR) : ''} ${l.name}`).join(' ');
  return { id: p.id, code: p.code, cat: p.cat, name: p.name[lang], desc: p.desc[lang], img, keys, lamps: lampViews };
}

export function toDetail(p: Product, lang: Lang, ui: Ui, img: Img | undefined, icons: Partial<Record<LampId, Img>> = {}): DetailItem {
  const nf = numFmt(lang);
  return {
    ...toCard(p, lang, img, icons),
    specs: p.specs.map((s) => ({
      label: ui[specLabel[s.k]],
      value: s.s ?? `${nf.format(s.n ?? 0)} ${s.unit ?? ''}`.trim(),
    })),
    harness: p.set?.harness.map((h) => ({
      name: h.name[lang],
      spec: [h.core?.replace(/\d+(?:\.\d+)?/g, (n) => nf.format(Number(n))), h.len != null ? `${nf.format(h.len)} m` : ''].filter(Boolean).join(' · '),
      qty: h.qty,
    })),
  };
}
