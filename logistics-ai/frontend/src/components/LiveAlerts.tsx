import type { AlertItem } from "../types/shipment";

export function LiveAlerts({ alerts }: { alerts: AlertItem[] }) {
  const visibleAlerts = alerts.filter((alert) => alert.visible);

  return (
    <section className="alerts-strip">
      {visibleAlerts.length === 0 ? (
        <div className="alert-item alert-info">No high-confidence alerts right now.</div>
      ) : (
        visibleAlerts.map((alert) => (
          <div key={`${alert.shipment_id}-${alert.title}`} className={`alert-item alert-${alert.severity}`}>
            <strong>{alert.title}</strong>
            <span>{alert.message}</span>
            <small>Confidence {alert.confidence}%</small>
          </div>
        ))
      )}
    </section>
  );
}
