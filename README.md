# Tollbooth Simulator

A local event-driven tollbooth simulation built with FastAPI, Kafka, MySQL, and vanilla JavaScript.

Vehicles drive through an animated tollbooth in the browser. When a vehicle crosses the toll sensor, the frontend sends a passage event to the API. The API publishes that event to Kafka, a separate consumer processes it and stores the charge in MySQL, and the frontend periodically refreshes a live view of the outstanding debt for each license plate.


## Architecture

```text
Vehicle animation
        |
        | POST /toll-passages
        v
FastAPI producer
        |
        | publish event
        v
Kafka topic: toll-passages
        |
        v
Charging consumer
        |
        | insert ledger record
        v
MySQL
        |
        | GET /debts
        v
Live debt dashboard
```

Each toll-passage event contains:

```json
{
  "eventId": "550e8400-e29b-41d4-a716-446655440000",
  "licensePlateId": "ABC-123",
  "timestamp": "2026-07-14T20:00:00Z"
}
```

The default toll charge is `$1.50`, represented as `150` cents.

## Features

* Animated vehicles passing through a single tollbooth
* Adjustable simulation speed
* FastAPI ingestion endpoint
* Kafka producer and consumer
* MySQL-backed append-only toll-passage ledger
* Duplicate-event protection through unique event IDs
* Manual Kafka offset commits after successful database writes
* Live debt totals grouped by license plate
* Unit tests for the API, consumer, database pool, and storage layer

## Technology

* Python 3.12
* uv
* FastAPI
* Confluent Kafka Python client
* Apache Kafka
* MySQL
* Docker Compose
* HTML, CSS, and JavaScript
* pytest

## Project Structure

```text
tollbooth-simulator/
├── compose.yaml
├── pyproject.toml
├── uv.lock
├── .env.example
│
├── src/
│   └── tollbooth_simulator/
│       ├── api/
│       │   └── passages.py
│       ├── db/
│       │   └── database.py
│       ├── storage/
│       │   └── passage_store.py
│       └── consumer.py
│
├── tests/
│   ├── api/
│   ├── db/
│   ├── storage/
│   └── test_consumer.py
│
└── web/
    ├── index.html
    ├── app.js
    └── styles.css
```

## Prerequisites

Install:

* Docker Desktop
* uv

Confirm they are available:

```bash
docker --version
docker compose version
uv --version
```

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd tollbooth-simulator
```

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Create the environment file

Copy the example:

```bash
cp .env.example .env
```

A local `.env` can look like:

```dotenv
MYSQL_ROOT_PASSWORD=replace-with-a-local-password
MYSQL_DATABASE=tollbooth
MYSQL_USER=tollbooth
MYSQL_PASSWORD=replace-with-a-local-password

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306

KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
TOLL_RATE_CENTS=150
```

Generate local passwords with:

```bash
openssl rand -hex 24
```

The `.env` file must not be committed to Git.

## Start Kafka and MySQL

```bash
docker compose up -d
```

Verify both containers:

```bash
docker compose ps
```

Expected services:

```text
tollbooth-kafka
tollbooth-mysql
```

## Create the Kafka Topic

Run this once:

```bash
docker exec tollbooth-kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --create \
  --if-not-exists \
  --topic toll-passages \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
```

Verify the topic:

```bash
docker exec tollbooth-kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --list \
  --bootstrap-server localhost:9092
```

You should see:

```text
toll-passages
```

## Create the MySQL Table

Open the MySQL shell:

```bash
docker exec -it tollbooth-mysql \
  mysql -u tollbooth -p tollbooth
```

Enter the password from your `.env`, then create the ledger table:

```sql
CREATE TABLE toll_passages (
    event_id CHAR(36) PRIMARY KEY,
    license_plate_id VARCHAR(16) NOT NULL,
    cost_cents INT UNSIGNED NOT NULL,
    occurred_at DATETIME(6) NOT NULL,
    processed_at DATETIME(6)
        NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_toll_passages_license_plate_id (
        license_plate_id
    )
);
```

Verify it:

```sql
SHOW TABLES;
DESCRIBE toll_passages;
```

Exit MySQL:

```sql
exit;
```

## Run the Application

The application uses four processes.

### Terminal 1: Infrastructure

Kafka and MySQL should already be running:

```bash
docker compose up -d
```

### Terminal 2: FastAPI Producer

```bash
PYTHONPATH=src uv run --env-file .env \
  uvicorn tollbooth_simulator.api.passages:app \
  --app-dir src \
  --reload \
  --port 8001
```

The API runs at:

```text
http://127.0.0.1:8001
```

Test the debt endpoint:

```bash
curl http://127.0.0.1:8001/debts
```

### Terminal 3: Kafka Consumer

```bash
PYTHONPATH=src uv run --env-file .env \
  python -m tollbooth_simulator.consumer
```

Expected output:

```text
Listening for events on 'toll-passages'...
```

Leave the consumer running.

### Terminal 4: Frontend

```bash
uv run python -m http.server 8000 --directory web
```

Open the simulation:

```bash
open http://127.0.0.1:8000
```

Press **Start** to begin generating vehicles.

## Runtime Flow

For each vehicle crossing:

1. The browser creates a unique event ID.
2. The browser sends `POST /toll-passages`.
3. FastAPI validates the event.
4. The Kafka producer publishes it to `toll-passages`.
5. Kafka acknowledges the message.
6. The consumer reads the event.
7. The consumer inserts a `$1.50` charge into MySQL.
8. The consumer commits the Kafka offset.
9. The frontend refreshes `GET /debts`.
10. The live balance for the license plate updates.

## API Endpoints

### Submit a Toll Passage

```http
POST /toll-passages
```

Example request:

```json
{
  "eventId": "550e8400-e29b-41d4-a716-446655440000",
  "licensePlateId": "ABC-123",
  "timestamp": "2026-07-14T20:00:00Z"
}
```

Example response:

```json
{
  "status": "ok"
}
```

### Retrieve All Debts

```http
GET /debts
```

Example response:

```json
[
  {
    "licensePlateId": "ABC-123",
    "totalDebtCents": 450
  },
  {
    "licensePlateId": "XYZ-908",
    "totalDebtCents": 150
  }
]
```
