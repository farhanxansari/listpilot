import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.config import settings
from app.extract import extract_attributes

LABELS = ROOT / "ground_truth.jsonl"
IMAGES = ROOT / "images"
OUT = ROOT / "results"
FIELDS = {
    "make": "make_ok",
    "model": "model_ok",
    "body_type": "body_ok",
    "colour": "colour_ok",
}


def text_match(truth, pred, cutoff):
    if truth is None:
        return None
    if pred is None:
        return False
    return fuzz.token_set_ratio(truth.lower(), pred.lower()) >= cutoff


def exact(truth, pred):
    return None if truth is None else truth == pred


def evaluate_car(car):
    row = {"car_id": car["car_id"], "difficulty": car["difficulty"], "error": None}
    try:
        res = extract_attributes([IMAGES / car["car_id"] / f for f in car["images"]])
    except Exception as e:  # noqa: BLE001 - record failure, keep evaluating
        row["error"] = f"{type(e).__name__}: {e}"
        return row
    p = res.attributes
    row.update(
        latency=res.latency_s,
        attempts=res.attempts,
        tokens=res.input_tokens + res.output_tokens,
        pred=p.model_dump(),
        conf=p.confidence.model_dump(),
        make_ok=text_match(car["make"], p.make, 85),
        model_ok=text_match(car["model"], p.model, 80),
        body_ok=exact(car["body_type"], p.body_type),
        colour_ok=exact(car["colour"], p.colour),
        true_dmg=bool(car["damages"]),
        pred_dmg=bool(p.damages),
        true_types=sorted({d["type"] for d in car["damages"]}),
        pred_types=sorted({d.type for d in p.damages}),
    )
    return row


def accuracy(rows, key, cond=lambda r: True):
    vals = [r[key] for r in rows if r.get(key) is not None and cond(r)]
    return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)


def fmt(a):
    acc, n = a
    return "  n/a" if acc is None else f"{acc * 100:5.1f}% (n={n})"


def summarize(rows):
    ok = [r for r in rows if r["error"] is None]
    s = {
        "model": settings.llm_model,
        "cars": len(rows),
        "failures": len(rows) - len(ok),
    }

    print(f"\n=== {settings.llm_model} | {len(ok)}/{len(rows)} cars ok ===")
    print("\nField accuracy (all | hard only):")
    for field, key in FIELDS.items():
        a, h = accuracy(ok, key), accuracy(ok, key, lambda r: r["difficulty"] == "hard")
        s[f"{field}_acc"] = a[0]
        print(f"  {field:10s} {fmt(a)}   | {fmt(h)}")

    tp = sum(r["true_dmg"] and r["pred_dmg"] for r in ok)
    fp = sum(not r["true_dmg"] and r["pred_dmg"] for r in ok)
    fn = sum(r["true_dmg"] and not r["pred_dmg"] for r in ok)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    s.update(damage_precision=prec, damage_recall=rec)
    print("\nDamage detection (car level):")
    print(
        f"  precision {prec if prec is None else f'{prec:.2f}'} | "
        f"recall {rec if rec is None else f'{rec:.2f}'} | TP={tp} FP={fp} FN={fn}"
    )

    t_hit = sum(len(set(r["true_types"]) & set(r["pred_types"])) for r in ok)
    t_pred = sum(len(r["pred_types"]) for r in ok)
    t_true = sum(len(r["true_types"]) for r in ok)
    print(f"  damage-type precision {t_hit}/{t_pred} | recall {t_hit}/{t_true}")

    print("\nConfidence calibration (accuracy when conf >= 0.8 vs < 0.8):")
    for field, key in FIELDS.items():
        hi = accuracy(ok, key, lambda r, f=field: r["conf"][f] >= 0.8)
        lo = accuracy(ok, key, lambda r, f=field: r["conf"][f] < 0.8)
        print(f"  {field:10s} high {fmt(hi)}   | low {fmt(lo)}")

    lat = sorted(r["latency"] for r in ok)
    if lat:
        p95 = lat[min(len(lat) - 1, int(0.95 * len(lat)))]
        s.update(
            latency_mean=statistics.mean(lat),
            latency_p95=p95,
            retries=sum(r["attempts"] > 1 for r in ok),
            tokens_mean=statistics.mean(r["tokens"] for r in ok),
        )
        print(
            f"\nLatency mean {s['latency_mean']:.1f}s | p95 {p95:.1f}s | "
            f"avg tokens {s['tokens_mean']:.0f} | cars needing retry {s['retries']}"
        )
    for r in rows:
        if r["error"]:
            print(f"  ERROR {r['car_id']}: {r['error']}")
    return s


def main():
    cars = [
        json.loads(line)
        for line in LABELS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    subset = len(sys.argv) > 2 and sys.argv[1] == "--only"
    if subset:
        wanted = set(sys.argv[2].split(","))
        cars = [c for c in cars if c["car_id"] in wanted]
    rows = []
    for i, car in enumerate(cars, 1):
        row = evaluate_car(car)
        status = "ERR" if row["error"] else "ok"
        print(f"[{i}/{len(cars)}] {car['car_id']} {status}", flush=True)
        rows.append(row)
        if row["error"] and "RateLimit" in row["error"]:
            print("Rate limit hit - stopping early. Try again later.")
            break
        time.sleep(1)  # stay under free-tier rate limits

    summary = summarize(rows)
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    name = settings.llm_model.replace("/", "_")
    name += "_catalog" if settings.catalog_prompt else ""
    name += "_subset" if subset else ""
    (OUT / f"{name}_{stamp}.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nSaved results/{name}_{stamp}.json")


if __name__ == "__main__":
    main()
