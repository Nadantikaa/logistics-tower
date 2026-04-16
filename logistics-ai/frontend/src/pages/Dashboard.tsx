import { useEffect, useMemo, useState } from "react";

import { DecisionLog } from "../components/DecisionLog";
import { LiveAlerts } from "../components/LiveAlerts";
import { MapPanel } from "../components/MapPanel";
import { SelectedShipmentPanel } from "../components/SelectedShipmentPanel";
import { ShipmentList } from "../components/ShipmentList";
import { useAuth } from "../context/AuthContext";
import { useDashboardData } from "../hooks/useDashboardData";

export function Dashboard() {
  const { session, logout } = useAuth();
  const { shipments, alerts, summary, decisionLog, lastUpdated, loading, error, topShipmentId } = useDashboardData();
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedShipmentId && topShipmentId) {
      setSelectedShipmentId(topShipmentId);
    }
  }, [selectedShipmentId, topShipmentId]);

  const selectedShipment = useMemo(
    () => shipments.find((shipment) => shipment.shipment_id === selectedShipmentId) ?? shipments[0] ?? null,
    [selectedShipmentId, shipments],
  );
  const selectedShipmentAlert = useMemo(
    () => alerts.find((alert) => alert.shipment_id === selectedShipment?.shipment_id) ?? null,
    [alerts, selectedShipment],
  );

  if (loading) {
    return <main className="dashboard-shell loading-state">Loading control tower...</main>;
  }

  if (error) {
    return <main className="dashboard-shell error-state">Dashboard failed to load: {error}</main>;
  }

  if (!selectedShipment) {
    return <main className="dashboard-shell empty-state">No shipment data available.</main>;
  }

  return (
    <main className="dashboard-shell">
      <header className="hero-banner">
        <div>
          <div className="hero-meta">
            <span className="live-indicator">Live Monitoring</span>
            <span className="live-timestamp">
              Last refresh {lastUpdated ? lastUpdated.toLocaleTimeString() : "--"}
            </span>
          </div>
          <p className="eyebrow">Logistics AI Control Tower</p>
          <h1>Act before delays happen.</h1>
          <p>{summary?.critical_summary}</p>
        </div>
        <div className="hero-aside">
          <div className="user-chip">
            <div>
              <span>Signed in</span>
              <strong>{session?.user.display_name ?? "Control Tower User"}</strong>
            </div>
          </div>
          <button type="button" className="logout-button" onClick={() => void logout()}>
            Log out
          </button>
        </div>
        <div className="hero-stats">
          <div>
            <span>Top Priority</span>
            <strong>{summary?.top_priority_shipment_id ?? "--"}</strong>
          </div>
          <div>
            <span>Active Alerts</span>
            <strong>{summary?.active_alerts ?? 0}</strong>
          </div>
          <div>
            <span>High Risk Shipments</span>
            <strong>{summary?.high_risk_shipments ?? 0}</strong>
          </div>
        </div>
      </header>

      <LiveAlerts alerts={alerts} />

      <div className="dashboard-grid">
        <div className="left-rail">
          <MapPanel shipments={shipments} selectedShipmentId={selectedShipment.shipment_id} />
          <ShipmentList
            shipments={shipments}
            selectedShipmentId={selectedShipment.shipment_id}
            onSelect={setSelectedShipmentId}
          />
        </div>

        <div className="main-column">
          <SelectedShipmentPanel
            shipment={selectedShipment}
            shipmentAlert={selectedShipmentAlert}
            shipments={shipments}
          />
          <DecisionLog entries={decisionLog} />
        </div>
      </div>
    </main>
  );
}
