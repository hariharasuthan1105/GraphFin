import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { TITLE } from "./research/state";
import "./research/research.css";

const pages = {
  overview: lazy(() => import("./research/pages/Overview")),
  analyze: lazy(() => import("./research/pages/DatasetAnalysis")),
  datasets: lazy(() => import("./research/pages/Datasets")),
  experiments: lazy(() => import("./research/pages/Experiments")),
  comparison: lazy(() => import("./research/pages/Comparison")),
  seeds: lazy(() => import("./research/pages/Seeds")),
  reproducibility: lazy(() => import("./research/pages/Reproducibility")),
  diagnostics: lazy(() => import("./research/pages/Diagnostics")),
  limitations: lazy(() => import("./research/pages/Limitations")),
  graph: lazy(() => import("./research/pages/GraphExplorer")),
};

const navItems = [
  { key: "overview", label: "Overview", num: "01" },
  { key: "datasets", label: "Datasets", num: "02" },
  { key: "experiments", label: "Experiments", num: "03" },
  { key: "comparison", label: "Model Comparison", num: "04" },
  { key: "seeds", label: "Seed Analysis", num: "05" },
  { key: "reproducibility", label: "Reproducibility", num: "06" },
  { key: "diagnostics", label: "CREST Diagnostics", num: "07" },
  { key: "limitations", label: "Research Limitations", num: "08" },
  { key: "graph", label: "Graph Explorer", num: "09" },
];

function locationRoute() {
  const r = window.location.hash.slice(2).split(/[/?]/)[0] || "overview";
  if (r === "graph-explorer") return "graph";
  return r;
}

export function App() {
  const [route, setRoute] = useState(locationRoute);
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const update = () => {
      setRoute(locationRoute());
      setOpen(false);
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);

  const currentLabel =
    navItems.find((item) => item.key === route)?.label ||
    (route === "analyze" ? "Dataset Analysis" : "Research Dashboard");

  useEffect(() => {
    document.title = TITLE + " - " + currentLabel;
  }, [currentLabel]);

  if (route === "workspace") {
    window.location.hash = "#/overview";
    return null;
  }

  const Page = pages[route as keyof typeof pages];

  return (
    <div className="research">
      <a
        className="skip"
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
        }}
      >
        Skip to research content
      </a>
      <aside
        className={"sidebar " + (open ? "is-open" : "")}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setOpen(false);
            menu.current?.focus();
          }
        }}
      >
        <a className="brand" href="#/overview" aria-label="GraphFin overview">
          <span>GRAPHFIN</span>
          <b aria-hidden="true">_</b>
        </a>
        <div className="nav-label eyebrow">RESEARCH WORKSPACE / 09</div>
        <nav aria-label="Research navigation">
          {navItems.map((item) => (
            <a
              key={item.key}
              href={"#/" + item.key}
              aria-current={route === item.key ? "page" : undefined}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.num}
              </span>
              {item.label}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p className="eyebrow">READ-ONLY RESEARCH</p>
          <p>
            Explore methods,
            <br />
            results, and evidence.
          </p>
        </div>
      </aside>
      {open && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="workspace">
        <header className="toolbar">
          <button
            className="menu-toggle"
            ref={menu}
            aria-label="Toggle navigation"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            MENU
          </button>
          <span className="breadcrumb">
            GRAPHFIN <span>/</span> {currentLabel}
          </span>
          <div className="toolbar-right-controls">
            <span
              style={{
                fontFamily: "Silkscreen, monospace",
                fontSize: "9px",
                letterSpacing: "0.08em",
                color: "#f5f5f5",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  background: "#b44a50",
                  display: "inline-block",
                }}
              />
              OPEN RESEARCH ACCESS
            </span>
            <span style={{ color: "#303034" }}>|</span>
            <span className="toolbar-mode">
              <i /> EVIDENCE TERMINAL
            </span>
          </div>
        </header>

        <main id="main" tabIndex={-1} key={route}>
          <Suspense
            fallback={
              <div className="state" role="status">
                <span className="pixels" aria-hidden="true">
                  ▪ ▪ ▪ ▪ ▪
                </span>
                <p>Reading research artifacts…</p>
              </div>
            }
          >
            {Page ? (
              <Page />
            ) : (
              <div className="state">
                <h1>Page not found</h1>
                <a href="#/overview">Return to overview</a>
              </div>
            )}
          </Suspense>
        </main>
        <footer className="research-footer">
          <span>{TITLE}</span>
          <span>RESEARCH, NOT FINANCIAL ADVICE / 008</span>
        </footer>
      </div>
    </div>
  );
}

export default App;
