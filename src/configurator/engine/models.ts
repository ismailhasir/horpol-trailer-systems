// Hazır 3D modeller (GLB): ilk istekte indirilir, önbelleğe alınır. Yükleyici (GLTFLoader) de yalnızca o an indirilir.
// Önbellekteki modelin geometrileri paylaşılan olarak işaretlenir: yeniden kurulumda dispose edilmez.
import * as THREE from 'three';
import { markShared } from './geo';

const pending = new Map<string, Promise<THREE.Object3D>>();
const ready = new Map<string, THREE.Object3D>();

export function loadModel(url: string): Promise<THREE.Object3D> {
  let p = pending.get(url);
  if (!p) {
    // Meshopt çözücü (~8 KB gzip) yalnızca ilk modelle birlikte indirilir; sıkıştırılmamış GLB'ler de aynı yükleyiciyle açılır
    p = Promise.all([import('three/examples/jsm/loaders/GLTFLoader.js'), import('three/examples/jsm/libs/meshopt_decoder.module.js')])
      .then(([{ GLTFLoader }, { MeshoptDecoder }]) => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(url))
      .then((g) => {
        g.scene.traverse((o) => {
          const mm = o as THREE.Mesh;
          if (!mm.isMesh) return;
          mm.castShadow = true;
          mm.receiveShadow = true;
          markShared(mm.geometry);
        });
        ready.set(url, g.scene);
        return g.scene;
      });
    p.catch(() => pending.delete(url));
    pending.set(url, p);
  }
  return p;
}

/** Yüklenmişse modeli döndürür (yoksa null; çağıran kodla çizilmiş yedek modeli kullanır) */
export function loadedModel(url: string): THREE.Object3D | null {
  return ready.get(url) ?? null;
}
