import type { Configuration } from "../state/config";
import { summaryLines, summaryText } from "./summary";

// Siparişin nereye gideceği henüz netleşmedi. Şimdilik:
// - VITE_ORDER_ENDPOINT tanımlıysa siparişi JSON olarak oraya POST eder,
// - değilse e-posta istemcisini sipariş metniyle açar (VITE_ORDER_EMAIL).
// Hedef kesinleşince yalnızca bu dosya değişecek.

export type SendResult = { kind: "sent" } | { kind: "mail" };

export async function sendOrder(config: Configuration): Promise<SendResult> {
  const endpoint = import.meta.env.VITE_ORDER_ENDPOINT as string | undefined;
  if (endpoint) {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ configuration: config, summary: summaryLines(config), text: summaryText(config) }),
    });
    if (!res.ok) throw new Error(`Sipariş gönderilemedi (${res.status})`);
    return { kind: "sent" };
  }
  const to = (import.meta.env.VITE_ORDER_EMAIL as string | undefined) ?? "";
  const subject = encodeURIComponent("Horpol aydınlatma seti siparişi");
  const body = encodeURIComponent(summaryText(config));
  window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
  return { kind: "mail" };
}
