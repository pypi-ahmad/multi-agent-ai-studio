from __future__ import annotations

import json
from datetime import UTC, datetime
from time import perf_counter
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import AgentRun, Chat, ChatMessage, RunStatus, TraceRecord, User
from ai_studio.schemas.chat import ChatCreate, ChatMessageCreate, ChatMessageRead, ChatRead
from ai_studio.state import get_app_state

router = APIRouter(prefix="/chat", tags=["chat"])


def _estimate_tokens(text: str) -> int:
    return max(len(text) // 4, 1)


def _chunk_text(text: str, chunk_size: int = 80) -> list[str]:
    if not text:
        return [""]
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]


@router.get("", response_model=list[ChatRead])
async def list_chats(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("chat.list")),
) -> list[ChatRead]:
    result = await session.execute(select(Chat).where(Chat.owner_id == user.id).order_by(Chat.updated_at.desc()))
    return [ChatRead.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ChatCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("chat.create")),
) -> ChatRead:
    chat = Chat(owner_id=user.id, title=payload.title)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="chat.create",
        target_type="chat",
        target_id=chat.id,
        details={"title": chat.title},
        commit=True,
    )
    return ChatRead.model_validate(chat)


@router.get("/{chat_id}/messages", response_model=list[ChatMessageRead])
async def list_messages(
    chat_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("chat.messages.list")),
) -> list[ChatMessageRead]:
    chat = await session.execute(select(Chat).where(Chat.id == chat_id, Chat.owner_id == user.id))
    if not chat.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    result = await session.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at.asc())
    )
    return [ChatMessageRead.model_validate(item) for item in result.scalars().all()]


@router.post("/{chat_id}/messages", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    chat_id: str,
    payload: ChatMessageCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("chat.messages.create")),
) -> ChatMessageRead:
    result = await session.execute(select(Chat).where(Chat.id == chat_id, Chat.owner_id == user.id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    app_state = get_app_state()
    runtime = app_state.supervisor_runtime

    run = AgentRun(
        owner_id=user.id,
        status=RunStatus.QUEUED,
        input_payload={"prompt": payload.content, "chat_id": chat_id},
    )
    user_message = ChatMessage(chat_id=chat_id, role="user", content=payload.content)
    session.add(run)
    session.add(user_message)
    await session.commit()
    await session.refresh(run)

    start = perf_counter()
    try:
        run.status = RunStatus.RUNNING
        await session.commit()
        outcome = await runtime.run_with_trace(payload.content)
        elapsed_ms = round((perf_counter() - start) * 1000, 2)

        run.status = RunStatus.COMPLETED
        run.output_payload = {
            "response": outcome["response"],
            "plan": outcome["plan"],
            "critique": outcome["critique"],
        }
        run.model_usage = outcome["metadata"]
        run.error_message = ""

        assistant_message = ChatMessage(
            chat_id=chat_id,
            role="assistant",
            content=outcome["response"],
            citations=[],
            token_usage={
                "prompt_tokens": _estimate_tokens(payload.content),
                "completion_tokens": _estimate_tokens(outcome["response"]),
                "latency_ms": elapsed_ms,
                "metadata": outcome["metadata"],
                "critique": outcome["critique"],
                "run_id": run.id,
                "trace_id": outcome["trace_id"],
            },
        )
        trace = TraceRecord(
            run_id=run.id,
            trace_id=outcome["trace_id"],
            span_count=len(outcome["timeline"]),
            meta={
                "timeline": outcome["timeline"],
                "chat_id": chat_id,
                "prompt_preview": payload.content[:200],
                "response_preview": outcome["response"][:400],
            },
        )

        chat.updated_at = datetime.now(tz=UTC)
        session.add(assistant_message)
        session.add(trace)
        await session.commit()
        await append_audit_log(
            session,
            actor_user_id=user.id,
            action="chat.run.complete",
            target_type="run",
            target_id=run.id,
            details={"chat_id": chat_id, "trace_id": outcome["trace_id"]},
            commit=True,
        )
        await session.refresh(assistant_message)
        return ChatMessageRead.model_validate(assistant_message)
    except Exception as exc:  # noqa: BLE001
        run.status = RunStatus.FAILED
        run.error_message = repr(exc)
        await session.commit()
        await append_audit_log(
            session,
            actor_user_id=user.id,
            action="chat.run.failed",
            target_type="run",
            target_id=run.id,
            details={"chat_id": chat_id, "error": repr(exc)},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=repr(exc)) from exc


@router.get("/{chat_id}/stream")
async def stream_chat(
    chat_id: str,
    prompt: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("chat.stream")),
) -> StreamingResponse:
    result = await session.execute(select(Chat).where(Chat.id == chat_id, Chat.owner_id == user.id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    app_state = get_app_state()
    runtime = app_state.supervisor_runtime

    run = AgentRun(
        owner_id=user.id,
        status=RunStatus.QUEUED,
        input_payload={"prompt": prompt, "chat_id": chat_id, "stream": True},
    )
    user_message = ChatMessage(chat_id=chat_id, role="user", content=prompt)
    session.add(run)
    session.add(user_message)
    await session.commit()
    await session.refresh(run)

    async def event_stream() -> AsyncIterator[str]:
        stage_timeline: list[dict[str, object]] = []
        start = perf_counter()
        final_payload: dict[str, object] | None = None

        try:
            run.status = RunStatus.RUNNING
            await session.commit()
            yield "event:meta\ndata:" + json.dumps({"run_id": run.id}) + "\n\n"

            async for event in runtime.stream_events(prompt):
                if event["event"] == "stage" and event["status"] == "complete":
                    stage_timeline.append(
                        {
                            "stage": event.get("stage"),
                            "latency_ms": event.get("latency_ms"),
                            "model": event.get("model", ""),
                        }
                    )
                if event["event"] == "final":
                    final_payload = event
                    response_text = str(event.get("response", ""))
                    for chunk in _chunk_text(response_text):
                        safe_chunk = chunk.replace("\n", "\\n")
                        yield f"data:{safe_chunk}\n\n"
                    continue

                safe_event = json.dumps(event)
                yield f"event:stage\ndata:{safe_event}\n\n"

            if final_payload is None:
                raise RuntimeError("Supervisor stream finished without final payload")

            response_text = str(final_payload.get("response", ""))
            critique_text = str(final_payload.get("critique", ""))
            metadata_obj = final_payload.get("metadata", {})
            metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
            trace_id = str(final_payload.get("trace_id", metadata.get("trace_id", "")))
            elapsed_ms = round((perf_counter() - start) * 1000, 2)

            run.status = RunStatus.COMPLETED
            run.output_payload = {
                "response": response_text,
                "plan": str(final_payload.get("plan", "")),
                "critique": critique_text,
            }
            run.model_usage = metadata
            run.error_message = ""

            assistant_message = ChatMessage(
                chat_id=chat_id,
                role="assistant",
                content=response_text,
                citations=[],
                token_usage={
                    "prompt_tokens": _estimate_tokens(prompt),
                    "completion_tokens": _estimate_tokens(response_text),
                    "latency_ms": elapsed_ms,
                    "metadata": metadata,
                    "critique": critique_text,
                    "run_id": run.id,
                    "trace_id": trace_id,
                },
            )
            trace = TraceRecord(
                run_id=run.id,
                trace_id=trace_id,
                span_count=len(stage_timeline),
                meta={
                    "timeline": stage_timeline,
                    "chat_id": chat_id,
                    "prompt_preview": prompt[:200],
                    "response_preview": response_text[:400],
                },
            )
            chat.updated_at = datetime.now(tz=UTC)
            session.add(assistant_message)
            session.add(trace)
            await session.commit()
            yield "event:end\ndata:done\n\n"
        except Exception as exc:  # noqa: BLE001
            run.status = RunStatus.FAILED
            run.error_message = repr(exc)
            await session.commit()
            yield "event:error\ndata:" + json.dumps({"error": repr(exc)}) + "\n\n"
            yield "event:end\ndata:done\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
