"""Reference body type for each car model, used to check what the seller declared.

Keys are lower-case model names. Matching picks the LONGEST key found in the
declared model, so "Swift Dzire VXI" matches "swift dzire" (sedan), not "swift".
"""

import re

BODY_TYPES_BY_MODEL = {
    # Maruti Suzuki
    "alto": "hatchback",
    "baleno": "hatchback",
    "celerio": "hatchback",
    "ciaz": "sedan",
    "dzire": "sedan",
    "swift dzire": "sedan",
    "eeco": "van",
    "ertiga": "muv",
    "ignis": "hatchback",
    "s-presso": "hatchback",
    "swift": "hatchback",
    "vitara": "suv",
    "vitara brezza": "suv",
    "brezza": "suv",
    "grand vitara": "suv",
    "wagon r": "hatchback",
    "xl6": "muv",
    "fronx": "suv",
    "s-cross": "suv",
    # Hyundai
    "aura": "sedan",
    "creta": "suv",
    "elantra": "sedan",
    "grand": "hatchback",
    "grand i10": "hatchback",
    "santro": "hatchback",
    "tucson": "suv",
    "venue": "suv",
    "verna": "sedan",
    "i10": "hatchback",
    "i20": "hatchback",
    "alcazar": "suv",
    "exter": "suv",
    # Honda
    "amaze": "sedan",
    "cr-v": "suv",
    "city": "sedan",
    "civic": "sedan",
    "jazz": "hatchback",
    "wr-v": "suv",
    "elevate": "suv",
    # Tata
    "altroz": "hatchback",
    "harrier": "suv",
    "hexa": "muv",
    "nexon": "suv",
    "safari": "suv",
    "tiago": "hatchback",
    "tigor": "sedan",
    "punch": "suv",
    "nano": "hatchback",
    # Mahindra
    "alturas": "suv",
    "bolero": "suv",
    "kuv": "suv",
    "kuv100": "suv",
    "marazzo": "muv",
    "scorpio": "suv",
    "scorpio-n": "suv",
    "thar": "suv",
    "xuv300": "suv",
    "xuv500": "suv",
    "xuv700": "suv",
    "xuv 3xo": "suv",
    # Kia
    "carnival": "muv",
    "seltos": "suv",
    "sonet": "suv",
    "carens": "muv",
    # Toyota
    "camry": "sedan",
    "fortuner": "suv",
    "glanza": "hatchback",
    "innova": "muv",
    "innova crysta": "muv",
    "yaris": "sedan",
    "urban cruiser": "suv",
    "hyryder": "suv",
    # Ford
    "aspire": "sedan",
    "ecosport": "suv",
    "endeavour": "suv",
    "figo": "hatchback",
    "freestyle": "hatchback",
    # Renault / Nissan / Datsun
    "duster": "suv",
    "kwid": "hatchback",
    "triber": "muv",
    "kiger": "suv",
    "kicks": "suv",
    "x-trail": "suv",
    "magnite": "suv",
    "go": "hatchback",
    "redigo": "hatchback",
    "redi-go": "hatchback",
    # Volkswagen / Skoda
    "polo": "hatchback",
    "vento": "sedan",
    "virtus": "sedan",
    "taigun": "suv",
    "octavia": "sedan",
    "rapid": "sedan",
    "superb": "sedan",
    "kushaq": "suv",
    "slavia": "sedan",
    # Others
    "hector": "suv",
    "astor": "suv",
    "compass": "suv",
    "wrangler": "suv",
    "gurkha": "suv",
    "d-max": "pickup",
    "mux": "suv",
    "cooper": "hatchback",
    # Luxury
    "a4": "sedan",
    "a6": "sedan",
    "a8": "sedan",
    "q7": "suv",
    "x1": "suv",
    "x3": "suv",
    "x4": "suv",
    "x5": "suv",
    "c-class": "sedan",
    "e-class": "sedan",
    "s-class": "sedan",
    "gls": "suv",
    "gl-class": "suv",
    "cayenne": "suv",
    "panamera": "sedan",
    "xc60": "suv",
    "xc90": "suv",
    "s90": "sedan",
}

_KEYS_LONGEST_FIRST = sorted(BODY_TYPES_BY_MODEL, key=len, reverse=True)


def expected_body_type(model: str | None) -> str | None:
    """Body type for a declared model name, or None if the model is unknown."""
    if not model:
        return None
    text = model.strip().lower()
    for key in _KEYS_LONGEST_FIRST:
        if re.search(rf"(?<![\w-]){re.escape(key)}(?![\w-])", text):
            return BODY_TYPES_BY_MODEL[key]
    return None
