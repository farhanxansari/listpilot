import json
from pathlib import Path

from app.agent import run_agent
from app.extract import extract_attributes
from app.schemas import SellerInput

ext = extract_attributes(sorted(Path("../evals/images/car_001").glob("*.jpg")))
seller = SellerInput(
    registration_number="HR 26 DK 8337",
    year=2019,
    km_driven=4200,
    fuel_type="Petrol",
    transmission_type="Automatic",
    seller_notes="Single owner, serviced at authorised centre.",
)

res = run_agent(ext.attributes, seller)
for t in res.trace:
    print(f"[{t['step']}] {t['tool']} {t['args']}\n     -> {t['result']}")
print("\nFLAGS:", json.dumps(res.state.flags, indent=2))
print("PRICE:", res.state.price)
print("LISTING:", json.dumps(res.state.listing, indent=2))
print(
    f"\nSTATUS={res.status} steps={res.steps} latency={res.latency_s:.1f}s tokens={res.input_tokens}/{res.output_tokens}"
)
