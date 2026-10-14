from pathlib import Path

from app.extract import extract_attributes

car_dir = Path("../evals/images/car_001")
result = extract_attributes(sorted(car_dir.glob("*.jpg")))

print(result.attributes.model_dump_json(indent=2))
print(
    f"attempts={result.attempts} latency={result.latency_s:.1f}s "
    f"tokens in/out={result.input_tokens}/{result.output_tokens}"
)
