// Testler kaynak .ts dosyalarını doğrudan içe aktarır (Node tip ayıklama). Kaynakta uzantısız göreli importlar var
// ('./data'): bulunamazsa ".ts" eklenip yeniden denenir. Vite/Astro'ya özgü modüller (astro:assets vb.) test edilmez.
import { registerHooks } from 'node:module';

registerHooks({
  resolve(spec, ctx, next) {
    try {
      return next(spec, ctx);
    } catch (e) {
      if (spec.startsWith('.') && !/\.[cm]?[jt]sx?$/.test(spec)) return next(`${spec}.ts`, ctx);
      throw e;
    }
  },
});
