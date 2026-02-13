"""
Code Executor tool for running code in sandboxed environment.

Provides safe code execution for Python and other languages
with timeout and resource constraints.
"""

import asyncio
import io
import logging
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, List, Optional

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)


class CodeExecutorTool(Tool):
    """
    Tool for executing code in a sandboxed environment.
    
    Currently supports:
    - Python code execution
    
    Security measures:
    - Restricted builtins (no file I/O, imports, etc.)
    - Execution timeout
    - Memory limits (via timeout)
    - Output size limits
    
    Future enhancements:
    - JavaScript execution
    - More language support
    - Docker-based sandboxing
    - Resource quotas
    """
    
    # Allowed built-in functions (safe subset)
    ALLOWED_BUILTINS = {
        'abs': abs,
        'all': all,
        'any': any,
        'bool': bool,
        'dict': dict,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'int': int,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'print': print,
        'range': range,
        'reversed': reversed,
        'round': round,
        'set': set,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'type': type,
        'zip': zip,
    }
    
    @property
    def name(self) -> str:
        return "code_executor"
    
    @property
    def description(self) -> str:
        return (
            "Execute code in a sandboxed environment. "
            "Currently supports Python code with restricted builtins for safety. "
            "Returns stdout, stderr, and any return values."
        )
    
    @property
    def category(self) -> str:
        return "computation"
    
    @property
    def tags(self) -> List[str]:
        return ["code", "python", "execute", "sandbox", "interpreter"]
    
    @property
    def timeout(self) -> int:
        return 5  # 5 seconds max execution
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type=ToolParameterType.STRING,
                description="Python code to execute",
                required=True,
            ),
            ToolParameter(
                name="language",
                type=ToolParameterType.STRING,
                description="Programming language",
                required=False,
                default="python",
                enum=["python"],
            ),
        ]
    
    def _execute_python(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code in restricted environment.
        
        Args:
            code: Python code to execute
            
        Returns:
            Dictionary with stdout, stderr, result, and error
        """
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Create restricted globals
        restricted_globals = {
            '__builtins__': self.ALLOWED_BUILTINS,
            '__name__': '__main__',
            '__doc__': None,
        }
        
        result = None
        error = None
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute code
                exec_result = exec(code, restricted_globals)
                
                # If code ended with an expression, try to evaluate it
                if code.strip() and not code.strip().endswith(':'):
                    try:
                        # Try to evaluate as expression
                        result = eval(code, restricted_globals)
                    except:
                        # Not an expression, that's OK
                        pass
        
        except SyntaxError as e:
            error = f"Syntax Error: {str(e)}"
        except NameError as e:
            error = f"Name Error: {str(e)} (restricted environment)"
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"
        
        return {
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "result": result,
            "error": error,
        }
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        **kwargs
    ) -> ToolResult:
        """
        Execute code in sandboxed environment.
        
        Args:
            code: Code to execute
            language: Programming language
            
        Returns:
            ToolResult with execution output
        """
        try:
            if not code.strip():
                return ToolResult.error_result("Empty code provided")
            
            if language != "python":
                return ToolResult.error_result(
                    f"Unsupported language: {language}. Only Python is currently supported."
                )
            
            # Execute in thread to avoid blocking
            loop = asyncio.get_event_loop()
            execution_result = await loop.run_in_executor(
                None,
                self._execute_python,
                code
            )
            
            # Check for execution errors
            if execution_result["error"]:
                return ToolResult.error_result(
                    error=execution_result["error"],
                    metadata={
                        "stdout": execution_result["stdout"],
                        "stderr": execution_result["stderr"],
                        "language": language,
                    }
                )
            
            # Limit output size
            max_output_size = 10000  # 10KB
            stdout = execution_result["stdout"]
            stderr = execution_result["stderr"]
            
            if len(stdout) > max_output_size:
                stdout = stdout[:max_output_size] + "\n... (output truncated)"
            if len(stderr) > max_output_size:
                stderr = stderr[:max_output_size] + "\n... (output truncated)"
            
            return ToolResult.success_result(
                data={
                    "stdout": stdout,
                    "stderr": stderr,
                    "result": execution_result["result"],
                    "language": language,
                },
                metadata={
                    "code_length": len(code),
                    "has_output": bool(stdout or stderr),
                    "has_result": execution_result["result"] is not None,
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult.error_result(
                "Code execution timed out. The code took too long to execute."
            )
        except Exception as e:
            logger.exception("Unexpected error in code executor")
            return ToolResult.error_result(f"Execution failed: {str(e)}")
