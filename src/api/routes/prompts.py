"""
Prompt Template Management API

Provides endpoints for creating, reading, updating, and deleting saved prompt
templates.  Users can persist custom system-prompt templates, use the built-in
presets (assistant, coding, creative, tutor, tool_agent), and render templates
with dynamic variable substitution before sending them to a model.

Routes
------
GET    /api/v1/prompts/presets              List all built-in preset names
GET    /api/v1/prompts/presets/{name}       Get a rendered preset prompt
GET    /api/v1/prompts                      List user's saved templates
POST   /api/v1/prompts                      Create a new template
GET    /api/v1/prompts/{template_id}        Get a specific template
PUT    /api/v1/prompts/{template_id}        Update a template
DELETE /api/v1/prompts/{template_id}        Delete a template
POST   /api/v1/prompts/{template_id}/render Render a template with variables
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.model.prompts import PromptTemplate, TOOL_AGENT_PROMPT

router = APIRouter(prefix="/prompts", tags=["prompt-templates"])

# ---------------------------------------------------------------------------
# In-process store (replace with DB persistence in production)
# ---------------------------------------------------------------------------
_TEMPLATE_STORE: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Human-readable template name")
    description: Optional[str] = Field(None, max_length=500)
    template: str = Field(..., min_length=1, description="Template string with optional $variable placeholders")
    tags: List[str] = Field(default_factory=list, description="Organisational tags")
    is_public: bool = Field(False, description="Whether the template is visible to other users")


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    template: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class RenderRequest(BaseModel):
    variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Variables to substitute into the template (e.g. {\"date\": \"2026-03-12\"})",
    )


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    template: str
    tags: List[str]
    is_public: bool
    created_at: str
    updated_at: str


class RenderResponse(BaseModel):
    rendered: str
    template_id: str
    variables_used: Dict[str, str]


class PresetResponse(BaseModel):
    name: str
    rendered: str
    description: str


# ---------------------------------------------------------------------------
# Built-in preset metadata
# ---------------------------------------------------------------------------
_PRESETS: Dict[str, str] = {
    "assistant": "General-purpose helpful assistant",
    "coding": "Expert programming assistant with code examples",
    "creative": "Creative writing companion for storytelling and editing",
    "tutor": "Patient, adaptive educational tutor",
    "tool_agent": "Tool-using agent with structured reasoning",
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _require_template(template_id: str) -> Dict[str, Any]:
    tpl = _TEMPLATE_STORE.get(template_id)
    if tpl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found.",
        )
    return tpl


# ---------------------------------------------------------------------------
# Preset endpoints
# ---------------------------------------------------------------------------


@router.get("/presets", response_model=List[Dict[str, str]])
async def list_presets() -> List[Dict[str, str]]:
    """List all built-in prompt presets."""
    return [
        {"name": name, "description": desc}
        for name, desc in _PRESETS.items()
    ]


@router.get("/presets/{preset_name}", response_model=PresetResponse)
async def get_preset(
    preset_name: str,
    date: Optional[str] = Query(None, description="Override the $date variable"),
    preferences: Optional[str] = Query(None, description="Override the $preferences variable"),
) -> PresetResponse:
    """Render a built-in preset and return the system prompt string."""
    if preset_name not in _PRESETS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_name}' not found.  Available: {list(_PRESETS)}",
        )

    if preset_name == "tool_agent":
        from string import Template
        tpl = Template(TOOL_AGENT_PROMPT)
        rendered = tpl.safe_substitute(
            date=date or datetime.utcnow().strftime("%Y-%m-%d"),
            available_tools="(none configured)",
        )
    else:
        pt = PromptTemplate.get_preset(preset_name)
        rendered = pt.render(
            **({"date": date} if date else {}),
            **({"preferences": preferences} if preferences else {}),
        )

    return PresetResponse(
        name=preset_name,
        rendered=rendered,
        description=_PRESETS[preset_name],
    )


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    include_public: bool = Query(True, description="Include public templates from other users"),
) -> List[TemplateResponse]:
    """List saved prompt templates."""
    templates = list(_TEMPLATE_STORE.values())

    if tag:
        templates = [t for t in templates if tag in t["tags"]]

    return [
        TemplateResponse(**{k: t[k] for k in TemplateResponse.model_fields})
        for t in templates
    ]


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateCreateRequest) -> TemplateResponse:
    """Create and persist a new prompt template."""
    template_id = str(uuid.uuid4())
    now = _now_iso()
    record: Dict[str, Any] = {
        "id": template_id,
        "name": body.name,
        "description": body.description,
        "template": body.template,
        "tags": body.tags,
        "is_public": body.is_public,
        "created_at": now,
        "updated_at": now,
    }
    _TEMPLATE_STORE[template_id] = record
    return TemplateResponse(**record)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str) -> TemplateResponse:
    """Retrieve a saved prompt template by ID."""
    record = _require_template(template_id)
    return TemplateResponse(**record)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
) -> TemplateResponse:
    """Update fields of an existing prompt template."""
    record = _require_template(template_id)

    updates = body.model_dump(exclude_unset=True)
    record.update(updates)
    record["updated_at"] = _now_iso()
    _TEMPLATE_STORE[template_id] = record

    return TemplateResponse(**record)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str) -> None:
    """Delete a prompt template."""
    _require_template(template_id)
    del _TEMPLATE_STORE[template_id]


@router.post("/{template_id}/render", response_model=RenderResponse)
async def render_template(
    template_id: str,
    body: RenderRequest,
) -> RenderResponse:
    """Render a saved template with the provided variable substitutions.

    Variable placeholders in the template string use Python's ``string.Template``
    syntax: ``$variable`` or ``${variable}``.
    """
    record = _require_template(template_id)

    pt = PromptTemplate(template=record["template"], name=record["name"])
    rendered = pt.render(**body.variables)

    return RenderResponse(
        rendered=rendered,
        template_id=template_id,
        variables_used=body.variables,
    )
