from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "halo-backend-conversation-orchestrator"
    assert "timestamp_utc" in body


def test_conversation_message_creates_new_session():
    payload = {"user_utterance": "Hello Halo"}
    response = client.post("/api/v1/conversation/message", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["reply_text"] == "Echo: Hello Halo"
    assert body["session_id"]
    assert body["timestamp_utc"]


def test_conversation_message_uses_existing_session():
    session_id = "test-session-123"
    payload = {"session_id": session_id, "user_utterance": "Ping"}
    response = client.post("/api/v1/conversation/message", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["session_id"] == session_id
    assert body["reply_text"] == "Echo: Ping"
