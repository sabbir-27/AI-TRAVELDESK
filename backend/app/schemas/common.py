"""Common response and health check schemas."""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    database: str
    redis: str
