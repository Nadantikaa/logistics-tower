import { useEffect, useMemo, useState } from "react";

import { api } from "../services/api";
import type { AlertItem, DecisionLogItem, MonitoringSummary, Shipment } from "../types/shipment";

interface DashboardState {
  shipments: Shipment[];
  alerts: AlertItem[];
  summary: MonitoringSummary | null;
  decisionLog: DecisionLogItem[];
  lastUpdated: Date | null;
  loading: boolean;
  error: string | null;
}

const POLL_INTERVAL_MS = 8000;

export function useDashboardData() {
  const [state, setState] = useState<DashboardState>({
    shipments: [],
    alerts: [],
    summary: null,
    decisionLog: [],
    lastUpdated: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const [shipments, alerts, summary, decisionLog] = await Promise.all([
          api.getShipments(),
          api.getAlerts(),
          api.getSummary(),
          api.getDecisionLog(),
        ]);

        if (!active) {
          return;
        }

        setState({
          shipments,
          alerts,
          summary,
          decisionLog,
          lastUpdated: new Date(),
          loading: false,
          error: null,
        });
      } catch (error) {
        if (!active) {
          return;
        }
        setState((previous) => ({
          ...previous,
          loading: false,
          error: error instanceof Error ? error.message : "Failed to load dashboard data.",
        }));
      }
    };

    load();
    const interval = window.setInterval(load, POLL_INTERVAL_MS);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const topShipmentId = useMemo(
    () => state.summary?.top_priority_shipment_id ?? state.shipments[0]?.shipment_id,
    [state],
  );

  return { ...state, topShipmentId };
}
