import numpy as np
import pandas as pd
import pytest

from spoqc.metrics.hqcr.doublet_score import _transcripts_near_doublets


@pytest.mark.parametrize("dtype", ["float32", "float64"])
@pytest.mark.parametrize("threshold", [0, 10, np.inf])
def test_doublet_window_matches_unrestricted_distance(dtype, threshold):
    transcripts = pd.DataFrame({
        "x": np.array([3, 0, 10, 1e-30, -9, -11, np.nan, 2**30], dtype=dtype),
        "y": np.array([4, 0, 0, 0, 6, 0, 0, 0], dtype=dtype),
    }, index=[4, 2, 2, 9, 1, 3, 0, 5])
    doublets = pd.DataFrame({"x": [0.0, 2**30 + 1.0], "y": [0.0, 0.0]})
    expected = np.zeros(len(transcripts), dtype=bool)
    for _, event in doublets.iterrows():
        distances = np.sqrt(
            (transcripts["x"] - event["x"]) ** 2 + (transcripts["y"] - event["y"]) ** 2
        )
        expected |= distances.to_numpy() <= threshold
    np.testing.assert_array_equal(
        _transcripts_near_doublets(transcripts, doublets, threshold), expected,
    )
