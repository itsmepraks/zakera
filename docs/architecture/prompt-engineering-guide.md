# Prompt Engineering Guide — Zakera AI Chat Agent

> **Audience**: Backend and ML engineers working on the Zakera codebase.
> **Module**: `src/model/prompt_templates.py`
> **Last updated**: March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Template Variables](#3-template-variables)
4. [Creating Custom Templates](#4-creating-custom-templates)
5. [Template Chaining](#5-template-chaining)
6. [Registry Usage](#6-registry-usage)
7. [Jinja2 Feature Reference](#7-jinja2-feature-reference)
8. [Built-in Template Catalogue](#8-built-in-template-catalogue)
9. [Prompt Engineering Best Practices](#9-prompt-engineering-best-practices)
10. [Testing Prompts](#10-testing-prompts)
11. [Integration with the Provider Layer](#11-integration-with-the-provider-layer)
12. [Versioning and Migration](#12-versioning-and-migration)

---

## 1. Overview

Zakera's prompt template system separates **prompt logic** from **application code**, giving
you:

- **Versioned templates** — every change is tracked with a semver version string, making
  rollback and A/B testing straightforward.
- **Type-checked variables** — declared `TemplateVariable` metadata catches missing inputs
  before they hit the LLM.
- **Composability** — `TemplateChain` lets you build multi-turn few-shot prompts from smaller,
  reusable pieces.
- **Registry discovery** — `TemplateRegistry` provides search, list, and JSON persistence so
  templates can be managed independently of deploys.
- **Testability** — pure Python rendering means you can assert exact prompt output in unit
  tests without mocking any LLM.

### Design philosophy

```
Data (variables) + Template (Jinja2) = Prompt (string)
Prompt (string) + Provider = Response
```

Prompts are **data**, not code. Store them in the registry. Version them like software.
Test them like functions.

---

## 2. Quick Start

### Render a built-in template

```python
from src.model.prompt_templates import template_registry

# Get the code-review template (latest version)
template = template_registry.get("code-review-v1")

# Render it
prompt = template.render(
    language="Python",
    code="def add(a, b):\n    return a + b",
    focus="edge cases and type safety",
)
print(prompt)
```

### Send to a provider using `to_messages()`

```python
from src.model.prompt_templates import template_registry
from src.model.providers import get_provider

template = template_registry.get("code-review-v1")
messages = template.to_messages(
    language="TypeScript",
    code="const add = (a, b) => a + b",
)

provider = get_provider("openai", model="gpt-4o")
response = await provider.generate(messages)
print(response.content)
```

---

## 3. Template Variables

Each `PromptTemplate` declares its inputs via `TemplateVariable` objects:

```python
TemplateVariable(
    name="language",        # variable name used in Jinja2 {{ language }}
    type="string",          # string | integer | float | boolean | list
    required=True,          # raises TemplateRenderError if missing
    default=None,           # used when not required and not provided
    description="Programming language for the code review.",
)
```

### Variable types

| Type      | Python type          | Jinja2 usage example             |
|-----------|----------------------|----------------------------------|
| `string`  | `str`                | `{{ variable }}`                 |
| `integer` | `int`                | `{{ word_count }}` words         |
| `float`   | `float`              | temperature={{ temp }}           |
| `boolean` | `bool`               | `{% if readonly %}...{% endif %}`|
| `list`    | `list`               | `{% for item in items %}...`     |

### Validation before rendering

```python
missing = template.validate_variables({"language": "Python"})
if missing:
    print(f"Missing: {missing}")  # ['code']
else:
    prompt = template.render(language="Python", code="...")
```

---

## 4. Creating Custom Templates

### Python API

```python
from src.model.prompt_templates import (
    PromptTemplate, TemplateVariable, template_registry
)

my_template = PromptTemplate(
    name="sentiment-classifier-v1",
    version="1.0.0",
    description="Classify the sentiment of a text snippet.",
    tags=["classification", "sentiment", "nlp"],
    template="""\
Classify the sentiment of the following text as Positive, Negative, or Neutral.
Return ONLY the label, nothing else.

Text: {{ text }}

Sentiment:""",
    variables=[
        TemplateVariable(
            name="text",
            type="string",
            required=True,
            description="The text to classify.",
        )
    ],
)

template_registry.register(my_template)
```

### JSON format

Templates can also be defined as JSON for tooling or UI-driven workflows:

```json
{
  "name": "sentiment-classifier-v1",
  "version": "1.0.0",
  "description": "Classify sentiment.",
  "tags": ["classification", "sentiment"],
  "template": "Classify the sentiment of: {{ text }}\\n\\nSentiment:",
  "variables": [
    {
      "name": "text",
      "type": "string",
      "required": true,
      "default": null,
      "description": "Text to classify."
    }
  ],
  "author": "prakriti",
  "created_at": "2026-03-14T22:00:00+00:00"
}
```

Load from file:

```python
count = template_registry.load_from_file("config/custom_templates.json")
print(f"Loaded {count} templates")
```

---

## 5. Template Chaining

`TemplateChain` composes multiple templates into a single multi-turn messages list.
Useful for:

- **Few-shot prompting** — inject worked examples before the real question.
- **Role priming** — separate system prompt template from user query template.
- **Multi-agent handoffs** — build context incrementally across agents.

```python
from src.model.prompt_templates import (
    PromptTemplate, TemplateChain, template_registry
)

# Build a few-shot chain
system_tmpl = PromptTemplate(
    name="sys", template="You are a JSON API. Respond only with valid JSON."
)
example_tmpl = PromptTemplate(
    name="example",
    template="Input: {{ input_example }}\nOutput: {{ output_example }}",
    variables=[
        TemplateVariable(name="input_example", type="string", required=True),
        TemplateVariable(name="output_example", type="string", required=True),
    ],
)
query_tmpl = PromptTemplate(
    name="query",
    template="Input: {{ user_input }}",
    variables=[
        TemplateVariable(name="user_input", type="string", required=True),
    ],
)

chain = TemplateChain()
chain.add(system_tmpl,  role="system",    context_key="system")
chain.add(example_tmpl, role="user",      context_key="example")
chain.add(query_tmpl,   role="user",      context_key="query")

messages = chain.render_chain(
    system={},
    example={"input_example": "list users", "output_example": '{"users": []}'},
    query={"user_input": "list products"},
)
# messages is now an OpenAI-compatible list ready for any provider
```

---

## 6. Registry Usage

### List all templates

```python
from src.model.prompt_templates import template_registry

for entry in template_registry.list_templates():
    print(f"{entry.name:40s} {entry.versions}  tags={entry.tags}")
```

### Search by keyword

```python
results = template_registry.search("sql")
for tmpl in results:
    print(tmpl.name, "—", tmpl.description)
```

### Get a specific version

```python
# Latest (default)
tmpl = template_registry.get("code-review-v1")

# Specific version
tmpl_v1 = template_registry.get("code-review-v1", version="1.0.0")
```

### Persist to disk

```python
# Save all registered templates
template_registry.save_to_file("config/templates_snapshot.json")

# Reload in another process
new_registry = TemplateRegistry()
new_registry.load_from_file("config/templates_snapshot.json")
```

---

## 7. Jinja2 Feature Reference

Zakera templates use **Jinja2** with `StrictUndefined` (undefined variables raise errors),
`trim_blocks=True`, and `lstrip_blocks=True`.

### Variable interpolation

```jinja2
Hello, {{ name }}!                    {# simple substitution #}
Hello, {{ name | default('world') }}! {# with fallback #}
Hello, {{ name | upper }}!            {# with filter #}
```

### Conditionals

```jinja2
{% if readonly %}
Use only SELECT statements.
{% elif write_access %}
You may use INSERT, UPDATE, and DELETE.
{% else %}
Ask for the required access level.
{% endif %}
```

### Loops

```jinja2
{% for chunk in context_chunks %}
[{{ loop.index }}] {{ chunk }}
{% endfor %}
```

### Useful built-in filters

| Filter              | Example                           | Effect                         |
|---------------------|-----------------------------------|--------------------------------|
| `default`           | `{{ x \| default('N/A') }}`       | Fallback value                 |
| `upper` / `lower`   | `{{ lang \| lower }}`             | Case conversion                |
| `trim`              | `{{ text \| trim }}`              | Strip whitespace               |
| `truncate`          | `{{ text \| truncate(100) }}`     | Limit length                   |
| `join`              | `{{ list \| join(', ') }}`        | Join list to string            |
| `length`            | `{{ items \| length }}`           | List/string length             |
| `int`               | `{{ count \| int }}`              | Type coercion                  |

---

## 8. Built-in Template Catalogue

| Name                         | Tags                           | Key Variables                              |
|------------------------------|--------------------------------|--------------------------------------------|
| `general-assistant-v1`       | general, assistant, base       | question, persona, language                |
| `code-review-v1`             | coding, review, quality        | language\*, code\*, focus, context         |
| `sql-query-generator-v1`     | sql, database, query           | question\*, schema, dialect, readonly      |
| `document-summarizer-v1`     | summarisation, documents       | document\*, length, style                  |
| `question-answering-rag-v1`  | rag, qa, retrieval             | question\*, context_chunks\*               |
| `creative-writing-v1`        | creative, writing, fiction     | subject\*, genre, tone, word_count         |
| `email-composer-v1`          | email, communication           | purpose\*, recipient_role, formality       |
| `debugging-assistant-v1`     | debugging, errors, coding      | language\*, error_message\*, code_context  |
| `data-analysis-v1`           | data, analysis, insights       | data\*, data_format, analysis_goals        |
| `system-architect-v1`        | architecture, design           | context\*, decision\*, constraints, scale  |

\* = required variable

### Example render: `question-answering-rag-v1`

```python
tmpl = template_registry.get("question-answering-rag-v1")
prompt = tmpl.render(
    question="What is the capital of France?",
    context_chunks=[
        "France is a country in Western Europe.",
        "Paris is the capital and largest city of France, with a population of over 2 million.",
    ],
)
```

Output:
```
Answer the question below using ONLY the information in the provided context.
If the context does not contain enough information to answer, say so clearly.
Do not fabricate facts.

Context:
[1] France is a country in Western Europe.
[2] Paris is the capital and largest city of France, with a population of over 2 million.

Question: What is the capital of France?

Answer:
```

---

## 9. Prompt Engineering Best Practices

### 9.1 Role priming

Always establish the model's role and expertise at the top of the system prompt:

```
You are an expert Python developer with 10+ years of experience in
asynchronous systems and distributed architectures.
```

For Zakera, use the `system_prompt` parameter in `to_messages()` rather than
embedding the role in the user template:

```python
messages = template.to_messages(
    system_prompt="You are an expert Python developer.",
    **template_vars,
)
```

### 9.2 Chain-of-thought

For complex reasoning tasks, instruct the model to think step by step before
providing a final answer. Add to the template:

```jinja2
Think through this step by step before providing your final answer.
Show your reasoning, then conclude with "Final answer:".
```

### 9.3 Output format anchoring

Explicitly specify the output format to reduce post-processing:

```jinja2
Respond ONLY with a JSON object matching this schema:
{
  "severity": "critical" | "major" | "minor",
  "summary": string,
  "suggestions": string[]
}
```

For structured output, use `generate_structured()` with the Ollama provider or
OpenAI's `response_format={"type": "json_object"}` parameter.

### 9.4 Context window budgeting

- Reserve ~20% of the context window for the completion.
- For RAG templates, truncate each context chunk to a fixed token budget:

```python
MAX_CHUNK_TOKENS = 400
chunks = [tokenize_and_truncate(c, MAX_CHUNK_TOKENS) for c in retrieved_chunks]
```

- Use the `UsageTracker` service to monitor token consumption per template
  and set alerts when a template consistently hits >80% of the context window.

### 9.5 Temperature guidance

| Task type            | Recommended temperature |
|----------------------|-------------------------|
| Code generation      | 0.1 – 0.3               |
| Code review          | 0.2 – 0.4               |
| SQL generation       | 0.0 – 0.2               |
| Document summariser  | 0.3 – 0.5               |
| Creative writing     | 0.7 – 1.0               |
| Data analysis        | 0.2 – 0.4               |
| General assistant    | 0.5 – 0.7               |

### 9.6 Avoiding common pitfalls

- **Prompt injection**: Sanitise user-supplied variables. Never embed untrusted
  content directly in system messages. Use Jinja2's `| e` escape filter for
  HTML contexts.
- **Over-specification**: Prompts that are too rigid produce brittle outputs.
  Leave creative latitude for open-ended tasks.
- **Conflicting instructions**: Avoid contradictions (e.g. "be concise" and
  "cover all points in detail").
- **Missing negatives**: Tell the model what NOT to do as well as what to do:
  "Do not include code examples" is clearer than hoping it won't.

---

## 10. Testing Prompts

### Deterministic rendering tests

Since rendering is pure Python, tests are fast and need no LLM:

```python
import pytest
from src.model.prompt_templates import template_registry, TemplateRenderError

def test_code_review_renders_language():
    tmpl = template_registry.get("code-review-v1")
    prompt = tmpl.render(language="Python", code="x = 1")
    assert "Python" in prompt
    assert "x = 1" in prompt

def test_code_review_raises_on_missing_code():
    tmpl = template_registry.get("code-review-v1")
    with pytest.raises(TemplateRenderError, match="code"):
        tmpl.render(language="Python")  # missing 'code'

def test_rag_renders_all_chunks():
    tmpl = template_registry.get("question-answering-rag-v1")
    prompt = tmpl.render(
        question="What is RAG?",
        context_chunks=["Chunk A", "Chunk B"],
    )
    assert "[1] Chunk A" in prompt
    assert "[2] Chunk B" in prompt
```

### Snapshot testing

For templates where exact wording matters, use snapshot tests:

```python
def test_sql_template_snapshot(snapshot):
    tmpl = template_registry.get("sql-query-generator-v1")
    prompt = tmpl.render(
        question="Count users created this month",
        dialect="PostgreSQL",
    )
    snapshot.assert_match(prompt, "sql_template_snapshot.txt")
```

### Validating all built-in templates

```python
from src.model.prompt_templates import BUILTIN_TEMPLATES

@pytest.mark.parametrize("tmpl", BUILTIN_TEMPLATES, ids=lambda t: t.name)
def test_builtin_template_has_description(tmpl):
    assert len(tmpl.description) > 10

@pytest.mark.parametrize("tmpl", BUILTIN_TEMPLATES, ids=lambda t: t.name)
def test_builtin_template_has_tags(tmpl):
    assert len(tmpl.tags) > 0

@pytest.mark.parametrize("tmpl", BUILTIN_TEMPLATES, ids=lambda t: t.name)
def test_builtin_template_roundtrips_json(tmpl):
    from src.model.prompt_templates import PromptTemplate
    restored = PromptTemplate.from_dict(tmpl.to_dict())
    assert restored.name == tmpl.name
    assert restored.template == tmpl.template
```

---

## 11. Integration with the Provider Layer

The `to_messages()` helper is the bridge between templates and providers:

```python
from src.model.prompt_templates import template_registry
from src.model.model_manager import ModelManager

async def review_code(
    language: str,
    code: str,
    provider_name: str = "openai",
    model: str = "gpt-4o",
) -> str:
    template = template_registry.get("code-review-v1")
    messages = template.to_messages(
        system_prompt=f"You are an expert {language} developer.",
        language=language,
        code=code,
    )
    manager = ModelManager()
    response = await manager.generate(
        provider=provider_name,
        model=model,
        messages=messages,
        temperature=0.3,
    )
    return response.content
```

### With the UsageTracker

Wrap template renders with usage tracking to correlate token costs with
specific templates:

```python
from src.api.services.usage_tracker import usage_tracker

response = await provider.generate(messages, temperature=0.3)
await usage_tracker.record(
    user_id=current_user.id,
    provider=provider_name,
    model=model,
    prompt_tokens=response.prompt_tokens,
    completion_tokens=response.completion_tokens,
    conversation_id=conversation_id,
    # Tag with the template name for cost attribution:
    metadata={"template": template.name, "template_version": template.version},
)
```

---

## 12. Versioning and Migration

### Versioning policy

| Change type                          | Version bump |
|--------------------------------------|-------------|
| New optional variable added          | `PATCH`      |
| Default value changed                | `PATCH`      |
| Wording tweaked (no semantic change) | `PATCH`      |
| New required variable added          | `MINOR`      |
| Variable removed                     | `MINOR`      |
| Fundamental rewrite / intent change  | `MAJOR`      |

### Registering a new version alongside the old

```python
# v1.0.0 remains registered; v1.1.0 is added
new_version = PromptTemplate(
    name="code-review-v1",
    version="1.1.0",
    template="...improved template...",
    ...
)
template_registry.register(new_version)

# Existing code that calls get("code-review-v1") now gets 1.1.0 (latest)
# Pin to old version explicitly:
old_tmpl = template_registry.get("code-review-v1", version="1.0.0")
```

### Migration checklist

- [ ] Bump the version string following the policy above.
- [ ] Update `description` to note what changed.
- [ ] Add/update `TemplateVariable` declarations.
- [ ] Write a rendering test for the new version.
- [ ] Run snapshot tests and update snapshots if the output changed intentionally.
- [ ] Update this catalogue table in the guide.
- [ ] Notify dependent services (e.g. usage-tracker dashboard) of the new template name.
