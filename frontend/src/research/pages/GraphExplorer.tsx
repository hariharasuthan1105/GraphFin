import { useEffect, useRef, useState } from "react";
import { Heading, Notice, Panel, State, Table, Qualifications } from "../ui";
import { fmt } from "../state";
import { query } from "../client";
import { graphRequest, useGraphCatalog } from "../graph/client";
import type { GraphSession, GraphNeighborhood } from "../graph/contract";
import GraphCanvas from "../graph/GraphCanvas";
import Inspector from "../graph/Inspector";
import "../graph/graph.css";

const iso = (seconds: number) =>
  new Date(seconds * 1000).toISOString().slice(0, 19);
export default function GraphExplorer() {
  const initial = new URLSearchParams(location.hash.split("?")[1] ?? "");
  const [dataset, setDataset] = useState(
    ["ibm-5k", "ibm-50k", "paysim"].includes(initial.get("dataset_id") ?? "")
      ? initial.get("dataset_id")!
      : "ibm-5k",
  );
  const [experiment, setExperiment] = useState(
    initial.get("experiment_id") ?? "baseline-5k-E4-s42-m42",
  );
  const [requestedRank, setRequestedRank] = useState(initial.get("rank") ?? "");
  const metadata = useGraphCatalog();
  const [session, setSession] = useState<GraphSession>();
  const [data, setData] = useState<GraphNeighborhood>();
  const [focus, setFocus] = useState("");
  const [selected, setSelected] = useState("");
  const [diagnostic, setDiagnostic] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();
  const controller = useRef<AbortController | null>(null);
  const [depth, setDepth] = useState(1);
  const [direction, setDirection] = useState("both");
  const [limit, setLimit] = useState(100);
  const [minCount, setMinCount] = useState(1);
  const [minAmount, setMinAmount] = useState(0);
  const [fullTime, setFullTime] = useState(true);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [list, setList] = useState("nodes");
  const ds = metadata.data?.datasets.find((x) => x.dataset_id === dataset);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (!session) return;
    const timer = setTimeout(() => {
      controller.current?.abort();
      setData(undefined);
      setSession(undefined);
      setBusy(false);
      setError(new Error("Graph session expired. Open a new approved lens."));
    }, session.expires_in_seconds * 1000);
    return () => clearTimeout(timer);
  }, [session]);
  function cancel() {
    controller.current?.abort();
    setData(undefined);
    setSession(undefined);
    setFocus("");
    setSelected("");
    setDiagnostic(undefined);
    setError(undefined);
    setBusy(false);
  }
  function selectDataset(value: string) {
    cancel();
    setDataset(value);
    setExperiment(
      value === "ibm-50k"
        ? "baseline-50k-E4-s42-m42"
        : "baseline-5k-E4-s42-m42",
    );
    setRequestedRank("");
    setFullTime(true);
  }
  async function fetchNeighborhood(
    current: GraphSession,
    ref: string,
    signal: AbortSignal,
    reset = false,
  ) {
    const a = reset || fullTime ? undefined : Date.parse(start + "Z") / 1000;
    const b = reset || fullTime ? undefined : Date.parse(end + "Z") / 1000;
    if (
      (a !== undefined && !Number.isFinite(a)) ||
      (b !== undefined && !Number.isFinite(b))
    )
      throw new Error("Set a valid UTC time window.");
    const path = query("/neighborhood", {
      focus_ref: ref,
      depth: reset ? 1 : depth,
      direction: reset ? "both" : direction,
      max_nodes: reset ? 100 : limit,
      max_edges: 500,
      min_count: reset ? 1 : minCount,
      min_amount: reset ? 0 : minAmount,
      start: a,
      end: b,
    });
    const response = await graphRequest<GraphNeighborhood>(
      path,
      "GraphNeighborhood",
      signal,
      current.session_id,
    );
    if (!signal.aborted) {
      setData(response);
      setFocus(ref);
      setSelected(ref);
      setDiagnostic(undefined);
    }
  }
  async function open() {
    if (!ds || ds.status !== "verified") return;
    if (!ds.experiments.some((x) => x.experiment_id === experiment)) {
      setError(new Error("Select a supported experiment for this dataset."));
      return;
    }
    if (
      requestedRank &&
      (!/^\d+$/.test(requestedRank) ||
        Number(requestedRank) < 1 ||
        Number(requestedRank) > 20)
    ) {
      setError(
        new Error("Only approved descending ranks 1–20 can open a graph lens."),
      );
      return;
    }
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setError(undefined);
    setData(undefined);
    setSession(undefined);
    try {
      const s = await graphRequest<GraphSession>(
        query("/session", {
          dataset_id: dataset,
          experiment_id: experiment,
          rank: requestedRank ? Number(requestedRank) : undefined,
        }),
        "GraphSession",
        c.signal,
      );
      if (c.signal.aborted) return;
      setSession(s);
      setFullTime(true);
      setDepth(1);
      setDirection("both");
      setLimit(100);
      setMinCount(1);
      setMinAmount(0);
      setStart(iso(s.dataset.time_start!));
      setEnd(iso(s.dataset.time_end!));
      await fetchNeighborhood(s, s.focus_ref, c.signal, true);
    } catch (e) {
      if (!c.signal.aborted)
        setError(
          e instanceof Error ? e : new Error("Graph evidence unavailable."),
        );
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }
  async function apply(ref = focus) {
    if (!session) return;
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setError(undefined);
    setDiagnostic(undefined);
    try {
      await fetchNeighborhood(session, ref, c.signal);
    } catch (e) {
      if (!c.signal.aborted) {
        setError(e instanceof Error ? e : new Error("Graph unavailable."));
        setData(undefined);
      }
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }
  function choose(ref: string) {
    setSelected(ref);
    setDiagnostic(undefined);
  }
  return (
    <>
      <Heading index="09" title="Graph Explorer">
        Explore a bounded lens of recorded transaction relationships. Every edge
        comes from the verified source; no model is run by interaction.
      </Heading>
      <a
        className="graph-header-link"
        href={"#/datasets?dataset_id=" + dataset}
      >
        Dataset Explorer → Download Dataset Report (PDF)
      </a>
      <Qualifications />
      {!metadata.data ? (
        <State error={metadata.error} retry={() => location.reload()} />
      ) : (
        <>
          <div className="graph-lens-grid">
            <aside className="graph-controls" aria-label="Graph query controls">
              <span className="eyebrow">DATA / QUERY LENS</span>
              <label>
                Dataset and tier
                <select
                  value={dataset}
                  onChange={(e) => selectDataset(e.target.value)}
                >
                  {metadata.data.datasets.map((x) => (
                    <option key={x.dataset_id} value={x.dataset_id}>
                      {x.name}
                      {x.status === "unavailable" ? " / unavailable" : ""}
                    </option>
                  ))}
                </select>
              </label>
              {ds?.status !== "verified" ? (
                <p role="status">
                  Topology unavailable: {ds?.reason ?? "not registered"}. PaySim
                  labels remain unresolved; its dataset report is available.
                </p>
              ) : (
                <>
                  <label>
                    Frozen experiment
                    <select
                      value={experiment}
                      onChange={(e) => {
                        cancel();
                        setExperiment(e.target.value);
                        setRequestedRank("");
                      }}
                    >
                      {ds.experiments.map((x) => (
                        <option key={x.experiment_id} value={x.experiment_id}>
                          {x.method} / split {x.split_seed} / model{" "}
                          {x.model_seed}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p>
                    Snapshot: full supplied observation. Version {ds.version}.{" "}
                    {fmt(ds.approved_scope_nodes, 0)} approved accounts of{" "}
                    {fmt(ds.total_nodes, 0)}; this is a restricted disclosure
                    scope.
                  </p>
                  <button disabled={busy} onClick={open}>
                    {busy && !session
                      ? "Opening verified lens…"
                      : "Open approved graph lens"}
                  </button>
                  {requestedRank && (
                    <p>
                      Opening descending saved rank {requestedRank}. Unsafe or
                      out-of-scope linkage is rejected.
                    </p>
                  )}
                  {session && (
                    <>
                      <label>
                        Focus account
                        <select
                          value={focus}
                          onChange={(e) => setFocus(e.target.value)}
                        >
                          {[
                            ...new Map([
                              ...(data?.nodes ?? []).map(
                                (n) =>
                                  [
                                    n.node_ref,
                                    { label: n.display_id },
                                  ] as const,
                              ),
                              ...session.anchors.map(
                                (a) =>
                                  [
                                    a.node_ref,
                                    { label: a.display_id + " / " + a.role },
                                  ] as const,
                              ),
                            ]).entries(),
                          ].map(([ref, item]) => (
                            <option key={ref} value={ref}>
                              {item.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Neighborhood depth
                        <select
                          value={depth}
                          onChange={(e) => setDepth(Number(e.target.value))}
                        >
                          <option value={1}>1 hop</option>
                          <option value={2}>2 hops</option>
                        </select>
                      </label>
                      <label>
                        Direction
                        <select
                          value={direction}
                          onChange={(e) => setDirection(e.target.value)}
                        >
                          <option value="both">Incoming and outgoing</option>
                          <option value="incoming">Incoming paths</option>
                          <option value="outgoing">Outgoing paths</option>
                        </select>
                      </label>
                      <label>
                        Visible node limit
                        <select
                          value={limit}
                          onChange={(e) => setLimit(Number(e.target.value))}
                        >
                          {[25, 50, 100, 250].map((n) => (
                            <option key={n}>{n}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Minimum transaction count
                        <input
                          type="number"
                          min={1}
                          max={1000000}
                          value={minCount}
                          onChange={(e) => setMinCount(Number(e.target.value))}
                        />
                      </label>
                      <label>
                        Minimum aggregate amount
                        <input
                          type="number"
                          min={0}
                          max={1e15}
                          step="any"
                          value={minAmount}
                          onChange={(e) => setMinAmount(Number(e.target.value))}
                        />
                      </label>
                      <label className="graph-check">
                        <input
                          type="checkbox"
                          checked={fullTime}
                          onChange={(e) => setFullTime(e.target.checked)}
                        />
                        Full source time window
                      </label>
                      <label>
                        From (synthetic UTC)
                        <input
                          type="datetime-local"
                          step="1"
                          disabled={fullTime}
                          value={start}
                          onChange={(e) => setStart(e.target.value)}
                        />
                      </label>
                      <label>
                        To (synthetic UTC)
                        <input
                          type="datetime-local"
                          step="1"
                          disabled={fullTime}
                          value={end}
                          onChange={(e) => setEnd(e.target.value)}
                        />
                      </label>
                      <button disabled={busy} onClick={() => apply()}>
                        {busy
                          ? "Reading bounded graph…"
                          : "Apply server filters"}
                      </button>
                      <p className="graph-field-hint">
                        All filters request a new bounded neighborhood. They do
                        not recalculate scientific features or model scores.
                        Time subwindows hide full-snapshot annotations.
                      </p>
                    </>
                  )}
                </>
              )}
            </aside>
            <div>
              {error ? (
                <State error={error} retry={open} />
              ) : busy ? (
                <div className="state" role="status">
                  <span className="pixels" aria-hidden="true">
                    ▪ ▪ ▪ ▪
                  </span>
                  <p>Reading verified, bounded graph evidence…</p>
                </div>
              ) : data ? (
                <>
                  <GraphCanvas
                    data={data}
                    selected={selected}
                    onNode={choose}
                    onEdge={choose}
                  />
                  {data.edges.length === 0 && (
                    <div className="graph-empty" role="status">
                      No relationships match this bounded query. The focus
                      account remains visible; try a lower threshold or broader
                      time window.
                    </div>
                  )}
                </>
              ) : (
                <div className="graph-empty">
                  Open an approved graph lens to inspect recorded topology. No
                  random substitute network is displayed.
                </div>
              )}
            </div>
            {data && (
              <Inspector
                data={data}
                selected={selected}
                onExplore={apply}
                diagnostic={diagnostic}
                setDiagnostic={setDiagnostic}
              />
            )}
          </div>
          {data && (
            <>
              <div className="graph-summary">
                <span>
                  {data.nodes.length} nodes / {data.edges.length} edges
                </span>
                <span>
                  {data.depth} hop / {data.direction}
                </span>
                <span>{data.remaining_queries} queries remaining</span>
                <span>{data.query_seconds.toFixed(3)} s server query</span>
              </div>
              {data.truncated && (
                <Notice>
                  <strong>Partial graph.</strong> Bounded disclosure/truncation:{" "}
                  {data.truncation_reasons.join(", ")}. The visible graph is not
                  the full transaction network.
                </Notice>
              )}
              {data.temporal_subset && (
                <Notice>
                  Temporal subset: frozen full-snapshot anomaly scores and
                  diagnostics are unavailable for this view.
                </Notice>
              )}
              <div
                className="graph-table-tabs"
                role="group"
                aria-label="Accessible graph lists"
              >
                <button
                  aria-pressed={list === "nodes"}
                  onClick={() => setList("nodes")}
                >
                  Accounts ({data.nodes.length})
                </button>
                <button
                  aria-pressed={list === "edges"}
                  onClick={() => setList("edges")}
                >
                  Relationships ({data.edges.length})
                </button>
              </div>
              <Panel
                title={
                  list === "nodes"
                    ? "Account list"
                    : "Directed relationship list"
                }
                tag="KEYBOARD / INSPECTION"
              >
                <div className="graph-access-list">
                  {list === "nodes" ? (
                    <Table
                      caption="Keyboard-accessible account selection; metrics use the full source snapshot"
                      headers={[
                        "Account",
                        "Incoming",
                        "Outgoing",
                        "Saved anomaly score",
                      ]}
                      rows={data.nodes.map((n) => [
                        <button
                          key="account"
                          onClick={() => choose(n.node_ref)}
                          aria-pressed={selected === n.node_ref}
                        >
                          {n.display_id}
                        </button>,
                        n.in_degree,
                        n.out_degree,
                        fmt(n.anomaly_score, 8),
                      ])}
                    />
                  ) : (
                    <Table
                      caption="Keyboard-accessible directed relationship selection; amounts in dataset units"
                      headers={[
                        "Relationship",
                        "Sender",
                        "Receiver",
                        "Transactions",
                        "Amount",
                      ]}
                      rows={data.edges.map((e, i) => [
                        <button
                          key="edge"
                          onClick={() => choose(e.edge_ref)}
                          aria-pressed={selected === e.edge_ref}
                        >
                          Inspect relationship {i + 1}
                        </button>,
                        data.nodes.find((n) => n.node_ref === e.source_ref)
                          ?.display_id,
                        data.nodes.find((n) => n.node_ref === e.target_ref)
                          ?.display_id,
                        e.transaction_count,
                        fmt(e.amount, 2),
                      ])}
                    />
                  )}
                </div>
              </Panel>
              <Notice>
                Graph {data.graph_id} · {data.version}. Node aggregates are
                full-snapshot measures; a reciprocal relationship may be hidden
                by filters. Amounts use {data.amount_unit}. CREST remains
                experimental model sensitivity; superior detection/explanation
                quality is unsupported.
              </Notice>
            </>
          )}
        </>
      )}
    </>
  );
}
