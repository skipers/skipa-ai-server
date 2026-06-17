from __future__ import annotations

import json

import pytest

from pre_application_valuation.storage import load_json, save_result


def test_save_result_writes_timestamped_file_and_latest(tmp_path) -> None:
    result = {
        "evaluation_id": "eval-1",
        "patent_title": "AI/품질 진단: 테스트",
        "artifacts": {},
    }

    output_path = save_result(result, output_dir=tmp_path)

    assert output_path.exists()
    assert output_path.parent == tmp_path
    assert "AI_품질_진단_테스트" in output_path.name
    assert result["artifacts"]["output_path"] == str(output_path)
    assert (tmp_path / "latest.json").exists()
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["evaluation_id"] == "eval-1"


def test_load_json_accepts_utf8_sig_and_requires_object(tmp_path) -> None:
    object_path = tmp_path / "object.json"
    object_path.write_text("\ufeff{\"ok\": true}", encoding="utf-8")

    assert load_json(object_path) == {"ok": True}

    list_path = tmp_path / "list.json"
    list_path.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError):
        load_json(list_path)

