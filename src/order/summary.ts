import { byId, lampCategories, setLengths, sockets, trailerTypes } from "../config/catalog";
import type { Configuration } from "../state/config";

export interface SummaryLine {
  label: string;
  value: string;
}

export function summaryLines(config: Configuration): SummaryLine[] {
  const lines: SummaryLine[] = [
    { label: "Dorse tipi", value: byId(trailerTypes, config.trailerTypeId).label },
    { label: "Soket", value: byId(sockets, config.socketId).label },
    { label: "Set uzunluğu", value: byId(setLengths, config.setLengthId).label },
  ];
  for (const category of lampCategories) {
    const selection = config.lamps[category.id];
    if (!selection || selection.count === 0) continue;
    const product = byId(category.products, selection.productId);
    lines.push({ label: category.summaryLabel, value: `${selection.count} × ${product.code}` });
  }
  return lines;
}

/** Siparişin düz metin hali (e-posta gövdesi, panoya kopyalama vb.). */
export function summaryText(config: Configuration): string {
  return ["Sipariş özeti", ...summaryLines(config).map((l) => `${l.label}: ${l.value}`)].join("\n");
}
