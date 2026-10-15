// Ürün verisini sayfa/ada bileşenlerinin ihtiyaç duyduğu, dile göre çözülmüş biçime çevirir.
import type { Product, SpecKey } from '../data/products';
import { numberLocale, type Lang } from './labels';
import type { Ui } from '../i18n/ui';

export interface Img {
  src: string;
  srcset: string;
}
export interface CardItem {
  id: string;
  code: string;
  cat: Product['cat'];
  name: string;
  desc: string;
  img: Img;
}
export interface DetailItem extends CardItem {
  specs: { label: string; value: string }[];
}

const specLabel: Record<SpecKey, keyof Ui> = {
  socket: 'spec_socket',
  length: 'spec_length',
  voltage: 'spec_voltage',
  protection: 'spec_protection',
  pins: 'spec_pins',
};

export function toCard(p: Product, lang: Lang, img: Img): CardItem {
  return { id: p.id, code: p.code, cat: p.cat, name: p.name[lang], desc: p.desc[lang], img };
}

export function toDetail(p: Product, lang: Lang, ui: Ui, img: Img): DetailItem {
  const nf = new Intl.NumberFormat(numberLocale(lang), { maximumFractionDigits: 2 });
  return {
    ...toCard(p, lang, img),
    specs: p.specs.map((s) => ({
      label: ui[specLabel[s.k]],
      value: s.s ?? `${nf.format(s.n ?? 0)} ${s.unit ?? ''}`.trim(),
    })),
  };
}
