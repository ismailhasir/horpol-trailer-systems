# Lambalar (ürün 3D modelleri, ışık işlevleri, tesisat)

Konfigüratördeki lambalar gerçek Horpol ürünlerinin Blender'da betikle üretilmiş modelleridir (2026-10-19).
Kaynaklar: vault `Kablolama ve Işıklandırma/` (ürün zip'leri: teknik çizim, homologasyon, sönük ve yanık fotoğraflar; yeni kablolama
şeması; HOR-1001 şeması; set listeleri). Üretici görselleri repoya kopyalanmadı.

## 1. Üretim hattı

```bash
blender -b -P tools/blender/lamps.py -- [--only lzd3194,ld2774] [--fast] [--preview <klasör>] [--icons]
npm run models:pack -- lamp      # gltfpack; lambalarda -kn -km (düğüm ve malzeme adları korunur)
```

- `tools/blender/lamps.py`: ortak çatı (geometri yardımcıları, malzeme kütüphanesi, dokular, dışa aktarma, simge render'ı) ve LZD 3194 MAVIC.
- `tools/blender/lamps_rear.py`: LZD 2856, 2423, 2448, 2877, 2880.
- `tools/blender/lamps_small.py`: LD 2774, 2773, 2765, 0128, 0127, LTD 2834, 229.
- `tools/blender/lamps_aux.py`: LD 2994 Dragon, LDCC 2698, LRD 2679, LRD 2681 (geçici, çizimden; aynı HOR 111 gövdesi), LDO 2660.
- `tools/blender/lamps_cad.py`: üretici CAD verisinden modeller: LZD 3194, LDCC 2698, LD 2994 (bkz. bölüm 7–8). CAD STL'leri yoksa el modeline düşer.
- Çıktılar: `src/assets/models/lamp-<id>.glb` (sitede ilk kullanımda indirilir), `src/assets/lamps/<id>-off.webp` / `-on.webp` (ürün simgeleri).

## 2. GLB sözleşmesi (sitenin okuduğu)

| Düğüm | İçerik |
|---|---|
| `BODY` | opak gövde, braket, vida, kablo, fiş |
| `INNER` | opak iç parçalar: reflektör, LED kabı, köşe küp reflektör |
| `EMIT.<işlev>` | ışık veren parçalar; malzeme adı `E.<işlev>.<renk>[.<etiket>]`; paylaşılan kılavuz `E.position+stop.red` (işlevlerden biri açıksa yanar; yalnız pozisyonda sönük); `.g<yüzde>` etiketi: LED'in ışığını yansıtan krom kap, işlev şiddetinin bu oranında ışır (ör. `E.reverse.white.g33` = ×0,33) |
| `LENS` | şeffaf dış lens (`Lens.<renk>[.cad]`; `.cad`: lensin kendisi az parlar), tepe lambası kubbesi (`Dome.amber`) |

İşlevler: position, stop, turn, reverse, fog, marker, front, outline, plate, work, beacon. Renkler: red, amber, white.
Yerel eksenler (three.js, metre): lens +Z'ye bakar, X genişlik, Y yukarı, montaj yüzeyi z = 0. Sağ arka lamba sol lambanın aynasıdır.

## 3. Sitede ışıklar

`src/configurator/engine/lampfx.ts`: lamba modellerinin kaydı ve işlevlerin yakılması. Işıklar modunda kullanıcı yanan işlevleri
seçer (pozisyon, fren, sinyal, geri vites, sis, çalışma, tepe); sinyal ~1,5 Hz yanıp söner, tepe lambası 2,1 Hz çift flaş.

**Revize (2026-10-20 akşam, kullanıcı isteği: "videoda gösterilen şekle uygun olmalı"):**
- **Işığı yalnız yanan parça verir.** Yanan malzeme HDR ışır; lensin kendisi artık ışımaz. Eskiden lens de yanan işlevin renginde parlıyordu, bu yüzden işlevler birbirine karışıyordu.
- **Işıma bloom ile çizilir** (`Engine.ts`, yalnız ışıklar modunda, ilk açılışta ~19 KB dinamik yüklenir). Işıma yanan parçanın kendi biçimini izler: neon şerit homojen şerit, sinyal kaması tek parça yanar. Eski küre biçimli hale sprite'ları "arkada 4 LED var" görüntüsü veriyordu, kapatıldı (`GLOW_SPRITES`).
- **Bloom eşiği en parlak renk kanalına göre ölçülür** (luma yerine). Doygun kırmızının luması düşük olduğu için eşiği geçemiyordu. HDR > 1 yalnız yanan ışıklarda olur, gece sahnesindeki beyaz dorse ışımaz.
- **Yansıma efektleri kapalı:** zemin ışık halkaları, kırmızı nokta ışık ve çalışma lambası spotu (`LAMP_SPILL`, `GLOW_SPRITES`).
- **Şiddetler** ürün föyündeki güç oranlarını izler (MAVIC: pozisyon 2 W, fren 10 W). Pozisyon 1,45, fren 2,7, sinyal 2,6, sis 2,6, geri vites 3,0 (önce 2,5; kırmızı kılavuzların yanında sönük kalıyordu); marker, ön ve kontur 2,4–2,6; çalışma 4,5, tepe 3,6.
- **Paylaşılan kılavuz** (`E.position+stop`) en güçlü yanan işlevin şiddetinde yanar.
- **Yansıtıcı kaplar** (`.g<yüzde>`): şiddet × oran. Oranlar bloom eşiğinin altında tutulur: kap parlak ama yapısı okunur, haleyi yalnız LED verir.
- Videoyla karşılaştırma ışıklar modunda yakın planda yapıldı. Gerçek cihazda bloom maliyeti ölçülmedi; zayıf cihazda MSAA kapalı ve çözünürlük 0,75.

**Çözünürlük (kullanıcı 2026-10-23: "her zaman en iyi kalitede"):** `Engine.ts` piksel oranı her zaman ekranınki (2'de sınırlı). Eskiden yavaş karelerde kademeli düşürülüp hiç geri yükseltilmiyordu: ışıklar (bloom) açılıp kapandıktan ya da model yüklerken görüntü kalıcı olarak bulanık kalıyordu. Düşük donanım ayarları (gölge haritası 1024, bloom 0,75 çözünürlük, MSAA yok, ortam haritası 128) da kaldırıldı: her cihazda gölge 2048, bloom tam çözünürlük + 4× MSAA, ortam 256.

## 4. Tesisat (yeni Horpol şeması)

`src/configurator/engine/equipment.ts`:
- ön soket → 0,5 m → konnektör → 16,5 m ana hat (kirişlerin arası) → Horpol modülü
- modül → 2 × 7×1 2,5 m arka hat → arka lambanın AMP 7 pin fişi
- arka lambanın Superseal soketinden: 2×0,5 yan hat (yan markerlar 0,6 m dallarla, ucunda ön pozisyon), plaka lambası (1,5 m),
  arka lastik kol; ön lastik kollar yan hattın ön ucundan
- çalışma ve tepe lambaları (HOR-1001 şeması): soketten ayrı 2×1 besleme, modülün yedek portlarından
- montaj noktaları dorse betiklerinin yazdığı `mounts` (R48 montaj haritası; bkz. `docs/<Tip> Dorse/README.md`)

Kablo renkleri tesisat görünümünde eğitsel koddur, gerçek kablo renkleri değildir.

## 5. Adet tavanları (alt sınır her kategoride 0)

| Kategori | Tavan |
|---|---|
| Arka lamba | çift; MAVIC / LZD 2856: 2, CUBE: 4, LUCY / LUNA: 8 |
| Yan marker | dorseye göre (iki yan toplamı): standart 18, lowbed 18, tanker 12, silo 10, damper 10 |
| Plaka | sabit adet (`fixed`, `data.ts`): LTD 2834 ve LTD 229 çift (2), RTR 3366 çerçevesi tek (1); − / + yalnız 0 ile bu adet arasında. Ürün değişince adet ürüne oturur (eskiden RTR'den lambaya geçince 1'de kalıyordu) |
| Ön pozisyon | 2 |
| Lastik kol | 4 (önde ve arkada birer çift) |
| Çalışma lambası | 2 |
| Tepe lambası | 2 (damperde 1) |

UN R48'e göre gereken en az yan marker (her yan) arayüzde uyarı olarak gösterilir: standart 6, lowbed 5, tanker 4, silo 3, damper 3.
Bu konfigüratör tip onayı ya da mevzuat uygunluk belgesi değildir.

## 6. Ürünler

Boyutlar paketli GLB (Meshopt). Ölçüler teknik çizimlerden; "doğrulanmadı" olanlar fotoğraftan oranlandı.

| Ürün | Kategori | Ölçü (mm) | Işık işlevleri (EMIT) | Üçgen | GLB |
|---|---|---|---|---|---|
| LZD 3194/AMP MAVIC (sağ: 3195, ayna) | arka | 405 × 148 × 63; 2 × M8 (±75), 4 Superseal (±126), AMP 7 pin | position+stop (neon), stop (iç üçgen), turn, reverse, fog | 63 368 (CAD) | 523 KB |
| LZD 2856 Heavy Duty (sağ: 2857) | arka | 451 × 139 × 74; 2 × M8 (152), 8 vida | turn, stop, position (neon şevron), reverse, fog | 6 494 | 100 KB |
| LZD 2423 LUCY | arka | Ø121,4 × 33,5, paslanmaz halka Ø155 | turn, position (neon halka + 4 kol), stop | 7 128 | 96 KB |
| LZD 2448 LUNA | arka | Ø121,4 × 36,2, krom halka Ø155,6 | position, turn (D modülü), stop | 7 338 | 97 KB |
| LZD 2877 / 2880 CUBE | arka | 115 × 138 × 40,3; siyah / krom çerçeve | position, stop, turn | 7 404 | 88 / 89 KB |
| LD 2774 | yan marker | lamba 119,6 × 45,9 × 20,4; tutucu 74,9 yük. | marker (amber neon çubuk) | 5 002 | 74 KB |
| LD 2773 | ön pozisyon | LD 2774 ile aynı gövde, beyaz | front | 5 002 | 74 KB |
| LD 2765 | yan marker | 110,8 × 52,2 × 20,65; tutucu 71,8 | marker (neon çerçeve halka) | 4 698 | 75 KB |
| LD 0128 / LD 0127 | yan / ön | 132 × 33 × 13, delik arası 115 | marker / front (3 LED) | 3 484 | 73 KB |
| LTD 2834 | plaka | 93,5 × 70 × 58; 2 × M5 (46) | plate (difüzör), position (kırmızı Π neon) | 17 714 (CAD, bölüm 9) | 147 KB |
| LTD 229 | plaka | 97 × 64,7 × 62,3; 2 × M5 (46) | plate (3 LED) | 21 232 (CAD, bölüm 9) | 195 KB |
| RTR 3366 | plaka çerçevesi | 530,6 × 158,7 × 42,9 | plate (3 modül, 12 LED) | 28 566 (CAD, bölüm 9) | 282 KB |
| LD 2994 Dragon | lastik kol | uzanım 200,8, yük. 179; plaka 35 × 105 | outline: beyaz öne, kırmızı arkaya, turuncu yana | 4 272 | 71 KB |
| LDCC 2698 | lastik kol | uzanım 168,8, yük. 177, gen. 37 | outline: beyaz / kırmızı neon halka, turuncu yan | 6 176 | 90 KB |
| LRD 2679 | çalışma | 101 × 100 × 50,5; U braket, M8 | work (12 küçük + 3 büyük LED) | 7 044 | 92 KB |
| LRD 2681 (geçici) | çalışma + geri vites | LRD 2679 gövdesi (aynı çizim) | work (12 küçük), work+reverse (3 büyük; doğrulanmadı) | 7 044 | 93 KB |
| LDO 2660 | tepe | flanş Ø150,5, kubbe Ø114, yük. 122,8 | beacon (16 LED, 2,1 Hz çift flaş) | 8 095 | 96 KB |

Toplam: 17 ürün, 1,4 MB (gzip 0,9 MB); bir yapılandırmada yalnız seçilen ürünler indirilir.

**Doğrulanmadı (öne çıkanlar):**
- LZD 2856: küçük kırmızı pencerenin sis olduğu (ürün sayfasında işlev–bölüm eşlemesi yok); LED sayısı sadeleştirildi.
- LZD 2423: stop cebi başına 3 LED; LZD 2448: D modülünün yönü fotoğrafa göre (çizimle ters).
- CUBE: iç parçalar ön fotoğraftan ölçeklendi. Halkalı yuvarlak lambalar yüzeye montajlı kabul edildi (gerçekte gömme olabilir).
- LD 2774/2765/0128 tutucu delikleri ve kaburgaları, LTD 2834 yan eğimi, LTD 229 pencere ve LED yerleşimi.
- LD 2994 / LDCC 2698 kafa derinliği ve kol eğrisi; LRD 2679 ve LDO 2660 iç LED yerleşimi.
- Ürün verisi: set listelerinde LD 2773 yan marker, LD 2774 ön lamba diye geçiyor; ürün belgeleri tersini söylüyor (LD 2774 turuncu yan marker, LD 2773 beyaz ön). Sitede ürün belgesi esas.

**MAVIC fotoğraflarından öğrenilen:** gerçek pozisyon deseni üstte uzun çubuk, dış uçta "<" kıvrımı ve altta çubuk; model yaklaşık, ileride hassaslaştırılabilir.

## 7. Üretici CAD verisiyle modelleme (dal `lamp-3d-rework`, 2026-10-20)

İlk örnek **LZD 3194/AMP MAVIC**. Kaynaklar (repoya girmez): vault kökü `Dideban Otomotiv/LZD-3194AMP.zip` (ürün föyü, teknik çizim,
homologasyon, 5 işlev ayrı yanık fotoğraf, etiketli ürün videosu) ve `3d-files_2026-10-02_1139.zip` (`LZD 3194_H101_AMP_4SS.STEP`).

```bash
# 1) STEP → kabuk başına STL (FreeCAD 1.1; çıktı tools/blender/cad/lzd3194, .gitignore'da)
STEP_IN="<…>/LZD 3194_H101_AMP_4SS.STEP" STEP_OUT=tools/blender/cad/lzd3194 "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" tools/cad/step_to_stl.py
# 2) model + simgeler, 3) paketleme
blender -b -P tools/blender/lamps.py -- --only lzd3194 --icons
npm run models:pack -- lamp-lzd3194
```

**STEP'te ne var, ne yok:** STEP bir dış zarf modeli: 44 kabuk, 9 237 yüz. İçinde olanlar:
- lens (dış ve iç kabuk; iç yüzde sis optiği ve kama kenarı işlenmiş)
- gövde (altıgen nervürlü iç taban, Superseal yuvaları, M8 saplamalar, AMP rakoru, geniş uçta kablo kanalı)
- 9 lens vidası

Renk ve malzeme yok. İç optik parçalar da yok: ışık kılavuzları, LED'ler, reflektörler, geri vites yuvaları.

**Yöntem (`lamps_cad.py`):**
- CAD ekseni: x genişlik (geniş uç −x), **yukarı = −z**, lens = +y, arka düzlem y = −78 mm. Yukarı yönü arka fotoğraftaki havalandırma kapağı ile AMP rakorunun konumundan doğrulandı.
- Üçgenler 26 yönde ışın testiyle dış/iç ayrılır. Dış yüzeyde flanşın önü (yerel z > 34,5 mm) **lens**, gerisi **gövde**.
- İç yüzeyler atılır; kovuk, ölçülen lens iç kenarından kurulan taban ve duvarla kapatılır.
- Lens fasetleri düzlemsel birleştirilir. Geri vites pencereleri renksiz, kama bölgesi turuncu (bölgeler kesilerek ayrılır).
- Gövde 30 bin üçgene sadeleşir. 4SS kablo artıkları atılır.
- İç parçalar ürün fotoğraflarından ölçülür. Fotoğraf → lamba koordinatı dönüşümü, lensin ardından görünen 9 vida başının CAD konumundan (x, y, z) kurulan **3B kamera matrisiyle** (DLT) yapılır. Vida hatası en çok 4,3 px (~1 mm). İlk sürümdeki düzlemsel homografi kavisli lens yüzünde ortada 7 mm'ye kadar kaydırıyordu (bkz. revize 2).
- Parçaların derinliği lens dış yüzüne ışın atılarak bulunur, böylece kılavuzlar lensi izler.

**İşlev haritası (videodaki etiketlerden; eski el modeli yanlıştı):**
- Neon üst çubuk ile iç ve dış "<" kılavuzlar **pozisyonda** boydan boya sönük yanar.
- **Frende** yalnız büyük üçgenin sağ kenarı doğrultusunun solundaki (geniş uç) bölüm parlar; sağı (sinyal tarafı) pozisyonda kalır. Kılavuz o doğrudan ikiye bölünür: sol `E.position+stop`, sağ `E.position`.
- Frende sol iç (ters) üçgen panel de yanar.
- Sağ uçtaki 2 × 4 hücre **sis**. Eski modelde fren sanılmıştı.
- Turuncu kama **sinyal**.
- Sol üstte 2 pencere, ikişer LED: **geri vites**.
- Büyük üçgen (üstünden neon çubuk geçer) ve alt şerit: reflektör.

**Sitede:**
- Büyük ışık parçalarının halesi 6 cm'lik hücrelere bölünür (`emitterSpots`). Paylaşılan kılavuzun pozisyon halesi küçük ve zemine ışık düşürmez.
- `.cad` lens az parlar; kılavuz deseni okunur.

**Ölçüm:**
- 63 368 üçgen, paket 523 KB (gzip 379 KB). Eski el modeli: 9 652 üçgen, 110 KB.
- Sahnede 2 arka lamba var. Gerçek cihazda FPS ölçülmedi.

**Doğrulanmadı / açık:**
- Fotoğraflar LZD 2650/2651 MAVIC'in. Ön yüz aynı kabul edildi.
- İç parçaların derinlik ve kalınlıkları tahmin.
- Fren ve pozisyon parlaklık oranı görsel.
- Galeride fren fotoğrafı yok (72-dpi-3 eksik: 1 sis, 2 pozisyon, 4 sinyal, 5 pozisyon+sinyal, 6 geri vites). Fren davranışı yalnız videodan.

**Revize (2026-10-20 akşam):**
- Geri vites pencereleri lamba eksenine hizalı, simetrik biçimle yeniden kuruldu. Fotoğraftan dönüştürülen çokgen perspektif yüzünden eğiliyordu.
- **Arka lastik kol lambaya takılı.** STEP'teki geniş uç bloğu aslında kol montajı: dış uca vidalı dikey plaka (x −230…−208 mm, 2 saplama ve somun) ve plakadan dışa, ~40° yukarı çıkan delikli kol ve kafa. CAD'deki ayrı parça p000, AMP fişi değil, bu kolun kafasıdır.
- Lamba modeli plakayı ayrı `BRACKET` düğümünde ve takma noktasını boş `MOUNT_arm` düğümünde taşır.
- Sitede (`equipment.ts`): dıştaki arka lambada `MOUNT_arm` varsa seçili arka lastik kol oraya takılır ve 40° yukarı eğilir (`ARM_TILT`). Kablosu lambanın Superseal'inden gelir. `MOUNT_arm` yoksa kol montaj haritasındaki yerinde kalır.
- Lamba genişliği `BRACKET` hariç ölçülür; lamba kenara dayanır, plaka dışa taşar.
- Model 70 186 üçgen, paket 569 KB.

**Revize 2 (2026-10-20 gece): fren ve alt şeritler.** Kullanıcı bildirimi:
- Frende şeritlerin tamamı yanmıyor, büyük üçgenin hizasından başlıyordu.
- Alt iki şerit büyük üçgenin altında tek şeride dönüşüyor, sonra yeniden ikiye ayrılıyordu.

Nedenler:
- İç ve dış "<" kılavuzların alt kolları solda üst üste biniyordu: çokgenler göz kararı çizilmişti, aralarında boşluk yoktu.
- Fren üçgeni gerçeğinin yaklaşık iki katıydı ve kılavuzların arasına uzanıyordu.
- Kılavuzlar 12 mm'lik düz dilimlerden kuruluydu. Dilim sınırlarında basamak ve dikiş izi kalıyordu.
- Düzlemsel homografi kavisli lenste parçaları ortada 7 mm'ye kadar kaydırıyordu.

Düzeltme (`lamps_cad.py`):
- Kılavuz, kama, ayırıcı ve fren üçgeni kenarları pozisyon (72-dpi-2) ve sinyal (72-dpi-4) fotoğraflarında sütun/satır parlaklık profilinden piksel olarak ölçüldü. Fren üçgeni sönük fotoğraflarda (72-dpi-1/6) koyu üçgen olarak görünüyor; biçimi oradan alındı.
- Gerçek biçim kavisli: üst çubuk ve kama dar uca doğru aşağı kıvrılır, alt şeritler büyük üçgenin altında hafif eğimli gider, sağda düzleşir.
- Alt iki şerit boydan boya ayrı (~9 mm genişlik):
  - kollar arasında koyu yarık
  - büyük üçgenin altında lensteki noktalı yazı şeridi (~1,4 mm aralık + koyu noktalar)
  - sağda siyah ayırıcı (~2,5 mm)
- Fotoğraf eşlemesi 3B kamera matrisine geçti (yukarıda).
- Kılavuzlar `_drape`: kısıtlı Delaunay ile ≤3 mm üçgenlere bölünmüş, her köşesi lens yüzeyini kesintisiz izleyen ince plaka.
- Fren üçgeni kılavuzlarla aynı düzlemde.
- **Fren bölgesi (kullanıcı düzeltmesi, aynı gece):** fren, kılavuzların tamamını değil, yalnız büyük üçgenin sağ kenarı doğrultusunun solunu yakar (`BRAKE_CUT`, `_clip_line`). Sağ bölüm yalnız pozisyon. Video karelerinde pozlama doygun olduğu için bu ayrım videodan okunamamıştı.

Ölçüm: 78 431 üçgen, paket 588 KB (gzip 428 KB). Önceki sürüm 546 KB.

**Revize 3 (2026-10-20 gece): geri vites.** Kullanıcı: geri vites diğer ışıklara göre sönük.
- Neden: ışığı yalnız dört küçük LED kutusu (6,4 mm) veriyordu. 21 mm'lik krom kaplar ve pencere tabanı karanlık kalıyordu.
- Videoda (0:50) yanınca kapların tamamı LED'in ışığını yansıtıp beyaz parlıyor, en parlak nokta ortadaki LED.
- Düzeltme:
  - Kaplar dipten ağza üç banda bölündü, her bant yansıtıcı krom (`_refl`, `_cup_bands`): ×0,33 / 0,26 / 0,19.
  - Pencere tabanı ×0,13.
  - Sönükken krom görünürler.
  - Geri vites şiddeti 2,5 → 3,0.
- İlk denemede oranlar yüksekti (×0,85…). Pencere bloom ile tek beyaz lekeye dönüşüyordu; oranlar eşiğin altına çekildi.
- 78 879 üçgen, paket 593 KB. Tarayıcıda yakın ve orta mesafede geri vites açık/kapalı kontrol edildi. LZD 2856'nın 24 LED'lik geri vitesi yalnız şiddet artışından etkilenir, kontrol edildi. Tarayıcıda yakın ve orta mesafede pozisyon, fren ve sinyal kontrol edildi. Gerçek cihazda FPS ölçülmedi.

## 8. Lastik kollar CAD'den (LDCC 2698, LD 2994) ve lambaya montaj (2026-10-20 akşam)

Kaynak: `3d-files_2026-10-02_1139.zip` (`LDCC 2698, 2699.STEP`, `LD 2994, LD 2995.STEP`), ürün arşivleri `LDCC-2698.zip`, `LD-2994.zip`
(föy, fotoğraf, Dragon videosu). STL dönüşümü bölüm 7'deki gibi (`tools/blender/cad/<id>`).

**İşlevler (föy ve videodaki etiketler):** üç işlev tek devrede (`outline`): arkaya kırmızı rear position, öne beyaz front position, uçta turuncu side marker.

**LDCC 2698**
- STEP 25 katı parça: gövde (kol, plaka, kafa), iki lens yarısı, 2 × 5 + 2 × 5 LED, 2 vida.
- CAD ekseni: dışa +x, yukarı +y, lens yüzleri ±z.
- Işık parçaları lensin kendi yüzeylerinden ayrıldı: z ±18,5 düzlemindeki halka bandı (pencereyi çevreleyen, LED'lerin oturduğu bant) ve LED'ler. İç pencere z ±17'de.
- Uçtaki turuncu pencere, lens yarılarının x > 36 mm bölümü.

**LD 2994 Dragon**
- STEP tek kabuk.
- CAD'de montaj yüzü yatay modellenmiş: dışa +z, yukarı −x, lens yüzleri ±y.
- ">—<" kanallar kafa yüzündeki kendi kabarık yüzleri, uçtaki iki turuncu çubuk da kendi yüzleri; ikisi de orta çizgiye uzaklıkla ayrıldı. Kablo duvarın 40 mm ötesinde kesildi.

**Ölçüler el modelleriyle tutarlı:** kafa merkezi LDCC'de plakadan 97 mm yukarıda ve 128,5 mm dışarıda, LD 2994'te 102 ve 169 mm. Model ve paket boyutları:
- LDCC: 25 715 üçgen, 220 KB
- LD 2994: 21 135 üçgen, 195 KB

**LZD 3194'e montaj (düzeltme).** Önceki sürümde kol 40° döndürülüyordu; kolun kendi biçimi zaten eğik olduğu için taban yatıyor ve kol fazladan yukarı kalkıyordu.
- STEP'teki LDCC 2698 vidaları LDCC'nin kendi CAD'iyle eşlendi. Buna göre kol plakasının duvar yüzü x −219,1 mm, merkezi y 0, z 20 mm.
- Aradaki x −219…−203 bölgesi lambanın adaptör bloğu: lamba modelinde `BRACKET` düğümü, genişliğe sayılmaz.
- Kol `MOUNT_arm` noktasına **döndürmeden** oturur (`equipment.ts`).

## 9. Plaka aydınlatması CAD'den (LTD 229, LTD 2834, yeni RTR 3366) ve plakaya düşen ışık (2026-10-20 gece)

Kaynak: `3d-files_2026-10-02_1139.zip` (`LTD 229.STEP`, `LTD 2834.STEP`, `RTR 3366.STEP`), ürün arşivleri vault kökünde `LTD-229.zip`,
`LTD-2834.zip`, `RTR-3366.zip` (föy, teknik çizim, onay belgesi, fotoğraf, video). STL dönüşümü bölüm 7'deki gibi.
`step_to_stl.py`: kabuk bütün olarak üçgenlenemezse yüz yüz üçgenler (LTD 2834'te difüzörün çevresindeki kapak kabuğu; 419 yüzün 4'ü atlandı).

**Yerleşim (çizim HOR 47, 2. sayfa).** Plaka lambaları plakanın iki yanında, lamba ekseni plaka kenarından 40–80 mm. Tabanları
taşıyıcının dikey yüzüne vidalı, ışık penceresi plakanın ortasına bakar. LTD 229 eskiden plakanın üstündeydi (yanlış); artık
LTD 2834 ile aynı yerleşimde. Yerel sözleşme ikisinde ortak: taban y = 0, +Y tabandan yukarı (sitede arkaya), pencere +Z.

**LTD 229 (HOR 47; 3 LED, 0,25/0,5 W)**
- CAD: x genişlik, +y yukarı, lens +z. 13 parça: kapak, taban bandı, lens, kablo rakoru, 2 civata + somun + pul, 2 kapak vidası, kablo (30 mm'de kesildi).
- Lensin CAD'inde iç yüzde nervürlü silindirik optik ve 3 LED konisi (üst orta, alt sol/sağ), ön yüzde kabartma onay yazıları var.
- Lens üçe ayrıldı: buzlu ön panel (fotoğrafta açık gri, `E.plate.white.g45`), şeffaf pencere ve pencerenin iç yüzündeki optik (`E.plate.white.g70`).
  - Ön yüz neredeyse düz, CAD tessellasyonu büyük üçgenler. Lens pencere kenarlarından bölündü; yoksa üçgenler pencere sınırını kesip leke bırakıyordu.
- Arkada 3 LED (koni tepeleri) ve LED kartı. Yanınca bütün ön yüz ışır (video 0:11).
- 21 232 üçgen, 195 KB.

**LTD 2834 (HOR 127; 12 LED, plaka 1/2 W, pozisyon 0,1/0,2 W)**
- CAD: x genişlik, taban −z, +z yukarı, difüzör −y.
- Parçalar: taban, kapak (tepede Π yarık, yanda difüzör açıklığı), süt beyazı difüzör (`plate`), Π ışık kılavuzu (`position`, kırmızı), civatalar, rakor.
- Dış yüzler tüm parçalar birlikte ışınla seçildi (`_assembly_exterior`).
- 17 714 üçgen, 147 KB.

**RTR 3366 (HOR 160; LED aydınlatmalı plaka çerçevesi, 12 LED, 0,8/1,5 W, IP68, R148) — yeni ürün**
- 530,6 × 158,7 × 42,9 mm siyah çerçeve. Üst bant 42,9 mm dışa taşan saçak; altında 3 ışık modülü (4'er LED) plakaya aşağı ışık verir.
- Saçağın üstünde 2 opsiyonel lamba kapağı var. Alt bant kablo kanalının kapağı; föye göre müşteri baskısı alır, modelde düz siyah. Kablo alttan, ortadan çıkar.
- Plaka yuvası (`MOUNT_plate`): plaka 6 yaylı tırnak (taşıyıcıdan 2,5 mm öne) ile üst dudak (plakanın üst kenarını 5 mm örter) arasında; plaka ön yüzü taşıyıcıdan 18,4 mm önde.
  - Alt bandın üst kenarı ile modüllerin alt yüzü arası 113,7 mm; 110 mm'lik plaka ortada.
- Sitede çerçeve plakanın yerine taşıyıcıya oturur, plaka yuvasına öne alınır (`Engine.setConfig` → `trailer.plate`).
- Konfigüratörde plaka kategorisinde, ürün tavanı 1 (`data.ts`). 28 566 üçgen, 282 KB.

**Plakaya düşen ışık (`plateLight.ts`).** Önceki revizyonda yansıma ışıkları kapatılınca plaka hiç aydınlanmıyordu.
- Lamba yerleşimine göre bir aydınlatma haritası (`lightMap`) üretilir: plakanın kendi yüzeyi aydınlanır, harfler koyu kalır.
- Yandaki lambalarda lambaya yakın kenar parlak, ortaya doğru azalır; RTR 3366'da üst kenar parlak, aşağı doğru azalır.
- Yalnız ışıklar modunda ve pozisyon yanınca. Tepe değer bloom eşiğinin altında.
- Düşüş eğrileri görseldir, fotometrik ölçüm yok.

**Doğrulanmadı / açık:**
- LED konumları lens optiğinden ölçüldü, LED kartı CAD'de yok.
- LTD 2834'ün kablo çıkışı yaklaşık.
- RTR 3366 simgesi boş çerçeveyi gösterir (ışık saçağın altında, üstten görünmez).
- Plaka yuvası ölçüsü 520 × 110 TR plakasına göre; 520 × 114 AB plakası doğrulanmadı.

## 10. İkinci STEP paketi: CUBE, STRADA, HORUS (2026-10-23)

Kaynak: `Downloads/Product-3D-Step-Files/3d-model-ek-urunler/Modele 3D - Dideban (2026-10-22)/` ve ürün paketleri (`Downloads/LZD-2820.zip`, `LZD-2875GRAPHITE.zip`, `LZD-2876.zip`, `LZD-3223.zip`). Betik: `tools/blender/lamps_cad2.py` (`lamps.py` bunu `lamps_cad.py`'den sonra yükler).

```bash
# STEP → STL (her ürün için; çıktı tools/blender/cad/<id>, .gitignore'da)
STEP_IN=".../LZD 2875_GRAPHITE.STEP" STEP_OUT=tools/blender/cad/lzd2875 "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" tools/cad/step_to_stl.py
# model + simgeler, paketleme (her zaman önekle)
blender -b -P tools/blender/lamps.py -- --only lzd2875,lzd2876,lzd2820,lzd3223 --icons
npm run models:pack -- lamp-lzd2875 lamp-lzd2876 lamp-lzd2820 lamp-lzd3223
```

STEP'lerin dördünde de yalnız dış zarf var (gövde, düz lens kabuğu, çerçeve / aralayıcı, saplamalar). İç optik önden çekilmiş ürün fotoğraflarından ölçüldü (ölçek: lens ya da çerçeve genişliği).

| Ürün | Ölçü (mm) | İşlevler (EMIT) | Not |
|---|---|---|---|
| LZD 2875/GRAPHITE CUBE (HOR 164AY, universal) | 115 × 138 × 27,9 (çerçeve), rakor Ø15,4 | position (8 neon çubuk), stop (2 kristal "gülümseme"), turn (5 şerit × 6 LED) | koyu füme lens; föy: yalnız üçlü set onaylı |
| LZD 2876 CUBE (HOR 164, universal) | aynı gövde | reverse (8 kristal çubuk), fog (5 kristal şerit) | hafif füme lens |
| LZD 2820 STRADA (sağ: LZD 2821, ayna) | 240 × 141 × 49,6; 2 saplama ±76 | position (neon yol çizgileri), turn (çubuk), reverse (2 pencere, 3'er krom kap), stop (iç yan panel) / fog (dış yan panel; kullanıcı 2026-10-23): ">" biçimli retro panellerin ardında 10 LED, panelin dış kenarında siyah bumerang. Plaka aydınlatması yok (kullanıcı 2026-10-23; ilk sürümde iç yan yüzde şerit vardı). Üst neon şeritlerin iç kenarı üçgene paralel (fotoğraf 2-1'den ölçüldü) | 7 × 0,5 kablo: sitede AMP çifti |
| LZD 3223 HORUS (HOR 153A) | 200 × 140 × 51; 2 × M6 ±76 | position (18 uzun altıgen modül), turn / reverse (6'şar kaburgalı altıgen), stop / fog (6'şar kristal altıgen); katmanlı retro üçgen | STEP'in içindeki ürün LZD 3215 (aynı gövde ve lens; 3215'te ek plaka ışığı) |

- **CUBE seti** (kullanıcı 2026-10-23, LUNA gibi): sitede tek ürün `cube`, her yanda dıştan 2–3 × LZD 2875 + içte LZD 2876 (toplam yalnız 0 / 6 / 8). Föy LZD 2875'i yalnız üçlü set olarak onaylıyor: 6'lı dizilimde yanda iki LZD 2875 kalır (kullanıcıya bildirildi). Tampon `tek32-cube6` / `tek32-cube8`, çerçeveler 4 mm arayla (çizim HOR-164AY-3-razem: 110–116 mm adım). Montaj: ön çerçevenin üst / alt ortasından iki vida (Ø4,5), arkada aralayıcı.
- **Işık kalibrasyonu (kullanıcı 2026-10-23: "ışık şeritleri birbirine karışıyor"):** LZD 3194'teki ilke: büyük yüzeyler (kılavuz gövdeleri, kristal / retro yüzeyin LED'den uzak hücreleri, yansıtıcılar) işlev çarpanı × oran ≤ ~1 (bloom eşiği 1,05), haleyi yalnız LED noktaları ve önlerindeki hücreler verir. İlk sürümde gövdeler tam şiddetteydi: LZD 2876'nın geri vites çubukları ve HORUS'un beyaz hücreleri tek beyaz bulut oluyordu.
- **Simgeler (kullanıcı 2026-10-23):** stop kategorisinin yanık simgesinde bütün işlevler açık (`lamps.py` ICON_LIT: pozisyon, sinyal, fren, geri vites, sis); seçeneklerde kartın üstüne gelince bu simge görünür. Önceden yalnız pozisyon + sinyal + fren yanıyordu: LZD 2876'nın (sis + geri vites) yanık simgesi sönük kalıyordu.
- **Malzeme:** retro yüzeyler renkli ayna (metalik kırmızı, kaplamasız): kaplama gökyüzünü beyaz yansıtınca renksiz lensin ardında pembe okunuyordu. HORUS lensinin üçgen bölgesi kırmızı (CAD lensinde retro prizmalar kalıplı). HORUS turuncu / beyaz hücreleri: şeffaf kaburgalı optik + altı fasetli krom kap + LED. Bu dosyadaki ışık malzemeleri `.c2` / `.d` / `.x…` ekli: `_glow` / `_retro_cad` ile aynı ad önbellekte başka ürünün malzemesini döndürüyordu.
- **Doğrulanmadı:** CUBE'un CAD'de "yukarı" yönü (lamba simetrik); HORUS sağ eşinin kodu; iç elemanların derinlikleri (fotoğraf önden); LED sayıları föydeki toplamla birebir değil.
- **Not:** LZD 3223 föyde **12 V**. Dorselerde genelde 24 V sistem kullanılır; kullanıcıya bildirildi.

## 11. Arka şerit lambalar ve LRD 2681 CAD'den (2026-10-23)

Betik `tools/blender/lamps_cad2.py` (sonu). STEP → STL: `tools/blender/cad/lzd2246`, `lzd3141`, `lrd2679`.

| Ürün | Ölçü (mm) | İşlevler (EMIT) | Kaynak |
|---|---|---|---|
| LZD 2246 (HOR 86, universal) | 257 × 27 × 20, 2 × Ø4,5 (230) | turn (dış uçta 6 turuncu kap), position+stop (iç uçta 6 kırmızı kap; kullanıcı 2026-10-23) | STEP: lens kabuğu + lastik conta; kaplar fotoğraftan |
| LZD 3141 LIZARD (HOR 145AD, universal) | 252 × 27 × 21 | position (22 üçgen kılavuz), stop (uçlarda 2 + 2 altıgen), turn (ortada 8 altıgen; föyde dinamik, sitede sabit) | STEP: lens, uç kapakları, arka kapak, taban; iç fotoğraftan |
| LRD 2681 (HOR 111) | 101 × 127 × 50,5, M8 | work (12 LED halka), work+reverse (ortadaki 3 büyük LED) | STEP'i yok: **aynı gövdenin LRD 2679 STEP'i** (gövde, ön çerçeve, C braket, cıvata, pul, somun, ped); orta beyaz blok ve halka 2681 fotoğraflarından |

- **Site (kullanıcı 2026-10-23):** yeni kategori `strip` "Arka şerit lambalar", **yalnız standart dorse** (`CategoryDef.only`), bir çift. Montaj haritası `strip`: arka çerçevenin üst başlığı, kırmızı kontur bandının üstü, dış uç kenardan 30 mm içte; sağ lamba lens ekseni çevresinde 180° döner (lambanın −X ucu iki yanda dışta: LZD 2246'da turuncu sinyal, LZD 3141'de uçtaki fren).
- **Kablolama:** stop LZD 3194 ise aynı yandaki lambanın boştaki 4. Superseal çıkışından (sinyal yanıp sönmeli pozisyon; kör tapa kalkar), değilse Horpol modülünün ön yüzündeki dış Superseal'lerden, yan hattın içinden. Uzatma şasiden köşe dikmesinin içinden başlığa çıkar; lambanın 1 m kablosuyla hat içi Superseal çifti.
- **Doğrulanmadı:** şerit lambaların başlıktaki tam yüksekliği ve yatay mı takıldığı (kullanıcı "üst köşeler" dedi); LZD 3194'ün 4. çıkışının şerit lambaya uygun devre olduğu (föyde "sinyal yanıp sönmeli pozisyon"); LRD 2681'in LRD 2679 ile aynı gövde olduğu (çizim ve fotoğraflar aynı; 2681'in kendi STEP'i hâlâ yok).

## 12. LD 500, LD 499 ve LTD 669 CAD'den (2026-10-23)

Betik `tools/blender/lamps_cad2.py` (sonu; `lamps_small.py`'deki geçici LD 500 / LD 499 modelleri CAD yoksa yedek). STEP → STL: `tools/blender/cad/ld500` ("LD 500, 522"), `ld499`, `ltd669` (ek paket 2026-10-22). Ürün paketleri: `Downloads/LD-500.zip`, `LD-499.zip`, `LTD-669.zip` (fotoğraf, teknik çizim).

```bash
blender -b -P tools/blender/lamps.py -- --only ld500,ld499,ltd669 --icons
blender -b -P tools/blender/bumpers.py -- --kits   # plaka lambası bağlantı takımları (mount-ltd2834, mount-ltd669)
npm run models:pack -- lamp-ld500 lamp-ld499 lamp-ltd669 mount-ltd669 mount-ltd2834
```

| Ürün | Ölçü (mm) | İşlevler (EMIT) | Kaynak |
|---|---|---|---|
| LD 500 (HOR 55/SM1) | lens 98 × 31; toplam yükseklik 50, derinlik 27; flanş delikleri 50 | marker: pencere (3 LED'lik Fresnel dilimleri + LED kartı), retro hafif | STEP: gövde + kablo yakası, lens (**iç yüzde gerçek retro prizmalar**, pencere optiği), L tutucu, 2 vida. LED kartı, yaka dolgusu, kablo fotoğraf / çizimden |
| LD 499 (HOR 55) | LD 500 ile aynı | front: pencere (tek LED, iç içe halkalar) | LD 499 STEP'inin lensi sadeleştirilmiş (retrosuz): **LD 500'ün lensi** kullanıldı, pencere optiği silinip fotoğraftaki halkalar eklendi |
| LTD 669 (evrensel) | 93 × 30 × 47; 2 × M5 (52,5) | position: kırmızı yarı saydam kubbenin bütünü + tepenin altında katman + 2 kırmızı LED; plate: beyaz LED kartı + 3 SMD LED | STEP: kubbe (içi boş, tepesinde kabartma E işareti), şeffaf pencere kutusu, taban, rakor, uç vidaları, saplamalar. Saplamaların somunları ve tabanın altındaki etiket alınmadı. İç (kart, LED'ler, elemanlar) fotoğraftan |

- **Yerleşim değişmedi:** LD 500 / LD 499 geçici modelle aynı yerel eksende (tutucu plakasının arka yüzü Z = 0, orijin toplam yüksekliğin ortası). LTD 669, LTD 2834 ile aynı sözleşmede: taban tampona, kubbe arkaya, pencere plakaya. Plakanın iki yanında aynı lamba (pencere tek yanda, evrensel); adet hâlâ varsayım.
- **Site:** LD 500 / LD 499 / LTD 669 için `LAMP_PORTS` kablo uçları (Superseal çifti lambanın kısa kablosunda). Plaka ışığının kaynağı lambanın penceresinde: LTD 669 30 mm derin olduğu için 13 mm (LTD 2834: 31 mm).
- **Bağlantı takımı:** `bumpers.py` KITS'e `ltd669` eklendi. Saplama / kablo ayrımı kesit genişliğiyle: eşik 4,5 → 5,3 mm. İki lambanın M5 saplaması da kesitte 5,0 mm: eski eşikle LTD 2834'ün saplamaları da somun yerine lastik rakor alıyordu (düzeldi).
- **Kubbe malzemesi:** `E.position.red.g30.dome` (yarı saydam, %60 opak, kendisi ışır). Sitede `Lens.*` ışımıyor; kubbenin altındaki katman tek başına sönük kalıyordu. Ad `E.` ile başladığı için `lens` etiketi silindi (`set_icon_glass` kırmızı lens saydamlığını 0,32'ye çekiyordu).
- **Işık oranları:** pencere optiği amber 0,55, beyaz 0,4 (beyazın halesi halkaları örtüyordu); LED kartı amber 0,45, beyaz 0,3; LTD 669 kubbe tepesi katmanı 0,7, LED kartı 0,5.
- **Doğrulanmadı:** LD 500'ün 3 LED'inin yerleri (Fresnel dilimlerinin merkezlerinden), LED kartının derinliği; LTD 669'un kırmızı LED'lerinin yeri ve sayısı (çizimde 2 LED, yeri fotoğrafta görünmüyor), plaka LED'lerinin yatay aralığı (fotoğraftan ±12,5).
