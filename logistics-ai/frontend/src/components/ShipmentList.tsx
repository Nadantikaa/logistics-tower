import type { Shipment } from "../types/shipment";
import { ShipmentCard } from "./ShipmentCard";

interface ShipmentListProps {
  shipments: Shipment[];
  selectedShipmentId: string | null;
  onSelect: (shipmentId: string) => void;
}

export function ShipmentList({ shipments, selectedShipmentId, onSelect }: ShipmentListProps) {
  return (
    <section className="panel shipment-list">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Fleet Overview</p>
          <h3>Shipments</h3>
        </div>
      </div>
      <div className="shipment-list-grid">
        {shipments.map((shipment) => (
          <ShipmentCard
            key={shipment.shipment_id}
            shipment={shipment}
            selected={shipment.shipment_id === selectedShipmentId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </section>
  );
}
