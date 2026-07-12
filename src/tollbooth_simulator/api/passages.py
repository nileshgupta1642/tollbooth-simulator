from datetime import datetime
from uuid import UUID

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI()


class TollPassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID
    licensePlateId: str = Field(
        min_length=1,
        max_length=16,
        pattern=r"^[A-Z0-9-]+$",
    )
    timestamp: datetime


@app.post("/toll-passages")
async def receive_toll_passage(event: TollPassage):
    print("Received toll passage:", event)
    return {"status": "ok"}