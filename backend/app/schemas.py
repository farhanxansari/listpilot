from typing import Literal

from pydantic import BaseModel, Field

from app.vocab import BODY_TYPES, COLOURS, DAMAGE_LOCATIONS, DAMAGE_TYPES

BodyType = Literal[tuple(sorted(BODY_TYPES))]
Colour = Literal[tuple(sorted(COLOURS))]
DamageType = Literal[tuple(sorted(DAMAGE_TYPES))]
DamageLocation = Literal[tuple(sorted(DAMAGE_LOCATIONS))]
Confidence = float


class Damage(BaseModel):
    type: DamageType
    location: DamageLocation
    description: str = Field(
        description="Short visual description, e.g. 'shallow dent near handle'"
    )
    confidence: Confidence = Field(ge=0, le=1)


class FieldConfidence(BaseModel):
    make: Confidence = Field(ge=0, le=1)
    model: Confidence = Field(ge=0, le=1)
    body_type: Confidence = Field(ge=0, le=1)
    colour: Confidence = Field(ge=0, le=1)


class CarAttributes(BaseModel):
    make: str | None = Field(description="Manufacturer, null if not identifiable")
    model: str | None = Field(description="Model name, null if not identifiable")
    body_type: BodyType
    colour: Colour
    damages: list[Damage] = Field(
        description="Only clearly visible damage. Empty list if none."
    )
    confidence: FieldConfidence
    notes: str | None = Field(
        default=None,
        description="Anything limiting the assessment, e.g. 'rear not visible'",
    )


class SellerInput(BaseModel):
    registration_number: str
    make: str = Field(description="Declared by the seller, e.g. 'Maruti'")
    model: str = Field(description="Declared by the seller, e.g. 'Swift'")
    year: int = Field(ge=1990, le=2030)
    km_driven: int = Field(ge=0)
    fuel_type: str = Field(description="Petrol, Diesel, CNG, LPG or Electric")
    transmission_type: str = Field(description="Manual or Automatic")
    colour: Colour | None = None
    reported_damage: bool | None = Field(
        default=None, description="False = seller says the car has no damage"
    )
    seller_notes: str | None = None
