import type {
  AlertItem,
  DecisionLogItem,
  DecisionOutput,
  MonitoringSummary,
  Shipment,
} from "../types/shipment";
import type { ActionType } from "../types/shipment";
import type { SimulationResult } from "../types/simulation";

function resolveApiBase() {
  const fallback = `${window.location.protocol}//${window.location.hostname}:8000/api`;
  const configured = import.meta.env.VITE_API_BASE;

  if (!configured) {
    return fallback;
  }

  return configured.replace("127.0.0.1", window.location.hostname).replace("localhost", window.location.hostname);
}

const API_BASE = resolveApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    if (response.status === 401) {
      window.location.reload();
    }
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
