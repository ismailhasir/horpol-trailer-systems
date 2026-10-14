# Horpol Trailer Systems · 3D Konfigüratör

Dorse aydınlatma setini seçerken ürünleri trailer üzerinde canlı 3D olarak gösteren konfigüratör.

```bash
npm install
npm run dev        # geliştirme sunucusu
npm test           # birim testler
npm run build      # tip kontrolü + üretim çıktısı (dist/)
```

## Yapı

| Yol | Ne var |
|---|---|
| `src/config/catalog.ts` | Tüm seçenekler: dorse tipleri, soketler, set uzunlukları, lamba kategorileri ve ürünler. Yeni seçenek = bu dosyaya bir satır. |
| `src/state/` | Seçim durumu; bağımlılıksız küçük store (React panelleri ve 3D sahne aynı store'u dinler). |
| `src/order/` | Sipariş özeti metni ve gönderimi (`send.ts`). |
| `src/scene/` | three.js sahnesi (`TrailerScene.ts`) ve saf yerleşim hesapları (`layout.ts`). |
| `src/components/` | Sol panel, sağ panel, sipariş özeti, lazy yüklenen 3D görüntüleyici. |

## Performans kararları

- **Sürekli render döngüsü yok.** Sahne yalnızca seçim, kamera hareketi ya da boyut değişince çizilir; boşta GPU kullanımı sıfır.
- **Instancing.** Lambalar ve tekerlekler kategori başına tek draw call; adet değişince sadece matrisler güncellenir.
- **Geometri yeniden üretilmez.** Dorse boyu değişince birim kutular ölçeklenir.
- **three.js ayrı chunk + modulepreload.** Paneller hemen etkileşime açılır, 3D motor paralel iner.
- **React sahneyi render etmez.** 3D sahne store'a doğrudan abone; seçim değişince React ağacı sahneyi yeniden kurmaz.
- Gölge haritası yok (zemin gölgesi tek gradient doku), DPR en fazla 2, yanık lambalar ışıktan bağımsız ucuz materyal.

## Sipariş gönderimi

Hedef henüz netleşmedi. `.env.example`'a bakın: `VITE_ORDER_ENDPOINT` tanımlıysa sipariş JSON olarak oraya POST edilir, değilse e-posta istemcisi sipariş metniyle açılır (`VITE_ORDER_EMAIL`).

## Durum

Dorse ve lambalar şimdilik yer tutucu geometri. Sonraki adımlar: gerçek GLB lamba modelleri (Draco/Meshopt sıkıştırmalı, lazy), sipariş formu ve gönderim hedefi.
