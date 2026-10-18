# Devam noktası (Linux makinesi, 2026-10-18 sonu)

Bu dosya, başka bir bilgisayardaki Claude Code oturumunun kaldığımız yerden devam etmesi içindir. Önce `CLAUDE.md`'yi oku.

## Durum
Konfigüratördeki **5 dorse tipinin hepsi** Blender'da betikle modellenip pişirilen GLB'dir (kodla çizilen model kalmadı):
standart (K.SBT), lowbed (K.SLS), silo (K.SSL 38), tanker (K.STB E 45), damper (K.SKS B 27).
Son commit: tüm bunları içerir. `git status` temiz olmalı (tools/shots + bu dosya yeni olabilir).

| Tip | Betik | Belge |
|---|---|---|
| standart | `tools/blender/standart_box.py` | `docs/Standart Dorse/` |
| lowbed | `tools/blender/lowbed.py` | `docs/Lowbed Dorse/` |
| silo | `tools/blender/silo.py` | `docs/Silobas Dorse/` |
| tanker | `tools/blender/tanker.py` | `docs/Tanker Dorse/` |
| damper | `tools/blender/damper.py` | `docs/Damper Dorse/` |

Ortak yardımcılar: `tools/blender/bl_common.py`. Site tarafı: `src/configurator/engine/baked.ts` (kayıt), `trailer.ts` (kurulum),
`<tip>-anchors.json` (betiğin ürettiği lamba/soket/tesisat noktaları). Sayıların tek kaynağı betikler; belgeler özet ve gerekçe.

## Kullanıcının istekleri (kalıcı)
- Modeller gerçekçi, profesyonel, çeşitli malzemeli olmalı; düz beyaz "oyuncak" görünüm reddedildi. Renk seçimi bana bırakıldı.
- **Şasinin tesisat görünümündeki doğruluğu ve görüntüsü en önemli** öncelik.
- Ölçüler Kässbohrer broşür çizimlerinden doğrulanır; belirsiz olan "doğrulanmadı" diye belgelenir. Kässbohrer görselleri/logosu/kırmızısı repoya girmez.
- Commit'i kullanıcı atar (İngilizce, tek cümle). Kapsamı onaysız büyütme.

## Bekleyen kararlar (öneri, onay yok)
- Silobas tankı doğal fırçalanmış alüminyum (referansta beyaz), damper kasası Horpol mavisi (#1c5198), tanker beyaz.
- Doğrulanmadı listeleri her belgenin 4. bölümünde (silo: tablo/çizim dingil mesafesi 7.615/7.815, boy 10.605/10.823; tanker: konikliğin bittiği yer, hacim ~47 m³ çıkıyor; damper: kasa alt kavisi, silindir bağlantıları).
- Bilinen sınırlama: gövdeye bağlı lambaların (gabari/ön) kabloları tesisat görünümünde havada; tankerde orta hatlar kirişlerin ~0,2 m üstünde.

## Olası sonraki işler
- Damper devirme animasyonu (kasa ayrı GLB), seçenekler (tente, yedek lastik).
- Standart dorseye bake_surface (toz/aşınma) uygulamak (şu an yalnız AO).
- Gizli tipler (kapalı, frigo, flatbed, stepdeck, arac, konteyner): veride duruyor, modelleri yok (standart gösterilir); kalıcı silinecekse `data.ts`, `i18n.ts`, `TrailerIcon.tsx`.
- RU/AR çeviri onayı (CLAUDE.md).

## Yeni bilgisayarda kurulum
1. `npm install`; `npm run dev` (http://localhost:4321/tr/konfigurator/). Üretilmiş GLB'ler repoda: siteyi çalıştırmak için Blender gerekmez.
2. Model değiştirmek için **Blender 5.2.2** kur ve `blender -b -P tools/blender/<tip>.py -- [--fast] [--anchors] [--preview <klasör>]` çalıştır
   (depo kökünden; `--fast` ~2-3 dk, tam kalite ~8-10 dk), sonra `npm run models:pack -- <tip>` (gltfpack, devDependency). Çıktı `tools/blender/out/` (gitignore).
3. Ekran görüntüsü/geçiş testi: `tools/shots/README.md`.
4. Tip denetimi: projede `tsc` yok; `npx -p typescript tsc --noEmit -p .` ile çalıştır.

## Referans dosyaları (repoda yok, telifli)
Ölçüm gerekirse indir (belgelerdeki bağlantılar): ürün sayfaları ve broşür PDF'leri kaessbohrer.com; her belgenin 1. bölümünde.
Çizimler piksel ölçümüyle okundu; ölçek ve elde edilen değerler belgelerin 3. bölümünde (ham ölçüm dosyaları saklanmadı).
Silobas için ek: satıcı ilanı fotoğrafları (truckscout24 ts-213-65-457), seri kataloğu PDF.

## Teknik tuzaklar (öğrenilenler)
- Tekrarlanan dokulu büyük yüzeylerde (silo tankı) AO ikinci UV'de (`uv1`); `trailer.ts → mergeByMaterial` uv1'i korumalı, yoksa tank siyah görünür.
- Aynı malzeme iki pişirme hedefinde olmamalı (`bake_ao` "UYARI" yazar); ayrı malzeme adı ver.
- Geniş metal yüzeyde iki boyutlu pürüzlülük lekesi yansımada dalga yapar: yalnız boyuna fırça izi (`tank_metal_tile`).
- Dev sunucusu eski çıktıyı önbellekten verebilir: yeniden başlat.
