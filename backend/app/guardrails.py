import re

RISKY_FEATURES = [
    "sunroof",
    "leather",
    "alloy",
    "navigation",
    "cruise control",
    "airbags",
    "abs",
    "touchscreen",
    "reverse camera",
    "360 camera",
]
DAMAGE_WORDS = ["damage", "dent", "scratch", "crack", "broken"]
SUBJECTIVE_CLAIMS = [
    "excellent condition",
    "mint condition",
    "like new",
    "perfect condition",
    "immaculate",
    "pristine",
    "showroom condition",
]


def _has(word: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def check_listing(listing, state) -> list[str]:
    """Return a list of problems. Empty list = listing is safe to publish."""
    issues = []
    text = " ".join([listing.title, listing.description, *listing.highlights]).lower()
    notes = (state.seller.seller_notes or "").lower()
    attrs = state.attributes

    if state.price is None and not state.flags:
        issues.append(
            "Call estimate_price before submitting (or flag why pricing failed)."
        )

    if attrs.damages and not any(_has(w, text) for w in DAMAGE_WORDS):
        issues.append("Photos show damage but the listing does not disclose it.")

    make = state.seller.make
    if make.split()[0].lower() not in text:
        issues.append(f"Listing should name the make ({make}).")

    for feat in RISKY_FEATURES:
        if _has(feat, text) and not _has(feat, notes):
            issues.append(
                f"Mentions '{feat}', which is not supported by photos or seller notes."
            )

    if "₹" in text or _has("lakh", text) or _has("rs", text):
        issues.append(
            "Do not write prices in the listing text; the price band is shown separately."
        )

    reg = re.sub(r"[\s-]", "", state.seller.registration_number.lower())
    if reg in re.sub(r"[\s-]", "", text):
        issues.append("Do not include the registration number in a public listing.")

    for claim in SUBJECTIVE_CLAIMS:
        if claim in text and claim not in notes:
            issues.append(
                f"Subjective claim '{claim}' is not supported; describe facts instead."
            )

    return issues
