"""Deterministic Mermaid rendering from an ImplementationPlan."""

from __future__ import annotations

from agents.spec_schemas import APIEndpoint, Component, Entity, ImplementationPlan, TechStack
from utils.mermaid_render import render_container_mmd, render_erd_mmd, write_diagrams


def _plan(**kw) -> ImplementationPlan:
    defaults = dict(
        spec_id="todo-x",
        tech_stack=TechStack(language="python", database="sqlite"),
        components=[
            Component(name="cli", responsibility="parses commands and prints output",
                      owns_fr_ids=["FR-001"]),
            Component(name="store", responsibility="persists tasks to the database",
                      owns_fr_ids=["FR-002"]),
        ],
        api_contracts=[
            APIEndpoint(path="/tasks", method="POST", fr_ids=["FR-002"]),
        ],
        data_model=[
            Entity(name="Task", fields={"id": "int primary key", "title": "str"},
                   relationships=["has many Tag", "linked somehow to History"]),
            Entity(name="Tag", fields={"name": "str"}),
        ],
    )
    defaults.update(kw)
    return ImplementationPlan(**defaults)


def test_container_has_component_nodes_and_endpoint_edges():
    mmd = render_container_mmd(_plan())
    assert mmd.startswith("flowchart LR")
    assert 'C0["cli<br/>' in mmd
    assert 'C1["store<br/>' in mmd
    # endpoint routes to the component owning FR-002, not the first component
    assert 'client -->|"POST /tasks"| C1' in mmd
    assert 'db[("sqlite")]' in mmd


def test_container_without_database_has_no_db_node():
    p = _plan(tech_stack=TechStack(language="python"))
    assert "db[(" not in render_container_mmd(p)


def test_endpoint_without_fr_match_falls_back_to_first_component():
    p = _plan(api_contracts=[APIEndpoint(path="/misc", method="GET", fr_ids=["FR-099"])])
    assert 'client -->|"GET /misc"| C0' in render_container_mmd(p)


def test_erd_typed_fields_and_cardinality():
    mmd = render_erd_mmd(_plan())
    assert mmd.startswith("erDiagram")
    assert "int id" in mmd
    assert "str title" in mmd
    assert 'Task ||--o{ Tag : "has many Tag"' in mmd


def test_erd_unparseable_relationship_becomes_comment():
    mmd = render_erd_mmd(_plan())
    assert "%% Task: linked somehow to History" in mmd


def test_rendering_is_deterministic():
    p = _plan()
    assert render_container_mmd(p) == render_container_mmd(p)
    assert render_erd_mmd(p) == render_erd_mmd(p)


def test_write_diagrams_creates_files(tmp_path):
    paths = write_diagrams(tmp_path, _plan())
    assert [p.name for p in paths] == ["container.mmd", "erd.mmd"]
    assert all(p.exists() for p in paths)
    # no data model -> no erd.mmd
    p2 = _plan(data_model=[])
    paths2 = write_diagrams(tmp_path / "other", p2)
    assert [p.name for p in paths2] == ["container.mmd"]
