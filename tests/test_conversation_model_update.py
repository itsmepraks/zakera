from __future__ import annotations

from src.api.auth import create_access_token


def test_update_conversation_model_name(client, test_conversation):
    token = create_access_token(data={"sub": test_conversation.user_id, "username": "testuser"})
    response = client.patch(
        f"/api/v1/conversations/{test_conversation.id}",
        json={"model_name": "openrouter/~openai/gpt-latest"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["model_name"] == "openrouter/~openai/gpt-latest"
