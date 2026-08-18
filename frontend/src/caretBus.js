const carets = new Map(); // id → Set<HTMLElement>

export function register(id, el) {
  if (!carets.has(id)) carets.set(id, new Set());
  carets.get(id).add(el);
}

export function unregister(id, el) {
  const set = carets.get(id);
  if (set) set.delete(el);
}

export function move(id, pct) {
  if (!Number.isFinite(pct)) return;
  const set = carets.get(id);
  if (set) set.forEach((el) => { el.style.left = `${pct}%`; });
}
