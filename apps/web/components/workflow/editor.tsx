"use client";

import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Connection,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  addEdge,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import { apiRequest } from "@/lib/api";

type WorkflowNodePayload = {
  id: string;
  kind: "supervisor" | "agent" | "tool" | "condition" | "loop" | "human_approval" | "checkpoint";
  config: Record<string, unknown>;
};

type WorkflowEdgePayload = {
  source: string;
  target: string;
  condition: string | null;
};

type WorkflowSpecPayload = {
  version: number;
  entrypoint: string;
  nodes: WorkflowNodePayload[];
  edges: WorkflowEdgePayload[];
};

type WorkflowRecord = {
  id: string;
  name: string;
  spec: WorkflowSpecPayload;
  updated_at: string;
};

type ValidationResult = {
  node_count: number;
  edge_count: number;
  entrypoint: string;
  reachable_node_count: number;
  warnings: string[];
};

const initialNodes: Node[] = [
  {
    id: "supervisor",
    type: "input",
    position: { x: 80, y: 60 },
    data: { label: "Supervisor" },
  },
  {
    id: "planner",
    position: { x: 360, y: 30 },
    data: { label: "Planner Agent" },
  },
  {
    id: "reviewer",
    position: { x: 360, y: 160 },
    data: { label: "Reviewer Agent" },
  },
  {
    id: "output",
    type: "output",
    position: { x: 660, y: 95 },
    data: { label: "Final Output" },
  },
];

const initialEdges: Edge[] = [
  { id: "e1", source: "supervisor", target: "planner", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e2", source: "planner", target: "reviewer", markerEnd: { type: MarkerType.ArrowClosed } },
  { id: "e3", source: "reviewer", target: "output", markerEnd: { type: MarkerType.ArrowClosed } },
];

function toReactFlowNodes(spec: WorkflowSpecPayload): Node[] {
  return spec.nodes.map((node, index) => {
    const configuredPosition = (node.config.position ?? null) as { x?: number; y?: number } | null;
    return {
      id: node.id,
      data: {
        label: String(node.config.label ?? node.id),
        kind: node.kind,
        config: node.config,
      },
      position: {
        x: typeof configuredPosition?.x === "number" ? configuredPosition.x : 80 + index * 220,
        y: typeof configuredPosition?.y === "number" ? configuredPosition.y : 80,
      },
    };
  });
}

function toReactFlowEdges(spec: WorkflowSpecPayload): Edge[] {
  return spec.edges.map((edge, index) => ({
    id: `e-${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    label: edge.condition ?? undefined,
    markerEnd: { type: MarkerType.ArrowClosed },
  }));
}

export function WorkflowEditor() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [json, setJson] = useState("");
  const [name, setName] = useState("Studio Workflow");
  const [workflows, setWorkflows] = useState<WorkflowRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const onConnect = (params: Edge | Connection) => setEdges((currentEdges) => addEdge(params, currentEdges));

  const loadWorkflows = async () => {
    try {
      const data = await apiRequest<WorkflowRecord[]>({ path: "/workflows" });
      setWorkflows(data);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    void loadWorkflows();
  }, []);

  const selectWorkflow = (workflow: WorkflowRecord) => {
    setSelectedId(workflow.id);
    setName(workflow.name);
    setNodes(toReactFlowNodes(workflow.spec));
    setEdges(toReactFlowEdges(workflow.spec));
    setValidation(null);
    setStatus("");
  };

  const spec = useMemo(
    () => ({
      version: 1,
      entrypoint: nodes[0]?.id || "supervisor",
      nodes: nodes.map((node) => {
        const nodeData = (node.data ?? {}) as { kind?: string; config?: Record<string, unknown>; label?: string };
        const configured = nodeData.config ?? {};
        return {
          id: node.id,
          kind: (nodeData.kind as WorkflowNodePayload["kind"]) || "agent",
          config: {
            ...configured,
            label: nodeData.label ?? node.id,
            position: node.position,
          },
        };
      }),
      edges: edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        condition: typeof edge.label === "string" ? edge.label : null,
      })),
    }),
    [nodes, edges],
  );

  const validateWorkflow = async () => {
    try {
      const result = await apiRequest<ValidationResult>({
        path: "/workflows/validate",
        method: "POST",
        body: { spec },
      });
      setValidation(result);
      setStatus("Workflow valid.");
      setError("");
    } catch (err) {
      setError((err as Error).message);
      setStatus("");
    }
  };

  const saveWorkflow = async () => {
    try {
      setStatus("Saving workflow...");
      if (selectedId) {
        await apiRequest({
          path: `/workflows/${selectedId}`,
          method: "PUT",
          body: { name, spec },
        });
      } else {
        const created = await apiRequest<WorkflowRecord>({
          path: "/workflows",
          method: "POST",
          body: { name, spec },
        });
        setSelectedId(created.id);
      }
      await loadWorkflows();
      setStatus("Workflow saved.");
      setError("");
    } catch (err) {
      setError((err as Error).message);
      setStatus("");
    }
  };

  const deleteWorkflow = async () => {
    if (!selectedId) return;
    try {
      await apiRequest({ path: `/workflows/${selectedId}`, method: "DELETE" });
      setSelectedId("");
      setName("Studio Workflow");
      setNodes(initialNodes);
      setEdges(initialEdges);
      setValidation(null);
      setStatus("Workflow deleted.");
      await loadWorkflows();
    } catch (err) {
      setError((err as Error).message);
      setStatus("");
    }
  };

  return (
    <section className="space-y-4">
      {error ? <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}
      {status ? <p className="rounded border border-border bg-background px-3 py-2 text-sm">{status}</p> : null}
      <div className="grid gap-3 lg:grid-cols-[1fr,280px]">
        <div className="space-y-2">
          <label className="text-xs text-foreground/70">Workflow Name</label>
          <input
            className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Workflow name"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs text-foreground/70">Saved Workflows</label>
          <select
            className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
            value={selectedId}
            onChange={(event) => {
              const id = event.target.value;
              setSelectedId(id);
              const target = workflows.find((item) => item.id === id);
              if (target) {
                selectWorkflow(target);
              }
            }}
          >
            <option value="">New workflow</option>
            {workflows.map((workflow) => (
              <option key={workflow.id} value={workflow.id}>
                {workflow.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="h-[520px] rounded-xl border border-border bg-card">
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} fitView>
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => setJson(JSON.stringify(spec, null, 2))}
          className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
        >
          Export WorkflowSpec JSON
        </button>
        <button type="button" onClick={validateWorkflow} className="rounded-lg border border-border px-4 py-2 text-sm">
          Validate
        </button>
        <button type="button" onClick={saveWorkflow} className="rounded-lg border border-border px-4 py-2 text-sm">
          Save
        </button>
        <button
          type="button"
          onClick={deleteWorkflow}
          disabled={!selectedId}
          className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300 disabled:opacity-50"
        >
          Delete
        </button>
      </div>
      {validation ? (
        <article className="rounded-xl border border-border bg-card p-4 text-xs">
          <p className="font-semibold">Validation</p>
          <p className="mt-1">
            Nodes: {validation.node_count} | Edges: {validation.edge_count} | Reachable: {validation.reachable_node_count}
          </p>
          {validation.warnings.length ? (
            <ul className="mt-2 list-disc pl-4 space-y-1">
              {validation.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-foreground/70">No compiler warnings.</p>
          )}
        </article>
      ) : null}
      {json ? (
        <pre className="rounded-xl border border-border bg-card p-4 text-xs overflow-auto max-h-64">{json}</pre>
      ) : null}
    </section>
  );
}
