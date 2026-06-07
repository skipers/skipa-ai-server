# API Workflow Verification

- Generated at: 2026-06-07T15:51:08
- Patent used: `10-1959619`
- Total/OK/Failed: 26/26/0

## Endpoints
- OK `GET /health` -> 200
- OK `GET /api/v1/chatbot/config` -> 200
- OK `GET /api/v1/chatbot/patents` -> 200
- OK `GET /api/v1/chatbot/patents/10-1959619` -> 200
- OK `GET /api/v1/chatbot/patents/10-1959619/files` -> 200
- OK `GET /api/v1/chatbot/patents/10-1959619/input/latest` -> 200
- OK `GET /api/v1/chatbot/patents/10-1959619/report/latest` -> 200
- OK `GET /api/v1/chatbot/patents/10-1959619/chunks` -> 200
- OK `POST /api/v1/chatbot/search` -> 200
- OK `POST /api/v1/chatbot/answer` -> 200
- OK `GET /api/v1/patent-chat/chat/mermaid` -> 200
- OK `GET /api/v1/patent-chat/ingestion/mermaid` -> 200
- OK `GET /api/v1/patent-chat/engine/status` -> 200
- OK `POST /api/v1/chatbot/preprocess/run` -> 200
- OK `GET /api/v1/chatbot/preprocess/status` -> 200
- OK `GET /api/v1/wiki/topics` -> 200
- OK `POST /api/v1/wiki/topics/reclassify` -> 200
- OK `POST /api/v1/wiki/topics/refresh` -> 200
- OK `GET /api/v1/wiki/topics/반도체_전자/patent` -> 200
- OK `GET /api/v1/wiki/agent/mermaid` -> 200
- OK `GET /api/v1/application/status` -> 200
- OK `GET /api/v1/application/external/status` -> 200
- OK `POST /api/v1/application/index/refresh` -> 200
- OK `GET /api/v1/application/chat/mermaid` -> 200
- OK `GET /api/v1/application/failed-patents` -> 200
- OK `POST /api/v1/application/chat` -> 200
