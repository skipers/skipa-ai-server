# Shared Data Layout

This directory is the shared data root for `eval_logic` and `chatbot`.

```text
data/
  mapped_patent_reports/
    <patent_id>/
      manifest.json
      original/
        input/
        pdf/
      reports/
        json/
      wiki/
      extracted/
      index/
  api_test/
    input/
      pdf/
      extracted/
      uploads/
    output/
      reports/
  business/
  artifacts/
  business_rag/
```

`eval_logic/src/core/paths.py` resolves this folder through `SKIPA_DATA_ROOT`
or `DATA_ROOT`, then defaults to the repository-level `data` directory. The
chatbot `.env` points `DATA_ROOT` here as well, so patent original data, report
JSON, and wiki/index data stay under one patent-specific folder.
