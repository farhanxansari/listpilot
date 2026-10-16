"""Compare what the seller declared with what the photos show.

Deterministic code, not the LLM: the vision model is reliable at body type,
colour and damage, but not at naming Indian models, so it verifies the seller's
declaration instead of identifying the car.
"""

from app.body_types import expected_body_type
from app.schemas import CarAttributes, SellerInput

MIN_CONFIDENCE = 0.7  # ignore photo readings the model itself is unsure about
SAME_BODY = [{"suv", "muv"}]  # vision often mixes these up; not a real mismatch
SAME_COLOUR = [{"grey", "silver"}]


def _compatible(a: str, b: str, groups: list[set[str]]) -> bool:
    return a == b or any(a in g and b in g for g in groups)


def verify(seller: SellerInput, seen: CarAttributes) -> list[dict]:
    """Return flags for every mismatch between the declaration and the photos."""
    flags = []
    declared = f"{seller.make} {seller.model}"

    expected = expected_body_type(seller.model)
    if expected is None:
        flags.append(
            {
                "check": "catalog",
                "severity": "low",
                "by": "verify",
                "reason": f"Declared model '{declared}' is not in the reference data; "
                "body type could not be verified.",
            }
        )
    elif (
        seen.body_type != "other"
        and seen.confidence.body_type >= MIN_CONFIDENCE
        and not _compatible(expected, seen.body_type, SAME_BODY)
    ):
        flags.append(
            {
                "check": "body_type",
                "severity": "high",
                "by": "verify",
                "reason": f"Seller declared {declared} (a {expected}), "
                f"but the photos show a {seen.body_type}.",
            }
        )

    if (
        seller.colour
        and seen.confidence.colour >= MIN_CONFIDENCE
        and not _compatible(seller.colour, seen.colour, SAME_COLOUR)
    ):
        flags.append(
            {
                "check": "colour",
                "severity": "low",
                "by": "verify",
                "reason": f"Seller declared colour {seller.colour}, "
                f"but the photos show {seen.colour}.",
            }
        )

    if seller.reported_damage is False and seen.damages:
        found = ", ".join(f"{d.type} on {d.location}" for d in seen.damages)
        flags.append(
            {
                "check": "damage",
                "severity": "high",
                "by": "verify",
                "reason": f"Seller reported no damage, but the photos show: {found}.",
            }
        )

    return flags
