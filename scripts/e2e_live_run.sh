#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8001/api/v1}"
API_ROOT="${BASE_URL%/api/v1}"
RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$ROOT_DIR/artifacts/e2e-live/$RUN_TS"
mkdir -p "$RUN_DIR/payloads"

api_call() {
  local method="$1"
  local path="$2"
  local expected="$3"
  local output_file="$4"
  shift 4

  local status
  status="$(curl -sS -o "$output_file" -w "%{http_code}" -X "$method" "${BASE_URL}${path}" "$@")"
  if [[ "$status" != "$expected" ]]; then
    echo "Request failed: $method $path (expected $expected, got $status)"
    cat "$output_file"
    exit 1
  fi
}

assert_jq() {
  local file="$1"
  shift
  if ! jq -e "$@" "$file" >/dev/null; then
    echo "Assertion failed: jq $* on $file"
    cat "$file"
    exit 1
  fi
}

echo "==> Preparing live E2E run directory: $RUN_DIR"
echo "==> Waiting for API readiness"
ready=0
for _ in {1..45}; do
  if curl -sS -f "${API_ROOT}/openapi.json" >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "API not ready at ${API_ROOT}"
  exit 1
fi

EMAIL="e2e_${RUN_TS,,}@example.com"
PASSWORD="StrongPass123!"
FULL_NAME="E2E Runner $RUN_TS"
CONFIRM_TOKEN="CONFIRM-DEVELOPMENT"
TOOL_ROOT="${TOOL_ROOT:-/app}"

echo "==> Auth register/login/refresh/me"
jq -n \
  --arg email "$EMAIL" \
  --arg password "$PASSWORD" \
  --arg full_name "$FULL_NAME" \
  '{email: $email, password: $password, full_name: $full_name}' > "$RUN_DIR/payloads/auth_register.json"
api_call POST "/auth/register" 200 "$RUN_DIR/auth_register.json" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/auth_register.json"
assert_jq "$RUN_DIR/auth_register.json" '.access_token | length > 40'
assert_jq "$RUN_DIR/auth_register.json" '.refresh_token | length > 40'

ACCESS_TOKEN="$(jq -r '.access_token' "$RUN_DIR/auth_register.json")"
REFRESH_TOKEN="$(jq -r '.refresh_token' "$RUN_DIR/auth_register.json")"

jq -n --arg email "$EMAIL" --arg password "$PASSWORD" '{email: $email, password: $password}' > "$RUN_DIR/payloads/auth_login.json"
api_call POST "/auth/login" 200 "$RUN_DIR/auth_login.json" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/auth_login.json"
assert_jq "$RUN_DIR/auth_login.json" '.access_token | length > 40'

api_call GET "/auth/me" 200 "$RUN_DIR/auth_me.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/auth_me.json" --arg email "$EMAIL" '.email == $email'
assert_jq "$RUN_DIR/auth_me.json" '.role == "owner"'

jq -n --arg refresh_token "$REFRESH_TOKEN" '{refresh_token: $refresh_token}' > "$RUN_DIR/payloads/auth_refresh.json"
api_call POST "/auth/refresh" 200 "$RUN_DIR/auth_refresh.json" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/auth_refresh.json"
ACCESS_TOKEN="$(jq -r '.access_token' "$RUN_DIR/auth_refresh.json")"
REFRESH_TOKEN="$(jq -r '.refresh_token' "$RUN_DIR/auth_refresh.json")"

echo "==> System + model routing"
api_call GET "/system/health" 200 "$RUN_DIR/system_health.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/system_health.json" '.services.ollama == "up"'

api_call GET "/system/models" 200 "$RUN_DIR/system_models.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/system_models.json" '.count > 0'

api_call POST "/models/refresh" 200 "$RUN_DIR/models_refresh.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/models_refresh.json" '.count > 0'

api_call GET "/models/snapshot" 200 "$RUN_DIR/models_snapshot.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/models_snapshot.json" '.count > 0'

ROUTING_MODEL="$(jq -r '.models[0].model_name' "$RUN_DIR/models_snapshot.json")"
jq -n --arg task "reasoning" --arg model_name "$ROUTING_MODEL" '{task: $task, model_name: $model_name}' > "$RUN_DIR/payloads/model_rule_set.json"
api_call POST "/models/routing-rules" 200 "$RUN_DIR/models_rule_set.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/model_rule_set.json"
assert_jq "$RUN_DIR/models_rule_set.json" --arg model "$ROUTING_MODEL" '.snapshot.custom_rules.reasoning == $model'

jq -n --arg task "reasoning" '{task: $task}' > "$RUN_DIR/payloads/model_rule_clear.json"
api_call DELETE "/models/routing-rules" 200 "$RUN_DIR/models_rule_clear.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/model_rule_clear.json"
assert_jq "$RUN_DIR/models_rule_clear.json" '.snapshot.custom_rules.reasoning == null'

echo "==> Agents + workflows"
jq -n \
  --arg name "E2E Agent $RUN_TS" \
  --arg description "Live E2E agent validation" \
  '{name: $name, description: $description, config: {persona: "validator", safety: "strict"}, is_template: false}' > "$RUN_DIR/payloads/agent_create.json"
api_call POST "/agents" 201 "$RUN_DIR/agent_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/agent_create.json"
assert_jq "$RUN_DIR/agent_create.json" '.id | length > 20'
AGENT_ID="$(jq -r '.id' "$RUN_DIR/agent_create.json")"

api_call GET "/agents" 200 "$RUN_DIR/agents_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/agents_list.json" --arg agent_id "$AGENT_ID" 'map(select(.id == $agent_id)) | length == 1'

jq -n \
  --arg name "E2E Workflow $RUN_TS" \
  '{
    name: $name,
    spec: {
      version: 1,
      entrypoint: "supervisor_1",
      nodes: [
        {id: "supervisor_1", kind: "supervisor", config: {mode: "tool-calling"}},
        {id: "agent_1", kind: "agent", config: {type: "coding"}}
      ],
      edges: [
        {source: "supervisor_1", target: "agent_1", condition: null}
      ]
    }
  }' > "$RUN_DIR/payloads/workflow_create.json"
api_call POST "/workflows" 201 "$RUN_DIR/workflow_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/workflow_create.json"
WORKFLOW_ID="$(jq -r '.id' "$RUN_DIR/workflow_create.json")"
assert_jq "$RUN_DIR/workflow_create.json" '.spec.nodes | length >= 2'

api_call GET "/workflows" 200 "$RUN_DIR/workflows_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/workflows_list.json" --arg workflow_id "$WORKFLOW_ID" 'map(select(.id == $workflow_id)) | length == 1'

echo "==> Chat orchestration (sync + streaming)"
jq -n --arg title "E2E Chat $RUN_TS" '{title: $title}' > "$RUN_DIR/payloads/chat_create.json"
api_call POST "/chat" 201 "$RUN_DIR/chat_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/chat_create.json"
CHAT_ID="$(jq -r '.id' "$RUN_DIR/chat_create.json")"

jq -n --arg content "Design a 3-step plan to add JWT auth tests in this codebase." '{content: $content, context: {mode: "e2e"}}' > "$RUN_DIR/payloads/chat_message.json"
api_call POST "/chat/${CHAT_ID}/messages" 201 "$RUN_DIR/chat_message_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/chat_message.json"
assert_jq "$RUN_DIR/chat_message_create.json" '.role == "assistant"'
assert_jq "$RUN_DIR/chat_message_create.json" '.token_usage.trace_id | length > 10'
TRACE_ID_FROM_CHAT="$(jq -r '.token_usage.trace_id' "$RUN_DIR/chat_message_create.json")"

api_call GET "/chat/${CHAT_ID}/messages" 200 "$RUN_DIR/chat_messages_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/chat_messages_list.json" 'length >= 2'

STREAM_STATUS="$(curl -sS -N --get -o "$RUN_DIR/chat_stream.sse" -w "%{http_code}" \
  "${BASE_URL}/chat/${CHAT_ID}/stream" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "prompt=Summarize why model routing matters in one paragraph.")"
if [[ "$STREAM_STATUS" != "200" ]]; then
  echo "Streaming request failed with status $STREAM_STATUS"
  cat "$RUN_DIR/chat_stream.sse"
  exit 1
fi
if ! rg -q "event:end" "$RUN_DIR/chat_stream.sse"; then
  echo "Streaming output missing event:end"
  cat "$RUN_DIR/chat_stream.sse"
  exit 1
fi

api_call GET "/runs" 200 "$RUN_DIR/runs_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/runs_list.json" 'length >= 2'

echo "==> Trace inspection"
api_call GET "/traces" 200 "$RUN_DIR/traces_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/traces_list.json" 'length >= 1'
TRACE_ROW_ID="$(jq -r '.[] | select(.trace_id == "'"$TRACE_ID_FROM_CHAT"'") | .id' "$RUN_DIR/traces_list.json" | head -n1)"
if [[ -z "$TRACE_ROW_ID" ]]; then
  TRACE_ROW_ID="$(jq -r '.[0].id' "$RUN_DIR/traces_list.json")"
fi

api_call GET "/traces/${TRACE_ROW_ID}" 200 "$RUN_DIR/trace_get.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/trace_get.json" '.span_count >= 1'

api_call GET "/traces/${TRACE_ROW_ID}/timeline" 200 "$RUN_DIR/trace_timeline.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/trace_timeline.json" 'length >= 1'

echo "==> Memory lifecycle"
jq -n \
  --arg scope "project:e2e:$RUN_TS" \
  --arg content "User prefers production-grade architecture with strict validation loops." \
  '{memory_type: "project", scope: $scope, content: $content, salience: 0.81, ttl_days: 30, metadata: {tag: "e2e"}}' > "$RUN_DIR/payloads/memory_create.json"
api_call POST "/memory" 201 "$RUN_DIR/memory_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/memory_create.json"
MEMORY_ID="$(jq -r '.id' "$RUN_DIR/memory_create.json")"

jq -n '{content: "Updated memory: prioritize deterministic infra.", salience: 0.86, metadata: {tag: "e2e-updated"}}' > "$RUN_DIR/payloads/memory_patch.json"
api_call PATCH "/memory/${MEMORY_ID}" 200 "$RUN_DIR/memory_patch.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/memory_patch.json"
assert_jq "$RUN_DIR/memory_patch.json" '.salience >= 0.86'

api_call GET "/memory" 200 "$RUN_DIR/memory_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/memory_list.json" --arg memory_id "$MEMORY_ID" 'map(select(.id == $memory_id)) | length == 1'

jq -n --arg scope "project:e2e:$RUN_TS" '{scope: $scope, memory_type: "project", limit: 20}' > "$RUN_DIR/payloads/memory_summary.json"
api_call POST "/memory/summary" 200 "$RUN_DIR/memory_summary_response.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/memory_summary.json"
assert_jq "$RUN_DIR/memory_summary_response.json" '.count >= 1'

jq -n --arg scope "project:e2e:$RUN_TS" '{scope: $scope, min_salience: 0.95}' > "$RUN_DIR/payloads/memory_forget.json"
api_call POST "/memory/forget" 200 "$RUN_DIR/memory_forget_response.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/memory_forget.json"
assert_jq "$RUN_DIR/memory_forget_response.json" '.deleted >= 0'

echo "==> RAG ingestion + retrieval"
api_call GET "/rag/connectors" 200 "$RUN_DIR/rag_connectors.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/rag_connectors.json" '.connectors | length >= 2'

RAG_FILE="$RUN_DIR/rag_sample.txt"
cat > "$RAG_FILE" <<'TXT'
Multi-Agent AI Studio validation note.
The deployment uses Ollama for local inference and Qdrant for vector retrieval.
The target hardware is NVIDIA RTX 4060 Laptop GPU with 8 GB VRAM.
TXT

jq -n \
  --arg name "E2E RAG Doc $RUN_TS" \
  --arg source_uri "file://$RAG_FILE" \
  '{name: $name, mime_type: "text/plain", source_uri: $source_uri, metadata: {suite: "e2e"}}' > "$RUN_DIR/payloads/rag_document_create.json"
api_call POST "/rag/documents" 201 "$RUN_DIR/rag_document_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/rag_document_create.json"
DOCUMENT_ID="$(jq -r '.id' "$RUN_DIR/rag_document_create.json")"

RAG_INGEST_STATUS="$(curl -sS -o "$RUN_DIR/rag_ingest_file.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/rag/documents/${DOCUMENT_ID}/ingest" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@${RAG_FILE};type=text/plain")"
if [[ "$RAG_INGEST_STATUS" != "202" ]]; then
  echo "RAG file ingest failed with status $RAG_INGEST_STATUS"
  cat "$RUN_DIR/rag_ingest_file.json"
  exit 1
fi
assert_jq "$RUN_DIR/rag_ingest_file.json" '.chunks_indexed >= 1'

jq -n \
  '{query: "Which GPU and VRAM does this platform target?", top_k: 3, mode: "hybrid", rerank: true, candidate_pool: 20, filters: {}}' > "$RUN_DIR/payloads/rag_retrieve.json"
api_call POST "/rag/retrieve" 200 "$RUN_DIR/rag_retrieve.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/rag_retrieve.json"
assert_jq "$RUN_DIR/rag_retrieve.json" '.hits | length >= 1'

api_call GET "/rag/documents" 200 "$RUN_DIR/rag_documents_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/rag_documents_list.json" --arg document_id "$DOCUMENT_ID" 'map(select(.id == $document_id)) | length == 1'

echo "==> Evaluation + experiments + settings + logs"
jq -n \
  '{name: "E2E Eval", dataset_ref: "artifacts/e2e/live", metric_scores: {answer_quality: 0.92, groundedness: 0.88, latency: 0.73}, notes: "Live validation run"}' > "$RUN_DIR/payloads/evaluation_create.json"
api_call POST "/evaluation" 201 "$RUN_DIR/evaluation_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/evaluation_create.json"
EVALUATION_ID="$(jq -r '.id' "$RUN_DIR/evaluation_create.json")"

api_call GET "/evaluation/summary" 200 "$RUN_DIR/evaluation_summary.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/evaluation_summary.json" '.count >= 1'

api_call POST "/evaluation/estimate-cost?prompt_tokens=1200&completion_tokens=420&latency_ms=891.2&gpu_seconds=2.9&cpu_seconds=0.8" 200 "$RUN_DIR/evaluation_cost_estimate.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/evaluation_cost_estimate.json" '.cloud_equivalent_usd > 0'

jq -n '{name: "E2E Experiment", config: {model: "auto", mode: "full"}, results: {accuracy: 0.91}}' > "$RUN_DIR/payloads/experiment_create.json"
api_call POST "/experiments" 201 "$RUN_DIR/experiment_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/experiment_create.json"
EXPERIMENT_ID="$(jq -r '.id' "$RUN_DIR/experiment_create.json")"

jq -n '{name: "E2E Experiment Updated", config: {model: "router", mode: "hybrid"}, results: {accuracy: 0.93, latency_ms: 812}}' > "$RUN_DIR/payloads/experiment_patch.json"
api_call PATCH "/experiments/${EXPERIMENT_ID}" 200 "$RUN_DIR/experiment_patch.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/experiment_patch.json"

api_call GET "/experiments" 200 "$RUN_DIR/experiments_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/experiments_list.json" --arg experiment_id "$EXPERIMENT_ID" 'map(select(.id == $experiment_id)) | length == 1'

jq -n '{value: {theme: "dark", stream: true, showTimeline: true}}' > "$RUN_DIR/payloads/settings_upsert.json"
api_call PUT "/settings/ui.preferences" 200 "$RUN_DIR/settings_upsert.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/settings_upsert.json"

api_call GET "/settings/ui.preferences" 200 "$RUN_DIR/settings_get.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/settings_get.json" '.value.theme == "dark"'

api_call GET "/settings" 200 "$RUN_DIR/settings_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/settings_list.json" 'length >= 1'

jq -n '{level: "info", message: "Live E2E log event", source: "e2e-suite", metadata: {stage: "verification"}}' > "$RUN_DIR/payloads/log_create.json"
api_call POST "/logs" 201 "$RUN_DIR/log_create.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/log_create.json"

api_call GET "/logs?source=e2e-suite&limit=20" 200 "$RUN_DIR/logs_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/logs_list.json" 'length >= 1'

echo "==> Marketplace"
jq -n --arg agent_id "$AGENT_ID" '{agent_id: $agent_id}' > "$RUN_DIR/payloads/template_publish.json"
api_call POST "/marketplace/templates/publish" 200 "$RUN_DIR/template_publish.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/template_publish.json"
TEMPLATE_ID="$(jq -r '.id' "$RUN_DIR/template_publish.json")"

api_call GET "/marketplace/templates" 200 "$RUN_DIR/templates_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/templates_list.json" --arg template_id "$TEMPLATE_ID" 'map(select(.id == $template_id)) | length == 1'

jq -n '{name: "Imported Template From E2E"}' > "$RUN_DIR/payloads/template_import.json"
api_call POST "/marketplace/templates/${TEMPLATE_ID}/import" 201 "$RUN_DIR/template_import.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/template_import.json"
assert_jq "$RUN_DIR/template_import.json" '.name == "Imported Template From E2E"'

echo "==> Tooling endpoints (filesystem / terminal / python)"
api_call GET "/tools" 200 "$RUN_DIR/tools_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
assert_jq "$RUN_DIR/tools_list.json" 'length >= 3'

jq -n --arg path "$TOOL_ROOT" '{path: $path}' > "$RUN_DIR/payloads/tools_fs_list.json"
api_call POST "/tools/filesystem/list" 200 "$RUN_DIR/tools_fs_list.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_list.json"
assert_jq "$RUN_DIR/tools_fs_list.json" '.items | length >= 1'

jq -n --arg root "$TOOL_ROOT/apps/api/src" '{root: $root, pattern: "class Settings", file_glob: "**/*.py", max_results: 5}' > "$RUN_DIR/payloads/tools_fs_search.json"
api_call POST "/tools/filesystem/search" 200 "$RUN_DIR/tools_fs_search.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_search.json"
assert_jq "$RUN_DIR/tools_fs_search.json" '.matches | length >= 1'

TOOL_FILE_ORIG="$TOOL_ROOT/artifacts/e2e-tools-note-${RUN_TS}.txt"
TOOL_FILE_MOVED="$TOOL_ROOT/artifacts/e2e-tools-note-${RUN_TS}.moved.txt"
TOOL_FILE_COPY="$TOOL_ROOT/artifacts/e2e-tools-note-${RUN_TS}.copy.txt"

jq -n --arg path "$TOOL_FILE_ORIG" '{path: $path, content: "tool-write-ok", overwrite: true}' > "$RUN_DIR/payloads/tools_fs_write.json"
api_call POST "/tools/filesystem/write" 200 "$RUN_DIR/tools_fs_write.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_write.json"
assert_jq "$RUN_DIR/tools_fs_write.json" '.status == "ok"'

jq -n --arg path "$TOOL_FILE_ORIG" '{path: $path}' > "$RUN_DIR/payloads/tools_fs_read.json"
api_call POST "/tools/filesystem/read" 200 "$RUN_DIR/tools_fs_read.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_read.json"
assert_jq "$RUN_DIR/tools_fs_read.json" '.content == "tool-write-ok"'

jq -n --arg source "$TOOL_FILE_ORIG" --arg destination "$TOOL_FILE_MOVED" '{source: $source, destination: $destination}' > "$RUN_DIR/payloads/tools_fs_move.json"
api_call POST "/tools/filesystem/move" 200 "$RUN_DIR/tools_fs_move.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_move.json"

jq -n --arg source "$TOOL_FILE_MOVED" --arg destination "$TOOL_FILE_COPY" '{source: $source, destination: $destination, recursive: false}' > "$RUN_DIR/payloads/tools_fs_copy.json"
api_call POST "/tools/filesystem/copy" 200 "$RUN_DIR/tools_fs_copy.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_copy.json"

jq -n --arg command "echo terminal-ok && pwd" --arg cwd "$TOOL_ROOT" '{command: $command, cwd: $cwd, timeout_seconds: 45}' > "$RUN_DIR/payloads/tools_terminal_exec.json"
api_call POST "/tools/terminal/exec" 200 "$RUN_DIR/tools_terminal_exec.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_terminal_exec.json"
assert_jq "$RUN_DIR/tools_terminal_exec.json" '.returncode == 0'
assert_jq "$RUN_DIR/tools_terminal_exec.json" '.stdout | contains("terminal-ok")'

jq -n --arg code 'print("python-tool-ok")' '{code: $code, timeout_seconds: 30}' > "$RUN_DIR/payloads/tools_python_exec.json"
api_call POST "/tools/python/exec" 200 "$RUN_DIR/tools_python_exec.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_python_exec.json"
assert_jq "$RUN_DIR/tools_python_exec.json" '.returncode == 0'
assert_jq "$RUN_DIR/tools_python_exec.json" '.stdout | contains("python-tool-ok")'

jq -n --arg path "$TOOL_FILE_MOVED" '{path: $path, recursive: false}' > "$RUN_DIR/payloads/tools_fs_delete_moved.json"
api_call POST "/tools/filesystem/delete" 200 "$RUN_DIR/tools_fs_delete_moved.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_delete_moved.json"

jq -n --arg path "$TOOL_FILE_COPY" '{path: $path, recursive: false}' > "$RUN_DIR/payloads/tools_fs_delete_copy.json"
api_call POST "/tools/filesystem/delete" 200 "$RUN_DIR/tools_fs_delete_copy.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Confirm-Token: $CONFIRM_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/tools_fs_delete_copy.json"

echo "==> Metrics timeline and artifact verification"
for _ in {1..6}; do
  api_call GET "/system/metrics/timeseries?minutes=60&limit=500" 200 "$RUN_DIR/system_metrics_timeseries.json" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
  if jq -e '.count > 0' "$RUN_DIR/system_metrics_timeseries.json" >/dev/null; then
    break
  fi
  sleep 5
done
assert_jq "$RUN_DIR/system_metrics_timeseries.json" '.count > 0'

docker compose ps > "$RUN_DIR/docker_compose_ps.txt"
docker compose logs --tail=200 api worker > "$RUN_DIR/docker_api_worker_logs_tail.txt"
docker compose exec -T postgres psql -U ai_studio -d ai_studio -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;" > "$RUN_DIR/postgres_tables.txt"
docker compose exec -T postgres psql -U ai_studio -d ai_studio -c "SELECT id, trace_id, span_count FROM traces ORDER BY created_at DESC LIMIT 5;" > "$RUN_DIR/postgres_traces_sample.txt"
docker compose exec -T postgres psql -U ai_studio -d ai_studio -c "SELECT id, name, status, source_uri FROM documents ORDER BY created_at DESC LIMIT 5;" > "$RUN_DIR/postgres_documents_sample.txt"
curl -sS "http://localhost:6333/collections/studio_chunks" > "$RUN_DIR/qdrant_collection.json"
assert_jq "$RUN_DIR/qdrant_collection.json" '.result.status == "green" or .result.status == "yellow"'

curl -sS -I "http://localhost:3000" > "$RUN_DIR/web_head.txt"
if ! rg -q "HTTP/1.1 (200|307|308)" "$RUN_DIR/web_head.txt"; then
  echo "Web frontend health check failed:"
  cat "$RUN_DIR/web_head.txt"
  exit 1
fi

jq -n \
  --arg run_ts "$RUN_TS" \
  --arg run_dir "$RUN_DIR" \
  --arg email "$EMAIL" \
  --arg agent_id "$AGENT_ID" \
  --arg workflow_id "$WORKFLOW_ID" \
  --arg chat_id "$CHAT_ID" \
  --arg trace_row_id "$TRACE_ROW_ID" \
  --arg trace_id "$TRACE_ID_FROM_CHAT" \
  --arg document_id "$DOCUMENT_ID" \
  --arg evaluation_id "$EVALUATION_ID" \
  --arg experiment_id "$EXPERIMENT_ID" \
  '{
    run_ts: $run_ts,
    run_dir: $run_dir,
    user_email: $email,
    ids: {
      agent_id: $agent_id,
      workflow_id: $workflow_id,
      chat_id: $chat_id,
      trace_row_id: $trace_row_id,
      trace_id: $trace_id,
      document_id: $document_id,
      evaluation_id: $evaluation_id,
      experiment_id: $experiment_id
    },
    checks: {
      api_auth: true,
      model_router: true,
      supervisor_chat_run: true,
      chat_stream: true,
      memory: true,
      rag_ingest_retrieve: true,
      evaluation: true,
      marketplace: true,
      tools: true,
      metrics_timeseries: true,
      postgres: true,
      qdrant: true,
      web: true
    }
  }' > "$RUN_DIR/summary.json"

echo "==> Auth logout"
jq -n --arg refresh_token "$REFRESH_TOKEN" '{refresh_token: $refresh_token}' > "$RUN_DIR/payloads/auth_logout.json"
api_call POST "/auth/logout" 200 "$RUN_DIR/auth_logout.json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  --data @"$RUN_DIR/payloads/auth_logout.json"
assert_jq "$RUN_DIR/auth_logout.json" '.status == "ok"'

echo "Live E2E run completed successfully."
echo "Artifacts: $RUN_DIR"
