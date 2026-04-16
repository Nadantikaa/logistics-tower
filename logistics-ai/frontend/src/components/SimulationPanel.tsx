import { useEffect, useState } from "react";

import { api } from "../services/api";
import type { ActionType, Shipment } from "../types/shipment";
import type { SimulationResult } from "../types/simulation";
import { DownstreamImpact } from "./DownstreamImpact";

const ACTIONS: ActionType[] = ["REROUTE", "HOLD", "SWITCH CARRIER", "EXPEDITE", "NO ACTION"];

export function SimulationPanel({ shipment }: { shipment: Shipment }) {
  const [selectedAction, setSelectedAction] = useState<ActionType>("REROUTE");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const simulateImpact = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.simulateImpact(shipment.shipment_id, selectedAction);
        setResult(response);
      } catch (simulationError) {
        setError(simulationError instanceof Error ? simulationError.message : "Simulation failed.");
      } finally {
        setLoading(false);
      }
    };

    simulateImpact();
  }, [selectedAction, shipment.shipment_id]);

  return (
    <section className="panel simulation-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Simulation Mode</p>
          <h3>What-if Analysis</h3>
        </div>
      </div>

      <div className="simulation-controls">
        <label>
          Select Action:
          <select 
            value={selectedAction} 
            onChange={(event) => setSelectedAction(event.target.value as ActionType)}
            disabled={loading}
          >
            {ACTIONS.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </label>
        {loading && <span className="loading-indicator">Computing impact...</span>}
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      {result ? (
        <>
          <div className="simulation-result">
            <div>
              <span>ETA</span>
              <strong>{new Date(result.simulated_eta).toLocaleString()}</strong>
            </div>
            <div>
              <span>Delay Probability</span>
              <strong>{result.simulated_delay_probability}%</strong>
            </div>
            <div>
              <span>Risk Score</span>
              <strong>{result.simulated_risk_score}%</strong>
            </div>
            <p>{result.impact_summary}</p>
          </div>

          <DownstreamImpact shipment={shipment} simulation={result} />
        </>
      ) : null}
    </section>
  );
}
