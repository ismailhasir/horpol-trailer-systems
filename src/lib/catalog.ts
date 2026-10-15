// Ürün verisini dile göre çözer ve görselleri optimize eder (derleme zamanında). Sayfalar ve üst çubuk bunu kullanır.
// Görseller GEÇİCİDİR (eski siteden); yüksek çözünürlüklü yenileriyle src/assets/products altında değiştirilecek.
import { getImage } from 'astro:assets';
import { products } from '../data/products';
import { toCard, toDetail, type CardItem, type DetailItem, type Img } from './format';
import { useUi } from '../i18n/ui';
import type { Lang } from './labels';
import setImg from '../assets/products/set.png';
import cableImg from '../assets/products/cable.png';
import socketImg from '../assets/products/socket.png';

const source = { set: setImg, cable: cableImg, socket: socketImg };
let images: Record<keyof typeof source, Img> | null = null;

async function loadImages() {
  if (images) return images;
  const out = {} as Record<keyof typeof source, Img>;
  for (const k of Object.keys(source) as (keyof typeof source)[]) {
    const [a, b] = await Promise.all([
      getImage({ src: source[k], width: 400, height: 400, format: 'webp', quality: 80 }),
      getImage({ src: source[k], width: 800, height: 800, format: 'webp', quality: 80 }),
    ]);
    out[k] = { src: a.src, srcset: `${a.src} 400w, ${b.src} 800w` };
  }
  images = out;
  return out;
}

export async function loadCatalog(lang: Lang): Promise<{ cards: CardItem[]; details: DetailItem[] }> {
  const imgs = await loadImages();
  const ui = useUi(lang);
  return {
    cards: products.map((p) => toCard(p, lang, imgs[p.cat])),
    details: products.map((p) => toDetail(p, lang, ui, imgs[p.cat])),
  };
}
