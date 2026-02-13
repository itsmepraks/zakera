"""
Calculator tool for mathematical expression evaluation.

Provides safe mathematical expression evaluation with support for
basic arithmetic, trigonometric, and advanced mathematical functions.
"""

import ast
import math
import operator
import logging
from typing import Any, List

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)


class CalculatorTool(Tool):
    """
    Tool for evaluating mathematical expressions safely.
    
    Supports:
    - Basic arithmetic (+, -, *, /, **, %, //)
    - Mathematical functions (sin, cos, tan, sqrt, log, etc.)
    - Constants (pi, e)
    - Variables and multiple expressions
    
    Examples:
        "2 + 2" -> 4
        "sin(pi / 2)" -> 1.0
        "sqrt(16) + log(100, 10)" -> 6.0
    """
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Allowed functions
    FUNCTIONS = {
        # Basic math
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        
        # Mathematical functions
        'sqrt': math.sqrt,
        'pow': math.pow,
        'exp': math.exp,
        'log': math.log,
        'log10': math.log10,
        'log2': math.log2,
        
        # Trigonometric
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'atan2': math.atan2,
        
        # Hyperbolic
        'sinh': math.sinh,
        'cosh': math.cosh,
        'tanh': math.tanh,
        
        # Angular conversion
        'degrees': math.degrees,
        'radians': math.radians,
        
        # Other
        'ceil': math.ceil,
        'floor': math.floor,
        'factorial': math.factorial,
        'gcd': math.gcd,
    }
    
    # Allowed constants
    CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
        'tau': math.tau,
        'inf': math.inf,
    }
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return (
            "Evaluates mathematical expressions safely. "
            "Supports arithmetic operations, trigonometric functions, "
            "logarithms, and common mathematical constants."
        )
    
    @property
    def category(self) -> str:
        return "computation"
    
    @property
    def tags(self) -> List[str]:
        return ["math", "calculator", "computation", "arithmetic"]
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type=ToolParameterType.STRING,
                description="Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)')",
                required=True,
            ),
            ToolParameter(
                name="precision",
                type=ToolParameterType.INTEGER,
                description="Number of decimal places for result",
                required=False,
                default=None,
                min_value=0,
                max_value=15,
            ),
        ]
    
    def _evaluate_node(self, node: ast.AST, variables: dict = None) -> Any:
        """
        Safely evaluate an AST node.
        
        Args:
            node: AST node to evaluate
            variables: Variable dictionary
            
        Returns:
            Evaluation result
            
        Raises:
            ToolExecutionError: If evaluation fails or uses unsafe operations
        """
        variables = variables or {}
        
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Older Python versions
            return node.n
        elif isinstance(node, ast.Name):
            # Check constants first
            if node.id in self.CONSTANTS:
                return self.CONSTANTS[node.id]
            # Then variables
            if node.id in variables:
                return variables[node.id]
            raise ToolExecutionError(f"Undefined variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ToolExecutionError(f"Unsupported operator: {op_type.__name__}")
            left = self._evaluate_node(node.left, variables)
            right = self._evaluate_node(node.right, variables)
            return self.OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ToolExecutionError(f"Unsupported operator: {op_type.__name__}")
            operand = self._evaluate_node(node.operand, variables)
            return self.OPERATORS[op_type](operand)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ToolExecutionError("Only named functions are allowed")
            
            func_name = node.func.id
            if func_name not in self.FUNCTIONS:
                raise ToolExecutionError(f"Unsupported function: {func_name}")
            
            args = [self._evaluate_node(arg, variables) for arg in node.args]
            return self.FUNCTIONS[func_name](*args)
        elif isinstance(node, ast.Expression):
            return self._evaluate_node(node.body, variables)
        else:
            raise ToolExecutionError(
                f"Unsupported expression type: {type(node).__name__}"
            )
    
    async def execute(self, expression: str, precision: int = None, **kwargs) -> ToolResult:
        """
        Execute mathematical expression evaluation.
        
        Args:
            expression: Mathematical expression to evaluate
            precision: Optional decimal precision
            
        Returns:
            ToolResult with calculated value
        """
        try:
            # Clean the expression
            expression = expression.strip()
            
            if not expression:
                return ToolResult.error_result("Empty expression provided")
            
            # Parse the expression into AST
            try:
                tree = ast.parse(expression, mode='eval')
            except SyntaxError as e:
                return ToolResult.error_result(
                    f"Invalid expression syntax: {str(e)}"
                )
            
            # Evaluate the expression
            result = self._evaluate_node(tree)
            
            # Apply precision if specified
            if precision is not None and isinstance(result, (int, float)):
                result = round(result, precision)
            
            # Return result
            return ToolResult.success_result(
                data={
                    "result": result,
                    "expression": expression,
                    "type": type(result).__name__,
                },
                metadata={
                    "precision": precision,
                    "result_type": "numeric" if isinstance(result, (int, float)) else "other",
                }
            )
            
        except ToolExecutionError as e:
            return ToolResult.error_result(str(e))
        except ZeroDivisionError:
            return ToolResult.error_result("Division by zero")
        except OverflowError:
            return ToolResult.error_result("Result too large to compute")
        except ValueError as e:
            return ToolResult.error_result(f"Math error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error in calculator")
            return ToolResult.error_result(f"Calculation failed: {str(e)}")
