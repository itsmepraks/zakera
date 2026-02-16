#!/usr/bin/env python3
"""Startup diagnostics for Zakera.

Runs comprehensive checks before starting the application.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{'=' * 70}")
    print(f"{text:^70}")
    print(f"{'=' * 70}\n")


def check_environment() -> Dict[str, Any]:
    """Check environment setup."""
    print("📋 Environment Check")
    print("-" * 70)
    
    results = {
        "env_file_exists": os.path.exists(".env"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
    }
    
    if results["env_file_exists"]:
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found")
        print("   Create from template: cp .env.example .env")
    
    print(f"✅ Python {results['python_version']}")
    print(f"✅ Platform: {results['platform']}")
    
    return results


def check_dependencies() -> Dict[str, bool]:
    """Check required dependencies."""
    print("\n📦 Dependency Check")
    print("-" * 70)
    
    required = {
        "fastapi": "Web framework",
        "uvicorn": "ASGI server",
        "sqlalchemy": "Database ORM",
        "pydantic": "Data validation",
        "tiktoken": "Token counting",
        "httpx": "HTTP client",
    }
    
    results = {}
    
    for package, description in required.items():
        try:
            __import__(package)
            print(f"✅ {description:.<40} {package}")
            results[package] = True
        except ImportError:
            print(f"❌ {description:.<40} {package} (MISSING)")
            results[package] = False
    
    if not all(results.values()):
        print("\n   Fix: pip install -r requirements.txt")
    
    return results


def check_providers() -> Dict[str, Any]:
    """Check model provider configuration."""
    print("\n🤖 Model Provider Configuration")
    print("-" * 70)
    
    providers = {
        "OpenAI": os.getenv("OPENAI_API_KEY"),
        "Anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "Gemini": os.getenv("GOOGLE_API_KEY"),
        "Ollama": os.getenv("ENABLE_OLLAMA", "false").lower() == "true",
    }
    
    configured_count = 0
    
    for provider, is_configured in providers.items():
        if is_configured:
            print(f"✅ {provider:.<30} Configured")
            configured_count += 1
        else:
            print(f"⚪ {provider:.<30} Not configured")
    
    if configured_count == 0:
        print("\n❌ No providers configured!")
        print("   Add at least one API key or enable Ollama in .env")
    else:
        print(f"\n✅ {configured_count} provider(s) configured")
    
    # Check default model
    default_model = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
    print(f"\nDefault model: {default_model}")
    
    return {"configured_count": configured_count, "providers": providers}


def check_directories() -> None:
    """Check and create required directories."""
    print("\n📁 Directory Check")
    print("-" * 70)
    
    required_dirs = [
        "data",
        "logs",
        "data/uploads",
    ]
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ {directory}/")
        else:
            print(f"⚠️  {directory}/ (creating...)")
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created {directory}/")


def print_quick_start_tips() -> None:
    """Print helpful getting started tips."""
    print("\n💡 Quick Start Tips")
    print("-" * 70)
    
    print("""
1. Start the server:
   python -m uvicorn src.api.main:app --reload

2. View API docs:
   http://localhost:8000/api/docs

3. Test the API:
   curl http://localhost:8000

4. Start frontend (in another terminal):
   cd src/frontend && npm install && npm run dev

5. Enable monitoring:
   cd monitoring && docker-compose up -d
   http://localhost:3001 (Grafana)
    """)


def print_configuration_summary() -> None:
    """Print current configuration summary."""
    print("\n⚙️  Current Configuration")
    print("-" * 70)
    
    config_items = [
        ("Default Model", os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")),
        ("Database", os.getenv("DATABASE_URL", "sqlite:///./data/zakera.db")[:50]),
        ("Log Level", os.getenv("LOG_LEVEL", "INFO")),
        ("Debug Mode", os.getenv("DEBUG", "false")),
        ("Metrics Enabled", os.getenv("ENABLE_METRICS", "true")),
        ("Tools Enabled", os.getenv("ENABLE_TOOLS", "true")),
    ]
    
    for key, value in config_items:
        print(f"  {key:.<30} {value}")


def main() -> int:
    """Main entry point.
    
    Returns:
        0 if all checks pass, 1 otherwise
    """
    print_header("Zakera Startup Diagnostics")
    
    # Run checks
    env_results = check_environment()
    dep_results = check_dependencies()
    provider_results = check_providers()
    check_directories()
    print_configuration_summary()
    print_quick_start_tips()
    
    # Determine if ready to start
    all_deps_installed = all(dep_results.values())
    providers_configured = provider_results["configured_count"] > 0
    
    print_header("Diagnostic Summary")
    
    if all_deps_installed and providers_configured:
        print("🎉 System is ready to start!\n")
        print("Run: python -m uvicorn src.api.main:app --reload\n")
        return 0
    else:
        print("⚠️  System is not ready\n")
        if not all_deps_installed:
            print("  ❌ Missing dependencies - run: pip install -r requirements.txt")
        if not providers_configured:
            print("  ❌ No model providers configured - add API key to .env")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
