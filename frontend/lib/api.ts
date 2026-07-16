export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 45000);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      ...init,
      signal: init?.signal || controller.signal,
      headers: requestHeaders(init)
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The document service took too long to respond. Please try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
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
