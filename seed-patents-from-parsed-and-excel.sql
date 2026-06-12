-- Seed patents from parsed JSON files plus the patent Excel list.
-- Run from the skipa-ai-server directory:
--   psql "$DATABASE_URL" -f seed-patents-from-parsed-and-excel.sql

begin;

create or replace function pg_temp.skipa_seed_parse_date(value text)
returns date
language sql
immutable
returns null on null input
as $$
    select case
        when btrim(value) = '' then null
        when btrim(value) ~ '^\d{4}-\d{2}-\d{2}$' then btrim(value)::date
        when length(regexp_replace(value, '[^0-9]', '', 'g')) = 8
            then to_date(regexp_replace(value, '[^0-9]', '', 'g'), 'YYYYMMDD')
        else null
    end
$$;

create temp table if not exists skipa_seed_patent_parsed_raw (
    payload jsonb not null
) on commit drop;

create temp table if not exists skipa_seed_patent_excel_raw (
    payload jsonb not null
) on commit drop;

create temp table if not exists skipa_seed_patent_citation_counts (
    registration_number text,
    citation_count integer,
    application_number text,
    title text,
    source text,
    status text,
    error text,
    fetched_at text
) on commit drop;

truncate table skipa_seed_patent_parsed_raw;
truncate table skipa_seed_patent_excel_raw;
truncate table skipa_seed_patent_citation_counts;

\copy skipa_seed_patent_parsed_raw (payload) from program 'python3 scripts/patent_seed_sources_to_jsonl.py parsed parsing_data/parsed/old' with (format csv, delimiter E'\x02', quote E'\x01')
\copy skipa_seed_patent_excel_raw (payload) from program 'python3 scripts/patent_seed_sources_to_jsonl.py excel "특허리스트_등록_20260423기준 (1).xlsx"' with (format csv, delimiter E'\x02', quote E'\x01')
\copy skipa_seed_patent_citation_counts from 'patent_citation_collection/output/patent_citation_counts.csv' with (format csv, header true)

with parsed_source as (
    select
        raw.payload ->> 'parsed_json_key' as parsed_json_key,
        raw.payload ->> 'directory_name' as directory_name,
        raw.payload -> 'payload' as parsed_payload,
        raw.payload -> 'payload' -> 'normalized_patent' as patent,
        raw.payload -> 'payload' -> 'normalized_patent' -> 'meta' as meta,
        raw.payload -> 'payload' -> 'raw' -> 'meta' as raw_meta
    from skipa_seed_patent_parsed_raw raw
),
json_patents as (
    select
        parsed_source.*,
        coalesce(
            nullif(nullif(meta ->> 'registration_number', ''), '-'),
            nullif(nullif(raw_meta ->> '등록번호', ''), '-')
        ) as registration_number,
        coalesce(
            nullif(nullif(meta ->> 'application_number', ''), '-'),
            nullif(nullif(raw_meta ->> '출원번호', ''), '-')
        ) as application_number_from_json,
        coalesce(
            nullif(nullif(meta ->> 'publication_number', ''), '-'),
            nullif(nullif(raw_meta ->> '공개번호', ''), '-')
        ) as publication_number,
        nullif(nullif(raw_meta ->> '공고번호', ''), '-') as announcement_number,
        coalesce(
            nullif(meta ->> 'title', ''),
            nullif(raw_meta ->> '발명의_명칭', ''),
            nullif(patent ->> 'patent_id', ''),
            directory_name
        ) as title,
        coalesce(meta -> 'ipc', '[]'::jsonb) as ipc_codes,
        coalesce(meta -> 'cpc', '[]'::jsonb) as cpc_codes,
        (
            select string_agg(value, '; ' order by ordinality)
            from jsonb_array_elements_text(coalesce(meta -> 'assignee', '[]'::jsonb))
                with ordinality as assignees(value, ordinality)
        ) as applicant,
        (
            select string_agg(value, '; ' order by ordinality)
            from jsonb_array_elements_text(coalesce(meta -> 'inventors', '[]'::jsonb))
                with ordinality as inventors(value, ordinality)
        ) as inventor,
        case
            when nullif(meta ->> 'citation_count', '') ~ '^\d+$'
                then (meta ->> 'citation_count')::integer
            else null
        end as citation_count,
        case
            when nullif(meta ->> 'total_claims', '') ~ '^\d+$'
                then (meta ->> 'total_claims')::integer
            else null
        end as examination_claim_count,
        coalesce(meta -> 'keywords', parsed_payload -> 'keywords', '[]'::jsonb) as keywords,
        case
            when jsonb_typeof(patent -> 'brief_summary') = 'string' then patent ->> 'brief_summary'
            when patent ? 'brief_summary' then (patent -> 'brief_summary')::text
            when parsed_payload ? 'brief_summary' then parsed_payload ->> 'brief_summary'
            else patent ->> 'description_summary'
        end as summary,
        coalesce(
            nullif(patent ->> 'source_pdf', ''),
            nullif(parsed_payload ->> 'source_pdf', '')
        ) as original_pdf_key,
        coalesce(
            nullif(nullif(meta ->> 'registration_number', ''), '-'),
            nullif(nullif(raw_meta ->> '등록번호', ''), '-'),
            nullif(nullif(patent ->> 'patent_id', ''), '-'),
            directory_name
        ) as patent_key
    from parsed_source
),
excel_patents as (
    select
        nullif(payload ->> 'management_number', '') as management_number,
        nullif(payload ->> 'final_title', '') as final_title,
        nullif(payload ->> 'business_field', '') as business_field,
        nullif(payload ->> 'tech_field', '') as tech_field,
        nullif(payload ->> 'related_products', '') as related_products,
        nullif(payload ->> 'filing_country', '') as filing_country,
        nullif(payload ->> 'is_joint_application', '') as is_joint_application,
        nullif(payload ->> 'joint_applicant', '') as joint_applicant,
        nullif(payload ->> 'status', '') as status,
        nullif(payload ->> 'application_date', '') as application_date,
        nullif(payload ->> 'registration_date', '') as registration_date,
        nullif(payload ->> 'application_number', '') as application_number,
        nullif(payload ->> 'registration_number', '') as registration_number,
        nullif(payload ->> 'expiry_date', '') as expiry_date
    from skipa_seed_patent_excel_raw
),
citation_counts as (
    select
        nullif(registration_number, '') as registration_number,
        nullif(application_number, '') as application_number,
        coalesce(citation_count, 0) as citation_count
    from skipa_seed_patent_citation_counts
),
merged as (
    select
        json_patents.*,
        excel_patents.management_number,
        excel_patents.final_title,
        excel_patents.business_field,
        excel_patents.tech_field,
        excel_patents.related_products,
        excel_patents.filing_country,
        excel_patents.is_joint_application,
        excel_patents.joint_applicant,
        excel_patents.status,
        excel_patents.application_date as excel_application_date,
        excel_patents.registration_date as excel_registration_date,
        excel_patents.application_number as excel_application_number,
        excel_patents.registration_number as excel_registration_number,
        excel_patents.expiry_date as excel_expiry_date,
        citation_counts.citation_count as collected_citation_count
    from json_patents
    left join lateral (
        select excel_patents.*
        from excel_patents
        where (
            json_patents.registration_number is not null
            and excel_patents.registration_number = json_patents.registration_number
        )
        or (
            json_patents.application_number_from_json is not null
            and excel_patents.application_number = json_patents.application_number_from_json
        )
        order by
            case
                when excel_patents.registration_number = json_patents.registration_number then 0
                else 1
            end
        limit 1
    ) excel_patents on true
    left join lateral (
        select citation_counts.*
        from citation_counts
        where (
            json_patents.registration_number is not null
            and citation_counts.registration_number = json_patents.registration_number
        )
        or (
            json_patents.application_number_from_json is not null
            and citation_counts.application_number = json_patents.application_number_from_json
        )
        order by
            case
                when citation_counts.registration_number = json_patents.registration_number then 0
                else 1
            end
        limit 1
    ) citation_counts on true
),
prepared as (
    select
        coalesce(merged.title, merged.final_title, merged.patent_key) as title,
        coalesce(
            merged.application_number_from_json,
            merged.excel_application_number,
            'NO-APPLICATION-' || merged.patent_key
        ) as application_number,
        coalesce(merged.registration_number, merged.excel_registration_number) as registration_number,
        merged.publication_number,
        merged.announcement_number,
        coalesce(
            pg_temp.skipa_seed_parse_date(merged.meta ->> 'application_date'),
            pg_temp.skipa_seed_parse_date(merged.raw_meta ->> '출원일자'),
            pg_temp.skipa_seed_parse_date(merged.excel_application_date)
        ) as application_date,
        coalesce(
            pg_temp.skipa_seed_parse_date(merged.meta ->> 'registration_date'),
            pg_temp.skipa_seed_parse_date(merged.raw_meta ->> '등록일자'),
            pg_temp.skipa_seed_parse_date(merged.excel_registration_date)
        ) as registration_date,
        coalesce(
            pg_temp.skipa_seed_parse_date(merged.meta ->> 'publication_date'),
            pg_temp.skipa_seed_parse_date(merged.raw_meta ->> '공개일자')
        ) as publication_date,
        pg_temp.skipa_seed_parse_date(merged.raw_meta ->> '공고일자') as announcement_date,
        merged.ipc_codes,
        merged.cpc_codes,
        merged.applicant,
        merged.inventor,
        pg_temp.skipa_seed_parse_date(merged.excel_expiry_date) as expiry_date,
        coalesce(merged.collected_citation_count, merged.citation_count, 0) as citation_count,
        merged.examination_claim_count,
        merged.original_pdf_key,
        merged.parsed_json_key,
        'APPROVED' as approval_status,
        merged.management_number,
        merged.business_field,
        merged.tech_field,
        case
            when merged.related_products is null then '[]'::jsonb
            else jsonb_build_array(merged.related_products)
        end as related_products,
        merged.filing_country,
        case
            when upper(coalesce(merged.is_joint_application, '')) in ('Y', 'YES', 'TRUE', '1') then true
            when upper(coalesce(merged.is_joint_application, '')) in ('N', 'NO', 'FALSE', '0') then false
            else jsonb_array_length(coalesce(merged.meta -> 'assignee', '[]'::jsonb)) > 1
        end as is_joint_application,
        merged.joint_applicant,
        merged.business_field as initial_department,
        departments.id as current_department_id,
        merged.keywords,
        merged.summary
    from merged
    left join departments on departments.name = merged.business_field
)
insert into patents (
    title,
    application_number,
    registration_number,
    publication_number,
    announcement_number,
    application_date,
    registration_date,
    publication_date,
    announcement_date,
    ipc_codes,
    cpc_codes,
    applicant,
    inventor,
    expiry_date,
    citation_count,
    examination_claim_count,
    original_pdf_key,
    parsed_json_key,
    approval_status,
    management_number,
    business_field,
    tech_field,
    related_products,
    filing_country,
    is_joint_application,
    joint_applicant,
    initial_department,
    current_department_id,
    keywords,
    summary,
    created_at,
    updated_at
)
select
    title,
    application_number,
    registration_number,
    publication_number,
    announcement_number,
    application_date,
    registration_date,
    publication_date,
    announcement_date,
    ipc_codes,
    cpc_codes,
    applicant,
    inventor,
    expiry_date,
    citation_count,
    examination_claim_count,
    original_pdf_key,
    parsed_json_key,
    approval_status,
    management_number,
    business_field,
    tech_field,
    related_products,
    filing_country,
    is_joint_application,
    joint_applicant,
    initial_department,
    current_department_id,
    keywords,
    summary,
    now(),
    now()
from prepared
on conflict (application_number) do update
set title = excluded.title,
    registration_number = excluded.registration_number,
    publication_number = excluded.publication_number,
    announcement_number = excluded.announcement_number,
    application_date = excluded.application_date,
    registration_date = excluded.registration_date,
    publication_date = excluded.publication_date,
    announcement_date = excluded.announcement_date,
    ipc_codes = excluded.ipc_codes,
    cpc_codes = excluded.cpc_codes,
    applicant = excluded.applicant,
    inventor = excluded.inventor,
    expiry_date = excluded.expiry_date,
    citation_count = excluded.citation_count,
    examination_claim_count = excluded.examination_claim_count,
    original_pdf_key = excluded.original_pdf_key,
    parsed_json_key = excluded.parsed_json_key,
    approval_status = excluded.approval_status,
    management_number = excluded.management_number,
    business_field = excluded.business_field,
    tech_field = excluded.tech_field,
    related_products = excluded.related_products,
    filing_country = excluded.filing_country,
    is_joint_application = excluded.is_joint_application,
    joint_applicant = excluded.joint_applicant,
    initial_department = excluded.initial_department,
    current_department_id = excluded.current_department_id,
    keywords = excluded.keywords,
    summary = excluded.summary,
    updated_at = now();

commit;
