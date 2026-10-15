"""Re-score a saved eval run against the CURRENT labels, without calling the model.

Use it after fixing labels in ground_truth.jsonl: the model's saved predictions
are compared again, so you don't spend API tokens re-running the model.

Usage (from the evals folder):
    uv run --project ..\\backend python rescore.py results\\<run file>.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from run_extraction_eval import exact, summarize, text_match

LABELS = ROOT / "ground_truth.jsonl"


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: uv run --project ..\\backend python rescore.py results\\<run file>.json"
        )
        sys.exit(1)
    run_path = Path(sys.argv[1])
    data = json.loads(run_path.read_text(encoding="utf-8"))
    truth = {
        json.loads(line)["car_id"]: json.loads(line)
        for line in LABELS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    rows = []
    for old in data["rows"]:
        car = truth.get(old["car_id"])
        if car is None:
            continue  # car removed from the labels since this run
        row = dict(old)
        row["difficulty"] = car["difficulty"]
        if old["error"] is None:
            p = old["pred"]
            row.update(
                make_ok=text_match(car["make"], p["make"], 85),
                model_ok=text_match(car["model"], p["model"], 80),
                body_ok=exact(car["body_type"], p["body_type"]),
                colour_ok=exact(car["colour"], p["colour"]),
                true_dmg=bool(car["damages"]),
                true_types=sorted({d["type"] for d in car["damages"]}),
            )
        rows.append(row)

    summary = summarize(rows)
    out = run_path.with_name(run_path.stem + "_rescored.json")
    out.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
