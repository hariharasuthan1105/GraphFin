"""
Report Generation Service for GraphFin.
Generates publication-quality PDF, Word (DOCX), and CSV evaluation reports
for both official locked research benchmarks and user-uploaded custom datasets.
Strictly read-only with respect to official benchmark files.
"""
import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table as RLTable,
    TableStyle,
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
)

from .report_charts import (
    generate_grouped_bar_chart,
    generate_confusion_matrix_chart,
    generate_roc_curve_chart,
    generate_pr_curve_chart,
)

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from ..core.config import settings
from ..core.exceptions import ValidationException
from ..core.logging import get_logger
from ..core.terminology import POSITIVE_LABELS, NEGATIVE_LABELS
from ..services.dataset_registry import dataset_registry
from ..services.evaluation_service import evaluation_service
from ..services.label_registry import label_registry
from ..services.split_service import split_service

logger = get_logger(__name__)

LOCKED_JSON_PATH = settings.DATA_DIR / "results" / "final_e0_e4_comparison.json"
LOCKED_CSV_PATH = settings.DATA_DIR / "results" / "final_e0_e4_comparison.csv"


def _fmt_metric(val: Any) -> str:
    """Safely format metric floats, returning 'N/A' if None or invalid."""
    if val is None or val == "":
        return "N/A"
    try:
        return f"{float(val):.4f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_int(val: Any) -> str:
    """Safely format integer counts, returning '0' if None or invalid."""
    if val is None or val == "":
        return "0"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return str(val)


class ReportService:
    """Generates evaluation reports in PDF, DOCX, and CSV formats."""

    def generate_report(
        self,
        source: str,
        format_type: str,
        dataset_id: Optional[str] = None,
        experiment_label: Optional[str] = None,
        split_label: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        """
        Generate evaluation report.
        Returns: (file_bytes, media_type, filename)
        """
        source = source.lower().strip()
        format_type = format_type.lower().strip()

        if source not in ("official", "custom"):
            raise ValidationException("source must be either 'official' or 'custom'.")
        if format_type not in ("pdf", "docx", "csv"):
            raise ValidationException("format must be 'pdf', 'docx', or 'csv'.")

        if source == "official":
            return self._generate_official_report(format_type)
        else:
            if not dataset_id:
                raise ValidationException("dataset_id is required when source='custom'.")
            return self._generate_custom_report(
                dataset_id=dataset_id,
                format_type=format_type,
                experiment_label=experiment_label,
                split_label=split_label,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # OFFICIAL RESEARCH RESULTS GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_official_report(self, format_type: str) -> Tuple[bytes, str, str]:
        """Generate report for official locked research benchmark (read-only)."""
        if not LOCKED_JSON_PATH.exists():
            raise ValidationException("Official research benchmark results file not found.")

        # Read-only load of locked results
        with open(LOCKED_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        experiments: List[Dict[str, Any]] = data.get("experiments", [])
        title = "GraphFin Research Evaluation Report"
        disclaimer = "Official Research Results — IBM AML HI-Small, locked benchmark"
        protocol_meta = [
            ("Dataset", "IBM AML HI-Small (Kaggle, IBM AMLSim / AMLworld-generated)"),
            ("Evaluation Tiers", "5,000 accounts (medium_real) and 49,992 accounts (large_real)"),
            ("Ground-Truth Labels", "Real Is-Laundering ground truth aggregated to account level (any involvement rule)"),
            ("Experiments", "E0 (graph baseline) through E4 (full GraphFin)"),
            ("Evaluation Protocol", "70/30 stratified entity-level held-out split (random_state=42)"),
        ]

        if format_type == "csv":
            if LOCKED_CSV_PATH.exists():
                with open(LOCKED_CSV_PATH, "rb") as f:
                    csv_bytes = f.read()
            else:
                csv_bytes = self._build_csv(experiments)
            return csv_bytes, "text/csv", "graphfin_official_research_results.csv"

        elif format_type == "pdf":
            pdf_bytes = self._build_pdf(
                title=title,
                banner_text=disclaimer,
                is_official=True,
                meta_pairs=protocol_meta,
                experiments=experiments,
            )
            return pdf_bytes, "application/pdf", "graphfin_official_research_results.pdf"

        elif format_type == "docx":
            docx_bytes = self._build_docx(
                title=title,
                banner_text=disclaimer,
                is_official=True,
                meta_pairs=protocol_meta,
                experiments=experiments,
            )
            return (
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "graphfin_official_research_results.docx",
            )

        raise ValidationException(f"Unsupported format: {format_type}")

    # ─────────────────────────────────────────────────────────────────────────
    # CUSTOM EVALUATION GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_custom_report(
        self,
        dataset_id: str,
        format_type: str,
        experiment_label: Optional[str] = None,
        split_label: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        """Generate report for user-uploaded custom dataset (live evaluation)."""
        # 1. Dataset stats
        tx_count = dataset_registry.get_transaction_count(dataset_id)
        if tx_count == 0:
            raise ValidationException(f"Dataset '{dataset_id}' not found or has no transactions.")

        # 2. Labels summary
        labels_summary = label_registry.get_summary(dataset_id)
        if not labels_summary or labels_summary.matched_count == 0:
            raise ValidationException(
                f"No ground-truth labels found for dataset '{dataset_id}'. "
                "Upload labels before generating an evaluation report."
            )

        # 3. Fetch evaluation data
        experiments_data: List[Dict[str, Any]] = []
        if experiment_label:
            single = evaluation_service.evaluate_experiment(
                dataset_id=dataset_id,
                experiment_label=experiment_label,
                include_curves=True,
                split_label=split_label,
            )
            experiments_data.append(single.model_dump())
        else:
            comp = evaluation_service.compare_experiments(
                dataset_id=dataset_id,
                include_curves=True,
                split_label=split_label,
            )
            if not comp.experiments:
                raise ValidationException(
                    f"No trained anomaly detection models found for dataset '{dataset_id}'. "
                    "Train at least one model before generating an evaluation report."
                )
            for exp in comp.experiments:
                if exp.status == "success":
                    experiments_data.append(exp.model_dump())

        if not experiments_data:
            raise ValidationException("No successful experiment evaluation results available.")

        # Normalize experiments structure for report formatting
        formatted_experiments: List[Dict[str, Any]] = []
        for exp in experiments_data:
            cm = exp.get("confusion_matrix") or {}
            formatted_experiments.append({
                "experiment_label": exp.get("experiment_label", "default"),
                "scale": f"Custom Dataset ({tx_count} txs)",
                "method": exp.get("method") or exp.get("model_type") or "Isolation Forest",
                "feature_groups": exp.get("feature_groups", []),
                "feature_count": exp.get("feature_count", len(exp.get("feature_names", []))),
                "contamination": exp.get("contamination"),
                "evaluation_mode": exp.get("evaluation_mode", "in_sample"),
                "split_label": exp.get("split_label"),
                "precision": exp.get("precision") or 0.0,
                "recall": exp.get("recall") or 0.0,
                "f1_score": exp.get("f1_score") or 0.0,
                "accuracy": exp.get("accuracy") or 0.0,
                "roc_auc": exp.get("roc_auc") or 0.0,
                "pr_auc": exp.get("pr_auc") or 0.0,
                "tp": cm.get("tp", 0),
                "fp": cm.get("fp", 0),
                "tn": cm.get("tn", 0),
                "fn": cm.get("fn", 0),
                "test_positive": exp.get("positive_count", 0),
                "test_negative": exp.get("negative_count", 0),
                "roc_curve": exp.get("roc_curve"),
                "precision_recall_curve": exp.get("precision_recall_curve") or exp.get("pr_curve"),
            })

        title = "GraphFin Custom Evaluation Report"
        banner_text = "Custom Evaluation — user-uploaded dataset, not part of the official research benchmark"
        meta_pairs = [
            ("Dataset ID", dataset_id),
            ("Transaction Count", f"{tx_count:,} transactions"),
            ("Matched Entities", f"{labels_summary.matched_count:,} accounts"),
            (POSITIVE_LABELS, f"{labels_summary.positive_count} ({labels_summary.prevalence_rate * 100:.2f}%)"),
            (NEGATIVE_LABELS, f"{labels_summary.negative_count:,}"),
            ("Evaluation Split", split_label or "In-sample / Default"),
        ]

        # Small sample caution if positive cases < 30
        caution_text = None
        if labels_summary.positive_count < 30:
            caution_text = (
                f"Small-Sample Caution: Dataset has only {labels_summary.positive_count} positive labels. "
                "Metric estimates (especially Precision and PR-AUC) have wider uncertainty bounds."
            )

        if format_type == "csv":
            csv_bytes = self._build_csv(formatted_experiments)
            return csv_bytes, "text/csv", f"graphfin_custom_eval_{dataset_id[:8]}.csv"

        elif format_type == "pdf":
            pdf_bytes = self._build_pdf(
                title=title,
                banner_text=banner_text,
                is_official=False,
                meta_pairs=meta_pairs,
                experiments=formatted_experiments,
                caution_note=caution_text,
            )
            return pdf_bytes, "application/pdf", f"graphfin_custom_eval_{dataset_id[:8]}.pdf"

        elif format_type == "docx":
            docx_bytes = self._build_docx(
                title=title,
                banner_text=banner_text,
                is_official=False,
                meta_pairs=meta_pairs,
                experiments=formatted_experiments,
                caution_note=caution_text,
            )
            return (
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                f"graphfin_custom_eval_{dataset_id[:8]}.docx",
            )

        raise ValidationException(f"Unsupported format: {format_type}")

    # ─────────────────────────────────────────────────────────────────────────
    # EXPORT BUILDERS: CSV, PDF, DOCX
    # ─────────────────────────────────────────────────────────────────────────

    def _build_csv(self, experiments: List[Dict[str, Any]]) -> bytes:
        """Construct CSV tabular bytes from experiment records."""
        output = io.StringIO()
        fieldnames = [
            "scale",
            "dataset_id",
            "experiment_label",
            "method",
            "feature_groups",
            "feature_count",
            "contamination",
            "evaluation_mode",
            "split_label",
            "test_positive",
            "test_negative",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "f1_score",
            "accuracy",
            "roc_auc",
            "pr_auc",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for exp in experiments:
            row = dict(exp)
            if isinstance(row.get("feature_groups"), list):
                row["feature_groups"] = "+".join(row["feature_groups"])
            writer.writerow(row)

        return output.getvalue().encode("utf-8")

    def _build_pdf(
        self,
        title: str,
        banner_text: str,
        is_official: bool,
        meta_pairs: List[Tuple[str, str]],
        experiments: List[Dict[str, Any]],
        caution_note: Optional[str] = None,
    ) -> bytes:
        """Generate PDF document using ReportLab in landscape orientation."""
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        )

        banner_style = ParagraphStyle(
            "Banner",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1E3A8A") if is_official else colors.HexColor("#92400E"),
            fontName="Helvetica-Bold",
        )

        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            fontName="Helvetica-Bold",
        )

        meta_val_style = ParagraphStyle(
            "MetaVal",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )

        cell_style = ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )

        cell_bold = ParagraphStyle(
            "CellBold",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0F172A"),
        )

        th_style = ParagraphStyle(
            "TH",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#FFFFFF"),
        )

        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=12,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        )

        exp_heading_style = ParagraphStyle(
            "ExpHeading",
            parent=styles["Heading3"],
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#1E3A8A") if is_official else colors.HexColor("#065F46"),
            spaceBefore=8,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        )

        fallback_style = ParagraphStyle(
            "FallbackNote",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            fontName="Helvetica-Oblique",
        )

        elements = []

        # 1. Document Title
        elements.append(Paragraph(title, title_style))

        # 2. Disclaimer Banner
        banner_bg = colors.HexColor("#DBEAFE") if is_official else colors.HexColor("#FEF3C7")
        banner_border = colors.HexColor("#3B82F6") if is_official else colors.HexColor("#F59E0B")
        banner_table = RLTable(
            [[Paragraph(banner_text, banner_style)]],
            colWidths=[720],
        )
        banner_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), banner_bg),
                ("BOX", (0, 0), (-1, -1), 1, banner_border),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ])
        )
        elements.append(banner_table)
        elements.append(Spacer(1, 10))

        # 3. Metadata Table (2-column layout)
        meta_rows = []
        for i in range(0, len(meta_pairs), 2):
            row_items = []
            lbl1, val1 = meta_pairs[i]
            row_items.extend([
                Paragraph(lbl1, meta_label_style),
                Paragraph(val1, meta_val_style),
            ])
            if i + 1 < len(meta_pairs):
                lbl2, val2 = meta_pairs[i + 1]
                row_items.extend([
                    Paragraph(lbl2, meta_label_style),
                    Paragraph(val2, meta_val_style),
                ])
            else:
                row_items.extend(["", ""])
            meta_rows.append(row_items)

        if meta_rows:
            meta_table = RLTable(meta_rows, colWidths=[110, 250, 110, 250])
            meta_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ])
            )
            elements.append(meta_table)
            elements.append(Spacer(1, 10))

        # 4. Caution Note if present
        if caution_note:
            caution_table = RLTable(
                [[Paragraph(f"<b>Caution:</b> {caution_note}", cell_style)]],
                colWidths=[720],
            )
            caution_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#EF4444")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ])
            )
            elements.append(caution_table)
            elements.append(Spacer(1, 10))

        # 5. Experiments Results Table
        headers = [
            "Experiment",
            "Features",
            "Eval Mode",
            "PR-AUC",
            "ROC-AUC",
            "F1",
            "Precision",
            "Recall",
            "Accuracy",
            "TP",
            "FP",
            "TN",
            "FN",
        ]
        col_widths = [115, 95, 70, 50, 50, 45, 45, 45, 45, 35, 40, 45, 40]

        table_data = [[Paragraph(h, th_style) for h in headers]]

        for exp in experiments:
            fg = exp.get("feature_groups", [])
            fg_str = "+".join(fg) if isinstance(fg, list) else str(fg)
            f_count = exp.get("feature_count", "")
            f_display = f"{fg_str} ({f_count})" if f_count else fg_str

            table_data.append([
                Paragraph(str(exp.get("experiment_label", "")), cell_bold),
                Paragraph(f_display, cell_style),
                Paragraph(str(exp.get("evaluation_mode", "")), cell_style),
                Paragraph(_fmt_metric(exp.get("pr_auc")), cell_bold),
                Paragraph(_fmt_metric(exp.get("roc_auc")), cell_style),
                Paragraph(_fmt_metric(exp.get("f1_score")), cell_style),
                Paragraph(_fmt_metric(exp.get("precision")), cell_style),
                Paragraph(_fmt_metric(exp.get("recall")), cell_style),
                Paragraph(_fmt_metric(exp.get("accuracy")), cell_style),
                Paragraph(_fmt_int(exp.get("tp")), cell_style),
                Paragraph(_fmt_int(exp.get("fp")), cell_style),
                Paragraph(_fmt_int(exp.get("tn")), cell_style),
                Paragraph(_fmt_int(exp.get("fn")), cell_style),
            ])

        res_table = RLTable(table_data, colWidths=col_widths, repeatRows=1)
        res_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ])
        )
        elements.append(res_table)
        elements.append(Spacer(1, 10))

        # Visual Charts Embedding
        # If multiple experiments (compare mode), include the two grouped bar charts once near the top
        if len(experiments) > 1:
            bar_pr = generate_grouped_bar_chart(experiments, metric_key="pr_auc", is_official=is_official)
            bar_roc = generate_grouped_bar_chart(experiments, metric_key="roc_auc", is_official=is_official)
            if bar_pr and bar_roc:
                elements.append(Paragraph("Comparative Performance Overview", section_style))
                img_pr = RLImage(io.BytesIO(bar_pr), width=350, height=172)
                img_roc = RLImage(io.BytesIO(bar_roc), width=350, height=172)
                bar_table = RLTable([[img_pr, img_roc]], colWidths=[355, 355])
                bar_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                elements.append(bar_table)
                elements.append(Spacer(1, 10))

        # Per-experiment breakdown: metrics table -> confusion matrix -> ROC curve -> PR curve
        for idx, exp in enumerate(experiments):
            exp_label = str(exp.get("experiment_label", f"Exp {idx + 1}"))
            scale_info = f" ({exp.get('scale')})" if exp.get("scale") else ""
            method_info = f" — {exp.get('method')}" if exp.get("method") else ""

            if len(experiments) > 1:
                elements.append(PageBreak())
                elements.append(Paragraph(f"Experiment Analysis: {exp_label}{scale_info}{method_info}", exp_heading_style))

                mini_headers = ["PR-AUC", "ROC-AUC", "F1", "Precision", "Recall", "Accuracy", "TP", "FP", "TN", "FN"]
                mini_widths = [70, 70, 65, 65, 65, 65, 75, 75, 80, 80]
                mini_table = RLTable(
                    [
                        [Paragraph(h, th_style) for h in mini_headers],
                        [
                            Paragraph(_fmt_metric(exp.get("pr_auc")), cell_bold),
                            Paragraph(_fmt_metric(exp.get("roc_auc")), cell_style),
                            Paragraph(_fmt_metric(exp.get("f1_score")), cell_style),
                            Paragraph(_fmt_metric(exp.get("precision")), cell_style),
                            Paragraph(_fmt_metric(exp.get("recall")), cell_style),
                            Paragraph(_fmt_metric(exp.get("accuracy")), cell_style),
                            Paragraph(_fmt_int(exp.get("tp")), cell_style),
                            Paragraph(_fmt_int(exp.get("fp")), cell_style),
                            Paragraph(_fmt_int(exp.get("tn")), cell_style),
                            Paragraph(_fmt_int(exp.get("fn")), cell_style),
                        ],
                    ],
                    colWidths=mini_widths,
                )
                mini_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                    ])
                )
                elements.append(mini_table)
                elements.append(Spacer(1, 10))

            # 1. Confusion Matrix
            cm_bytes = generate_confusion_matrix_chart(
                tp=int(exp.get("tp", 0)),
                fp=int(exp.get("fp", 0)),
                tn=int(exp.get("tn", 0)),
                fn=int(exp.get("fn", 0)),
                exp_label=exp_label,
            )
            if cm_bytes:
                cm_img = RLImage(io.BytesIO(cm_bytes), width=380, height=237)
                cm_img.hAlign = "LEFT"
                elements.append(cm_img)
                elements.append(Spacer(1, 10))

            # Fallback messages
            reason = exp.get("unavailable_reason")
            if not reason:
                reason = "raw curve points not stored in locked benchmark fixture" if is_official else "insufficient class diversity in test partition"
            roc_fallback_msg = f"ROC curve unavailable: {reason}"
            pr_fallback_msg = f"Precision-Recall curve unavailable: {reason}"

            # 2. ROC Curve
            roc_bytes = generate_roc_curve_chart(
                roc_curve_data=exp.get("roc_curve"),
                roc_auc=exp.get("roc_auc"),
                exp_label=exp_label,
            )
            if roc_bytes:
                roc_img = RLImage(io.BytesIO(roc_bytes), width=380, height=269)
                roc_img.hAlign = "LEFT"
                elements.append(roc_img)
                elements.append(Spacer(1, 10))
            else:
                elements.append(Paragraph(roc_fallback_msg, fallback_style))
                elements.append(Spacer(1, 8))

            # 3. Precision-Recall Curve
            pr_bytes = generate_pr_curve_chart(
                pr_curve_data=exp.get("precision_recall_curve") or exp.get("pr_curve"),
                pr_auc=exp.get("pr_auc"),
                exp_label=exp_label,
            )
            if pr_bytes:
                pr_img = RLImage(io.BytesIO(pr_bytes), width=380, height=269)
                pr_img.hAlign = "LEFT"
                elements.append(pr_img)
                elements.append(Spacer(1, 10))
            else:
                elements.append(Paragraph(pr_fallback_msg, fallback_style))
                elements.append(Spacer(1, 8))

        # Footer note
        footer_text = "Report generated by GraphFin Anomaly Detection System."
        elements.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#94A3B8"))))

        doc.build(elements)
        return buf.getvalue()

    def _build_docx(
        self,
        title: str,
        banner_text: str,
        is_official: bool,
        meta_pairs: List[Tuple[str, str]],
        experiments: List[Dict[str, Any]],
        caution_note: Optional[str] = None,
    ) -> bytes:
        """Generate Word (DOCX) document using python-docx."""
        doc = Document()

        # Page setup: Landscape orientation
        section = doc.sections[0]
        new_width, new_height = section.page_height, section.page_width
        section.page_width = new_width
        section.page_height = new_height
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)

        # Title
        p_title = doc.add_paragraph()
        run_title = p_title.add_run(title)
        run_title.font.size = Pt(18)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(15, 23, 42)
        p_title.paragraph_format.space_after = Pt(4)

        # Disclaimer banner paragraph
        p_banner = doc.add_paragraph()
        run_banner = p_banner.add_run(f"[{banner_text}]")
        run_banner.font.size = Pt(10)
        run_banner.font.bold = True
        if is_official:
            run_banner.font.color.rgb = RGBColor(30, 58, 138)
        else:
            run_banner.font.color.rgb = RGBColor(146, 64, 14)
        p_banner.paragraph_format.space_after = Pt(12)

        # Metadata block
        p_meta_header = doc.add_paragraph()
        r_mh = p_meta_header.add_run("Protocol & Dataset Metadata")
        r_mh.font.bold = True
        r_mh.font.size = Pt(11)

        meta_table = doc.add_table(rows=0, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.LEFT
        for label, val in meta_pairs:
            row_cells = meta_table.add_row().cells
            p0 = row_cells[0].paragraphs[0]
            r0 = p0.add_run(label)
            r0.font.bold = True
            r0.font.size = Pt(9)
            r0.font.color.rgb = RGBColor(100, 116, 139)

            p1 = row_cells[1].paragraphs[0]
            r1 = p1.add_run(val)
            r1.font.size = Pt(9)
            r1.font.color.rgb = RGBColor(15, 23, 42)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

        # Caution note if present
        if caution_note:
            p_c = doc.add_paragraph()
            r_c = p_c.add_run(f"Caution: {caution_note}")
            r_c.font.size = Pt(9)
            r_c.font.bold = True
            r_c.font.color.rgb = RGBColor(185, 28, 28)
            p_c.paragraph_format.space_after = Pt(8)

        # Experiments table
        p_tbl_header = doc.add_paragraph()
        r_th = p_tbl_header.add_run("Evaluated Experiments & Headline Metrics")
        r_th.font.bold = True
        r_th.font.size = Pt(11)

        headers = [
            "Experiment",
            "Features",
            "Eval Mode",
            "PR-AUC",
            "ROC-AUC",
            "F1",
            "Precision",
            "Recall",
            "Accuracy",
            "TP",
            "FP",
            "TN",
            "FN",
        ]

        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells

        for idx, h in enumerate(headers):
            p = hdr_cells[idx].paragraphs[0]
            r = p.add_run(h)
            r.font.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(15, 23, 42)

        for exp in experiments:
            fg = exp.get("feature_groups", [])
            fg_str = "+".join(fg) if isinstance(fg, list) else str(fg)
            f_count = exp.get("feature_count", "")
            f_display = f"{fg_str} ({f_count})" if f_count else fg_str

            row_cells = table.add_row().cells
            vals = [
                str(exp.get("experiment_label", "")),
                f_display,
                str(exp.get("evaluation_mode", "")),
                _fmt_metric(exp.get("pr_auc")),
                _fmt_metric(exp.get("roc_auc")),
                _fmt_metric(exp.get("f1_score")),
                _fmt_metric(exp.get("precision")),
                _fmt_metric(exp.get("recall")),
                _fmt_metric(exp.get("accuracy")),
                _fmt_int(exp.get("tp")),
                _fmt_int(exp.get("fp")),
                _fmt_int(exp.get("tn")),
                _fmt_int(exp.get("fn")),
            ]
            for i, val in enumerate(vals):
                p = row_cells[i].paragraphs[0]
                r = p.add_run(val)
                r.font.size = Pt(8)
                if i in (0, 3):  # Bold experiment name and PR-AUC
                    r.font.bold = True

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # Visual Charts Embedding
        # If multiple experiments (compare mode), include the two grouped bar charts once near the top
        if len(experiments) > 1:
            bar_pr = generate_grouped_bar_chart(experiments, metric_key="pr_auc", is_official=is_official)
            bar_roc = generate_grouped_bar_chart(experiments, metric_key="roc_auc", is_official=is_official)
            if bar_pr and bar_roc:
                p_comp = doc.add_paragraph()
                r_comp = p_comp.add_run("Comparative Performance Overview")
                r_comp.font.bold = True
                r_comp.font.size = Pt(12)
                r_comp.font.color.rgb = RGBColor(15, 23, 42)
                p_comp.paragraph_format.space_before = Pt(12)
                p_comp.paragraph_format.space_after = Pt(6)

                doc.add_picture(io.BytesIO(bar_pr), width=Inches(5.0))
                doc.add_paragraph().paragraph_format.space_after = Pt(6)
                doc.add_picture(io.BytesIO(bar_roc), width=Inches(5.0))
                doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # Per-experiment breakdown: metrics table -> confusion matrix -> ROC curve -> PR curve
        for idx, exp in enumerate(experiments):
            exp_label = str(exp.get("experiment_label", f"Exp {idx + 1}"))
            scale_info = f" ({exp.get('scale')})" if exp.get("scale") else ""
            method_info = f" — {exp.get('method')}" if exp.get("method") else ""

            if len(experiments) > 1:
                doc.add_page_break()
                p_exp = doc.add_paragraph()
                r_exp = p_exp.add_run(f"Experiment Analysis: {exp_label}{scale_info}{method_info}")
                r_exp.font.bold = True
                r_exp.font.size = Pt(12)
                if is_official:
                    r_exp.font.color.rgb = RGBColor(30, 58, 138)
                else:
                    r_exp.font.color.rgb = RGBColor(6, 95, 70)
                p_exp.paragraph_format.space_before = Pt(8)
                p_exp.paragraph_format.space_after = Pt(4)

                # Mini metrics table
                mini_headers = ["PR-AUC", "ROC-AUC", "F1", "Precision", "Recall", "Accuracy", "TP", "FP", "TN", "FN"]
                mini_tbl = doc.add_table(rows=2, cols=len(mini_headers))
                mini_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                for c_idx, h in enumerate(mini_headers):
                    p = mini_tbl.rows[0].cells[c_idx].paragraphs[0]
                    r = p.add_run(h)
                    r.font.bold = True
                    r.font.size = Pt(8.5)
                    r.font.color.rgb = RGBColor(15, 23, 42)

                mini_vals = [
                    _fmt_metric(exp.get("pr_auc")),
                    _fmt_metric(exp.get("roc_auc")),
                    _fmt_metric(exp.get("f1_score")),
                    _fmt_metric(exp.get("precision")),
                    _fmt_metric(exp.get("recall")),
                    _fmt_metric(exp.get("accuracy")),
                    _fmt_int(exp.get("tp")),
                    _fmt_int(exp.get("fp")),
                    _fmt_int(exp.get("tn")),
                    _fmt_int(exp.get("fn")),
                ]
                for c_idx, val in enumerate(mini_vals):
                    p = mini_tbl.rows[1].cells[c_idx].paragraphs[0]
                    r = p.add_run(val)
                    r.font.size = Pt(8)
                    if c_idx == 0:
                        r.font.bold = True

                doc.add_paragraph().paragraph_format.space_after = Pt(8)

            # 1. Confusion Matrix Image
            cm_bytes = generate_confusion_matrix_chart(
                tp=int(exp.get("tp", 0)),
                fp=int(exp.get("fp", 0)),
                tn=int(exp.get("tn", 0)),
                fn=int(exp.get("fn", 0)),
                exp_label=exp_label,
            )
            if cm_bytes:
                doc.add_picture(io.BytesIO(cm_bytes), width=Inches(5.0))
                doc.add_paragraph().paragraph_format.space_after = Pt(6)

            # Fallback text determination
            reason = exp.get("unavailable_reason")
            if not reason:
                reason = "raw curve points not stored in locked benchmark fixture" if is_official else "insufficient class diversity in test partition"
            roc_fallback_msg = f"ROC curve unavailable: {reason}"
            pr_fallback_msg = f"Precision-Recall curve unavailable: {reason}"

            # 2. ROC Curve Image
            roc_bytes = generate_roc_curve_chart(
                roc_curve_data=exp.get("roc_curve"),
                roc_auc=exp.get("roc_auc"),
                exp_label=exp_label,
            )
            if roc_bytes:
                doc.add_picture(io.BytesIO(roc_bytes), width=Inches(5.0))
                doc.add_paragraph().paragraph_format.space_after = Pt(6)
            else:
                p_fb = doc.add_paragraph()
                r_fb = p_fb.add_run(roc_fallback_msg)
                r_fb.font.italic = True
                r_fb.font.size = Pt(8.5)
                r_fb.font.color.rgb = RGBColor(100, 116, 139)
                p_fb.paragraph_format.space_after = Pt(4)

            # 3. Precision-Recall Curve Image
            pr_bytes = generate_pr_curve_chart(
                pr_curve_data=exp.get("precision_recall_curve") or exp.get("pr_curve"),
                pr_auc=exp.get("pr_auc"),
                exp_label=exp_label,
            )
            if pr_bytes:
                doc.add_picture(io.BytesIO(pr_bytes), width=Inches(5.0))
                doc.add_paragraph().paragraph_format.space_after = Pt(6)
            else:
                p_fb = doc.add_paragraph()
                r_fb = p_fb.add_run(pr_fallback_msg)
                r_fb.font.italic = True
                r_fb.font.size = Pt(8.5)
                r_fb.font.color.rgb = RGBColor(100, 116, 139)
                p_fb.paragraph_format.space_after = Pt(4)

        # Footer note
        p_ft = doc.add_paragraph()
        r_ft = p_ft.add_run("Report generated by GraphFin Anomaly Detection System.")
        r_ft.font.size = Pt(8)
        r_ft.font.italic = True
        r_ft.font.color.rgb = RGBColor(148, 163, 184)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()


report_service = ReportService()
