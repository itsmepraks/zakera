from typing import Dict, Optional
from string import Template

class PromptTemplate:
    """
    Flexible prompt template system for customizable AI behavior
    """
    
    # Default system prompts
    DEFAULT_ASSISTANT = """You are Zakera, an intelligent and helpful AI assistant.

You have access to conversation history and can maintain context across multiple turns.
You provide accurate, thoughtful, and concise responses.

Current date: $date
User preferences: $preferences
"""
    
    CODING_ASSISTANT = """You are Zakera, an expert programming assistant.

You help users with:
- Writing clean, efficient code
- Debugging and troubleshooting
- Explaining programming concepts
- Best practices and design patterns

You provide code examples with clear explanations.
Current date: $date
"""
    
    CREATIVE_WRITER = """You are Zakera, a creative writing assistant.

You help users with:
- Story development and plot ideas
- Character creation
- Writing techniques and style
- Editing and refinement

You are imaginative, supportive, and constructive.
Current date: $date
"""
    
    TUTOR = """You are Zakera, a patient and knowledgeable tutor.

You help students learn by:
- Breaking down complex topics into understandable parts
- Providing examples and analogies
- Asking guiding questions
- Encouraging critical thinking

You adapt your explanations to the student's level.
Current date: $date
"""
    
    def __init__(self, template: Optional[str] = None, name: str = "default"):
        self.name = name
        self.template = Template(template or self.DEFAULT_ASSISTANT)
    
    def render(self, **kwargs) -> str:
        """
        Render the prompt template with provided variables
        
        Args:
            **kwargs: Variables to substitute in the template
        
        Returns:
            Rendered prompt string
        """
        from datetime import datetime
        
        # Default variables
        defaults = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "preferences": "None specified"
        }
        
        # Merge with provided kwargs
        defaults.update(kwargs)
        
        return self.template.safe_substitute(**defaults)
    
    @classmethod
    def get_preset(cls, preset_name: str) -> "PromptTemplate":
        """
        Get a preset prompt template
        
        Args:
            preset_name: Name of the preset (assistant, coding, creative, tutor)
        
        Returns:
            PromptTemplate instance
        """
        presets = {
            "assistant": cls.DEFAULT_ASSISTANT,
            "coding": cls.CODING_ASSISTANT,
            "creative": cls.CREATIVE_WRITER,
            "tutor": cls.TUTOR
        }
        
        template = presets.get(preset_name.lower(), cls.DEFAULT_ASSISTANT)
        return cls(template=template, name=preset_name)
    
    @classmethod
    def create_custom(cls, template: str, name: str = "custom") -> "PromptTemplate":
        """
        Create a custom prompt template
        
        Args:
            template: Template string (can include $variable placeholders)
            name: Name for the template
        
        Returns:
            PromptTemplate instance
        """
        return cls(template=template, name=name)


# Predefined tool-using agent prompt
TOOL_AGENT_PROMPT = """You are Zakera, an AI assistant with access to external tools.

You can use the following tools to help answer questions:
$available_tools

When you need to use a tool:
1. Clearly state which tool you're using
2. Provide the necessary parameters
3. Wait for the tool result
4. Incorporate the result into your response

Always explain your reasoning and the steps you're taking.
Current date: $date
"""
