// Teklif listesi (sepet): tarayıcıda saklanır. Depolama engelliyse bellekte çalışmaya devam eder.
// Yalnızca ürün kimliği ve adet saklanır; adlar gösterim anında dile göre ürün verisinden alınır.
// Yalnızca ana sayfa ürünleri içindir. Konfigüratör siparişi ayrıdır (ADR-016), buraya girmez.
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

// Sipariş adedi (çarpan): listedeki TÜM ürünler bu sayıyla çarpılır (aynı siparişten birden fazla verilmiş gibi).
const MKEY = 'horpol.quote.mult.v1';
let multMemory: number | null = null;
export function readMult(): number {
  if (multMemory) return multMemory;
  try {
    const n = Number(localStorage.getItem(MKEY));
    return Number.isFinite(n) && n >= 1 ? Math.min(MAX, Math.floor(n)) : 1;
  } catch {
    return 1;
  }
}
export function setMult(n: number) {
  const v = Math.max(1, Math.min(MAX, Math.floor(n) || 1));
  try {
    localStorage.setItem(MKEY, String(v));
    multMemory = null;
  } catch {
    multMemory = v;
  }
  window.dispatchEvent(new CustomEvent('cart:change'));
}
export function useMult(): number {
  const [n, setN] = useState(1);
  useEffect(() => {
    const sync = () => setN(readMult());
    sync();
    window.addEventListener('cart:change', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('cart:change', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);
  return n;
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

/** Sayfadaki adalar arası haberleşme (ürün penceresi, sepet çekmecesi, bildirim). */
export const openProduct = (id: string) => window.dispatchEvent(new CustomEvent('hts:product', { detail: id }));
/** stage 'form': çekmece doğrudan teklif formuyla açılır */
export const openCart = () => window.dispatchEvent(new CustomEvent('hts:cart'));
export const openSearch = () => window.dispatchEvent(new CustomEvent('hts:search'));
export interface ToastDetail {
  msg: string;
  action?: { label: string; run: () => void };
}
export const showToast = (detail: ToastDetail) => window.dispatchEvent(new CustomEvent<ToastDetail>('hts:toast', { detail }));
