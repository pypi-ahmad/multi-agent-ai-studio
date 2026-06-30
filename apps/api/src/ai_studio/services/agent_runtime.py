from __future__ import annotations

from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph
from opentelemetry import trace

from ai_studio.services.model_router import ModelRouter, TaskType
from ai_studio.services.ollama_client import OllamaClient

_tracer = trace.get_tracer(__name__)


class AgentState(TypedDict):
    prompt: str
    plan: str
    decomposition: str
    task_type: str
    specialist_output: str
    response: str
    critique: str
    metadata: dict[str, Any]


class SupervisorRuntime:
    """LangGraph supervisor runtime with planner, decomposer, routing, specialists, reviewer, critic."""

    def __init__(self, model_router: ModelRouter, ollama_client: OllamaClient) -> None:
        self._model_router = model_router
        self._ollama_client = ollama_client
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("planner", self._planner)
        graph.add_node("decomposer", self._decomposer)
        graph.add_node("router", self._router)
        graph.add_node("specialist", self._specialist)
        graph.add_node("reviewer", self._reviewer)
        graph.add_node("critic", self._critic)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "decomposer")
        graph.add_edge("decomposer", "router")
        graph.add_edge("router", "specialist")
        graph.add_edge("specialist", "reviewer")
        graph.add_edge("reviewer", "critic")
        graph.add_edge("critic", END)
        return graph.compile()

    @staticmethod
    def _route_task_type(prompt: str) -> str:
        text = prompt.lower()
        routing_rules = [
            ("ocr", ["ocr", "scan", "handwritten", "pdf image"]),
            ("vision", ["image", "chart", "diagram", "screenshot", "visual"]),
            ("sql", ["sql", "query", "postgres", "table", "database"]),
            ("coding", ["code", "python", "bug", "debug", "refactor", "function", "api"]),
            ("rag", ["retrieve", "rag", "citation", "knowledge base", "document"]),
            ("memory", ["remember", "memory", "recall", "context"]),
            ("data", ["csv", "excel", "dataset", "statistics", "analysis"]),
            ("research", ["research", "compare", "summarize", "references"]),
            ("translation", ["translate", "translation", "multilingual"]),
        ]

        for task_type, hints in routing_rules:
            if any(hint in text for hint in hints):
                return task_type
        return "general"

    async def _planner(self, state: AgentState) -> AgentState:
        model = await self._model_router.pick("reasoning")
        plan = await self._ollama_client.generate(
            model,
            "Create concise execution plan for task:\n" + state["prompt"],
            options={"num_predict": 140, "temperature": 0.2},
        )
        state["plan"] = plan
        state["metadata"]["planner_model"] = model
        return state

    async def _decomposer(self, state: AgentState) -> AgentState:
        model = await self._model_router.pick("reasoning")
        decomposition = await self._ollama_client.generate(
            model,
            "Break task into execution subtasks with dependencies and validation checks.\n"
            f"Task: {state['prompt']}\n"
            f"Plan: {state['plan']}",
            options={"num_predict": 180, "temperature": 0.15},
        )
        state["decomposition"] = decomposition
        state["metadata"]["decomposer_model"] = model
        return state

    async def _router(self, state: AgentState) -> AgentState:
        task_type = self._route_task_type(state["prompt"])
        state["task_type"] = task_type
        state["metadata"]["task_type"] = task_type
        state["metadata"]["router_model"] = "rule-router"
        return state

    async def _specialist(self, state: AgentState) -> AgentState:
        task_type = state["task_type"]
        capability_map: dict[str, TaskType] = {
            "coding": "coding",
            "ocr": "ocr",
            "vision": "vision",
            "translation": "translation",
            "research": "reasoning",
            "data": "reasoning",
            "sql": "coding",
            "rag": "reasoning",
            "memory": "summarization",
            "general": "chat",
        }
        capability: TaskType = capability_map.get(task_type, "chat")
        model = await self._model_router.pick(capability)

        role_prompt_map = {
            "coding": "You are Coding Agent. Produce implementation guidance, bug fixes, and architecture notes.",
            "ocr": "You are OCR Agent. Explain OCR extraction strategy and confidence/risk handling.",
            "vision": "You are Vision Agent. Analyze visual artifacts and extract structured insight.",
            "sql": "You are SQL Agent. Produce safe SQL strategy, query plan hints, and optimization notes.",
            "rag": "You are RAG Agent. Focus ingestion, retrieval, reranking, and citation grounding.",
            "memory": "You are Memory Agent. Focus memory selection, retention, summarization, and forgetting rules.",
            "research": "You are Research Agent. Produce concise synthesis with assumptions and validation checks.",
            "data": "You are Data Agent. Focus tabular processing, stats, data quality checks, and outputs.",
            "translation": "You are Translation Agent. Preserve meaning and technical terms exactly.",
            "general": "You are Executor Agent. Deliver precise actionable output.",
        }

        specialist_output = await self._ollama_client.generate(
            model,
            f"{role_prompt_map.get(task_type, role_prompt_map['general'])}\n"
            f"Task: {state['prompt']}\n"
            f"Plan: {state['plan']}\n"
            f"Decomposition: {state['decomposition']}",
            options={"num_predict": 260, "temperature": 0.2},
        )
        state["specialist_output"] = specialist_output
        state["metadata"]["specialist_model"] = model
        return state

    async def _reviewer(self, state: AgentState) -> AgentState:
        model = await self._model_router.pick("summarization")
        feedback = await self._ollama_client.generate(
            model,
            "Review specialist output for correctness/completeness and list concrete fixes.\n"
            f"Task: {state['prompt']}\n"
            f"Output: {state['specialist_output']}\n"
            "Respond with max 6 bullet points.",
            options={"num_predict": 160, "temperature": 0.1},
        )
        response = await self._ollama_client.generate(
            model,
            "Generate final concise result from specialist output and review notes.\n"
            f"Task: {state['prompt']}\n"
            f"Specialist Output: {state['specialist_output']}\n"
            f"Review Notes: {feedback}",
            options={"num_predict": 280, "temperature": 0.15},
        )
        state["response"] = response
        state["metadata"]["reviewer_model"] = model
        state["metadata"]["reviewer_feedback"] = feedback
        return state

    async def _critic(self, state: AgentState) -> AgentState:
        model = await self._model_router.pick("reasoning")
        critique = await self._ollama_client.generate(
            model,
            "Challenge assumptions and suggest improvements.\n"
            f"Task: {state['prompt']}\n"
            f"Plan: {state['plan']}\n"
            f"Final Answer: {state['response']}\n"
            "Respond with max 5 bullet points.",
            options={"num_predict": 150, "temperature": 0.1},
        )
        state["critique"] = critique
        state["metadata"]["critic_model"] = model
        return state

    async def run(self, prompt: str) -> dict[str, Any]:
        run = await self.run_with_trace(prompt)
        return {
            "plan": run["plan"],
            "response": run["response"],
            "critique": run["critique"],
            "metadata": run["metadata"],
        }

    async def run_with_trace(self, prompt: str) -> dict[str, Any]:
        state: AgentState = {
            "prompt": prompt,
            "plan": "",
            "decomposition": "",
            "task_type": "general",
            "specialist_output": "",
            "response": "",
            "critique": "",
            "metadata": {},
        }
        trace_id = str(uuid4())
        timeline: list[dict[str, Any]] = []

        stages = [
            ("planner", self._planner),
            ("decomposer", self._decomposer),
            ("router", self._router),
            ("specialist", self._specialist),
            ("reviewer", self._reviewer),
            ("critic", self._critic),
        ]

        for stage_name, handler in stages:
            started = perf_counter()
            with _tracer.start_as_current_span(f"agent.stage.{stage_name}") as span:
                span.set_attribute("ai_studio.trace_id", trace_id)
                span.set_attribute("ai_studio.stage", stage_name)
                span.set_attribute("ai_studio.task_type", state.get("task_type", "general"))
                state = await handler(state)
                stage_model = state["metadata"].get(f"{stage_name}_model") or state["metadata"].get("specialist_model", "")
                span.set_attribute("ai_studio.model", str(stage_model))

            latency_ms = round((perf_counter() - started) * 1000, 2)
            timeline.append(
                {
                    "stage": stage_name,
                    "latency_ms": latency_ms,
                    "model": state["metadata"].get(f"{stage_name}_model", ""),
                }
            )

        state["metadata"]["trace_id"] = trace_id
        state["metadata"]["timeline"] = timeline
        state["metadata"]["task_type"] = state["task_type"]

        return {
            "trace_id": trace_id,
            "plan": state["plan"],
            "response": state["response"],
            "critique": state["critique"],
            "metadata": state["metadata"],
            "timeline": timeline,
        }

    async def stream_events(self, prompt: str) -> AsyncIterator[dict[str, Any]]:
        state: AgentState = {
            "prompt": prompt,
            "plan": "",
            "decomposition": "",
            "task_type": "general",
            "specialist_output": "",
            "response": "",
            "critique": "",
            "metadata": {},
        }
        trace_id = str(uuid4())
        timeline: list[dict[str, Any]] = []

        stages = [
            ("planner", self._planner),
            ("decomposer", self._decomposer),
            ("router", self._router),
            ("specialist", self._specialist),
            ("reviewer", self._reviewer),
            ("critic", self._critic),
        ]

        for stage_name, handler in stages:
            yield {"event": "stage", "status": "start", "stage": stage_name, "trace_id": trace_id}
            started = perf_counter()
            with _tracer.start_as_current_span(f"agent.stream.stage.{stage_name}") as span:
                span.set_attribute("ai_studio.trace_id", trace_id)
                span.set_attribute("ai_studio.stage", stage_name)
                state = await handler(state)
                span.set_attribute("ai_studio.model", str(state["metadata"].get(f"{stage_name}_model", "")))

            latency_ms = round((perf_counter() - started) * 1000, 2)

            stage_payload = {
                "event": "stage",
                "status": "complete",
                "stage": stage_name,
                "trace_id": trace_id,
                "latency_ms": latency_ms,
                "model": state["metadata"].get(f"{stage_name}_model", ""),
            }
            if stage_name == "planner":
                stage_payload["output"] = state["plan"]
            elif stage_name == "decomposer":
                stage_payload["output"] = state["decomposition"]
            elif stage_name == "specialist":
                stage_payload["output"] = state["specialist_output"]
            elif stage_name == "reviewer":
                stage_payload["output"] = state["response"]
            elif stage_name == "critic":
                stage_payload["output"] = state["critique"]

            timeline.append(
                {
                    "stage": stage_name,
                    "latency_ms": latency_ms,
                    "model": stage_payload.get("model", ""),
                }
            )
            yield stage_payload

        state["metadata"]["trace_id"] = trace_id
        state["metadata"]["timeline"] = timeline
        state["metadata"]["task_type"] = state["task_type"]

        yield {
            "event": "final",
            "trace_id": trace_id,
            "plan": state["plan"],
            "response": state["response"],
            "critique": state["critique"],
            "metadata": state["metadata"],
        }
