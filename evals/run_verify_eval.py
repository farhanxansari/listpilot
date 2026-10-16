"""Offline eval of seller-declaration verification. Makes NO API calls.

It reuses the vision predictions saved by run_extraction_eval.py and checks:
  1. Honest sellers  - declare the true model: how often are they wrongly flagged?
  2. Wrong model     - declare a model with a different body type: how often caught?
  3. Hidden damage   - declare "no damage": damaged cars caught, clean cars left alone?

Usage (from the evals folder):
    uv run --project ..\\backend python run_verify_eval.py results\\<baseline run>.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.body_types import expected_body_type
from app.schemas import CarAttributes, SellerInput
from app.verify import verify

LABELS = ROOT / "ground_truth.jsonl"
# a decoy model whose body type differs from the true one
DECOYS = {
    "hatchback": ("Hyundai", "Creta"),
    "sedan": ("Hyundai", "Creta"),
    "suv": ("Maruti", "Swift"),
    "muv": ("Maruti", "Swift"),
    "pickup": ("Maruti", "Swift"),
    "van": ("Hyundai", "Creta"),
}


def seller(make, model, reported_damage=None):
    return SellerInput(
        registration_number="DL3CAB1234",
        make=make,
        model=model,
        year=2019,
        km_driven=40000,
        fuel_type="Petrol",
        transmission_type="Manual",
        reported_damage=reported_damage,
    )


def flagged(flags, check):
    return any(f["check"] == check for f in flags)


def pct(hit, total):
    return f"{hit}/{total}" + (f" ({100 * hit / total:.0f}%)" if total else "")


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: uv run --project ..\\backend python run_verify_eval.py results\\<run>.json"
        )
        sys.exit(1)
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["rows"]
    truth = {
        json.loads(line)["car_id"]: json.loads(line)
        for line in LABELS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    honest_n = honest_fa = wrong_n = wrong_caught = 0
    dmg_n = dmg_caught = clean_n = clean_fa = 0
    notes = []

    for r in rows:
        car = truth.get(r["car_id"])
        if r["error"] or car is None:
            continue
        seen = CarAttributes.model_validate(r["pred"])
        cid = r["car_id"]

        true_body = expected_body_type(car["model"])
        if car["make"] and car["model"] and true_body:
            honest_n += 1
            if flagged(verify(seller(car["make"], car["model"]), seen), "body_type"):
                honest_fa += 1
                notes.append(
                    f"{cid}: honest seller flagged ({car['model']} is a {true_body}, "
                    f"photos read as {seen.body_type})"
                )

            make, model = DECOYS[true_body]
            wrong_n += 1
            if flagged(verify(seller(make, model), seen), "body_type"):
                wrong_caught += 1
            else:
                notes.append(
                    f"{cid}: wrong model '{model}' NOT caught "
                    f"(photos read as {seen.body_type}, "
                    f"conf {seen.confidence.body_type:.2f})"
                )

        flags = verify(seller("Maruti", "Swift", reported_damage=False), seen)
        if car["damages"]:
            dmg_n += 1
            if flagged(flags, "damage"):
                dmg_caught += 1
            else:
                notes.append(f"{cid}: hidden damage NOT caught")
        else:
            clean_n += 1
            if flagged(flags, "damage"):
                clean_fa += 1
                notes.append(f"{cid}: clean car wrongly flagged for damage")

    print("=== Seller-declaration verification (offline, no API calls) ===\n")
    print(f"Wrong model declared  -> caught        {pct(wrong_caught, wrong_n)}")
    print(f"Honest declaration    -> false alarm   {pct(honest_fa, honest_n)}")
    print(f"Damage hidden         -> caught        {pct(dmg_caught, dmg_n)}")
    print(f"Clean car, no damage  -> false alarm   {pct(clean_fa, clean_n)}")
    if notes:
        print("\nDetails:")
        for n in notes:
            print("  -", n)


if __name__ == "__main__":
    main()
