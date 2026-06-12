# Chatbot Performance Evaluation

- Run ID: `20260611_102344`
- Evaluated at: `2026-06-11T10:25:18`
- Output JSON: `/Users/kgw/skipers-ai/chatbot/data/artifacts/chatbot_performance_eval/20260611_102344/performance_evaluation.json`
- Python: `3.11.0` / Platform: `macOS-26.0-arm64-arm-64bit`

## Executive scorecard

| Area | Score | Status | Notes |
| --- | ---: | --- | --- |
| infrastructure | 1.0000 | good | Qdrant connected=True, MinIO connected=True |
| data | 0.7155 | watch | 75 patents; parsed/report/pdf ratios {'input': 0.5733, 'report': 1.0, 'pdf': 0.5733} |
| vectorstore | 1.0000 | good | Shared, live, wiki, visual, application collection coverage |
| retrieval | 1.0000 | good | 10/10 searches returned hits |
| chat | 0.5291 | risk | 3 sampled end-to-end chat calls |
| visual | 1.0000 | good | visual collection docs=173 |
| pre_eval | 1.0000 | good | legacy cases=1, pre-application vectorstores=0 |
| **overall** | **0.9074** | **good** | weighted composite |

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
| patent_global | `skipa_patent_docs_global` | False | None | Qdrant GET /collections/skipa_patent_docs_global failed: HTTP 404 {"status":{"error":"Not found: Collection `skipa_patent_docs_global` doesn't exist!"},"time":8.491e-6} |
| patent_live | `skipa_patent_live` | True | 0 | green |
| patent_visuals | `skipa_patent_visual_clip` | True | 173 | green |
| wiki_global | `skipa_wiki_docs_global` | False | None | Qdrant GET /collections/skipa_wiki_docs_global failed: HTTP 404 {"status":{"error":"Not found: Collection `skipa_wiki_docs_global` doesn't exist!"},"time":5.877e-6} |
| wiki_live | `skipa_wiki_live` | True | 33 | green |
| application | `skipa_application_docs` | True | 18 | green |

- Patent blue-green active: `skipa_patent_live_blue` / color `blue`
- Wiki blue-green active: `skipa_wiki_live_blue` / color `blue`

## API Latency

- Summary: `{'count': 8, 'avg_ms': 1966.33, 'p50_ms': 403.77, 'p95_ms': 8032.19, 'max_ms': 10297.16}`

| Endpoint | Status | Latency ms | Error |
| --- | ---: | ---: | --- |
| `/` | 200 | 3.02 |  |
| `/api/v1/chatbot/config` | 200 | 10297.16 |  |
| `/api/v1/chatbot/qdrant/status` | 200 | 25.31 |  |
| `/api/v1/chatbot/minio/status` | 200 | 748.77 |  |
| `/api/v1/chatbot/patents` | 200 | 3825.83 |  |
| `/api/v1/chatbot/vectorstore/status` | 200 | 768.51 |  |
| `/api/v1/chatbot/visual-vectorstore/status` | 200 | 58.77 |  |
| `/api/v1/pre-eval/vectorstore/status` | 200 | 3.27 |  |

## Retrieval Benchmarks

- Summary: `{'count': 10, 'avg_ms': 824.22, 'p50_ms': 817.76, 'p95_ms': 960.71, 'max_ms': 971.24}`

| Case | Patent | Hits | Mode | Latency ms | Score avg |
| --- | --- | ---: | --- | ---: | ---: |
| global_core_search | `None` | 5 | shared_qdrant_search | 707.12 | 0.6964 |
| global_report_decision | `None` | 6 | shared_qdrant_search | 854.27 | 0.5587 |
| patent_original_natural_1 | `10-1165267` | 6 | shared_qdrant_search | 831.93 | 0.6025 |
| patent_report_natural_1 | `10-1165267` | 6 | shared_qdrant_search | 798.45 | 0.5673 |
| patent_original_id_anchor_1 | `10-1165267` | 6 | shared_qdrant_search | 803.59 | 0.6838 |
| patent_report_id_anchor_1 | `10-1165267` | 6 | shared_qdrant_search | 947.83 | 0.6436 |
| patent_original_natural_2 | `10-1261156` | 6 | shared_qdrant_search | 971.24 | 0.6731 |
| patent_report_natural_2 | `10-1261156` | 6 | shared_qdrant_search | 612.68 | 0.6688 |
| patent_original_id_anchor_2 | `10-1261156` | 6 | shared_qdrant_search | 921.41 | 0.7608 |
| patent_report_id_anchor_2 | `10-1261156` | 6 | shared_qdrant_search | 793.64 | 0.6893 |

## Chat Benchmarks

- Summary: `{'count': 3, 'avg_ms': 21411.21, 'p50_ms': 19375.96, 'p95_ms': 26968.4, 'max_ms': 27812.01}`

| Case | Patent | Sources | LLM | Composite v2 | Faithfulness | Latency ms |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| selected_patent_natural_deep_dive | `10-1165267` | 10 | True | 0.5387 | 0.268 | 27812.01 |
| selected_patent_id_anchor_decision_table | `10-1261156` | 10 | True | 0.587 | 0.4423 | 19375.96 |
| global_portfolio_summary | `None` | 8 | True | 0.4616 | 0.2783 | 17045.65 |

## Visual And Pre-Eval

- Visual status: candidates `75`, indexed manifests `10`, pending `65`, qdrant docs `173`
- Visual search: `{'name': 'visual_search', 'ok': True, 'elapsed_ms': 1008.65, 'error': None, 'mode': 'visual_text_search', 'collection': 'skipa_patent_visual_clip', 'hit_count': 0, 'text_hit_count': 0, 'image_hit_count': 0, 'clip_provider': 'open_clip:ViT-B-32:openai:mps', 'embedding_provider': 'openai', 'hits': []}`
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
