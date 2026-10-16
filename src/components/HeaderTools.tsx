// Üst çubuktaki etkileşimli parça: ürün arama, teklif listesi (düğme + çekmece), ürün ayrıntı penceresi ve bildirim.
// Pencereler yerel <dialog> ile yapılır: odak kapanı, Esc ve arka plan tıklaması tarayıcıdan gelir.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { addToCart, removeFromCart, restoreItem, setMult, setQty, showToast, useCart, useMult, type ToastDetail } from '../lib/cart';
import { fmt, type Ui } from '../i18n/ui';
import type { DetailItem } from '../lib/format';
import type { Lang } from '../lib/labels';

interface Props {
  /** false: konfigüratör sayfası. Ürün arama ve teklif listesi (sepet) gösterilmez, yalnızca bildirim çalışır. */
  shop?: boolean;
  items: DetailItem[];
  ui: Ui;
  lang: Lang;
}
type Stage = 'list' | 'form' | 'done';

const Svg = ({ d, size = 20 }: { d: string[]; size?: number }) => (
  <svg class="icon" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
    {d.map((p) => (
      <path d={p} />
    ))}
  </svg>
);
const I = {
  search: ['M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z', 'm20 20-3.8-3.8'],
  cart: ['M3 4h2.4l2.1 10.2a1 1 0 0 0 1 .8h8.7a1 1 0 0 0 1-.76L20 8H6', 'M9.5 19.3h.01', 'M17 19.3h.01'],
  close: ['M6 6l12 12', 'M18 6 6 18'],
  download: ['M12 4v11', 'm7.5 11 4.5 4.5 4.5-4.5', 'M5 19.5h14'],
};

function useDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    const handle = () => onClose();
    d.addEventListener('close', handle);
    return () => d.removeEventListener('close', handle);
  }, [onClose]);
  const onBackdrop = (e: MouseEvent) => {
    if (e.target === ref.current) onClose();
  };
  return { ref, onBackdrop };
}

export default function HeaderTools({ items, ui, lang, shop = true }: Props) {
  const byId = useMemo(() => new Map(items.map((i) => [i.id, i])), [items]);
  const cart = useCart();
  const lines = cart.map((c) => ({ ...c, p: byId.get(c.id) })).filter((l): l is typeof l & { p: DetailItem } => !!l.p);
  const mult = useMult();
  const total = lines.reduce((a, l) => a + l.qty, 0) * mult;
  const itemCount = lines.length;
  const [pdfBusy, setPdfBusy] = useState(false);
  const downloadPdf = async () => {
    if (pdfBusy || !lines.length) return;
    setPdfBusy(true);
    try {
      const { downloadCartPdf } = await import('../lib/cart-pdf');
      await downloadCartPdf({ lines: lines.map((l) => ({ code: l.p.code, name: l.p.name, qty: l.qty })), mult, ui, lang });
    } catch (e) {
      console.error(e);
      showToast({ msg: ui.pdf_failed });
    } finally {
      setPdfBusy(false);
    }
  };

  const [searchOpen, setSearchOpen] = useState(false);
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(0);
  const [productId, setProductId] = useState<string | null>(null);
  const [pqty, setPqty] = useState(1);
  const [cartOpen, setCartOpen] = useState(false);
  const [stage, setStage] = useState<Stage>('list');
  const [toast, setToast] = useState<ToastDetail | null>(null);
  const [form, setForm] = useState({ company: '', name: '', phone: '', email: '', tax: '', address: '', note: '', ok: false });
  const [error, setError] = useState('');
  const toastRef = useRef<HTMLDivElement>(null);
  const toastTimer = useRef<number>(0);

  const closeSearch = () => setSearchOpen(false);
  const closeProduct = () => setProductId(null);
  const closeCart = () => {
    setCartOpen(false);
    setStage('list');
    setError('');
  };
  const search = useDialog(searchOpen, closeSearch);
  const prod = useDialog(productId !== null, closeProduct);
  const drawer = useDialog(cartOpen, closeCart);

  useEffect(() => {
    const onProduct = (e: Event) => {
      setProductId((e as CustomEvent<string>).detail);
      setPqty(1);
      setSearchOpen(false);
    };
    const onCart = () => {
      setStage('list');
      setCartOpen(true);
    };
    const onSearch = () => {
      setQ('');
      setSel(0);
      setSearchOpen(true);
    };
    const onToast = (e: Event) => setToast((e as CustomEvent<ToastDetail>).detail);
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onSearch();
      }
    };
    window.addEventListener('hts:product', onProduct);
    window.addEventListener('hts:cart', onCart);
    window.addEventListener('hts:search', onSearch);
    window.addEventListener('hts:toast', onToast);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('hts:product', onProduct);
      window.removeEventListener('hts:cart', onCart);
      window.removeEventListener('hts:search', onSearch);
      window.removeEventListener('hts:toast', onToast);
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  // Bildirim: üst katmanda (popover) gösterilir, böylece açık pencerelerin üstünde kalır.
  useEffect(() => {
    if (!toast) return;
    try {
      toastRef.current?.showPopover?.();
    } catch {
      /* popover desteklenmiyorsa öğe zaten görünür */
    }
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 4500);
    return () => window.clearTimeout(toastTimer.current);
  }, [toast]);

  const results = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase(lang);
    const list = needle ? items.filter((i) => `${i.code} ${i.name}`.toLocaleLowerCase(lang).includes(needle)) : items;
    return list.slice(0, 8);
  }, [q, items, lang]);

  const detail = productId ? byId.get(productId) : undefined;

  const removeLine = (id: string, qty: number) => {
    removeFromCart(id);
    showToast({ msg: ui.removed, action: { label: ui.undo, run: () => restoreItem({ id, qty }) } });
  };

  const submit = (e: Event) => {
    e.preventDefault();
    if (!form.company.trim() || !form.name.trim() || !form.phone.trim() || !form.email.trim() || !form.tax.trim() || !form.address.trim()) {
      setError(ui.err_fields);
      return;
    }
    if (!form.ok) {
      setError(ui.err_consent);
      return;
    }
    setError('');
    setStage('done');
  };

  const onSearchKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSel((s) => Math.min(results.length - 1, s + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSel((s) => Math.max(0, s - 1));
    } else if (e.key === 'Enter' && results[sel]) {
      e.preventDefault();
      setProductId(results[sel].id);
      setPqty(1);
      setSearchOpen(false);
    }
  };

  const field = (key: 'company' | 'name' | 'phone' | 'email' | 'tax', label: string, type = 'text', auto = '') => (
    <label>
      {label}
      <input
        class="input"
        type={type}
        autocomplete={auto}
        value={form[key]}
        required
        onInput={(e) => setForm((f) => ({ ...f, [key]: (e.target as HTMLInputElement).value }))}
      />
    </label>
  );

  return (
    <>
      {shop && (<>
      <button type="button" class="search-btn" aria-label={ui.search_btn} onClick={() => window.dispatchEvent(new CustomEvent('hts:search'))}>
        <Svg d={I.search} />
        <span>{ui.search_btn}</span>
      </button>
      <button type="button" class="icon-btn" aria-label={`${ui.cart_btn}${total ? ` (${total})` : ''}`} onClick={() => window.dispatchEvent(new CustomEvent('hts:cart'))}>
        <Svg d={I.cart} />
        {total > 0 && <span class="badge">{total}</span>}
      </button>

      {/* arama */}
      <dialog ref={search.ref} class="search-dlg" aria-label={ui.search_title} onClick={search.onBackdrop}>
        {searchOpen && (
          <div class="search-in">
            <input
              class="input"
              type="search"
              autofocus
              placeholder={ui.search_ph}
              aria-label={ui.search_title}
              value={q}
              onInput={(e) => {
                setQ((e.target as HTMLInputElement).value);
                setSel(0);
              }}
              onKeyDown={onSearchKey}
            />
            {results.length ? (
              <ul class="results" role="listbox">
                {results.map((r, i) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={i === sel}
                      onClick={() => {
                        setProductId(r.id);
                        setPqty(1);
                        setSearchOpen(false);
                      }}
                    >
                      <span class="code-inline mono ltr">{r.code}</span>
                      <span>{r.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p class="note" style="padding:8px 4px">
                {ui.search_empty}
              </p>
            )}
          </div>
        )}
      </dialog>

      {/* ürün ayrıntısı */}
      <dialog ref={prod.ref} aria-label={detail?.name} onClick={prod.onBackdrop}>
        {detail && (
          <div class="dlg">
            <button type="button" class="icon-btn dlg-x" aria-label={ui.close} onClick={closeProduct}>
              <Svg d={I.close} />
            </button>
            <div class="dlg-im">
              <img src={detail.img.src} srcset={detail.img.srcset} sizes="(max-width: 760px) 90vw, 380px" width={400} height={400} alt="" />
            </div>
            <div class="dlg-in">
              <span class="code-inline mono ltr">{detail.code}</span>
              <h2>{detail.name}</h2>
              <p class="desc">{detail.desc}</p>
              <table class="spec">
                <tbody>
                  {detail.specs.map((s) => (
                    <tr>
                      <th scope="row">{s.label}</th>
                      <td class="ltr" style="text-align:start">{s.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p class="note">{ui.spec_note}</p>
              <div class="buy">
                <div class="qty">
                  <button type="button" aria-label={ui.qty_dec} onClick={() => setPqty((n) => Math.max(1, n - 1))}>
                    −
                  </button>
                  <output>{pqty}</output>
                  <button type="button" aria-label={ui.qty_inc} onClick={() => setPqty((n) => Math.min(99, n + 1))}>
                    +
                  </button>
                </div>
                <button
                  type="button"
                  class="btn btn-primary"
                  onClick={() => {
                    addToCart(detail.id, pqty);
                    showToast({ msg: fmt(ui.added, { code: detail.code }) });
                    closeProduct();
                  }}
                >
                  {ui.add_to_list}
                </button>
              </div>
            </div>
          </div>
        )}
      </dialog>

      {/* teklif listesi */}
      <dialog ref={drawer.ref} class="drawer" aria-labelledby="cart-title" onClick={drawer.onBackdrop}>
        {cartOpen && (
          <>
            <div class="drawer-head">
              <h2 id="cart-title">{stage === 'form' ? ui.form_title : stage === 'done' ? ui.done_title : ui.cart_title}</h2>
              <div class="head-actions">
                {stage !== 'done' && itemCount > 0 && (
                  <button type="button" class="icon-btn" data-tip={ui.pdf_download} aria-label={ui.pdf_download} onClick={downloadPdf} disabled={pdfBusy}>
                    <Svg d={I.download} />
                  </button>
                )}
                <button type="button" class="icon-btn" aria-label={ui.close} onClick={closeCart}>
                  <Svg d={I.close} />
                </button>
              </div>
            </div>

            {stage === 'done' && (
              <>
                <div class="drawer-body">
                  <div class="done">
                    <h3>{ui.done_title}</h3>
                    <p>{ui.done_text}</p>
                  </div>
                </div>
                <div class="drawer-foot">
                  <button type="button" class="btn" onClick={closeCart}>
                    {ui.done_close}
                  </button>
                </div>
              </>
            )}

            {stage !== 'done' && itemCount === 0 && (
              <>
                <div class="drawer-body">
                  <div class="empty">{ui.cart_empty}</div>
                </div>
                <div class="drawer-foot">
                  <a
                    class="btn"
                    href="#urunler"
                    onClick={() => {
                      closeCart();
                    }}
                  >
                    {ui.cart_go}
                  </a>
                </div>
              </>
            )}

            {stage === 'list' && itemCount > 0 && (
              <>
                <div class="drawer-body">
                  <div class="mult">
                    <div>
                      <b>{ui.order_qty}</b>
                      <small>{ui.order_qty_hint}</small>
                    </div>
                    <div class="qty" role="group" aria-label={ui.order_qty}>
                      <button type="button" aria-label={ui.qty_dec} disabled={mult <= 1} onClick={() => setMult(mult - 1)}>
                        −
                      </button>
                      <output>{mult}</output>
                      <button type="button" aria-label={ui.qty_inc} disabled={mult >= 99} onClick={() => setMult(mult + 1)}>
                        +
                      </button>
                    </div>
                  </div>
                  {lines.map((l) => (
                    <div class="line" key={l.id}>
                      <div>
                        <div class="line-name">{l.p.name}</div>
                        <div class="line-code mono ltr">
                          {l.p.code}
                          {mult > 1 ? ` · ${l.qty} × ${mult} = ${l.qty * mult}` : ''}
                        </div>
                      </div>
                      <div class="qty">
                        <button type="button" aria-label={ui.qty_dec} onClick={() => setQty(l.id, l.qty - 1)}>
                          −
                        </button>
                        <output>{l.qty}</output>
                        <button type="button" aria-label={ui.qty_inc} onClick={() => setQty(l.id, l.qty + 1)}>
                          +
                        </button>
                      </div>
                      <button type="button" class="rm" onClick={() => removeLine(l.id, l.qty)}>
                        {ui.remove}
                      </button>
                    </div>
                  ))}
                </div>
                <div class="drawer-foot">
                  <button type="button" class="btn btn-primary" onClick={() => setStage('form')}>
                    {fmt(ui.cart_request, { n: itemCount })}
                  </button>
                </div>
              </>
            )}

            {stage === 'form' && itemCount > 0 && (
              <form class="contents-form" onSubmit={submit} noValidate style="display:contents">
                <div class="drawer-body">
                  <p class="summary">
                    {fmt(ui.items_count, { n: itemCount })}: {lines.map((l) => `${l.p.code} × ${l.qty * mult}`).join(', ')}
                  </p>
                  <div class="order">
                    {field('company', ui.f_company, 'text', 'organization')}
                    <div class="two">
                      {field('name', ui.f_name, 'text', 'name')}
                      {field('phone', ui.f_phone, 'tel', 'tel')}
                    </div>
                    {field('email', ui.f_email, 'email', 'email')}
                    {field('tax', ui.f_tax, 'text', 'off')}
                    <label>
                      {ui.f_address}
                      <textarea class="input" rows={2} autocomplete="street-address" required value={form.address} onInput={(e) => setForm((f) => ({ ...f, address: (e.target as HTMLTextAreaElement).value }))} />
                    </label>
                    <label>
                      <span>
                        {ui.f_note} <span class="opt">({ui.f_optional})</span>
                      </span>
                      <textarea class="input" rows={2} value={form.note} onInput={(e) => setForm((f) => ({ ...f, note: (e.target as HTMLTextAreaElement).value }))} />
                    </label>
                    <label class="consent">
                      <input type="checkbox" checked={form.ok} onChange={(e) => setForm((f) => ({ ...f, ok: (e.target as HTMLInputElement).checked }))} />
                      <span>{ui.f_consent}</span>
                    </label>
                    {error && (
                      <p class="err" role="alert">
                        {error}
                      </p>
                    )}
                  </div>
                </div>
                <div class="drawer-foot">
                  <button type="submit" class="btn btn-primary">
                    {ui.f_send}
                  </button>
                  <button type="button" class="btn" onClick={() => setStage('list')}>
                    {ui.f_back}
                  </button>
                </div>
              </form>
            )}
          </>
        )}
      </dialog>

      </>)}

      {toast && (
        <div class="toast" popover="manual" ref={toastRef} role="status">
          <span>{toast.msg}</span>
          {toast.action && (
            <button
              type="button"
              onClick={() => {
                toast.action?.run();
                setToast(null);
              }}
            >
              {toast.action.label}
            </button>
          )}
        </div>
      )}
    </>
  );
}
