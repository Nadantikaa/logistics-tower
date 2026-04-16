import type { SimulationResult } from "../types/simulation";
import type { Shipment } from "../types/shipment";

interface DownstreamImpactProps {
  shipment: Shipment;
  simulation: SimulationResult | null;
}

export function DownstreamImpact({ shipment, simulation }: DownstreamImpactProps) {
  if (!simulation || (simulation.primary_delay_increase === 0 && simulation.affected_shipments.length === 0)) {
    return null;
  }

  return (
    <div className="downstream-impact-section">
      <h3 className="section-title">Downstream Impact Analysis</h3>

      <div className="impact-content">
        {/* Primary Shipment Section */}
        <div className="primary-section">
          <p className="subsection-label">Primary Shipment:</p>
          <div className="primary-delay-card">
            <div className="delay-item">
              <span className="shipment-id-primary">{shipment.shipment_id}</span>
              <span className="delay-value-primary">+{simulation.primary_delay_increase} hours</span>
            </div>
            <p className="delay-context">
              If no action is taken, <strong>{shipment.shipment_id}</strong> delay increases by <strong>+{simulation.primary_delay_increase} hours</strong>
            </p>
          </div>
        </div>

        {/* Dependent Shipments Section */}
        {simulation.affected_shipments.length > 0 && (
          <div className="dependent-section">
            <p className="subsection-label">Affected Downstream Shipments:</p>
            <ul className="affected-shipments-list">
              {simulation.affected_shipments.map((affected) => (
                <li key={affected.id} className="affected-shipment-row">
                  <div className="affected-header">
                    <span className="shipment-id-dependent">{affected.id}</span>
                    <span className="delay-value-dependent">+{affected.delay_increase} hours</span>
                  </div>
                  {affected.reason && (
                    <p className="affected-reason">{affected.reason}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Shared Resource */}
        {shipment.shared_resource && (
          <div className="shared-context">
            <p className="context-label">
              <strong>Shared Resource:</strong> <span className="resource-name">{shipment.shared_resource}</span>
            </p>
          </div>
        )}

        {/* Impact Summary */}
        {simulation.affected_shipments.length > 0 && (
          <div className="impact-stats">
            <div className="stat-box">
              <span className="stat-label">Shipments Impacted</span>
              <span className="stat-value">{simulation.ripple_summary.total_affected}</span>
            </div>
            <div className="stat-box">
              <span className="stat-label">Maximum Delay</span>
              <span className="stat-value">+{simulation.ripple_summary.max_delay}h</span>
            </div>
          </div>
        )}

        {/* Action Guidance */}
        <div className="impact-guidance">
          <p className="guidance-text">
            {simulation.affected_shipments.length > 0
              ? `Without intervention: ${shipment.shipment_id} adds +${simulation.primary_delay_increase}h delay, cascading to ${simulation.ripple_summary.total_affected} dependent shipments with up to +${simulation.ripple_summary.max_delay}h additional impact.`
              : `Without intervention: ${shipment.shipment_id} delay increases by +${simulation.primary_delay_increase} hours.`}
          </p>
        </div>
      </div>
    </div>
  );
}
