// Ürün listesi: kategori filtresi, liste içi arama, adetli ekleme. Ayrıntı penceresi HeaderTools içindedir (olayla açılır).
import { useMemo, useState } from 'preact/hooks';
import { addToCart, openProduct, showToast } from '../lib/cart';
import { fmt, type Ui } from '../i18n/ui';
import type { CardItem } from '../lib/format';
import type { Lang } from '../lib/labels';
import SetVisual from './SetVisual';

interface Props {
  items: CardItem[];
  ui: Ui;
  lang: Lang;
}
type Filter = 'all' | CardItem['cat'];

export default function Catalog({ items, ui, lang }: Props) {
  const [filter, setFilter] = useState<Filter>('all');
  const [q, setQ] = useState('');
  const [qty, setQty] = useState<Record<string, number>>({});

  const tabs: { key: Filter; label: string }[] = [
    { key: 'all', label: ui.cat_all },
    { key: 'set', label: ui.cat_set },
    { key: 'cable', label: ui.cat_cable },
    { key: 'socket', label: ui.cat_socket },
  ];
  const kindLabel = { set: ui.cat_set, cable: ui.cat_cable, socket: ui.cat_socket };
  const countOf = (k: Filter) => (k === 'all' ? items.length : items.filter((i) => i.cat === k).length);

  const rows = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase(lang);
    return items.filter(
      (i) => (filter === 'all' || i.cat === filter) && (!needle || `${i.code} ${i.name} ${i.keys}`.toLocaleLowerCase(lang).includes(needle)),
    );
  }, [items, filter, q, lang]);

  const get = (id: string) => qty[id] ?? 1;
  const step = (id: string, d: number) => setQty((s) => ({ ...s, [id]: Math.max(1, Math.min(99, (s[id] ?? 1) + d)) }));
  const add = (it: CardItem) => {
    addToCart(it.id, get(it.id));
    setQty((s) => ({ ...s, [it.id]: 1 }));
    showToast({ msg: fmt(ui.added, { code: it.code }) });
  };

  return (
    <div>
      <div class="toolbar">
        <div class="seg" role="group" aria-label={ui.nav_products}>
          {tabs.map((t) => (
            <button type="button" aria-pressed={filter === t.key} onClick={() => setFilter(t.key)}>
              {t.label}
              <span class="n">{countOf(t.key)}</span>
            </button>
          ))}
        </div>
        <label class="list-search">
          <span class="sr-only">{ui.list_search}</span>
          <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z" />
            <path d="m20 20-3.8-3.8" />
          </svg>
          <input class="input" type="search" placeholder={ui.list_search} value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />
        </label>
      </div>
      <p class="count" aria-live="polite">
        {fmt(ui.results, { n: rows.length })}
      </p>
      <div class="grid">
        {rows.length === 0 && <div class="empty">{ui.empty_results}</div>}
        {rows.map((it) => (
          <article class="card" key={it.id}>
            <button type="button" class="card-ph" onClick={() => openProduct(it.id)} aria-label={`${it.name}: ${ui.detail_open}`}>
              {it.lamps ? (
                <SetVisual lamps={it.lamps} sizes="(max-width: 560px) 40vw, 120px" />
              ) : (
                it.img && <img src={it.img.src} srcset={it.img.srcset} sizes="(max-width: 560px) 90vw, 280px" width={400} height={400} alt="" loading="lazy" decoding="async" />
              )}
              {it.code !== it.name && <span class="code">{it.code}</span>}
            </button>
            <div class="card-body">
              <span class="kind">{kindLabel[it.cat]}</span>
              <h3>
                <button type="button" onClick={() => openProduct(it.id)}>
                  {it.name}
                </button>
              </h3>
              {it.lamps ? (
                <ul class="set-list" aria-label={ui.set_lamps}>
                  {it.lamps.map((l) => (
                    <li key={l.id}>
                      <span class="q ltr">{l.qty}×</span>
                      <span class="c mono ltr">{l.code}</span>
                      <span class="nm">{l.name}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{it.desc}</p>
              )}
              <div class="buy">
                <div class="qty">
                  <button type="button" aria-label={ui.qty_dec} onClick={() => step(it.id, -1)}>
                    −
                  </button>
                  <output aria-live="polite">{get(it.id)}</output>
                  <button type="button" aria-label={ui.qty_inc} onClick={() => step(it.id, 1)}>
                    +
                  </button>
                </div>
                <button type="button" class="btn btn-primary btn-sm" onClick={() => add(it)}>
                  {ui.add}
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
