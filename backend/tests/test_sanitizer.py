import math
import numpy as np
import pandas as pd
from app.core.json_encoder import sanitize_for_json


def test_sanitize_primitives():
    assert sanitize_for_json(123) == 123
    assert sanitize_for_json(45.67) == 45.67
    assert sanitize_for_json("hello") == "hello"
    assert sanitize_for_json(True) is True
    assert sanitize_for_json(False) is False
    assert sanitize_for_json(None) is None


def test_sanitize_nan_and_inf():
    assert sanitize_for_json(float("nan")) is None
    assert sanitize_for_json(float("inf")) is None
    assert sanitize_for_json(float("-inf")) is None
    assert sanitize_for_json(np.nan) is None
    assert sanitize_for_json(np.inf) is None
    assert sanitize_for_json(-np.inf) is None
    assert sanitize_for_json(pd.NA) is None
    assert sanitize_for_json(pd.NaT) is None


def test_sanitize_numpy_scalars():
    assert sanitize_for_json(np.int64(42)) == 42
    assert isinstance(sanitize_for_json(np.int64(42)), int)
    assert sanitize_for_json(np.float64(3.14)) == 3.14
    assert isinstance(sanitize_for_json(np.float64(3.14)), float)
    assert sanitize_for_json(np.bool_(True)) is True
    assert isinstance(sanitize_for_json(np.bool_(True)), bool)


def test_sanitize_nested_structures():
    raw_data = {
        "normal_key": "val",
        "nan_val": np.nan,
        "inf_val": float("inf"),
        "nested_list": [1, np.nan, "text", {"sub_inf": np.inf}],
        "numpy_array": np.array([10, np.nan, 30]),
    }
    cleaned = sanitize_for_json(raw_data)
    assert cleaned["nan_val"] is None
    assert cleaned["inf_val"] is None
    assert cleaned["nested_list"][1] is None
    assert cleaned["nested_list"][3]["sub_inf"] is None
    assert cleaned["numpy_array"] == [10.0, None, 30.0]

