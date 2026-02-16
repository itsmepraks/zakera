"""Configuration validation utilities.

Validates environment configuration and provides helpful error messages.
"""

import os
import sys
from typing import Dict, List, Tuple, Any, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check.
    
    Attributes:
        valid: Whether validation passed
        message: Descriptive message
        severity: Error severity (error, warning, info)
        fix_suggestion: Suggested fix for the issue
    """
    valid: bool
    message: str
    severity: str = "error"  # error, warning, info
    fix_suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation."""
        icon = "✅" if self.valid else ("⚠️" if self.severity == "warning" else "❌")
        msg = f"{icon} {self.message}"
        if not self.valid and self.fix_suggestion:
            msg += f"\n   Fix: {self.fix_suggestion}"
        return msg


class ConfigValidator:
    """Validates Zakera configuration."""
    
    def __init__(self):
        """Initialize validator."""
        self.results: List[ValidationResult] = []
    
    def validate_all(self) -> bool:
        """Run all validation checks.
        
        Returns:
            True if all critical validations pass
        """
        logger.info("Starting configuration validation...")
        
        self.results = []
        
        # Run all checks
        self._check_required_files()
        self._check_python_version()
        self._check_environment_variables()
        self._check_model_providers()
        self._check_database_config()
        self._check_security_config()
        self._check_dependencies()
        
        # Count issues
        errors = sum(1 for r in self.results if not r.valid and r.severity == "error")
        warnings = sum(1 for r in self.results if not r.valid and r.severity == "warning")
        
        logger.info(
            f"Validation complete: {errors} errors, {warnings} warnings"
        )
        
        return errors == 0
    
    def _check_required_files(self) -> None:
        """Check that required files exist."""
        required_files = [
            ("requirements.txt", "Python dependencies file"),
            ("src/api/main.py", "Main application file"),
            ("src/model/config.py", "Model configuration file"),
        ]
        
        for filepath, description in required_files:
            if os.path.exists(filepath):
                self.results.append(ValidationResult(
                    valid=True,
                    message=f"Found {description}: {filepath}",
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    valid=False,
                    message=f"Missing {description}: {filepath}",
                    severity="error",
                    fix_suggestion="Ensure you're running from the project root directory"
                ))
    
    def _check_python_version(self) -> None:
        """Check Python version meets requirements."""
        version = sys.version_info
        
        if version >= (3, 9):
            self.results.append(ValidationResult(
                valid=True,
                message=f"Python version: {version.major}.{version.minor}.{version.micro}",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                valid=False,
                message=f"Python {version.major}.{version.minor} is too old",
                severity="error",
                fix_suggestion="Upgrade to Python 3.9 or higher"
            ))
    
    def _check_environment_variables(self) -> None:
        """Check environment variables are set."""
        # Critical variables
        if os.getenv("SECRET_KEY"):
            # Check if it's the default
            if "your_secret_key" in os.getenv("SECRET_KEY", ""):
                self.results.append(ValidationResult(
                    valid=False,
                    message="SECRET_KEY is set to default value",
                    severity="error",
                    fix_suggestion="Generate a secure secret: python -c 'import secrets; print(secrets.token_hex(32))'"
                ))
            else:
                self.results.append(ValidationResult(
                    valid=True,
                    message="SECRET_KEY is configured",
                    severity="info"
                ))
        else:
            self.results.append(ValidationResult(
                valid=False,
                message="SECRET_KEY not set",
                severity="error",
                fix_suggestion="Add SECRET_KEY to .env file"
            ))
        
        # Database URL
        if os.getenv("DATABASE_URL"):
            self.results.append(ValidationResult(
                valid=True,
                message="DATABASE_URL is configured",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                valid=False,
                message="DATABASE_URL not set",
                severity="warning",
                fix_suggestion="Will use default SQLite database"
            ))
    
    def _check_model_providers(self) -> None:
        """Check that at least one model provider is configured."""
        providers_found = []
        
        # Check API providers
        if os.getenv("OPENAI_API_KEY"):
            providers_found.append("OpenAI")
        if os.getenv("ANTHROPIC_API_KEY"):
            providers_found.append("Anthropic")
        if os.getenv("GOOGLE_API_KEY"):
            providers_found.append("Gemini")
        
        # Check local providers
        if os.getenv("ENABLE_OLLAMA", "false").lower() == "true":
            providers_found.append("Ollama")
        if os.getenv("ENABLE_HUGGINGFACE", "false").lower() == "true":
            providers_found.append("HuggingFace")
        
        if providers_found:
            self.results.append(ValidationResult(
                valid=True,
                message=f"Model providers configured: {', '.join(providers_found)}",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                valid=False,
                message="No model providers configured",
                severity="error",
                fix_suggestion="Add at least one provider API key or enable Ollama"
            ))
        
        # Check default model is set
        default_model = os.getenv("DEFAULT_MODEL")
        if default_model:
            self.results.append(ValidationResult(
                valid=True,
                message=f"Default model: {default_model}",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                valid=False,
                message="DEFAULT_MODEL not set",
                severity="warning",
                fix_suggestion="Will use gpt-3.5-turbo as default"
            ))
    
    def _check_database_config(self) -> None:
        """Check database configuration."""
        db_url = os.getenv("DATABASE_URL", "")
        
        if not db_url:
            self.results.append(ValidationResult(
                valid=True,
                message="Using default SQLite database",
                severity="info"
            ))
            return
        
        # Check database type
        if db_url.startswith("sqlite://"):
            # Extract database path
            db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
            db_dir = os.path.dirname(db_path)
            
            if db_dir and not os.path.exists(db_dir):
                self.results.append(ValidationResult(
                    valid=False,
                    message=f"Database directory doesn't exist: {db_dir}",
                    severity="warning",
                    fix_suggestion=f"Create directory: mkdir -p {db_dir}"
                ))
        
        elif db_url.startswith("postgresql://"):
            self.results.append(ValidationResult(
                valid=True,
                message="Using PostgreSQL database",
                severity="info"
            ))
        
        elif db_url.startswith("mysql://"):
            self.results.append(ValidationResult(
                valid=True,
                message="Using MySQL database",
                severity="info"
            ))
    
    def _check_security_config(self) -> None:
        """Check security configuration."""
        # Check CORS
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
        if allowed_origins:
            origins = [o.strip() for o in allowed_origins.split(",")]
            self.results.append(ValidationResult(
                valid=True,
                message=f"CORS configured for {len(origins)} origin(s)",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                valid=False,
                message="ALLOWED_ORIGINS not set",
                severity="warning",
                fix_suggestion="Set ALLOWED_ORIGINS to configure CORS"
            ))
        
        # Check if running in debug mode
        if os.getenv("DEBUG", "false").lower() == "true":
            self.results.append(ValidationResult(
                valid=False,
                message="DEBUG mode is enabled",
                severity="warning",
                fix_suggestion="Disable DEBUG in production: DEBUG=false"
            ))
    
    def _check_dependencies(self) -> None:
        """Check that key dependencies are installed."""
        required_packages = [
            ("fastapi", "FastAPI web framework"),
            ("sqlalchemy", "Database ORM"),
            ("tiktoken", "Token counting"),
            ("httpx", "HTTP client"),
        ]
        
        for package, description in required_packages:
            try:
                __import__(package)
                self.results.append(ValidationResult(
                    valid=True,
                    message=f"{description} installed",
                    severity="info"
                ))
            except ImportError:
                self.results.append(ValidationResult(
                    valid=False,
                    message=f"{description} not installed",
                    severity="error",
                    fix_suggestion=f"Install with: pip install {package}"
                ))
    
    def print_report(self) -> None:
        """Print validation report to console."""
        print("\n" + "=" * 70)
        print("Zakera Configuration Validation Report")
        print("=" * 70 + "\n")
        
        # Group by severity
        errors = [r for r in self.results if not r.valid and r.severity == "error"]
        warnings = [r for r in self.results if not r.valid and r.severity == "warning"]
        info = [r for r in self.results if r.valid or r.severity == "info"]
        
        # Print errors
        if errors:
            print("\n❌ ERRORS:")
            for result in errors:
                print(f"\n{result}")
        
        # Print warnings
        if warnings:
            print("\n⚠️  WARNINGS:")
            for result in warnings:
                print(f"\n{result}")
        
        # Print info (only if no errors)
        if not errors and info:
            print("\n✅ CONFIGURATION:")
            for result in info[:10]:  # Limit to first 10
                print(f"  {result.message}")
        
        # Summary
        print("\n" + "=" * 70)
        print(f"Summary: {len(errors)} errors, {len(warnings)} warnings")
        
        if errors:
            print("\n⛔ Fix errors before starting the application")
        elif warnings:
            print("\n✅ Configuration valid (but check warnings)")
        else:
            print("\n🎉 All checks passed!")
        
        print("=" * 70 + "\n")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary as dictionary.
        
        Returns:
            Summary dictionary with counts and results
        """
        errors = [r for r in self.results if not r.valid and r.severity == "error"]
        warnings = [r for r in self.results if not r.valid and r.severity == "warning"]
        
        return {
            "valid": len(errors) == 0,
            "total_checks": len(self.results),
            "errors": len(errors),
            "warnings": len(warnings),
            "error_messages": [r.message for r in errors],
            "warning_messages": [r.message for r in warnings]
        }


def validate_config(verbose: bool = True) -> bool:
    """Validate configuration and optionally print report.
    
    Args:
        verbose: Whether to print detailed report
        
    Returns:
        True if configuration is valid
    """
    validator = ConfigValidator()
    is_valid = validator.validate_all()
    
    if verbose:
        validator.print_report()
    
    return is_valid
