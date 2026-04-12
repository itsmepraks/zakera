"""
Versioned prompt-template library for the Zakera AI chat agent.

Provides Jinja2-powered PromptTemplate objects, a composable TemplateChain
for multi-turn prompts, and a TemplateRegistry for discovery and persistence.

Quick start::

    from src.model.prompt_templates import template_registry

    template = template_registry.get("code-review-v1")
    prompt = template.render(
        language="Python",
        code="def add(a, b): return a + b",
        focus="edge cases",
    )
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jinja2
    from jinja2 import Environment, StrictUndefined, TemplateError
except ImportError as _jinja_missing:  # pragma: no cover
    raise ImportError(
        "Jinja2 is required for prompt_templates. "
        "Install it with: pip install jinja2"
    ) from _jinja_missing

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TemplateRenderError(ValueError):
    """Raised when a template cannot be rendered due to missing/invalid variables."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TemplateVariable:
    """Metadata for a single template variable."""

    name: str
    type: str = "string"  # string | integer | float | boolean | list
    required: bool = True
    default: Any = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVariable":
        return cls(
            name=data["name"],
            type=data.get("type", "string"),
            required=data.get("required", True),
            default=data.get("default"),
            description=data.get("description", ""),
        )


@dataclass
class PromptTemplate:
    """
    A versioned, Jinja2-powered prompt template.

    Attributes:
        name:        Unique human-readable identifier (e.g. "code-review-v1").
        template:    Jinja2 template source string.
        version:     Semantic version string (e.g. "1.0.0").
        description: Short description for the registry UI.
        variables:   Declared input variables with types and defaults.
        tags:        Free-form categorisation tags (e.g. ["coding", "review"]).
        created_at:  ISO-8601 creation timestamp.
        author:      Author identifier.
    """

    name: str
    template: str
    version: str = "1.0.0"
    description: str = ""
    variables: List[TemplateVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    author: str = "zakera"

    # Jinja2 environment is shared across all PromptTemplate instances.
    _jinja_env: Environment = field(
        default_factory=lambda: Environment(
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        ),
        repr=False,
        compare=False,
    )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def validate_variables(self, kwargs: Dict[str, Any]) -> List[str]:
        """
        Return a list of missing required variable names.
        An empty list means the kwargs are sufficient to render.
        """
        missing = []
        for var in self.variables:
            if var.required and var.name not in kwargs and var.default is None:
                missing.append(var.name)
        return missing

    def render(self, **kwargs: Any) -> str:
        """
        Render the template with the provided keyword arguments.

        Raises:
            TemplateRenderError: If a required variable is missing or the
                Jinja2 template contains a syntax/runtime error.
        """
        # Apply defaults for optional variables
        context: Dict[str, Any] = {}
        for var in self.variables:
            if var.default is not None and var.name not in kwargs:
                context[var.name] = var.default
        context.update(kwargs)

        missing = self.validate_variables(context)
        if missing:
            raise TemplateRenderError(
                f"Template '{self.name}' is missing required variables: "
                + ", ".join(missing)
            )

        try:
            jinja_template = self._jinja_env.from_string(self.template)
            rendered = jinja_template.render(**context)
            return rendered.strip()
        except jinja2.UndefinedError as exc:
            raise TemplateRenderError(
                f"Template '{self.name}' references undefined variable: {exc}"
            ) from exc
        except TemplateError as exc:
            raise TemplateRenderError(
                f"Template '{self.name}' failed to render: {exc}"
            ) from exc

    def to_messages(
        self,
        role: str = "user",
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, str]]:
        """
        Render and wrap in an OpenAI-compatible messages list.

        Args:
            role:          The role for the rendered message ('user' or 'assistant').
            system_prompt: Optional system message prepended to the list.
            **kwargs:      Template variables.

        Returns:
            A list of dicts with 'role' and 'content' keys.
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": role, "content": self.render(**kwargs)})
        return messages

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "template": self.template,
            "version": self.version,
            "description": self.description,
            "variables": [v.to_dict() for v in self.variables],
            "tags": self.tags,
            "created_at": self.created_at,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        return cls(
            name=data["name"],
            template=data["template"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            variables=[
                TemplateVariable.from_dict(v)
                for v in data.get("variables", [])
            ],
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            author=data.get("author", "zakera"),
        )


# ---------------------------------------------------------------------------
# Template chain
# ---------------------------------------------------------------------------


@dataclass
class _ChainEntry:
    template: PromptTemplate
    role: str
    context_key: str  # key in the contexts dict passed to render_chain()


class TemplateChain:
    """
    Compose multiple PromptTemplate objects into a multi-turn message list.

    Example::

        chain = TemplateChain()
        chain.add(system_template, role="system", context_key="system")
        chain.add(user_template,   role="user",   context_key="user")
        chain.add(few_shot_template, role="assistant", context_key="few_shot")

        messages = chain.render_chain(
            system={"persona": "helpful assistant"},
            user={"question": "What is RAG?"},
            few_shot={"example_answer": "RAG stands for…"},
        )
    """

    def __init__(self) -> None:
        self._entries: List[_ChainEntry] = []

    def add(
        self,
        template: PromptTemplate,
        role: str = "user",
        context_key: Optional[str] = None,
    ) -> "TemplateChain":
        """
        Append a template to the chain.

        Args:
            template:    The PromptTemplate to add.
            role:        OpenAI message role ('system', 'user', or 'assistant').
            context_key: Key under which to look up kwargs in render_chain().
                         Defaults to the template name.
        """
        key = context_key or template.name
        self._entries.append(_ChainEntry(template=template, role=role, context_key=key))
        return self  # fluent API

    def render_chain(self, **contexts: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Render all templates and return an OpenAI-compatible messages list.

        Args:
            **contexts: One kwarg per chain entry, keyed by context_key.
                        Each value is a dict of template variables.
        """
        messages: List[Dict[str, str]] = []
        for entry in self._entries:
            entry_context = contexts.get(entry.context_key, {})
            content = entry.template.render(**entry_context)
            messages.append({"role": entry.role, "content": content})
        return messages

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class TemplateRegistryEntry:
    name: str
    versions: List[str]
    tags: List[str]
    description: str


class TemplateRegistry:
    """
    In-memory registry for PromptTemplate objects.

    Supports versioned storage, search, and JSON file persistence.
    """

    def __init__(self) -> None:
        # dict[name -> dict[version -> PromptTemplate]]
        self._store: Dict[str, Dict[str, PromptTemplate]] = {}

    def register(self, template: PromptTemplate) -> None:
        """Add or replace a template version in the registry."""
        if template.name not in self._store:
            self._store[template.name] = {}
        self._store[template.name][template.version] = template
        logger.debug("Registered template '%s' v%s", template.name, template.version)

    def get(
        self, name: str, version: str = "latest"
    ) -> Optional[PromptTemplate]:
        """
        Retrieve a template by name and optional version.

        Args:
            name:    Template name.
            version: Specific version string or 'latest' (default).

        Returns:
            The PromptTemplate, or None if not found.
        """
        if name not in self._store:
            return None
        versions = self._store[name]
        if version == "latest":
            # Sort by version string; for proper semver, use packaging.version
            latest = sorted(versions.keys())[-1]
            return versions[latest]
        return versions.get(version)

    def list_templates(self) -> List[TemplateRegistryEntry]:
        """Return a summary of all registered templates."""
        entries = []
        for name, versions in self._store.items():
            # Pick the latest for description/tags
            latest_ver = sorted(versions.keys())[-1]
            tmpl = versions[latest_ver]
            entries.append(
                TemplateRegistryEntry(
                    name=name,
                    versions=sorted(versions.keys()),
                    tags=tmpl.tags,
                    description=tmpl.description,
                )
            )
        return entries

    def search(self, query: str) -> List[PromptTemplate]:
        """
        Search templates by name, description, or tags (case-insensitive).

        Returns the latest version of each matching template.
        """
        q = query.lower()
        results = []
        for name, versions in self._store.items():
            latest_ver = sorted(versions.keys())[-1]
            tmpl = versions[latest_ver]
            haystack = " ".join(
                [tmpl.name, tmpl.description] + tmpl.tags
            ).lower()
            if q in haystack:
                results.append(tmpl)
        return results

    def load_from_file(self, path: str | Path) -> int:
        """
        Load templates from a JSON file produced by save_to_file().

        Returns the number of templates loaded.
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        count = 0
        for item in data.get("templates", []):
            self.register(PromptTemplate.from_dict(item))
            count += 1
        logger.info("Loaded %d templates from %s", count, path)
        return count

    def save_to_file(self, path: str | Path) -> None:
        """Persist all registered templates to a JSON file."""
        path = Path(path)
        all_templates = []
        for versions in self._store.values():
            for tmpl in versions.values():
                all_templates.append(tmpl.to_dict())
        with path.open("w", encoding="utf-8") as fh:
            json.dump({"templates": all_templates}, fh, indent=2, ensure_ascii=False)
        logger.info("Saved %d templates to %s", len(all_templates), path)


# ---------------------------------------------------------------------------
# Built-in template library
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: List[PromptTemplate] = [
    # 1. General assistant
    PromptTemplate(
        name="general-assistant-v1",
        version="1.0.0",
        description="Friendly general-purpose assistant prompt with persona and language control.",
        tags=["general", "assistant", "base"],
        template="""\
You are {{ persona | default('a helpful, friendly AI assistant') }}.
{% if language and language != 'English' %}
Please respond in {{ language }}.
{% endif %}

User question:
{{ question }}
""",
        variables=[
            TemplateVariable(
                name="question", type="string", required=True,
                description="The user's question or request."
            ),
            TemplateVariable(
                name="persona", type="string", required=False,
                default="a helpful, friendly AI assistant",
                description="Custom persona description."
            ),
            TemplateVariable(
                name="language", type="string", required=False,
                default="English",
                description="Language for the response."
            ),
        ],
    ),

    # 2. Code review
    PromptTemplate(
        name="code-review-v1",
        version="1.0.0",
        description="Structured code review assistant with configurable focus areas.",
        tags=["coding", "review", "quality"],
        template="""\
You are an expert {{ language }} developer performing a thorough code review.

Please review the following {{ language }} code with a focus on: {{ focus | default('correctness, readability, and performance') }}.

Provide your review in this structure:
1. **Summary**: Overall assessment (1-2 sentences)
2. **Issues**: List each problem with severity (Critical / Major / Minor / Nit)
3. **Suggestions**: Concrete improvement recommendations
4. **Positive aspects**: What the code does well

Code to review:
```{{ language | lower }}
{{ code }}
```
{% if context %}

Additional context:
{{ context }}
{% endif %}
""",
        variables=[
            TemplateVariable(
                name="language", type="string", required=True,
                description="Programming language (e.g. Python, TypeScript)."
            ),
            TemplateVariable(
                name="code", type="string", required=True,
                description="The code snippet to review."
            ),
            TemplateVariable(
                name="focus", type="string", required=False,
                default="correctness, readability, and performance",
                description="Aspect(s) to focus on."
            ),
            TemplateVariable(
                name="context", type="string", required=False,
                default=None,
                description="Optional surrounding context or requirements."
            ),
        ],
    ),

    # 3. SQL query generator
    PromptTemplate(
        name="sql-query-generator-v1",
        version="1.0.0",
        description="Translate natural-language database questions into SQL queries.",
        tags=["sql", "database", "query"],
        template="""\
You are a database expert. Generate a {{ dialect | default('SQL') }} query that answers the following question.

Question: {{ question }}
{% if schema %}

Database schema:
{{ schema }}
{% endif %}

Requirements:
- Return ONLY the SQL query, no explanation unless asked
- Use proper indentation and aliases for readability
- Prefer CTEs over nested subqueries for complex logic
{% if readonly %}
- Use only SELECT statements (read-only access)
{% endif %}
""",
        variables=[
            TemplateVariable(
                name="question", type="string", required=True,
                description="Natural-language description of what to query."
            ),
            TemplateVariable(
                name="schema", type="string", required=False,
                default=None,
                description="DDL or table descriptions to inform the query."
            ),
            TemplateVariable(
                name="dialect", type="string", required=False,
                default="PostgreSQL",
                description="SQL dialect: PostgreSQL, MySQL, SQLite, etc."
            ),
            TemplateVariable(
                name="readonly", type="boolean", required=False,
                default=True,
                description="Restrict to read-only (SELECT) queries."
            ),
        ],
    ),

    # 4. Document summariser
    PromptTemplate(
        name="document-summarizer-v1",
        version="1.0.0",
        description="Summarise documents with configurable length and style.",
        tags=["summarisation", "documents", "nlp"],
        template="""\
Summarise the following document.

{% if length == 'short' %}
Target length: 2-3 sentences (executive summary only).
{% elif length == 'long' %}
Target length: comprehensive summary covering all major points.
{% else %}
Target length: 1 paragraph capturing the key ideas.
{% endif %}
{% if style %}
Summarisation style: {{ style }}
{% endif %}

Document:
---
{{ document }}
---

Summary:
""",
        variables=[
            TemplateVariable(
                name="document", type="string", required=True,
                description="The text to summarise."
            ),
            TemplateVariable(
                name="length", type="string", required=False,
                default="medium",
                description="Summary length: short | medium | long."
            ),
            TemplateVariable(
                name="style", type="string", required=False,
                default=None,
                description="Summarisation style, e.g. 'bullet points', 'narrative'."
            ),
        ],
    ),

    # 5. RAG question-answering
    PromptTemplate(
        name="question-answering-rag-v1",
        version="1.0.0",
        description="Retrieval-augmented generation QA with injected context chunks.",
        tags=["rag", "qa", "retrieval"],
        template="""\
Answer the question below using ONLY the information in the provided context.
If the context does not contain enough information to answer, say so clearly.
Do not fabricate facts.

Context:
{% for chunk in context_chunks %}
[{{ loop.index }}] {{ chunk }}
{% endfor %}

Question: {{ question }}

Answer:
""",
        variables=[
            TemplateVariable(
                name="question", type="string", required=True,
                description="The question to answer."
            ),
            TemplateVariable(
                name="context_chunks", type="list", required=True,
                description="List of retrieved text chunks providing context."
            ),
        ],
    ),

    # 6. Creative writing
    PromptTemplate(
        name="creative-writing-v1",
        version="1.0.0",
        description="Creative story or poem generator with genre, tone, and length control.",
        tags=["creative", "writing", "fiction"],
        template="""\
Write a {{ genre | default('short story') }} about {{ subject }}.

Tone: {{ tone | default('engaging and imaginative') }}
{% if word_count %}
Target word count: approximately {{ word_count }} words.
{% endif %}
{% if additional_instructions %}
Additional instructions: {{ additional_instructions }}
{% endif %}
""",
        variables=[
            TemplateVariable(
                name="subject", type="string", required=True,
                description="The main subject or theme of the piece."
            ),
            TemplateVariable(
                name="genre", type="string", required=False,
                default="short story",
                description="Genre: short story, poem, haiku, limerick, etc."
            ),
            TemplateVariable(
                name="tone", type="string", required=False,
                default="engaging and imaginative",
                description="Desired tone: humorous, serious, melancholic, etc."
            ),
            TemplateVariable(
                name="word_count", type="integer", required=False,
                default=None,
                description="Approximate target word count."
            ),
            TemplateVariable(
                name="additional_instructions", type="string", required=False,
                default=None,
                description="Any extra creative direction."
            ),
        ],
    ),

    # 7. Email composer
    PromptTemplate(
        name="email-composer-v1",
        version="1.0.0",
        description="Draft professional emails with purpose, recipient context, and formality level.",
        tags=["email", "communication", "professional"],
        template="""\
Draft a professional email with the following details:

Purpose: {{ purpose }}
Recipient role: {{ recipient_role | default('colleague') }}
Formality level: {{ formality | default('formal') }}
{% if key_points %}
Key points to include:
{% for point in key_points %}
- {{ point }}
{% endfor %}
{% endif %}
{% if sender_name %}
Sign off as: {{ sender_name }}
{% endif %}

Email:
""",
        variables=[
            TemplateVariable(
                name="purpose", type="string", required=True,
                description="The goal/purpose of the email."
            ),
            TemplateVariable(
                name="recipient_role", type="string", required=False,
                default="colleague",
                description="The recipient's role (e.g. manager, client, team)."
            ),
            TemplateVariable(
                name="formality", type="string", required=False,
                default="formal",
                description="Formality: formal | semi-formal | casual."
            ),
            TemplateVariable(
                name="key_points", type="list", required=False,
                default=None,
                description="List of key points to include in the email body."
            ),
            TemplateVariable(
                name="sender_name", type="string", required=False,
                default=None,
                description="Name to use in the sign-off."
            ),
        ],
    ),

    # 8. Debugging assistant
    PromptTemplate(
        name="debugging-assistant-v1",
        version="1.0.0",
        description="Analyse error messages and stack traces with code context.",
        tags=["debugging", "errors", "coding"],
        template="""\
You are an expert {{ language }} debugger. Analyse the following error and provide a diagnosis and fix.

Error message:
```
{{ error_message }}
```
{% if code_context %}

Relevant code:
```{{ language | lower }}
{{ code_context }}
```
{% endif %}
{% if description %}

What I was trying to do:
{{ description }}
{% endif %}

Provide:
1. **Root cause** — what is causing this error
2. **Fix** — exact code change(s) needed
3. **Prevention** — how to avoid this class of error in future
""",
        variables=[
            TemplateVariable(
                name="language", type="string", required=True,
                description="Programming language."
            ),
            TemplateVariable(
                name="error_message", type="string", required=True,
                description="The full error message or stack trace."
            ),
            TemplateVariable(
                name="code_context", type="string", required=False,
                default=None,
                description="The code that caused the error."
            ),
            TemplateVariable(
                name="description", type="string", required=False,
                default=None,
                description="What the developer was attempting to do."
            ),
        ],
    ),

    # 9. Data analysis
    PromptTemplate(
        name="data-analysis-v1",
        version="1.0.0",
        description="Structured data insight generator for tabular or JSON data.",
        tags=["data", "analysis", "insights"],
        template="""\
Analyse the following {{ data_format | default('data') }} and provide structured insights.

Data:
{{ data }}

{% if analysis_goals %}
Analysis goals:
{% for goal in analysis_goals %}
- {{ goal }}
{% endfor %}
{% endif %}

Provide your analysis in this structure:
1. **Overview**: What the data represents
2. **Key findings**: Most important patterns or trends (bullet points)
3. **Anomalies**: Any outliers or unexpected values
4. **Recommendations**: Actionable next steps based on the data
""",
        variables=[
            TemplateVariable(
                name="data", type="string", required=True,
                description="The data to analyse (CSV, JSON, table, etc.)."
            ),
            TemplateVariable(
                name="data_format", type="string", required=False,
                default="tabular data",
                description="Format descriptor: CSV, JSON, table, etc."
            ),
            TemplateVariable(
                name="analysis_goals", type="list", required=False,
                default=None,
                description="Specific questions or goals for the analysis."
            ),
        ],
    ),

    # 10. System architect
    PromptTemplate(
        name="system-architect-v1",
        version="1.0.0",
        description="Technical design advisor for architecture decisions with constraint awareness.",
        tags=["architecture", "design", "technical"],
        template="""\
You are a senior software architect. Provide a technical recommendation for the following design decision.

Context: {{ context }}
Decision to make: {{ decision }}
{% if constraints %}

Constraints:
{% for c in constraints %}
- {{ c }}
{% endfor %}
{% endif %}
{% if scale %}
Expected scale: {{ scale }}
{% endif %}

Structure your response as:
1. **Recommended approach** — the best solution given the constraints
2. **Rationale** — why this approach is preferred
3. **Trade-offs** — what is sacrificed
4. **Alternatives considered** — 1-2 runner-up options and why they were not chosen
5. **Implementation notes** — key implementation details or gotchas
""",
        variables=[
            TemplateVariable(
                name="context", type="string", required=True,
                description="Background context about the system or project."
            ),
            TemplateVariable(
                name="decision", type="string", required=True,
                description="The specific architectural decision to evaluate."
            ),
            TemplateVariable(
                name="constraints", type="list", required=False,
                default=None,
                description="Technical or business constraints."
            ),
            TemplateVariable(
                name="scale", type="string", required=False,
                default=None,
                description="Expected scale (e.g. '10k RPM', '1M users')."
            ),
        ],
    ),

    # 11. Sentiment analyzer
    PromptTemplate(
        name="sentiment-analyzer-v1",
        template="""Analyze the sentiment of the following text and provide a structured response.

Text to analyze:
{{ text }}

Provide your analysis in this format:
- Overall sentiment: [Positive/Negative/Neutral/Mixed]
- Confidence: [High/Medium/Low]
- Key emotional indicators: [list the words/phrases that indicate sentiment]
- Nuances: [any subtleties or context-dependent aspects]
- Summary: [1-2 sentence summary of the sentiment analysis]""",
        version="1.0.0",
        description="Analyze the sentiment and emotional tone of text with structured output.",
        variables=[TemplateVariable(name="text", type="string", required=True, description="The text to analyze for sentiment")],
        tags=["sentiment", "analysis", "nlp", "classification"],
    ),

    # 12. Meeting notes summarizer
    PromptTemplate(
        name="meeting-notes-summarizer-v1",
        template="""You are an expert at summarizing meeting notes into clear, actionable outputs.

Meeting Notes:
{{ meeting_notes }}

{% if attendees %}Attendees: {{ attendees }}{% endif %}
{% if meeting_date %}Date: {{ meeting_date }}{% endif %}

Please provide a structured summary with:

## Key Discussion Points
[Bullet points of the main topics discussed]

## Decisions Made
[Bullet points of any decisions reached]

## Action Items
[Table or list with: Task | Owner | Due Date (if mentioned)]

## Next Steps
[What happens next, any follow-up meetings scheduled]

Keep the summary concise but complete. Highlight any risks or blockers mentioned.""",
        version="1.0.0",
        description="Transform raw meeting notes into structured summaries with action items and decisions.",
        variables=[
            TemplateVariable(name="meeting_notes", type="string", required=True, description="The raw meeting notes to summarize"),
            TemplateVariable(name="attendees", type="string", required=False, default="", description="List of meeting attendees"),
            TemplateVariable(name="meeting_date", type="string", required=False, default="", description="Date of the meeting"),
        ],
        tags=["meetings", "summarization", "productivity", "action-items"],
    ),

    # 13. API documentation generator
    PromptTemplate(
        name="api-documentation-generator-v1",
        template="""Generate clear, comprehensive API documentation for the following code or endpoint specification.

{{ code_or_spec }}

{% if language %}Programming language / framework: {{ language }}{% endif %}

Generate documentation that includes:

## Overview
[Brief description of what this API/function does]

## Endpoint / Function Signature
[Full signature with types]

## Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
[Fill in the table]

## Return Value
[Description of what is returned, including type and structure]

## Error Cases
[List of possible errors/exceptions and when they occur]

## Example Usage
```
[Provide a realistic example]
```

## Notes
[Any important caveats, rate limits, authentication requirements, or edge cases]""",
        version="1.0.0",
        description="Generate structured API documentation from code or endpoint specifications.",
        variables=[
            TemplateVariable(name="code_or_spec", type="string", required=True, description="The code, function, or API endpoint spec to document"),
            TemplateVariable(name="language", type="string", required=False, default="", description="The programming language or framework being used"),
        ],
        tags=["documentation", "api", "developer-tools", "technical-writing"],
    ),

    # 14. Thinking assistant (Chain-of-Thought)
    PromptTemplate(
        name="thinking-assistant-v1",
        version="1.0.0",
        description="Encourage step-by-step reasoning (Chain-of-Thought) for complex tasks.",
        tags=["reasoning", "cot", "thought", "problem-solving"],
        template="""\
You are an intelligent AI assistant capable of complex reasoning.

When answering the following request, please follow these steps:
1. **Analysis**: Break down the user's request and identify key constraints.
2. **Thought Process**: Reason through the problem step-by-step. Show your "thinking" before arriving at a final answer.
3. **Drafting**: Create an initial solution or response.
4. **Final Answer**: Provide the refined, complete response to the user.

Request:
{{ request }}
""",
        variables=[
            TemplateVariable(
                name="request", type="string", required=True,
                description="The complex task or question to reason through."
            ),
        ],
    ),
]

BUILTIN_TEMPLATES.extend(
    [
        # 15. Security auditor
        PromptTemplate(
            name="security-auditor-v1",
            version="1.0.0",
            description="Audit code, configuration, and architecture for security issues.",
            tags=["security", "audit", "compliance", "review"],
            template="""\
You are a senior application security auditor.

Audit the following {{ artifact_type | default('code or configuration') }} for vulnerabilities, misconfigurations, and privacy risks.

Subject:
{{ subject }}
{% if context %}

Context:
{{ context }}
{% endif %}
{% if threat_model %}

Threat model:
{{ threat_model }}
{% endif %}
{% if focus %}

Focus areas:
{{ focus }}
{% endif %}
{% if compliance_requirements %}

Compliance requirements:
{% for req in compliance_requirements %}
- {{ req }}
{% endfor %}
{% endif %}

Provide your review in this structure:
1. **Executive summary** — overall risk posture in 1-2 sentences
2. **Critical findings** — issues that should be fixed immediately
3. **Important findings** — material security concerns and misconfigurations
4. **Recommendations** — concrete remediation steps
5. **Secure-by-default improvements** — changes that reduce future risk
6. **Residual risk** — what remains after remediation
""",
            variables=[
                TemplateVariable(
                    name="subject", type="string", required=True,
                    description="The code, design, or configuration to audit."
                ),
                TemplateVariable(
                    name="artifact_type", type="string", required=False,
                    default="code or configuration",
                    description="Type of artifact being audited."
                ),
                TemplateVariable(
                    name="context", type="string", required=False,
                    default=None,
                    description="Optional product, system, or release context."
                ),
                TemplateVariable(
                    name="threat_model", type="string", required=False,
                    default=None,
                    description="Optional attacker model or abuse scenario."
                ),
                TemplateVariable(
                    name="focus", type="string", required=False,
                    default="authentication, authorization, input validation, secrets handling, logging, and dependency risk",
                    description="Security areas to emphasise in the audit."
                ),
                TemplateVariable(
                    name="compliance_requirements", type="list", required=False,
                    default=None,
                    description="Optional standards or controls such as SOC 2, PCI DSS, or HIPAA."
                ),
            ],
        ),

        # 16. API designer
        PromptTemplate(
            name="api-designer-v1",
            version="1.0.0",
            description="Design REST or JSON APIs with resources, errors, and versioning guidance.",
            tags=["api", "design", "architecture", "backend"],
            template="""\
You are a senior API designer.

Design an API for the following goal:

Goal:
{{ goal }}
{% if audience %}

Primary audience:
{{ audience }}
{% endif %}
{% if constraints %}

Constraints:
{% for constraint in constraints %}
- {{ constraint }}
{% endfor %}
{% endif %}
{% if current_system %}

Current system or existing endpoints:
{{ current_system }}
{% endif %}
{% if auth_strategy %}

Authentication / authorization:
{{ auth_strategy }}
{% endif %}
{% if style %}

Preferred API style:
{{ style }}
{% endif %}
{% if preferred_format %}

Preferred payload format:
{{ preferred_format }}
{% endif %}

Provide your answer in this structure:
1. **Recommended API style** — REST, RPC, GraphQL, or hybrid
2. **Resource model** — key entities and their relationships
3. **Endpoints** — paths, methods, and purpose
4. **Request / response schema** — important fields and examples
5. **Validation and errors** — status codes, error payloads, edge cases
6. **Security and versioning** — auth, backwards compatibility, rollout notes
7. **Example request and response** — one realistic example
""",
            variables=[
                TemplateVariable(
                    name="goal", type="string", required=True,
                    description="The product or feature the API should support."
                ),
                TemplateVariable(
                    name="audience", type="string", required=False,
                    default=None,
                    description="Who will consume the API."
                ),
                TemplateVariable(
                    name="constraints", type="list", required=False,
                    default=None,
                    description="Technical or business constraints."
                ),
                TemplateVariable(
                    name="current_system", type="string", required=False,
                    default=None,
                    description="Existing system context or endpoint conventions."
                ),
                TemplateVariable(
                    name="auth_strategy", type="string", required=False,
                    default=None,
                    description="Authentication or authorization approach."
                ),
                TemplateVariable(
                    name="style", type="string", required=False,
                    default="REST",
                    description="Preferred API style."
                ),
                TemplateVariable(
                    name="preferred_format", type="string", required=False,
                    default="JSON",
                    description="Preferred request/response format."
                ),
            ],
        ),
    ]
)

# ---------------------------------------------------------------------------
# Module-level singleton registry (pre-loaded with built-ins)
# ---------------------------------------------------------------------------

template_registry = TemplateRegistry()
for _tmpl in BUILTIN_TEMPLATES:
    template_registry.register(_tmpl)

logger.debug(
    "Zakera prompt_templates: registered %d built-in templates",
    len(BUILTIN_TEMPLATES),
)
