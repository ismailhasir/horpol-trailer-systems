import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Statik çıktı. Etkileşimli parçalar (arama, ürün listesi, teklif listesi) Preact "island" olarak yüklenir.
export default defineConfig({
  // Geçici önizleme (GitHub Pages, .github/workflows/pages.yml): site https://ismailhasir.github.io, kök yolu
  // /horpol-trailer-systems. Yerelde ikisi de boş: site kökte (/) çalışır. Alan adı belli olunca site buraya yazılır.
  site: process.env.SITE_URL || undefined,
  base: process.env.BASE_PATH || '/',
  integrations: [preact()],
  devToolbar: { enabled: false },
  vite: {
    // Yalnız dev: bloom modülleri ilk kez "Işıklar" açılınca dinamik yüklenir. Vite onları o an keşfedip yeniden paketliyor,
    // sayfanın istediği eski sürüm 504 (Outdated Optimize Dep) dönüyor ve bloom sessizce kapalı kalıyordu. Baştan paketlenir.
    optimizeDeps: {
      include: [
        'three/examples/jsm/postprocessing/EffectComposer.js',
        'three/examples/jsm/postprocessing/RenderPass.js',
        'three/examples/jsm/postprocessing/UnrealBloomPass.js',
        'three/examples/jsm/postprocessing/OutputPass.js',
      ],
    },
  },
});
