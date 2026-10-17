"""Runs one listing job end to end: photos -> verification -> agent -> result.

Heavy modules (vision client, LightGBM price model) are imported inside the
function, so the API starts fast and tests never load them.
"""

import json
import time
from pathlib import Path

from app.db import add_event, get_listing, update_listing


def run_pipeline(listing_id: str) -> None:
    from app.agent import run_agent
    from app.extract import extract_attributes
    from app.schemas import SellerInput

    listing = get_listing(listing_id)
    seller = SellerInput.model_validate_json(listing.seller)
    photos = [Path(p) for p in json.loads(listing.photos)]

    def emit(type_: str, data: dict) -> None:
        add_event(listing_id, type_, data)

    start = time.perf_counter()
    update_listing(listing_id, status="running")
    emit("step", {"name": "photos", "message": f"Checking {len(photos)} photo(s)"})
    try:
        ext = extract_attributes(photos)
        checks = ext.attributes.model_dump(
            exclude={"make", "model"}
        )  # keep confidence for the UI
        emit("photo_checks", checks)

        res = run_agent(ext.attributes, seller, on_event=emit)

        result = {
            "status": res.status,
            "listing": res.state.listing,
            "price": res.state.price,
            "flags": res.state.flags,
            "photo_checks": checks,
            "metrics": {
                "latency_s": round(time.perf_counter() - start, 1),
                "tokens": ext.input_tokens
                + ext.output_tokens
                + res.input_tokens
                + res.output_tokens,
                "agent_steps": res.steps,
            },
        }
        update_listing(listing_id, result=json.dumps(result, default=str))
        emit("done", {"status": res.status})
        update_listing(
            listing_id, status=res.status
        )  # last, so streams see "done" first
    except Exception as e:  # noqa: BLE001 - any failure must end the job, not hang it
        message = f"{type(e).__name__}: {e}"
        emit("error", {"message": message})
        update_listing(listing_id, status="failed", error=message)
