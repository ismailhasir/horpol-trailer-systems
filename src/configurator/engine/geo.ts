// Sahne ağları için küçük ortak yardımcılar: gölge ayarlı Mesh ve paylaşılan (önbellekteki) geometri işareti.
import * as THREE from 'three';

export function mesh(geo: THREE.BufferGeometry, mat: THREE.Material, cast = true, receive = true) {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = cast;
  m.receiveShadow = receive;
  return m;
}

const shared = new WeakSet<THREE.BufferGeometry>();
/** Birden çok yapıda kullanılan ya da önbellekte duran geometri: yeniden kurulumda dispose edilmez */
export function markShared<T extends THREE.BufferGeometry>(g: T): T {
  shared.add(g);
  return g;
}
export function isShared(g: THREE.BufferGeometry | undefined) {
  return !g || shared.has(g);
}
