import math
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from pydantic import BaseModel, ValidationError
from rapidfuzz import fuzz, process

from app.guardrails import check_listing
from app.schemas import CarAttributes, SellerInput

ASSETS = Path(__file__).parent / "assets"
_PRICE = joblib.load(ASSETS / "price_model.joblib")
_SPECS = pd.read_json(ASSETS / "specs.json")
_BRANDS = sorted(_SPECS["brand"].unique())

RTO_STATES = {
    "DL": "Delhi",
    "HR": "Haryana",
    "UP": "Uttar Pradesh",
    "MH": "Maharashtra",
    "KA": "Karnataka",
    "TN": "Tamil Nadu",
    "RJ": "Rajasthan",
    "GJ": "Gujarat",
    "WB": "West Bengal",
    "TS": "Telangana",
    "AP": "Andhra Pradesh",
    "PB": "Punjab",
    "MP": "Madhya Pradesh",
    "KL": "Kerala",
    "BR": "Bihar",
    "CH": "Chandigarh",
    "UK": "Uttarakhand",
}
STD_REG = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})$")
BH_REG = re.compile(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$")


@dataclass
class AgentState:
    attributes: CarAttributes
    seller: SellerInput
    flags: list[dict] = field(default_factory=list)
    price: dict | None = None
    listing: dict | None = None
    calls: dict = field(default_factory=dict)


# ---------- tools ----------
class ValidateRegistrationArgs(BaseModel):
    registration_number: str


def validate_registration(a: ValidateRegistrationArgs, state) -> dict:
    reg = re.sub(r"[\s-]", "", a.registration_number.upper())
    if BH_REG.match(reg):
        return {"valid": True, "series": "BH", "normalized": reg}
    if m := STD_REG.match(reg):
        code = m.group(1)
        if code not in RTO_STATES:
            return {"valid": False, "reason": f"unknown state code '{code}'"}
        return {
            "valid": True,
            "series": "standard",
            "state": RTO_STATES[code],
            "rto_number": m.group(2),
            "normalized": reg,
        }
    return {"valid": False, "reason": "does not match Indian registration formats"}


class MileageArgs(BaseModel):
    year: int
    km_driven: int


def check_mileage(a: MileageArgs, state) -> dict:
    age = max(date.today().year - a.year, 1)
    per_year = a.km_driven / age
    if age >= 2 and per_year < 2_000:
        verdict = "suspiciously_low"  # possible odometer tampering
    elif per_year > 40_000:
        verdict = "very_high"
    else:
        verdict = "normal"
    return {"verdict": verdict, "km_per_year": round(per_year), "age_years": age}


def _match_category(value: str, column: str) -> str:
    """Case-insensitive match to a category the price model was trained on."""
    for cat in _PRICE["categories"][column]:
        if cat.lower() == value.strip().lower():
            return cat
    return value  # unknown -> model treats it as missing


class PriceArgs(BaseModel):
    brand: str
    model: str
    year: int
    km_driven: int
    fuel_type: str
    transmission_type: str


def estimate_price(a: PriceArgs, state) -> dict:
    b = process.extractOne(a.brand, _BRANDS, scorer=fuzz.WRatio, score_cutoff=80)
    if not b:
        return {
            "error": f"brand '{a.brand}' not in pricing data",
            "retryable": False,
            "next_step": "flag_for_inspection",
        }
    brand = b[0]
    models = _SPECS.loc[_SPECS.brand == brand, "model"].tolist()
    mm = process.extractOne(a.model, models, scorer=fuzz.WRatio, score_cutoff=75)
    if not mm:
        return {
            "error": f"model '{a.model}' not in pricing data for {brand}",
            "retryable": False,
            "next_step": "flag_for_inspection",
        }
    spec = _SPECS[(_SPECS.brand == brand) & (_SPECS.model == mm[0])].iloc[0]

    row = {
        "brand": brand,
        "model": mm[0],
        "vehicle_age": max(date.today().year - a.year, 0),
        "km_driven": a.km_driven,
        "fuel_type": _match_category(a.fuel_type, "fuel_type"),
        "transmission_type": _match_category(a.transmission_type, "transmission_type"),
        "engine": spec.engine,
        "max_power": spec.max_power,
        "mileage": spec.mileage,
        "seats": spec.seats,
    }
    X = pd.DataFrame([row])
    for col, cats in _PRICE["categories"].items():
        X[col] = pd.Categorical(X[col], categories=cats)
    X = X[_PRICE["features"]]

    m, q = _PRICE["models"], _PRICE["qhat"]

    def r(v):
        return int(round(math.exp(v), -3))

    result = {
        "matched": f"{brand} {mm[0]}",
        "low": r(m[0.1].predict(X)[0] - q),
        "mid": r(m[0.5].predict(X)[0]),
        "high": r(m[0.9].predict(X)[0] + q),
        "note": "80% calibrated price band in INR",
    }
    state.price = result
    return result


class FlagArgs(BaseModel):
    reason: str
    severity: Literal["low", "high"]


def flag_for_inspection(a: FlagArgs, state) -> dict:
    state.flags.append({"reason": a.reason, "severity": a.severity, "by": "agent"})
    return {"flagged": True, "total_flags": len(state.flags)}


class ListingArgs(BaseModel):
    title: str
    description: str
    highlights: list[str]


def submit_listing(a: ListingArgs, state) -> dict:
    issues = check_listing(a, state)
    if issues:
        return {"accepted": False, "issues": issues}
    state.listing = a.model_dump()
    return {"accepted": True}


# ---------- registry ----------
TOOLS = {
    "validate_registration": (
        ValidateRegistrationArgs,
        validate_registration,
        "Validate an Indian registration number and return its state.",
    ),
    "check_mileage": (
        MileageArgs,
        check_mileage,
        "Check if the odometer reading is plausible for the car's age.",
    ),
    "estimate_price": (
        PriceArgs,
        estimate_price,
        "Estimate an 80% calibrated price band in INR for the car. "
        "If it returns retryable=false, do not call it again.",
    ),
    "flag_for_inspection": (
        FlagArgs,
        flag_for_inspection,
        "Flag something that needs a human inspector to review.",
    ),
    "submit_listing": (
        ListingArgs,
        submit_listing,
        "Submit the final listing. May be rejected with issues to fix.",
    ),
}

MAX_CALLS = {
    "validate_registration": 2,
    "check_mileage": 2,
    "estimate_price": 2,
    "flag_for_inspection": 6,
    "submit_listing": 3,
}


def tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": d,
                "parameters": args.model_json_schema(),
            },
        }
        for n, (args, _, d) in TOOLS.items()
    ]


def run_tool(name: str, raw_args: str, state: AgentState) -> dict:
    if name not in TOOLS:
        return {"error": f"unknown tool '{name}'"}
    state.calls[name] = state.calls.get(name, 0) + 1
    if state.calls[name] > MAX_CALLS.get(name, 3):
        return {
            "error": f"{name} call limit reached. Do not call it again; "
            "flag any problem and submit the listing."
        }
    args_model, fn, _ = TOOLS[name]
    try:
        return fn(args_model.model_validate_json(raw_args or "{}"), state)
    except ValidationError as e:
        return {"error": f"invalid arguments: {e}"}
    except Exception as e:  # tool errors go back to the model, never crash the loop
        return {"error": f"{type(e).__name__}: {e}"}
