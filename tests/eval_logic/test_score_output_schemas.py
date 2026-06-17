from __future__ import annotations

from core.schemas import CollectedEvidence, EvaluationStepResult, PatentEvaluationOutput, ScoreItem


def test_score_item_from_dict_clamps_score_and_filters_sources() -> None:
    score = ScoreItem.from_dict(
        {
            "item": "기술성",
            "dim": "기술성",
            "score": 9,
            "method": "auto",
            "sources": [{"url": "https://example.com"}, "bad-source"],
        }
    )

    assert score.score == 5
    assert score.sources == [{"url": "https://example.com"}]
    assert score.to_dict()["score"] == 5


def test_collected_evidence_to_dict_omits_empty_values() -> None:
    evidence = CollectedEvidence(
        patent_metadata={"title": "테스트 특허"},
        sources=[],
        errors=[],
    )

    assert evidence.to_dict() == {"patent_metadata": {"title": "테스트 특허"}}


def test_evaluation_step_result_rounds_elapsed_seconds() -> None:
    step = EvaluationStepResult(name="score", status="success", elapsed_seconds=1.236, message="done")

    assert step.to_dict() == {
        "name": "score",
        "status": "success",
        "elapsed_seconds": 1.24,
        "message": "done",
    }


def test_patent_evaluation_output_serializes_nested_scores_and_steps() -> None:
    output = PatentEvaluationOutput(
        patent_id="10-1234567",
        title="테스트 특허",
        auto_scores=[ScoreItem.from_dict({"item": "기술 구체성", "dim": "기술성", "score": 4, "method": "auto"})],
        llm_scores=[ScoreItem.from_dict({"item": "사업성", "dim": "사업성", "score": 3, "method": "llm"})],
        steps=[EvaluationStepResult(name="run", status="success", elapsed_seconds=0.1)],
        input_file="input.json",
    )

    dumped = output.to_dict()

    assert dumped["patent_id"] == "10-1234567"
    assert len(output.all_scores()) == 2
    assert dumped["auto_scores"][0]["item"] == "기술 구체성"
    assert dumped["summary"]["steps"][0]["name"] == "run"
    assert dumped["input_file"] == "input.json"

