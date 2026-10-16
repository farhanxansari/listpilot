"""Persistence for listing jobs and their progress events.

SQLite locally; set DATABASE_URL to a Postgres URL in production, no code change.
Events are stored (not just pushed) so a client that reconnects to the stream
gets the full history.
"""

import json
from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.config import settings

FINAL_STATUSES = {"ready_to_publish", "needs_review", "failed"}

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args)


def _now() -> datetime:
    return datetime.now(UTC)


class Listing(SQLModel, table=True):
    id: str = Field(primary_key=True)
    status: str = (
        "queued"  # queued -> running -> ready_to_publish | needs_review | failed
    )
    seller: str  # SellerInput as JSON
    photos: str  # JSON list of file paths
    result: str | None = None  # final output as JSON
    error: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    listing_id: str = Field(index=True)
    type: str
    data: str  # JSON
    created_at: datetime = Field(default_factory=_now)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_listing(listing_id: str) -> Listing | None:
    with Session(engine) as s:
        return s.get(Listing, listing_id)


def save_listing(listing: Listing) -> None:
    with Session(engine) as s:
        s.add(listing)
        s.commit()


def update_listing(listing_id: str, **fields) -> None:
    with Session(engine) as s:
        listing = s.get(Listing, listing_id)
        for k, v in fields.items():
            setattr(listing, k, v)
        listing.updated_at = _now()
        s.add(listing)
        s.commit()


def add_event(listing_id: str, type_: str, data: dict) -> None:
    with Session(engine) as s:
        s.add(
            Event(listing_id=listing_id, type=type_, data=json.dumps(data, default=str))
        )
        s.commit()


def events_after(listing_id: str, last_id: int) -> list[Event]:
    with Session(engine) as s:
        query = (
            select(Event)
            .where(Event.listing_id == listing_id, Event.id > last_id)
            .order_by(Event.id)
        )
        return list(s.exec(query).all())
