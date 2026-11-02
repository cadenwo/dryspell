import type { AreaSummary, Status } from "./types";

// Every starter area is in Pacific time (Squamish included).
const TZ = "America/Los_Angeles";

const dayHour = new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short", hour: "numeric" });
const hourOnly = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric" });
const dayKey = new Intl.DateTimeFormat("en-US", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
const clock = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" });

export const fmtDayHour = (iso: string) => dayHour.format(new Date(iso));
export const fmtHour = (iso: string) => hourOnly.format(new Date(iso));
export const fmtClock = (iso: string) => clock.format(new Date(iso));

export function fmtWindow(start: string, end: string, openEnded = false): string {
  if (openEnded) return `${fmtDayHour(start)} onward`;
  // `end` is the last dry hour; the window runs through the end of that hour.
  const endPlus = new Date(new Date(end).getTime() + 3600_000).toISOString();
  const sameDay = dayKey.format(new Date(start)) === dayKey.format(new Date(endPlus));
  return `${fmtDayHour(start)} – ${sameDay ? fmtHour(endPlus) : fmtDayHour(endPlus)}`;
}

export function headline(a: AreaSummary): string {
  if (a.status === "dry") return "Dry now";
  if (a.hours_until_dry === null) return "Not dry in the forecast";
  if (a.hours_until_dry <= 1) return "Dry within the hour";
  if (a.hours_until_dry < 24) return `Dry in ~${a.hours_until_dry}h`;
  return `Dry in ~${Math.round(a.hours_until_dry / 24)}d`;
}

export const STATUS_LABEL: Record<Status, string> = { dry: "Dry", damp: "Damp", wet: "Wet" };

export const STATUS_STYLE: Record<Status, { pill: string; bar: string; fill: string }> = {
  dry: { pill: "bg-moss/15 text-moss ring-moss/30", bar: "bg-moss", fill: "var(--color-moss)" },
  damp: { pill: "bg-lichen/15 text-lichen ring-lichen/30", bar: "bg-lichen", fill: "var(--color-lichen)" },
  wet: { pill: "bg-rain/15 text-rain ring-rain/30", bar: "bg-rain", fill: "var(--color-rain)" },
};
