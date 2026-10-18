# Ekran görüntüsü / geçiş testleri (Playwright)

Dev sunucusu açıkken (`npm run dev`) çalışır; `window.__engine` yalnız dev'de var. Playwright projeye bağlı değil, ayrı klasörde kurulur:

```bash
mkdir -p ~/pw && cd ~/pw && npm init -y && npm i playwright && npx playwright install chromium
cp <repo>/tools/shots/*.mjs .
node shots.mjs out silo 12 --only=overview,rear34_low,system_mid   # tip, uzunluk, pozlar (--system tüm tesisat pozları)
node cycle.mjs                                                       # 5 tip arası geçiş; ara durum ve konsol hataları
```

SwiftShader (yazılım GL) kullanır; her poz ~1-2 dk sürebilir. `URL=` ortam değişkeni sunucu adresini değiştirir (varsayılan 127.0.0.1:4321).
