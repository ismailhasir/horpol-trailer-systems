import { useEffect, useRef, useState } from "react";
import { TrailerScene, type CameraView } from "../scene/TrailerScene";
import { configStore } from "../state/store";

const VIEWS: { id: CameraView; label: string }[] = [
  { id: "perspective", label: "3D" },
  { id: "side", label: "Yan" },
  { id: "rear", label: "Arka" },
];

export default function Viewer() {
  const hostRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<TrailerScene | null>(null);
  const [view, setView] = useState<CameraView>("perspective");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let scene: TrailerScene;
    try {
      scene = new TrailerScene(hostRef.current!);
    } catch {
      setFailed(true);
      return;
    }
    sceneRef.current = scene;
    scene.update(configStore.get());
    const unsubscribe = configStore.subscribe((c) => scene.update(c));
    return () => {
      unsubscribe();
      scene.dispose();
      sceneRef.current = null;
    };
  }, []);

  if (failed) {
    return <div className="stage-loading">Tarayıcınız 3D önizlemeyi desteklemiyor. Seçimleriniz ve sipariş yine de çalışır.</div>;
  }

  return (
    <>
      <div ref={hostRef} className="viewer" />
      <div className="view-switch" role="group" aria-label="Kamera açısı">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            className={v.id === view ? "seg active" : "seg"}
            aria-pressed={v.id === view}
            onClick={() => {
              setView(v.id);
              sceneRef.current?.setView(v.id);
            }}
          >
            {v.label}
          </button>
        ))}
      </div>
      <p className="hint">Sürükleyerek döndürün · kaydırarak yakınlaştırın</p>
    </>
  );
}
