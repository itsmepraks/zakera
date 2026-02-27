"""Configuration for performance testing suite."""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PerformanceTestConfig:
    """Configuration for performance tests."""
    
    # API Configuration
    HOST: str = os.getenv("PERF_TEST_HOST", "http://localhost:8000")
    API_KEY: str = os.getenv("PERF_TEST_API_KEY", "test-api-key")
    API_VERSION: str = "v1"
    
    # Test Parameters
    USERS: int = int(os.getenv("PERF_TEST_USERS", "50"))
    SPAWN_RATE: int = int(os.getenv("PERF_TEST_SPAWN_RATE", "5"))
    RUN_TIME: str = os.getenv("PERF_TEST_RUN_TIME", "5m")
    
    # Wait Times (seconds)
    MIN_WAIT: float = 1.0
    MAX_WAIT: float = 3.0
    
    # Model Configuration
    DEFAULT_MODEL: str = os.getenv("PERF_TEST_MODEL", "gpt-3.5-turbo")
    PROVIDER: str = os.getenv("PERF_TEST_PROVIDER", "openai")
    
    # Test Scenarios
    SCENARIO: str = os.getenv("PERF_TEST_SCENARIO", "normal")
    
    # API Endpoints
    ENDPOINTS: Dict[str, str] = {
        "health": "/api/v1/monitoring/health",
        "chat": "/api/v1/chat",
        "conversations": "/api/v1/conversations",
        "messages": "/api/v1/conversations/{conversation_id}/messages",
        "export": "/api/v1/conversations/{conversation_id}/export",
        "providers": "/api/v1/models/providers",
        "tools": "/api/v1/tools",
        "auth": "/api/v1/auth/login",
        "websocket": "/api/v1/ws",
    }
    
    # Task Weights (probability distribution)
    TASK_WEIGHTS: Dict[str, int] = {
        "send_message": 70,
        "list_conversations": 10,
        "get_conversation": 5,
        "export_conversation": 3,
        "list_providers": 2,
        "health_check": 10,
    }
    
    # Performance Thresholds
    THRESHOLDS: Dict[str, float] = {
        "p95_latency_ms": 100.0,
        "p99_latency_ms": 200.0,
        "error_rate_percent": 1.0,
        "throughput_rps": 100.0,
    }
    
    # Test Messages
    TEST_MESSAGES: List[str] = [
        "Hello, how are you?",
        "What is the weather like today?",
        "Can you explain quantum computing?",
        "Tell me a joke",
        "What are the latest tech trends?",
        "How do I improve my productivity?",
        "Explain machine learning in simple terms",
        "What is the capital of France?",
        "Help me write a Python function",
        "What are best practices for API design?",
    ]
    
    # Reporting
    REPORT_DIR: str = "reports/performance"
    EXPORT_HTML: bool = True
    EXPORT_CSV: bool = True
    EXPORT_PROMETHEUS: bool = True
    
    # Monitoring
    PROMETHEUS_PORT: int = 8088
    ENABLE_CUSTOM_METRICS: bool = True
    
    # WebSocket Configuration
    WS_PING_INTERVAL: int = 30
    WS_PING_TIMEOUT: int = 10
    WS_MESSAGE_TIMEOUT: int = 60
    
    # Database
    DB_CONNECTION_POOL_SIZE: int = 50
    DB_MAX_OVERFLOW: int = 100
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 1.0


# Scenario-specific configurations
SCENARIO_CONFIGS = {
    "normal": {
        "users": 50,
        "spawn_rate": 5,
        "run_time": "5m",
        "min_wait": 1.0,
        "max_wait": 3.0,
        "description": "Normal production load"
    },
    "stress": {
        "users": 200,
        "spawn_rate": 20,
        "run_time": "10m",
        "min_wait": 0.5,
        "max_wait": 2.0,
        "description": "Stress test to find breaking point"
    },
    "spike": {
        "users": 500,
        "spawn_rate": 50,
        "run_time": "3m",
        "min_wait": 0.1,
        "max_wait": 1.0,
        "description": "Sudden traffic spike"
    },
    "endurance": {
        "users": 100,
        "spawn_rate": 10,
        "run_time": "1h",
        "min_wait": 2.0,
        "max_wait": 5.0,
        "description": "Long-running stability test"
    },
}


def get_scenario_config(scenario: str = None) -> Dict:
    """Get configuration for specific test scenario."""
    scenario = scenario or os.getenv("PERF_TEST_SCENARIO", "normal")
    return SCENARIO_CONFIGS.get(scenario, SCENARIO_CONFIGS["normal"])


# Global config instance
config = PerformanceTestConfig()
