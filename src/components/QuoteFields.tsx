// Teklif formunun alanları ve denetimi: ana sayfa teklif listesi (HeaderTools) ile konfigüratör "Teklif al" penceresi
// (ConfigOrder) aynı formu kullanır. Gönderim henüz yok (ADR-010): form doğrulanınca yalnız "hazırlandı" adımı gösterilir.
import type { Ui } from '../i18n/ui';

export interface QuoteForm {
  company: string;
  name: string;
  phone: string;
  email: string;
  tax: string;
  address: string;
  note: string;
  ok: boolean;
}
export const emptyQuote = (): QuoteForm => ({ company: '', name: '', phone: '', email: '', tax: '', address: '', note: '', ok: false });

/** Hata metni ya da boş dize (geçerli) */
export function validateQuote(f: QuoteForm, ui: Ui): string {
  if (![f.company, f.name, f.phone, f.email, f.tax, f.address].every((v) => v.trim())) return ui.err_fields;
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim())) return ui.err_email;
  if (!f.ok) return ui.err_consent;
  return '';
}

interface Props {
  form: QuoteForm;
  setForm: (fn: (f: QuoteForm) => QuoteForm) => void;
  error: string;
  ui: Ui;
}

export default function QuoteFields({ form, setForm, error, ui }: Props) {
  const set = (key: keyof QuoteForm) => (e: Event) => {
    const el = e.target as HTMLInputElement;
    setForm((f) => ({ ...f, [key]: el.type === 'checkbox' ? el.checked : el.value }));
  };
  // hata gösterilirken eksik (ya da biçimi yanlış e-posta) alan işaretlenir: ekran okuyucu da duyurur
  const bad = (key: 'company' | 'name' | 'phone' | 'email' | 'tax' | 'address') => !!error && (!form[key].trim() || (key === 'email' && error === ui.err_email));
  const field = (key: 'company' | 'name' | 'phone' | 'email' | 'tax', label: string, type = 'text', auto = '') => (
    <label>
      {label}
      <input class="input" type={type} autocomplete={auto} value={form[key]} required aria-invalid={bad(key)} onInput={set(key)} />
    </label>
  );
  return (
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
        <textarea class="input" rows={2} autocomplete="street-address" required aria-invalid={bad('address')} value={form.address} onInput={set('address')} />
      </label>
      <label>
        <span>
          {ui.f_note} <span class="opt">({ui.f_optional})</span>
        </span>
        <textarea class="input" rows={2} value={form.note} onInput={set('note')} />
      </label>
      <label class="consent">
        <input type="checkbox" checked={form.ok} onChange={set('ok')} />
        <span>{ui.f_consent}</span>
      </label>
      {error && (
        <p class="err" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
