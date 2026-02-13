"""
Base classes and interfaces for the Zakera tool system.

Provides abstract base classes for creating tools, handling parameters,
results, and errors in a consistent way across the platform.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import asyncio
import logging

logger = logging.getLogger(__name__)


class ToolParameterType(str, Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """
    Definition of a tool parameter.
    
    Attributes:
        name: Parameter name
        type: Parameter type (string, integer, etc.)
        description: Human-readable description
        required: Whether parameter is required
        default: Default value if not provided
        enum: List of allowed values (optional)
        min_value: Minimum value for numbers
        max_value: Maximum value for numbers
        pattern: Regex pattern for strings
    """
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a parameter value.
        
        Args:
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            if self.required and self.default is None:
                return False, f"Parameter '{self.name}' is required"
            return True, None
        
        # Type validation
        if self.type == ToolParameterType.STRING and not isinstance(value, str):
            return False, f"Parameter '{self.name}' must be a string"
        elif self.type == ToolParameterType.INTEGER and not isinstance(value, int):
            return False, f"Parameter '{self.name}' must be an integer"
        elif self.type == ToolParameterType.FLOAT and not isinstance(value, (int, float)):
            return False, f"Parameter '{self.name}' must be a number"
        elif self.type == ToolParameterType.BOOLEAN and not isinstance(value, bool):
            return False, f"Parameter '{self.name}' must be a boolean"
        elif self.type == ToolParameterType.ARRAY and not isinstance(value, list):
            return False, f"Parameter '{self.name}' must be an array"
        elif self.type == ToolParameterType.OBJECT and not isinstance(value, dict):
            return False, f"Parameter '{self.name}' must be an object"
        
        # Enum validation
        if self.enum and value not in self.enum:
            return False, f"Parameter '{self.name}' must be one of {self.enum}"
        
        # Range validation for numbers
        if self.type in [ToolParameterType.INTEGER, ToolParameterType.FLOAT]:
            if self.min_value is not None and value < self.min_value:
                return False, f"Parameter '{self.name}' must be >= {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Parameter '{self.name}' must be <= {self.max_value}"
        
        # Pattern validation for strings
        if self.type == ToolParameterType.STRING and self.pattern:
            import re
            if not re.match(self.pattern, value):
                return False, f"Parameter '{self.name}' must match pattern {self.pattern}"
        
        return True, None


@dataclass
class ToolResult:
    """
    Result of a tool execution.
    
    Attributes:
        success: Whether execution was successful
        data: Result data
        error: Error message if failed
        metadata: Additional metadata
        execution_time: Time taken to execute
        timestamp: When the result was created
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
    
    @classmethod
    def success_result(
        cls,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None
    ) -> "ToolResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            metadata=metadata or {},
            execution_time=execution_time
        )
    
    @classmethod
    def error_result(
        cls,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None
    ) -> "ToolResult":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {},
            execution_time=execution_time
        )


class ToolError(Exception):
    """Base exception for tool-related errors."""
    pass


class ToolValidationError(ToolError):
    """Raised when tool parameter validation fails."""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""
    pass


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found in the registry."""
    pass


class Tool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are plugins that extend the AI agent's capabilities by providing
    access to external services, APIs, or computational functions.
    
    Attributes:
        name: Unique tool identifier
        description: Human-readable description
        version: Tool version
        parameters: List of tool parameters
        enabled: Whether tool is currently enabled
        rate_limit: Maximum calls per minute (None for unlimited)
        timeout: Maximum execution time in seconds
        requires_auth: Whether tool requires authentication
    """
    
    def __init__(self):
        self._call_count = 0
        self._last_call_time: Optional[datetime] = None
        self._is_initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass
    
    @property
    def version(self) -> str:
        """Tool version."""
        return "1.0.0"
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """List of parameters this tool accepts."""
        pass
    
    @property
    def enabled(self) -> bool:
        """Whether this tool is currently enabled."""
        return True
    
    @property
    def rate_limit(self) -> Optional[int]:
        """Maximum calls per minute (None for unlimited)."""
        return None
    
    @property
    def timeout(self) -> int:
        """Maximum execution time in seconds."""
        return 30
    
    @property
    def requires_auth(self) -> bool:
        """Whether this tool requires authentication."""
        return False
    
    @property
    def category(self) -> str:
        """Tool category for organization."""
        return "general"
    
    @property
    def tags(self) -> List[str]:
        """Tags for tool discovery."""
        return []
    
    async def initialize(self) -> None:
        """
        Initialize the tool.
        
        Called once before the tool is first used.
        Override to set up connections, load resources, etc.
        """
        self._is_initialized = True
        logger.info(f"Initialized tool: {self.name}")
    
    async def cleanup(self) -> None:
        """
        Cleanup tool resources.
        
        Called when the tool is no longer needed.
        Override to close connections, free resources, etc.
        """
        self._is_initialized = False
        logger.info(f"Cleaned up tool: {self.name}")
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Validate tool parameters.
        
        Args:
            parameters: Parameter dictionary to validate
            
        Raises:
            ToolValidationError: If validation fails
        """
        for param_def in self.parameters:
            value = parameters.get(param_def.name, param_def.default)
            
            is_valid, error_msg = param_def.validate(value)
            if not is_valid:
                raise ToolValidationError(error_msg)
            
            # Set default value if not provided
            if param_def.name not in parameters and param_def.default is not None:
                parameters[param_def.name] = param_def.default
    
    @abstractmethod
    async def execute(self, **parameters: Any) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **parameters: Tool parameters as keyword arguments
            
        Returns:
            ToolResult containing execution results
            
        Raises:
            ToolExecutionError: If execution fails
        """
        pass
    
    async def run(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Run the tool with validation and error handling.
        
        Args:
            parameters: Tool parameters
            
        Returns:
            ToolResult containing execution results
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Initialize if needed
            if not self._is_initialized:
                await self.initialize()
            
            # Validate parameters
            self.validate_parameters(parameters)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(**parameters),
                timeout=self.timeout
            )
            
            # Add execution time
            execution_time = asyncio.get_event_loop().time() - start_time
            result.execution_time = execution_time
            
            # Update call tracking
            self._call_count += 1
            self._last_call_time = datetime.utcnow()
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult.error_result(
                error=f"Tool execution timed out after {self.timeout} seconds",
                execution_time=execution_time
            )
        except ToolValidationError as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult.error_result(
                error=f"Parameter validation failed: {str(e)}",
                execution_time=execution_time
            )
        except ToolExecutionError as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult.error_result(
                error=f"Execution failed: {str(e)}",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.exception(f"Unexpected error executing tool {self.name}")
            return ToolResult.error_result(
                error=f"Unexpected error: {str(e)}",
                execution_time=execution_time
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "tags": self.tags,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                }
                for p in self.parameters
            ],
            "enabled": self.enabled,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "requires_auth": self.requires_auth,
            "call_count": self._call_count,
            "last_call_time": self._last_call_time.isoformat() if self._last_call_time else None,
        }
    
    def __repr__(self) -> str:
        return f"<Tool: {self.name} (v{self.version})>"
