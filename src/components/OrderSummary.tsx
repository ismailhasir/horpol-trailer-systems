import { useState } from "react";
import { sendOrder } from "../order/send";
import { summaryLines } from "../order/summary";
import type { Configuration } from "../state/config";

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "done"; message: string } | { kind: "error"; message: string };

export function OrderSummary({ config }: { config: Configuration }) {
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function submit() {
    setStatus({ kind: "sending" });
    try {
      const result = await sendOrder(config);
      setStatus({
        kind: "done",
        message: result.kind === "sent" ? "Siparişiniz gönderildi." : "Sipariş e-posta uygulamanızda açıldı.",
      });
    } catch (e) {
      setStatus({ kind: "error", message: e instanceof Error ? e.message : "Sipariş gönderilemedi." });
    }
  }

  return (
    <section className="section summary-section">
      <h2>Sipariş özeti</h2>
      <dl className="summary">
        {summaryLines(config).map((line) => (
          <div className="row" key={line.label}>
            <dt>{line.label}</dt>
            <dd>{line.value}</dd>
          </div>
        ))}
      </dl>
      <button type="button" className="btn-primary" onClick={submit} disabled={status.kind === "sending"}>
        {status.kind === "sending" ? "Gönderiliyor…" : "Siparişi gönder"}
      </button>
      {(status.kind === "done" || status.kind === "error") && (
        <p className={status.kind === "error" ? "notice error" : "notice"} role="status">
          {status.message}
        </p>
      )}
    </section>
  );
}
