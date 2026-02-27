"""WebSocket Load Test - Tests WebSocket connections and streaming

Tests:
- WebSocket connection establishment
- Real-time message streaming
- Connection stability
- Reconnection behavior
- Concurrent connections
"""

import json
import time
import os
import sys
import random
from locust import User, task, between, events
from locust.exception import RescheduleTask
import logging
import websocket
import gevent

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.auth_helper import AuthHelper
from utils.data_generator import DataGenerator
from utils.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket client for load testing"""
    
    def __init__(self, host, api_key):
        self.host = host
        self.api_key = api_key
        self.ws = None
        self.connected = False
        self.messages_received = 0
        self.connection_time = None
    
    def connect(self):
        """Establish WebSocket connection"""
        ws_url = self.host.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url = f"{ws_url}/api/v1/chat/ws?token={self.api_key}"
        
        start_time = time.time()
        
        try:
            self.ws = websocket.create_connection(
                ws_url,
                timeout=30
            )
            self.connected = True
            self.connection_time = time.time() - start_time
            return True
        
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.connected = False
            return False
    
    def send_message(self, message, conversation_id=None, model='gpt-3.5-turbo'):
        """Send message via WebSocket"""
        if not self.connected or not self.ws:
            return None
        
        payload = {
            'type': 'chat_message',
            'message': message,
            'conversation_id': conversation_id,
            'model': model,
            'stream': True
        }
        
        start_time = time.time()
        
        try:
            self.ws.send(json.dumps(payload))
            
            # Receive streaming response
            full_response = ""
            chunks_received = 0
            
            while True:
                try:
                    data = self.ws.recv()
                    if not data:
                        break
                    
                    response = json.loads(data)
                    
                    if response.get('type') == 'content':
                        full_response += response.get('content', '')
                        chunks_received += 1
                    
                    elif response.get('type') == 'done':
                        break
                    
                    elif response.get('type') == 'error':
                        logger.error(f"WebSocket error: {response.get('error')}")
                        return None
                
                except websocket.WebSocketTimeoutException:
                    logger.warning("WebSocket receive timeout")
                    break
            
            duration = time.time() - start_time
            self.messages_received += 1
            
            return {
                'response': full_response,
                'chunks': chunks_received,
                'duration': duration
            }
        
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            return None
    
    def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.connected = False


class WebSocketUser(User):
    """Simulates a user with WebSocket connection"""
    
    wait_time = between(
        float(os.getenv('MIN_WAIT_TIME', 1)),
        float(os.getenv('MAX_WAIT_TIME', 5))
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = AuthHelper()
        self.data_gen = DataGenerator()
        self.ws_client = None
        self.conversation_id = None
        self.metrics = MetricsCollector()
        self.api_key = os.getenv('API_KEY', 'test-key')
    
    def on_start(self):
        """Called when user starts"""
        # Connect WebSocket
        self.connect_websocket()
    
    def on_stop(self):
        """Called when user stops"""
        if self.ws_client:
            self.ws_client.disconnect()
    
    def connect_websocket(self):
        """Establish WebSocket connection"""
        start_time = time.time()
        
        self.ws_client = WebSocketClient(self.host, self.api_key)
        success = self.ws_client.connect()
        
        duration = (time.time() - start_time) * 1000  # ms
        
        if success:
            events.request.fire(
                request_type="WebSocket",
                name="Connect",
                response_time=duration,
                response_length=0,
                exception=None,
                context={}
            )
            logger.info(f"WebSocket connected in {duration:.2f}ms")
        else:
            events.request.fire(
                request_type="WebSocket",
                name="Connect",
                response_time=duration,
                response_length=0,
                exception=Exception("Connection failed"),
                context={}
            )
            raise RescheduleTask()
    
    @task(10)
    def send_streaming_message(self):
        """Send message and receive streaming response"""
        if not self.ws_client or not self.ws_client.connected:
            self.connect_websocket()
        
        message = self.data_gen.generate_message()
        model = self.data_gen.select_random_model()
        
        start_time = time.time()
        
        result = self.ws_client.send_message(
            message=message,
            conversation_id=self.conversation_id,
            model=model
        )
        
        duration = (time.time() - start_time) * 1000
        
        if result:
            events.request.fire(
                request_type="WebSocket",
                name="Send Streaming Message",
                response_time=duration,
                response_length=len(result['response']),
                exception=None,
                context={'chunks': result['chunks']}
            )
            
            # Record metrics
            self.metrics.record_websocket_metrics(
                duration=duration / 1000,
                chunks=result['chunks'],
                message_length=len(message),
                response_length=len(result['response'])
            )
        else:
            events.request.fire(
                request_type="WebSocket",
                name="Send Streaming Message",
                response_time=duration,
                response_length=0,
                exception=Exception("Message send failed"),
                context={}
            )
    
    @task(2)
    def send_quick_messages(self):
        """Send multiple quick messages in succession"""
        if not self.ws_client or not self.ws_client.connected:
            self.connect_websocket()
        
        num_messages = random.randint(2, 5)
        
        for i in range(num_messages):
            message = self.data_gen.generate_short_message()
            
            start_time = time.time()
            result = self.ws_client.send_message(
                message=message,
                conversation_id=self.conversation_id,
                model='gemini-1.5-flash'  # Fast model for quick messages
            )
            duration = (time.time() - start_time) * 1000
            
            if result:
                events.request.fire(
                    request_type="WebSocket",
                    name="Quick Message",
                    response_time=duration,
                    response_length=len(result['response']),
                    exception=None,
                    context={}
                )
            
            # Short delay between messages
            gevent.sleep(0.5)
    
    @task(1)
    def test_reconnection(self):
        """Test reconnection behavior"""
        if self.ws_client and self.ws_client.connected:
            # Disconnect
            self.ws_client.disconnect()
            
            # Wait a bit
            gevent.sleep(1)
            
            # Reconnect
            self.connect_websocket()
    
    @task(1)
    def long_running_stream(self):
        """Test longer conversation with multiple exchanges"""
        if not self.ws_client or not self.ws_client.connected:
            self.connect_websocket()
        
        # Simulate a longer conversation
        num_exchanges = random.randint(3, 7)
        
        for i in range(num_exchanges):
            message = self.data_gen.generate_message()
            result = self.ws_client.send_message(
                message=message,
                conversation_id=self.conversation_id
            )
            
            if not result:
                break
            
            # Simulate user reading and thinking
            gevent.sleep(random.uniform(2, 5))


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("Starting WebSocket load test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("WebSocket load test completed")
