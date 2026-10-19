// Set görseli: setin lamba simgelerinden ızgara kompozisyon (kart ve ayrıntı penceresi ortak kullanır).
// Simgesi henüz üretilmemiş lamba için sade bir yer tutucu çizilir (kod yazılı çerçeve).
import type { LampView } from '../lib/format';

export function LampIcon({ lamp, sizes }: { lamp: LampView; sizes: string }) {
  if (lamp.icon)
    return <img src={lamp.icon.src} srcset={lamp.icon.srcset} sizes={sizes} width={160} height={160} alt="" loading="lazy" decoding="async" />;
  return (
    <span class="lamp-ph">
      <svg viewBox="0 0 48 32" aria-hidden="true" focusable="false">
        <rect x="3" y="6" width="42" height="20" rx="6" />
        <path d="M12 16h24" />
      </svg>
      <span class="mono ltr">{lamp.code}</span>
    </span>
  );
}

/** Izgara: iki satır; tek sayıda lambada ilk lamba (arka lamba) iki satırı kaplar. */
export default function SetVisual({ lamps, sizes }: { lamps: LampView[]; sizes: string }) {
  const n = lamps.length;
  const odd = n > 1 && n % 2 === 1;
  const cols = Math.max(1, Math.ceil((n + (odd ? 1 : 0)) / 2));
  return (
    <div class={odd ? 'set-vis odd' : 'set-vis'} style={`--cols:${cols}`} aria-hidden="true">
      {lamps.map((l) => (
        <div class="set-tile" key={l.id}>
          <LampIcon lamp={l} sizes={sizes} />
          <span class="set-q ltr">×{l.qty}</span>
        </div>
      ))}
    </div>
  );
}
