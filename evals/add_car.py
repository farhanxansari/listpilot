"""Add one car to the eval set by answering a few questions.

Usage (from the evals folder):
    uv run python add_car.py candidates\\hyundai_creta\\2.jpg
    uv run python add_car.py photo1.jpg photo2.jpg     (several angles of ONE car)
"""

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.vocab import BODY_TYPES, COLOURS, DAMAGE_LOCATIONS, DAMAGE_TYPES

LABELS = ROOT / "ground_truth.jsonl"
IMAGES = ROOT / "images"
CANDIDATES = ROOT / "candidates"
CREDITS = CANDIDATES / "credits.csv"


def choose(question: str, options: list[str]) -> str:
    print(f"\n{question}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        answer = input("Type the number: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print("  Please type one of the numbers shown.")


def ask(question: str, allow_blank: bool = False) -> str | None:
    while True:
        answer = input(f"\n{question}: ").strip()
        if answer:
            return answer
        if allow_blank:
            return None
        print("  This can't be empty.")


def yes(question: str) -> bool:
    return input(f"\n{question} (y/n): ").strip().lower().startswith("y")


def next_car_id() -> str:
    used = set()
    if LABELS.exists():
        for line in LABELS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                used.add(json.loads(line)["car_id"])
    n = 1
    while f"car_{n:03d}" in used or (IMAGES / f"car_{n:03d}").exists():
        n += 1
    return f"car_{n:03d}"


def find_credit(photo: Path) -> str | None:
    if not CREDITS.exists():
        return None
    try:
        rel = photo.resolve().relative_to(CANDIDATES.resolve()).as_posix()
    except ValueError:
        return None
    with CREDITS.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["file"] == rel:
                return row["commons_page"]
    return None


def main() -> None:
    photos = [Path(p) for p in sys.argv[1:]]
    if not photos:
        print(
            "Give the photo path(s), e.g.:  uv run python add_car.py candidates\\tata_nexon\\1.jpg"
        )
        sys.exit(1)
    for p in photos:
        if not p.exists():
            print(f"File not found: {p}")
            sys.exit(1)

    car_id = next_car_id()
    print(f"\n=== Labelling {car_id} ({len(photos)} photo(s)) ===")
    print("Open the photo and answer from what you SEE in it.")

    make = ask(
        "Make, e.g. Maruti Suzuki / Hyundai / Tata (leave blank if unknown)",
        allow_blank=True,
    )
    model = ask(
        "Model, e.g. Swift / Creta / Nexon (leave blank if unknown)", allow_blank=True
    )
    body_type = choose("Body type?", sorted(BODY_TYPES))
    colour = choose("Main colour?", sorted(COLOURS))

    damages = []
    while yes(
        "Is there damage you can CLEARLY see?" if not damages else "Any MORE damage?"
    ):
        damages.append(
            {
                "type": choose("What kind of damage?", sorted(DAMAGE_TYPES)),
                "location": choose("Where on the car?", sorted(DAMAGE_LOCATIONS)),
            }
        )

    difficulty = choose(
        "Is this photo hard (night, glare, blurry, partly hidden)?", ["normal", "hard"]
    )

    credit = find_credit(photos[0])
    if credit:
        source = "wikimedia"
    else:
        source = choose(
            "Where is this photo from?", ["own", "damage_dataset", "stanford"]
        )

    names = (
        ["front.jpg"]
        if len(photos) == 1
        else [f"photo_{i}.jpg" for i in range(1, len(photos) + 1)]
    )
    entry = {
        "car_id": car_id,
        "images": names,
        "make": make,
        "model": model,
        "body_type": body_type,
        "colour": colour,
        "damages": damages,
        "source": source,
        "difficulty": difficulty,
    }
    if credit:
        entry["credit"] = credit

    print("\nThis will be saved:")
    print(json.dumps(entry, indent=2))
    if not yes("Save it?"):
        print("Cancelled. Nothing was saved.")
        return

    folder = IMAGES / car_id
    folder.mkdir(parents=True, exist_ok=True)
    for src, name in zip(photos, names):
        shutil.copy(src, folder / name)
    with LABELS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"\nSaved {car_id}. Next car: run the same command with another photo.")


if __name__ == "__main__":
    main()
