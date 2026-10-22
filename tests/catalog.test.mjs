// Katalog bütünlüğü: lamba modelleri ve simgeleri konfigüratör ürünleriyle eşleşir; sipariş özeti setleri bileşen bileşen yazar.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readdirSync } from 'node:fs';
import { CATEGORIES, DEFAULT_CONFIG, normalize } from '../src/configurator/data.ts';
import { summaryRows } from '../src/configurator/summary.ts';
import { useCUi } from '../src/configurator/i18n.ts';

const tr = useCUi('tr');

const assets = new URL('../src/assets/', import.meta.url);
const ids = new Set(CATEGORIES.flatMap((c) => c.products.flatMap((p) => [p.id, ...(p.set ?? [])])));

test('her lamba modeli bir ürüne ait (katalogdan çıkan ürünün modeli kalmaz)', () => {
  const glbs = readdirSync(new URL('models/', assets)).filter((f) => f.startsWith('lamp-')).map((f) => f.slice(5, -4));
  for (const id of glbs) assert.ok(ids.has(id), `lamp-${id}.glb katalogda yok`);
});

test('modeli olan her lambanın sönük ve yanık simgesi var', () => {
  for (const id of ids) {
    if (!existsSync(new URL(`models/lamp-${id}.glb`, assets))) continue;
    for (const s of ['off', 'on']) assert.ok(existsSync(new URL(`lamps/${id}-${s}.webp`, assets)), `${id}-${s}.webp yok`);
  }
});

const rows = (lamps) => {
  const c = structuredClone(DEFAULT_CONFIG);
  for (const [k, v] of Object.entries(lamps)) c.lamps[k] = { ...c.lamps[k], ...v };
  return summaryRows(normalize(c), tr, 'tr');
};

test('sipariş özeti: plaka aydınlatması seçildiği gibi, çerçeve zorunlu değil (kullanıcı 2026-10-22)', () => {
  assert.ok(!rows({}).some((r) => r.value.includes('RTR 3366')));
  assert.ok(rows({ plate: { product: 'rtr3366', qty: 1 } }).some((r) => r.value === '1 × RTR 3366'));
  assert.ok(!rows({ plate: { qty: 0 } }).some((r) => r.value.includes('RTR 3366') || r.value.includes('LTD 2834')));
});

test('sipariş özeti: LUNA seti bileşenleriyle', () => {
  const v = (n) => rows({ stop: { product: 'luna', qty: n } }).map((r) => r.value);
  assert.ok(v(6).includes('4 × LZD 2448 + 2 × LZD 2452'));
  assert.ok(v(8).includes('6 × LZD 2448 + 2 × LZD 2452'));
});

test('sipariş özeti: adedi 0 olan kategori yazılmaz, set adedi 1 ise satır yok', () => {
  const r = rows({ work: { qty: 0 } });
  assert.ok(!r.some((x) => x.value.includes('LRD 2681')));
  assert.ok(!r.some((x) => x.label === tr.set_qty));
});
