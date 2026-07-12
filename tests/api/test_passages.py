from fastapi.testclient import TestClient

from tollbooth_simulator.api.passages import app


client = TestClient(app)


def test_receive_toll_passage_returns_ok() -> None:
    event = {
        "eventId": "event-123",
        "licensePlateId": "ABC-123",
        "timestamp": "2026-07-12T18:00:00Z",
    }

    response = client.post("/toll-passages", json=event)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}