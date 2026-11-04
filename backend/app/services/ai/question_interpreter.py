import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from app.models.ask_data import (
    QueryChartRecommendation,
    QueryFilterCondition,
    QueryPlan,
    QuerySortRule,
)
from app.models.dataset import ColumnProfile
from app.services.ai.base_provider import BaseLLMProvider


class HeuristicQuestionInterpreter:
    """
    Deterministic rule-based query interpreter for offline and fallback execution.
    Recognizes common natural language data questions and maps them safely to QueryPlans.
    """

    MEDIA_URL_TOKENS = {
        "url", "logo", "image", "avatar", "icon", "website", "web_site",
        "link", "id", "uuid", "key", "hash", "photo", "pic", "thumbnail",
    }

    ENTITY_SYNONYMS = {
        "company": ["company", "companies", "firm", "firms", "organization", "organizations", "enterprise", "enterprises", "employer", "employers", "business", "businesses", "vendor", "vendors", "corp"],
        "customer": ["customer", "customers", "client", "clients", "buyer", "buyers", "user", "users", "consumer", "consumers"],
        "product": ["product", "products", "item", "items", "good", "goods", "merchandise"],
        "country": ["country", "countries", "nation", "nations", "origin", "territory"],
        "city": ["city", "cities", "town", "towns", "metro", "municipality"],
        "name": ["name", "names", "title", "titles", "label", "labels"],
    }

    @classmethod
    def stem_word(cls, word: str) -> str:
        """Simple English stemmer for plurals and common suffixes."""
        w = word.lower().strip()
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y"
        elif w.endswith("es") and len(w) > 3 and not w.endswith("ses"):
            return w[:-2]
        elif w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            return w[:-1]
        return w

    @classmethod
    def clean_text_token(cls, text: str) -> str:
        """Strip punctuation and possessives ('s, ’s) to normalize tokens."""
        text = re.sub(r"['’]s\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.lower().split())

    @classmethod
    def find_matching_column(
        cls,
        text: str,
        columns: List[ColumnProfile],
        prefer_entity: bool = True,
        required_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Smart column matcher with entity disambiguation and media/URL penalization.
        Prioritizes meaningful entity names (e.g. 'Company Name') over technical fields ('Company Logo (URL)').
        """
        if not columns:
            return None

        cleaned_query = cls.clean_text_token(text)
        query_raw_tokens = set(cleaned_query.split())
        query_stemmed_tokens = {cls.stem_word(t) for t in query_raw_tokens}

        # Check if query specifically asks for media/URL fields
        user_wants_media = any(t in query_raw_tokens for t in {"logo", "url", "image", "website", "link", "photo"})

        best_col: Optional[str] = None
        best_score = -1.0

        for col_prof in columns:
            col_orig = col_prof.name
            cleaned_col = cls.clean_text_token(col_orig)
            col_raw_tokens = set(cleaned_col.split())
            col_stemmed_tokens = {cls.stem_word(t) for t in col_raw_tokens}

            if required_type and col_prof.data_type != required_type:
                continue

            score = 0.0

            # 1. Exact phrase sequence match in text (Full exact match takes highest priority!)
            if cleaned_col == cleaned_query or col_orig.lower() == text.lower().strip():
                score += 200.0
            elif cleaned_col in cleaned_query:
                score += 150.0
            else:
                # Stemmed token overlap
                common_stems = query_stemmed_tokens.intersection(col_stemmed_tokens)
                if common_stems:
                    token_overlap_ratio = len(common_stems) / max(len(col_stemmed_tokens), 1)
                    score += 50.0 + (token_overlap_ratio * 30.0)

                # Entity synonym matching
                for entity_key, syn_list in cls.ENTITY_SYNONYMS.items():
                    syn_stems = {cls.stem_word(s) for s in syn_list}
                    if query_stemmed_tokens.intersection(syn_stems):
                        if col_stemmed_tokens.intersection(syn_stems) or cls.stem_word(entity_key) in col_stemmed_tokens:
                            score += 25.0

            # 2. Priority boost for 'name' or 'title' columns when query is looking for an entity
            if prefer_entity and any(t in col_raw_tokens for t in {"name", "title"}):
                score += 20.0

            # 3. Penalize media, URL, and technical identifier columns unless explicitly requested
            has_media_token = any(m in col_raw_tokens for m in cls.MEDIA_URL_TOKENS)
            if has_media_token and not user_wants_media:
                score -= 85.0

            # Prefer string/categorical columns if searching for entities
            if prefer_entity and col_prof.data_type == "string":
                score += 5.0

            if score > best_score:
                best_score = score
                best_col = col_orig

        # Minimum confidence threshold
        if best_score >= 35.0:
            return best_col

        return None

    @classmethod
    def interpret(
        cls,
        question: str,
        columns: List[ColumnProfile],
        recent_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> QueryPlan:
        q_lower = question.lower().strip()
        plan_id = f"plan_{uuid.uuid4().hex[:10]}"
        numeric_cols = [c.name for c in columns if c.data_type in ("integer", "float")]
        cat_cols = [c.name for c in columns if c.data_type in ("string", "boolean")]
        date_cols = [c.name for c in columns if c.data_type == "datetime"]

        # Clean non-media categorical candidates
        clean_cat_cols = [c for c in cat_cols if not any(m in c.lower() for m in cls.MEDIA_URL_TOKENS)]
        default_cat_col = clean_cat_cols[0] if clean_cat_cols else (cat_cols[0] if cat_cols else None)

        # Context inheritance for follow-up questions (e.g., "now by class", "what about gender?")
        inherited_primary: Optional[str] = None
        inherited_op: Optional[str] = None
        if recent_messages:
            for prev_msg in reversed(recent_messages):
                if prev_msg.get("columns_used"):
                    inherited_primary = prev_msg["columns_used"][0]
                    prev_method = prev_msg.get("calculation_method", "").lower()
                    for op_word in ("mean", "average", "sum", "total", "count", "median", "max", "min"):
                        if op_word in prev_method:
                            inherited_op = "mean" if op_word == "average" else ("sum" if op_word == "total" else op_word)
                            break
                    break

        # =========================================================================
        # 1. BROAD ANALYTICAL INSIGHTS & BUSINESS INTELLIGENCE (PHASE 4.3)
        # =========================================================================
        # 1A. Automated Insights / Important Findings
        insights_patterns = [
            r"what are the (?:most )?important findings",
            r"key (?:findings|insights)",
            r"what are the key insights",
            r"most important insights",
            r"discover insights",
            r"top findings",
            r"main findings",
            r"automated insights",
            r"what does the data reveal",
            r"what insights can you find",
        ]
        if any(re.search(pat, q_lower) for pat in insights_patterns):
            return QueryPlan(
                plan_id=plan_id,
                intent="automated_insights",
                operation="discover_insights",
                chart=QueryChartRecommendation(chart_type="none"),
            )

        # 1B. Best and Worst Performing Categories
        best_worst_patterns = [
            r"which categories perform (?:the )?best and (?:the )?worst",
            r"which categories perform best and worst",
            r"which category performs (?:the )?best",
            r"which category performs (?:the )?worst",
            r"best and worst (?:performing )?categories",
            r"top and bottom (?:performing )?categories",
            r"highest and lowest performing categories",
            r"performance comparison across categories",
            r"best performing",
            r"worst performing",
        ]
        if any(re.search(pat, q_lower) for pat in best_worst_patterns):
            return QueryPlan(
                plan_id=plan_id,
                intent="best_worst_performers",
                operation="benchmark_performers",
                chart=QueryChartRecommendation(chart_type="bar"),
            )

        # 1C. Anomaly & Unusual Pattern Detection
        anomaly_patterns = [
            r"are there (?:any )?unusual patterns",
            r"unusual patterns",
            r"are there (?:any )?anomalies",
            r"are there (?:any )?outliers",
            r"detect anomalies",
            r"detect outliers",
            r"what are the anomalies",
            r"anomaly detection",
            r"outlier detection",
        ]
        if any(re.search(pat, q_lower) for pat in anomaly_patterns):
            return QueryPlan(
                plan_id=plan_id,
                intent="anomaly_detection",
                operation="detect_anomalies",
                chart=QueryChartRecommendation(chart_type="none"),
            )

        # 1D. Actionable Recommendations
        recommendation_patterns = [
            r"what actions would you recommend",
            r"what do you recommend",
            r"what are your recommendations",
            r"what recommendations (?:do you have|based on)",
            r"actionable recommendations",
            r"suggested actions",
            r"business recommendations",
            r"what should we do based on (?:the )?data",
            r"^recommendations$",
        ]
        if any(re.search(pat, q_lower) for pat in recommendation_patterns):
            return QueryPlan(
                plan_id=plan_id,
                intent="business_recommendations",
                operation="recommend_actions",
                chart=QueryChartRecommendation(chart_type="none"),
            )

        # 1E. Data Quality Issues Audit
        quality_patterns = [
            r"what are the (?:most )?important data[\s_-]?quality issues",
            r"data quality issues",
            r"data quality problems",
            r"quality audit",
            r"data quality audit",
            r"data health",
        ]
        if any(re.search(pat, q_lower) for pat in quality_patterns):
            return QueryPlan(
                plan_id=plan_id,
                intent="data_quality_insights",
                operation="data_quality_audit",
                chart=QueryChartRecommendation(chart_type="none"),
            )

        # =========================================================================
        # 1F. TEMPORAL TRENDS, ANOMALIES & SEASONALITY (PHASE 4.4)
        # =========================================================================
        # 1F.1 Trend Analysis (e.g. "Is revenue increasing or decreasing over time?")
        trend_patterns = [
            r"is (?:the\s+)?(?:\w+\s+)?(?:increasing|decreasing|growing|falling|dropping|trending) over time",
            r"trend over time",
            r"(?:what is the|show me the|analyze)?\s*trend",
            r"how (?:is|has) .*? changed over time",
            r"over time",
            r"temporal trend",
            r"time series",
        ]
        if any(re.search(pat, q_lower) for pat in trend_patterns):
            # Extract target metric if mentioned
            metric_target = cls.find_matching_column(question, [c for c in columns if c.data_type in ("integer", "float")], prefer_entity=False)
            date_target = cls.find_matching_column(question, [c for c in columns if c.data_type == "datetime" or any(w in c.name.lower() for w in ("date", "time", "timestamp"))], prefer_entity=False)
            return QueryPlan(
                plan_id=plan_id,
                intent="trend_analysis",
                operation="analyze_trend",
                primary_column=metric_target,
                secondary_column=date_target,
                chart=QueryChartRecommendation(chart_type="line"),
            )

        # 1F.2 Period Benchmarks (e.g. "Which month had the highest sales?", "Which period performed best and worst?")
        period_benchmark_patterns = [
            r"which (?:month|quarter|year|week|period) (?:had|has) the (?:highest|lowest|most|least|best|worst)",
            r"which (?:month|quarter|year|week|period) performed (?:the )?(?:best|worst)",
            r"highest (?:month|quarter|year|period)",
            r"lowest (?:month|quarter|year|period)",
            r"best (?:month|quarter|year|period)",
            r"worst (?:month|quarter|year|period)",
            r"which period performed best and worst",
            r"best and worst period",
        ]
        if any(re.search(pat, q_lower) for pat in period_benchmark_patterns):
            is_cyclical = any(w in q_lower for w in ("day of week", "weekday", "seasonally", "calendar month", "historically across"))
            metric_target = cls.find_matching_column(question, [c for c in columns if c.data_type in ("integer", "float")], prefer_entity=False)
            return QueryPlan(
                plan_id=plan_id,
                intent="period_benchmark",
                operation="benchmark_periods",
                primary_column=metric_target,
                period_mode="cyclical" if is_cyclical else "chronological",
                chart=QueryChartRecommendation(chart_type="bar"),
            )

        # 1F.3 Sudden Temporal Drops / Spikes (e.g. "Are there any sudden drops in performance?", "What unusual changes occurred?")
        temporal_anomaly_patterns = [
            r"any sudden (?:drops|spikes|jumps|plunges|crashes|surges|falls)",
            r"sudden (?:drop|spike|crash|plunge|surge|jump|decline)",
            r"what unusual changes (?:occurred|happened)",
            r"unusual changes",
            r"unexpected changes between (?:consecutive )?periods",
            r"performance drops",
        ]
        if any(re.search(pat, q_lower) for pat in temporal_anomaly_patterns):
            metric_target = cls.find_matching_column(question, [c for c in columns if c.data_type in ("integer", "float")], prefer_entity=False)
            return QueryPlan(
                plan_id=plan_id,
                intent="temporal_anomaly",
                operation="detect_temporal_anomalies",
                primary_column=metric_target,
                chart=QueryChartRecommendation(chart_type="line"),
            )

        # 1F.4 Seasonality (e.g. "Are there recurring seasonal patterns?")
        seasonality_patterns = [
            r"recurring seasonal patterns",
            r"seasonal patterns",
            r"seasonal cycles",
            r"cyclical patterns",
            r"seasonality",
            r"is there (?:any )?seasonality",
        ]
        if any(re.search(pat, q_lower) for pat in seasonality_patterns):
            metric_target = cls.find_matching_column(question, [c for c in columns if c.data_type in ("integer", "float")], prefer_entity=False)
            return QueryPlan(
                plan_id=plan_id,
                intent="seasonality_analysis",
                operation="detect_seasonality",
                primary_column=metric_target,
                chart=QueryChartRecommendation(chart_type="bar"),
            )

        # =========================================================================
        # 2. GENERAL DATASET OVERVIEW QUESTIONS
        # =========================================================================
        overview_patterns = [
            r"what does this (?:data|dataset|file) contain",
            r"which data contains this (?:uploaded\s+)?(?:file|dataset)",
            r"what data is in this (?:uploaded\s+)?(?:file|dataset)",
            r"what information is (?:available|present|in|found).*?(?:file|dataset|data)",
            r"explain this (?:uploaded\s+)?(?:dataset|data|file)",
            r"overview of this (?:data|dataset|file)",
            r"tell me about this (?:dataset|data|file)",
            r"describe this (?:dataset|data|file)",
            r"what is this (?:dataset|data|file) about",
            r"what are the (?:important\s+)?columns",
            r"summary of (?:this\s+)?(?:dataset|data|file)",
            r"give me an overview",
            r"^overview$",
            r"^summary$",
        ]
        if any(re.search(pat, q_lower) for pat in overview_patterns):
            return QueryPlan(
                plan_id=plan_id,
                intent="dataset_summary",
                operation="overview",
                chart=QueryChartRecommendation(chart_type="none"),
            )

        # Dataset row/column dimension queries
        if any(w in q_lower for w in ("how many rows", "dataset size", "how many records", "total records", "number of rows")):
            return QueryPlan(
                plan_id=plan_id,
                intent="dataset_summary",
                operation="count",
                chart=QueryChartRecommendation(chart_type="none"),
            )

        # =========================================================================
        # 2. MISSING VALUES INSPECTION
        # =========================================================================
        if any(w in q_lower for w in ("missing", "null", "empty", "na values", "missing values")):
            return QueryPlan(
                plan_id=plan_id,
                intent="missing_value_inspection",
                operation="missing_summary",
                limit=15,
                chart=QueryChartRecommendation(
                    chart_type="bar",
                    title="Missing Values Count by Column",
                    x_column="column_name",
                    y_column="missing_count",
                ),
            )

        # =========================================================================
        # 3. TEXT FILTERING: STARTS WITH / BEGINS WITH
        # =========================================================================
        starts_match = re.search(
            r"\b(?:starts?|starting|begins?|beginning)\s+with\s+(?:the\s+letter\s+)?['\"]?([a-zA-Z0-9_\-]+)['\"]?",
            q_lower,
        )
        if not starts_match:
            starts_match = re.search(
                r"\bwhose\s+([a-zA-Z0-9_\s]+)\s+starts?\s+with\s+(?:the\s+letter\s+)?['\"]?([a-zA-Z0-9_\-]+)['\"]?",
                q_lower,
            )
        if starts_match:
            prefix_val = starts_match.group(starts_match.lastindex)
            target_col = cls.find_matching_column(q_lower, columns, prefer_entity=True) or default_cat_col
            if target_col:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="text_search",
                    operation="filter_records",
                    primary_column=target_col,
                    filters=[
                        QueryFilterCondition(
                            column=target_col,
                            operator="starts_with",
                            value=prefix_val,
                        )
                    ],
                    sort=QuerySortRule(column=target_col, direction="ascending"),
                    limit=50,
                    chart=QueryChartRecommendation(chart_type="none"),
                )

        # =========================================================================
        # 4. TEXT FILTERING: ENDS WITH
        # =========================================================================
        ends_match = re.search(
            r"\b(?:ends?|ending)\s+with\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?",
            q_lower,
        )
        if ends_match:
            suffix_val = ends_match.group(1)
            target_col = cls.find_matching_column(q_lower, columns, prefer_entity=True) or default_cat_col
            if target_col:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="text_search",
                    operation="filter_records",
                    primary_column=target_col,
                    filters=[
                        QueryFilterCondition(
                            column=target_col,
                            operator="ends_with",
                            value=suffix_val,
                        )
                    ],
                    sort=QuerySortRule(column=target_col, direction="ascending"),
                    limit=50,
                    chart=QueryChartRecommendation(chart_type="none"),
                )

        # =========================================================================
        # 5. TEXT FILTERING: CONTAINS / KEYWORD
        # =========================================================================
        contains_match = re.search(
            r"\b(?:contains?|containing|includes?|including)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?",
            q_lower,
        )
        if not contains_match:
            contains_match = re.search(
                r"\bwith\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?\s+in\s+(?:the\s+)?(?:name|title|text)?",
                q_lower,
            )
        if contains_match and not any(w in q_lower for w in ("how many rows", "missing", "correlat")):
            keyword_val = contains_match.group(1)
            target_col = cls.find_matching_column(q_lower, columns, prefer_entity=True) or default_cat_col
            if target_col:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="text_search",
                    operation="filter_records",
                    primary_column=target_col,
                    filters=[
                        QueryFilterCondition(
                            column=target_col,
                            operator="contains",
                            value=keyword_val,
                        )
                    ],
                    sort=QuerySortRule(column=target_col, direction="ascending"),
                    limit=50,
                    chart=QueryChartRecommendation(chart_type="none"),
                )

        # =========================================================================
        # 6. DISTINCT / UNIQUE VALUES LISTING
        # =========================================================================
        unique_match = re.search(
            r"\b(?:unique|distinct|list\s+all|different)\s+([a-zA-Z0-9_\s]+)",
            q_lower,
        )
        if unique_match or any(w in q_lower for w in ("unique values", "distinct values", "list of all")):
            target_col = cls.find_matching_column(q_lower, columns, prefer_entity=True) or default_cat_col
            if target_col:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="distinct_values",
                    operation="unique_values",
                    primary_column=target_col,
                    sort=QuerySortRule(column=target_col, direction="ascending"),
                    limit=50,
                    chart=QueryChartRecommendation(chart_type="none"),
                )

        # =========================================================================
        # 7. CORRELATION / RELATIONSHIP
        # =========================================================================
        if any(w in q_lower for w in ("correlat", "relationship between", "associated with")):
            matched_num = [c for c in numeric_cols if c.lower() in q_lower]
            if len(matched_num) >= 2:
                col1, col2 = matched_num[0], matched_num[1]
                return QueryPlan(
                    plan_id=plan_id,
                    intent="correlation_analysis",
                    operation="correlation",
                    primary_column=col1,
                    secondary_column=col2,
                    chart=QueryChartRecommendation(
                        chart_type="scatter",
                        title=f"Correlation between {col1} and {col2}",
                        x_column=col1,
                        y_column=col2,
                    ),
                )
            elif len(numeric_cols) >= 2:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="correlation_analysis",
                    operation="correlation",
                    primary_column=numeric_cols[0],
                    secondary_column=numeric_cols[1],
                    chart=QueryChartRecommendation(
                        chart_type="scatter",
                        title=f"Correlation: {numeric_cols[0]} vs {numeric_cols[1]}",
                        x_column=numeric_cols[0],
                        y_column=numeric_cols[1],
                    ),
                )

        # =========================================================================
        # 8. TREND / TIME SERIES
        # =========================================================================
        if any(w in q_lower for w in ("trend", "over time", "monthly", "yearly", "daily", "timeline")):
            target_dt = date_cols[0] if date_cols else None
            target_num = cls.find_matching_column(q_lower, [c for c in columns if c.data_type in ("integer", "float")]) or (numeric_cols[0] if numeric_cols else None)
            granularity = "month"
            if "year" in q_lower:
                granularity = "year"
            elif "day" in q_lower:
                granularity = "day"

            if target_dt and target_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="trend_analysis",
                    operation="mean",
                    primary_column=target_num,
                    secondary_column=target_dt,
                    date_granularity=granularity,
                    chart=QueryChartRecommendation(
                        chart_type="line",
                        title=f"{target_num} Trend over {target_dt}",
                        x_column=target_dt,
                        y_column=target_num,
                        aggregation="mean",
                    ),
                )

        # =========================================================================
        # 9. MOST FREQUENT / COMMON CATEGORY
        # =========================================================================
        if any(w in q_lower for w in ("most frequent", "most common", "appears most frequently", "highest frequency", "top category")):
            target_col = cls.find_matching_column(q_lower, [c for c in columns if c.name in cat_cols], prefer_entity=True) or default_cat_col
            if target_col:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="distribution_analysis",
                    operation="value_counts",
                    primary_column=target_col,
                    sort=QuerySortRule(column=target_col, direction="descending"),
                    limit=5,
                    chart=QueryChartRecommendation(
                        chart_type="bar",
                        title=f"Frequency Breakdown of {target_col}",
                        x_column=target_col,
                        y_column="count",
                    ),
                )

        # =========================================================================
        # 10. TOP N / BOTTOM N RANKING
        # =========================================================================
        top_n_match = re.search(r"\b(?:top|highest|lowest|bottom)\s*(\d+)?", q_lower)
        if top_n_match or any(w in q_lower for w in ("highest", "lowest", "bottom", "maximum", "minimum")):
            limit_val = int(top_n_match.group(1)) if top_n_match and top_n_match.group(1) else 5
            is_asc = any(w in q_lower for w in ("lowest", "bottom", "least"))
            matched_num = cls.find_matching_column(q_lower, [c for c in columns if c.name in numeric_cols]) or inherited_primary or (numeric_cols[0] if numeric_cols else None)
            matched_cat = cls.find_matching_column(q_lower, [c for c in columns if c.name in cat_cols], prefer_entity=True) or default_cat_col

            if matched_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="ranking_top_bottom",
                    operation="max" if not is_asc else "min",
                    primary_column=matched_num,
                    group_by_columns=[matched_cat] if matched_cat else [],
                    sort=QuerySortRule(column=matched_num, direction="ascending" if is_asc else "descending"),
                    limit=limit_val,
                    chart=QueryChartRecommendation(
                        chart_type="bar",
                        title=f"{'Bottom' if is_asc else 'Top'} {limit_val} records by {matched_num}",
                        x_column=matched_cat or matched_num,
                        y_column=matched_num,
                    ),
                )

        # =========================================================================
        # 11. EXACT VALUE FILTERING (e.g. "How many companies from India?")
        # =========================================================================
        from_match = re.search(r"\b(?:from|in|where\s+[a-zA-Z0-9_\s]+\s+is)\s+['\"]?([a-zA-Z0-9_\s\-]+)['\"]?", q_lower)
        if from_match and any(w in q_lower for w in ("how many", "count", "number of", "records")):
            filter_val = from_match.group(1).strip()
            filter_col = cls.find_matching_column(q_lower, [c for c in columns if c.name in cat_cols], prefer_entity=False) or default_cat_col
            target_metric_col = cls.find_matching_column(q_lower, [c for c in columns if c.name in cat_cols], prefer_entity=True) or filter_col
            if filter_col:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="count",
                    primary_column=target_metric_col or filter_col,
                    filters=[
                        QueryFilterCondition(
                            column=filter_col,
                            operator="exact",
                            value=filter_val,
                        )
                    ],
                    chart=QueryChartRecommendation(chart_type="none"),
                )

        # =========================================================================
        # 12. GROUP-BY COMPARISONS (e.g. "by category", "per class")
        # =========================================================================
        group_match = re.search(r"\b(?:by|per|across|for each|breakdown by)\s+([a-zA-Z0-9_\s]+)", q_lower)
        if group_match or (any(w in q_lower for w in ("by ", "per ", "across ")) and cat_cols):
            group_candidate = group_match.group(1).strip() if group_match else q_lower
            matched_grp = cls.find_matching_column(group_candidate, [c for c in columns if c.name in cat_cols or c.data_type == "integer"], prefer_entity=False) or default_cat_col
            val_candidates = [c for c in columns if c.name in numeric_cols and (not matched_grp or c.name != matched_grp)]
            matched_num = cls.find_matching_column(q_lower, val_candidates) or inherited_primary or (val_candidates[0] if val_candidates else None)

            if matched_grp:
                op = "mean"
                if any(w in q_lower for w in ("total", "sum", "revenue", "sales")):
                    op = "sum"
                elif any(w in q_lower for w in ("count", "number of", "how many")):
                    op = "count"
                elif any(w in q_lower for w in ("median", "middle")):
                    op = "median"
                elif any(w in q_lower for w in ("max", "highest", "maximum")):
                    op = "max"
                elif any(w in q_lower for w in ("min", "lowest", "minimum")):
                    op = "min"
                elif inherited_op:
                    op = inherited_op

                return QueryPlan(
                    plan_id=plan_id,
                    intent="group_by_comparison",
                    operation=op,
                    primary_column=matched_num if op != "count" else (matched_num or matched_grp),
                    group_by_columns=[matched_grp],
                    sort=QuerySortRule(column=matched_num if matched_num else matched_grp, direction="descending"),
                    limit=10,
                    chart=QueryChartRecommendation(
                        chart_type="bar",
                        title=f"{op.capitalize()} of {matched_num or 'records'} by {matched_grp}",
                        x_column=matched_grp,
                        y_column=matched_num,
                        aggregation=op,
                    ),
                )

        # =========================================================================
        # 13. SINGLE COLUMN METRIC AGGREGATION / DISTRIBUTION
        # =========================================================================
        target_col = cls.find_matching_column(q_lower, columns, prefer_entity=False)
        if target_col:
            col_prof = next((c for c in columns if c.name == target_col), None)
            is_num = col_prof and col_prof.data_type in ("integer", "float")

            if any(w in q_lower for w in ("average", "mean", "avg")) and is_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="mean",
                    primary_column=target_col,
                )
            elif any(w in q_lower for w in ("total", "sum", "altogether")) and is_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="sum",
                    primary_column=target_col,
                )
            elif any(w in q_lower for w in ("median", "middle")) and is_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="median",
                    primary_column=target_col,
                )
            elif any(w in q_lower for w in ("highest", "maximum", "max")) and is_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="max",
                    primary_column=target_col,
                )
            elif any(w in q_lower for w in ("lowest", "minimum", "min")) and is_num:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="min",
                    primary_column=target_col,
                )
            elif any(w in q_lower for w in ("percentage", "distribution", "breakdown", "proportion")):
                return QueryPlan(
                    plan_id=plan_id,
                    intent="distribution_analysis",
                    operation="distribution" if is_num else "value_counts",
                    primary_column=target_col,
                    chart=QueryChartRecommendation(
                        chart_type="histogram" if is_num else "pie",
                        title=f"Distribution of {target_col}",
                        x_column=target_col,
                    ),
                )
            elif any(w in q_lower for w in ("count", "how many", "number of")):
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric",
                    operation="count",
                    primary_column=target_col,
                )
            else:
                return QueryPlan(
                    plan_id=plan_id,
                    intent="aggregate_metric" if is_num else "distribution_analysis",
                    operation="mean" if is_num else "value_counts",
                    primary_column=target_col,
                    chart=QueryChartRecommendation(
                        chart_type="histogram" if is_num else "bar",
                        title=f"Overview of {target_col}",
                        x_column=target_col,
                    ),
                )

        # Ambiguous / unclear query
        suggested = [
            f"What is the average {numeric_cols[0]}?" if numeric_cols else "What is the total record count?",
            f"Show distribution of {default_cat_col}." if default_cat_col else "Which columns have missing values?",
            f"Compare {numeric_cols[0]} across {default_cat_col}." if (numeric_cols and default_cat_col) else "Give me an overview of this data.",
        ]
        return QueryPlan(
            plan_id=plan_id,
            intent="ambiguous_clarification",
            operation="none",
            is_ambiguous=True,
            clarification_reason="Your question did not specify which column or metric you want to analyze.",
            suggested_clarifications=suggested,
        )


class QuestionInterpreter:
    """
    Translates user questions into validated QueryPlans using Gemini with strict schema enforcement,
    and seamlessly falls back to the deterministic HeuristicQuestionInterpreter when offline or unkeyed.
    """

    @classmethod
    async def interpret_question(
        cls,
        question: str,
        columns: List[ColumnProfile],
        row_count: int,
        provider: Optional[BaseLLMProvider] = None,
        recent_messages: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: int = 25,
    ) -> Tuple[QueryPlan, str]:
        """
        Interprets natural language question into a QueryPlan.
        Returns: Tuple[QueryPlan, mode: "ai_generated" | "statistical_fallback"]
        """
        if not provider or not getattr(provider, "_api_key", None):
            plan = HeuristicQuestionInterpreter.interpret(question, columns, recent_messages)
            return plan, "statistical_fallback"

        schema_summary = []
        for c in columns:
            col_info = {
                "name": c.name,
                "data_type": c.data_type,
                "null_count": c.null_count,
                "unique_count": c.unique_count,
            }
            if c.min is not None and c.max is not None:
                col_info["min"] = c.min
                col_info["max"] = c.max
                col_info["mean"] = c.mean
            if c.top_values:
                col_info["top_categories"] = [tv.value for tv in c.top_values[:3]]
            schema_summary.append(col_info)

        history_summary = []
        if recent_messages:
            for m in recent_messages[-3:]:
                history_summary.append({
                    "role": m.get("role", "user"),
                    "question": m.get("question") or m.get("content", ""),
                    "columns_used": m.get("columns_used", []),
                    "calculation_method": m.get("calculation_method", ""),
                })

        system_instruction = (
            "You are the analytical query planner for AutoAnalyst AI (Powered by Saniya). "
            "Your objective is to translate user natural-language questions into a strict structured analytical QueryPlan JSON. "
            "CRITICAL RULES:\n"
            "1. Output MUST strictly match the required QueryPlan JSON schema.\n"
            "2. Never invent columns; target columns MUST exactly match an available dataset column.\n"
            "3. COLUMN DISAMBIGUATION: When user asks about an entity (like company, customer, product), choose the human-readable entity name column (e.g. 'Company Name'), NEVER technical columns like URL, Logo, ID, or Website unless specifically requested.\n"
            "4. BROAD ANALYTICAL QUESTIONS:\n"
            "   - If user asks for key findings, main insights, or 'what are the most important findings', set intent='automated_insights', operation='discover_insights', chart.chart_type='none'.\n"
            "   - If user asks for best and worst performing categories, or top/bottom performers, set intent='best_worst_performers', operation='benchmark_performers', chart.chart_type='bar'.\n"
            "   - If user asks for unusual patterns, anomalies, or outliers, set intent='anomaly_detection', operation='detect_anomalies', chart.chart_type='none'.\n"
            "   - If user asks for recommendations, suggested actions, or what actions to take, set intent='business_recommendations', operation='recommend_actions', chart.chart_type='none'.\n"
            "   - If user asks for data quality issues, health problems, or audit, set intent='data_quality_insights', operation='data_quality_audit', chart.chart_type='none'.\n"
            "   - If user asks for temporal trends or if a metric is increasing/decreasing over time, set intent='trend_analysis', operation='analyze_trend', chart.chart_type='line'.\n"
            "   - If user asks for highest/lowest month, best/worst period, set intent='period_benchmark', operation='benchmark_periods', chart.chart_type='bar'. Set period_mode='cyclical' if asking by weekday or calendar month, else 'chronological'.\n"
            "   - If user asks for sudden drops, spikes, or unusual changes over time, set intent='temporal_anomaly', operation='detect_temporal_anomalies', chart.chart_type='line'.\n"
            "   - If user asks for seasonal patterns or seasonality, set intent='seasonality_analysis', operation='detect_seasonality', chart.chart_type='bar'.\n"
            "5. GENERAL DATASET QUESTIONS: When user asks what the dataset contains, explains the file, or asks for an overview, set intent='dataset_summary', operation='overview', chart.chart_type='none'.\n"
            "6. TEXT SEARCH: When user asks for records starting with, ending with, or containing text, set intent='text_search', operation='filter_records', and add the appropriate filter condition with operator='starts_with'|'ends_with'|'contains'|'exact'.\n"
            "7. DISTINCT / UNIQUE VALUES: When user asks for all unique or distinct names/categories, set intent='distinct_values', operation='unique_values'.\n"
            "8. Allowed operations: count, sum, mean, median, min, max, std, percentage, value_counts, correlation, distribution, missing_summary, filter_records, unique_values, overview, discover_insights, benchmark_performers, detect_anomalies, recommend_actions, data_quality_audit, analyze_trend, benchmark_periods, detect_temporal_anomalies, detect_seasonality, none.\n"
            "9. Allowed intents: aggregate_metric, group_by_comparison, correlation_analysis, distribution_analysis, trend_analysis, period_benchmark, temporal_anomaly, seasonality_analysis, ranking_top_bottom, filter_inspection, text_search, distinct_values, missing_value_inspection, dataset_summary, automated_insights, best_worst_performers, anomaly_detection, business_recommendations, data_quality_insights, ambiguous_clarification, unsupported_query.\n"
            "10. Allowed operators: eq, ne, gt, gte, lt, lte, in, not_in, contains, not_contains, starts_with, ends_with, exact, between.\n"
            "11. If a question is ambiguous or vague, set is_ambiguous=true and provide 2-3 specific suggested_clarifications."
        )

        prompt = f"""Interpret the following user question against the dataset schema and produce a structured QueryPlan JSON.

DATASET SCHEMA (Columns & Types):
{json.dumps(schema_summary, indent=2)}

TOTAL DATASET ROWS: {row_count}

RECENT CONVERSATION CONTEXT:
{json.dumps(history_summary, indent=2) if history_summary else "None"}

USER QUESTION:
"{question}"

OUTPUT JSON SCHEMA:
{{
  "plan_id": "plan_{uuid.uuid4().hex[:8]}",
  "intent": "<intent>",
  "operation": "<operation>",
  "primary_column": "<exact_column_name or null>",
  "secondary_column": "<exact_column_name or null>",
  "group_by_columns": ["<exact_column_name>"],
  "filters": [
    {{"column": "<col>", "operator": "starts_with|ends_with|contains|exact|eq|gt|lt", "value": "<val>"}}
  ],
  "sort": {{"column": "<column_name>", "direction": "descending|ascending"}},
  "limit": 10,
  "date_granularity": "month|year|day|null",
  "chart": {{
    "chart_type": "bar|line|scatter|box|pie|histogram|none",
    "title": "<chart title>",
    "x_column": "<column>",
    "y_column": "<column>",
    "aggregation": "<aggregation>"
  }},
  "is_ambiguous": false,
  "clarification_reason": null,
  "suggested_clarifications": []
}}
"""

        try:
            raw_plan_dict = await provider.generate_json(
                prompt=prompt,
                system_instruction=system_instruction,
                timeout_seconds=timeout_seconds,
            )

            if not raw_plan_dict.get("plan_id"):
                raw_plan_dict["plan_id"] = f"plan_{uuid.uuid4().hex[:8]}"

            plan = QueryPlan.model_validate(raw_plan_dict)

            col_map = {c.name.lower(): c.name for c in columns}
            if plan.primary_column:
                matched = col_map.get(plan.primary_column.lower())
                if matched:
                    plan.primary_column = matched
                else:
                    plan.is_ambiguous = True
                    plan.clarification_reason = f"Column '{plan.primary_column}' does not exist in dataset."
                    plan.suggested_clarifications = [f"Did you mean one of: {', '.join(list(col_map.values())[:4])}?"]

            if plan.secondary_column:
                matched = col_map.get(plan.secondary_column.lower())
                if matched:
                    plan.secondary_column = matched

            validated_groups = []
            for grp in plan.group_by_columns:
                matched = col_map.get(grp.lower())
                if matched:
                    validated_groups.append(matched)
            plan.group_by_columns = validated_groups

            return plan, "ai_generated"

        except Exception:
            plan = HeuristicQuestionInterpreter.interpret(question, columns, recent_messages)
            return plan, "statistical_fallback"
