import { useResearch, fmt } from "../state";
import { useState } from "react";
import type { Page_Diagnostic_, Diagnostic } from "../contract";
import { State, Heading, Panel, Table, Pager, Notice, Status } from "../ui";
import { query } from "../client";
import { useSession } from "../sessionContext";
function Detail({ id }: { id: string }) {
  const r = useResearch<Diagnostic>("/diagnostics/" + id, "Diagnostic");
  return !r.data ? (
    <State {...r} />
  ) : (
    <Panel title="Saved evidence sensitivity" tag={r.data.diagnostic_id}>
      <div className="panel-body">
        <Status value={r.data} />
        <p>
          {r.data.account_token} / {r.data.method}
        </p>
        <p>{r.data.reason ?? "No additional reason recorded."}</p>
      </div>
      <Table
        caption="Stored omission and score evidence"
        headers={[
          "Family",
          "Omitted count",
          "Evidence fraction",
          "Amount fraction",
          "Intervened score",
          "Signed fidelity",
        ]}
        rows={[
          [
            r.data.family ?? "Unavailable",
            fmt(r.data.omitted_count, 0),
            fmt(r.data.omitted_fraction),
            fmt(r.data.omitted_amount_fraction),
            fmt(r.data.intervened_score),
            fmt(r.data.signed_fidelity),
          ],
        ]}
      />
      <Notice>
        Stability and runtime are not exposed by this API projection. Tokens are
        process-local and must not be treated as durable account identities.
      </Notice>
    </Panel>
  );
}

export default function Diagnostics() {
  const { activeSession } = useSession();
  const [selectedAccId, setSelectedAccId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [id, setId] = useState<string>();
  const r = useResearch<Page_Diagnostic_>(
    query("/diagnostics", { page_number: page, page_size: 10 }),
    "Page_Diagnostic_",
  );

  const inspectedAcc = activeSession?.accounts.find(
    (a) => a.id === (selectedAccId || activeSession.topAnomalies[0]?.id),
  );

  return (
    <>
      <Heading index="09" title="Diagnostics & explanation sensitivity">
        Experimental model-sensitivity diagnostics on research benchmarks, and local flow concentration audits.
      </Heading>

      {activeSession && (
        <Panel
          title="Active Dataset: Local Flow Sensitivity & Structural Drivers"
          tag="INTERACTIVE AUDIT"
        >
          <div className="panel-body">
            <div style={{ marginBottom: "14px" }}>
              <label style={{ fontSize: "12px", color: "#94a3b8" }}>
                Select Inspected Account:
                <select
                  value={inspectedAcc?.id || ""}
                  onChange={(e) => setSelectedAccId(e.target.value)}
                  style={{
                    marginLeft: "8px",
                    background: "#08090d",
                    color: "#f8fafc",
                    border: "1px solid #1e2434",
                    borderRadius: "4px",
                    padding: "4px 8px",
                    fontFamily: "IBM Plex Mono, monospace",
                  }}
                >
                  {activeSession.accounts
                    .slice(0, 30)
                    .map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.id} (Score: {a.anomalyScore.toFixed(3)})
                      </option>
                    ))}
                </select>
              </label>
            </div>

            {inspectedAcc && (
              <div
                style={{
                  background: "#08090d",
                  border: "1px solid #1a1e28",
                  borderRadius: "4px",
                  padding: "12px",
                  marginBottom: "12px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontFamily: "IBM Plex Mono, monospace", color: "#ffffff", fontWeight: 700 }}>
                    {inspectedAcc.id}
                  </span>
                  <span style={{ fontSize: "11px", color: inspectedAcc.anomalyScore >= 0.7 ? "#ef4444" : "#b44a50" }}>
                    Risk Tier: {(inspectedAcc.anomalyScore * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
                  <div>Total Sent: ${inspectedAcc.totalSent.toLocaleString()} · Total Received: ${inspectedAcc.totalReceived.toLocaleString()}</div>
                  <div>Primary Topological Driver: {inspectedAcc.patterns.join(", ") || "Moderate Degree Elevation"}</div>
                  <div>Direct Counterparties: {inspectedAcc.counterparties.length} connected entities</div>
                </div>
              </div>
            )}

            <p style={{ margin: 0, fontSize: "11px", color: "#64748b", lineHeight: 1.4 }}>
              <strong>Scientific Honesty Note:</strong> CREST counterparty intervention models (shown below) were experimentally evaluated on frozen academic benchmarks. For interactive uploaded datasets, GraphFin provides deterministic local flow concentration metrics without falsifying offline ablation interventions.
            </p>
          </div>
        </Panel>
      )}
      <Notice>
        CREST detection superiority has not been demonstrated. CREST explanation
        superiority has not been demonstrated. Score changes are neither proof
        of fraud nor causal criminal evidence.
      </Notice>
      {!r.data ? (
        <State {...r} />
      ) : (
        <>
          <Panel title="Saved diagnostic availability" tag={r.data.status}>
            <Table
              caption="Pseudonymized saved explanations; no interventions generated"
              headers={[
                "Diagnostic",
                "Account token",
                "Method",
                "Available",
                "Valid",
                "Baseline score",
                "Signed fidelity",
              ]}
              rows={r.data.items.map((x) => [
                <button key="select" onClick={() => setId(x.diagnostic_id)}>
                  {x.diagnostic_id}
                </button>,
                x.account_token,
                x.method,
                x.available ? "Available" : "Unavailable",
                x.valid == null ? "Unavailable" : x.valid ? "Yes" : "No",
                fmt(x.baseline_score),
                fmt(x.signed_fidelity),
              ])}
            />
            <Pager
              page={page}
              setPage={(p) => {
                setPage(p);
                setId(undefined);
              }}
              size={10}
              total={r.data.total}
            />
          </Panel>
          {id && <Detail id={id} />}
        </>
      )}
    </>
  );
}
