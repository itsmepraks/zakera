"""WebSocket performance testing."""

import json
import time
import random
from typing import Optional

from locust import HttpUser, task, between, tag
import websocket
from websocket import WebSocketException

from .config import config
from .utils.auth import AuthHelper
from .utils.data_generator import DataGenerator


class WebSocketUser(HttpUser):
    """User class for WebSocket performance testing."""
    
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws: Optional[websocket.WebSocket] = None
        self.auth_helper = AuthHelper(self.client)
        self.data_gen = DataGenerator()
        self.token: Optional[str] = None
    
    def on_start(self):
        """Called when user starts. Establish WebSocket connection."""
        self.token = self.auth_helper.login()
        self._connect_websocket()
    
    def on_stop(self):
        """Called when user stops. Close WebSocket connection."""
        self._disconnect_websocket()
    
    def _connect_websocket(self):
        """Establish WebSocket connection."""
        try:
            # Convert http to ws
            ws_url = self.host.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url = f"{ws_url}{config.ENDPOINTS['websocket']}"
            
            # Add token to URL
            ws_url = f"{ws_url}?token={self.token}"
            
            start_time = time.time()
            
            self.ws = websocket.create_connection(
                ws_url,
                timeout=config.WS_MESSAGE_TIMEOUT
            )
            
            connection_time = (time.time() - start_time) * 1000
            
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="connect",
                response_time=connection_time,
                response_length=0,
                exception=None,
                context={}
            )
            
            print(f"WebSocket connected in {connection_time:.2f}ms")
            
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="connect",
                response_time=0,
                response_length=0,
                exception=e,
                context={}
            )
            self.ws = None
    
    def _disconnect_websocket(self):
        """Close WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
                print("WebSocket disconnected")
            except Exception as e:
                print(f"WebSocket disconnect error: {e}")
    
    def _send_message(self, message: str) -> Optional[dict]:
        """Send message via WebSocket and wait for response.
        
        Args:
            message: Message to send
            
        Returns:
            Response data or None
        """
        if not self.ws:
            self._connect_websocket()
            if not self.ws:
                return None
        
        try:
            payload = {
                "type": "message",
                "content": message,
                "model": config.DEFAULT_MODEL
            }
            
            start_time = time.time()
            
            # Send message
            self.ws.send(json.dumps(payload))
            
            # Wait for response
            response = self.ws.recv()
            
            response_time = (time.time() - start_time) * 1000
            
            data = json.loads(response)
            
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="send_message",
                response_time=response_time,
                response_length=len(response),
                exception=None,
                context={}
            )
            
            return data
            
        except WebSocketException as e:
            print(f"WebSocket error: {e}")
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="send_message",
                response_time=0,
                response_length=0,
                exception=e,
                context={}
            )
            # Try to reconnect
            self._disconnect_websocket()
            self._connect_websocket()
            return None
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="send_message",
                response_time=0,
                response_length=0,
                exception=e,
                context={}
            )
            return None
    
    @task(80)
    @tag("websocket", "normal")
    def send_chat_message(self):
        """Send a chat message via WebSocket."""
        message = self.data_gen.generate_message()
        response = self._send_message(message)
        
        if response:
            print(f"Received response: {response.get('type')}")
    
    @task(10)
    @tag("websocket", "normal")
    def send_typing_indicator(self):
        """Send typing indicator."""
        if not self.ws:
            return
        
        try:
            payload = {"type": "typing", "status": "start"}
            self.ws.send(json.dumps(payload))
            
            time.sleep(random.uniform(0.5, 2.0))
            
            payload = {"type": "typing", "status": "stop"}
            self.ws.send(json.dumps(payload))
            
        except Exception as e:
            print(f"Typing indicator error: {e}")
    
    @task(5)
    @tag("websocket", "stress")
    def rapid_fire_messages(self):
        """Send multiple messages rapidly."""
        for _ in range(5):
            message = self.data_gen.generate_message()
            self._send_message(message)
            time.sleep(0.1)
    
    @task(5)
    @tag("websocket")
    def ping_pong(self):
        """Test WebSocket ping/pong."""
        if not self.ws:
            return
        
        try:
            start_time = time.time()
            self.ws.ping()
            # Wait for pong
            time.sleep(0.1)
            response_time = (time.time() - start_time) * 1000
            
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="ping",
                response_time=response_time,
                response_length=0,
                exception=None,
                context={}
            )
        except Exception as e:
            print(f"Ping error: {e}")


class WebSocketStressUser(HttpUser):
    """Stress testing for WebSocket connections."""
    
    wait_time = between(0.1, 0.5)
    
    @task
    @tag("websocket-stress")
    def connection_stress_test(self):
        """Rapidly open and close connections."""
        auth_helper = AuthHelper(self.client)
        token = auth_helper.login()
        
        ws_url = self.host.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}{config.ENDPOINTS['websocket']}?token={token}"
        
        try:
            start_time = time.time()
            ws = websocket.create_connection(ws_url, timeout=5)
            
            # Send a few messages
            for i in range(3):
                ws.send(json.dumps({
                    "type": "message",
                    "content": f"Stress test message {i}"
                }))
                ws.recv()
            
            ws.close()
            
            response_time = (time.time() - start_time) * 1000
            
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="connection_lifecycle",
                response_time=response_time,
                response_length=0,
                exception=None,
                context={}
            )
            
        except Exception as e:
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="connection_lifecycle",
                response_time=0,
                response_length=0,
                exception=e,
                context={}
            )
