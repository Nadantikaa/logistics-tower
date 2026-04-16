from typing import Literal

from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    shipment_id: str
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str
    confidence: int = Field(ge=0, le=100)
    visible: bool = True

