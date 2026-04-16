import { useState } from "react";

import type { AlertItem } from "../types/shipment";
import type { Shipment } from "../types/shipment";
import { RiskBadge } from "./RiskBadge";
import { WhyDrawer } from "./WhyDrawer";

interface ActionCardProps {
  shipment: Shipment;
  shipmentAlert: AlertItem | null;
  shipments: Shipment[];
}

function getStatusColor(status: string): string {
  switch (status) {
    case "EXECUTED":
      return "status-executed";
    case "FAILED":
      return "status-failed";
    case "PENDING":
    default:
      return "status-pending";
  }
}

export function ActionCard({ shipment, shipmentAlert, shipments }: ActionCardProps) {
  const [open, setOpen] = useState(false);
  const isPromotedAlert = shipmentAlert?.visible ?? false;
  const decision = shipment.decision;
  const hasRipple = decision?.affected_shipments_ripple && decision.affected_shipments_ripple.length > 0;

  return (
    <section className="panel action-card">
      <div className="action-header">
        <div>
          <p className="eyebrow">Action Optimizer</p>
          <h2>{decision?.action ?? "NO ACTION"}</h2>
        </div>
        <RiskBadge riskLevel={shipment.risk_level} />
      </div>

      <div className="action-main">
        <div className="action-callout">{decision?.action ?? "NO ACTION"}</div>
        <div className="action-copy">
          <p className="action-confidence">Confidence: {decision?.confidence ?? 0}%</p>
          <p>{decision?.alert ?? "Monitoring without active intervention."}</p>
          <div className="action-meta">
            <span className="meta-chip">Source: {decision?.source ?? "n/a"}</span>
            <span className={`meta-chip ${isPromotedAlert ? "meta-chip-live" : "meta-chip-muted"}`}>
              {isPromotedAlert ? "Promoted Alert" : "Monitoring Only"}
            </span>
            <span className={`meta-chip status-chip ${getStatusColor(shipment.execution_status)}`}>
              Status: {shipment.execution_status}
            </span>
          </div>
          <button className="why-button" onClick={() => setOpen((value) => !value)} type="button">
            Why?
          </button>
        </div>
      </div>

      {/* Static ripple effects from recommended action */}
      {hasRipple && (
        <div className="optimization-impact">
          <h4>Baseline Impact</h4>
          <div className="ripple-info">
            <p>
              Primary delay: <strong>+{decision.primary_delay_increase} hours</strong>
            </p>
            {decision.ripple_summary && (
              <p>
                Affected shipments: <strong>{decision.ripple_summary.total_affected}</strong> | Max delay:{" "}
                <strong>{decision.ripple_summary.max_delay}h</strong>
              </p>
            )}
          </div>
          {decision.affected_shipments_ripple && decision.affected_shipments_ripple.length > 0 && (
            <div className="affected-list">
              <p className="affected-label">Downstream impacts:</p>
              <ul>
                {decision.affected_shipments_ripple.map((aff) => (
                  <li key={aff.id}>
                    <span>{aff.id}</span>: +{aff.delay_increase}h ({aff.reason})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {open ? <WhyDrawer shipment={shipment} shipments={shipments} /> : null}
    </section>
  );
}
