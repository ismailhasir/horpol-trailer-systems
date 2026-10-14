import { byId, lampCategories, type LampCategory } from "../config/catalog";
import type { LampSelection } from "../state/config";
import { configStore, useConfiguration } from "../state/store";
import { OrderSummary } from "./OrderSummary";

function setLamp(category: LampCategory, patch: Partial<LampSelection>) {
  configStore.set((c) => ({ ...c, lamps: { ...c.lamps, [category.id]: { ...c.lamps[category.id], ...patch } } }));
}

function LampSection({ category, selection }: { category: LampCategory; selection: LampSelection }) {
  const product = byId(category.products, selection.productId);
  const { min, max, step } = category.count;
  return (
    <section className="section">
      <h2>{category.title}</h2>
      <div className="product">
        {product.image && <img src={product.image} alt="" width={72} height={48} loading="lazy" decoding="async" />}
        <div>
          <strong>{product.code}</strong>
          <span>{product.name}</span>
        </div>
      </div>
      {category.products.length > 1 && (
        <label className="field">
          <span className="field-label">Model</span>
          <select value={selection.productId} onChange={(e) => setLamp(category, { productId: e.target.value })}>
            {category.products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className="field count-row">
        <span className="field-label">Adet</span>
        {min === max ? (
          <span className="count">{selection.count}</span>
        ) : (
          <div className="stepper">
            <button
              type="button"
              aria-label={`${category.title} azalt`}
              disabled={selection.count <= min}
              onClick={() => setLamp(category, { count: Math.max(min, selection.count - step) })}
            >
              −
            </button>
            <span className="count" aria-live="polite">
              {selection.count}
            </span>
            <button
              type="button"
              aria-label={`${category.title} artır`}
              disabled={selection.count >= max}
              onClick={() => setLamp(category, { count: Math.min(max, selection.count + step) })}
            >
              +
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

export function LampPanel() {
  const config = useConfiguration();
  return (
    <>
      {lampCategories.map((category) => (
        <LampSection key={category.id} category={category} selection={config.lamps[category.id]} />
      ))}
      <OrderSummary config={config} />
    </>
  );
}
