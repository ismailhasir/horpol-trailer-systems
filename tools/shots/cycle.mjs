// Tüm tipler arasında arayüzden geçiş: her seçimde ara anahtarı (eski model görünüyor mu) ve sonucu kaydeder.
import { chromium } from 'playwright';
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1200, height: 760 } });
const errs = [];
p.on('pageerror', (e) => errs.push(e.message));
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
// model indirmesini yavaşlat: ara durum görünür olsun
await p.route((u) => u.pathname.endsWith('.glb') && !u.search, async (r) => { await new Promise((x) => setTimeout(x, 2500)); r.continue(); });
await p.goto('http://127.0.0.1:4321/tr/konfigurator/', { waitUntil: 'networkidle', timeout: 180000 });
await p.waitForFunction(() => window.__engine?.anchors, null, { timeout: 180000 });
const names = { lowbed: 'Lowbed', silo: 'Silobas', tanker: 'Tanker', damper: 'Damper', standart: 'Standart' };
const out = [];
for (const id of ['lowbed', 'silo', 'tanker', 'damper', 'standart']) {
  const before = await p.evaluate(() => window.__engine.key);
  await p.click('.dd-btn');
  await p.click(`.dd-menu li:has-text("${names[id]}")`);
  await p.waitForTimeout(600);
  const mid = await p.evaluate(() => ({ key: window.__engine.key, ind: document.querySelector('.cfg-modelstate')?.textContent ?? null }));
  await p.waitForFunction((t) => window.__engine.key.startsWith(t), id, { timeout: 120000 });
  const after = await p.evaluate(() => ({ key: window.__engine.key, L: window.__engine.anchors.L, ind: document.querySelector('.cfg-modelstate')?.textContent ?? null }));
  out.push({ id, before, mid, after });
}
console.log(JSON.stringify(out, null, 1));
console.log('ERRORS', JSON.stringify(errs));
await b.close();
