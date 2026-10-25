import { useResearch, TITLE, fmt } from "../state";
import type { Overview as OverviewData } from "../contract";
import { State, Metric, Panel, Notice } from "../ui";
export default function Overview() {
  const r = useResearch<OverviewData>("/overview", "Overview");
  return (
    <>
      <section className="hero">
        <div className="hero-network" aria-hidden="true">
          <svg viewBox="0 0 500 350">
            <g fill="none" stroke="#77777d" strokeWidth=".7">
              <path d="M20 220L100 100 220 50 300 180 440 80M100 100L170 260 300 180 420 300M220 50L170 260 420 300 440 80M20 220L300 180 480 220M100 100L440 80" />
            </g>
            <g fill="#f5f5f5">
              {[
                [20, 220],
                [100, 100],
                [220, 50],
                [300, 180],
                [440, 80],
                [170, 260],
                [420, 300],
                [480, 220],
              ].map(([x, y]) => (
                <rect key={x} x={x - 3} y={y - 3} width="6" height="6" />
              ))}
            </g>
          </svg>
        </div>
        <div className="hero-copy">
          <span className="eyebrow">SYSTEM / 008 — RESEARCH TERMINAL</span>
          <div className="hero-word">
            GRAPHFIN<span className="red">_</span>
          </div>
          <h1>Financial Network Intelligence</h1>
          <p>
            An auditable view of graph-based anomaly research.
            <br />
            Explore the evidence. Understand its boundaries.
          </p>
        </div>
        <div className="hero-foot">
          <span>GRAPH SYSTEMS / EMPIRICAL RESEARCH</span>
          <span>READ-ONLY ●</span>
        </div>
      </section>
      {!r.data ? (
        <State {...r} />
      ) : (
        <>
          <div className="metrics">
            <Metric
              label="Completed runs"
              value={fmt(r.data.completed_run_count, 0)}
              note={`${r.data.completed_evaluation_count} method evaluations`}
            />
            <Metric
              label="Research methods"
              value={fmt(r.data.available_methods.length, 0)}
              note={r.data.available_methods.join(" / ")}
            />
            <Metric
              label="Network scales"
              value={fmt(r.data.scales.length, 0)}
              note={r.data.scales.join(" / ") + " accounts"}
            />
            <Metric
              label="Replay evidence"
              value={
                r.data.reproducibility_available ? "Available" : "Unavailable"
              }
              note="Same-input reproducibility"
            />
          </div>
          <div className="grid-two">
            <Panel title="Research coverage" tag="01 / DATASETS">
              {r.data.datasets.map((d) => (
                <a className="list-item" key={d.dataset_id} href={"#/datasets"}>
                  <div>
                    <strong>{d.name}</strong>
                    <small>{d.provenance_status.replaceAll("_", " ")}</small>
                  </div>
                  <code>
                    {fmt(d.accounts, 0)}{" "}
                    <span className="muted">accounts ↗</span>
                  </code>
                </a>
              ))}
            </Panel>
            <Panel title="Evidence, not assumptions" tag="02 / SCOPE">
              <div className="panel-body">
                <p>
                  Compare frozen baselines on compatible held-out populations.
                  Keep calibration, split variation and model randomness
                  distinct.
                </p>
                <a className="action-link" href="#/comparison">
                  Explore model comparison <span>↗</span>
                </a>
                <p className="eyebrow" style={{ marginTop: 22 }}>
                  MODEL-SEED EVIDENCE /{" "}
                  {r.data.model_seed_analysis_available
                    ? "AVAILABLE"
                    : "UNAVAILABLE"}
                </p>
                <p className="eyebrow">
                  CREST DIAGNOSTICS /{" "}
                  {r.data.crest_diagnostics_available
                    ? "AVAILABLE"
                    : "UNAVAILABLE"}
                </p>
              </div>
            </Panel>
          </div>
          <Notice>
            IBM AML label lineage is partially verified. PaySim label provenance
            remains unresolved. CREST detection and explanation superiority have
            not been demonstrated.
          </Notice>
          {r.data.unavailable_components.length > 0 && (
            <Notice>
              Unavailable components: {r.data.unavailable_components.join(", ")}
            </Notice>
          )}
          <Panel title="The research project" tag="PROJECT / INFORMATION">
            <div className="panel-body">
              <p className="project-title">{TITLE}</p>
              <p>
                Reproducible experiments and transparent limitations for
                synthetic financial transaction networks. This system is not a
                certified real-world fraud-monitoring service.
              </p>
            </div>
          </Panel>
        </>
      )}
    </>
  );
}
