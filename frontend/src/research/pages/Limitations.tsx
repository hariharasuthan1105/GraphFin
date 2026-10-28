import { useResearch } from "../state";
import type { Limitations as Data } from "../contract";
import { State, Heading, Panel, Notice } from "../ui";

export default function Limitations() {
  const r = useResearch<Data>("/limitations", "Limitations");
  return (
    <>
      <Heading index="10" title="Research & analysis limitations">
        A complete evidence record includes uncertainty, negative results, and operational boundaries.
      </Heading>
      <Notice>
        IBM AML: upstream account-label lineage partially verified. PaySim:
        conflicting label provenance unresolved (1,832 account disagreements). CREST: superior detection and
        explanation quality unsupported. Transfer interpretation depends on dataset and
        ground-truth provenance.
      </Notice>

      {/* Interactive Analysis Limitations Section */}
      <Panel title="Interactive Analysis Boundaries & Operational Limits" tag="CLIENT-SIDE CONSTRAINTS">
        <div className="panel-body">
          <div style={{ display: "grid", gap: "12px", fontSize: "12px", color: "#94a3b8", lineHeight: 1.6 }}>
            <div>
              <strong style={{ color: "#f8fafc", display: "block" }}>
                1. Browser Memory & Scale Boundaries
              </strong>
              Local uploads accept at most 25 MB and 25,000 records. Larger files are rejected without partial analysis. Graph rendering shows a disclosed bounded subset; scores use all accepted records. Sessions clear on refresh unless you explicitly save a local recovery snapshot. Snapshots retain account aggregates, exclude raw rows, expire after 7 days and are removed on the next visit. Browser storage restrictions may prevent saving.
            </div>
            <div>
              <strong style={{ color: "#f8fafc", display: "block" }}>
                2. Heuristic Structural Anomaly vs Supervised ML Predictions
              </strong>
              Interactive uploaded dataset scoring evaluates deterministic topological patterns (in/out degree asymmetry, directed cycles, net flow dispersal, and volume z-scores). These metrics identify graph anomalies, not legal proof of fraud or supervised model predictions.
            </div>
            <div>
              <strong style={{ color: "#f8fafc", display: "block" }}>
                3. Ground-Truth Absence in Custom Files
              </strong>
              Unless explicit ground-truth labels are provided in the upload schema, anomaly scores represent structural deviations without empirical precision/recall verification.
            </div>
            <div>
              <strong style={{ color: "#f8fafc", display: "block" }}>
                4. Transductive Subgraph Limits
              </strong>
              Extracted graph metrics are transductive: they reflect only the relationships present within the uploaded file. Truncated or windowed transactions cannot capture external out-of-band banking counterparties.
            </div>
          </div>
        </div>
      </Panel>

      {!r.data ? (
        <State {...r} />
      ) : (
        r.data.items.map((x, index) => (
          <details key={x.topic} open><summary><span className="eyebrow">{String(index + 1).padStart(2, "0")}</span>{x.topic}</summary><p className="eyebrow">{x.assessment}</p>
            <div className="panel-body">
              <p>{x.description}</p>
            </div>
          </details>
        ))
      )}
      <Panel title="Read the status precisely">
        <div className="panel-body">
          <p>
            Completed refers to execution. Reproducible refers to repeated
            outputs on the same inputs. Verified refers to authenticated
            artifact bytes. None establishes ground-truth validity. Exploratory
            diagnostics describe model sensitivity; unsupported conclusions
            remain unsupported.
          </p>
        </div>
      </Panel>
    </>
  );
}
