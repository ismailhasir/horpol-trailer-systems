// Teklif listesi (sepet): tarayıcıda saklanır. Depolama engelliyse bellekte çalışmaya devam eder.
// Yalnızca ürün kimliği ve adet saklanır; adlar gösterim anında dile göre ürün verisinden alınır.
// İleride (ADR-013 ek) konfigüratör seti de bu listeye girecek.
import { useEffect, useState } from 'preact/hooks';

export interface CartItem {
  id: string;
  qty: number;
}

const KEY = 'horpol.quote.v1';
let memory: CartItem[] | null = null;
const MAX = 99;

export function readCart(): CartItem[] {
  if (memory) return memory;
  try {
    const v = localStorage.getItem(KEY);
    const parsed = v ? (JSON.parse(v) as CartItem[]) : [];
    return Array.isArray(parsed) ? parsed.filter((i) => i && typeof i.id === 'string' && i.qty > 0) : [];
  } catch {
    return [];
  }
}

function write(items: CartItem[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
    memory = null;
  } catch {
    memory = items;
  }
  window.dispatchEvent(new CustomEvent('cart:change'));
}

export function addToCart(id: string, qty = 1) {
  const items = readCart().map((i) => ({ ...i }));
  const found = items.find((i) => i.id === id);
  if (found) found.qty = Math.min(MAX, found.qty + qty);
  else items.push({ id, qty: Math.min(MAX, qty) });
  write(items);
}

export function setQty(id: string, qty: number) {
  write(readCart().map((i) => (i.id === id ? { ...i, qty: Math.max(1, Math.min(MAX, Math.floor(qty) || 1)) } : i)));
}

export function removeFromCart(id: string) {
  write(readCart().filter((i) => i.id !== id));
}

export function restoreItem(item: CartItem) {
  write([...readCart().filter((i) => i.id !== item.id), item]);
}

export function clearCart() {
  write([]);
}

export function useCart(): CartItem[] {
  const [items, setItems] = useState<CartItem[]>([]);
  useEffect(() => {
    const sync = () => setItems(readCart());
    sync();
    window.addEventListener('cart:change', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('cart:change', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);
  return items;
}

// --- Konfigüratör setleri (ADR-013): yapılandırma adres satırı biçiminde saklanır ---
export interface CartSet {
  id: string;
  /** yapılandırma (toQuery çıktısı) */
  q: string;
  qty: number;
}
const SKEY = 'horpol.sets.v1';
let setMemory: CartSet[] | null = null;

export function readSets(): CartSet[] {
  if (setMemory) return setMemory;
  try {
    const v = localStorage.getItem(SKEY);
    const parsed = v ? (JSON.parse(v) as CartSet[]) : [];
    return Array.isArray(parsed) ? parsed.filter((s) => s && typeof s.q === 'string' && s.qty > 0) : [];
  } catch {
    return [];
  }
}
function writeSets(items: CartSet[]) {
  try {
    localStorage.setItem(SKEY, JSON.stringify(items));
    setMemory = null;
  } catch {
    setMemory = items;
  }
  window.dispatchEvent(new CustomEvent('cart:change'));
}
/** Aynı yapılandırma zaten listedeyse adedini artırır. Set kimliğini döndürür. */
export function addSet(q: string, qty = 1): string {
  const items = readSets().map((s) => ({ ...s }));
  const found = items.find((s) => s.q === q);
  if (found) {
    found.qty = Math.min(MAX, found.qty + qty);
    writeSets(items);
    return found.id;
  }
  const id = `set-${Date.now().toString(36)}`;
  items.push({ id, q, qty });
  writeSets(items);
  return id;
}
export function setSetQty(id: string, qty: number) {
  writeSets(readSets().map((s) => (s.id === id ? { ...s, qty: Math.max(1, Math.min(MAX, Math.floor(qty) || 1)) } : s)));
}
export function removeSet(id: string) {
  writeSets(readSets().filter((s) => s.id !== id));
}
export function restoreSet(item: CartSet) {
  writeSets([...readSets().filter((s) => s.id !== item.id), item]);
}
export function useSets(): CartSet[] {
  const [items, setItems] = useState<CartSet[]>([]);
  useEffect(() => {
    const sync = () => setItems(readSets());
    sync();
    window.addEventListener('cart:change', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('cart:change', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);
  return items;
}

/** Sayfadaki adalar arası haberleşme (ürün penceresi, sepet çekmecesi, bildirim). */
export const openProduct = (id: string) => window.dispatchEvent(new CustomEvent('hts:product', { detail: id }));
/** stage 'form': çekmece doğrudan teklif formuyla açılır */
export const openCart = (stage: 'list' | 'form' = 'list') => window.dispatchEvent(new CustomEvent('hts:cart', { detail: stage }));
export const openSearch = () => window.dispatchEvent(new CustomEvent('hts:search'));
export interface ToastDetail {
  msg: string;
  action?: { label: string; run: () => void };
}
export const showToast = (detail: ToastDetail) => window.dispatchEvent(new CustomEvent<ToastDetail>('hts:toast', { detail }));
