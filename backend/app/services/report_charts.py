"""
Chart Generation Service for GraphFin Evaluation Reports.
Renders publication-quality, print-friendly PNG images (in-memory)
for PDF and Word (DOCX) reports using matplotlib Agg backend.
"""
import io
from typing import Any, Dict, List, Optional
import matplotlib

# Headless backend (no GUI/display server needed)
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Styling constants for professional, print-friendly reports (clean light background)
STYLE = {
    "bg_color": "#FFFFFF",
    "text_color": "#0F172A",
    "subtext_color": "#475569",
    "grid_color": "#E2E8F0",
    "blue_primary": "#2563EB",
    "purple_accent": "#7C3AED",
    "green_normal": "#059669",
    "red_suspicious": "#DC2626",
    "amber_warning": "#D97706",
    "font_family": "sans-serif",
}

from ..core.terminology import (
    ACTUAL_NORMAL,
    ACTUAL_POSITIVE,
    ANOMALIES_DETECTED,
    ANOMALIES_MISSED,
    FALSE_ALARMS,
    FN_TITLE,
    FP_TITLE,
    NORMAL_CLEARED,
    PREDICTED_NORMAL,
    PREDICTED_SUSPICIOUS,
    TN_TITLE,
    TP_TITLE,
)


def generate_grouped_bar_chart(
    experiments: List[Dict[str, Any]],
    metric_key: str = "pr_auc",
    is_official: bool = True,
) -> Optional[bytes]:
    """
    Generate grouped bar chart for compare view.
    - Official mode: 5K vs 50K side-by-side bars for E0-E4.
    - Custom mode: single bars for each evaluated custom experiment.
    """
    if not experiments:
        return None

    metric_name = "PR-AUC (Average Precision)" if metric_key == "pr_auc" else "ROC-AUC"
    chart_title = f"Comparative {metric_name} by Experiment"

    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=150)
    fig.patch.set_facecolor(STYLE["bg_color"])
    ax.set_facecolor(STYLE["bg_color"])

    try:
        if is_official:
            # Group by experiment label across 5K and 50K tiers
            exp_order = [
                "E0_graph_baseline",
                "E1_graph_ml",
                "E2_graph_behavioral_ml",
                "E3_graph_temporal_ml",
                "E4_full_graphfin",
            ]
            exp_short_names = ["E0 (Baseline)", "E1 (Graph)", "E2 (+Behav)", "E3 (+Temp)", "E4 (Full)"]

            m5k_map = {}
            m50k_map = {}
            for exp in experiments:
                lbl = exp.get("experiment_label")
                val = float(exp.get(metric_key) or 0.0)
                scale = str(exp.get("scale", "")).lower()
                ds_id = str(exp.get("dataset_id", ""))
                # Identify 5k vs 50k
                if "5,000" in scale or "ddbaab44" in ds_id or "medium" in scale:
                    m5k_map[lbl] = val
                else:
                    m50k_map[lbl] = val

            vals_5k = [m5k_map.get(e, 0.0) for e in exp_order]
            vals_50k = [m50k_map.get(e, 0.0) for e in exp_order]

            x = np.arange(len(exp_order))
            width = 0.35

            bars1 = ax.bar(x - width / 2, vals_5k, width, label="5,000 Accounts", color=STYLE["blue_primary"])
            bars2 = ax.bar(x + width / 2, vals_50k, width, label="49,992 Accounts", color=STYLE["purple_accent"])

            # Value labels on bars
            for bar in list(bars1) + list(bars2):
                h = bar.get_height()
                if h > 0:
                    ax.annotate(
                        f"{h:.3f}",
                        xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 2),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=7,
                        color=STYLE["text_color"],
                    )

            ax.set_xticks(x)
            ax.set_xticklabels(exp_short_names, fontsize=8, color=STYLE["text_color"])
            ax.legend(loc="upper right", frameon=True, facecolor="#F8FAFC", edgecolor=STYLE["grid_color"], fontsize=8)

        else:
            # Custom experiments
            exp_labels = [exp.get("experiment_label", f"Exp {i+1}") for i, exp in enumerate(experiments)]
            vals = [float(exp.get(metric_key) or 0.0) for exp in experiments]

            x = np.arange(len(exp_labels))
            bars = ax.bar(x, vals, width=0.45, color=STYLE["blue_primary"])

            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.annotate(
                        f"{h:.3f}",
                        xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 2),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=7.5,
                        color=STYLE["text_color"],
                    )

            ax.set_xticks(x)
            ax.set_xticklabels(exp_labels, fontsize=8, color=STYLE["text_color"], rotation=15 if len(exp_labels) > 4 else 0)

        ax.set_title(chart_title, fontsize=10.5, fontweight="bold", color=STYLE["text_color"], pad=10)
        ax.set_ylabel(metric_name, fontsize=8.5, color=STYLE["subtext_color"])
        ax.set_ylim(0, max(1.05, ax.get_ylim()[1]))
        ax.grid(axis="y", linestyle="--", alpha=0.6, color=STYLE["grid_color"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(STYLE["grid_color"])
        ax.spines["bottom"].set_color(STYLE["grid_color"])

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
        buf.seek(0)
        return buf.getvalue()

    finally:
        plt.close(fig)


def generate_confusion_matrix_chart(
    tp: int, fp: int, tn: int, fn: int, exp_label: str
) -> Optional[bytes]:
    """
    Generate clean 2x2 grid visualization of the confusion matrix.
    Labels: "Predicted Suspicious / Normal" x "Actual Positive / Normal"
    (Using correct "Actual Positive" terminology).
    """
    fig, ax = plt.subplots(figsize=(4.8, 3.0), dpi=150)
    fig.patch.set_facecolor(STYLE["bg_color"])
    ax.set_facecolor(STYLE["bg_color"])

    try:
        # Hide axes ticks and spines
        ax.axis("off")

        # Table data layout: 2 rows (Actual Positive, Actual Normal) x 2 cols (Predicted Suspicious, Predicted Normal)
        # We render 4 visually distinguished rounded/bordered boxes
        total = tp + fp + tn + fn
        tp_pct = f"{(tp / total * 100):.1f}%" if total > 0 else ""
        fn_pct = f"{(fn / total * 100):.1f}%" if total > 0 else ""
        fp_pct = f"{(fp / total * 100):.1f}%" if total > 0 else ""
        tn_pct = f"{(tn / total * 100):.1f}%" if total > 0 else ""

        # Coordinates for the 4 boxes: (x, y, width, height)
        # Left column: x = 0.28, Right column: x = 0.62
        # Top row: y = 0.48, Bottom row: y = 0.12
        boxes = [
            # Top-Left: True Positive (TP)
            {
                "x": 0.26, "y": 0.48, "bg": "#ECFDF5", "border": "#10B981",
                "title": TP_TITLE, "val": f"{tp:,}", "sub": f"{ANOMALIES_DETECTED} ({tp_pct})"
            },
            # Top-Right: False Negative (FN)
            {
                "x": 0.62, "y": 0.48, "bg": "#FEF2F2", "border": "#EF4444",
                "title": FN_TITLE, "val": f"{fn:,}", "sub": f"{ANOMALIES_MISSED} ({fn_pct})"
            },
            # Bottom-Left: False Positive (FP)
            {
                "x": 0.26, "y": 0.12, "bg": "#FFFBEB", "border": "#F59E0B",
                "title": FP_TITLE, "val": f"{fp:,}", "sub": f"{FALSE_ALARMS} ({fp_pct})"
            },
            # Bottom-Right: True Negative (TN)
            {
                "x": 0.62, "y": 0.12, "bg": "#F8FAFC", "border": "#94A3B8",
                "title": TN_TITLE, "val": f"{tn:,}", "sub": f"{NORMAL_CLEARED} ({tn_pct})"
            },
        ]

        w_box = 0.33
        h_box = 0.32

        for b in boxes:
            rect = plt.Rectangle(
                (b["x"], b["y"]), w_box, h_box,
                facecolor=b["bg"], edgecolor=b["border"],
                linewidth=1.2, transform=ax.transAxes, clip_on=False
            )
            ax.add_patch(rect)
            # Label
            ax.text(
                b["x"] + w_box / 2, b["y"] + h_box - 0.07, b["title"],
                ha="center", va="center", fontsize=7.5, fontweight="bold",
                color=STYLE["text_color"], transform=ax.transAxes
            )
            # Value
            ax.text(
                b["x"] + w_box / 2, b["y"] + h_box / 2, b["val"],
                ha="center", va="center", fontsize=11.5, fontweight="bold",
                color=STYLE["text_color"], transform=ax.transAxes
            )
            # Subtitle
            ax.text(
                b["x"] + w_box / 2, b["y"] + 0.06, b["sub"],
                ha="center", va="center", fontsize=6.5,
                color=STYLE["subtext_color"], transform=ax.transAxes
            )

        # Row headers (Actual Label)
        ax.text(0.24, 0.48 + h_box / 2, ACTUAL_POSITIVE, ha="right", va="center", fontsize=8, fontweight="bold", color=STYLE["text_color"], transform=ax.transAxes)
        ax.text(0.24, 0.12 + h_box / 2, ACTUAL_NORMAL, ha="right", va="center", fontsize=8, fontweight="bold", color=STYLE["text_color"], transform=ax.transAxes)
        ax.text(0.04, 0.46, "Actual", ha="center", va="center", fontsize=8.5, fontweight="bold", color=STYLE["subtext_color"], rotation=90, transform=ax.transAxes)

        # Column headers (Predicted Label)
        ax.text(0.26 + w_box / 2, 0.84, PREDICTED_SUSPICIOUS, ha="center", va="bottom", fontsize=8, fontweight="bold", color=STYLE["text_color"], transform=ax.transAxes)
        ax.text(0.62 + w_box / 2, 0.84, PREDICTED_NORMAL, ha="center", va="bottom", fontsize=8, fontweight="bold", color=STYLE["text_color"], transform=ax.transAxes)

        # Title
        ax.text(0.5, 0.98, f"Confusion Matrix — {exp_label}", ha="center", va="top", fontsize=9.5, fontweight="bold", color=STYLE["text_color"], transform=ax.transAxes)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
        buf.seek(0)
        return buf.getvalue()

    finally:
        plt.close(fig)


def generate_roc_curve_chart(
    roc_curve_data: Optional[Dict[str, Any]],
    roc_auc: Optional[float],
    exp_label: str,
) -> Optional[bytes]:
    """
    Generate ROC Curve: TPR vs FPR with diagonal reference line and AUC in legend.
    Returns None if curve points are unavailable.
    """
    if not roc_curve_data:
        return None

    fpr = roc_curve_data.get("fpr")
    tpr = roc_curve_data.get("tpr")
    if not fpr or not tpr or len(fpr) < 2:
        return None

    fig, ax = plt.subplots(figsize=(4.8, 3.4), dpi=150)
    fig.patch.set_facecolor(STYLE["bg_color"])
    ax.set_facecolor(STYLE["bg_color"])

    try:
        auc_val = float(roc_auc) if roc_auc is not None else 0.0
        # Diagonal reference line
        ax.plot([0, 1], [0, 1], linestyle="--", color="#94A3B8", linewidth=1.2, label="Chance (AUC = 0.5000)")
        # ROC Curve
        ax.plot(fpr, tpr, color=STYLE["blue_primary"], linewidth=2.0, label=f"ROC (AUC = {auc_val:.4f})")

        ax.set_title(f"ROC Curve — {exp_label}", fontsize=9.5, fontweight="bold", color=STYLE["text_color"], pad=8)
        ax.set_xlabel("False Positive Rate (FPR)", fontsize=8, color=STYLE["subtext_color"])
        ax.set_ylabel("True Positive Rate (TPR)", fontsize=8, color=STYLE["subtext_color"])
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, linestyle=":", alpha=0.6, color=STYLE["grid_color"])
        ax.tick_params(colors=STYLE["subtext_color"], labelsize=7.5)
        ax.legend(loc="lower right", frameon=True, facecolor="#F8FAFC", edgecolor=STYLE["grid_color"], fontsize=7.5)

        for s in ax.spines.values():
            s.set_color(STYLE["grid_color"])

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
        buf.seek(0)
        return buf.getvalue()

    finally:
        plt.close(fig)


def generate_pr_curve_chart(
    pr_curve_data: Optional[Dict[str, Any]],
    pr_auc: Optional[float],
    exp_label: str,
) -> Optional[bytes]:
    """
    Generate Precision-Recall Curve: Precision vs Recall with PR-AUC shown.
    Returns None if curve points are unavailable.
    """
    if not pr_curve_data:
        return None

    recall = pr_curve_data.get("recall")
    precision = pr_curve_data.get("precision")
    if not recall or not precision or len(recall) < 2:
        return None

    fig, ax = plt.subplots(figsize=(4.8, 3.4), dpi=150)
    fig.patch.set_facecolor(STYLE["bg_color"])
    ax.set_facecolor(STYLE["bg_color"])

    try:
        auc_val = float(pr_auc) if pr_auc is not None else 0.0
        ax.plot(recall, precision, color=STYLE["green_normal"], linewidth=2.0, label=f"PR Curve (AUC = {auc_val:.4f})")

        ax.set_title(f"Precision-Recall Curve — {exp_label}", fontsize=9.5, fontweight="bold", color=STYLE["text_color"], pad=8)
        ax.set_xlabel("Recall", fontsize=8, color=STYLE["subtext_color"])
        ax.set_ylabel("Precision", fontsize=8, color=STYLE["subtext_color"])
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, linestyle=":", alpha=0.6, color=STYLE["grid_color"])
        ax.tick_params(colors=STYLE["subtext_color"], labelsize=7.5)
        ax.legend(loc="upper right", frameon=True, facecolor="#F8FAFC", edgecolor=STYLE["grid_color"], fontsize=7.5)

        for s in ax.spines.values():
            s.set_color(STYLE["grid_color"])

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
        buf.seek(0)
        return buf.getvalue()

    finally:
        plt.close(fig)
