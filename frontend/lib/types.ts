export type Status = "dry" | "damp" | "wet";

export interface DryWindow {
  start: string;
  end: string;
  open_ended: boolean;
}

export interface AreaSummary {
  id: string;
  name: string;
  region: string;
  lat: number;
  lon: number;
  rock: string;
  notes: string;
  status: Status;
  moisture_mm: number;
  wetness_pct: number;
  dry_threshold_pct: number;
  hours_until_dry: number | null;
  next_dry_window: DryWindow | null;
  computed_at: string;
}

export interface HourPoint {
  time: string;
  precip_mm: number;
  et0_mm: number;
  temp_c: number | null;
  moisture_mm: number;
  wetness_pct: number;
  status: Status;
  is_forecast: boolean;
}

export interface AreaForecast extends AreaSummary {
  hourly: HourPoint[];
}

export interface AreasResponse {
  areas: AreaSummary[];
  errors: { id: string; name: string; error: string }[];
}
