"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchAreas, fetchForecast } from "@/lib/api";
import { fmtClock } from "@/lib/format";
import type { AreaForecast, AreasResponse, Status } from "@/lib/types";
import AreaCard from "./AreaCard";

const ORDER: Record<Status, number> = { dry: 0, damp: 1, wet: 2 };

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: AreasResponse };

export default function Dashboard() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [forecasts, setForecasts] = useState<Record<string, AreaForecast | "error">>({});
  const [slow, setSlow] = useState(false);

  const load = useCallback((signal: AbortSignal) => {
    // Free-tier hosts sleep when idle; tell the user if the first request is slow.
    const slowTimer = setTimeout(() => setSlow(true), 4000);

    fetchAreas(signal)
      .then((data) => {
        setState({ kind: "ready", data });
        data.areas.forEach((a) =>
          fetchForecast(a.id, signal)
            .then((f) => setForecasts((prev) => ({ ...prev, [a.id]: f })))
            .catch((e) => {
              if (!signal.aborted) setForecasts((prev) => ({ ...prev, [a.id]: "error" }));
              console.error(e);
            }),
        );
      })
      .catch((e: Error) => {
        if (!signal.aborted) setState({ kind: "error", message: e.message });
      })
      .finally(() => clearTimeout(slowTimer));
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    load(ctrl.signal);
    return () => ctrl.abort();
  }, [load]);

  if (state.kind === "loading") {
    return (
      <div>
        <p className="mb-4 h-5 text-sm text-muted">
          {slow ? "Waking up the API (free-tier cold start, can take ~30s)…" : ""}
        </p>
        <div className="grid gap-5 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-80 animate-pulse rounded-2xl border border-line bg-panel" />
          ))}
        </div>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="rounded-2xl border border-line bg-panel p-6">
        <p className="font-medium">Couldn&apos;t load conditions.</p>
        <p className="mt-1 font-mono text-sm text-muted">{state.message}</p>
        <button
          onClick={() => {
            setState({ kind: "loading" });
            setSlow(false);
            load(new AbortController().signal);
          }}
          className="mt-4 rounded-lg bg-foreground px-3 py-1.5 text-sm font-medium text-background"
        >
          Retry
        </button>
      </div>
    );
  }

  const areas = [...state.data.areas].sort(
    (a, b) =>
      ORDER[a.status] - ORDER[b.status] || (a.hours_until_dry ?? 1e9) - (b.hours_until_dry ?? 1e9),
  );
  const updated = areas[0]?.computed_at;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2 text-sm text-muted">
        <span>
          {areas.filter((a) => a.status === "dry").length} of {areas.length} areas dry right now
        </span>
        {updated && <span className="font-mono text-xs">model run {fmtClock(updated)} PT</span>}
      </div>
      {state.data.errors.length > 0 && (
        <p className="mb-4 rounded-lg border border-line bg-panel px-4 py-2 text-sm text-muted">
          Weather data unavailable for {state.data.errors.map((e) => e.name).join(", ")}.
        </p>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        {areas.map((a) => {
          const f = forecasts[a.id];
          return (
            <AreaCard
              key={a.id}
              area={a}
              forecast={f && f !== "error" ? f : undefined}
              forecastError={f === "error"}
            />
          );
        })}
      </div>
    </div>
  );
}
