// Blender'da modellenen standart dorse (kuru yük kapalı kasa, referans Kässbohrer K.SBT / 20-12/27):
// tools/blender/standart_box.py → şasi + tekerlekler (standart-chassis.glb), kasa (standart-body.glb), zemin temas gölgesi
// (standart-contact.webp) ve bağlantı noktaları (standart-anchors.json). Ölçüler yalnız betikte; burada elle sayı yok.
// Koordinatlar: x boyuna (arka uç 0, ön -L), y yukarı, z yanal; metre.
import * as THREE from 'three';
import chassisUrl from '../../assets/models/standart-chassis.glb?url';
import bodyUrl from '../../assets/models/standart-body.glb?url';
import contactUrl from '../../assets/models/standart-contact.webp?url';
import A from './standart-anchors.json';
import { markShared } from './geo';

export const STANDART_GLB = chassisUrl;
export const STANDART_BODY_GLB = bodyUrl;
export const STANDART = A;

/** Tesisat görünümünde gizlenen kasanın yerini gösteren kontur: uç çerçeveleri, ara dikmeler, boyuna kenarlar */
export function standartSections(): THREE.Vector3[][] {
  const { x0, x1, y0, y1, halfW: h } = A.box;
  const out: THREE.Vector3[][] = [];
  const frame = (x: number) => [new THREE.Vector3(x, y0, h), new THREE.Vector3(x, y1, h), new THREE.Vector3(x, y1, -h), new THREE.Vector3(x, y0, -h)];
  const n = 6;
  for (let i = 0; i <= n; i++) out.push(frame(x0 + ((x1 - x0) * i) / n));
  for (const y of [y0, y1]) for (const z of [h, -h]) out.push([new THREE.Vector3(x0, y, z), new THREE.Vector3(x1, y, z)]);
  return out;
}

let contact: { geo: THREE.BufferGeometry; mat: THREE.MeshBasicMaterial } | null = null;
/** Zemin temas gölgesi (Blender'da pişirilmiş AO; beyaz = koyu). Tema renginden bağımsız: siyah, saydamlıkla karışır. */
export function standartContact(): THREE.Mesh {
  const c = A.contact;
  if (!contact) {
    const tex = new THREE.TextureLoader().load(contactUrl);
    tex.colorSpace = THREE.NoColorSpace;
    contact = {
      geo: markShared(new THREE.PlaneGeometry(c.x1 - c.x0, c.z1 - c.z0).rotateX(-Math.PI / 2)),
      mat: new THREE.MeshBasicMaterial({ color: 0x000000, alphaMap: tex, transparent: true, opacity: 0.55, depthWrite: false, fog: false }),
    };
  }
  const m = new THREE.Mesh(contact.geo, contact.mat);
  m.position.set((c.x0 + c.x1) / 2, 0.004, (c.z0 + c.z1) / 2);
  m.renderOrder = -1;
  m.userData.noEdge = true;
  m.userData.contact = true;
  return m;
}
