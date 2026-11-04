import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import pandas as pd

from app.models.cleaning import DataQualityProfile
from app.models.dashboard import ChartConfig, DashboardKPI
from app.models.reports import (
    ALL_REPORT_SECTIONS,
    ExecutiveReportData,
    ReportAnomaliesRisks,
    ReportCategoryBenchmarks,
    ReportConfigRequest,
    ReportDataQualityAudit,
    ReportExecutiveSummary,
    ReportKeyFindings,
    ReportKeyKPIs,
    ReportRecommendations,
    ReportSectionId,
    ReportTrendsSeasonality,
)
from app.services.ai.insights_synthesizer import InsightsSynthesizer
from app.services.cleaning_service import CleaningService
from app.services.dashboard_service import dashboard_service
from app.services.dataset_storage import dataset_storage


class ReportAssemblyService:
    """
    Coordinates unified executive intelligence report assembly.
    Aggregates verified analytical results across Phases 1 through 4.4
    without duplicating numerical computations.
    Enforces strict active dataset snapshot integrity and fact provenance.
    """

    @classmethod
    def resolve_active_dataset(cls, dataset_id: str) -> Tuple[str, bool, str, Path]:
        """
        Resolves the active dataset version (cleaned if active, otherwise original)
        and verifies the underlying file and SHA-256 snapshot hash.
        
        Returns:
            Tuple of (active_id, is_cleaned, snapshot_hash, file_path)
        """
        clean_id = f"clean_{dataset_id}"
        is_cleaned = bool(dataset_storage.get_dataset(clean_id))
        active_id = clean_id if is_cleaned else dataset_id

        detail = dataset_storage.get_dataset(active_id)
        if not detail:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        file_path = dataset_storage.get_dataset_file_path(active_id)
        if not file_path.exists():
            raise ValueError(f"Dataset file for '{active_id}' does not exist on disk.")

        snapshot_hash = dataset_storage.compute_sha256(file_path)
        if not snapshot_hash:
            raise ValueError(f"Failed to compute snapshot hash for dataset '{active_id}'.")

        return active_id, is_cleaned, snapshot_hash, file_path

    @classmethod
    async def assemble_report(
        cls,
        dataset_id: str,
        config: Optional[ReportConfigRequest] = None,
        force_refresh: bool = False,
    ) -> ExecutiveReportData:
        """
        Assembles a comprehensive, fact-grounded executive report.
        
        Guarantees:
        - Exactly one snapshot hash across all sections.
        - Fails safely if snapshot changes during assembly.
        - No duplicate numerical calculations (reuses Pandas/NumPy engines).
        - Explicit date-scoping disclaimers.
        - Safe representation of non-temporal and missing data.
        - Preserves empirical fact vs analytical hypothesis distinction.
        """
        cfg = config or ReportConfigRequest()
        selected: Set[ReportSectionId] = set(cfg.selected_sections)

        # 1. Resolve active dataset exactly once
        active_id, is_cleaned, initial_snapshot_hash, file_path = cls.resolve_active_dataset(dataset_id)
        detail = dataset_storage.get_dataset(active_id)
        if not detail:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        # 2. Load DataFrame
        df = dataset_storage._load_dataframe(active_id)

        # 3. Snapshot safeguard before calling analytical engines
        current_hash = dataset_storage.compute_sha256(file_path)
        if current_hash != initial_snapshot_hash:
            raise ValueError(
                f"Dataset snapshot changed during report initialization "
                f"(initial {initial_snapshot_hash[:12]} vs current {current_hash[:12]}). "
                f"Aborted to prevent mixed report state."
            )

        # 4. Handle completely empty dataset edge case
        if df.empty or len(df.columns) == 0:
            return cls._build_empty_dataset_report(
                dataset_id=dataset_id,
                active_id=active_id,
                filename=detail.overview.filename,
                snapshot_hash=initial_snapshot_hash,
                is_cleaned=is_cleaned,
                cleaning_version=detail.overview.version,
                config=cfg,
            )

        # 5. Retrieve verified automated insights via InsightsSynthesizer
        insights_res = await InsightsSynthesizer.get_or_generate_insights(
            dataset_id=dataset_id,
            force_refresh=force_refresh,
            date_col=cfg.target_date_col,
            metric_col=cfg.target_metric_col,
        )

        # 6. Verify insights snapshot consistency
        if insights_res.snapshot_hash != initial_snapshot_hash:
            # Stale cache detected; force re-generation with current active snapshot
            insights_res = await InsightsSynthesizer.get_or_generate_insights(
                dataset_id=dataset_id,
                force_refresh=True,
                date_col=cfg.target_date_col,
                metric_col=cfg.target_metric_col,
            )
            if insights_res.snapshot_hash != initial_snapshot_hash:
                raise ValueError(
                    f"Snapshot consistency failure: insights snapshot hash '{insights_res.snapshot_hash[:12]}' "
                    f"does not match active dataset file hash '{initial_snapshot_hash[:12]}'."
                )

        # 7. Retrieve Dashboard KPIs via DashboardService
        kpis = dashboard_service.calculate_kpis(df, selected_col=cfg.target_metric_col)

        # 8. Retrieve Recommended Visual Charts (if requested)
        charts: List[ChartConfig] = []
        if cfg.include_charts:
            charts = dashboard_service.recommend_charts(df, max_charts=4)

        # 9. Retrieve Data Quality Profile via CleaningService
        orig_id = detail.overview.parent_id if (detail.overview.is_cleaned and detail.overview.parent_id) else dataset_id
        orig_detail = dataset_storage.get_dataset(orig_id)
        orig_path = dataset_storage.get_dataset_file_path(orig_detail.overview.id if orig_detail else orig_id)
        orig_hash = dataset_storage.compute_sha256(orig_path)
        
        quality_profile = CleaningService.calculate_quality_profile(
            df=df,
            dataset_id=detail.overview.id,
            filename=detail.overview.filename,
            is_cleaned=detail.overview.is_cleaned,
            version=detail.overview.version,
            parent_id=detail.overview.parent_id,
            original_file_hash=orig_hash,
        )

        # 10. Snapshot check after all analytical operations
        post_assembly_hash = dataset_storage.compute_sha256(file_path)
        if post_assembly_hash != initial_snapshot_hash:
            raise ValueError(
                f"Dataset snapshot changed during report assembly "
                f"(initial {initial_snapshot_hash[:12]} vs post-assembly {post_assembly_hash[:12]}). "
                f"Operation aborted to prevent mixed snapshot state."
            )

        # 11. Assemble the Eight Standardized Sections Respecting User Config

        # --- Section 1: Executive Summary ---
        exec_summary: Optional[ReportExecutiveSummary] = None
        if ReportSectionId.EXECUTIVE_SUMMARY in selected:
            takeaways = [
                f.title for f in insights_res.key_findings if f.importance == "high"
            ][:4]
            if not takeaways and insights_res.key_findings:
                takeaways = [f.title for f in insights_res.key_findings[:3]]
            
            narrative = insights_res.executive_summary
            if not narrative:
                narrative = (
                    f"Automated executive analysis of {detail.overview.filename} comprising "
                    f"{len(df):,} records and {len(df.columns)} analytical attributes."
                )

            exec_summary = ReportExecutiveSummary(
                narrative=narrative,
                mode=insights_res.mode,
                provider=insights_res.provider,
                model=insights_res.model,
                health_score=insights_res.health_score,
                key_takeaways=takeaways,
            )

        # --- Section 2: Key KPIs ---
        key_kpis: Optional[ReportKeyKPIs] = None
        if ReportSectionId.KEY_KPIS in selected:
            key_kpis = ReportKeyKPIs(
                kpis=kpis,
                health_score=insights_res.health_score,
                selected_column=cfg.target_metric_col or kpis.selected_column,
            )

        # --- Section 3: Key Findings ---
        key_findings: Optional[ReportKeyFindings] = None
        if ReportSectionId.KEY_FINDINGS in selected:
            findings_list = list(insights_res.key_findings)
            high_imp = sum(1 for f in findings_list if f.importance == "high")
            key_findings = ReportKeyFindings(
                findings=findings_list,
                total_count=len(findings_list),
                high_importance_count=high_imp,
            )

        # --- Section 4: Category Benchmarks ---
        category_benchmarks: Optional[ReportCategoryBenchmarks] = None
        if ReportSectionId.CATEGORY_BENCHMARKS in selected:
            benchmarks = [copy.deepcopy(b) for b in insights_res.best_worst_analyses]
            if not cfg.include_charts:
                for b in benchmarks:
                    b.chart = None
            category_benchmarks = ReportCategoryBenchmarks(
                benchmarks=benchmarks,
                dimension_count=len(benchmarks),
            )

        # --- Section 5: Trends & Seasonality ---
        trends_seasonality: Optional[ReportTrendsSeasonality] = None
        if ReportSectionId.TRENDS_AND_SEASONALITY in selected:
            trends = [copy.deepcopy(t) for t in insights_res.trends]
            seasonality = copy.deepcopy(insights_res.seasonality)
            if not cfg.include_charts:
                for t in trends:
                    t.chart = None
                if seasonality:
                    seasonality.chart = None
            trends_seasonality = ReportTrendsSeasonality(
                has_temporal_data=insights_res.has_temporal_data,
                trends=trends,
                seasonality=seasonality,
                available_combinations=insights_res.available_combinations,
            )

        # --- Section 6: Anomalies & Risks ---
        anomalies_risks: Optional[ReportAnomaliesRisks] = None
        if ReportSectionId.ANOMALIES_AND_RISKS in selected:
            anomalies = list(insights_res.anomalies_and_patterns)
            temp_anomalies = list(insights_res.temporal_anomalies)
            crit_count = sum(1 for a in anomalies if a.severity == "critical") + sum(1 for ta in temp_anomalies if ta.severity == "critical")
            warn_count = sum(1 for a in anomalies if a.severity == "warning") + sum(1 for ta in temp_anomalies if ta.severity == "warning")
            anomalies_risks = ReportAnomaliesRisks(
                anomalies=anomalies,
                temporal_anomalies=temp_anomalies,
                total_anomaly_count=len(anomalies) + len(temp_anomalies),
                critical_count=crit_count,
                warning_count=warn_count,
            )

        # --- Section 7: Recommendations ---
        recommendations: Optional[ReportRecommendations] = None
        if ReportSectionId.RECOMMENDATIONS in selected:
            recs = list(insights_res.recommendations)
            high_prio = sum(1 for r in recs if r.priority == "high")
            hypo_count = sum(1 for r in recs if r.is_hypothesis)
            emp_count = sum(1 for r in recs if not r.is_hypothesis)
            recommendations = ReportRecommendations(
                recommendations=recs,
                total_count=len(recs),
                high_priority_count=high_prio,
                empirical_facts_count=emp_count,
                analytical_hypotheses_count=hypo_count,
            )

        # --- Section 8: Data Quality Audit ---
        data_quality_audit: Optional[ReportDataQualityAudit] = None
        if ReportSectionId.DATA_QUALITY_AUDIT in selected:
            data_quality_audit = ReportDataQualityAudit(
                quality_profile=quality_profile,
                overall_quality_score=quality_profile.quality_metrics.overall_quality_score,
                quality_grade=quality_profile.quality_metrics.quality_grade,
                completeness_score=quality_profile.quality_metrics.completeness_score,
                uniqueness_score=quality_profile.quality_metrics.uniqueness_score,
                validity_score=quality_profile.quality_metrics.validity_score,
                column_count=quality_profile.total_columns,
                missing_cells=quality_profile.total_missing_cells,
                duplicate_rows=quality_profile.duplicate_rows,
            )

        # 12. Date-Range Honesty & Analytical Disclaimers
        date_limitations: List[str] = []
        if cfg.date_range_start or cfg.date_range_end:
            start_desc = cfg.date_range_start or "earliest available"
            end_desc = cfg.date_range_end or "latest available"
            date_limitations.append(
                f"Configured reporting date window: {start_desc} to {end_desc}. "
                f"Analytical notice: Statistical findings, benchmarks, and data quality audits "
                f"are evaluated across the complete verified snapshot ({len(df):,} records) "
                f"to preserve statistical sample reliability and benchmark validity."
            )

        # 13. General Analytical Limitations
        general_limitations = list(insights_res.limitations)
        if not insights_res.has_temporal_data:
            general_limitations.append(
                "Dataset contains no valid datetime columns; chronological trend and seasonality analytics are unavailable."
            )

        # 14. Preserve Grounded Facts Registry (Strict Provenance)
        grounded_facts = list(insights_res.grounded_facts)

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        return ExecutiveReportData(
            report_id=report_id,
            dataset_id=dataset_id,
            active_dataset_id=active_id,
            dataset_name=detail.overview.filename,
            snapshot_hash=initial_snapshot_hash,
            is_cleaned=is_cleaned,
            cleaning_version=detail.overview.version,
            generated_at=now_iso,
            brand_name="AutoAnalyst AI",
            brand_tagline="Your Autonomous Data Analyst",
            brand_attribution="Powered by Saniya",
            confidentiality_notice=cfg.confidentiality_notice,
            config=cfg,
            health_score=insights_res.health_score,
            executive_summary=exec_summary,
            key_kpis=key_kpis,
            key_findings=key_findings,
            category_benchmarks=category_benchmarks,
            trends_and_seasonality=trends_seasonality,
            anomalies_and_risks=anomalies_risks,
            recommendations=recommendations,
            data_quality_audit=data_quality_audit,
            columns=detail.columns,
            charts=charts if cfg.include_charts else [],
            grounded_facts=grounded_facts,
            limitations=general_limitations,
            date_scoping_limitations=date_limitations,
        )

    @classmethod
    def _build_empty_dataset_report(
        cls,
        dataset_id: str,
        active_id: str,
        filename: str,
        snapshot_hash: str,
        is_cleaned: bool,
        cleaning_version: int,
        config: ReportConfigRequest,
    ) -> ExecutiveReportData:
        """Safely assembles an empty report for 0-row or empty datasets without failing."""
        empty_kpi = DashboardKPI(
            total_rows=0,
            total_columns=0,
            total_cells=0,
            missing_cells=0,
            missing_percentage=0.0,
            duplicate_rows=0,
            duplicate_percentage=0.0,
            data_completeness=0.0,
            selected_column=None,
            selected_column_stats=None,
        )
        selected = set(config.selected_sections)
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        exec_summary = None
        if ReportSectionId.EXECUTIVE_SUMMARY in selected:
            exec_summary = ReportExecutiveSummary(
                narrative=f"The dataset '{filename}' contains no rows or data cells. Analytical processing cannot be performed.",
                mode="statistical_fallback",
                health_score=0.0,
                key_takeaways=["Dataset is empty."],
            )

        key_kpis = None
        if ReportSectionId.KEY_KPIS in selected:
            key_kpis = ReportKeyKPIs(
                kpis=empty_kpi,
                health_score=0.0,
                selected_column=None,
            )

        data_quality_audit = None
        if ReportSectionId.DATA_QUALITY_AUDIT in selected:
            data_quality_audit = ReportDataQualityAudit(
                quality_profile=None,
                overall_quality_score=0.0,
                quality_grade="Needs Attention",
                completeness_score=0.0,
                uniqueness_score=0.0,
                validity_score=0.0,
                column_count=0,
                missing_cells=0,
                duplicate_rows=0,
            )

        return ExecutiveReportData(
            report_id=report_id,
            dataset_id=dataset_id,
            active_dataset_id=active_id,
            dataset_name=filename,
            snapshot_hash=snapshot_hash,
            is_cleaned=is_cleaned,
            cleaning_version=cleaning_version,
            generated_at=now_iso,
            brand_name="AutoAnalyst AI",
            brand_tagline="Your Autonomous Data Analyst",
            brand_attribution="Powered by Saniya",
            confidentiality_notice=config.confidentiality_notice,
            config=config,
            health_score=0.0,
            executive_summary=exec_summary,
            key_kpis=key_kpis,
            key_findings=ReportKeyFindings() if ReportSectionId.KEY_FINDINGS in selected else None,
            category_benchmarks=ReportCategoryBenchmarks() if ReportSectionId.CATEGORY_BENCHMARKS in selected else None,
            trends_and_seasonality=ReportTrendsSeasonality() if ReportSectionId.TRENDS_AND_SEASONALITY in selected else None,
            anomalies_and_risks=ReportAnomaliesRisks() if ReportSectionId.ANOMALIES_AND_RISKS in selected else None,
            recommendations=ReportRecommendations() if ReportSectionId.RECOMMENDATIONS in selected else None,
            data_quality_audit=data_quality_audit,
            columns=[],
            charts=[],
            grounded_facts=[],
            limitations=["Dataset is empty (contains zero rows or columns)."],
            date_scoping_limitations=[],
        )
