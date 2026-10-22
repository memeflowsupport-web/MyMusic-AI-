from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class GenerationJobCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    style: str | None = Field(default=None, max_length=80)
    instrumental: bool = False


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt: str
    style: str | None
    instrumental: bool
    status: JobStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class TrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    title: str
    audio_key: str | None
    duration_seconds: int | None
    created_at: datetime
