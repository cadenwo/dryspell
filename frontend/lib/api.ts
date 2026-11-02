import type { AreaForecast, AreasResponse } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { signal, cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const fetchAreas = (signal?: AbortSignal) => get<AreasResponse>("/areas", signal);

export const fetchForecast = (id: string, signal?: AbortSignal) =>
  get<AreaForecast>(`/areas/${encodeURIComponent(id)}/forecast`, signal);
