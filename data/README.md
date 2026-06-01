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

## Patent Folder Contract

Each patent should be managed under one folder:

```text
data/mapped_patent_reports/<patent_id>/
  manifest.json
  original/input/      # normalized patent input JSON
  original/pdf/        # original uploaded patent PDF
  reports/json/        # generated report JSON
  wiki/                # patent-specific wiki data and vectorstore
  extracted/           # text/image/table chunks and assets
  index/               # patent-specific vector index
```

`latest.json` and `latest.pdf` files are convenience pointers to the newest
input, report, and original PDF. Timestamped files are kept for reproducibility.

`data/api_test` is kept for Swagger/API reproducibility. Production features
should use the patent-specific folders as the long-term source of truth.
