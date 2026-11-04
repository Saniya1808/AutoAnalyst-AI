import math
from datetime import date, datetime
from typing import Any
import numpy as np
import pandas as pd


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize objects to ensure 100% standard JSON compliance.
    Replaces NaN, NaT, and +/-Infinity with None.
    Converts NumPy scalars and dates into standard Python primitives.
    """
    if obj is None:
        return None

    # Handle pandas NaT / NA
    if obj is pd.NA or obj is pd.NaT:
        return None

    # Handle Python/NumPy booleans
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)

    # Handle Python/NumPy integers
    if isinstance(obj, (int, np.integer)):
        return int(obj)

    # Handle Python/NumPy floats
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or np.isnan(obj) or math.isinf(obj) or np.isinf(obj):
            return None
        return float(obj)

    # Handle strings
    if isinstance(obj, str):
        return obj

    # Handle Datetime / Date / Timestamp
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    # Handle Timedelta
    if isinstance(obj, (pd.Timedelta)):
        return str(obj)

    # Handle NumPy arrays
    if isinstance(obj, np.ndarray):
        return [sanitize_for_json(item) for item in obj.tolist()]

    # Handle Dicts
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    # Handle Lists, Tuples, Sets
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]

    # Handle pandas Series
    if isinstance(obj, pd.Series):
        return [sanitize_for_json(item) for item in obj.tolist()]

    # Fallback to string or repr if cannot serialize
    try:
        # Check if it has a to_dict method (like Pydantic or Pandas DataFrame)
        if hasattr(obj, "model_dump"):
            return sanitize_for_json(obj.model_dump())
        if hasattr(obj, "dict"):
            return sanitize_for_json(obj.dict())
    except Exception:
        pass

    return str(obj)

