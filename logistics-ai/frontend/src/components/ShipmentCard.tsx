import { useState } from "react";

import type { Shipment } from "../types/shipment";
import { RiskBadge } from "./RiskBadge";
import { WhyDrawer } from "./WhyDrawer";

interface ShipmentCardProps {
  shipment: Shipment;
  selected: boolean;
  onSelect: (shipmentId: string) => void;
}

export function ShipmentCard({ shipment, selected, onSelect }: ShipmentCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <article className={`shipment-card ${selected ? "selected" : ""}`} onClick={() => onSelect(shipment.shipment_id)}>
      <div className="shipment-card-top">
        <div>
          <p className="shipment-id">{shipment.shipment_id}</p>
          <strong>{shipment.current_location}</strong>
        </div>
        <RiskBadge riskLevel={shipment.risk_level} />
      </div>

      <p className="shipment-route">
        {shipment.origin} to {shipment.destination}
      </p>
      <div className="shipment-card-bottom">
        <span>Priority {shipment.priority}</span>
        <button
          className="mini-button"
          onClick={(event) => {
            event.stopPropagation();
            setOpen((value) => !value);
          }}
          type="button"
        >
          Why?
        </button>
      </div>
      {open ? <WhyDrawer shipment={shipment} /> : null}
    </article>
  );
}
