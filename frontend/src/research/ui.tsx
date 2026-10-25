import { useEffect, useState, type ReactNode } from "react";
import { fmt } from "./state";
import type { Experiment } from "./contract";
type Evidence = Pick<Experiment, "status" | "provenance_status">;
export function State({ error, retry }: { error?: Error; retry: () => void }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setSlow(true), 3000);
    return () => clearTimeout(t);
  }, []);
  return error ? (
    <div role="alert" className="state">
      <span className="eyebrow">REQUEST UNAVAILABLE</span>
      <h2>Evidence could not be loaded.</h2>
      <p>{error.message}</p>
      <button onClick={retry}>Retry request ↗</button>
    </div>
  ) : (
    <div className="state" role="status">
      <span className="pixels" aria-hidden="true">
        ▪ ▪ ▪ ▪ ▪
      </span>
      <p>
        {slow
          ? "Still waiting for verified research artifacts…"
          : "Reading research artifacts…"}
      </p>
    </div>
  );
}
export function Panel({
  title,
  tag,
  children,
}: {
  title: string;
  tag?: string;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {tag && <span className="eyebrow">{tag}</span>}
      </div>
      {children}
    </section>
  );
}
export function Heading({
  index,
  title,
  children,
}: {
  index: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <p className="eyebrow red">RESEARCH / {index}</p>
      <h1 tabIndex={-1}>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}
export function Notice({ children }: { children: ReactNode }) {
  return (
    <aside className="notice">
      <span aria-hidden="true">↳</span>
      <div>{children}</div>
    </aside>
  );
}
export function Status({ value }: { value: Evidence }) {
  return (
    <div className="status-line">
      <span className="badge">□ {value.status}</span>
      <span className="badge">
        Labels: {value.provenance_status.replaceAll("_", " ")}
      </span>
    </div>
  );
}
export function Qualifications() {
  return (
    <Notice>
      IBM AML: upstream account-label lineage partially verified. PaySim:
      conflicting label provenance unresolved. Verified artifacts do not
      establish ground-truth validity.
    </Notice>
  );
}
export function Table({
  headers,
  rows,
  caption,
}: {
  headers: string[];
  rows: ReactNode[][];
  caption: string;
}) {
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={caption}
    >
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((h) => (
              <th scope="col" key={h}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => (
                <td key={j}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="empty">No matching records. Try another filter.</p>
      )}
    </div>
  );
}
export function Pager({
  page,
  total,
  size,
  setPage,
}: {
  page: number;
  total: number;
  size: number;
  setPage: (v: number) => void;
}) {
  return (
    <div className="pager">
      <span>
        {total} records / page {page} of {Math.max(1, Math.ceil(total / size))}
      </span>
      <div>
        <button disabled={page === 1} onClick={() => setPage(page - 1)}>
          ← Previous
        </button>
        <button
          disabled={page * size >= total}
          onClick={() => setPage(page + 1)}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
export function Hash({ value }: { value?: string | null }) {
  const [message, setMessage] = useState("");
  return value ? (
    <span className="hash">
      <code title={value}>{value.slice(0, 12)}…</code>
      <button
        aria-label="Copy full checksum"
        onClick={() =>
          navigator.clipboard.writeText(value).then(
            () => setMessage("Copied"),
            () => setMessage("Copy unavailable"),
          )
        }
      >
        Copy
      </button>
      <span role="status">{message}</span>
    </span>
  ) : (
    <>Unavailable</>
  );
}
export function Tier({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label>
      Network tier
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="ibm-5k">IBM AML / 5K</option>
        <option value="ibm-50k">IBM AML / ~50K</option>
      </select>
    </label>
  );
}
export function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note: string;
}) {
  return (
    <div className="metric">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </div>
  );
}
export function Chart({
  labels,
  values,
  title,
}: {
  labels: string[];
  values: (number | null | undefined)[];
  title: string;
}) {
  const max = Math.max(
    ...values.filter((v): v is number => typeof v === "number"),
    0.001,
  );
  return (
    <figure className="chart">
      <figcaption>
        {title} <span>higher values →</span>
      </figcaption>
      {labels.map((label, i) => (
        <div className="bar-row" key={label}>
          <span>{label}</span>
          <div className="bar-track">
            <div
              className={"bar bar-" + (i % 3)}
              style={{
                transform: `scaleX(${values[i] == null ? 0 : values[i]! / max})`,
              }}
            />
          </div>
          <code>{fmt(values[i])}</code>
        </div>
      ))}
      <p className="chart-axis">
        0 — {fmt(max)} · linear scale · exact values in the table below
      </p>
    </figure>
  );
}
