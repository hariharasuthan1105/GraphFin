import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { TITLE } from "./research/state";
import { SessionProvider, useSession } from "./research/sessionContext";
import "./research/research.css";

const pages = {
  overview: lazy(() => import("./research/pages/Overview")),
  datasets: lazy(() => import("./research/pages/Datasets")),
  analyze: lazy(() => import("./research/pages/DatasetAnalysis")),
  graph: lazy(() => import("./research/pages/GraphExplorer")),
  experiments: lazy(() => import("./research/pages/Experiments")),
  comparison: lazy(() => import("./research/pages/Comparison")),
  seeds: lazy(() => import("./research/pages/Seeds")),
  reproducibility: lazy(() => import("./research/pages/Reproducibility")),
  diagnostics: lazy(() => import("./research/pages/Diagnostics")),
  limitations: lazy(() => import("./research/pages/Limitations")),
  reports: lazy(() => import("./research/pages/Reports")),
};

const navItems = [
  { key: "overview", label: "Overview", num: "01" },
  { key: "datasets", label: "Dataset Explorer", num: "02" },
  { key: "analyze", label: "Interactive Analysis", num: "03" },
  { key: "graph", label: "Graph Explorer", num: "04" },
  { key: "experiments", label: "Experiment Registry", num: "05" },
  { key: "comparison", label: "Model Comparison", num: "06" },
  { key: "seeds", label: "Seed Analysis", num: "07" },
  { key: "reproducibility", label: "Reproducibility", num: "08" },
  { key: "diagnostics", label: "CREST Diagnostics", num: "09" },
  { key: "limitations", label: "Research Limitations", num: "10" },
  { key: "reports", label: "Reports & Downloads", num: "11" },
];

function locationRoute() {
  const r = window.location.hash.slice(2).split(/[/?]/)[0] || "overview";
  if (r === "graph-explorer") return "graph";
  if (r === "dataset-reports") return "reports";
  return r;
}

function MainShell() {
  const [route, setRoute] = useState(locationRoute);
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLButtonElement>(null);
  const { appMode, setAppMode, activeSession } = useSession();

  useEffect(() => {
    const update = () => {
      setRoute(locationRoute());
      setOpen(false);
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);

  const currentItem = navItems.find((item) => item.key === route);
  const currentLabel = currentItem?.label || "Research Dashboard";

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

        {/* Sidebar Mode Toggle */}
        <div style={{ padding: "0 14px 14px 14px" }}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              background: "#101012",
              border: "1px solid #303034",
              borderRadius: "4px",
              padding: "4px",
            }}
          >
            <button
              type="button"
              onClick={() => setAppMode("interactive")}
              style={{
                background: appMode === "interactive" ? "#842d35" : "transparent",
                color: appMode === "interactive" ? "#ffffff" : "#a6a6a6",
                border: appMode === "interactive" ? "1px solid #b44a50" : "1px solid transparent",
                borderRadius: "3px",
                padding: "6px 8px",
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                fontWeight: 600,
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span>✦</span> Interactive Analysis
            </button>
            <button
              type="button"
              onClick={() => setAppMode("research")}
              style={{
                background: appMode === "research" ? "#842d35" : "transparent",
                color: appMode === "research" ? "#ffffff" : "#a6a6a6",
                border: appMode === "research" ? "1px solid #b44a50" : "1px solid transparent",
                borderRadius: "3px",
                padding: "6px 8px",
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                fontWeight: 600,
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span>⚲</span> Research Evidence
            </button>
          </div>
        </div>

        <div className="nav-label eyebrow">NAVIGATION / 11 SECTIONS</div>
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
          <p className="eyebrow">
            {appMode === "interactive" ? "INTERACTIVE SESSION" : "READ-ONLY RESEARCH"}
          </p>
          <p>
            {appMode === "interactive" ? (
              activeSession ? (
                <span style={{ color: "#f5f5f5", wordBreak: "break-all" }}>
                  <b style={{ color: "#c04b52" }}>●</b> {activeSession.summary.datasetName} ({activeSession.accounts.length} acc)
                </span>
              ) : (
                "No custom dataset uploaded yet."
              )
            ) : (
              "Explore verified benchmarks & evidence."
            )}
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
            {/* Topbar Mode Switcher */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "3px",
                background: "#101012",
                border: "1px solid #303034",
                borderRadius: "4px",
                padding: "2px",
              }}
            >
              <button
                type="button"
                onClick={() => setAppMode("interactive")}
                style={{
                  background: appMode === "interactive" ? "#842d35" : "transparent",
                  color: appMode === "interactive" ? "#ffffff" : "#a6a6a6",
                  border: appMode === "interactive" ? "1px solid #b44a50" : "1px solid transparent",
                  borderRadius: "3px",
                  padding: "4px 8px",
                  fontSize: "10px",
                  fontFamily: "IBM Plex Mono, monospace",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ✦ INTERACTIVE
              </button>
              <button
                type="button"
                onClick={() => setAppMode("research")}
                style={{
                  background: appMode === "research" ? "#842d35" : "transparent",
                  color: appMode === "research" ? "#ffffff" : "#a6a6a6",
                  border: appMode === "research" ? "1px solid #b44a50" : "1px solid transparent",
                  borderRadius: "3px",
                  padding: "4px 8px",
                  fontSize: "10px",
                  fontFamily: "IBM Plex Mono, monospace",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ⚲ RESEARCH
              </button>
            </div>

            <span style={{ color: "#303034" }}>|</span>

            {/* Active Session Indicator */}
            {activeSession ? (
              <span
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "10px",
                  letterSpacing: "0.04em",
                  color: "#f5f5f5",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#171719",
                  padding: "4px 8px",
                  borderRadius: "3px",
                  border: "1px solid #303034",
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    background: "#c04b52",
                    borderRadius: "50%",
                    display: "inline-block",
                  }}
                />
                SESSION ACTIVE
              </span>
            ) : (
              <span
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "10px",
                  letterSpacing: "0.04em",
                  color: "#77777d",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#101012",
                  padding: "4px 8px",
                  borderRadius: "3px",
                  border: "1px solid #303034",
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    background: "#303034",
                    borderRadius: "50%",
                    display: "inline-block",
                  }}
                />
                READY
              </span>
            )}
          </div>
        </header>

        <main id="main" tabIndex={-1} key={route}>
          <Suspense
            fallback={
              <div className="state" role="status">
                <span className="pixels" aria-hidden="true">
                  ▪ ▪ ▪ ▪ ▪
                </span>
                <p>Loading view…</p>
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
          <span>RESEARCH & INTERACTIVE ANOMALY DETECTION / 008</span>
        </footer>
      </div>
    </div>
  );
}

export function App() {
  return (
    <SessionProvider>
      <MainShell />
    </SessionProvider>
  );
}

export default App;
