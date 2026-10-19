// Lamba montaj haritası kontrolü (UN R48, O3/O4 yarı römork). Bağımlılıksız:  node tools/check-lighting.mjs
// Beş dorse tipinin bağlantı noktası JSON'undaki `mounts` alanını (tools/blender/<tip>.py → mounts_dict) okur, her kural için
// tablo basar (tip, kural, değer, sınır, sonuç) ve yan marker için adet → aralık ilişkisini hesaplar.
// Sonuçlar: UYGUN, UYGUN* (R48'in "yapı izin vermezse" istisnası; gerekçe JSON'daki notes'ta), BİLGİ, AYKIRI. AYKIRI varsa çıkış kodu 1.
// Koordinatlar: x boyuna (arka uç 0, ön −L), y yukarı, z yanal (+z sol), metre.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const TYPES = ['standart', 'lowbed', 'silo', 'tanker', 'damper'];

// Lamba ölçüleri (tools/blender/lamps.py ve equipment.ts → LAMP_W): kontrol en kötü durumla yapılır
const REAR_H = 0.148; // LZD 3194 yüksekliği
const REAR_W_MAX = 0.451; // en geniş arka lamba (LZD 2856)
const FOG_TOP = -0.012; // LZD 3194 sis kanalı (yerel y −0,040…−0,012) ve kanal kalınlığı ±0,002
const FOG_BOT = -0.042;
const REV_TOP = 0.062; // geri vites pencereleri (yerel y 0,050 ± 0,012)
const MARKER_L = 0.11; // yan marker boyu / yüksekliği (yer tutucu PH_SIZE)
const MARKER_H = 0.045;
const FRONT_W = 0.11; // ön pozisyon genişliği / yüksekliği
const FRONT_H = 0.045;

const rows = [];
let bad = 0;
const f = (v, d = 3) => (typeof v === 'number' ? v.toFixed(d) : String(v));
function row(type, rule, value, limit, ok, star = false) {
  const res = ok === null ? 'BİLGİ' : ok ? (star ? 'UYGUN*' : 'UYGUN') : 'AYKIRI';
  if (ok === false) bad++;
  rows.push([type, rule, value, limit, res]);
}
const profileAt = (p, x) => {
  if (x <= p[0][0]) return p[0][1];
  for (let i = 1; i < p.length; i++) {
    if (x <= p[i][0]) {
      const [x0, y0] = p[i - 1];
      const [x1, y1] = p[i];
      return x1 === x0 ? y1 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
    }
  }
  return p[p.length - 1][1];
};

// data.ts'deki yan marker tavanı (iki yan toplamı)
let SIDE_MAX = {};
try {
  const src = readFileSync(join(ROOT, 'src/configurator/data.ts'), 'utf8');
  const m = src.match(/SIDE_MAX[^=]*=\s*\{([^}]*)\}/);
  if (m) for (const [, k, v] of m[1].matchAll(/(\w+)\s*:\s*(\d+)/g)) SIDE_MAX[k] = Number(v);
} catch {
  SIDE_MAX = {};
}

/** Yan markerlar n adet (yan başına), sitedeki gibi x0 → x1 eşit aralıklı */
function sidePositions(S, n) {
  if (n === 1) return [(S.x0 + S.x1) / 2];
  return Array.from({ length: n }, (_, i) => S.x0 + ((S.x1 - S.x0) * i) / (n - 1));
}
function evalSide(S, L, n) {
  const xs = sidePositions(S, n);
  const first = xs[0] + L;
  const last = -xs[xs.length - 1];
  let gap = 0;
  for (let i = 1; i < xs.length; i++) gap = Math.max(gap, xs[i] - xs[i - 1]);
  const mid = xs.some((x) => x + L >= L / 3 && x + L <= (2 * L) / 3);
  const clash = xs.filter((x) => (S.avoid ?? []).some(([a, b]) => x > a && x < b));
  const okFirst = first <= S.rule.firstFromFront + 1e-6;
  const okLast = last <= S.rule.lastFromRear + 1e-6;
  const okGap = n > 1 && gap <= S.rule.maxGap + 1e-6;
  return { xs, first, last, gap, mid, clash, ok: okFirst && okLast && okGap && mid && clash.length === 0, okFirst, okLast, okGap };
}

const sideTables = [];
for (const t of TYPES) {
  const a = JSON.parse(readFileSync(join(ROOT, `src/configurator/engine/${t}-anchors.json`), 'utf8'));
  const M = a.mounts;
  if (!M) {
    row(t, 'mounts alanı', 'yok', 'olmalı', false);
    continue;
  }
  const W2 = a.W / 2;
  const L = a.L;

  // ---------- arka ----------
  const R = M.rear;
  row(t, 'Arka poz/stop/sinyal: dış kenara', f(W2 - R.zOuter), '≤ 0.400', W2 - R.zOuter <= 0.4);
  const lo = R.y - REAR_H / 2;
  const hi = R.y + REAR_H / 2;
  row(t, 'Arka lamba yükseklik (alt–üst kenar)', `${f(lo)}–${f(hi)}`, '0.350–1.500', lo >= 0.35 && hi <= 1.5);
  row(t, 'Stop iç kenarları arası (en kötü)', f(2 * R.zInner), '≥ 0.600', 2 * R.zInner >= 0.6);
  row(t, 'Arka bölge genişliği (en geniş lamba)', f(R.zOuter - R.zInner), `≥ ${f(REAR_W_MAX)}`, R.zOuter - R.zInner >= REAR_W_MAX);
  const fogTop = R.y + FOG_TOP;
  const fogBot = R.y + FOG_BOT;
  row(t, 'Arka sis (LZD 3194 sis kanalı)', `${f(fogBot)}–${f(fogTop)}`, '0.250–1.000', fogBot >= 0.25 && fogTop <= 1.0);
  row(t, 'Arka sis (tüm lamba gövdesi, bilgi)', f(hi), '≤ 1.000', hi <= 1.0 ? true : null);
  row(t, 'Geri vites (pencere üst / gövde alt)', `${f(lo)}–${f(R.y + REV_TOP)}`, '0.250–1.200', lo >= 0.25 && R.y + REV_TOP <= 1.2);

  // ---------- plaka ----------
  const P = M.plate;
  const pTop = P.plateY + P.plateH / 2;
  const okPl = P.y > pTop && P.y - pTop <= 0.1 && P.z.every((z) => Math.abs(z) <= P.plateW / 2) && Math.abs(P.x - R.faceX) <= 0.1;
  row(t, 'Plaka lambası plakanın üstünde', `+${f(P.y - pTop)} m, |z| ${f(Math.max(...P.z.map(Math.abs)), 2)}`, `0–0.10 m, |z| ≤ ${f(P.plateW / 2, 2)}`, okPl);
  row(t, 'Plaka yüksekliği (alt kenar)', f(P.plateY - P.plateH / 2), '≥ 0.300', P.plateY - P.plateH / 2 >= 0.3);

  // ---------- ön pozisyon ----------
  const F = M.front;
  if (a.W > 1.6) {
    const edge = W2 - (F.z + FRONT_W / 2);
    row(t, 'Ön pozisyon: dış kenara', f(Math.max(0, edge)), '≤ 0.150', edge <= 0.15);
    row(t, 'Ön pozisyon yükseklik', `${f(F.y - FRONT_H / 2)}–${f(F.y + FRONT_H / 2)}`, '0.350–2.100', F.y - FRONT_H / 2 >= 0.35 && F.y + FRONT_H / 2 <= 2.1);
  }

  // ---------- kontur (lastik kol) ----------
  if (a.W > 2.1) {
    for (const [k, nm] of [
      ['armFront', 'Kontur ön (beyaz)'],
      ['armRear', 'Kontur arka (kırmızı)'],
    ]) {
      const A = M[k];
      row(t, `${nm}: dış kenara`, f(Math.max(0, W2 - A.wallZ)), '≤ 0.400', W2 - A.wallZ <= 0.4);
      const from = k === 'armFront' ? A.x + L : -A.x;
      row(t, `${nm}: yükseklik / ${k === 'armFront' ? 'önden' : 'arkadan'}`, `y ${f(A.y, 2)} / ${f(from, 2)} m`, `üst ${f(a.topY, 2)} (yüksek sabit yer)`, null);
    }
  }

  // ---------- yan marker ----------
  const S = M.side;
  if (L > 6) {
    const ys = sidePositions(S, S.maxPerSide).map((x) => profileAt(S.y, x));
    const yLo = Math.min(...ys) - MARKER_H / 2;
    const yHi = Math.max(...ys) + MARKER_H / 2;
    const strict = yLo >= 0.25 && yHi <= 0.9;
    row(t, 'Yan marker yükseklik', `${f(yLo)}–${f(yHi)}`, '0.250–0.900 (yapı izin vermezse 1.500)', yLo >= 0.25 && yHi <= 1.5, !strict);
    row(t, 'Yan marker: ilki önden (x0)', f(S.x0 + L, 2), `≤ ${f(S.rule.firstFromFront, 1)}`, S.x0 + L <= S.rule.firstFromFront + 1e-6);
    row(t, 'Yan marker: sonuncusu arkadan (x1)', f(-S.x1, 2), `≤ ${f(S.rule.lastFromRear, 1)}`, -S.x1 <= S.rule.lastFromRear + 1e-6);
    // adet → aralık
    const table = [];
    let nMin = null;
    let clashAny = false;
    for (let n = 1; n <= S.maxPerSide; n++) {
      const e = evalSide(S, L, n);
      if (e.ok && nMin === null) nMin = n;
      if (e.clash.length) clashAny = true;
      table.push([t, n, 2 * n, n > 1 ? f(e.gap, 2) : '—', f(e.first, 2), f(e.last, 2), e.mid ? 'var' : 'yok', e.clash.length ? e.clash.map((x) => f(x, 2)).join(' ') : '—', e.ok ? 'UYGUN' : 'yetersiz/AYKIRI']);
    }
    sideTables.push(...table);
    const theo = Math.ceil((L - S.rule.firstFromFront - S.rule.lastFromRear) / S.rule.maxGap) + 1;
    row(t, 'Yan marker: en az adet (yan başına, eşit dağıtım)', nMin ?? 'yok', `kuramsal en az ${theo}; tavan ${S.maxPerSide}`, nMin !== null);
    row(t, 'Yan marker: yasak bölge çakışması (n = 1…tavan)', clashAny ? 'var' : 'yok', 'yok', !clashAny);
    if (SIDE_MAX[t] !== undefined) row(t, 'Yan marker tavanı = data.ts SIDE_MAX / 2', `${S.maxPerSide} / ${SIDE_MAX[t] / 2}`, 'eşit', S.maxPerSide === SIDE_MAX[t] / 2);
    row(t, 'Yan marker yuva aralığı (tavanda)', f((S.x1 - S.x0) / (S.maxPerSide - 1), 2), '≥ 1.20 (çakışmasız)', (S.x1 - S.x0) / (S.maxPerSide - 1) >= 1.2);
  }

  // ---------- çalışma / tepe ----------
  const wk = M.work ?? [];
  const wkOk = wk.length <= 2 && wk.every((w) => w.dir[0] > 0 && w.dir[1] < 0);
  row(t, 'Çalışma lambası: adet, arkaya-aşağı', `${wk.length}, y ${wk.map((w) => f(w.y, 2)).join('/')}`, '≤ 2, dir x>0 y<0', wkOk);
  const bc = M.beacon ?? [];
  row(t, 'Tepe lambası: adet / taban y', `${bc.length} / ${bc.map((b) => f(b.y, 2)).join(', ')}`, `1–2; dorse üstü ${f(a.topY, 2)}`, bc.length >= 1 && bc.length <= 2);

  // ---------- montaj ----------
  const par = M.parents ?? {};
  const keys = ['rear', 'plate', 'side', 'front', 'armFront', 'armRear', 'work', 'beacon'];
  const okPar = keys.every((k) => par[k] === 'chassis' || par[k] === 'body');
  const bodyKeys = keys.filter((k) => par[k] === 'body');
  row(t, 'Montaj: yalnız sabit parça', bodyKeys.length ? `kasa/üst yapı: ${bodyKeys.join(',')}` : 'hepsi şasi', 'chassis | sabit body', okPar);
}

// ---------- yazdır ----------
function print(head, data) {
  const w = head.map((h, i) => Math.max(String(h).length, ...data.map((r) => String(r[i]).length)));
  const line = (r) => r.map((c, i) => String(c).padEnd(w[i])).join('  ');
  console.log(line(head));
  console.log(w.map((n) => '-'.repeat(n)).join('  '));
  let prev = null;
  for (const r of data) {
    if (prev !== null && r[0] !== prev) console.log('');
    prev = r[0];
    console.log(line(r));
  }
}
console.log('UN R48 lamba montaj haritası kontrolü (O3/O4 yarı römork)\n');
print(['tip', 'kural', 'değer', 'sınır', 'sonuç'], rows);
console.log('\nYan marker: adet → aralık (yan başına n, sitedeki gibi x0 → x1 eşit dağıtım)\n');
print(['tip', 'n/yan', 'toplam', 'en büyük aralık', 'ilki önden', 'sonuncu arkadan', 'orta 1/3', 'yasak bölgede', 'sonuç'], sideTables);
console.log('\nUYGUN* = R48 istisnası (yan marker: yapı 0,9 m altına izin vermiyor; R48 6.18 üst sınırı zaten 1,5 m). Gerekçe: mounts.notes.');
console.log(bad ? `\n${bad} AYKIRI` : '\nTüm kurallar UYGUN.');
process.exit(bad ? 1 : 0);
