// Konfigüratör kuralları (src/configurator/data.ts): varsayılan yapılandırma, adet sınırları, dorse kuralları, adres satırı.
// Kurallar vault Revizeler/Standart Dorse.md ve kullanıcı kararlarından; bir test kırılırsa önce kuralın değişip değişmediğine bak.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  CATEGORIES,
  DEFAULT_CONFIG,
  SIDE_MAX,
  TRAILER_LIST,
  categoriesFor,
  fromQuery,
  layoutOf,
  lockedArm,
  maxQty,
  normalize,
  productById,
  productsFor,
  qtyOptions,
  sideMinPerSide,
  toQuery,
} from '../src/configurator/data.ts';

const base = () => structuredClone(DEFAULT_CONFIG);
const withLamps = (lamps, extra = {}) => {
  const c = base();
  Object.assign(c, extra);
  for (const [k, v] of Object.entries(lamps)) c.lamps[k] = { ...c.lamps[k], ...v };
  return c;
};

test('varsayılan yapılandırma kurallara zaten uygun (ilk açılış ve sıfırlama aynı)', () => {
  assert.deepEqual(normalize(base()), DEFAULT_CONFIG);
});

test('varsayılan yan marker adedi UN R48 en az sayısını karşılar', () => {
  assert.ok(DEFAULT_CONFIG.lamps.side.qty >= 2 * sideMinPerSide(DEFAULT_CONFIG.trailer));
});

test('normalize kendi çıktısını değiştirmez (her dorse, rastgele seçimler)', () => {
  let seed = 7;
  const rnd = (n) => ((seed = (seed * 1103515245 + 12345) % 2147483648) % n);
  for (let i = 0; i < 400; i++) {
    const c = base();
    c.trailer = TRAILER_LIST[rnd(TRAILER_LIST.length)].id;
    c.length = ['13.6', '12', '9'][rnd(3)];
    for (const cat of CATEGORIES) c.lamps[cat.id] = { product: cat.products[rnd(cat.products.length)].id, qty: rnd(25) - 2 };
    const once = normalize(c);
    assert.deepEqual(normalize(structuredClone(once)), once, JSON.stringify(c));
    for (const cat of CATEGORIES) {
      const q = once.lamps[cat.id].qty;
      assert.ok(q >= 0 && q <= maxQty(once, cat.id), `${cat.id} ${q}`);
    }
  }
});

test('standart dorse: tepe lambası kategorisi gizli ve adedi 0', () => {
  assert.ok(!categoriesFor('standart').some((c) => c.id === 'beacon'));
  assert.equal(normalize(withLamps({ beacon: { qty: 2 } })).lamps.beacon.qty, 0);
});

test('standart dorse: ön pozisyon lambası yan markerın eşinden gelir', () => {
  assert.equal(normalize(withLamps({ side: { product: 'ld500' }, front: { product: 'ld2773' } })).lamps.front.product, 'ld499');
  assert.equal(normalize(withLamps({ side: { product: 'ld2774' }, front: { product: 'ld499' } })).lamps.front.product, 'ld2773');
});

test('LZD 3194 seçiliyse lastik kol LDCC 2698 olur ve değiştirilemez', () => {
  const c = normalize(withLamps({ stop: { product: 'lzd3194', qty: 2 }, arm: { product: 'ld2994', qty: 2 } }));
  assert.equal(c.lamps.arm.product, 'ldcc2698');
  assert.equal(lockedArm(c), 'ldcc2698');
});

test('diğer stoplarda lastik kol serbest; stop 0 iken kilit yok', () => {
  const c = normalize(withLamps({ stop: { product: 'lzd2854', qty: 2 }, arm: { product: 'ld2994', qty: 2 } }));
  assert.equal(c.lamps.arm.product, 'ld2994');
  assert.equal(lockedArm(c), undefined);
  assert.equal(lockedArm(normalize(withLamps({ stop: { product: 'lzd3194', qty: 0 } }))), undefined);
});

test('standart dorse: lastik kol 0 ya da 2', () => {
  assert.equal(maxQty(base(), 'arm'), 2);
  assert.equal(normalize(withLamps({ arm: { qty: 4 } })).lamps.arm.qty, 2);
  assert.equal(normalize(withLamps({ arm: { qty: 1 } })).lamps.arm.qty, 2);
  assert.equal(normalize(withLamps({ arm: { qty: 0 } })).lamps.arm.qty, 0);
});

test('lowbed: sınırlar standart dorseyle aynı, yalnız tepe lambası takılabilir (kullanıcı 2026-10-22)', () => {
  const lb = { trailer: 'lowbed' };
  assert.ok(categoriesFor('lowbed').some((c) => c.id === 'beacon'));
  assert.equal(normalize(withLamps({ beacon: { qty: 2 } }, lb)).lamps.beacon.qty, 2);
  assert.equal(normalize(withLamps({ arm: { qty: 4 } }, lb)).lamps.arm.qty, 2);
  assert.equal(normalize(withLamps({ stop: { product: 'lzd3194', qty: 2 }, arm: { product: 'ld2994', qty: 2 } }, lb)).lamps.arm.product, 'ldcc2698');
  assert.equal(normalize(withLamps({ side: { product: 'ld500' }, front: { product: 'ld2773' } }, lb)).lamps.front.product, 'ld499');
  assert.ok(productsFor('lowbed', 'plate').some((p) => p.id === 'rtr3366'));
});

test('LUNA seti: toplam yalnız 0, 6 ya da 8', () => {
  const luna = productById('stop', 'luna');
  assert.deepEqual(qtyOptions(luna), [0, 6, 8]);
  const q = (n) => normalize(withLamps({ stop: { product: 'luna', qty: n } })).lamps.stop.qty;
  assert.equal(q(0), 0);
  assert.equal(q(2), 6);
  assert.equal(q(6), 6);
  assert.equal(q(8), 8);
  assert.equal(q(12), 8);
});

test('CUBE seti: LUNA gibi toplam yalnız 0, 6 ya da 8; içte LZD 2876 (kullanıcı 2026-10-23)', () => {
  const cube = productById('stop', 'cube');
  assert.deepEqual(qtyOptions(cube), [0, 6, 8]);
  assert.deepEqual(layoutOf(cube, 3), ['lzd2875', 'lzd2875', 'lzd2876']);
  assert.deepEqual(layoutOf(cube, 4), ['lzd2875', 'lzd2875', 'lzd2875', 'lzd2876']);
  const q = (n) => normalize(withLamps({ stop: { product: 'cube', qty: n } })).lamps.stop.qty;
  assert.equal(q(2), 6);
  assert.equal(q(6), 6);
  assert.equal(q(8), 8);
  assert.equal(q(12), 8);
});

test('arka şerit lambalar yalnız standart dorsede, bir çift (kullanıcı 2026-10-23)', () => {
  assert.deepEqual(productsFor('standart', 'strip').map((p) => p.id), ['lzd2246', 'lzd3141']);
  assert.ok(categoriesFor('standart').some((c) => c.id === 'strip'));
  for (const t of ['lowbed', 'silo', 'tanker', 'damper']) {
    assert.ok(!categoriesFor(t).some((c) => c.id === 'strip'), t);
    assert.equal(normalize(withLamps({ strip: { product: 'lzd3141', qty: 2 } }, { trailer: t })).lamps.strip.qty, 0, t);
  }
  assert.equal(normalize(withLamps({ strip: { product: 'lzd3141', qty: 1 } })).lamps.strip.qty, 2);
  assert.equal(normalize(withLamps({ strip: { product: 'lzd2246', qty: 6 } })).lamps.strip.qty, 2);
});

test('büyük kombine stoplar tek çift', () => {
  assert.equal(normalize(withLamps({ stop: { product: 'lzd2854', qty: 6 } })).lamps.stop.qty, 2);
  assert.equal(normalize(withLamps({ stop: { product: 'lzd2820', qty: 6 } })).lamps.stop.qty, 2);
  assert.equal(normalize(withLamps({ stop: { product: 'lzd3223', qty: 4 } })).lamps.stop.qty, 2);
});

test('yan marker çift sayıda ve dorse tavanında', () => {
  assert.equal(normalize(withLamps({ side: { qty: 3 } })).lamps.side.qty, 4);
  for (const [t, max] of Object.entries(SIDE_MAX)) {
    if (!TRAILER_LIST.some((x) => x.id === t)) continue;
    assert.equal(normalize(withLamps({ side: { qty: 99 } }, { trailer: t })).lamps.side.qty, max, t);
  }
});

test('plaka: üç aydınlatma tek tek seçilir, aynı anda biri (kullanıcı 2026-10-22); lambalar çift, çerçeve tek', () => {
  for (const t of ['standart', 'lowbed']) {
    assert.deepEqual(productsFor(t, 'plate').map((p) => p.id), ['ltd2834', 'ltd669', 'rtr3366'], t);
    assert.deepEqual(normalize(withLamps({ plate: { product: 'rtr3366', qty: 2 } }, { trailer: t })).lamps.plate, { product: 'rtr3366', qty: 1 });
    assert.equal(normalize(withLamps({ plate: { product: 'ltd2834', qty: 1 } }, { trailer: t })).lamps.plate.qty, 2);
  }
});

test('dorseye uymayan uzunluk ilk uygun uzunluğa döner', () => {
  assert.equal(normalize({ ...base(), trailer: 'silo', length: '13.6' }).length, '12');
  assert.equal(normalize({ ...base(), trailer: 'damper', length: '13.6' }).length, '9');
  assert.equal(normalize({ ...base(), trailer: 'standart', length: '9' }).length, '13.6');
});

test('dorse başına seçilebilir set uzunlukları (kullanıcı 2026-10-22)', () => {
  const lengths = Object.fromEntries(TRAILER_LIST.map((t) => [t.id, t.lengths]));
  assert.deepEqual(lengths, { standart: ['13.6'], lowbed: ['13.6', '9'], silo: ['12', '9'], tanker: ['12'], damper: ['9'] });
});

test('adres satırı: gidiş dönüş aynı yapılandırmayı verir', () => {
  const c = normalize(withLamps({ stop: { product: 'luna', qty: 8 }, side: { product: 'ld500', qty: 14 }, work: { qty: 2 } }));
  assert.deepEqual(fromQuery(toQuery(c)), c);
});

test('bozuk adres satırı geçerli yapılandırmaya döner', () => {
  const c = fromQuery('t=yok&s=99&l=7&stop=foo.abc&side=ld2774.-5&arm=x.y&work=lrd2681.1e9');
  assert.equal(c.trailer, 'standart');
  assert.equal(c.socket, '7x2');
  assert.equal(c.length, '13.6');
  assert.deepEqual(c.lamps.stop, { product: 'lzd3194', qty: 0 });
  assert.equal(c.lamps.side.qty, 0);
  assert.equal(c.lamps.work.qty, maxQty(c, 'work'));
  assert.deepEqual(normalize(structuredClone(c)), c);
});

test('gizli dorse tipi adresle açılamaz', () => {
  assert.equal(fromQuery('t=kapali').trailer, 'standart');
});
