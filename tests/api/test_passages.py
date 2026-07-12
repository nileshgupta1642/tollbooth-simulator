from fastapi.testclient import TestClient

from tollbooth_simulator.api.passages import app


client = TestClient(app)


def test_receive_toll_passage_returns_ok() -> None:
    passage_event = {
        "eventId": "00000000-0000-4000-8000-000000000001",
        "licensePlateId": "ABC-123",
        "timestamp": "2026-07-12T18:00:00Z",
    }

    response = client.post(
        "/toll-passages",
        json=passage_event,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}