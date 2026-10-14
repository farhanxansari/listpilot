import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.vocab import (
    BODY_TYPES,
    COLOURS,
    DAMAGE_LOCATIONS,  # noqa: E402
    DAMAGE_TYPES,
    DIFFICULTIES,
    SOURCES,
)

ROOT = Path(__file__).parent
LABELS = ROOT / "ground_truth.jsonl"
IMAGES = ROOT / "images"
REQUIRED = {
    "car_id",
    "images",
    "make",
    "model",
    "body_type",
    "colour",
    "damages",
    "source",
    "difficulty",
}


def check(car: dict, line_no: int) -> list[str]:
    errs = []
    cid = car.get("car_id", f"line {line_no}")
    if missing := REQUIRED - car.keys():
        errs.append(f"{cid}: missing fields {sorted(missing)}")
        return errs
    if not car["images"]:
        errs.append(f"{cid}: no images listed")
    for img in car["images"]:
        if not (IMAGES / cid / img).exists():
            errs.append(f"{cid}: image not found -> images/{cid}/{img}")
    # make/model may be null for damage-dataset cars
    if car["body_type"] is not None and car["body_type"] not in BODY_TYPES:
        errs.append(f"{cid}: bad body_type '{car['body_type']}'")
    if car["colour"] is not None and car["colour"] not in COLOURS:
        errs.append(f"{cid}: bad colour '{car['colour']}'")
    if car["source"] not in SOURCES:
        errs.append(f"{cid}: bad source '{car['source']}'")
    if car["difficulty"] not in DIFFICULTIES:
        errs.append(f"{cid}: bad difficulty '{car['difficulty']}'")
    for d in car["damages"]:
        if d.get("type") not in DAMAGE_TYPES:
            errs.append(f"{cid}: bad damage type '{d.get('type')}'")
        if d.get("location") not in DAMAGE_LOCATIONS:
            errs.append(f"{cid}: bad damage location '{d.get('location')}'")
    return errs


def main() -> None:
    cars, errors, seen = [], [], set()
    for i, line in enumerate(LABELS.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            car = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON ({e})")
            continue
        if car.get("car_id") in seen:
            errors.append(f"line {i}: duplicate car_id '{car['car_id']}'")
        seen.add(car.get("car_id"))
        errors += check(car, i)
        cars.append(car)

    if errors:
        print(f"❌ {len(errors)} problem(s):")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    damaged = sum(1 for c in cars if c["damages"])
    print(f"✅ {len(cars)} cars valid")
    print(f"   damaged: {damaged} | clean: {len(cars) - damaged}")
    print(f"   hard: {sum(c['difficulty'] == 'hard' for c in cars)}")
    print(f"   sources: {dict(Counter(c['source'] for c in cars))}")


if __name__ == "__main__":
    main()
