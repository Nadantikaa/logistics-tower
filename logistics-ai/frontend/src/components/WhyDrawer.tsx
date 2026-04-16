import type { Shipment } from "../types/shipment";

interface WhyDrawerProps {
  shipment: Shipment;
  shipments: Shipment[];
}

export function WhyDrawer({ shipment, shipments }: WhyDrawerProps) {
  // Helper function to find dependent shipment's delay
  const getDependentShipmentDelay = (shipmentId: string): number | null => {
    const dep = shipments.find((s) => s.shipment_id === shipmentId);
    return dep ? dep.predicted_delay_hours : null;
  };
  return (
    <div className="why-drawer">
      <p>{shipment.decision?.reason ?? "No decision rationale available."}</p>
      <div className="metrics-grid">
        <div>
          <span>ETA</span>
          <strong>{new Date(shipment.ml_output.eta_prediction).toLocaleString()}</strong>
        </div>
        <div>
          <span>Delay Probability</span>
          <strong>{shipment.ml_output.delay_probability}%</strong>
        </div>
        <div>
          <span>Anomaly</span>
          <strong>{shipment.ml_output.anomaly_score}%</strong>
        </div>
        <div>
          <span>Risk Score</span>
          <strong>{shipment.ml_output.risk_score}%</strong>
        </div>
      </div>

      {(shipment.dependent_shipments.length > 0 || shipment.predicted_delay_hours > 0) && (
        <div className="dependency-section">
          <h4 className="dependency-title">Downstream Impact</h4>

          {shipment.predicted_delay_hours > 0 && (
            <div className="primary-delay-block">
              <p className="block-label">Primary Shipment:</p>
              <div className="delay-item primary-item">
                <span className="shipment-badge">{shipment.shipment_id}</span>
                <span className="delay-value">+{shipment.predicted_delay_hours} hours delay</span>
              </div>
            </div>
          )}

          {shipment.dependent_shipments.length > 0 && (
            <div className="dependent-delay-block">
              <p className="block-label">Dependent Shipments:</p>
              <ul className="dependent-list">
                {shipment.dependent_shipments.map((depId) => {
                  const depDelay = getDependentShipmentDelay(depId);
                  return (
                    <li key={depId} className="dependent-item">
                      <span className="shipment-badge">{depId}</span>
                      {depDelay !== null && <span className="delay-value">+{depDelay} hours</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {shipment.shared_resource && (
            <p className="shared-resource-label">
              <strong>Shared Resource:</strong> <span className="resource-value">{shipment.shared_resource}</span>
            </p>
          )}
        </div>
      )}

      <p className="why-footer">Decision source: {shipment.decision?.source ?? "n/a"}</p>
    </div>
  );
}
