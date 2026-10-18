// Konfigüratörden sabit pozlarda görüntü alır.
// node shots.mjs <outDir> <trailer> [length] [--system] [--only=a,b]
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const out = path.resolve(args[0] ?? 'out');
const trailer = args[1] ?? 'standart';
const length = args.find((a) => /^\d/.test(a)) ?? '13.6';
const only = (args.find((a) => a.startsWith('--only=')) ?? '').slice(7).split(',').filter(Boolean);
const W = +(process.env.SHOT_W ?? 1400);
const H = +(process.env.SHOT_H ?? 860);
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.type(), m.text().slice(0, 300)); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
// BLOCK=lowbed: o tipin GLB isteği düşürülür → kodla çizilen yedek model görünür (önce/sonra karşılaştırması)
if (process.env.BLOCK) await page.route((u) => u.pathname.includes(`${process.env.BLOCK}-`) && u.pathname.endsWith('.glb') && !u.search, (r) => r.abort());
await page.goto(process.env.URL ?? 'http://127.0.0.1:4321/tr/konfigurator/', { waitUntil: 'networkidle', timeout: 120000 });
await page.waitForFunction(() => window.__engine?.anchors, null, { timeout: 120000 });

// Poses: [name, system, camPos, target] (null camPos => engine view)
let L = 13.7;
const mkPoses = () => [
  ['overview', false, 'overview'],
  ['rear', false, 'rear'],
  ['side', false, 'side'],
  ['front', false, 'front'],
  ['rear34_low', false, [5.2, 1.1, 5.2], [-2.5, 0.9, 0]],
  ['under_side', false, [-6.5, 0.6, 6.5], [-6.5, 0.8, 0]],
  ['front34_low', false, [-L - 4.5, 1.2, 4.6], [-L + 3, 1.0, 0]],
  ['system', true, 'system'],
  ['system_top', true, 'top'],
  ['system_close_rear', true, [1.6, 3.4, 3.6], [-2.6, 1.0, 0]],
  ['system_close_front', true, [-L - 1.5, 3.6, 3.4], [-L + 3.0, 1.0, 0]],
  ['system_mid', true, [-6.0, 3.8, 4.5], [-6.0, 0.9, 0]],
  ['rear_high', false, [4.5, 4.2, 4.0], [-1.5, 1.4, 0]],
  ['neck', false, [-L + 1.0, 3.6, 4.2], [-L + 2.4, 1.3, 0]],
];

await page.evaluate(async ({ trailer, length }) => {
  const e = window.__engine;
  const cfg = structuredClone(e.cfg);
  cfg.trailer = trailer;
  cfg.length = length;
  cfg.lamps.arm.qty = 2;
  cfg.lamps.front.qty = 2;
  cfg.lamps.extra.qty = 2;
  e.setConfig(cfg);
  // model indirmesi (varsa) için bekle
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 500));
    if (e.trailer && e.key === `${trailer}|${length}` && !e._pendingModel) break;
  }
}, { trailer, length });
await page.waitForTimeout(4000);
L = await page.evaluate(() => window.__engine.anchors.L);
const poses = mkPoses();

for (const [name, sys, cam, target] of poses) {
  if (only.length && !only.includes(name)) continue;
  const data = await page.evaluate(async ({ sys, cam, target }) => {
    const e = window.__engine;
    if (e.system !== sys) e.setSystem(sys);
    e.tween = null;
    if (typeof cam === 'string') {
      e.setView(cam, true);
      e.tween = null;
    } else {
      e.tween = null;
      e.camera.position.set(...cam);
      e.controls.target.set(...target);
      e.controls.update();
    }
    e.shadowDirty = 3;
    for (let i = 0; i < 4; i++) {
      e.renderer.shadowMap.needsUpdate = true;
      e.renderer.render(e.scene, e.camera);
      await new Promise((r) => requestAnimationFrame(r));
    }
    return e.snapshot();
  }, { sys, cam, target });
  fs.writeFileSync(path.join(out, `${name}.jpg`), Buffer.from(data.split(',')[1], 'base64'));
  console.log('shot', name);
}
const info = await page.evaluate(() => {
  const e = window.__engine;
  return { calls: e.renderer.info.render.calls, tris: e.renderer.info.render.triangles, geos: e.renderer.info.memory.geometries, tex: e.renderer.info.memory.textures };
});
console.log(JSON.stringify(info));
await browser.close();
