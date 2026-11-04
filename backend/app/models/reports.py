from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.ask_data import QueryResultFact
from app.models.automated_insights import (
    AnomalyPattern,
    BestWorstAnalysis,
    DateMetricCombination,
    KeyFinding,
    SeasonalityAnalysis,
    TemporalAnomaly,
    TrendAnalysis,
    BusinessRecommendation,
)
from app.models.cleaning import DataQualityProfile
from app.models.dashboard import ChartConfig, DashboardKPI
from app.models.dataset import ColumnProfile


# =============================================================================
# Report Section Identifiers
# =============================================================================

class ReportSectionId(str, Enum):
    """The eight standardized report sections in AutoAnalyst AI."""
    EXECUTIVE_SUMMARY = "executive_summary"
    KEY_KPIS = "key_kpis"
    KEY_FINDINGS = "key_findings"
    CATEGORY_BENCHMARKS = "category_benchmarks"
    TRENDS_AND_SEASONALITY = "trends_and_seasonality"
    ANOMALIES_AND_RISKS = "anomalies_and_risks"
    RECOMMENDATIONS = "recommendations"
    DATA_QUALITY_AUDIT = "data_quality_audit"


ALL_REPORT_SECTIONS: List[ReportSectionId] = [
    ReportSectionId.EXECUTIVE_SUMMARY,
    ReportSectionId.KEY_KPIS,
    ReportSectionId.KEY_FINDINGS,
    ReportSectionId.CATEGORY_BENCHMARKS,
    ReportSectionId.TRENDS_AND_SEASONALITY,
    ReportSectionId.ANOMALIES_AND_RISKS,
    ReportSectionId.RECOMMENDATIONS,
    ReportSectionId.DATA_QUALITY_AUDIT,
]


# =============================================================================
# Report Configuration Request
# =============================================================================

class ReportConfigRequest(BaseModel):
    """User configuration for executive report assembly and export."""
    title: str = Field(
        default="Executive Intelligence Report",
        max_length=150,
        description="Executive report title (max 150 characters)",
    )
    subtitle: Optional[str] = Field(
        default=None,
        max_length=250,
        description="Optional custom subtitle or business context (max 250 characters)",
    )
    selected_sections: List[ReportSectionId] = Field(
        default_factory=lambda: list(ALL_REPORT_SECTIONS),
        description="Standardized report sections to include (defaults to all eight)",
    )
    include_charts: bool = Field(
        default=True,
        description="Whether to include visual chart configurations in the report",
    )
    date_range_start: Optional[str] = Field(
        default=None,
        description="Optional start date filter (YYYY-MM-DD or ISO 8601)",
    )
    date_range_end: Optional[str] = Field(
        default=None,
        description="Optional end date filter (YYYY-MM-DD or ISO 8601)",
    )
    confidentiality_notice: Optional[str] = Field(
        default="CONFIDENTIAL & PROPRIETARY — FOR INTERNAL USE ONLY",
        max_length=200,
        description="Confidentiality statement displayed on report cover and headers (max 200 characters)",
    )
    target_metric_col: Optional[str] = Field(
        default=None,
        description="Optional numerical metric for focused KPI and benchmark analysis",
    )
    target_date_col: Optional[str] = Field(
        default=None,
        description="Optional datetime column for focused trend analysis",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            return "Executive Intelligence Report"
        return clean

    @field_validator("date_range_start", "date_range_end")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip()
        if not v_clean:
            return None
        try:
            parsed = pd.to_datetime(v_clean)
            if pd.isna(parsed):
                raise ValueError(f"Invalid date format '{v}'.")
        except Exception:
            raise ValueError(
                f"Invalid date format '{v}'. Expected YYYY-MM-DD or ISO 8601 format."
            )
        return v_clean

    @model_validator(mode="after")
    def validate_date_range(self) -> "ReportConfigRequest":
        if self.date_range_start and self.date_range_end:
            start_dt = pd.to_datetime(self.date_range_start)
            end_dt = pd.to_datetime(self.date_range_end)
            if end_dt < start_dt:
                raise ValueError(
                    f"Date range end '{self.date_range_end}' cannot be earlier than start '{self.date_range_start}'."
                )
        return self


# =============================================================================
# Individual Report Section Models (Eight Standardized Sections)
# =============================================================================

class ReportExecutiveSummary(BaseModel):
    """Section 1: Executive Summary & Strategic Narrative."""
    narrative: str = Field(..., description="High-level narrative executive briefing")
    mode: Literal["ai_generated", "statistical_fallback"] = "statistical_fallback"
    provider: Optional[str] = None
    model: Optional[str] = None
    health_score: float = 100.0
    key_takeaways: List[str] = Field(default_factory=list, description="Top strategic takeaways")


class ReportKeyKPIs(BaseModel):
    """Section 2: Executive KPI Cards & Selected Metric Statistics."""
    kpis: DashboardKPI = Field(..., description="Core dashboard KPI metrics")
    health_score: float = 100.0
    selected_column: Optional[str] = None


class ReportKeyFindings(BaseModel):
    """Section 3: Automated Key Findings ranked by significance."""
    findings: List[KeyFinding] = Field(default_factory=list)
    total_count: int = 0
    high_importance_count: int = 0


class ReportCategoryBenchmarks(BaseModel):
    """Section 4: Best and Worst Category Benchmarks."""
    benchmarks: List[BestWorstAnalysis] = Field(default_factory=list)
    dimension_count: int = 0


class ReportTrendsSeasonality(BaseModel):
    """Section 5: Temporal Trends, Statistical Significance, and Seasonality."""
    has_temporal_data: bool = False
    trends: List[TrendAnalysis] = Field(default_factory=list)
    seasonality: Optional[SeasonalityAnalysis] = None
    available_combinations: List[DateMetricCombination] = Field(default_factory=list)


class ReportAnomaliesRisks(BaseModel):
    """Section 6: Categorical, Skewness, and Temporal Anomalies."""
    anomalies: List[AnomalyPattern] = Field(default_factory=list, description="Cross-sectional anomalies")
    temporal_anomalies: List[TemporalAnomaly] = Field(default_factory=list, description="Time-series spikes and drops")
    total_anomaly_count: int = 0
    critical_count: int = 0
    warning_count: int = 0


class ReportRecommendations(BaseModel):
    """Section 7: Actionable Business Recommendations."""
    recommendations: List[BusinessRecommendation] = Field(default_factory=list)
    total_count: int = 0
    high_priority_count: int = 0
    empirical_facts_count: int = 0
    analytical_hypotheses_count: int = 0


class ReportDataQualityAudit(BaseModel):
    """Section 8: Comprehensive Data Quality & Health Audit."""
    quality_profile: Optional[DataQualityProfile] = None
    overall_quality_score: float = 100.0
    quality_grade: str = "Excellent"
    completeness_score: float = 100.0
    uniqueness_score: float = 100.0
    validity_score: float = 100.0
    column_count: int = 0
    missing_cells: int = 0
    duplicate_rows: int = 0


# =============================================================================
# Complete Executive Report Data Model
# =============================================================================

class ExecutiveReportData(BaseModel):
    """
    Unified executive business intelligence report data structure.
    Assembled deterministically from verified analytical engines across Phases 1–4.4.
    """
    report_id: str = Field(..., description="Unique executive report identifier")
    dataset_id: str = Field(..., description="Requested dataset ID")
    active_dataset_id: str = Field(..., description="Resolved active dataset ID (clean_{id} or raw)")
    dataset_name: str = Field(..., description="Dataset filename")
    snapshot_hash: str = Field(..., description="SHA-256 snapshot hash of the active dataset file")
    is_cleaned: bool = Field(default=False, description="True if based on an active cleaned snapshot")
    cleaning_version: int = Field(default=0, description="Cleaned dataset version number")
    generated_at: str = Field(..., description="ISO 8601 generation timestamp")

    # Branding
    brand_name: str = Field(default="AutoAnalyst AI", description="Product name")
    brand_tagline: str = Field(default="Your Autonomous Data Analyst", description="Product tagline")
    brand_attribution: str = Field(default="Powered by Saniya", description="Brand attribution")
    confidentiality_notice: Optional[str] = Field(
        default="CONFIDENTIAL & PROPRIETARY — FOR INTERNAL USE ONLY",
        description="Confidentiality banner text",
    )

    # Configuration used for assembly
    config: ReportConfigRequest = Field(..., description="User configuration applied to this report")
    health_score: float = Field(default=100.0, description="Overall dataset health score (0-100)")

    # The Eight Standardized Report Sections (None if excluded by user config)
    executive_summary: Optional[ReportExecutiveSummary] = None
    key_kpis: Optional[ReportKeyKPIs] = None
    key_findings: Optional[ReportKeyFindings] = None
    category_benchmarks: Optional[ReportCategoryBenchmarks] = None
    trends_and_seasonality: Optional[ReportTrendsSeasonality] = None
    anomalies_and_risks: Optional[ReportAnomaliesRisks] = None
    recommendations: Optional[ReportRecommendations] = None
    data_quality_audit: Optional[ReportDataQualityAudit] = None

    # Supporting metadata & schemas
    columns: List[ColumnProfile] = Field(default_factory=list, description="Dataset column profiles")
    charts: List[ChartConfig] = Field(default_factory=list, description="Visual Plotly chart configurations")
    grounded_facts: List[QueryResultFact] = Field(default_factory=list, description="Verified fact provenance registry")
    limitations: List[str] = Field(default_factory=list, description="General analytical limitations")
    date_scoping_limitations: List[str] = Field(default_factory=list, description="Disclaimers regarding date filtering scope")

    @property
    def section_inclusion_status(self) -> Dict[str, bool]:
        """Convenience map of which standardized sections are populated."""
        return {
            ReportSectionId.EXECUTIVE_SUMMARY.value: self.executive_summary is not None,
            ReportSectionId.KEY_KPIS.value: self.key_kpis is not None,
            ReportSectionId.KEY_FINDINGS.value: self.key_findings is not None,
            ReportSectionId.CATEGORY_BENCHMARKS.value: self.category_benchmarks is not None,
            ReportSectionId.TRENDS_AND_SEASONALITY.value: self.trends_and_seasonality is not None,
            ReportSectionId.ANOMALIES_AND_RISKS.value: self.anomalies_and_risks is not None,
            ReportSectionId.RECOMMENDATIONS.value: self.recommendations is not None,
            ReportSectionId.DATA_QUALITY_AUDIT.value: self.data_quality_audit is not None,
        }

