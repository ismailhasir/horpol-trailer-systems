// Sitenin kök yolu: yerelde "/", GitHub Pages önizlemesinde "/horpol-trailer-systems/" (astro.config base, BASE_PATH). Kökten
// başlayan bütün iç bağlantılar ve public/ dosyaları buradan geçer; Vite'ın içe aktardığı dosyalar (modeller, görseller) kök
// yolunu zaten kendisi ekler.
const BASE = import.meta.env.BASE_URL.replace(/\/+$/, '');

/** "/tr/konfigurator/" → "<kök>/tr/konfigurator/" */
export const withBase = (path: string) => `${BASE}${path.startsWith('/') ? path : `/${path}`}`;
