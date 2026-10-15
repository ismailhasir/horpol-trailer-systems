# Horpol Trailer Systems

Horpol dorse aydınlatma setleri için **3D konfigüratör + kurumsal site**. Kullanıcı seçtiği lambaları eş zamanlı 3D olarak dorse üzerinde görür, sipariş özetiyle siparişi gönderir. Birinci öncelik: UX'ten taviz vermeden mümkün olduğunca performanslı yapı.

## Oturum protokolü (önce bunu yap)
Kullanıcı "dün bıraktığımız yerden devam edelim" ya da "devam" derse:
1. Vault'taki `Devam Noktası.md` ve en son `Günlük/<tarih>.md` notunu oku.
2. **5 satırda** özetle: neredeyiz, son ne yapıldı, sıradaki adım, bekleyen sorular.
3. Sıradaki adımı öner, onay iste. Kod/dosya değiştirmeden önce `git status` bak.

Gün sonunda ("günü kapat") ya da büyük iş bitince: `Günlük/<tarih>.md` yaz, `Devam Noktası.md`'yi güncelle, yeni kararları `02 - Kararlar.md`'ye ADR olarak işle.

## Dökümantasyon (Obsidian vault)
`C:\Users\DidebanGrafik\OneDrive\Desktop\Dideban Otomotiv\Horpol Trailer Systems\`
(Windows güncellemesinden sonra Masaüstü OneDrive'a taşındı: notlar ve eski proje paketleri `C:\Users\DidebanGrafik\OneDrive\Desktop\` altında. `C:\Users\DidebanGrafik\Desktop\` altında yalnızca boş kopyalar var.)
**Çalışma deposu (2026-10-15'ten itibaren):** `C:\Users\DidebanGrafik\Documents\GitHub\horpol-trailer-systems` (OneDrive dışında, yeni klon). `OneDrive\Belgeler\GitHub\horpol-trailer-systems` eski kopya, kullanma.
Giriş: `Devam Noktası.md` → `Dökümantasyon Wiki.md`. Kararlar: `02 - Kararlar.md`. Plan: `06 - Planlama ve Yol Haritası.md`. Yığın: `09 - Teknoloji Yığını.md`.

## Kurallar
- Türkçe konuş. Kısa, net, dürüst ol; doğrulamadığını "doğrulanmadı" diye işaretle. Kullanıcı Astro'ya yeni: kavramları basit anlat.
- **Commit'i kullanıcı atar.** Commit mesajları İngilizce, tek cümle. Sistem yolunda `git` olmayabilir: GitHub Desktop'ın içindeki `git.exe` (`%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`).
- Şifre/anahtar girme; indirme, gönderme, yayınlama öncesi sor.
- Kaynak koda e-posta, sır, anahtar yazma.
- "Önerilen" ile "Kabul edilen" kararları ayır; kullanıcı onaylamadan ADR'yi "Kabul"e çekme.
- Kapsamı kullanıcı onayı olmadan büyütme.
- Eski projeler (`Desktop\Horpol_Trailer_Systems_*`) yalnızca ilham: kod taşıma. WAS'ın modelleri/görselleri kopyalanmaz.
- Renkleri token'lardan al, ham renk yazma. Mantıksal CSS özellikleri (`inline-start`).
- Repo yolunu kısa tut (Windows 260 karakter sınırı npm'i bozabilir).
- Yeni 3D/JS bağımlılığı eklemeden önce bütçeye etkisini ölç (bkz. vault `08 - 3D Performans ve Kalite Stratejisi.md`).

## Teknik kurallar (statik site, kodlandı 2026-10-15)
- Komutlar: `npm install`, `npm run dev` (http://localhost:4321/tr/), `npm run build`. Astro 7, **Preact 10** (11 uyumsuz).
- Sayfalar ürün verisini yalnızca `src/data/products.ts` + `src/lib/catalog.ts` üzerinden okur.
- Yeni arayüz metni: `src/i18n/ui.ts` içinde **4 dile birden** (tr, en, ru, ar). RU/AR çevirmen onayı bekliyor.
- Renkler yalnızca `src/styles/global.css` başındaki token'lardan. Arapça için `left/right` yok, mantıksal özellikler.
- İletişim bilgileri gerçek (kullanıcı verdi), sosyal medya adresleri yer tutucu; hepsi yalnızca `src/config/site.ts`. Bilinmeyen iş bilgisini (rakam, süre, iddia) uydurma.
- Ürün görselleri ve hero görseli **geçici**; yenileri `src/assets/` altına konur, `getImage` ile optimize edilir.
- Yazı tipleri: IBM Plex (`@fontsource`, `400.css` biçimi: `unicode-range` içerir). Alt küme dosyalarını (`latin-400.css`) kullanma.
- Teklif listesi anahtarı `horpol.quote.v1` (`src/lib/cart.ts`). Ada bileşenleri arası haberleşme `hts:*` olaylarıyla.
- Dev sunucusu Windows'ta bazen eski çıktıyı önbellekten verir: sunucuyu yeniden başlat.

## Teknik özet (3D ve sonrası: öneri, onay bekliyor; kesin liste vault'ta)
Düz three.js (R3F yok), GLB + Meshopt + KTX2, anchor tabanlı yerleşim, saf-veri konfigürasyon (Zod), Cloudflare Pages/D1, Vitest + Playwright + Lighthouse CI.
