// Diller. Yeni dil eklemek için src/i18n/ui.ts ve src/data/products.ts içine de ekleyin.
export type Lang = 'tr' | 'en' | 'ru' | 'ar';
export const LANGS: Lang[] = ['tr', 'en', 'ru', 'ar'];
export const DEFAULT_LANG: Lang = 'tr';
export const RTL_LANGS: Lang[] = ['ar'];
export const isRtl = (lang: Lang) => RTL_LANGS.includes(lang);
export const LANG_NAMES: Record<Lang, string> = { tr: 'Türkçe', en: 'English', ru: 'Русский', ar: 'العربية' };

/** Sayı biçimi: Arapçada da Latin rakamları kullanılır (teknik değerler için). */
export const numberLocale = (lang: Lang) => (lang === 'ar' ? 'ar-u-nu-latn' : lang);
