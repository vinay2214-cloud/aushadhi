export type StockStatus = "CRITICAL" | "LOW" | "MODERATE" | "GOOD";
export type ReportingStatus = "ON_TIME" | "DELAYED" | "MISSING";
export type CenterType = "SC" | "PHC" | "CHC" | "DH";

export interface HealthCenter {
  id: string;
  name: string;
  type: CenterType;
  district: string;
  subdistrict: string;
  location: { lat: number; lng: number };
  catchment_population: number;
  medical_officer: string;
  contact_phone: string;
  nearest_warehouse_distance_km: number;
  status: {
    last_checked: string;
    overall_stock_status: StockStatus;
    critical_items_count: number;
    low_items_count: number;
    data_quality_score: number;
    last_report_date: string;
    reporting_status: ReportingStatus;
  };
}
