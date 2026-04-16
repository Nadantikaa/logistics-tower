import type { DecisionLogItem } from "../types/shipment";

export function DecisionLog({ entries }: { entries: DecisionLogItem[] }) {
  return (
    <section className="panel decision-log">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Trace</p>
          <h3>Decision Log</h3>
        </div>
      </div>
      <div className="decision-log-list">
        {entries.slice(0, 5).map((entry) => (
          <div key={`${entry.shipment_id}-${entry.timestamp}`} className="decision-log-item">
            <strong>{entry.shipment_id}</strong>
            <span>{entry.action}</span>
            <span>{entry.confidence}%</span>
            <span className="decision-source-tag">{entry.source}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
