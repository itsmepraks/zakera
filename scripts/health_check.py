#!/usr/bin/env python3
"""Health check and diagnostics script for Zakera.

Run this script to diagnose configuration issues and check system health.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --quick    # Skip slow checks
    python scripts/health_check.py --fix      # Attempt to fix common issues
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from typing import Dict, Any, List
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive health checker for Zakera."""
    
    def __init__(self, quick: bool = False):
        """Initialize health checker.
        
        Args:
            quick: Skip slow checks if True
        """
        self.quick = quick
        self.results: List[Dict[str, Any]] = []
    
    async def check_all(self) -> bool:
        """Run all health checks.
        
        Returns:
            True if all critical checks pass
        """
        print("\n" + "=" * 70)
        print("Zakera Health Check & Diagnostics")
        print("=" * 70 + "\n")
        
        # Configuration checks
        print("🔧 Configuration Checks")
        await self._check_configuration()
        
        # Provider checks
        if not self.quick:
            print("\n🤖 Model Provider Checks")
            await self._check_providers()
        
        # Database checks
        print("\n💾 Database Checks")
        await self._check_database()
        
        # System checks
        print("\n💻 System Checks")
        await self._check_system()
        
        # API checks (if running)
        if not self.quick:
            print("\n🌐 API Checks")
            await self._check_api()
        
        # Summary
        self._print_summary()
        
        # Return overall health
        critical_failures = [
            r for r in self.results 
            if not r.get("passed") and r.get("critical", True)
        ]
        
        return len(critical_failures) == 0
    
    async def _check_configuration(self) -> None:
        """Check configuration validity."""
        from src.utils.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        is_valid = validator.validate_all()
        
        if is_valid:
            print("  ✅ Configuration is valid")
            self.results.append({
                "check": "configuration",
                "passed": True,
                "critical": True
            })
        else:
            print("  ❌ Configuration has errors")
            summary = validator.get_summary()
            print(f"     Errors: {summary['errors']}, Warnings: {summary['warnings']}")
            self.results.append({
                "check": "configuration",
                "passed": False,
                "critical": True,
                "errors": summary['error_messages']
            })
    
    async def _check_providers(self) -> None:
        """Check model provider connectivity."""
        # Check OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        print("  ✅ OpenAI API is accessible")
                        self.results.append({"check": "openai", "passed": True})
                    else:
                        print(f"  ❌ OpenAI API returned {response.status_code}")
                        self.results.append({"check": "openai", "passed": False})
            except Exception as e:
                print(f"  ❌ OpenAI API check failed: {e}")
                self.results.append({"check": "openai", "passed": False, "error": str(e)})
        
        # Check Ollama
        if os.getenv("ENABLE_OLLAMA", "false").lower() == "true":
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{ollama_url}/api/tags", timeout=5.0)
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        print(f"  ✅ Ollama is running ({len(models)} models available)")
                        self.results.append({"check": "ollama", "passed": True})
                    else:
                        print(f"  ❌ Ollama returned {response.status_code}")
                        self.results.append({"check": "ollama", "passed": False})
            except Exception as e:
                print(f"  ⚠️  Ollama not accessible: {e}")
                print("     Install: curl -fsSL https://ollama.com/install.sh | sh")
                self.results.append({"check": "ollama", "passed": False, "error": str(e)})
    
    async def _check_database(self) -> None:
        """Check database connectivity."""
        db_url = os.getenv("DATABASE_URL", "sqlite:///./data/zakera.db")
        
        if db_url.startswith("sqlite"):
            # Check SQLite file
            db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
            
            if os.path.exists(db_path):
                size_mb = os.path.getsize(db_path) / (1024 * 1024)
                print(f"  ✅ Database file exists ({size_mb:.2f} MB)")
                self.results.append({"check": "database", "passed": True})
            else:
                print(f"  ⚠️  Database file not found: {db_path}")
                print(f"     Will be created on first run")
                self.results.append({"check": "database", "passed": True, "warning": "Not created yet"})
        else:
            print(f"  ℹ️  Using external database: {db_url.split('@')[0]}...")
            self.results.append({"check": "database", "passed": True})
    
    async def _check_system(self) -> None:
        """Check system resources."""
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"  💻 CPU usage: {cpu_percent}%")
        
        # Memory
        memory = psutil.virtual_memory()
        print(f"  🧠 Memory: {memory.percent}% used ({memory.available / (1024**3):.1f} GB available)")
        
        if memory.percent > 90:
            print("  ⚠️  High memory usage detected")
            self.results.append({"check": "memory", "passed": False, "critical": False})
        else:
            self.results.append({"check": "memory", "passed": True})
        
        # Disk
        disk = psutil.disk_usage('/')
        print(f"  💿 Disk: {disk.percent}% used ({disk.free / (1024**3):.1f} GB free)")
        
        if disk.percent > 90:
            print("  ⚠️  Low disk space")
            self.results.append({"check": "disk", "passed": False, "critical": False})
        else:
            self.results.append({"check": "disk", "passed": True})
    
    async def _check_api(self) -> None:
        """Check if API is running and healthy."""
        api_url = os.getenv("API_URL", "http://localhost:8000")
        
        try:
            async with httpx.AsyncClient() as client:
                # Check root endpoint
                response = await client.get(api_url, timeout=5.0)
                if response.status_code == 200:
                    print(f"  ✅ API is running at {api_url}")
                    self.results.append({"check": "api", "passed": True})
                    
                    # Check health endpoint
                    health_response = await client.get(
                        f"{api_url}/api/v1/health",
                        timeout=5.0
                    )
                    if health_response.status_code == 200:
                        print("  ✅ Health endpoint is responding")
                else:
                    print(f"  ❌ API returned {response.status_code}")
                    self.results.append({"check": "api", "passed": False})
        except Exception as e:
            print(f"  ℹ️  API not running (this is OK if you haven't started it yet)")
            print(f"     Start with: python -m uvicorn src.api.main:app --reload")
            self.results.append({"check": "api", "passed": False, "critical": False})
    
    def _print_summary(self) -> None:
        """Print summary of health checks."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("passed"))
        failed = total - passed
        critical_failures = sum(
            1 for r in self.results 
            if not r.get("passed") and r.get("critical", True)
        )
        
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"\nTotal checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Critical failures: {critical_failures}")
        
        if critical_failures > 0:
            print("\n⛔ CRITICAL: Fix errors before starting")
        elif failed > 0:
            print("\n⚠️  Some checks failed (non-critical)")
        else:
            print("\n🎉 All checks passed! System is healthy")
        
        print("=" * 70 + "\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Zakera health check and diagnostics"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip slow checks (API connectivity tests)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix common issues"
    )
    
    args = parser.parse_args()
    
    # Run health checks
    checker = HealthChecker(quick=args.quick)
    is_healthy = await checker.check_all()
    
    # Exit with appropriate code
    sys.exit(0 if is_healthy else 1)


if __name__ == "__main__":
    asyncio.run(main())
