import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Statik çıktı. Etkileşimli parçalar (arama, ürün listesi, teklif listesi) Preact "island" olarak yüklenir.
export default defineConfig({
  integrations: [preact()],
  devToolbar: { enabled: false },
});
