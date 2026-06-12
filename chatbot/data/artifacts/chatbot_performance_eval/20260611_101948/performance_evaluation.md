# Chatbot Performance Evaluation

- Run ID: `20260611_101948`
- Evaluated at: `2026-06-11T10:21:35`
- Output JSON: `/Users/kgw/skipers-ai/chatbot/data/artifacts/chatbot_performance_eval/20260611_101948/performance_evaluation.json`
- Python: `3.11.0` / Platform: `macOS-26.0-arm64-arm-64bit`

## Executive scorecard

| Area | Score | Status | Notes |
| --- | ---: | --- | --- |
| infrastructure | 1.0000 | good | Qdrant connected=True, MinIO connected=True |
| data | 0.7155 | watch | 75 patents; parsed/report/pdf ratios {'input': 0.5733, 'report': 1.0, 'pdf': 0.5733} |
| vectorstore | 1.0000 | good | Shared, live, wiki, visual, application collection coverage |
| retrieval | 0.2500 | risk | 2/8 searches returned hits |
| chat | 0.0825 | risk | 3 sampled end-to-end chat calls |
| visual | 1.0000 | good | visual collection docs=173 |
| pre_eval | 1.0000 | good | legacy cases=1, pre-application vectorstores=0 |
| **overall** | **0.7127** | **watch** | weighted composite |

## Infrastructure

- Qdrant: connected `True`, collections `50`, URL `http://localhost:6333`
- MinIO: connected `True`, remote objects `30`, remote size `14949411`, local patents `75`, backend `aws_cli`
- MinIO note: `boto3 is not installed`

## Data Coverage

- Patent count: `75`
- Input/report/pdf counts: `43` / `75` / `43`
- Chunk total/avg/max: `2657` / `35.43` / `64`
- Report statuses: `{'partial_success': 27, 'needs_human_review': 48}`; invalid validation count `27`

## Qdrant Collections

| Label | Collection | Exists | Points | Status |
| --- | --- | --- | ---: | --- |
| shared_patents | `skipa_patent_docs` | True | 2657 | green |
| patent_global | `skipa_patent_docs_global` | False | None | Qdrant GET /collections/skipa_patent_docs_global failed: HTTP 404 {"status":{"error":"Not found: Collection `skipa_patent_docs_global` doesn't exist!"},"time":5.656e-6} |
| patent_live | `skipa_patent_live` | True | 0 | green |
| patent_visuals | `skipa_patent_visual_clip` | True | 173 | green |
| wiki_global | `skipa_wiki_docs_global` | False | None | Qdrant GET /collections/skipa_wiki_docs_global failed: HTTP 404 {"status":{"error":"Not found: Collection `skipa_wiki_docs_global` doesn't exist!"},"time":4.301e-6} |
| wiki_live | `skipa_wiki_live` | True | 2 | green |
| application | `skipa_application_docs` | True | 18 | green |

- Patent blue-green active: `skipa_patent_live_blue` / color `blue`
- Wiki blue-green active: `skipa_wiki_live_green` / color `green`

## API Latency

- Summary: `{'count': 8, 'avg_ms': 2394.18, 'p50_ms': 403.98, 'p95_ms': 9603.62, 'max_ms': 11795.01}`

| Endpoint | Status | Latency ms | Error |
| --- | ---: | ---: | --- |
| `/` | 200 | 3.09 |  |
| `/api/v1/chatbot/config` | 200 | 11795.01 |  |
| `/api/v1/chatbot/qdrant/status` | 200 | 21.57 |  |
| `/api/v1/chatbot/minio/status` | 200 | 747.68 |  |
| `/api/v1/chatbot/patents` | 200 | 5533.9 |  |
| `/api/v1/chatbot/vectorstore/status` | 200 | 988.93 |  |
| `/api/v1/chatbot/visual-vectorstore/status` | 200 | 60.28 |  |
| `/api/v1/pre-eval/vectorstore/status` | 200 | 3.0 |  |

## Retrieval Benchmarks

- Summary: `{'count': 8, 'avg_ms': 1531.39, 'p50_ms': 1670.13, 'p95_ms': 1985.53, 'max_ms': 2039.37}`

| Case | Patent | Hits | Mode | Latency ms | Score avg |
| --- | --- | ---: | --- | ---: | ---: |
| global_core_search | `None` | 5 | shared_qdrant_search | 733.82 | 0.5944 |
| global_report_decision | `None` | 6 | shared_qdrant_search | 941.78 | 0.5433 |
| patent_original_1 | `10-1165267` | 0 | keyword_chunk_search | 2039.37 | None |
| patent_report_1 | `10-1165267` | 0 | keyword_chunk_search | 1885.53 | None |
| patent_original_2 | `10-1261156` | 0 | keyword_chunk_search | 1701.8 | None |
| patent_report_2 | `10-1261156` | 0 | keyword_chunk_search | 1578.75 | None |
| patent_original_3 | `10-1261894` | 0 | keyword_chunk_search | 1638.47 | None |
| patent_report_3 | `10-1261894` | 0 | keyword_chunk_search | 1731.57 | None |

## Chat Benchmarks

- Summary: `{'count': 3, 'avg_ms': 23389.63, 'p50_ms': 24531.47, 'p95_ms': 26934.26, 'max_ms': 27201.24}`

| Case | Patent | Sources | LLM | Composite v2 | Faithfulness | Latency ms |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| selected_patent_deep_dive | `10-1165267` | 0 | True | 0.1548 | 0.0 | 24531.47 |
| selected_patent_decision_table | `10-1261156` | 0 | True | 0.1298 | 0.0 | 27201.24 |
| global_portfolio_summary | `None` | 8 | True | 0.4577 | 0.2718 | 18436.17 |

## Visual And Pre-Eval

- Visual status: candidates `75`, indexed manifests `10`, pending `65`, qdrant docs `173`
- Visual search: `{'name': 'visual_search', 'ok': True, 'elapsed_ms': 1445.86, 'error': None, 'mode': 'visual_text_search', 'collection': 'skipa_patent_visual_clip', 'hit_count': 0, 'text_hit_count': 0, 'image_hit_count': 0, 'clip_provider': 'open_clip:ViT-B-32:openai:mps', 'embedding_provider': 'openai', 'hits': []}`
- Pre-eval legacy case count: `1`
- Pre-application vectorstore count: `0`

## Main Findings

- MinIO and Qdrant are both connected through the active local port-forward sessions.
- MinIO `patent/` currently exposes 30 objects, while the local cache exposes 75 patents; treat MinIO as a subset or verify prefix/sync scope before relying on it as the only source of truth.
- Local chatbot venv is missing boto3, so MinIO status used AWS CLI fallback. Production image requirements include boto3, but local reproducibility should be tightened.
- 27 report.json files have validation.valid=false; this lowers answer quality because report chunks can contain partial_success/error metadata.
- Visual collection has data, but some patent visual manifests are pending or errored; visual RAG coverage is partial.

## Limits

- BERTScore was skipped to avoid model download/runtime noise; lexical/semantic lightweight metrics were still computed.
- This is a sampled performance evaluation, not a high-concurrency load test.
- The script does not mutate MinIO, Qdrant, or local patent data.
