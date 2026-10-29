# Graph edge visibility and direction

Validated 29 October 2026 against baseline `b119a082dc357f2844152187c8b2b4d072e08c09`.

## Root cause

The active uploaded/simulated renderer is `datasetAnalysis/AnalysisGraphCanvas.tsx`. Normal connections used `#383840` at 55% opacity and 1.2 SVG units; automatic viewport fitting reduced apparent thickness further. An automatically selected account dimmed unrelated connections to 15% opacity. The black canvas therefore showed almost invisible hairlines. Arrow markers used dark fills, stroke-relative scaling and arbitrary offsets from center-to-center lines. Reciprocal directions shared the same straight line, and self-transfers had zero-length lines. The renderer, rather than compositing or device-pixel-ratio settings, caused the visibility problem.

## Rendering changes

| State | Stroke | Screen width | Opacity |
|---|---|---:|---:|
| Normal recorded relationship | `#A8C5DB` silver-blue | 2.2 CSS px | 0.88 |
| Touches a flagged account | `#F05A70` crimson | 2.5 CSS px | 0.95 |
| Selected account neighborhood | `#FFD3DB` white-red | 3.5 CSS px | 0.88 or 0.95 |
| Hovered/focused relationship | `#FFFFFF` | 3.8 CSS px | 0.88 or 0.95 |
| Unrelated to selected account | original state color/width | unchanged | 0.58 |

Strokes use `non-scaling-stroke`. Arrowheads are approximately 8 CSS px, 10 for selected/hovered edges, with a 3 CSS px gap outside the recipient node. Rendering geometry trims both endpoints, separates reciprocal paths using quadratic curves and draws self-transfers with cubic loops. Multiple transactions remain one aggregated directed edge. A single shared glow layer is composited behind the bounded edge layer; no per-edge shadow filters or continuous animation loops are added.

Hover/focus details expose actual endpoints, transaction count, aggregate amount and known currency; mixed units remain explicitly unconverted. Crimson indicates an edge touching an already flagged account, not independent transfer-level classification. Neighbor rings emphasize the selected neighborhood. The ALL control clears selection; Graph Explorer initially shows an unselected network instead of automatically dimming most edges. Pan deltas use viewport coordinates correctly and pointer capture; zoom transitions remain smooth, while direct dragging does not lag. Reduced motion removes transitions. Labels retain a readable screen size and long IDs are visually abbreviated with the full identifier available in the title/inspector.

Per-instance SVG IDs prevent marker/gradient collisions when more than one graph is mounted. The resize observer disconnects on unmount. Existing node selection, graph mode distinctions, layout force parameters and rendering caps remain intact: up to 60 accounts and 180 relationships, with visible scope counts.

## Validation

* TypeScript, lint and production build pass.
* Directed geometry unit tests pass at four scales, including boundary trimming, reciprocal orientation, self-loops and coincident positions.
* Existing seven analysis/recovery regressions, typography integration and stability tests pass. Graph/report fixture tests pass, including the actual 10,000-transfer benchmark. The five-page PDF is still generated.
* All 70 full-application browser checks pass, including navigation, consent, mobile layouts, graph controls and report download.
* Dedicated edge browser checks verify all seven relationships in a four-account fixture, the two aggregated A-to-B transfers totaling INR 150, reciprocal curves, self-loop, arrow endpoints outside recipients, keyboard tooltip, selected width and unrelated-edge visibility, pan/zoom/reset/search, and correct Account Inspector values.
* Uploaded and simulated modes pass 1920×1080, 1440×900, 1280×720, 768×1024 and 390×844. Screenshots cover each. Chromium layout/DPR emulation tests the CSS viewport and physical-pixel conditions corresponding to 100%, 125% and 150% browser zoom; these are zoom-equivalent automated checks, not a claim that browser chrome was operated manually.
* High-DPI 2× SVG screenshot captured. Reduced-motion mode reports zero transition duration for camera and edge paths. No critical JavaScript errors or dataset POSTs occurred.
* Dense fixture: 3,540 directed relationships remain bounded at 60 nodes/180 visible edges. Upload, analysis and layout took approximately 3.1 seconds in the final local run; median/p95 idle frame intervals were both approximately 16.7 ms. These are desktop/headless measurements, not a guarantee for every mobile device. No WebGL library or dependency added.

Before/after images use the same 10,000-transfer upload, selected ACC000662, 1440×900 viewport and 100% graph zoom. Simulated-mode images use the same mule-ring preset and zoom. Baseline images were captured from the deployed baseline before release; after images were captured from the updated local renderer. The screenshot gallery and machine-readable browser results are saved outside the public repository in the task's `outputs/graph-edges` directory.

## Scientific invariance and scope

No graph engine, parser, cycle detector, scoring weights, threshold, PDF generator, 19-feature Python pipeline or historical research artifact is changed. Benchmark values remain 10,000 transactions, 1,000 accounts, 9,860 directed edges, nine review flags, mean simple degree 19.72, 335 directed three-cycles and zero noteworthy loops. ACC000662 retains transaction counts 5/59, unique directional neighbors 5/10 and counterparty union 15. Evidence, backend consent/security and uploaded-versus-simulated labels are preserved. The only page changes supply currency/selection callbacks to the shared renderer.

The bounded display is not the entire accepted graph. Crimson is account-associated review emphasis, not proof of a suspicious transfer. No new analysis or model claim is introduced.
