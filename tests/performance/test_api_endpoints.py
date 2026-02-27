"""Detailed API endpoint performance testing."""

import time
import random
from typing import Optional

from locust import HttpUser, TaskSet, task, between, tag, SequentialTaskSet

from .config import config
from .utils.auth import AuthHelper
from .utils.data_generator import DataGenerator


class ConversationWorkflow(SequentialTaskSet):
    """Sequential workflow for conversation testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_id: Optional[str] = None
        self.message_ids = []
    
    def on_start(self):
        """Initialize workflow."""
        self.auth_helper = AuthHelper(self.client)
        self.data_gen = DataGenerator()
        
        self.token = self.auth_helper.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task
    def step1_create_conversation(self):
        """Step 1: Create a new conversation."""
        with self.client.post(
            config.ENDPOINTS["conversations"],
            headers=self.headers,
            json={
                "title": self.data_gen.generate_conversation_title()
            },
            catch_response=True,
            name="01_create_conversation"
        ) as response:
            if response.status_code == 201:
                self.conversation_id = response.json()["id"]
                print(f"Created conversation: {self.conversation_id}")
                response.success()
            else:
                response.failure("Failed to create conversation")
    
    @task
    def step2_send_messages(self):
        """Step 2: Send multiple messages."""
        if not self.conversation_id:
            return
        
        for i in range(5):
            message = self.data_gen.generate_message()
            
            with self.client.post(
                config.ENDPOINTS["chat"],
                headers=self.headers,
                json={
                    "message": message,
                    "conversation_id": self.conversation_id,
                    "model": config.DEFAULT_MODEL
                },
                catch_response=True,
                name="02_send_message"
            ) as response:
                if response.status_code == 200:
                    data = response.json()
                    message_id = data.get("message_id")
                    if message_id:
                        self.message_ids.append(message_id)
                    response.success()
                else:
                    response.failure(f"Message {i} failed")
            
            time.sleep(random.uniform(0.5, 1.5))
    
    @task
    def step3_get_conversation(self):
        """Step 3: Retrieve conversation."""
        if not self.conversation_id:
            return
        
        with self.client.get(
            f"{config.ENDPOINTS['conversations']}/{self.conversation_id}",
            headers=self.headers,
            catch_response=True,
            name="03_get_conversation"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                message_count = len(data.get("messages", []))
                print(f"Conversation has {message_count} messages")
                response.success()
            else:
                response.failure("Failed to get conversation")
    
    @task
    def step4_update_conversation(self):
        """Step 4: Update conversation title."""
        if not self.conversation_id:
            return
        
        new_title = f"Updated: {self.data_gen.generate_conversation_title()}"
        
        with self.client.patch(
            f"{config.ENDPOINTS['conversations']}/{self.conversation_id}",
            headers=self.headers,
            json={"title": new_title},
            catch_response=True,
            name="04_update_conversation"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Failed to update conversation")
    
    @task
    def step5_export_conversation(self):
        """Step 5: Export conversation."""
        if not self.conversation_id:
            return
        
        export_format = random.choice(["json", "markdown", "text"])
        
        with self.client.get(
            config.ENDPOINTS["export"].format(conversation_id=self.conversation_id),
            headers=self.headers,
            params={"format": export_format},
            catch_response=True,
            name="05_export_conversation"
        ) as response:
            if response.status_code == 200:
                size_kb = len(response.content) / 1024
                print(f"Exported {export_format}: {size_kb:.2f} KB")
                response.success()
            else:
                response.failure("Failed to export conversation")
    
    @task
    def step6_list_conversations(self):
        """Step 6: List all conversations."""
        with self.client.get(
            config.ENDPOINTS["conversations"],
            headers=self.headers,
            params={"limit": 20},
            catch_response=True,
            name="06_list_conversations"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                count = len(data.get("conversations", []))
                print(f"Listed {count} conversations")
                response.success()
            else:
                response.failure("Failed to list conversations")
    
    @task
    def step7_delete_conversation(self):
        """Step 7: Delete conversation."""
        if not self.conversation_id:
            return
        
        with self.client.delete(
            f"{config.ENDPOINTS['conversations']}/{self.conversation_id}",
            headers=self.headers,
            catch_response=True,
            name="07_delete_conversation"
        ) as response:
            if response.status_code in [200, 204]:
                print(f"Deleted conversation: {self.conversation_id}")
                response.success()
            else:
                response.failure("Failed to delete conversation")


class APIEndpointUser(HttpUser):
    """User for detailed API endpoint testing."""
    
    tasks = [ConversationWorkflow]
    wait_time = between(2, 5)
