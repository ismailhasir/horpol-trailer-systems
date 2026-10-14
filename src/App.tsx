import { lazy, Suspense } from "react";
import { TrailerPanel } from "./components/TrailerPanel";
import { LampPanel } from "./components/LampPanel";

// 3D görüntüleyici (ve three.js) ayrı chunk olarak yüklenir; paneller hemen
// etkileşime açılır, sahne hazır olunca seçimler zaten store'da beklemektedir.
const Viewer = lazy(() => import("./components/Viewer"));

export function App() {
  return (
    <div className="shell">
      <header className="top">
        <img className="logo" src="/horpol-logo.webp" alt="Horpol" width={56} height={40} />
        <div className="brand">
          <strong>Horpol Trailer Systems</strong>
          <span>3D aydınlatma seti konfigüratörü</span>
        </div>
      </header>
      <aside className="panel panel-left" aria-label="Dorse ve set özellikleri">
        <TrailerPanel />
      </aside>
      <main className="stage">
        <Suspense fallback={<div className="stage-loading">3D önizleme yükleniyor…</div>}>
          <Viewer />
        </Suspense>
      </main>
      <aside className="panel panel-right" aria-label="Lambalar ve sipariş">
        <LampPanel />
      </aside>
    </div>
  );
}
