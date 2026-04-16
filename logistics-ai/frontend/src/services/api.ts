import type {
  AlertItem,
  DecisionLogItem,
  DecisionOutput,
  MonitoringSummary,
  Shipment,
} from "../types/shipment";
import type { ActionType } from "../types/shipment";
import type { SimulationResult } from "../types/simulation";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getShipments: () => request<Shipment[]>("/shipments"),
  getAlerts: () => request<AlertItem[]>("/alerts"),
  getSummary: () => request<MonitoringSummary>("/monitoring/summary"),
  getDecisionLog: () => request<DecisionLogItem[]>("/decision-log"),
  evaluateDecision: (shipmentId: string) =>
    request<DecisionOutput>(`/decisions/evaluate/${shipmentId}`, {
      method: "POST",
    }),
  simulateDecision: (shipmentId: string, action: ActionType) =>
    request<SimulationResult>(`/simulate/${shipmentId}`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  simulateImpact: (shipmentId: string, action: ActionType) =>
    request<SimulationResult>(`/simulate/impact/${shipmentId}`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
};
