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
- `tools/blender/lamps_aux.py`: LD 2994 Dragon, LDCC 2698, LRD 2679, LDO 2660.
- Çıktılar: `src/assets/models/lamp-<id>.glb` (sitede ilk kullanımda indirilir), `src/assets/lamps/<id>-off.webp` / `-on.webp` (ürün simgeleri).

## 2. GLB sözleşmesi (sitenin okuduğu)

| Düğüm | İçerik |
|---|---|
| `BODY` | opak gövde, braket, vida, kablo, fiş |
| `INNER` | opak iç parçalar: reflektör, LED kabı, köşe küp reflektör |
| `EMIT.<işlev>` | ışık veren parçalar; malzeme adı `E.<işlev>.<renk>` |
| `LENS` | şeffaf dış lens (`Lens.<renk>`), tepe lambası kubbesi (`Dome.amber`) |

İşlevler: position, stop, turn, reverse, fog, marker, front, outline, plate, work, beacon. Renkler: red, amber, white.
Yerel eksenler (three.js, metre): lens +Z'ye bakar, X genişlik, Y yukarı, montaj yüzeyi z = 0. Sağ arka lamba sol lambanın aynasıdır.

## 3. Sitede ışıklar

`src/configurator/engine/lampfx.ts`: lamba modellerinin kaydı ve işlevlerin yakılması. Işıklar modunda kullanıcı yanan işlevleri
seçer (pozisyon, fren, sinyal, geri vites, sis, çalışma, tepe). Yanan malzeme ton eşlemesiz doygun renkte ışır, aynı renkteki dış
lens de hafifçe aydınlanır; sinyal ~1,5 Hz yanıp söner, tepe lambası 2,1 Hz çift flaş. Zemine renkli ışık yansıması yok (kaldırıldı).

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
| Plaka | 2 |
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
| LZD 3194/AMP MAVIC (sağ: 3195, ayna) | arka | 405 × 148 × 63; 2 × M8 (250), AMP 7 pin, 4 Superseal | position, stop, turn, reverse, fog | 9 652 | 110 KB |
| LZD 2856 Heavy Duty (sağ: 2857) | arka | 451 × 139 × 74; 2 × M8 (152), 8 vida | turn, stop, position (neon şevron), reverse, fog | 6 494 | 100 KB |
| LZD 2423 LUCY | arka | Ø121,4 × 33,5, paslanmaz halka Ø155 | turn, position (neon halka + 4 kol), stop | 7 128 | 96 KB |
| LZD 2448 LUNA | arka | Ø121,4 × 36,2, krom halka Ø155,6 | position, turn (D modülü), stop | 7 338 | 97 KB |
| LZD 2877 / 2880 CUBE | arka | 115 × 138 × 40,3; siyah / krom çerçeve | position, stop, turn | 7 404 | 88 / 89 KB |
| LD 2774 | yan marker | lamba 119,6 × 45,9 × 20,4; tutucu 74,9 yük. | marker (amber neon çubuk) | 5 002 | 74 KB |
| LD 2773 | ön pozisyon | LD 2774 ile aynı gövde, beyaz | front | 5 002 | 74 KB |
| LD 2765 | yan marker | 110,8 × 52,2 × 20,65; tutucu 71,8 | marker (neon çerçeve halka) | 4 698 | 75 KB |
| LD 0128 / LD 0127 | yan / ön | 132 × 33 × 13, delik arası 115 | marker / front (3 LED) | 3 484 | 73 KB |
| LTD 2834 | plaka | 93,5 × 70 × 58; 2 × M5 (46) | plate (difüzör), position (kırmızı Π neon) | 2 364 | 46 KB |
| LTD 229 | plaka | 97 × 64,7 × 62,3; 2 × M5 (46) | plate (3 LED) | 3 042 | 54 KB |
| LD 2994 Dragon | lastik kol | uzanım 200,8, yük. 179; plaka 35 × 105 | outline: beyaz öne, kırmızı arkaya, turuncu yana | 4 272 | 71 KB |
| LDCC 2698 | lastik kol | uzanım 168,8, yük. 177, gen. 37 | outline: beyaz / kırmızı neon halka, turuncu yan | 6 176 | 90 KB |
| LRD 2679 | çalışma | 101 × 100 × 50,5; U braket, M8 | work (12 küçük + 3 büyük LED) | 7 044 | 92 KB |
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
