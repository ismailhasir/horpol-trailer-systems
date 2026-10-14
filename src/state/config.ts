import { lampCategories, setLengths, sockets, trailerTypes, type LampCategoryId } from "../config/catalog";

export interface LampSelection {
  productId: string;
  count: number;
}

export interface Configuration {
  trailerTypeId: string;
  socketId: string;
  setLengthId: string;
  lamps: Record<LampCategoryId, LampSelection>;
}

export function defaultConfiguration(): Configuration {
  const lamps = Object.fromEntries(
    lampCategories.map((c) => [c.id, { productId: c.products[0].id, count: c.count.default }]),
  ) as Record<LampCategoryId, LampSelection>;
  return {
    trailerTypeId: trailerTypes[0].id,
    socketId: sockets[0].id,
    setLengthId: setLengths[0].id,
    lamps,
  };
}
