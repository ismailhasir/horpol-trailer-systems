// Konfigüratör "Teklif al" penceresi. Ana sayfadaki teklif listesinden (sepet) tamamen ayrıdır (ADR-016):
// yalnızca bu yapılandırmayı içerir, sepete yazmaz, sepetten okumaz.
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Config } from '../configurator/data';
import type { CUi } from '../configurator/i18n';
import { summaryRows } from '../configurator/summary';
import type { Ui } from '../i18n/ui';
import type { Lang } from '../lib/labels';
import QuoteFields, { emptyQuote, validateQuote } from './QuoteFields';

interface Props {
  open: boolean;
  onClose: () => void;
  cfg: Config;
  qty: number;
  t: CUi;
  ui: Ui;
  lang: Lang;
}

export default function ConfigOrder({ open, onClose, cfg, qty, t, ui, lang }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState(emptyQuote);
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
    const err = validateQuote(form, ui);
    setError(err);
    if (!err) setDone(true);
  };

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
                <QuoteFields form={form} setForm={setForm} error={error} ui={ui} />
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
