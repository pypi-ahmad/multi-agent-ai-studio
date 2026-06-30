# RAG Guide

## What It Does

Implements production-grade retrieval-augmented generation for local-first workflows:

- Document registration and ingestion.
- Embeddings via Ollama router-selected embedding model.
- Vector storage in Qdrant.
- Hybrid retrieval (semantic + keyword).
- Embedding-based reranking.
- Highlight snippets and source metadata for citation-ready responses.

## Connector Matrix

### File Upload Connector

Route: `POST /api/v1/rag/documents/{document_id}/ingest`

Supported formats:

- PDF
- DOCX
- Markdown / TXT
- HTML
- CSV
- XLSX

### GitHub Connector

Route: `POST /api/v1/rag/connectors/ingest`

Payload:

- `connector: "github"`
- `source_uri`: repository clone URL
- `options`: `branch`, `max_files`, `max_file_bytes`

Behavior:

1. Shallow clone repository.
2. Read allowed text/code files.
3. Chunk + embed + index in Qdrant.

### Web Crawler Connector

Route: `POST /api/v1/rag/connectors/ingest`

Payload:

- `connector: "web"`
- `source_uri`: seed URL
- `options`: `max_pages`, `max_depth`, `same_domain`

Behavior:

1. Crawl pages breadth-first.
2. Extract cleaned text with Trafilatura/BeautifulSoup.
3. Chunk + embed + index.

## Retrieval Modes

Route: `POST /api/v1/rag/retrieve`

- `mode: semantic` - vector similarity only.
- `mode: keyword` - lexical scoring only.
- `mode: hybrid` - weighted vector + lexical blend.

`rerank: true` applies secondary embedding similarity rerank on the top candidate pool.

## Recommended Defaults

- `mode: "hybrid"`
- `candidate_pool: 30`
- `top_k: 5`
- `rerank: true`

## Operational Notes

- Keep connector metadata consistent for reliable filtering.
- Limit crawler depth/pages for low-latency ingestion.
- Prefer repository subsets for large monorepos.
