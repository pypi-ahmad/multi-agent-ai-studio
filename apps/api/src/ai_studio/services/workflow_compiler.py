from __future__ import annotations

from dataclasses import dataclass

from ai_studio.schemas.workflow import WorkflowSpec


@dataclass(slots=True)
class CompiledWorkflow:
    node_count: int
    edge_count: int
    entrypoint: str
    reachable_node_count: int
    warnings: list[str]


class WorkflowCompiler:
    """Validate and compile WorkflowSpec into runtime-ready contract."""

    def compile(self, spec: WorkflowSpec) -> CompiledWorkflow:
        if not spec.nodes:
            raise ValueError("Workflow requires at least one node")

        node_ids = [node.id for node in spec.nodes]
        duplicates = {node_id for node_id in node_ids if node_ids.count(node_id) > 1}
        if duplicates:
            duplicate_text = ", ".join(sorted(duplicates))
            raise ValueError(f"Workflow has duplicate node ids: {duplicate_text}")

        node_map = {node.id: node for node in spec.nodes}
        if spec.entrypoint not in node_ids:
            raise ValueError("Workflow entrypoint not present in nodes")

        warnings: list[str] = []
        for edge in spec.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                raise ValueError("Workflow edge references unknown node")
            if edge.source == edge.target and node_map[edge.source].kind != "loop":
                raise ValueError("Only loop nodes can self-reference")
            if edge.condition and node_map[edge.source].kind not in {"condition", "supervisor"}:
                warnings.append(
                    f"Conditional edge '{edge.source}->{edge.target}' attached to non-condition node"
                )

        out_map: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for edge in spec.edges:
            out_map[edge.source].append(edge.target)

        visited: set[str] = set()
        stack = [spec.entrypoint]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            stack.extend(out_map.get(node_id, []))

        for node in spec.nodes:
            if node.kind == "human_approval" and len(out_map[node.id]) == 0:
                warnings.append(f"human_approval node '{node.id}' has no continuation edge")
            if node.kind == "checkpoint" and len(out_map[node.id]) > 1:
                warnings.append(f"checkpoint node '{node.id}' has multiple continuation edges")

        unreachable = sorted(node_id for node_id in node_ids if node_id not in visited)
        if unreachable:
            warnings.append("Unreachable nodes: " + ", ".join(unreachable))

        return CompiledWorkflow(
            node_count=len(spec.nodes),
            edge_count=len(spec.edges),
            entrypoint=spec.entrypoint,
            reachable_node_count=len(visited),
            warnings=warnings,
        )
