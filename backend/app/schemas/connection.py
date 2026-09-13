"""schemas/connection.py — Pydantic API contracts for connection CRUD."""

from pydantic import BaseModel
from typing import Literal


class ConnectionCreate(BaseModel):
    name: str
    source_type: Literal["mysql", "mongodb"]
    dsn: str
    is_source: bool = True


class ConnectionRead(BaseModel):
    id: int
    name: str
    source_type: str
    is_source: bool

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None
