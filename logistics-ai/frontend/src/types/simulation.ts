import type { ActionType, AffectedShipmentInfo, RippleEffectSummary } from "./shipment";

export interface SimulationResult {
  action: ActionType;
  baseline_eta: string;
  simulated_eta: string;
  baseline_delay_probability: number;
  simulated_delay_probability: number;
  baseline_risk_score: number;
  simulated_risk_score: number;
  impact_summary: string;
  // Ripple effect fields
  primary_delay_increase: number;
  affected_shipments: AffectedShipmentInfo[];
  ripple_summary: RippleEffectSummary;
}
