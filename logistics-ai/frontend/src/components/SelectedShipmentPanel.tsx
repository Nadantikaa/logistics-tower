import type { AlertItem, Shipment } from "../types/shipment";
import { ActionCard } from "./ActionCard";
import { SignalTags } from "./SignalTags";
import { SimulationPanel } from "./SimulationPanel";

interface SelectedShipmentPanelProps {
  shipment: Shipment;
  shipmentAlert: AlertItem | null;
  shipments: Shipment[];
  canManage: boolean;
}

export function SelectedShipmentPanel({ shipment, shipmentAlert, shipments, canManage }: SelectedShipmentPanelProps) {
  return (
    <section className="selected-shipment">
      <div className="panel selected-summary">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Selected Shipment</p>
            <h1>{shipment.shipment_id}</h1>
          </div>
          <div className="priority-stack">
            {shipment.is_critical ? <span className="priority-flag">Highest Priority</span> : null}
            <span className="priority-score">Priority {shipment.priority}</span>
          </div>
        </div>

        <p className="hero-route">
          {shipment.origin} to {shipment.destination}
        </p>
        <p className="hero-status">
          {shipment.status} at {shipment.current_location}
        </p>

        <div className="status-ribbon">
          <span className="status-chip">Decision Source: {shipment.decision?.source ?? "n/a"}</span>
          <span className={`status-chip ${shipmentAlert?.visible ? "status-chip-live" : "status-chip-muted"}`}>
            {shipmentAlert?.visible ? "Alert threshold met" : "Below alert threshold"}
          </span>
        </div>

        <SignalTags
          weather={shipment.signals.weather_status}
          congestion={shipment.signals.port_congestion_level}
          newsTags={shipment.signals.news_tags}
        />

        <div className="metrics-grid metrics-grid-hero">
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
      </div>

      <ActionCard shipment={shipment} shipmentAlert={shipmentAlert} shipments={shipments} />
      <SimulationPanel shipment={shipment} canManage={canManage} />
    </section>
  );
}
