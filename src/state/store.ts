import { useSyncExternalStore } from "react";
import { defaultConfiguration, type Configuration } from "./config";

// Bağımlılıksız, küçük bir dış store. React panelleri useConfiguration ile,
// 3D sahne ise subscribe ile doğrudan dinler; böylece sahne güncellemeleri
// React render döngüsüne hiç girmez.

type Listener = (config: Configuration) => void;

let state: Configuration = defaultConfiguration();
const listeners = new Set<Listener>();

export const configStore = {
  get: () => state,
  set(update: (prev: Configuration) => Configuration) {
    const next = update(state);
    if (next === state) return;
    state = next;
    listeners.forEach((l) => l(state));
  },
  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};

export function useConfiguration(): Configuration {
  return useSyncExternalStore(configStore.subscribe, configStore.get);
}
