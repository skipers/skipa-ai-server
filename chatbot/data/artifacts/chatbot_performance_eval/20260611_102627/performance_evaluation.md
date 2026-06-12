# Chatbot Performance Evaluation

- Run ID: `20260611_102627`
- Evaluated at: `2026-06-11T10:27:59`
- Output JSON: `/Users/kgw/skipers-ai/chatbot/data/artifacts/chatbot_performance_eval/20260611_102627/performance_evaluation.json`
- Python: `3.11.0` / Platform: `macOS-26.0-arm64-arm-64bit`

## Executive scorecard

| Area | Score | Status | Notes |
| --- | ---: | --- | --- |
| infrastructure | 1.0000 | good | Qdrant connected=True, MinIO connected=True |
| data | 0.7155 | watch | 75 patents; parsed/report/pdf ratios {'input': 0.5733, 'report': 1.0, 'pdf': 0.5733} |
| vectorstore | 0.8000 | watch | Shared, live, wiki, visual, application collection coverage |
| retrieval | 1.0000 | good | 10/10 searches returned hits |
| chat | 0.5407 | risk | 3 sampled end-to-end chat calls |
| visual | 0.5400 | risk | visual collection docs=173 |
| pre_eval | 0.7000 | watch | legacy cases=1, pre-application vectorstores=0 |
| **overall** | **0.8046** | **watch** | weighted composite |

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
| patent_global | `skipa_patent_docs_global` | False | None | Qdrant GET /collections/skipa_patent_docs_global failed: HTTP 404 {"status":{"error":"Not found: Collection `skipa_patent_docs_global` doesn't exist!"},"time":7.701e-6} |
| patent_live | `skipa_patent_live` | True | 0 | green |
| patent_visuals | `skipa_patent_visual_clip` | True | 173 | green |
| wiki_global | `skipa_wiki_docs_global` | False | None | Qdrant GET /collections/skipa_wiki_docs_global failed: HTTP 404 {"status":{"error":"Not found: Collection `skipa_wiki_docs_global` doesn't exist!"},"time":0.000036654} |
| wiki_live | `skipa_wiki_live` | True | 33 | green |
| application | `skipa_application_docs` | True | 18 | green |

- Patent blue-green active: `skipa_patent_live_blue` / color `blue`
- Wiki blue-green active: `skipa_wiki_live_blue` / color `blue`

## API Latency

- Summary: `{'count': 8, 'avg_ms': 2226.11, 'p50_ms': 410.45, 'p95_ms': 9004.93, 'max_ms': 11180.85}`

| Endpoint | Status | Latency ms | Error |
| --- | ---: | ---: | --- |
| `/` | 200 | 3.14 |  |
| `/api/v1/chatbot/config` | 200 | 11180.85 |  |
| `/api/v1/chatbot/qdrant/status` | 200 | 28.08 |  |
| `/api/v1/chatbot/minio/status` | 200 | 809.9 |  |
| `/api/v1/chatbot/patents` | 200 | 4963.94 |  |
| `/api/v1/chatbot/vectorstore/status` | 200 | 767.79 |  |
| `/api/v1/chatbot/visual-vectorstore/status` | 200 | 53.11 |  |
| `/api/v1/pre-eval/vectorstore/status` | 200 | 2.03 |  |

## Retrieval Benchmarks

- Summary: `{'count': 10, 'avg_ms': 973.21, 'p50_ms': 880.62, 'p95_ms': 1606.7, 'max_ms': 1611.68}`

| Case | Patent | Hits | Mode | Latency ms | Score avg |
| --- | --- | ---: | --- | ---: | ---: |
| global_core_search | `None` | 5 | shared_qdrant_search | 851.09 | 0.6966 |
| global_report_decision | `None` | 6 | shared_qdrant_search | 893.87 | 0.5594 |
| patent_original_natural_1 | `10-1165267` | 6 | shared_qdrant_search | 867.38 | 0.6028 |
| patent_report_natural_1 | `10-1165267` | 6 | shared_qdrant_search | 500.41 | 0.5678 |
| patent_original_id_anchor_1 | `10-1165267` | 6 | shared_qdrant_search | 1487.32 | 0.6837 |
| patent_report_id_anchor_1 | `10-1165267` | 6 | shared_qdrant_search | 546.83 | 0.6451 |
| patent_original_natural_2 | `10-1261156` | 6 | shared_qdrant_search | 1611.68 | 0.6733 |
| patent_report_natural_2 | `10-1261156` | 6 | shared_qdrant_search | 315.61 | 0.6688 |
| patent_original_id_anchor_2 | `10-1261156` | 6 | shared_qdrant_search | 1600.62 | 0.7622 |
| patent_report_id_anchor_2 | `10-1261156` | 6 | shared_qdrant_search | 1057.29 | 0.6895 |

## Chat Benchmarks

- Summary: `{'count': 3, 'avg_ms': 20100.73, 'p50_ms': 20356.83, 'p95_ms': 22691.67, 'max_ms': 22951.1}`

| Case | Patent | Sources | LLM | Composite v2 | Faithfulness | Latency ms |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| selected_patent_natural_deep_dive | `10-1165267` | 10 | True | 0.5482 | 0.3953 | 22951.1 |
| selected_patent_id_anchor_decision_table | `10-1261156` | 10 | True | 0.6021 | 0.4561 | 16994.26 |
| global_portfolio_summary | `None` | 8 | True | 0.4719 | 0.2768 | 20356.83 |

## Visual And Pre-Eval

- Visual status: candidates `75`, indexed manifests `10`, pending `65`, qdrant docs `173`
- Visual search: `{'name': 'visual_search', 'ok': True, 'elapsed_ms': 1681.15, 'error': None, 'mode': 'visual_text_search', 'collection': 'skipa_patent_visual_clip', 'hit_count': 0, 'text_hit_count': 0, 'image_hit_count': 0, 'clip_provider': 'open_clip:ViT-B-32:openai:mps', 'embedding_provider': 'openai', 'hits': []}`
- Pre-eval legacy case count: `1`
- Pre-application vectorstore count: `0`

## Main Findings

- MinIO and Qdrant are both connected through the active local port-forward sessions.
- MinIO `patent/` currently exposes 30 objects, while the local cache exposes 75 patents; treat MinIO as a subset or verify prefix/sync scope before relying on it as the only source of truth.
- Local chatbot venv is missing boto3, so MinIO status used AWS CLI fallback. Production image requirements include boto3, but local reproducibility should be tightened.
- 27 report.json files have validation.valid=false; this lowers answer quality because report chunks can contain partial_success/error metadata.
- Patent live blue-green alias is active but its active slot has 0 documents; current search succeeds by falling back to the shared patent collection.
- Visual collection has data, but some patent visual manifests are pending or errored; visual RAG coverage is partial.

## Limits

- BERTScore was skipped to avoid model download/runtime noise; lexical/semantic lightweight metrics were still computed.
- This is a sampled performance evaluation, not a high-concurrency load test.
- The script does not mutate MinIO, Qdrant, or local patent data.
