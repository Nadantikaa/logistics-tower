import type { RiskLevel } from "../types/shipment";

export function RiskBadge({ riskLevel }: { riskLevel: RiskLevel }) {
  return <span className={`risk-badge risk-${riskLevel.toLowerCase()}`}>{riskLevel}</span>;
}
