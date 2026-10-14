// Konfigüratörün tüm seçenekleri burada. Yeni bir dorse tipi, soket, set
// uzunluğu, lamba ürünü ya da lamba kategorisi eklemek için yalnızca bu
// dosyadaki listelere satır eklemek yeterli; paneller ve sipariş özeti
// buradan otomatik üretilir.

export type TrailerBodyKind = "box" | "curtain" | "tipper";

export interface TrailerType {
  id: string;
  label: string;
  body: {
    kind: TrailerBodyKind;
    /** Kasa yüksekliği (m), şasi üstünden. */
    height: number;
    color: string;
  };
}

export interface SetLength {
  id: string;
  label: string;
  /** Dorse boyu (m); sahnede kasa bu uzunlukta çizilir. */
  meters: number;
}

export interface Socket {
  id: string;
  label: string;
  /** Ön panelde gösterilecek fiş sayısı. */
  plugs: number;
}

export interface LampProduct {
  id: string;
  /** Sipariş özetinde görünen kod. */
  code: string;
  name: string;
  image?: string;
}

export type LampCategoryId = "stop" | "side" | "plate";

export interface LampCategory {
  id: LampCategoryId;
  /** Panel başlığı. */
  title: string;
  /** Sipariş özeti satır etiketi. */
  summaryLabel: string;
  /** Yanık lamba rengi (sahnede). */
  glow: string;
  count: { min: number; max: number; step: number; default: number };
  products: LampProduct[];
}

export const trailerTypes: TrailerType[] = [
  { id: "standard", label: "Standart Dorse", body: { kind: "curtain", height: 2.75, color: "#d9dee6" } },
  { id: "reefer", label: "Frigorifik Dorse", body: { kind: "box", height: 2.8, color: "#f4f6f9" } },
  { id: "tipper", label: "Damperli Dorse", body: { kind: "tipper", height: 1.5, color: "#9aa4b1" } },
];

export const sockets: Socket[] = [
  { id: "7x2", label: "7x2", plugs: 2 },
  { id: "15pin", label: "15 pin", plugs: 1 },
  { id: "7x2+15pin", label: "7x2 + 15 pin", plugs: 3 },
];

export const setLengths: SetLength[] = [
  { id: "13.60", label: "13,60 mt", meters: 13.6 },
  { id: "12.00", label: "12 mt", meters: 12 },
  { id: "9.00", label: "9 mt", meters: 9 },
];

export const lampCategories: LampCategory[] = [
  {
    id: "stop",
    title: "Stop lambaları",
    summaryLabel: "Stop",
    glow: "#ff2a1a",
    count: { min: 2, max: 2, step: 2, default: 2 },
    products: [
      { id: "lzd-3049", code: "LZD 3049/H101/AMP1", name: "LZD 3049 stop lambası", image: "/products/lzd-3049.webp" },
    ],
  },
  {
    id: "side",
    title: "Yan marker lambaları",
    summaryLabel: "Yan marker",
    glow: "#ffa21a",
    count: { min: 4, max: 18, step: 2, default: 8 },
    products: [
      { id: "ld-2774", code: "LD 2774", name: "LD 2774 yan marker", image: "/products/ld-2774.webp" },
    ],
  },
  {
    id: "plate",
    title: "Plaka aydınlatması",
    summaryLabel: "Plaka",
    glow: "#fff4dc",
    count: { min: 2, max: 2, step: 2, default: 2 },
    products: [
      { id: "ltd-2834", code: "LTD 2834", name: "LTD 2834 plaka lambası", image: "/products/ltd-2834.webp" },
    ],
  },
];

export function byId<T extends { id: string }>(list: T[], id: string): T {
  const found = list.find((item) => item.id === id);
  if (!found) throw new Error(`Bilinmeyen seçenek: ${id}`);
  return found;
}
