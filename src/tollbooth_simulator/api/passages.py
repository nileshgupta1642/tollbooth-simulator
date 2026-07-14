import os
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from confluent_kafka import KafkaException
from confluent_kafka.aio import AIOProducer
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field


KAFKA_TOPIC = "toll-passages"
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOProducer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "acks": "all",
            "enable.idempotence": True,
        }
    )

    app.state.kafka_producer = producer

    try:
        # FastAPI continuously handles requests while execution
        # is paused here.
        yield
    finally:
        # Before the API process exits, finish any final messages
        # that are still queued or in flight.
        await producer.flush()
        await producer.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


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
async def receive_toll_passage(
    event: TollPassage,
    request: Request,
) -> dict[str, str]:
    producer: AIOProducer = request.app.state.kafka_producer

    try:
        # Submit this toll-passage event to the Kafka producer.
        delivery_future = await producer.produce(
            topic=KAFKA_TOPIC,
            key=event.licensePlateId,
            value=event.model_dump_json(),
        )

        # Wait for Kafka to acknowledge this specific message.
        delivered_message = await delivery_future

    except (KafkaException, BufferError) as error:
        raise HTTPException(
            status_code=503,
            detail="Failed to publish toll passage to Kafka",
        ) from error

    print(
        "Published toll passage to Kafka:",
        f"eventId={event.eventId}",
        f"plate={event.licensePlateId}",
        f"partition={delivered_message.partition()}",
        f"offset={delivered_message.offset()}",
    )

    return {"status": "ok"}