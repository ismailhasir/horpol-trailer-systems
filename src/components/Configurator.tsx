// 3D konfigüratör arayüzü (Preact). Motor (three.js) ayrı parçada, dinamik import ile yüklenir.
// Durum tek bir Config nesnesidir: adres satırına yazılır (paylaşılabilir), özet ve sepet aynı nesneden üretilir.
import { useCallback, useEffect, useMemo, useRef, useState } from 'preact/hooks';
import {
  CATEGORIES,
  DEFAULT_CONFIG,
  LENGTHS,
  SOCKETS,
  TRAILER_LIST,
  fromQuery,
  normalize,
  productById,
  toQuery,
  type CategoryId,
  type Config,
  type LampStyle,
  type LengthId,
  type TrailerId,
} from '../configurator/data';
import { categoryName, socketName, trailerDesc, trailerName, type CUi } from '../configurator/i18n';
import { summaryRows } from '../configurator/summary';
import { showToast } from '../lib/cart';
import ConfigOrder from './ConfigOrder';
import { numberLocale, type Lang } from '../lib/labels';
import type { Ui } from '../i18n/ui';
import TrailerIcon from './TrailerIcon';
import type { Engine, View } from '../configurator/engine/Engine';

interface Props {
  lang: Lang;
  t: CUi;
  ui: Ui;
}

const Ico = ({ d, size = 18 }: { d: string[]; size?: number }) => (
  <svg class="icon" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false">
    {d.map((p) => (
      <path d={p} />
    ))}
  </svg>
);
const IC = {
  chevron: ['m6 9 6 6 6-6'],
  check: ['m4.5 12.5 4.5 4.5L19.5 6.5'],
  wire: ['M4 7h6a4 4 0 0 1 4 4v2a4 4 0 0 0 4 4h2', 'M4 4v6', 'M20 14v6'],
  moon: ['M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a6.8 6.8 0 0 0 10.7 10.7Z'],
  reset: ['M3 12a9 9 0 1 0 3-6.7', 'M3 4v5h5'],
  download: ['M12 4v11', 'm7.5 11 4.5 4.5 4.5-4.5', 'M5 19.5h14'],
  cart: ['M3 4h2.4l2.1 10.2a1 1 0 0 0 1 .8h8.7a1 1 0 0 0 1-.76L20 8H6', 'M9.5 19.3h.01', 'M17 19.3h.01'],
  send: ['M4 12 20 4l-4 16-4-6-8-2Z', 'm12 14 8-10'],
  collapse: ['M4 14h6v6', 'M20 10h-6V4', 'm14 10 7-7', 'm3 21 7-7'],
  expand: ['M15 3h6v6', 'M9 21H3v-6', 'm21 3-7 7', 'm3 21 7-7'],
};

/** Ürün seçeneği için küçük temsili lamba çizimi */
function LampGlyph({ style }: { style: LampStyle }) {
  const r = '#d4221c';
  const a = '#f29a0c';
  const w = '#dfe6f0';
  const h = '#1d2026';
  const body = (children: preact.ComponentChildren) => (
    <svg class="lglyph" viewBox="0 0 40 20" width="40" height="20" aria-hidden="true">
      {children}
    </svg>
  );
  switch (style) {
    case 'block':
      return body(<><rect x="2" y="4" width="36" height="12" rx="2" fill={h} /><rect x="4" y="5.5" width="8" height="9" rx="1" fill={a} /><rect x="13" y="5.5" width="10" height="9" rx="1" fill={r} /><rect x="24" y="5.5" width="7" height="9" rx="1" fill={r} /><rect x="32" y="5.5" width="4.5" height="9" rx="1" fill={w} /></>);
    case 'carmen':
      return body(<><rect x="1" y="5" width="38" height="10" rx="4" fill={h} /><rect x="3" y="6.4" width="34" height="2.2" rx="1" fill={a} /><rect x="3" y="9.5" width="27" height="4" rx="1.5" fill={r} /><rect x="31" y="9.5" width="5.5" height="4" rx="1.5" fill={w} /></>);
    case 'navia':
      return body(<><rect x="6" y="2.5" width="28" height="15" rx="6" fill={h} /><rect x="8" y="4.5" width="24" height="7" rx="3.5" fill={r} /><rect x="10" y="12.5" width="13" height="3" rx="1.5" fill={a} /><circle cx="27.5" cy="14" r="2" fill={w} /></>);
    case 'compact':
      return body(<><rect x="9" y="4" width="22" height="12" rx="2" fill={h} /><rect x="11" y="5.5" width="6" height="9" rx="1" fill={a} /><rect x="18" y="5.5" width="11" height="9" rx="1" fill={r} /></>);
    case 'round':
      return body(<><rect x="2" y="4" width="36" height="12" rx="3" fill={h} /><circle cx="9" cy="10" r="4.3" fill={a} /><circle cx="20" cy="10" r="4.3" fill={r} /><circle cx="31" cy="10" r="4.3" fill={r} /></>);
    case 'oval':
      return body(<><rect x="8" y="5" width="24" height="10" rx="5" fill={h} /><rect x="10" y="6.5" width="20" height="7" rx="3.5" fill={a} /></>);
    case 'rect':
      return body(<><rect x="9" y="5" width="22" height="10" rx="1.5" fill={h} /><rect x="11" y="6.6" width="18" height="6.8" rx="1" fill={a} /></>);
    case 'slim':
      return body(<><rect x="4" y="7" width="32" height="6" rx="3" fill={h} /><rect x="6" y="8.3" width="28" height="3.4" rx="1.7" fill={a} /></>);
    case 'disc':
      return body(<><circle cx="20" cy="10" r="7" fill={h} /><circle cx="20" cy="10" r="5.2" fill={a} /></>);
    case 'plate-wide':
    case 'plate-small': {
      const wd = style === 'plate-wide' ? 26 : 16;
      return body(<><rect x={20 - wd / 2} y="5" width={wd} height="7" rx="1.5" fill={h} /><rect x={20 - wd / 2 + 2} y="11" width={wd - 4} height="2.5" rx="1" fill={w} /></>);
    }
    case 'pos-rect':
      return body(<><rect x="10" y="5" width="20" height="10" rx="2" fill={h} /><rect x="12" y="6.6" width="16" height="6.8" rx="1.4" fill={w} /></>);
    case 'pos-round':
      return body(<><circle cx="20" cy="10" r="7" fill={h} /><circle cx="20" cy="10" r="5" fill={w} /></>);
    case 'strip':
      return body(<><rect x="5" y="7.5" width="30" height="5" rx="2.5" fill={h} /><rect x="7" y="8.8" width="26" height="2.4" rx="1.2" fill={r} /></>);
    case 'arm-dragon':
      return body(<><path d="M8 16 22 7" stroke={h} stroke-width="3" stroke-linecap="round" /><rect x="21" y="3" width="12" height="8" rx="1.5" fill={h} /><rect x="22" y="4.2" width="3.5" height="5.6" fill={w} /><rect x="26" y="4.2" width="3" height="5.6" fill={a} /><rect x="29.5" y="4.2" width="2.5" height="5.6" fill={r} /></>);
    case 'arm-classic':
      return body(<><path d="M6 10h16" stroke={h} stroke-width="3" stroke-linecap="round" /><rect x="21" y="6" width="12" height="8" rx="1.5" fill={h} /><rect x="22" y="7.2" width="3.5" height="5.6" fill={w} /><rect x="26" y="7.2" width="3" height="5.6" fill={a} /><rect x="29.5" y="7.2" width="2.5" height="5.6" fill={r} /></>);
  }
}

const CAT_DOT: Record<CategoryId, string> = { stop: '#d4221c', side: '#f29a0c', plate: '#c9d2de', front: '#e9eef6', arm: '#22c55e', extra: '#38bdf8' };

export default function Configurator({ lang, t, ui }: Props) {
  const [cfg, setCfg] = useState<Config>(() => {
    if (typeof location !== 'undefined' && location.search) return fromQuery(location.search);
    return structuredClone(DEFAULT_CONFIG);
  });
  const [status, setStatus] = useState<'loading' | 'ready' | 'fail'>('loading');
  const [view, setView] = useState<View>('overview');
  const [system, setSystem] = useState(false);
  const [lights, setLights] = useState(false);
  const [openCat, setOpenCat] = useState<CategoryId | null>('stop');
  const [ddOpen, setDdOpen] = useState(false);
  const [ddIdx, setDdIdx] = useState(0);
  const [tab, setTab] = useState<'trailer' | 'lamps' | 'summary'>('trailer');
  const [touch, setTouch] = useState(false);
  /** sol panel: ayrıntılı (varsayılan) ya da yalnızca seçimleri gösteren sade şerit */
  const [compact, setCompact] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<Engine | null>(null);
  const ddRef = useRef<HTMLDivElement>(null);

  // --- motor ---
  useEffect(() => {
    let alive = true;
    setTouch(matchMedia('(pointer: coarse)').matches);
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const theme = () => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light') as 'dark' | 'light';
    let mo: MutationObserver | null = null;
    (async () => {
      try {
        const { Engine } = await import('../configurator/engine/Engine');
        if (!alive || !canvasRef.current) return;
        const eng = new Engine(canvasRef.current, {
          theme: theme(),
          reducedMotion: reduced,
          onPick: (c) => {
            setOpenCat(c);
            setTab('lamps');
            eng.focusCategory(c);
          },
        });
        const model = eng.preload(cfgRef.current.trailer);
        await eng.init();
        await model;
        if (!alive) {
          eng.dispose();
          return;
        }
        engineRef.current = eng;
        if (import.meta.env.DEV) (window as unknown as { __engine: Engine }).__engine = eng;
        eng.setConfig(cfgRef.current);
        setStatus('ready');
        mo = new MutationObserver(() => eng.setTheme(theme()));
        mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      } catch (e) {
        console.error(e);
        if (alive) setStatus('fail');
      }
    })();
    return () => {
      alive = false;
      mo?.disconnect();
      engineRef.current?.dispose();
      engineRef.current = null;
    };
  }, []);

  // paneller sahnenin üstünde: kameraya boş alanı bildir
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = rootRef.current;
    if (!root || status !== 'ready') return;
    const measure = () => {
      const eng = engineRef.current;
      if (!eng) return;
      const overlay = getComputedStyle(root.querySelector('.cfg-right')!).position === 'absolute';
      if (!overlay) {
        eng.setInsets({ left: 0, right: 0, top: 0, bottom: 52 });
        return;
      }
      const rtl = document.documentElement.dir === 'rtl';
      const left = root.querySelector('.cfg-left') as HTMLElement;
      const l = left.offsetWidth;
      const r = (root.querySelector('.cfg-right') as HTMLElement).offsetWidth;
      // sade şerit yalnızca sol üst köşeyi kaplar: dorse altından geçebilir, soldan pay gerekmez
      const side = { a: compact ? 0 : l + 24, b: r + 32 };
      const top = compact ? left.offsetHeight * 0.5 : 0;
      eng.setInsets({ left: rtl ? side.b : side.a, right: rtl ? side.a : side.b, top, bottom: 64 }, true);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(root);
    return () => ro.disconnect();
  }, [status, compact]);

  const cfgRef = useRef(cfg);
  useEffect(() => {
    cfgRef.current = cfg;
    engineRef.current?.setConfig(cfg);
    const q = toQuery(cfg);
    if (location.search.slice(1) !== q) history.replaceState(null, '', `${location.pathname}?${q}`);
  }, [cfg]);

  // açılır liste dışına tıklanınca kapanır
  useEffect(() => {
    if (!ddOpen) return;
    const f = (e: MouseEvent) => {
      if (ddRef.current && !ddRef.current.contains(e.target as Node)) setDdOpen(false);
    };
    document.addEventListener('mousedown', f);
    return () => document.removeEventListener('mousedown', f);
  }, [ddOpen]);

  const update = (fn: (c: Config) => Config) => setCfg((c) => normalize(fn(structuredClone(c))));
  const trailerDef = TRAILER_LIST.find((x) => x.id === cfg.trailer)!;
  const nf = useMemo(() => new Intl.NumberFormat(numberLocale(lang), { minimumFractionDigits: 0, maximumFractionDigits: 2 }), [lang]);
  const lenLabel = (l: LengthId) => `${l === '13.6' ? new Intl.NumberFormat(numberLocale(lang), { minimumFractionDigits: 2 }).format(13.6) : nf.format(Number(l))} ${t.length_unit}`;
  /** aynı siparişten kaç set (tüm yapılandırma bu sayıyla çarpılır) */
  const [orderQty, setOrderQty] = useState(1);
  const rows = summaryRows(cfg, t, lang, orderQty);
  const stepper = (
    <div class="qty" role="group" aria-label={t.set_qty} title={t.set_qty}>
      <button type="button" aria-label={ui.qty_dec} disabled={orderQty <= 1} onClick={() => setOrderQty((q) => Math.max(1, q - 1))}>
        −
      </button>
      <output>{orderQty}</output>
      <button type="button" aria-label={ui.qty_inc} disabled={orderQty >= 99} onClick={() => setOrderQty((q) => Math.min(99, q + 1))}>
        +
      </button>
    </div>
  );

  const chooseTrailer = (id: TrailerId) => {
    update((c) => ({ ...c, trailer: id }));
    setDdOpen(false);
  };
  const onDdKey = (e: KeyboardEvent) => {
    if (!ddOpen && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      setDdIdx(TRAILER_LIST.findIndex((x) => x.id === cfg.trailer));
      setDdOpen(true);
      return;
    }
    if (!ddOpen) return;
    if (e.key === 'Escape') setDdOpen(false);
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setDdIdx((i) => Math.min(TRAILER_LIST.length - 1, i + 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setDdIdx((i) => Math.max(0, i - 1));
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      chooseTrailer(TRAILER_LIST[ddIdx].id);
    }
  };

  const step = (cat: CategoryId, dir: 1 | -1) => {
    const def = CATEGORIES.find((c) => c.id === cat)!;
    update((c) => {
      c.lamps[cat].qty += dir * def.step;
      return c;
    });
    engineRef.current?.focusCategory(cat);
  };
  const pickProduct = (cat: CategoryId, id: string) => {
    update((c) => {
      c.lamps[cat].product = id;
      if (c.lamps[cat].qty === 0) c.lamps[cat].qty = CATEGORIES.find((x) => x.id === cat)!.step;
      return c;
    });
    engineRef.current?.focusCategory(cat);
  };
  const toggleCat = (cat: CategoryId) => {
    setOpenCat((o) => (o === cat ? null : cat));
    engineRef.current?.focusCategory(cat);
  };
  const go = (v: View) => {
    setView(v);
    if (system) {
      setSystem(false);
      engineRef.current?.setSystem(false);
    }
    engineRef.current?.setView(v);
  };
  const toggleSystem = () => {
    const on = !system;
    setSystem(on);
    engineRef.current?.setSystem(on);
  };
  const toggleLights = () => {
    const on = !lights;
    setLights(on);
    engineRef.current?.setLights(on);
  };
  const reset = () => {
    setCfg(structuredClone(DEFAULT_CONFIG));
    setOrderQty(1);
    setView('overview');
    engineRef.current?.setView('overview');
  };
  /** Konfigüratör siparişi ana sayfa sepetinden ayrıdır: kendi penceresi açılır (ADR-016) */
  const [orderOpen, setOrderOpen] = useState(false);
  const closeOrder = useCallback(() => setOrderOpen(false), []);
  const send = () => setOrderOpen(true);
  const [pdfBusy, setPdfBusy] = useState(false);
  const downloadPdf = async () => {
    if (pdfBusy) return;
    setPdfBusy(true);
    try {
      const { downloadSummaryPdf } = await import('../configurator/pdf');
      await downloadSummaryPdf({ cfg, qty: orderQty, t, lang, url: location.href, siteName: ui.site_name });
    } catch (e) {
      console.error(e);
      showToast({ msg: t.pdf_failed });
    } finally {
      setPdfBusy(false);
    }
  };

  const views: [View, string][] = [
    ['overview', t.view_overview],
    ['rear', t.view_rear],
    ['side', t.view_side],
    ['front', t.view_front],
    ['top', t.view_top],
  ];

  return (
    <div class="cfg" data-tab={tab} ref={rootRef}>
      {/* ---------- sahne ---------- */}
      <section class="cfg-stage" aria-label={t.title}>
        <canvas ref={canvasRef} class={status === 'ready' ? 'ready' : ''} />
        {status === 'loading' && (
          <div class="cfg-loading" role="status">
            <span class="spinner" aria-hidden="true" />
            {t.loading}
          </div>
        )}
        {status === 'fail' && (
          <div class="cfg-loading fail" role="alert">
            {t.webgl_fail}
          </div>
        )}
        {system && (
          <ul class="cfg-legend" aria-label={t.system}>
            <li><i style="background:#3b82f6" />{t.legend_main}</li>
            <li><i style="background:#f59e0b" />{t.legend_side}</li>
            <li><i style="background:#ef4444" />{t.legend_rear}</li>
            <li><i style="background:#e5e7eb" />{t.legend_plate}</li>
            <li><i style="background:#22c55e" />{t.legend_marker}</li>
          </ul>
        )}
        <p class="cfg-hint">{touch ? t.hint_touch : t.hint}</p>
        <div class="cfg-tools" role="toolbar" aria-label={t.view_label}>
          <div class="cfg-views">
            {views.map(([v, label]) => (
              <button type="button" data-v={v} aria-pressed={!system && view === v} onClick={() => go(v)}>
                {label}
              </button>
            ))}
          </div>
          <span class="sep" />
          <button type="button" class="cfg-tog" aria-pressed={system} onClick={toggleSystem} title={t.system}>
            <Ico d={IC.wire} />
            <span>{t.system}</span>
          </button>
          <button type="button" class="cfg-tog" aria-pressed={lights} onClick={toggleLights} title={t.lights}>
            <Ico d={IC.moon} />
            <span>{t.lights}</span>
          </button>
          <button type="button" class="cfg-ic" onClick={reset} title={t.reset} aria-label={t.reset}>
            <Ico d={IC.reset} />
          </button>
        </div>
      </section>

      {/* ---------- mobil sekmeler ---------- */}
      <div class="cfg-tabs" role="tablist">
        {(['trailer', 'lamps', 'summary'] as const).map((k) => (
          <button type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>
            {k === 'trailer' ? t.tab_trailer : k === 'lamps' ? t.tab_lamps : t.tab_summary}
          </button>
        ))}
      </div>

      {/* ---------- sol: dorse ---------- */}
      <aside class={`cfg-card cfg-left${compact ? ' compact' : ''}`} aria-label={t.trailer_label}>
        {compact && (
          <button type="button" class="cfg-compact" onClick={() => setCompact(false)} title={t.expand} aria-label={`${t.expand}: ${trailerName(t, cfg.trailer)}, ${socketName(t, cfg.socket)}, ${lenLabel(cfg.length)}`}>
            <span class="cc-item">
              <small>{t.tab_trailer}</small>
              <TrailerIcon id={cfg.trailer} />
            </span>
            <span class="cc-sep" aria-hidden="true" />
            <span class="cc-item">
              <small>{t.socket_label}</small>
              <b>{socketName(t, cfg.socket)}</b>
            </span>
            <span class="cc-sep" aria-hidden="true" />
            <span class="cc-item">
              <small>{t.length_label}</small>
              <b>{lenLabel(cfg.length)}</b>
            </span>
            <span class="cc-exp" aria-hidden="true">
              <Ico d={IC.expand} size={16} />
            </span>
          </button>
        )}
        {!compact && (
          <button type="button" class="cfg-ic sm cfg-collapse" onClick={() => setCompact(true)} title={t.collapse} aria-label={t.collapse}>
            <Ico d={IC.collapse} size={16} />
          </button>
        )}
        {!compact && (<>
        <div class="cfg-field">
          <span class="cfg-label" id="dd-label">{t.trailer_label}</span>
          <div class={`dd ${ddOpen ? 'open' : ''}`} ref={ddRef}>
            <button
              type="button"
              class="dd-btn"
              aria-haspopup="listbox"
              aria-expanded={ddOpen}
              aria-labelledby="dd-label"
              onClick={() => {
                setDdIdx(TRAILER_LIST.findIndex((x) => x.id === cfg.trailer));
                setDdOpen(!ddOpen);
              }}
              onKeyDown={onDdKey}
            >
              <TrailerIcon id={cfg.trailer} />
              <span class="dd-txt">
                <b>{trailerName(t, cfg.trailer)}</b>
                <small>{trailerDesc(t, cfg.trailer)}</small>
              </span>
              <Ico d={IC.chevron} />
            </button>
            {ddOpen && (
              <ul class="dd-menu" role="listbox" aria-labelledby="dd-label">
                {TRAILER_LIST.map((tr, i) => (
                  <li
                    role="option"
                    aria-selected={tr.id === cfg.trailer}
                    class={i === ddIdx ? 'active' : ''}
                    onMouseEnter={() => setDdIdx(i)}
                    onClick={() => chooseTrailer(tr.id)}
                  >
                    <TrailerIcon id={tr.id} />
                    <span class="dd-txt">
                      <b>{trailerName(t, tr.id)}</b>
                      <small>{trailerDesc(t, tr.id)}</small>
                    </span>
                    {tr.id === cfg.trailer && <Ico d={IC.check} size={16} />}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div class="cfg-field">
          <span class="cfg-label">{t.socket_label}</span>
          <div class="cfg-seg" role="radiogroup" aria-label={t.socket_label}>
            {SOCKETS.map((s) => (
              <button type="button" role="radio" aria-checked={cfg.socket === s} onClick={() => update((c) => ({ ...c, socket: s }))}>
                {socketName(t, s)}
              </button>
            ))}
          </div>
        </div>

        <div class="cfg-field">
          <span class="cfg-label">{t.length_label}</span>
          <div class="cfg-seg" role="radiogroup" aria-label={t.length_label}>
            {LENGTHS.map((l) => {
              const ok = trailerDef.lengths.includes(l);
              return (
                <button
                  type="button"
                  role="radio"
                  aria-checked={cfg.length === l}
                  disabled={!ok}
                  title={ok ? undefined : t.not_for_trailer}
                  onClick={() => update((c) => ({ ...c, length: l }))}
                >
                  {lenLabel(l)}
                </button>
              );
            })}
          </div>
        </div>
        </>)}
      </aside>

      {/* ---------- sağ: lambalar + özet ---------- */}
      <aside class="cfg-card cfg-right" aria-label={t.lamps_title}>
        <div class="cfg-lamps">
          {CATEGORIES.map((cat) => {
            const ch = cfg.lamps[cat.id];
            const prod = productById(cat.id, ch.product);
            const open = openCat === cat.id;
            return (
              <section class={`lc ${open ? 'open' : ''} ${ch.qty === 0 ? 'off' : ''}`} key={cat.id}>
                <div class="lc-head">
                  <button type="button" class="lc-toggle" aria-expanded={open} onClick={() => toggleCat(cat.id)}>
                    <i class="lc-dot" style={`background:${CAT_DOT[cat.id]}`} />
                    <span class="lc-name">
                      <b>{categoryName(t, cat.id)}</b>
                      <small class="mono">{ch.qty ? prod.code : t.none}</small>
                    </span>
                    <Ico d={IC.chevron} size={16} />
                  </button>
                  <div class="qty sm" role="group" aria-label={`${categoryName(t, cat.id)}: ${t.qty}`}>
                    <button type="button" aria-label={ui.qty_dec} disabled={ch.qty <= cat.min} onClick={() => step(cat.id, -1)}>
                      −
                    </button>
                    <output>{ch.qty}</output>
                    <button type="button" aria-label={ui.qty_inc} disabled={ch.qty >= cat.max} onClick={() => step(cat.id, 1)}>
                      +
                    </button>
                  </div>
                </div>
                {open && (
                  <div class="lc-opts" role="radiogroup" aria-label={`${categoryName(t, cat.id)}: ${t.model}`}>
                    {cat.products.map((p) => (
                      <button type="button" role="radio" aria-checked={p.id === ch.product} onClick={() => pickProduct(cat.id, p.id)}>
                        <LampGlyph style={p.style} />
                        <span class="mono">{p.code}</span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            );
          })}
          <p class="cfg-note">{t.note_3d}</p>
        </div>

        <div class="cfg-summary" aria-live="polite">
          <div class="cs-head">
            <h2>{t.summary_title}</h2>
            <button type="button" class="cfg-ic sm" data-tip={t.pdf_download} onClick={downloadPdf} disabled={pdfBusy} aria-label={t.pdf_download}>
              <Ico d={IC.download} size={17} />
            </button>
          </div>
          <dl>
            {rows.map((r) => (
              <div>
                <dt>{r.label}</dt>
                <dd class={r.mono ? 'mono' : ''}>{r.value}</dd>
              </div>
            ))}
          </dl>
          <div class="cs-actions">
            {stepper}
            <button type="button" class="btn btn-primary" onClick={send}>
              {t.get_quote}
            </button>
          </div>
        </div>
      </aside>

      {/* ---------- mobil alt çubuk ---------- */}
      <div class="cfg-bar">
        <div class="cfg-mini">
          <b>{trailerName(t, cfg.trailer)}</b>
          <span>
            {socketName(t, cfg.socket)} · {lenLabel(cfg.length)}
          </span>
        </div>
        {stepper}
        <button type="button" class="btn btn-primary" onClick={send}>
          {t.get_quote}
        </button>
      </div>
      <ConfigOrder open={orderOpen} onClose={closeOrder} cfg={cfg} qty={orderQty} t={t} ui={ui} lang={lang} />
    </div>
  );
}
