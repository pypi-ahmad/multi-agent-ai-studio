from __future__ import annotations

import pytest
from ai_studio.schemas.workflow import WorkflowEdge, WorkflowNode, WorkflowSpec
from ai_studio.services.workflow_compiler import WorkflowCompiler


def test_workflow_compiler_accepts_valid_spec() -> None:
    compiler = WorkflowCompiler()
    spec = WorkflowSpec(
        version=1,
        entrypoint="supervisor",
        nodes=[
            WorkflowNode(id="supervisor", kind="supervisor", config={}),
            WorkflowNode(id="planner", kind="agent", config={}),
        ],
        edges=[WorkflowEdge(source="supervisor", target="planner")],
    )

    compiled = compiler.compile(spec)

    assert compiled.node_count == 2
    assert compiled.edge_count == 1
    assert compiled.entrypoint == "supervisor"


def test_workflow_compiler_rejects_unknown_edge_node() -> None:
    compiler = WorkflowCompiler()
    spec = WorkflowSpec(
        version=1,
        entrypoint="supervisor",
        nodes=[WorkflowNode(id="supervisor", kind="supervisor", config={})],
        edges=[WorkflowEdge(source="supervisor", target="missing")],
    )

    with pytest.raises(ValueError, match="unknown node"):
        compiler.compile(spec)
