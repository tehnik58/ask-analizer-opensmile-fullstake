const API_BASE = import.meta.env.DEV ? "" : "http://localhost:8000";

export async function uploadFiles(original, translations) {
  const form = new FormData();
  form.append("original", original);
  for (const f of translations) {
    form.append("translations", f);
  }
  const resp = await fetch(`${API_BASE}/api/upload/`, { method: "POST", body: form });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return resp.json();
}

export async function getResults(sessionId) {
  const resp = await fetch(`${API_BASE}/api/results/${sessionId}`);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Fetch failed");
  }
  return resp.json();
}

export function audioUrl(path) {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}
