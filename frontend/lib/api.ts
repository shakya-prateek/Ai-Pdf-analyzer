export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const API_WAKE_TIMEOUT_MS = 120_000;
const API_REQUEST_TIMEOUT_MS = 90_000;
const API_READY_TTL_MS = 60_000;

let readyUntil = 0;
let readinessRequest: Promise<void> | null = null;

export type Citation = {
  document_name: string;
  page_number: number;
  page_image_url: string;
  quoted_text: string;
};

export type Classification = {
  document_type: string;
  topics: string[];
  content_characteristics: {
    has_tables: boolean;
    has_handwriting: boolean;
    is_scanned: boolean;
    is_image_heavy: boolean;
    language: string;
  };
  sensitivity: { level: string; reasons: string[] };
  summary: string;
};

export type DocumentRecord = {
  id: string;
  original_name: string;
  status: string;
  error_message?: string | null;
  classification?: Classification | null;
  created_at?: string;
};

export function absoluteImageUrl(path: string) {
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

function requestHeaders(init?: RequestInit) {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  return headers;
}

async function fetchWithTimeout(
  path: string,
  init: RequestInit | undefined,
  timeoutMs: number
) {
  const controller = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => controller.abort();
  init?.signal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    return await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      ...init,
      signal: controller.signal,
      headers: requestHeaders(init)
    });
  } catch (error) {
    if (timedOut || (error instanceof DOMException && error.name === "AbortError")) {
      throw new Error(
        "The document service is waking up or busy. Please try again in a moment."
      );
    }
    throw new Error(
      "Unable to reach the document service. Check the connection and try again."
    );
  } finally {
    window.clearTimeout(timeout);
    init?.signal?.removeEventListener("abort", abortFromCaller);
  }
}

export async function ensureApiReady() {
  if (Date.now() < readyUntil) return;
  if (!readinessRequest) {
    readinessRequest = (async () => {
      const response = await fetchWithTimeout(
        "/api/health",
        undefined,
        API_WAKE_TIMEOUT_MS
      );
      if (!response.ok) {
        throw new Error(`Document service unavailable (${response.status})`);
      }
      readyUntil = Date.now() + API_READY_TTL_MS;
    })().finally(() => {
      readinessRequest = null;
    });
  }
  await readinessRequest;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  if (path !== "/api/health") await ensureApiReady();
  const response = await fetchWithTimeout(path, init, API_REQUEST_TIMEOUT_MS);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function fetchProtectedImage(path: string) {
  const response = await fetch(absoluteImageUrl(path), {
    cache: "no-store",
    headers: requestHeaders()
  });
  if (!response.ok) throw new Error("Unable to load protected page image");
  return response.blob();
}
