// Blender'da modellenip ortam örtmesi pişirilen dorse tipleri, konfigüratördeki tüm görünür tipler (tools/blender/<tip>.py → npm run models:pack).
// Her tip: şasi + tekerlekler GLB, kasa/üst yapı GLB, zemin temas gölgesi (WebP) ve betiğin aynı ölçülerden ürettiği
// bağlantı noktası JSON'u (lamba, soket, tesisat profili, tesisat görünümü kontur çizgileri). Burada elle ölçü yok.
// Koordinatlar: x boyuna (arka uç 0, ön -L), y yukarı, z yanal; metre.
import * as THREE from 'three';
import type { TrailerId } from '../data';
import { markShared } from './geo';
import stdChassis from '../../assets/models/standart-chassis.glb?url';
import stdBody from '../../assets/models/standart-body.glb?url';
import stdContact from '../../assets/models/standart-contact.webp?url';
import stdAnchors from './standart-anchors.json';
import lbChassis from '../../assets/models/lowbed-chassis.glb?url';
import lbBody from '../../assets/models/lowbed-body.glb?url';
import lbContact from '../../assets/models/lowbed-contact.webp?url';
import lbAnchors from './lowbed-anchors.json';
import siChassis from '../../assets/models/silo-chassis.glb?url';
import siBody from '../../assets/models/silo-body.glb?url';
import siContact from '../../assets/models/silo-contact.webp?url';
import siAnchors from './silo-anchors.json';
import tkChassis from '../../assets/models/tanker-chassis.glb?url';
import tkBody from '../../assets/models/tanker-body.glb?url';
import tkContact from '../../assets/models/tanker-contact.webp?url';
import tkAnchors from './tanker-anchors.json';
import dmChassis from '../../assets/models/damper-chassis.glb?url';
import dmBody from '../../assets/models/damper-body.glb?url';
import dmContact from '../../assets/models/damper-contact.webp?url';
import dmAnchors from './damper-anchors.json';

type P3 = { x: number; y: number; z: number };
/** Betiğin yazdığı JSON (tools/blender/bl_common.py → write_anchors) */
export interface BakedAnchors {
  L: number;
  W: number;
  topY: number;
  rear: { x: number; lampY: number; lampZ: number[]; plateY: number; dropX?: number };
  /** profile: yan markerların yüksekliği [x, y] (x artan) */
  /** brackets: markerlar şasiden uzanan braketlerde (devrilen kasalı tipler); site çizer */
  side: { x0: number; x1: number; z: number; profile: number[][]; brackets?: boolean };
  front: P3;
  armFront: P3;
  armRear: P3;
  extra: { x: number; y: number; z0: number; z1: number };
  socket: { x: number; y: number };
  /** profile: tesisatın şasi boyunca izlediği yükseklik [x, y] (x artan) */
  harness: { y: number; frontX: number; trunkZ: number; rearZ: number; profile: number[][] };
  contact: { x0: number; x1: number; z0: number; z1: number };
  /** tesisat görünümünde gizlenen gövdenin yerini gösteren kontur çizgileri (kapalı çokgenler) */
  sections: number[][][];
}

export interface BakedSpec {
  chassis: string;
  body: string;
  contact: string;
  anchors: BakedAnchors;
}

export const BAKED: Partial<Record<TrailerId, BakedSpec>> = {
  standart: { chassis: stdChassis, body: stdBody, contact: stdContact, anchors: stdAnchors },
  lowbed: { chassis: lbChassis, body: lbBody, contact: lbContact, anchors: lbAnchors },
  silo: { chassis: siChassis, body: siBody, contact: siContact, anchors: siAnchors },
  tanker: { chassis: tkChassis, body: tkBody, contact: tkContact, anchors: tkAnchors },
  damper: { chassis: dmChassis, body: dmBody, contact: dmContact, anchors: dmAnchors },
};

export function bakedSections(a: BakedAnchors): THREE.Vector3[][] {
  return a.sections.map((loop) => loop.map(([x, y, z]) => new THREE.Vector3(x, y, z)));
}

const contacts = new Map<string, { geo: THREE.BufferGeometry; mat: THREE.MeshBasicMaterial }>();
/** Zemin temas gölgesi (Blender'da pişirilmiş AO; beyaz = koyu). Tema renginden bağımsız: siyah, saydamlıkla karışır. */
export function bakedContact(spec: BakedSpec): THREE.Mesh {
  const c = spec.anchors.contact;
  let k = contacts.get(spec.contact);
  if (!k) {
    const tex = new THREE.TextureLoader().load(spec.contact);
    tex.colorSpace = THREE.NoColorSpace;
    k = {
      geo: markShared(new THREE.PlaneGeometry(c.x1 - c.x0, c.z1 - c.z0).rotateX(-Math.PI / 2)),
      mat: new THREE.MeshBasicMaterial({ color: 0x000000, alphaMap: tex, transparent: true, opacity: 0.55, depthWrite: false, fog: false }),
    };
    contacts.set(spec.contact, k);
  }
  const m = new THREE.Mesh(k.geo, k.mat);
  m.position.set((c.x0 + c.x1) / 2, 0.004, (c.z0 + c.z1) / 2);
  m.renderOrder = -1;
  m.userData.noEdge = true;
  return m;
}
