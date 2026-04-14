import pytest
from src.model.prompt_templates import template_registry, TemplateRenderError


def test_incident_response_v1_rendering():
    # 1. Fetch template from registry
    template = template_registry.get("incident-response-v1")
    assert template is not None
    assert template.name == "incident-response-v1"

    # 2. Assert rendering works with valid input
    data = {
        "incident_id": "INC-001",
        "severity": "Critical",
        "description": "Database outage in production",
        "timeline": "2026-04-13T22:00:00: Outage detected, 2026-04-13T22:05:00: Engineering notified",
    }
    rendered = template.render(**data)
    assert "INC-001" in rendered
    assert "Critical" in rendered
    assert "Database outage in production" in rendered
    assert "Immediate Actions" in rendered
    assert "Containment Strategy" in rendered


def test_incident_response_v1_missing_variable():
    # 3. Assert TemplateRenderError on missing required variables
    template = template_registry.get("incident-response-v1")
    with pytest.raises(TemplateRenderError):
        template.render(incident_id="INC-001")  # missing other required vars
