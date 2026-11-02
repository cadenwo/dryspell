import type { HourPoint } from "@/lib/types";
import { STATUS_STYLE, fmtDayHour } from "@/lib/format";

const W = 720;
const H = 120;
const RAIN_H = 28; // px band at the bottom for precipitation bars
const MAX_RAIN_MM = 4; // bars saturate here

interface Props {
  hourly: HourPoint[];
  dryThresholdPct: number;
}

/** Rock wetness (area, colored by status) over time with rain bars and a "now" marker. */
export default function MoistureChart({ hourly, dryThresholdPct }: Props) {
  if (hourly.length < 2) return null;

  const n = hourly.length;
  const dx = W / (n - 1);
  const plotH = H - RAIN_H;
  const y = (pct: number) => plotH - (Math.min(100, Math.max(0, pct)) / 100) * (plotH - 4);
  const nowIdx = Math.max(0, hourly.findIndex((h) => h.is_forecast) - 1);
  const nowX = nowIdx * dx;

  // Merge consecutive hours with the same status/forecast flag into one filled
  // shape, so there are no anti-aliasing seams between hourly slices.
  const runs: { from: number; to: number; status: HourPoint["status"]; forecast: boolean }[] = [];
  for (let i = 1; i < n; i++) {
    const h = hourly[i];
    const last = runs[runs.length - 1];
    if (last && last.status === h.status && last.forecast === h.is_forecast) last.to = i;
    else runs.push({ from: i - 1, to: i, status: h.status, forecast: h.is_forecast });
  }
  const segments = runs.map((r) => {
    const top = [];
    for (let i = r.from; i <= r.to; i++) top.push(`L${i * dx},${y(hourly[i].wetness_pct)}`);
    return (
      <path
        key={r.from}
        d={`M${r.from * dx},${plotH} ${top.join(" ")} L${r.to * dx},${plotH} Z`}
        fill={STATUS_STYLE[r.status].fill}
        fillOpacity={r.forecast ? 0.35 : 0.7}
      />
    );
  });

  const line = hourly.map((h, i) => `${i ? "L" : "M"}${i * dx},${y(h.wetness_pct)}`).join(" ");

  // Start, now, +24h, end: evenly spaced for a 24h-back / 48h-ahead window.
  const ticks = [0, nowIdx, nowIdx + 24, n - 1]
    .filter((v) => v >= 0 && v < n)
    .filter((v, i, arr) => arr.indexOf(v) === i && (i === 0 || v - arr[i - 1] >= 12 || v === nowIdx));

  return (
    <figure className="mt-4">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="h-28 w-full"
        role="img"
        aria-label="Rock wetness over the past 24 hours and next 48 hours"
      >
        {segments}
        <path d={line} fill="none" stroke="currentColor" strokeOpacity={0.6} strokeWidth={1.25} vectorEffect="non-scaling-stroke" />
        <line
          x1={0}
          x2={W}
          y1={y(dryThresholdPct)}
          y2={y(dryThresholdPct)}
          stroke="var(--color-moss)"
          strokeDasharray="4 4"
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
        {hourly.map((h, i) =>
          h.precip_mm > 0 ? (
            <rect
              key={`r-${h.time}`}
              x={i * dx - dx * 0.35}
              width={dx * 0.7}
              y={H - (Math.min(h.precip_mm, MAX_RAIN_MM) / MAX_RAIN_MM) * (RAIN_H - 4)}
              height={(Math.min(h.precip_mm, MAX_RAIN_MM) / MAX_RAIN_MM) * (RAIN_H - 4)}
              fill="var(--color-rain)"
              fillOpacity={h.is_forecast ? 0.5 : 0.9}
            >
              <title>{`${fmtDayHour(h.time)}: ${h.precip_mm.toFixed(1)} mm rain`}</title>
            </rect>
          ) : null,
        )}
        <line x1={0} x2={W} y1={plotH} y2={plotH} stroke="currentColor" strokeOpacity={0.15} vectorEffect="non-scaling-stroke" />
        <line
          x1={nowX}
          x2={nowX}
          y1={0}
          y2={H}
          stroke="currentColor"
          strokeOpacity={0.8}
          strokeWidth={1.5}
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="relative mt-1 h-4 font-mono text-[10px] text-muted">
        {ticks.map((i) => (
          <span
            key={i}
            className="absolute -translate-x-1/2 whitespace-nowrap first:translate-x-0 last:-translate-x-full"
            style={{ left: `${(i / (n - 1)) * 100}%` }}
          >
            {i === nowIdx ? "now" : fmtDayHour(hourly[i].time)}
          </span>
        ))}
      </div>
      <figcaption className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0 w-4 border-t border-dashed border-moss" /> dry threshold
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-1.5 bg-rain" /> rain (mm/h)
        </span>
        <span>faded = forecast</span>
      </figcaption>
    </figure>
  );
}
