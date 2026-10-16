import base64
import io
import json
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from PIL import Image
from pydantic import ValidationError

from app.config import settings
from app.schemas import CarAttributes

client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
MAX_ATTEMPTS = 3
CATALOG_PATH = Path(__file__).parent / "assets" / "specs.json"


def _catalog_text() -> str:
    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    by_brand: dict[str, set[str]] = {}
    for r in rows:
        by_brand.setdefault(r["brand"], set()).add(r["model"])
    return "\n".join(
        f"- {b}: {', '.join(sorted(m))}" for b, m in sorted(by_brand.items())
    )


BASE_RULES = """You are a used-car inspection assistant for an Indian car marketplace.
You receive photos of ONE car from different angles. Extract its attributes.

Rules:
- Report only damage you can CLEARLY see. Reflections, dirt, shadows and panel gaps are NOT damage.
- If unsure of make or model, return null and give low confidence. Never guess confidently.
- Confidence is 0-1: how sure you are from the photos alone.
"""

CATALOG_RULES = f"""
These are cars sold in INDIA. Many Indian models look like foreign models
(e.g. Mahindra Thar vs Jeep Wrangler, Tata Punch vs Toyota Yaris Cross,
Mahindra XUV700 vs Mazda CX-8). Prefer the Indian-market identification.
If the car matches a make/model in this list, use EXACTLY these names:
{_catalog_text()}
If it is not in the list, give your best identification and a lower model confidence.
"""

SYSTEM_PROMPT = (
    BASE_RULES
    + (CATALOG_RULES if settings.catalog_prompt else "")
    + "\n- Respond with ONLY a JSON object matching this schema, no prose:\n\n"
    + json.dumps(CarAttributes.model_json_schema())
)


@dataclass
class ExtractionResult:
    attributes: CarAttributes
    attempts: int
    latency_s: float
    input_tokens: int
    output_tokens: int


def _encode(path: Path, max_side: int = 1024) -> str:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))  # smaller image = fewer tokens = cheaper
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def extract_attributes(image_paths: list[Path]) -> ExtractionResult:
    content = [{"type": "text", "text": f"{len(image_paths)} photo(s) of the car:"}]
    content += [
        {"type": "image_url", "image_url": {"url": _encode(p)}} for p in image_paths
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]

    start, in_tok, out_tok = time.perf_counter(), 0, 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        in_tok += resp.usage.prompt_tokens
        out_tok += resp.usage.completion_tokens
        raw = resp.choices[0].message.content
        try:
            attrs = CarAttributes.model_validate_json(raw)
            return ExtractionResult(
                attrs, attempt, time.perf_counter() - start, in_tok, out_tok
            )
        except ValidationError as e:
            # feed the exact error back so the model can self-correct
            messages += [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": f"Invalid output. Fix these errors and return only JSON:\n{e}",
                },
            ]
    raise RuntimeError(f"Extraction failed after {MAX_ATTEMPTS} attempts")
