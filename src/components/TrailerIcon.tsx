// Dorse tipleri için minimalist yan görünüm simgeleri (64x24, çizgi). Renk currentColor.
import type { TrailerId } from '../configurator/data';

const wheels = (xs: number[], y = 19.5, r = 2.6) => xs.map((x) => <circle cx={x} cy={y} r={r} />);
const base = (
  <>
    <path d="M6 16.8h52" />
    <path d="M17 17v3.6M15.4 20.6h3.2" />
  </>
);
const std3 = wheels([43, 48.5, 54]);

const ICONS: Record<TrailerId, preact.JSX.Element> = {
  standart: (
    <>
      <rect x="6" y="4" width="52" height="12" rx="1" />
      <path d="M19 6v8M30 6v8M41 6v8" stroke-dasharray="1.6 1.6" />
      {base}
      {std3}
    </>
  ),
  kapali: (
    <>
      <rect x="6" y="4" width="52" height="12" rx="1" />
      <path d="M52 6v8" />
      {base}
      {std3}
    </>
  ),
  frigo: (
    <>
      <rect x="9" y="4" width="49" height="12" rx="1.6" />
      <rect x="5" y="5.5" width="4" height="6" rx="0.8" />
      {base}
      {std3}
    </>
  ),
  flatbed: (
    <>
      <path d="M6 14.6h52M6 14.6V8.5" />
      <path d="M6 9.5h2" />
      {base}
      {std3}
    </>
  ),
  stepdeck: (
    <>
      <path d="M6 12.6h12l2.5 2.5H58M6 12.6V7.5" />
      <path d="M6 16.8h52" />
      <path d="M17 17v3.6M15.4 20.6h3.2" />
      {std3}
    </>
  ),
  lowbed: (
    <>
      <path d="M4 11.5h12l2.5 6.2h19.5l2-4h18" />
      <path d="M53 13.7l4-5" />
      <path d="M12 12v8.2M10.4 20.2h3.2" />
      {wheels([45, 49.5, 54], 19.8, 2.1)}
    </>
  ),
  damper: (
    <>
      <path d="M8 4.5h50l-1.6 11.3H10.2z" />
      <path d="M8 8.5 5 15.5" />
      {base}
      {wheels([45, 50.5])}
    </>
  ),
  tanker: (
    <>
      <rect x="7" y="4.6" width="51" height="10.6" rx="5.3" />
      <path d="M22 4.6v-1.8M38 4.6v-1.8" />
      {base}
      {std3}
    </>
  ),
  silo: (
    <>
      <path d="M11 4.2h45a2.4 2.4 0 0 1 1.2 4.5L32.5 14.4 9.6 8.9A2.4 2.4 0 0 1 11 4.2z" />
      <path d="M32.5 14.4v2.4M5.5 13h4v3.8" />
      {base}
      {std3}
    </>
  ),
  arac: (
    <>
      <path d="M6 9.8h50M6 15.2h52M8 9.8v5.4M20 9.8v5.4M32 9.8v5.4M44 9.8v5.4M6 4v11" />
      <path d="M56 9.8l3-2.6" />
      {base}
      {std3}
    </>
  ),
  konteyner: (
    <>
      <rect x="8" y="4.6" width="49" height="10.6" />
      <path d="M14 6v7.8M20 6v7.8M26 6v7.8M32 6v7.8M38 6v7.8M44 6v7.8M50 6v7.8" stroke-width="0.9" />
      {base}
      {std3}
    </>
  ),
};

export default function TrailerIcon({ id, class: cls }: { id: TrailerId; class?: string }) {
  return (
    <svg class={cls ?? 'ticon'} viewBox="0 0 64 24" width="64" height="24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
      {ICONS[id]}
    </svg>
  );
}
