// Tesisat hatlarının renkleri: 3D sahnedeki kablo malzemeleri (engine/materials.ts, engine/equipment.ts) ve paneldeki
// "Tesisat" lejantı (Configurator.tsx) bu tek kaynaktan okur. three.js içermez: arayüz parçasına motoru taşımaz.
export const WIRE_COLORS = {
  main: '#3b82f6',
  side: '#f59e0b',
  rear: '#ef4444',
  plate: '#e5e7eb',
  marker: '#22c55e',
  /** çalışma ve tepe lambası hatları */
  aux: '#a855f7',
} as const;
