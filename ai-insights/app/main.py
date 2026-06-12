"""FastAPI entrypoint for AI portfolio insights."""

from __future__ import annotations

from fastapi import FastAPI

from .schemas import PortfolioInsightsRequest, PortfolioInsightsResponse
from .service import generate_portfolio_insights


app = FastAPI(
    title="SKIPA AI Portfolio Insights API",
    description="Portfolio trend/distribution/decision data to Korean AI insight lines.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/portfolio/insights", response_model=PortfolioInsightsResponse, tags=["portfolio"])
def create_portfolio_insights(request: PortfolioInsightsRequest) -> dict[str, list[str]]:
    insights = generate_portfolio_insights(request)
    return {"insights": insights}

