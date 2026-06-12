# Patent Citation Count Collection

Collect forward citation counts for patents listed in the project Excel file.

## Input

Default Excel path, relative to `skipa-ai-server`:

```text
특허리스트_등록_20260423기준 (1).xlsx
```

The script reads these columns:

- `등록번호`
- `출원번호`
- `발명의 명칭(최종)`

## Output

Default CSV path:

```text
patent_citation_collection/output/patent_citation_counts.csv
```

Columns:

- `registration_number`
- `citation_count`
- `application_number`
- `title`
- `source`
- `status`
- `error`
- `fetched_at`

When citation data cannot be collected, `citation_count` is written as `0`.

## Run

```bash
cd /Users/knh/workspace/skipa/skipa-ai-server
python3 patent_citation_collection/collect_citation_counts.py
```

The script loads `KIPRIS_API_KEY` from `skipa-ai-server/.env` when available.

If KIPRIS returns `AccessKey&ServiceID Is Not Registerd Error`, the current key
does not have CitingService access. The CSV is still generated with
`citation_count=0`; rerun the same command after registering/enabling that
service for the key.
