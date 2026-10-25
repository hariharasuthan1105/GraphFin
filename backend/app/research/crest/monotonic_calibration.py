"""Exploratory source-only monotonic logistic score calibration (rank-preserving)."""
import numpy as np

VERSION = "source-logistic-rank-preserving-v3"


class SourceLogisticCalibration:
    def __init__(self, source_training_scores):
        x = np.asarray(source_training_scores, dtype=np.float64)
        if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
            raise ValueError("Calibration requires finite source-training scores only.")
        self.location = float(np.median(x))
        q25, q75 = np.quantile(x, [0.25, 0.75])
        robust_scale = float((q75-q25)/1.349)
        # A prespecified unit-scale floor avoids extreme training logits on
        # small-magnitude IF scores; the transform still checks held-out
        # saturation explicitly because test scores may exceed training range.
        range_scale = float(np.max(np.abs(x-self.location))/20.0)
        scale = max(robust_scale, range_scale, 1.0)
        if not np.isfinite(scale) or scale <= 0:
            scale = float(np.std(x))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("Source training scores have no positive finite scale.")
        self.scale = scale

    def transform(self, scores):
        x = np.asarray(scores, dtype=np.float64)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError("Calibration input must be finite scores.")
        z = (x-self.location)/self.scale
        # logaddexp is stable on both tails; detect floating-point saturation
        # explicitly below rather than silently accepting newly introduced ties.
        out = np.exp(-np.logaddexp(0.0, -z))
        unique_raw = np.unique(x)
        unique_out = np.unique(out)
        if len(unique_raw) != len(unique_out):
            raise FloatingPointError("Logistic saturation/rounding introduced a tie in this score range.")
        if len(unique_raw) > 1:
            ordered = np.sort(unique_raw)
            mapped = np.exp(-np.logaddexp(0.0, -(ordered-self.location)/self.scale))
            if not np.all(np.diff(mapped) > 0):
                raise FloatingPointError("Calibration failed strict rank-preservation check.")
        return out

    def metadata(self):
        return {"version": VERSION, "fit_population": "source-training raw scores only",
                "location_median": self.location, "scale_max_of_iqr_over_1.349_source_range_over_20_and_unit_floor": self.scale,
                "transform": "exp(-logaddexp(0,-(s-location)/scale))",
                "saturation_policy": "raise if distinct finite input scores collapse to equal float64 outputs"}
