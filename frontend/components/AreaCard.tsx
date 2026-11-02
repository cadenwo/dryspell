import type { AreaForecast, AreaSummary } from "@/lib/types";
import { STATUS_LABEL, STATUS_STYLE, fmtWindow, headline } from "@/lib/format";
import MoistureChart from "./MoistureChart";

interface Props {
  area: AreaSummary;
  forecast?: AreaForecast;
  forecastError?: boolean;
}

export default function AreaCard({ area, forecast, forecastError }: Props) {
  const s = STATUS_STYLE[area.status];
  const win = area.next_dry_window;

  return (
    <article className="rounded-2xl border border-line bg-panel p-5 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">{area.name}</h2>
          <p className="text-sm text-muted">{area.region}</p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${s.pill}`}>
          {STATUS_LABEL[area.status]}
        </span>
      </header>

      <p className="mt-4 text-2xl font-semibold tracking-tight">{headline(area)}</p>

      <div className="mt-3">
        <div className="flex justify-between text-xs text-muted">
          <span>Surface wetness</span>
          <span className="font-mono">{area.wetness_pct.toFixed(0)}%</span>
        </div>
        <div className="relative mt-1 h-2 overflow-hidden rounded-full bg-line">
          <div className={`h-full rounded-full ${s.bar}`} style={{ width: `${Math.max(2, area.wetness_pct)}%` }} />
          <div
            className="absolute top-0 h-full w-px bg-foreground/60"
            style={{ left: `${area.dry_threshold_pct}%` }}
            title="Dry threshold"
          />
        </div>
      </div>

      <dl className="mt-4 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Next 3h+ dry window</dt>
          <dd className="text-right font-medium">{win ? fmtWindow(win.start, win.end, win.open_ended) : "None in forecast"}</dd>
        </div>
      </dl>

      {forecast ? (
        <MoistureChart hourly={forecast.hourly} dryThresholdPct={area.dry_threshold_pct} />
      ) : forecastError ? (
        <p className="mt-4 text-xs text-muted">Hourly chart unavailable.</p>
      ) : (
        <div className="mt-4 h-28 animate-pulse rounded-lg bg-line/60" />
      )}

      <p className="mt-4 text-xs leading-relaxed text-muted">{area.notes}</p>
    </article>
  );
}
