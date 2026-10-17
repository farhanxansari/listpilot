"""Send one car to the running API and print the live progress stream.

Start the server first (in another terminal):
    uv run uvicorn app.main:app --reload
Then:
    uv run python try_api.py
    uv run python try_api.py ..\\evals\\images\\car_007\\front.jpg   (any photo(s))
"""

import json
import sys
from pathlib import Path

import httpx

API = "http://localhost:8000"
PHOTOS = [Path(p) for p in sys.argv[1:]] or [Path("../evals/images/car_001/front.jpg")]
SELLER = {
    "registration_number": "HR 26 DK 8337",
    "make": "Honda",
    "model": "Amaze",
    "year": 2019,
    "km_driven": 42000,
    "fuel_type": "Petrol",
    "transmission_type": "Manual",
    "colour": "grey",
    "reported_damage": False,
    "seller_notes": "Single owner, serviced at authorised centre.",
}

files = [("photos", (p.name, p.read_bytes(), "image/jpeg")) for p in PHOTOS]
resp = httpx.post(f"{API}/listings", files=files, data={"seller": json.dumps(SELLER)})
if resp.status_code != 202:
    print(resp.status_code, resp.text)
    sys.exit(1)
listing_id = resp.json()["id"]
print(f"Created listing {listing_id}\n--- live stream ---")

with httpx.stream("GET", f"{API}/listings/{listing_id}/stream", timeout=None) as stream:
    event = None
    for line in stream.iter_lines():
        if line.startswith("event: "):
            event = line[len("event: ") :]
        elif line.startswith("data: "):
            print(f"[{event}] {line[len('data: ') :]}")

result = httpx.get(f"{API}/listings/{listing_id}").json()
print("\n--- final result ---")
print(json.dumps(result, indent=2, ensure_ascii=False))
