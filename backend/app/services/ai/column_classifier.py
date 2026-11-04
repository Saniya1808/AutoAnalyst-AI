import re
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from app.models.automated_insights import ColumnClassification, SemanticRole
from app.models.dataset import ColumnProfile
from app.services.profiler import infer_column_type


class ColumnClassifier:
    """
    Intelligent semantic classification of dataset columns for AutoAnalyst AI.
    Prevents meaningless averages on identifiers (e.g. PassengerId) and stops
    high-cardinality names or URLs from being used as categorical dimensions.
    """

    IDENTIFIER_NAME_PATTERNS = [
        r"^id$",
        r"[\s_-]id$",
        r"^id[\s_-]",
        r"[\s_-]id[\s_-]",
        r"^uuid$",
        r"^guid$",
        r"^key$",
        r"^code$",
        r"^ssn$",
        r"^index$",
        r"^record[\s_-]?id",
        r"^row[\s_-]?id",
        r"^passenger[\s_-]?id",
        r"^customer[\s_-]?id",
        r"^user[\s_-]?id",
        r"^order[\s_-]?id",
        r"^employee[\s_-]?id",
        r"^ticket$",
        r"^account[\s_-]?id",
    ]

    URL_MEDIA_PATTERNS = [
        r"url",
        r"link",
        r"logo",
        r"image",
        r"avatar",
        r"website",
        r"web_site",
        r"photo",
        r"thumbnail",
        r"icon",
    ]

    ENTITY_NAME_PATTERNS = [
        r"^name$",
        r"[\s_-]name$",
        r"^name[\s_-]",
        r"^title$",
        r"[\s_-]title$",
        r"^label$",
        r"company[\s_-]?name",
        r"customer[\s_-]?name",
        r"product[\s_-]?name",
        r"employee[\s_-]?name",
        r"passenger[\s_-]?name",
    ]

    @classmethod
    def is_identifier_column(cls, series: pd.Series, col_name: str, row_count: int) -> bool:
        """Determines if a column is an identifier, primary key, or technical index."""
        col_lower = col_name.lower().strip()

        # Date/Time attributes must never be classified as technical identifiers
        if any(w in col_lower for w in ("date", "time", "timestamp", "year", "month", "day", "created_at", "updated_at")):
            return False

        # 1. Regex check on column name
        if any(re.search(pat, col_lower) for pat in cls.IDENTIFIER_NAME_PATTERNS):
            return True

        # 2. Sequential integer index check (e.g. 1..N or 0..N-1)
        clean = series.dropna()
        if len(clean) > 5 and row_count > 5:
            if pd.api.types.is_integer_dtype(clean) or (clean.dtype == object and clean.astype(str).str.isdigit().all()):
                try:
                    num_clean = pd.to_numeric(clean, errors="coerce").dropna()
                    if len(num_clean) == row_count:
                        # Check strictly monotonic increasing
                        if num_clean.is_monotonic_increasing and num_clean.nunique() == row_count:
                            return True
                except Exception:
                    pass

        # 3. High cardinality alphanumeric ID/hash
        if len(clean) > 10 and clean.dtype == object:
            unique_ratio = clean.nunique() / len(clean)
            if unique_ratio > 0.98:
                # Sample values
                sample_vals = clean.head(10).astype(str)
                # If uniform length and contains digits/alphanumeric with no spaces
                if all(" " not in v and len(v) >= 6 for v in sample_vals):
                    if any(c.isdigit() for v in sample_vals for c in v):
                        return True

        return False

    @classmethod
    def is_url_or_media_column(cls, series: pd.Series, col_name: str) -> bool:
        """Determines if a column contains URLs, media links, or image paths."""
        col_lower = col_name.lower().strip()
        if any(re.search(pat, col_lower) for pat in cls.URL_MEDIA_PATTERNS):
            return True

        clean = series.dropna().astype(str)
        if len(clean) > 0:
            sample = clean.head(20)
            url_matches = sample.str.startswith(("http://", "https://", "www.", "ftp://"))
            if url_matches.mean() > 0.40:
                return True

        return False

    @classmethod
    def classify_column(
        cls,
        series: pd.Series,
        col_name: str,
        col_profile: Optional[ColumnProfile] = None,
        total_rows: Optional[int] = None,
    ) -> ColumnClassification:
        """Classifies a column into its semantic role and analytical policy."""
        row_count = total_rows or len(series)
        inferred_type = col_profile.data_type if col_profile else infer_column_type(series)
        null_count = int(series.isna().sum())
        clean_series = series.dropna()
        unique_count = int(clean_series.nunique())
        unique_ratio = unique_count / max(len(clean_series), 1)
        col_lower = col_name.lower().strip()

        # 1. URL / Media
        if cls.is_url_or_media_column(series, col_name):
            return ColumnClassification(
                name=col_name,
                semantic_role="url_media",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=False,
                is_usable_for_grouping=False,
                classification_reason="Column contains URL links, image assets, or web addresses.",
            )

        # 2. Identifier
        if cls.is_identifier_column(series, col_name, row_count):
            return ColumnClassification(
                name=col_name,
                semantic_role="identifier",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=False,
                is_usable_for_grouping=False,
                classification_reason=f"Column represents a technical identifier or record key ('{col_name}').",
            )

        # 3. Date / Time
        if inferred_type == "datetime" or any(w in col_lower for w in ("date", "time", "timestamp", "created_at", "updated_at")):
            return ColumnClassification(
                name=col_name,
                semantic_role="date_time",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=False,
                is_usable_for_grouping=True,
                classification_reason="Column contains temporal or calendar timestamps.",
            )

        # 4. Entity Names (high cardinality descriptive labels, e.g. Customer Name, Product Name)
        if any(re.search(pat, col_lower) for pat in cls.ENTITY_NAME_PATTERNS) and (unique_count > 25 and unique_ratio > 0.35):
            return ColumnClassification(
                name=col_name,
                semantic_role="entity_name",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=False,
                is_usable_for_grouping=False,
                classification_reason="High-cardinality entity label (e.g. personal names, product titles).",
            )

        # 5. Free Text (paragraphs or long notes)
        if inferred_type == "string" and len(clean_series) > 0:
            avg_words = clean_series.astype(str).str.split().str.len().mean()
            if avg_words > 6.0 and unique_ratio > 0.60:
                return ColumnClassification(
                    name=col_name,
                    semantic_role="free_text",
                    inferred_type=inferred_type,
                    unique_count=unique_count,
                    null_count=null_count,
                    is_usable_for_metrics=False,
                    is_usable_for_grouping=False,
                    classification_reason="Long unstructured narrative or free-form text.",
                )

        # 6. Categorical Dimension (low cardinality string, boolean, or discrete integer)
        # Low cardinality integers like Pclass (1, 2, 3) or status codes are genuine dimensions!
        if (inferred_type in ("string", "boolean") and unique_count <= 50) or (
            inferred_type == "integer" and 2 <= unique_count <= 10 and unique_ratio < 0.15
        ):
            return ColumnClassification(
                name=col_name,
                semantic_role="categorical_dimension",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=False,
                is_usable_for_grouping=True,
                classification_reason=f"Discrete category dimension with {unique_count} distinct levels.",
            )

        # 7. Numerical Measure (continuous or non-identifier integers/floats)
        if inferred_type in ("integer", "float"):
            return ColumnClassification(
                name=col_name,
                semantic_role="numerical_measure",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=True,
                is_usable_for_grouping=False,
                classification_reason="Quantitative metric suitable for statistical aggregations.",
            )

        # Default string classification
        if inferred_type == "string":
            is_groupable = unique_count <= 35
            return ColumnClassification(
                name=col_name,
                semantic_role="categorical_dimension" if is_groupable else "entity_name",
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                is_usable_for_metrics=False,
                is_usable_for_grouping=is_groupable,
                classification_reason=f"Categorical attribute ({unique_count} distinct values).",
            )

        return ColumnClassification(
            name=col_name,
            semantic_role="categorical_dimension",
            inferred_type=inferred_type,
            unique_count=unique_count,
            null_count=null_count,
            is_usable_for_metrics=False,
            is_usable_for_grouping=True,
            classification_reason="General attribute.",
        )

    @classmethod
    def classify_dataset(
        cls, df: pd.DataFrame, col_profiles: Optional[List[ColumnProfile]] = None
    ) -> Dict[str, ColumnClassification]:
        """Classifies all columns in a dataset."""
        profile_map = {p.name: p for p in col_profiles} if col_profiles else {}
        classifications = {}
        for col in df.columns:
            classifications[col] = cls.classify_column(
                series=df[col],
                col_name=col,
                col_profile=profile_map.get(col),
                total_rows=len(df),
            )
        return classifications

