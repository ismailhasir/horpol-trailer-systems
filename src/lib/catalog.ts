// Ürün verisini dile göre çözer ve görselleri optimize eder (derleme zamanında). Sayfalar ve üst çubuk bunu kullanır.
// Ara kablo/soket görselleri GEÇİCİDİR (eski siteden). Setler fotoğraf yerine lamba simgelerini gösterir.
import { getImage } from 'astro:assets';
import type { ImageMetadata } from 'astro';
import { products, type LampId } from '../data/products';
import { toCard, toDetail, type CardItem, type DetailItem, type Img } from './format';
import { useUi } from '../i18n/ui';
import type { Lang } from './labels';
import cableImg from '../assets/products/cable.png';
import socketImg from '../assets/products/socket.png';

const source = { cable: cableImg, socket: socketImg };
let images: Record<keyof typeof source, Img> | null = null;

// Lamba simgeleri (src/assets/lamps/<id>-off.webp) başka bir iş akışında üretiliyor; henüz olmayanlar eşleşmez,
// arayüz onların yerine yer tutucu gösterir. Glob boş dönse de derleme kırılmaz.
const iconFiles = import.meta.glob<ImageMetadata>('../assets/lamps/*-off.webp', { eager: true, import: 'default' });
// Ana sayfada gerçek ürün fotoğrafı (kullanıcının seçtiği, src/assets/products/lamps/<id>.<uzantı>); yoksa model simgesi
const photoFiles = import.meta.glob<ImageMetadata>('../assets/products/lamps/*.{png,jpg,jpeg,webp}', { eager: true, import: 'default' });
let icons: Partial<Record<LampId, Img>> | null = null;

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

async function loadIcons() {
  if (icons) return icons;
  const out: Partial<Record<LampId, Img>> = {};
  const photos = new Map<string, ImageMetadata>();
  for (const [path, meta] of Object.entries(photoFiles)) {
    const id = /([^/]+)\.(png|jpe?g|webp)$/.exec(path)?.[1];
    if (id) photos.set(id, meta);
  }
  const all = new Map<string, ImageMetadata>();
  for (const [path, meta] of Object.entries(iconFiles)) {
    const id = /([^/]+)-off\.webp$/.exec(path)?.[1];
    if (id) all.set(id, meta);
  }
  for (const [id, meta] of photos) all.set(id, meta); // fotoğraf simgenin önüne geçer
  await Promise.all(
    [...all.entries()].map(async ([key, meta]) => {
      const id = key as LampId;
      const [a, b] = await Promise.all([
        getImage({ src: meta, width: 160, format: 'webp', quality: 82 }),
        getImage({ src: meta, width: 320, format: 'webp', quality: 82 }),
      ]);
      out[id] = { src: a.src, srcset: `${a.src} 160w, ${b.src} 320w` };
    }),
  );
  icons = out;
  return out;
}

export async function loadCatalog(lang: Lang): Promise<{ cards: CardItem[]; details: DetailItem[] }> {
  const [imgs, ic] = await Promise.all([loadImages(), loadIcons()]);
  const ui = useUi(lang);
  const img = (cat: (typeof products)[number]['cat']) => (cat === 'set' ? undefined : imgs[cat]);
  return {
    cards: products.map((p) => toCard(p, lang, img(p.cat), ic)),
    details: products.map((p) => toDetail(p, lang, ui, img(p.cat), ic)),
  };
}
