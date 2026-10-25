import { useResearch, fmt } from "../state";
import { useState } from "react";
import type { Page_Diagnostic_, Diagnostic } from "../contract";
import { State, Heading, Panel, Table, Pager, Notice, Status } from "../ui";
import { query } from "../client";
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
  const [page, setPage] = useState(1);
  const [id, setId] = useState<string>();
  const r = useResearch<Page_Diagnostic_>(
    query("/diagnostics", { page_number: page, page_size: 10 }),
    "Page_Diagnostic_",
  );
  return (
    <>
      <Heading index="07" title="CREST diagnostics">
        Experimental model-sensitivity diagnostic
      </Heading>
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
