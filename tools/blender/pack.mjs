// Blender'ın ham GLB çıktılarını (tools/blender/out/) Meshopt ile sıkıştırıp sitenin kullandığı yere yazar (src/assets/models/).
// Kuantalama kapalı (-vpf -vnf -vtf): öznitelikler Float32 kalır; sitedeki birleştirme (mergeByMaterial) matris uygulayıp
// geometrileri birleştirdiği için kuantalanmış (Int16) veri kırpılır/düşer. Meshopt sıkıştırması yine işler.
// Çalıştırma: npm run models:pack [-- lowbed]   (önce: blender -b -P tools/blender/<tip>.py)
import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import { gzipSync } from 'node:zlib';
import { readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const cli = require.resolve('gltfpack/cli.js');
// tools/blender/out altındaki tüm GLB'ler (ya da komut satırında verilenler: npm run models:pack -- lowbed)
const only = process.argv.slice(2);
const MODELS = readdirSync('tools/blender/out')
  .filter((f) => f.endsWith('.glb'))
  .map((f) => f.slice(0, -4))
  .filter((n) => !only.length || only.some((o) => n.startsWith(o)))
  .sort();
const kb = (n) => `${(n / 1024).toFixed(0)} KB`;

let total = 0;
let totalGz = 0;
for (const name of MODELS) {
  const src = `tools/blender/out/${name}.glb`;
  const dst = `src/assets/models/${name}.glb`;
  if (!existsSync(src)) {
    console.error(`Eksik: ${src} (önce Blender betiğini çalıştırın)`);
    process.exit(1);
  }
  const r = spawnSync(process.execPath, [cli, '-i', src, '-o', dst, '-cc', '-ce', 'ext', '-vpf', '-vnf', '-vtf'], { stdio: 'inherit' });
  if (r.status !== 0) process.exit(r.status ?? 1);
  const size = statSync(dst).size;
  const gz = gzipSync(readFileSync(dst), { level: 9 }).length;
  total += size;
  totalGz += gz;
  console.log(`${name}: ${kb(statSync(src).size)} → ${kb(size)} (gzip ${kb(gz)})`);
}
console.log(`Toplam: ${kb(total)} (gzip ${kb(totalGz)})`);
