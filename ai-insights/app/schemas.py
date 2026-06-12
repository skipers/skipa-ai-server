"""Request and response schemas for portfolio AI insights."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class YearlyPatentTrend(BaseModel):
    year: int
    applications: int = 0
    registrations: int = 0
    expiries: int = 0


class YearlyAnnuityCost(BaseModel):
    year: int
    amount: float = 0


class PortfolioTrends(BaseModel):
    yearlyPatentTrends: list[YearlyPatentTrend] = Field(default_factory=list)
    yearlyAnnuityCosts: list[YearlyAnnuityCost] = Field(default_factory=list)


class GradeDistributionItem(BaseModel):
    departmentId: int | None = None
    departmentName: str | None = None
    s: int = 0
    a: int = 0
    b: int = 0
    c: int = 0
    d: int = 0


class NamedCountItem(BaseModel):
    name: str
    count: int = 0


class FilingCountryItem(BaseModel):
    country: str
    count: int = 0


class DepartmentCountItem(BaseModel):
    departmentId: int | None = None
    departmentName: str
    count: int = 0


class PortfolioDistribution(BaseModel):
    byGrade: list[GradeDistributionItem] = Field(default_factory=list)
    byTechField: list[NamedCountItem] = Field(default_factory=list)
    byFilingCountry: list[FilingCountryItem] = Field(default_factory=list)
    byDepartment: list[DepartmentCountItem] = Field(default_factory=list)


class QuarterlyDecisionItem(BaseModel):
    quarter: str
    maintain: int = 0
    abandon: int = 0


class DepartmentDecisionItem(BaseModel):
    departmentId: int | None = None
    departmentName: str
    maintain: int = 0
    abandon: int = 0


class TechFieldDecisionItem(BaseModel):
    name: str
    maintain: int = 0
    abandon: int = 0


class PortfolioDecisions(BaseModel):
    byQuarter: list[QuarterlyDecisionItem] = Field(default_factory=list)
    byDepartment: list[DepartmentDecisionItem] = Field(default_factory=list)
    byTechField: list[TechFieldDecisionItem] = Field(default_factory=list)


class PortfolioInsightsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "trends": {
                        "yearlyPatentTrends": [
                            {"year": 2024, "applications": 12, "registrations": 8, "expiries": 1}
                        ],
                        "yearlyAnnuityCosts": [{"year": 2026, "amount": 1500000}],
                    },
                    "distribution": {
                        "byGrade": [
                            {
                                "departmentId": None,
                                "departmentName": "전체",
                                "s": 3,
                                "a": 12,
                                "b": 20,
                                "c": 7,
                                "d": 2,
                            }
                        ],
                        "byTechField": [{"name": "반도체", "count": 18}],
                        "byFilingCountry": [{"country": "KR", "count": 25}],
                        "byDepartment": [
                            {"departmentId": 1, "departmentName": "반도체 사업부", "count": 18}
                        ],
                    },
                    "decisions": {
                        "byQuarter": [{"quarter": "2026Q2", "maintain": 10, "abandon": 3}],
                        "byDepartment": [
                            {"departmentId": 1, "departmentName": "반도체 사업부", "maintain": 8, "abandon": 2}
                        ],
                        "byTechField": [{"name": "반도체", "maintain": 8, "abandon": 2}],
                    },
                }
            ]
        }
    )

    trends: PortfolioTrends
    distribution: PortfolioDistribution
    decisions: PortfolioDecisions


class PortfolioInsightsResponse(BaseModel):
    insights: list[str]

