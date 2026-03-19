"""
Locust load-test scenarios for the Zakera AI Chat Agent API.

Usage (local)
-------------
    locust --locustfile tests/load/locustfile.py --host http://localhost:8000

Then open http://localhost:8089 in your browser.

Headless CI mode
----------------
    locust --locustfile tests/load/locustfile.py \\
           --host http://staging.example.com \\
           --users 50 --spawn-rate 5 --run-time 5m \\
           --headless --csv report

Environment variables
---------------------
    LOCUST_API_TOKEN    Pre-minted JWT (skips the /auth/token login step).
    LOCUST_USERNAME     Username for login (default: loadtest@zakera.ai).
    LOCUST_PASSWORD     Password for login (default: LoadTest123!).
    LOCUST_SKIP_AUTH    Set to 'true' to skip auth entirely (open endpoints).
"""

from __future__ import annotations

import json
import os
import random
import uuid
from typing import Any

from locust import HttpUser, TaskSet, between, events, task

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKIP_AUTH = os.getenv("LOCUST_SKIP_AUTH", "false").lower() == "true"
PRE_MINTED_TOKEN = os.getenv("LOCUST_API_TOKEN", "")
DEFAULT_USERNAME = os.getenv("LOCUST_USERNAME", "loadtest@zakera.ai")
DEFAULT_PASSWORD = os.getenv("LOCUST_PASSWORD", "LoadTest123!")

# A pool of realistic-looking chat prompts to keep the load varied
PROMPTS = [
    "Summarise the key points from our previous discussion.",
    "What are the best practices for async Python programming?",
    "Explain the difference between RAG and fine-tuning an LLM.",
    "Write a haiku about distributed systems.",
    "How do I optimise a PostgreSQL query with a large JOIN?",
    "What is the capital of New Zealand and what is it known for?",
    "Give me a 3-step plan to improve my morning routine.",
    "Translate 'Hello, how are you?' into French, Spanish, and Japanese.",
    "What are the pros and cons of microservices vs monolithic architecture?",
    "Can you help me debug this Python TypeError: 'NoneType' is not iterable?",
    "Write a short product description for a smart water bottle.",
    "What is the time complexity of merge sort?",
]


# ---------------------------------------------------------------------------
# Task set
# ---------------------------------------------------------------------------

class ZakeraChatTasks(TaskSet):
    """Weighted task set simulating a realistic Zakera user session."""

    conversation_ids: list[str]

    def on_start(self) -> None:
        """Called once per simulated user before tasks begin."""
        self.conversation_ids = []
        # Seed at least one conversation so GET/summarize tasks have an ID
        conv_id = self._create_conversation()
        if conv_id:
            self.conversation_ids.append(conv_id)

    # ---- Tasks -----------------------------------------------------------

    @task(40)
    def send_chat_message(self) -> None:
        """POST a message to a random conversation (most frequent task)."""
        conv_id = self._pick_conversation_id()
        prompt = random.choice(PROMPTS)
        with self.client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"role": "user", "content": prompt},
            headers=self.user.auth_headers,
            catch_response=True,
            name="POST /conversations/:id/messages",
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Unexpected status {resp.status_code}")
            else:
                resp.success()

    @task(20)
    def list_conversations(self) -> None:
        """GET paginated conversation list."""
        with self.client.get(
            "/api/v1/conversations",
            params={"page": 1, "per_page": 20},
            headers=self.user.auth_headers,
            catch_response=True,
            name="GET /conversations",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                # Collect any new conversation IDs for use in other tasks
                for conv in data.get("items", [])[:5]:
                    cid = conv.get("id")
                    if cid and cid not in self.conversation_ids:
                        self.conversation_ids.append(cid)
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(15)
    def get_conversation(self) -> None:
        """GET a single conversation by ID."""
        conv_id = self._pick_conversation_id()
        with self.client.get(
            f"/api/v1/conversations/{conv_id}",
            headers=self.user.auth_headers,
            catch_response=True,
            name="GET /conversations/:id",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(10)
    def generate_summary(self) -> None:
        """POST to the summarization endpoint (moderate weight)."""
        conv_id = self._pick_conversation_id()
        with self.client.post(
            f"/api/v1/conversations/{conv_id}/summary",
            json={},
            headers=self.user.auth_headers,
            catch_response=True,
            name="POST /conversations/:id/summary",
        ) as resp:
            if resp.status_code in (200, 404, 422):
                resp.success()  # 404/422 are expected for empty convs
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(10)
    def health_check(self) -> None:
        """GET /health — fast baseline with no auth overhead."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="GET /health",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")

    @task(5)
    def export_conversation(self) -> None:
        """GET conversation export in JSON format (least frequent)."""
        conv_id = self._pick_conversation_id()
        with self.client.get(
            f"/api/v1/conversations/{conv_id}/export",
            params={"format": "json"},
            headers=self.user.auth_headers,
            catch_response=True,
            name="GET /conversations/:id/export",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    # ---- Helpers ---------------------------------------------------------

    def _pick_conversation_id(self) -> str:
        """Return a random known conversation ID, or a placeholder."""
        if self.conversation_ids:
            return random.choice(self.conversation_ids)
        return str(uuid.uuid4())  # Will 404 — acceptable in load tests

    def _create_conversation(self) -> str | None:
        """Create a new conversation and return its ID."""
        try:
            resp = self.client.post(
                "/api/v1/conversations",
                json={"title": f"Load Test {uuid.uuid4().hex[:8]}"},
                headers=self.user.auth_headers,
                name="POST /conversations (setup)",
            )
            if resp.status_code in (200, 201):
                return resp.json().get("id")
        except Exception:  # noqa: BLE001
            pass
        return None


# ---------------------------------------------------------------------------
# User class
# ---------------------------------------------------------------------------

class ZakeraUser(HttpUser):
    """
    Simulated Zakera end-user.

    Authenticates on startup (or uses a pre-minted token) and then
    executes the weighted task set with a realistic think-time.
    """

    tasks = [ZakeraChatTasks]
    wait_time = between(0.5, 3.0)  # seconds between tasks

    auth_headers: dict[str, str]
    _token: str

    def on_start(self) -> None:
        self.auth_headers = {}
        if SKIP_AUTH:
            return
        if PRE_MINTED_TOKEN:
            self._token = PRE_MINTED_TOKEN
        else:
            self._token = self._login()
        if self._token:
            self.auth_headers = {"Authorization": f"Bearer {self._token}"}

    def _login(self) -> str:
        """Exchange credentials for a JWT via the /auth/token endpoint."""
        try:
            resp = self.client.post(
                "/api/v1/auth/token",
                data={
                    "username": DEFAULT_USERNAME,
                    "password": DEFAULT_PASSWORD,
                    "grant_type": "password",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                name="POST /auth/token (setup)",
            )
            if resp.status_code == 200:
                return resp.json().get("access_token", "")
            else:
                print(f"[ZakeraUser] Login failed: {resp.status_code} {resp.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ZakeraUser] Login exception: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Custom event hooks for detailed failure reporting
# ---------------------------------------------------------------------------

@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response: Any,
    context: Any,
    exception: Any,
    **kwargs: Any,
) -> None:
    """Log 5xx errors to stdout for quick triage during a test run."""
    if exception is None and hasattr(response, "status_code"):
        if response.status_code >= 500:
            print(
                f"[5xx] {request_type} {name} → {response.status_code} "
                f"({response_time:.0f}ms)"
            )
