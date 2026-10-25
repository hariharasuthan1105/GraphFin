"""Bounded in-memory PDF projection of authenticated research evidence.

No legacy live-evaluation path, CSV parsing, model loading or scientific job is
called. ReportLab is already used by GraphFin's existing reporting service.
"""
from collections import defaultdict
from hashlib import sha256
from html import escape
from io import BytesIO
import statistics

from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

from .research_catalog_service import ResearchCatalogService, ResearchError, TITLE

VERSION = 'graphfin-dataset-report-v1'
DATASETS = frozenset(('ibm-5k', 'ibm-50k', 'paysim'))
INK = colors.HexColor('#202124')
GRAY = colors.HexColor('#55585E')
PALE = colors.HexColor('#F2F3F4')
WIDTH = A4[0] - 108


def number(value, digits=6):
    if value is None:
        return 'Unavailable'
    return f'{value:,.{digits}f}' if isinstance(value, float) else f'{value:,}'


class DatasetReportService:
    def generate(self, dataset_id: str, catalog: ResearchCatalogService) -> bytes:
        if dataset_id not in DATASETS:
            raise ResearchError('DATASET_NOT_FOUND', 'Approved research dataset not found.', 404)
        dataset = catalog.dataset(dataset_id)
        experiments = catalog.experiments(dataset_id=dataset_id) if dataset_id.startswith('ibm-') else []
        experiments = [x for x in experiments if x.status == 'verified']
        protocol = catalog.reproducibility() if experiments else None
        catalog_hash = sha256(catalog.catalog_file.read_bytes()).hexdigest()
        styles = {
            'body': ParagraphStyle('Body', fontName='Helvetica', fontSize=9.2, leading=14, textColor=INK, spaceAfter=9),
            'small': ParagraphStyle('Small', fontName='Helvetica', fontSize=8, leading=11, textColor=GRAY, spaceAfter=6),
            'h1': ParagraphStyle('Heading', fontName='Times-Bold', fontSize=27, leading=31, textColor=INK, spaceAfter=14),
            'h2': ParagraphStyle('Section', fontName='Times-Bold', fontSize=16, leading=20, textColor=INK, spaceBefore=12, spaceAfter=10),
            'label': ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=8, leading=12, textColor=GRAY, spaceAfter=12),
            'cell': ParagraphStyle('Cell', fontName='Helvetica', fontSize=8, leading=11, textColor=INK),
        }

        def paragraph(text, style='body'):
            return Paragraph(escape(str(text)), styles[style])

        def table(headers, rows, widths=None):
            data = [[paragraph(x, 'cell') for x in headers]] + [[paragraph(x, 'cell') for x in row] for row in rows]
            result = Table(data, colWidths=widths or [WIDTH / len(headers)] * len(headers), repeatRows=1, hAlign='LEFT')
            result.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PALE),
                ('LINEBELOW', (0, 0), (-1, 0), .8, INK),
                ('LINEBELOW', (0, 1), (-1, -1), .3, colors.HexColor('#D5D7DA')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            return result

        def chart(labels, values, caption, integer=False):
            height = 35 + len(labels) * 25
            drawing = Drawing(WIDTH, height)
            left, right = 108, WIDTH - 65
            maximum = max([x for x in values if x is not None] + [0]) or 1
            drawing.add(Line(left, 19, right, 19, strokeColor=colors.lightgrey, strokeWidth=.5))
            drawing.add(String(left, 5, '0', fontName='Helvetica', fontSize=7, fillColor=GRAY))
            drawing.add(String(right, 5, number(maximum, 0 if integer else 4), textAnchor='end', fontName='Helvetica', fontSize=7, fillColor=GRAY))
            for i, (label, value) in enumerate(zip(labels, values)):
                y = height - 22 - i * 25
                drawing.add(String(0, y + 2, label, fontName='Helvetica', fontSize=8, fillColor=INK))
                if value is not None:
                    drawing.add(Rect(left, y, max(0, value / maximum * (right-left)), 10, fillColor=INK if i % 2 == 0 else GRAY, strokeColor=None))
                drawing.add(String(WIDTH, y + 2, number(value, 0 if integer else 6), textAnchor='end', fontName='Helvetica', fontSize=8, fillColor=INK))
            return [drawing, paragraph(caption, 'small')]

        story = [paragraph('GRAPHFIN / DATASET RESEARCH REPORT', 'label'),
                 paragraph('Dataset Evidence Report', 'h1'),
                 paragraph(dataset.name + ' | ' + dataset.version),
                 paragraph(TITLE), Spacer(1, 12), paragraph('Executive summary', 'h2'),
                 paragraph('This report exports authenticated, saved GraphFin evidence. Dataset metadata, evaluation completion and label validity are separate properties. No models were fitted and no new fraud predictions were generated to create this document.'),
                 table(['Research dimension', 'Recorded evidence'], [
                     ['Dataset type', dataset.dataset_type], ['Result status', dataset.status],
                     ['Label provenance', dataset.provenance_status.replace('_', ' ')],
                     ['Active accounts', number(dataset.accounts)], ['Retained transactions', number(dataset.transactions)],
                     ['Label policy', dataset.label_definition], ['Time semantics', dataset.time_semantics],
                 ], [130, WIDTH-130]), Spacer(1, 14)]
        if dataset_id == 'paysim':
            story += chart([x.identity.replace('paysim-', '') for x in dataset.label_sets], [x.positives for x in dataset.label_sets],
                           'Figure 1. Positive account counts in two separate supplied label sets. Counts are not merged; the upstream provenance conflict remains unresolved.', True)
        else:
            story += chart(['Positive accounts', 'Negative accounts'], [dataset.positives, dataset.negatives],
                           'Figure 1. Supplied active account-label counts, linear count scale. These are synthetic benchmark labels, not independently verified financial ground truth.', True)
        story += [PageBreak(), paragraph('01 / DATA AND METHODOLOGY', 'label'), paragraph('Definitions and evaluation scope', 'h1'),
                  paragraph('An account is the graph-analysis unit. Supplied labels are interpreted under their recorded label-definition identities; the label file alone cannot establish the original labeling procedure. Original raw laundering/fraud flags are not available for independent truth reconstruction.'),
                  table(['Label identity', 'Accounts', 'Positives', 'Negative accounts'], [[x.identity, number(x.accounts), number(x.positives), number(x.accounts-x.positives)] for x in dataset.label_sets], [WIDTH*.4, WIDTH*.2, WIDTH*.2, WIDTH*.2]),
                  paragraph('Label provenance', 'h2')]
        if dataset_id == 'paysim':
            counts = ' and '.join(number(x)+'-positive' for x in sorted(x.positives for x in dataset.label_sets))
            story += [paragraph(f'The two label files have {number(dataset.label_disagreements)} account disagreements. The {counts} definitions remain distinct. Endpoint-role observations do not establish an authoritative generation procedure. This report does not select a preferred source.'),
                      paragraph('Evaluation availability', 'h2'), paragraph('No completed, scientifically compatible PaySim detector comparison is registered in the Phase 7 research catalog. IBM metrics are not substituted. Simulation-time metadata must not be interpreted as real observed calendar dates.'),
                      paragraph('Transfer interpretation depends on dataset identity and unresolved ground-truth provenance. A successful export does not validate transfer accuracy.')]
        else:
            configs = {x.method: x for x in experiments}
            story += [paragraph('IBM upstream account-label lineage is partially verified. Features use the full observation graph (transductive construction); evaluation labels do not fit the unsupervised detector. Held-out membership and model versions are preserved in the experiment records.'),
                      paragraph('Table 1 counts the supplied label-file population; the executive summary counts active accounts after transaction preprocessing. For this dataset these are '+number(dataset.label_sets[0].accounts)+' label rows and '+number(dataset.accounts)+' active accounts. Inactive label rows are not evaluated.', 'small'),
                      paragraph('Frozen experimental definitions', 'h2'),
                      table(['Method', 'Version', 'Feature count'], [[m, r.version, len(r.feature_names)] for m,r in sorted(configs.items())], [65, WIDTH-140, 75]),
                      paragraph(f'For Isolation Forest methods: {protocol.n_estimators} estimators; max_samples={protocol.max_samples}; contamination={protocol.contamination}. Baseline model seed 42. Split seeds: '+', '.join(map(str,protocol.split_seeds))+'.'),
                      paragraph('E0 retains its explicit source-score baseline version. E6_BASE is calibration-only and is distinct from E4 because score ties can change average precision. The full intervention-based E6 benchmark remains incomplete.', 'small')]
        story += [PageBreak(), paragraph('02 / STORED BENCHMARK EVIDENCE', 'label'), paragraph('Descriptive statistical results', 'h1')]
        groups = defaultdict(list)
        for row in experiments:
            groups[row.method].append(row)
        summaries = []
        for method, rows in sorted(groups.items()):
            values = [r.metrics.average_precision for r in rows if r.metrics and r.metrics.average_precision is not None]
            summaries.append((method, len(values), statistics.mean(values) if values else None,
                              statistics.stdev(values) if len(values)>1 else None,
                              min(values) if values else None, max(values) if values else None))
        if summaries:
            story += chart([x[0] for x in summaries], [x[2] for x in summaries],
                           'Figure 2. Mean Average Precision across stored splits for this dataset only. Linear scale starts at zero; methods and sample sizes are shown in Table 2.')
            story += [table(['Method', 'n', 'Mean AP', 'Sample SD', 'Minimum', 'Maximum'],
                            [[x[0],x[1],*[number(v) for v in x[2:]]] for x in summaries], [65,32,98,98,97,97]),
                      Spacer(1, 10), paragraph('Table 2. AP uses the non-interpolated PR-AUC convention. Sample SD = sqrt(sum((AP - mean AP)^2)/(n - 1)). Missing measurements remain unavailable; no confidence intervals are manufactured. Splits overlap and are not independent datasets. Differences are descriptive, not significance tests.', 'small'),
                      paragraph('Selection and interpretation', 'h2'), paragraph('No method is declared universally superior. The calibrated E6_BASE does not establish CREST detector superiority. Separate model-seed evidence is available for E1/E4 at split 42 and seeds 13, 42 and 101; it is not merged into this split summary.')]
        else:
            story += [paragraph('Detector metrics unavailable', 'h2'), paragraph('Average precision, ROC-AUC, retrieval counts and confidence intervals for this dataset are unavailable in the approved completed-experiment catalog. No bars or statistical values are invented.'),
                      table(['Research quantity', 'Availability'], [['Completed compatible detector runs', 'Unavailable'], ['Mean AP / sample SD', 'Unavailable'], ['ROC-AUC / Precision@K', 'Unavailable'], ['Confidence intervals', 'Unavailable']]),
                      paragraph('Available data evidence', 'h2'), paragraph('Figure 1 and the label table report genuine supplied label-set counts. They describe the disagreement; they do not resolve which labeling procedure is authoritative.')]
        story += [PageBreak(), paragraph('03 / PROVENANCE AND SCIENTIFIC LIMITATIONS', 'label'), paragraph('Traceability and disclosures', 'h1')]
        def digest(value):
            return 'Unavailable' if value is None else value[:32]+' '+value[32:]
        hashes = [['Dataset transactions', digest(dataset.transaction_sha256)], ['Catalog configuration', digest(catalog_hash)],
                  ['Dataset metadata evidence', digest(dataset.artifact_sha256)]]
        hashes += [[x.identity, digest(x.sha256)] for x in dataset.label_sets]
        if experiments:
            hashes.append(['Benchmark metric evidence', digest(experiments[0].artifact_sha256)])
        story += [table(['Evidence identity', 'SHA256 (line-wrapped)'], hashes, [140, WIDTH-140]),
                  paragraph('Scientific limitations', 'h2')]
        for item in [
            'IBM AML upstream account-label lineage is partially verified; original raw laundering flags are absent.',
            'PaySim has unresolved conflicting label provenance. The two label sets must not be silently merged or selected.',
            'CREST is an experimental model-sensitivity diagnostic. Superior detection and superior explanation quality have not been demonstrated.',
            'The original intervention-based E6 detector benchmark is incomplete. Diagnostic score changes are not causal evidence of financial crime.',
            'Same-input replay supports reproducibility, not external generalization. Anomaly scores are not fraud probabilities.',
        ]:
            story.append(paragraph(item))
        story += [paragraph('Export definition', 'h2'), paragraph(VERSION+' | deterministic in-memory PDF from approved catalog evidence. No raw account identifiers, transaction records, model binaries or local filesystem paths are included.', 'small')]

        def page_frame(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8); canvas.setFillColor(GRAY)
            canvas.drawString(54, A4[1]-31, 'GRAPHFIN / RESEARCH EVIDENCE')
            canvas.drawRightString(A4[0]-54, A4[1]-31, dataset.name.upper()+' / DATASET REPORT')
            canvas.setStrokeColor(colors.HexColor('#CBCDD0')); canvas.setLineWidth(.4)
            canvas.line(54,A4[1]-39,A4[0]-54,A4[1]-39); canvas.line(54,38,A4[0]-54,38)
            canvas.setFont('Helvetica', 7)
            canvas.drawString(54,26,'Research benchmark - not an operational fraud determination')
            canvas.drawRightString(A4[0]-54,26,f'{doc.page:02d}')
            canvas.restoreState()

        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=54,leftMargin=54,topMargin=60,bottomMargin=54,
                                title=TITLE, author='GraphFin Research', subject=VERSION+' | '+dataset_id)
        doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame,
                  canvasmaker=lambda *a, **kw: Canvas(*a, **dict(kw, invariant=1)))
        data = output.getvalue()
        if len(data)>2*1024*1024:
            raise ResearchError('REPORT_TOO_LARGE', 'Dataset report exceeded its output budget.')
        return data


dataset_report_service = DatasetReportService()
