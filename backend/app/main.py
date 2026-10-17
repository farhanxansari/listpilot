import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app import pipeline
from app.body_types import expected_body_type
from app.config import settings
from app.db import (
    FINAL_STATUSES,
    Listing,
    events_after,
    get_listing,
    init_db,
    save_listing,
)
from app.schemas import SellerInput

MAX_PHOTOS = 6
MAX_PHOTO_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
STREAM_TIMEOUT_S = 600
SPECS_PATH = Path(__file__).parent / "assets" / "specs.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="ListPilot", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
# uploaded photos, so the frontend can show them (public: fine for a demo, not for production)
app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir, check_dir=False),
    name="uploads",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/catalog")
def catalog():
    """Makes and models the seller can pick from (the price model's training data)."""
    rows = json.loads(SPECS_PATH.read_text(encoding="utf-8"))
    by_make: dict[str, set[str]] = {}
    for r in rows:
        by_make.setdefault(r["brand"], set()).add(r["model"])
    return {
        "makes": [{"make": m, "models": sorted(v)} for m, v in sorted(by_make.items())]
    }


@app.post("/listings", status_code=202)
async def create_listing(
    background_tasks: BackgroundTasks,
    photos: Annotated[list[UploadFile], File(description="1-6 photos of ONE car")],
    seller: Annotated[str, Form(description="SellerInput as a JSON string")],
):
    try:
        seller_input = SellerInput.model_validate_json(seller)
    except ValidationError as e:
        raise HTTPException(422, detail=json.loads(e.json())) from e
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise HTTPException(400, f"Upload between 1 and {MAX_PHOTOS} photos.")

    listing_id = uuid.uuid4().hex[:12]
    folder = settings.upload_dir / listing_id
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, photo in enumerate(photos, 1):
        ext = ALLOWED_TYPES.get(photo.content_type or "")
        if ext is None:
            raise HTTPException(
                400, f"'{photo.filename}' must be a JPEG, PNG or WebP image."
            )
        data = await photo.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(400, f"'{photo.filename}' is larger than 8 MB.")
        path = folder / f"photo_{i}{ext}"
        path.write_bytes(data)
        paths.append(str(path))

    save_listing(
        Listing(
            id=listing_id,
            seller=seller_input.model_dump_json(),
            photos=json.dumps(paths),
        )
    )
    background_tasks.add_task(pipeline.run_pipeline, listing_id)
    return {
        "id": listing_id,
        "status": "queued",
        "stream_url": f"/listings/{listing_id}/stream",
    }


@app.get("/listings/{listing_id}")
def read_listing(listing_id: str):
    listing = get_listing(listing_id)
    if listing is None:
        raise HTTPException(404, "Listing not found.")
    seller = json.loads(listing.seller)
    return {
        "id": listing.id,
        "status": listing.status,
        "seller": seller,
        "declared_body_type": expected_body_type(seller.get("model")),
        "photos": [
            f"/uploads/{listing.id}/{Path(p).name}" for p in json.loads(listing.photos)
        ],
        "result": json.loads(listing.result) if listing.result else None,
        "error": listing.error,
        "created_at": listing.created_at,
    }


@app.get("/listings/{listing_id}/stream")
async def stream_listing(listing_id: str):
    """Server-Sent Events: one event per pipeline step, ends when the job finishes."""
    if get_listing(listing_id) is None:
        raise HTTPException(404, "Listing not found.")

    async def events():
        last_id, deadline = 0, time.monotonic() + STREAM_TIMEOUT_S
        while time.monotonic() < deadline:
            new = events_after(listing_id, last_id)
            for ev in new:
                last_id = ev.id
                yield f"id: {ev.id}\nevent: {ev.type}\ndata: {ev.data}\n\n"
            if not new and get_listing(listing_id).status in FINAL_STATUSES:
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
