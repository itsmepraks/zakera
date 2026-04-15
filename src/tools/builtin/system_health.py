from ..base import Tool
class SystemHealthTool(Tool):
  name = 'system_health'
  description = 'Check provider health'
  def execute(self, **kwargs): return {'status': 'ok'}