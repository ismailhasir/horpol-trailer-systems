// Konfigüratör "Teklif al" penceresi. Ana sayfadaki teklif listesinden (sepet) tamamen ayrıdır (ADR-016):
// yalnızca bu yapılandırmayı içerir, sepete yazmaz, sepetten okumaz.
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Config } from '../configurator/data';
import type { CUi } from '../configurator/i18n';
import { summaryRows } from '../configurator/summary';
import type { Ui } from '../i18n/ui';
import type { Lang } from '../lib/labels';

interface Props {
  open: boolean;
  onClose: () => void;
  cfg: Config;
  qty: number;
  t: CUi;
  ui: Ui;
  lang: Lang;
}

const empty = { company: '', name: '', phone: '', email: '', tax: '', address: '', note: '', ok: false };

export default function ConfigOrder({ open, onClose, cfg, qty, t, ui, lang }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState(empty);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      setDone(false);
      setError('');
      d.showModal();
    }
    if (!open && d.open) d.close();
  }, [open]);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    d.addEventListener('close', onClose);
    return () => d.removeEventListener('close', onClose);
  }, [onClose]);

  const rows = summaryRows(cfg, t, lang, qty);

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
    setDone(true);
  };

  const field = (key: 'company' | 'name' | 'phone' | 'email' | 'tax', label: string, type = 'text', auto = '') => (
    <label>
      {label}
      <input class="input" type={type} autocomplete={auto} value={form[key]} required onInput={(e) => setForm((f) => ({ ...f, [key]: (e.target as HTMLInputElement).value }))} />
    </label>
  );

  return (
    <dialog ref={ref} class="drawer" aria-labelledby="co-title" onClick={(e) => e.target === ref.current && onClose()}>
      {open && (
        <>
          <div class="drawer-head">
            <h2 id="co-title">{done ? ui.done_title : t.quote_title}</h2>
            <button type="button" class="icon-btn" aria-label={ui.close} onClick={onClose}>
              <svg class="icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path d="M6 6l12 12" />
                <path d="M18 6 6 18" />
              </svg>
            </button>
          </div>

          {done ? (
            <>
              <div class="drawer-body">
                <div class="done">
                  <h3>{ui.done_title}</h3>
                  <p>{ui.done_text}</p>
                </div>
              </div>
              <div class="drawer-foot">
                <button type="button" class="btn" onClick={onClose}>
                  {ui.done_close}
                </button>
              </div>
            </>
          ) : (
            <form onSubmit={submit} noValidate style="display:contents">
              <div class="drawer-body">
                <dl class="co-sum">
                  {rows.map((r) => (
                    <div>
                      <dt>{r.label}</dt>
                      <dd class={r.mono ? 'mono ltr' : ''}>{r.value}</dd>
                    </div>
                  ))}
                </dl>
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
                  {t.get_quote}
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </dialog>
  );
}
