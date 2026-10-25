"""Source-only positive affine scores and separately defined raw CREST fusion."""
import numpy as np

AFFINE_VERSION = "source-binary-iqr-affine-v1"
FUSION_VERSION = "raw-affine-crest-feasibility-v1"
FAMILIES = ("counterparty", "temporal", "budgeted")


class TrainingAffine:
    def __init__(self, source_training_scores):
        x = np.asarray(source_training_scores, dtype=np.float64)
        if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
            raise ValueError("Finite nonempty source-training scores required.")
        self.location = float(np.median(x))
        q25, q75 = np.quantile(x, [.25, .75])
        width = float(q75-q25)
        self.fallback = "none"
        if not np.isfinite(width) or width <= 0:
            width = float(np.max(x)-np.min(x))
            self.fallback = "source_range"
        if not np.isfinite(width) or width <= 0:
            width = 1.0
            self.fallback = "unit_for_constant_source"
        # A binary scale avoids rounding in division except at exponent limits.
        # Quantizing the positive TRAINING scale does not quantize scores.
        self.scale = float(np.exp2(np.floor(np.log2(width))))
        if not np.isfinite(self.scale) or self.scale <= 0:
            raise FloatingPointError("Source scale is not representable.")
        self.source_iqr = float(q75-q25)
        self.training_count = len(x)

    def transform(self, scores):
        x = np.asarray(scores, dtype=np.float64)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError("Finite one-dimensional raw scores required.")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            z = (x-self.location)/self.scale
        if not np.isfinite(z).all():
            raise FloatingPointError("Affine transform overflowed.")
        unique = np.unique(x)
        with np.errstate(over="ignore", invalid="ignore"):
            ordered = (unique-self.location)/self.scale
        if len(unique)>1 and not np.all(np.diff(ordered)>0):
            raise FloatingPointError("Affine arithmetic changed ordering or introduced a tie.")
        return z

    def metadata(self):
        return {"version":AFFINE_VERSION, "fit_population":"source-training raw E4 scores only",
                "training_count":self.training_count, "median_train":self.location,
                "scale_train":self.scale, "source_iqr":self.source_iqr,
                "scale_rule":"2**floor(log2(IQR)); source-range then unit fallback",
                "fallback":self.fallback, "numerics":"float64, strict order check, no clipping"}


def raw_modes(z0, family_deltas, alpha=.25, beta=.25):
    """Equal-family medians; bounded robustness, nonnegative anomaly-level penalty.

    D_f=median(delta_z); A_f=median(abs(delta_z)); R_f=1/(1+A_f).
    D averages available families; R averages families with >=2 interventions.
    Raw scores are unbounded and are not fraud probabilities. Missing required
    statistics cause explicit baseline fallback, as in the frozen policy.
    """
    d, r, families = [], [], {}
    for family in FAMILIES:
        values = np.asarray(family_deltas.get(family, ()), dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Finite intervention deltas required.")
        signed = float(np.median(values)) if len(values) else None
        absolute = float(np.median(np.abs(values))) if len(values) else None
        robust = 1/(1+absolute) if len(values)>=2 else None
        if signed is not None: d.append(signed)
        if robust is not None: r.append(robust)
        families[family] = {"count":len(values), "median_signed":signed,
                            "median_absolute":absolute, "robustness":robust}
    D = float(np.mean(d)) if d else None
    R = float(np.mean(r)) if r else None
    scores, fallbacks = {}, {}
    for mode, use_d, use_r in [("RAW_BASE",False,False),("RAW_SENSITIVITY",True,False),
                               ("RAW_ROBUSTNESS",False,True),("RAW_HYBRID",True,True)]:
        use_d = use_d and alpha!=0
        use_r = use_r and beta!=0
        missing = (["sensitivity_unavailable"] if use_d and D is None else []) + (["robustness_unavailable"] if use_r and R is None else [])
        score = z0 if missing else z0 + (alpha*D if use_d else 0) - (beta*max(z0,0)*(1-R) if use_r else 0)
        if not np.isfinite(score): raise FloatingPointError("Nonfinite fusion score.")
        scores[mode], fallbacks[mode] = float(score), missing
    return {"version":FUSION_VERSION, "sensitivity":D, "robustness":R,
            "families":families, "scores":scores, "fallbacks":fallbacks}
