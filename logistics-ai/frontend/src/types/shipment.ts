export type ActionType =
  | "REROUTE"
  | "HOLD"
  | "SWITCH CARRIER"
  | "EXPEDITE"
  | "NO ACTION";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type CongestionLevel = "LOW" | "MEDIUM" | "HIGH";
export type ExecutionStatus = "EXECUTED" | "PENDING" | "FAILED";

export interface DecisionOutput {
  action: ActionType;
  confidence: number;
  reason: string;
  alert: string;
  source: "llm" | "fallback";
  // Ripple effects for recommended action (static baseline)
  primary_delay_increase?: number;
  affected_shipments_ripple?: AffectedShipmentInfo[];
  ripple_summary?: {
    total_affected: number;
    max_delay: number;
  };
}

export interface MlOutput {
  eta_prediction: string;
  delay_probability: number;
  anomaly_score: number;
  risk_score: number;
}

export interface AffectedShipmentInfo {
  id: string;
  delay_increase: number;
  reason: string;
}

export interface RippleEffectSummary {
  total_affected: number;
  max_delay: number;
}

export interface Shipment {
  shipment_id: string;
  origin: string;
  destination: string;
  current_location: string;
  status: string;
  priority: number;
  is_critical: boolean;
  risk_level: RiskLevel;
  signals: {
    weather_status: string;
    temperature_c?: number;
    port_congestion_level: CongestionLevel;
    news_tags: string[];
    shipment_status: string;
  };
  ml_output: MlOutput;
  decision: DecisionOutput | null;
  // Dependency modeling fields
  dependent_shipments: string[];
  shared_resource: string;
  execution_status: ExecutionStatus;
  predicted_delay_hours: number;
}

export interface AlertItem {
  shipment_id: string;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  confidence: number;
  visible: boolean;
}

export interface MonitoringSummary {
  top_priority_shipment_id: string;
  active_alerts: number;
  high_risk_shipments: number;
  critical_summary: string;
}

export interface DecisionLogItem {
  shipment_id: string;
  timestamp: string;
  action: string;
  confidence: number;
  source: string;
}
