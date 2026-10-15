import json
from pathlib import Path

ROOT = Path(__file__).parent
files = sorted((ROOT / "results").glob("*.json"))
data = json.loads(files[-1].read_text(encoding="utf-8"))  # latest run
truth = {
    json.loads(line)["car_id"]: json.loads(line)
    for line in (ROOT / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
}

for r in data["rows"]:
    if r["error"]:
        print(f"{r['car_id']}: ERROR {r['error']}")
        continue
    t, p = truth[r["car_id"]], r["pred"]
    problems = []
    for field, key in [
        ("make", "make_ok"),
        ("model", "model_ok"),
        ("body_type", "body_ok"),
        ("colour", "colour_ok"),
    ]:
        if r[key] is False:
            problems.append(f"{field}: label={t[field]!r} model={p[field]!r}")
    if r["pred_dmg"] != r["true_dmg"]:
        problems.append(
            f"damage: label={t['damages']} model={[d['type'] + '@' + d['location'] for d in p['damages']]}"
        )
    if problems:
        print(f"\n{r['car_id']}  (images/{r['car_id']})")
        for pr in problems:
            print("   -", pr)
