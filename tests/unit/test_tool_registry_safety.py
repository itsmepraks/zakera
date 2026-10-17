"""Safety-boundary tests for legacy built-in tool discovery."""

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools.base import Tool, ToolResult
from src.tools.registry import ToolRegistry


def make_tool(tool_name: str):
    class TestTool(Tool):
        @property
        def name(self) -> str:
            return tool_name

        @property
        def description(self) -> str:
            return f"Test double for {tool_name}"

        @property
        def parameters(self):
            return []

        async def execute(self, **kwargs) -> ToolResult:
            return ToolResult.success_result(data=None)

    return TestTool


class TestUnsafeLegacyToolDiscovery(unittest.TestCase):
    def discover(self, enabled: bool) -> ToolRegistry:
        builtin_package = types.ModuleType("src.tools.builtin")
        builtin_package.__file__ = str(Path(__file__).parent / "fake_builtin" / "__init__.py")

        modules = {}
        for module_name in ("calculator", "code_executor", "file_reader"):
            module = types.ModuleType(f"src.tools.builtin.{module_name}")
            setattr(module, "DiscoveredTool", make_tool(module_name))
            modules[module_name] = module

        def import_module(name: str):
            return modules[name.rsplit(".", 1)[-1]]

        environment = {"ZAKERA_ENABLE_UNSAFE_LEGACY_TOOLS": "true"} if enabled else {}
        registry = ToolRegistry()

        with (
            patch.dict(os.environ, environment, clear=True),
            patch.dict(sys.modules, {"src.tools.builtin": builtin_package}),
            patch(
                "src.tools.registry.pkgutil.iter_modules",
                return_value=[
                    (None, "calculator", False),
                    (None, "code_executor", False),
                    (None, "file_reader", False),
                ],
            ),
            patch("src.tools.registry.importlib.import_module", side_effect=import_module),
        ):
            registry.discover_builtin_tools()

        return registry

    def test_unsafe_tools_are_excluded_by_default(self):
        registry = self.discover(enabled=False)

        self.assertIn("calculator", registry)
        self.assertNotIn("code_executor", registry)
        self.assertNotIn("file_reader", registry)

    def test_unsafe_tools_require_explicit_opt_in(self):
        registry = self.discover(enabled=True)

        self.assertIn("calculator", registry)
        self.assertIn("code_executor", registry)
        self.assertIn("file_reader", registry)


if __name__ == "__main__":
    unittest.main()
