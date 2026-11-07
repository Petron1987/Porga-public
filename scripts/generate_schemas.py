"""Regenerate reviewable contracts from the actual runtime models."""

import json
from pathlib import Path

from porga import integration_protocols, project_protocols, protocols

destination = Path(__file__).resolve().parents[1] / "protocols"
destination.mkdir(exist_ok=True)
names = (
    "ProjectSpec",
    "AgentSpec",
    "TaskSpec",
    "Artifact",
    "PermissionPolicy",
    "EvaluationGate",
    "EvolutionProposal",
    "Plan",
    "ResearchReport",
    "QAReview",
    "RunSpec",
)
for name in names:
    model = getattr(protocols, name)
    (destination / f"{name}.schema.json").write_text(
        json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
project_names = (
    "CharterDraft",
    "CapabilitySpec",
    "AgentDefinition",
    "TaskGraph",
    "OrganizationRevision",
)
for name in project_names:
    model = getattr(project_protocols, name)
    (destination / f"{name}.schema.json").write_text(
        json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
integration_names = ("ExternalProjectSpec", "ExternalBinding", "RunOptions")
for name in integration_names:
    model = getattr(integration_protocols, name)
    (destination / f"{name}.schema.json").write_text(
        json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
count = len(names) + len(project_names) + len(integration_names)
print(f"Generated {count} schemas in {destination.name}/")
