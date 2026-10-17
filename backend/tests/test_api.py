"""API tests. The real pipeline (LLM calls) is replaced by a fake one."""

import json

import pytest
from app import main, pipeline
from app.db import add_event, update_listing
from fastapi.testclient import TestClient

SELLER = {
    "registration_number": "DL3CAB1234",
    "make": "Maruti",
    "model": "Swift",
    "year": 2019,
    "km_driven": 40000,
    "fuel_type": "Petrol",
    "transmission_type": "Manual",
}
JPEG = ("car.jpg", b"\xff\xd8\xff fake image bytes", "image/jpeg")


def fake_pipeline(listing_id: str) -> None:
    update_listing(listing_id, status="running")
    add_event(listing_id, "step", {"name": "photos"})
    update_listing(listing_id, result=json.dumps({"status": "ready_to_publish"}))
    add_event(listing_id, "done", {"status": "ready_to_publish"})
    update_listing(listing_id, status="ready_to_publish")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(pipeline, "run_pipeline", fake_pipeline)
    with TestClient(main.app) as c:
        yield c


def create(client, photos=(JPEG,), seller=SELLER):
    files = [("photos", p) for p in photos]
    return client.post("/listings", files=files, data={"seller": json.dumps(seller)})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_read_listing(client):
    resp = create(client)
    assert resp.status_code == 202
    listing_id = resp.json()["id"]
    body = client.get(f"/listings/{listing_id}").json()
    assert body["status"] == "ready_to_publish"
    assert body["result"]["status"] == "ready_to_publish"
    assert body["seller"]["model"] == "Swift"
    assert body["declared_body_type"] == "hatchback"
    assert body["photos"][0].startswith(f"/uploads/{listing_id}/")
    assert client.get(body["photos"][0]).status_code == 200


def test_stream_ends_with_done(client):
    listing_id = create(client).json()["id"]
    text = client.get(f"/listings/{listing_id}/stream").text
    assert "event: step" in text
    assert text.rstrip().split("\n\n")[-1].startswith("id:")
    assert "event: done" in text


def test_invalid_seller_is_rejected(client):
    assert create(client, seller={**SELLER, "year": 1800}).status_code == 422


def test_too_many_photos_rejected(client):
    assert create(client, photos=[JPEG] * 7).status_code == 400


def test_non_image_rejected(client):
    bad = ("notes.txt", b"hello", "text/plain")
    assert create(client, photos=[bad]).status_code == 400


def test_unknown_listing_is_404(client):
    assert client.get("/listings/nope").status_code == 404
    assert client.get("/listings/nope/stream").status_code == 404


def test_catalog_lists_makes_and_models(client):
    makes = {m["make"]: m["models"] for m in client.get("/catalog").json()["makes"]}
    assert "Honda" in makes
    assert "Amaze" in makes["Honda"]
