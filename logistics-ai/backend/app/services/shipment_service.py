from app.models.shipment import ShipmentSeed
from app.services.data_store import store


def list_shipment_seeds() -> list[ShipmentSeed]:
    return [ShipmentSeed.model_validate(item) for item in store.read_json("shipments.json")]

