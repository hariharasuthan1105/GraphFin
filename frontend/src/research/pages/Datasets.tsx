import { useResearch, fmt } from "../state";
import { useState } from "react";
import { DatasetReportDownload } from "../DatasetReportDownload";
import type { Page_Dataset_, Dataset } from "../contract";
import { State, Heading, Panel, Table, Status, Hash, Notice } from "../ui";
function Detail({ id }: { id: string }) {
  const r = useResearch<Dataset>("/datasets/" + id, "Dataset");
  return !r.data ? (
    <State {...r} />
  ) : (
    <Panel title={r.data.name} tag="DATASET / IDENTITY">
      <div className="panel-body">
        <Status value={r.data} />
        <p>{r.data.version}</p>
        <p>{r.data.label_definition}</p>
        <p>{r.data.time_semantics}</p>
        <Hash key="hash" value={r.data.transaction_sha256} />
        <DatasetReportDownload key={id} datasetId={id} />
        {r.data.label_disagreements != null && (
          <Notice>
            Unresolved label conflict: {fmt(r.data.label_disagreements, 0)}{" "}
            account disagreements. Neither label set is selected.
          </Notice>
        )}
      </div>
      <Table
        caption="Distinct label sets — never merged"
        headers={["Label identity", "Accounts", "Positives", "Checksum"]}
        rows={(r.data.label_sets ?? []).map((l) => [
          l.identity,
          fmt(l.accounts, 0),
          fmt(l.positives, 0),
          <Hash key="hash" value={l.sha256} />,
        ])}
      />
    </Panel>
  );
}
export default function Datasets() {
  const r = useResearch<Page_Dataset_>("/datasets", "Page_Dataset_");
  const [id, setId] = useState(() => {
    const requested = new URLSearchParams(
      location.hash.split("?")[1] ?? "",
    ).get("dataset_id");
    return requested && ["ibm-5k", "ibm-50k", "paysim"].includes(requested)
      ? requested
      : "ibm-5k";
  });
  return (
    <>
      <Heading index="02" title="Dataset explorer">
        Synthetic networks. Explicit label identities. Verifiable artifact
        lineage.
      </Heading>
      {!r.data ? (
        <State {...r} />
      ) : (
        <>
          <Panel title="Network inventory" tag="SOURCE / METADATA">
            <Table
              caption="Dataset counts; unavailable fields are not zero"
              headers={[
                "Dataset",
                "Accounts",
                "Transactions",
                "Positive",
                "Negative",
                "Prevalence",
                "Provenance",
              ]}
              rows={r.data.items.map((d) => [
                <button
                  key="select"
                  onClick={() => setId(d.dataset_id)}
                  aria-pressed={id === d.dataset_id}
                >
                  {d.name}
                </button>,
                fmt(d.accounts, 0),
                fmt(d.transactions, 0),
                fmt(d.positives, 0),
                fmt(d.negatives, 0),
                fmt(d.prevalence, 6),
                d.provenance_status.replaceAll("_", " "),
              ])}
            />
          </Panel>
          <Detail id={id} />
        </>
      )}
    </>
  );
}
