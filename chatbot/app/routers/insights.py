"""Expose the standalone ai-insights API through the chatbot FastAPI app."""

from __future__ import annotations

from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import Any

from fastapi import APIRouter


_AI_INSIGHTS_PACKAGE = "_skipa_ai_insights_app"


def _load_ai_insights_package() -> str:
    if _AI_INSIGHTS_PACKAGE in sys.modules:
        return _AI_INSIGHTS_PACKAGE

    repo_root = Path(__file__).resolve().parents[3]
    package_dir = repo_root / "ai-insights" / "app"
    init_path = package_dir / "__init__.py"
    spec = spec_from_file_location(
        _AI_INSIGHTS_PACKAGE,
        init_path,
        submodule_search_locations=[str(package_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load ai-insights app package")

    module = module_from_spec(spec)
    sys.modules[_AI_INSIGHTS_PACKAGE] = module
    spec.loader.exec_module(module)
    return _AI_INSIGHTS_PACKAGE


_package_name = _load_ai_insights_package()
_schemas = import_module(f"{_package_name}.schemas")
_service = import_module(f"{_package_name}.service")

PortfolioInsightsRequest: Any = _schemas.PortfolioInsightsRequest
PortfolioInsightsResponse: Any = _schemas.PortfolioInsightsResponse
generate_portfolio_insights = _service.generate_portfolio_insights

router = APIRouter(tags=["insights"])


@router.post(
    "/portfolio/insights",
    response_model=PortfolioInsightsResponse,
    summary="포트폴리오 AI 인사이트 생성",
    description=(
        "`ai-insights` 앱의 기존 API를 챗봇 FastAPI 앱에서도 제공합니다. "
        "같은 포트의 Swagger(`/docs`)에서 재평가/사전평가 챗봇 API와 함께 확인할 수 있습니다."
    ),
)
def create_portfolio_insights(request: PortfolioInsightsRequest) -> dict[str, list[str]]:
    insights = generate_portfolio_insights(request)
    return {"insights": insights}
