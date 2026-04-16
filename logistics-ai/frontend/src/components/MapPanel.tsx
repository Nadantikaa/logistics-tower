import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";

import type { Shipment } from "../types/shipment";

const locations: Record<string, [number, number]> = {
  "Chennai Port": [13.0827, 80.2707],
  "Mumbai Port": [18.9474, 72.8406],
  "Visakhapatnam Port": [17.6868, 83.2185],
  "Kolkata Port": [22.5411, 88.3112],
};

const selectedIcon = new L.DivIcon({
  className: "map-marker",
  html: '<div class="map-marker-inner map-marker-selected"></div>',
  iconSize: [22, 22],
});

const defaultIcon = new L.DivIcon({
  className: "map-marker",
  html: '<div class="map-marker-inner"></div>',
  iconSize: [18, 18],
});

interface MapPanelProps {
  shipments: Shipment[];
  selectedShipmentId: string | null;
}

export function MapPanel({ shipments, selectedShipmentId }: MapPanelProps) {
  return (
    <section className="panel map-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Live Geography</p>
          <h3>Shipment Map</h3>
        </div>
      </div>

      <div className="map-shell">
        <MapContainer center={[18.5, 80.2]} zoom={4.5} scrollWheelZoom={false} className="leaflet-map">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {shipments.map((shipment) => {
            const position = locations[shipment.current_location];
            if (!position) {
              return null;
            }

            return (
              <Marker
                key={shipment.shipment_id}
                position={position}
                icon={shipment.shipment_id === selectedShipmentId ? selectedIcon : defaultIcon}
              >
                <Popup>
                  <strong>{shipment.shipment_id}</strong>
                  <div>{shipment.current_location}</div>
                  <div>{shipment.decision?.action ?? "NO ACTION"}</div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </section>
  );
}
